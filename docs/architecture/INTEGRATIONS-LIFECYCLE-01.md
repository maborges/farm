# INTEGRATIONS-LIFECYCLE-01 — Ciclo de Vida e Operações Canônicas do Domínio de Integrações

## 1. Objetivo

Definir o ciclo de vida oficial das integrações do AgroSaaS.

Este documento estabelece:

- estados arquiteturais oficiais;
- transições válidas e proibidas;
- operações canônicas;
- regras de auditoria;
- princípios de versionamento;
- onboarding e desligamento;
- ciclo de vida de jobs;
- relação entre lifecycle, health e alertas;
- relação do domínio Integrações com o Wizard;
- aplicação prática ao provider Sankhya.

Este documento é normativo para qualquer integração futura do AgroSaaS.

## 2. Motivação

`INTEGRATIONS-ARCH-01` definiu:

- Integrações como domínio transversal oficial;
- escopos `PLATFORM`, `TENANT`, `ESTABELECIMENTO` e `USUARIO`;
- backoffice como console de observabilidade e suporte;
- console do tenant como casa da configuração do cliente.

`INTEGRATIONS-ARCH-02` definiu:

- `IntegrationProvider`;
- `IntegrationProviderDefinition`;
- `IntegrationConnection`;
- `IntegrationCredential`;
- `IntegrationFeature`;
- `IntegrationSyncPolicy`;
- `IntegrationHealth`;
- `IntegrationConfig`.

`INTEGRATIONS-GOV-01` e `SANKHYA-GOV-02` consolidaram guardrails e correções mínimas de produção.

Faltava formalizar:

- quando uma integração é apenas configurada;
- quando ela é válida;
- quando ela pode operar;
- como ela entra em sincronização;
- como ela degrada, suspende, revoga e é removida;
- como se comportam jobs, alertas, rollback e auditoria.

Decisão:

- a partir deste documento, nenhuma integração poderá nascer sem lifecycle explícito.

## 3. Lifecycle

O lifecycle canônico do domínio Integrações representa o estado administrativo e operacional da configuração de integração do cliente.

Ele não substitui:

- `IntegrationHealth`, que descreve saúde runtime;
- `IntegrationJob`, que descreve execução de jobs;
- `IntegrationAlert`, que descreve atenção operacional;
- `Wizard`, que apenas consome pré-requisitos.

O lifecycle responde:

- a integração existe?
- a configuração foi salva?
- a configuração foi validada?
- ela está autorizada a operar?
- ela está temporariamente suspensa?
- ela foi revogada?
- ela foi removida?

## 4. Estados

### 4.1 Estados oficiais

Estados oficiais do lifecycle:

- `NOT_CONFIGURED`
- `CONFIGURED`
- `VALIDATING`
- `VALID`
- `INVALID`
- `ACTIVE`
- `SYNCING`
- `PARTIALLY_DEGRADED`
- `DEGRADED`
- `SUSPENDED`
- `DISABLED`
- `REVOKED`
- `REMOVED`

### 4.2 Semântica de cada estado

#### `NOT_CONFIGURED`

A integração ainda não possui configuração persistida utilizável para aquele escopo.

Uso correto:

- integração ainda não iniciada;
- configuração removida;
- tenant ainda não informou connection/credential mínimas.

#### `CONFIGURED`

A configuração foi salva, mas ainda não foi validada tecnicamente ou funcionalmente.

Uso correto:

- connection salva;
- credential salva;
- features escolhidas;
- ainda sem teste conclusivo de conexão/credencial.

#### `VALIDATING`

A integração está em processo explícito de validação.

Uso correto:

- teste de conexão em andamento;
- handshake com provider em andamento;
- validação inicial de credencial, feature ou schema.

#### `VALID`

A configuração foi validada com sucesso, mas ainda não está necessariamente ativa para operar continuamente.

Uso correto:

- configuração tecnicamente válida;
- credencial aceita;
- provider respondeu;
- ainda não houve ativação formal ou primeiro sync operacional.

#### `INVALID`

A configuração existe, mas é inválida para operar.

Uso correto:

- credencial rejeitada;
- endpoint incorreto;
- schema inconsistente;
- feature incompatível;
- teste falhou.

#### `ACTIVE`

Estado canônico de operação normal.

Uso correto:

- integração validada;
- habilitada administrativamente;
- apta a processar jobs, syncs, eventos ou webhooks.

#### `SYNCING`

Estado transitório de execução operacional.

Uso correto:

- sync manual em execução;
- sync agendado rodando;
- carga inicial ou reprocessamento.

Regra:

- `SYNCING` não substitui `ACTIVE`; ele representa subestado operacional transitório sobre configuração ativa.

#### `PARTIALLY_DEGRADED`

A integração segue ativa, mas com perda parcial de capacidade.

Uso correto:

- algumas features operam e outras falham;
- parte do provider responde;
- sync parcial bem-sucedido com falha em subset conhecido;
- limitação localizada sem necessidade de suspensão total.

#### `DEGRADED`

A integração segue formalmente ativa, mas com degradação material relevante.

Uso correto:

- instabilidade recorrente;
- retries acumulando;
- health comprometido;
- operação possível, porém com risco alto ou resultado incompleto.

#### `SUSPENDED`

Integração temporariamente interrompida por decisão operacional ou proteção automática controlada.

Uso correto:

- pausa manual do administrador;
- pausa por troubleshooting;
- pausa preventiva por falhas repetidas;
- pausa para rotação de credencial.

#### `DISABLED`

Integração deliberadamente desligada no escopo em questão, mas mantida como configuração histórica.

Uso correto:

- cliente não quer operar temporariamente;
- feature desativada;
- contrato da integração desligado sem revogar histórico.

Diferença para `SUSPENDED`:

- `SUSPENDED` presume intenção de retomada curta e estado operacional interrompido;
- `DISABLED` presume desligamento administrativo mais estável.

#### `REVOKED`

Credencial ou autorização do provider foi revogada de forma efetiva.

Uso correto:

- token revogado;
- credencial invalidada pelo provider;
- acesso removido pelo cliente;
- certificado revogado.

Regra:

- `REVOKED` impede retorno direto para `ACTIVE` sem nova credencial e nova validação.

#### `REMOVED`

Configuração foi removida logicamente como integração vigente.

Uso correto:

- integração desligada definitivamente naquele escopo;
- configuração substituída;
- remoção administrativa concluída com retenção histórica/auditável.

Regra:

- `REMOVED` é estado final.

### 4.3 Estados deliberadamente não adotados

Estados avaliados e não adotados como lifecycle primário:

- `CONNECTED`
- `AUTH_ERROR`
- `RATE_LIMITED`
- `CONFIG_ERROR`
- `PARTIAL_FAILURE`

Motivo:

- pertencem à camada `IntegrationHealth`, não ao lifecycle administrativo primário.

## 5. Transições

### 5.1 Fluxo canônico principal

```text
NOT_CONFIGURED
  ↓
CONFIGURED
  ↓
VALIDATING
  ↓
VALID
  ↓
ACTIVE
  ↓
SYNCING
  ↓
ACTIVE
```

### 5.2 Fluxos de falha e recuperação

```text
VALIDATING
  ↓
INVALID

ACTIVE
  ↓
PARTIALLY_DEGRADED
  ↓
ACTIVE

ACTIVE
  ↓
DEGRADED
  ↓
ACTIVE

ACTIVE
  ↓
SUSPENDED
  ↓
VALID
  ↓
ACTIVE

ACTIVE
  ↓
REVOKED
  ↓
CONFIGURED
  ↓
VALIDATING
  ↓
VALID
  ↓
ACTIVE
```

### 5.3 Transições válidas

- `NOT_CONFIGURED -> CONFIGURED`
- `CONFIGURED -> VALIDATING`
- `VALIDATING -> VALID`
- `VALIDATING -> INVALID`
- `INVALID -> CONFIGURED`
- `VALID -> ACTIVE`
- `VALID -> DISABLED`
- `ACTIVE -> SYNCING`
- `SYNCING -> ACTIVE`
- `SYNCING -> PARTIALLY_DEGRADED`
- `SYNCING -> DEGRADED`
- `ACTIVE -> PARTIALLY_DEGRADED`
- `PARTIALLY_DEGRADED -> ACTIVE`
- `PARTIALLY_DEGRADED -> DEGRADED`
- `ACTIVE -> DEGRADED`
- `DEGRADED -> ACTIVE`
- `ACTIVE -> SUSPENDED`
- `PARTIALLY_DEGRADED -> SUSPENDED`
- `DEGRADED -> SUSPENDED`
- `SUSPENDED -> VALID`
- `ACTIVE -> DISABLED`
- `DISABLED -> CONFIGURED`
- `ACTIVE -> REVOKED`
- `INVALID -> REVOKED`
- `REVOKED -> CONFIGURED`
- `DISABLED -> REMOVED`
- `REVOKED -> REMOVED`
- `NOT_CONFIGURED -> REMOVED` é proibida

### 5.4 Transições proibidas

São proibidas, entre outras:

- `NOT_CONFIGURED -> ACTIVE`
- `NOT_CONFIGURED -> SYNCING`
- `CONFIGURED -> ACTIVE`
- `CONFIGURED -> SYNCING`
- `INVALID -> ACTIVE`
- `REVOKED -> ACTIVE`
- `DISABLED -> ACTIVE`
- `REMOVED -> ACTIVE`
- `REMOVED -> CONFIGURED`
- `SYNCING -> NOT_CONFIGURED`

### 5.5 Regras de transição

- nenhuma integração entra em `ACTIVE` sem passar por validação;
- `REVOKED` exige troca de credencial e nova validação;
- `REMOVED` é terminal no contexto da configuração removida;
- `SYNCING` é transitório e não deve ser usado como estado administrativo estável;
- `PARTIALLY_DEGRADED` e `DEGRADED` não autorizam mascarar falhas críticas sem alerta.

## 6. Operações

### 6.1 Operações canônicas oficiais

- Configurar
- Editar
- Trocar Credencial
- Testar Conexão
- Ativar
- Desativar
- Suspender
- Retomar
- Executar Sync Manual
- Reprocessar
- Cancelar Job
- Limpar Fila
- Exportar Logs
- Revogar Credenciais
- Remover Integração
- Rollback Configuração

### 6.2 Semântica das operações

#### Configurar

Cria ou grava `Connection`, `Credential`, `Feature` e `SyncPolicy` mínimas.

Efeito esperado:

- `NOT_CONFIGURED -> CONFIGURED`

#### Editar

Altera parâmetros não secretos ou features/policies.

Efeito esperado:

- pode manter `CONFIGURED`, `VALID`, `ACTIVE` ou forçar retorno a `CONFIGURED` conforme criticidade.

#### Trocar Credencial

Rotaciona segredos.

Efeito esperado:

- volta para `CONFIGURED` ou `VALIDATING`;
- nunca deve manter `ACTIVE` silenciosamente sem nova validação.

#### Testar Conexão

Executa validação técnica.

Efeito esperado:

- `CONFIGURED -> VALIDATING -> VALID`
- ou `CONFIGURED -> VALIDATING -> INVALID`

#### Ativar

Habilita a integração validada para operação normal.

Efeito esperado:

- `VALID -> ACTIVE`

#### Desativar

Desliga administrativamente a integração sem remover histórico.

Efeito esperado:

- `VALID -> DISABLED`
- `ACTIVE -> DISABLED`

#### Suspender

Pausa temporária.

Efeito esperado:

- `ACTIVE -> SUSPENDED`
- `DEGRADED -> SUSPENDED`
- `PARTIALLY_DEGRADED -> SUSPENDED`

#### Retomar

Retira suspensão.

Efeito esperado:

- `SUSPENDED -> VALID`
- seguido de `VALID -> ACTIVE` quando aplicável

#### Executar Sync Manual

Dispara execução explícita.

Efeito esperado:

- `ACTIVE -> SYNCING -> ACTIVE`

#### Reprocessar

Executa nova tentativa de carga parcial, job falho ou janela específica.

#### Cancelar Job

Interrompe job em andamento, sem alterar necessariamente a configuração principal.

#### Limpar Fila

Operação excepcional de governança operacional. Deve ser restrita ao backoffice/suporte.

#### Exportar Logs

Extrai histórico operacional auditável.

#### Revogar Credenciais

Inutiliza uso futuro da credencial atual.

Efeito esperado:

- `ACTIVE -> REVOKED`
- `INVALID -> REVOKED`

#### Remover Integração

Remove a integração vigente do escopo operacional.

Efeito esperado:

- `DISABLED -> REMOVED`
- `REVOKED -> REMOVED`

#### Rollback Configuração

Restaura versão anterior válida da configuração.

Efeito esperado:

- retorna a uma versão conhecida e reinicia validação

### 6.3 Quem pode executar cada operação

#### Console do tenant

Pode executar:

- Configurar
- Editar
- Trocar Credencial
- Testar Conexão
- Ativar
- Desativar
- Suspender
- Retomar
- Executar Sync Manual
- Exportar Logs do próprio escopo

#### Backoffice

Pode executar:

- observar health, logs e jobs;
- executar troubleshooting controlado;
- reprocessar em apoio operacional;
- cancelar job excepcionalmente;
- exportar logs para suporte;
- revogar integração em incidentes críticos quando a governança permitir.

Backoffice não é:

- console primário de configuração do cliente.

## 7. Auditoria

### 7.1 Toda operação administrativa deve registrar

- tenant;
- estabelecimento, quando existir;
- usuário;
- data/hora;
- IP;
- operação;
- resultado;
- motivo;
- correlação;
- integração;
- provider;
- versão afetada;
- escopo;
- origem da chamada: tenant console ou backoffice.

### 7.2 Dados que nunca devem ser registrados

- senha em texto puro;
- token em texto puro;
- `app_secret` bruto;
- chave privada;
- certificado secreto completo;
- headers sensíveis completos;
- payloads contendo segredos não mascarados.

### 7.3 Regras

- logs de auditoria são append-only;
- alterações de credencial devem registrar metadado da rotação, nunca o segredo;
- falha de autenticação pode registrar motivo e provider, nunca a credencial enviada.

## 8. Versionamento

### 8.1 Princípios oficiais

Toda configuração de integração deve ser versionável.

Versionamento deve cobrir:

- mudança de connection;
- mudança de credential;
- mudança de feature;
- mudança de sync policy;
- mudança de escopo;
- mudança de ativação/desativação.

### 8.2 O que uma versão deve conter

- identificador da versão;
- referência ao provider;
- referência ao escopo;
- snapshot mascarado de connection;
- snapshot mascarado de credential;
- features habilitadas;
- policies vigentes;
- autor da alteração;
- timestamp;
- motivo da mudança;
- hash/assinatura interna quando aplicável.

### 8.3 Rollback

Rollback arquiteturalmente permitido:

- apenas para versões íntegras e auditáveis;
- sempre seguido de nova validação;
- nunca restaurando credencial em texto puro.

## 9. Onboarding

### 9.1 Fluxo oficial

```text
Selecionar Provider
  ↓
Definir Escopo
  ↓
Preencher Connection
  ↓
Preencher Credential
  ↓
Selecionar Features
  ↓
Selecionar Sync Policies
  ↓
Testar
  ↓
Salvar
  ↓
Ativar
  ↓
Primeiro Sync
  ↓
Operação Normal
```

### 9.2 Regras

- provider sempre vem antes da configuração;
- escopo sempre vem antes da credencial;
- nenhuma ativação sem teste;
- nenhuma ativação sem auditoria de autoria;
- primeiro sync deve ser distinguido de sync recorrente para fins de observabilidade.

### 9.3 Desativação e remoção

#### Desligamento temporário

Estado:

- `SUSPENDED`

Uso:

- troubleshooting;
- manutenção;
- pausa operacional.

#### Desligamento administrativo

Estado:

- `DISABLED`

Uso:

- cliente não deseja operar naquele momento;
- feature desligada por decisão formal.

#### Revogação

Estado:

- `REVOKED`

Uso:

- credencial ou autorização invalidada.

#### Remoção definitiva

Estado:

- `REMOVED`

Uso:

- encerramento lógico daquela configuração vigente, preservando histórico.

## 10. Jobs

### 10.1 Estados oficiais dos jobs

- `PENDING`
- `RUNNING`
- `SUCCESS`
- `FAILED`
- `CANCELLED`
- `RETRYING`

### 10.2 Regras

- `IntegrationJob` não altera sozinho o lifecycle administrativo final;
- job falho recorrente pode induzir `PARTIALLY_DEGRADED` ou `DEGRADED`;
- job cancelado não implica remoção da integração;
- retries devem manter correlação e idempotência;
- toda execução deve registrar tenant/escopo/provider/feature.

### 10.3 Relação com lifecycle

- `ACTIVE` pode gerar jobs `PENDING`, `RUNNING`, `SUCCESS`, `FAILED`, `RETRYING`;
- `SUSPENDED`, `DISABLED`, `REVOKED` e `REMOVED` não devem aceitar novos jobs normais;
- `REPROCESSAR` é exceção controlada, não regra permanente.

## 11. Health

### 11.1 Relação entre lifecycle e health

O lifecycle não substitui `IntegrationHealth`.

Exemplo de composição válida:

- `ACTIVE + CONNECTED`
- `ACTIVE + DEGRADED`
- `ACTIVE + PARTIAL_FAILURE`
- `VALID + DISCONNECTED`
- `INVALID + CONFIG_ERROR`
- `REVOKED + AUTH_ERROR`

### 11.2 Regras

- `ACTIVE` não exige health perfeito, mas exige operação autorizada;
- `DEGRADED` de health não implica obrigatoriamente `DEGRADED` de lifecycle na primeira ocorrência;
- `AUTH_ERROR` recorrente deve puxar lifecycle para `INVALID` ou `REVOKED` conforme origem;
- `CONFIG_ERROR` não deve conviver com `ACTIVE` por tempo indefinido.

## 12. Alertas

### 12.1 Alertas mínimos obrigatórios

O domínio deve ser capaz de alertar quando houver:

- credencial expirada;
- token próximo da expiração;
- sync parado acima do SLA;
- provider indisponível;
- falhas consecutivas acima do limiar;
- fila crescendo acima do limiar;
- health em `DEGRADED` persistente;
- `AUTH_ERROR`;
- `RATE_LIMITED` recorrente;
- job preso em `RUNNING`;
- retries excessivos;
- discrepância entre feature ativa e sync sem sucesso.

### 12.2 Relação com governança

- alertas de tenant devem ser visíveis ao console do tenant conforme RBAC;
- alertas de suporte e plataforma devem ser visíveis no backoffice;
- nenhum alerta deve expor segredo bruto.

## 13. Aplicação ao Sankhya

### 13.1 Mapeamento conceitual

No Sankhya atual, o fluxo canônico esperado passa a ser:

```text
NOT_CONFIGURED
  ↓
CONFIGURED
  ↓
VALIDATING
  ↓
VALID
  ↓
ACTIVE
  ↓
SYNCING
  ↓
ACTIVE
```

### 13.2 Escopo

Escopo padrão:

- `TENANT`

Escopo futuro possível:

- `ESTABELECIMENTO`

Escopo proibido:

- `UnidadeProdutiva`

### 13.3 Operações aplicáveis ao Sankhya

- configurar gateway e parâmetros;
- trocar credencial;
- testar conexão;
- ativar;
- sincronizar pessoas;
- sincronizar produtos;
- operar NFe;
- operar financeiro;
- suspender;
- desativar;
- revogar;
- remover logicamente quando o domínio canônico suportar.

### 13.4 Backoffice no Sankhya

Backoffice Sankhya deve continuar com:

- observabilidade;
- health;
- logs;
- diagnóstico;
- suporte.

Tenant Sankhya deve continuar com:

- configuração;
- credencial;
- teste;
- sync manual;
- acompanhamento operacional do próprio escopo.

## 14. Decisões arquiteturais

- lifecycle administrativo e health runtime são camadas distintas;
- jobs possuem ciclo de vida próprio;
- `SYNCING` é estado transitório;
- `REVOKED` não volta direto para `ACTIVE`;
- `REMOVED` é terminal para a configuração removida;
- backoffice não é console primário do cliente;
- Wizard apenas consome lifecycle, não configura integrações.

## 15. Limitações deliberadas

Limitações aceitas para a V1:

- lifecycle definido conceitualmente, ainda não implementado como engine canônica transversal;
- versionamento formal de configuração ainda não materializado;
- alertas e jobs ainda dependem da evolução operacional do domínio;
- `ESTABELECIMENTO` ainda não está implementado como domínio produtivo completo.

## 16. Evoluções futuras

Próximas evoluções recomendadas:

- `INTEGRATIONS-DOMAIN-01` ou equivalente para modelo persistente canônico;
- `INTEGRATIONS-GOV-02` para guardrails específicos de lifecycle;
- implementação de histórico/versionamento de configurações;
- implementação de `IntegrationJob`, `IntegrationHealth` e `IntegrationAlert` canônicos;
- preparação de consumo do lifecycle pelo Wizard e por health dashboards.

