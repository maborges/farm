#!/usr/bin/env python3
"""
Script de seed para validação Android real do Campo PWA.

Cria tarefas de teste no backend:
  - 2 tarefas para hoje (PENDENTE)
  - 2 tarefas atrasadas (PENDENTE)
  - 1 tarefa futura (não deve aparecer no PWA)

Uso:
  cd /opt/lampp/htdocs/farm/services/api
  python ../../scripts/campo_seed_validacao.py \
    --base-url http://localhost:8000/api/v1 \
    --token <JWT_TOKEN_DO_GESTOR> \
    --fazenda-id <UUID_FAZENDA>
"""
import argparse
import sys
import json
from datetime import date, timedelta

try:
    import httpx
except ImportError:
    print("Instale httpx: pip install httpx")
    sys.exit(1)


def criar_tarefa(client: httpx.Client, base_url: str, payload: dict) -> dict:
    r = client.post(f"{base_url}/campo/tarefas", json=payload)
    r.raise_for_status()
    return r.json()


def main():
    parser = argparse.ArgumentParser(description="Seed de tarefas para validação Android")
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--token", required=True, help="JWT do gestor")
    parser.add_argument("--fazenda-id", required=True, help="UUID da UnidadeProdutiva")
    parser.add_argument("--talhao-id", default=None, help="UUID do talhão (opcional)")
    args = parser.parse_args()

    hoje = date.today()
    ontem = hoje - timedelta(days=1)
    semana_passada = hoje - timedelta(days=7)
    amanha = hoje + timedelta(days=1)

    tarefas = [
        {
            "titulo": "[TESTE-D1] Aplicação herbicida — hoje",
            "type": "APLICACAO_DEFENSIVO",
            "module": "agricola",
            "data_programada": str(hoje),
            "prioridade": "ALTA",
            "unidade_produtiva_id": args.fazenda_id,
            "area_rural_id": args.talhao_id,
            "dados": {"produto": "Glifosato", "dose_L_ha": "2.5"},
        },
        {
            "titulo": "[TESTE-D2] Vacinação febre aftosa — hoje",
            "type": "VACINACAO_LOTE",
            "module": "pecuaria",
            "data_programada": str(hoje),
            "prioridade": "URGENTE",
            "unidade_produtiva_id": args.fazenda_id,
            "dados": {"vacina": "Aftosa", "dose_ml": "2"},
        },
        {
            "titulo": "[TESTE-D3] Pesagem lote — ATRASADA 1 dia",
            "type": "PESAGEM_ANIMAL",
            "module": "pecuaria",
            "data_programada": str(ontem),
            "prioridade": "NORMAL",
            "unidade_produtiva_id": args.fazenda_id,
            "dados": {"lote": "Lote A"},
        },
        {
            "titulo": "[TESTE-D4] Amostragem solo — ATRASADA 7 dias",
            "type": "AMOSTRAGEM_SOLO",
            "module": "agricola",
            "data_programada": str(semana_passada),
            "prioridade": "BAIXA",
            "unidade_produtiva_id": args.fazenda_id,
            "area_rural_id": args.talhao_id,
            "dados": {"profundidade_cm": "20"},
        },
        {
            "titulo": "[TESTE-D5] Irrigação — FUTURA (não deve aparecer no PWA)",
            "type": "IRRIGACAO_EVENTO",
            "module": "agricola",
            "data_programada": str(amanha),
            "prioridade": "NORMAL",
            "unidade_produtiva_id": args.fazenda_id,
            "dados": {"tempo_min": "60"},
        },
    ]

    headers = {"Authorization": f"Bearer {args.token}"}
    created = []

    with httpx.Client(headers=headers, timeout=30) as client:
        for t in tarefas:
            try:
                result = criar_tarefa(client, args.base_url, t)
                created.append(result)
                print(f"✅ {t['titulo']} → id={result['id']}")
            except httpx.HTTPStatusError as e:
                print(f"❌ {t['titulo']} → {e.response.status_code}: {e.response.text}")

    print(f"\n{len(created)}/{len(tarefas)} tarefas criadas.")
    print("\nIDs criados:")
    for c in created:
        print(f"  {c['id']}  {c['titulo']}")

    print("\n📱 No PWA:")
    print("  - Seção 'Para Hoje': 2 tarefas (TESTE-D1 e TESTE-D2)")
    print("  - Seção 'Atrasadas': 2 tarefas (TESTE-D3 e TESTE-D4)")
    print("  - TESTE-D5 NÃO deve aparecer (data futura)")


if __name__ == "__main__":
    main()
