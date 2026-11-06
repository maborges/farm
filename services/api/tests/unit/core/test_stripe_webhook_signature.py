from unittest.mock import AsyncMock, patch

import pytest
import stripe
from fastapi import HTTPException

from core.routers.stripe_webhooks import stripe_webhook


class RequestStub:
    async def body(self):
        return b'{"id":"evt_test"}'


@pytest.mark.asyncio
async def test_webhook_rejects_missing_signature_before_verification():
    with patch("core.routers.stripe_webhooks.StripeService.verificar_webhook") as verify:
        with pytest.raises(HTTPException) as error:
            await stripe_webhook(RequestStub(), None)

    assert error.value.status_code == 400
    verify.assert_not_called()


@pytest.mark.asyncio
async def test_webhook_rejects_invalid_signature_without_processing_event():
    invalid = stripe.error.SignatureVerificationError("invalid signature", "sig")
    with patch(
        "core.routers.stripe_webhooks.StripeService.verificar_webhook", side_effect=invalid
    ), patch("core.routers.stripe_webhooks._handle_checkout_completed", new_callable=AsyncMock) as handle:
        with pytest.raises(HTTPException) as error:
            await stripe_webhook(RequestStub(), "invalid")

    assert error.value.status_code == 400
    handle.assert_not_awaited()


@pytest.mark.asyncio
async def test_webhook_processes_valid_signature_event():
    event = {"type": "checkout.session.completed", "data": {"object": {"id": "cs_test"}}}
    with patch("core.routers.stripe_webhooks.StripeService.verificar_webhook", return_value=event) as verify, \
         patch("core.routers.stripe_webhooks._handle_checkout_completed", new_callable=AsyncMock) as handle:
        result = await stripe_webhook(RequestStub(), "valid")

    assert result == {"status": "ok"}
    verify.assert_called_once_with(b'{"id":"evt_test"}', "valid")
    handle.assert_awaited_once_with({"id": "cs_test"})
