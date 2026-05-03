"""Step 133 — Lembretes automáticos de follow-up comercial."""
from datetime import datetime, timezone, timedelta
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.solicitacoes_comerciais import SolicitacaoComercial
from notificacoes.models import Notificacao

TIPO_FOLLOWUP = "FOLLOWUP_COMERCIAL"
JANELA_HORAS = 1       # notificar se dentro de 1h
COOLDOWN_HORAS = 24    # não re-enviar dentro de 24h


async def _ja_notificado(
    session: AsyncSession,
    solicitacao_id: UUID,
    usuario_id: UUID,
    nivel: str,
) -> bool:
    """True se já existe notificação nas últimas COOLDOWN_HORAS para este follow-up."""
    limite = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=COOLDOWN_HORAS)
    stmt = (
        select(Notificacao)
        .where(
            Notificacao.tipo == TIPO_FOLLOWUP,
            Notificacao.origem == "followup",
            Notificacao.origem_id == str(solicitacao_id),
            Notificacao.usuario_id == usuario_id,
            Notificacao.nivel == nivel,
            Notificacao.created_at >= limite,
        )
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def process_followups(session: AsyncSession) -> int:
    """
    Busca solicitações com follow-up próximo ou atrasado e emite notificações.
    Criadas a quantidade de notificações criadas.
    """
    now = datetime.utcnow()
    janela = now + timedelta(hours=JANELA_HORAS)

    stmt = select(SolicitacaoComercial).where(
        SolicitacaoComercial.proximo_followup_em.is_not(None),
        SolicitacaoComercial.proximo_followup_em <= janela,
        SolicitacaoComercial.status != "CONCLUIDA",
        SolicitacaoComercial.responsavel_usuario_id.is_not(None),
    )
    result = await session.execute(stmt)
    solicitacoes = result.scalars().all()

    if not solicitacoes:
        logger.debug("[followup_worker] Nenhum follow-up a processar.")
        return 0

    logger.info(f"[followup_worker] {len(solicitacoes)} follow-up(s) identificado(s).")

    criadas = 0
    for sol in solicitacoes:
        usuario_id: UUID = sol.responsavel_usuario_id
        atrasado = sol.proximo_followup_em < now
        nivel = "DANGER" if atrasado else "WARNING"

        if await _ja_notificado(session, sol.id, usuario_id, nivel):
            logger.info(
                f"[followup_worker] Suprimido (cooldown): sol={sol.id} nivel={nivel}"
            )
            continue

        # Buscar nome do tenant para a mensagem
        from core.models.tenant import Tenant
        tenant = await session.get(Tenant, sol.tenant_id)
        tenant_nome = tenant.nome if tenant else str(sol.tenant_id)

        if atrasado:
            prazo_fmt = sol.proximo_followup_em.strftime("%d/%m %H:%M")
            mensagem = (
                f"Follow-up com '{tenant_nome}' está atrasado "
                f"(previsto para {prazo_fmt})."
            )
        else:
            prazo_fmt = sol.proximo_followup_em.strftime("%d/%m %H:%M")
            mensagem = (
                f"Você tem um follow-up agendado para '{tenant_nome}' "
                f"às {prazo_fmt}."
            )

        notif = Notificacao(
            tenant_id=sol.tenant_id,
            tipo=TIPO_FOLLOWUP,
            titulo="Lembrete de Follow-up Comercial",
            mensagem=mensagem,
            nivel=nivel,
            lida=False,
            meta={},
            origem="followup",
            origem_id=str(sol.id),
            usuario_id=usuario_id,
        )
        session.add(notif)
        criadas += 1
        logger.info(
            f"[followup_worker] Notificação criada: nivel={nivel} "
            f"sol={sol.id} responsavel={usuario_id}"
        )

        # E-mail apenas para DANGER (follow-up atrasado)
        if nivel == "DANGER":
            await _enviar_email_followup(session, usuario_id, tenant_nome, mensagem)

    if criadas:
        await session.commit()
        logger.info(f"[followup_worker] {criadas} notificação(ões) salva(s).")

    return criadas


async def _enviar_email_followup(
    session: AsyncSession,
    usuario_id: UUID,
    tenant_nome: str,
    mensagem: str,
) -> None:
    """Envia e-mail ao responsável AdminUser quando follow-up está atrasado."""
    try:
        from core.models.admin_user import AdminUser
        admin = await session.get(AdminUser, usuario_id)
        if not admin or not admin.email:
            logger.warning(
                f"[followup_worker] AdminUser {usuario_id} sem e-mail — e-mail não enviado."
            )
            return

        import asyncio
        from notificacoes.email_service import enviar_email

        assunto = f"AgroSaaS — Follow-up atrasado: {tenant_nome}"
        asyncio.create_task(enviar_email(admin.email, assunto, mensagem))
        logger.info(f"[followup_worker] E-mail agendado para {admin.email}")
    except Exception as exc:
        logger.error(f"[followup_worker] Falha ao enviar e-mail: {exc}")
