import uuid
from datetime import date as _date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.exceptions import BusinessRuleError
from financeiro.models.lancamento import LancamentoFinanceiro
from financeiro.models.despesa import Despesa
from financeiro.models.plano_conta import PlanoConta

class LancamentoOperacionalService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def registrar_uso_insumo(
        self,
        safra_id: uuid.UUID,
        nome_produto: str,
        valor: float,
        movimentacao_id: uuid.UUID | None = None,
    ) -> None:
        """Cria um lançamento de custo de uso de insumos."""
        if valor <= 0:
            return

        # Idempotência
        if movimentacao_id is not None:
            stmt_dup = select(LancamentoFinanceiro.id).where(
                LancamentoFinanceiro.tenant_id == self.tenant_id,
                LancamentoFinanceiro.origem == "ESTOQUE",
                LancamentoFinanceiro.origem_id == movimentacao_id,
            ).limit(1)
            if (await self.session.execute(stmt_dup)).first():
                return

        lancamento = LancamentoFinanceiro(
            tenant_id=self.tenant_id,
            safra_id=safra_id,
            descricao=f"Uso de insumo: {nome_produto}",
            valor=valor,
            data=_date.today(),
            tipo="CUSTO",
            categoria="INSUMOS",
            origem="ESTOQUE",
            origem_id=movimentacao_id,
        )
        self.session.add(lancamento)

    async def registrar_despesa_manutencao(
        self,
        unidade_produtiva_id: uuid.UUID,
        safra_id: uuid.UUID | None,
        numero_os: str,
        nome_equipamento: str,
        valor: float,
        origem_id: uuid.UUID,
        cultivo_id: uuid.UUID | None = None,
    ) -> Despesa | None:
        """Cria uma despesa associada à manutenção."""
        if valor <= 0:
            return None

        stmt_pc = (
            select(PlanoConta.id)
            .where(
                PlanoConta.tenant_id == self.tenant_id,
                PlanoConta.categoria_rfb == "CUSTEIO",
                PlanoConta.natureza == "ANALITICA",
                PlanoConta.ativo == True,
            )
            .limit(1)
        )
        plano_id = (await self.session.execute(stmt_pc)).scalar()
        if not plano_id:
            return None

        hoje = _date.today()
        despesa = Despesa(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            plano_conta_id=plano_id,
            cultivo_id=cultivo_id,
            descricao=f"Manutenção — {numero_os}: {nome_equipamento}",
            valor_total=valor,
            data_emissao=hoje,
            data_vencimento=hoje,
            data_pagamento=hoje,
            status="PAGO",
            origem_id=origem_id,
            origem_tipo="ORDEM_SERVICO",
        )
        self.session.add(despesa)
        await self.session.flush()
        return despesa

    async def registrar_despesa_abastecimento(
        self,
        unidade_produtiva_id: uuid.UUID,
        nome_equipamento: str,
        litros: float,
        valor_total: float,
        origem_id: uuid.UUID,
    ) -> Despesa | None:
        """Cria uma despesa associada a abastecimento externo."""
        if valor_total <= 0:
            return None

        stmt_pc = (
            select(PlanoConta.id)
            .where(
                PlanoConta.tenant_id == self.tenant_id,
                PlanoConta.nome.ilike("%Combustível%"),
                PlanoConta.natureza == "ANALITICA",
                PlanoConta.ativo == True,
            )
            .limit(1)
        )
        plano_id = (await self.session.execute(stmt_pc)).scalar()
        
        if not plano_id:
            return None

        hoje = _date.today()
        despesa = Despesa(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            plano_conta_id=plano_id,
            descricao=f"Abastecimento Externo — {nome_equipamento} ({litros}L)",
            valor_total=valor_total,
            data_emissao=hoje,
            data_vencimento=hoje,
            data_pagamento=hoje,
            status="PAGO",
            origem_id=origem_id,
            origem_tipo="ABASTECIMENTO",
        )
        self.session.add(despesa)
        await self.session.flush()
        return despesa
