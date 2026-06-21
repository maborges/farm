"""Integração de disciplina de leitura/escrita para legados territoriais."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.cadastros.propriedade_imovel.models import TipoVinculoPropriedadeImovel
from core.cadastros.propriedade_imovel.schemas import PropriedadeImovelCreate
from core.cadastros.propriedade_imovel.service import PropriedadeImovelService
from imoveis.models.imovel import MetodoAvaliacaoImovel, TipoDocumento
from imoveis.services.avaliacao_service import AvaliacaoService
from imoveis.services.documento_service import DocumentoLegalService


def _mock_result(one=None, items=None):
    result = MagicMock()
    result.scalar_one_or_none.return_value = one
    result.scalars.return_value.all.return_value = items or []
    return result


@pytest.mark.asyncio
async def test_documento_legal_service_usa_imovel_rural_como_unica_base_documental():
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
        tipo=TipoDocumento.CCIR,
        path_storage="/docs/ccir.pdf",
        nome_arquivo="ccir.pdf",
        tamanho_bytes=256,
        conteudo_bytes=b"ccir",
        descricao="CCIR vigente",
        numero_documento="CCIR-2026",
        data_emissao=date(2026, 1, 1),
        data_vencimento=date(2027, 1, 1),
        restrito=False,
        created_by=None,
    )

    assert documento.imovel_id == imovel_id
    assert documento.tenant_id == tenant_id
    assert documento.tipo == TipoDocumento.CCIR
    assert alertas == []


@pytest.mark.asyncio
async def test_avaliacao_service_usa_imovel_rural_como_base_patrimonial_unica():
    tenant_id = uuid.uuid4()
    imovel_id = uuid.uuid4()
    session = AsyncMock()
    session.execute.return_value = _mock_result(
        one=SimpleNamespace(id=imovel_id, area_total_ha=Decimal("50.0000"), nome="Imovel", municipio="Sorriso", uf="MT")
    )
    session.add = MagicMock()

    service = AvaliacaoService(session)
    avaliacao, _alertas = await service.criar_avaliacao(
        tenant_id=tenant_id,
        imovel_id=imovel_id,
        data_avaliacao=datetime(2026, 6, 21, tzinfo=timezone.utc),
        metodo=MetodoAvaliacaoImovel.DECLARADO,
        valor_total=Decimal("50000.00"),
        valor_por_hectare=None,
        valor_terra_nua=None,
        valor_benfeitorias=None,
        valor_lavoura_perene=None,
        moeda="BRL",
        responsavel=None,
        numero_laudo=None,
        observacoes="Compatibilidade documental",
        anexos=[],
        created_by=uuid.uuid4(),
    )

    assert avaliacao.imovel_id == imovel_id
    assert avaliacao.tenant_id == tenant_id


@pytest.mark.asyncio
async def test_vinculo_canonico_e_a_unica_escrita_relacional_entre_dominios():
    tenant_id = uuid.uuid4()
    propriedade_id = uuid.uuid4()
    imovel_id = uuid.uuid4()
    session = AsyncMock()
    session.execute.side_effect = [
        _mock_result(one=SimpleNamespace(id=propriedade_id, ativo=True)),
        _mock_result(one=SimpleNamespace(id=imovel_id, deleted_at=None)),
        _mock_result(items=[]),
    ]
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    service = PropriedadeImovelService(session, tenant_id)
    service._validar_principalidade = AsyncMock(return_value=None)

    vinculo = await service.criar(
        PropriedadeImovelCreate(
            propriedade_id=propriedade_id,
            imovel_rural_id=imovel_id,
            tipo_vinculo=TipoVinculoPropriedadeImovel.ARRENDAMENTO,
            ativo=True,
            data_inicio=date(2026, 1, 1),
            origem_documental="Contrato vigente",
            observacoes="Anticorrupcao",
            area_vinculada=Decimal("10.0"),
            percentual_vinculado=Decimal("20.0"),
            vinculo_principal=False,
        ),
        usuario_id=uuid.uuid4(),
    )

    assert vinculo.propriedade_id == propriedade_id
    assert vinculo.imovel_rural_id == imovel_id
    assert vinculo.tenant_id == tenant_id

