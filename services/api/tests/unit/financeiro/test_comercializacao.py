"""
FIN-COM-01 a FIN-COM-12: Testes unitários de ComercializacaoCommodity.
"""

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from agricola.colheita.models import ProdutoColhido
from agricola.safras.models import Safra
from core.cadastros.commodities.models import Commodity
from core.cadastros.pessoas.models import Pessoa
from core.cadastros.propriedades.models import AreaRural
from financeiro.comercializacao.models import ComercializacaoCommodity
from financeiro.comercializacao.schemas import (
    STATUS_VALIDOS,
    ComercializacaoCreate,
    ComercializacaoUpdate,
)
from financeiro.comercializacao.service import TRANSICOES, ComercializacaoService
from financeiro.models.receita import Receita

# ===========================================================================
# FIN-COM-01 a FIN-COM-06: Validação de ComercializacaoCreate
# ===========================================================================


class TestComercializacaoCreate:
    """Validação do schema de criação de comercialização."""

    # FIN-COM-01: Criação válida mínima
    def test_minimo(self):
        c = ComercializacaoCreate(
            commodity_id=uuid.uuid4(),
            comprador_id=uuid.uuid4(),
            quantidade=100.0,
            unidade="SACA_60KG",
            preco_unitario=150.0,
        )
        assert c.quantidade == 100.0
        assert c.moeda == "BRL"

    # FIN-COM-02: Quantidade positiva obrigatória
    def test_quantidade_positiva(self):
        with pytest.raises(ValidationError):
            ComercializacaoCreate(
                commodity_id=uuid.uuid4(),
                comprador_id=uuid.uuid4(),
                quantidade=0,
                unidade="SACA_60KG",
                preco_unitario=150.0,
            )

    # FIN-COM-03: Quantidade negativa rejeitada
    def test_quantidade_negativa(self):
        with pytest.raises(ValidationError):
            ComercializacaoCreate(
                commodity_id=uuid.uuid4(),
                comprador_id=uuid.uuid4(),
                quantidade=-50.0,
                unidade="SACA_60KG",
                preco_unitario=150.0,
            )

    # FIN-COM-04: Preço unitário positivo obrigatório
    def test_preco_positivo(self):
        with pytest.raises(ValidationError):
            ComercializacaoCreate(
                commodity_id=uuid.uuid4(),
                comprador_id=uuid.uuid4(),
                quantidade=100.0,
                unidade="SACA_60KG",
                preco_unitario=0,
            )

    # FIN-COM-05: Preço negativo rejeitado
    def test_preco_negativo(self):
        with pytest.raises(ValidationError):
            ComercializacaoCreate(
                commodity_id=uuid.uuid4(),
                comprador_id=uuid.uuid4(),
                quantidade=100.0,
                unidade="SACA_60KG",
                preco_unitario=-10.0,
            )

    # FIN-COM-06: Campos opcionais
    def test_campos_opcionais(self):
        c = ComercializacaoCreate(
            commodity_id=uuid.uuid4(),
            comprador_id=uuid.uuid4(),
            quantidade=500.0,
            unidade="SACA_60KG",
            preco_unitario=155.50,
            moeda="BRL",
            numero_contrato="CTR-2026-001",
            forma_pagamento="BOLETO",
            data_entrega_prevista=None,
            local_entrega="Armazém Central",
            frete_por_conta="COMPRADOR",
        )
        assert c.numero_contrato == "CTR-2026-001"
        assert c.forma_pagamento == "BOLETO"


# ===========================================================================
# FIN-COM-07 a FIN-COM-09: Validação de ComercializacaoUpdate
# ===========================================================================


class TestComercializacaoUpdate:
    """Validação do schema de atualização."""

    # FIN-COM-07: Partial update válido
    def test_partial_update(self):
        u = ComercializacaoUpdate(status="CONFIRMADO")
        assert u.status == "CONFIRMADO"
        assert u.preco_unitario is None

    # FIN-COM-08: Status inválido rejeitado
    @pytest.mark.parametrize("status_invalido", ["PAGO", "ENTREGA", "INVALIDO", ""])
    def test_status_invalido_rejeitado(self, status_invalido):
        with pytest.raises(ValidationError) as exc_info:
            ComercializacaoUpdate(status=status_invalido)
        assert "deve ser um de" in str(exc_info.value).lower()

    # FIN-COM-09: Status válido aceito
    @pytest.mark.parametrize("status_valido", sorted(STATUS_VALIDOS))
    def test_status_valido_aceito(self, status_valido):
        u = ComercializacaoUpdate(status=status_valido)
        assert u.status == status_valido


# ===========================================================================
# FIN-COM-10 a FIN-COM-12: Regras de transição de status
# ===========================================================================


class TestTransicoesStatus:
    """Testes das regras de transição de status."""

    # FIN-COM-10: Transições permitidas do RASCUNHO
    def test_transicoes_rascunho(self):
        permitidas = TRANSICOES["RASCUNHO"]
        assert "CONFIRMADO" in permitidas
        assert "CANCELADO" in permitidas
        assert "FINALIZADO" not in permitidas

    # FIN-COM-11: Transições permitidas do CONFIRMADO
    def test_transicoes_confirmado(self):
        permitidas = TRANSICOES["CONFIRMADO"]
        assert "EM_TRANSITO" in permitidas
        assert "CANCELADO" in permitidas
        assert "FINALIZADO" not in permitidas

    # FIN-COM-12: FINALIZADO e CANCELADO são terminais
    def test_estados_terminais(self):
        assert TRANSICOES["FINALIZADO"] == []
        assert TRANSICOES["CANCELADO"] == []


class FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


@pytest.mark.asyncio
async def test_confirmar_comercializacao_reserva_estoque_e_cria_receita():
    tenant_id = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()

    safra = Safra(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        ano_safra="2025/26",
        cultura="SOJA",
        status="POS_COLHEITA",
    )
    area = AreaRural(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        tipo="TALHAO",
        nome="Talhão Comercial",
        ativo=True,
    )
    commodity = Commodity(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        sistema=False,
        nome="Soja Comercial",
        codigo=f"SC-{uuid.uuid4().hex[:8]}",
        tipo="AGRICOLA",
        unidade_padrao="SACA_60KG",
        peso_unidade=60.0,
        possui_cotacao=False,
        ativo=True,
    )
    comprador = Pessoa(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        tipo="PJ",
        nome_exibicao="Comprador Teste",
        base_legal="CONTRATO",
        ativo=True,
    )
    produto = ProdutoColhido(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        safra_id=safra.id,
        talhao_id=area.id,
        romaneio_id=None,
        commodity_id=commodity.id,
        classificacao_id=None,
        qualidade_laudo_id=None,
        qualidade_status="APROVADO",
        quantidade=100.0,
        unidade="SACA_60KG",
        peso_liquido_kg=6000.0,
        peso_desconto_qualidade_kg=0.0,
        peso_liquido_comercial_kg=6000.0,
        data_entrada=date.today(),
        destino="ARMAZEM",
        status="ARMAZENADO",
    )
    plano_id = uuid.uuid4()

    session = MagicMock()
    session.execute = AsyncMock(
        side_effect=[
            FakeResult(object()),
            FakeResult(object()),
            FakeResult(plano_id),
        ]
    )

    async def mock_get(model, _id):
        if model is ProdutoColhido:
            return produto
        if model is AreaRural:
            return area
        if model is Commodity:
            return commodity
        return None

    session.get = AsyncMock(side_effect=mock_get)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()

    svc = ComercializacaoService(session, tenant_id)
    comercializacao = await svc.criar(
        ComercializacaoCreate(
            commodity_id=commodity.id,
            comprador_id=comprador.id,
            quantidade=100.0,
            unidade="SACA_60KG",
            preco_unitario=180.0,
            moeda="BRL",
            forma_pagamento="PRAZO",
            data_entrega_prevista=date.today(),
            produto_colhido_id=produto.id,
            local_entrega="Armazém Central",
        )
    )

    assert comercializacao.valor_total == pytest.approx(18000.0)
    comercializacao.status = "RASCUNHO"
    assert session.add.call_count == 1

    await svc.transicionar_status(comercializacao, "CONFIRMADO")

    assert produto.status == "RESERVADO"
    assert comercializacao.status == "CONFIRMADO"
    assert session.add.call_count == 2

    receita = session.add.call_args_list[1].args[0]
    assert receita.origem_tipo == "COMERCIALIZACAO"
    assert receita.origem_id == comercializacao.id
    assert receita.valor_total == pytest.approx(18000.0)
    assert receita.pessoa_id == comprador.id
    assert comercializacao.receita_id == receita.id

    await svc.transicionar_status(comercializacao, "EM_TRANSITO")
    assert comercializacao.status == "EM_TRANSITO"

    await svc.transicionar_status(comercializacao, "ENTREGUE")
    assert comercializacao.status == "ENTREGUE"

    await svc.transicionar_status(comercializacao, "FINALIZADO")

    assert produto.status == "VENDIDO"
    assert comercializacao.status == "FINALIZADO"
    assert session.commit.await_count == 4


@pytest.mark.asyncio
async def test_finalizar_comercializacao_recebe_receita_automaticamente_quando_pagamento_imediato():
    tenant_id = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()

    safra = Safra(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        ano_safra="2025/26",
        cultura="SOJA",
        status="POS_COLHEITA",
    )
    area = AreaRural(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        tipo="TALHAO",
        nome="Talhão Comercial",
        ativo=True,
    )
    commodity = Commodity(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        sistema=False,
        nome="Soja Comercial",
        codigo=f"SC-{uuid.uuid4().hex[:8]}",
        tipo="AGRICOLA",
        unidade_padrao="SACA_60KG",
        peso_unidade=60.0,
        possui_cotacao=False,
        ativo=True,
    )
    comprador = Pessoa(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        tipo="PJ",
        nome_exibicao="Comprador Teste",
        base_legal="CONTRATO",
        ativo=True,
    )
    produto = ProdutoColhido(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        safra_id=safra.id,
        talhao_id=area.id,
        romaneio_id=None,
        commodity_id=commodity.id,
        classificacao_id=None,
        qualidade_laudo_id=None,
        qualidade_status="APROVADO",
        quantidade=100.0,
        unidade="SACA_60KG",
        peso_liquido_kg=6000.0,
        peso_desconto_qualidade_kg=0.0,
        peso_liquido_comercial_kg=6000.0,
        data_entrada=date.today(),
        destino="ARMAZEM",
        status="ARMAZENADO",
    )
    plano_id = uuid.uuid4()

    session = MagicMock()
    session.execute = AsyncMock(
        side_effect=[
            FakeResult(object()),
            FakeResult(object()),
            FakeResult(plano_id),
        ]
    )

    comercializacao_ref = {"obj": None}
    receita_ref = {"obj": None}

    async def mock_get(model, _id):
        if model is ProdutoColhido:
            return produto
        if model is AreaRural:
            return area
        if model is Commodity:
            return commodity
        if model is Receita:
            return (
                receita_ref["obj"] if receita_ref["obj"] and receita_ref["obj"].id == _id else None
            )
        return None

    session.get = AsyncMock(side_effect=mock_get)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    def add_side_effect(obj):
        if isinstance(obj, ComercializacaoCommodity):
            comercializacao_ref["obj"] = obj
        if isinstance(obj, Receita):
            receita_ref["obj"] = obj

    session.add = MagicMock(side_effect=add_side_effect)

    svc = ComercializacaoService(session, tenant_id)
    comercializacao = await svc.criar(
        ComercializacaoCreate(
            commodity_id=commodity.id,
            comprador_id=comprador.id,
            quantidade=100.0,
            unidade="SACA_60KG",
            preco_unitario=180.0,
            moeda="BRL",
            forma_pagamento="A_VISTA",
            data_entrega_prevista=date.today(),
            produto_colhido_id=produto.id,
            local_entrega="Armazém Central",
        )
    )
    comercializacao.status = "RASCUNHO"

    await svc.transicionar_status(comercializacao, "CONFIRMADO")
    receita = receita_ref["obj"]
    assert receita is not None
    assert receita.status == "A_RECEBER"

    await svc.transicionar_status(comercializacao, "EM_TRANSITO")
    await svc.transicionar_status(comercializacao, "ENTREGUE")
    await svc.transicionar_status(comercializacao, "FINALIZADO")

    assert produto.status == "VENDIDO"
    assert comercializacao.status == "FINALIZADO"
    assert comercializacao.data_pagamento == date.today()
    assert receita.status == "RECEBIDO"
    assert receita.valor_recebido == pytest.approx(receita.valor_total)
    assert receita.data_recebimento == date.today()

    receita.valor_recebido = 1.0
    await svc._auto_receber_receita(comercializacao)
    assert receita.valor_recebido == 1.0
