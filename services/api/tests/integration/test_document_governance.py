"""Integração de governanca documental territorial/fundiaria."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from imoveis.models.imovel import MetodoAvaliacaoImovel, StatusDocumento, TipoDocumento
from imoveis.services.avaliacao_service import AvaliacaoService
from imoveis.services.documento_service import DocumentoLegalService


def _mock_result(one=None, items=None):
    result = MagicMock()
    result.scalar_one_or_none.return_value = one
    result.scalars.return_value.all.return_value = items or []
    return result


@pytest.mark.asyncio
async def test_documento_legal_service_consome_imovel_rural_como_fonte_oficial():
    tenant_id = uuid.uuid4()
    imovel_id = uuid.uuid4()
    session = AsyncMock()
    session.get.return_value = SimpleNamespace(id=imovel_id, tenant_id=tenant_id, deleted_at=None)
    session.execute.side_effect = [_mock_result(one=None)]
    session.add = MagicMock()
    session.flush = AsyncMock()

    service = DocumentoLegalService(session)
    documento, alertas = await service.criar_documento(
        tenant_id=tenant_id,
        imovel_id=imovel_id,
        tipo=TipoDocumento.CAR,
        path_storage="/docs/car.pdf",
        nome_arquivo="car.pdf",
        tamanho_bytes=128,
        conteudo_bytes=b"car",
        descricao="CAR consolidado",
        numero_documento="CAR-001",
        data_emissao=date(2026, 1, 1),
        data_vencimento=None,
        restrito=False,
        created_by=None,
    )

    assert documento.tenant_id == tenant_id
    assert documento.imovel_id == imovel_id
    assert documento.status == StatusDocumento.ATIVO
    assert documento.tipo == TipoDocumento.CAR
    assert documento.path_storage == "/docs/car.pdf"
    assert alertas == []


@pytest.mark.asyncio
async def test_avaliacao_service_consome_imovel_rural_como_fonte_patrimonial():
    tenant_id = uuid.uuid4()
    imovel_id = uuid.uuid4()
    session = AsyncMock()
    session.execute.return_value = _mock_result(
        one=SimpleNamespace(id=imovel_id, area_total_ha=Decimal("100.0000"), nome="Imovel A", municipio="Sorriso", uf="MT")
    )
    session.add = MagicMock()

    service = AvaliacaoService(session)
    avaliacao, alertas = await service.criar_avaliacao(
        tenant_id=tenant_id,
        imovel_id=imovel_id,
        data_avaliacao=date(2026, 6, 21),
        metodo=MetodoAvaliacaoImovel.DECLARADO,
        valor_total=Decimal("100000.00"),
        valor_por_hectare=None,
        valor_terra_nua=None,
        valor_benfeitorias=None,
        valor_lavoura_perene=None,
        moeda="BRL",
        responsavel="Avaliador",
        numero_laudo="LAUDO-01",
        observacoes="Governanca documental",
        anexos=[],
        created_by=uuid.uuid4(),
    )

    assert avaliacao.tenant_id == tenant_id
    assert avaliacao.imovel_id == imovel_id
    assert avaliacao.valor_total == Decimal("100000.00")
    assert alertas == ["Avaliação patrimonial criada"]

