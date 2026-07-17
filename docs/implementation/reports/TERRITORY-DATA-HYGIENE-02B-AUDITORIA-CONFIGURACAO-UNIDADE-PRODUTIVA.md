# TERRITORY-DATA-HYGIENE-02B - Auditoria Funcional de Configurações por Unidade Produtiva

## 1. Resumo Executivo

A auditoria confirmou que `configuracao_fazenda` continua ativa em runtime no backend, com contrato exposto por `GET /config/fazenda/{unidade_produtiva_id}` e `PUT /config/fazenda/{unidade_produtiva_id}`. O objeto físico existe no schema `farms`, o model ORM existe e a camada de serviço persiste registros com `commit()` interno.

Ao mesmo tempo, a tabela está vazia no ambiente auditado, não foram encontrados consumidores reais no frontend web, no Campo PWA, em workers, integrações ou relatórios, e nenhuma chave de `overrides` foi comprovada como interpretada funcionalmente por outro módulo. A auditoria funcional isolada também mostrou que a camada atual aceita gravação de `overrides` genérico sem schema e sem validação de ownership da UP.

Conclusão técnica:

- existe runtime backend ativo;
- não existe uso operacional comprovado;
- o JSON `overrides` é um bucket genérico sem governança de contrato;
- a segurança multi-tenant é insuficiente porque um tenant consegue gravar override para UP de outro tenant se souber o ID;
- o nome `fazenda` é um resíduo semântico legado frente ao domínio oficial `UnidadeProdutiva`.

Classificação final:

- `DEPRECAR_E_OBSERVAR`

Próxima ação recomendada:

- bloquear novos consumidores sem contrato tipado;
- adicionar validação explícita de ownership da UP;
- introduzir RLS e teste PostgreSQL real antes de qualquer consolidação ou renomeação;
- observar uso real antes de decidir `RENOMEAR_E_MIGRAR`.

## 2. Contrato Atual

Arquivos auditados:

- [services/api/core/models/configuracao_fazenda.py](/opt/lampp/htdocs/farm/services/api/core/models/configuracao_fazenda.py)
- [services/api/core/services/configuracoes_service.py](/opt/lampp/htdocs/farm/services/api/core/services/configuracoes_service.py)
- [services/api/core/routers/configuration.py](/opt/lampp/htdocs/farm/services/api/core/routers/configuration.py)
- [services/api/core/schemas/config_schemas.py](/opt/lampp/htdocs/farm/services/api/core/schemas/config_schemas.py)
- [services/api/core/dependencies.py](/opt/lampp/htdocs/farm/services/api/core/dependencies.py)

### Modelo de entrada

- `ConfiguracaoFazendaUpdate`
- corpo: `overrides: Dict[str, Any]`

### Modelo de saída

- `ConfiguracaoFazendaResponse`
- campos: `unidade_produtiva_id`, `overrides`

### Comportamento funcional

- `GET` sem registro retorna defaults com `overrides = {}`
- `PUT` cria ou atualiza a linha
- `set_override_fazenda(...)` faz substituição integral do JSON, não merge
- há `commit()` dentro do service
- não há validação de schema para as chaves do JSON
- não há validação explícita de ownership da UP antes da gravação

### Origem do `tenant_id`

- vem do contexto autenticado via dependência de tenant
- não vem do payload
- o router e o service filtram por `tenant_id`, mas não validam a pertença da UP ao tenant

### Tratamento de concorrência

- não foi identificado controle otimista
- não há histórico
- não há mecanismo de versionamento
- o JSON é sobrescrito em atualização

## 3. Chaves de Overrides

Busca em backend, frontend, Campo, packages, scripts, testes e docs não revelou contrato tipado efetivo para `overrides`.

Chave observada em documentação e no experimento controlado:

| Chave | Tipo esperado | Quem grava | Quem lê | Efeito funcional | Validada? |
| --- | --- | --- | --- | --- | --- |
| `fuso_horario` | string | backend administrativo | nenhum consumidor funcional comprovado | persistência de texto | Não |
| `tema` | string arbitrária | backend administrativo | nenhum consumidor funcional comprovado | persistência de texto | Não |

Classificação:

- `ARMAZENAMENTO_SEM_CONSUMIDOR_FUNCIONAL`

Não foi encontrada interpretação funcional consistente de chaves no runtime. O JSON aceita valores arbitrários e apenas os persiste.

## 4. Consumidores

### Consumidores reais encontrados

| Arquivo / módulo | Tipo | Evidência |
| --- | --- | --- |
| `services/api/core/services/configuracoes_service.py` | `INTERNAL_RUNTIME` | leitura e gravação da entidade |
| `services/api/core/routers/configuration.py` | `INTERNAL_RUNTIME` | expõe GET e PUT no runtime |
| `services/api/core/models/configuracao_fazenda.py` | `INTERNAL_RUNTIME` | model ORM ativo |

### Consumidores não encontrados

- frontend web runtime: não encontrado
- Campo PWA: não encontrado
- workers: não encontrado
- integrações: não encontrado
- relatórios/BI: não encontrado
- testes representativos: não encontrado

Classificação geral dos consumidores:

- `INTERNAL_RUNTIME` existe
- `ACTIVE_CLIENT` não comprovado
- `TEST_ONLY` não encontrado
- `DOC_ONLY` existe em documentação, mas sem prova funcional

## 5. Tráfego Real

Não foi localizada base histórica confiável de tráfego operacional para este contrato.

Verificações realizadas:

- não foi encontrado log persistido de API no banco auditado;
- `pg_stat_statements` não estava disponível para a auditoria;
- não foi encontrado histórico observável de chamadas às rotas `/config/fazenda/...`;
- não houve consumidor frontend identificado durante a busca no repositório.

Classificação:

- `USO_OPERACIONAL_NAO_COMPROVADO`

## 6. Persistência

Arquivo principal:

- [services/api/core/services/configuracoes_service.py](/opt/lampp/htdocs/farm/services/api/core/services/configuracoes_service.py)

### Observações

- cria registro se não existir;
- atualiza o registro existente;
- substitui o JSON inteiro;
- permite chaves desconhecidas;
- faz `commit()` interno;
- faz `refresh()` após persistir;
- não há histórico de alterações;
- não há soft delete;
- não há controle de versão;
- não há proteção contra lost update;
- não há validação de schema;
- não há checagem explícita de vínculo UP/tenant.

### Riscos identificados

- `LOST_UPDATE`
- `JSON_SEM_SCHEMA`
- `OVERRIDE_DESCONTROLADO`
- `SEM_HISTORICO`
- `SEM_AUDITORIA`
- `SEM_RLS`
- `COMMIT_INTERNO`

### Experimento controlado

Em PostgreSQL real, com tenant isolado de teste:

- `GET` sem registro retornou ausência de linha;
- `PUT` criou a linha com sucesso;
- `PUT` posterior substituiu o JSON e removeu a chave anterior;
- gravação para UP de outro tenant foi aceita pelo service, evidenciando lacuna de ownership.

## 7. Multi-Tenancy

### Origem do tenant

- `tenant_id` vem do contexto autenticado da requisição.

### Validações presentes

- existe filtro por `tenant_id` na busca;
- existe FK para `tenants.id`;
- existe índice único por `unidade_produtiva_id`.

### Validações ausentes

- não há validação explícita de que a UP pertence ao tenant corrente antes de gravar;
- não há RLS na tabela;
- não há política de banco para reforçar o isolamento;
- não há prova de bloqueio contra enumeração de UP por ID.

### Conclusão de segurança

- a segurança multi-tenant é **insuficiente** para este contrato no estado atual
- a presença de FK e índice único não compensa a falta de ownership validation

## 8. RLS

Situação física da tabela:

- RLS habilitado? `NÃO`
- policies encontradas? `NÃO`

Conclusão:

- RLS é necessária? `SIM`

Motivo:

- o contrato grava dados por UP e por tenant;
- a aplicação sozinha não impediu gravação cruzada no experimento controlado;
- o padrão da plataforma exige defesa em profundidade.

## 9. Semântica

### Interpretação funcional provável

O contrato parece representar uma configuração administrativa por Unidade Produtiva, mas isso não foi comprovado por consumidor funcional real. O nome da tabela ainda preserva a semântica de `fazenda`, enquanto o modelo operacional oficial do domínio é `UnidadeProdutiva`.

### Classificação semântica

- `LEGITIMATE_UP_CONFIGURATION` como conceito de negócio potencial
- `GENERIC_CONFIGURATION_BUCKET` como implementação atual
- `UNDEFINED_DOMAIN` para consumo real comprovado

### Conclusão

- o conceito pertence à UP? `SIM`, semanticamente
- a implementação atual já é segura e consolidada? `NÃO`

## 10. Comparação com Configurações Oficiais

Foram procurados equivalentes em:

- `tenant_configuracoes`
- `configuracoes`
- `settings`
- `preferences`
- feature flags
- integration settings
- module settings
- thresholds de alertas e recomendações

Resultado:

- não foi encontrado mecanismo oficial tipado que substitua este bucket genérico por UP;
- `overrides` não se mostrou equivalente a configuração oficial normalizada;
- não há evidência de duplicidade funcional comprovada com outro mecanismo.

| Conceito | `configuracao_fazenda` | Fonte alternativa | Duplicidade? |
| --- | --- | --- | --- |
| Configuração por UP | sim, em tese | não comprovada | Não comprovada |
| Configuração de tenant | não | `tenant_configuracoes` e afins | Não |
| Flags de módulo | não | feature flags / module settings | Não |

## 11. Testes

### Estado da cobertura

Não foram encontrados testes dedicados para:

- `GET /config/fazenda/{unidade_produtiva_id}`
- `PUT /config/fazenda/{unidade_produtiva_id}`
- `get_configuracao_fazenda(...)`
- `set_override_fazenda(...)`
- concorrência
- tenant divergente
- persistência PostgreSQL real

### Classificação

- `COBERTURA_AUSENTE`

### Consequência

Os testes existentes não provam o contrato funcional nem a segurança multi-tenant deste mecanismo.

## 12. Cenários PostgreSQL

### Cenário A - GET sem configuração

- contrato real observado: `200` com defaults no router, ausência de linha no service
- defaults retornados: `overrides = {}`

### Cenário B - PUT com override válido

- cria linha com sucesso
- grava valores em `overrides`

### Cenário C - PUT repetido

- comportamento observado: replace do JSON
- chaves anteriores são perdidas quando não reenviadas

### Cenário D - tenant divergente

- comportamento observado: escrita aceita em UP de outro tenant se o ID é conhecido
- classificação: falha de ownership

### Cenário E - chave desconhecida

- comportamento observado: aceita e persiste
- classificação: `JSON_SEM_SCHEMA`

### Cenário F - concorrência

- não foi comprovado controle contra lost update
- o contrato não possui proteção explícita observada

## 13. Riscos

- gravação cruzada entre tenants por falta de validação de ownership
- bucket JSON sem schema nem governança
- substituição total do JSON em updates
- ausência de RLS
- ausência de histórico/auditoria
- nomenclatura legado `fazenda` confunde o domínio atual
- inexistência de consumidores funcionais comprovados fora do backend

## 14. Decisão de Nomenclatura

Situação atual:

- `ConfiguracaoFazenda`
- `configuracao_fazenda`
- `/config/fazenda/{id}`
- `get_configuracao_fazenda`
- `set_override_fazenda`

Conclusão:

- o nome atual é legível dentro do legado histórico, mas não é a melhor representação do domínio oficial
- a direção recomendada, caso a funcionalidade seja consolidada futuramente, é migrar para nomenclatura de Unidade Produtiva

Destino recomendado em caso de migração:

- `ConfiguracaoUnidadeProdutiva`
- `configuracao_unidade_produtiva`
- `/config/unidades-produtivas/{id}`
- `get_configuracao_unidade_produtiva`
- `set_configuracao_unidade_produtiva`

## 15. Classificação Final

Escolha única:

- `DEPRECAR_E_OBSERVAR`

Motivos:

- existe runtime backend ativo;
- não há uso operacional comprovado;
- não há consumidor funcional real fora do backend;
- o JSON não possui schema;
- a segurança multi-tenant não é suficiente;
- o nome é legado, mas a remoção ainda não é segura porque o contrato existe e aceita gravação.

## 16. Plano Recomendado

1. bloquear novos consumidores até existir contrato tipado;
2. adicionar validação explícita de ownership da UP antes de gravar;
3. introduzir RLS na tabela;
4. criar testes PostgreSQL reais para GET, PUT, tenant divergente e concorrência;
5. observar uso real por um período definido;
6. se houver adoção comprovada, planejar renomeação e migração;
7. se não houver adoção comprovada e o contrato continuar sem uso, preparar depreciação formal.

## 17. Veredicto

**NO-GO**

Motivo:

- há runtime backend, mas não há evidência suficiente de uso funcional real;
- o contrato é genérico e sem schema;
- a segurança multi-tenant é insuficiente;
- não há base operacional para consolidar ou remover com segurança neste momento.

### Respostas obrigatórias

- Há consumidor funcional real? **SIM**
- Há chaves interpretadas por módulos? **NÃO**
- Há uso operacional comprovado? **NÃO**
- O JSON possui schema? **NÃO**
- A segurança multi-tenant é suficiente? **NÃO**
- RLS é necessária? **SIM**
- O conceito pertence à UP? **SIM**
- A nomenclatura fazenda é legada? **SIM**
- Classificação final: **DEPRECAR_E_OBSERVAR**
- Próxima ação: **Adicionar ownership validation, RLS e teste PostgreSQL real antes de decidir renomeação ou remoção**
