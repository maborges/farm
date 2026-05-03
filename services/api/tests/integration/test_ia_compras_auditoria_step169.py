"""
Testes de integração — Auditoria de Recomendações IA (Step 169).
Cobre: persistência de IA, fallback, limite atingido e histórico ordenado.
"""
import pytest
from httpx import AsyncClient
import uuid
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from sqlalchemy import delete, select

from ia.models import IAComprasRecomendacao
from core.models.tenant import Tenant
from core.services.auth_service import AuthService

VALID_TENANT_ID = "aaaaaaaa-0000-0000-0000-000000000001"
VALID_ITEM_ID = "cc000001-0000-0000-0000-000000000001"
VALID_SOL_ID = "dd000001-0000-0000-0000-000000000001"
USER_ID = uuid.UUID("eeeeeeee-0000-0000-0000-000000000005")

PAYLOAD = {
    "item_id": VALID_ITEM_ID,
    "solicitacao_id": VALID_SOL_ID,
}


@pytest.fixture(autouse=True)
async def _limpar_recomendacoes(session):
    await session.execute(delete(IAComprasRecomendacao))
    await session.commit()
    yield
    await session.execute(delete(IAComprasRecomendacao))
    await session.commit()


async def _garantir_tenant(session, tenant_id: uuid.UUID, nome: str) -> None:
    if await session.get(Tenant, tenant_id):
        return
    session.add(
        Tenant(
            id=tenant_id,
            nome=nome,
            documento=str(tenant_id).replace("-", "")[:14],
            ativo=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    )
    await session.commit()


def _headers_tenant(tenant_id: uuid.UUID) -> dict:
    claims = {
        "sub": str(USER_ID),
        "tenant_id": str(tenant_id),
        "modules": ["CORE", "O1_FROTA", "O2_ESTOQUE", "O3_COMPRAS"],
        "fazendas_auth": [{"id": "bbbbbbbb-0000-0000-0000-000000000002", "role": "admin"}],
        "is_superuser": False,
        "plan_tier": "PROFISSIONAL",
    }
    token = AuthService(MagicMock()).create_access_token(claims, expires_delta=timedelta(hours=1))
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(tenant_id),
        "X-Fazenda-ID": "bbbbbbbb-0000-0000-0000-000000000002",
    }


@pytest.mark.asyncio
async def test_recomendacao_fallback_e_persistida(client: AsyncClient, session, headers_operacional: dict):
    """Fallback (sem IA_ENABLED) deve ser persistido na tabela."""
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "", "IA_ENABLED": "false"}):
        response = await client.post(
            "/api/v1/ia/compras/estrategia",
            json=PAYLOAD,
            headers=headers_operacional,
        )
    assert response.status_code == 200

    rows = (await session.execute(
        select(IAComprasRecomendacao)
        .where(IAComprasRecomendacao.tenant_id == uuid.UUID(VALID_TENANT_ID))
        .order_by(IAComprasRecomendacao.created_at.desc())
    )).scalars().all()

    assert len(rows) >= 1
    rec = rows[0]
    assert rec.estrategia in ("Comprar agora", "Negociar", "Aguardar")
    assert rec.resumo != ""
    assert isinstance(rec.justificativas, list)
    assert rec.fonte in ("DETERMINISTICO", "IA")


@pytest.mark.asyncio
async def test_recomendacao_limite_atingido_persistida(client: AsyncClient, session, headers_operacional: dict):
    """Recomendação com limite_atingido=True deve ser persistida com o flag correto."""
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key", "IA_ENABLED": "true"}), \
         patch("ia.compras_estrategia_service.tenant_tem_ia", return_value=True), \
         patch("ia.usage_service.verificar_limite_ia", return_value=(False, "PLANO")), \
         patch("ia.usage_service.registrar_uso_ia", AsyncMock()):
        response = await client.post(
            "/api/v1/ia/compras/estrategia",
            json=PAYLOAD,
            headers=headers_operacional,
        )
    assert response.status_code == 200
    assert response.json()["limite_atingido"] is True

    rows = (await session.execute(
        select(IAComprasRecomendacao)
        .where(IAComprasRecomendacao.tenant_id == uuid.UUID(VALID_TENANT_ID))
        .order_by(IAComprasRecomendacao.created_at.desc())
    )).scalars().all()
    assert any(r.limite_atingido for r in rows)


@pytest.mark.asyncio
async def test_historico_retorna_ordenado(client: AsyncClient, session, headers_operacional: dict):
    """GET /recomendacoes deve retornar lista ordenada do mais recente para o mais antigo."""
    response = await client.get(
        f"/api/v1/ia/compras/recomendacoes?solicitacao_id={VALID_SOL_ID}",
        headers=headers_operacional,
    )
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    if len(items) >= 2:
        for i in range(len(items) - 1):
            assert items[i]["created_at"] >= items[i + 1]["created_at"]


@pytest.mark.asyncio
async def test_historico_sem_filtro(client: AsyncClient, headers_operacional: dict):
    """GET /recomendacoes sem filtro retorna histórico geral do tenant."""
    response = await client.get(
        "/api/v1/ia/compras/recomendacoes",
        headers=headers_operacional,
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_historico_isolamento_tenant(client: AsyncClient, session, headers_operacional: dict):
    """Registros de outro tenant não aparecem no histórico."""
    outro_tenant = uuid.UUID("cccccccc-0000-0000-0000-000000000003")
    await _garantir_tenant(session, outro_tenant, "Tenant Auditoria Outro")
    rec_outro = IAComprasRecomendacao(
        id=uuid.uuid4(),
        tenant_id=outro_tenant,
        estrategia="Aguardar",
        resumo="Registro de outro tenant",
        justificativas=["motivo"],
        nivel_confianca=0.5,
        fonte="DETERMINISTICO",
        limite_atingido=False,
    )
    session.add(rec_outro)
    await session.commit()

    response = await client.get("/api/v1/ia/compras/recomendacoes", headers=headers_operacional)
    assert response.status_code == 200
    resumos = [i["resumo"] for i in response.json()]
    assert "Registro de outro tenant" not in resumos

    response_outro = await client.get("/api/v1/ia/compras/recomendacoes", headers=_headers_tenant(outro_tenant))
    assert response_outro.status_code == 200
    assert any(i["resumo"] == "Registro de outro tenant" for i in response_outro.json())
