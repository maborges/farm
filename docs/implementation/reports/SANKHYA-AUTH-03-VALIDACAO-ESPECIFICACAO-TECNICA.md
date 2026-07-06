# SANKHYA-AUTH-03 - Validação da Especificação Técnica de Acesso ao ERP Sankhya

Data: 2026-07-05

## 1. Objetivo

Validar se o acesso ao ERP Sankhya, conforme a especificação técnica registrada em `integracao_sankhya_especificacao_tecnica.md`, está atendendo ao que foi definido para o piloto do AgroSaaS.

## 2. Escopo da validação

Esta validação cobre:

- autenticação técnica;
- emissão e reutilização de token;
- teste de conexão Gateway;
- uso de credenciais e headers;
- segurança e mascaramento de segredos;
- suporte ao consumo do ERP pelo cliente SOAP genérico atual;
- cobertura parcial ou total das APIs documentadas na especificação.

## 3. Base de análise

Documentos e arquivos analisados:

- [docs/implementation/reports/integracao_sankhya_especificacao_tecnica.md](/opt/lampp/htdocs/farm/docs/implementation/reports/integracao_sankhya_especificacao_tecnica.md)
- [docs/implementation/reports/SANKHYA-AUTH-02-TEST-CONNECTION.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-AUTH-02-TEST-CONNECTION.md)
- [services/api/integracoes/sankhya/services/auth_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/auth_service.py)
- [services/api/integracoes/sankhya/services/sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py)
- [services/api/integracoes/sankhya/services/nfe_financeiro_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/nfe_financeiro_service.py)
- [services/api/integracoes/sankhya/routers/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/routers/__init__.py)
- testes unitários do módulo Sankhya em `services/api/tests/unit/integracoes/*`

## 4. Resultado executivo

O acesso ao ERP Sankhya está atendendo para o piloto Gateway-first.

O que está atendido:

- autenticação técnica centralizada;
- obtenção e reutilização de token;
- renovação automática quando o token expira;
- chamada ao endpoint `/authenticate`;
- header `Authorization: Bearer <token>`;
- header `X-Token` com segredo criptografado;
- teste de conexão sanitizado;
- permissões internas para configurar, consultar e testar a integração;
- mascaramento de segredos em respostas e diagnósticos.

O que está atendido parcialmente:

- o catálogo de APIs documentado na especificação;
- a persistência local completa do estado de integração descrita no documento;
- o cache de token em ambiente distribuído;
- a separação arquitetural exata nas camadas nomeadas pela especificação;
- a nomenclatura pública original `token/appkey/username/password`, porque a implementação atual opera com Gateway-first usando `client_id/client_secret/x_token`.

O que não está atendido:

- os contratos explícitos de documento da especificação:
  - `CACSP.incluirNota`
  - `CACSP.incluirAlterarCabecalhoNota`
  - `CACSP.incluirAlterarItemNota`
  - `ServicosNfeSP.confirmarNotas`
  - `CACSP.cancelarNota`
  - `SelecaoDocumentoSP.faturar`
- o uso explícito de `DbExplorerSP.executeQuery` como contrato nomeado;
- a camada de persistência local descrita como `SankhyaSyncRepository` e `IntegrationLogService` com contrato próprio;
- o requisito de usuário de negócio no payload como parte do fluxo ativo do piloto.

## 5. Matriz de aderência

| Item da especificação | Situação | Evidência / observação |
| --- | --- | --- |
| Controle de acesso centralizado | ATENDE | [auth_service.py#L75-L94](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/auth_service.py#L75-L94) |
| Autenticação técnica | ATENDE PARCIALMENTE | A spec cita `token/appkey/username/password`; a implementação atual usa Gateway-first com `client_id/client_secret/x_token`. |
| Emissão do token de acesso | ATENDE | [auth_service.py#L141-L168](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/auth_service.py#L141-L168) |
| Reutilização e expiração | ATENDE PARCIALMENTE | Há cache em memória e renovação automática, mas não cache centralizado multi-instância. |
| Autorização funcional interna | ATENDE | [routers/__init__.py#L95-L120](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/routers/__init__.py#L95-L120) |
| API de Login | ATENDE | [auth_service.py#L245-L300](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/auth_service.py#L245-L300) |
| API de Consulta de Dados | ATENDE PARCIALMENTE | Há cliente SOAP genérico e syncs de leitura, mas não contrato explícito `DbExplorerSP.executeQuery`. |
| API de Gravação e Atualização de Entidades | ATENDE PARCIALMENTE | Há escrita/importação em syncs, mas sem contrato dedicado `DatasetSP.save`. |
| Inclusão de Documento | NÃO ATENDE | Não localizado contrato equivalente ativo. |
| Alteração de Cabeçalho | NÃO ATENDE | Não localizado contrato equivalente ativo. |
| Alteração de Item | NÃO ATENDE | Não localizado contrato equivalente ativo. |
| Confirmação de Documento | NÃO ATENDE | Não localizado contrato equivalente ativo. |
| Cancelamento de Documento | NÃO ATENDE | Não localizado contrato equivalente ativo. |
| Faturamento de Documento | NÃO ATENDE | Não localizado contrato equivalente ativo. |
| Persistência local do estado | ATENDE PARCIALMENTE | Existem `IntegrationJob`, `IntegrationHealth` e `SankhyaSyncLog`, mas não o modelo completo descrito na spec. |
| Idempotência | ATENDE PARCIALMENTE | Há upsert em pessoas, produtos e NFe, mas não contrato genérico de idempotência documental. |
| Retentativa controlada | ATENDE PARCIALMENTE | Há reutilização de token e fluxo de jobs, mas não política formal de retry/backoff como a spec descreve. |
| Requisitos de segurança | ATENDE | Segredos são mascarados/criptografados e o token não é persistido no teste de conexão. |
| Requisitos arquiteturais | ATENDE PARCIALMENTE | Há `auth_service`, `sync_service`, `canonical_adapter` e rotas, mas não exatamente as camadas nomeadas pela spec. |

## 6. Escopo do Primeiro Piloto

O primeiro piloto não tem como objetivo implementar toda a especificação técnica do ERP Sankhya.

O objetivo do piloto é validar a integração Gateway-first dentro do escopo aprovado, com foco em:

- autenticação técnica;
- validação da conexão;
- sincronização de leitura;
- carga inicial dos dados necessários;
- rastreabilidade operacional mínima.

Funcionalidades descritas na especificação completa, mas não necessárias ao piloto, permanecem como evolução futura e poderão ser priorizadas após a validação operacional.

## 7. Matriz de prioridade do piloto

| Funcionalidade | Prioridade |
| --- | --- |
| Autenticação Gateway | P0 |
| Teste de conexão | P0 |
| Leitura de pessoas | P0 |
| Leitura de produtos | P0 |
| Leitura financeira | P0 |
| Leitura de NFe | P1 |
| Escrita de documentos | Pós-piloto |
| Cancelamento | Pós-piloto |
| Faturamento | Pós-piloto |
| Cache distribuído | Evolução futura |
| Pipeline bidirecional | Evolução futura |

Observação: esta priorização reflete o escopo aprovado do primeiro piloto e não altera a aderência técnica da especificação completa.

## 8. O que a implementação já entrega

### 6.1 Autenticação Gateway

O serviço de autenticação já:

- valida configuração Gateway;
- chama o endpoint `/authenticate`;
- extrai `access_token`;
- calcula expiração;
- reutiliza token válido em cache local;
- monta cabeçalhos autorizados para o ERP.

### 6.2 Teste de conexão

O endpoint de teste de conexão já:

- valida configuração completa;
- autentica sem persistir estado externo;
- retorna diagnóstico sanitizado;
- informa ambiente, base URL, auth URL e máscaras de segredo;
- indica se houve token obtido e sua expiração.

### 6.3 Consumo do ERP no piloto

O cliente SOAP genérico atual já suporta:

- leitura de pessoas;
- leitura de produtos;
- leitura de NFe;
- exportação/importação de NFe e financeiro;
- uso do header autenticado conforme o modelo Gateway ou legado.

## 9. Lacunas relevantes e interpretação de escopo

As principais lacunas em relação à especificação são:

- ausência dos contratos documentais de escrita e faturamento;
- ausência de uma camada dedicada de persistência local no formato exato da especificação;
- ausência de cache distribuído para token;
- ausência de nomenclatura pública alinhada à spec legada;
- ausência de uma trilha documental de operação para todas as APIs listadas no texto técnico.

As marcações de `NÃO ATENDE` acima podem representar três situações distintas:

- fora do escopo do primeiro piloto;
- evolução futura natural da integração;
- funcionalidade realmente ausente e potencialmente necessária em fase posterior.

No contexto deste piloto, essas lacunas não impedem a execução do primeiro piloto operacional.

## 10. Conclusão

Para o primeiro piloto operacional, o acesso ao ERP Sankhya está adequado e funcional.

Para a especificação técnica completa, o estado atual é:

- **ATENDE** no núcleo de autenticação e acesso;
- **ATENDE PARCIALMENTE** na camada de arquitetura e persistência;
- **NÃO ATENDE** nos contratos documentais avançados de escrita, confirmação, cancelamento e faturamento.

As funcionalidades classificadas como não implementadas referem-se à especificação completa da integração Sankhya e não constituem bloqueadores para o primeiro piloto operacional. O escopo aprovado do MVP contempla exclusivamente os componentes necessários para a autenticação Gateway-first, validação da conexão, sincronização de leitura e carga inicial. As demais funcionalidades serão avaliadas após a validação do piloto, conforme necessidades reais identificadas em operação.

## 11. Recomendação

Recomenda-se tratar o fluxo atual como:

- **pronto para o piloto Gateway-first**;
- **não equivalente a uma implementação completa da especificação técnica**;
- **base segura para evolução incremental**, sem criar componentes paralelos.
