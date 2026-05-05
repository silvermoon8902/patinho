import logging
from email.message import EmailMessage

import aiosmtplib

from app.config import settings

logger = logging.getLogger(__name__)


def _footer_html(reason: str) -> str:
    """Shared footer with brand, reason, and LGPD contact info."""
    support = settings.SMTP_FROM_EMAIL or "contato@patinho.app"
    return f"""
<div style="max-width:480px;margin:16px auto 0;padding:16px 32px;font-family:Arial,sans-serif;color:#6b7280;font-size:11px;line-height:1.6;">
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:0 0 12px;" />
  <p style="margin:0 0 8px;">
    <strong style="color:#001F3F;">Patinho</strong> — Desafios entre amigos
  </p>
  <p style="margin:0 0 6px;">{reason}</p>
  <p style="margin:0;">
    Dúvidas ou solicitações sobre seus dados? Escreva para
    <a href="mailto:{support}" style="color:#001F3F;">{support}</a>.
  </p>
</div>"""


def _footer_text(reason: str) -> str:
    support = settings.SMTP_FROM_EMAIL or "contato@patinho.app"
    return f"""
—
Patinho — Desafios entre amigos
{reason}
Contato: {support}"""


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
    reason = "Você recebeu este e-mail porque solicitou a redefinição da sua senha no Patinho."
    html = f"""<!DOCTYPE html>
<html lang="pt-BR"><body style="font-family:Arial,sans-serif;background:#f5f5f5;padding:20px;margin:0;">
<div style="max-width:480px;margin:0 auto;background:white;padding:32px;border-radius:12px;">
<h1 style="color:#001F3F;margin:0 0 8px;">Patinho</h1>
<h2 style="margin:0 0 16px;">Redefinir senha</h2>
<p style="color:#333;">Olá, {name}!</p>
<p style="color:#333;">Recebemos uma solicitação para redefinir sua senha. Clique no botão para criar uma nova:</p>
<p style="text-align:center;margin:32px 0;">
<a href="{reset_url}" style="background:#FFD10D;color:#001F3F;padding:14px 28px;text-decoration:none;border-radius:8px;font-weight:bold;display:inline-block;">Redefinir senha</a>
</p>
<p style="color:#6b7280;font-size:14px;">Este link expira em 1 hora. Se você não solicitou, ignore este e-mail.</p>
</div>
{_footer_html(reason)}
</body></html>"""
    text = f"""Olá, {name}!

Para redefinir sua senha, acesse (válido por 1 hora):
{reset_url}

Se você não solicitou, ignore este e-mail.
{_footer_text(reason)}
"""
    return html, text


def render_welcome(name: str, app_url: str) -> tuple[str, str]:
    reason = "Você recebeu este e-mail porque acabou de criar uma conta no Patinho."
    html = f"""<!DOCTYPE html>
<html lang="pt-BR"><body style="font-family:Arial,sans-serif;background:#f5f5f5;padding:20px;margin:0;">
<div style="max-width:480px;margin:0 auto;background:white;padding:32px;border-radius:12px;">
<h1 style="color:#001F3F;margin:0 0 16px;">Bem-vindo ao Patinho, {name}!</h1>
<p style="color:#333;">Sua conta foi criada com sucesso. Agora você pode criar desafios e convidar amigos.</p>
<p style="text-align:center;margin:32px 0;">
<a href="{app_url}" style="background:#FFD10D;color:#001F3F;padding:14px 28px;text-decoration:none;border-radius:8px;font-weight:bold;display:inline-block;">Começar</a>
</p>
</div>
{_footer_html(reason)}
</body></html>"""
    text = f"""Bem-vindo, {name}!

Acesse: {app_url}
{_footer_text(reason)}
"""
    return html, text


def render_bet_invite(
    inviter_name: str,
    bet_title: str,
    invite_url: str,
    entry_amount: str,
) -> tuple[str, str]:
    """Returns (html, text) for a bet invite email."""
    reason = (
        f"Você recebeu este e-mail porque {inviter_name} te adicionou como "
        "convidado para um desafio no Patinho. Se você não conhece essa "
        "pessoa, pode ignorar esta mensagem — nenhum dado seu foi exposto."
    )
    html = f"""<!DOCTYPE html>
<html lang="pt-BR"><body style="font-family:Arial,sans-serif;background:#f5f5f5;padding:20px;margin:0;">
<div style="max-width:480px;margin:0 auto;background:white;padding:32px;border-radius:12px;">
<h1 style="color:#001F3F;margin:0 0 8px;">Patinho</h1>
<h2 style="color:#001F3F;margin:0 0 16px;">Você recebeu um convite!</h2>
<p style="color:#333;"><strong>{inviter_name}</strong> te convidou para participar do desafio:</p>
<h3 style="background:#001F3F;color:#FFD10D;padding:12px;border-radius:8px;margin:16px 0;">{bet_title}</h3>
<p style="color:#333;">Valor de entrada: <strong style="color:#001F3F;">{entry_amount}</strong></p>
<p style="text-align:center;margin:32px 0;">
<a href="{invite_url}" style="background:#FFD10D;color:#001F3F;padding:14px 28px;text-decoration:none;border-radius:8px;font-weight:bold;display:inline-block;">Participar do Desafio</a>
</p>
<p style="color:#6b7280;font-size:14px;">Se o botão não funcionar, copie e cole este link no seu navegador:<br/>
<a href="{invite_url}" style="color:#001F3F;word-break:break-all;">{invite_url}</a></p>
</div>
{_footer_html(reason)}
</body></html>"""
    text = f"""Olá!

{inviter_name} te convidou para participar do desafio "{bet_title}" no Patinho.

Valor de entrada: {entry_amount}

Acesse o link abaixo para ver as regras e participar:
{invite_url}
{_footer_text(reason)}
"""
    return html, text


def render_bet_locked_creator(
    creator_name: str,
    bet_title: str,
    bet_url: str,
) -> tuple[str, str]:
    """Sent to the creator when their voting bet hits closes_at.

    The bet is now in LOCKED state and waits for the creator to declare
    the winner. Without a reminder, creators miss the transition and
    funds stay frozen until our 7-day safety net cancels the bet.
    """
    reason = (
        "Você recebeu este e-mail porque o prazo de um desafio que você "
        "criou no Patinho terminou e está aguardando sua decisão."
    )
    html = f"""<!DOCTYPE html>
<html lang="pt-BR"><body style="font-family:Arial,sans-serif;background:#f5f5f5;padding:20px;margin:0;">
<div style="max-width:480px;margin:0 auto;background:white;padding:32px;border-radius:12px;">
<h1 style="color:#001F3F;margin:0 0 8px;">Patinho</h1>
<h2 style="color:#001F3F;margin:0 0 16px;">Hora de declarar o vencedor</h2>
<p style="color:#333;">Olá, {creator_name}!</p>
<p style="color:#333;">O prazo do desafio abaixo terminou. Como criador, você precisa escolher a opção vencedora para que os participantes possam aceitar ou contestar o resultado:</p>
<h3 style="background:#001F3F;color:#FFD10D;padding:12px;border-radius:8px;margin:16px 0;">{bet_title}</h3>
<p style="text-align:center;margin:32px 0;">
<a href="{bet_url}" style="background:#FFD10D;color:#001F3F;padding:14px 28px;text-decoration:none;border-radius:8px;font-weight:bold;display:inline-block;">Declarar vencedor</a>
</p>
<p style="color:#6b7280;font-size:14px;">Se você não declarar nos próximos 7 dias, o desafio será cancelado automaticamente e todos os participantes receberão reembolso.</p>
</div>
{_footer_html(reason)}
</body></html>"""
    text = f"""Olá, {creator_name}!

O prazo do desafio "{bet_title}" terminou. Como criador, você precisa escolher a opção vencedora.

Acesse: {bet_url}

Se não declarar em 7 dias, o desafio será cancelado e todos receberão reembolso.
{_footer_text(reason)}
"""
    return html, text


def render_winner_declared_participant(
    name: str,
    bet_title: str,
    winner_label: str,
    bet_url: str,
) -> tuple[str, str]:
    """Sent to non-creator participants after creator declares the winner.

    Recipients have 24h to accept or contest before auto-resolution.
    """
    reason = (
        "Você recebeu este e-mail porque participa de um desafio no Patinho "
        "cujo vencedor acaba de ser declarado pelo criador."
    )
    html = f"""<!DOCTYPE html>
<html lang="pt-BR"><body style="font-family:Arial,sans-serif;background:#f5f5f5;padding:20px;margin:0;">
<div style="max-width:480px;margin:0 auto;background:white;padding:32px;border-radius:12px;">
<h1 style="color:#001F3F;margin:0 0 8px;">Patinho</h1>
<h2 style="color:#001F3F;margin:0 0 16px;">Resultado declarado</h2>
<p style="color:#333;">Olá, {name}!</p>
<p style="color:#333;">O criador do desafio abaixo declarou o vencedor. Você tem <strong>24 horas</strong> para aceitar ou contestar antes que o pagamento seja liberado:</p>
<h3 style="background:#001F3F;color:#FFD10D;padding:12px;border-radius:8px;margin:16px 0;">{bet_title}</h3>
<p style="color:#333;">Opção vencedora declarada: <strong>{winner_label}</strong></p>
<p style="text-align:center;margin:32px 0;">
<a href="{bet_url}" style="background:#FFD10D;color:#001F3F;padding:14px 28px;text-decoration:none;border-radius:8px;font-weight:bold;display:inline-block;">Ver desafio e responder</a>
</p>
<p style="color:#6b7280;font-size:14px;">Se você não responder em 24h, o resultado é considerado aceito e o pagamento é distribuído.</p>
</div>
{_footer_html(reason)}
</body></html>"""
    text = f"""Olá, {name}!

O criador do desafio "{bet_title}" declarou que a opção vencedora é "{winner_label}".

Você tem 24 horas para aceitar ou contestar: {bet_url}

Se não responder, o resultado é considerado aceito.
{_footer_text(reason)}
"""
    return html, text


def render_prize_won(name: str, bet_title: str, amount: str, bet_url: str) -> tuple[str, str]:
    reason = "Você recebeu este e-mail porque ganhou um prêmio em um desafio que você participou no Patinho."
    html = f"""<!DOCTYPE html>
<html lang="pt-BR"><body style="font-family:Arial,sans-serif;background:#f5f5f5;padding:20px;margin:0;">
<div style="max-width:480px;margin:0 auto;background:white;padding:32px;border-radius:12px;">
<h1 style="color:#001F3F;margin:0 0 16px;">Parabéns, {name}!</h1>
<p style="color:#333;">Você ganhou o desafio:</p>
<h3 style="background:#001F3F;color:#FFD10D;padding:12px;border-radius:8px;">{bet_title}</h3>
<p style="color:#333;">Prêmio creditado: <strong style="color:#22C55E;font-size:24px;">{amount}</strong></p>
<p style="text-align:center;margin:32px 0;">
<a href="{bet_url}" style="background:#FFD10D;color:#001F3F;padding:14px 28px;text-decoration:none;border-radius:8px;font-weight:bold;display:inline-block;">Ver resultado</a>
</p>
</div>
{_footer_html(reason)}
</body></html>"""
    text = f"""Parabéns, {name}!

Você ganhou '{bet_title}'. Prêmio: {amount}
{bet_url}
{_footer_text(reason)}
"""
    return html, text
