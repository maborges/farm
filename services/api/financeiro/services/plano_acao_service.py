import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from financeiro.models.plano_acao import PlanoAcaoItem
from financeiro.services.lancamento_service import LancamentoService
from core.exceptions import EntityNotFoundError, BusinessRuleError


class PlanoAcaoService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def listar(self, safra_id: uuid.UUID) -> list[PlanoAcaoItem]:
        stmt = (
            select(PlanoAcaoItem)
            .where(
                PlanoAcaoItem.tenant_id == self.tenant_id,
                PlanoAcaoItem.safra_id == safra_id,
            )
            .order_by(PlanoAcaoItem.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def sincronizar(self, safra_id: uuid.UUID) -> list[PlanoAcaoItem]:
        """Persiste ações geradas em runtime; não duplica tipo já ativo/concluído."""
        lancamento_svc = LancamentoService(self.session, self.tenant_id)
        sugestoes = await lancamento_svc.gerar_plano_acao(safra_id)

        existentes_stmt = select(PlanoAcaoItem).where(
            PlanoAcaoItem.tenant_id == self.tenant_id,
            PlanoAcaoItem.safra_id == safra_id,
            PlanoAcaoItem.status.in_(["PENDENTE", "CONCLUIDA"]),
        )
        existentes_result = await self.session.execute(existentes_stmt)
        tipos_existentes = {r.tipo for r in existentes_result.scalars().all()}

        novos: list[PlanoAcaoItem] = []
        for s in sugestoes:
            if s.tipo.upper() in tipos_existentes:
                continue
            item = PlanoAcaoItem(
                id=uuid.uuid4(),
                tenant_id=self.tenant_id,
                safra_id=safra_id,
                tipo=s.tipo.upper(),
                titulo=s.titulo,
                descricao=s.descricao,
                prioridade=s.prioridade.upper(),
                status="PENDENTE",
                rota=s.rota,
                origem="AUTO",
            )
            self.session.add(item)
            novos.append(item)

        if novos:
            await self.session.flush()
            logger.info(f"Plano de ação: {len(novos)} novos itens para safra {safra_id}")

        return await self.listar(safra_id)

    async def atualizar_status(self, item_id: uuid.UUID, novo_status: str) -> PlanoAcaoItem:
        if novo_status not in ("CONCLUIDA", "IGNORADA"):
            raise BusinessRuleError("Status deve ser CONCLUIDA ou IGNORADA")

        stmt = select(PlanoAcaoItem).where(
            PlanoAcaoItem.id == item_id,
            PlanoAcaoItem.tenant_id == self.tenant_id,
        )
        result = await self.session.execute(stmt)
        item = result.scalar_one_or_none()
        if not item:
            raise EntityNotFoundError("Item do plano de ação não encontrado")

        agora = datetime.now(timezone.utc)
        item.status = novo_status
        if novo_status == "CONCLUIDA":
            item.concluido_at = agora
        else:
            item.ignorado_at = agora

        await self.session.flush()
        return item
