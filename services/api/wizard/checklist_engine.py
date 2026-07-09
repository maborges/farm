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

_ERP_REQUIRED_FEATURE_CODES = ("pessoas", "produtos", "financeiro", "nfe")
_ERP_CRITICAL_HEALTH = {
    IntegrationHealthStatus.AUTH_ERROR.value,
    IntegrationHealthStatus.CONFIG_ERROR.value,
    IntegrationHealthStatus.DISCONNECTED.value,
}
_ERP_ALLOWED_HEALTH_WARNING = {
    IntegrationHealthStatus.DEGRADED.value,
    IntegrationHealthStatus.PARTIAL_FAILURE.value,
    IntegrationHealthStatus.RATE_LIMITED.value,
}
_ERP_REQUIRED_DIAGNOSTICS = ("connection_test", "timeline", "manual_reconciliation")
_ERP_REQUIRED_OBSERVABILITY = ("health", "jobs", "logs", "reconciliation")


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


@dataclass(frozen=True)
class ErpChecklistRuntime:
    declared: bool
    provider: MarketplaceIntegracao | None
    config: TenantIntegracao | None
    health: IntegrationHealth | None
    features: dict[str, IntegrationFeature]
    policies: dict[str, IntegrationSyncPolicy]
    pending_links: int = 0
    conflict_links: int = 0


class ChecklistEngine:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.implantacao_service = ImplantacaoService(session)
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
        if not runtime.declared and runtime.config is None:
            return self._dispensed(
                "CHECK_INTEGRACAO_ERP",
                "Operação sem ERP declarada para este tenant; o piloto restrito segue sem bloqueio.",
            )
        if runtime.config is None or runtime.provider is None:
            return self._missing(
                "CHECK_INTEGRACAO_ERP",
                "ERP declarado no wizard, mas o provider ERP ainda não foi configurado no console ERP.",
            )
        if runtime.health is None:
            return self._missing(
                "CHECK_INTEGRACAO_ERP",
                "Provider ERP configurado, mas health pendente. Execute o teste de conexão no console ERP.",
            )
        if runtime.health.status in _ERP_CRITICAL_HEALTH:
            return self._missing(
                "CHECK_INTEGRACAO_ERP",
                f"Provider ERP configurado, mas health crítico ({runtime.health.status}).",
                status=ChecklistItemStatus.FALHOU.value,
                severidade=PendenciaSeverity.CRITICA.value,
            )
        missing_capabilities = self._missing_erp_capabilities(runtime)
        if missing_capabilities:
            return self._missing(
                "CHECK_INTEGRACAO_ERP",
                "Capabilities P0 incompletas para o piloto restrito: "
                + ", ".join(missing_capabilities)
                + ".",
                status=ChecklistItemStatus.FALHOU.value,
                severidade=PendenciaSeverity.CRITICA.value,
            )
        missing_policies = self._missing_erp_policies(runtime)
        if missing_policies:
            return self._missing(
                "CHECK_INTEGRACAO_ERP",
                "Policies de sincronização mínimas pendentes para: "
                + ", ".join(missing_policies)
                + ".",
            )
        if runtime.conflict_links > 0:
            return self._missing(
                "CHECK_INTEGRACAO_ERP",
                f"Conflitos críticos de reconciliação ERP pendentes: {runtime.conflict_links}.",
                status=ChecklistItemStatus.FALHOU.value,
                severidade=PendenciaSeverity.CRITICA.value,
            )
        if runtime.pending_links > 0:
            return self._missing(
                "CHECK_INTEGRACAO_ERP",
                f"Reconciliação manual pendente para {runtime.pending_links} associação(ões) ERP.",
            )
        return self._validated(
            "CHECK_INTEGRACAO_ERP",
            self._erp_ready_message(runtime),
            entidade="Integração ERP",
            entidade_id=runtime.config.id,
        )

    def _erp_declared_for_implantacao(
        self,
        implantacao: ImplantacaoOperacional,
    ) -> bool:
        for payload in (
            implantacao.escopo_modulos or {},
            implantacao.diagnostico_inicial_snapshot or {},
        ):
            if not isinstance(payload, dict):
                continue
            if payload.get("integracao_erp") is True:
                return True
            if payload.get("estrategia_carga") == "ERP":
                return True
            if isinstance(payload.get("erp_nome"), str) and payload["erp_nome"].strip():
                return True
            if payload.get("carga_erp") or payload.get("escopo_carga_erp"):
                return True
        return False

    async def _load_erp_runtime(
        self,
        implantacao: ImplantacaoOperacional,
    ) -> ErpChecklistRuntime:
        declared = self._erp_declared_for_implantacao(implantacao)
        tenant_id = str(implantacao.tenant_id)
        config_stmt = (
            select(TenantIntegracao, MarketplaceIntegracao)
            .join(MarketplaceIntegracao, TenantIntegracao.provider_id == MarketplaceIntegracao.id)
            .where(
                TenantIntegracao.tenant_id == tenant_id,
                TenantIntegracao.deleted_at.is_(None),
                TenantIntegracao.scope_type.in_(
                    [IntegrationScope.TENANT.value, IntegrationScope.ESTABELECIMENTO.value]
                ),
                TenantIntegracao.lifecycle_state.notin_(
                    [IntegrationStatus.REMOVED.value, IntegrationStatus.REVOKED.value]
                ),
                MarketplaceIntegracao.provider_type == "ERP",
                MarketplaceIntegracao.ativa.is_(True),
            )
            .order_by(TenantIntegracao.installed_at.desc())
            .limit(1)
        )
        runtime_row = (await self.session.execute(config_stmt)).first()
        if runtime_row is None:
            return ErpChecklistRuntime(
                declared=declared,
                provider=None,
                config=None,
                health=None,
                features={},
                policies={},
            )
        config, provider = runtime_row
        return ErpChecklistRuntime(
            declared=declared,
            provider=provider,
            config=config,
            health=await self._load_erp_health(config.id),
            features=await self._load_erp_features(config.id),
            policies=await self._load_erp_policies(config.id),
            pending_links=await self._count_erp_links(
                tenant_id,
                config.id,
                provider.id,
                ExternalRecordAssociationStatus.PENDING.value,
            ),
            conflict_links=await self._count_erp_links(
                tenant_id,
                config.id,
                provider.id,
                ExternalRecordAssociationStatus.CONFLICT.value,
            ),
        )

    async def _load_erp_health(self, config_id: int) -> IntegrationHealth | None:
        stmt = select(IntegrationHealth).where(IntegrationHealth.config_id == config_id).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _load_erp_features(self, config_id: int) -> dict[str, IntegrationFeature]:
        stmt = select(IntegrationFeature).where(IntegrationFeature.config_id == config_id)
        features = (await self.session.execute(stmt)).scalars().all()
        return {feature.codigo: feature for feature in features}

    async def _load_erp_policies(self, config_id: int) -> dict[str, IntegrationSyncPolicy]:
        stmt = select(IntegrationSyncPolicy, IntegrationFeature).join(
            IntegrationFeature,
            IntegrationSyncPolicy.feature_id == IntegrationFeature.id,
        ).where(IntegrationSyncPolicy.config_id == config_id)
        rows = (await self.session.execute(stmt)).all()
        return {feature.codigo: policy for policy, feature in rows}

    async def _count_erp_links(
        self,
        tenant_id: str,
        config_id: int,
        provider_id: int,
        status: str,
    ) -> int:
        stmt = select(ExternalRecordAssociation.id).where(
            ExternalRecordAssociation.tenant_id == tenant_id,
            ExternalRecordAssociation.config_id == config_id,
            ExternalRecordAssociation.provider_id == provider_id,
            ExternalRecordAssociation.status == status,
        )
        return len((await self.session.execute(stmt)).scalars().all())

    def _missing_erp_capabilities(
        self,
        runtime: ErpChecklistRuntime,
    ) -> list[str]:
        if runtime.provider is None:
            return list(_ERP_REQUIRED_FEATURE_CODES)
        capability_matrix = self._provider_capability_matrix(runtime.provider)
        missing = self._missing_erp_diagnostics(runtime.provider)
        for feature_code in _ERP_REQUIRED_FEATURE_CODES:
            feature = runtime.features.get(feature_code)
            capability = capability_matrix.get(feature_code) or getattr(feature, "settings_payload", {}) or {}
            missing.extend(self._missing_erp_feature_capability(feature_code, feature, capability))
        return sorted(set(missing))

    def _missing_erp_diagnostics(
        self,
        provider: MarketplaceIntegracao,
    ) -> list[str]:
        health_schema = provider.health_schema or {}
        diagnostics = health_schema.get("diagnostics") if isinstance(health_schema, dict) else {}
        return [
            f"diagnostico:{key}"
            for key in _ERP_REQUIRED_DIAGNOSTICS
            if not isinstance(diagnostics, dict) or diagnostics.get(key) is not True
        ]

    def _provider_capability_matrix(
        self,
        provider: MarketplaceIntegracao,
    ) -> dict[str, dict[str, Any]]:
        schema = provider.feature_schema or {}
        matrix = schema.get("capability_matrix") if isinstance(schema, dict) else []
        if not isinstance(matrix, list):
            return {}
        return {
            item["feature_code"]: item
            for item in matrix
            if isinstance(item, dict) and isinstance(item.get("feature_code"), str)
        }

    def _missing_erp_feature_capability(
        self,
        feature_code: str,
        feature: IntegrationFeature | None,
        capability: dict[str, Any],
    ) -> list[str]:
        if feature is None or feature.habilitada is not True:
            return [feature_code]
        if capability.get("status") not in {"SUPPORTED", "PARTIAL"}:
            return [feature_code]
        if capability.get("maturity") not in {"TESTED", "PILOT_READY", "PRODUCTION_READY"}:
            return [feature_code]
        observability = capability.get("observability_requirements")
        if not isinstance(observability, list):
            return [feature_code]
        return [
            f"{feature_code}:{requirement}"
            for requirement in _ERP_REQUIRED_OBSERVABILITY
            if requirement not in observability
        ]

    def _missing_erp_policies(
        self,
        runtime: ErpChecklistRuntime,
    ) -> list[str]:
        missing: list[str] = []
        for feature_code in _ERP_REQUIRED_FEATURE_CODES:
            policy = runtime.policies.get(feature_code)
            feature = runtime.features.get(feature_code)
            supported = ((feature.settings_payload or {}) if feature else {}).get("supported_modes", [])
            if policy is None or policy.ativa is not True:
                missing.append(feature_code)
                continue
            if supported and policy.mode not in supported:
                missing.append(feature_code)
        return sorted(set(missing))

    def _erp_ready_message(
        self,
        runtime: ErpChecklistRuntime,
    ) -> str:
        provider_name = runtime.provider.nome if runtime.provider is not None else "ERP"
        if runtime.health is not None and runtime.health.status in _ERP_ALLOWED_HEALTH_WARNING:
            return (
                f"Integração ERP apta para piloto restrito com o provider {provider_name}, "
                f"com health em {runtime.health.status} e monitoramento recomendado."
            )
        return f"Integração ERP apta para piloto restrito com o provider {provider_name}."

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
