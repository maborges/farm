from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.cadastros.propriedades.models import AreaRural
from core.cadastros.propriedades.propriedade_models import ExploracaoRural, Propriedade
from core.exceptions import EntityNotFoundError
from imoveis.models.imovel import (
    ImovelRural,
    MatriculaImovelRural,
)

from .models import PropriedadeImovel
from .visao_schemas import (
    AreaOperacionalResumo,
    CartorioResumo,
    DocumentoFundiarioResumo,
    ExploracaoRuralResumo,
    ImovelFundiarioResumo,
    MatriculaFundiariaResumo,
    PropriedadeVisaoResumo,
    VisaoFundiariaRead,
    VisaoTerritorialRead,
    VinculoTerritorialResumo,
)


class VisaoTerritorialService:
    """Consulta agregada somente leitura para a visão territorial/fundiária."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def obter_visao_territorial(self, propriedade_id: uuid.UUID) -> VisaoTerritorialRead:
        propriedade = await self._obter_propriedade(propriedade_id)
        exploracoes = list(propriedade.exploracoes)
        unidade_ids = {expl.unidade_produtiva_id for expl in exploracoes}
        areas = await self._listar_areas_operacionais(unidade_ids)
        vinculos = list(propriedade.propriedade_imoveis)
        imoveis = self._deduplicar_imoveis(vinculos)
        return VisaoTerritorialRead(
            propriedade=PropriedadeVisaoResumo.model_validate(propriedade),
            areas_operacionais=[AreaOperacionalResumo.model_validate(area) for area in areas],
            exploracoes_rurais=[ExploracaoRuralResumo.model_validate(expl) for expl in exploracoes],
            imoveis_rurais=[self._imovel_resumo(imovel) for imovel in imoveis],
            vinculos=[self._vinculo_resumo(v) for v in vinculos],
        )

    async def obter_visao_fundiaria(self, imovel_id: uuid.UUID) -> VisaoFundiariaRead:
        imovel = await self._obter_imovel(imovel_id)
        matriculas = await self._listar_matriculas(imovel_id)
        vinculos = list(imovel.propriedade_imoveis)
        propriedades = self._deduplicar_propriedades(vinculos)
        imovel_resumo = self._imovel_resumo(imovel, matriculas)
        return VisaoFundiariaRead(
            imovel_rural=imovel_resumo,
            propriedades_vinculadas=[PropriedadeVisaoResumo.model_validate(p) for p in propriedades],
            vinculos=[self._vinculo_resumo(v) for v in vinculos],
        )

    async def _obter_propriedade(self, propriedade_id: uuid.UUID) -> Propriedade:
        from sqlalchemy import or_
        from core.cadastros.propriedades.propriedade_models import ExploracaoRural

        options = (
            selectinload(Propriedade.exploracoes),
            selectinload(Propriedade.propriedade_imoveis)
            .selectinload(PropriedadeImovel.imovel_rural)
            .selectinload(ImovelRural.documentos),
            selectinload(Propriedade.propriedade_imoveis)
            .selectinload(PropriedadeImovel.imovel_rural)
            .selectinload(ImovelRural.cartorio),
            selectinload(Propriedade.propriedade_imoveis)
            .selectinload(PropriedadeImovel.imovel_rural)
            .selectinload(ImovelRural.propriedade_imoveis),
        )

        stmt = (
            select(Propriedade)
            .outerjoin(ExploracaoRural, Propriedade.id == ExploracaoRural.propriedade_id)
            .where(
                or_(Propriedade.id == propriedade_id, ExploracaoRural.unidade_produtiva_id == propriedade_id),
                Propriedade.tenant_id == self.tenant_id,
            )
            .options(*options)
        )
        result = await self.session.execute(stmt)
        obj = result.scalars().first()
        if obj:
            return obj

        stmt = (
            select(Propriedade)
            .join(PropriedadeImovel, PropriedadeImovel.propriedade_id == Propriedade.id)
            .join(ImovelRural, ImovelRural.id == PropriedadeImovel.imovel_rural_id)
            .where(
                ImovelRural.unidade_produtiva_id == propriedade_id,
                Propriedade.tenant_id == self.tenant_id,
                PropriedadeImovel.tenant_id == self.tenant_id,
                ImovelRural.tenant_id == self.tenant_id,
                ImovelRural.deleted_at.is_(None),
            )
            .order_by(
                PropriedadeImovel.vinculo_principal.desc(),
                PropriedadeImovel.ativo.desc(),
                PropriedadeImovel.data_inicio.desc(),
                PropriedadeImovel.created_at.desc(),
            )
            .options(*options)
        )
        result = await self.session.execute(stmt)
        obj = result.scalars().first()
        if not obj:
            raise EntityNotFoundError("Propriedade não encontrada neste tenant.")
        return obj

    async def _obter_imovel(self, imovel_id: uuid.UUID) -> ImovelRural:
        stmt = (
            select(ImovelRural)
            .where(ImovelRural.id == imovel_id, ImovelRural.tenant_id == self.tenant_id, ImovelRural.deleted_at.is_(None))
            .options(
                selectinload(ImovelRural.documentos),
                selectinload(ImovelRural.cartorio),
                selectinload(ImovelRural.propriedade_imoveis).selectinload(PropriedadeImovel.propriedade),
                selectinload(ImovelRural.propriedade_imoveis).selectinload(PropriedadeImovel.imovel_rural),
            )
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Imóvel rural não encontrado neste tenant.")
        return obj

    async def _listar_areas_operacionais(self, unidade_ids: set[uuid.UUID]) -> list[AreaRural]:
        if not unidade_ids:
            return []
        stmt = (
            select(AreaRural)
            .where(AreaRural.tenant_id == self.tenant_id, AreaRural.unidade_produtiva_id.in_(list(unidade_ids)))
            .order_by(AreaRural.unidade_produtiva_id, AreaRural.tipo, AreaRural.nome)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _listar_matriculas(self, imovel_id: uuid.UUID) -> list[MatriculaImovelRural]:
        stmt = (
            select(MatriculaImovelRural)
            .where(MatriculaImovelRural.imovel_id == imovel_id, MatriculaImovelRural.tenant_id == self.tenant_id)
            .options(selectinload(MatriculaImovelRural.cartorio))
            .order_by(MatriculaImovelRural.numero_matricula)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    def _deduplicar_imoveis(self, vinculos: Iterable[PropriedadeImovel]) -> list[ImovelRural]:
        vistos: dict[uuid.UUID, ImovelRural] = {}
        for vinculo in vinculos:
            if vinculo.imovel_rural and vinculo.imovel_rural.id not in vistos:
                vistos[vinculo.imovel_rural.id] = vinculo.imovel_rural
        return list(vistos.values())

    def _deduplicar_propriedades(self, vinculos: Iterable[PropriedadeImovel]) -> list[Propriedade]:
        vistos: dict[uuid.UUID, Propriedade] = {}
        for vinculo in vinculos:
            if vinculo.propriedade and vinculo.propriedade.id not in vistos:
                vistos[vinculo.propriedade.id] = vinculo.propriedade
        return list(vistos.values())

    def _imovel_resumo(
        self,
        imovel: ImovelRural,
        matriculas: list[MatriculaImovelRural] | None = None,
    ) -> ImovelFundiarioResumo:
        matriculas = matriculas or []
        cartorio = CartorioResumo.model_validate(imovel.cartorio) if imovel.cartorio else None
        documentos = [DocumentoFundiarioResumo.model_validate(doc) for doc in list(imovel.documentos)]
        matriculas_resumo = [self._matricula_resumo(item) for item in matriculas]
        return ImovelFundiarioResumo(
            id=imovel.id,
            tenant_id=imovel.tenant_id,
            unidade_produtiva_id=imovel.unidade_produtiva_id,
            nome=imovel.nome,
            municipio=imovel.municipio,
            uf=imovel.uf,
            area_total_ha=imovel.area_total_ha,
            area_app_ha=imovel.area_app_ha,
            area_rl_ha=imovel.area_rl_ha,
            nirf=imovel.nirf,
            car_numero=imovel.car_numero,
            ccir_numero=imovel.ccir_numero,
            numero_matricula=imovel.numero_matricula,
            cartorio=cartorio,
            documentos_resumo=documentos,
            matriculas_resumo=matriculas_resumo,
        )

    def _matricula_resumo(self, matricula: MatriculaImovelRural) -> MatriculaFundiariaResumo:
        return MatriculaFundiariaResumo(
            id=matricula.id,
            numero_matricula=matricula.numero_matricula,
            cartorio_nome=matricula.cartorio_nome or (matricula.cartorio.nome if matricula.cartorio else None),
            area_matricula_ha=matricula.area_matricula_ha,
            data_transmissao=matricula.data_transmissao,
            tipo_transmissao=matricula.tipo_transmissao,
            ativo=getattr(matricula, "ativo", True),
        )

    def _vinculo_resumo(self, vinculo: PropriedadeImovel) -> VinculoTerritorialResumo:
        return VinculoTerritorialResumo.model_validate(vinculo)
