import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

from core.services.territory_read_service import TerritoryReadService
from core.models.unidade_produtiva import UnidadeProdutiva
from core.cadastros.propriedades.propriedade_models import ExploracaoRural, Propriedade
from core.cadastros.propriedade_imovel.models import PropriedadeImovel
from imoveis.models.imovel import ImovelRural

class MockQueryBuilder:
    def __init__(self, items):
        self.items = items
    def scalars(self):
        return self
    def all(self):
        return self.items

@pytest.mark.asyncio
async def test_territory_read_service_canonical_source():
    session_mock = AsyncMock()
    tenant_id = uuid.uuid4()
    svc = TerritoryReadService(session_mock, tenant_id)
    
    up_id = uuid.uuid4()
    prop_id = uuid.uuid4()
    imovel_id = uuid.uuid4()
    
    up = UnidadeProdutiva(id=up_id, tenant_id=tenant_id)
    expl = ExploracaoRural(id=uuid.uuid4(), unidade_produtiva_id=up_id, propriedade_id=prop_id, tenant_id=tenant_id)
    prop = Propriedade(id=prop_id, tenant_id=tenant_id, nome="Fazenda Ouro")
    assoc = PropriedadeImovel(id=uuid.uuid4(), propriedade_id=prop_id, imovel_rural_id=imovel_id, tenant_id=tenant_id, ativo=True, vinculo_principal=True)
    imovel = ImovelRural(id=imovel_id, tenant_id=tenant_id, nome="Sítio Prata", nirf="123")
    
    # Mocking the session execute calls which happen in sequence
    session_mock.execute.side_effect = [
        MockQueryBuilder([up]),
        MockQueryBuilder([expl]),
        MockQueryBuilder([prop]),
        MockQueryBuilder([assoc]),
        MockQueryBuilder([imovel])
    ]
    
    res = await svc.obter_visao_territorial_da_unidade(up_id)
    
    assert res is not None
    assert res.fonte_da_leitura == "CANONICAL_PROPERTY_ASSOCIATION"
    assert res.estado_de_convergencia == "CANONICAL"
    assert res.imovel_principal["nirf"] == "123"



@pytest.mark.asyncio
async def test_territory_read_service_multiple_imoveis():
    session_mock = AsyncMock()
    tenant_id = uuid.uuid4()
    svc = TerritoryReadService(session_mock, tenant_id)
    
    up_id = uuid.uuid4()
    prop_id = uuid.uuid4()
    imovel1_id = uuid.uuid4()
    imovel2_id = uuid.uuid4()
    
    up = UnidadeProdutiva(id=up_id, tenant_id=tenant_id)
    expl = ExploracaoRural(id=uuid.uuid4(), unidade_produtiva_id=up_id, propriedade_id=prop_id, tenant_id=tenant_id)
    prop = Propriedade(id=prop_id, tenant_id=tenant_id, nome="Fazenda Multi")
    assoc1 = PropriedadeImovel(id=uuid.uuid4(), propriedade_id=prop_id, imovel_rural_id=imovel1_id, tenant_id=tenant_id, ativo=True, vinculo_principal=True)
    assoc2 = PropriedadeImovel(id=uuid.uuid4(), propriedade_id=prop_id, imovel_rural_id=imovel2_id, tenant_id=tenant_id, ativo=True, vinculo_principal=False)
    imovel1 = ImovelRural(id=imovel1_id, tenant_id=tenant_id, nome="Sítio A", nirf="111")
    imovel2 = ImovelRural(id=imovel2_id, tenant_id=tenant_id, nome="Sítio B", nirf="222")
    
    session_mock.execute.side_effect = [
        MockQueryBuilder([up]),
        MockQueryBuilder([expl]),
        MockQueryBuilder([prop]),
        MockQueryBuilder([assoc1, assoc2]),
        MockQueryBuilder([imovel1, imovel2])
    ]
    
    res = await svc.obter_visao_territorial_da_unidade(up_id)
    
    assert res is not None
    assert res.fonte_da_leitura == "CANONICAL_PROPERTY_ASSOCIATION"
    assert res.estado_de_convergencia == "CANONICAL"
    assert res.imovel_principal["nirf"] == "111"
    assert len(res.imoveis_secundarios) == 1
    assert res.imoveis_secundarios[0]["nirf"] == "222"
