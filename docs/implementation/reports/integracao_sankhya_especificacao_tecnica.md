# Especificacao Tecnica de Integracao com o ERP Sankhya

## Objetivo

Este documento define como uma aplicacao deve se integrar ao ERP Sankhya, com foco em:

1. controle de acesso as APIs
2. APIs acessadas
3. responsabilidade de cada API
4. sequencia recomendada de chamadas
5. requisitos de seguranca, rastreabilidade e arquitetura

## Visao Geral

A integracao com o Sankhya segue um modelo de autenticacao tecnica centralizada. A aplicacao nao autentica cada usuario final diretamente no ERP. Em vez disso, utiliza uma conta tecnica de integracao para obter um token de acesso e reutiliza esse token nas chamadas subsequentes.

Separadamente, a aplicacao pode manter regras proprias de autorizacao para decidir quais usuarios internos podem executar rotinas de integracao, consultar logs ou disparar processos. Essas permissoes sao internas da aplicacao e nao substituem a autenticacao tecnica exigida pelo Sankhya.

## Controle de Acesso as APIs

### 1. Autenticacao tecnica

O acesso ao Sankhya deve ser feito por meio de uma conta tecnica da integracao, com as seguintes credenciais:

- `token`
- `appkey`
- `username`
- `password`

Essas credenciais identificam a integracao perante o ERP.

### 2. Emissao do token de acesso

O processo esperado e:

1. a aplicacao realiza login no endpoint de autenticacao do Sankhya
2. o ERP retorna um `bearerToken`
3. a aplicacao armazena temporariamente esse token
4. todas as chamadas seguintes usam o token no header HTTP

Formato do header:

```http
Authorization: Bearer <token>
```

### 3. Reutilizacao e expiracao

O token deve ser reutilizado enquanto estiver valido. Quando expirar, a aplicacao deve solicitar um novo token automaticamente.

Recomendacoes:

- nao depender exclusivamente de sessao web para guardar o token
- usar cache centralizado quando houver jobs, filas ou multiplas instancias
- renovar o token antes do vencimento real

### 4. Autorizacao funcional

O Sankhya valida a conta tecnica autenticada. Ja o controle de quem pode disparar integracoes deve ser tratado pela propria aplicacao, com permissoes internas para:

- executar integracoes
- consultar logs
- cancelar documentos
- reenviar processos
- acessar operacoes administrativas

### 5. Usuario de negocio

Em algumas operacoes, a aplicacao pode informar identificadores de usuario do proprio Sankhya dentro do payload do documento. Isso serve para rastreabilidade, regras de negocio e atribuicao operacional no ERP, mas nao substitui a autenticacao HTTP da API.

## Catalogo das APIs Utilizadas

### 1. API de Login

**Funcao**

Autenticar a integracao e emitir o token de acesso.

**Finalidade**

- iniciar uma sessao tecnica com o ERP
- renovar o token quando necessario

**Entrada**

- `token`
- `appkey`
- `username`
- `password`

**Saida esperada**

- `bearerToken`

### 2. API de Consulta de Dados

**Servico**

`DbExplorerSP.executeQuery`

**Funcao**

Executar consultas de leitura no ERP.

**Finalidade**

- consultar parceiros
- consultar produtos
- consultar contas correntes
- consultar historicos de operacao
- consultar documentos
- consultar movimentacoes e saldos

**Cuidados**

- tratar como API de leitura controlada
- limitar o uso a consultas necessarias para integracao
- validar e revisar as consultas executadas

### 3. API de Gravacao e Atualizacao de Entidades

**Servico**

`DatasetSP.save`

**Funcao**

Inserir ou atualizar registros em entidades do Sankhya.

**Finalidade**

- atualizar dados auxiliares
- gravar informacoes complementares
- sincronizar campos de entidades
- enviar datasets de integracao

**Cuidados**

- validar rigorosamente os campos enviados
- impedir sobrescrita indevida de informacoes
- registrar log funcional e tecnico do que foi alterado

### 4. API de Inclusao de Documento

**Servico**

`CACSP.incluirNota`

**Funcao**

Criar documentos no ERP.

**Finalidade**

- gerar pedido de compra
- gerar contrato
- gerar documento base para faturamento
- gerar documento operacional de armazenagem

**Dados normalmente enviados**

- parceiro
- empresa
- tipo de operacao
- tipo de movimento
- centro de custo
- comprador
- data de negociacao
- produto
- quantidade
- valor unitario
- valor total
- observacao

**Saida esperada**

- identificador do documento gerado no ERP

### 5. API de Alteracao de Cabecalho

**Servico**

`CACSP.incluirAlterarCabecalhoNota`

**Funcao**

Alterar o cabecalho de um documento existente.

**Finalidade**

- alterar parceiro
- alterar favorecido
- alterar data de negociacao
- alterar centro de custo
- ajustar dados financeiros
- complementar informacoes do documento

### 6. API de Alteracao de Item

**Servico**

`CACSP.incluirAlterarItemNota`

**Funcao**

Alterar os itens de um documento existente.

**Finalidade**

- ajustar quantidade
- ajustar valor unitario
- ajustar valor total
- ajustar observacao do item
- corrigir campos operacionais do item

### 7. API de Confirmacao de Documento

**Servico**

`ServicosNfeSP.confirmarNotas`

**Funcao**

Confirmar o documento no ERP.

**Finalidade**

- confirmar pedido
- confirmar contrato
- confirmar fatura
- concluir a etapa operacional apos criacao ou ajuste

**Efeito esperado**

O documento deixa o estado intermediario de criacao e passa a estado confirmado dentro do ERP.

### 8. API de Cancelamento de Documento

**Servico**

`CACSP.cancelarNota`

**Funcao**

Cancelar documentos ja criados no ERP.

**Finalidade**

- desfazer integracao indevida
- cancelar documento incorreto
- executar rollback funcional
- encerrar documento com motivo registrado

**Entrada esperada**

- identificador do documento
- motivo do cancelamento

### 9. API de Faturamento de Documento

**Servico**

`SelecaoDocumentoSP.faturar`

**Funcao**

Gerar faturamento a partir de um pedido, contrato ou documento base existente.

**Finalidade**

- faturar pedido de compra
- gerar fatura de armazenagem
- converter documento base em documento faturado

**Saida esperada**

- identificador da nota ou fatura gerada

## Papel de Cada API no Processo

### Autenticacao

- login
- emissao de token
- renovacao de acesso tecnico

### Leitura

- consulta de dados mestres
- validacao de pre-condicoes
- consulta de documentos e historicos
- obtencao de dados para conciliacao

### Escrita de entidades

- atualizacao de dados auxiliares
- sincronizacao de campos complementares
- envio de datasets operacionais

### Documentos

- criacao do documento principal
- ajuste de cabecalho
- ajuste de itens
- confirmacao
- cancelamento
- faturamento

## Sequencias Recomendadas de Integracao

### Fluxo padrao de criacao de documento

1. autenticar no Sankhya
2. consultar os dados obrigatorios no ERP e no sistema local
3. validar de/para, regras de negocio e dependencias
4. criar o documento
5. ajustar cabecalho, se necessario
6. ajustar itens, se necessario
7. confirmar o documento
8. persistir numero, status, payload e retorno no sistema local

### Fluxo de faturamento

1. autenticar
2. validar se o documento base existe e esta apto a faturamento
3. solicitar o faturamento
4. ajustar cabecalho da fatura, se necessario
5. ajustar itens da fatura, se necessario
6. confirmar a fatura
7. persistir identificadores e status no sistema local

### Fluxo de cancelamento

1. autenticar
2. validar se o documento pode ser cancelado
3. cancelar o documento no ERP
4. atualizar o status local
5. registrar o motivo e a resposta da operacao

### Fluxo de sincronizacao de dados

1. autenticar
2. consultar dados no ERP
3. transformar os dados para o modelo local
4. persistir no sistema local
5. se aplicavel, enviar atualizacoes complementares ao ERP

## Requisitos Funcionais da Nova Aplicacao

### 1. Persistencia local do estado da integracao

A aplicacao deve armazenar localmente:

- identificador interno da transacao
- identificador do documento no Sankhya
- tipo da operacao
- status local
- status retornado pelo ERP
- data e hora de envio
- data e hora de retorno
- payload enviado
- resposta recebida
- quantidade de tentativas
- mensagem de erro final

### 2. Idempotencia

Antes de criar um documento, a aplicacao deve verificar se a transacao ja possui vinculo com documento do ERP.

Objetivo:

- impedir duplicidade por reprocessamento
- evitar criacao repetida por timeout ou retentativa

### 3. Tratamento de status

O sistema deve separar claramente os estados:

- pendente
- autenticado
- enviado
- criado
- alterado
- confirmado
- faturado
- cancelado
- erro

### 4. Retentativa controlada

Deve haver estrategia de retentativa para erros transitorios:

- indisponibilidade momentanea
- timeout
- falha de rede
- expiracao de token

Nao deve haver retentativa cega para erros de negocio sem correcao previa.

## Requisitos de Seguranca

1. Nao armazenar credenciais em codigo-fonte.
2. Usar variaveis de ambiente ou secret manager.
3. Nao registrar `bearerToken` em logs.
4. Mascarar dados sensiveis em request e response.
5. Segregar credenciais por ambiente.
6. Usar conta tecnica exclusiva por aplicacao ou contexto de integracao.
7. Restringir quais usuarios internos podem disparar operacoes criticas.
8. Monitorar falhas de autenticacao e comportamento anomalo.

## Requisitos Arquiteturais

### Camadas recomendadas

1. `SankhyaAuthService`
2. `SankhyaApiClient`
3. `SankhyaIntegrationService`
4. `SankhyaSyncRepository`
5. `IntegrationLogService`

### Responsabilidades

**SankhyaAuthService**

- realizar login
- armazenar token
- renovar token quando necessario

**SankhyaApiClient**

- encapsular chamadas HTTP
- padronizar headers
- serializar payloads
- tratar respostas tecnicas

**SankhyaIntegrationService**

- aplicar regra de negocio
- decidir ordem de chamadas
- tratar fluxo de criacao, confirmacao, faturamento e cancelamento

**SankhyaSyncRepository**

- persistir estado local da integracao
- garantir idempotencia
- armazenar referencias entre sistema local e ERP

**IntegrationLogService**

- registrar trilha de auditoria
- armazenar erros tecnicos e funcionais
- apoiar reconciliacao e suporte

## Modelo Recomendado de Resposta Interna

### Sucesso

```json
{
  "success": true,
  "operation": "confirmar_documento",
  "erp_document_id": "123456",
  "status": "confirmed",
  "message": "Documento confirmado com sucesso",
  "raw_response": {}
}
```

### Erro

```json
{
  "success": false,
  "operation": "criar_documento",
  "erp_document_id": null,
  "status": "error",
  "message": "Tipo de operacao invalido",
  "raw_response": {}
}
```

## Recomendacoes Operacionais

1. Implementar logs tecnicos e logs de negocio separados.
2. Criar rotinas de reconciliacao para identificar divergencias entre sistema local e ERP.
3. Expor monitoramento para falhas de autenticacao, criacao, confirmacao e faturamento.
4. Definir alertas para excesso de retentativas ou cancelamentos.
5. Documentar contratos de payload por tipo de operacao.

## Conclusao

A nova aplicacao deve adotar uma integracao com o Sankhya baseada em autenticacao tecnica centralizada, uso controlado de `Bearer token`, padronizacao das chamadas de consulta e escrita, e rastreabilidade completa do ciclo documental.

O modelo recomendado separa claramente:

- autenticacao tecnica
- autorizacao interna da aplicacao
- regras de negocio
- persistencia do estado local
- observabilidade e auditoria

Esse desenho reduz duplicidade, melhora seguranca, facilita suporte e permite evolucao controlada da integracao.
