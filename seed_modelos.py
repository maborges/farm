import sys
import os
import asyncio
import uuid
import json

# connect to postgres
import asyncpg

async def main():
    conn = await asyncpg.connect("postgresql://borgus:numsey01@192.168.0.2/farms")

    models = [
        {
            "especie": "Bovino de Leite",
            "tipo_risco": "Estresse Térmico",
            "regras_risco": '{"nivel_critico": 82, "nivel_alto": 78, "nivel_medio": 72}',
            "is_global": True
        },
        {
            "especie": "Bovino de Corte",
            "tipo_risco": "Estresse Térmico",
            "regras_risco": '{"nivel_critico": 84, "nivel_alto": 79, "nivel_medio": 75}',
            "is_global": True
        },
        {
            "especie": "Ovino",
            "tipo_risco": "Estresse Térmico",
            "regras_risco": '{"nivel_critico": 85, "nivel_alto": 81, "nivel_medio": 78}',
            "is_global": True
        },
        {
            "especie": "Caprino",
            "tipo_risco": "Estresse Térmico",
            "regras_risco": '{"nivel_critico": 85, "nivel_alto": 81, "nivel_medio": 78}',
            "is_global": True
        }
    ]

    for m in models:
        # Check if exists
        res = await conn.fetchval("SELECT id FROM modelos_zoosanitarios WHERE especie = $1 AND is_global = true", m["especie"])
        if not res:
            await conn.execute("INSERT INTO modelos_zoosanitarios (id, especie, tipo_risco, regras_risco, is_global, tenant_id) VALUES ($1, $2, $3, $4::jsonb, $5, NULL)",
                                str(uuid.uuid4()), m["especie"], m["tipo_risco"], m["regras_risco"], True)
            print(f"Inserted {m['especie']}")
    
    await conn.close()
    print("Done")

if __name__ == "__main__":
    asyncio.run(main())
