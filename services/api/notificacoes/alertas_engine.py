"""
Motor de Alertas Automáticos do AgroSaaS.

Gera notificações baseadas em eventos e regras de negócio:
- Vencimentos de contas a pagar/receber
- Estoque baixo de insumos
- Tarefas atrasadas
- Carência de defensivos
- Condições climáticas adversas
- Alertas de NDVI
- Etc.

Execução:
- Via Celery Beat (agendado diariamente)
- Via webhook (eventos em tempo real)
- Manual (admin)

Uso:
    python -m notificacoes.alertas_engine
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List
from uuid import UUID
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from core.database import async_session_maker
from notificacoes.service import NotificacaoService
from notificacoes.schemas import NotificacaoCreate


class AlertasEngine:
    """Motor de geração automática de alertas."""

    async def verificar_todos_tenants(self) -> dict:
        """Itera sobre todos os tenants ativos e verifica alertas."""
        from core.models.tenant import Tenant
        from core.models.billing import AssinaturaTenant

        async with async_session_maker() as session:
            # Buscar todos os tenants com assinatura ativa.
            # Sem .distinct() no SQL: Tenant tem colunas `json` (não `jsonb`,
            # ex. branding/smtp_config) e Postgres não sabe comparar `json`
            # para DISTINCT (UndefinedFunctionError, confirmado em produção
            # 2026-08-14 — este método nunca tinha rodado com sucesso contra
            # dado real). Dedup por id em Python em vez disso.
            stmt = (
                select(Tenant)
                .join(AssinaturaTenant, AssinaturaTenant.tenant_id == Tenant.id)
                .where(
                    Tenant.ativo == True,
                    # ATIVA + TRIAL: excluir TRIAL deixava tenants novos invisíveis
                    # (mesmo padrão de bug já documentado em feedback_trial_subscriptions).
                    AssinaturaTenant.status.in_(["ATIVA", "TRIAL"]),
                    # "GRUPO" nunca foi um valor válido de tipo_assinatura — só
                    # existem TENANT (default) e ADICIONAL (core/models/billing.py:106).
                    # Filtro anterior fazia 0 tenants baterem sempre, silenciosamente.
                    AssinaturaTenant.tipo_assinatura == "TENANT",
                )
            )
            result = await session.execute(stmt)
            vistos = set()
            tenants = []
            for tenant in result.scalars().all():
                if tenant.id not in vistos:
                    vistos.add(tenant.id)
                    tenants.append(tenant)

        logger.info(f"Verificando alertas para {len(tenants)} tenants ativos")

        resultados = {
            "tenants_verificados": len(tenants),
            "alertas_gerados": 0,
            "erros": 0,
        }

        for tenant in tenants:
            try:
                alertas = await self.verificar_tenant(tenant.id)
                resultados["alertas_gerados"] += len(alertas)
                logger.info(f"Tenant {tenant.nome}: {len(alertas)} alertas gerados")
            except Exception as e:
                logger.error(f"Erro ao verificar tenant {tenant.nome}: {e}")
                resultados["erros"] += 1

        return resultados

    async def verificar_tenant(self, tenant_id: UUID) -> List[NotificacaoCreate]:
        """Verifica todas as regras de alerta para um tenant específico."""
        alertas_gerados = []

        async with async_session_maker() as session:
            svc = NotificacaoService(session, tenant_id)

            # 1. Vencimentos próximos — aposentado em favor de alert_engine/generators/
            # financeiro_generator.py (mesma checagem, cobre A_RECEBER/A_PAGAR com
            # status parcial, vencidos separados de próximos). Ver memória do
            # projeto project_tres_sistemas_alertas_mapeados.

            # 2. Estoque baixo
            estoque_baixo = await self._verificar_estoque_baixo(session, tenant_id)
            alertas_gerados.extend(estoque_baixo)

            # 3. Carência de defensivos
            carencia = await self._verificar_carencia_defensivos(session, tenant_id)
            alertas_gerados.extend(carencia)

            # 4. Tarefas atrasadas — aposentado em favor de alert_engine/generators/
            # agricultura_generator.py (AGRICULTURA_OPERACAO_ATRASADA), mais testado
            # e agora também espelhado em Notificacao via AlertLifecycleService.
            # Ver memória do projeto project_tres_sistemas_alertas_mapeados.

            # 4.1 Diárias de RH pendentes de pagamento
            diarias_pendentes = await self._verificar_diarias_pendentes(session, tenant_id)
            alertas_gerados.extend(diarias_pendentes)

            # 4.2 Balanças físicas com aferição vencida (metrologia legal)
            afericao_vencida = await self._verificar_afericao_vencida(session, tenant_id)
            alertas_gerados.extend(afericao_vencida)

            # Criar notificações
            for alerta in alertas_gerados:
                await svc.criar_e_push(alerta)

            # Reusa o agregador oficial agrícola para observabilidade de workflow
            from agricola.alertas.service import AlertasAgricolasService

            governanca_svc = AlertasAgricolasService(session, tenant_id)
            findings_total = await governanca_svc.verificar_governanca_operacional()
            if findings_total:
                logger.info(
                    f"Tenant {tenant_id}: {findings_total} inconsistência(s) de workflow operacional observadas"
                )
            reconciliacao_total = await governanca_svc.verificar_reconciliacao_economica()
            if reconciliacao_total:
                logger.info(
                    f"Tenant {tenant_id}: {reconciliacao_total} inconsistência(s) de reconciliação econômica observadas"
                )

            # 5. Exposição Comercial (Hedge) — apenas se módulo F4_HEDGING ativo
            await self._verificar_exposicao_comercial(session, tenant_id)

        return alertas_gerados

    async def _verificar_exposicao_comercial(
        self, session: AsyncSession, tenant_id: UUID
    ) -> None:
        """Verifica e emite alertas de risco de cobertura comercial via HedgeSnapshotService.

        Delega ao HedgeSnapshotService para manter a lógica centralizada no módulo F4.
        Executado apenas para tenants que possuem contratos futuros ativos.

        Args:
            session: Sessão AsyncSession.
            tenant_id: UUID do tenant.
        """
        from datetime import date as date_type
        from financeiro.hedge.snapshot_service import HedgeSnapshotService

        try:
            snapshot_svc = HedgeSnapshotService(session)
            hoje = date_type.today()
            count = await snapshot_svc.verificar_exposicao_comercial(
                tenant_id=tenant_id,
                data_ref=hoje,
            )
            if count:
                logger.info(f"Tenant {tenant_id}: {count} alerta(s) de exposição comercial gerado(s)")
        except Exception as exc:
            logger.warning(f"Tenant {tenant_id}: erro ao verificar exposição comercial — {exc}")



    async def _verificar_estoque_baixo(
        self, session: AsyncSession, tenant_id: UUID
    ) -> List[NotificacaoCreate]:
        """Verifica produtos com estoque abaixo do mínimo."""
        from core.cadastros.models import ProdutoCatalogo as Produto
        from operacional.models.estoque import SaldoEstoque

        alertas = []

        # Prioriza mínimo contextual do saldo; fallback compatível para catálogo.
        minimo_efetivo = func.coalesce(SaldoEstoque.estoque_minimo, Produto.estoque_minimo)

        stmt = (
            select(Produto, SaldoEstoque)
            .join(SaldoEstoque, SaldoEstoque.produto_id == Produto.id)
            .where(
                Produto.tenant_id == tenant_id,
                minimo_efetivo > 0,
                SaldoEstoque.quantidade_atual < minimo_efetivo,
            )
            .limit(10)
        )
        result = await session.execute(stmt)
        produtos_baixo = result.all()

        if produtos_baixo:
            itens = [
                f"{p.Produto.nome}: {p.SaldoEstoque.quantidade_atual}/{(p.SaldoEstoque.estoque_minimo if p.SaldoEstoque.estoque_minimo is not None else p.Produto.estoque_minimo)} {p.Produto.unidade_medida}"
                for p in produtos_baixo
            ]
            alertas.append(
                NotificacaoCreate(
                    tipo="ESTOQUE_BAIXO",
                    titulo=f"{len(produtos_baixo)} produtos com estoque baixo",
                    mensagem="Produtos: " + ", ".join(itens[:5]) + ("..." if len(itens) > 5 else ""),
                    meta={
                        "quantidade": len(produtos_baixo),
                        "produtos": [
                            {
                                "id": str(p.Produto.id),
                                "nome": p.Produto.nome,
                                "quantidade_atual": float(p.SaldoEstoque.quantidade_atual),
                                "estoque_minimo": float(
                                    p.SaldoEstoque.estoque_minimo
                                    if p.SaldoEstoque.estoque_minimo is not None
                                    else p.Produto.estoque_minimo
                                ),
                                "unidade": p.Produto.unidade_medida,
                            }
                            for p in produtos_baixo
                        ],
                    },
                )
            )
            await self._espelhar_operational_alert(
                session,
                tenant_id,
                dedupe_key=f"notificacoes:estoque_baixo:{tenant_id}",
                source_type="ESTOQUE_BAIXO",
                source_id=str(tenant_id),
                title=f"{len(produtos_baixo)} produtos com estoque baixo",
                message="Produtos: " + ", ".join(itens[:5]) + ("..." if len(itens) > 5 else ""),
            )

        return alertas

    async def _verificar_carencia_defensivos(
        self, session: AsyncSession, tenant_id: UUID
    ) -> List[NotificacaoCreate]:
        """Verifica carência de defensivos agrícolas vencendo em 24-48h.

        Corrigido em 2026-08-14: importava `agricola.models.aplicacao.AplicacaoDefensivo`,
        módulo/model inexistente (ModuleNotFoundError). Carência é campo de
        `InsumoOperacao` (linha do insumo aplicado numa `OperacaoAgricola`),
        não uma entidade própria — precisa join com OperacaoAgricola (talhão),
        AreaRural (nome do talhão) e Produto (nome do defensivo).
        """
        from agricola.operacoes.models import InsumoOperacao, OperacaoAgricola
        from core.cadastros.propriedades.models import AreaRural
        from core.cadastros.produtos.models import Produto

        alertas = []
        hoje = datetime.now(timezone.utc).date()
        daqui_2_dias = hoje + timedelta(days=2)

        stmt = (
            select(InsumoOperacao, OperacaoAgricola, AreaRural, Produto)
            .join(OperacaoAgricola, OperacaoAgricola.id == InsumoOperacao.operacao_id)
            .join(AreaRural, AreaRural.id == OperacaoAgricola.talhao_id)
            .join(Produto, Produto.id == InsumoOperacao.produto_id)
            .where(
                InsumoOperacao.tenant_id == tenant_id,
                InsumoOperacao.data_reentrada.is_not(None),
                InsumoOperacao.data_reentrada >= hoje,
                InsumoOperacao.data_reentrada <= daqui_2_dias,
            )
            .limit(10)
        )
        result = await session.execute(stmt)
        linhas = result.all()

        if linhas:
            itens = [
                f"{produto.nome} (Talhão {area.nome}) - vence em {(insumo.data_reentrada - hoje).days} dias"
                for insumo, _op, area, produto in linhas
            ]
            alertas.append(
                NotificacaoCreate(
                    tipo="CARENCIA_DEFENSIVO",
                    titulo=f"{len(linhas)} defensivos com carência vencendo",
                    mensagem="Atenção: " + ", ".join(itens[:3]) + ("..." if len(itens) > 3 else ""),
                    meta={
                        "quantidade": len(linhas),
                        "aplicacoes": [
                            {
                                "id": str(insumo.id),
                                "defensivo": produto.nome,
                                "talhao": area.nome,
                                "carencia_dias": insumo.carencia_dias,
                                "data_fim_carencia": insumo.data_reentrada.isoformat(),
                            }
                            for insumo, _op, area, produto in linhas
                        ],
                    },
                )
            )
            await self._espelhar_operational_alert(
                session,
                tenant_id,
                dedupe_key=f"notificacoes:carencia_defensivo:{tenant_id}",
                source_type="CARENCIA_DEFENSIVO",
                source_id=str(tenant_id),
                title=f"{len(linhas)} defensivos com carência vencendo",
                message="Atenção: " + ", ".join(itens[:3]) + ("..." if len(itens) > 3 else ""),
                category_compliance=True,
            )

        return alertas

    async def _verificar_diarias_pendentes(
        self, session: AsyncSession, tenant_id: UUID
    ) -> List[NotificacaoCreate]:
        """Verifica diárias de RH pendentes de pagamento há mais de 15 dias, agrupadas por colaborador.

        Gera uma notificação acionável (meta.acoes com endpoint de pagamento
        real, POST /rh/diarias/pagar-lote) por colaborador — não uma por
        diária, para não gerar spam quando há várias diárias acumuladas.
        """
        from rh.models import LancamentoDiaria
        from rh.service import obter_dados_exibicao_colaborador
        from core.models.auth import Usuario  # noqa: F401 — mantém padrão de import local dos demais métodos

        alertas: List[NotificacaoCreate] = []
        limite = datetime.now(timezone.utc).date() - timedelta(days=15)

        stmt = (
            select(LancamentoDiaria)
            .where(
                LancamentoDiaria.tenant_id == tenant_id,
                LancamentoDiaria.status == "PENDENTE",
                LancamentoDiaria.data <= limite,
            )
            .order_by(LancamentoDiaria.colaborador_id)
            .limit(200)
        )
        result = await session.execute(stmt)
        lancamentos = result.scalars().all()

        por_colaborador: dict[UUID, list[LancamentoDiaria]] = {}
        for lanc in lancamentos:
            por_colaborador.setdefault(lanc.colaborador_id, []).append(lanc)

        for colaborador_id, itens in por_colaborador.items():
            dados = await obter_dados_exibicao_colaborador(session, colaborador_id)
            nome = dados.get("nome") or "Colaborador"
            total = sum(item.valor_diaria for item in itens)
            total_fmt = f"{total:,.2f}".translate(str.maketrans(",.", ".,"))
            alertas.append(
                NotificacaoCreate(
                    tipo="DIARIA_PENDENTE",
                    titulo=f"{len(itens)} diária(s) pendente(s) — {nome}",
                    mensagem=f"{nome} tem {len(itens)} diária(s) não pagas há mais de 15 dias. Total: R$ {total_fmt}",
                    origem="rh_diaria",
                    origem_id=str(colaborador_id),
                    meta={
                        "colaborador_id": str(colaborador_id),
                        "quantidade": len(itens),
                        "total_pendente": float(total),
                        "acoes": [
                            {
                                "label": "Pagar",
                                "acao": "pagar",
                                "endpoint": "/rh/diarias/pagar-lote",
                                "method": "POST",
                                "body": {"ids": [str(item.id) for item in itens]},
                            }
                        ],
                    },
                )
            )
            await self._espelhar_operational_alert(
                session,
                tenant_id,
                dedupe_key=f"notificacoes:diaria_pendente:{colaborador_id}",
                source_type="DIARIA_PENDENTE",
                source_id=str(colaborador_id),
                title=f"{len(itens)} diária(s) pendente(s) — {nome}",
                message=f"{nome} tem {len(itens)} diária(s) não pagas há mais de 15 dias. Total: R$ {total_fmt}",
                domain_finance=True,
            )

        return alertas

    async def _verificar_afericao_vencida(
        self, session: AsyncSession, tenant_id: UUID
    ) -> List[NotificacaoCreate]:
        """Verifica balanças físicas ativas cuja aferição mais recente já venceu
        (metrologia legal) — mesma lógica de `BalancaFisicaService._mapa_ultima_afericao`
        (DISTINCT ON pela aferição mais recente por balança), sem depender do
        módulo balanca importar notificacoes (evita acoplamento na outra direção)."""
        from balanca.models import BalancaFisica, AfericaoBalanca

        alertas: List[NotificacaoCreate] = []
        agora = datetime.now(timezone.utc).replace(tzinfo=None)

        ultima_afericao = (
            select(AfericaoBalanca.balanca_fisica_id, AfericaoBalanca.validade_ate)
            .distinct(AfericaoBalanca.balanca_fisica_id)
            .where(AfericaoBalanca.tenant_id == tenant_id)
            .order_by(AfericaoBalanca.balanca_fisica_id, AfericaoBalanca.data_afericao.desc())
            .subquery()
        )
        stmt = (
            select(BalancaFisica.id, BalancaFisica.nome, ultima_afericao.c.validade_ate)
            .join(ultima_afericao, ultima_afericao.c.balanca_fisica_id == BalancaFisica.id)
            .where(
                BalancaFisica.tenant_id == tenant_id,
                BalancaFisica.ativa == True,  # noqa: E712
                ultima_afericao.c.validade_ate.isnot(None),
                ultima_afericao.c.validade_ate < agora,
            )
            .limit(20)
        )
        result = await session.execute(stmt)
        vencidas = result.all()

        if vencidas:
            itens = [f"{row.nome} (venceu {row.validade_ate.date().isoformat()})" for row in vencidas]
            alertas.append(
                NotificacaoCreate(
                    tipo="AFERICAO_BALANCA_VENCIDA",
                    titulo=f"{len(vencidas)} balança(s) com aferição vencida",
                    mensagem="Balanças: " + ", ".join(itens[:5]) + ("..." if len(itens) > 5 else ""),
                    origem="balanca_fisica",
                    origem_id=str(tenant_id),
                    meta={
                        "quantidade": len(vencidas),
                        "balancas": [
                            {"id": str(row.id), "nome": row.nome, "validade_ate": row.validade_ate.isoformat()}
                            for row in vencidas
                        ],
                    },
                )
            )
            await self._espelhar_operational_alert(
                session,
                tenant_id,
                dedupe_key=f"notificacoes:afericao_balanca_vencida:{tenant_id}",
                source_type="AFERICAO_BALANCA_VENCIDA",
                source_id=str(tenant_id),
                title=f"{len(vencidas)} balança(s) com aferição vencida",
                message="Balanças: " + ", ".join(itens[:5]) + ("..." if len(itens) > 5 else ""),
            )

        return alertas

    @staticmethod
    async def _espelhar_operational_alert(
        session: AsyncSession,
        tenant_id: UUID,
        *,
        dedupe_key: str,
        source_type: str,
        source_id: str,
        title: str,
        message: str,
        category_compliance: bool = False,
        domain_finance: bool = False,
    ) -> None:
        """Espelha um alerta nativo de AlertasEngine em `operational_alerts`, para
        aparecer no resumo do dashboard (`GET /alerts/summary`) — fecha a assimetria
        com `alert_engine`, que já espelha na direção oposta (ver
        `AlertLifecycleService._notificar_usuarios`). `notify=False` porque a
        `Notificacao` já foi/será criada por este mesmo motor, via `svc.criar_e_push`
        — sem isso duplicaria a notificação no sino.
        """
        from alert_engine.models import AlertStatus, Category, Domain, Priority, Severity, TriggerType
        from alert_engine.schemas import OperationalAlertCreate
        from alert_engine.service import AlertLifecycleService

        try:
            svc = AlertLifecycleService(session, tenant_id)
            await svc.create_or_update_alert(
                OperationalAlertCreate(
                    tenant_id=tenant_id,
                    domain=Domain.FINANCE if domain_finance else Domain.OPERATIONS,
                    category=Category.COMPLIANCE if category_compliance else Category.OPERACIONAL,
                    title=title,
                    message=message,
                    severity=Severity.WARNING,
                    priority=Priority.HIGH,
                    status=AlertStatus.OPEN,
                    trigger_type=TriggerType.RULE,
                    source_type=source_type,
                    source_id=source_id,
                    source_event_ids=[],
                    source_indicator_ids=[],
                    dedupe_key=dedupe_key,
                ),
                notify=False,
            )
        except Exception as exc:  # pragma: no cover - defensive isolation
            logger.exception(f"Falha ao espelhar {source_type} em operational_alerts: {exc}")


# =============================================================================
# EXECUÇÃO MANUAL / CLI
# =============================================================================

async def main():
    """Executa o motor de alertas manualmente."""
    logger.info("Iniciando motor de alertas automáticos...")

    engine = AlertasEngine()
    resultados = await engine.verificar_todos_tenants()

    logger.info(f"✓ Tenants verificados: {resultados['tenants_verificados']}")
    logger.info(f"✓ Alertas gerados: {resultados['alertas_gerados']}")
    logger.info(f"✗ Erros: {resultados['erros']}")

    return resultados


if __name__ == "__main__":
    asyncio.run(main())
