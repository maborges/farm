import uuid
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, func, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from fastapi import WebSocket
from loguru import logger

from core.base_service import BaseService
from notificacoes.models import Notificacao, NotificacaoLeitura, NotificacaoPreferencia
from notificacoes.schemas import NotificacaoCreate, NotificacaoPreferenciaUpdate


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
        from datetime import datetime, timezone, timedelta

        COOLDOWN_HORAS = 24

        # --- Anti-spam Cooldown (tenant-wide, a notificação é compartilhada) ---
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

        recente = (await self.session.execute(stmt_cooldown.limit(1))).scalar_one_or_none()
        if recente:
            logger.info(f"Notificação suprimida por cooldown: {dados.tipo} (origem={dados.origem})")
            return None
        # --------------------------

        # A notificação em si é sempre criada tenant-wide — preferências não
        # suprimem mais a criação para todo o tenant (antes dependiam só do
        # email_responsavel). Elas passam a decidir apenas o fan-out de email
        # por usuário, em _enviar_emails_por_preferencia.
        notif = await self.create({
            "tipo": dados.tipo,
            "titulo": dados.titulo,
            "mensagem": dados.mensagem,
            "nivel": dados.nivel,
            "origem": dados.origem,
            "origem_id": dados.origem_id,
            "meta": dados.meta,
            "usuario_id": None,
        })
        # Não commitamos aqui se a sessão é gerida externamente, mas o código original dava commit.
        # Mantendo o commit original para não quebrar fluxos que dependem disso.
        await self.session.commit()
        await self.session.refresh(notif)

        import asyncio
        from core.database import async_session_maker

        async def _atualizar_e_notificar():
            msg_final = dados.mensagem
            if dados.nivel in ["WARNING", "DANGER"] or dados.tipo == "OPORTUNIDADE":
                try:
                    # Usar uma nova sessão para não interferir na sessão atual
                    async with async_session_maker() as bg_session:
                        bg_svc = NotificacaoService(bg_session, self.tenant_id)
                        msg_final = await bg_svc.gerar_mensagem_ia(dados)
                        if msg_final != dados.mensagem:
                            notif_db = await bg_session.get(Notificacao, notif.id)
                            if notif_db:
                                notif_db.mensagem = msg_final
                                await bg_session.commit()
                except Exception as e:
                    logger.error(f"Erro no background task de IA: {e}")

            # Envio de email — um por usuário elegível (preferência própria), não mais um só responsável
            if notif.nivel == "DANGER" or dados.tipo == "OPORTUNIDADE":
                try:
                    async with async_session_maker() as bg_session:
                        bg_svc = NotificacaoService(bg_session, self.tenant_id)
                        await bg_svc._enviar_emails_por_preferencia(notif, dados.tipo, msg_final)
                except Exception as e:
                    logger.error(f"Erro no fan-out de email de notificação: {e}")

            # Websocket Push
            try:
                await manager.push(str(self.tenant_id), {
                    "tipo": "nova_notificacao",
                    "id": str(notif.id),
                    "notificacao_tipo": notif.tipo,
                    "titulo": notif.titulo,
                    "mensagem": msg_final,
                    "nivel": notif.nivel,
                    "created_at": notif.created_at.isoformat(),
                })
            except Exception as e:
                logger.error(f"Erro ao enviar WS push: {e}")

        # Dispara IA e notificações de saída (email/ws) em background
        asyncio.create_task(_atualizar_e_notificar())

        return notif

    async def _enviar_emails_por_preferencia(
        self, notif: Notificacao, tipo: str, msg_final: str
    ) -> None:
        """Envia email para cada usuário ativo do tenant elegível por sua própria preferência.

        Substitui o antigo comportamento de enviar só para Tenant.email_responsavel:
        cada usuário tem email_ativo/nivel_sensibilidade próprios; sem preferência
        cadastrada, o padrão é elegível (email_ativo=True, sensibilidade=ALTO).
        """
        from core.models.auth import Usuario, TenantUsuario
        from notificacoes.email_service import enviar_email

        stmt = (
            select(Usuario, NotificacaoPreferencia)
            .join(TenantUsuario, TenantUsuario.usuario_id == Usuario.id)
            .outerjoin(
                NotificacaoPreferencia,
                and_(
                    NotificacaoPreferencia.usuario_id == Usuario.id,
                    NotificacaoPreferencia.tenant_id == self.tenant_id,
                    NotificacaoPreferencia.tipo == tipo,
                ),
            )
            .where(
                TenantUsuario.tenant_id == self.tenant_id,
                TenantUsuario.status == "ATIVO",
            )
        )
        result = await self.session.execute(stmt)

        assunto = f"AgroSaaS — Alerta Inteligente: {notif.titulo}"
        for user, pref in result.all():
            email_ativo = pref.email_ativo if pref else True
            sensibilidade = pref.nivel_sensibilidade if pref else "ALTO"
            if not email_ativo:
                continue
            if sensibilidade == "MEDIO" and notif.nivel not in ["WARNING", "DANGER"]:
                continue
            if sensibilidade == "BAIXO" and notif.nivel != "DANGER":
                continue
            try:
                await enviar_email(user.email, assunto, msg_final)
            except Exception as e:
                logger.error(f"Erro ao enviar email de notificação para {user.email}: {e}")

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
        """Cria notificação apenas se não houver outra da mesma origem+tipo ainda não lida por ninguém.

        "Não lida" aqui é tenant-wide (nenhum usuário leu ainda) — equivalente
        ao comportamento anterior baseado em `Notificacao.lida`, agora expresso
        via ausência de qualquer linha em `notificacoes_leituras` para essa
        notificação. Assim que alguém lê, uma nova ocorrência pode ser criada.
        """
        if dados.origem and dados.origem_id:
            ja_lida = (
                select(NotificacaoLeitura.id)
                .where(NotificacaoLeitura.notificacao_id == Notificacao.id, NotificacaoLeitura.lida == True)  # noqa: E712
                .exists()
            )
            stmt = select(Notificacao).where(
                Notificacao.tenant_id == self.tenant_id,
                Notificacao.tipo == dados.tipo,
                Notificacao.origem == dados.origem,
                Notificacao.origem_id == dados.origem_id,
                ~ja_lida,
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
                meta={
                    "acoes": [
                        {"label": "Concluir", "acao": "concluir", "endpoint": f"/plano-acoes/{item.id}/status", "method": "PATCH", "body": {"status": "CONCLUIDA"}},
                        {"label": "Ignorar", "acao": "ignorar", "endpoint": f"/plano-acoes/{item.id}/status", "method": "PATCH", "body": {"status": "IGNORADA"}},
                    ]
                },
            ))
            if notif:
                criadas.append(notif)
                logger.info(f"Notificação criada para ação {item.id}")

        return criadas

    async def listar(
        self, usuario_id: UUID, lida: bool | None = None, limit: int = 50
    ) -> list[Notificacao]:
        """Lista notificações do tenant com o estado de leitura do usuário informado.

        `Notificacao.lida` (coluna) é ignorada aqui — o estado real vem de
        `notificacoes_leituras`, por usuário (ausência de linha = não lida).
        """
        lida_usuario = func.coalesce(NotificacaoLeitura.lida, False)
        sistema_ativo = func.coalesce(NotificacaoPreferencia.sistema_ativo, True)
        acao_registrada = NotificacaoLeitura.acao
        stmt = (
            select(Notificacao, lida_usuario, acao_registrada)
            .outerjoin(
                NotificacaoLeitura,
                and_(
                    NotificacaoLeitura.notificacao_id == Notificacao.id,
                    NotificacaoLeitura.usuario_id == usuario_id,
                ),
            )
            .outerjoin(
                NotificacaoPreferencia,
                and_(
                    NotificacaoPreferencia.usuario_id == usuario_id,
                    NotificacaoPreferencia.tenant_id == self.tenant_id,
                    NotificacaoPreferencia.tipo == Notificacao.tipo,
                ),
            )
            .where(Notificacao.tenant_id == self.tenant_id, sistema_ativo == True)  # noqa: E712
        )
        if lida is not None:
            stmt = stmt.where(lida_usuario == lida)
        stmt = stmt.order_by(Notificacao.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)

        notificacoes: list[Notificacao] = []
        for notif, lida_valor, acao_valor in result.all():
            self.session.expunge(notif)
            notif.lida = bool(lida_valor)
            notif.meta = await self._filtrar_acoes_por_permissao(notif, usuario_id, ja_executada=acao_valor)
            notificacoes.append(notif)
        return notificacoes

    async def _filtrar_acoes_por_permissao(
        self, notif: Notificacao, usuario_id: UUID, ja_executada: str | None
    ) -> dict:
        """Remove de meta.acoes as ações que o usuário atual não pode executar.

        Notificação é tenant-wide na criação, mas os botões de ação exibidos
        variam por usuário — checa a autorização real de cada domínio (RH,
        recomendações) em vez de confiar em algo gravado estaticamente na
        criação da notificação.
        """
        meta = dict(notif.meta or {})
        acoes = meta.get("acoes")
        if not acoes:
            return meta
        if ja_executada:
            meta["acao_executada"] = ja_executada
            meta["acoes"] = []
            return meta

        if notif.tipo == "RECOMENDACAO" and notif.origem_id:
            from recommendations.authorization import RecommendationAuthorizationService

            auth = RecommendationAuthorizationService(self.session, self.tenant_id, usuario_id)
            permitidas = []
            for item in acoes:
                if await auth.pode_executar(UUID(notif.origem_id), item["acao"]):
                    permitidas.append(item)
            meta["acoes"] = permitidas
        elif notif.tipo == "DIARIA_PENDENTE":
            from core.dependencies import resolver_permissao_usuario

            if await resolver_permissao_usuario(self.session, self.tenant_id, usuario_id, "rh:*"):
                meta["acoes"] = acoes
            else:
                meta["acoes"] = []
        elif notif.tipo == "PLANO_ACAO":
            # PATCH /plano-acoes/{id}/status não tem checagem de permissão hoje
            # (nenhuma Depends de RBAC no endpoint) — qualquer usuário do tenant
            # com sessão válida já pode chamá-lo, então não há nada a filtrar aqui.
            meta["acoes"] = acoes
        elif notif.tipo == "AGRICULTURA_OPERACAO_ATRASADA":
            from core.dependencies import resolver_role_tenant_usuario

            role = await resolver_role_tenant_usuario(self.session, self.tenant_id, usuario_id)
            if role in ("agronomo", "admin", "operador"):
                meta["acoes"] = acoes
            else:
                meta["acoes"] = []
        else:
            meta["acoes"] = []
        return meta

    async def marcar_lidas(self, usuario_id: UUID, ids: list[UUID] | None = None) -> int:
        """Marca como lidas para o usuário informado (não afeta outros usuários do tenant)."""
        agora = datetime.now(timezone.utc)
        stmt_ids = select(Notificacao.id).where(Notificacao.tenant_id == self.tenant_id)
        if ids:
            stmt_ids = stmt_ids.where(Notificacao.id.in_(ids))
        notif_ids = [row[0] for row in (await self.session.execute(stmt_ids)).all()]
        if not notif_ids:
            return 0

        values = [
            {
                "id": uuid.uuid4(),
                "tenant_id": self.tenant_id,
                "notificacao_id": notif_id,
                "usuario_id": usuario_id,
                "lida": True,
                "read_at": agora,
            }
            for notif_id in notif_ids
        ]
        insert_stmt = pg_insert(NotificacaoLeitura).values(values)
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=["notificacao_id", "usuario_id"],
            set_={"lida": True, "read_at": agora},
        )
        await self.session.execute(upsert_stmt)
        await self.session.commit()
        return len(notif_ids)

    async def registrar_acao(self, usuario_id: UUID, notificacao_id: UUID, acao: str) -> None:
        """Registra que o usuário disparou uma ação a partir da notificação (marca lida junto).

        Só audita — quem executa a ação de negócio de verdade é o endpoint do
        domínio (ex: POST /rh/diarias/pagar-lote, POST /recommendations/{id}/accept),
        chamado separadamente pelo frontend.
        """
        agora = datetime.now(timezone.utc)
        values = {
            "id": uuid.uuid4(),
            "tenant_id": self.tenant_id,
            "notificacao_id": notificacao_id,
            "usuario_id": usuario_id,
            "lida": True,
            "read_at": agora,
            "acao": acao,
            "acao_em": agora,
        }
        insert_stmt = pg_insert(NotificacaoLeitura).values(**values)
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=["notificacao_id", "usuario_id"],
            set_={"lida": True, "read_at": agora, "acao": acao, "acao_em": agora},
        )
        await self.session.execute(upsert_stmt)
        await self.session.commit()

    async def total_nao_lidas(self, usuario_id: UUID) -> int:
        lida_usuario = func.coalesce(NotificacaoLeitura.lida, False)
        sistema_ativo = func.coalesce(NotificacaoPreferencia.sistema_ativo, True)
        stmt = (
            select(func.count(Notificacao.id))
            .outerjoin(
                NotificacaoLeitura,
                and_(
                    NotificacaoLeitura.notificacao_id == Notificacao.id,
                    NotificacaoLeitura.usuario_id == usuario_id,
                ),
            )
            .outerjoin(
                NotificacaoPreferencia,
                and_(
                    NotificacaoPreferencia.usuario_id == usuario_id,
                    NotificacaoPreferencia.tenant_id == self.tenant_id,
                    NotificacaoPreferencia.tipo == Notificacao.tipo,
                ),
            )
            .where(
                Notificacao.tenant_id == self.tenant_id,
                lida_usuario == False,  # noqa: E712
                sistema_ativo == True,  # noqa: E712
            )
        )
        return (await self.session.execute(stmt)).scalar() or 0

    async def listar_preferencias(self, usuario_id: UUID) -> list[NotificacaoPreferencia]:
        stmt = select(NotificacaoPreferencia).where(
            NotificacaoPreferencia.tenant_id == self.tenant_id,
            NotificacaoPreferencia.usuario_id == usuario_id,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def upsert_preferencia(
        self, usuario_id: UUID, tipo: str, dados: NotificacaoPreferenciaUpdate
    ) -> NotificacaoPreferencia:
        import uuid

        stmt = select(NotificacaoPreferencia).where(
            NotificacaoPreferencia.tenant_id == self.tenant_id,
            NotificacaoPreferencia.usuario_id == usuario_id,
            NotificacaoPreferencia.tipo == tipo,
        )
        pref = (await self.session.execute(stmt)).scalar_one_or_none()

        if pref:
            pref.email_ativo = dados.email_ativo
            pref.sistema_ativo = dados.sistema_ativo
            pref.whatsapp_ativo = dados.whatsapp_ativo
            pref.horario_envio = dados.horario_envio
            pref.nivel_sensibilidade = dados.nivel_sensibilidade
            pref.updated_at = datetime.now(timezone.utc)
        else:
            pref = NotificacaoPreferencia(
                id=uuid.uuid4(),
                tenant_id=self.tenant_id,
                usuario_id=usuario_id,
                tipo=tipo,
                email_ativo=dados.email_ativo,
                sistema_ativo=dados.sistema_ativo,
                whatsapp_ativo=dados.whatsapp_ativo,
                horario_envio=dados.horario_envio,
                nivel_sensibilidade=dados.nivel_sensibilidade,
            )
            self.session.add(pref)

        await self.session.commit()
        await self.session.refresh(pref)
        return pref
