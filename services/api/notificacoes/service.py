from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, func
from fastapi import WebSocket
from loguru import logger

from core.base_service import BaseService
from notificacoes.models import Notificacao
from notificacoes.schemas import NotificacaoCreate


class NotificationManager:
    """Manages active WebSocket connections grouped by tenant_id."""

    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, tenant_id: str, ws: WebSocket):
        await ws.accept()
        self._connections.setdefault(tenant_id, []).append(ws)

    def disconnect(self, tenant_id: str, ws: WebSocket):
        conns = self._connections.get(tenant_id, [])
        if ws in conns:
            conns.remove(ws)

    async def push(self, tenant_id: str, data: dict):
        for ws in list(self._connections.get(str(tenant_id), [])):
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(str(tenant_id), ws)


manager = NotificationManager()


class NotificacaoService(BaseService[Notificacao]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(Notificacao, session, tenant_id)

    async def criar_e_push(self, dados: NotificacaoCreate) -> Notificacao | None:
        from core.models.tenant import Tenant
        from core.models.auth import Usuario
        from notificacoes.models import NotificacaoPreferencia
        from datetime import datetime, timezone, timedelta
        
        COOLDOWN_HORAS = 24
        
        # Encontrar o responsável para validar as preferências
        stmt = select(Tenant.email_responsavel).where(Tenant.id == self.tenant_id)
        email_resp = (await self.session.execute(stmt)).scalar()
        
        enviar_por_email = True
        sistema_ativo = True
        sensibilidade = "ALTO"
        user = None
        
        if email_resp:
            stmt_user = select(Usuario).where(Usuario.email == email_resp).limit(1)
            user = (await self.session.execute(stmt_user)).scalar_one_or_none()

        usuario_id = user.id if user else None

        # --- Anti-spam Cooldown ---
        # Usar naive datetime pois a coluna created_at é TIMESTAMP WITHOUT TIME ZONE no banco
        limite_tempo = datetime.now().replace(microsecond=0) - timedelta(hours=COOLDOWN_HORAS)
        
        stmt_cooldown = select(Notificacao).where(
            Notificacao.tenant_id == self.tenant_id,
            Notificacao.tipo == dados.tipo,
            Notificacao.nivel == dados.nivel,
            Notificacao.created_at >= limite_tempo
        )
        if dados.origem:
            stmt_cooldown = stmt_cooldown.where(Notificacao.origem == dados.origem)
        if dados.origem_id:
            stmt_cooldown = stmt_cooldown.where(Notificacao.origem_id == dados.origem_id)
        if usuario_id:
            stmt_cooldown = stmt_cooldown.where(Notificacao.usuario_id == usuario_id)
            
        recente = (await self.session.execute(stmt_cooldown.limit(1))).scalar_one_or_none()
        if recente:
            logger.info(f"Notificação suprimida por cooldown: {dados.tipo} (origem={dados.origem})")
            return None
        # --------------------------

        if user:
            stmt_pref = select(NotificacaoPreferencia).where(
                NotificacaoPreferencia.tenant_id == self.tenant_id,
                NotificacaoPreferencia.usuario_id == user.id,
                NotificacaoPreferencia.tipo == dados.tipo
            )
            pref = (await self.session.execute(stmt_pref)).scalar_one_or_none()
            if pref:
                enviar_por_email = pref.email_ativo
                sistema_ativo = pref.sistema_ativo
                sensibilidade = pref.nivel_sensibilidade

        # --- Filtro de Sensibilidade (Step 196) ---
        # ALTO: Todas passão
        # MEDIO: Apenas WARNING e DANGER passão
        # BAIXO: Apenas DANGER passão
        if sensibilidade == "MEDIO" and dados.nivel not in ["WARNING", "DANGER"]:
            return None
        if sensibilidade == "BAIXO" and dados.nivel != "DANGER":
            return None
        # ------------------------------------------

        if not sistema_ativo:
            # Se sistema está desativado mas email ativo, ainda enviamos email se for crítico
            if enviar_por_email and dados.nivel == "DANGER" and email_resp:
                pass # continua para o envio de email
            else:
                return None

        # --- IA: Gerar Mensagem Inteligente (Step 196) ---
        mensagem_final = dados.mensagem
        if dados.nivel in ["WARNING", "DANGER"] or dados.tipo == "OPORTUNIDADE":
            mensagem_final = await self.gerar_mensagem_ia(dados)

        notif = await self.create({
            "tipo": dados.tipo,
            "titulo": dados.titulo,
            "mensagem": mensagem_final,
            "nivel": dados.nivel,
            "origem": dados.origem,
            "origem_id": dados.origem_id,
            "meta": dados.meta,
            "usuario_id": user.id if user else None,
        })
        await self.session.commit()
        await self.session.refresh(notif)
        
        # Envio proativo de email para notificações críticas (DANGER) ou Oportunidades
        if (notif.nivel == "DANGER" or dados.tipo == "OPORTUNIDADE") and email_resp and enviar_por_email:
            import asyncio
            from notificacoes.email_service import enviar_email
            
            assunto = f"AgroSaaS — Alerta Inteligente: {notif.titulo}"
            asyncio.create_task(enviar_email(email_resp, assunto, notif.mensagem))
        
        await manager.push(str(self.tenant_id), {
            "tipo": "nova_notificacao",
            "id": str(notif.id),
            "notificacao_tipo": notif.tipo,
            "titulo": notif.titulo,
            "mensagem": notif.mensagem,
            "nivel": notif.nivel,
            "created_at": notif.created_at.isoformat(),
        })
        return notif

    async def gerar_mensagem_ia(self, dados: NotificacaoCreate) -> str:
        """Gera uma mensagem curta e impactante usando IA para notificações externas (Step 196)."""
        import os
        import httpx
        from loguru import logger
        
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return dados.mensagem
            
        prompt = f"""Você é um copiloto agro-financeiro. Resuma o alerta abaixo em uma única frase curta (máximo 120 caracteres) para uma notificação PUSH/EMAIL.
Deve ser direta, profissional e conter um emoji relevante.

ALERTA:
Título: {dados.titulo}
Mensagem Original: {dados.mensagem}
Gravidade: {dados.nivel}

Exemplo de saída: 🚨 Margem caiu para 8%. Recomendamos revisar custos operacionais imediatamente.
"""

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": os.getenv("IA_MODEL", "claude-haiku-4-5-20251001"),
                        "max_tokens": 200,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                resp.raise_for_status()
                return resp.json()["content"][0]["text"].strip()
        except Exception as e:
            logger.error(f"Erro ao gerar mensagem IA para notificação: {e}")
            return dados.mensagem

    async def criar_sem_duplicar(self, dados: NotificacaoCreate) -> Notificacao | None:
        """Cria notificação apenas se não houver outra não-lida da mesma origem+tipo."""
        if dados.origem and dados.origem_id:
            stmt = select(Notificacao).where(
                Notificacao.tenant_id == self.tenant_id,
                Notificacao.tipo == dados.tipo,
                Notificacao.origem == dados.origem,
                Notificacao.origem_id == dados.origem_id,
                Notificacao.lida == False,  # noqa: E712
            ).limit(1)
            result = await self.session.execute(stmt)
            if result.scalar_one_or_none():
                return None
        return await self.criar_e_push(dados)

    async def sincronizar_safra(self, safra_id: UUID) -> list[Notificacao]:
        """Gera notificações a partir do plano de ação pendente da safra."""
        from financeiro.services.plano_acao_service import PlanoAcaoService

        svc = PlanoAcaoService(self.session, self.tenant_id)
        itens = await svc.listar(safra_id)
        pendentes = [i for i in itens if i.status == "PENDENTE"]

        NIVEL_MAP = {"ALTA": "DANGER", "MEDIA": "WARNING", "BAIXA": "INFO"}

        criadas: list[Notificacao] = []
        for item in pendentes:
            notif = await self.criar_sem_duplicar(NotificacaoCreate(
                tipo="PLANO_ACAO",
                titulo=item.titulo,
                mensagem=item.descricao,
                nivel=NIVEL_MAP.get(item.prioridade, "INFO"),
                origem="plano_acao",
                origem_id=str(item.id),
            ))
            if notif:
                criadas.append(notif)
                logger.info(f"Notificação criada para ação {item.id}")

        return criadas

    async def listar(self, lida: bool | None = None, limit: int = 50) -> list[Notificacao]:
        stmt = select(Notificacao).where(Notificacao.tenant_id == self.tenant_id)
        if lida is not None:
            stmt = stmt.where(Notificacao.lida == lida)
        stmt = stmt.order_by(Notificacao.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def marcar_lidas(self, ids: list[UUID] | None = None) -> int:
        agora = datetime.now(timezone.utc)
        stmt = update(Notificacao).where(Notificacao.tenant_id == self.tenant_id)
        if ids:
            stmt = stmt.where(Notificacao.id.in_(ids))
        stmt = stmt.values(lida=True, read_at=agora)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    async def total_nao_lidas(self) -> int:
        stmt = (
            select(func.count(Notificacao.id))
            .where(
                Notificacao.tenant_id == self.tenant_id,
                Notificacao.lida == False,  # noqa: E712
            )
        )
        return (await self.session.execute(stmt)).scalar() or 0
