"""Serviço de envio e auditoria de e-mails para identidades individuais do Agro."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from loguru import logger

# Registro em memória de e-mails despachados para testes e homologação em ambiente controlado
_SENT_EMAILS_LOG: list[dict[str, Any]] = []


def get_sent_emails() -> list[dict[str, Any]]:
    """Retorna cópia da lista de e-mails despachados (para asserções de teste)."""
    return list(_SENT_EMAILS_LOG)


def clear_sent_emails() -> None:
    """Limpa o histórico de e-mails despachados."""
    _SENT_EMAILS_LOG.clear()


async def dispatch_verification_email(destinatario: str, nome: str, codigo: str) -> None:
    """Despacha e-mail com código de confirmação de 6 dígitos."""
    assunto = "DeepFarms Agro — Confirmação de E-mail"
    mensagem = (
        f"Olá, {nome}!\n\n"
        f"Seu código de confirmação para a conta individual DeepFarms Agro é:\n\n"
        f"    {codigo}\n\n"
        f"Este código expira em 24 horas. Se você não solicitou este cadastro, desconsidere esta mensagem."
    )

    registro = {
        "tipo": "CONFIRMACAO_EMAIL",
        "destinatario": destinatario,
        "nome": nome,
        "codigo": codigo,
        "assunto": assunto,
        "mensagem": mensagem,
        "enviado_em": datetime.now(timezone.utc).isoformat(),
    }
    _SENT_EMAILS_LOG.append(registro)
    logger.info("E-mail de confirmação despachado", destinatario=destinatario, codigo=codigo)

    # Tenta envio via serviço SMTP configurado
    try:
        from notificacoes.email_service import enviar_email
        asyncio.create_task(enviar_email(destinatario, assunto, mensagem))
    except Exception as exc:
        logger.warning(f"SMTP não disponível para envio imediato: {exc}")


async def dispatch_password_reset_email(destinatario: str, nome: str, token: str) -> None:
    """Despacha e-mail com instruções e token unívoco de recuperação de senha."""
    assunto = "DeepFarms Agro — Recuperação de Senha"
    mensagem = (
        f"Olá, {nome}!\n\n"
        f"Recebemos uma solicitação de redefinição de senha para sua conta individual DeepFarms Agro.\n\n"
        f"Seu token de recuperação seguro é:\n\n"
        f"    {token}\n\n"
        f"Este token possui uso único e expira em 60 minutos.\n"
        f"Caso não tenha feito essa solicitação, nenhuma ação é necessária e sua senha permanece segura."
    )

    registro = {
        "tipo": "RECUPERACAO_SENHA",
        "destinatario": destinatario,
        "nome": nome,
        "token": token,
        "assunto": assunto,
        "mensagem": mensagem,
        "enviado_em": datetime.now(timezone.utc).isoformat(),
    }
    _SENT_EMAILS_LOG.append(registro)
    logger.info("E-mail de recuperação de senha despachado", destinatario=destinatario)

    try:
        from notificacoes.email_service import enviar_email
        asyncio.create_task(enviar_email(destinatario, assunto, mensagem))
    except Exception as exc:
        logger.warning(f"SMTP não disponível para envio imediato: {exc}")
