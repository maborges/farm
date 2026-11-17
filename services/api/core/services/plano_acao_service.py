from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import EntityNotFoundError
from core.models.plano_acao import PlanoAcaoGerencial
from core.schemas.plano_acao_schemas import PlanoAcaoCreate, PlanoAcaoUpdate


class PlanoAcaoService:
    """Serviço de gestão de planos de ação gerenciais com isolamento por tenant."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def listar(
        self,
        status: str | None = None,
        safra_id: UUID | None = None,
    ) -> list[PlanoAcaoGerencial]:
        """Lista planos de ação do tenant aplicando derivação automática de atraso.

        Args:
            status: Filtro opcional de status.
            safra_id: Filtro opcional de safra.

        Returns:
            list[PlanoAcaoGerencial]: Planos ordenados por prazo e criação.
        """
        stmt = select(PlanoAcaoGerencial).where(PlanoAcaoGerencial.tenant_id == self.tenant_id)
        if safra_id is not None:
            stmt = stmt.where(PlanoAcaoGerencial.safra_id == safra_id)
        stmt = stmt.order_by(PlanoAcaoGerencial.prazo.asc().nulls_last(), PlanoAcaoGerencial.created_at.desc())

        itens = list((await self.session.execute(stmt)).scalars().all())
        hoje = date.today()
        for item in itens:
            if item.prazo and item.prazo < hoje and item.status in ("ABERTO", "EM_ANDAMENTO"):
                item.status = "ATRASADO"

        if status:
            return [i for i in itens if i.status == status]
        return itens

    async def criar(self, dados: PlanoAcaoCreate) -> PlanoAcaoGerencial:
        """Cria um novo plano de ação gerencial para o tenant.

        Args:
            dados: Payload validado de criação.

        Returns:
            PlanoAcaoGerencial: Registro persistido.
        """
        status_inicial = "ATRASADO" if dados.prazo and dados.prazo < date.today() else "ABERTO"
        plano = PlanoAcaoGerencial(
            tenant_id=self.tenant_id,
            status=status_inicial,
            **dados.model_dump(),
        )
        self.session.add(plano)
        await self.session.flush()
        await self.session.refresh(plano)
        return plano

    async def atualizar(self, plano_id: UUID, dados: PlanoAcaoUpdate) -> PlanoAcaoGerencial:
        """Atualiza campos ou status de um plano de ação do tenant.

        Args:
            plano_id: UUID do plano de ação.
            dados: Campos a atualizar.

        Returns:
            PlanoAcaoGerencial: Registro atualizado.

        Raises:
            EntityNotFoundError: Quando o plano não pertence ao tenant ou não existe.
        """
        plano = await self._obter_por_id(plano_id)
        payload = dados.model_dump(exclude_unset=True)
        for campo, valor in payload.items():
            setattr(plano, campo, valor)

        if payload.get("status") == "CONCLUIDO" and plano.concluido_em is None:
            plano.concluido_em = datetime.now(timezone.utc)
        elif payload.get("status") and payload.get("status") != "CONCLUIDO":
            plano.concluido_em = None

        await self.session.flush()
        await self.session.refresh(plano)
        return plano

    async def excluir(self, plano_id: UUID) -> None:
        """Remove um plano de ação do tenant.

        Args:
            plano_id: UUID do plano de ação.

        Raises:
            EntityNotFoundError: Quando o plano não pertence ao tenant ou não existe.
        """
        plano = await self._obter_por_id(plano_id)
        await self.session.delete(plano)
        await self.session.flush()

    async def _obter_por_id(self, plano_id: UUID) -> PlanoAcaoGerencial:
        stmt = select(PlanoAcaoGerencial).where(
            PlanoAcaoGerencial.id == plano_id,
            PlanoAcaoGerencial.tenant_id == self.tenant_id,
        )
        plano = await self.session.scalar(stmt)
        if not plano:
            raise EntityNotFoundError("Plano de ação não encontrado.")
        return plano
