"""
Router para webhooks do Asaas.

Recebe notificações de eventos de pagamento do gateway Asaas.
"""
import secrets

from fastapi import APIRouter, HTTPException, Request, status
from loguru import logger

from core.config import settings
from core.database import async_session_maker
from core.services.asaas_service import AsaasService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def _validar_assinatura_asaas(request: Request) -> None:
    """Valida o token de autenticação do webhook Asaas (header asaas-access-token).

    O Asaas reenvia, em cada chamada de webhook, o valor configurado como
    "Token de autenticação" no painel de integrações. Sem essa checagem,
    qualquer requisição externa poderia forjar eventos de pagamento/cobrança.
    """
    if not settings.asaas_webhook_token:
        logger.warning(
            "ASAAS_WEBHOOK_TOKEN não configurado — validação de assinatura do "
            "webhook Asaas está desabilitada. Configure antes de ir para produção."
        )
        return

    token_recebido = request.headers.get("asaas-access-token", "")
    if not secrets.compare_digest(token_recebido, settings.asaas_webhook_token):
        logger.error("Webhook Asaas rejeitado: token de autenticação inválido ou ausente.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")


@router.post(
    "/asaas",
    status_code=status.HTTP_200_OK,
    summary="Webhook do Asaas",
    description="Recebe notificações de eventos de pagamento do Asaas"
)
async def webhook_asaas(request: Request):
    """
    Processa webhooks do Asaas.

    **Eventos suportados:**
    - PAYMENT_RECEIVED: Pagamento recebido (PIX, cartão)
    - PAYMENT_CONFIRMED: Pagamento confirmado (boleto após compensação)
    - PAYMENT_OVERDUE: Pagamento vencido
    - PAYMENT_DELETED: Cobrança cancelada
    - PAYMENT_RESTORED: Cobrança restaurada

    **Segurança:**
    - Valida o header `asaas-access-token` contra `settings.asaas_webhook_token`.

    **Documentação Asaas:**
    https://docs.asaas.com/reference/webhooks
    """
    _validar_assinatura_asaas(request)

    try:
        # Receber payload
        payload = await request.json()

        logger.info(f"Webhook Asaas recebido: {payload.get('event')}")

        # Processar webhook
        async with async_session_maker() as session:
            asaas_service = AsaasService(session)

            success = await asaas_service.processar_webhook(payload)

            if success:
                return {"status": "processed", "message": "Webhook processado com sucesso"}
            else:
                logger.warning("Webhook não foi processado completamente")
                return {"status": "ignored", "message": "Webhook ignorado"}

    except ValueError as e:
        logger.error(f"Payload inválido no webhook Asaas: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload inválido."
        )
    except Exception as e:
        logger.error(f"Erro ao processar webhook Asaas: {e}", exc_info=True)
        # Retornar 200 mesmo com erro para evitar reenvios desnecessários
        # Asaas reenvia webhook se receber 4xx/5xx
        return {"status": "error", "message": "Erro ao processar webhook"}


@router.get(
    "/asaas/health",
    summary="Health check do webhook",
    description="Endpoint de teste para verificar se webhook está acessível"
)
async def webhook_asaas_health():
    """Health check para webhook do Asaas."""
    return {
        "status": "ok",
        "service": "asaas-webhook",
        "message": "Webhook está operacional"
    }
