from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select

from alert_engine.models import AlertStatus, Category, Domain, Priority, Severity, TriggerType
from alert_engine.schemas import OperationalAlertCreate
from alert_engine.service import AlertLifecycleService
from certificacoes_esg.models import (
    NaoConformidadeCertificacao,
    PlanoAcaoCertificacao,
    ProgramaCertificacao,
    StatusNaoConformidade,
    StatusPlanoAcao,
    StatusProgramaCertificacao,
)
from core.cadastros.propriedade_imovel.models import PropriedadeImovel
from core.cadastros.propriedades.propriedade_models import ExploracaoRural, Propriedade
from imoveis.models.imovel import ImovelRural

try:  # Python 3.11+
    from datetime import UTC
except ImportError:  # Python 3.10 compatibility in the test environment.
    UTC = timezone.utc  # noqa: UP017

from ._support import has_active_alert, set_rls_context
from .base import BaseAlertGenerator
from .context import AlertGeneratorContext
from .registry import register_alert_generator
from .result import AlertGeneratorResult


@dataclass(slots=True)
class _CertificacaoESG:
    entidade_id: UUID
    nome: str
    status: str
    data_fim: date
    propriedade_id: UUID | None
    imovel_rural_id: UUID | None
    propriedade_imovel_id: UUID | None


@dataclass(slots=True)
class _NaoConformidadeESG:
    entidade_id: UUID
    nome: str
    status: StatusNaoConformidade
    detectada_em: datetime
    prazo_correcao: datetime | None
    severidade: str
    propriedade_id: UUID | None
    imovel_rural_id: UUID | None
    propriedade_imovel_id: UUID | None


@dataclass(slots=True)
class _PlanoAcaoESG:
    entidade_id: UUID
    nome: str
    status: StatusPlanoAcao
    prazo: datetime
    concluido_em: datetime | None
    propriedade_id: UUID | None
    imovel_rural_id: UUID | None
    propriedade_imovel_id: UUID | None


@register_alert_generator
class ESGCertificacoesAlertGenerator(BaseAlertGenerator):
    """Generates canonical ESG and certifications alerts from existing models."""

    generator_name = "esg_certificacoes"
    domain = Domain.SYSTEM
    category = Category.COMPLIANCE
    execution_modes = ("scheduled",)

    async def run(self, context: AlertGeneratorContext) -> AlertGeneratorResult:
        """Execute ESG/certification rules from canonical context."""

        await set_rls_context(self.session, context.tenant_id)
        counters = {
            "certificacao_vencimento_proximo": 0,
            "certificacao_vencida": 0,
            "nao_conformidade_aberta": 0,
            "plano_acao_atrasado": 0,
        }
        result = AlertGeneratorResult(
            generator_name=self.generator_name,
            metadata={"rule_counters": counters},
        )
        dias_aviso_vencimento = self._metadata_int(context, "dias_aviso_vencimento", 30)

        for certificacao in await self._listar_certificacoes_vencimento_proximo(
            context.tenant_id,
            context.unidade_produtiva_id,
            dias_aviso_vencimento,
        ):
            created = await self._emitir_alerta_certificacao_vencimento_proximo(
                context.tenant_id,
                certificacao,
            )
            result.created += created
            result.updated += 1 - created
            counters["certificacao_vencimento_proximo"] += created

        for certificacao in await self._listar_certificacoes_vencidas(
            context.tenant_id,
            context.unidade_produtiva_id,
        ):
            created = await self._emitir_alerta_certificacao_vencida(
                context.tenant_id,
                certificacao,
            )
            result.created += created
            result.updated += 1 - created
            counters["certificacao_vencida"] += created

        for nao_conformidade in await self._listar_nao_conformidades_abertas(
            context.tenant_id,
            context.unidade_produtiva_id,
        ):
            created = await self._emitir_alerta_nao_conformidade_aberta(
                context.tenant_id,
                nao_conformidade,
            )
            result.created += created
            result.updated += 1 - created
            counters["nao_conformidade_aberta"] += created

        for plano_acao in await self._listar_planos_acao_atrasados(
            context.tenant_id,
            context.unidade_produtiva_id,
        ):
            created = await self._emitir_alerta_plano_acao_atrasado(
                context.tenant_id,
                plano_acao,
            )
            result.created += created
            result.updated += 1 - created
            counters["plano_acao_atrasado"] += created

        result.metadata = {"rule_counters": counters}
        return result

    async def _listar_certificacoes_vencimento_proximo(
        self,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
        dias_aviso_vencimento: int,
    ) -> list[_CertificacaoESG]:
        hoje = date.today()
        limite = hoje + timedelta(days=dias_aviso_vencimento)
        stmt = select(ProgramaCertificacao).where(
            ProgramaCertificacao.tenant_id == tenant_id,
            ProgramaCertificacao.status_programa.in_(
                (StatusProgramaCertificacao.ATIVO, StatusProgramaCertificacao.SUSPENSO)
            ),
            ProgramaCertificacao.data_fim.is_not(None),
            ProgramaCertificacao.data_fim >= hoje,
            ProgramaCertificacao.data_fim <= limite,
        )
        stmt = self._aplicar_escopo_unidade(
            stmt,
            ProgramaCertificacao,
            tenant_id,
            unidade_produtiva_id,
        )
        rows = await self.session.execute(
            stmt.order_by(
                ProgramaCertificacao.data_fim.asc(),
                ProgramaCertificacao.created_at.asc(),
            )
        )
        return [
            self._to_certificacao_esg(row)
            for row in rows.scalars().all()
            if row.data_fim is not None
        ]

    async def _listar_certificacoes_vencidas(
        self,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
    ) -> list[_CertificacaoESG]:
        hoje = date.today()
        stmt = select(ProgramaCertificacao).where(
            ProgramaCertificacao.tenant_id == tenant_id,
            ProgramaCertificacao.status_programa.in_(
                (StatusProgramaCertificacao.ATIVO, StatusProgramaCertificacao.SUSPENSO)
            ),
            ProgramaCertificacao.data_fim.is_not(None),
            ProgramaCertificacao.data_fim < hoje,
        )
        stmt = self._aplicar_escopo_unidade(
            stmt,
            ProgramaCertificacao,
            tenant_id,
            unidade_produtiva_id,
        )
        rows = await self.session.execute(
            stmt.order_by(
                ProgramaCertificacao.data_fim.asc(),
                ProgramaCertificacao.created_at.asc(),
            )
        )
        return [
            self._to_certificacao_esg(row)
            for row in rows.scalars().all()
            if row.data_fim is not None
        ]

    async def _listar_nao_conformidades_abertas(
        self,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
    ) -> list[_NaoConformidadeESG]:
        stmt = select(NaoConformidadeCertificacao).where(
            NaoConformidadeCertificacao.tenant_id == tenant_id,
            NaoConformidadeCertificacao.status.in_(
                (
                    StatusNaoConformidade.ABERTA,
                    StatusNaoConformidade.EM_ANALISE,
                    StatusNaoConformidade.EM_CORRECAO,
                )
            ),
            NaoConformidadeCertificacao.resolvida_em.is_(None),
        )
        stmt = self._aplicar_escopo_unidade(
            stmt,
            NaoConformidadeCertificacao,
            tenant_id,
            unidade_produtiva_id,
        )
        rows = await self.session.execute(
            stmt.order_by(
                NaoConformidadeCertificacao.detectada_em.asc(),
                NaoConformidadeCertificacao.created_at.asc(),
            )
        )
        return [self._to_nao_conformidade_esg(row) for row in rows.scalars().all()]

    async def _listar_planos_acao_atrasados(
        self,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
    ) -> list[_PlanoAcaoESG]:
        hoje = datetime.now(UTC)
        stmt = select(PlanoAcaoCertificacao).where(
            PlanoAcaoCertificacao.tenant_id == tenant_id,
            PlanoAcaoCertificacao.status.in_(
                (
                    StatusPlanoAcao.PENDENTE,
                    StatusPlanoAcao.EM_ANDAMENTO,
                    StatusPlanoAcao.ATRASADO,
                )
            ),
            PlanoAcaoCertificacao.concluido_em.is_(None),
            PlanoAcaoCertificacao.prazo < hoje,
        )
        stmt = self._aplicar_escopo_unidade(
            stmt,
            PlanoAcaoCertificacao,
            tenant_id,
            unidade_produtiva_id,
        )
        rows = await self.session.execute(
            stmt.order_by(PlanoAcaoCertificacao.prazo.asc(), PlanoAcaoCertificacao.created_at.asc())
        )
        return [self._to_plano_acao_esg(row) for row in rows.scalars().all()]

    async def _emitir_alerta_certificacao_vencimento_proximo(
        self,
        tenant_id: UUID,
        certificacao: _CertificacaoESG,
    ) -> int:
        dias = (certificacao.data_fim - date.today()).days
        return await self._persistir_alerta(
            tenant_id=tenant_id,
            unidade_produtiva_id=await self._resolver_unidade_produtiva(
                certificacao.propriedade_id,
                certificacao.imovel_rural_id,
                certificacao.propriedade_imovel_id,
            ),
            severity=Severity.WARNING,
            priority=Priority.HIGH,
            title="Certificação próxima do vencimento",
            message=(
                f"A certificação '{certificacao.nome}' vence em {dias} dia(s) "
                f"em {certificacao.data_fim.isoformat()}."
            ),
            source_type="ESG_CERTIFICACAO_VENCIMENTO_PROXIMO",
            source_id=str(certificacao.entidade_id),
            dedupe_key=f"esg:certificacao_vencimento_proximo:{certificacao.entidade_id}",
            metadata={
                "certificacao_id": str(certificacao.entidade_id),
                "nome": certificacao.nome,
                "status": certificacao.status,
                "data_fim": certificacao.data_fim.isoformat(),
                "dias_restantes": dias,
            },
        )

    async def _emitir_alerta_certificacao_vencida(
        self,
        tenant_id: UUID,
        certificacao: _CertificacaoESG,
    ) -> int:
        dias = (date.today() - certificacao.data_fim).days
        return await self._persistir_alerta(
            tenant_id=tenant_id,
            unidade_produtiva_id=await self._resolver_unidade_produtiva(
                certificacao.propriedade_id,
                certificacao.imovel_rural_id,
                certificacao.propriedade_imovel_id,
            ),
            severity=Severity.CRITICAL,
            priority=Priority.URGENT,
            title="Certificação vencida",
            message=f"A certificação '{certificacao.nome}' está vencida há {dias} dia(s).",
            source_type="ESG_CERTIFICACAO_VENCIDA",
            source_id=str(certificacao.entidade_id),
            dedupe_key=f"esg:certificacao_vencida:{certificacao.entidade_id}",
            metadata={
                "certificacao_id": str(certificacao.entidade_id),
                "nome": certificacao.nome,
                "status": certificacao.status,
                "data_fim": certificacao.data_fim.isoformat(),
                "dias_atraso": dias,
            },
        )

    async def _emitir_alerta_nao_conformidade_aberta(
        self,
        tenant_id: UUID,
        nao_conformidade: _NaoConformidadeESG,
    ) -> int:
        return await self._persistir_alerta(
            tenant_id=tenant_id,
            unidade_produtiva_id=await self._resolver_unidade_produtiva(
                nao_conformidade.propriedade_id,
                nao_conformidade.imovel_rural_id,
                nao_conformidade.propriedade_imovel_id,
            ),
            severity=Severity.WARNING,
            priority=Priority.HIGH,
            title="Não conformidade aberta",
            message=(
                f"A não conformidade '{nao_conformidade.nome}' permanece em "
                f"status {nao_conformidade.status.value}."
            ),
            source_type="ESG_NAO_CONFORMIDADE_ABERTA",
            source_id=str(nao_conformidade.entidade_id),
            dedupe_key=f"esg:nao_conformidade_aberta:{nao_conformidade.entidade_id}",
            metadata={
                "nao_conformidade_id": str(nao_conformidade.entidade_id),
                "nome": nao_conformidade.nome,
                "status": nao_conformidade.status.value,
                "detectada_em": nao_conformidade.detectada_em.isoformat(),
                "prazo_correcao": (
                    nao_conformidade.prazo_correcao.isoformat()
                    if nao_conformidade.prazo_correcao
                    else None
                ),
                "severidade": nao_conformidade.severidade,
            },
        )

    async def _emitir_alerta_plano_acao_atrasado(
        self,
        tenant_id: UUID,
        plano_acao: _PlanoAcaoESG,
    ) -> int:
        dias_atraso = max((datetime.now(UTC) - plano_acao.prazo).days, 0)
        severity = Severity.CRITICAL if dias_atraso >= 30 else Severity.WARNING
        priority = Priority.URGENT if severity == Severity.CRITICAL else Priority.HIGH
        return await self._persistir_alerta(
            tenant_id=tenant_id,
            unidade_produtiva_id=await self._resolver_unidade_produtiva(
                plano_acao.propriedade_id,
                plano_acao.imovel_rural_id,
                plano_acao.propriedade_imovel_id,
            ),
            severity=severity,
            priority=priority,
            title="Plano de ação ESG atrasado",
            message=(
                f"O plano de ação '{plano_acao.nome}' está atrasado há {dias_atraso} dia(s)."
            ),
            source_type="ESG_PLANO_ACAO_ATRASADO",
            source_id=str(plano_acao.entidade_id),
            dedupe_key=f"esg:plano_acao_atrasado:{plano_acao.entidade_id}",
            metadata={
                "plano_acao_id": str(plano_acao.entidade_id),
                "nome": plano_acao.nome,
                "status": plano_acao.status.value,
                "prazo": plano_acao.prazo.isoformat(),
                "concluido_em": (
                    plano_acao.concluido_em.isoformat() if plano_acao.concluido_em else None
                ),
                "dias_atraso": dias_atraso,
            },
        )

    async def _persistir_alerta(
        self,
        *,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
        severity: Severity,
        priority: Priority,
        title: str,
        message: str,
        source_type: str,
        source_id: str,
        dedupe_key: str,
        metadata: dict[str, Any],
        trigger_type: TriggerType = TriggerType.SCHEDULE,
    ) -> int:
        was_update = await has_active_alert(self.session, tenant_id, dedupe_key)
        payload = OperationalAlertCreate(
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            domain=Domain.SYSTEM,
            category=Category.COMPLIANCE,
            title=title,
            message=message,
            severity=severity,
            priority=priority,
            status=AlertStatus.OPEN,
            trigger_type=trigger_type,
            source_type=source_type,
            source_id=source_id,
            source_event_ids=[],
            source_indicator_ids=[],
            dedupe_key=dedupe_key,
            context=metadata,
        )
        await AlertLifecycleService(self.session, tenant_id).create_or_update_alert(payload)
        return 0 if was_update else 1

    async def _resolver_unidade_produtiva(
        self,
        propriedade_id: UUID | None,
        imovel_rural_id: UUID | None,
        propriedade_imovel_id: UUID | None,
    ) -> UUID | None:
        if propriedade_id is not None:
            stmt = (
                select(ExploracaoRural.unidade_produtiva_id)
                .where(
                    ExploracaoRural.tenant_id == self.tenant_id,
                    ExploracaoRural.propriedade_id == propriedade_id,
                )
                .order_by(ExploracaoRural.created_at.desc())
            )
            result = await self.session.execute(stmt)
            return result.scalars().first()
        if imovel_rural_id is not None:
            stmt = (
                select(ExploracaoRural.unidade_produtiva_id)
                .select_from(PropriedadeImovel)
                .join(Propriedade, Propriedade.id == PropriedadeImovel.propriedade_id)
                .join(ExploracaoRural, ExploracaoRural.propriedade_id == Propriedade.id)
                .where(
                    PropriedadeImovel.tenant_id == self.tenant_id,
                    PropriedadeImovel.imovel_rural_id == imovel_rural_id,
                )
                .order_by(ExploracaoRural.created_at.desc())
                .limit(1)
            )
            result = await self.session.execute(stmt)
            unidade = result.scalars().first()
            if unidade is not None:
                return unidade
            return None
        if propriedade_imovel_id is not None:
            stmt = (
                select(ExploracaoRural.unidade_produtiva_id)
                .select_from(PropriedadeImovel)
                .join(Propriedade, Propriedade.id == PropriedadeImovel.propriedade_id)
                .join(ExploracaoRural, ExploracaoRural.propriedade_id == Propriedade.id)
                .where(
                    PropriedadeImovel.tenant_id == self.tenant_id,
                    PropriedadeImovel.id == propriedade_imovel_id,
                )
                .order_by(ExploracaoRural.created_at.desc())
                .limit(1)
            )
            result = await self.session.execute(stmt)
            unidade = result.scalars().first()
            if unidade is not None:
                return unidade
            
            return None
        return None

    def _aplicar_escopo_unidade(
        self,
        stmt: Any,
        model: type[Any],
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
    ) -> Any:
        if unidade_produtiva_id is None:
            return stmt
        propriedades = (
            select(ExploracaoRural.propriedade_id)
            .where(
                ExploracaoRural.tenant_id == tenant_id,
                ExploracaoRural.unidade_produtiva_id == unidade_produtiva_id,
            )
            .distinct()
        )
        imoveis = (
            select(ImovelRural.id)
            .join(PropriedadeImovel, PropriedadeImovel.imovel_rural_id == ImovelRural.id)
            .where(
                PropriedadeImovel.tenant_id == tenant_id,
                PropriedadeImovel.propriedade_id.in_(propriedades),
            )
        )
        vinculos = (
            select(PropriedadeImovel.id)
            .where(
                PropriedadeImovel.tenant_id == tenant_id,
                PropriedadeImovel.propriedade_id.in_(propriedades),
            )
        )
        return stmt.where(
            or_(
                model.propriedade_id.in_(propriedades),
                model.imovel_rural_id.in_(imoveis),
                model.propriedade_imovel_id.in_(vinculos),
            )
        )

    @staticmethod
    def _to_certificacao_esg(row: ProgramaCertificacao) -> _CertificacaoESG:
        return _CertificacaoESG(
            entidade_id=row.id,
            nome=row.nome,
            status=(
                row.status_programa.value
                if hasattr(row.status_programa, "value")
                else str(row.status_programa)
            ),
            data_fim=row.data_fim if row.data_fim is not None else date.today(),
            propriedade_id=row.propriedade_id,
            imovel_rural_id=row.imovel_rural_id,
            propriedade_imovel_id=row.propriedade_imovel_id,
        )

    @staticmethod
    def _to_nao_conformidade_esg(row: NaoConformidadeCertificacao) -> _NaoConformidadeESG:
        return _NaoConformidadeESG(
            entidade_id=row.id,
            nome=row.titulo,
            status=row.status,
            detectada_em=row.detectada_em,
            prazo_correcao=row.prazo_correcao,
            severidade=(
                row.severidade.value if hasattr(row.severidade, "value") else str(row.severidade)
            ),
            propriedade_id=row.propriedade_id,
            imovel_rural_id=row.imovel_rural_id,
            propriedade_imovel_id=row.propriedade_imovel_id,
        )

    @staticmethod
    def _to_plano_acao_esg(row: PlanoAcaoCertificacao) -> _PlanoAcaoESG:
        return _PlanoAcaoESG(
            entidade_id=row.id,
            nome=row.titulo,
            status=row.status,
            prazo=row.prazo,
            concluido_em=row.concluido_em,
            propriedade_id=row.propriedade_id,
            imovel_rural_id=row.imovel_rural_id,
            propriedade_imovel_id=row.propriedade_imovel_id,
        )

    @staticmethod
    def _metadata_int(context: AlertGeneratorContext, key: str, default: int) -> int:
        value = context.metadata.get(key, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
