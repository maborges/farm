# MIGRATION-METADATA-01D5 — Auditoria e saneamento de índices da baseline

## Veredicto

`MIGRATION-METADATA-01D5 STATUS: GO PARA PROVA POSTGRESQL`

A camada de índices da baseline foi auditada após `register_models()` e após a
aplicação de `baseline_candidate_tables()`. Os cinco critérios estruturais da
fase foram satisfeitos. Nenhuma alteração foi executada em RDS ou em outro
banco PostgreSQL.

## Escopo e resultado

| Métrica | Resultado |
|---|---:|
| Tabelas da baseline | 344 |
| FKs preservadas/auditadas | 892 |
| Índices no metadata da baseline | 1.029 |
| Nomes de índice duplicados | 0 |
| Definições de índice duplicadas | 0 |
| Colisões no namespace de relations de `farms` | 0 |
| Índices com colunas inválidas | 0 |
| Índices UNIQUE redundantes com `UniqueConstraint` | 0 |
| Targets de FK fora da baseline | 0 |
| CHECKs inválidos | 0 |
| FKs compostas sem PK/UNIQUE | 0 |
| Relações Tenant Integrity ausentes | 0 |

O inventário inicial tinha 1.050 objetos `Index`. Foram eliminados 21
objetos redundantes: 13 duplicidades de nome e 8 duplicidades semânticas com
nomes diferentes. O contrato funcional das colunas indexadas foi mantido; em
cada caso foi mantida uma única definição gerada pelo metadata.

## Caso `ix_campo_tarefas_type`

Em `campo_tarefas`, a coluna `type` declarava `index=True` e o `__table_args__`
também declarava explicitamente `Index("ix_campo_tarefas_type", "type")`.
Essas duas declarações materializavam duas instâncias `Index` com o mesmo nome
na mesma tabela. A migration histórica `20260508_campo_pwa.py` confirma que o
índice é uma relação esperada do domínio, mas a cadeia histórica não é usada
como mecanismo de instalação limpa.

A correção removeu somente a declaração explícita redundante do model e
preservou o índice derivado de `index=True`. O metadata passou a conter uma
instância e o SQL offline passou a emitir:

`ix_campo_tarefas_type`: 1 ocorrência de `CREATE INDEX`.

Não foram usados `IF NOT EXISTS`, `DROP`, tratamento silencioso de erro ou
renome artificial.

## Duplicidades corrigidas

### Nomes repetidos

As seguintes duplicidades tinham a mesma causa estrutural — coluna com
`index=True` coexistindo com `Index(...)` explícito equivalente — e foram
resolvidas removendo a declaração explícita redundante:

- `ix_campo_tarefas_type`;
- `ix_esg_relatorio_evidencias_evidencia_id`;
- `ix_esg_relatorio_indicadores_evidencia_id`;
- `ix_esg_relatorios_imovel_rural_id`;
- `ix_esg_relatorios_programa_id`;
- `ix_esg_relatorios_propriedade_id`;
- `ix_esg_relatorios_propriedade_imovel_id`;
- `ix_rastreabilidade_passaportes_caderno_lote_comercial_id`;
- `ix_rastreabilidade_passaportes_imovel_rural_id`;
- `ix_rastreabilidade_passaportes_lote_rastreabilidade_id`;
- `ix_rastreabilidade_passaportes_programa_id`;
- `ix_rastreabilidade_passaportes_propriedade_id`;
- `ix_rastreabilidade_passaportes_propriedade_imovel_id`.

### Definições semanticamente repetidas com nomes distintos

Também foram removidos os `Index(...)` explícitos redundantes abaixo,
mantendo-se o índice de coluna gerado pelo SQLAlchemy:

| Tabela | Definição removida | Definição mantida |
|---|---|---|
| `planos_operacionais_tarefas_insumos` | `ix_plano_op_tarefa_insumos_produto` em `produto_id` | `ix_planos_operacionais_tarefas_insumos_produto_id` |
| `automacoes_configuracoes` | `ix_automacoes_conf_tenant` em `tenant_id` | `ix_automacoes_configuracoes_tenant_id` |
| `rastreabilidade_passaporte_evidencias` | `ix_passaporte_evidencias_evidencia_id` em `evidencia_id` | índice gerado da coluna |
| `cadastros_propriedades` | `ix_propriedades_tenant` em `tenant_id` | `ix_cadastros_propriedades_tenant_id` |
| `cadastros_exploracoes_rurais` | `ix_exploracoes_tenant` em `tenant_id` | `ix_cadastros_exploracoes_rurais_tenant_id` |
| `planos_operacionais_tarefas` | `ix_plano_op_tarefas_safra_tarefa` em `safra_tarefa_id` | índice gerado da coluna |
| `campo_tarefas` | `ix_campo_tarefas_unidade` em `unidade_produtiva_id` | `ix_campo_tarefas_unidade_produtiva_id` |
| `safra_tarefas` | `ix_safra_tarefas_talhao` em `talhao_id` | `ix_safra_tarefas_talhao_id` |

As migrations históricas foram usadas apenas para confirmar a origem e a
semântica dos índices. Nenhuma migration histórica foi alterada.

## Arquivos alterados

- `services/api/agricola/planejamento_operacional/models.py`;
- `services/api/agricola/tarefas/models.py`;
- `services/api/automacoes/models.py`;
- `services/api/campo/models.py`;
- `services/api/certificacoes_esg/models.py`;
- `services/api/core/cadastros/propriedades/propriedade_models.py`;
- `services/api/migrations/metadata_audit.py`;
- `services/api/tests/migrations/test_baseline_metadata_audit.py`;
- este relatório.

O auditor reutilizado agora percorre os índices das 344 tabelas e retorna
`total_indexes`, `duplicate_index_names`, `duplicate_index_definitions`,
`index_relation_name_collisions`, `indexes_missing_columns` e
`redundant_unique_indexes`. A colisão de nomes é comparada globalmente contra
tabelas e sequences da baseline no namespace de `farms`, e não somente dentro
da tabela proprietária.

## Validações executadas

- `PYTHONPATH=. .venv/bin/pytest -q tests/migrations/test_baseline_metadata_audit.py`: **9 passed**;
- testes de auditoria, registry e contratos DDL: **23 passed**;
- `PYTHONPATH=. .venv/bin/alembic upgrade baseline_deepfarms_v1 --sql`: concluído;
- SQL offline: **1.029** comandos `CREATE INDEX`/`CREATE UNIQUE INDEX`, **0** nomes repetidos;
- teste/checagem de `ix_campo_tarefas_type`: **1** emissão;
- `git diff --check`: passou;
- Ruff focalizado em `migrations/metadata_audit.py` e
  `tests/migrations/test_baseline_metadata_audit.py`: passou.

Os testes adicionados protegem contra regressão de nomes duplicados,
definições duplicadas, colisões globais de relations, colunas inválidas e
contra o reaparecimento específico de `ix_campo_tarefas_type`.

## Blockers remanescentes

Nenhum blocker estrutural conhecido na baseline. FKs, Tenant Integrity e
CHECKs continuam com os resultados aprovados na fase 01D4.

A próxima ação autorizada é exclusivamente a prova online em PostgreSQL vazio;
esta fase não executou a baseline no RDS.
