# MIGRATION-METADATA-01D3 — Auditoria pré-execução da baseline

**Data:** 2026-09-09  
**Escopo:** `Base.metadata` após `register_models()`, registry, contrato da baseline, revision independente, migrations históricas relevantes e relatórios de contrato físico disponíveis no repositório.

## 1. Veredicto

```text
MIGRATION-METADATA-01D3 STATUS: NO-GO
```

A baseline não deve ser tentada no RDS ainda. Foram encontrados cinco blockers de integridade reproduzíveis antes de qualquer DDL online: dois pares de tipos incompatíveis, duas FKs compostas cujo pai não possui PK/UNIQUE com a mesma composição e ordem, e uma FK composta de Tenant Integrity que está no histórico fechado mas não está no metadata atual. A compilação offline passa, mas `--sql` não faz validação semântica pelo PostgreSQL.

## 2. Cobertura e método

O registry carregou 373 tabelas ORM; o conjunto aprovado pela baseline contém 344 tabelas. Foram auditadas **891 FKs** e **61 CHECK constraints** do conjunto de 344. O auditor reutilizável está em [`migrations/metadata_audit.py`](/opt/lampp/htdocs/farm/services/api/migrations/metadata_audit.py) e os testes em [`tests/migrations/test_baseline_metadata_audit.py`](/opt/lampp/htdocs/farm/services/api/tests/migrations/test_baseline_metadata_audit.py).

O auditor compara tipos compilados no dialeto PostgreSQL, resolve targets e colunas do metadata, verifica PK/UNIQUE (incluindo índice UNIQUE simples), analisa referências textuais de CHECK e confere o escopo da baseline.

| Item | Resultado |
|---|---:|
| Tabelas na baseline | 344 |
| FKs auditadas | 891 |
| Incompatibilidades de tipo | 2 |
| FKs compostas sem PK/UNIQUE compatível | 2 |
| Targets fora da baseline | 0 |
| CHECKs com coluna inexistente | 0 |
| FKs sem nome explícito no ORM | 885 |

## 3. FKs bloqueantes

| Tabela origem | Constraint | Coluna origem | Tipo origem | Tabela destino | Coluna destino | Tipo destino | Problema | Decisão recomendada |
|---|---|---|---|---|---|---|---|---|
| `cochos` | gerada pelo PostgreSQL (`None` no ORM) | `responsavel_id` | `VARCHAR(36)` | `usuarios` | `id` | `UUID` | PostgreSQL rejeita a FK por tipos incompatíveis | Congelar o contrato semântico. A migration `67b25594e50f` usa UUID; corrigir o model/baseline para UUID somente após essa decisão, preservando a FK. |
| `confinamento_lotes` | gerada pelo PostgreSQL (`None` no ORM) | `unidade_produtiva_id` | `VARCHAR(36)` | `unidades_produtivas` | `id` | `UUID` | PostgreSQL rejeita a FK por tipos incompatíveis | O pai canônico é UUID. Provar e congelar a representação UUID; corrigir o model/baseline em desenvolvimento, sem cast ou remoção da FK. |
| `frota_abastecimentos` | `fk_fa_tenant_equipamento` | `tenant_id`, `equipamento_id` | `UUID`, `UUID` | `cadastros_equipamentos` | `tenant_id`, `id` | `UUID`, `UUID` | Pai possui somente PK(`id`); falta UNIQUE(`tenant_id`, `id`) | Emitir UNIQUE no pai antes das FKs (ou dentro do `CREATE TABLE`) e manter a FK composta. |
| `frota_apontamentos_uso` | `fk_fau_tenant_jornada` | `tenant_id`, `jornada_id` | `UUID`, `UUID` | `frota_jornadas_equipamento` | `tenant_id`, `id` | `UUID`, `UUID` | Pai possui somente PK(`id`); falta UNIQUE(`tenant_id`, `id`) | Emitir UNIQUE no pai antes das FKs (ou dentro do `CREATE TABLE`) e manter a FK composta. |

Não foram identificadas outras incompatibilidades de tipo entre as 891 FKs. Classes Python distintas que compilam para `UUID` PostgreSQL foram tratadas como equivalentes.

## 4. FKs compostas e Tenant Integrity

As seis FKs compostas presentes no metadata são:

| Filho | Pai | Colunas no pai | Situação |
|---|---|---|---|
| `cadastros_areas_rurais` | `unidades_produtivas` | (`tenant_id`, `id`) | UNIQUE presente |
| `cadastros_equipamentos` | `unidades_produtivas` | (`tenant_id`, `id`) | UNIQUE presente |
| `estoque_depositos` | `unidades_produtivas` | (`tenant_id`, `id`) | UNIQUE presente |
| `frota_jornadas_equipamento` | `unidades_produtivas` | (`tenant_id`, `id`) | UNIQUE presente |
| `frota_abastecimentos` | `cadastros_equipamentos` | (`tenant_id`, `id`) | **ausente — blocker** |
| `frota_apontamentos_uso` | `frota_jornadas_equipamento` | (`tenant_id`, `id`) | **ausente — blocker** |

O conjunto Tenant Integrity fechado em `tenant_integrity_repair_01c_composite_fks.py` possui uma sétima relação: `compras_pedidos → estoque_depositos`, `fk_cp_tenant_deposito`, sobre (`tenant_id`, `deposito_id`) → (`tenant_id`, `id`), com `ON DELETE NO ACTION`. Ela não está no metadata atual. Isso é regressão de isolamento/contrato e deve ser restaurado na baseline, além de o pai `estoque_depositos` possuir UNIQUE compatível.

`unidades_produtivas` possui `uq_unidades_produtivas_tenant_id_id` no ORM, em concordância com `20260716_config_up_security_freeze` e com o relatório Tenant Integrity. Não há redesenho de isolamento nesta auditoria.

Há 233 FKs ORM diretas para `tenants` com `CASCADE`, mas `baseline_contract.py` transforma essas FKs em `RESTRICT` na emissão da baseline. Isso está alinhado à decisão Tenant Integrity. Cascades em relações operacionais entre entidades não foram classificados como cascades diretos de tenant e não foram removidos. Todas as 891 FKs têm `ON UPDATE NO ACTION` no ORM.

## 5. CHECK constraints

Foram examinadas 61 CHECKs:

```text
CHECKs com colunas inexistentes: 0
CHECK atual de wizard usando codigo_etapa em wizard_implantacoes_operacionais: 0
```

`wizard_implantacoes_operacionais` usa corretamente `etapa_atual` no metadata atual. A migration histórica `20260630_wizard_foundation` contém a expressão original `codigo_etapa` e registra sua substituição para `etapa_atual`; essa ocorrência não deve ser copiada cegamente para a baseline. Não foi detectado literal inválido nos CHECKs atuais.

Os 39 conjuntos de CHECK divergentes registrados em `MIGRATION-METADATA-01C` continuam sendo fechamento de contrato físico, mas não produziram blocker de coluna inexistente nesta auditoria.

## 6. Targets fora da baseline e tabelas excluídas

Targets fora do conjunto aprovado: **0**. Não reaparecem como tabelas da baseline: `balanca_afericoes`, `balanca_avaliacoes_prestador`, `balanca_dispositivos`, `balanca_fisicas`, `balanca_operadores`, `balanca_ordens`, `balanca_pesagens`, `balanca_sync_tombstones`, `amostras`, `mapas_fertilidade` e `territory_legacy_backup_01h2`.

As sequências das três últimas tabelas estão marcadas `NOT_REQUIRED`; `alembic_version` é infraestrutura do Alembic e não pertence às 344 tabelas de domínio.

## 7. ORM × contrato × histórico

| Objeto | ORM atual | Contrato / migration histórica | Divergência |
|---|---|---|---|
| `wizard_implantacoes_operacionais.etapa_atual` | CHECK correto | `20260630_wizard_foundation` possui legado `codigo_etapa` e substituição | Resolvido no ORM; baseline deve usar apenas a expressão atual. |
| `unidades_produtivas` | UNIQUE(`tenant_id`, `id`) presente | `20260716_config_up_security_freeze` cria `uq_unidades_produtivas_tenant_id_id` | Resolvido; não remover nem duplicar. |
| `cochos.responsavel_id` | `String(36)` para `usuarios.id` | `67b25594e50f` usa UUID; `fase3_sprints27_33_final` usa Integer | Contrato histórico inconsistente; exige decisão explícita. |
| `confinamento_lotes.unidade_produtiva_id` | `String(36)` para UUID | `67b25594e50f` declara UUID; versão final anterior não tem esse vínculo canônico | ORM atual incompatível; confirmar UUID e manter FK. |
| FKs compostas de Tenant Integrity | 6 no ORM atual | `tenant_integrity_repair_01c_composite_fks` fecha 7 relações e UNIQUEs dos pais | Restaurar `fk_cp_tenant_deposito` e fechar os dois UNIQUEs ausentes; não aceitar regressão cross-tenant. |

O histórico foi usado como evidência/contrato, não como mecanismo de instalação limpa. Nenhuma migration histórica foi alterada.

## 8. Ordem de criação

A revision `20260908_baseline_deepfarms_v1.py` emite:

```text
schema → ENUMs → sequences → tables sem FKs → FKs → indexes
→ functions/triggers → RLS/FORCE → policies
```

As FKs vêm depois de todas as tabelas. As duas UNIQUE ausentes precisam existir no `CREATE TABLE` do pai ou ser criadas antes de `op.create_foreign_key`.

## 9. Classificação

**BLOQUEANTE**

1. `cochos.responsavel_id VARCHAR(36) → usuarios.id UUID`.
2. `confinamento_lotes.unidade_produtiva_id VARCHAR(36) → unidades_produtivas.id UUID`.
3. `fk_fa_tenant_equipamento` sem UNIQUE compatível em `cadastros_equipamentos`.
4. `fk_fau_tenant_jornada` sem UNIQUE compatível em `frota_jornadas_equipamento`.
5. `fk_cp_tenant_deposito` ausente do metadata, embora faça parte do contrato Tenant Integrity fechado.

**ALTA**

1. Contrato histórico divergente dos dois campos `_id` de confinamento; não converter por conveniência nem remover FK.
2. Prova online em PostgreSQL vazio descartável ainda não executada, conforme `MIGRATION-METADATA-01D`.
3. `UNIQUE_CONTRACT`, `CHECK_CONTRACT` e `INDEX_CONTRACT` ainda não expressam todas as decisões físicas pendentes do 01C.

**MÉDIA**

1. 885 FKs sem nome explícito no ORM. PostgreSQL gera nomes válidos; não é blocker, mas nomes determinísticos são recomendados.
2. Diferenças históricas de 11 UNIQUE, 39 CHECK e 327 conjuntos de índices permanecem como fechamento de contrato/performance.

**BAIXA**

1. Padronizar a representação Python/SQLAlchemy do UUID para reduzir ruído em auditorias futuras.

## 10. Menor conjunto seguro de alterações

Somente no desenvolvimento e versionado:

1. decidir e congelar os contratos dos dois campos incompatíveis, com UUID como hipótese sustentada por `67b25594e50f`, sujeita à confirmação do domínio;
2. alinhar models e baseline aos contratos aprovados;
3. adicionar UNIQUE(`tenant_id`, `id`) em `cadastros_equipamentos` e `frota_jornadas_equipamento` antes das FKs compostas;
4. restaurar `fk_cp_tenant_deposito` na baseline, mantendo `NO ACTION` e as decisões de Tenant Integrity;
5. executar novamente o guardrail e exigir zero findings estruturais e zero regressões do conjunto Tenant Integrity;
6. aplicar em PostgreSQL descartável vazio, recriar o alvo e repetir a prova online antes do RDS.

Não fazem parte do conjunto seguro: remover FKs, fazer casts implícitos, alterar migrations históricas, reabrir Tenant Integrity ou reparar diretamente no EC2/RDS.

## 11. Validações executadas

```text
PYTHONPATH=. .venv/bin/pytest -q tests/migrations/test_baseline_metadata_audit.py
4 passed

git diff --check
passed

PYTHONPATH=. .venv/bin/alembic upgrade baseline_deepfarms_v1 --sql
return code 0
```

O SQL offline foi gerado em `/tmp/migration-metadata-01d3-baseline.sql`. A aprovação final continua bloqueada pelos cinco findings de integridade e pela ausência de prova online em banco descartável.
