import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.base_service import BaseService
from core.exceptions import BusinessRuleError
from core.services.storage_service import save_and_track
from agricola.logistica_reversa_embalagens.models import DevolucaoEmbalagem, StatusDevolucaoEmbalagem

PRAZO_DEVOLUCAO_DIAS = 365  # Lei 9.974/2000 — 1 ano da compra


class DevolucaoEmbalagemService(BaseService[DevolucaoEmbalagem]):
    """OPERATIONS-GAP-01 §21.16/§21.20: logística reversa de embalagens de
    defensivos (Lei 9.974/2000). Pendências nascem automaticamente no
    recebimento de compra (`compras_service.py::receber_pedido`); nunca são
    criadas manualmente via router."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        super().__init__(DevolucaoEmbalagem, session, tenant_id, user_id=user_id)

    async def criar_pendencia_devolucao(
        self,
        *,
        item_recebimento_id: uuid.UUID,
        produto_id: uuid.UUID,
        quantidade_embalagens: int,
        data_compra: date,
        destino_pessoa_id: uuid.UUID | None = None,
    ) -> DevolucaoEmbalagem:
        devolucao = DevolucaoEmbalagem(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            item_recebimento_id=item_recebimento_id,
            produto_id=produto_id,
            quantidade_embalagens_compradas=quantidade_embalagens,
            quantidade_embalagens_devolvidas=0,
            data_compra=data_compra,
            prazo_limite=data_compra + timedelta(days=PRAZO_DEVOLUCAO_DIAS),
            destino_pessoa_id=destino_pessoa_id,
            status=StatusDevolucaoEmbalagem.PENDENTE.value,
        )
        self.session.add(devolucao)
        await self.session.flush()
        return devolucao

    async def registrar_devolucao(
        self,
        devolucao_id: uuid.UUID,
        quantidade_embalagens: int,
        *,
        destino_pessoa_id: uuid.UUID | None = None,
        observacoes: str | None = None,
        comprovante_content: bytes | None = None,
        comprovante_filename: str | None = None,
    ) -> DevolucaoEmbalagem:
        devolucao = await self.get_or_fail(devolucao_id)
        if devolucao.status == StatusDevolucaoEmbalagem.DEVOLVIDO.value:
            raise BusinessRuleError("Devolução já concluída para esta compra.")

        nova_quantidade = devolucao.quantidade_embalagens_devolvidas + quantidade_embalagens
        if nova_quantidade > devolucao.quantidade_embalagens_compradas:
            raise BusinessRuleError(
                f"Quantidade devolvida ({nova_quantidade}) excede o comprado "
                f"({devolucao.quantidade_embalagens_compradas})."
            )
        devolucao.quantidade_embalagens_devolvidas = nova_quantidade
        if destino_pessoa_id is not None:
            devolucao.destino_pessoa_id = destino_pessoa_id
        if observacoes is not None:
            devolucao.observacoes = observacoes

        if comprovante_content is not None:
            storage_path = await save_and_track(
                self.session, self.tenant_id, comprovante_content,
                area_rural_id=str(devolucao.produto_id), filename=comprovante_filename or "comprovante.pdf",
            )
            devolucao.comprovante_pdf_url = storage_path

        if devolucao.quantidade_embalagens_devolvidas >= devolucao.quantidade_embalagens_compradas:
            devolucao.status = StatusDevolucaoEmbalagem.DEVOLVIDO.value

        await self.session.flush()
        return devolucao

    async def listar_pendentes(self, vencendo_em_dias: int | None = None) -> list[DevolucaoEmbalagem]:
        stmt = select(DevolucaoEmbalagem).where(
            DevolucaoEmbalagem.tenant_id == self.tenant_id,
            DevolucaoEmbalagem.status == StatusDevolucaoEmbalagem.PENDENTE.value,
        )
        if vencendo_em_dias is not None:
            stmt = stmt.where(DevolucaoEmbalagem.prazo_limite <= date.today() + timedelta(days=vencendo_em_dias))
        stmt = stmt.order_by(DevolucaoEmbalagem.prazo_limite.asc())
        return list((await self.session.execute(stmt)).scalars().all())
