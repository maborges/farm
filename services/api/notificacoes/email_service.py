import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from loguru import logger
import asyncio
from concurrent.futures import ThreadPoolExecutor

from core.config import settings

# Executor para rodar o envio de email sem bloquear o event loop principal
executor = ThreadPoolExecutor(max_workers=3)

def _send_email_sync(destinatario: str, assunto: str, mensagem: str):
    if not settings.smtp_host:
        logger.warning(f"SMTP não configurado. Ignorando envio de email para {destinatario}.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = settings.mail_from
    msg["To"] = destinatario

    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #ef4444;">AgroSaaS &mdash; Atenção na sua safra</h2>
            <p><strong>Problema detectado:</strong></p>
            <p>{mensagem.replace(chr(10), '<br>')}</p>
            <br>
            <a href="{settings.frontend_url}/dashboard" 
               style="background-color: #16a34a; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block;">
               Acessar Dashboard
            </a>
            <hr style="margin-top: 30px; border: none; border-top: 1px solid #e2e8f0;">
            <small style="color: #64748b;">Este é um alerta automático do sistema. Por favor, não responda.</small>
        </div>
      </body>
    </html>
    """
    
    part = MIMEText(html, "html")
    msg.attach(part)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            # Em ambientes de produção reais o ideal seria `server.starttls()` se suportado,
            # mas mantemos simples e compatível com mailtrap sem TLS no default
            if settings.smtp_user and settings.smtp_pass:
                server.login(settings.smtp_user, settings.smtp_pass)
            server.send_message(msg)
            
        logger.info(f"Email enviado com sucesso para {destinatario}: {assunto}")
    except Exception as e:
        # Logs robustos, mas não lançamos erro para garantir que a aplicação não quebre
        logger.error(f"Falha ao enviar email para {destinatario} via {settings.smtp_host}:{settings.smtp_port}: {e}")

async def enviar_email(destinatario: str, assunto: str, mensagem: str):
    """Envia email proativo em background usando um thread pool."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(executor, _send_email_sync, destinatario, assunto, mensagem)
