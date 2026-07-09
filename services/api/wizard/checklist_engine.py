from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.cadastros.equipamentos.models import Equipamento
from core.cadastros.produtos.models import Produto
from core.cadastros.propriedades.models import AreaRural, TipoArea
from core.exceptions import EntityNotFoundError
from core.models.unidade_produtiva import UnidadeProdutiva
from financeiro.models.plano_conta import PlanoConta
from integracoes.models import (
    ExternalRecordAssociation,
    ExternalRecordAssociationStatus,
    IntegrationFeature,
    IntegrationHealth,
    IntegrationHealthStatus,
    IntegrationScope,
    IntegrationStatus,
    IntegrationSyncPolicy,
    MarketplaceIntegracao,
    TenantIntegracao,
)
from integracoes.erp_readiness_service import (
    ErpChecklistRuntime,
    ErpReadinessResult,
    ErpReadinessService,
)
from operacional.models.estoque import Deposito
from wizard.models import (
    ChecklistEvidenceType,
    ChecklistItemStatus,
    ImplantacaoChecklistItem,
    ImplantacaoOperacional,
    PendenciaSeverity,
    PendenciaTipo,
)
from wizard.services import ImplantacaoService

try:
    from datetime import UTC
except ImportError:  # pragma: no cover - Python < 3.11 compatibility
    UTC = timezone.utc  # noqa: UP017


ChecklistVerifier = Callable[
    [ImplantacaoOperacional],
    Awaitable["ChecklistEvaluation"],
]


@dataclass(frozen=True)
class ChecklistEvidence:
    entidade: str
    entidade_id: str | None
    timestamp: datetime
    descricao: str
    evidencia_tipo: str


@dataclass(frozen=True)
class ChecklistEvaluation:
    codigo_item: str
    status: str
    descricao: str
    evidencia: ChecklistEvidence | None
    pendencia_severidade: str | None = None
    pendencia_tipo: str = PendenciaTipo.PENDENCIA.value


class ChecklistEngine:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.implantacao_service = ImplantacaoService(session)
        self.erp_readiness_service = ErpReadinessService(session)
        self._verifiers: dict[str, ChecklistVerifier] = {
            "CHECK_UNIDADE_PRODUTIVA": self._check_unidade_produtiva,
            "CHECK_ESTRUTURA_TERRITORIAL": self._check_estrutura_territorial,
            "CHECK_AGRICULTURA_TALHAO": self._check_talhao_agricultura,
            "CHECK_PECUARIA_PIQUETE": self._check_piquete_pecuaria,
            "CHECK_ESTOQUE_DEPOSITO": self._check_deposito_estoque,
            "CHECK_FINANCEIRO_PLANO_CONTA": self._check_plano_conta,
            "CHECK_PRODUTO_CATALOGO": self._check_catalogo_produto,
            "CHECK_EQUIPAMENTO_CADASTRO": self._check_equipamento,
            "CHECK_CULTURA": self._check_cultura,
            "CHECK_INTEGRACAO_ERP": self._check_integracao_erp,
        }

    async def avaliar_implantacao(
        self,
        implantacao: ImplantacaoOperacional,
    ) -> list[ChecklistEvaluation]:
        implantacao_id = implantacao.id
        await self.implantacao_service.etapa_service.inicializar_etapas_canonicas(implantacao)
        etapas = await self.implantacao_service.etapa_service.listar_etapas(implantacao_id)
        await self.implantacao_service.checklist_service.criar_checklist_base_idempotente(
            implantacao,
            etapas,
        )
        itens = await self.implantacao_service.checklist_service.listar_itens(implantacao_id)
        resultados: list[ChecklistEvaluation] = []
        for item in itens:
            resultados.append(await self.avaliar_item(implantacao, item))
        implantacao.bloqueio_critico_aberto = await (
            self.implantacao_service.pendencia_service.has_open_critical_blockers(
                implantacao_id
            )
        )
        self.session.add(implantacao)
        await self.session.flush()
        await self.implantacao_service.recalcular_progresso_basico(implantacao_id)
        return resultados

    async def avaliar_todos(
        self,
        tenant_id: uuid.UUID,
    ) -> list[ChecklistEvaluation]:
        implantacao = await self.implantacao_service.get_active_implantacao(tenant_id)
        if implantacao is None:
            raise EntityNotFoundError("Implantação ativa não encontrada para o tenant.")
        return await self.avaliar_implantacao(implantacao)

    async def avaliar_item(
        self,
        implantacao: ImplantacaoOperacional,
        item: ImplantacaoChecklistItem,
    ) -> ChecklistEvaluation:
        verifier = self._verifiers.get(item.codigo_item)
        if verifier is None:
            return ChecklistEvaluation(
                codigo_item=item.codigo_item,
                status=ChecklistItemStatus.PENDENTE.value,
                descricao="Checklist sem verificador automatico configurado.",
                evidencia=None,
            )
        resultado = await verifier(implantacao)
        await self._sincronizar_item(implantacao, item, resultado)
        return resultado

    async def _sincronizar_item(
        self,
        implantacao: ImplantacaoOperacional,
        item: ImplantacaoChecklistItem,
        resultado: ChecklistEvaluation,
    ) -> None:
        implantacao_id = implantacao.id
        owner_usuario_id = implantacao.owner_usuario_id
        status_atual = implantacao.status
        etapa_atual = implantacao.etapa_atual
        agora = resultado.evidencia.timestamp if resultado.evidencia else datetime.now(UTC)
        pendencia_titulo = self._pendencia_titulo(item.codigo_item)
        pendencia_aberta = await (
            self.implantacao_service.pendencia_service.buscar_pendencia_aberta_por_titulo(
                implantacao_id,
                pendencia_titulo,
            )
        )

        changed = (
            item.status != resultado.status
            or item.evidencia_tipo != (
                resultado.evidencia.evidencia_tipo
                if resultado.evidencia
                else ChecklistEvidenceType.AUTOMATICA.value
            )
            or item.evidencia_ref_id != (
                resultado.evidencia.entidade_id if resultado.evidencia else None
            )
        )

        item.status = resultado.status
        item.descricao = resultado.descricao
        item.evidencia_tipo = (
            resultado.evidencia.evidencia_tipo
            if resultado.evidencia
            else ChecklistEvidenceType.AUTOMATICA.value
        )
        item.evidencia_ref_id = (
            resultado.evidencia.entidade_id if resultado.evidencia else None
        )
        item.updated_at = agora

        if resultado.status == ChecklistItemStatus.ATENDIDO.value:
            item.checked_by_usuario_id = owner_usuario_id
            item.checked_at = agora
        elif resultado.status == ChecklistItemStatus.DISPENSADO.value:
            item.checked_by_usuario_id = owner_usuario_id
            item.checked_at = agora
        else:
            item.checked_by_usuario_id = None
            item.checked_at = None

        self.session.add(item)
        await self.session.flush()

        if resultado.status in {
            ChecklistItemStatus.ATENDIDO.value,
            ChecklistItemStatus.DISPENSADO.value,
        }:
            resolved = await (
                self.implantacao_service.pendencia_service.resolver_pendencia_por_titulo(
                    implantacao_id,
                    pendencia_titulo,
                )
            )
            if pendencia_aberta is not None and resolved is not None:
                await self.implantacao_service.historico_service.registrar(
                    implantacao_id,
                    evento="CHECKLIST_ITEM_RESOLVED",
                    status_anterior=status_atual,
                    status_novo=status_atual,
                    etapa_anterior=etapa_atual,
                    etapa_nova=etapa_atual,
                    ator_usuario_id=owner_usuario_id,
                    payload_snapshot=self._history_payload(item, resultado),
                )
                return
            if changed:
                await self.implantacao_service.historico_service.registrar(
                    implantacao_id,
                    evento="CHECKLIST_ITEM_VALIDATED",
                    status_anterior=status_atual,
                    status_novo=status_atual,
                    etapa_anterior=etapa_atual,
                    etapa_nova=etapa_atual,
                    ator_usuario_id=owner_usuario_id,
                    payload_snapshot=self._history_payload(item, resultado),
                )
            return

        created_pendencia = None
        if item.obrigatorio:
            created_pendencia = await (
                self.implantacao_service.pendencia_service.criar_ou_manter_pendencia(
                    implantacao_id,
                    titulo=pendencia_titulo,
                    descricao=resultado.descricao,
                    tipo=resultado.pendencia_tipo,
                    severidade=(
                        resultado.pendencia_severidade
                        or PendenciaSeverity.MEDIA.value
                    ),
                    etapa_id=item.etapa_id,
                )
            )
        if changed or (created_pendencia and created_pendencia[1]):
            await self.implantacao_service.historico_service.registrar(
                implantacao_id,
                evento="CHECKLIST_ITEM_FAILED",
                status_anterior=status_atual,
                status_novo=status_atual,
                etapa_anterior=etapa_atual,
                etapa_nova=etapa_atual,
                ator_usuario_id=owner_usuario_id,
                payload_snapshot=self._history_payload(item, resultado),
            )

    def _history_payload(
        self,
        item: ImplantacaoChecklistItem,
        resultado: ChecklistEvaluation,
    ) -> dict[str, Any]:
        payload = {
            "codigo_item": item.codigo_item,
            "status": resultado.status,
            "descricao": resultado.descricao,
            "automatico": True,
        }
        if resultado.evidencia is not None:
            payload["evidencia"] = {
                "entidade": resultado.evidencia.entidade,
                "entidade_id": resultado.evidencia.entidade_id,
                "timestamp": resultado.evidencia.timestamp.isoformat(),
                "descricao": resultado.evidencia.descricao,
                "evidencia_tipo": resultado.evidencia.evidencia_tipo,
            }
        return payload

    def _pendencia_titulo(self, codigo_item: str) -> str:
        return f"WIZARD::{codigo_item}"

    def _module_enabled(
        self,
        implantacao: ImplantacaoOperacional,
        *aliases: str,
    ) -> bool:
        scope = implantacao.escopo_modulos or {}
        for alias in aliases:
            value = scope.get(alias)
            if isinstance(value, dict) and value.get("enabled") is True:
                return True
            if isinstance(value, bool) and value:
                return True
            if isinstance(value, str) and value.lower() in {"true", "1", "enabled", "ativo"}:
                return True
        return False

    def _dispensed(
        self,
        codigo_item: str,
        descricao: str,
    ) -> ChecklistEvaluation:
        return ChecklistEvaluation(
            codigo_item=codigo_item,
            status=ChecklistItemStatus.DISPENSADO.value,
            descricao=descricao,
            evidencia=ChecklistEvidence(
                entidade="MODULO",
                entidade_id=None,
                timestamp=datetime.now(UTC),
                descricao=descricao,
                evidencia_tipo=ChecklistEvidenceType.AUTOMATICA.value,
            ),
        )

    def _validated(
        self,
        codigo_item: str,
        descricao: str,
        *,
        entidade: str,
        entidade_id: str | uuid.UUID | None,
    ) -> ChecklistEvaluation:
        return ChecklistEvaluation(
            codigo_item=codigo_item,
            status=ChecklistItemStatus.ATENDIDO.value,
            descricao=descricao,
            evidencia=ChecklistEvidence(
                entidade=entidade,
                entidade_id=str(entidade_id) if entidade_id is not None else None,
                timestamp=datetime.now(UTC),
                descricao=descricao,
                evidencia_tipo=ChecklistEvidenceType.AUTOMATICA.value,
            ),
        )

    def _missing(
        self,
        codigo_item: str,
        descricao: str,
        *,
        status: str = ChecklistItemStatus.PENDENTE.value,
        severidade: str | None = None,
    ) -> ChecklistEvaluation:
        return ChecklistEvaluation(
            codigo_item=codigo_item,
            status=status,
            descricao=descricao,
            evidencia=None,
            pendencia_severidade=severidade,
        )

    async def _check_unidade_produtiva(
        self,
        implantacao: ImplantacaoOperacional,
    ) -> ChecklistEvaluation:
        unidade_id = await self._find_unidade_produtiva(implantacao)
        if unidade_id is None:
            return self._missing(
                "CHECK_UNIDADE_PRODUTIVA",
                "Nenhuma Unidade Produtiva ativa encontrada para a implantação.",
                severidade=PendenciaSeverity.CRITICA.value,
            )
        return self._validated(
            "CHECK_UNIDADE_PRODUTIVA",
            "Pelo menos uma Unidade Produtiva ativa foi encontrada para a implantação.",
            entidade="Unidade Produtiva",
            entidade_id=unidade_id,
        )

    async def _check_estrutura_territorial(
        self,
        implantacao: ImplantacaoOperacional,
    ) -> ChecklistEvaluation:
        area_id = await self._find_area_rural(implantacao)
        if area_id is None:
            return self._missing(
                "CHECK_ESTRUTURA_TERRITORIAL",
                "Nenhuma Área Rural ativa encontrada.",
            )
        return self._validated(
            "CHECK_ESTRUTURA_TERRITORIAL",
            "Área Rural ativa encontrada.",
            entidade="Área Rural",
            entidade_id=area_id,
        )

    async def _check_talhao_agricultura(
        self,
        implantacao: ImplantacaoOperacional,
    ) -> ChecklistEvaluation:
        if not self._module_enabled(implantacao, "agricultura"):
            return self._dispensed(
                "CHECK_AGRICULTURA_TALHAO",
                "Agricultura não está habilitada nesta implantação.",
            )
        talhao_id = await self._find_area_by_tipo(implantacao, TipoArea.TALHAO.value)
        if talhao_id is None:
            return self._missing(
                "CHECK_AGRICULTURA_TALHAO",
                "Agricultura habilitada sem talhão cadastrado.",
                status=ChecklistItemStatus.FALHOU.value,
                severidade=PendenciaSeverity.CRITICA.value,
            )
        return self._validated(
            "CHECK_AGRICULTURA_TALHAO",
            "Talhão encontrado para o módulo Agricultura.",
            entidade="Área Rural",
            entidade_id=talhao_id,
        )

    async def _check_piquete_pecuaria(
        self,
        implantacao: ImplantacaoOperacional,
    ) -> ChecklistEvaluation:
        if not self._module_enabled(implantacao, "pecuaria"):
            return self._dispensed(
                "CHECK_PECUARIA_PIQUETE",
                "Pecuária não está habilitada nesta implantação.",
            )
        piquete_id = await self._find_area_by_tipo(implantacao, TipoArea.PIQUETE.value)
        if piquete_id is None:
            return self._missing(
                "CHECK_PECUARIA_PIQUETE",
                "Pecuária habilitada sem piquete cadastrado.",
                status=ChecklistItemStatus.FALHOU.value,
                severidade=PendenciaSeverity.CRITICA.value,
            )
        return self._validated(
            "CHECK_PECUARIA_PIQUETE",
            "Piquete encontrado para o módulo Pecuária.",
            entidade="Área Rural",
            entidade_id=piquete_id,
        )

    async def _check_deposito_estoque(
        self,
        implantacao: ImplantacaoOperacional,
    ) -> ChecklistEvaluation:
        if not self._module_enabled(implantacao, "estoque"):
            return self._dispensed(
                "CHECK_ESTOQUE_DEPOSITO",
                "Estoque não está habilitado nesta implantação.",
            )
        deposito_id = await self._find_deposito(implantacao)
        if deposito_id is None:
            return self._missing(
                "CHECK_ESTOQUE_DEPOSITO",
                "Estoque habilitado sem depósito ativo cadastrado.",
            )
        return self._validated(
            "CHECK_ESTOQUE_DEPOSITO",
            "Depósito ativo encontrado para o módulo Estoque.",
            entidade="Depósito",
            entidade_id=deposito_id,
        )

    async def _check_plano_conta(
        self,
        implantacao: ImplantacaoOperacional,
    ) -> ChecklistEvaluation:
        if not self._module_enabled(implantacao, "financeiro"):
            return self._dispensed(
                "CHECK_FINANCEIRO_PLANO_CONTA",
                "Financeiro não está habilitado nesta implantação.",
            )
        plano_conta_id = await self._find_plano_conta(implantacao)
        if plano_conta_id is None:
            return self._missing(
                "CHECK_FINANCEIRO_PLANO_CONTA",
                "Financeiro habilitado sem plano de contas ativo.",
            )
        return self._validated(
            "CHECK_FINANCEIRO_PLANO_CONTA",
            "Plano de contas ativo encontrado.",
            entidade="Plano de Contas",
            entidade_id=plano_conta_id,
        )

    async def _check_catalogo_produto(
        self,
        implantacao: ImplantacaoOperacional,
    ) -> ChecklistEvaluation:
        if not (
            self._module_enabled(implantacao, "agricultura")
            or self._module_enabled(implantacao, "estoque")
        ):
            return self._dispensed(
                "CHECK_PRODUTO_CATALOGO",
                "Catálogo de produtos não exigido para esta implantação.",
            )
        produto_id = await self._find_produto(implantacao)
        if produto_id is None:
            return self._missing(
                "CHECK_PRODUTO_CATALOGO",
                "Nenhum produto ativo encontrado no catálogo mínimo.",
            )
        return self._validated(
            "CHECK_PRODUTO_CATALOGO",
            "Produto ativo encontrado no catálogo mínimo.",
            entidade="Produto",
            entidade_id=produto_id,
        )

    async def _check_equipamento(
        self,
        implantacao: ImplantacaoOperacional,
    ) -> ChecklistEvaluation:
        if not self._module_enabled(implantacao, "frota", "maquinas"):
            return self._dispensed(
                "CHECK_EQUIPAMENTO_CADASTRO",
                "Frota/Máquinas não está habilitada nesta implantação.",
            )
        equipamento_id = await self._find_equipamento(implantacao)
        if equipamento_id is None:
            return self._missing(
                "CHECK_EQUIPAMENTO_CADASTRO",
                "Nenhum equipamento ativo encontrado.",
            )
        return self._validated(
            "CHECK_EQUIPAMENTO_CADASTRO",
            "Pelo menos um equipamento ou máquina foi cadastrado.",
            entidade="Equipamento",
            entidade_id=equipamento_id,
        )

    async def _check_cultura(
        self,
        implantacao: ImplantacaoOperacional,
    ) -> ChecklistEvaluation:
        if not self._module_enabled(implantacao, "agricultura"):
            return self._dispensed(
                "CHECK_CULTURA",
                "Agricultura não está habilitada nesta implantação.",
            )
        # Verify if there is a Cultura for the tenant (simplified check)
        stmt = select(Produto).where(
            Produto.tenant_id == implantacao.tenant_id,
            Produto.ativo.is_(True),
            Produto.categoria.ilike("%cultura%"), # Simple fallback for check
        ).limit(1)
        cultura_id = (await self.session.execute(stmt)).scalars().first()

        if cultura_id is None:
            return self._missing(
                "CHECK_CULTURA",
                "Agricultura habilitada sem culturas produtivas cadastradas.",
                status=ChecklistItemStatus.FALHOU.value,
                severidade=PendenciaSeverity.CRITICA.value,
            )
        return self._validated(
            "CHECK_CULTURA",
            "Cultura produtiva encontrada.",
            entidade="ProdutoCultura",
            entidade_id=cultura_id.id,
        )

    async def _check_integracao_erp(
        self,
        implantacao: ImplantacaoOperacional,
    ) -> ChecklistEvaluation:
        runtime = await self._load_erp_runtime(implantacao)
        readiness = self.erp_readiness_service.avaliar_runtime(implantacao, runtime)
        return self._readiness_to_checklist_evaluation(readiness, runtime)

    async def _load_erp_runtime(
        self,
        implantacao: ImplantacaoOperacional,
    ) -> ErpChecklistRuntime:
        return await self.erp_readiness_service.carregar_runtime(implantacao)

    def _readiness_to_checklist_evaluation(
        self,
        readiness: ErpReadinessResult,
        runtime: ErpChecklistRuntime,
    ) -> ChecklistEvaluation:
        if readiness.status == "DISPENSADO":
            return self._dispensed("CHECK_INTEGRACAO_ERP", readiness.description)
        if readiness.status == "ATENDIDO":
            return self._validated(
                "CHECK_INTEGRACAO_ERP",
                readiness.description,
                entidade="Integração ERP",
                entidade_id=runtime.config.id if runtime.config else None,
            )
        return self._missing(
            "CHECK_INTEGRACAO_ERP",
            readiness.description,
            status=readiness.status,
            severidade=(
                PendenciaSeverity.CRITICA.value if readiness.status == "FALHOU" else None
            ),
        )

    async def _find_unidade_produtiva(
        self,
        implantacao: ImplantacaoOperacional,
    ) -> uuid.UUID | None:
        stmt = select(UnidadeProdutiva.id).where(
            UnidadeProdutiva.tenant_id == implantacao.tenant_id,
            UnidadeProdutiva.ativo.is_(True),
        )
        if implantacao.unidade_produtiva_id is not None:
            stmt = stmt.where(UnidadeProdutiva.id == implantacao.unidade_produtiva_id)
        stmt = stmt.limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _find_area_rural(
        self,
        implantacao: ImplantacaoOperacional,
    ) -> uuid.UUID | None:
        stmt = select(AreaRural.id).where(
            AreaRural.tenant_id == implantacao.tenant_id,
            AreaRural.ativo.is_(True),
        )
        if implantacao.unidade_produtiva_id is not None:
            stmt = stmt.where(
                AreaRural.unidade_produtiva_id == implantacao.unidade_produtiva_id
            )
        stmt = stmt.limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _find_area_by_tipo(
        self,
        implantacao: ImplantacaoOperacional,
        tipo: str,
    ) -> uuid.UUID | None:
        stmt = select(AreaRural.id).where(
            AreaRural.tenant_id == implantacao.tenant_id,
            AreaRural.ativo.is_(True),
            AreaRural.tipo == tipo,
        )
        if implantacao.unidade_produtiva_id is not None:
            stmt = stmt.where(
                AreaRural.unidade_produtiva_id == implantacao.unidade_produtiva_id
            )
        stmt = stmt.limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _find_deposito(
        self,
        implantacao: ImplantacaoOperacional,
    ) -> uuid.UUID | None:
        stmt = select(Deposito.id).where(
            Deposito.tenant_id == implantacao.tenant_id,
            Deposito.ativo.is_(True),
        )
        if implantacao.unidade_produtiva_id is not None:
            stmt = stmt.where(
                Deposito.unidade_produtiva_id == implantacao.unidade_produtiva_id
            )
        stmt = stmt.limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _find_plano_conta(
        self,
        implantacao: ImplantacaoOperacional,
    ) -> uuid.UUID | None:
        stmt = (
            select(PlanoConta.id)
            .where(
                PlanoConta.tenant_id == implantacao.tenant_id,
                PlanoConta.ativo.is_(True),
            )
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _find_produto(
        self,
        implantacao: ImplantacaoOperacional,
    ) -> uuid.UUID | None:
        stmt = (
            select(Produto.id)
            .where(
                Produto.ativo.is_(True),
                or_(
                    Produto.tenant_id == implantacao.tenant_id,
                    Produto.tenant_id.is_(None),
                ),
            )
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _find_equipamento(
        self,
        implantacao: ImplantacaoOperacional,
    ) -> uuid.UUID | None:
        stmt = select(Equipamento.id).where(
            Equipamento.tenant_id == implantacao.tenant_id,
            Equipamento.ativo.is_(True),
        )
        if implantacao.unidade_produtiva_id is not None:
            stmt = stmt.where(
                or_(
                    Equipamento.unidade_produtiva_id == implantacao.unidade_produtiva_id,
                    Equipamento.unidade_produtiva_id.is_(None),
                )
            )
        stmt = stmt.limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()


__all__ = [
    "ChecklistEngine",
    "ChecklistEvaluation",
    "ChecklistEvidence",
]
