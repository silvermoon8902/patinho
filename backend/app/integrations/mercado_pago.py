import hashlib
import hmac
import logging
from decimal import Decimal

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

MERCADO_PAGO_BASE_URL = "https://api.mercadopago.com"


class MercadoPagoClient:
    def __init__(self) -> None:
        self.base_url = MERCADO_PAGO_BASE_URL

    @property
    def access_token(self) -> str:
        return settings.MERCADO_PAGO_ACCESS_TOKEN

    @property
    def webhook_secret(self) -> str:
        return settings.MERCADO_PAGO_WEBHOOK_SECRET

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": None,  # set per-request
        }

    @property
    def is_sandbox(self) -> bool:
        return (self.access_token or "").startswith("TEST-")

    async def create_pix_payment(
        self,
        amount: Decimal,
        external_reference: str,
        description: str,
        payer_email: str | None = None,
        payer_first_name: str | None = None,
        payer_last_name: str | None = None,
        payer_cpf: str | None = None,
    ) -> dict:
        """Create a Pix payment via Mercado Pago API.

        MP rejects Pix payments when the payer block is missing
        identification (CPF), or when payer.email collides with the
        collector account. We forward the buyer's actual email/name and
        their registered CPF. In sandbox we accept a documented test CPF
        when the user has none on file; in live mode we refuse instead of
        sending a fake document.
        """
        if not self.access_token or self.access_token in ("", "TEST-xxx"):
            logger.warning("Mercado Pago not configured — returning mock payment")
            return {
                "id": f"mock-{external_reference[:8]}",
                "status": "pending",
                "qr_code": None,
                "qr_code_base64": None,
                "copy_paste": "MP_NOT_CONFIGURED",
            }

        cpf_digits = "".join(c for c in (payer_cpf or "") if c.isdigit())
        if not cpf_digits:
            if self.is_sandbox:
                # Documented sandbox-valid CPF used only with TEST-* tokens
                # so live deposits never go out with a placeholder document.
                cpf_digits = "19119119100"
            else:
                from fastapi import HTTPException, status as http_status

                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Cadastre seu CPF no perfil antes de depositar. "
                        "O Mercado Pago exige CPF para pagamentos Pix."
                    ),
                )

        payload = {
            "transaction_amount": float(amount),
            "description": description,
            "payment_method_id": "pix",
            "external_reference": external_reference,
            "payer": {
                "email": payer_email or "comprador@patinho.app",
                "first_name": payer_first_name or "Comprador",
                "last_name": payer_last_name or "Patinho",
                "identification": {
                    "type": "CPF",
                    "number": cpf_digits,
                },
            },
        }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": external_reference,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/payments",
                json=payload,
                headers=headers,
            )

        if response.status_code not in (200, 201):
            logger.error(
                "Mercado Pago create_pix_payment failed: %s %s",
                response.status_code,
                response.text,
            )
            raise httpx.HTTPStatusError(
                f"MP API error: {response.status_code}",
                request=response.request,
                response=response,
            )

        data = response.json()
        point_of_interaction = data.get("point_of_interaction", {})
        transaction_data = point_of_interaction.get("transaction_data", {})

        return {
            "id": str(data["id"]),
            "status": data["status"],
            "qr_code": transaction_data.get("qr_code"),
            "qr_code_base64": transaction_data.get("qr_code_base64"),
            "copy_paste": transaction_data.get("qr_code"),
        }

    async def get_payment(self, payment_id: str) -> dict:
        """Fetch payment details from Mercado Pago."""
        if not self.access_token or self.access_token in ("", "TEST-xxx"):
            logger.warning("Mercado Pago not configured — cannot fetch payment")
            return {"status": "pending", "external_reference": ""}

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/v1/payments/{payment_id}",
                headers=headers,
            )

        if response.status_code != 200:
            logger.error(
                "Mercado Pago get_payment failed: %s %s",
                response.status_code,
                response.text,
            )
            raise httpx.HTTPStatusError(
                f"MP API error: {response.status_code}",
                request=response.request,
                response=response,
            )

        return response.json()

    def verify_webhook_signature(self, signature: str, raw_body: bytes) -> bool:
        """Verify the x-signature HMAC from Mercado Pago webhook."""
        if not self.webhook_secret:
            logger.warning("Webhook secret not configured, skipping verification")
            return True

        # MP sends signature in format: ts=<timestamp>,v1=<hash>
        parts = {}
        for part in signature.split(","):
            key, _, value = part.strip().partition("=")
            parts[key] = value

        ts = parts.get("ts", "")
        v1 = parts.get("v1", "")

        if not ts or not v1:
            return False

        # Build the signed payload: id:<data_id>;request-id:<request_id>;ts:<ts>;
        # For simplicity, use the manifest template from MP docs
        manifest = f"{ts}.{raw_body.decode('utf-8')}"
        expected = hmac.new(
            self.webhook_secret.encode("utf-8"),
            manifest.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, v1)


mp_client = MercadoPagoClient()
