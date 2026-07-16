import pytest
import uuid
from datetime import date
from unittest.mock import AsyncMock, patch, MagicMock

from core.cadastros.propriedade_imovel.service import PropriedadeImovelService
from core.cadastros.propriedade_imovel.models import TipoVinculoPropriedadeImovel, PropriedadeImovel
from core.exceptions import BusinessRuleError

class MockVinculo:
    def __init__(self, id, propriedade_id, imovel_rural_id, tipo_vinculo, vinculo_principal, ativo=True, data_fim=None):
        self.id = id
        self.propriedade_id = propriedade_id
        self.imovel_rural_id = imovel_rural_id
        self.tipo_vinculo = tipo_vinculo
        self.vinculo_principal = vinculo_principal
        self.ativo = ativo
        self.data_inicio = date.today()
        self.data_fim = data_fim

@pytest.mark.asyncio
async def test_primeiro_vinculo_criado_como_principal():
    session_mock = AsyncMock()
    service = PropriedadeImovelService(session_mock, uuid.uuid4())
    
    with patch.object(service, '_buscar_principal_ativo', return_value=None), \
         patch.object(service, '_validar_referencias', return_value=None):
         
        result_mock = MagicMock()
        result_mock.scalars().first.return_value = None
        session_mock.execute.return_value = result_mock
        
        vinculo = await service.garantir_vinculo_ativo(
            propriedade_id=uuid.uuid4(),
            imovel_rural_id=uuid.uuid4(),
            tipo_vinculo=None
        )
        
        assert vinculo.vinculo_principal is True
        assert vinculo.tipo_vinculo == TipoVinculoPropriedadeImovel.PROPRIEDADE_PRINCIPAL.value

@pytest.mark.asyncio
async def test_segundo_vinculo_criado_como_secundario():
    session_mock = AsyncMock()
    service = PropriedadeImovelService(session_mock, uuid.uuid4())
    
    prop_id = uuid.uuid4()
    principal_ativo = MockVinculo(uuid.uuid4(), prop_id, uuid.uuid4(), TipoVinculoPropriedadeImovel.PROPRIEDADE_PRINCIPAL.value, True)
    
    with patch.object(service, '_buscar_principal_ativo', return_value=principal_ativo), \
         patch.object(service, '_validar_referencias', return_value=None):
         
        result_mock = MagicMock()
        result_mock.scalars().first.return_value = None
        session_mock.execute.return_value = result_mock
        
        vinculo = await service.garantir_vinculo_ativo(
            propriedade_id=prop_id,
            imovel_rural_id=uuid.uuid4(),
            tipo_vinculo=None
        )
        
        assert vinculo.vinculo_principal is False
        assert vinculo.tipo_vinculo == TipoVinculoPropriedadeImovel.PROPRIEDADE_SECUNDARIA.value

@pytest.mark.asyncio
async def test_troca_explicita_de_principal():
    session_mock = AsyncMock()
    service = PropriedadeImovelService(session_mock, uuid.uuid4())
    
    prop_id = uuid.uuid4()
    vinculo_novo_id = uuid.uuid4()
    
    principal_ativo = MockVinculo(uuid.uuid4(), prop_id, uuid.uuid4(), TipoVinculoPropriedadeImovel.PROPRIEDADE_PRINCIPAL.value, True)
    secundario_atual = MockVinculo(vinculo_novo_id, prop_id, uuid.uuid4(), TipoVinculoPropriedadeImovel.PROPRIEDADE_SECUNDARIA.value, False)
    
    with patch.object(service, 'obter', return_value=secundario_atual), \
         patch.object(service, '_buscar_principal_ativo', return_value=principal_ativo):
         
        novo_principal = await service.definir_vinculo_principal(prop_id, vinculo_novo_id)
        
        assert principal_ativo.vinculo_principal is False
        assert principal_ativo.tipo_vinculo == TipoVinculoPropriedadeImovel.PROPRIEDADE_SECUNDARIA.value
        
        assert novo_principal.vinculo_principal is True
        assert novo_principal.tipo_vinculo == TipoVinculoPropriedadeImovel.PROPRIEDADE_PRINCIPAL.value
        
        session_mock.flush.assert_called_once()
