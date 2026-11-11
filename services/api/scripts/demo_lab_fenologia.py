"""Populate coffee phenology in the isolated demonstration laboratory."""

import asyncio
from datetime import date, timedelta

from sqlalchemy import select

from scripts.demo_lab_common import TENANT_ID, demo_id, demo_session, ensure_model


async def main():
    async with demo_session() as session:
        from core.model_registry import register_models
        register_models()
        from agricola.fenologia.models import FenologiaEscala, SafraFenologiaRegistro
        from agricola.fenologia.seed_escalas import ESCALAS_CAFE
        from agricola.safras.models import SafraTalhao

        season_id = demo_id("cafe/safra-2026")
        areas = (await session.execute(select(SafraTalhao.area_id).where(
            SafraTalhao.tenant_id == TENANT_ID, SafraTalhao.safra_id == season_id
        ).order_by(SafraTalhao.area_id))).scalars().all()
        if len(areas) != 4:
            raise RuntimeError("Expected four demonstration coffee plots")
        scales = {}
        for code, name, description, order in ESCALAS_CAFE:
            existing = (await session.execute(select(FenologiaEscala).where(
                FenologiaEscala.tenant_id == TENANT_ID, FenologiaEscala.cultura == "Café",
                FenologiaEscala.codigo == code,
            ))).scalars().all()
            if len(existing) > 1:
                raise RuntimeError(f"Duplicate coffee scale: {code}")
            scales[code] = existing[0] if existing else await ensure_model(
                session, FenologiaEscala, demo_id("fenologia/cafe/" + code),
                {"tenant_id": TENANT_ID, "cultura": "Café", "codigo": code,
                 "nome": name, "descricao": description, "ordem": order,
                 "is_system": True, "ativo": True},
            )
        observations = (
            ("73", date(2026, 2, 12), "Observação demonstrativa: frutos em expansão."),
            ("75", date(2026, 3, 26), "Observação demonstrativa: frutos verdes desenvolvidos."),
            ("81", date(2026, 5, 14), "Observação demonstrativa: início da maturação."),
        )
        for index, area_id in enumerate(areas):
            for code, observed, note in observations:
                await ensure_model(session, SafraFenologiaRegistro,
                    demo_id(f"fenologia/{area_id}/{code}"),
                    {"tenant_id": TENANT_ID, "safra_id": season_id, "talhao_id": area_id,
                     "escala_id": scales[code].id, "data_observacao": observed + timedelta(days=index),
                     "observacao": note, "usuario_id": None, "grupo_id": None, "dados_extras": None})
        await session.commit()
        print(f"Fenologia: {len(scales)} escalas e {len(areas) * len(observations)} registros demonstrativos.")


if __name__ == "__main__":
    asyncio.run(main())
