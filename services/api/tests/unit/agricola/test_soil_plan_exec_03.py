from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.analises_solo.models import AnaliseSolo
from agricola.analises_solo.service import AnaliseSoloService
from agricola.cultivos.service import CultivoService
from agricola.tarefas.models import SafraTarefa
from agricola.tarefas.router import criar_tarefa
from agricola.tarefas.schemas import PlanejarOperacaoRequest, TarefaCreate
from agricola.tarefas.service import TarefaService
from core.exceptions import BusinessRuleError


pytestmark = pytest.mark.asyncio


def _make_session() -> AsyncMock:
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    return session


def _make_analise(tenant_id: uuid.UUID, talhao_id: uuid.UUID) -> AnaliseSolo:
    return AnaliseSolo(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        talhao_id=talhao_id,
    )


def _recomendacoes_completas() -> dict:
    return {
        "calagem": {"necessaria": True, "dose_t_ha": 2.0, "observacao": "obs"},
        "fosforo": {"rec_p2o5_kg_ha": 40.0, "observacao": "obs"},
        "potassio": {"rec_k2o_kg_ha": 30.0, "observacao": "obs"},
        "nitrogenio": {"rec_n_kg_ha": 20.0, "observacao": "obs"},
    }


def _talhao(area_ha: float = 10.0):
    talhao = MagicMock()
    talhao.area_hectares_manual = area_ha
    talhao.area_hectares = area_ha
    return talhao


# ---------------------------------------------------------------------
# 1. Potássio não quebra mais o fluxo (PRECOS["K2O"])
# ---------------------------------------------------------------------


async def test_potassio_gera_tarefa_adubacao_potassio_sem_keyerror():
    tenant_id = uuid.uuid4()
    talhao_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    analise = _make_analise(tenant_id, talhao_id)

    session = _make_session()
    service = AnaliseSoloService(session, tenant_id)
    service.get_or_fail = AsyncMock(return_value=analise)
    service.gerar_recomendacoes = AsyncMock(
        return_value={"potassio": {"rec_k2o_kg_ha": 30.0, "observacao": "obs"}}
    )
    service._tarefa_ativa_existente = AsyncMock(return_value=None)

    tarefa_criada = SafraTarefa(
        id=uuid.uuid4(), tenant_id=tenant_id, tipo="ADUBACAO_POTASSIO", status="PENDENTE_APROVACAO"
    )

    with patch("agricola.analises_solo.service.SafraService") as safra_service_mock:
        safra_service_mock.return_value.get_or_fail = AsyncMock(return_value=MagicMock())
        session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=_talhao()))

        with patch.object(TarefaService, "criar", new=AsyncMock(return_value=tarefa_criada)):
            resultado = await service.vincular_e_gerar_tarefas(analise.id, safra_id)

    assert resultado["quantidade_gerada"] == 1
    assert resultado["tarefas_geradas"] == [tarefa_criada.id]
    assert resultado["quantidade_existente"] == 0


# ---------------------------------------------------------------------
# 2. Idempotência: segunda chamada não duplica
# ---------------------------------------------------------------------


async def test_segunda_chamada_nao_duplica_tarefas_ativas():
    tenant_id = uuid.uuid4()
    talhao_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    analise = _make_analise(tenant_id, talhao_id)

    session = _make_session()
    service = AnaliseSoloService(session, tenant_id)
    service.get_or_fail = AsyncMock(return_value=analise)
    service.gerar_recomendacoes = AsyncMock(
        return_value={"potassio": {"rec_k2o_kg_ha": 30.0, "observacao": "obs"}}
    )

    tarefa_existente = SafraTarefa(
        id=uuid.uuid4(), tenant_id=tenant_id, tipo="ADUBACAO_POTASSIO", status="PENDENTE_APROVACAO"
    )
    service._tarefa_ativa_existente = AsyncMock(return_value=tarefa_existente)

    with patch("agricola.analises_solo.service.SafraService") as safra_service_mock:
        safra_service_mock.return_value.get_or_fail = AsyncMock(return_value=MagicMock())
        session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=_talhao()))

        with patch.object(TarefaService, "criar", new=AsyncMock()) as criar_mock:
            resultado = await service.vincular_e_gerar_tarefas(analise.id, safra_id)

    criar_mock.assert_not_awaited()
    assert resultado["quantidade_gerada"] == 0
    assert resultado["tarefas_existentes"] == [tarefa_existente.id]


async def test_tarefa_cancelada_permite_gerar_nova_tarefa_equivalente():
    tenant_id = uuid.uuid4()
    talhao_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    analise = _make_analise(tenant_id, talhao_id)

    session = _make_session()
    service = AnaliseSoloService(session, tenant_id)
    service.get_or_fail = AsyncMock(return_value=analise)
    service.gerar_recomendacoes = AsyncMock(
        return_value={"potassio": {"rec_k2o_kg_ha": 30.0, "observacao": "obs"}}
    )
    # Tarefa CANCELADA não deve ser considerada "ativa" -> _tarefa_ativa_existente retorna None
    service._tarefa_ativa_existente = AsyncMock(return_value=None)

    nova_tarefa = SafraTarefa(id=uuid.uuid4(), tenant_id=tenant_id, tipo="ADUBACAO_POTASSIO", status="PENDENTE_APROVACAO")

    with patch("agricola.analises_solo.service.SafraService") as safra_service_mock:
        safra_service_mock.return_value.get_or_fail = AsyncMock(return_value=MagicMock())
        session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=_talhao()))

        with patch.object(TarefaService, "criar", new=AsyncMock(return_value=nova_tarefa)):
            resultado = await service.vincular_e_gerar_tarefas(analise.id, safra_id)

    assert resultado["quantidade_gerada"] == 1


# ---------------------------------------------------------------------
# 3. Validação de safra (tenant)
# ---------------------------------------------------------------------


async def test_safra_de_outro_tenant_e_rejeitada():
    tenant_id = uuid.uuid4()
    talhao_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    analise = _make_analise(tenant_id, talhao_id)

    session = _make_session()
    service = AnaliseSoloService(session, tenant_id)
    service.get_or_fail = AsyncMock(return_value=analise)

    with patch("agricola.analises_solo.service.SafraService") as SafraServiceMock:
        from core.exceptions import EntityNotFoundError

        SafraServiceMock.return_value.get_or_fail = AsyncMock(
            side_effect=EntityNotFoundError("Safra", str(safra_id))
        )

        with pytest.raises(EntityNotFoundError):
            await service.vincular_e_gerar_tarefas(analise.id, safra_id)


# ---------------------------------------------------------------------
# 4. Aprovação obrigatória antes de gerar_operacao_planejada
# ---------------------------------------------------------------------


def _make_tarefa(*, status: str) -> SafraTarefa:
    return SafraTarefa(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        safra_id=uuid.uuid4(),
        talhao_id=uuid.uuid4(),
        origem="SOLO",
        tipo="ADUBACAO_POTASSIO",
        descricao="Adubação de Potássio",
        criticidade="NORMAL",
        prioridade="ALTA",
        status=status,
        area_ha=10.0,
    )


def _mock_result(first_return):
    return MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=first_return))))


async def test_tarefa_pendente_aprovacao_bloqueia_operacao_planejada():
    session = _make_session()
    tenant_id = uuid.uuid4()
    tarefa = _make_tarefa(status="PENDENTE_APROVACAO")
    service = TarefaService(session, tenant_id)

    # gerar_operacao_planejada busca a tarefa via SELECT ... FOR UPDATE (lock
    # contra corrida em cliques duplicados), não mais via self._get().
    session.execute.return_value = _mock_result(tarefa)

    dados = PlanejarOperacaoRequest(data_prevista=date.today(), insumos=[])

    with pytest.raises(BusinessRuleError):
        await service.gerar_operacao_planejada(tarefa.id, dados)


async def test_tarefa_aprovada_gera_operacao_planejada():
    session = _make_session()
    tenant_id = uuid.uuid4()
    tarefa = _make_tarefa(status="APROVADA")
    service = TarefaService(session, tenant_id)

    # 1ª chamada: SELECT ... FOR UPDATE da tarefa (lock). 2ª chamada: checagem
    # de operação PLANEJADA já existente (nenhuma ainda).
    session.execute.side_effect = [_mock_result(tarefa), _mock_result(None)]
    session.get = AsyncMock(return_value=None)  # AreaRural do talhão (sem fazenda legada no teste)

    operacao_criada = MagicMock(status="PLANEJADA")
    dados = PlanejarOperacaoRequest(data_prevista=date.today(), insumos=[])

    with patch("agricola.operacoes.service.OperacaoService.criar", new=AsyncMock(return_value=operacao_criada)), \
         patch("campo.service.TarefaProgramadaService.criar_vinculada_operacao", new=AsyncMock()):
        operacao = await service.gerar_operacao_planejada(tarefa.id, dados)

    assert operacao.status == "PLANEJADA"


# ---------------------------------------------------------------------
# 5. Idempotência no caminho paralelo: TarefaService.criar() chamado
#    diretamente com origem="SOLO" (usado pelo cultivo-analise-drawer,
#    que não passa por AnaliseSoloService.vincular_e_gerar_tarefas)
# ---------------------------------------------------------------------


def _tarefa_create_solo(*, talhao_id, analise_solo_id, tipo="ADUBACAO_POTASSIO") -> TarefaCreate:
    return TarefaCreate(
        talhao_id=talhao_id,
        analise_solo_id=analise_solo_id,
        origem="SOLO",
        tipo=tipo,
        descricao="Adubação de Potássio — Dose: 30.0 kg/ha de K2O",
    )


async def test_criar_direto_com_origem_solo_reaproveita_tarefa_ativa_existente():
    tenant_id = uuid.uuid4()
    talhao_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    analise_solo_id = uuid.uuid4()

    session = _make_session()
    service = TarefaService(session, tenant_id)

    tarefa_existente = SafraTarefa(
        id=uuid.uuid4(), tenant_id=tenant_id, tipo="ADUBACAO_POTASSIO", status="PENDENTE_APROVACAO"
    )
    service._tarefa_solo_ativa_existente = AsyncMock(return_value=tarefa_existente)

    dados = _tarefa_create_solo(talhao_id=talhao_id, analise_solo_id=analise_solo_id)
    resultado = await service.criar(safra_id, dados)

    assert resultado is tarefa_existente
    session.add.assert_not_called()


async def test_criar_direto_com_origem_solo_cria_quando_nao_ha_tarefa_ativa():
    tenant_id = uuid.uuid4()
    talhao_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    analise_solo_id = uuid.uuid4()

    session = _make_session()
    service = TarefaService(session, tenant_id)
    service._tarefa_solo_ativa_existente = AsyncMock(return_value=None)

    dados = _tarefa_create_solo(talhao_id=talhao_id, analise_solo_id=analise_solo_id)
    resultado = await service.criar(safra_id, dados)

    session.add.assert_called_once()
    assert resultado.origem == "SOLO"
    assert resultado.status == "PENDENTE_APROVACAO"


async def test_criar_direto_origem_manual_ignora_checagem_de_idempotencia():
    tenant_id = uuid.uuid4()
    talhao_id = uuid.uuid4()
    safra_id = uuid.uuid4()

    session = _make_session()
    service = TarefaService(session, tenant_id)
    service._tarefa_solo_ativa_existente = AsyncMock()

    dados = TarefaCreate(
        talhao_id=talhao_id,
        origem="MANUAL",
        tipo="OUTRO",
        descricao="Tarefa manual qualquer",
    )
    resultado = await service.criar(safra_id, dados)

    service._tarefa_solo_ativa_existente.assert_not_awaited()
    session.add.assert_called_once()
    assert resultado.status == "APROVADA"


# ---------------------------------------------------------------------
# 6. Regressão: o router POST /safras/{id}/tarefas NÃO pode sobrescrever
#    dados.origem para "MANUAL" — isso quebrava a idempotência do drawer
#    de solo (origem="SOLO" virava "MANUAL" antes de chegar em criar()).
# ---------------------------------------------------------------------


async def test_router_criar_tarefa_preserva_origem_solo_enviada_pelo_cliente():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    talhao_id = uuid.uuid4()
    analise_solo_id = uuid.uuid4()

    session = _make_session()
    dados = _tarefa_create_solo(talhao_id=talhao_id, analise_solo_id=analise_solo_id)

    with patch.object(TarefaService, "criar", new=AsyncMock()) as criar_mock, \
         patch.object(TarefaService, "_tarefa_solo_ativa_existente", new=AsyncMock(return_value=None)):
        criar_mock.return_value = SafraTarefa(
            id=uuid.uuid4(), tenant_id=tenant_id, origem="SOLO", tipo="ADUBACAO_POTASSIO", status="PENDENTE_APROVACAO"
        )
        await criar_tarefa(
            safra_id=safra_id,
            dados=dados,
            session=session,
            tenant_id=tenant_id,
            _=None,
            user={"sub": str(uuid.uuid4())},
        )

    enviado = criar_mock.await_args.args[1]
    assert enviado.origem == "SOLO", "router não deve mais forçar origem=MANUAL"


async def test_router_criar_tarefa_manual_sem_origem_permanece_manual():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    talhao_id = uuid.uuid4()

    session = _make_session()
    dados = TarefaCreate(talhao_id=talhao_id, tipo="OUTRO", descricao="Tarefa manual do form")
    assert dados.origem == "MANUAL"  # default do schema, sem override no router

    with patch.object(TarefaService, "criar", new=AsyncMock()) as criar_mock:
        criar_mock.return_value = SafraTarefa(
            id=uuid.uuid4(), tenant_id=tenant_id, origem="MANUAL", tipo="OUTRO", status="APROVADA"
        )
        await criar_tarefa(
            safra_id=safra_id,
            dados=dados,
            session=session,
            tenant_id=tenant_id,
            _=None,
            user={"sub": str(uuid.uuid4())},
        )

    enviado = criar_mock.await_args.args[1]
    assert enviado.origem == "MANUAL"


# ---------------------------------------------------------------------
# 7. Fase da tarefa: SOLO/TEMPLATE herdam a fase atual da safra quando
#    não informada; MANUAL preserva a escolha do usuário (inclusive None).
# ---------------------------------------------------------------------


def _mock_scalar(value):
    m = MagicMock()
    m.scalar_one_or_none = MagicMock(return_value=value)
    return m


async def test_criar_solo_preenche_fase_com_status_atual_da_safra_quando_nao_informada():
    tenant_id = uuid.uuid4()
    talhao_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    analise_solo_id = uuid.uuid4()

    session = _make_session()
    session.execute.return_value = _mock_scalar("PREPARO_SOLO")
    service = TarefaService(session, tenant_id)
    service._tarefa_solo_ativa_existente = AsyncMock(return_value=None)

    dados = _tarefa_create_solo(talhao_id=talhao_id, analise_solo_id=analise_solo_id)
    assert dados.fase is None

    resultado = await service.criar(safra_id, dados)

    assert resultado.fase == "PREPARO_SOLO"


async def test_criar_solo_preserva_fase_explicita_quando_informada():
    tenant_id = uuid.uuid4()
    talhao_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    analise_solo_id = uuid.uuid4()

    session = _make_session()
    service = TarefaService(session, tenant_id)
    service._tarefa_solo_ativa_existente = AsyncMock(return_value=None)
    service._fase_atual_safra = AsyncMock()

    dados = TarefaCreate(
        talhao_id=talhao_id,
        analise_solo_id=analise_solo_id,
        origem="SOLO",
        tipo="CALAGEM",
        descricao="Calagem via análise de solo",
        fase="PLANTIO",
    )
    resultado = await service.criar(safra_id, dados)

    assert resultado.fase == "PLANTIO"
    service._fase_atual_safra.assert_not_awaited()


async def test_criar_manual_nao_preenche_fase_automaticamente():
    tenant_id = uuid.uuid4()
    talhao_id = uuid.uuid4()
    safra_id = uuid.uuid4()

    session = _make_session()
    service = TarefaService(session, tenant_id)
    service._fase_atual_safra = AsyncMock(return_value="PLANTIO")

    dados = TarefaCreate(
        talhao_id=talhao_id,
        origem="MANUAL",
        tipo="OUTRO",
        descricao="Tarefa manual sem fase",
    )
    resultado = await service.criar(safra_id, dados)

    assert resultado.fase is None
    service._fase_atual_safra.assert_not_awaited()


# ---------------------------------------------------------------------
# 8. Preview de tarefas do drawer (cultivo-analise-drawer) não retornava
#    observação: CultivoService.gerar_tarefas_solo lia rec.get("obs"),
#    mas AnaliseSoloService.gerar_recomendacoes usa a chave "observacao".
# ---------------------------------------------------------------------


async def test_gerar_tarefas_solo_preview_preenche_obs_com_observacao_da_recomendacao():
    tenant_id = uuid.uuid4()
    cultivo_area_id = uuid.uuid4()
    analise_id = uuid.uuid4()

    session = _make_session()
    service = CultivoService(session, tenant_id)

    area = MagicMock()
    area.id = cultivo_area_id
    area.analise_solo_id = analise_id
    area.regiao_analise = None
    area.area_ha = 10.0
    area.cultivo_id = uuid.uuid4()

    analise = MagicMock()
    cultivo = MagicMock()
    cultivo.cultivar_id = None
    cultivo.cultura = "SOJA"

    session.execute.side_effect = [
        _mock_scalar_first(area),
        _mock_scalar_first(analise),
        _mock_scalar_first(cultivo),
    ]

    recomendacoes = {
        "potassio": {
            "necessaria": True,
            "rec_k2o_kg_ha": 30.0,
            "nivel": "BAIXO",
            "observacao": "K baixo (2.0 mg/dm³). Recomendar 30.0 kg/ha de K₂O.",
        }
    }
    with patch.object(AnaliseSoloService, "gerar_recomendacoes", new=AsyncMock(return_value=recomendacoes)):
        resultado = await service.gerar_tarefas_solo(cultivo_area_id)

    assert len(resultado) == 1
    assert resultado[0].obs == "K baixo (2.0 mg/dm³). Recomendar 30.0 kg/ha de K₂O."
    assert resultado[0].nutriente == "potassio", (
        "nutriente deve ser a chave semântica ('potassio'), não o símbolo químico "
        "('K₂O') — o frontend usa esse valor para mapear o tipo da SafraTarefa "
        "(NUTRIENTE_TIPO); símbolo errado faz todas as tarefas caírem em tipo=OUTRO "
        "e serem colapsadas pela checagem de idempotência."
    )


async def test_gerar_tarefas_solo_preview_usa_chave_semantica_para_todos_os_nutrientes():
    """
    Regressão: nutriente=nutriente (símbolo químico: CALCARIO/P₂O₅/K₂O/N) fazia o
    frontend (NUTRIENTE_TIPO, que espera calagem/fosforo/potassio/nitrogenio) cair
    sempre no fallback tipo="OUTRO" para as 4 recomendações — daí a checagem de
    idempotência (por tenant+analise+safra+talhao+tipo) tratar a 2ª/3ª/4ª tarefa
    como duplicata da 1ª, e só uma sobreviver.
    """
    tenant_id = uuid.uuid4()
    cultivo_area_id = uuid.uuid4()
    analise_id = uuid.uuid4()

    session = _make_session()
    service = CultivoService(session, tenant_id)

    area = MagicMock()
    area.id = cultivo_area_id
    area.analise_solo_id = analise_id
    area.regiao_analise = None
    area.area_ha = 10.0
    area.cultivo_id = uuid.uuid4()

    analise = MagicMock()
    cultivo = MagicMock()
    cultivo.cultivar_id = None
    cultivo.cultura = "SOJA"

    session.execute.side_effect = [
        _mock_scalar_first(area),
        _mock_scalar_first(analise),
        _mock_scalar_first(cultivo),
    ]

    recomendacoes = {
        "calagem": {"necessaria": True, "dose_t_ha": 2.0, "nivel": "BAIXO", "observacao": "obs cal"},
        "fosforo": {"rec_p2o5_kg_ha": 40.0, "nivel": "BAIXO", "observacao": "obs p"},
        "potassio": {"rec_k2o_kg_ha": 30.0, "nivel": "BAIXO", "observacao": "obs k"},
        "nitrogenio": {"rec_n_kg_ha": 20.0, "nivel": "MEDIO", "observacao": "obs n"},
    }
    with patch.object(AnaliseSoloService, "gerar_recomendacoes", new=AsyncMock(return_value=recomendacoes)):
        resultado = await service.gerar_tarefas_solo(cultivo_area_id)

    nutrientes = {t.nutriente for t in resultado}
    assert nutrientes == {"calagem", "fosforo", "potassio", "nitrogenio"}, (
        f"esperado 4 chaves semânticas distintas, obtido: {nutrientes}"
    )


def _mock_scalar_first(value):
    m = MagicMock()
    m.scalar_one_or_none = MagicMock(return_value=value)
    m.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=value)))
    return m
