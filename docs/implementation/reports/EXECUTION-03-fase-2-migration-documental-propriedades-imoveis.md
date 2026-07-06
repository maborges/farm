# EXECUTION-03 — Fase 2 Migration Alembic em Modo Documental

Data de execução: 2026-06-21

## Escopo executado

Tickets cobertos em modo documental:

- TCK-013 — Criar migration inicial do vínculo
- TCK-014 — Criar tabela `propriedade_imovel`
- TCK-015 — Criar constraints, índices e rollback

Este relatório não cria migration real, não altera `services/api/migrations/versions`, não executa `alembic revision`, não executa `alembic upgrade` e não executa `alembic downgrade`.

---

## 1. Contexto de migrations existentes

### Caminho real das migrations

- As migrations do projeto estão em:
  - `services/api/migrations/versions`

### Verificação de heads e estado atual

- A tentativa de ler o estado do Alembic com o binário do ambiente falhou por limitação do ambiente de execução, sem alterar banco:
  - `PermissionError: [Errno 1] Operation not permitted`
- A leitura de `alembic heads` foi possível e retornou:
  - `b1c2d3e4f5a6` com aviso de revisão duplicada
  - `c3d4e5f6a7b8 (head)`
  - `ff59b3b71a2d (head)`

### Leitura técnica

- O repositório já possui múltiplos heads no grafo de migrations.
- Há aviso de revisão duplicada para `b1c2d3e4f5a6`, o que exige atenção antes de qualquer migration nova.
- A futura migration da convergência deve ser anexada com cuidado ao head correto ou à estrutura consolidada do grafo, evitando produzir mais um head paralelo sem necessidade.

### Migrations relevantes já identificadas

- `imoveis_rurais_init.py`
- `43cdf769d080_fix_imoveis_broken_fks.py`
- `fa37f6f94792_onda1_cadastros_normalizacao.py`
- `c853a6f175f1_add_logo_url_to_unidades_produtivas.py`
- `step1_migrate_talhoes_to_areas_rurais.py`
- `step2_drop_talhoes_legado.py`
- `4e0b633ffb18_onda4_limpeza_final.py`

### Dependências de ordem já compreendidas

- `step1_migrate_talhoes_to_areas_rurais.py` precede `step2_drop_talhoes_legado.py`.
- `step2_drop_talhoes_legado.py` aborta se existirem FKs pendentes para `talhoes`.
- `4e0b633ffb18_onda4_limpeza_final.py` já consolida FKs de talhão para `cadastros_areas_rurais`.
- `c853a6f175f1_add_logo_url_to_unidades_produtivas.py` já consolida a nomenclatura `fazenda_id` para `unidade_produtiva_id`.

### Riscos de conflito

- Risco de criar migration fora do head correto.
- Risco de conflitar com o legado de `talhoes` e com o histórico de `cadastros_areas_rurais`.
- Risco de produzir nova inconsistência se o grafo atual de migrations não for respeitado.
- Risco de múltiplos heads persistirem e dificultarem a inclusão da convergência.

---

## 2. Especificação da tabela futura `propriedade_imovel`

### Nome da tabela

- `propriedade_imovel`

### Schema esperado

- Schema default do projeto, consistente com o restante do domínio atual.
- Não há indicação documental de schema alternativo.

### Finalidade

- Registrar o vínculo oficial entre `Propriedades` e `Imóveis Rurais`.
- Sustentar principalidade, sobreposição, vigência e rastreabilidade do relacionamento.

### Colunas previstas

| Coluna | Tipo esperado | Nullable | Default | Comentário |
|---|---|---:|---|---|
| `id` | UUID | Não | gerado pela aplicação/DB | PK da entidade |
| `tenant_id` | UUID | Não | n/a | Isolamento multi-tenant |
| `propriedade_id` | UUID | Não | n/a | FK para a propriedade operacional |
| `imovel_rural_id` | UUID | Não | n/a | FK para o imóvel rural legal |
| `tipo_vinculo` | enum ou check controlado | Não | n/a | Natureza do vínculo |
| `ativo` | Boolean | Não | `true` | Estado atual do vínculo |
| `data_inicio` | Date/DateTime | Não | n/a | Início da vigência |
| `data_fim` | Date/DateTime | Sim | `NULL` | Fim da vigência |
| `origem_documental` | Text/Varchar | Não | n/a | Base documental do vínculo |
| `observacoes` | Text | Sim | `NULL` | Notas de governança e auditoria |
| `area_vinculada` | Numeric(12,4) | Sim | `NULL` | Área vinculada ao relacionamento |
| `percentual_vinculado` | Numeric(5,2) ou similar | Sim | `NULL` | Percentual associado ao vínculo |
| `vinculo_principal` | Boolean | Sim/Não conforme decisão final | `false` sugerido | Marca de vínculo principal |
| `origem_referencia` | Varchar/Text | Sim | `NULL` | Referência resumida da documentação fonte |
| `status_documental` | Varchar/enum | Sim | `NULL` | Estado de validação documental |
| `created_at` | DateTime/Timestamp | Não | `now()`/equivalente | Auditoria temporal |
| `updated_at` | DateTime/Timestamp | Não | `now()`/equivalente | Auditoria temporal |
| `created_by` | UUID | Sim | `NULL` | Autor da criação |
| `updated_by` | UUID | Sim | `NULL` | Autor da última atualização |

### Observações de modelagem

- `created_by` e `updated_by` foram incluídos como campos operacionais esperados para auditoria, alinhados ao padrão do projeto.
- O tipo exato de `data_inicio` e `data_fim` deve seguir o padrão já usado no domínio de datas do repositório.
- `percentual_vinculado` pode usar precisão decimal de curta escala, suficiente para percentuais de vínculo.

---

## 3. Constraints

### PK

- `pk_propriedade_imovel`

### FKs

- `fk_propriedade_imovel_tenant_id` -> `tenants.id`
- `fk_propriedade_imovel_propriedade_id` -> `propriedades` ou tabela física equivalente do domínio operacional
- `fk_propriedade_imovel_imovel_rural_id` -> `imoveis_rurais.id`

### Unique constraints propostas

- `uq_propriedade_imovel_tenant_propriedade_imovel_vigencia`
- `uq_propriedade_imovel_principal_ativo`

### Check constraints propostas

- `ck_propriedade_imovel_datas_validas`
  - exige `data_fim >= data_inicio` quando `data_fim` não for nula
- `ck_propriedade_imovel_percentual_intervalo`
  - exige `percentual_vinculado` entre `0` e `100`
- `ck_propriedade_imovel_area_nao_negativa`
  - exige `area_vinculada >= 0`
- `ck_propriedade_imovel_tipo_vinculo_valido`
  - restringe `tipo_vinculo` ao enum oficial
- `ck_propriedade_imovel_ativo_booleano`
  - garante semântica clara de estado

### Proteção de vínculo principal ativo

- Deve existir uma regra que impeça mais de um vínculo principal ativo por propriedade em uma mesma vigência.
- A implementação pode ser feita por unique parcial, constraint condicional ou combinação de check + índice parcial, desde que a semântica final seja garantida.

### Observação

- A proposta acima é documental e não executável.
- A escolha do mecanismo físico final deve respeitar a capacidade real do banco e o padrão do projeto.

---

## 4. Índices

### Índices esperados

| Índice | Classificação | Objetivo |
|---|---|---|
| `ix_propriedade_imovel_tenant_id` | Obrigatório | Filtragem por tenant |
| `ix_propriedade_imovel_propriedade_id` | Obrigatório | Busca por propriedade |
| `ix_propriedade_imovel_imovel_rural_id` | Obrigatório | Busca por imóvel rural |
| `ix_propriedade_imovel_tenant_propriedade` | Obrigatório | Busca combinada de tenant + propriedade |
| `ix_propriedade_imovel_tenant_imovel` | Obrigatório | Busca combinada de tenant + imóvel |
| `ix_propriedade_imovel_tipo_vinculo` | Recomendado | Filtragem por natureza do vínculo |
| `ix_propriedade_imovel_ativo` | Recomendado | Filtragem por vínculos vigentes |
| `ix_propriedade_imovel_data_inicio` | Recomendado | Consultas temporais e histórico |
| `ix_propriedade_imovel_data_fim` | Recomendado | Consultas temporais e histórico |
| `ix_propriedade_imovel_vinculo_principal` | Recomendado | Consultas sobre principalidade |

### Classificação

- **Obrigatório**
  - tenant, propriedade, imóvel e índices compostos de lookup
- **Recomendado**
  - filtros por tipo, ativo e vigência
- **Futuro**
  - índices adicionais de auditoria ou materialized views, se houver escala real de uso

---

## 5. RLS físico esperado

### Especificação

- A tabela futura `propriedade_imovel` deve possuir `tenant_id` direto.
- A tabela deve ter `ENABLE ROW LEVEL SECURITY`.
- A tabela deve ter `FORCE ROW LEVEL SECURITY`.
- A política deve usar `app.current_tenant_id`.

### Cobertura de políticas

- `CREATE POLICY` para `SELECT`
- `CREATE POLICY` para `INSERT`
- `CREATE POLICY` para `UPDATE`
- `CREATE POLICY` para `DELETE`

### Política única ou separada

- Recomendação documental: **políticas separadas por operação**.
- Justificativa:
  - clareza de auditoria;
  - facilidade de diagnóstico;
  - menor risco de regras permissivas acidentais;
  - leitura explícita do que cada operação pode fazer.

### Tratamento de `app.current_tenant_id` ausente

- Se `app.current_tenant_id` estiver ausente, a política deve negar acesso.
- O comportamento esperado é fail-closed, nunca fail-open.

### Como impedir escrita cross-tenant

- Comparar `tenant_id` da linha com `current_setting('app.current_tenant_id')::uuid`.
- Negar `INSERT` e `UPDATE` quando o tenant da sessão não coincidir.
- Impedir `DELETE` fora do tenant.

### Especificação resumida

- A política física deve ser rígida, explícita e não permissiva.
- O objetivo é impedir qualquer acesso cross-tenant mesmo se a camada de aplicação falhar.

---

## 6. Upgrade / Downgrade planejado

### Upgrade documental previsto

1. Criar enum ou check constraint para `tipo_vinculo`.
2. Criar a tabela `propriedade_imovel`.
3. Criar FKs e constraints.
4. Criar índices.
5. Aplicar RLS físico.
6. Aplicar comentários de schema e colunas.

### Downgrade documental previsto

1. Remover policies.
2. Remover `FORCE ROW LEVEL SECURITY`.
3. Remover `ENABLE ROW LEVEL SECURITY` associado ao objeto.
4. Remover índices.
5. Remover constraints.
6. Remover tabela.
7. Remover enum, se o enum tiver sido criado exclusivamente para a migration.

### Observação

- O rollback deve ser desenhado para não apagar o histórico da especificação de negócio.
- Caso o enum seja reaproveitado em outro lugar, o downgrade não deve removê-lo indevidamente.

---

## 7. Riscos de migration

### Risco de schema `farms`

- Risco baixo a médio, dependendo de onde a implementação física será ancorada.
- A modelagem atual usa nomes consolidados como `unidades_produtivas`, `imoveis_rurais` e `cadastros_areas_rurais`, então a futura migration deve respeitar essa taxonomia e não reintroduzir alias antigos sem necessidade.

### Risco de enum PostgreSQL versus check constraint

- Enum PostgreSQL:
  - mais rígido;
  - melhor semântica de domínio;
  - maior custo de alteração futura.
- Check constraint:
  - mais flexível;
  - pode ser mais fácil de evoluir;
  - exige disciplina para não virar regra frouxa.

### Risco de RLS sem policy

- Alto.
- Uma tabela sem policy física pode ficar protegida apenas por contrato de aplicação.

### Risco de FKs legadas

- Alto.
- O legado em `cadastros_areas_matriculas`, `cadastros_areas_registros_ambientais` e outras estruturas territoriais pode conflitar com a nova tabela se a migração não respeitar a direção da verdade.

### Risco de rollback

- Alto se o downgrade for incompleto.
- A remoção parcial de RLS, índices ou constraints pode deixar o banco em estado inconsistente.

### Risco de dados históricos

- Alto.
- A convergência deve preservar histórico de vínculos encerrados e não pode quebrar a auditabilidade.

### Risco de dados duplicados

- Alto.
- Enquanto a duplicidade fundiária existir em Propriedades e Imóveis Rurais, a migration precisa nascer preparada para convivência temporária e migração progressiva.

---

## 8. Conclusão documental

### A migration real pode ser criada agora?

- **Não.**

### O desenho da tabela está completo?

- **Sim, para revisão humana e planejamento técnico.**

### As constraints estão claras?

- **Sim.**

### Os índices estão claros?

- **Sim.**

### A estratégia de RLS físico está clara?

- **Sim, em nível documental.**

### O rollback está claro?

- **Sim, em nível documental.**

### Quais bloqueios ainda impedem execução técnica?

- Worktree ainda não está limpo.
- RLS físico ainda não foi formalizado nas migrations do banco.
- A duplicidade fundiária ainda está em fase de convivência e precisa de controle durante a transição.
- Os múltiplos heads do Alembic precisam ser tratados com cuidado antes de adicionar nova revisão.
- A migration real ainda não foi autorizada para execução.

---

## 9. Resumo executivo

- A Fase 2 documental está pronta para revisão humana.
- A especificação da futura migration foi detalhada o suficiente para virar tarefa técnica quando os bloqueios de base forem resolvidos.
- A criação real da migration ainda deve aguardar a limpeza do worktree, a formalização física de RLS e o controle da duplicidade fundiária.

