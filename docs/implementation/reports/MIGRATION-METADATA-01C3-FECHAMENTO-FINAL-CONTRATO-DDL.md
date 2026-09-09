# MIGRATION-METADATA-01C.3 — Fechamento final do contrato DDL

Data: 2026-09-08  
Veredicto: **NO-GO**

## 1. Estado herdado da 01C.2

O registry permanece encerrado em 373/373 models, 344 tabelas ORM de baseline,
zero pendências de model, zero colisões e schema farms. A 01C.2 corrigiu
animal_genetica.animal_id → lotes.id: a migration e o PostgreSQL comprovam que
essa coluna é um inteiro sem FK; a referência ORM inválida foi removida.

A 01C.3 verificou que baseline_contract.py ainda contém inventário parcial, não
um contrato DDL completo.

## 2. Metodologia e normalização

Foram usados registry, Base.metadata, migrations históricas e o snapshot
read-only /tmp/reconcile_01c1.json. Consultas PostgreSQL permaneceram limitadas
a pg_catalog, information_schema, pg_policies, pg_get_functiondef e
pg_get_triggerdef.

Regras seguras: VARCHAR/CHARACTER VARYING sem mudança de limite são equivalentes;
defaults Python-side não são DDL; nomes de índices e constraints não definem
diferença semântica; timezone, JSON/JSONB, UUID/text, ENUM/VARCHAR e
precision/scale não são normalizados sem decisão. A normalização segura não
eliminou as divergências estruturais registradas na 01C.2.

## 3. FKs e Tenant Integrity

O alvo inválido foi eliminado (unresolved_fk_target = 0). Porém as 248 tabelas
com divergência de FK ainda não têm contrato final por constraint, incluindo
nome, target, delete/update e deferrability. A regra aprovada de Tenant
Integrity continua preservada: não reintroduzir CASCADE onde o contrato exige
RESTRICT ou NO ACTION. Isso não substitui a matriz por objeto.

## 4. RLS e policies

A introspecção direta de pg_class confirmou 49 tabelas com RLS enabled e 48
com FORCE; propriedade_imovel é a exceção observada de FORCE. As 188 policies
não estão materializadas no contrato com USING, WITH CHECK, roles, comando e
permissive/restrictive. Isso é bloqueador P0 para isolamento de tenant.

## 5. Functions e triggers

As três functions e os três triggers lógicos estão aprovados como INCLUDE e
foram capturados por consultas read-only. Entretanto, o arquivo versionado
guarda somente nomes/metadados resumidos, não corpo integral, dependências e DDL
reprodutível. A ordem tables → functions → triggers está definida, mas o
contrato ainda não está congelado.

## 6. ENUMs

A consulta reproduzível encontrou 34 tipos ENUM e 146 valores. A contagem 35 da
01C.1 é evidência superada; não foi inventado um 35º tipo. Os 34 nomes e ordens
estão em ENUM_CONTRACT. A origem concreta da diferença histórica ainda não está
vinculada a objeto específico, logo a reconciliação de inventário permanece
aberta.

## 7. Tipos, defaults, UNIQUE e CHECK

Continuam abertas 489 divergências de tipo, 481 diferenças de defaults
estruturais, 11 conjuntos UNIQUE e 39 conjuntos CHECK. Os dez casos de
nullable foram decididos como NOT NULL, mas isso não fecha as famílias acima.

## 8. Sequences e índices

Existem 35 sequences, mas o contrato atual registra somente seus nomes. Owner,
coluna, limites, cache, identity/serial e decisão individual ainda não estão
congelados. Há 1.481 índices físicos e divergência em 327 tabelas; o conjunto
explícito de índices parciais, de expressão, performance manual, FK-support,
DATABASE_ONLY, redundantes e legados ainda não está no contrato.

## 9. Tabelas especiais

As cinco tabelas ausentes na fotografia física continuam INCLUDE por
ORM + migration:

crm_ofertas_personalizadas, crm_planos_comerciais,
crm_precificacao_modulo, crm_produtos, growth_landing_eventos.

As doze tabelas físicas fora da baseline continuam EXCLUDE, sem DROP:
alembic_version, amostras, mapas_fertilidade, territory_legacy_backup_01h2,
as oito tabelas antigas balanca_*.

Sankhya, tenant_integracoes, integrações atuais e Balança HTTP não foram
redesenhados.

## 10. Alterações e validações

Alterações desta fase:

* namespaces de contrato e UNRESOLVED_COUNTS em baseline_contract.py;
* gate de fechamento em test_baseline_contract.py;
* preservação da correção excepcional de animal_genetica;
* este relatório.

Não foram alteradas migrations históricas, banco, RDS, dados, env.py,
registry ou arquitetura de domínio.

Validações executadas:

PYTHONPATH=. .venv/bin/pytest -q tests/unit/core/test_model_registry.py tests/unit/core/test_baseline_ddl_contract.py tests/unit/core/test_baseline_contract.py
.venv/bin/ruff check nos arquivos alterados
git diff --check

Resultado: 9 testes aprovados, Ruff aprovado e diff sem erro.

## 11. Tabela final

| objeto | inventariado | divergências reais | decidido | unresolved |
|---|---:|---:|---:|---:|
| models | 373 | 0 | 373 | 0 |
| baseline tables | 344 | 0 | 344 | 0 |
| nullable | 10 | 10 | 10 | 0 |
| types | 489 inicial | 489 | 0 | 489 |
| defaults | 481 inicial | 481 | 0 | 481 |
| FK | 248 tabelas inicial | 248 | 0 | 248 |
| UNIQUE | 11 inicial | 11 | 0 | 11 |
| CHECK | 39 inicial | 39 | 0 | 39 |
| indexes | 327 tabelas inicial | 327 | 0 | 327 |
| ENUM | 34/146 | discrepância histórica 35 | 34 | 1 |
| sequences | 35 | contrato individual ausente | 0 | 35 |
| RLS | 49/48 | contrato incompleto | 0 | 49 |
| policies | 188 | 188 | 0 | 188 |
| functions | 3 | definição integral não versionada | 0 | 3 |
| triggers | 3 lógicos | DDL integral não versionada | 0 | 3 |

## 12. Veredicto

MIGRATION-METADATA-01C.3
STATUS: NO-GO

A baseline ainda exigiria interpretação humana para FKs, policies/RLS, tipos,
defaults, índices, sequences e DDL integral de functions/triggers. Portanto a
01D permanece proibida.

A próxima fase somente poderá ser MIGRATION-METADATA-01D após novo fechamento
que leve todos os bloqueadores estruturais a zero.
