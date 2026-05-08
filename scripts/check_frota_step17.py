import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta

# Configura o path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
API_DIR = os.path.join(PROJECT_ROOT, 'services', 'api')
sys.path.append(API_DIR)

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func, select, and_

# Configuração dinâmica de DB
try:
    from core.config import settings
    DATABASE_URL = str(settings.database_url)
    if "postgresql" not in DATABASE_URL:
        raise ValueError("Not postgres")
except Exception:
    DATABASE_URL = f"sqlite+aiosqlite:///{os.path.join(API_DIR, 'agrosaas.db')}"

from growth.models import LandingEvento

async def check_metrics():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    _EVENTOS_CTA = {"cta_click", "cta_test_click", "cta_demo_click", "plan_select"}
    # Pegamos apenas os eventos dos últimos 10 minutos para focar nesta simulação
    desde = datetime.now(timezone.utc) - timedelta(hours=2)
    path = "/frota"

    async with async_session() as session:
        print(f"Métricas Step 17 para {path}:")
        
        # Total
        q_v = await session.execute(select(func.count()).where(and_(LandingEvento.evento == "landing_view", LandingEvento.path == path, LandingEvento.created_at >= desde)))
        total_v = q_v.scalar() or 0
        
        q_c = await session.execute(select(func.count()).where(and_(LandingEvento.evento.in_(_EVENTOS_CTA), LandingEvento.path == path, LandingEvento.created_at >= desde)))
        total_c = q_c.scalar() or 0
        
        print(f"Total Visitas Recentes: {total_v}")
        print(f"Total CTA Recentes: {total_c}")
        print(f"Conversion Rate: {round((total_c/total_v*100), 2) if total_v > 0 else 0}%")
        print("-" * 20)

        for variant in ("A", "B", "C"):
            q_vv = await session.execute(select(func.count()).where(and_(LandingEvento.evento == "landing_view", LandingEvento.path == path, LandingEvento.headline_variant == variant, LandingEvento.created_at >= desde)))
            v_v = q_vv.scalar() or 0
            
            q_cc = await session.execute(select(func.count()).where(and_(LandingEvento.evento.in_(_EVENTOS_CTA), LandingEvento.path == path, LandingEvento.headline_variant == variant, LandingEvento.created_at >= desde)))
            v_c = q_cc.scalar() or 0
            
            rate = round((v_c/v_v*100), 2) if v_v > 0 else 0
            label = "B1 (Número)" if variant == "A" else "B2 (Tempo)" if variant == "B" else "B3 (Risco)"
            print(f"Variant {variant} ({label}): Visitas={v_v}, Clicks={v_c}, CR={rate}%")

if __name__ == "__main__":
    asyncio.run(check_metrics())
