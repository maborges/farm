"""Close the laboratory coffee season after validating its economic flow."""

import asyncio
from datetime import date

from sqlalchemy import func, select

from scripts.demo_lab_cafe import PHASES
from scripts.demo_lab_common import TENANT_ID, demo_id, demo_session
from scripts.demo_lab_guard import DemoLabTargetError


async def close():
    """Advance the season using its service after verifying tasks and DRE."""
    async with demo_session() as session:
        from core.model_registry import register_models

        register_models()
        from agricola.cultivos.models import Cultivo
        from agricola.dre.service import DREAgricolaV1Service
        from agricola.planejamento_operacional.models import PlanoOperacional
        from agricola.safras.models import Safra, SafraFaseHistorico
        from agricola.safras.service import SafraService
        from agricola.tarefas.models import SafraTarefa

        season_id = demo_id("cafe/safra-2026")
        season = (
            await session.execute(
                select(Safra).where(Safra.tenant_id == TENANT_ID, Safra.id == season_id)
            )
        ).scalar_one()
        tasks = (
            await session.execute(
                select(func.count())
                .select_from(SafraTarefa)
                .where(
                    SafraTarefa.tenant_id == TENANT_ID,
                    SafraTarefa.safra_id == season_id,
                    SafraTarefa.status == "CONCLUIDA",
                    SafraTarefa.operacao_id.is_not(None),
                )
            )
        ).scalar_one()
        dre = await DREAgricolaV1Service(session, TENANT_ID).gerar(safra_id=season_id)
        if tasks != 24 or dre.receita_bruta != 3000000 or dre.custos_diretos != 150000:
            raise DemoLabTargetError("Incomplete season or unexpected economic values")
        if season.status not in {phase for phase, _ in PHASES}:
            raise DemoLabTargetError("Unexpected season status")
        history = (
            await session.execute(
                select(SafraFaseHistorico).where(
                    SafraFaseHistorico.tenant_id == TENANT_ID,
                    SafraFaseHistorico.safra_id == season_id,
                    SafraFaseHistorico.fase_nova == "PLANEJADA",
                )
            )
        ).scalar_one_or_none()
        if history is None:
            session.add(
                SafraFaseHistorico(
                    id=demo_id("cafe/historico-planejamento"),
                    tenant_id=TENANT_ID,
                    safra_id=season_id,
                    fase_anterior=None,
                    fase_nova="PLANEJADA",
                    observacao="Ciclo sintético retroativo registrado no laboratório.",
                    dados_fase={"data_simulada": PHASES[0][1].isoformat()},
                )
            )
            await session.flush()
        service = SafraService(session, TENANT_ID)
        index = [phase for phase, _ in PHASES].index(season.status)
        for phase, simulated_date in PHASES[index + 1 :]:
            await service.avancar_fase(
                season_id,
                phase,
                observacao="Fase sintética de demonstração.",
                dados_fase={"data_simulada": simulated_date.isoformat()},
            )
        crop = (
            await session.execute(
                select(Cultivo).where(
                    Cultivo.tenant_id == TENANT_ID,
                    Cultivo.id == demo_id("cafe/cultivo-2026"),
                )
            )
        ).scalar_one()
        crop.data_plantio_real = date(2026, 2, 15)
        crop.data_colheita_real = date(2026, 8, 15)
        crop.data_fim = date(2026, 11, 5)
        crop.produtividade_real_sc_ha = 30
        crop.custo_realizado_ha = 1500
        crop.status = "ENCERRADO"
        plan = (
            await session.execute(
                select(PlanoOperacional).where(
                    PlanoOperacional.tenant_id == TENANT_ID,
                    PlanoOperacional.id == demo_id("cafe/plano"),
                )
            )
        ).scalar_one()
        plan.status = "CONCLUIDO"
        await session.commit()
        print("Season closed; simulated dates are in phase metadata")


if __name__ == "__main__":
    asyncio.run(close())
