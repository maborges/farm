"""Guardrails unitários do ciclo de posse operacional 01F."""

from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from core.exceptions import BusinessRuleError
from operacional.schemas.estoque import DestinacaoRequisicaoRequest
from operacional.services.requisicao_posse_service import RequisicaoPosseService
from operacional.services.requisicao_recebimento_service import RequisicaoRecebimentoService


def _command(**changes):
    payload = {
        "item_id": uuid4(),
        "entrega_evento_id": uuid4(),
        "tipo_evento": "CONSUMO",
        "quantidade": Decimal("8"),
        "base_version": 3,
        "client_operation_id": "disposition-1",
        "operacao_execucao_id": uuid4(),
        "dispositivo_id": uuid4(),
    }
    payload.update(changes)
    return DestinacaoRequisicaoRequest(**payload)


def test_disposition_command_requires_exact_origin_and_idempotency() -> None:
    with pytest.raises(ValidationError):
        DestinacaoRequisicaoRequest(
            item_id=uuid4(), entrega_evento_id=uuid4(), tipo_evento="CONSUMO", quantidade=1
        )


def test_retry_payload_cannot_change_origin_or_quantity() -> None:
    data = _command()
    event = SimpleNamespace(
        requisicao_id=uuid4(),
        usuario_id=uuid4(),
        item_requisicao_id=data.item_id,
        evento_entrega_id=data.entrega_evento_id,
        tipo_evento=data.tipo_evento,
        quantidade=data.quantidade,
        operacao_execucao_id=data.operacao_execucao_id,
        deposito_id=data.deposito_id,
        lote_id=data.lote_id,
    )
    req_id = event.requisicao_id
    RequisicaoPosseService._validate_retry(event, data, req_id, event.usuario_id)
    with pytest.raises(BusinessRuleError):
        RequisicaoPosseService._validate_retry(
            event,
            data.model_copy(update={"quantidade": Decimal("9")}),
            req_id,
            event.usuario_id,
        )


def test_conciliation_status_distinguishes_pending_possession() -> None:
    assert RequisicaoRecebimentoService._conciliation_status(0, 0, 8) == "EM_POSSE"
    assert RequisicaoRecebimentoService._conciliation_status(0, 0, 0) == "CONCILIADO"
    assert RequisicaoRecebimentoService._conciliation_status(8, 0, 0) == "PENDENTE_DIVERGENCIA"


@pytest.mark.asyncio
async def test_returnable_cannot_be_consumed() -> None:
    data = _command(tipo_evento="CONSUMO")
    item = SimpleNamespace(natureza_item="RETORNAVEL")
    with pytest.raises(BusinessRuleError, match="retornável"):
        await RequisicaoPosseService(None, uuid4())._validate_nature_and_execution(
            SimpleNamespace(), item, data
        )


def test_01f_has_no_second_physical_exit_for_dispositions() -> None:
    source = Path("services/api/operacional/services/requisicao_posse_service.py").read_text()
    command = source[source.index("    async def destinar("):source.index("    async def _lock_request_item")]
    assert 'tipo_movimento="SAIDA"' not in command
    assert 'tipo_movimento="ENTRADA"' not in command
    assert "RequisicaoItemEvento" in command


def test_operation_closure_uses_canonical_conciliation_guard() -> None:
    source = Path("services/api/agricola/operacoes/service.py").read_text()
    assert "validar_operacao_conciliada" in source
