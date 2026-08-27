from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from certificacoes_esg.models import (
    AvaliacaoCertificacao,
    ChecklistCertificacao,
    CriterioCertificacao,
    EvidenciaCertificacao,
    PassaporteRastreabilidade,
    PassaporteRastreabilidadeEvidencia,
    PassaporteRastreabilidadeEvento,
    NaoConformidadeCertificacao,
    RelatorioESG,
    RelatorioESGEvidencia,
    RelatorioESGIndicador,
    StatusNaoConformidade,
    StatusPassaporte,
    StatusRelatorioESG,
    PlanoAcaoCertificacao,
    ProgramaCertificacao,
    StatusPlanoAcao,
    StatusProgramaCertificacao,
)
from certificacoes_esg.integrity import calculate_snapshot_hash, verify_snapshot_hash
from certificacoes_esg.schemas import (
    EvidenciaCertificacaoCreate,
    NaoConformidadeCertificacaoCreate,
    NaoConformidadeStatusUpdate,
    PlanoAcaoCertificacaoCreate,
    PlanoAcaoStatusUpdate,
    PassaporteRastreabilidadeCreate,
    PassaporteRastreabilidadeEvidenciaCreate,
    PassaporteRastreabilidadeEventoCreate,
    PassaporteRastreabilidadeUpdateStatus,
    RelatorioESGCreate,
    RelatorioESGEvidenciaCreate,
    RelatorioESGIndicadorCreate,
    RelatorioESGUpdateStatus,
)
from agricola.rastreabilidade.models import CadernoLoteComercial, LoteRastreabilidade
from core.cadastros.propriedade_imovel.models import PropriedadeImovel
from core.cadastros.propriedades.propriedade_models import Propriedade
from core.exceptions import BusinessRuleError, EntityNotFoundError, TenantViolationError
from imoveis.models.imovel import ImovelRural

BLOCKED_ORIGINS = {
    "CAR",
    "MATRICULA",
    "CCIR",
    "ITR",
    "NIRF",
    "SIGEF",
    "AREA_OPERACIONAL",
}

logger = logging.getLogger(__name__)


class CertificacoesESGService:
    """Serviços internos do domínio consumidor Certificações/ESG."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        self.session = session
        self.tenant_id = tenant_id
        self.user_id = user_id

    def _agora(self) -> datetime:
        return datetime.now(timezone.utc)

    def _resolver_created_by(self, created_by: uuid.UUID | None) -> uuid.UUID:
        value = created_by or self.user_id
        if value is None:
            raise BusinessRuleError("created_by é obrigatório para a operação.")
        return value

    def _normalize_text(self, value: str, field_name: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise BusinessRuleError(f"{field_name} não pode ser vazio.")
        return cleaned

    async def _query_or_fail(self, model: type[Any], entity_id: uuid.UUID, message: str) -> Any:
        stmt = select(model).where(model.id == entity_id, model.tenant_id == self.tenant_id)
        obj = (await self.session.execute(stmt)).scalars().first()
        if obj is None:
            raise EntityNotFoundError(message)
        if hasattr(obj, "tenant_id") and obj.tenant_id != self.tenant_id:
            raise TenantViolationError(
                "Tentativa de acesso cross-tenant interceptada.",
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                resource=model.__tablename__,
            )
        return obj

    async def _validar_programa(self, programa_id: uuid.UUID) -> None:
        await self._query_or_fail(ProgramaCertificacao, programa_id, "Programa de certificação não encontrado.")

    async def _validar_checklist_programa(self, checklist_id: uuid.UUID, programa_id: uuid.UUID) -> None:
        checklist = await self._query_or_fail(
            ChecklistCertificacao,
            checklist_id,
            "Checklist de certificação não encontrado.",
        )
        if checklist.programa_certificacao_id != programa_id:
            raise BusinessRuleError("Checklist não pertence ao programa informado.")

    async def _validar_criterio_programa(self, criterio_id: uuid.UUID, programa_id: uuid.UUID) -> None:
        criterio = await self._query_or_fail(
            CriterioCertificacao,
            criterio_id,
            "Critério de certificação não encontrado.",
        )
        checklist = await self._query_or_fail(
            ChecklistCertificacao,
            criterio.checklist_certificacao_id,
            "Checklist do critério não encontrado.",
        )
        if checklist.programa_certificacao_id != programa_id:
            raise BusinessRuleError("Critério não pertence ao programa informado.")

    async def _validar_avaliacao_programa(self, avaliacao_id: uuid.UUID, programa_id: uuid.UUID) -> None:
        avaliacao = await self._query_or_fail(
            AvaliacaoCertificacao,
            avaliacao_id,
            "Avaliação de certificação não encontrada.",
        )
        checklist = await self._query_or_fail(
            ChecklistCertificacao,
            avaliacao.checklist_certificacao_id,
            "Checklist da avaliação não encontrado.",
        )
        if checklist.programa_certificacao_id != programa_id:
            raise BusinessRuleError("Avaliação não pertence ao programa informado.")

    async def _validar_propriedade_imovel(self, relacao_id: uuid.UUID, dados: dict[str, Any]) -> None:
        relacao = await self._query_or_fail(
            PropriedadeImovel,
            relacao_id,
            "Vínculo propriedade-imóvel não encontrado.",
        )
        if dados.get("propriedade_id") and relacao.propriedade_id != dados["propriedade_id"]:
            raise BusinessRuleError("Vínculo informado não corresponde à propriedade informada.")
        if dados.get("imovel_rural_id") and relacao.imovel_rural_id != dados["imovel_rural_id"]:
            raise BusinessRuleError("Vínculo informado não corresponde ao imóvel informado.")

    async def _validar_referencia_simples(self, model: type[Any], entity_id: uuid.UUID, message: str) -> None:
        await self._query_or_fail(model, entity_id, message)

    def _query_tenant(self, model: type[Any]):
        return select(model).where(model.tenant_id == self.tenant_id)

    async def listar_programas(self) -> list[ProgramaCertificacao]:
        """Lista programas do tenant em ordem de atividade e início."""
        stmt = self._query_tenant(ProgramaCertificacao).order_by(
            ProgramaCertificacao.status_programa.asc(),
            ProgramaCertificacao.data_inicio.desc(),
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar_programa(self, dados: Any) -> ProgramaCertificacao:
        """Cria um programa de certificação pertencente ao tenant atual."""
        nome = self._normalize_text(dados.nome, "nome")
        programa = ProgramaCertificacao(
            tenant_id=self.tenant_id,
            nome=nome,
            tipo_certificacao=dados.tipo_certificacao,
            status_programa=dados.status_programa,
            data_inicio=dados.data_inicio,
            data_fim=dados.data_fim,
            organismo_certificador=dados.organismo_certificador,
            escopo=dados.escopo,
            observacoes=dados.observacoes,
        )
        self.session.add(programa)
        await self.session.flush()
        await self.session.refresh(programa)
        return programa

    async def atualizar_programa(self, programa_id: uuid.UUID, dados: Any) -> ProgramaCertificacao:
        """Atualiza um programa do tenant e mantém o período consistente."""
        programa = await self._query_or_fail(ProgramaCertificacao, programa_id, "Programa não encontrado.")
        for field, value in dados.model_dump(exclude_none=True).items():
            setattr(programa, field, self._normalize_text(value, field) if field == "nome" else value)
        if programa.data_fim and programa.data_fim < programa.data_inicio:
            raise BusinessRuleError("data_fim não pode ser anterior à data_inicio.")
        await self.session.flush()
        await self.session.refresh(programa)
        return programa

    async def criar_evidencia(
        self,
        dados: EvidenciaCertificacaoCreate,
        *,
        created_by: uuid.UUID | None = None,
    ) -> EvidenciaCertificacao:
        """Cria uma evidência imutável vinculada ao domínio de certificação."""
        titulo = self._normalize_text(dados.titulo, "titulo")
        descricao = self._normalize_text(dados.descricao, "descricao")
        origem_tipo = self._normalize_text(dados.origem_tipo, "origem_tipo")
        if origem_tipo.upper() in BLOCKED_ORIGINS:
            raise BusinessRuleError("origem_tipo não pode representar fonte oficial territorial/fundiária.")
        await self._validar_programa(dados.programa_id)
        if dados.checklist_id:
            await self._validar_checklist_programa(dados.checklist_id, dados.programa_id)
        if dados.criterio_id:
            await self._validar_criterio_programa(dados.criterio_id, dados.programa_id)
        if dados.avaliacao_id:
            await self._validar_avaliacao_programa(dados.avaliacao_id, dados.programa_id)
        if dados.propriedade_id:
            await self._validar_referencia_simples(Propriedade, dados.propriedade_id, "Propriedade não encontrada.")
        if dados.imovel_rural_id:
            await self._validar_referencia_simples(ImovelRural, dados.imovel_rural_id, "Imóvel rural não encontrado.")
        if dados.propriedade_imovel_id:
            await self._validar_propriedade_imovel(
                dados.propriedade_imovel_id,
                dados.model_dump(exclude={"propriedade_imovel_id"}),
            )

        obj = EvidenciaCertificacao(
            tenant_id=self.tenant_id,
            created_by=self._resolver_created_by(created_by),
            titulo=titulo,
            descricao=descricao,
            origem_tipo=origem_tipo,
            **dados.model_dump(exclude={"titulo", "descricao", "origem_tipo"}),
        )
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def listar_evidencias(
        self,
        *,
        programa_id: uuid.UUID | None = None,
        checklist_id: uuid.UUID | None = None,
        criterio_id: uuid.UUID | None = None,
        avaliacao_id: uuid.UUID | None = None,
        propriedade_id: uuid.UUID | None = None,
        imovel_rural_id: uuid.UUID | None = None,
        propriedade_imovel_id: uuid.UUID | None = None,
        tipo_evidencia: Any | None = None,
        responsavel_pessoa_id: uuid.UUID | None = None,
        publico: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[EvidenciaCertificacao]:
        stmt = self._query_tenant(EvidenciaCertificacao)
        if programa_id is not None:
            stmt = stmt.where(EvidenciaCertificacao.programa_id == programa_id)
        if checklist_id is not None:
            stmt = stmt.where(EvidenciaCertificacao.checklist_id == checklist_id)
        if criterio_id is not None:
            stmt = stmt.where(EvidenciaCertificacao.criterio_id == criterio_id)
        if avaliacao_id is not None:
            stmt = stmt.where(EvidenciaCertificacao.avaliacao_id == avaliacao_id)
        if propriedade_id is not None:
            stmt = stmt.where(EvidenciaCertificacao.propriedade_id == propriedade_id)
        if imovel_rural_id is not None:
            stmt = stmt.where(EvidenciaCertificacao.imovel_rural_id == imovel_rural_id)
        if propriedade_imovel_id is not None:
            stmt = stmt.where(EvidenciaCertificacao.propriedade_imovel_id == propriedade_imovel_id)
        if tipo_evidencia is not None:
            stmt = stmt.where(EvidenciaCertificacao.tipo_evidencia == tipo_evidencia)
        if responsavel_pessoa_id is not None:
            stmt = stmt.where(EvidenciaCertificacao.responsavel_pessoa_id == responsavel_pessoa_id)
        if publico is not None:
            stmt = stmt.where(EvidenciaCertificacao.publico.is_(publico))
        stmt = stmt.order_by(EvidenciaCertificacao.created_at.desc()).offset(skip).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def listar_nao_conformidades(
        self,
        *,
        programa_id: uuid.UUID | None = None,
        checklist_id: uuid.UUID | None = None,
        criterio_id: uuid.UUID | None = None,
        avaliacao_id: uuid.UUID | None = None,
        evidencia_id: uuid.UUID | None = None,
        propriedade_id: uuid.UUID | None = None,
        imovel_rural_id: uuid.UUID | None = None,
        propriedade_imovel_id: uuid.UUID | None = None,
        severidade: Any | None = None,
        status: StatusNaoConformidade | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[NaoConformidadeCertificacao]:
        """Lista não conformidades respeitando tenant e filtros de domínio."""
        stmt = self._query_tenant(NaoConformidadeCertificacao)
        if programa_id is not None:
            stmt = stmt.where(NaoConformidadeCertificacao.programa_id == programa_id)
        if checklist_id is not None:
            stmt = stmt.where(NaoConformidadeCertificacao.checklist_id == checklist_id)
        if criterio_id is not None:
            stmt = stmt.where(NaoConformidadeCertificacao.criterio_id == criterio_id)
        if avaliacao_id is not None:
            stmt = stmt.where(NaoConformidadeCertificacao.avaliacao_id == avaliacao_id)
        if evidencia_id is not None:
            stmt = stmt.where(NaoConformidadeCertificacao.evidencia_id == evidencia_id)
        if propriedade_id is not None:
            stmt = stmt.where(NaoConformidadeCertificacao.propriedade_id == propriedade_id)
        if imovel_rural_id is not None:
            stmt = stmt.where(NaoConformidadeCertificacao.imovel_rural_id == imovel_rural_id)
        if propriedade_imovel_id is not None:
            stmt = stmt.where(NaoConformidadeCertificacao.propriedade_imovel_id == propriedade_imovel_id)
        if severidade is not None:
            stmt = stmt.where(NaoConformidadeCertificacao.severidade == severidade)
        if status is not None:
            stmt = stmt.where(NaoConformidadeCertificacao.status == status)
        stmt = stmt.order_by(
            NaoConformidadeCertificacao.detectada_em.desc(), NaoConformidadeCertificacao.created_at.desc()
        ).offset(skip).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar_nao_conformidade(
        self,
        dados: NaoConformidadeCertificacaoCreate,
        *,
        created_by: uuid.UUID | None = None,
    ) -> NaoConformidadeCertificacao:
        """Cria uma não conformidade do domínio de certificação."""
        await self._validar_programa(dados.programa_id)
        titulo = self._normalize_text(dados.titulo, "titulo")
        descricao = self._normalize_text(dados.descricao, "descricao")
        status = dados.status
        if dados.checklist_id:
            await self._validar_checklist_programa(dados.checklist_id, dados.programa_id)
        if dados.criterio_id:
            await self._validar_criterio_programa(dados.criterio_id, dados.programa_id)
        if dados.avaliacao_id:
            await self._validar_avaliacao_programa(dados.avaliacao_id, dados.programa_id)
        if dados.evidencia_id:
            await self._validar_referencia_simples(
                EvidenciaCertificacao,
                dados.evidencia_id,
                "Evidência de certificação não encontrada.",
            )
        if dados.propriedade_id:
            await self._validar_referencia_simples(Propriedade, dados.propriedade_id, "Propriedade não encontrada.")
        if dados.imovel_rural_id:
            await self._validar_referencia_simples(ImovelRural, dados.imovel_rural_id, "Imóvel rural não encontrado.")
        if dados.propriedade_imovel_id:
            await self._validar_propriedade_imovel(
                dados.propriedade_imovel_id,
                dados.model_dump(exclude={"propriedade_imovel_id"}),
            )

        detectada_em = dados.detectada_em or self._agora()
        if dados.prazo_correcao and dados.prazo_correcao < detectada_em:
            raise BusinessRuleError("prazo_correcao deve ser maior ou igual a detectada_em.")
        if dados.resolvida_em and dados.resolvida_em < detectada_em:
            raise BusinessRuleError("resolvida_em deve ser maior ou igual a detectada_em.")

        obj = NaoConformidadeCertificacao(
            tenant_id=self.tenant_id,
            created_by=self._resolver_created_by(created_by),
            detectada_em=detectada_em,
            titulo=titulo,
            descricao=descricao,
            status=status,
            **dados.model_dump(exclude={"detectada_em", "titulo", "descricao", "status"}),
        )
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def atualizar_status_nao_conformidade(
        self,
        nao_conformidade_id: uuid.UUID,
        dados: NaoConformidadeStatusUpdate,
    ) -> NaoConformidadeCertificacao:
        """Atualiza o status de uma não conformidade com validação de tenant."""
        obj = await self._query_or_fail(
            NaoConformidadeCertificacao,
            nao_conformidade_id,
            "Não conformidade não encontrada.",
        )
        obj.status = dados.status
        if dados.prazo_correcao is not None:
            if dados.prazo_correcao < obj.detectada_em:
                raise BusinessRuleError("prazo_correcao deve ser maior ou igual a detectada_em.")
            obj.prazo_correcao = dados.prazo_correcao
        if dados.resolvida_em is not None:
            if dados.resolvida_em < obj.detectada_em:
                raise BusinessRuleError("resolvida_em deve ser maior ou igual a detectada_em.")
            obj.resolvida_em = dados.resolvida_em
        current_status = obj.status
        if not isinstance(current_status, StatusNaoConformidade):
            current_status = StatusNaoConformidade(current_status)
        if current_status == StatusNaoConformidade.RESOLVIDA and obj.resolvida_em is None:
            obj.resolvida_em = self._agora()
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def criar_plano_acao(
        self,
        dados: PlanoAcaoCertificacaoCreate,
        *,
        created_by: uuid.UUID | None = None,
    ) -> PlanoAcaoCertificacao:
        """Cria um plano de ação do domínio de certificação."""
        await self._validar_programa(dados.programa_id)
        if dados.nao_conformidade_id:
            await self._validar_referencia_simples(
                NaoConformidadeCertificacao,
                dados.nao_conformidade_id,
                "Não conformidade de certificação não encontrada.",
            )
        if dados.evidencia_id:
            await self._validar_referencia_simples(
                EvidenciaCertificacao,
                dados.evidencia_id,
                "Evidência de certificação não encontrada.",
            )
        if dados.propriedade_id:
            await self._validar_referencia_simples(Propriedade, dados.propriedade_id, "Propriedade não encontrada.")
        if dados.imovel_rural_id:
            await self._validar_referencia_simples(ImovelRural, dados.imovel_rural_id, "Imóvel rural não encontrado.")
        if dados.propriedade_imovel_id:
            await self._validar_propriedade_imovel(
                dados.propriedade_imovel_id,
                dados.model_dump(exclude={"propriedade_imovel_id"}),
            )

        titulo = self._normalize_text(dados.titulo, "titulo")
        descricao = self._normalize_text(dados.descricao, "descricao")
        prazo = dados.prazo or (self._agora() + timedelta(days=30))

        obj = PlanoAcaoCertificacao(
            tenant_id=self.tenant_id,
            created_by=self._resolver_created_by(created_by),
            prazo=prazo,
            titulo=titulo,
            descricao=descricao,
            **dados.model_dump(exclude={"prazo", "titulo", "descricao"}),
        )
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        if obj.concluido_em is not None and obj.concluido_em < obj.created_at:
            raise BusinessRuleError("concluido_em deve ser maior ou igual a created_at.")
        return obj

    async def atualizar_status_plano_acao(
        self,
        plano_acao_id: uuid.UUID,
        dados: PlanoAcaoStatusUpdate,
    ) -> PlanoAcaoCertificacao:
        """Atualiza o status de um plano de ação com regras de tenant e datas."""
        obj = await self._query_or_fail(
            PlanoAcaoCertificacao,
            plano_acao_id,
            "Plano de ação não encontrado.",
        )
        obj.status = dados.status
        if dados.concluido_em is not None:
            if dados.concluido_em < obj.created_at:
                raise BusinessRuleError("concluido_em deve ser maior ou igual a created_at.")
            obj.concluido_em = dados.concluido_em
        elif dados.status == StatusPlanoAcao.CONCLUIDO:
            obj.concluido_em = self._agora()
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def listar_planos_acao(
        self,
        *,
        programa_id: uuid.UUID | None = None,
        nao_conformidade_id: uuid.UUID | None = None,
        evidencia_id: uuid.UUID | None = None,
        responsavel_pessoa_id: uuid.UUID | None = None,
        propriedade_id: uuid.UUID | None = None,
        imovel_rural_id: uuid.UUID | None = None,
        propriedade_imovel_id: uuid.UUID | None = None,
        prioridade: Any | None = None,
        status: StatusPlanoAcao | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[PlanoAcaoCertificacao]:
        """Lista planos de ação respeitando tenant e filtros de domínio."""
        stmt = self._query_tenant(PlanoAcaoCertificacao)
        if programa_id is not None:
            stmt = stmt.where(PlanoAcaoCertificacao.programa_id == programa_id)
        if nao_conformidade_id is not None:
            stmt = stmt.where(PlanoAcaoCertificacao.nao_conformidade_id == nao_conformidade_id)
        if evidencia_id is not None:
            stmt = stmt.where(PlanoAcaoCertificacao.evidencia_id == evidencia_id)
        if responsavel_pessoa_id is not None:
            stmt = stmt.where(PlanoAcaoCertificacao.responsavel_pessoa_id == responsavel_pessoa_id)
        if propriedade_id is not None:
            stmt = stmt.where(PlanoAcaoCertificacao.propriedade_id == propriedade_id)
        if imovel_rural_id is not None:
            stmt = stmt.where(PlanoAcaoCertificacao.imovel_rural_id == imovel_rural_id)
        if propriedade_imovel_id is not None:
            stmt = stmt.where(PlanoAcaoCertificacao.propriedade_imovel_id == propriedade_imovel_id)
        if prioridade is not None:
            stmt = stmt.where(PlanoAcaoCertificacao.prioridade == prioridade)
        if status is not None:
            stmt = stmt.where(PlanoAcaoCertificacao.status == status)
        stmt = stmt.order_by(
            PlanoAcaoCertificacao.prazo.asc(), PlanoAcaoCertificacao.created_at.desc()
        ).offset(skip).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def _validar_relatorio_base(self, programa_id: uuid.UUID | None) -> None:
        if programa_id is not None:
            await self._validar_programa(programa_id)

    async def criar_relatorio_esg(
        self,
        dados: RelatorioESGCreate,
        *,
        created_by: uuid.UUID | None = None,
    ) -> RelatorioESG:
        titulo = self._normalize_text(dados.titulo, "titulo")
        await self._validar_relatorio_base(dados.programa_id)
        if dados.publicado_em is None and dados.status == StatusRelatorioESG.PUBLICADO:
            raise BusinessRuleError("publicado_em é obrigatório quando status for PUBLICADO.")
        if dados.cancelado_em is None and dados.status == StatusRelatorioESG.CANCELADO:
            raise BusinessRuleError("cancelado_em é obrigatório quando status for CANCELADO.")
        obj = RelatorioESG(
            tenant_id=self.tenant_id,
            created_by=self._resolver_created_by(created_by),
            titulo=titulo,
            **dados.model_dump(exclude={"titulo"}),
        )
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def listar_relatorios_esg(
        self,
        *,
        programa_id: uuid.UUID | None = None,
        propriedade_id: uuid.UUID | None = None,
        imovel_rural_id: uuid.UUID | None = None,
        propriedade_imovel_id: uuid.UUID | None = None,
        status: StatusRelatorioESG | None = None,
        publico: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[RelatorioESG]:
        stmt = self._query_tenant(RelatorioESG)
        if programa_id is not None:
            stmt = stmt.where(RelatorioESG.programa_id == programa_id)
        if propriedade_id is not None:
            stmt = stmt.where(RelatorioESG.propriedade_id == propriedade_id)
        if imovel_rural_id is not None:
            stmt = stmt.where(RelatorioESG.imovel_rural_id == imovel_rural_id)
        if propriedade_imovel_id is not None:
            stmt = stmt.where(RelatorioESG.propriedade_imovel_id == propriedade_imovel_id)
        if status is not None:
            stmt = stmt.where(RelatorioESG.status == status)
        if publico is not None:
            stmt = stmt.where(RelatorioESG.publico.is_(publico))
        stmt = stmt.order_by(RelatorioESG.created_at.desc()).offset(skip).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    def _publicar_com_snapshot_hash(self, obj: Any, publicado_em: datetime | None) -> None:
        """Aplica publicado_em e recalcula snapshot_hash de forma determinística.

        Compartilhado entre RelatorioESG e PassaporteRastreabilidade: ambos exigem
        snapshot_json presente e travam o hash a partir dele ao publicar.
        """
        if publicado_em is not None:
            obj.publicado_em = publicado_em
        elif obj.publicado_em is None:
            obj.publicado_em = self._agora()

        if obj.snapshot_json is None:
            raise BusinessRuleError("snapshot_json é obrigatório quando status for PUBLICADO.")

        obj.snapshot_hash = calculate_snapshot_hash(obj.snapshot_json)
        logger.info(
            "Publicação com snapshot_hash: tenant_id=%s tipo=%s id=%s",
            self.tenant_id, type(obj).__name__, obj.id,
        )

    async def atualizar_status_relatorio_esg(
        self,
        relatorio_id: uuid.UUID,
        dados: RelatorioESGUpdateStatus,
    ) -> RelatorioESG:
        obj = await self._query_or_fail(RelatorioESG, relatorio_id, "Relatório ESG não encontrado.")
        
        # Regra de Imutabilidade
        if obj.status == StatusRelatorioESG.PUBLICADO:
            raise BusinessRuleError("Não é permitido alterar um Relatório ESG já publicado.")

        obj.status = dados.status
        if dados.snapshot_json is not None:
            obj.snapshot_json = dados.snapshot_json
            # Hash é ignorado no input se for PUBLICADO, pois será calculado de forma determinística
            if dados.status != StatusRelatorioESG.PUBLICADO:
                obj.snapshot_hash = dados.snapshot_hash or obj.snapshot_hash

        if dados.status == StatusRelatorioESG.PUBLICADO:
            self._publicar_com_snapshot_hash(obj, dados.publicado_em)
        elif dados.status == StatusRelatorioESG.CANCELADO:
            if dados.cancelado_em is not None:
                obj.cancelado_em = dados.cancelado_em
            elif obj.cancelado_em is None:
                obj.cancelado_em = self._agora()
            logger.info(
                "Relatório ESG cancelado: tenant_id=%s id=%s", self.tenant_id, obj.id,
            )
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def adicionar_indicador_relatorio_esg(
        self,
        dados: RelatorioESGIndicadorCreate,
    ) -> RelatorioESGIndicador:
        await self._query_or_fail(RelatorioESG, dados.relatorio_id, "Relatório ESG não encontrado.")
        nome = self._normalize_text(dados.nome, "nome")
        obj = RelatorioESGIndicador(
            tenant_id=self.tenant_id,
            nome=nome,
            **dados.model_dump(exclude={"nome"}),
        )
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def vincular_evidencia_relatorio_esg(
        self,
        dados: RelatorioESGEvidenciaCreate,
    ) -> RelatorioESGEvidencia:
        await self._query_or_fail(RelatorioESG, dados.relatorio_id, "Relatório ESG não encontrado.")
        await self._query_or_fail(EvidenciaCertificacao, dados.evidencia_id, "Evidência de certificação não encontrada.")
        obj = RelatorioESGEvidencia(tenant_id=self.tenant_id, **dados.model_dump())
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def listar_indicadores_relatorio_esg(self, relatorio_id: uuid.UUID) -> list[RelatorioESGIndicador]:
        await self._query_or_fail(RelatorioESG, relatorio_id, "Relatório ESG não encontrado.")
        stmt = self._query_tenant(RelatorioESGIndicador).where(RelatorioESGIndicador.relatorio_id == relatorio_id)
        stmt = stmt.order_by(RelatorioESGIndicador.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def listar_evidencias_relatorio_esg(self, relatorio_id: uuid.UUID) -> list[RelatorioESGEvidencia]:
        await self._query_or_fail(RelatorioESG, relatorio_id, "Relatório ESG não encontrado.")
        stmt = self._query_tenant(RelatorioESGEvidencia).where(RelatorioESGEvidencia.relatorio_id == relatorio_id)
        stmt = stmt.order_by(RelatorioESGEvidencia.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar_passaporte_rastreabilidade(
        self,
        dados: PassaporteRastreabilidadeCreate,
        *,
        created_by: uuid.UUID | None = None,
    ) -> PassaporteRastreabilidade:
        titulo = self._normalize_text(dados.titulo, "titulo")
        if dados.programa_id is not None:
            await self._validar_programa(dados.programa_id)
        if dados.propriedade_id is not None:
            await self._validar_referencia_simples(Propriedade, dados.propriedade_id, "Propriedade não encontrada.")
        if dados.imovel_rural_id is not None:
            await self._validar_referencia_simples(ImovelRural, dados.imovel_rural_id, "Imóvel rural não encontrado.")
        if dados.propriedade_imovel_id is not None:
            await self._validar_propriedade_imovel(
                dados.propriedade_imovel_id,
                dados.model_dump(exclude={"propriedade_imovel_id"}),
            )
        if dados.lote_rastreabilidade_id is not None:
            await self._validar_referencia_simples(
                LoteRastreabilidade,
                dados.lote_rastreabilidade_id,
                "Lote de rastreabilidade não encontrado.",
            )
        if dados.caderno_lote_comercial_id is not None:
            await self._validar_referencia_simples(
                CadernoLoteComercial,
                dados.caderno_lote_comercial_id,
                "Caderno de lote comercial não encontrado.",
            )
        # Se já nasce publicado e público, gera o token
        public_token = None
        publicado_publicamente_em = None
        if dados.status == StatusPassaporte.PUBLICADO and dados.publico:
            public_token = uuid.uuid4()
            publicado_publicamente_em = self._agora()

        obj = PassaporteRastreabilidade(
            tenant_id=self.tenant_id,
            created_by=self._resolver_created_by(created_by),
            titulo=titulo,
            public_token=public_token,
            publicado_publicamente_em=publicado_publicamente_em,
            created_at=self._agora(),
            updated_at=self._agora(),
            **dados.model_dump(exclude={"titulo"}),
        )
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def listar_passaportes_rastreabilidade(
        self,
        *,
        programa_id: uuid.UUID | None = None,
        propriedade_id: uuid.UUID | None = None,
        imovel_rural_id: uuid.UUID | None = None,
        propriedade_imovel_id: uuid.UUID | None = None,
        status: StatusPassaporte | None = None,
        publico: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[PassaporteRastreabilidade]:
        stmt = self._query_tenant(PassaporteRastreabilidade)
        if programa_id is not None:
            stmt = stmt.where(PassaporteRastreabilidade.programa_id == programa_id)
        if propriedade_id is not None:
            stmt = stmt.where(PassaporteRastreabilidade.propriedade_id == propriedade_id)
        if imovel_rural_id is not None:
            stmt = stmt.where(PassaporteRastreabilidade.imovel_rural_id == imovel_rural_id)
        if propriedade_imovel_id is not None:
            stmt = stmt.where(PassaporteRastreabilidade.propriedade_imovel_id == propriedade_imovel_id)
        if status is not None:
            stmt = stmt.where(PassaporteRastreabilidade.status == status)
        if publico is not None:
            stmt = stmt.where(PassaporteRastreabilidade.publico.is_(publico))
        stmt = stmt.order_by(PassaporteRastreabilidade.created_at.desc()).offset(skip).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def atualizar_status_passaporte_rastreabilidade(
        self,
        passaporte_id: uuid.UUID,
        dados: PassaporteRastreabilidadeUpdateStatus,
    ) -> PassaporteRastreabilidade:
        obj = await self._query_or_fail(
            PassaporteRastreabilidade,
            passaporte_id,
            "Passaporte de rastreabilidade não encontrado.",
        )
        
        # Regra de Imutabilidade
        if obj.status == StatusPassaporte.PUBLICADO and dados.status != StatusPassaporte.REVOGADO:
            raise BusinessRuleError("Não é permitido alterar um Passaporte de Rastreabilidade já publicado.")

        obj.status = dados.status
        if dados.snapshot_json is not None:
            obj.snapshot_json = dados.snapshot_json
            if dados.status != StatusPassaporte.PUBLICADO:
                obj.snapshot_hash = dados.snapshot_hash or obj.snapshot_hash
        
        if dados.publico is not None:
            obj.publico = dados.publico

        if dados.status == StatusPassaporte.PUBLICADO:
            self._publicar_com_snapshot_hash(obj, dados.publicado_em)

            # Se for publicado e público, gerar token se não existir
            if obj.publico:
                if not obj.public_token:
                    obj.public_token = uuid.uuid4()
                if not obj.publicado_publicamente_em:
                    obj.publicado_publicamente_em = self._agora()

        elif dados.status == StatusPassaporte.REVOGADO:
            if dados.revogado_em is not None:
                obj.revogado_em = dados.revogado_em
            elif obj.revogado_em is None:
                obj.revogado_em = self._agora()
            logger.info(
                "Passaporte de rastreabilidade revogado: tenant_id=%s id=%s", self.tenant_id, obj.id,
            )
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def adicionar_evento_passaporte(
        self,
        dados: PassaporteRastreabilidadeEventoCreate,
    ) -> PassaporteRastreabilidadeEvento:
        await self._query_or_fail(
            PassaporteRastreabilidade,
            dados.passaporte_id,
            "Passaporte de rastreabilidade não encontrado.",
        )
        titulo = self._normalize_text(dados.titulo, "titulo")
        descricao = self._normalize_text(dados.descricao, "descricao")
        origem_tipo = self._normalize_text(dados.origem_tipo, "origem_tipo")
        obj = PassaporteRastreabilidadeEvento(
            tenant_id=self.tenant_id,
            titulo=titulo,
            descricao=descricao,
            origem_tipo=origem_tipo,
            **dados.model_dump(exclude={"titulo", "descricao", "origem_tipo"}),
        )
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def vincular_evidencia_passaporte(
        self,
        dados: PassaporteRastreabilidadeEvidenciaCreate,
    ) -> PassaporteRastreabilidadeEvidencia:
        await self._query_or_fail(
            PassaporteRastreabilidade,
            dados.passaporte_id,
            "Passaporte de rastreabilidade não encontrado.",
        )
        await self._query_or_fail(EvidenciaCertificacao, dados.evidencia_id, "Evidência de certificação não encontrada.")
        obj = PassaporteRastreabilidadeEvidencia(tenant_id=self.tenant_id, **dados.model_dump())
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def listar_eventos_passaporte(self, passaporte_id: uuid.UUID) -> list[PassaporteRastreabilidadeEvento]:
        await self._query_or_fail(
            PassaporteRastreabilidade,
            passaporte_id,
            "Passaporte de rastreabilidade não encontrado.",
        )
        stmt = self._query_tenant(PassaporteRastreabilidadeEvento).where(
            PassaporteRastreabilidadeEvento.passaporte_id == passaporte_id
        )
        stmt = stmt.order_by(PassaporteRastreabilidadeEvento.ocorrido_em.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def listar_evidencias_passaporte(self, passaporte_id: uuid.UUID) -> list[PassaporteRastreabilidadeEvidencia]:
        await self._query_or_fail(
            PassaporteRastreabilidade,
            passaporte_id,
            "Passaporte de rastreabilidade não encontrado.",
        )
        stmt = self._query_tenant(PassaporteRastreabilidadeEvidencia).where(
            PassaporteRastreabilidadeEvidencia.passaporte_id == passaporte_id
        )
        stmt = stmt.order_by(PassaporteRastreabilidadeEvidencia.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())


class CertificacoesESGPublicService:
    """Serviços públicos de validação e leitura de certificações/ESG (não requerem tenant)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def verificar_integridade_snapshot(self, snapshot_json: dict[str, Any], snapshot_hash: str) -> dict[str, Any]:
        """
        Realiza a validação pura matemática de um snapshot comparado ao hash.
        """
        is_valid = verify_snapshot_hash(snapshot_json, snapshot_hash)
        if not is_valid:
            return {"integridade": "INVALIDA"}
            
        return {
            "integridade": "VALIDA",
            "algoritmo": "SHA256",
            "hash": snapshot_hash
        }

    async def verificar_integridade_passaporte(self, public_token: uuid.UUID) -> dict[str, Any]:
        """
        Busca um passaporte público pelo token e atesta sua integridade criptográfica.
        """
        stmt = select(PassaporteRastreabilidade).where(PassaporteRastreabilidade.public_token == public_token)
        passaporte = (await self.session.execute(stmt)).scalars().first()

        if not passaporte or passaporte.status != StatusPassaporte.PUBLICADO or not passaporte.publico:
            return {"integridade": "INVALIDA"}
            
        if not passaporte.snapshot_json or not passaporte.snapshot_hash:
            return {"integridade": "INVALIDA"}

        result = self.verificar_integridade_snapshot(passaporte.snapshot_json, passaporte.snapshot_hash)
        
        if result["integridade"] == "VALIDA":
            # Adiciona metadados adicionais em caso de sucesso
            result["versao"] = passaporte.versao
            result["publicado_em"] = passaporte.publicado_em

        return result
