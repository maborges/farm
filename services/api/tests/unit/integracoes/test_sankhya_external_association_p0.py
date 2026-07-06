# ruff: noqa: S105, S106
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import Column, String, Table, select
from sqlalchemy import Uuid as UUIDType
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.cadastros.pessoas.models import Pessoa, PessoaDocumento
from core.cadastros.produtos.models import CategoriaProduto, Marca, ModeloProduto, Produto
from core.database import Base
from core.measurements.models import UnidadeMedida
from financeiro.models.conciliacao import ContaBancaria
from events.outbox_model import DomainEventOutbox
from financeiro.models.despesa import Despesa
from financeiro.models.nota_fiscal import NotaFiscal, StatusSEFAZ, TipoNF
from financeiro.models.plano_conta import PlanoConta
from integracoes.models import (
    ExternalRecordAssociation,
    ExternalRecordAssociationHistory,
    ExternalRecordAssociationStatus,
    IntegrationCredential,
    IntegrationFeature,
    IntegrationHealth,
    IntegrationJob,
    IntegrationSyncPolicy,
    IntegrationVersion,
    MarketplaceIntegracao,
    TenantIntegracao,
)
from integracoes.sankhya.models import (
    SankhyaConfig,
    SankhyaLancamentoFinanceiro,
    SankhyaNFe,
    SankhyaPessoa,
    SankhyaProduto,
)
from integracoes.sankhya.services.nfe_financeiro_service import (
    SankhyaFinanceiroService,
    SankhyaNFeService,
)
from integracoes.sankhya.services.external_association_helper import (
    SankhyaExternalAssociationHelper,
)
from integracoes.sankhya.services.sync_service import (
    SankhyaPessoaService,
    SankhyaProdutoService,
    SankhyaSyncService,
)
from operacional.models.estoque import Deposito
from agricola.models import OperacaoTipoFase

if "tenants" not in Base.metadata.tables:
    Table(
        "tenants",
        Base.metadata,
        Column("id", UUIDType(as_uuid=True), primary_key=True),
        Column("nome", String(255), nullable=True),
    )

if "unidades_produtivas" not in Base.metadata.tables:
    Table(
        "unidades_produtivas",
        Base.metadata,
        Column("id", UUIDType(as_uuid=True), primary_key=True),
        Column("tenant_id", UUIDType(as_uuid=True), nullable=True),
        Column("nome", String(255), nullable=True),
    )

if "cultivos" not in Base.metadata.tables:
    Table(
        "cultivos",
        Base.metadata,
        Column("id", UUIDType(as_uuid=True), primary_key=True),
        Column("tenant_id", UUIDType(as_uuid=True), nullable=True),
        Column("nome", String(255), nullable=True),
    )

if "usuarios" not in Base.metadata.tables:
    Table(
        "usuarios",
        Base.metadata,
        Column("id", UUIDType(as_uuid=True), primary_key=True),
        Column("nome", String(255), nullable=True),
    )


@pytest_asyncio.fixture()
async def session(monkeypatch: pytest.MonkeyPatch) -> AsyncSession:
    async def fake_publish(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr(
        "integracoes.sankhya.services.canonical_adapter.publish_domain_event_safe",
        fake_publish,
    )

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        for table in (
            Base.metadata.tables["tenants"],
            Base.metadata.tables["unidades_produtivas"],
            Base.metadata.tables["cultivos"],
            Base.metadata.tables["usuarios"],
            DomainEventOutbox.__table__,
            Marca.__table__,
            ModeloProduto.__table__,
            CategoriaProduto.__table__,
            Produto.__table__,
            Pessoa.__table__,
            PessoaDocumento.__table__,
            UnidadeMedida.__table__,
            PlanoConta.__table__,
            ContaBancaria.__table__,
            NotaFiscal.__table__,
            Despesa.__table__,
            Deposito.__table__,
            OperacaoTipoFase.__table__,
            SankhyaConfig.__table__,
            SankhyaPessoa.__table__,
            SankhyaProduto.__table__,
            SankhyaNFe.__table__,
            SankhyaLancamentoFinanceiro.__table__,
            MarketplaceIntegracao.__table__,
            IntegrationCredential.__table__,
            TenantIntegracao.__table__,
            IntegrationVersion.__table__,
            IntegrationFeature.__table__,
            IntegrationSyncPolicy.__table__,
            IntegrationJob.__table__,
            IntegrationHealth.__table__,
            ExternalRecordAssociation.__table__,
            ExternalRecordAssociationHistory.__table__,
        ):
            await conn.run_sync(table.create)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as current:
        yield current

    await engine.dispose()


async def _insert_base_scope(session: AsyncSession, tenant_id: uuid.UUID) -> dict[str, uuid.UUID]:
    unidade_id = uuid.uuid4()
    await session.execute(
        Base.metadata.tables["tenants"].insert().values(id=tenant_id, nome=f"Tenant {tenant_id}")
    )
    await session.execute(
        Base.metadata.tables["unidades_produtivas"].insert().values(
            id=unidade_id,
            tenant_id=tenant_id,
            nome="Unidade Base",
        )
    )
    await session.commit()
    return {"unidade_id": unidade_id}


async def _seed_sankhya_runtime(
    session: AsyncSession,
    tenant_id: str,
    *,
    environment: str = "producao",
) -> SankhyaConfig:
    service = SankhyaSyncService(session)
    return await service.criar_config(
        tenant_id=tenant_id,
        sankhya_environment=environment,
        ws_url="https://erp.example/ws",
        username="usuario",
        password="segredo",
        sync_interval=900,
    )


async def _set_runtime_environment(
    session: AsyncSession,
    tenant_id: str,
    environment: str,
) -> None:
    config = await session.scalar(
        select(TenantIntegracao).where(TenantIntegracao.tenant_id == tenant_id)
    )
    assert config is not None
    payload = dict(config.connection_payload or {})
    payload["environment"] = environment
    payload["sankhya_environment"] = environment
    config.connection_payload = payload
    session.add(config)
    await session.commit()


async def _create_pessoa(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    documento: str,
    *,
    nome: str = "Pessoa Local",
) -> Pessoa:
    pessoa = Pessoa(
        tenant_id=tenant_id,
        tipo="PF" if len(documento) == 11 else "PJ",
        nome_exibicao=nome,
        base_legal="CONTRATO",
        tags=[],
        ativo=True,
    )
    session.add(pessoa)
    await session.flush()
    session.add(
        PessoaDocumento(
            pessoa_id=pessoa.id,
            tipo="CPF" if len(documento) == 11 else "CNPJ",
            numero=documento,
            nome_completo=nome if len(documento) == 11 else None,
            razao_social=nome if len(documento) == 14 else None,
        )
    )
    await session.commit()
    await session.refresh(pessoa)
    return pessoa


async def _create_produto(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    codigo_interno: str,
    nome: str,
    unidade_medida: str = "UN",
    codigo_barras: str | None = None,
) -> Produto:
    produto = Produto(
        tenant_id=tenant_id,
        nome=nome,
        tipo="INSUMO",
        unidade_medida=unidade_medida,
        codigo_interno=codigo_interno,
        sku=codigo_interno,
        codigo_barras=codigo_barras,
        ativo=True,
    )
    session.add(produto)
    await session.commit()
    await session.refresh(produto)
    return produto


async def _create_unidade_medida(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    codigo: str,
) -> UnidadeMedida:
    unidade = UnidadeMedida(
        tenant_id=tenant_id,
        codigo=codigo,
        nome=codigo,
        dimensao="QUANTIDADE",
        codigo_canonico=codigo,
        fator_canonico=1,
        sistema=False,
        ativo=True,
        casas_decimais=2,
        eh_canonica=True,
    )
    session.add(unidade)
    await session.commit()
    await session.refresh(unidade)
    return unidade


async def _create_plano_conta(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    codigo: str,
    nome: str = "Plano",
) -> PlanoConta:
    plano = PlanoConta(
        tenant_id=tenant_id,
        codigo=codigo,
        nome=nome,
        tipo="DESPESA",
        natureza="ANALITICA",
        ativo=True,
    )
    session.add(plano)
    await session.commit()
    await session.refresh(plano)
    return plano


async def _create_nota_fiscal(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    unidade_id: uuid.UUID,
    chave_acesso: str,
    numero: int,
    serie: str,
) -> NotaFiscal:
    nota = NotaFiscal(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_id,
        tipo=TipoNF.NF_E,
        numero=numero,
        serie=serie,
        emitente_nome="Fornecedor",
        destinatario_nome="Tenant",
        valor_total=120.0,
        status_sefaz=StatusSEFAZ.AUTORIZADA,
        chave_acesso=chave_acesso,
        data_emissao=datetime.now(timezone.utc),
        unidade="UN",
    )
    session.add(nota)
    await session.commit()
    await session.refresh(nota)
    return nota


async def _create_despesa(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    unidade_id: uuid.UUID,
    plano_conta_id: uuid.UUID,
    numero_documento: str,
    vencimento: date,
    valor_total: Decimal,
) -> Despesa:
    despesa = Despesa(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_id,
        plano_conta_id=plano_conta_id,
        descricao="Despesa Sankhya",
        valor_total=valor_total,
        data_emissao=vencimento,
        data_vencimento=vencimento,
        numero_nf=numero_documento,
        nota_fiscal=numero_documento,
        ativo=True,
    )
    session.add(despesa)
    await session.commit()
    await session.refresh(despesa)
    return despesa


async def _create_conta_bancaria(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    nome: str,
    banco: str | None = None,
    agencia: str | None = None,
    conta: str | None = None,
) -> ContaBancaria:
    conta_bancaria = ContaBancaria(
        tenant_id=tenant_id,
        nome=nome,
        banco=banco,
        agencia=agencia,
        conta=conta,
        tipo="CORRENTE",
        ativa=True,
    )
    session.add(conta_bancaria)
    await session.commit()
    await session.refresh(conta_bancaria)
    return conta_bancaria


async def _create_deposito(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_id: uuid.UUID,
    *,
    nome: str,
    localizacao_desc: str | None = None,
) -> Deposito:
    deposito = Deposito(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_id,
        nome=nome,
        tipo="GERAL",
        localizacao_desc=localizacao_desc,
        ativo=True,
    )
    session.add(deposito)
    await session.commit()
    await session.refresh(deposito)
    return deposito


async def _create_tipo_operacao(
    session: AsyncSession,
    *,
    tipo_operacao: str,
    fases_permitidas: list[str] | None = None,
) -> OperacaoTipoFase:
    item = OperacaoTipoFase(
        id=uuid.uuid4(),
        tipo_operacao=tipo_operacao,
        fases_permitidas=fases_permitidas or ["PLANTIO"],
        descricao=f"Tipo {tipo_operacao}",
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def _list_associations(
    session: AsyncSession,
    *,
    tenant_id: str,
    external_entity: str | None = None,
) -> list[ExternalRecordAssociation]:
    stmt = select(ExternalRecordAssociation).where(ExternalRecordAssociation.tenant_id == tenant_id)
    if external_entity is not None:
        stmt = stmt.where(ExternalRecordAssociation.external_entity == external_entity)
    stmt = stmt.order_by(ExternalRecordAssociation.created_at.asc())
    return list((await session.execute(stmt)).scalars().all())


@pytest.mark.asyncio
async def test_pessoa_codparc_cria_associacao_oficial_sem_tratar_staging_como_vinculo(
    session: AsyncSession,
) -> None:
    tenant_uuid = uuid.uuid4()
    tenant_id = str(tenant_uuid)
    await _insert_base_scope(session, tenant_uuid)
    await _seed_sankhya_runtime(session, tenant_id)
    pessoa_local = await _create_pessoa(session, tenant_uuid, "12345678901", nome="Pessoa A")

    service = SankhyaPessoaService(session)
    await service._salvar_pessoa_fisica(
        tenant_id,
        {
            "CODPARC": "1001",
            "NOME": "Pessoa Sankhya",
            "CGC_CPF": "123.456.789-01",
            "EMAIL": "pessoa@example.com",
            "TELEFONE": "9999-0000",
            "ATIVO": "S",
        },
    )

    associations = await _list_associations(session, tenant_id=tenant_id, external_entity="Parceiro")
    assert len(associations) == 1
    assert associations[0].local_entity == "Pessoa"
    assert associations[0].local_record_id == str(pessoa_local.id)
    assert associations[0].external_record_id == "1001"
    assert associations[0].status == ExternalRecordAssociationStatus.ACTIVE.value
    assert associations[0].secondary_keys["documento"] == "12345678901"

    staging = await session.scalar(select(SankhyaPessoa).where(SankhyaPessoa.tenant_id == tenant_id))
    assert staging is not None
    assert staging.sankhya_id == "1001"


@pytest.mark.asyncio
async def test_pessoa_mesmo_codparc_em_tenants_diferentes_mantem_isolamento(
    session: AsyncSession,
) -> None:
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    await _insert_base_scope(session, tenant_a)
    await _insert_base_scope(session, tenant_b)
    await _seed_sankhya_runtime(session, str(tenant_a))
    await _seed_sankhya_runtime(session, str(tenant_b))
    pessoa_a = await _create_pessoa(session, tenant_a, "11111111111", nome="Pessoa Tenant A")
    pessoa_b = await _create_pessoa(session, tenant_b, "22222222222", nome="Pessoa Tenant B")

    service = SankhyaPessoaService(session)
    await service._salvar_pessoa_fisica(str(tenant_a), {"CODPARC": "900", "CGC_CPF": "11111111111"})
    await service._salvar_pessoa_fisica(str(tenant_b), {"CODPARC": "900", "CGC_CPF": "22222222222"})

    associations_a = await _list_associations(session, tenant_id=str(tenant_a), external_entity="Parceiro")
    associations_b = await _list_associations(session, tenant_id=str(tenant_b), external_entity="Parceiro")

    assert associations_a[0].local_record_id == str(pessoa_a.id)
    assert associations_b[0].local_record_id == str(pessoa_b.id)
    assert associations_a[0].id != associations_b[0].id


@pytest.mark.asyncio
async def test_pessoa_conflito_quando_codparc_passa_a_apontar_para_outro_local(
    session: AsyncSession,
) -> None:
    tenant_uuid = uuid.uuid4()
    tenant_id = str(tenant_uuid)
    await _insert_base_scope(session, tenant_uuid)
    await _seed_sankhya_runtime(session, tenant_id)
    await _create_pessoa(session, tenant_uuid, "33333333333", nome="Pessoa 1")
    await _create_pessoa(session, tenant_uuid, "44444444444", nome="Pessoa 2")

    service = SankhyaPessoaService(session)
    await service._salvar_pessoa_fisica(tenant_id, {"CODPARC": "777", "CGC_CPF": "33333333333"})
    await service._salvar_pessoa_fisica(tenant_id, {"CODPARC": "777", "CGC_CPF": "44444444444"})

    association = (await _list_associations(session, tenant_id=tenant_id, external_entity="Parceiro"))[0]
    assert association.status == ExternalRecordAssociationStatus.CONFLICT.value


@pytest.mark.asyncio
async def test_produto_codprod_cria_associacao_e_unidade_fica_pendente_sem_equivalencia_segura(
    session: AsyncSession,
) -> None:
    tenant_uuid = uuid.uuid4()
    tenant_id = str(tenant_uuid)
    await _insert_base_scope(session, tenant_uuid)
    await _seed_sankhya_runtime(session, tenant_id)
    produto_local = await _create_produto(
        session,
        tenant_uuid,
        codigo_interno="501",
        nome="Adubo Especial",
        unidade_medida="UN",
    )

    service = SankhyaProdutoService(session)
    await service._salvar_produto(
        tenant_id,
        {
            "CODPROD": "501",
            "DESCRPROD": "Adubo Especial",
            "UNIDADE": "CX",
            "ATIVO": "S",
        },
    )

    produto_assoc = (await _list_associations(session, tenant_id=tenant_id, external_entity="Produto"))[0]
    unidade_assoc = (await _list_associations(session, tenant_id=tenant_id, external_entity="Unidade"))[0]

    assert produto_assoc.local_record_id == str(produto_local.id)
    assert produto_assoc.status == ExternalRecordAssociationStatus.ACTIVE.value
    assert unidade_assoc.local_record_id is None
    assert unidade_assoc.status == ExternalRecordAssociationStatus.PENDING.value
    assert unidade_assoc.external_record_id == "CX"


@pytest.mark.asyncio
async def test_produto_mesmo_codprod_em_ambientes_diferentes_gera_associacoes_distintas(
    session: AsyncSession,
) -> None:
    tenant_uuid = uuid.uuid4()
    tenant_id = str(tenant_uuid)
    await _insert_base_scope(session, tenant_uuid)
    await _seed_sankhya_runtime(session, tenant_id, environment="producao")
    await _create_produto(session, tenant_uuid, codigo_interno="601", nome="Produto Ambiente")
    await _create_unidade_medida(session, tenant_uuid, codigo="UN")

    service = SankhyaProdutoService(session)
    payload = {
        "CODPROD": "601",
        "DESCRPROD": "Produto Ambiente",
        "UNIDADE": "UN",
        "ATIVO": "S",
    }
    await service._salvar_produto(tenant_id, payload)
    await _set_runtime_environment(session, tenant_id, "homologacao")
    await service._salvar_produto(tenant_id, payload)

    associations = await _list_associations(session, tenant_id=tenant_id, external_entity="Produto")
    assert len(associations) == 2
    assert {item.environment for item in associations} == {"producao", "homologacao"}


@pytest.mark.asyncio
async def test_nfe_chave_acesso_eh_chave_forte_da_associacao(
    session: AsyncSession,
) -> None:
    tenant_uuid = uuid.uuid4()
    tenant_id = str(tenant_uuid)
    scope = await _insert_base_scope(session, tenant_uuid)
    await _seed_sankhya_runtime(session, tenant_id)
    nota_local = await _create_nota_fiscal(
        session,
        tenant_uuid,
        unidade_id=scope["unidade_id"],
        chave_acesso="35140712345678000123550010000000011000000010",
        numero=123,
        serie="1",
    )

    service = SankhyaNFeService(session)
    await service._salvar_nfe_entrada(
        tenant_id,
        {
            "CHAVEACESSO": nota_local.chave_acesso,
            "NUNOTA": "9988",
            "NUMNOTA": "123",
            "SERIE": "1",
            "MODNOTA": "55",
            "CODNEG": "4455",
        },
    )

    association = (await _list_associations(session, tenant_id=tenant_id, external_entity="NFe"))[0]
    assert association.local_record_id == str(nota_local.id)
    assert association.external_record_id == nota_local.chave_acesso
    assert association.secondary_keys["nunota"] == "9988"
    assert association.secondary_keys["serie"] == "1"


@pytest.mark.asyncio
async def test_financeiro_usa_chave_composta_e_registra_natureza_pendente_sem_regra_segura(
    session: AsyncSession,
) -> None:
    tenant_uuid = uuid.uuid4()
    tenant_id = str(tenant_uuid)
    scope = await _insert_base_scope(session, tenant_uuid)
    await _seed_sankhya_runtime(session, tenant_id)
    plano = await _create_plano_conta(session, tenant_uuid, codigo="LOCAL-001", nome="Plano Local")
    despesa_local = await _create_despesa(
        session,
        tenant_uuid,
        unidade_id=scope["unidade_id"],
        plano_conta_id=plano.id,
        numero_documento="DOC-500",
        vencimento=date(2026, 7, 15),
        valor_total=Decimal("150.00"),
    )

    service = SankhyaFinanceiroService(session)
    await service._salvar_lancamento(
        tenant_id,
        {
            "TIPO": "CONTAS_PAGAR",
            "CODPARC": "321",
            "NUMDOC": "DOC-500",
            "DESDOB": "01",
            "DTVENC": "2026-07-15",
            "VLRDESDOB": "150.00",
            "CODNAT": "NAT-999",
            "CODEMP": "10",
            "CODFILIAL": "20",
            "STATUS": "ABERTO",
        },
    )

    titulo_assoc = (await _list_associations(session, tenant_id=tenant_id, external_entity="TituloFinanceiro"))[0]
    natureza_assoc = (
        await _list_associations(session, tenant_id=tenant_id, external_entity="NaturezaFinanceira")
    )[0]

    assert titulo_assoc.local_record_id == str(despesa_local.id)
    assert titulo_assoc.status == ExternalRecordAssociationStatus.ACTIVE.value
    assert titulo_assoc.external_record_id != "01"
    assert titulo_assoc.external_record_id == "CONTAS_PAGAR|321|DOC-500|01|2026-07-15|150.00|10|20"
    assert natureza_assoc.local_record_id is None
    assert natureza_assoc.status == ExternalRecordAssociationStatus.PENDING.value
    assert natureza_assoc.external_record_id == "NAT-999"


@pytest.mark.asyncio
async def test_associacao_pendente_da_unidade_e_reconciliada_quando_equivalencia_passa_a_existir(
    session: AsyncSession,
) -> None:
    tenant_uuid = uuid.uuid4()
    tenant_id = str(tenant_uuid)
    await _insert_base_scope(session, tenant_uuid)
    await _seed_sankhya_runtime(session, tenant_id)
    await _create_produto(session, tenant_uuid, codigo_interno="700", nome="Produto UM")

    service = SankhyaProdutoService(session)
    payload = {
        "CODPROD": "700",
        "DESCRPROD": "Produto UM",
        "UNIDADE": "SC",
        "ATIVO": "S",
    }
    await service._salvar_produto(tenant_id, payload)
    first_unit_assoc = (await _list_associations(session, tenant_id=tenant_id, external_entity="Unidade"))[0]
    assert first_unit_assoc.status == ExternalRecordAssociationStatus.PENDING.value

    unidade_local = await _create_unidade_medida(session, tenant_uuid, codigo="SC")
    await service._salvar_produto(tenant_id, payload)

    unit_assoc = (await _list_associations(session, tenant_id=tenant_id, external_entity="Unidade"))[0]
    assert unit_assoc.local_record_id == str(unidade_local.id)
    assert unit_assoc.status == ExternalRecordAssociationStatus.ACTIVE.value

    history = list(
        (
            await session.execute(
                select(ExternalRecordAssociationHistory).where(
                    ExternalRecordAssociationHistory.link_id == unit_assoc.id
                )
            )
        ).scalars()
    )
    assert len(history) >= 2


@pytest.mark.asyncio
async def test_organizacao_sem_modelo_local_seguro_fica_pendente(session: AsyncSession) -> None:
    tenant_uuid = uuid.uuid4()
    tenant_id = str(tenant_uuid)
    await _insert_base_scope(session, tenant_uuid)
    await _seed_sankhya_runtime(session, tenant_id)

    helper = SankhyaExternalAssociationHelper(session)
    empresa, filial = await helper.sync_organizacao(
        tenant_id,
        {
            "CODEMP": "10",
            "CODFILIAL": "20",
        },
    )

    assert empresa is not None
    assert filial is not None
    assert empresa.status == ExternalRecordAssociationStatus.PENDING.value
    assert filial.status == ExternalRecordAssociationStatus.PENDING.value
    assert empresa.local_record_id is None
    assert filial.local_record_id is None
    assert filial.external_company_id == "10"
    assert filial.external_branch_id == "20"


@pytest.mark.asyncio
async def test_deposito_codlocal_com_mesmo_codigo_em_tenants_diferentes_mantem_isolamento(
    session: AsyncSession,
) -> None:
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    scope_a = await _insert_base_scope(session, tenant_a)
    scope_b = await _insert_base_scope(session, tenant_b)
    await _seed_sankhya_runtime(session, str(tenant_a), environment="producao")
    await _seed_sankhya_runtime(session, str(tenant_b), environment="producao")
    unidade_a = scope_a["unidade_id"]
    unidade_b = scope_b["unidade_id"]
    deposito_a = await _create_deposito(session, tenant_a, unidade_a, nome="CD-01")
    deposito_b = await _create_deposito(session, tenant_b, unidade_b, nome="CD-01")

    helper = SankhyaExternalAssociationHelper(session)
    await helper.sync_deposito(
        str(tenant_a),
        {"CODLOCAL": "10", "NOMELOCAL": "CD-01", "TIPOLOCAL": "ARMAZEM"},
    )
    await helper.sync_deposito(
        str(tenant_b),
        {"CODLOCAL": "10", "NOMELOCAL": "CD-01", "TIPOLOCAL": "ARMAZEM"},
    )

    associations_a = await _list_associations(session, tenant_id=str(tenant_a), external_entity="LocalEstoque")
    associations_b = await _list_associations(session, tenant_id=str(tenant_b), external_entity="LocalEstoque")

    assert associations_a[0].local_record_id == str(deposito_a.id)
    assert associations_b[0].local_record_id == str(deposito_b.id)
    assert associations_a[0].external_record_id == associations_b[0].external_record_id == "10"


@pytest.mark.asyncio
async def test_deposito_mesmo_codlocal_em_ambientes_diferentes_gera_associacoes_distintas(
    session: AsyncSession,
) -> None:
    tenant_uuid = uuid.uuid4()
    tenant_id = str(tenant_uuid)
    scope = await _insert_base_scope(session, tenant_uuid)
    await _seed_sankhya_runtime(session, tenant_id, environment="producao")
    deposito = await _create_deposito(session, tenant_uuid, scope["unidade_id"], nome="CD-01")

    helper = SankhyaExternalAssociationHelper(session)
    payload = {"CODLOCAL": "10", "NOMELOCAL": "CD-01", "TIPOLOCAL": "ARMAZEM"}
    await helper.sync_deposito(tenant_id, payload)
    await _set_runtime_environment(session, tenant_id, "homologacao")
    await helper.sync_deposito(tenant_id, payload)

    associations = await _list_associations(session, tenant_id=tenant_id, external_entity="LocalEstoque")
    assert len(associations) == 2
    assert {item.environment for item in associations} == {"producao", "homologacao"}
    assert all(item.local_record_id == str(deposito.id) for item in associations)


@pytest.mark.asyncio
async def test_conta_bancaria_cria_associacao_ativa_e_mantem_pendencias_de_banco_agencia_carteira(
    session: AsyncSession,
) -> None:
    tenant_uuid = uuid.uuid4()
    tenant_id = str(tenant_uuid)
    await _insert_base_scope(session, tenant_uuid)
    await _seed_sankhya_runtime(session, tenant_id)
    conta_local = await _create_conta_bancaria(
        session,
        tenant_uuid,
        nome="Conta Bradesco",
        banco="237",
        agencia="1234",
        conta="000123-4",
    )

    helper = SankhyaExternalAssociationHelper(session)
    conta_assoc = await helper.sync_conta_bancaria(
        tenant_id,
        {
            "CODBANCO": "237",
            "AGENCIA": "1234",
            "CONTA": "000123-4",
            "CARTEIRA": "109",
            "NOMECONTA": "Conta Bradesco",
        },
    )

    assert conta_assoc is not None
    assert conta_assoc.local_record_id == str(conta_local.id)
    assert conta_assoc.status == ExternalRecordAssociationStatus.ACTIVE.value
    assert conta_assoc.external_record_id == "237|1234|000123-4|109"

    banco_assoc = (await _list_associations(session, tenant_id=tenant_id, external_entity="Banco"))[0]
    agencia_assoc = (await _list_associations(session, tenant_id=tenant_id, external_entity="Agencia"))[0]
    carteira_assoc = (await _list_associations(session, tenant_id=tenant_id, external_entity="Carteira"))[0]

    assert banco_assoc.status == ExternalRecordAssociationStatus.PENDING.value
    assert agencia_assoc.status == ExternalRecordAssociationStatus.PENDING.value
    assert carteira_assoc.status == ExternalRecordAssociationStatus.PENDING.value


@pytest.mark.asyncio
async def test_centros_e_tipo_operacao_seguem_pendente_ou_ativo_conforme_master_local(
    session: AsyncSession,
) -> None:
    tenant_uuid = uuid.uuid4()
    tenant_id = str(tenant_uuid)
    await _insert_base_scope(session, tenant_uuid)
    await _seed_sankhya_runtime(session, tenant_id)
    await _create_tipo_operacao(session, tipo_operacao="PLANTIO")

    helper = SankhyaExternalAssociationHelper(session)
    tipo_assoc = await helper.sync_tipo_operacao(
        tenant_id,
        {
            "CODTIPOPER": "1001",
            "TIPOOPERACAO": "PLANTIO",
            "DESCRTIPOPER": "Plantio",
        },
    )
    centro_custo_assoc = await helper.sync_centro_custo(
        tenant_id,
        {"CODCENCUS": "CC-01"},
    )
    centro_resultado_assoc = await helper.sync_centro_resultado(
        tenant_id,
        {"CODCENRES": "CR-01"},
    )

    assert tipo_assoc is not None
    assert tipo_assoc.status == ExternalRecordAssociationStatus.ACTIVE.value
    assert tipo_assoc.local_record_id is not None
    assert centro_custo_assoc is not None
    assert centro_resultado_assoc is not None
    assert centro_custo_assoc.status == ExternalRecordAssociationStatus.PENDING.value
    assert centro_resultado_assoc.status == ExternalRecordAssociationStatus.PENDING.value
