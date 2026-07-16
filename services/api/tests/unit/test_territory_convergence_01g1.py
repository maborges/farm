import pytest
import uuid
import csv
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from scripts.resolve_territory_legacy import apply_decision, resolve_batch
from core.models.unidade_produtiva import UnidadeProdutiva
from core.cadastros.propriedades.propriedade_models import Propriedade, ExploracaoRural
from imoveis.models.imovel import ImovelRural
from core.cadastros.propriedade_imovel.models import PropriedadeImovel

@pytest.fixture
def mock_record():
    return {
        "tenant_id": str(uuid.uuid4()),
        "unidade_produtiva_id": str(uuid.uuid4()),
        "imovel_rural_id": str(uuid.uuid4()),
        "action": "LINK_EXISTING_PROPERTY",
        "propriedade_id": str(uuid.uuid4()),
        "tipo_exploracao": "PROPRIA",
        "data_inicio": "2024-01-01",
        "nome_nova_propriedade": "",
        "justification": "Test",
        "reviewed_by": "pytest"
    }

@pytest.mark.asyncio
async def test_skip_action(mock_record):
    mock_record["action"] = "SKIP"
    result = await apply_decision(None, mock_record)
    assert result == "SKIPPED"

@pytest.mark.asyncio
async def test_missing_ids(mock_record):
    mock_record["tenant_id"] = ""
    with pytest.raises(ValueError, match="obrigatórios"):
        await apply_decision(None, mock_record)

@pytest.mark.asyncio
async def test_create_property_requires_fields(mock_record):
    mock_record["action"] = "CREATE_PROPERTY"
    mock_record["nome_nova_propriedade"] = ""
    with pytest.raises(ValueError, match="requer nome_nova_propriedade"):
        await apply_decision(None, mock_record)

@pytest.mark.asyncio
async def test_invalid_action(mock_record):
    mock_record["action"] = "INVALID"
    with pytest.raises(ValueError, match="desconhecida"):
        await apply_decision(None, mock_record)

def test_csv_parser(tmp_path):
    csv_path = tmp_path / "test.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["tenant_id", "unidade_produtiva_id", "imovel_rural_id", "action"])
        writer.writeheader()
        writer.writerow({
            "tenant_id": "123",
            "unidade_produtiva_id": "456",
            "imovel_rural_id": "789",
            "action": "SKIP"
        })
    assert csv_path.exists()
