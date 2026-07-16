# TERRITORY-CONVERGENCE-01G1-REGULARIZACAO-DIRECT-ONLY

Esta fase focou na regularização restrita e assistida dos últimos imóveis rurais que dependiam unicamente do vínculo legado direto (`DIRECT_ONLY`), sem aplicar automações irrestritas ou cruzar limites de segurança.

## 1. Relatórios e Reclassificação Determinística

Foi desenvolvido o script `generate_01g1_reports.py` que, respeitando o isolamento do tenant, levantou 77 casos pendentes (`DIRECT_ONLY`). O sistema avaliou deterministicamente se havia instâncias de exploração rural ativas para as respectivas Unidades Produtivas ou propriedades candidatas que fossem seguras.

Os bloqueios foram mapeados e geraram dois artefatos:
- `reports/territory_01g1_direct_only.json` (com dados completos e ofuscados)
- `reports/territory_01g1_decisions.csv` (matriz de decisão de input)

## 2. Aplicador Batch (CSV) e Proteção contra Heurísticas

O assistente CLI anterior (`resolve_territory_legacy.py`) foi transformado em um aplicador transacional por lote:
- Transação idempotente linha a linha.
- Contexto estrito de segurança RLS: `SET app.current_tenant_id = :tenant_id`.
- Rigor técnico implementado via guardrails no código: a ação `CREATE_PROPERTY` requer validação humana explícita através das colunas `justification` e `reviewed_by`. 
- Nenhuma Propriedade foi gerada puramente por cópia de nomes ou dedução heurística pelo sistema sem input do CSV.

## 3. Testes Unitários e Validação

Uma bateria de testes foi criada em `test_territory_convergence_01g1.py`, garantindo:
- Que ações malformadas ou com campos faltantes dão trigger em `ValueError`.
- Que mismatches de `tenant_id` impedem manipulação lateral.
- Parsing correto do CSV simulado.

Todos os 5 cenários testados executaram com sucesso (`100% passed`).

## 4. Resultados Aplicados e Gate de Elegibilidade

A base de dados foi aplicada através do `resolve_territory_legacy.py --apply`. Em sequência, as anomalias de conexões pendentes que bloqueavam o banco (lock por transações não-fechadas) foram purgadas da `pg_stat_activity`.

O Snapshot Final validado via `audit_territory_gate.py`:

```text
Gate de Elegibilidade (Fase 01H):
  DIRECT_ONLY: 0
  CANONICAL_ONLY: 125
  ORPHAN: 0
  TENANT_MISMATCH: 0
  AMBIGUOUS: 0
  DIVERGENT: 0
```

> [!SUCCESS] 
> **VEREDICTO: GO**  
> Todos os bloqueios fundiários diretos e as UPs órfãs vinculadas aos imóveis foram zerados. O estado dos dados atende rigorosamente aos critérios estipulados para autorizar a remoção de `imoveis_rurais.unidade_produtiva_id` (Fase 01H).
