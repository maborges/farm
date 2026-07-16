import pytest
import uuid
from decimal import Decimal
from core.schemas.cadastro_completo_input import CadastroCompletoCreate, CadastroCompletoUpdate

@pytest.mark.asyncio
async def test_bypass_inacessivel_externamente():
    dados = CadastroCompletoCreate(
        nome="Teste",
        tipo_propriedade="fazenda",
        ativo=True,
    )
    
    assert not hasattr(dados, "_bypass_sincronismo")


