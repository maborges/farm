import pytest
import uuid
from ia.acoes_assistidas_service import AcaoAssistidaService
from ia.models import IAAcaoAssistidaHistorico
from sqlalchemy import select

@pytest.mark.asyncio
async def test_registrar_acao_batch(session, tenant_id):
    """Testa o registro de uma ação assistida em lote (Step 209)."""
    origem_id = uuid.uuid4()
    
    acoes_ids = [str(uuid.uuid4()) for _ in range(3)]
    parametros = {
        "acoes_ids": acoes_ids,
        "agregado": {
            "receita_percentual": 5,
            "custos_percentual": -10
        }
    }
    
    acao = await AcaoAssistidaService.registrar_acao(
        session=session,
        tenant_id=tenant_id,
        origem="PLANO_ACAO",
        tipo_acao="BATCH",
        parametros_json=parametros
    )
    
    assert acao.tipo_acao == "BATCH"
    assert acao.parametros_json["acoes_ids"] == acoes_ids
    assert acao.parametros_json["agregado"]["receita_percentual"] == 5
    
    # Verificar no banco
    stmt = select(IAAcaoAssistidaHistorico).where(IAAcaoAssistidaHistorico.id == acao.id)
    result = await session.execute(stmt)
    acao_db = result.scalar_one()
    
    assert acao_db.tipo_acao == "BATCH"

@pytest.mark.asyncio
async def test_concluir_acao_batch(session, tenant_id):
    """Testa a conclusão de uma ação em lote (Step 209)."""
    acao = await AcaoAssistidaService.registrar_acao(
        session=session,
        tenant_id=tenant_id,
        origem="PLANO_ACAO",
        tipo_acao="BATCH",
        parametros_json={"batch": True}
    )
    
    concluida = await AcaoAssistidaService.concluir_acao(
        session=session,
        acao_id=acao.id,
        tenant_id=tenant_id
    )
    
    assert concluida is True
    
    stmt = select(IAAcaoAssistidaHistorico).where(IAAcaoAssistidaHistorico.id == acao.id)
    result = await session.execute(stmt)
    acao_db = result.scalar_one()
    
    assert acao_db.concluida is True
    assert acao_db.concluida_em is not None
