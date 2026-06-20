from __future__ import annotations

import uuid
from datetime import date
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from enterprise.models.sprints_27_33 import (
    ConfinamentoLote,
    RacaoTMR,
    Cocho,
    AnimalGenetica,
    SugestaoAcasalamento,
)
from pecuaria.producao.models import ProducaoLeite


class PecuariaAdvancedService:
    def __init__(self, session: AsyncSession, tenant_id):
        self.session = session
        self.tenant_id = str(tenant_id)
        self.tenant_uuid = uuid.UUID(str(tenant_id))

    # ── Genética ─────────────────────────────────────────────────────────────

    async def listar_genetica(self) -> list[AnimalGenetica]:
        stmt = select(AnimalGenetica).where(AnimalGenetica.tenant_id == self.tenant_id).order_by(AnimalGenetica.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar_genetica(self, dados: dict) -> AnimalGenetica:
        obj = AnimalGenetica(tenant_id=self.tenant_id, **dados)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def listar_sugestoes(self) -> list[SugestaoAcasalamento]:
        stmt = select(SugestaoAcasalamento).where(SugestaoAcasalamento.tenant_id == self.tenant_id).order_by(SugestaoAcasalamento.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar_sugestao(self, dados: dict) -> SugestaoAcasalamento:
        obj = SugestaoAcasalamento(tenant_id=self.tenant_id, **dados)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def resumo_genetica(self) -> dict:
        registros = await self.listar_genetica()
        sugestoes = await self.listar_sugestoes()
        return {
            "total_registros": len(registros),
            "total_matrizes": sum(1 for item in registros if item.matriz),
            "total_reprodutores": sum(1 for item in registros if item.reprodutor),
            "total_sugestoes": len(sugestoes),
        }

    # ── Confinamento ────────────────────────────────────────────────────────

    async def listar_confinamentos(self) -> list[ConfinamentoLote]:
        stmt = select(ConfinamentoLote).where(ConfinamentoLote.tenant_id == self.tenant_id).order_by(ConfinamentoLote.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar_confinamento(self, dados: dict) -> ConfinamentoLote:
        obj = ConfinamentoLote(tenant_id=self.tenant_id, **dados)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def listar_racoes(self) -> list[RacaoTMR]:
        stmt = select(RacaoTMR).where(RacaoTMR.tenant_id == self.tenant_id).order_by(RacaoTMR.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar_racao(self, dados: dict) -> RacaoTMR:
        obj = RacaoTMR(tenant_id=self.tenant_id, **dados)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def listar_cochos(self) -> list[Cocho]:
        stmt = select(Cocho).where(Cocho.tenant_id == self.tenant_id).order_by(Cocho.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar_cocho(self, dados: dict) -> Cocho:
        obj = Cocho(tenant_id=self.tenant_id, **dados)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def resumo_confinamento(self) -> dict:
        lotes = await self.listar_confinamentos()
        racoes = await self.listar_racoes()
        cochos = await self.listar_cochos()
        total_animais = sum(int(l.total_animais or 0) for l in lotes)
        gmd_medio = sum(float(l.ganho_medio_diario or 0) for l in lotes) / len(lotes) if lotes else 0.0
        conversao_media = sum(float(l.conversao_alimentar or 0) for l in lotes) / len(lotes) if lotes else 0.0
        return {
            "total_lotes": len(lotes),
            "total_animais": total_animais,
            "total_racoes": len(racoes),
            "total_cochos": len(cochos),
            "gmd_medio": gmd_medio,
            "conversao_media": conversao_media,
        }

    # ── Leite ───────────────────────────────────────────────────────────────

    async def listar_producao(self) -> list[ProducaoLeite]:
        stmt = select(ProducaoLeite).where(ProducaoLeite.tenant_id == self.tenant_uuid).order_by(ProducaoLeite.data.desc(), ProducaoLeite.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar_producao(self, dados: dict) -> ProducaoLeite:
        obj = ProducaoLeite(tenant_id=self.tenant_uuid, **dados)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def resumo_leite(self) -> dict:
        registros = await self.listar_producao()
        volume_total = sum(float(r.volume_litros or 0) for r in registros)
        media_volume = volume_total / len(registros) if registros else 0.0
        media_gordura = sum(float(r.gordura_pct or 0) for r in registros) / len(registros) if registros else 0.0
        media_proteina = sum(float(r.proteina_pct or 0) for r in registros) / len(registros) if registros else 0.0
        return {
            "total_registros": len(registros),
            "volume_total_litros": volume_total,
            "media_volume_litros": media_volume,
            "media_gordura_pct": media_gordura,
            "media_proteina_pct": media_proteina,
        }
