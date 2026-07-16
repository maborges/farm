# ERP-DATA-HYGIENE-01C — Planejamento Executivo da Modernização do Provider Sankhya

## 1. Resumo Executivo
O presente documento detalha o planejamento executivo para a eliminação da dependência operacional do runtime Sankhya em relação à estrutura ORM `SankhyaConfig`. Baseado nas descobertas da fase 01B, propõe-se uma migração incremental em 9 etapas. O runtime passará a consumir entidades canônicas do Core ERP, tais como `TenantIntegracao` e `IntegrationCredential`, sem introduzir novas tabelas, garantindo segurança operacional, compatibilidade temporária controlada, e a abolição progressiva das leituras e gravações no modelo legado.

## 2. Premissas
- O Core ERP é considerado maduro, agnóstico e imutável neste escopo.
- Não serão criadas novas tabelas, adapters ou rotas nesta transição.
- O planejamento deve priorizar estabilidade e prever fallbacks explícitos antes do encerramento final do modelo legado.
- A migração será realizada com o provider Sankhya ativo e operante.

## 3. Estado Atual
No estado atual, o runtime do provider Sankhya depende do model ORM `SankhyaConfig`, o qual agrupa:
- **Configuração Técnica:** URLs base e de autenticação, e environment.
- **Credenciais:** Múltiplos modelos de autenticação (OAuth Gateway e legados) concentrados na mesma tabela.
- **Lifecycle & Health:** Status ativo da integração, data do último teste e seu resultado.
- **Políticas e Sincronização:** Intervalos de polling e data da última sincronização bem-sucedida.

*Arquitetura*:
```text
SankhyaRuntime -> SankhyaConfig
```

## 4. Estado Arquitetural Desejado
O provider consumirá estruturas canônicas.
```text
SankhyaRuntime
        ↓
TenantIntegracao
        ├── IntegrationCredential
        ├── IntegrationFeature
        ├── IntegrationSyncPolicy
        ├── IntegrationHealth
        ├── IntegrationJob
        └── IntegrationVersion
```

## 5. Inventário dos Consumidores
- `SankhyaGatewayAuthService`
- `SankhyaSyncService`
- `SankhyaWSClient`
- `SankhyaNFeFinanceiroService`
- `SankhyaCanonicalAdapter`
- Endpoints (routers)
- Workers/schedulers de sincronização
- Testes unitários e de integração

## 6. Matriz de Criticidade (Consumidores)

| Consumidor | Dependência atual | Criticidade | Estrutura de destino | Fase de migração | Testes necessários | Risco principal |
| ---------- | ----------------- | ----------- | -------------------- | ---------------- | ------------------ | --------------- |
| `SankhyaWSClient` | Config técnica (URLs) | Média | `TenantIntegracao.config_data` | 01E | Teste de conexão, intercept de base URL | Quebra de integração com APIs do provider |
| `SankhyaGatewayAuthService` | Credenciais, login urls | Alta | `IntegrationCredential` | 01F | Testes OAuth/Legacy login, Mock do gateway | Interrupção total de acesso para todos os tenants |
| Endpoints / Lifecycle | Flag `ativo` | Baixa | `TenantIntegracao.status` | 01G | Validação de ativação via painel | Desabilitar integrações ativas indevidamente |
| Monitoramento de Health | `ultimo_teste`, `teste_status` | Baixa | `IntegrationHealth` | 01G | Verificação de painel/status | Perda visual de conexão no painel |
| Schedulers/Workers | `sync_interval`, `ultimo_sync` | Alta | `IntegrationSyncPolicy`, `IntegrationJob` | 01H / 01I | Testes de polling e dispatch de jobs | Jobs de sincronização deixarem de rodar |
| `SankhyaSyncService` (Geral) | Todas as variáveis p/ injeção | Alta | Instâncias canônicas | 01E a 01J | Testes E2E e unitários de sync (pessoas/produtos) | Corrupção de dados ou quebra global do runtime |
| `SankhyaCanonicalAdapter` | Leitura (para migração) e Escrita | Média | N/A (será a fonte primária de migração temporária) | 01K | Testes do adapter sem fallback | Regressão na persistência de credenciais novas |

## 7. Ordem Detalhada das Fases

### ERP-DATA-HYGIENE-01D — Contrato interno de dados do provider
- **Objetivo:** Definir DTOs locais (se necessário, sem criar novas estruturas globais) e adaptar as chamadas das funções principais para receber DTOs ou Models Canônicos diretamente, em vez de um objeto `SankhyaConfig`.
- **Atuação:** Refatorar construtores do `auth_service` e clients, desacoplando-os do ORM legado.

### ERP-DATA-HYGIENE-01E — Leitura canônica de configuração técnica
- **Objetivo:** Substituir a leitura de `api_base_url`, `auth_url`, `environment` por dados oriundos do `TenantIntegracao.config_data`.
- **Precedência:** Canônico. Mantém-se fallback e gravação dupla ativados.

### ERP-DATA-HYGIENE-01F — Leitura canônica de credenciais
- **Objetivo:** Utilizar dados criptografados e mascarados da tabela `IntegrationCredential` para Auth Gateway e WS Básico.
- **Regras:** Mapear `client_id`, `client_secret`, etc. Não realizar fallback silencioso caso a credencial canônica não seja encontrada.

### ERP-DATA-HYGIENE-01G — Lifecycle, ativação e health
- **Objetivo:** Rotas e serviços dependem de `TenantIntegracao.status` ao invés de `sankhya_config.ativo`. Health visual consumirá de `IntegrationHealth`.
- **Detalhes:** Não altera rotinas do router global de ERP. A falha no `IntegrationHealth` não desativa a integração.

### ERP-DATA-HYGIENE-01H — Jobs e estado de sincronização
- **Objetivo:** Gravar desfechos das operações (`ultimo_sync`, métricas) em `IntegrationJob`.
- **Detalhamento:** Migrar escritas e leituras dos workers e routines (pessoas, produtos, finanças) para referenciar `IntegrationJob`.

### ERP-DATA-HYGIENE-01I — Política de sincronização
- **Objetivo:** Eliminar a leitura de `sync_interval`. O comportamento de polling ou evento baseará-se em `IntegrationSyncPolicy`.
- **Gatilho:** Só iniciará quando todo consumo de config técnica e credentials estiver concluído, para evitar schedulers dependentes de dados desatualizados.

### ERP-DATA-HYGIENE-01J — Encerramento da leitura legada
- **Objetivo:** Eliminar qualquer fallback no código para `SankhyaConfig`. O erro será explícito se a entidade canônica não estiver presente.
- **Critério:** Nenhuma instrução de "get_config()" no fluxo operacional.

### ERP-DATA-HYGIENE-01K — Encerramento da gravação dupla
- **Objetivo:** Interromper a geração/atualização de `SankhyaConfig`.
- **Critério:** O `SankhyaCanonicalAdapter` não deve mais recriar e atualizar linhas em `sankhya_config` quando configurado via painel.

### ERP-DATA-HYGIENE-01L — Auditoria final de consumidores
- **Objetivo:** Verificação estática que garanta a ausência de queries ativas. `SankhyaConfig` passará a existir apenas como histórico.

## 8. Matriz de Transição (Fases)

| Fase | Objetivo | Consumidores alterados | Campos envolvidos | Fonte de verdade | Fallback permitido | Escrita dupla | Risco | Rollback | Critério de GO |
| ---- | -------- | ---------------------- | ----------------- | ---------------- | ------------------ | ------------- | ----- | -------- | -------------- |
| 01D | Contrato Interno | Construtores API/Clients | Todos | Legado | N/A | Sim | Baixo | Reverter construtores | Construtores não dependem de SQLAlchemy ORM |
| 01E | Config Técnica | `SankhyaWSClient`, `auth_service` | URLs, Env | Canônico | Sim | Sim | Médio | Desfazer bind p/ `TenantIntegracao` | Clients funcionam usando dados do JSON |
| 01F | Credenciais | `auth_service` | auth tokens/passwords | Canônico | Sim, via aviso | Sim | Alto | Retornar para leitura da config antiga | Auth opera sem token legado do config |
| 01G | Lifecycle e Health | Handlers, Middlewares, UI | `ativo`, `ultimo_teste` | Canônico | Sim | Sim | Baixo | Retornar para flag do config | O painel não consulta `ultimo_teste` legado |
| 01H | Estado de Jobs | Services Sincronização | `ultimo_sync` | Canônico | Não | Sim | Médio | Reverter writes para SankhyaConfig | `IntegrationJob` registra sucesso/falha |
| 01I | Schedulers | Workers | `sync_interval` | Canônico | Não | Sim | Alto | Worker aponta p/ tabela legada | Jobs operam com `IntegrationSyncPolicy` |
| 01J | Fim Leitura Legada | Todos (remoção de fallback)| N/A | Canônico | Não | Sim | Médio | Reverter remoção (git revert) | Nenhum fallback legados no código de leitura |
| 01K | Fim Gravação Dupla | `SankhyaCanonicalAdapter` | N/A | Canônico | Não | Não | Médio | Reativar sync-back via Adapter | Nova configuração não gera linha no legado |
| 01L | Auditoria Final | N/A (Código) | Todos | Canônico | Não | Não | Baixo | N/A | AST / Grep não retornam instâncias ativas |

## 9. Regras de Precedência
- **Fase Inicial**: O `SankhyaConfig` prevalece nos tenants não migrados, mas a gravação de dados operacionais sempre atualiza ambas as pontas (gravação dupla).
- **Fase Intermediária (01E-01G)**: Os dados canônicos começam a prevalecer, mas possuem permissão explícita para invocar fallback caso nulos (com logs avisando o fallback).
- **Fase Avançada (01J em diante)**: A consulta vai exclusivamente à entidade canônica. Precedência legada é proibida, e falha na busca emite exceção.

## 10. Estratégia de Fallback
- O fallback deve ser observável. Logs devem conter identificação do tenant e o aviso `[FALLBACK_LEGACY]`.
- Nenhuma configuração canônica inválida deverá ativar o fallback, para não ofuscar erros em ambiente canônico. O fallback é acionado apenas quando a estrutura canônica não foi construída ou os campos estão literalmente ausentes/não-migrados.
- O fallback é expressamente proibido a partir da fase **01J**.

## 11. Estratégia para Tenants Legados
1. **Identificação**: Um tenant legado é aquele que existe em `sankhya_config` mas carece de entradas em `tenant_integracoes` (e relacionamentos).
2. **Correção de Estruturas**: Na fase 01F, se houver falhas, um script de migração one-off deverá forçar a execução do Canonical Adapter, criando `TenantIntegracao`, e extraindo `IntegrationCredential` para todos os registros que estão apenas em `sankhya_config`.
3. **Múltiplas Integrações**: Tratamento de exceções, caso hajam múltiplas integrações para o mesmo provider (por exemplo: por estabelecimento), estas devem ser convertidas preservando a chave de estabelecimento correta.

## 12. Riscos
1. A maior dependência operacional (Risco Alto) reside no **`auth_service.py`**, dada a diversidade de login (OAuth vs Basic). Uma ruptura neste serviço indisponibiliza todas as chamadas HTTP.
2. A remoção de agendamentos (`sync_interval`) incorretamente pode gerar uma pausa não intencional na rotina de sincronia, levando à desatualização silenciosa de estoques e fluxos de caixa para tenants produtivos.

## 13. Rollback por Fase
Não se trata de reverter o BD, mas o fluxo de leitura:
- **01E/01F**: Git revert nas alterações de leitura do DTO ou `auth_service.py`. A gravação dupla garantirá que os dados em `SankhyaConfig` estejam perfeitamente válidos e atualizados. O fallback legado é ativado via retorno de branch.
- **01I**: Desfazer a leitura dos Workers no cron, obrigando-os a reconsultar os selects antigos de `sankhya_config.ativo = True`.
- **01K**: Restaurar a função no `CanonicalAdapter` que intercepta modificações do model canônico e realiza upsert em `sankhya_config`.

## 14. Testes por Fase
- **01E/01F**: Testes Unitários de autenticação usando Gateway e Basic Auth isolados, confirmando sucesso via payload de IntegrationCredential em oposição a SankhyaConfig.
- **01H/01I**: Testes de regressão de Workers e concorrência no poll de Sync (assegurando que o novo `IntegrationSyncPolicy` não causa disparos duplicados ou nulos).
- **01J**: O pipeline não pode ter nenhuma regressão. Testes unitários com fixtures legadas e sem canônicas **devem propositalmente falhar**, para garantir que o runtime repudie estado legado.

## 15. Guardrails
- Implantação futura de um check lint ou pre-commit na fase 01L via semgrep ou equivalente:
  `rg "SankhyaConfig" services/api/integracoes/sankhya/services` deverá gerar interrupção na pipeline (CI Failure), sinalizando não conformidade arquitetural.

## 16. Respostas às Questões Obrigatórias
1. **Primeiro consumidor a não receber SankhyaConfig**: O client interno (`SankhyaWSClient`) e os construtores de services (`01D`).
2. **Dependência de maior risco**: `SankhyaGatewayAuthService` (autenticação) e os Schedulers/Workers (polling).
3. **Removida primeiro com menor risco**: Health, `teste_status` e ativação (`01G`), por seu baixo impacto funcional na sincronização e prioridade visual.
4. **Leituras que devem migrar primeiro**: Configurações técnicas não sensíveis (URLs) e propriedades de lifecycle.
5. **Duração da gravação dupla**: Do início do projeto até o final da fase 01J, mantendo o fallback coberto.
6. **Detectar divergência**: Consulta nos bancos cruzando credenciais descriptografadas do legacy vs canonical credential, com hash comparativo.
7. **Fonte de verdade em cada fase**: Em A, legado. Nas intermediárias (01E-01J), canônico ganha preferência e é a fonte da verdade da operação, mantendo legado como fallback de segurança. Em D, totalmente canônico.
8. **Fallback permitido**: Durante as migrações progressivas 01E a 01I.
9. **Fallback proibido**: Na fase 01J e posteriores.
10. **Proteger tenants antigos**: O fallback legados nas fases iniciais os mantém em operação, mas scripts programados do Canonical Adapter migrarão esses dados (ver ponto 11).
11. **Diferenciar tenant não-migrado de inválido**: Pela presença da entidade `TenantIntegracao` correspondente; se não há entidade canônica preenchida mas há legado válido, foi falha na migração do adaptador (tenant não migrado).
12. **Fluxos em auth legada**: `legacy_ws_basic_auth` (username/password) e `gateway_legacy_login` (appkey/token).
13. **Fluxos exclusivos do OAuth Gateway**: Onde X-Token e client_id/client_secret são requeridos (`gateway_oauth_client_credentials`).
14. **Contratos mínimos de teste**: Login OAuth/Legacy que retorne acessos corretos sem vazamento, e sync_service instanciando chamadas WS com sufixos técnicos corretos.
15. **Criação interrompida**: Fase 01K.
16. **Gravação interrompida**: Fase 01K (fim total da gravação dupla).
17. **Leituras eliminadas**: Fase 01J.
18. **Referências aceitas temporariamente**: Em migrations legadas passadas (`alembic/versions`), testes de reconciliação de migração.
19. **Evidência sem consumidores**: O comando de busca e grep na pasta `services/api/integracoes/sankhya` não retorna nenhuma utilização instanciando, escrevendo ou lendo propriedades do Model, exceto no arquivo base do sqlalchemy model.
20. **Estratégia segura de rollback**: O modelo progressivo sem remover o config até 01K. Rollback no código recupera imediatamente a utilidade da gravação dupla feita durante o problema.

## 17. Recomendação da Primeira Execução
A primeira execução real deve ser o **ERP-DATA-HYGIENE-01D**, operando sob as diretrizes de definir um contrato em forma de tipos ou classes nativas em Python que atuam como uma barreira protetora entre o `SankhyaConfig` legado e as lógicas de negócio dos clients.

## 18. Veredicto Final
**GO PARA ERP-DATA-HYGIENE-01D**
O plano abrange os riscos e possui rastreabilidade, podendo iniciar a refatoração protetiva do contrato interno de leitura no framework.
