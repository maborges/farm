import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from core.exceptions import BusinessRuleError, EntityNotFoundError
from operacional.services import estoque_implantacao_service as service_module
from operacional.services.estoque_implantacao_service import EstoqueImplantacaoService


pytestmark = pytest.mark.asyncio


class DummySession:
    async def flush(self):
        return None

    async def refresh(self, _obj):
        return None

    def add(self, _obj):
        return None


def _produto(*, tenant_id: uuid.UUID, nome: str, codigo_interno: str | None = None, sku: str | None = None):
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        nome=nome,
        codigo_interno=codigo_interno,
        sku=sku,
        ativo=True,
    )


def _deposito(*, tenant_id: uuid.UUID, nome: str):
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        nome=nome,
        ativo=True,
        unidade_produtiva_id=uuid.uuid4(),
    )


async def _async_return(value):
    return value


async def _service_with_catalog(
    monkeypatch: pytest.MonkeyPatch,
    *,
    tenant_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    produtos: list[SimpleNamespace] | None = None,
    depositos: list[SimpleNamespace] | None = None,
) -> EstoqueImplantacaoService:
    active_tenant_id = tenant_id or uuid.uuid4()
    service = EstoqueImplantacaoService(DummySession(), active_tenant_id, user_id=user_id)
    monkeypatch.setattr(service, "_listar_produtos_tenant", lambda: _async_return(produtos or []))
    monkeypatch.setattr(service, "_listar_depositos_tenant", lambda: _async_return(depositos or []))
    return service


def _attach_in_memory_persistence(
    service: EstoqueImplantacaoService,
    monkeypatch: pytest.MonkeyPatch,
    *,
    produtos: list[SimpleNamespace],
    depositos: list[SimpleNamespace],
    shared_store: dict | None = None,
) -> dict:
    store = shared_store or {"sessions": {}, "items": {}, "movements": []}

    async def persist_session(sessao):
        if getattr(sessao, "id", None) is None:
            sessao.id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        sessao.criado_em = getattr(sessao, "criado_em", None) or now
        sessao.atualizado_em = now
        store["sessions"][sessao.id] = sessao

    async def persist_items(itens):
        now = datetime.now(timezone.utc)
        for item in itens:
            if getattr(item, "id", None) is None:
                item.id = uuid.uuid4()
            item.criado_em = getattr(item, "criado_em", None) or now
            item.atualizado_em = now
            store["items"][item.id] = item

    async def get_session_or_fail(sessao_id, *, for_update=False):
        sessao = store["sessions"].get(sessao_id)
        if not sessao or sessao.tenant_id != service.tenant_id:
            raise EntityNotFoundError("Sessao de implantacao nao encontrada.")
        return sessao

    async def get_item_or_fail(sessao_id, item_id):
        item = store["items"].get(item_id)
        if not item or item.sessao_id != sessao_id or item.tenant_id != service.tenant_id:
            raise EntityNotFoundError("Item de implantacao nao encontrado.")
        return item

    def _filtered_items(sessao_id, *, status=None, somente_erros=False, somente_avisos=False, ignorado=None):
        items = [
            item for item in store["items"].values()
            if item.sessao_id == sessao_id and item.tenant_id == service.tenant_id
        ]
        if status is not None:
            items = [item for item in items if item.status == status]
        if somente_erros:
            items = [item for item in items if item.status == "ERRO"]
        if somente_avisos:
            items = [item for item in items if item.status == "AVISO"]
        if ignorado is not None:
            items = [item for item in items if item.ignorado is ignorado]
        items.sort(key=lambda item: item.numero_linha)
        return items

    async def list_items(sessao_id, *, status=None, somente_erros=False, somente_avisos=False, ignorado=None, limit=100, offset=0):
        items = _filtered_items(
            sessao_id,
            status=status,
            somente_erros=somente_erros,
            somente_avisos=somente_avisos,
            ignorado=ignorado,
        )
        return items[offset:offset + limit]

    async def list_all_items(sessao_id):
        return _filtered_items(sessao_id)

    async def count_items(sessao_id, *, status=None, somente_erros=False, somente_avisos=False, ignorado=None):
        return len(
            _filtered_items(
                sessao_id,
                status=status,
                somente_erros=somente_erros,
                somente_avisos=somente_avisos,
                ignorado=ignorado,
            )
        )

    def _filtered_sessions(*, status=None, arquivo_nome=None, criado_em_inicio=None, criado_em_fim=None):
        sessions = [sessao for sessao in store["sessions"].values() if sessao.tenant_id == service.tenant_id]
        if status is not None:
            sessions = [sessao for sessao in sessions if sessao.status == status]
        if arquivo_nome:
            sessions = [sessao for sessao in sessions if arquivo_nome.lower() in sessao.arquivo_nome.lower()]
        if criado_em_inicio:
            sessions = [sessao for sessao in sessions if sessao.criado_em >= criado_em_inicio]
        if criado_em_fim:
            sessions = [sessao for sessao in sessions if sessao.criado_em <= criado_em_fim]
        sessions.sort(key=lambda sessao: sessao.criado_em, reverse=True)
        return sessions

    async def list_sessions(*, status=None, arquivo_nome=None, criado_em_inicio=None, criado_em_fim=None, limit=100, offset=0):
        sessions = _filtered_sessions(
            status=status,
            arquivo_nome=arquivo_nome,
            criado_em_inicio=criado_em_inicio,
            criado_em_fim=criado_em_fim,
        )
        return sessions[offset:offset + limit]

    async def count_sessions(*, status=None, arquivo_nome=None, criado_em_inicio=None, criado_em_fim=None):
        return len(
            _filtered_sessions(
                status=status,
                arquivo_nome=arquivo_nome,
                criado_em_inicio=criado_em_inicio,
                criado_em_fim=criado_em_fim,
            )
        )

    async def validar_produto(produto_id):
        for produto in produtos:
            if produto.id == produto_id and produto.tenant_id == service.tenant_id and produto.ativo:
                return produto
        raise BusinessRuleError("Produto informado nao pertence ao tenant ou esta inativo.")

    async def validar_deposito(deposito_id, unidade_produtiva_id=None):
        for deposito in depositos:
            if deposito.id == deposito_id and deposito.tenant_id == service.tenant_id and deposito.ativo:
                if unidade_produtiva_id is not None and deposito.unidade_produtiva_id != unidade_produtiva_id:
                    raise BusinessRuleError("Deposito informado pertence a outra unidade produtiva da sessao.")
                return deposito
        raise BusinessRuleError("Deposito informado nao pertence ao tenant ou esta inativo.")

    async def validar_unidade(_unidade_produtiva_id):
        return SimpleNamespace(id=uuid.uuid4(), tenant_id=service.tenant_id, ativo=True)

    class FakeEstoqueService:
        def __init__(self, backing_store: dict):
            self.backing_store = backing_store
            self.registrar_entrada = AsyncMock()
            self.registrar_ajuste = AsyncMock()

        async def registrar_saldo_inicial_implantacao(
            self,
            *,
            produto_id,
            deposito_id,
            quantidade,
            origem_id,
            observacao=None,
            custo_unitario=None,
            unidade_produtiva_id=None,
            numero_lote_legado=None,
            validade_legado=None,
        ):
            movimento = SimpleNamespace(
                id=uuid.uuid4(),
                tenant_id=service.tenant_id,
                produto_id=produto_id,
                deposito_id=deposito_id,
                tipo_movimento="SALDO_INICIAL",
                origem="IMPLANTACAO",
                origem_id=origem_id,
                quantidade=quantidade,
                custo_unitario=custo_unitario,
                observacoes=observacao,
                unidade_produtiva_id=unidade_produtiva_id,
                numero_lote=numero_lote_legado,
                validade_legado=validade_legado,
            )
            self.backing_store["movements"].append(movimento)
            return movimento

    estoque_service = FakeEstoqueService(store)

    monkeypatch.setattr(service, "_persist_session_record", persist_session)
    monkeypatch.setattr(service, "_persist_item_records", persist_items)
    monkeypatch.setattr(service, "_get_session_or_fail", get_session_or_fail)
    monkeypatch.setattr(service, "_get_item_or_fail", get_item_or_fail)
    monkeypatch.setattr(service, "_list_session_items", list_items)
    monkeypatch.setattr(service, "_list_all_session_items", list_all_items)
    monkeypatch.setattr(service, "_count_session_items", count_items)
    monkeypatch.setattr(service, "_list_sessions", list_sessions)
    monkeypatch.setattr(service, "_count_sessions", count_sessions)
    monkeypatch.setattr(service, "_validar_produto_resolvido", validar_produto)
    monkeypatch.setattr(service, "_validar_deposito_resolvido", validar_deposito)
    monkeypatch.setattr(service, "_validar_unidade_produtiva", validar_unidade)
    monkeypatch.setattr(service, "_buscar_sessao_duplicada_por_hash", AsyncMock(return_value=None))
    monkeypatch.setattr(service, "_build_estoque_service", lambda: estoque_service)
    monkeypatch.setattr(
        service,
        "_existe_saldo_inicial_para_item",
        lambda item: _async_return(
            any(
                mov.produto_id == item.produto_id_resolvido and mov.deposito_id == item.deposito_id_resolvido
                for mov in store["movements"]
            )
        ),
    )
    store["estoque_service"] = estoque_service
    return store


async def _criar_sessao_exemplo(monkeypatch: pytest.MonkeyPatch):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    produto = _produto(tenant_id=tenant_id, nome="Herbicida X", codigo_interno="ABC123")
    deposito = _deposito(tenant_id=tenant_id, nome="Deposito Central")
    service = await _service_with_catalog(
        monkeypatch,
        tenant_id=tenant_id,
        user_id=user_id,
        produtos=[produto],
        depositos=[deposito],
    )
    store = _attach_in_memory_persistence(service, monkeypatch, produtos=[produto], depositos=[deposito])
    audit_mock = AsyncMock()
    monkeypatch.setattr(service_module, "write_audit_log", audit_mock)
    content = (
        "produto_codigo,produto_nome,deposito_nome,quantidade,custo_unitario\n"
        "ABC123,Herbicida X,Deposito Central,10,15\n"
    ).encode("utf-8")
    sessao = await service.criar_sessao_from_csv(
        filename="estoque.csv",
        content=content,
        mapping=None,
        criado_por=user_id,
    )
    return service, store, audit_mock, sessao, produto, deposito


async def test_gerar_template_csv_retorna_cabecalho_esperado():
    service = EstoqueImplantacaoService(DummySession(), uuid.uuid4())
    content = await service.gerar_template_csv()
    assert content.splitlines()[0] == (
        "produto_codigo,produto_nome,deposito_nome,quantidade,unidade,custo_unitario,lote,validade,observacoes"
    )


async def test_preview_reconhece_aliases_de_colunas(monkeypatch: pytest.MonkeyPatch):
    tenant_id = uuid.uuid4()
    service = await _service_with_catalog(
        monkeypatch,
        tenant_id=tenant_id,
        produtos=[_produto(tenant_id=tenant_id, nome="Herbicida X")],
        depositos=[_deposito(tenant_id=tenant_id, nome="Deposito Central")],
    )
    content = "descricao,almoxarifado,qtde,custo\nHerbicida X,Deposito Central,10,15.5\n".encode("utf-8")
    result = await service.gerar_preview_csv(filename="estoque.csv", content=content)
    assert result.estrutura_minima_valida is True
    assert result.mapeamento_utilizado == {
        "descricao": "produto_nome",
        "almoxarifado": "deposito_nome",
        "qtde": "quantidade",
        "custo": "custo_unitario",
    }
    assert result.itens[0].status == "VALIDA"


async def test_preview_aceita_mapeamento_explicito(monkeypatch: pytest.MonkeyPatch):
    tenant_id = uuid.uuid4()
    service = await _service_with_catalog(
        monkeypatch,
        tenant_id=tenant_id,
        produtos=[_produto(tenant_id=tenant_id, nome="Herbicida X", codigo_interno="ABC123")],
        depositos=[_deposito(tenant_id=tenant_id, nome="Deposito Central")],
    )
    content = "item_codigo,item,local,saldo\nABC123,Herbicida X,Deposito Central,8\n".encode("utf-8")
    result = await service.gerar_preview_csv(
        filename="estoque.csv",
        content=content,
        mapping={"item_codigo": "produto_codigo", "item": "produto_nome", "local": "deposito_nome", "saldo": "quantidade"},
    )
    assert result.estrutura_minima_valida is True
    assert result.mapeamento_utilizado["item_codigo"] == "produto_codigo"
    assert result.itens[0].dados_normalizados["produto_id"] is not None


async def test_preview_linha_valida_com_aviso_de_custo_ausente(monkeypatch: pytest.MonkeyPatch):
    tenant_id = uuid.uuid4()
    service = await _service_with_catalog(
        monkeypatch,
        tenant_id=tenant_id,
        produtos=[_produto(tenant_id=tenant_id, nome="Herbicida X")],
        depositos=[_deposito(tenant_id=tenant_id, nome="Deposito Central")],
    )
    content = "produto_nome,deposito_nome,quantidade\nHerbicida X,Deposito Central,10\n".encode("utf-8")
    result = await service.gerar_preview_csv(filename="estoque.csv", content=content)
    assert result.linhas_com_aviso == 1
    assert result.itens[0].status == "AVISO"
    assert any(warning.codigo == "custo_unitario_ausente" for warning in result.itens[0].avisos)


async def test_preview_produto_nao_encontrado_retorna_erro_e_sugestoes(monkeypatch: pytest.MonkeyPatch):
    tenant_id = uuid.uuid4()
    service = await _service_with_catalog(
        monkeypatch,
        tenant_id=tenant_id,
        produtos=[_produto(tenant_id=tenant_id, nome="Herbicida X")],
        depositos=[_deposito(tenant_id=tenant_id, nome="Deposito Central")],
    )
    content = "produto_nome,deposito_nome,quantidade\nHerbicida Y,Deposito Central,10\n".encode("utf-8")
    result = await service.gerar_preview_csv(filename="estoque.csv", content=content)
    assert result.linhas_com_erro == 1
    assert "Herbicida Y" in result.produtos_nao_encontrados
    assert any(error.codigo == "produto_nao_encontrado" for error in result.itens[0].erros)
    assert "produto_nome" in result.itens[0].sugestoes


async def test_preview_deposito_nao_encontrado_retorna_erro(monkeypatch: pytest.MonkeyPatch):
    tenant_id = uuid.uuid4()
    service = await _service_with_catalog(
        monkeypatch,
        tenant_id=tenant_id,
        produtos=[_produto(tenant_id=tenant_id, nome="Herbicida X")],
        depositos=[_deposito(tenant_id=tenant_id, nome="Deposito Oficial")],
    )
    content = "produto_nome,deposito_nome,quantidade\nHerbicida X,Deposito Central,10\n".encode("utf-8")
    result = await service.gerar_preview_csv(filename="estoque.csv", content=content)
    assert result.linhas_com_erro == 1
    assert "Deposito Central" in result.depositos_nao_encontrados


async def test_preview_quantidade_invalida_retorna_erro(monkeypatch: pytest.MonkeyPatch):
    tenant_id = uuid.uuid4()
    service = await _service_with_catalog(
        monkeypatch,
        tenant_id=tenant_id,
        produtos=[_produto(tenant_id=tenant_id, nome="Herbicida X")],
        depositos=[_deposito(tenant_id=tenant_id, nome="Deposito Central")],
    )
    content = "produto_nome,deposito_nome,quantidade\nHerbicida X,Deposito Central,abc\n".encode("utf-8")
    result = await service.gerar_preview_csv(filename="estoque.csv", content=content)
    assert any(error.codigo == "quantidade_invalida" for error in result.itens[0].erros)


async def test_preview_custo_invalido_retorna_erro(monkeypatch: pytest.MonkeyPatch):
    tenant_id = uuid.uuid4()
    service = await _service_with_catalog(
        monkeypatch,
        tenant_id=tenant_id,
        produtos=[_produto(tenant_id=tenant_id, nome="Herbicida X")],
        depositos=[_deposito(tenant_id=tenant_id, nome="Deposito Central")],
    )
    content = "produto_nome,deposito_nome,quantidade,custo_unitario\nHerbicida X,Deposito Central,10,-1\n".encode("utf-8")
    result = await service.gerar_preview_csv(filename="estoque.csv", content=content)
    assert any(error.codigo == "custo_unitario_invalido" for error in result.itens[0].erros)


async def test_preview_bloqueia_match_cross_tenant(monkeypatch: pytest.MonkeyPatch):
    tenant_id = uuid.uuid4()
    outro_tenant = uuid.uuid4()
    service = await _service_with_catalog(
        monkeypatch,
        tenant_id=tenant_id,
        produtos=[_produto(tenant_id=outro_tenant, nome="Herbicida X")],
        depositos=[_deposito(tenant_id=outro_tenant, nome="Deposito Central")],
    )
    content = "produto_nome,deposito_nome,quantidade\nHerbicida X,Deposito Central,10\n".encode("utf-8")
    result = await service.gerar_preview_csv(filename="estoque.csv", content=content)
    assert result.linhas_com_erro == 1
    assert result.itens[0].dados_normalizados.get("produto_id") is None
    assert result.itens[0].dados_normalizados.get("deposito_id") is None


async def test_criar_sessao_valida_persiste_itens_e_auditoria(monkeypatch: pytest.MonkeyPatch):
    service, store, audit_mock, sessao, _produto_ok, _deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    assert sessao.status == "PRONTO_PARA_CONFIRMAR"
    assert sessao.total_itens == 1
    assert len(store["sessions"]) == 1
    assert len(store["items"]) == 1
    audit_mock.assert_awaited_once()
    assert audit_mock.await_args.kwargs["action"] == "create_session"
    assert audit_mock.await_args.kwargs["resource"] == "estoque_implantacao_sessoes"
    assert service.user_id is not None


async def test_criar_sessao_com_erros_mantem_status_de_validacao(monkeypatch: pytest.MonkeyPatch):
    tenant_id = uuid.uuid4()
    produto = _produto(tenant_id=tenant_id, nome="Herbicida X")
    deposito = _deposito(tenant_id=tenant_id, nome="Deposito Central")
    service = await _service_with_catalog(monkeypatch, tenant_id=tenant_id, produtos=[produto], depositos=[deposito])
    _attach_in_memory_persistence(service, monkeypatch, produtos=[produto], depositos=[deposito])
    monkeypatch.setattr(service_module, "write_audit_log", AsyncMock())
    content = "produto_nome,deposito_nome,quantidade\nProduto Inexistente,Deposito Central,10\n".encode("utf-8")
    sessao = await service.criar_sessao_from_csv(filename="estoque.csv", content=content, mapping=None, criado_por=None)
    assert sessao.status == "VALIDADO_COM_ERROS"
    assert sessao.linhas_com_erro == 1


async def test_busca_sessao_por_tenant_bloqueia_cross_tenant(monkeypatch: pytest.MonkeyPatch):
    service, store, _audit_mock, sessao, _produto_ok, _deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    resultado = await service.obter_sessao(sessao.id)
    assert resultado.id == sessao.id

    outro_service = EstoqueImplantacaoService(DummySession(), uuid.uuid4())

    async def get_session_fail(_sessao_id):
        raise EntityNotFoundError("Sessao de implantacao nao encontrada.")

    monkeypatch.setattr(outro_service, "_get_session_or_fail", get_session_fail)
    with pytest.raises(EntityNotFoundError):
        await outro_service.obter_sessao(next(iter(store["sessions"])))


async def test_corrigir_item_com_produto_e_deposito_validos_dispara_auditoria(monkeypatch: pytest.MonkeyPatch):
    service, store, audit_mock, sessao, produto_ok, deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    item_id = next(iter(store["items"]))
    item = store["items"][item_id]
    item.produto_id_resolvido = None
    item.deposito_id_resolvido = None
    item.dados_normalizados.pop("produto_id", None)
    item.dados_normalizados.pop("deposito_id", None)
    item.status = "ERRO"
    item.erros = [{"codigo": "produto_nao_encontrado"}]

    resultado = await service.corrigir_item(
        sessao.id,
        item_id,
        service_module.EstoqueImplantacaoItemCorrecaoRequest(
            produto_id_resolvido=produto_ok.id,
            deposito_id_resolvido=deposito_ok.id,
        ),
    )

    assert resultado.status == "PRONTO_PARA_CONFIRMAR"
    assert store["items"][item_id].status == "CORRIGIDO"
    assert audit_mock.await_count == 2
    assert audit_mock.await_args.kwargs["action"] == "correct_item"


async def test_rejeita_correcao_com_produto_ou_deposito_cross_tenant(monkeypatch: pytest.MonkeyPatch):
    service, store, _audit_mock, sessao, _produto_ok, _deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    item_id = next(iter(store["items"]))
    outro_produto = _produto(tenant_id=uuid.uuid4(), nome="Outro", codigo_interno="OUT")
    outro_deposito = _deposito(tenant_id=uuid.uuid4(), nome="Outro Deposito")

    with pytest.raises(BusinessRuleError):
        await service.corrigir_item(
            sessao.id,
            item_id,
            service_module.EstoqueImplantacaoItemCorrecaoRequest(produto_id_resolvido=outro_produto.id),
        )

    with pytest.raises(BusinessRuleError):
        await service.corrigir_item(
            sessao.id,
            item_id,
            service_module.EstoqueImplantacaoItemCorrecaoRequest(deposito_id_resolvido=outro_deposito.id),
        )


async def test_ignorar_item_nao_bloqueia_e_gera_auditoria(monkeypatch: pytest.MonkeyPatch):
    service, store, audit_mock, sessao, _produto_ok, _deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    item_id = next(iter(store["items"]))
    store["items"][item_id].status = "ERRO"
    store["items"][item_id].erros = [{"codigo": "produto_nao_encontrado"}]

    resultado = await service.corrigir_item(
        sessao.id,
        item_id,
        service_module.EstoqueImplantacaoItemCorrecaoRequest(ignorado=True),
    )

    assert resultado.linhas_com_erro == 0
    assert store["items"][item_id].status == "IGNORADO"
    assert audit_mock.await_args.kwargs["action"] == "ignore_item"


async def test_cancelar_sessao_dispara_auditoria(monkeypatch: pytest.MonkeyPatch):
    service, _store, audit_mock, sessao, _produto_ok, _deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    resultado = await service.cancelar_sessao(sessao.id)
    assert resultado.status == "CANCELADO"
    assert audit_mock.await_count == 2
    assert audit_mock.await_args.kwargs["action"] == "cancel_session"


async def test_impede_correcao_apos_cancelamento_ou_confirmacao(monkeypatch: pytest.MonkeyPatch):
    service, store, _audit_mock, sessao, _produto_ok, _deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    item_id = next(iter(store["items"]))
    store["sessions"][sessao.id].status = "CANCELADO"
    with pytest.raises(BusinessRuleError):
        await service.corrigir_item(sessao.id, item_id, service_module.EstoqueImplantacaoItemCorrecaoRequest(observacoes="x"))

    store["sessions"][sessao.id].status = "CONFIRMADO"
    with pytest.raises(BusinessRuleError):
        await service.corrigir_item(sessao.id, item_id, service_module.EstoqueImplantacaoItemCorrecaoRequest(observacoes="y"))


async def test_listagem_sessoes_filtra_por_tenant_e_nome(monkeypatch: pytest.MonkeyPatch):
    service, store, _audit_mock, sessao, _produto_ok, _deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    outra_sessao = SimpleNamespace(**store["sessions"][sessao.id].__dict__.copy())
    outra_sessao.id = uuid.uuid4()
    outra_sessao.arquivo_nome = "outro_arquivo.csv"
    outra_sessao.criado_em = sessao.criado_em - timedelta(days=1)
    store["sessions"][outra_sessao.id] = outra_sessao

    cross_tenant = SimpleNamespace(**store["sessions"][sessao.id].__dict__.copy())
    cross_tenant.id = uuid.uuid4()
    cross_tenant.tenant_id = uuid.uuid4()
    cross_tenant.arquivo_nome = "cross.csv"
    store["sessions"][cross_tenant.id] = cross_tenant

    resultado = await service.listar_sessoes(arquivo_nome="estoque", limit=10, offset=0)
    assert resultado.total == 1
    assert resultado.itens[0].arquivo_nome == "estoque.csv"


async def test_listagem_sessoes_filtra_por_periodo(monkeypatch: pytest.MonkeyPatch):
    service, store, _audit_mock, sessao, _produto_ok, _deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    inicio = sessao.criado_em - timedelta(hours=1)
    fim = sessao.criado_em + timedelta(hours=1)
    resultado = await service.listar_sessoes(criado_em_inicio=inicio, criado_em_fim=fim, limit=10, offset=0)
    assert resultado.total == 1
    assert resultado.itens[0].id == sessao.id
    store["sessions"][sessao.id].criado_em = sessao.criado_em - timedelta(days=10)
    resultado_vazio = await service.listar_sessoes(criado_em_inicio=inicio, criado_em_fim=fim, limit=10, offset=0)
    assert resultado_vazio.total == 0


async def test_listagem_itens_aplica_paginacao_e_filtros(monkeypatch: pytest.MonkeyPatch):
    service, store, _audit_mock, sessao, _produto_ok, _deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    base_item = next(iter(store["items"].values()))
    segundo = SimpleNamespace(**base_item.__dict__.copy())
    segundo.id = uuid.uuid4()
    segundo.numero_linha = 3
    segundo.status = "AVISO"
    segundo.avisos = [{"mensagem": "custo"}]
    store["items"][segundo.id] = segundo

    terceiro = SimpleNamespace(**base_item.__dict__.copy())
    terceiro.id = uuid.uuid4()
    terceiro.numero_linha = 4
    terceiro.status = "ERRO"
    terceiro.erros = [{"mensagem": "erro"}]
    store["items"][terceiro.id] = terceiro

    paginado = await service.listar_itens_sessao(sessao.id, limit=1, offset=1)
    assert paginado.total == 3
    assert len(paginado.itens) == 1
    assert paginado.itens[0].numero_linha == 3

    filtrado = await service.listar_itens_sessao(sessao.id, status="ERRO", limit=10, offset=0)
    assert filtrado.total == 1
    assert filtrado.itens[0].status == "ERRO"


async def test_revalidacao_recalcula_totais_e_auditoria(monkeypatch: pytest.MonkeyPatch):
    service, store, audit_mock, sessao, _produto_ok, _deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    item = next(iter(store["items"].values()))
    item.dados_normalizados["custo_unitario"] = None
    item.avisos = [{"codigo": "custo_unitario_ausente", "mensagem": "Custo unitario ausente."}]
    item.status = "AVISO"
    store["sessions"][sessao.id].status = "PRONTO_PARA_CORRECAO"

    resultado = await service.revalidar_sessao(sessao.id)
    assert resultado.status == "PRONTO_PARA_CORRECAO"
    assert resultado.linhas_com_aviso == 1
    assert audit_mock.await_args.kwargs["action"] == "revalidate_session"


async def test_sessao_cancelada_nao_pode_ser_revalidada(monkeypatch: pytest.MonkeyPatch):
    service, store, _audit_mock, sessao, _produto_ok, _deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    store["sessions"][sessao.id].status = "CANCELADO"
    with pytest.raises(BusinessRuleError):
        await service.revalidar_sessao(sessao.id)


async def test_aptidao_false_com_item_em_erro(monkeypatch: pytest.MonkeyPatch):
    service, store, _audit_mock, sessao, _produto_ok, _deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    item = next(iter(store["items"].values()))
    item.status = "ERRO"
    item.erros = [{"codigo": "produto_nao_encontrado", "mensagem": "Produto nao encontrado"}]

    resultado = await service.validar_sessao_apta_para_confirmacao(sessao.id, service.tenant_id)
    assert resultado.apta is False
    assert resultado.total_itens_confirmaveis == 0
    assert any("erros pendentes" in erro.lower() for erro in resultado.erros_bloqueantes)


async def test_aptidao_true_com_item_valido(monkeypatch: pytest.MonkeyPatch):
    service, _store, _audit_mock, sessao, _produto_ok, _deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    resultado = await service.validar_sessao_apta_para_confirmacao(sessao.id, service.tenant_id)
    assert resultado.apta is True
    assert resultado.total_itens_confirmaveis == 1
    assert resultado.valor_total_confirmavel == 150.0


async def test_item_ignorado_nao_bloqueia_confirmacao(monkeypatch: pytest.MonkeyPatch):
    service, store, _audit_mock, sessao, _produto_ok, _deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    item = next(iter(store["items"].values()))
    item.status = "IGNORADO"
    item.ignorado = True
    item.erros = [{"codigo": "produto_nao_encontrado"}]

    resultado = await service.validar_sessao_apta_para_confirmacao(sessao.id, service.tenant_id)
    assert resultado.apta is False
    assert "nao possui itens confirmaveis" in " ".join(resultado.erros_bloqueantes).lower()


async def test_confirmacao_sessao_apta_grava_saldo_inicial_e_auditoria(monkeypatch: pytest.MonkeyPatch):
    service, store, audit_mock, sessao, _produto_ok, _deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    resultado = await service.confirmar_sessao(
        sessao.id,
        service_module.EstoqueImplantacaoConfirmacaoRequest(
            confirmar_avisos=False,
            observacao="Carga inicial validada pelo responsavel",
        ),
    )

    assert resultado.status == "CONFIRMADO"
    assert store["sessions"][sessao.id].confirmado_por == service.user_id
    assert len(store["movements"]) == 1
    movimento = store["movements"][0]
    assert movimento.tipo_movimento == "SALDO_INICIAL"
    assert movimento.origem == "IMPLANTACAO"
    assert movimento.origem_id in store["items"]
    assert "sessao" in (movimento.observacoes or "").lower()
    assert audit_mock.await_args.kwargs["action"] == "confirm_session"
    assert store["estoque_service"].registrar_entrada.await_count == 0
    assert store["estoque_service"].registrar_ajuste.await_count == 0


async def test_confirmacao_rejeita_sessao_com_erro(monkeypatch: pytest.MonkeyPatch):
    service, store, _audit_mock, sessao, _produto_ok, _deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    item = next(iter(store["items"].values()))
    item.status = "ERRO"
    item.erros = [{"codigo": "produto_nao_encontrado", "mensagem": "Produto nao encontrado"}]

    with pytest.raises(BusinessRuleError):
        await service.confirmar_sessao(sessao.id, service_module.EstoqueImplantacaoConfirmacaoRequest(confirmar_avisos=True))

    assert not store["movements"]


async def test_confirmacao_rejeita_sessao_cancelada(monkeypatch: pytest.MonkeyPatch):
    service, store, _audit_mock, sessao, _produto_ok, _deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    store["sessions"][sessao.id].status = "CANCELADO"
    with pytest.raises(BusinessRuleError):
        await service.confirmar_sessao(sessao.id, service_module.EstoqueImplantacaoConfirmacaoRequest(confirmar_avisos=True))


async def test_confirmacao_rejeita_sessao_ja_confirmada(monkeypatch: pytest.MonkeyPatch):
    service, store, _audit_mock, sessao, _produto_ok, _deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    store["sessions"][sessao.id].status = "CONFIRMADO"
    with pytest.raises(BusinessRuleError):
        await service.confirmar_sessao(sessao.id, service_module.EstoqueImplantacaoConfirmacaoRequest(confirmar_avisos=True))


async def test_confirmacao_ignora_itens_marcados_como_ignorado(monkeypatch: pytest.MonkeyPatch):
    service, store, _audit_mock, sessao, _produto_ok, _deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    base_item = next(iter(store["items"].values()))
    ignorado = SimpleNamespace(**base_item.__dict__.copy())
    ignorado.id = uuid.uuid4()
    ignorado.numero_linha = 3
    ignorado.status = "IGNORADO"
    ignorado.ignorado = True
    store["items"][ignorado.id] = ignorado

    resultado = await service.confirmar_sessao(sessao.id, service_module.EstoqueImplantacaoConfirmacaoRequest(confirmar_avisos=True))
    assert resultado.status == "CONFIRMADO"
    assert len(store["movements"]) == 1
    assert all(mov.origem_id != ignorado.id for mov in store["movements"])


async def test_confirmacao_bloqueia_avisos_sem_confirmar_avisos(monkeypatch: pytest.MonkeyPatch):
    service, store, _audit_mock, sessao, _produto_ok, _deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    item = next(iter(store["items"].values()))
    item.status = "AVISO"
    item.avisos = [{"codigo": "custo_unitario_ausente", "mensagem": "Custo unitario ausente."}]
    item.dados_normalizados["custo_unitario"] = None
    store["sessions"][sessao.id].status = "PRONTO_PARA_CORRECAO"

    with pytest.raises(BusinessRuleError):
        await service.confirmar_sessao(sessao.id, service_module.EstoqueImplantacaoConfirmacaoRequest(confirmar_avisos=False))
    assert len(store["movements"]) == 0


async def test_confirmacao_permite_avisos_com_confirmar_avisos_true(monkeypatch: pytest.MonkeyPatch):
    service, store, _audit_mock, sessao, _produto_ok, _deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    item = next(iter(store["items"].values()))
    item.status = "AVISO"
    item.avisos = [{"codigo": "custo_unitario_ausente", "mensagem": "Custo unitario ausente."}]
    item.dados_normalizados["custo_unitario"] = None
    store["sessions"][sessao.id].status = "PRONTO_PARA_CORRECAO"

    resultado = await service.confirmar_sessao(sessao.id, service_module.EstoqueImplantacaoConfirmacaoRequest(confirmar_avisos=True))
    assert resultado.status == "CONFIRMADO"
    assert len(store["movements"]) == 1


async def test_confirmacao_respeita_tenant_isolation(monkeypatch: pytest.MonkeyPatch):
    service, store, _audit_mock, sessao, _produto_ok, _deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    outro_service = EstoqueImplantacaoService(DummySession(), uuid.uuid4(), user_id=uuid.uuid4())

    async def get_session_fail(_sessao_id, *, for_update=False):
        raise EntityNotFoundError("Sessao de implantacao nao encontrada.")

    monkeypatch.setattr(outro_service, "_get_session_or_fail", get_session_fail)
    with pytest.raises(EntityNotFoundError):
        await outro_service.confirmar_sessao(sessao.id, service_module.EstoqueImplantacaoConfirmacaoRequest(confirmar_avisos=True))
    assert len(store["movements"]) == 0


async def test_confirmacao_bloqueia_duplicidade_por_idempotencia(monkeypatch: pytest.MonkeyPatch):
    service, store, _audit_mock, sessao, _produto_ok, _deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    await service.confirmar_sessao(sessao.id, service_module.EstoqueImplantacaoConfirmacaoRequest(confirmar_avisos=True))
    with pytest.raises(BusinessRuleError):
        await service.confirmar_sessao(sessao.id, service_module.EstoqueImplantacaoConfirmacaoRequest(confirmar_avisos=True))
    assert len(store["movements"]) == 1


async def test_confirmacao_interrompe_em_erro_intermediario(monkeypatch: pytest.MonkeyPatch):
    service, store, _audit_mock, sessao, _produto_ok, _deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    base_item = next(iter(store["items"].values()))
    segundo = SimpleNamespace(**base_item.__dict__.copy())
    segundo.id = uuid.uuid4()
    segundo.numero_linha = 3
    store["items"][segundo.id] = segundo

    async def explode_na_segunda_confirmacao(**kwargs):
        if len(store["movements"]) >= 1:
            raise BusinessRuleError("falha intermediaria")
        movimento = SimpleNamespace(
            id=uuid.uuid4(),
            tenant_id=service.tenant_id,
            produto_id=kwargs["produto_id"],
            deposito_id=kwargs["deposito_id"],
            tipo_movimento="SALDO_INICIAL",
            origem="IMPLANTACAO",
            origem_id=kwargs["origem_id"],
            quantidade=kwargs["quantidade"],
            custo_unitario=kwargs.get("custo_unitario"),
            observacoes=kwargs.get("observacao"),
        )
        store["movements"].append(movimento)
        return movimento

    store["estoque_service"].registrar_saldo_inicial_implantacao = explode_na_segunda_confirmacao
    with pytest.raises(BusinessRuleError):
        await service.confirmar_sessao(sessao.id, service_module.EstoqueImplantacaoConfirmacaoRequest(confirmar_avisos=True))
    assert store["sessions"][sessao.id].status != "CONFIRMADO"


async def test_aptidao_bloqueia_linhas_duplicadas_mesmo_produto_deposito(monkeypatch: pytest.MonkeyPatch):
    service, store, _audit_mock, sessao, _produto_ok, _deposito_ok = await _criar_sessao_exemplo(monkeypatch)
    base_item = next(iter(store["items"].values()))
    duplicado = SimpleNamespace(**base_item.__dict__.copy())
    duplicado.id = uuid.uuid4()
    duplicado.numero_linha = 7
    store["items"][duplicado.id] = duplicado

    resultado = await service.validar_sessao_apta_para_confirmacao(sessao.id, service.tenant_id)
    assert resultado.apta is False
    assert any("duplica o produto/deposito" in erro.lower() for erro in resultado.erros_bloqueantes)
