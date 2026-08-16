import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.cultivos.models import Cultivo
from agricola.custos.constants import DEPRECIACAO_EQUIPAMENTO
from agricola.custos.models import CostAllocation
from agricola.production_units.models import ProductionUnit
from agricola.safras.models import Safra
from core.cadastros.equipamentos.models import CategoriaPatrimonial, Equipamento
from core.services.depreciacao_service import calcular_valor_mensal, lancar_depreciacao_mensal
import financeiro.models.rateio  # noqa: F401 — necessário p/ resolver FK cost_allocations.fin_rateio_id
import imoveis.models.imovel  # noqa: F401
import agricola.operacoes.models  # noqa: F401 — necessário p/ resolver FK cost_allocations.operation_execution_id


class TestCalcularValorMensal:
    def test_caso_normal(self):
        valor = calcular_valor_mensal(120_000, 12_000, 10)
        assert valor == Decimal("900")

    def test_sem_vida_util_retorna_zero(self):
        assert calcular_valor_mensal(120_000, 0, None) == Decimal("0")
        assert calcular_valor_mensal(120_000, 0, 0) == Decimal("0")

    def test_sem_valor_aquisicao_retorna_zero(self):
        assert calcular_valor_mensal(None, 0, 10) == Decimal("0")

    def test_residual_maior_que_aquisicao_nao_gera_negativo(self):
        assert calcular_valor_mensal(10_000, 50_000, 5) == Decimal("0")

    def test_sem_residual(self):
        valor = calcular_valor_mensal(60_000, None, 5)
        assert valor == Decimal("1000")


@pytest.mark.asyncio
async def test_lancar_depreciacao_mensal_idempotente(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    talhao_id: uuid.UUID,
):
    """Cria um equipamento depreciável ligado a uma UP com ProductionUnit ativa,
    roda o lançamento 2x e confirma que apenas 1 CostAllocation foi criado."""
    safra = Safra(id=uuid.uuid4(), tenant_id=tenant_id, ano_safra="2025/26", cultura="SOJA", status="COLHEITA")
    session.add(safra)
    cultivo = Cultivo(tenant_id=tenant_id, safra_id=safra.id, cultura="SOJA", status="ATIVO")
    session.add(cultivo)
    await session.flush()
    session.add(ProductionUnit(
        tenant_id=tenant_id,
        safra_id=safra.id,
        cultivo_id=cultivo.id,
        area_id=talhao_id,
        percentual_participacao=100,
        area_ha=100.0,
        status="ATIVA",
    ))

    equipamento = Equipamento(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        tipo="TRATOR",
        nome="Trator Teste Depreciação",
        categoria_patrimonial=CategoriaPatrimonial.ATIVO_DEPRECIAVEL.value,
        valor_aquisicao=120_000.0,
        valor_residual=12_000.0,
        vida_util_anos=10,
    )
    session.add(equipamento)
    await session.commit()

    # Nota: o tenant_id fixo de teste (fixture compartilhada) pode acumular outros
    # equipamentos/CostAllocations de testes anteriores que fizeram commit direto no
    # banco — por isso a verificação de idempotência é feita de forma isolada, filtrando
    # por source_id do equipamento criado neste teste, e não pelos contadores agregados.
    await lancar_depreciacao_mensal(session, tenant_id=tenant_id)
    await lancar_depreciacao_mensal(session, tenant_id=tenant_id)

    stmt = select(CostAllocation).where(
        CostAllocation.source == DEPRECIACAO_EQUIPAMENTO,
        CostAllocation.source_id == equipamento.id,
    )
    resultado = (await session.execute(stmt)).scalars().all()
    assert len(resultado) == 1
    assert resultado[0].amount == Decimal("900.00")
