import uuid
import pytest
from datetime import date, datetime, timedelta
from sqlalchemy import text, select
from core.exceptions import BusinessRuleError
from core.cadastros.equipamentos.models import Equipamento, EquipamentoCalibracao
from core.cadastros.equipamentos.schemas import EquipamentoCalibracaoCreate
from core.cadastros.equipamentos.service import EquipamentoCalibracaoService
from operacional.models.checklist import ChecklistModelo, ChecklistRealizado
from agricola.operacoes.models import OperacaoAgricola
from agricola.operacoes.schemas import OperacaoAgricolaCreate
from agricola.operacoes.service import OperacaoService
from agricola.caderno.models import CadernoCampoEntrada
from agricola.caderno.service import CadernoCampoService
from agricola.caderno.schemas import EventoCadernoOfflinePayload, EvidenciaOfflinePayload
from campo.models import DispositivoCampo
from core.models.auth import TenantUsuario, Usuario

# Helper functions to create required parent records in DB for the test
async def _criar_safra_e_requisitos(session, tenant_id):
    res_safra = await session.execute(
        text("SELECT id FROM safras WHERE tenant_id = :tenant_id AND ano_safra = '2026_calib' AND cultura = 'Café'"),
        {"tenant_id": tenant_id}
    )
    row_safra = res_safra.fetchone()
    if row_safra:
        safra_id = row_safra[0]
        await session.execute(
            text("UPDATE safras SET status = 'DESENVOLVIMENTO' WHERE id = :id"),
            {"id": safra_id}
        )
    else:
        safra_id = uuid.uuid4()
        await session.execute(
            text(
                "INSERT INTO safras (id, tenant_id, ano_safra, cultura, status, created_at, updated_at) "
                "VALUES (:id, :tenant_id, '2026_calib', 'Café', 'DESENVOLVIMENTO', NOW(), NOW())"
            ),
            {"id": safra_id, "tenant_id": tenant_id}
        )
    await session.commit()
    return safra_id


@pytest.mark.asyncio
async def test_fluxo_calibracao_sanitaria_bloqueio_e_liberacao(session, tenant_id, unidade_produtiva_id, talhao_id):
    safra_id = await _criar_safra_e_requisitos(session, tenant_id)

    # 1. Criar um pulverizador
    equipamento_id = uuid.uuid4()
    pulverizador = Equipamento(
        id=equipamento_id,
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        tipo="PULVERIZADOR",
        nome="Pulverizador John Deere 3000",
        status="ATIVO",
        ativo=True,
    )
    session.add(pulverizador)
    await session.commit()

    # 2. Tentar criar operação agrícola utilizando o pulverizador sem calibração
    op_svc = OperacaoService(session, tenant_id)
    op_data = OperacaoAgricolaCreate(
        safra_id=safra_id,
        talhao_id=talhao_id,
        tipo="PULVERIZAÇÃO",
        descricao="Pulverização de defensivos",
        data_realizada=date.today(),
        maquina_id=equipamento_id,
        area_aplicada_ha=1.0,
        insumos=[]
    )

    with pytest.raises(BusinessRuleError) as exc_info:
        await op_svc.criar(op_data)
    assert str(exc_info.value) == "Equipamento sem calibração válida."

    # 3. Criar uma calibração válida para o pulverizador
    calib_svc = EquipamentoCalibracaoService(session, tenant_id)
    calib_create = EquipamentoCalibracaoCreate(
        equipamento_id=equipamento_id,
        data_calibracao=date.today(),
        validade_ate=date.today() + timedelta(days=30),
        metodo="Copos coletores manuais",
        vazao=1.5,
        pressao=45.0,
        observacoes="Calibração realizada com sucesso."
    )
    res = await calib_svc._obter_contexto_safra_talhao_para_equipamento(equipamento_id)
    print(f"\nDEBUG RESOLVE CONTEXT: {res}\n")
    calib = await calib_svc.criar_calibracao(calib_create)
    await session.commit()

    # Assert hash documental foi gerado
    assert calib.hash_documental is not None
    assert len(calib.hash_documental) == 64

    # Assert evento de caderno de campo INSPECAO / CALIBRACAO_EQUIPAMENTO foi criado automaticamente
    caderno_svc = CadernoCampoService(session, tenant_id)
    evento_calib = await caderno_svc.obter_por_origem("CALIBRACAO_EQUIPAMENTO", str(calib.id))
    assert evento_calib is not None
    assert evento_calib.tipo_evento == "INSPECAO"
    assert "Copos coletores manuais" in evento_calib.descricao

    # 4. Tentar criar operação agrícola (agora tem calibração, mas falta liberação sanitária)
    with pytest.raises(BusinessRuleError) as exc_info:
        await op_svc.criar(op_data)
    assert str(exc_info.value) == "Liberação sanitária pendente."

    # 5. Criar ChecklistModelo e ChecklistRealizado de inspeção sanitária aprovado
    modelo_id = uuid.uuid4()
    checklist_modelo = ChecklistModelo(
        id=modelo_id,
        tenant_id=tenant_id,
        nome="Inspeção Sanitária de Pulverizador",
        tipo_equipamento="PULVERIZADOR",
        itens=[
            {"ordem": 1, "descricao": "Tanque limpo", "obrigatorio": True},
            {"ordem": 2, "descricao": "Filtros inspecionados", "obrigatorio": True}
        ],
        ativo=True
    )
    session.add(checklist_modelo)
    await session.commit()

    # Cria respostas válidas (OK)
    respostas = [
        {"ordem": 1, "descricao": "Tanque limpo", "status": "OK", "observacao": None},
        {"ordem": 2, "descricao": "Filtros inspecionados", "status": "OK", "observacao": None}
    ]

    # Preenche checklist realizado via lógica integrada
    from operacional.routers.checklist import realizar_checklist
    from operacional.schemas.checklist import ChecklistRealizadoCreate, ChecklistRespostaItem

    chk_create = ChecklistRealizadoCreate(
        equipamento_id=equipamento_id,
        modelo_id=modelo_id,
        operador_id=None,
        respostas=[ChecklistRespostaItem(**r) for r in respostas],
        observacoes_gerais="Sem contaminação detectada"
    )

    checklist_realizado = await realizar_checklist(chk_create, session, tenant_id)
    await session.commit()

    assert checklist_realizado.liberado_para_uso is True

    # Assert caderno de campo INSPECAO / CHECKLIST_SANITARIO foi gerado automaticamente
    evento_chk = await caderno_svc.obter_por_origem("CHECKLIST_SANITARIO", str(checklist_realizado.id))
    assert evento_chk is not None
    assert evento_chk.tipo_evento == "INSPECAO"
    assert "Liberação Sanitária aprovada" in evento_chk.descricao

    # 6. Criar operação agrícola (deve funcionar agora que tem calibração e liberação válidas)
    operacao = await op_svc.criar(op_data)
    await session.commit()
    assert operacao.id is not None
    assert operacao.maquina_id == equipamento_id


@pytest.mark.asyncio
async def test_isolamento_multi_tenant_calibracao(session, tenant_id):
    outro_tenant_id = uuid.uuid4()
    doc_num = outro_tenant_id.hex[:14]
    slug_str = f"outro_{outro_tenant_id.hex[:6]}"
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, slug, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, 'Outro Tenant', :slug, :documento, true, 0.0, 100.0, 'pt-BR', NOW(), NOW())"
        ),
        {"id": outro_tenant_id, "slug": slug_str, "documento": doc_num}
    )
    await session.commit()

    eq = Equipamento(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        tipo="PULVERIZADOR",
        nome="Sprayer original",
        status="ATIVO",
        ativo=True
    )
    session.add(eq)
    await session.commit()

    calib_svc_outro = EquipamentoCalibracaoService(session, outro_tenant_id)
    calib_create = EquipamentoCalibracaoCreate(
        equipamento_id=eq.id,
        data_calibracao=date.today(),
        validade_ate=date.today() + timedelta(days=15),
        metodo="Automático",
        vazao=2.0,
        pressao=50.0,
    )

    with pytest.raises(BusinessRuleError) as exc_info:
        await calib_svc_outro.criar_calibracao(calib_create)
    assert str(exc_info.value) == "Equipamento não localizado ou inacessível."


@pytest.mark.asyncio
async def test_sincronizacao_offline_pwa_calibracao_e_checklist(session, tenant_id, unidade_produtiva_id, talhao_id):
    safra_id = await _criar_safra_e_requisitos(session, tenant_id)

    device_id = uuid.uuid4()
    user_id = uuid.uuid4()
    rand_suffix = uuid.uuid4().hex[:8]
    usuario = Usuario(
        id=user_id,
        email=f"offline-{rand_suffix}@agrosaas.local",
        username=f"offline_{rand_suffix}",
        nome_completo="Operador Offline",
        ativo=True,
        is_superuser=False,
    )
    session.add(usuario)
    await session.flush()
    session.add(TenantUsuario(tenant_id=tenant_id, usuario_id=user_id, is_owner=True, status="ATIVO"))

    await session.execute(
        text(
            "INSERT INTO cadastros_pessoas (id, tenant_id, nome_exibicao, tipo, base_legal, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, 'Operador Offline', 'PF', 'CONTRATO', true, NOW(), NOW())"
        ),
        {"id": user_id, "tenant_id": tenant_id}
    )

    device = DispositivoCampo(
        id=device_id,
        tenant_id=tenant_id,
        user_id=user_id,
        nome="Mobile Device 01",
        status="ATIVO",
        fazenda_ids=[unidade_produtiva_id],
        expires_at=datetime.utcnow() + timedelta(days=365),
        created_at=datetime.utcnow()
    )
    session.add(device)

    eq_id = uuid.uuid4()
    eq = Equipamento(
        id=eq_id,
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        tipo="PULVERIZADOR",
        nome="Pulverizador Offline",
        status="ATIVO",
        ativo=True
    )
    session.add(eq)

    modelo_id = uuid.uuid4()
    modelo = ChecklistModelo(
        id=modelo_id,
        tenant_id=tenant_id,
        nome="Checklist Sanitário Offline",
        tipo_equipamento="PULVERIZADOR",
        itens=[{"ordem": 1, "descricao": "Tanque limpo", "obrigatorio": True}],
        ativo=True
    )
    session.add(modelo)
    await session.commit()

    # 1. Simular sync de evento de calibração offline
    local_id_calib = str(uuid.uuid4())
    payload_calib = EventoCadernoOfflinePayload(
        local_id=local_id_calib,
        tenant_id=tenant_id,
        safra_id=safra_id,
        talhao_id=talhao_id,
        tipo_evento="INSPECAO",
        client_created_at=datetime.utcnow(),
        client_updated_at=datetime.utcnow(),
        device_id=str(device_id),
        payload_operacional={
            "descricao": "Calibração via PWA",
            "calibracao": {
                "equipamento_id": str(eq_id),
                "data_calibracao": date.today().isoformat(),
                "validade_ate": (date.today() + timedelta(days=10)).isoformat(),
                "metodo": "PWA Manual",
                "vazao": 1.8,
                "pressao": 40.0,
                "observacoes": "PWA Sync"
            }
        }
    )

    caderno_svc = CadernoCampoService(session, tenant_id)
    resultados = await caderno_svc.sincronizar_eventos_offline([payload_calib], device=device)
    await session.commit()

    assert len(resultados) == 1
    assert resultados[0].status == "SYNCED"

    calib = await session.get(EquipamentoCalibracao, uuid.UUID(local_id_calib))
    assert calib is not None
    assert calib.metodo == "PWA Manual"

    evento_calib = await caderno_svc.obter_por_origem("CALIBRACAO_EQUIPAMENTO", local_id_calib)
    assert evento_calib is not None
    assert evento_calib.tipo_evento == "INSPECAO"

    # 2. Simular sync de evento de checklist sanitário offline
    local_id_chk = str(uuid.uuid4())
    payload_chk = EventoCadernoOfflinePayload(
        local_id=local_id_chk,
        tenant_id=tenant_id,
        safra_id=safra_id,
        talhao_id=talhao_id,
        tipo_evento="INSPECAO",
        client_created_at=datetime.utcnow(),
        client_updated_at=datetime.utcnow(),
        device_id=str(device_id),
        payload_operacional={
            "descricao": "Inspeção Sanitária via PWA",
            "checklist": {
                "equipamento_id": str(eq_id),
                "modelo_id": str(modelo_id),
                "liberado_para_uso": True,
                "respostas": [{"ordem": 1, "descricao": "Tanque limpo", "status": "OK", "observacao": None}],
                "observacoes_gerais": "Limpo via PWA"
            }
        }
    )

    resultados_chk = await caderno_svc.sincronizar_eventos_offline([payload_chk], device=device)
    await session.commit()

    assert len(resultados_chk) == 1
    assert resultados_chk[0].status == "SYNCED"

    chk_realizado = await session.get(ChecklistRealizado, uuid.UUID(local_id_chk))
    assert chk_realizado is not None
    assert chk_realizado.liberado_para_uso is True

    evento_chk = await caderno_svc.obter_por_origem("CHECKLIST_SANITARIO", local_id_chk)
    assert evento_chk is not None
    assert evento_chk.tipo_evento == "INSPECAO"
