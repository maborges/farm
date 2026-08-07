from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.base_service import BaseService
from core.exceptions import BusinessRuleError
from agricola.caderno.models import VisitaTecnica, EPIEntrega
from agricola.caderno.schemas import VisitaTecnicaCreate, EPIEntregaCreate


class VisitaTecnicaService(BaseService[VisitaTecnica]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(VisitaTecnica, session, tenant_id)

    async def criar(self, dados: VisitaTecnicaCreate, usuario_id: UUID) -> VisitaTecnica:
        visita = VisitaTecnica(
            tenant_id=self.tenant_id,
            safra_id=dados.safra_id,
            talhao_id=dados.talhao_id,
            responsavel_tecnico_id=usuario_id,
            nome_rt=dados.nome_rt,
            crea=dados.crea,
            data_visita=dados.data_visita,
            observacoes=dados.observacoes,
            recomendacoes=dados.recomendacoes,
            constatacoes=dados.constatacoes,
        )
        self.session.add(visita)
        await self.session.flush()
        return visita

    async def assinar(self, visita_id: UUID, nome_rt: str, crea: str) -> VisitaTecnica:
        visita = await self.get_or_fail(visita_id)
        if visita.assinado:
            raise BusinessRuleError("Visita técnica já foi assinada.")
        visita.assinado = True
        visita.data_assinatura = datetime.utcnow()
        visita.nome_rt = nome_rt
        visita.crea = crea
        await self.session.flush()
        return visita

    async def listar_por_safra(self, safra_id: UUID, talhao_id: UUID | None = None) -> list[VisitaTecnica]:
        stmt = select(VisitaTecnica).where(
            VisitaTecnica.tenant_id == self.tenant_id,
            VisitaTecnica.safra_id == safra_id,
        ).order_by(VisitaTecnica.data_visita.desc())
        if talhao_id:
            stmt = stmt.where(VisitaTecnica.talhao_id == talhao_id)
        return list((await self.session.execute(stmt)).scalars().all())


class EPIEntregaService(BaseService[EPIEntrega]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(EPIEntrega, session, tenant_id)

    async def criar(self, dados: EPIEntregaCreate) -> EPIEntrega:
        epi = EPIEntrega(
            tenant_id=self.tenant_id,
            trabalhador_id=dados.trabalhador_id,
            nome_trabalhador=dados.nome_trabalhador,
            epi_tipo=dados.epi_tipo,
            quantidade=dados.quantidade,
            data_entrega=dados.data_entrega,
            validade=dados.validade,
            operacao_id=dados.operacao_id,
        )
        self.session.add(epi)
        await self.session.flush()
        return epi

    async def listar(self, operacao_id: UUID | None = None) -> list[EPIEntrega]:
        stmt = select(EPIEntrega).where(
            EPIEntrega.tenant_id == self.tenant_id,
        ).order_by(EPIEntrega.data_entrega.desc())
        if operacao_id:
            stmt = stmt.where(EPIEntrega.operacao_id == operacao_id)
        return list((await self.session.execute(stmt)).scalars().all())
