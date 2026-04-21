import logging
from email.message import EmailMessage

import aiosmtplib

from app.config import settings

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, html: str, text: str | None = None) -> bool:
    """Send an email via configured SMTP. Returns False (and logs) if not configured."""
    if not settings.SMTP_HOST:
        logger.warning("SMTP not configured — skipping email to %s (%s)", to, subject)
        return False
    msg = EmailMessage()
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = to
    msg["Subject"] = subject
    if text:
        msg.set_content(text)
        msg.add_alternative(html, subtype="html")
    else:
        msg.set_content(html, subtype="html")
    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME or None,
            password=settings.SMTP_PASSWORD or None,
            use_tls=False,
            start_tls=settings.SMTP_USE_TLS,
        )
        logger.info("Email sent to %s (%s)", to, subject)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to)
        return False


def render_password_reset(name: str, reset_url: str) -> tuple[str, str]:
    html = f"""<!DOCTYPE html>
<html lang="pt-BR"><body style="font-family:Arial,sans-serif;background:#f5f5f5;padding:20px;">
<div style="max-width:480px;margin:0 auto;background:white;padding:32px;border-radius:12px;">
<h1 style="color:#001F3F;">Patinho</h1>
<h2>Redefinir senha</h2>
<p>Olá, {name}!</p>
<p>Recebemos uma solicitação para redefinir sua senha. Clique no botão para criar uma nova:</p>
<p style="text-align:center;margin:32px 0;">
<a href="{reset_url}" style="background:#FFD10D;color:#001F3F;padding:14px 28px;text-decoration:none;border-radius:8px;font-weight:bold;">Redefinir senha</a>
</p>
<p style="color:#6b7280;font-size:14px;">Este link expira em 1 hora. Se você não solicitou, ignore este e-mail.</p>
</div></body></html>"""
    text = f"""Olá, {name}!

Para redefinir sua senha, acesse (válido por 1 hora):
{reset_url}

Se você não solicitou, ignore este e-mail.
— Patinho
"""
    return html, text


def render_welcome(name: str, app_url: str) -> tuple[str, str]:
    html = f"""<!DOCTYPE html>
<html lang="pt-BR"><body style="font-family:Arial,sans-serif;background:#f5f5f5;padding:20px;">
<div style="max-width:480px;margin:0 auto;background:white;padding:32px;border-radius:12px;">
<h1 style="color:#001F3F;">Bem-vindo ao Patinho, {name}!</h1>
<p>Sua conta foi criada com sucesso. Agora você pode criar desafios e convidar amigos.</p>
<p style="text-align:center;margin:32px 0;">
<a href="{app_url}" style="background:#FFD10D;color:#001F3F;padding:14px 28px;text-decoration:none;border-radius:8px;font-weight:bold;">Começar</a>
</p>
</div></body></html>"""
    text = f"Bem-vindo, {name}! Acesse: {app_url}\n— Patinho"
    return html, text


def render_prize_won(name: str, bet_title: str, amount: str, bet_url: str) -> tuple[str, str]:
    html = f"""<!DOCTYPE html>
<html lang="pt-BR"><body style="font-family:Arial,sans-serif;background:#f5f5f5;padding:20px;">
<div style="max-width:480px;margin:0 auto;background:white;padding:32px;border-radius:12px;">
<h1 style="color:#001F3F;">Parabéns, {name}!</h1>
<p>Você ganhou o desafio:</p>
<h3 style="background:#001F3F;color:#FFD10D;padding:12px;border-radius:8px;">{bet_title}</h3>
<p>Prêmio creditado: <strong style="color:#22C55E;font-size:24px;">{amount}</strong></p>
<p style="text-align:center;margin:32px 0;">
<a href="{bet_url}" style="background:#FFD10D;color:#001F3F;padding:14px 28px;text-decoration:none;border-radius:8px;font-weight:bold;">Ver resultado</a>
</p>
</div></body></html>"""
    text = f"Parabéns, {name}! Você ganhou '{bet_title}'. Prêmio: {amount}\n{bet_url}\n— Patinho"
    return html, text
