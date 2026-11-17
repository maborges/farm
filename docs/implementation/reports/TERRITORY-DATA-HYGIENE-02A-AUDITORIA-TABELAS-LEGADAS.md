# TERRITORY-DATA-HYGIENE-02A - Auditoria de Tabelas Legadas no Contexto de Propriedades e Imóveis Rurais

## 1. Resumo Executivo

A auditoria confirmou que `configuracao_fazenda` não é uma tabela morta: ela segue com leitura e gravação em runtime pelo backend administrativo de configurações por UP. Ao mesmo tempo, a tabela está vazia no banco auditado, não possui políticas RLS e carrega uma nomenclatura histórica de "fazenda" que já não coincide com o modelo oficial de `UnidadeProdutiva`.

O único artefato físico adicional confirmado no contexto foi `territory_legacy_backup_01h2`, criado explicitamente pela migration de remoção física de colunas territoriais como backup de downgrade. Esse objeto não tem consumidor runtime e deve ser tratado como backup temporário, não como legado operacional.

Conclusão prática:

- `configuracao_fazenda` é um candidato a depreciação controlada, mas não pode ser removida agora.
- `territory_legacy_backup_01h2` é backup temporário de migração, sem uso em runtime.
- Não há evidência suficiente para iniciar remoção controlada do conjunto territorial auditado.

## 2. Ambiente

- Banco: `farms`
- Schema auditado: `farms`
- Conexão usada para a auditoria física: `postgresql+asyncpg://borgus:***@192.168.0.3/farms`
- PostgreSQL real com RLS usado como base da auditoria
- Nenhuma alteração de código foi feita nesta fase

## 3. Schema Auditado

Inventário físico do schema `farms` revelou, entre outras, as seguintes estruturas relevantes para esta auditoria:

- `configuracao_fazenda`
- `territory_legacy_backup_01h2`
- `cadastros_propriedades`
- `cadastros_exploracoes_rurais`
- `propriedade_imovel`
- `imoveis_rurais`
- `imoveis_cartorios`
- `imoveis_matriculas`
- `cadastros_areas_rurais`
- `cadastros_areas_registros_ambientais`
- `cadastros_areas_valores_patrimoniais`

Outras tabelas de apoio encontradas no schema foram avaliadas, mas não houve evidência suficiente para classificá-las como legado operacional no contexto territorial.

## 4. Análise de `configuracao_fazenda`

### Evidência de runtime

`configuracao_fazenda` é consumida pelo backend em:

- [services/api/core/models/configuracao_fazenda.py](/opt/lampp/htdocs/farm/services/api/core/models/configuracao_fazenda.py)
- [services/api/core/services/configuracoes_service.py](/opt/lampp/htdocs/farm/services/api/core/services/configuracoes_service.py)
- [services/api/core/routers/configuration.py](/opt/lampp/htdocs/farm/services/api/core/routers/configuration.py)

Os trechos relevantes mostram:

- model ORM `ConfiguracaoFazenda`
- leitura em `get_configuracao_fazenda(...)`
- gravação em `set_override_fazenda(...)`
- rotas `GET /config/fazenda/{unidade_produtiva_id}` e `PUT /config/fazenda/{unidade_produtiva_id}`

### Conclusão funcional

- `configuracao_fazenda` é usada no runtime? **SIM**
- `configuracao_fazenda` recebe gravações? **SIM**
- `configuracao_fazenda` possui dados exclusivos? **NÃO**
- `configuracao_fazenda` pode ser removida? **NÃO**

### Leitura do contexto histórico

A nomenclatura ainda carrega o legado de `fazenda`, mas o payload e o vínculo já operam com `unidade_produtiva_id`. Isso indica resíduo semântico de migração, não abandono funcional.

## 5. Estrutura Física de `configuracao_fazenda`

### Colunas

| Coluna | Tipo | Nullable | Default | Conceito |
| --- | --- | --- | --- | --- |
| `id` | `uuid` | Não | none | PK surrogate |
| `unidade_produtiva_id` | `uuid` | Não | none | vínculo com a UP |
| `tenant_id` | `uuid` | Não | none | escopo multi-tenant |
| `overrides` | `json` | Não | `'{}'` | overrides por UP |
| `updated_at` | `timestamptz` | Não | `now()` | timestamp de atualização |

### Constraints e índices

- PK: `configuracao_fazenda_pkey`
- FK: `configuracao_fazenda_fazenda_id_fkey` -> `unidades_produtivas.id`
- FK: `configuracao_fazenda_tenant_id_fkey` -> `tenants.id`
- Índice único: `ix_configuracao_fazenda_unidade_produtiva_id`
- Índice: `ix_configuracao_fazenda_tenant_id`

### RLS / policies / triggers / comments

- RLS habilitado na tabela? **NÃO**
- Policies encontradas? **NÃO**
- Triggers encontradas? **NÃO**
- Comentário de tabela? **NÃO**

## 6. Dados Existentes

Contagens auditadas:

- total de registros: `0`
- registros ativos: `0`
- registros soft-deleted: `N/A` (a tabela não possui `deleted_at`)
- registros por tenant: nenhum
- registros órfãos: `0`
- registros sem tenant: `0`
- registros duplicados: nenhum
- última criação: `N/A` (sem linhas)
- última atualização: `N/A` (sem linhas)

Observação:

- a tabela não possui coluna `deleted_at`
- a ausência de linhas elimina a necessidade de backfill para eventual remoção, mas não elimina o risco funcional porque há consumidores runtime ativos

## 7. Fluxos de Escrita

Classificação: `ACTIVE_WRITE`

Evidências:

- `ConfiguracoesService.set_override_fazenda(...)` cria ou atualiza `ConfiguracaoFazenda` e faz `commit()`
- `configuration.py` expõe `PUT /config/fazenda/{unidade_produtiva_id}`

Origem do payload:

- payload de `ConfiguracaoFazendaUpdate`
- corpo `overrides: Dict[str, Any]`

Momento:

- operação administrativa de override por UP

Transação:

- commit feito na camada de service

Consumidor posterior:

- leitura posterior pela própria rota `GET /config/fazenda/{unidade_produtiva_id}`

## 8. Fluxos de Leitura

Classificação: `ACTIVE_RUNTIME_READ`

Evidências:

- `ConfiguracoesService.get_configuracao_fazenda(...)`
- `GET /config/fazenda/{unidade_produtiva_id}`

Não foram encontrados consumidores em frontend web, Campo PWA, workers ou integrações além do backend administrativo e documentação.

## 9. Dependências

### Entradas da tabela

- `tenant_id` -> `tenants.id`
- `unidade_produtiva_id` -> `unidades_produtivas.id`

### Saídas / dependentes

- nenhuma policy
- nenhum trigger
- nenhuma view/materialized view dependente encontrada
- nenhuma função/procedure dependente encontrada

### RLS

- a tabela depende de filtro de tenant na aplicação, não de RLS do PostgreSQL

## 10. Matriz de Campos

| Campo em `configuracao_fazenda` | Conceito | Fonte oficial atual | Duplicado? | Divergências | Consumidores |
| --- | --- | --- | --- | --- | --- |
| `id` | identificador técnico | não há equivalente funcional | Não | sem divergência | backend admin |
| `unidade_produtiva_id` | escopo do override por UP | `UnidadeProdutiva` | Não | nome histórico ainda usa "fazenda" em rotas/modelo | service/router de configuração |
| `tenant_id` | isolamento multi-tenant | `Tenant` | Não | nenhuma | service/router de configuração |
| `overrides` | overrides genéricos por UP | não há campo oficial equivalente normalizado | Não | JSON livre, não normalizado | service/router de configuração |
| `updated_at` | auditoria técnica | timestamps oficiais do modelo | Não | sem `created_at` na tabela | runtime administrativo |

## 11. Divergências de Dados

Como a tabela está vazia, não foi possível observar divergência entre valores de `configuracao_fazenda` e estruturas oficiais.

Classificação:

- `SEM_EQUIVALENTE_OFICIAL`: `overrides`
- `DIVERGENTE_DO_OFICIAL`: não observado
- `PARCIALMENTE_DUPLICADO`: não observado
- `ORFAO`: não observado
- `SEM_CONSUMIDOR`: não, há consumidor runtime

## 12. Outras Tabelas Suspeitas

### Confirmadas como backup técnico

- `territory_legacy_backup_01h2`
  - criado pela migration [services/api/migrations/versions/265b28773962_territory_convergence_remove_legacy_.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/265b28773962_territory_convergence_remove_legacy_.py)
  - contém 717 linhas
  - sem consumos runtime encontrados
  - sem FKs/policies/triggers
  - finalidade: downgrade e preservação operacional da remoção física

### Inspecionadas e não classificadas como legado operacional

- `cadastros_propriedades`
- `cadastros_exploracoes_rurais`
- `propriedade_imovel`
- `imoveis_rurais`
- `imoveis_cartorios`
- `imoveis_matriculas`
- `cadastros_areas_rurais`
- `cadastros_areas_registros_ambientais`
- `cadastros_areas_valores_patrimoniais`
- `imoveis_arrendamentos`
- `imoveis_arrendamento_parcelas`
- `imoveis_arrendamento_reajustes`
- `pec_piquetes`
- `safra_talhao_grupos`
- `safra_talhao_grupo_itens`

Essas estruturas têm função de domínio ou apoio e não foram tratadas como legado apenas por nome.

## 13. Models sem Tabela

Foram observados modelos sem correspondência física direta no inventário do schema `farms`, especialmente em módulos adjacentes ao território, como carbono e automação.

Exemplos confirmados no comparativo de diretórios de models:

- `carbono_emissoes`
- `carbono_projetos`
- `carbono_relatorios`

Classificação:

- `MÓDULO_OPCIONAL`

Observação:

- parte do inventário automático também aponta inconsistências de nomenclatura em módulos que não são territoriais; isso deve ser auditado separadamente antes de qualquer remoção

## 14. Tabelas sem Model

Confirmadas:

- `territory_legacy_backup_01h2` -> `BACKUP_TEMPORÁRIO`
- `alembic_version` -> sistema / infraestrutura

Não houve evidência suficiente para afirmar que exista outra tabela territorial legada sem model ORM no escopo desta auditoria.

## 15. Backups e Staging

### `territory_legacy_backup_01h2`

- finalidade: preservar colunas legadas removidas pela migration `265b28773962`
- runtime acessa? **NÃO**
- política de retenção: preservar até decisão formal de descarte
- pode ser removida agora? **NÃO**
- dependência de downgrade: **SIM**

### `alembic_version`

- tabela técnica de versão de migrations
- não é estrutura de domínio

## 16. Classificação Final

| Estrutura | Classificação | Motivo |
| --- | --- | --- |
| `configuracao_fazenda` | `LEGADO_ATIVO` | nome histórico + consumidor runtime ativo + tabela vazia |
| `territory_legacy_backup_01h2` | `BACKUP_TEMPORÁRIO` | backup explícito da migration de remoção física |
| `alembic_version` | `NÃO_CONFIRMADO` | infraestrutura, fora do domínio |

## 17. Candidatos à Remoção

Nenhum candidato foi considerado seguro para remoção imediata.

Motivos:

- `configuracao_fazenda` ainda é usada no runtime
- `territory_legacy_backup_01h2` é backup técnico com papel de downgrade/retensão

## 18. Candidatos Bloqueados

- `configuracao_fazenda`
  - bloqueado por consumidor runtime ativo
  - bloqueado por ausência de evidência de migração dos consumidores
- `territory_legacy_backup_01h2`
  - bloqueado por ser artefato de backup/downgrade

## 19. Riscos

- nomenclatura histórica "fazenda" ainda exposta no backend de configuração
- ausência de RLS físico em `configuracao_fazenda`
- ausência de dados não equivale a ausência de consumo
- inventário de models fora do escopo territorial pode gerar falsos positivos e exige auditoria separada

## 20. Plano Recomendado

1. Manter `configuracao_fazenda` enquanto houver consumidor runtime.
2. Adicionar observabilidade e um teste de inventário para impedir novos consumidores do nome legado.
3. Definir política formal de retenção para `territory_legacy_backup_01h2`.
4. Separar, em auditoria própria, os modelos sem tabela dos módulos carbono/ambiental que não pertencem ao escopo territorial.
5. Só propor remoção de tabela após migração completa de leitura/escrita e confirmação de zero dependências.

## 21. Veredicto

Não há evidência suficiente para iniciar uma remoção controlada do conjunto auditado.

Respostas obrigatórias:

- `configuracao_fazenda` é usada no runtime? **SIM**
- `configuracao_fazenda` recebe gravações? **SIM**
- `configuracao_fazenda` possui dados exclusivos? **NÃO**
- `configuracao_fazenda` pode ser removida? **NÃO**

- Outras tabelas legadas encontradas? **SIM**
- Existem tabelas sem model? **SIM**
- Existem models sem tabela? **SIM**
- Há duplicidade de fonte de verdade? **NÃO**
- É necessário backfill? **NÃO**
- É seguro iniciar remoção? **NÃO**

NO-GO
