"""
Testes de integração — IA Estratégia de Compra (Step 168).
Cobre: chamada bem-sucedida, fallback quando IA indisponível, limites respeitados.
"""
import pytest
from httpx import AsyncClient
import uuid
from unittest.mock import patch, AsyncMock

VALID_TENANT_ID = "aaaaaaaa-0000-0000-0000-000000000001"
VALID_ITEM_ID = "cc000001-0000-0000-0000-000000000001"
VALID_SOL_ID = "dd000001-0000-0000-0000-000000000001"

PAYLOAD = {
    "item_id": VALID_ITEM_ID,
    "solicitacao_id": VALID_SOL_ID,
}


@pytest.mark.asyncio
async def test_estrategia_retorna_fallback_sem_ia_key(client: AsyncClient, headers_operacional: dict):
    """Sem ANTHROPIC_API_KEY, deve retornar fallback determinístico sem erro."""
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "", "IA_ENABLED": "false"}):
        response = await client.post(
            "/api/v1/ia/compras/estrategia",
            json=PAYLOAD,
            headers=headers_operacional,
        )
    assert response.status_code == 200
    data = response.json()
    assert "resumo" in data
    assert data["estrategia"] in ("Comprar agora", "Negociar", "Aguardar")
    assert isinstance(data["justificativas"], list)
    assert 0.0 <= data["nivel_confianca"] <= 1.0
    assert data["ia_disponivel"] is False


@pytest.mark.asyncio
async def test_estrategia_fallback_quando_ia_falha(client: AsyncClient, headers_operacional: dict):
    """Quando IA lança exceção, deve usar fallback sem quebrar o fluxo."""
    async def _mock_chamar_ia(ctx):
        raise RuntimeError("Timeout simulado")

    with patch("ia.compras_estrategia_service._chamar_ia", side_effect=_mock_chamar_ia), \
         patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key", "IA_ENABLED": "true"}), \
         patch("ia.compras_estrategia_service.tenant_tem_ia", return_value=True), \
         patch("ia.usage_service.verificar_limite_ia", return_value=(True, "PLANO")):
        response = await client.post(
            "/api/v1/ia/compras/estrategia",
            json=PAYLOAD,
            headers=headers_operacional,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["estrategia"] in ("Comprar agora", "Negociar", "Aguardar")
    assert data["ia_disponivel"] is True  # IA estava disponível mas falhou


@pytest.mark.asyncio
async def test_estrategia_sucesso_com_mock_ia(client: AsyncClient, headers_operacional: dict):
    """Com mock de IA respondendo, deve retornar EstrategiaCompra completa."""
    from ia.compras_estrategia_service import EstrategiaCompra

    mock_resultado = EstrategiaCompra(
        resumo="Recomendamos fechar agora com o fornecedor A.",
        estrategia="Comprar agora",
        justificativas=["Preço abaixo da média histórica", "Fornecedor estável"],
        nivel_confianca=0.88,
        fonte="IA",
        ia_disponivel=True,
    )

    with patch("ia.compras_estrategia_service.gerar_estrategia_compra", return_value=mock_resultado):
        response = await client.post(
            "/api/v1/ia/compras/estrategia",
            json=PAYLOAD,
            headers=headers_operacional,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["estrategia"] == "Comprar agora"
    assert data["nivel_confianca"] == 0.88
    assert len(data["justificativas"]) == 2
    assert data["fonte"] == "IA"


@pytest.mark.asyncio
async def test_estrategia_limite_atingido(client: AsyncClient, headers_operacional: dict):
    """Quando limite de uso for atingido, deve retornar fallback com limite_atingido=True."""
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
    data = response.json()
    assert data["limite_atingido"] is True
    assert data["estrategia"] in ("Comprar agora", "Negociar", "Aguardar")


@pytest.mark.asyncio
async def test_estrategia_payload_invalido(client: AsyncClient, headers_operacional: dict):
    """Payload sem item_id deve retornar 422."""
    response = await client.post(
        "/api/v1/ia/compras/estrategia",
        json={"solicitacao_id": VALID_SOL_ID},
        headers=headers_operacional,
    )
    assert response.status_code == 422
