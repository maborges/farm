"""
EXEC-37 — Testes de integração: Auto-vínculo Fundiário (UnidadeProdutiva → ImovelRural → PropriedadeImovel)

Fluxo correto do domínio:
  1. UnidadeProdutiva + dado fundiário (CAR/NIRF/CCIR/SIGEF/Matrícula) → cria ou localiza ImovelRural
  2. Propriedade (entidade econômica) + ExploracaoRural → vínculo com UnidadeProdutiva
  3. Com ExploracaoRural existente → _sincronizar_vinculo_fundiario cria PropriedadeImovel

Cenários:
  1: CAR novo → cria ImovelRural
  2: CAR existente → reutiliza ImovelRural
  3: Com ExploracaoRural → cria PropriedadeImovel canônico
  4: Sem dado fundiário → não cria ImovelRural
  5: Sync idempotente — sem duplicatas
  6: SIGEF novo → cria ImovelRural identificado por SIGEF
  7: Matrícula nova → cria ImovelRural identificado por número de matrícula
"""

import pytest
import uuid
from decimal import Decimal
from datetime import date
from sqlalchemy import text, select

from core.models.unidade_produtiva import UnidadeProdutiva
from core.schemas.unidade_produtiva_input import UnidadeProdutivaCreate, UnidadeProdutivaUpdate
from core.services.unidade_produtiva_service import UnidadeProdutivaService
from imoveis.models.imovel import ImovelRural
from core.cadastros.propriedade_imovel.models import PropriedadeImovel
from core.cadastros.propriedades.propriedade_models import Propriedade, ExploracaoRural, NaturezaVinculo


TENANT_A_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000010")
TEST_USER_ID = uuid.UUID("eeeeeeee-0000-0000-0000-000000000005")


async def _set_tenant(session, tenant_id: uuid.UUID) -> None:
    """Configura variável de sessão PostgreSQL para RLS."""
    await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}';"))


async def _criar_propriedade_e_exploracao(
    session,
    tenant_id: uuid.UUID,
    unidade_id: uuid.UUID,
) -> Propriedade:
    """
    Helper: cria Propriedade econômica + ExploracaoRural vinculando-a à UnidadeProdutiva.
    Necessário para que PropriedadeImovel possa ser gerado no sync.
    """
    prop = Propriedade(
        tenant_id=tenant_id,
        nome=f"Propriedade Econômica {uuid.uuid4().hex[:6]}",
        ie_isento=True,
    )
    session.add(prop)
    await session.flush()

    expl = ExploracaoRural(
        tenant_id=tenant_id,
        propriedade_id=prop.id,
        unidade_produtiva_id=unidade_id,
        natureza=NaturezaVinculo.PROPRIA,
        data_inicio=date.today(),
    )
    session.add(expl)
    await session.flush()
    return prop


@pytest.fixture
def base_dados():
    return UnidadeProdutivaCreate(
        nome="Fazenda Auto Vínculo",
        tipo_propriedade="fazenda",
        area_total_ha=Decimal("150.0"),
        municipio="Testolândia",
        uf="SP",
    )


# ===========================================================================
# Cenário 1: Dados fundiários novos → cria ImovelRural
# ===========================================================================
@pytest.mark.asyncio
async def test_cenario_1_car_novo_cria_imovel_rural(session, tenant_id, base_dados):
    """Propriedade nova + CAR novo deve criar ImovelRural automaticamente."""
    import random
    await _set_tenant(session, tenant_id)

    service = UnidadeProdutivaService(session, tenant_id, user_id=TEST_USER_ID)
    dados = base_dados.model_copy(update={
        "codigo_car": f"SP{random.randint(100000000000, 999999999999)}"
    })

    unidade = await service.create_unidade_produtiva(dados)
    await session.commit()

    stmt = select(ImovelRural).where(
        ImovelRural.tenant_id == tenant_id,
        ImovelRural.car_numero == dados.codigo_car,
    )
    imovel = (await session.execute(stmt)).scalar_one_or_none()

    assert imovel is not None, "ImovelRural não foi criado automaticamente"
    assert imovel.nome == unidade.nome


# ===========================================================================
# Cenário 2: CAR já existente → reutiliza ImovelRural, sem duplicata
# ===========================================================================
@pytest.mark.asyncio
async def test_cenario_2_car_existente_reutiliza_imovel(session, tenant_id, base_dados):
    """CAR já cadastrado → ImovelRural deve ser reaproveitado sem duplicar."""
    import random
    await _set_tenant(session, tenant_id)

    car_numero = f"SP{random.randint(100000000000, 999999999999)}"

    # Cria UnidadeProdutiva prévia para satisfazer FK de ImovelRural
    service = UnidadeProdutivaService(session, tenant_id, user_id=TEST_USER_ID)
    unidade_previa = await service.create_unidade_produtiva(base_dados)
    await session.commit()

    # Cria ImovelRural vinculado à unidade prévia
    imovel_previo = ImovelRural(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_previa.id,
        nome="Imóvel Original",
        municipio="Testolândia",
        uf="SP",
        area_total_ha=Decimal("200.0"),
        car_numero=car_numero,
        created_by=TEST_USER_ID,
    )
    session.add(imovel_previo)
    await session.commit()

    # Nova UnidadeProdutiva com o mesmo CAR
    await _set_tenant(session, tenant_id)
    dados_novos = base_dados.model_copy(update={"codigo_car": car_numero, "nome": "Fazenda Nova"})
    await service.create_unidade_produtiva(dados_novos)
    await session.commit()

    await _set_tenant(session, tenant_id)
    stmt = select(ImovelRural).where(
        ImovelRural.tenant_id == tenant_id,
        ImovelRural.car_numero == car_numero,
    )
    imoveis = (await session.execute(stmt)).scalars().all()

    assert len(imoveis) == 1, f"Esperado 1 ImovelRural, encontrado {len(imoveis)}"
    assert imoveis[0].id == imovel_previo.id


# ===========================================================================
# Cenário 3: Com ExploracaoRural → PropriedadeImovel criado ao sincronizar
# ===========================================================================
@pytest.mark.asyncio
async def test_cenario_3_com_exploracao_cria_vinculo_canonico(session, tenant_id, base_dados):
    """
    Quando existe ExploracaoRural (Propriedade ↔ UnidadeProdutiva),
    o sync deve criar PropriedadeImovel automaticamente.
    """
    import random
    await _set_tenant(session, tenant_id)

    car_numero = f"SP{random.randint(100000000000, 999999999999)}"
    service = UnidadeProdutivaService(session, tenant_id, user_id=TEST_USER_ID)
    dados = base_dados.model_copy(update={"codigo_car": car_numero})

    # 1. Cria unidade com dado fundiário → ImovelRural criado
    unidade = await service.create_unidade_produtiva(dados)
    await session.commit()

    # 2. Cria Propriedade econômica + ExploracaoRural
    await _set_tenant(session, tenant_id)
    prop = await _criar_propriedade_e_exploracao(session, tenant_id, unidade.id)
    await session.commit()

    # 3. Dispara sync via update → PropriedadeImovel deve ser criado
    await _set_tenant(session, tenant_id)
    await service.update(unidade.id, UnidadeProdutivaUpdate(nome="Fazenda Sync Teste"))
    await session.commit()

    # Verifica ImovelRural
    await _set_tenant(session, tenant_id)
    stmt_imovel = select(ImovelRural).where(
        ImovelRural.tenant_id == tenant_id,
        ImovelRural.car_numero == car_numero,
    )
    imovel = (await session.execute(stmt_imovel)).scalar_one_or_none()
    assert imovel is not None

    # Verifica PropriedadeImovel canônico
    stmt_vinculo = select(PropriedadeImovel).where(
        PropriedadeImovel.tenant_id == tenant_id,
        PropriedadeImovel.propriedade_id == prop.id,
        PropriedadeImovel.imovel_rural_id == imovel.id,
    )
    vinculo = (await session.execute(stmt_vinculo)).scalar_one_or_none()
    assert vinculo is not None, "PropriedadeImovel canônico não foi criado"
    assert vinculo.tipo_vinculo == "PROPRIEDADE_PRINCIPAL"
    assert vinculo.vinculo_principal is True


# ===========================================================================
# Cenário 4: Sem dado fundiário → NÃO cria ImovelRural
# ===========================================================================
@pytest.mark.asyncio
async def test_cenario_4_sem_dado_fundiario_nao_cria_imovel(session, tenant_id, base_dados):
    """Sem CAR/NIRF/CCIR → ImovelRural NÃO deve ser criado."""
    await _set_tenant(session, tenant_id)

    service = UnidadeProdutivaService(session, tenant_id, user_id=TEST_USER_ID)
    dados = base_dados.model_copy()
    dados.codigo_car = None
    dados.nirf = None
    dados.ccir = None

    unidade = await service.create_unidade_produtiva(dados)
    await session.commit()

    await _set_tenant(session, tenant_id)
    stmt = select(ImovelRural).where(
        ImovelRural.tenant_id == tenant_id,
        ImovelRural.unidade_produtiva_id == unidade.id,
    )
    imoveis = (await session.execute(stmt)).scalars().all()
    assert len(imoveis) == 0, "ImovelRural foi criado indevidamente sem dado fundiário"


# ===========================================================================
# Cenário 5: Sync idempotente — não duplica ao chamar update 2x
# ===========================================================================
@pytest.mark.asyncio
async def test_cenario_5_sync_idempotente(session, tenant_id, base_dados):
    """Chamar update múltiplas vezes não deve duplicar ImovelRural nem PropriedadeImovel."""
    import random
    await _set_tenant(session, tenant_id)

    car_numero = f"SP{random.randint(100000000000, 999999999999)}"
    service = UnidadeProdutivaService(session, tenant_id, user_id=TEST_USER_ID)
    dados = base_dados.model_copy(update={"codigo_car": car_numero})

    unidade = await service.create_unidade_produtiva(dados)
    await session.commit()

    await _set_tenant(session, tenant_id)
    prop = await _criar_propriedade_e_exploracao(session, tenant_id, unidade.id)
    await session.commit()

    # 1ª sync
    await _set_tenant(session, tenant_id)
    await service.update(unidade.id, UnidadeProdutivaUpdate(nome="Sync 1"))
    await session.commit()

    # 2ª sync (idempotente)
    await _set_tenant(session, tenant_id)
    await service.update(unidade.id, UnidadeProdutivaUpdate(nome="Sync 2"))
    await session.commit()

    await _set_tenant(session, tenant_id)
    stmt_imovel = select(ImovelRural).where(
        ImovelRural.tenant_id == tenant_id,
        ImovelRural.car_numero == car_numero,
    )
    qtd_imoveis = len((await session.execute(stmt_imovel)).scalars().all())

    stmt_vinculo = select(PropriedadeImovel).where(
        PropriedadeImovel.tenant_id == tenant_id,
        PropriedadeImovel.propriedade_id == prop.id,
    )
    qtd_vinculos = len((await session.execute(stmt_vinculo)).scalars().all())

    assert qtd_imoveis == 1, f"Esperado 1 ImovelRural, encontrado {qtd_imoveis}"
    assert qtd_vinculos == 1, f"Esperado 1 PropriedadeImovel, encontrado {qtd_vinculos}"


# ===========================================================================
# Cenário 6: SIGEF novo → cria ImovelRural identificado por SIGEF
# ===========================================================================
@pytest.mark.asyncio
async def test_cenario_6_sigef_novo_cria_imovel_rural(session, tenant_id, base_dados):
    """Propriedade nova + SIGEF deve criar ImovelRural automaticamente com sigef_codigo."""
    import random
    await _set_tenant(session, tenant_id)

    sigef_codigo = f"BR-SP-{random.randint(100000, 999999)}-A"
    service = UnidadeProdutivaService(session, tenant_id, user_id=TEST_USER_ID)
    dados = base_dados.model_copy(update={"sigef_codigo": sigef_codigo})

    unidade = await service.create_unidade_produtiva(dados)
    await session.commit()

    await _set_tenant(session, tenant_id)
    stmt = select(ImovelRural).where(
        ImovelRural.tenant_id == tenant_id,
        ImovelRural.sigef_codigo == sigef_codigo,
    )
    imovel = (await session.execute(stmt)).scalar_one_or_none()

    assert imovel is not None, "ImovelRural não foi criado automaticamente pelo SIGEF"
    assert imovel.sigef_codigo == sigef_codigo
    assert imovel.unidade_produtiva_id == unidade.id


# ===========================================================================
# Cenário 7: Matrícula nova → cria ImovelRural com numero_matricula
# ===========================================================================
@pytest.mark.asyncio
async def test_cenario_7_matricula_nova_cria_imovel_rural(session, tenant_id, base_dados):
    """Propriedade nova + numero_matricula deve criar ImovelRural com a matrícula informada."""
    import random
    await _set_tenant(session, tenant_id)

    numero_matricula = f"{random.randint(10000, 99999)}"
    service = UnidadeProdutivaService(session, tenant_id, user_id=TEST_USER_ID)
    dados = base_dados.model_copy(update={"numero_matricula": numero_matricula})

    unidade = await service.create_unidade_produtiva(dados)
    await session.commit()

    await _set_tenant(session, tenant_id)
    stmt = select(ImovelRural).where(
        ImovelRural.tenant_id == tenant_id,
        ImovelRural.numero_matricula == numero_matricula,
    )
    imovel = (await session.execute(stmt)).scalar_one_or_none()

    assert imovel is not None, "ImovelRural não foi criado automaticamente pela Matrícula"
    assert imovel.numero_matricula == numero_matricula
    assert imovel.unidade_produtiva_id == unidade.id
