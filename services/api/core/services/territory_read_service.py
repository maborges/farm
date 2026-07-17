import uuid
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, text
from loguru import logger
from collections import defaultdict

from core.models.unidade_produtiva import UnidadeProdutiva
from core.cadastros.propriedades.propriedade_models import ExploracaoRural, Propriedade
from core.cadastros.propriedade_imovel.models import PropriedadeImovel, TipoVinculoPropriedadeImovel
from imoveis.models.imovel import ImovelRural
from core.schemas.territorio_read import TerritoryReadView

class TerritoryReadService:
    """Serviço oficial de leitura do domínio territorial (TERRITORY-CONVERGENCE-01E)."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def obter_visao_territorial_da_unidade(self, unidade_id: uuid.UUID) -> TerritoryReadView:
        res = await self.obter_visoes_territoriais_em_lote([unidade_id])
        return res.get(unidade_id)

    async def obter_visoes_territoriais_em_lote(self, unidade_ids: List[uuid.UUID]) -> Dict[uuid.UUID, TerritoryReadView]:
        if not unidade_ids:
            return {}

        # Etapa 1 — Unidade Produtiva (Neste ponto pressupomos que já foram validadas pelo caller)
        # Vamos carregar as UP fields em memória para o Etapa 7 (Fallback)
        stmt_up = select(UnidadeProdutiva).where(
            UnidadeProdutiva.id.in_(unidade_ids),
            UnidadeProdutiva.tenant_id == self.tenant_id
        )
        ups_result = await self.session.execute(stmt_up)
        ups = {up.id: up for up in ups_result.scalars().all()}

        # Etapa 2 — Exploração Rural
        stmt_expl = select(ExploracaoRural).where(
            ExploracaoRural.unidade_produtiva_id.in_(unidade_ids),
            ExploracaoRural.tenant_id == self.tenant_id
        )
        expl_result = await self.session.execute(stmt_expl)
        exploracoes = list(expl_result.scalars().all())

        propriedade_ids = {e.propriedade_id for e in exploracoes}

        # Etapa 3 — Propriedade
        propriedades_dict = {}
        if propriedade_ids:
            stmt_prop = select(Propriedade).where(
                Propriedade.id.in_(propriedade_ids),
                Propriedade.tenant_id == self.tenant_id
            )
            prop_result = await self.session.execute(stmt_prop)
            for p in prop_result.scalars().all():
                propriedades_dict[p.id] = p

        # Etapa 4 — PropriedadeImovel (Associações ativas)
        associacoes_dict = defaultdict(list)
        imovel_ids = set()
        if propriedade_ids:
            stmt_assoc = select(PropriedadeImovel).where(
                PropriedadeImovel.propriedade_id.in_(propriedade_ids),
                PropriedadeImovel.tenant_id == self.tenant_id,
                PropriedadeImovel.ativo.is_(True)
            ).order_by(
                PropriedadeImovel.vinculo_principal.desc(),
                PropriedadeImovel.data_inicio.desc(),
                PropriedadeImovel.created_at.desc()
            )
            assoc_result = await self.session.execute(stmt_assoc)
            for a in assoc_result.scalars().all():
                associacoes_dict[a.propriedade_id].append(a)
                imovel_ids.add(a.imovel_rural_id)

        # Etapa 5 — Imóvel Rural (Oficial)
        imoveis_dict = {}
        if imovel_ids:
            stmt_imovel = select(ImovelRural).where(
                ImovelRural.id.in_(imovel_ids),
                ImovelRural.tenant_id == self.tenant_id,
                ImovelRural.deleted_at.is_(None)
            )
            imovel_result = await self.session.execute(stmt_imovel)
            for im in imovel_result.scalars().all():
                imoveis_dict[im.id] = im

        # Montagem dos resultados
        resultados = {}
        for up_id in unidade_ids:
            up = ups.get(up_id)
            if not up:
                continue
                
            # Filtra pro escopo desta UP
            up_exploracoes = [e for e in exploracoes if e.unidade_produtiva_id == up_id]
            up_prop_ids = {e.propriedade_id for e in up_exploracoes}
            up_props = [propriedades_dict[pid] for pid in up_prop_ids if pid in propriedades_dict]
            
            up_assocs = []
            for pid in up_prop_ids:
                up_assocs.extend(associacoes_dict.get(pid, []))
                
            # Classificação Principal vs Secundário
            principal = None
            secundarios = []
            fonte = ""
            estado = ""
            avisos = []
            
            for a in up_assocs:
                im = imoveis_dict.get(a.imovel_rural_id)
                if not im:
                    continue
                im_dict = self._imovel_to_dict(im)
                if a.vinculo_principal and not principal:
                    principal = im_dict
                else:
                    secundarios.append(im_dict)

            if principal or secundarios:
                fonte = "CANONICAL_PROPERTY_ASSOCIATION"
                estado = "CANONICAL"
                if not principal and secundarios:
                    avisos.append("Imóveis vinculados existem, mas nenhum foi definido como principal.")
                    estado = "AMBIGUOUS"
                
                # Check conflicts?
                principais = [a for a in up_assocs if a.vinculo_principal]
                if len(principais) > 1:
                    estado = "CONFLICT"
                    avisos.append("Múltiplos vínculos principais encontrados para a mesma propriedade.")
                    
            else:
                estado = "NO_RURAL_PROPERTY"
                if not up_exploracoes:
                    estado = "NO_RURAL_EXPLORATION"

            logger.info(f"[TerritoryRead] source={fonte} state={estado} up_id={up_id} tenant_id={self.tenant_id}")

            view = TerritoryReadView(
                unidade_produtiva_id=up_id,
                exploracoes_rurais=[{"id": str(e.id), "propriedade_id": str(e.propriedade_id)} for e in up_exploracoes],
                propriedades=[{"id": str(p.id), "nome": p.nome} for p in up_props],
                imovel_principal=principal,
                imoveis_secundarios=secundarios,
                associacoes=[{"id": str(a.id), "propriedade_id": str(a.propriedade_id), "imovel_rural_id": str(a.imovel_rural_id), "vinculo_principal": a.vinculo_principal, "tipo_vinculo": a.tipo_vinculo} for a in up_assocs],
                fonte_da_leitura=fonte,
                estado_de_convergencia=estado,
                avisos=avisos
            )
            resultados[up_id] = view

        return resultados
        
    def _imovel_to_dict(self, im: ImovelRural) -> Dict:
        return {
            "id": str(im.id),
            "nome": im.nome,
            "nirf": im.nirf,
            "car_numero": im.car_numero,
            "numero_matricula": im.numero_matricula,
            "ccir_numero": im.ccir_numero,
            "sigef_codigo": im.sigef_codigo,
            "area_total_ha": str(im.area_total_ha) if im.area_total_ha else None
        }
