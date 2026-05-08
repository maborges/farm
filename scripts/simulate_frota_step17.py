import asyncio
import uuid
import random
import hashlib
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

# Configuração dinâmica de DB
try:
    from core.config import settings
    DATABASE_URL = str(settings.database_url)
    if "postgresql" not in DATABASE_URL:
        raise ValueError("Not postgres")
except Exception:
    DATABASE_URL = f"sqlite+aiosqlite:///{os.path.join(API_DIR, 'agrosaas.db')}"

from growth.models import LandingEvento

async def simulate():
    print(f"Usando DB: {DATABASE_URL}")
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    variants = ["A", "B", "C"]
    # Metas de conversão para Step 17
    # A (B1): 25% | B (B2): 18% | C (B3): 21%
    rates = {"A": 0.25, "B": 0.18, "C": 0.21}
    
    total_visitas = 400
    path = "/frota"

    async with async_session() as session:
        print(f"Iniciando simulação de {total_visitas} visitas em {path} (Step 17)...")
        
        for i in range(total_visitas):
            variant = random.choice(variants)
            sessao_id = str(uuid.uuid4())
            ip_hash = hashlib.sha256(f"ip-s17-{i}".encode()).hexdigest()[:32]
            
            # 1. Registro de landing_view
            evento_view = LandingEvento(
                sessao_id=sessao_id,
                evento="landing_view",
                headline_variant=variant,
                path=path,
                ip_hash=ip_hash,
                device="desktop",
                created_at=datetime.now(timezone.utc) - timedelta(minutes=random.randint(1, 100))
            )
            session.add(evento_view)
            
            # 2. Possível clique no CTA baseado na taxa
            if random.random() < rates[variant]:
                evento_cta = LandingEvento(
                    sessao_id=sessao_id,
                    evento=random.choice(["cta_test_click", "cta_demo_click"]),
                    headline_variant=variant,
                    path=path,
                    ip_hash=ip_hash,
                    device="desktop",
                    created_at=evento_view.created_at + timedelta(seconds=random.randint(5, 60))
                )
                session.add(evento_cta)
            
            if i % 100 == 0:
                await session.commit()
                print(f"Processado {i}/{total_visitas}...")

        await session.commit()
        print("Simulação concluída!")

if __name__ == "__main__":
    asyncio.run(simulate())
