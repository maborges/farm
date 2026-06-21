"""Integração de compatibilidade para a convergência territorial/fundiária."""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.cadastros.propriedade_imovel.models import TipoVinculoPropriedadeImovel
from core.cadastros.propriedade_imovel.schemas import PropriedadeImovelCreate, PropriedadeImovelRead
from core.cadastros.propriedade_imovel.service import PropriedadeImovelService
from core.cadastros.propriedades.propriedade_service import ExploracaoRuralService
from imoveis.services.imovel_service import ImovelService


def _mock_result(items=None, one=None):
    result = MagicMock()
    result.scalars.return_value.all.return_value = items or []
    result.scalar_one_or_none.return_value = one
    return result


@pytest.mark.asyncio
async def test_fluxos_legados_propriedades_e_imoveis_permanecem_independentes():
    tenant_id = uuid.uuid4()

    propriedade_session = AsyncMock()
    propriedade_session.execute.return_value = _mock_result(
        one=SimpleNamespace(id=uuid.uuid4(), tenant_id=tenant_id, nome="Fazenda", ativo=True)
    )
    propriedade_session.add = MagicMock()
    propriedade_session.flush = AsyncMock()

    exploracao_service = ExploracaoRuralService(propriedade_session, tenant_id)
    await exploracao_service.listar_por_propriedade(uuid.uuid4())

    imovel_session = AsyncMock()
    imovel_session.execute.return_value = _mock_result(
        items=[SimpleNamespace(id=uuid.uuid4(), nome="Imóvel 1", situacao="pendente")]
    )
    imovel_service = ImovelService(imovel_session)
    imoveis = await imovel_service.get_imoveis_by_fazenda(uuid.uuid4(), tenant_id)

    assert len(imoveis) == 1
    assert imoveis[0].nome == "Imóvel 1"
    assert hasattr(exploracao_service, "criar")
    assert hasattr(imovel_service, "criar_imovel")


@pytest.mark.asyncio
async def test_vinculo_canonico_preserva_tenant_isolation_e_resposta_nestada():
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    propriedade_id = uuid.uuid4()
    imovel_id = uuid.uuid4()

    session.execute.side_effect = [
        _mock_result(one=SimpleNamespace(id=propriedade_id, ativo=True)),
        _mock_result(one=SimpleNamespace(id=imovel_id, deleted_at=None)),
        _mock_result(items=[]),
    ]
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    service = PropriedadeImovelService(session, tenant_id)
    payload = PropriedadeImovelCreate(
        propriedade_id=propriedade_id,
        imovel_rural_id=imovel_id,
        tipo_vinculo=TipoVinculoPropriedadeImovel.ARRENDAMENTO,
        ativo=True,
        data_inicio=date(2026, 1, 1),
        origem_documental="Contrato validado",
        observacoes="Compatibilidade",
        area_vinculada=Decimal("12.5"),
        percentual_vinculado=Decimal("10"),
        vinculo_principal=False,
    )

    vinculo = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        propriedade_id=propriedade_id,
        imovel_rural_id=imovel_id,
        tipo_vinculo=TipoVinculoPropriedadeImovel.ARRENDAMENTO.value,
        ativo=True,
        data_inicio=date(2026, 1, 1),
        data_fim=None,
        origem_documental="Contrato validado",
        observacoes="Compatibilidade",
        area_vinculada=Decimal("12.5"),
        percentual_vinculado=Decimal("10"),
        vinculo_principal=False,
        origem_referencia=None,
        status_documental=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        created_by=None,
        updated_by=None,
        propriedade=SimpleNamespace(id=propriedade_id, nome="Fazenda", ativo=True),
        imovel_rural=SimpleNamespace(id=imovel_id, nome="Imóvel 1", municipio="Sorriso", uf="MT"),
    )

    async def _refresh(obj):
        return None

    session.refresh.side_effect = _refresh

    # Evita revalidar principalidade para o cenário secundário
    service._validar_principalidade = AsyncMock(return_value=None)
    session.execute.side_effect = [
        _mock_result(one=SimpleNamespace(id=propriedade_id, ativo=True)),
        _mock_result(one=SimpleNamespace(id=imovel_id, deleted_at=None)),
    ]

    resultado = await service.criar(payload, usuario_id=uuid.uuid4())
    assert resultado.tenant_id == tenant_id

    read_model = PropriedadeImovelRead.model_validate(vinculo)
    assert read_model.propriedade.nome == "Fazenda"
    assert read_model.imovel_rural.nome == "Imóvel 1"
