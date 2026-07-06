# INTEGRATIONS-LIFECYCLE-01 — Ciclo de Vida e Operações Oficiais do Domínio de Integrações

## 1. Resumo executivo

Foi formalizado o lifecycle oficial do domínio Integrações do AgroSaaS, compatível com:

- `INTEGRATIONS-ARCH-01`;
- `INTEGRATIONS-ARCH-02`;
- `INTEGRATIONS-GOV-01`;
- `SANKHYA-GOV-02`.

O documento separa explicitamente:

- lifecycle administrativo da integração;
- health runtime;
- ciclo de vida de jobs;
- auditoria;
- onboarding;
- desligamento;
- relação com o Wizard.

## 2. Lifecycle oficial

Estados oficiais definidos:

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

Decisões principais:

- `SYNCING` é transitório;
- `REMOVED` é terminal;
- `REVOKED` não retorna direto para `ACTIVE`;
- health não substitui lifecycle.

## 3. Transições oficiais

Fluxo principal:

`NOT_CONFIGURED -> CONFIGURED -> VALIDATING -> VALID -> ACTIVE -> SYNCING -> ACTIVE`

Fluxos de recuperação:

- `VALIDATING -> INVALID`
- `INVALID -> CONFIGURED`
- `ACTIVE -> PARTIALLY_DEGRADED -> ACTIVE`
- `ACTIVE -> DEGRADED -> ACTIVE`
- `ACTIVE -> SUSPENDED -> VALID -> ACTIVE`
- `ACTIVE -> REVOKED -> CONFIGURED -> VALIDATING -> VALID -> ACTIVE`
- `DISABLED -> REMOVED`
- `REVOKED -> REMOVED`

Transições proibidas relevantes:

- `NOT_CONFIGURED -> ACTIVE`
- `CONFIGURED -> ACTIVE`
- `INVALID -> ACTIVE`
- `REVOKED -> ACTIVE`
- `REMOVED -> ACTIVE`

## 4. Operações oficiais

Operações oficiais definidas:

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

Separação de responsabilidade:

- tenant configura e opera sua própria integração;
- backoffice observa, diagnostica e dá suporte;
- backoffice não é console principal de configuração do cliente.

## 5. Auditoria e versionamento

Foi definido que toda operação administrativa deve registrar:

- tenant;
- estabelecimento, quando existir;
- usuário;
- timestamp;
- IP;
- operação;
- resultado;
- motivo;
- correlação;
- integração;
- provider;
- escopo;
- versão afetada.

Também ficou definido que nunca se registra:

- senha em texto puro;
- token bruto;
- chave privada;
- certificado secreto completo.

Versionamento ficou formalizado como requisito arquitetural obrigatório para:

- connection;
- credential;
- features;
- sync policy;
- escopo;
- rollback auditável.

## 6. Jobs, health e alertas

Estados oficiais de jobs:

- `PENDING`
- `RUNNING`
- `SUCCESS`
- `FAILED`
- `CANCELLED`
- `RETRYING`

Relação com health:

- lifecycle administrativo e `IntegrationHealth` são camadas distintas;
- `ACTIVE` pode coexistir com `CONNECTED`, `DEGRADED` ou `PARTIAL_FAILURE`;
- `AUTH_ERROR` recorrente deve puxar correção de lifecycle.

Alertas mínimos definidos:

- credencial expirada;
- token próximo da expiração;
- sync parado;
- provider indisponível;
- falhas consecutivas;
- fila crescente;
- retries excessivos;
- health degradado persistente;
- job preso em execução.

## 7. Relação com o Wizard

Ficou formalizado que o Wizard:

- não configura integração;
- não cria provider;
- não salva credential;
- não executa onboarding técnico da integração.

O Wizard apenas consome prontidão.

Regra oficial:

- o Wizard pode verificar se uma integração exigida pelo piloto ou pelo módulo contratado está `ACTIVE`;
- ele não substitui o console de Integrações.

## 8. Aplicação ao Sankhya

Foi documentado que o Sankhya deve seguir esse lifecycle no escopo:

- `TENANT` hoje;
- `ESTABELECIMENTO` futuramente;
- nunca `UnidadeProdutiva`.

Fluxos aplicáveis:

- configurar;
- trocar credencial;
- testar conexão;
- ativar;
- sincronizar pessoas;
- sincronizar produtos;
- operar NFe;
- operar financeiro;
- suspender;
- desativar;
- revogar.

## 9. Limitações deliberadas

Permanece fora do escopo desta execução:

- implementação do lifecycle como engine de produção;
- implementação do versionamento persistente;
- implementação oficial de jobs, health e alerts;
- modelagem de `ESTABELECIMENTO`.

## 10. Próxima execução recomendada

Próxima execução recomendada:

`INTEGRATIONS-DOMAIN-01` ou equivalente.

Foco recomendado:

- modelo persistente oficial de `IntegrationConfig`, `IntegrationVersion`, `IntegrationJob`, `IntegrationHealth` e `IntegrationAlert`;
- base para consumo do lifecycle por Wizard, dashboards e observabilidade;
- governança específica de transições e rollback.

