"""Notificador proativo consolidado com janela de throttling anti-ruído."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.admin_user import AdminUser
from core.schemas.agro_config_schemas import KEY_MERCADO
from core.services.agro_config_service import agro_config_service

from .models import AgroDataSource

AlertKindLiteral = Literal[
    "FALHA_CONSECUTIVA",
    "SUGESTAO_SENTINELA",
    "QUARENTENA_PENDENTE",
]

ALERT_THROTTLE_SEC = 21600
_MEMORY_THROTTLE: dict[tuple[str, str], datetime] = {}


def reset_alert_throttle() -> None:
    """Limpa o estado em memória de throttling (uso principal em suítes de teste)."""
    _MEMORY_THROTTLE.clear()


async def _acquire_alert_slot(
    slug: str,
    event_kind: AlertKindLiteral,
    *,
    redis_client: Any | None = None,
    now: datetime | None = None,
) -> bool:
    """Retorna ``True`` se a janela de 6h permite novo envio para ``(slug, event_kind)``."""
    ref_now = now or datetime.now(timezone.utc)  # noqa: UP017
    key = f"agro:collector:alert:{slug}:{event_kind}"
    if redis_client is not None:
        try:
            return bool(await redis_client.set(key, "1", nx=True, ex=ALERT_THROTTLE_SEC))
        except Exception as exc:
            logger.debug(f"[agro_collector] fallback throttle em memória para {key}: {exc}")

    prev = _MEMORY_THROTTLE.get((slug, event_kind))
    if prev is not None and (ref_now - prev) < timedelta(seconds=ALERT_THROTTLE_SEC):
        return False
    _MEMORY_THROTTLE[(slug, event_kind)] = ref_now
    return True


async def resolve_alert_recipients(
    session: AsyncSession,
    source: AgroDataSource,
) -> list[str]:
    """Resolve destinatários configurados na fonte, em ``agro:mercado:config`` ou ``admin_users``.

    Args:
        session: Sessão SQLAlchemy ativa.
        source: Fonte associada ao alerta.

    Returns:
        Lista deduplicada de e-mails válidos.
    """
    emails: list[str] = []
    cfg_src = source.config_extrator or {}
    src_emails = cfg_src.get("alert_emails")
    if isinstance(src_emails, list):
        emails.extend(str(e).strip() for e in src_emails if "@" in str(e))

    if not emails:
        try:
            val, _, _ = await agro_config_service.get_config(session, KEY_MERCADO, use_cache=False)
            if isinstance(val, dict) and isinstance(val.get("alert_emails"), list):
                emails.extend(str(e).strip() for e in val["alert_emails"] if "@" in str(e))
        except Exception as exc:
            logger.debug(f"[agro_collector] erro ao ler destinatários de config: {exc}")

    if not emails:
        try:
            rows = (
                await session.execute(select(AdminUser.email).where(AdminUser.ativo.is_(True)))
            ).scalars().all()
            emails.extend(str(e).strip() for e in rows if "@" in str(e))
        except (OperationalError, ProgrammingError):
            pass

    return list(dict.fromkeys(emails))


async def notify_collector_event(
    *,
    session: AsyncSession,
    source: AgroDataSource,
    event_kind: AlertKindLiteral,
    summary_lines: list[str],
    redis_client: Any | None = None,
    send_email_fn: Callable[[str, str, str], Awaitable[Any]] | None = None,
    now: datetime | None = None,
) -> int:
    """Envia resumo consolidado por e-mail respeitando janela de throttling sem ruído.

    Args:
        session: Sessão SQLAlchemy ativa.
        source: Fonte que originou o evento.
        event_kind: Categoria do alerta (falha, sentinela ou quarentena).
        summary_lines: Linhas legíveis que compõem o corpo do resumo.
        redis_client: Cliente Redis opcional para throttling distribuído.
        send_email_fn: Função assíncrona opcional substituindo ``enviar_email``.
        now: Referência UTC opcional para testes determinísticos.

    Returns:
        Quantidade de e-mails efetivamente despachados nesta chamada.
    """
    allowed = await _acquire_alert_slot(
        source.slug, event_kind, redis_client=redis_client, now=now
    )
    if not allowed:
        return 0

    recipients = await resolve_alert_recipients(session, source)
    if not recipients:
        return 0

    if send_email_fn is None:
        from notificacoes.email_service import enviar_email as default_send

        mailer = default_send
    else:
        mailer = send_email_fn

    subject_map = {
        "FALHA_CONSECUTIVA": f"[DeepFarms Agro] Falha recorrente na fonte {source.sigla}",
        "SUGESTAO_SENTINELA": f"[DeepFarms Agro] Sentinela encontrou nova URL para {source.sigla}",
        "QUARENTENA_PENDENTE": (
            f"[DeepFarms Agro] Itens em quarentena aguardam revisão ({source.sigla})"
        ),
    }
    subject = subject_map[event_kind]
    body = (
        f"Fonte: {source.nome} ({source.slug} / UF {source.uf_padrao})\n"
        f"Evento: {event_kind}\n\n"
        + "\n".join(f"- {line}" for line in summary_lines)
        + "\n\nAcesse Backoffice > Mercado & Fontes Oficiais para auditar."
    )

    sent_count = 0
    for email in recipients:
        try:
            await mailer(email, subject, body)
            sent_count += 1
        except Exception as exc:
            logger.warning(f"[agro_collector] falha ao notificar {email}: {exc}")
    return sent_count
