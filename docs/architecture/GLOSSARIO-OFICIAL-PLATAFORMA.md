# Glossário Oficial da Plataforma

## Integrações ERP

Este glossário padroniza a linguagem visível ao usuário no fluxo de integração ERP.
Ele não altera nomes técnicos de classes, models, endpoints ou contratos internos.

| Termo técnico | Termo preferencial na interface | Quando usar |
| --- | --- | --- |
| Provider | ERP conectado | Ao indicar qual sistema está integrado ao tenant |
| Provider atual | ERP atual | Ao mostrar o sistema configurado no momento |
| Capability | Função disponível | Ao listar o que a integração consegue fazer |
| Capability Matrix | Funções disponíveis | Ao resumir a cobertura funcional do ERP |
| Health | Situação da integração | Ao mostrar o estado da comunicação e estabilidade |
| Health crítico | Falha crítica de comunicação | Ao indicar bloqueio operacional |
| Policy | Regra de atualização | Ao explicar como a sincronização funciona |
| Sync | Atualização de dados | Ao tratar da troca de informações entre AgroSaaS e ERP |
| Runtime oficial | Fluxo principal da integração | Ao explicar a origem dos dados operacionais |
| Canonical | Principal | Ao diferenciar a camada oficial de compatibilidades legadas |
| Readiness | Situação para o piloto | Ao mostrar se a integração está pronta para uso inicial |
| Payload | Dados recebidos | Ao exibir conteúdo técnico em telas operacionais |
| Schema | Estrutura informada | Ao explicar formatos declarados pelo ERP |
| Contract | Regras carregadas | Ao apresentar definições já materializadas |
| Gateway OAuth | Acesso pelo gateway | Ao explicar a forma de autenticação sem impor jargão técnico |
| Feature | Área da integração | Ao resumir blocos funcionais como pessoas, produtos e NFe |
| Reconciliation | Confirmação de vínculo | Ao tratar associações pendentes entre AgroSaaS e ERP |
| External association | Vínculo entre AgroSaaS e ERP | Ao descrever relacionamento de registros |

## Regras de redação

1. Toda mensagem deve explicar o que aconteceu, o que isso significa ou o que o usuário precisa fazer agora.
2. Quando um termo técnico for inevitável, ele deve aparecer acompanhado de contexto operacional.
3. Mensagens de erro devem priorizar ação prática antes de detalhe técnico.
4. O backoffice pode usar linguagem um pouco mais técnica, mas ainda deve ser compreensível para operação e suporte.
