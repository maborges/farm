import asyncio
import uuid
import datetime
from sqlalchemy import text, select
from core.database import async_session_maker
from core.models.tenant import Tenant
from core.models.unidade_produtiva import UnidadeProdutiva
from core.models.auth import Usuario, TenantUsuario
from core.cadastros.propriedades.models import AreaRural
from agricola.safras.models import Safra
from core.cadastros.pessoas.models import Pessoa, TipoRelacionamento, PessoaRelacionamento
from agricola.caderno.models import CadernoCampoEntrada
import agricola.cultivos.models

from agricola.caderno.schemas import EntradaCreate, EventoCadernoOfflinePayload
from agricola.caderno.service import CadernoCampoService
from core.exceptions import BusinessRuleError

TENANT_ID = uuid.uuid4()
UP1_ID = uuid.uuid4()
UP2_ID = uuid.uuid4()
USER_ID = uuid.uuid4()
SAFRA_ID = uuid.uuid4()
TALHAO1_ID = uuid.uuid4()
TALHAO2_ID = uuid.uuid4()
JOAO_ID = uuid.uuid4()
MARIA_ID = uuid.uuid4()
PRESTADOR_ID = uuid.uuid4()
TIPO_FUNC_ID = uuid.uuid4()

async def setup_db():
    async with async_session_maker() as session:
        # Create Tenant
        session.add(Tenant(id=TENANT_ID, nome="Dry Run Tenant", documento="00000000000"))
        await session.flush()
        # Create UPs
        session.add(UnidadeProdutiva(id=UP1_ID, tenant_id=TENANT_ID, nome="UP1", ativo=True))
        session.add(UnidadeProdutiva(id=UP2_ID, tenant_id=TENANT_ID, nome="UP2", ativo=True))
        await session.flush()
        # Create User
        session.add(Usuario(id=USER_ID, email="sup1@test.com", username="sup1", nome_completo="Supervisor UP1"))
        await session.flush()
        session.add(TenantUsuario(tenant_id=TENANT_ID, usuario_id=USER_ID, is_owner=True))
        await session.flush()
        # Create Safra
        session.add(Safra(id=SAFRA_ID, tenant_id=TENANT_ID, ano_safra="2025", cultura="Soja"))
        await session.flush()
        # Create AreaRural (Talhões)
        session.add(AreaRural(id=TALHAO1_ID, tenant_id=TENANT_ID, unidade_produtiva_id=UP1_ID, nome="Talhao UP1", tipo="TALHAO"))
        session.add(AreaRural(id=TALHAO2_ID, tenant_id=TENANT_ID, unidade_produtiva_id=UP2_ID, nome="Talhao UP2", tipo="TALHAO"))
        await session.flush()
        
        # Create Pessoas
        session.add(Pessoa(id=JOAO_ID, tenant_id=TENANT_ID, nome_exibicao="João", tipo="PF"))
        session.add(Pessoa(id=MARIA_ID, tenant_id=TENANT_ID, nome_exibicao="Maria", tipo="PF"))
        session.add(Pessoa(id=PRESTADOR_ID, tenant_id=TENANT_ID, nome_exibicao="Prestador Zé", tipo="PF"))
        
        # Create TipoRelacionamento
        session.add(TipoRelacionamento(id=TIPO_FUNC_ID, tenant_id=TENANT_ID, nome="Funcionário", codigo="FUNC"))
        
        await session.flush()
        
        # Create Relacionamentos
        session.add(PessoaRelacionamento(pessoa_id=JOAO_ID, tipo_id=TIPO_FUNC_ID, unidade_produtiva_id=UP1_ID))
        session.add(PessoaRelacionamento(pessoa_id=MARIA_ID, tipo_id=TIPO_FUNC_ID, unidade_produtiva_id=UP2_ID))
        session.add(PessoaRelacionamento(pessoa_id=PRESTADOR_ID, tipo_id=TIPO_FUNC_ID, unidade_produtiva_id=UP1_ID))
        
        await session.commit()

async def teardown_db():
    async with async_session_maker() as session:
        for stmt in [
            "DELETE FROM cadastros_pessoas WHERE tenant_id = :tid",
            "DELETE FROM safras WHERE tenant_id = :tid",
            "DELETE FROM cadastros_areas_rurais WHERE tenant_id = :tid",
            "DELETE FROM usuarios WHERE id = :uid",
            "DELETE FROM unidades_produtivas WHERE tenant_id = :tid",
            "DELETE FROM tenants WHERE id = :tid",
            "DELETE FROM cadastros_tipos_relacionamento WHERE id = :id"
        ]:
            try:
                await session.execute(text(stmt), {"tid": TENANT_ID, "id": TIPO_FUNC_ID, "uid": USER_ID})
            except Exception:
                pass
        try:
            await session.commit()
        except Exception:
            pass

async def run_scenario(name, coro):
    try:
        print(f"\\n--- Executando: {name} ---")
        await coro()
        print(f"\\033[92mPASS\\033[0m: {name}")
        return True
    except Exception as e:
        print(f"\\033[91mFAIL\\033[0m: {name} -> {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def cen_1_fluxo_feliz():
    async with async_session_maker() as session:
        svc = CadernoCampoService(session, TENANT_ID)
        entrada = await svc.criar_entrada(EntradaCreate(
            safra_id=SAFRA_ID,
            talhao_id=TALHAO1_ID,
            tipo="APLICACAO",
            data_registro=datetime.date.today(),
            executado_por_pessoa_id=JOAO_ID,
            origem_evento="WEB_MANUAL",
            descricao="Teste 1"
        ), usuario_id=USER_ID)
        await session.commit()
        assert entrada.executado_por_pessoa_id == JOAO_ID
        assert entrada.usuario_id == USER_ID

async def cen_2_outra_up():
    async with async_session_maker() as session:
        svc = CadernoCampoService(session, TENANT_ID)
        try:
            await svc.criar_entrada(EntradaCreate(
                safra_id=SAFRA_ID,
                talhao_id=TALHAO1_ID,  # UP1
                tipo="APLICACAO",
                data_registro=datetime.date.today(),
                executado_por_pessoa_id=MARIA_ID, # Maria is from UP2
                origem_evento="WEB_MANUAL",
            descricao="Teste 1"
            ), usuario_id=USER_ID)
            assert False, "Should have raised exception"
        except BusinessRuleError as e:
            assert "Unidade Produtiva" in str(e)

async def cen_3_alocacao_temporaria():
    async with async_session_maker() as session:
        # Add Joao to UP2
        session.add(PessoaRelacionamento(pessoa_id=JOAO_ID, tipo_id=TIPO_FUNC_ID, unidade_produtiva_id=UP2_ID))
        await session.commit()
        
        svc = CadernoCampoService(session, TENANT_ID)
        entrada = await svc.criar_entrada(EntradaCreate(
            safra_id=SAFRA_ID,
            talhao_id=TALHAO2_ID, # UP2
            tipo="APLICACAO",
            data_registro=datetime.date.today(),
            executado_por_pessoa_id=JOAO_ID,
            origem_evento="WEB_MANUAL",
            descricao="Teste 1"
        ), usuario_id=USER_ID)
        await session.commit()
        assert entrada.executado_por_pessoa_id == JOAO_ID

async def cen_4_prestador_sem_login():
    async with async_session_maker() as session:
        svc = CadernoCampoService(session, TENANT_ID)
        entrada = await svc.criar_entrada(EntradaCreate(
            safra_id=SAFRA_ID,
            talhao_id=TALHAO1_ID,
            tipo="APLICACAO",
            data_registro=datetime.date.today(),
            executado_por_pessoa_id=PRESTADOR_ID,
            origem_evento="WEB_MANUAL",
            descricao="Teste 1"
        ), usuario_id=USER_ID)
        await session.commit()
        assert entrada.executado_por_pessoa_id == PRESTADOR_ID
        
async def cen_5_user_vs_pessoa():
    async with async_session_maker() as session:
        svc = CadernoCampoService(session, TENANT_ID)
        entrada = await svc.criar_entrada(EntradaCreate(
            safra_id=SAFRA_ID,
            talhao_id=TALHAO1_ID,
            tipo="APLICACAO",
            data_registro=datetime.date.today(),
            executado_por_pessoa_id=JOAO_ID,
            origem_evento="WEB_MANUAL",
            descricao="Teste 1"
        ), usuario_id=USER_ID)
        assert entrada.usuario_id != entrada.executado_por_pessoa_id
        
async def cen_6_offline_pwa():
    async with async_session_maker() as session:
        svc = CadernoCampoService(session, TENANT_ID)
        from campo.models import DispositivoCampo
        # Create a mock device
        dev_id = uuid.uuid4()
        session.add(DispositivoCampo(
            id=dev_id, 
            tenant_id=TENANT_ID, 
            user_id=USER_ID, 
            nome="Dev", 
            status="ATIVO", 
            expires_at=datetime.datetime.now() + datetime.timedelta(days=1),
            fazenda_ids=[UP1_ID]
        ))
        await session.flush()
        
        # Test basic sync handling executado_por_pessoa_id
        evento_id = uuid.uuid4()
        ev = EventoCadernoOfflinePayload(
            local_id="evt-1",
            tenant_id=TENANT_ID,
            safra_id=SAFRA_ID,
            device_id=str(dev_id),
            tipo_evento="APLICACAO",
            client_created_at=datetime.datetime.now(),
            client_updated_at=datetime.datetime.now(),
            unidade_produtiva_id=UP1_ID,
            talhao_id=TALHAO1_ID,
            executado_por_pessoa_id=JOAO_ID,
            payload_operacional={
                "descricao": "Teste offline",
                "tipo": "APLICACAO",
                "data_registro": datetime.date.today().isoformat()
            }
        )
        resultados = await svc.sincronizar_eventos_offline([ev], device=await session.get(DispositivoCampo, dev_id))
        print("RESULTADOS:", resultados)
        await session.commit()
        
        # Verify
        entrada = (await session.execute(select(CadernoCampoEntrada).where(CadernoCampoEntrada.origem_id == "evt-1"))).scalar_one_or_none()
        assert entrada.executado_por_pessoa_id == JOAO_ID

async def cen_7_legado():
    async with async_session_maker() as session:
        svc = CadernoCampoService(session, TENANT_ID)
        entrada = await svc.criar_entrada(EntradaCreate(
            safra_id=SAFRA_ID,
            talhao_id=TALHAO1_ID,
            tipo="APLICACAO",
            data_registro=datetime.date.today(),
            executado_por_pessoa_id=None,
            origem_evento="WEB_MANUAL",
            descricao="Teste 1"
        ), usuario_id=USER_ID)
        assert entrada.executado_por_pessoa_id is None

async def main():
    try:
        await teardown_db()
        await setup_db()
        
        await run_scenario("Cenário 1: Fluxo Feliz", cen_1_fluxo_feliz)
        await run_scenario("Cenário 2: Pessoa de Outra UP", cen_2_outra_up)
        await run_scenario("Cenário 3: Alocação Temporária", cen_3_alocacao_temporaria)
        await run_scenario("Cenário 4: Executor Sem Login", cen_4_prestador_sem_login)
        await run_scenario("Cenário 5: User != Pessoa", cen_5_user_vs_pessoa)
        await run_scenario("Cenário 6: Offline PWA", cen_6_offline_pwa)
        await run_scenario("Cenário 7: Legado (sem executor)", cen_7_legado)
        
    finally:
        await teardown_db()

if __name__ == "__main__":
    asyncio.run(main())
