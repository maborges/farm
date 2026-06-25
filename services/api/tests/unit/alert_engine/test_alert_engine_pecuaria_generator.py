from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import func, select

from alert_engine.generators import PecuariaAlertGenerator
from alert_engine.models import AlertLifecycleEvent, OperationalAlert, Priority, Severity
from alert_engine.service import AlertLifecycleService
from campo.models import TarefaCampo
from core.models.tenant import Tenant
from core.models.unidade_produtiva import UnidadeProdutiva
from pecuaria.animal.models import LoteAnimal
from pecuaria.schemas.lote_indicadores_schema import LoteIndicadoresResponse


ADMIN_USER_ID = uuid.UUID("eeeeeeee-0000-0000-0000-000000000005")


async def _seed_tenant(session, tenant_id: uuid.UUID) -> None:
    session.add(
        Tenant(
            id=tenant_id,
            nome=f"Tenant {tenant_id.hex[:8]}",
            documento=tenant_id.hex[:11],
            ativo=True,
        )
    )
    await session.commit()


async def _seed_unidade(session, tenant_id: uuid.UUID, nome: str = "Fazenda Pecuária") -> uuid.UUID:
    unidade = UnidadeProdutiva(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        nome=nome,
        tipo_propriedade="fazenda",
        ativo=True,
    )
    session.add(unidade)
    await session.commit()
    return unidade.id


async def _seed_lote(
    session,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    *,
    identificacao: str = "Lote Pecuário",
    ativo: bool = True,
) -> LoteAnimal:
    lote = LoteAnimal(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_id=None,
        identificacao=identificacao,
        especie="BOVINO",
        categoria=None,
        raca=None,
        quantidade_cabecas=10 if ativo else 0,
        peso_medio_kg=320.0,
        data_formacao=date.today() - timedelta(days=30),
        observacoes=None,
        ativo=ativo,
    )
    session.add(lote)
    await session.commit()
    return lote


async def _seed_tarefa(
    session,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    *,
    lote_id: uuid.UUID,
    status_execucao: str,
    data_programada: date | None,
    dados: dict | None = None,
) -> TarefaCampo:
    tarefa = TarefaCampo(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        dispositivo_id=None,
        user_id=ADMIN_USER_ID,
        operador_id=None,
        client_id=str(uuid.uuid4()),
        origem="PROGRAMADA",
        status_execucao=status_execucao,
        titulo="Vacinação",
        data_programada=data_programada,
        prioridade="NORMAL",
        type="VACINACAO",
        module="pecuaria",
        unidade_produtiva_id=unidade_produtiva_id,
        area_rural_id=None,
        lote_id=lote_id,
        status=status_execucao,
        dados=dados or {},
        fotos=[],
        localizacao_status="INDISPONIVEL",
        latitude=None,
        longitude=None,
        iniciada_em=None,
        concluida_em=datetime.utcnow() if status_execucao == "CONCLUIDA" else None,
        invalidado_em=None,
        invalidado_por=None,
        motivo_invalidacao=None,
        client_created_at=datetime.utcnow(),
        client_updated_at=datetime.utcnow(),
    )
    session.add(tarefa)
    await session.commit()
    return tarefa


def _resumo_lote(
    lote: LoteAnimal,
    *,
    quantidade_animais: int,
    ultima_pesagem: date | None,
    custo_sanitario_por_cabeca: float,
) -> LoteIndicadoresResponse:
    return LoteIndicadoresResponse(
        lote_id=lote.id,
        nome_lote=lote.identificacao,
        quantidade_animais=quantidade_animais,
        peso_total_kg=float(quantidade_animais * 300.0),
        peso_medio_kg=300.0 if quantidade_animais else 0.0,
        gmd_medio_kg_dia=None,
        ultima_pesagem=ultima_pesagem,
        custo_sanitario_total=float(quantidade_animais * custo_sanitario_por_cabeca),
        custo_sanitario_por_cabeca=float(custo_sanitario_por_cabeca),
        custo_sanitario_por_kg=1.0,
        custo_sanitario_por_arroba=15.0,
    )


async def _count_alerts(session, tenant_id: uuid.UUID) -> int:
    stmt = select(func.count(OperationalAlert.id)).where(OperationalAlert.tenant_id == tenant_id)
    return int((await session.execute(stmt)).scalar_one() or 0)


async def _count_lifecycle_events(session, tenant_id: uuid.UUID) -> int:
    stmt = select(func.count(AlertLifecycleEvent.id)).where(AlertLifecycleEvent.tenant_id == tenant_id)
    return int((await session.execute(stmt)).scalar_one() or 0)


@pytest.mark.asyncio
async def test_lote_sem_pesagem_gera_alerta(session, monkeypatch) -> None:
    tenant_id = uuid.uuid4()
    await _seed_tenant(session, tenant_id)
    unidade_id = await _seed_unidade(session, tenant_id)
    lote = await _seed_lote(session, tenant_id, unidade_id, identificacao="Lote A")
    generator = PecuariaAlertGenerator(session, tenant_id)

    async def _stub_resumo(self, lote_id: uuid.UUID) -> LoteIndicadoresResponse:
        assert lote_id == lote.id
        return _resumo_lote(lote, quantidade_animais=12, ultima_pesagem=None, custo_sanitario_por_cabeca=30.0)

    monkeypatch.setattr("alert_engine.generators.pecuaria_generator.LoteIndicadoresService.resumir", _stub_resumo, raising=False)

    result = await generator.gerar_alertas_pecuaria()
    summary = await AlertLifecycleService(session, tenant_id).get_alert_summary()

    alert = (
        await session.execute(
            select(OperationalAlert).where(
                OperationalAlert.tenant_id == tenant_id,
                OperationalAlert.dedupe_key == f"pecuaria:lote_sem_pesagem:{lote.id}",
            )
        )
    ).scalar_one()

    assert result.lotes_sem_pesagem == 1
    assert result.total_alertas == 1
    assert alert.domain == "LIVESTOCK"
    assert alert.category == "PRODUCAO"
    assert alert.severity == "WARNING"
    assert alert.priority == "HIGH"
    assert alert.source_type == "PECUARIA_LOTE_SEM_PESAGEM"
    assert alert.source_id == str(lote.id)
    assert summary.total_open == 1
    assert summary.by_domain["LIVESTOCK"].open == 1
    assert summary.top_alerts[0].dedupe_key == alert.dedupe_key
    assert await _count_lifecycle_events(session, tenant_id) == 1


@pytest.mark.asyncio
async def test_lote_com_pesagem_recente_nao_gera_alerta(session, monkeypatch) -> None:
    tenant_id = uuid.uuid4()
    await _seed_tenant(session, tenant_id)
    unidade_id = await _seed_unidade(session, tenant_id)
    lote = await _seed_lote(session, tenant_id, unidade_id, identificacao="Lote B")
    generator = PecuariaAlertGenerator(session, tenant_id)

    async def _stub_resumo(self, lote_id: uuid.UUID) -> LoteIndicadoresResponse:
        assert lote_id == lote.id
        return _resumo_lote(lote, quantidade_animais=8, ultima_pesagem=date.today() - timedelta(days=10), custo_sanitario_por_cabeca=30.0)

    monkeypatch.setattr("alert_engine.generators.pecuaria_generator.LoteIndicadoresService.resumir", _stub_resumo, raising=False)

    result = await generator.gerar_alertas_pecuaria()

    assert result.lotes_sem_pesagem == 0
    assert await _count_alerts(session, tenant_id) == 0


@pytest.mark.asyncio
async def test_lote_sem_animais_nao_gera_alerta(session, monkeypatch) -> None:
    tenant_id = uuid.uuid4()
    await _seed_tenant(session, tenant_id)
    unidade_id = await _seed_unidade(session, tenant_id)
    lote = await _seed_lote(session, tenant_id, unidade_id, identificacao="Lote C")
    generator = PecuariaAlertGenerator(session, tenant_id)

    async def _stub_resumo(self, lote_id: uuid.UUID) -> LoteIndicadoresResponse:
        assert lote_id == lote.id
        return _resumo_lote(lote, quantidade_animais=0, ultima_pesagem=None, custo_sanitario_por_cabeca=0.0)

    monkeypatch.setattr("alert_engine.generators.pecuaria_generator.LoteIndicadoresService.resumir", _stub_resumo, raising=False)

    result = await generator.gerar_alertas_pecuaria()

    assert result.total_alertas == 0
    assert await _count_alerts(session, tenant_id) == 0


@pytest.mark.asyncio
async def test_vacinacao_atrasada_gera_alerta(session, monkeypatch) -> None:
    tenant_id = uuid.uuid4()
    await _seed_tenant(session, tenant_id)
    unidade_id = await _seed_unidade(session, tenant_id)
    lote = await _seed_lote(session, tenant_id, unidade_id, identificacao="Lote D")
    tarefa = await _seed_tarefa(
        session,
        tenant_id,
        unidade_id,
        lote_id=lote.id,
        status_execucao="PENDENTE",
        data_programada=date.today() - timedelta(days=3),
    )
    generator = PecuariaAlertGenerator(session, tenant_id)

    async def _stub_resumo(self, lote_id: uuid.UUID) -> LoteIndicadoresResponse:
        return _resumo_lote(lote, quantidade_animais=10, ultima_pesagem=date.today(), custo_sanitario_por_cabeca=20.0)

    monkeypatch.setattr("alert_engine.generators.pecuaria_generator.LoteIndicadoresService.resumir", _stub_resumo, raising=False)

    result = await generator.gerar_alertas_pecuaria()

    alert = (
        await session.execute(
            select(OperationalAlert).where(
                OperationalAlert.tenant_id == tenant_id,
                OperationalAlert.dedupe_key == f"pecuaria:vacinacao_atrasada:{tarefa.id}",
            )
        )
    ).scalar_one()

    assert result.vacinacoes_atrasadas == 1
    assert alert.domain == "LIVESTOCK"
    assert alert.category == "SANITARIO"
    assert alert.severity == "CRITICAL"
    assert alert.priority == "URGENT"
    assert alert.source_type == "PECUARIA_VACINACAO_ATRASADA"
    assert alert.source_id == str(tarefa.id)


@pytest.mark.asyncio
async def test_vacinacao_concluida_nao_gera_alerta(session, monkeypatch) -> None:
    tenant_id = uuid.uuid4()
    await _seed_tenant(session, tenant_id)
    unidade_id = await _seed_unidade(session, tenant_id)
    lote = await _seed_lote(session, tenant_id, unidade_id, identificacao="Lote E")
    await _seed_tarefa(
        session,
        tenant_id,
        unidade_id,
        lote_id=lote.id,
        status_execucao="CONCLUIDA",
        data_programada=date.today() - timedelta(days=3),
    )
    generator = PecuariaAlertGenerator(session, tenant_id)

    async def _stub_resumo(self, lote_id: uuid.UUID) -> LoteIndicadoresResponse:
        return _resumo_lote(lote, quantidade_animais=10, ultima_pesagem=date.today(), custo_sanitario_por_cabeca=20.0)

    monkeypatch.setattr("alert_engine.generators.pecuaria_generator.LoteIndicadoresService.resumir", _stub_resumo, raising=False)

    result = await generator.gerar_alertas_pecuaria()

    assert result.vacinacoes_atrasadas == 0
    assert await _count_alerts(session, tenant_id) == 0


@pytest.mark.asyncio
async def test_custo_sanitario_alto_gera_alerta(session, monkeypatch) -> None:
    tenant_id = uuid.uuid4()
    await _seed_tenant(session, tenant_id)
    unidade_id = await _seed_unidade(session, tenant_id)
    lote = await _seed_lote(session, tenant_id, unidade_id, identificacao="Lote F")
    generator = PecuariaAlertGenerator(session, tenant_id)

    async def _stub_resumo(self, lote_id: uuid.UUID) -> LoteIndicadoresResponse:
        return _resumo_lote(lote, quantidade_animais=10, ultima_pesagem=date.today(), custo_sanitario_por_cabeca=75.0)

    monkeypatch.setattr("alert_engine.generators.pecuaria_generator.LoteIndicadoresService.resumir", _stub_resumo, raising=False)

    result = await generator.gerar_alertas_pecuaria()

    alert = (
        await session.execute(
            select(OperationalAlert).where(
                OperationalAlert.tenant_id == tenant_id,
                OperationalAlert.dedupe_key == f"pecuaria:custo_sanitario_alto:{lote.id}",
            )
        )
    ).scalar_one()

    assert result.custos_sanitarios_altos == 1
    assert alert.category == "ECONOMICO"
    assert alert.severity == "WARNING"
    assert alert.priority == "NORMAL"
    assert alert.trigger_type == "THRESHOLD"
    assert alert.source_type == "PECUARIA_CUSTO_SANITARIO_ALTO"


@pytest.mark.asyncio
async def test_custo_abaixo_do_limite_nao_gera_alerta(session, monkeypatch) -> None:
    tenant_id = uuid.uuid4()
    await _seed_tenant(session, tenant_id)
    unidade_id = await _seed_unidade(session, tenant_id)
    lote = await _seed_lote(session, tenant_id, unidade_id, identificacao="Lote G")
    generator = PecuariaAlertGenerator(session, tenant_id)

    async def _stub_resumo(self, lote_id: uuid.UUID) -> LoteIndicadoresResponse:
        return _resumo_lote(lote, quantidade_animais=10, ultima_pesagem=date.today(), custo_sanitario_por_cabeca=25.0)

    monkeypatch.setattr("alert_engine.generators.pecuaria_generator.LoteIndicadoresService.resumir", _stub_resumo, raising=False)

    result = await generator.gerar_alertas_pecuaria()

    assert result.custos_sanitarios_altos == 0
    assert await _count_alerts(session, tenant_id) == 0


@pytest.mark.asyncio
async def test_reprocessamento_e_idempotente(session, monkeypatch) -> None:
    tenant_id = uuid.uuid4()
    await _seed_tenant(session, tenant_id)
    unidade_id = await _seed_unidade(session, tenant_id)
    lote = await _seed_lote(session, tenant_id, unidade_id, identificacao="Lote H")
    generator = PecuariaAlertGenerator(session, tenant_id)

    async def _stub_resumo(self, lote_id: uuid.UUID) -> LoteIndicadoresResponse:
        return _resumo_lote(lote, quantidade_animais=11, ultima_pesagem=None, custo_sanitario_por_cabeca=30.0)

    monkeypatch.setattr("alert_engine.generators.pecuaria_generator.LoteIndicadoresService.resumir", _stub_resumo, raising=False)

    first = await generator.gerar_alertas_pecuaria()
    second = await generator.gerar_alertas_pecuaria()

    assert first.lotes_sem_pesagem == 1
    assert second.lotes_sem_pesagem == 1
    assert await _count_alerts(session, tenant_id) == 1
    assert await _count_lifecycle_events(session, tenant_id) == 1


@pytest.mark.asyncio
async def test_tenant_isolation(session, monkeypatch) -> None:
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    await _seed_tenant(session, tenant_a)
    await _seed_tenant(session, tenant_b)
    unidade_a = await _seed_unidade(session, tenant_a, nome="Fazenda A")
    unidade_b = await _seed_unidade(session, tenant_b, nome="Fazenda B")
    lote_a = await _seed_lote(session, tenant_a, unidade_a, identificacao="Lote A")
    lote_b = await _seed_lote(session, tenant_b, unidade_b, identificacao="Lote B")
    generator = PecuariaAlertGenerator(session, tenant_a)

    async def _stub_resumo(self, lote_id: uuid.UUID) -> LoteIndicadoresResponse:
        if lote_id == lote_a.id:
            return _resumo_lote(lote_a, quantidade_animais=9, ultima_pesagem=None, custo_sanitario_por_cabeca=30.0)
        return _resumo_lote(lote_b, quantidade_animais=9, ultima_pesagem=None, custo_sanitario_por_cabeca=30.0)

    monkeypatch.setattr("alert_engine.generators.pecuaria_generator.LoteIndicadoresService.resumir", _stub_resumo, raising=False)

    result = await generator.gerar_alertas_pecuaria()

    assert result.lotes_sem_pesagem == 1
    assert await _count_alerts(session, tenant_a) == 1
    assert await _count_alerts(session, tenant_b) == 0


@pytest.mark.asyncio
async def test_summary_reflete_alertas_pecuarios(session, monkeypatch) -> None:
    tenant_id = uuid.uuid4()
    await _seed_tenant(session, tenant_id)
    unidade_id = await _seed_unidade(session, tenant_id)
    lote = await _seed_lote(session, tenant_id, unidade_id, identificacao="Lote I")
    generator = PecuariaAlertGenerator(session, tenant_id)

    async def _stub_resumo(self, lote_id: uuid.UUID) -> LoteIndicadoresResponse:
        return _resumo_lote(lote, quantidade_animais=14, ultima_pesagem=None, custo_sanitario_por_cabeca=30.0)

    monkeypatch.setattr("alert_engine.generators.pecuaria_generator.LoteIndicadoresService.resumir", _stub_resumo, raising=False)

    await generator.gerar_alertas_pecuaria()
    summary = await AlertLifecycleService(session, tenant_id).get_alert_summary()

    assert summary.total_open == 1
    assert summary.by_domain["LIVESTOCK"].open == 1
    assert summary.max_severity == Severity.WARNING
    assert summary.max_priority == Priority.HIGH
    assert summary.top_alerts[0].source_type == "PECUARIA_LOTE_SEM_PESAGEM"


@pytest.mark.asyncio
async def test_lifecycle_create_is_registered(session, monkeypatch) -> None:
    tenant_id = uuid.uuid4()
    await _seed_tenant(session, tenant_id)
    unidade_id = await _seed_unidade(session, tenant_id)
    lote = await _seed_lote(session, tenant_id, unidade_id, identificacao="Lote J")
    generator = PecuariaAlertGenerator(session, tenant_id)

    async def _stub_resumo(self, lote_id: uuid.UUID) -> LoteIndicadoresResponse:
        return _resumo_lote(lote, quantidade_animais=7, ultima_pesagem=None, custo_sanitario_por_cabeca=30.0)

    monkeypatch.setattr("alert_engine.generators.pecuaria_generator.LoteIndicadoresService.resumir", _stub_resumo, raising=False)

    await generator.gerar_alertas_pecuaria()

    event = (
        await session.execute(
            select(AlertLifecycleEvent).where(AlertLifecycleEvent.tenant_id == tenant_id)
        )
    ).scalar_one()

    assert event.action_type == "CREATE"
    assert event.previous_status == "OPEN"
    assert event.new_status == "OPEN"
    assert event.source_channel == "ENGINE"
    assert event.payload["created_by"] == "ENGINE"
