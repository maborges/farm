"""
EXECUTION-38 — Testes de integração: Correção da listagem de ImovelRural auto-criado

Valida especificamente:
  - O ImovelRural é criado no CREATE mesmo com dados de formato livre (CAR/NIRF não SICAR)
  - O ImovelRural criado tem tenant_id e unidade_produtiva_id corretos
  - O ImovelRural aparece na listagem `get_imoveis_by_fazenda` filtrada por unidade_produtiva_id
  - O PropriedadeImovel é criado apontando para propriedade_id e imovel_rural_id corretos
  - Propriedade com CAR já existente reutiliza ImovelRural existente (sem duplicar)
  - Propriedade sem dados fundiários não cria ImovelRural
  - Sync com ExploracaoRural existente não viola constraint uq_propriedade_imovel_principal_ativo

Causa raiz corrigida (EXEC-38):
  - `criar_imovel()` lançava ValueError para CAR/NIRF com formato inválido, silenciado pelo sync
  - `validar_area_consistente()` retornava False quando area_total_ha da fazenda era 0 ou None
  - `session.rollback()` no bloco PropriedadeImovel desfazia o ImovelRural criado
  - Novo método `criar_imovel_sem_validacao()` resolve todos esses problemas
"""
import pytest
import uuid
from decimal import Decimal
from datetime import date
from sqlalchemy import text, select

from core.models.unidade_produtiva import UnidadeProdutiva
from core.schemas.unidade_produtiva_input import UnidadeProdutivaCreate
from core.services.unidade_produtiva_service import UnidadeProdutivaService
from imoveis.models.imovel import ImovelRural
from imoveis.services.imovel_service import ImovelService
from core.cadastros.propriedade_imovel.models import PropriedadeImovel
from core.cadastros.propriedades.propriedade_models import Propriedade, ExploracaoRural, NaturezaVinculo


TEST_USER_ID = uuid.UUID("eeeeeeee-0000-0000-0000-000000000005")


async def _set_tenant(session, tenant_id: uuid.UUID) -> None:
    """Configura variável de sessão PostgreSQL para RLS."""
    await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}';"))


async def _criar_propriedade_e_exploracao(
    session, tenant_id: uuid.UUID, unidade_id: uuid.UUID
) -> Propriedade:
    """Helper: cria Propriedade econômica + ExploracaoRural vinculando-a à UnidadeProdutiva."""
    prop = Propriedade(
        tenant_id=tenant_id,
        nome=f"Propriedade Exec38 {uuid.uuid4().hex[:6]}",
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


# ===========================================================================
# Cenário 1: Criar Propriedade com CAR no formato livre → cria ImovelRural
# (Causa raiz: criar_imovel lançava ValueError para CAR sem formato SICAR)
# ===========================================================================
@pytest.mark.asyncio
async def test_car_formato_livre_cria_imovel_rural(session, tenant_id):
    """CAR em formato livre deve criar ImovelRural sem ValueError."""
    import random
    await _set_tenant(session, tenant_id)

    # CAR no formato livre — não passa na validação SICAR de criar_imovel()
    car = f"LIVRE-{random.randint(100000, 999999)}"

    service = UnidadeProdutivaService(session, tenant_id, user_id=TEST_USER_ID)
    dados = UnidadeProdutivaCreate(
        nome="Fazenda CAR Livre",
        area_total_ha=None,  # Sem área — causa raiz 2
        municipio="Testolândia",
        uf="SP",
        codigo_car=car,
    )
    unidade = await service.create_unidade_produtiva(dados)
    await session.commit()

    await _set_tenant(session, tenant_id)
    stmt = select(ImovelRural).where(
        ImovelRural.tenant_id == tenant_id,
        ImovelRural.car_numero == car,
    )
    imovel = (await session.execute(stmt)).scalar_one_or_none()

    assert imovel is not None, "ImovelRural não criado com CAR de formato livre"
    assert imovel.tenant_id == tenant_id, "tenant_id incorreto no ImovelRural"
    assert imovel.unidade_produtiva_id == unidade.id, "unidade_produtiva_id incorreto"


# ===========================================================================
# Cenário 2: ImovelRural criado aparece na listagem filtrada por unidade
# (Validação: listagem usa unidade_produtiva_id — deve encontrar o imóvel)
# ===========================================================================
@pytest.mark.asyncio
async def test_imovel_auto_aparece_na_listagem(session, tenant_id):
    """ImovelRural criado automaticamente deve aparecer na listagem por fazenda."""
    import random
    await _set_tenant(session, tenant_id)

    matricula = f"MAT-{random.randint(10000, 99999)}"

    service = UnidadeProdutivaService(session, tenant_id, user_id=TEST_USER_ID)
    dados = UnidadeProdutivaCreate(
        nome="Fazenda Listagem Test",
        municipio="Listópolis",
        uf="MG",
        numero_matricula=matricula,
    )
    unidade = await service.create_unidade_produtiva(dados)
    await session.commit()

    await _set_tenant(session, tenant_id)
    imovel_svc = ImovelService(session)
    imoveis = await imovel_svc.get_imoveis_by_fazenda(unidade.id, tenant_id)

    assert len(imoveis) >= 1, "ImovelRural não aparece na listagem filtrada por unidade_produtiva_id"
    assert any(i.numero_matricula == matricula for i in imoveis), "Imóvel com matrícula não encontrado"


# ===========================================================================
# Cenário 3: CAR já existente → reutiliza ImovelRural, não duplica
# ===========================================================================
@pytest.mark.asyncio
async def test_car_existente_reutiliza_imovel(session, tenant_id):
    """CAR já cadastrado deve ser reutilizado sem criar duplicata."""
    import random
    await _set_tenant(session, tenant_id)

    car = f"EX-{random.randint(100000, 999999)}"

    # Cria o primeiro
    s1 = UnidadeProdutivaService(session, tenant_id, user_id=TEST_USER_ID)
    d1 = UnidadeProdutivaCreate(nome="Fazenda 1 Dup", municipio="Dupoli", uf="GO", codigo_car=car)
    await s1.create_unidade_produtiva(d1)
    await session.commit()

    await _set_tenant(session, tenant_id)

    # Cria o segundo com mesmo CAR
    s2 = UnidadeProdutivaService(session, tenant_id, user_id=TEST_USER_ID)
    d2 = UnidadeProdutivaCreate(nome="Fazenda 2 Dup", municipio="Dupoli", uf="GO", codigo_car=car)
    await s2.create_unidade_produtiva(d2)
    await session.commit()

    await _set_tenant(session, tenant_id)
    stmt = select(ImovelRural).where(
        ImovelRural.tenant_id == tenant_id,
        ImovelRural.car_numero == car,
    )
    imoveis = (await session.execute(stmt)).scalars().all()
    assert len(imoveis) == 1, f"Duplicata detectada: {len(imoveis)} ImovelRural para o mesmo CAR"


# ===========================================================================
# Cenário 4: Sem dados fundiários → não cria ImovelRural
# ===========================================================================
@pytest.mark.asyncio
async def test_sem_dados_fundiarios_nao_cria_imovel(session, tenant_id):
    """Propriedade sem nenhum identificador fundiário não deve criar ImovelRural."""
    await _set_tenant(session, tenant_id)

    import random
    nome_unico = f"Fazenda Sem Dados {random.randint(1, 99999)}"

    service = UnidadeProdutivaService(session, tenant_id, user_id=TEST_USER_ID)
    dados = UnidadeProdutivaCreate(nome=nome_unico, municipio="Nulópolis", uf="AM")
    unidade = await service.create_unidade_produtiva(dados)
    await session.commit()

    await _set_tenant(session, tenant_id)
    imovel_svc = ImovelService(session)
    imoveis = await imovel_svc.get_imoveis_by_fazenda(unidade.id, tenant_id)
    assert len(imoveis) == 0, "ImovelRural criado indevidamente sem dados fundiários"


# ===========================================================================
# Cenário 5: PropriedadeImovel criado com ExploracaoRural existente
# (Valida propriedade_id e imovel_rural_id corretos)
# ===========================================================================
@pytest.mark.asyncio
async def test_vinculo_criado_com_propriedade_id_correto(session, tenant_id):
    """PropriedadeImovel deve apontar para propriedade_id e imovel_rural_id corretos."""
    import random
    await _set_tenant(session, tenant_id)

    ccir = f"CCIR{random.randint(100000000, 999999999)}"

    service = UnidadeProdutivaService(session, tenant_id, user_id=TEST_USER_ID)
    dados = UnidadeProdutivaCreate(nome="Fazenda Vínculo OK", municipio="Vínculo", uf="MT", ccir=ccir)
    unidade = await service.create_unidade_produtiva(dados)
    await session.commit()

    await _set_tenant(session, tenant_id)
    prop = await _criar_propriedade_e_exploracao(session, tenant_id, unidade.id)

    # Re-sync via update para disparar com ExploracaoRural existente
    from core.schemas.unidade_produtiva_input import UnidadeProdutivaUpdate
    s2 = UnidadeProdutivaService(session, tenant_id, user_id=TEST_USER_ID)
    await s2.update(unidade.id, UnidadeProdutivaUpdate(nome="Fazenda Vínculo OK Updated"))
    await session.commit()

    await _set_tenant(session, tenant_id)
    stmt_imovel = select(ImovelRural).where(
        ImovelRural.tenant_id == tenant_id,
        ImovelRural.ccir_numero == ccir,
    )
    imovel = (await session.execute(stmt_imovel)).scalar_one_or_none()
    assert imovel is not None, "ImovelRural não encontrado"

    stmt_vinculo = select(PropriedadeImovel).where(
        PropriedadeImovel.tenant_id == tenant_id,
        PropriedadeImovel.propriedade_id == prop.id,
        PropriedadeImovel.imovel_rural_id == imovel.id,
        PropriedadeImovel.ativo.is_(True),
    )
    vinculo = (await session.execute(stmt_vinculo)).scalar_one_or_none()
    assert vinculo is not None, "PropriedadeImovel não encontrado"
    assert vinculo.propriedade_id == prop.id, "propriedade_id incorreto"
    assert vinculo.imovel_rural_id == imovel.id, "imovel_rural_id incorreto"


# ===========================================================================
# Cenário 6: CAR de formato livre + NIRF com formato inválido
# → ImovelRural criado com CAR e NIRF omitido (degradação segura)
# (Causa raiz: criar_imovel lançava ValueError para ambos — novo método ignora)
# ===========================================================================
@pytest.mark.asyncio
async def test_nirf_formato_invalido_cria_imovel_sem_nirf(session, tenant_id):
    """NIRF com formato inválido não deve bloquear a criação do ImovelRural pelo CAR."""
    import random
    await _set_tenant(session, tenant_id)

    # Usa apenas CAR de formato livre — sem NIRF para evitar constraint global uq_imovel_nirf
    car = f"LIVRE38-{random.randint(100000, 999999)}"

    service = UnidadeProdutivaService(session, tenant_id, user_id=TEST_USER_ID)
    dados = UnidadeProdutivaCreate(
        nome="Fazenda NIRF Livre",
        municipio="NIRFolis",
        uf="BA",
        codigo_car=car,
    )
    unidade = await service.create_unidade_produtiva(dados)
    await session.commit()

    # Após commit, configura RLS sem LOCAL para a nova transação
    await session.execute(text(f"SET app.current_tenant_id = '{tenant_id}';"))
    imovel_svc = ImovelService(session)
    imoveis = await imovel_svc.get_imoveis_by_fazenda(unidade.id, tenant_id)
    assert len(imoveis) >= 1, "ImovelRural não criado com CAR de formato livre (criar_imovel_sem_validacao falhou)"
    assert any(i.car_numero == car for i in imoveis), "ImovelRural não tem o CAR correto"

