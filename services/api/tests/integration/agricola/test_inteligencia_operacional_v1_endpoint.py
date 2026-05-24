from __future__ import annotations

import importlib
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from httpx import AsyncClient

from core.services.auth_service import AuthService
from agricola.inteligencia_operacional.schemas import (
    PlanoAcaoOperacionalAgricolaFonte,
    PlanoAcaoOperacionalAgricolaItem,
)
from core.exceptions import EntityNotFoundError


TENANT_OUTRO = UUID("bbbbbbbb-0000-0000-0000-000000000010")
USER_FIXO = UUID("eeeeeeee-0000-0000-0000-000000000005")
FAZENDA_FIXA = UUID("bbbbbbbb-0000-0000-0000-000000000002")


def _token_para_tenant(tenant_id: UUID, role: str = "admin") -> str:
    svc = AuthService(MagicMock())
    claims = {
        "sub": str(USER_FIXO),
        "tenant_id": str(tenant_id),
        "modules": ["CORE", "A1_PLANEJAMENTO", "A2_CAMPO"],
        "fazendas_auth": [{"id": str(FAZENDA_FIXA), "role": role}],
        "is_superuser": False,
        "plan_tier": "PROFISSIONAL",
    }
    return svc.create_access_token(claims)


def _headers(token: str, tenant_id: UUID) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(tenant_id),
        "X-Fazenda-ID": str(FAZENDA_FIXA),
    }


def _plano_fake(tenant_suffix: str = "1") -> PlanoAcaoOperacionalAgricolaItem:
    safra_id = UUID("aaaaaaaa-0000-0000-0000-000000000001")
    production_unit_id = UUID("aaaaaaaa-0000-0000-0000-000000000010")
    entidade_id = f"entidade-{tenant_suffix}"
    fonte = PlanoAcaoOperacionalAgricolaFonte(
        origem_analitica="PRIORIDADE",
        codigo="RESULTADO_OPERACIONAL_NEGATIVO",
        titulo="Resultado operacional negativo",
        severidade="PRIORIDADE_CRITICA",
        scope="PRODUCTION_UNIT",
        entidade_tipo="PRODUCTION_UNIT",
        entidade_id=entidade_id,
        entidade_label="UP Teste",
    )
    return PlanoAcaoOperacionalAgricolaItem(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        chave=f"RESULTADO_OPERACIONAL_NEGATIVO:PRODUCTION_UNIT:{entidade_id}",
        scope="PRODUCTION_UNIT",
        titulo="Resultado operacional negativo",
        resumo="Resumo assistido",
        motivo="Motivo assistido",
        severidade="PRIORIDADE_CRITICA",
        impacto_estimado=12000.0,
        acoes_sugeridas=["Revisar custos alocados", "Validar reconciliação"],
        prazo_sugerido="Imediato",
        contexto_operacional="Contexto operacional assistido",
        origem_primaria=fonte,
        fontes_analiticas=[fonte],
        safra_id=safra_id,
        production_unit_id=production_unit_id,
        unidade_produtiva_id=UUID("aaaaaaaa-0000-0000-0000-000000000020"),
        entidade_tipo="PRODUCTION_UNIT",
        entidade_id=entidade_id,
        entidade_label="UP Teste",
        posicao=1,
    )


class FakeTask(SimpleNamespace):
    def model_dump(self, mode: str = "python"):
        return dict(self.__dict__)


def _tarefa_fake() -> FakeTask:
    now = datetime.utcnow()
    return FakeTask(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        tenant_id=UUID("aaaaaaaa-0000-0000-0000-000000000001"),
        safra_id=UUID("aaaaaaaa-0000-0000-0000-000000000001"),
        talhao_id=None,
        production_unit_id=UUID("aaaaaaaa-0000-0000-0000-000000000010"),
        cultivo_area_id=None,
        analise_solo_id=None,
        origem="MANUAL",
        tipo="OUTRO",
        fase=None,
        criticidade="CRITICA",
        descricao="Revisar reconciliação oficial",
        obs="Plano assistido convertido em tarefa real.",
        prioridade="URGENTE",
        status="APROVADA",
        dose_estimada_kg_ha=None,
        quantidade_total_estimada_kg=None,
        area_ha=None,
        custo_estimado=None,
        data_prevista=date(2026, 1, 31),
        aprovado_por=USER_FIXO,
        aprovado_em=now,
        operacao_id=None,
        concluida_em=None,
        cancelado_por=None,
        cancelado_em=None,
        motivo_cancelamento=None,
        created_by=USER_FIXO,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_converter_plano_em_tarefa_exige_confirmacao_explicita(
    client: AsyncClient,
    headers_agricola: dict,
):
    plano_id = _plano_fake().id

    response = await client.post(
        f"/api/v1/agricola/inteligencia-operacional/planos/{plano_id}/converter-tarefa",
        params={"safra_id": str(UUID("aaaaaaaa-0000-0000-0000-000000000001"))},
        json={
            "confirmado": False,
            "titulo": "Revisar reconciliação",
            "descricao": "Descrição de teste",
            "tipo": "OUTRO",
            "prioridade": "URGENTE",
            "data_prevista": "2026-01-31",
        },
        headers=headers_agricola,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_converter_plano_em_tarefa_cria_tarefa_e_registra_auditoria(
    client: AsyncClient,
    headers_agricola: dict,
):
    fake_plano = _plano_fake()
    fake_tarefa = _tarefa_fake()
    captured: dict = {}
    router_module = importlib.import_module("agricola.inteligencia_operacional.router")

    class FakeService:
        def __init__(self, session, tenant_id):
            captured["tenant_id"] = tenant_id

        async def obter_plano_por_id(self, **kwargs):
            captured["lookup_kwargs"] = kwargs
            return fake_plano

        @staticmethod
        def criticidade_para_tarefa(severidade: str) -> str:
            captured["criticidade_severidade"] = severidade
            return "CRITICA"

        def montar_obs_conversion(self, **kwargs):
            captured["obs_kwargs"] = kwargs
            return "\n".join(
                [
                    "Plano assistido convertido em tarefa real.",
                    "Origem operacional: PLANO_ASSISTIDO",
                ]
            )

    class FakeTarefaService:
        def __init__(self, session, tenant_id):
            captured["tarefa_tenant_id"] = tenant_id

        async def criar(self, safra_id, dados, user_id=None):
            captured["criar_kwargs"] = {
                "safra_id": safra_id,
                "dados": dados,
                "user_id": user_id,
            }
            return fake_tarefa

    with (
        patch.object(router_module, "InteligenciaOperacionalAgricolaV1Service", FakeService),
        patch.object(router_module, "TarefaService", FakeTarefaService),
        patch.object(router_module, "write_audit_log", new=AsyncMock()) as audit_mock,
        patch("sqlalchemy.ext.asyncio.AsyncSession.refresh", new=AsyncMock()),
    ):
        response = await client.post(
            f"/api/v1/agricola/inteligencia-operacional/planos/{fake_plano.id}/converter-tarefa",
            params={
                "safra_id": str(fake_plano.safra_id),
                "production_unit_id": str(fake_plano.production_unit_id),
                "unidade_produtiva_id": str(fake_plano.unidade_produtiva_id),
                "data_inicio": "2026-01-01",
                "data_fim": "2026-01-31",
            },
            json={
                "confirmado": True,
                "titulo": "Revisar reconciliação oficial",
                "descricao": "Validar custos alocados, origem econômica e fechamento do ciclo.",
                "tipo": "OUTRO",
                "prioridade": "URGENTE",
                "data_prevista": "2026-01-31",
            },
            headers=headers_agricola,
        )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["status"] == "APROVADA"
    assert payload["descricao"] == "Revisar reconciliação oficial"
    assert payload["prioridade"] == "URGENTE"
    assert str(captured["tenant_id"]) == headers_agricola["X-Tenant-ID"]
    assert captured["lookup_kwargs"]["safra_id"] == fake_plano.safra_id
    assert captured["lookup_kwargs"]["production_unit_id"] == fake_plano.production_unit_id
    assert captured["lookup_kwargs"]["unidade_produtiva_id"] == fake_plano.unidade_produtiva_id
    assert captured["lookup_kwargs"]["data_inicio"].isoformat() == "2026-01-01"
    assert captured["lookup_kwargs"]["data_fim"].isoformat() == "2026-01-31"
    assert captured["criar_kwargs"]["dados"].origem == "MANUAL"
    assert captured["criar_kwargs"]["dados"].descricao == "Revisar reconciliação oficial"
    assert "Plano assistido convertido em tarefa real." in captured["criar_kwargs"]["dados"].obs
    assert "Origem operacional: PLANO_ASSISTIDO" in captured["criar_kwargs"]["dados"].obs
    assert captured["criar_kwargs"]["dados"].production_unit_id == fake_plano.production_unit_id
    assert captured["criar_kwargs"]["user_id"] == USER_FIXO
    assert audit_mock.await_count == 1
    assert audit_mock.await_args.kwargs["action"] == "convert_to_task"
    assert audit_mock.await_args.kwargs["resource"] == "agricola_inteligencia_operacional_plano"
    assert audit_mock.await_args.kwargs["payload_after"]["confirmado"] is True
    assert audit_mock.await_args.kwargs["payload_before"]["origem_operacional"] == "PLANO_ASSISTIDO"
    assert audit_mock.await_args.kwargs["payload_before"]["aprovado_explicitamente"] is True
    assert audit_mock.await_args.kwargs["payload_after"]["origem_operacional"] == "PLANO_ASSISTIDO"
    assert audit_mock.await_args.kwargs["payload_after"]["aprovado_por"] == str(USER_FIXO)


@pytest.mark.asyncio
async def test_converter_plano_em_tarefa_rejeita_tenant_diferente(
    client: AsyncClient,
):
    fake_plano = _plano_fake()
    router_module = importlib.import_module("agricola.inteligencia_operacional.router")
    token_outro = _token_para_tenant(TENANT_OUTRO)
    headers_outro = _headers(token_outro, TENANT_OUTRO)
    tenant_esperado = UUID("aaaaaaaa-0000-0000-0000-000000000001")

    class FakeService:
        def __init__(self, session, tenant_id):
            self.tenant_id = tenant_id

        async def obter_plano_por_id(self, **kwargs):
            if self.tenant_id != tenant_esperado:
                raise EntityNotFoundError("Plano operacional assistido não encontrado.")
            return fake_plano

    with patch.object(router_module, "InteligenciaOperacionalAgricolaV1Service", FakeService):
        response = await client.post(
            f"/api/v1/agricola/inteligencia-operacional/planos/{fake_plano.id}/converter-tarefa",
            params={"safra_id": str(fake_plano.safra_id)},
            json={
                "confirmado": True,
                "titulo": "Revisar reconciliação oficial",
                "descricao": "Validar custos alocados, origem econômica e fechamento do ciclo.",
                "tipo": "OUTRO",
                "prioridade": "URGENTE",
                "data_prevista": "2026-01-31",
            },
            headers=headers_outro,
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_converter_plano_em_tarefa_requer_role_adequado(
    client: AsyncClient,
):
    fake_plano = _plano_fake()
    token_operador = _token_para_tenant(UUID("aaaaaaaa-0000-0000-0000-000000000001"), role="operador")
    headers_operador = _headers(token_operador, UUID("aaaaaaaa-0000-0000-0000-000000000001"))

    response = await client.post(
        f"/api/v1/agricola/inteligencia-operacional/planos/{fake_plano.id}/converter-tarefa",
        params={"safra_id": str(fake_plano.safra_id)},
        json={
            "confirmado": True,
            "titulo": "Revisar reconciliação oficial",
            "descricao": "Validar custos alocados, origem econômica e fechamento do ciclo.",
            "tipo": "OUTRO",
            "prioridade": "URGENTE",
            "data_prevista": "2026-01-31",
        },
        headers=headers_operador,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_converter_plano_em_tarefa_retorna_404_quando_plano_nao_existe(
    client: AsyncClient,
    headers_agricola: dict,
):
    fake_plano = _plano_fake()
    router_module = importlib.import_module("agricola.inteligencia_operacional.router")

    class FakeService:
        def __init__(self, session, tenant_id):
            pass

        async def obter_plano_por_id(self, **kwargs):
            raise EntityNotFoundError("Plano operacional assistido não encontrado.")

    with patch.object(router_module, "InteligenciaOperacionalAgricolaV1Service", FakeService):
        response = await client.post(
            f"/api/v1/agricola/inteligencia-operacional/planos/{fake_plano.id}/converter-tarefa",
            params={"safra_id": str(fake_plano.safra_id)},
            json={
                "confirmado": True,
                "titulo": "Revisar reconciliação oficial",
                "descricao": "Validar custos alocados, origem econômica e fechamento do ciclo.",
                "tipo": "OUTRO",
                "prioridade": "URGENTE",
                "data_prevista": "2026-01-31",
            },
            headers=headers_agricola,
        )

    assert response.status_code == 404
