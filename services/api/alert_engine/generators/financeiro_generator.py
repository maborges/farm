from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select

from agricola.production_units.models import ProductionUnit
from agricola.safras.models import Safra
from alert_engine.models import AlertStatus, Category, Domain, Priority, Severity, TriggerType
from alert_engine.schemas import OperationalAlertCreate
from alert_engine.service import AlertLifecycleService
from core.cadastros.propriedades.models import AreaRural
from financeiro.models.cenario import FinanceiroSafraCenario
from financeiro.services.cenario_service import CenarioFinanceiroService
from financeiro.services.despesa_service import DespesaService
from financeiro.services.receita_service import ReceitaService
from financeiro.services.relatorio_service import RelatorioService

from ._support import has_active_alert, set_rls_context
from .base import BaseAlertGenerator
from .context import AlertGeneratorContext
from .registry import register_alert_generator
from .result import AlertGeneratorResult


@dataclass(slots=True)
class _TituloFinanceiro:
    titulo_id: UUID
    unidade_produtiva_id: UUID | None
    descricao: str
    status: str
    data_vencimento: date
    valor: float
    tipo: str


@dataclass(slots=True)
class _DesvioFinanceiro:
    safra_id: UUID
    cenario_nome: str
    resultado_real: float
    resultado_planejado: float
    desvio: float
    desvio_percentual: float


@register_alert_generator
class FinanceiroAlertGenerator(BaseAlertGenerator):
    """Generates canonical finance alerts from existing financial services."""

    generator_name = "financeiro"
    domain = Domain.FINANCE
    category = Category.FINANCEIRO
    execution_modes = ("scheduled",)

    async def run(self, context: AlertGeneratorContext) -> AlertGeneratorResult:
        """Execute financial rules from canonical context."""

        await set_rls_context(self.session, context.tenant_id)
        counters = {
            "vencimentos_proximos": 0,
            "lancamentos_vencidos": 0,
            "fluxo_caixa_critico": 0,
            "orcamento_excedido": 0,
        }
        result = AlertGeneratorResult(
            generator_name=self.generator_name,
            metadata={"rule_counters": counters},
        )

        dias_aviso_vencimento = self._metadata_int(context, "dias_aviso_vencimento", 7)
        limite_saldo_fluxo_caixa = self._metadata_float(
            context,
            "limite_saldo_fluxo_caixa",
            0.0,
        )
        limite_desvio_orcamento = self._metadata_float(
            context,
            "limite_desvio_orcamento_percentual",
            10.0,
        )

        for titulo in await self._listar_vencimentos_proximos(
            context.tenant_id,
            context.unidade_produtiva_id,
            dias_aviso_vencimento,
        ):
            created = await self._emitir_alerta_vencimento_proximo(context.tenant_id, titulo)
            result.created += created
            result.updated += 1 - created
            counters["vencimentos_proximos"] += created

        for titulo in await self._listar_vencidos(
            context.tenant_id,
            context.unidade_produtiva_id,
        ):
            created = await self._emitir_alerta_vencido(context.tenant_id, titulo)
            result.created += created
            result.updated += 1 - created
            counters["lancamentos_vencidos"] += created

        fluxo = await self._avaliar_fluxo_caixa_critico(
            context.tenant_id,
            context.unidade_produtiva_id,
            limite_saldo_fluxo_caixa,
        )
        if fluxo is not None:
            created = await self._emitir_alerta_fluxo_caixa(context.tenant_id, fluxo)
            result.created += created
            result.updated += 1 - created
            counters["fluxo_caixa_critico"] += created

        for desvio in await self._listar_desvios_orcamento(
            context.tenant_id,
            context.unidade_produtiva_id,
            limite_desvio_orcamento,
        ):
            created = await self._emitir_alerta_orcamento_excedido(
                context.tenant_id,
                desvio,
                limite_desvio_orcamento,
            )
            result.created += created
            result.updated += 1 - created
            counters["orcamento_excedido"] += created

        result.metadata = {"rule_counters": counters}
        return result

    async def _listar_vencimentos_proximos(
        self,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
        dias_aviso_vencimento: int,
    ) -> list[_TituloFinanceiro]:
        limite = date.today() + timedelta(days=dias_aviso_vencimento)
        receitas_svc = ReceitaService(self.session, tenant_id)
        despesas_svc = DespesaService(self.session, tenant_id)
        titulos = []
        for status in ("A_RECEBER", "RECEBIDO_PARCIAL"):
            titulos.extend(
                await self._carregar_titulos(
                    receitas_svc,
                    unidade_produtiva_id,
                    status,
                    date.today(),
                    limite,
                    "RECEITA",
                )
            )
        for status in ("A_PAGAR", "PAGO_PARCIAL"):
            titulos.extend(
                await self._carregar_titulos(
                    despesas_svc,
                    unidade_produtiva_id,
                    status,
                    date.today(),
                    limite,
                    "DESPESA",
                )
            )
        return sorted(titulos, key=lambda item: (item.data_vencimento, item.titulo_id))

    async def _listar_vencidos(
        self,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
    ) -> list[_TituloFinanceiro]:
        hoje = date.today()
        vencimento_ate = hoje - timedelta(days=1)
        receitas_svc = ReceitaService(self.session, tenant_id)
        despesas_svc = DespesaService(self.session, tenant_id)
        titulos = []
        for status in ("A_RECEBER", "RECEBIDO_PARCIAL"):
            titulos.extend(
                await self._carregar_titulos(
                    receitas_svc,
                    unidade_produtiva_id,
                    status,
                    None,
                    vencimento_ate,
                    "RECEITA",
                )
            )
        for status in ("A_PAGAR", "ATRASADO", "PAGO_PARCIAL"):
            titulos.extend(
                await self._carregar_titulos(
                    despesas_svc,
                    unidade_produtiva_id,
                    status,
                    None,
                    vencimento_ate,
                    "DESPESA",
                )
            )
        return sorted(titulos, key=lambda item: (item.data_vencimento, item.titulo_id))

    async def _carregar_titulos(
        self,
        service: ReceitaService | DespesaService,
        unidade_produtiva_id: UUID | None,
        status: str,
        vencimento_de: date | None,
        vencimento_ate: date | None,
        tipo: str,
    ) -> list[_TituloFinanceiro]:
        rows = await service.listar_com_filtros(
            unidade_produtiva_id=unidade_produtiva_id,
            status=status,
            vencimento_de=vencimento_de,
            vencimento_ate=vencimento_ate,
        )
        return [
            _TituloFinanceiro(
                titulo_id=row.id,
                unidade_produtiva_id=row.unidade_produtiva_id,
                descricao=row.descricao,
                status=row.status,
                data_vencimento=row.data_vencimento,
                valor=float(row.valor_total or 0.0),
                tipo=tipo,
            )
            for row in rows
        ]

    async def _avaliar_fluxo_caixa_critico(
        self,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
        limite_saldo_fluxo_caixa: float,
    ) -> _TituloFinanceiro | None:
        hoje = date.today()
        fim_mes = date(hoje.year, hoje.month, monthrange(hoje.year, hoje.month)[1])
        fluxo = await RelatorioService(self.session, tenant_id).fluxo_caixa(
            hoje.replace(day=1),
            fim_mes,
            unidade_produtiva_id,
        )
        saldo_previsto = float(fluxo.totais.total_saldo_previsto)
        if saldo_previsto >= limite_saldo_fluxo_caixa:
            return None
        return _TituloFinanceiro(
            titulo_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            descricao="Fluxo de caixa projetado",
            status="PROJETADO",
            data_vencimento=fim_mes,
            valor=saldo_previsto,
            tipo="FLUXO_CAIXA",
        )

    async def _listar_desvios_orcamento(
        self,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
        limite_desvio_orcamento: float,
    ) -> list[_DesvioFinanceiro]:
        stmt = select(FinanceiroSafraCenario.safra_id).where(
            FinanceiroSafraCenario.tenant_id == tenant_id,
            FinanceiroSafraCenario.escolhido.is_(True),
        )
        if unidade_produtiva_id is not None:
            stmt = (
                stmt.join(Safra, Safra.id == FinanceiroSafraCenario.safra_id)
                .join(ProductionUnit, ProductionUnit.safra_id == Safra.id)
                .join(AreaRural, AreaRural.id == ProductionUnit.area_id)
                .where(
                    Safra.tenant_id == tenant_id,
                    ProductionUnit.tenant_id == tenant_id,
                    AreaRural.tenant_id == tenant_id,
                    AreaRural.unidade_produtiva_id == unidade_produtiva_id,
                )
            )
        rows = await self.session.execute(stmt.order_by(FinanceiroSafraCenario.safra_id.asc()))
        desvios: list[_DesvioFinanceiro] = []
        for row in rows.all():
            analise = await CenarioFinanceiroService(self.session, tenant_id).analisar_desvio(
                row[0]
            )
            if not analise.get("cenario_escolhido"):
                continue
            desvio_percentual = float(analise.get("desvio_percentual") or 0.0)
            if desvio_percentual > -limite_desvio_orcamento:
                continue
            desvios.append(
                _DesvioFinanceiro(
                    safra_id=row[0],
                    cenario_nome=str(analise.get("cenario_escolhido") or ""),
                    resultado_real=float(analise.get("resultado_real") or 0.0),
                    resultado_planejado=float(analise.get("resultado_planejado") or 0.0),
                    desvio=float(analise.get("desvio") or 0.0),
                    desvio_percentual=desvio_percentual,
                )
            )
        return desvios

    async def _emitir_alerta_vencimento_proximo(
        self,
        tenant_id: UUID,
        titulo: _TituloFinanceiro,
    ) -> int:
        dias = (titulo.data_vencimento - date.today()).days
        return await self._persistir_alerta(
            tenant_id=tenant_id,
            unidade_produtiva_id=titulo.unidade_produtiva_id,
            category=Category.FINANCEIRO,
            severity=Severity.INFO,
            priority=Priority.NORMAL,
            title="Título próximo do vencimento",
            message=(
                f"O título financeiro '{titulo.descricao}' vence em {dias} dia(s) "
                f"em {titulo.data_vencimento.isoformat()}."
            ),
            source_type="FINANCEIRO_VENCIMENTO_PROXIMO",
            source_id=str(titulo.titulo_id),
            dedupe_key=f"financeiro:vencimento_proximo:{titulo.titulo_id}",
            metadata={
                "titulo_id": str(titulo.titulo_id),
                "tipo": titulo.tipo,
                "status": titulo.status,
                "descricao": titulo.descricao,
                "valor": titulo.valor,
                "data_vencimento": titulo.data_vencimento.isoformat(),
                "dias_restantes": dias,
            },
        )

    async def _emitir_alerta_vencido(
        self,
        tenant_id: UUID,
        titulo: _TituloFinanceiro,
    ) -> int:
        dias = (date.today() - titulo.data_vencimento).days
        return await self._persistir_alerta(
            tenant_id=tenant_id,
            unidade_produtiva_id=titulo.unidade_produtiva_id,
            category=Category.FINANCEIRO,
            severity=Severity.WARNING,
            priority=Priority.HIGH,
            title="Título vencido",
            message=(f"O título financeiro '{titulo.descricao}' está vencido há {dias} dia(s)."),
            source_type="FINANCEIRO_VENCIDO",
            source_id=str(titulo.titulo_id),
            dedupe_key=f"financeiro:vencido:{titulo.titulo_id}",
            metadata={
                "titulo_id": str(titulo.titulo_id),
                "tipo": titulo.tipo,
                "status": titulo.status,
                "descricao": titulo.descricao,
                "valor": titulo.valor,
                "data_vencimento": titulo.data_vencimento.isoformat(),
                "dias_atraso": dias,
            },
        )

    async def _emitir_alerta_fluxo_caixa(
        self,
        tenant_id: UUID,
        fluxo: _TituloFinanceiro,
    ) -> int:
        severity = Severity.CRITICAL if fluxo.valor < 0 else Severity.WARNING
        priority = Priority.URGENT if severity == Severity.CRITICAL else Priority.HIGH
        return await self._persistir_alerta(
            tenant_id=tenant_id,
            unidade_produtiva_id=fluxo.unidade_produtiva_id,
            category=Category.FINANCEIRO,
            severity=severity,
            priority=priority,
            title="Fluxo de caixa crítico",
            message=(f"O fluxo de caixa projetado está em R$ {fluxo.valor:,.2f} no período atual."),
            source_type="FINANCEIRO_FLUXO_CAIXA_CRITICO",
            source_id=str(tenant_id),
            dedupe_key=(
                f"financeiro:fluxo_caixa_critico:{tenant_id}:"
                f"{fluxo.unidade_produtiva_id or 'global'}"
            ),
            metadata={
                "tenant_id": str(tenant_id),
                "unidade_produtiva_id": str(fluxo.unidade_produtiva_id)
                if fluxo.unidade_produtiva_id
                else None,
                "periodo": fluxo.data_vencimento.isoformat(),
                "saldo_previsto": fluxo.valor,
            },
        )

    async def _emitir_alerta_orcamento_excedido(
        self,
        tenant_id: UUID,
        desvio: _DesvioFinanceiro,
        limite_desvio_orcamento: float,
    ) -> int:
        severity = (
            Severity.CRITICAL
            if desvio.desvio_percentual <= -(limite_desvio_orcamento * 2)
            else Severity.WARNING
        )
        priority = Priority.URGENT if severity == Severity.CRITICAL else Priority.HIGH
        return await self._persistir_alerta(
            tenant_id=tenant_id,
            unidade_produtiva_id=None,
            category=Category.FINANCEIRO,
            severity=severity,
            priority=priority,
            title="Orçamento financeiro excedido",
            message=(
                f"A safra {desvio.safra_id} está {abs(desvio.desvio_percentual):.2f}% "
                "abaixo do planejado."
            ),
            source_type="FINANCEIRO_ORCAMENTO_EXCEDIDO",
            source_id=str(desvio.safra_id),
            dedupe_key=f"financeiro:orcamento_excedido:{desvio.safra_id}",
            metadata={
                "safra_id": str(desvio.safra_id),
                "cenario_nome": desvio.cenario_nome,
                "resultado_real": desvio.resultado_real,
                "resultado_planejado": desvio.resultado_planejado,
                "desvio": desvio.desvio,
                "desvio_percentual": desvio.desvio_percentual,
                "limite_desvio_percentual": limite_desvio_orcamento,
            },
        )

    async def _persistir_alerta(
        self,
        *,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
        category: Category,
        severity: Severity,
        priority: Priority,
        title: str,
        message: str,
        source_type: str,
        source_id: str,
        dedupe_key: str,
        metadata: dict[str, object],
        trigger_type: TriggerType = TriggerType.SCHEDULE,
    ) -> int:
        was_update = await has_active_alert(self.session, tenant_id, dedupe_key)
        payload = OperationalAlertCreate(
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            domain=Domain.FINANCE,
            category=category,
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

    @staticmethod
    def _metadata_int(context: AlertGeneratorContext, key: str, default: int) -> int:
        value = context.metadata.get(key, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _metadata_float(context: AlertGeneratorContext, key: str, default: float) -> float:
        value = context.metadata.get(key, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
