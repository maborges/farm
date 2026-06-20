import uuid
from datetime import date
from unittest.mock import AsyncMock

import pytest

from financeiro.services.relatorio_service import RelatorioService


pytestmark = pytest.mark.asyncio


class FakeMappingResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows


async def test_livro_caixa_agrega_lancamentos_e_preserva_grupos():
    tenant_id = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()
    session = AsyncMock()
    session.execute.return_value = FakeMappingResult(
        [
            {
                "data": date(2026, 1, 5),
                "descricao": "Venda de grãos",
                "tipo": "RECEITA",
                "categoria_rfb": "RECEITA_ATIVIDADE",
                "plano_conta_nome": "Receita Rural",
                "valor": 1500.0,
                "forma": "PIX",
                "documento": "NF1",
            },
            {
                "data": date(2026, 1, 12),
                "descricao": "Insumos",
                "tipo": "DESPESA",
                "categoria_rfb": "CUSTEIO",
                "plano_conta_nome": "Custeio",
                "valor": 400.0,
                "forma": "BOLETO",
                "documento": "NF2",
            },
        ]
    )

    resposta = await RelatorioService(session, tenant_id).livro_caixa(
        date(2026, 1, 1),
        date(2026, 1, 31),
        unidade_produtiva_id,
    )

    assert session.execute.await_count == 1
    assert resposta.total_receitas == 1500.0
    assert resposta.total_despesas == 400.0
    assert len(resposta.grupos) == 2
    assert resposta.grupos[0].tipo in {"DESPESA", "RECEITA"}
    assert resposta.grupos[1].tipo in {"DESPESA", "RECEITA"}
    assert resposta.resultado == 1100.0


async def test_livro_caixa_retorna_lista_vazia_sem_movimentos():
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    session.execute.return_value = FakeMappingResult([])

    resposta = await RelatorioService(session, tenant_id).livro_caixa(
        date(2026, 2, 1),
        date(2026, 2, 28),
    )

    assert session.execute.await_count == 1
    assert resposta.total_receitas == 0.0
    assert resposta.total_despesas == 0.0
    assert resposta.grupos == []
