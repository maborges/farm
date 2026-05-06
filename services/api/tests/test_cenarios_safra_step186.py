import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from financeiro.services.cenario_service import CenarioFinanceiroService
from financeiro.schemas.cenario_schema import CenarioSafraCreate
from agricola.safras.models import Safra
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_cenario_service_fluxo_completo(session: AsyncSession, tenant_id: uuid.UUID):
    """Testa o fluxo completo do serviço de cenários (Salvar, Listar, Deletar)."""
    # Setup: Criar uma safra vinculada ao tenant de teste
    safra = Safra(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        ano_safra="2026/26",
        cultura="SOJA",
        status="PLANEJAMENTO"
    )
    session.add(safra)
    await session.commit()

    svc = CenarioFinanceiroService(session, tenant_id)

    # 1. Salvar Cenário
    data = CenarioSafraCreate(
        safra_id=safra.id,
        nome="Cenário Otimista",
        receita_percentual=15.0,
        custos_percentual=-10.0,
        resultado_simulado=250000.0,
        margem_simulada=32.5
    )
    
    cenario = await svc.salvar(data)
    assert cenario.nome == "Cenário Otimista"
    assert cenario.tenant_id == tenant_id
    assert cenario.safra_id == safra.id

    # 2. Listar Cenários
    lista = await svc.listar(safra.id)
    assert len(lista) == 1
    assert lista[0].id == cenario.id

    # 3. Deletar Cenário
    await svc.deletar(cenario.id)
    lista_vazia = await svc.listar(safra.id)
    assert len(lista_vazia) == 0


@pytest.mark.asyncio
async def test_cenario_service_validacao_safra_tenant(session: AsyncSession, tenant_id: uuid.UUID, outro_tenant_id: uuid.UUID):
    """Garante que não é possível salvar cenário para safra de outro tenant."""
    # Setup: Safra de OUTRO tenant (usando fixture para evitar violação de FK)
    safra_alheia = Safra(
        id=uuid.uuid4(),
        tenant_id=outro_tenant_id,
        ano_safra="2026/26",
        cultura="MILHO"
    )
    session.add(safra_alheia)
    await session.commit()

    svc = CenarioFinanceiroService(session, tenant_id)

    data = CenarioSafraCreate(
        safra_id=safra_alheia.id,
        nome="Cenário Hacker",
        receita_percentual=100.0,
        custos_percentual=0.0,
        resultado_simulado=1000000.0,
        margem_simulada=100.0
    )

    with pytest.raises(HTTPException) as excinfo:
        await svc.salvar(data)
    
    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "Safra não encontrada"
