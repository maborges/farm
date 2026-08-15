from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.cadastros.pessoas.models import Pessoa, PessoaProfissionalAgronomo
from core.cadastros.produtos.models import Produto, ProdutoEstoque
from agricola.receituario_agronomico.models import StatusReceituario
from agricola.receituario_agronomico.schemas import ReceituarioAgronomicoCreate, ReceituarioItemCreate
from agricola.receituario_agronomico.service import ReceituarioAgronomicoService
from operacional.schemas.estoque import SaidaEstoqueRequest
from operacional.services.estoque_service import EstoqueService
from test_operational_workflow_governance_step03 import _criar_unidade_produtiva, _garantir_tenant


async def _criar_pessoa_agronomo(
    session: AsyncSession, tenant_id: uuid.UUID, *, crea_validade: date | None, ativo: bool = True,
) -> uuid.UUID:
    pessoa = Pessoa(tenant_id=tenant_id, tipo="PF", nome_exibicao="Agrônomo Teste")
    session.add(pessoa)
    await session.flush()
    perfil = PessoaProfissionalAgronomo(
        tenant_id=tenant_id, pessoa_id=pessoa.id,
        crea_numero="123456", crea_uf="SP", crea_validade=crea_validade, ativo=ativo,
    )
    session.add(perfil)
    await session.commit()
    return pessoa.id


async def _criar_pessoa_sem_perfil(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    pessoa = Pessoa(tenant_id=tenant_id, tipo="PF", nome_exibicao="Pessoa Qualquer")
    session.add(pessoa)
    await session.commit()
    return pessoa.id


async def _criar_produto_defensivo(
    session: AsyncSession, tenant_id: uuid.UUID, *, requer_receituario: bool = True,
) -> uuid.UUID:
    produto = Produto(tenant_id=tenant_id, nome="Herbicida Teste", tipo="DEFENSIVO", unidade_medida="L")
    session.add(produto)
    await session.flush()
    session.add(ProdutoEstoque(produto_id=produto.id, requer_receituario=requer_receituario))
    await session.commit()
    return produto.id


async def _criar_receituario_emitido(
    session: AsyncSession, tenant_id: uuid.UUID, *, produto_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID, agronomo_pessoa_id: uuid.UUID,
    data_emissao: date, validade_dias: int,
):
    svc = ReceituarioAgronomicoService(session, tenant_id)
    receituario = await svc.emitir(ReceituarioAgronomicoCreate(
        agronomo_pessoa_id=agronomo_pessoa_id,
        unidade_produtiva_id=unidade_produtiva_id,
        data_emissao=data_emissao,
        validade_dias=validade_dias,
        itens=[ReceituarioItemCreate(produto_id=produto_id, dose=2.5, unidade_dose="L/ha")],
    ))
    receituario.status = StatusReceituario.EMITIDO.value
    await session.commit()
    return receituario


@pytest.mark.asyncio
async def test_emissao_exige_agronomo_com_crea_ativo(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    produto_id = await _criar_produto_defensivo(session, tenant_id)
    pessoa_sem_perfil = await _criar_pessoa_sem_perfil(session, tenant_id)

    svc = ReceituarioAgronomicoService(session, tenant_id)
    with pytest.raises(BusinessRuleError):
        await svc.emitir(ReceituarioAgronomicoCreate(
            agronomo_pessoa_id=pessoa_sem_perfil,
            unidade_produtiva_id=unidade_id,
            data_emissao=date.today(),
            itens=[ReceituarioItemCreate(produto_id=produto_id, dose=1.0, unidade_dose="L/ha")],
        ))


@pytest.mark.asyncio
async def test_emissao_exige_crea_nao_vencido(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    produto_id = await _criar_produto_defensivo(session, tenant_id)
    agronomo_id = await _criar_pessoa_agronomo(
        session, tenant_id, crea_validade=date.today() - timedelta(days=1),
    )

    svc = ReceituarioAgronomicoService(session, tenant_id)
    with pytest.raises(BusinessRuleError):
        await svc.emitir(ReceituarioAgronomicoCreate(
            agronomo_pessoa_id=agronomo_id,
            unidade_produtiva_id=unidade_id,
            data_emissao=date.today(),
            itens=[ReceituarioItemCreate(produto_id=produto_id, dose=1.0, unidade_dose="L/ha")],
        ))


@pytest.mark.asyncio
async def test_isolamento_tenant_receituario(session: AsyncSession):
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    await _garantir_tenant(session, tenant_a)
    await _garantir_tenant(session, tenant_b)
    unidade_id = await _criar_unidade_produtiva(session, tenant_a)
    produto_id = await _criar_produto_defensivo(session, tenant_a)
    agronomo_id = await _criar_pessoa_agronomo(session, tenant_a, crea_validade=date.today() + timedelta(days=365))

    receituario = await _criar_receituario_emitido(
        session, tenant_a, produto_id=produto_id, unidade_produtiva_id=unidade_id,
        agronomo_pessoa_id=agronomo_id, data_emissao=date.today(), validade_dias=90,
    )

    svc_b = ReceituarioAgronomicoService(session, tenant_b)
    with pytest.raises(EntityNotFoundError):
        await svc_b.get_or_fail(receituario.id)


@pytest.mark.asyncio
async def test_saida_bloqueada_sem_receituario(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    produto_id = await _criar_produto_defensivo(session, tenant_id)

    estoque_svc = EstoqueService(session, tenant_id)
    with pytest.raises(BusinessRuleError):
        await estoque_svc.registrar_saida(SaidaEstoqueRequest(
            produto_id=produto_id, quantidade=10.0,
            unidade_produtiva_id=unidade_id, motivo="Teste bloqueio",
        ))


@pytest.mark.asyncio
async def test_saida_nao_bloqueada_com_receituario_valido(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    produto_id = await _criar_produto_defensivo(session, tenant_id)
    agronomo_id = await _criar_pessoa_agronomo(session, tenant_id, crea_validade=date.today() + timedelta(days=365))
    await _criar_receituario_emitido(
        session, tenant_id, produto_id=produto_id, unidade_produtiva_id=unidade_id,
        agronomo_pessoa_id=agronomo_id, data_emissao=date.today(), validade_dias=90,
    )

    estoque_svc = EstoqueService(session, tenant_id)
    # Sem depósito/saldo cadastrado, a checagem de receituário passa e o fluxo
    # segue até a falha esperada de "nenhum depósito ativo" — prova que o
    # bloqueio de receituário não é mais o motivo da exceção.
    with pytest.raises(BusinessRuleError, match="depósito"):
        await estoque_svc.registrar_saida(SaidaEstoqueRequest(
            produto_id=produto_id, quantidade=10.0,
            unidade_produtiva_id=unidade_id, motivo="Teste liberado",
        ))


@pytest.mark.asyncio
async def test_saida_bloqueada_com_receituario_vencido(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    produto_id = await _criar_produto_defensivo(session, tenant_id)
    agronomo_id = await _criar_pessoa_agronomo(session, tenant_id, crea_validade=date.today() + timedelta(days=365))
    await _criar_receituario_emitido(
        session, tenant_id, produto_id=produto_id, unidade_produtiva_id=unidade_id,
        agronomo_pessoa_id=agronomo_id, data_emissao=date.today() - timedelta(days=200), validade_dias=90,
    )

    estoque_svc = EstoqueService(session, tenant_id)
    with pytest.raises(BusinessRuleError, match="Receituário"):
        await estoque_svc.registrar_saida(SaidaEstoqueRequest(
            produto_id=produto_id, quantidade=10.0,
            unidade_produtiva_id=unidade_id, motivo="Teste vencido",
        ))


@pytest.mark.asyncio
async def test_saida_liberada_para_produto_sem_exigencia(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    produto_id = await _criar_produto_defensivo(session, tenant_id, requer_receituario=False)

    estoque_svc = EstoqueService(session, tenant_id)
    with pytest.raises(BusinessRuleError, match="depósito"):
        await estoque_svc.registrar_saida(SaidaEstoqueRequest(
            produto_id=produto_id, quantidade=10.0,
            unidade_produtiva_id=unidade_id, motivo="Teste produto sem exigência",
        ))
