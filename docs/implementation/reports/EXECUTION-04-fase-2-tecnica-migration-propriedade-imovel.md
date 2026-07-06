# EXECUTION-04 — Fase 2 Técnica: Migration Real de `propriedade_imovel`

## Objetivo
Criar a migration real da tabela oficial `propriedade_imovel`, partindo do head consolidado `merge_heads_before_propriedade_imovel`.

## 1. Pré-check

### `git status --short`
O worktree já possuía alterações não relacionadas, mas não havia conflito técnico com o saneamento do grafo Alembic.

### `alembic heads`
Antes da nova migration:
- `merge_heads_before_propriedade_imovel (head)`

Depois da nova migration:
- `add_propriedade_imovel (head)`

### Conclusão
O head consolidado existia e o grafo estava apto para receber a migration real.

## 2. Migration criada

### Arquivo
- [`services/api/migrations/versions/add_propriedade_imovel.py`](/opt/lampp/htdocs/farm/services/api/migrations/versions/add_propriedade_imovel.py)

### Revision criada
- `add_propriedade_imovel`

### Dependência
- `down_revision = "merge_heads_before_propriedade_imovel"`

## 3. Tabela `propriedade_imovel`

### Definição
A migration cria a tabela:
- `propriedade_imovel`

### Campos incluídos
- `id` UUID PK
- `tenant_id` UUID not null
- `propriedade_id` UUID not null
- `imovel_rural_id` UUID not null
- `tipo_vinculo` string not null
- `ativo` boolean not null default true
- `data_inicio` date not null
- `data_fim` date nullable
- `origem_documental` text not null
- `observacoes` text nullable
- `area_vinculada` numeric nullable
- `percentual_vinculado` numeric nullable
- `vinculo_principal` boolean not null default false
- `origem_referencia` text nullable
- `status_documental` string nullable
- `created_at` timestamp not null default now
- `updated_at` timestamp not null default now
- `created_by` UUID nullable
- `updated_by` UUID nullable

### Observação técnica
- `data_inicio` e `data_fim` foram modeladas como `DATE`, seguindo o padrão da vigência documental.
- `created_at` e `updated_at` usam `DateTime(timezone=True)`.

## 4. Constraints

### Incluídas
- PK em `id`
- FK `tenant_id -> tenants.id`
- FK `propriedade_id -> cadastros_propriedades.id`
- FK `imovel_rural_id -> imoveis_rurais.id`
- FK `created_by -> usuarios.id`
- FK `updated_by -> usuarios.id`
- check constraint para `tipo_vinculo` textual
- check constraint para datas válidas
- check constraint para `percentual_vinculado` entre 0 e 100
- check constraint para `area_vinculada` não negativa

### Proteção de vínculo principal
- foi criada uma unique index parcial:
  - `uq_propriedade_imovel_principal_ativo`
- regra:
  - `vinculo_principal IS TRUE AND ativo IS TRUE AND data_fim IS NULL`

### Decisão tomada
- não foi criado enum PostgreSQL
- foi usada validação textual por check constraint, como solicitado

## 5. Índices

### Obrigatórios
- `ix_propriedade_imovel_tenant_id`
- `ix_propriedade_imovel_propriedade_id`
- `ix_propriedade_imovel_imovel_rural_id`
- `ix_propriedade_imovel_tenant_propriedade`
- `ix_propriedade_imovel_tenant_imovel_rural`

### Recomendados
- `ix_propriedade_imovel_tipo_vinculo`
- `ix_propriedade_imovel_ativo`
- `ix_propriedade_imovel_data_inicio`
- `ix_propriedade_imovel_data_fim`
- `ix_propriedade_imovel_vinculo_principal`

## 6. RLS físico

### Aplicado na migration
- `ALTER TABLE propriedade_imovel ENABLE ROW LEVEL SECURITY`
- `ALTER TABLE propriedade_imovel FORCE ROW LEVEL SECURITY`

### Policies criadas
- `propriedade_imovel_select_policy`
- `propriedade_imovel_insert_policy`
- `propriedade_imovel_update_policy`
- `propriedade_imovel_delete_policy`

### Regra base
- `tenant_id = current_setting('app.current_tenant_id', true)::uuid`

### Segurança
- abordagem fail-closed
- sem `app.current_tenant_id`, a comparação não libera acesso
- não existe acesso cross-tenant por policy

## 7. Comentários

### Implementados
- comentário de tabela explicando o papel oficial do vínculo
- comentários nas colunas principais
- destaque para:
  - rastreabilidade
  - ESG
  - Projeto Raízes
  - não armazenamento de dados operacionais/fundiários completos

## 8. Downgrade

### Definido
Sim.

### Ordem
1. remover policies
2. remover `FORCE RLS` / desabilitar RLS
3. remover índices
4. remover tabela

### Observação
- rollback está documentado e a estrutura da migration permite reversão limpa

## 9. Validação

### Validação estática executada
- `py_compile` da migration nova, da merge migration e da migration de avaliações renumerada
- `alembic heads`
- inspeção textual dos arquivos criados

### Resultado de `alembic heads`
```text
add_propriedade_imovel (head)
```

### Validação de banco
- `alembic upgrade head` não pôde ser concluído no ambiente
- `alembic current` também não pôde ser concluído no ambiente

### Motivo
O ambiente retornou:
- `PermissionError: [Errno 1] Operation not permitted`

O erro ocorreu na abertura de conexão do `asyncpg` dentro do `migrations/env.py`, antes de qualquer execução de schema.

## 10. Arquivos alterados

### Criados
- [`services/api/migrations/versions/add_propriedade_imovel.py`](/opt/lampp/htdocs/farm/services/api/migrations/versions/add_propriedade_imovel.py)

### Mantidos para o grafo
- [`services/api/migrations/versions/merge_heads_before_propriedade_imovel.py`](/opt/lampp/htdocs/farm/services/api/migrations/versions/merge_heads_before_propriedade_imovel.py)
- [`services/api/migrations/versions/b1c2d3e4f5a7_add_imoveis_avaliacoes.py`](/opt/lampp/htdocs/farm/services/api/migrations/versions/b1c2d3e4f5a7_add_imoveis_avaliacoes.py)

### Substituído
- [`services/api/migrations/versions/b1c2d3e4f5a6_add_imoveis_avaliacoes.py`](/opt/lampp/htdocs/farm/services/api/migrations/versions/b1c2d3e4f5a6_add_imoveis_avaliacoes.py)

## 11. Respostas objetivas

### 1. Migration foi criada?
Sim.

### 2. Qual revision criada?
`add_propriedade_imovel`

### 3. A migration depende do head consolidado?
Sim. Depende de `merge_heads_before_propriedade_imovel`.

### 4. A tabela `propriedade_imovel` foi definida?
Sim, com campos, constraints, índices, comentários e RLS físico.

### 5. RLS físico foi incluído?
Sim, apenas em `propriedade_imovel`.

### 6. Downgrade foi definido?
Sim.

### 7. Upgrade/downgrade foram testados?
Não no banco, por limitação do ambiente. A validação estática passou.

### 8. Pode avançar para Fase 3 — Backend?
Sim, do ponto de vista da migration e do grafo Alembic.

## Conclusão
A migration real de `propriedade_imovel` foi criada a partir do head consolidado, com RLS físico, check constraint textual para `tipo_vinculo`, constraints de integridade, índices e rollback documentado. O único bloqueio residual foi ambiental, impedindo a conexão com o banco para executar `upgrade/current`.
