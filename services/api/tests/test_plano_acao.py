"""Testes de criação, deduplicação e mudança de status do Plano de Ação."""
import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from financeiro.services.plano_acao_service import PlanoAcaoService
from financeiro.models.plano_acao import PlanoAcaoItem
from financeiro.schemas.lancamento_schema import ItemPlanoAcao
from core.exceptions import BusinessRuleError


def _make_sugestao(tipo: str, prioridade: str = "ALTA") -> ItemPlanoAcao:
    return ItemPlanoAcao(
        id=tipo.lower(),
        tipo=tipo.upper(),
        titulo=f"Título {tipo}",
        descricao=f"Descrição {tipo}",
        prioridade=prioridade,
        status="PENDENTE",
        rota=f"/financeiro/{tipo.lower()}",
    )


def _make_item(tipo: str, status: str = "PENDENTE", tenant_id: uuid.UUID | None = None) -> PlanoAcaoItem:
    item = PlanoAcaoItem()
    item.id = uuid.uuid4()
    item.tenant_id = tenant_id or uuid.uuid4()
    item.safra_id = uuid.uuid4()
    item.tipo = tipo
    item.titulo = f"Título {tipo}"
    item.descricao = f"Descrição {tipo}"
    item.prioridade = "ALTA"
    item.status = status
    item.rota = f"/financeiro/{tipo.lower()}"
    item.origem = "AUTO"
    item.concluido_at = None
    item.ignorado_at = None
    return item


def _mock_execute(rows: list):
    """Cria um AsyncMock que imita session.execute().scalars().all()"""
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = rows
    scalars_mock.scalar_one_or_none.return_value = rows[0] if rows else None
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    result_mock.scalar_one_or_none.return_value = rows[0] if rows else None
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)
    return session


@pytest.mark.asyncio
async def test_sincronizar_cria_novos_itens():
    """Deve criar itens para sugestões sem registro anterior."""
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    session = _mock_execute([])  # sem existentes

    svc = PlanoAcaoService(session, tenant_id)
    sugestoes = [_make_sugestao("REVISAR_CUSTOS"), _make_sugestao("ANALISAR_INSUMOS")]

    with patch("financeiro.services.plano_acao_service.LancamentoService") as MockSvc:
        MockSvc.return_value.gerar_plano_acao = AsyncMock(return_value=sugestoes)
        with patch.object(svc, "listar", AsyncMock(return_value=[])):
            await svc.sincronizar(safra_id)

    assert session.add.call_count == 2


@pytest.mark.asyncio
async def test_sincronizar_nao_duplica_tipo_pendente():
    """Não deve criar novo item se tipo já existe com status PENDENTE."""
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    existente = _make_item("REVISAR_CUSTOS", status="PENDENTE", tenant_id=tenant_id)
    session = _mock_execute([existente])

    svc = PlanoAcaoService(session, tenant_id)
    sugestoes = [_make_sugestao("REVISAR_CUSTOS")]

    with patch("financeiro.services.plano_acao_service.LancamentoService") as MockSvc:
        MockSvc.return_value.gerar_plano_acao = AsyncMock(return_value=sugestoes)
        with patch.object(svc, "listar", AsyncMock(return_value=[existente])):
            await svc.sincronizar(safra_id)

    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_atualizar_status_concluida():
    """Deve marcar item como CONCLUIDA e preencher concluido_at."""
    tenant_id = uuid.uuid4()
    item = _make_item("REVISAR_CUSTOS", status="PENDENTE", tenant_id=tenant_id)
    session = _mock_execute([item])

    svc = PlanoAcaoService(session, tenant_id)
    result = await svc.atualizar_status(item.id, "CONCLUIDA")

    assert result.status == "CONCLUIDA"
    assert result.concluido_at is not None


@pytest.mark.asyncio
async def test_atualizar_status_ignorada():
    """Deve marcar item como IGNORADA e preencher ignorado_at."""
    tenant_id = uuid.uuid4()
    item = _make_item("ANALISAR_INSUMOS", status="PENDENTE", tenant_id=tenant_id)
    session = _mock_execute([item])

    svc = PlanoAcaoService(session, tenant_id)
    result = await svc.atualizar_status(item.id, "IGNORADA")

    assert result.status == "IGNORADA"
    assert result.ignorado_at is not None


@pytest.mark.asyncio
async def test_atualizar_status_invalido():
    """Status inválido deve lançar BusinessRuleError."""
    session = _mock_execute([])
    svc = PlanoAcaoService(session, uuid.uuid4())

    with pytest.raises(BusinessRuleError):
        await svc.atualizar_status(uuid.uuid4(), "INVALIDO")
