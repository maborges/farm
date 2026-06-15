import uuid
from datetime import date

import pytest
from sqlalchemy import func, select

from agricola.beneficiamento.schemas import LoteFromRomaneiosRequest
from agricola.beneficiamento.service import BeneficiamentoService
from agricola.colheita.models import ProdutoColhido
from agricola.romaneios.models import RomaneioColheita
from agricola.safras.models import Safra
from core.cadastros.commodities.models import Commodity
from core.cadastros.produtos.models import Produto
from core.exceptions import BusinessRuleError, EntityNotFoundError
from financeiro.models.receita import Receita
from operacional.models.qualidade import QualidadeProtocolo, QualidadeCriterio, QualidadeLaudo
from operacional.models.estoque import EstoqueMovimento, LoteEstoque, Deposito
import operacional.models.qualidade  # noqa: F401


async def _criar_base(session, tenant_id, talhao_id):
    commodity_id = uuid.uuid4()
    safra_id = uuid.uuid4()

    session.add(
        Produto(
            id=commodity_id,
            tenant_id=tenant_id,
            nome=f"Café Teste {commodity_id.hex[:8]}",
            tipo="OUTRO",
            unidade_medida="SACA",
            preco_medio=0.0,
            ativo=True,
        )
    )
    session.add(
        Commodity(
            id=commodity_id,
            tenant_id=tenant_id,
            nome=f"Café Teste {commodity_id.hex[:8]}",
            codigo=f"CAFE-BEN-{commodity_id.hex[:8]}",
            tipo="AGRICOLA",
            unidade_padrao="SACA_60KG",
            peso_unidade=60.0,
            ativo=True,
        )
    )
    session.add(
        Safra(
            id=safra_id,
            tenant_id=tenant_id,
            ano_safra="2025",
            status="PLANEJAMENTO",
        )
    )
    await session.commit()
    return safra_id, commodity_id


async def _criar_romaneio_produto(
    session,
    tenant_id,
    safra_id,
    talhao_id,
    commodity_id,
    *,
    peso_padrao=9400.0,
    peso_comercial=None,
    qualidade_status=None,
):
    romaneio_id = uuid.uuid4()
    produto_id = uuid.uuid4()

    romaneio = RomaneioColheita(
        id=romaneio_id,
        tenant_id=tenant_id,
        safra_id=safra_id,
        talhao_id=talhao_id,
        commodity_id=commodity_id,
        numero_romaneio=f"ROM-{romaneio_id.hex[:8]}",
        data_colheita=date(2025, 5, 15),
        peso_bruto_kg=10000.0,
        tara_kg=500.0,
        peso_liquido_kg=9500.0,
        peso_liquido_padrao_kg=peso_padrao,
        peso_liquido_comercial_kg=peso_comercial,
        qualidade_status=qualidade_status,
    )
    session.add(romaneio)
    await session.flush()

    session.add(
        ProdutoColhido(
            id=produto_id,
            tenant_id=tenant_id,
            safra_id=safra_id,
            talhao_id=talhao_id,
            romaneio_id=romaneio_id,
            commodity_id=commodity_id,
            qualidade_status=qualidade_status,
            quantidade=156.667,
            unidade="SACA_60KG",
            peso_liquido_kg=peso_padrao,
            peso_desconto_qualidade_kg=0,
            peso_liquido_comercial_kg=peso_comercial,
            data_entrada=date(2025, 5, 15),
            status="ARMAZENADO",
        )
    )
    await session.commit()
    return romaneio_id, produto_id


async def _preparar_lote_armazenavel(
    session,
    tenant_id,
    talhao_id,
    unidade_produtiva_id,
    *,
    peso_padrao=9400.0,
    peso_comercial=None,
    qualidade_status=None,
    qualidade_laudo_id=None,
    peso_desconto_qualidade_kg=0.0,
):
    safra_id, commodity_id = await _criar_base(session, tenant_id, talhao_id)
    romaneio_id, produto_id = await _criar_romaneio_produto(
        session,
        tenant_id,
        safra_id,
        talhao_id,
        commodity_id,
        peso_padrao=peso_padrao,
        peso_comercial=peso_comercial,
        qualidade_status=qualidade_status,
    )
    if qualidade_laudo_id or qualidade_status is not None or peso_desconto_qualidade_kg or peso_comercial is not None:
        if qualidade_laudo_id:
            protocolo = QualidadeProtocolo(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                nome=f"Protocolo Qualidade {uuid.uuid4().hex[:6]}",
                ativo=True,
            )
            criterio = QualidadeCriterio(
                id=uuid.uuid4(),
                protocolo_id=protocolo.id,
                nome="Umidade",
                tipo_dado="NUMERIC",
            )
            laudo = QualidadeLaudo(
                id=qualidade_laudo_id,
                tenant_id=tenant_id,
                unidade_produtiva_id=None,
                protocolo_id=protocolo.id,
                romaneio_id=romaneio_id,
                status="APROVADO",
            )
            session.add_all([protocolo, criterio, laudo])
            await session.flush()
        romaneio = await session.get(RomaneioColheita, romaneio_id)
        produto = await session.get(ProdutoColhido, produto_id)
        romaneio.qualidade_laudo_id = qualidade_laudo_id
        romaneio.qualidade_status = qualidade_status
        romaneio.peso_desconto_qualidade_kg = peso_desconto_qualidade_kg
        romaneio.peso_liquido_comercial_kg = peso_comercial
        produto.qualidade_laudo_id = qualidade_laudo_id
        produto.qualidade_status = qualidade_status
        produto.peso_desconto_qualidade_kg = peso_desconto_qualidade_kg
        produto.peso_liquido_comercial_kg = peso_comercial
        await session.commit()
    deposito = Deposito(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        nome=f"Deposito Bene {uuid.uuid4().hex[:6]}",
        tipo="ALMOXARIFADO",
        ativo=True,
    )
    session.add(deposito)
    await session.commit()
    return romaneio_id, produto_id, deposito.id


@pytest.mark.asyncio
async def test_beneficiamento_usa_peso_comercial_quando_existente(session, tenant_id, talhao_id):
    safra_id, commodity_id = await _criar_base(session, tenant_id, talhao_id)
    romaneio_id, _ = await _criar_romaneio_produto(
        session,
        tenant_id,
        safra_id,
        talhao_id,
        commodity_id,
        peso_padrao=9400.0,
        peso_comercial=9380.0,
        qualidade_status="APROVADO",
    )

    receita_antes = await session.scalar(
        select(func.count(Receita.id)).where(Receita.tenant_id == tenant_id, Receita.origem_id == romaneio_id)
    )
    ledger_antes = await session.scalar(
        select(func.count(EstoqueMovimento.id)).where(
            EstoqueMovimento.tenant_id == tenant_id,
            EstoqueMovimento.origem_id == romaneio_id,
        )
    )

    svc = BeneficiamentoService(session, tenant_id)
    lote = await svc.criar_from_romaneio(romaneio_id)

    assert float(lote.peso_entrada_kg) == 9380.0
    assert (receita_antes or 0) == 0
    assert (ledger_antes or 0) == 0
    receita_depois = await session.scalar(
        select(func.count(Receita.id)).where(Receita.tenant_id == tenant_id, Receita.origem_id == romaneio_id)
    )
    ledger_depois = await session.scalar(
        select(func.count(EstoqueMovimento.id)).where(
            EstoqueMovimento.tenant_id == tenant_id,
            EstoqueMovimento.origem_id == romaneio_id,
        )
    )
    assert (receita_depois or 0) == 0
    assert (ledger_depois or 0) == 0


@pytest.mark.asyncio
async def test_beneficiamento_mantem_peso_padrao_quando_sem_peso_comercial(session, tenant_id, talhao_id):
    safra_id, commodity_id = await _criar_base(session, tenant_id, talhao_id)
    romaneio_id, _ = await _criar_romaneio_produto(
        session,
        tenant_id,
        safra_id,
        talhao_id,
        commodity_id,
        peso_padrao=9400.0,
        peso_comercial=None,
        qualidade_status=None,
    )

    svc = BeneficiamentoService(session, tenant_id)
    lote = await svc.criar_from_romaneio(romaneio_id)

    assert float(lote.peso_entrada_kg) == 9400.0


@pytest.mark.asyncio
async def test_beneficiamento_bloqueia_qualidade_reprovada(session, tenant_id, talhao_id):
    safra_id, commodity_id = await _criar_base(session, tenant_id, talhao_id)
    romaneio_id, _ = await _criar_romaneio_produto(
        session,
        tenant_id,
        safra_id,
        talhao_id,
        commodity_id,
        peso_padrao=9400.0,
        peso_comercial=9300.0,
        qualidade_status="REPROVADO",
    )

    svc = BeneficiamentoService(session, tenant_id)
    with pytest.raises(BusinessRuleError, match="REPROVADO"):
        await svc.criar_from_romaneio(romaneio_id)


@pytest.mark.asyncio
async def test_beneficiamento_blend_bloqueia_se_algum_item_reprovado(session, tenant_id, talhao_id):
    safra_id, commodity_id = await _criar_base(session, tenant_id, talhao_id)
    aprovado_id, _ = await _criar_romaneio_produto(
        session,
        tenant_id,
        safra_id,
        talhao_id,
        commodity_id,
        peso_padrao=9400.0,
        peso_comercial=9380.0,
        qualidade_status="APROVADO",
    )
    reprovado_id, _ = await _criar_romaneio_produto(
        session,
        tenant_id,
        safra_id,
        talhao_id,
        commodity_id,
        peso_padrao=9100.0,
        peso_comercial=9000.0,
        qualidade_status="REPROVADO",
    )

    svc = BeneficiamentoService(session, tenant_id)
    with pytest.raises(BusinessRuleError, match="REPROVADO"):
        await svc.criar_from_romaneios(
            LoteFromRomaneiosRequest(romaneio_ids=[aprovado_id, reprovado_id], metodo="NATURAL")
        )


@pytest.mark.asyncio
async def test_beneficiamento_preserva_isolamento_tenant(session_a, session_b, tenant_id, outro_tenant_id, talhao_id):
    safra_id, commodity_id = await _criar_base(session_a, tenant_id, talhao_id)
    romaneio_id, _ = await _criar_romaneio_produto(
        session_a,
        tenant_id,
        safra_id,
        talhao_id,
        commodity_id,
        peso_padrao=9400.0,
        peso_comercial=9380.0,
        qualidade_status="APROVADO",
    )

    svc = BeneficiamentoService(session_b, outro_tenant_id)
    with pytest.raises(EntityNotFoundError):
        await svc.criar_from_romaneio(romaneio_id)


@pytest.mark.asyncio
async def test_armazenar_no_estoque_propaga_qualidade_e_observacao(session, tenant_id, talhao_id, unidade_produtiva_id):
    romaneio_id, _, deposito_id = await _preparar_lote_armazenavel(
        session,
        tenant_id,
        talhao_id,
        unidade_produtiva_id,
        peso_padrao=9400.0,
        peso_comercial=9380.0,
        qualidade_status="APROVADO",
        qualidade_laudo_id=uuid.uuid4(),
        peso_desconto_qualidade_kg=20.0,
    )

    svc = BeneficiamentoService(session, tenant_id)
    lote = await svc.criar_from_romaneio(romaneio_id)
    lote.status = "ARMAZENADO"
    lote.armazem_id = deposito_id
    lote.sacas_beneficiadas = 156.667
    await session.commit()

    resultado = await svc.armazenar_no_estoque(lote.id)
    lote_estoque = await session.get(LoteEstoque, uuid.UUID(resultado["lote_estoque_id"]))
    movimento = await session.scalar(
        select(EstoqueMovimento).where(EstoqueMovimento.lote_id == lote_estoque.id)
    )

    assert lote_estoque.status == "ATIVO"
    assert lote_estoque.qualidade_status == "APROVADO"
    assert lote_estoque.qualidade_laudo_id is not None
    assert float(lote_estoque.peso_desconto_qualidade_kg) == 20.0
    assert lote_estoque.metadata_json["qualidade_status"] == "APROVADO"
    assert lote_estoque.metadata_json["qualidade_laudo_id"] == str(lote_estoque.qualidade_laudo_id)
    assert movimento.origem == "MANUAL"
    assert movimento.tipo_movimento == "ENTRADA"
    assert "qualidade_status" in (movimento.observacoes or "")


@pytest.mark.asyncio
async def test_armazenar_no_estoque_sem_qualidade_mantem_fluxo(session, tenant_id, talhao_id, unidade_produtiva_id):
    romaneio_id, _, deposito_id = await _preparar_lote_armazenavel(
        session,
        tenant_id,
        talhao_id,
        unidade_produtiva_id,
        peso_padrao=9400.0,
        peso_comercial=None,
        qualidade_status=None,
        qualidade_laudo_id=None,
        peso_desconto_qualidade_kg=0.0,
    )

    svc = BeneficiamentoService(session, tenant_id)
    lote = await svc.criar_from_romaneio(romaneio_id)
    lote.status = "ARMAZENADO"
    lote.armazem_id = deposito_id
    lote.sacas_beneficiadas = 156.667
    await session.commit()

    resultado = await svc.armazenar_no_estoque(lote.id)
    lote_estoque = await session.get(LoteEstoque, uuid.UUID(resultado["lote_estoque_id"]))

    assert float(lote_estoque.peso_desconto_qualidade_kg) == 0.0
    assert lote_estoque.qualidade_status is None
    assert lote_estoque.qualidade_laudo_id is None


@pytest.mark.asyncio
async def test_armazenar_no_estoque_preserva_isolamento_tenant(session_a, session_b, tenant_id, outro_tenant_id, talhao_id, unidade_produtiva_id):
    romaneio_id, _, deposito_id = await _preparar_lote_armazenavel(
        session_a,
        tenant_id,
        talhao_id,
        unidade_produtiva_id,
        peso_padrao=9400.0,
        peso_comercial=9380.0,
        qualidade_status="APROVADO",
        qualidade_laudo_id=uuid.uuid4(),
        peso_desconto_qualidade_kg=20.0,
    )

    svc_a = BeneficiamentoService(session_a, tenant_id)
    lote = await svc_a.criar_from_romaneio(romaneio_id)
    lote.status = "ARMAZENADO"
    lote.armazem_id = deposito_id
    await session_a.commit()

    svc_b = BeneficiamentoService(session_b, outro_tenant_id)
    with pytest.raises(EntityNotFoundError):
        await svc_b.armazenar_no_estoque(lote.id)
