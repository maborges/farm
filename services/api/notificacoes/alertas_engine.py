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
            # Buscar todos os tenants com assinatura ativa
            stmt = (
                select(Tenant)
                .join(AssinaturaTenant, AssinaturaTenant.tenant_id == Tenant.id)
                .where(
                    Tenant.ativo == True,
                    AssinaturaTenant.status == "ATIVA",
                    AssinaturaTenant.tipo_assinatura == "GRUPO",
                )
                .distinct()
            )
            result = await session.execute(stmt)
            tenants = list(result.scalars().all())

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

            # 1. Vencimentos próximos (5 dias)
            vencimentos = await self._verificar_vencimentos(session, tenant_id)
            alertas_gerados.extend(vencimentos)

            # 2. Estoque baixo
            estoque_baixo = await self._verificar_estoque_baixo(session, tenant_id)
            alertas_gerados.extend(estoque_baixo)

            # 3. Carência de defensivos
            carencia = await self._verificar_carencia_defensivos(session, tenant_id)
            alertas_gerados.extend(carencia)

            # 4. Tarefas atrasadas
            tarefas_atrasadas = await self._verificar_tarefas_atrasadas(session, tenant_id)
            alertas_gerados.extend(tarefas_atrasadas)

            # 4.1 Diárias de RH pendentes de pagamento
            diarias_pendentes = await self._verificar_diarias_pendentes(session, tenant_id)
            alertas_gerados.extend(diarias_pendentes)

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


    async def _verificar_vencimentos(
        self, session: AsyncSession, tenant_id: UUID
    ) -> List[NotificacaoCreate]:
        """Verifica contas a pagar/receber vencendo nos próximos 5 dias."""
        from financeiro.models.despesa import Despesa
        from financeiro.models.receita import Receita

        alertas = []
        hoje = datetime.now(timezone.utc).date()
        daqui_5_dias = hoje + timedelta(days=5)

        # Despesas vencendo
        stmt = (
            select(Despesa)
            .where(
                Despesa.tenant_id == tenant_id,
                Despesa.status == "PENDENTE",
                Despesa.data_vencimento >= hoje,
                Despesa.data_vencimento <= daqui_5_dias,
            )
            .limit(10)
        )
        result = await session.execute(stmt)
        despesas = result.scalars().all()

        if despesas:
            total = sum(d.valor for d in despesas)
            alertas.append(
                NotificacaoCreate(
                    tipo="VENCIMENTO_CONTAS_PAGAR",
                    titulo=f"{len(despesas)} contas a pagar vencendo em 5 dias",
                    mensagem=f"Total: R$ {total:.2f}. Verifique o fluxo de caixa para evitar atrasos.",
                    meta={
                        "quantidade": len(despesas),
                        "total": float(total),
                        "periodo": "5 dias",
                    },
                )
            )

        # Receitas vencendo
        stmt = (
            select(Receita)
            .where(
                Receita.tenant_id == tenant_id,
                Receita.status == "PENDENTE",
                Receita.data_vencimento >= hoje,
                Receita.data_vencimento <= daqui_5_dias,
            )
            .limit(10)
        )
        result = await session.execute(stmt)
        receitas = result.scalars().all()

        if receitas:
            total = sum(r.valor for r in receitas)
            alertas.append(
                NotificacaoCreate(
                    tipo="VENCIMENTO_CONTAS_RECEBER",
                    titulo=f"{len(receitas)} contas a receber vencendo em 5 dias",
                    mensagem=f"Total: R$ {total:.2f}. Acompanhe o recebimento.",
                    meta={
                        "quantidade": len(receitas),
                        "total": float(total),
                        "periodo": "5 dias",
                    },
                )
            )

        return alertas

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
                f"{p.Produto.nome}: {p.SaldoEstoque.quantidade}/{(p.SaldoEstoque.estoque_minimo if p.SaldoEstoque.estoque_minimo is not None else p.Produto.estoque_minimo)} {p.Produto.unidade}"
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
                                "quantidade_atual": float(p.SaldoEstoque.quantidade),
                                "estoque_minimo": float(
                                    p.SaldoEstoque.estoque_minimo
                                    if p.SaldoEstoque.estoque_minimo is not None
                                    else p.Produto.estoque_minimo
                                ),
                                "unidade": p.Produto.unidade,
                            }
                            for p in produtos_baixo
                        ],
                    },
                )
            )

        return alertas

    async def _verificar_carencia_defensivos(
        self, session: AsyncSession, tenant_id: UUID
    ) -> List[NotificacaoCreate]:
        """Verifica carência de defensivos agrícolas vencendo em 24-48h."""
        from agricola.models.aplicacao import AplicacaoDefensivo

        alertas = []
        agora = datetime.now(timezone.utc)
        daqui_24h = agora + timedelta(hours=24)
        daqui_48h = agora + timedelta(hours=48)

        # Aplicações com carência vencendo em 24h
        stmt = (
            select(AplicacaoDefensivo)
            .where(
                AplicacaoDefensivo.tenant_id == tenant_id,
                AplicacaoDefensivo.data_aplicacao + AplicacaoDefensivo.carencia_dias >= agora,
                AplicacaoDefensivo.data_aplicacao + AplicacaoDefensivo.carencia_dias <= daqui_48h,
            )
            .limit(10)
        )
        result = await session.execute(stmt)
        aplicacoes = result.scalars().all()

        if aplicacoes:
            itens = [
                f"{a.defensivo_nome} (Talhão {a.talhao_nome}) - vence em {(a.data_aplicacao + timedelta(days=a.carencia_dias) - agora).days} dias"
                for a in aplicacoes
            ]
            alertas.append(
                NotificacaoCreate(
                    tipo="CARENCIA_DEFENSIVO",
                    titulo=f"{len(aplicacoes)} defensivos com carência vencendo",
                    mensagem="Atenção: " + ", ".join(itens[:3]) + ("..." if len(itens) > 3 else ""),
                    meta={
                        "quantidade": len(aplicacoes),
                        "aplicacoes": [
                            {
                                "id": str(a.id),
                                "defensivo": a.defensivo_nome,
                                "talhao": a.talhao_nome,
                                "carencia_dias": a.carencia_dias,
                                "data_fim_carencia": (a.data_aplicacao + timedelta(days=a.carencia_dias)).isoformat(),
                            }
                            for a in aplicacoes
                        ],
                    },
                )
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

        return alertas

    async def _verificar_tarefas_atrasadas(
        self, session: AsyncSession, tenant_id: UUID
    ) -> List[NotificacaoCreate]:
        """Verifica operações agrícolas atrasadas.

        Corrigido em 2026-08-14: usava `agricola.models.operacao.OperacaoCampo`,
        módulo inexistente (ModuleNotFoundError a cada execução — provavelmente
        derrubava o ciclo de alertas inteiro do tenant, já que `verificar_tenant`
        não isola falhas por sub-checagem). Model/query corretos alinhados com
        `alert_engine/generators/agricultura_generator.py::_listar_operacoes_atrasadas`,
        já em produção para esse mesmo cálculo.
        """
        from agricola.operacoes.models import OperacaoAgricola
        from core.cadastros.propriedades.models import AreaRural

        alertas = []
        hoje = datetime.now(timezone.utc).date()
        status_concluidos = ("CONCLUIDA", "CANCELADA", "REALIZADA")

        stmt = (
            select(OperacaoAgricola)
            .join(AreaRural, AreaRural.id == OperacaoAgricola.talhao_id)
            .where(
                OperacaoAgricola.tenant_id == tenant_id,
                AreaRural.tenant_id == tenant_id,
                OperacaoAgricola.data_prevista.is_not(None),
                OperacaoAgricola.status.notin_(status_concluidos),
                OperacaoAgricola.data_prevista < hoje,
            )
            .limit(10)
        )
        result = await session.execute(stmt)
        operacoes = result.scalars().all()

        if operacoes:
            nova_data = hoje + timedelta(days=3)
            atraso_medio = sum((hoje - o.data_prevista).days for o in operacoes) / len(operacoes)
            alertas.append(
                NotificacaoCreate(
                    tipo="TAREFAS_ATRASADAS",
                    titulo=f"{len(operacoes)} operações agrícolas atrasadas",
                    mensagem=f"Atraso médio: {atraso_medio:.0f} dias. Verifique o cronograma.",
                    meta={
                        "quantidade": len(operacoes),
                        "atraso_medio_dias": float(atraso_medio),
                        "acoes": [
                            {
                                "label": f"Adiar {o.descricao[:30]} +3d",
                                "acao": f"adiar_{o.id}",
                                "endpoint": f"/operacoes/{o.id}",
                                "method": "PATCH",
                                "body": {"data_prevista": nova_data.isoformat()},
                            }
                            for o in operacoes
                        ],
                        "operacoes": [
                            {
                                "id": str(o.id),
                                "descricao": o.descricao,
                                "data_prevista": o.data_prevista.isoformat(),
                                "dias_atraso": (hoje - o.data_prevista).days,
                            }
                            for o in operacoes
                        ],
                    },
                )
            )

        return alertas


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
