"""
Webhook handler para pagamentos de créditos de IA.

Registra: POST /pagamentos/webhook

Eventos tratados:
- status=PAID → ativa pacote de créditos IA para o tenant
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field
from loguru import logger
from sqlalchemy import select

from core.config import settings
from core.database import async_session_maker
from core.models.solicitacoes_comerciais import SolicitacaoComercial
from ia.models import IACreditosPacote

router = APIRouter(prefix="/pagamentos", tags=["Pagamentos — Webhooks"])

_STATUS_PAGO = "PAGO"


class WebhookPagamentoPayload(BaseModel):
    status: str
    solicitacao_id: str = Field(..., description="UUID da SolicitacaoComercial")
    valor: Optional[float] = None


def _validar_secret(header_secret: Optional[str]) -> None:
    """Valida o secret do webhook. Em dev (secret vazio) ignora a validação."""
    secret_configurado = getattr(settings, "pagamentos_webhook_secret", "")
    if not secret_configurado:
        return
    if header_secret != secret_configurado:
        logger.warning("Webhook pagamento recebido com secret inválido")
        raise HTTPException(status_code=401, detail="Assinatura de webhook inválida")


@router.post("/webhook", include_in_schema=False)
async def pagamentos_webhook(
    request: Request,
    body: WebhookPagamentoPayload,
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
):
    _validar_secret(x_webhook_secret)

    logger.bind(
        event="webhook_pagamento_recebido",
        solicitacao_id=body.solicitacao_id,
        status=body.status,
        valor=body.valor,
    ).info("webhook_pagamento_recebido")

    if body.status != "PAID":
        logger.bind(
            event="webhook_status_ignorado",
            solicitacao_id=body.solicitacao_id,
            status=body.status,
        ).info("webhook_status_ignorado")
        return {"status": "ignored", "reason": "status não processável"}

    try:
        solicitacao_uuid = uuid.UUID(body.solicitacao_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="solicitacao_id inválido")

    await _ativar_creditos(solicitacao_uuid)
    return {"status": "ok"}


async def _ativar_creditos(solicitacao_id: uuid.UUID) -> None:
    async with async_session_maker() as db:
        try:
            solicitacao: Optional[SolicitacaoComercial] = await db.get(
                SolicitacaoComercial, solicitacao_id
            )

            if not solicitacao:
                logger.error(
                    f"Webhook: solicitacao {solicitacao_id} não encontrada"
                )
                return

            if solicitacao.tipo != "CREDITOS_IA":
                logger.warning(
                    f"Webhook: solicitacao {solicitacao_id} tem tipo {solicitacao.tipo}, ignorado"
                )
                return

            # Idempotência: já processada anteriormente
            if solicitacao.status_pagamento == _STATUS_PAGO:
                logger.bind(
                    event="webhook_duplicado_ignorado",
                    solicitacao_id=str(solicitacao_id),
                ).info("webhook_duplicado_ignorado")
                return

            # Extrair quantidade dos detalhes
            detalhes = solicitacao.detalhes or {}
            quantidade = detalhes.get("quantidade")
            if not quantidade or not isinstance(quantidade, int) or quantidade <= 0:
                logger.error(
                    f"Webhook: quantidade inválida ou ausente em solicitacao {solicitacao_id}: {quantidade}"
                )
                return

            # Ativar pacote de créditos
            pacote = IACreditosPacote(
                id=uuid.uuid4(),
                tenant_id=solicitacao.tenant_id,
                quantidade_creditos=quantidade,
                creditos_usados=0,
                origem="PAGAMENTO",
                status="ATIVO",
                adquirido_em=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            )
            db.add(pacote)

            # Atualizar solicitação
            solicitacao.status_pagamento = _STATUS_PAGO
            solicitacao.status = "CONCLUIDA"
            solicitacao.updated_at = datetime.now(timezone.utc)

            await db.commit()

            logger.bind(
                event="creditos_ia_ativados",
                tenant_id=str(solicitacao.tenant_id),
                solicitacao_id=str(solicitacao_id),
                quantidade=quantidade,
                pacote_id=str(pacote.id),
            ).info("creditos_ia_ativados")

        except Exception as e:
            await db.rollback()
            logger.error(f"Erro ao processar webhook pagamento {solicitacao_id}: {e}")
            raise
