# ruff: noqa
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
from pecuaria.animal.models import Animal, EventoAnimal
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
        repro = await self._resumo_reproducao()
        return {
            "total_registros": len(registros),
            "total_matrizes": sum(1 for item in registros if item.matriz),
            "total_reprodutores": sum(1 for item in registros if item.reprodutor),
            "total_sugestoes": len(sugestoes),
            **repro,
        }

    async def _resumo_reproducao(self) -> dict:
        coberturas = await self._contar_eventos_reproducao(("COBERTURA", "INSEMINACAO"))
        diagnosticos = await self._contar_eventos_reproducao(("DIAGNOSTICO_PRENHEZ",))
        partos = await self._contar_eventos_reproducao(("PARTO",))
        nascimentos = await self._contar_eventos_reproducao(("NASCIMENTO",))
        desmamas = await self._contar_eventos_reproducao(("DESMAME",))
        peso_nascimento_medio = await self._media_peso_evento("NASCIMENTO")
        peso_desmama_medio = await self._media_peso_evento("DESMAME")
        idade_media_desmama = await self._media_idade_desmama()
        intervalo_medio_partos = await self._intervalo_medio_partos()
        prenhe = await self._contar_diagnosticos_prenhes()
        perdas = await self._contar_perdas_reprodutivas()
        taxa_prenhez = (prenhe / diagnosticos * 100) if diagnosticos else 0.0
        taxa_natalidade = (nascimentos / coberturas * 100) if coberturas else 0.0
        taxa_desmama = (desmamas / nascimentos * 100) if nascimentos else 0.0
        matrizes = await self._contar_matrizes()
        crias_por_matriz = (nascimentos / matrizes) if matrizes else 0.0
        return {
            "total_coberturas": coberturas,
            "total_diagnosticos_prenhez": diagnosticos,
            "total_partos": partos,
            "total_nascimentos": nascimentos,
            "total_desmamas": desmamas,
            "taxa_prenhez_pct": round(taxa_prenhez, 2),
            "taxa_natalidade_pct": round(taxa_natalidade, 2),
            "taxa_desmama_pct": round(taxa_desmama, 2),
            "intervalo_medio_partos_dias": round(intervalo_medio_partos, 2),
            "peso_nascimento_medio_kg": round(peso_nascimento_medio, 2),
            "peso_desmama_medio_kg": round(peso_desmama_medio, 2),
            "idade_media_desmama_dias": round(idade_media_desmama, 2),
            "crias_por_matriz": round(crias_por_matriz, 2),
            "perdas_reprodutivas": perdas,
        }

    async def _contar_eventos_reproducao(self, tipos: tuple[str, ...]) -> int:
        stmt = select(func.count(EventoAnimal.id)).where(
            EventoAnimal.tenant_id == self.tenant_id,
            EventoAnimal.tipo.in_(tipos),
        )
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def _media_peso_evento(self, tipo: str) -> float:
        stmt = select(func.coalesce(func.avg(EventoAnimal.peso_kg), 0)).where(
            EventoAnimal.tenant_id == self.tenant_id,
            EventoAnimal.tipo == tipo,
            EventoAnimal.peso_kg.is_not(None),
        )
        return float((await self.session.execute(stmt)).scalar_one() or 0)

    async def _contar_matrizes(self) -> int:
        stmt = select(func.count(AnimalGenetica.id)).where(
            AnimalGenetica.tenant_id == self.tenant_id,
            AnimalGenetica.matriz == True,  # noqa: E712
        )
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def _contar_diagnosticos_prenhes(self) -> int:
        stmt = select(func.count(EventoAnimal.id)).where(
            EventoAnimal.tenant_id == self.tenant_id,
            EventoAnimal.tipo == "DIAGNOSTICO_PRENHEZ",
            EventoAnimal.dados_extras["resultado"].as_string().ilike("PRENHE"),
        )
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def _contar_perdas_reprodutivas(self) -> int:
        stmt = select(func.count(EventoAnimal.id)).where(
            EventoAnimal.tenant_id == self.tenant_id,
            EventoAnimal.tipo == "DIAGNOSTICO_PRENHEZ",
            EventoAnimal.dados_extras["resultado"].as_string().in_(("VAZIA", "INCONCLUSIVO")),
        )
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def _media_idade_desmama(self) -> float:
        stmt = select(EventoAnimal.animal_id, EventoAnimal.data_evento).where(
            EventoAnimal.tenant_id == self.tenant_id,
            EventoAnimal.tipo == "DESMAME",
        )
        rows = list((await self.session.execute(stmt)).all())
        if not rows:
            return 0.0
        ids = [animal_id for animal_id, _ in rows]
        animais = {
            item.id: item
            for item in (
                await self.session.execute(select(Animal).where(Animal.id.in_(ids), Animal.tenant_id == self.tenant_id))
            ).scalars().all()
        }
        idades: list[float] = []
        for animal_id, data_evento in rows:
            animal = animais.get(animal_id)
            if animal and animal.data_nascimento:
                idades.append(float((data_evento - animal.data_nascimento).days))
        return sum(idades) / len(idades) if idades else 0.0

    async def _intervalo_medio_partos(self) -> float:
        stmt = select(EventoAnimal.animal_id, EventoAnimal.data_evento).where(
            EventoAnimal.tenant_id == self.tenant_id,
            EventoAnimal.tipo == "PARTO",
        ).order_by(EventoAnimal.animal_id, EventoAnimal.data_evento)
        rows = list((await self.session.execute(stmt)).all())
        intervalos: list[float] = []
        ultimo_por_mae: dict[uuid.UUID, date] = {}
        for animal_id, data_evento in rows:
            ultima = ultimo_por_mae.get(animal_id)
            if ultima:
                intervalos.append(float((data_evento - ultima).days))
            ultimo_por_mae[animal_id] = data_evento
        return sum(intervalos) / len(intervalos) if intervalos else 0.0

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
