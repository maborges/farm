# Sankhya ERP - Guia de preenchimento dos campos da tela de integracao

**Tela:** `/dashboard/settings/integracoes/erp`
**Objetivo:** orientar o que informar em cada campo do bloco `Modelo de conexao`
**Escopo:** apenas documentacao. Nenhum arquivo de fonte, banco ou migracao foi alterado.

---

## 1. Quando usar este guia

Use este guia ao configurar a integracao com o ERP Sankhya no console do tenant.

O sistema trabalha com dois modos:

1. **Gateway atual** - modelo principal recomendado.
2. **Legado** - mantido apenas para compatibilidade historica.

Na pratica, se voce estiver iniciando uma configuracao nova, o mais comum e preencher os campos do Gateway atual e deixar os campos legados vazios.

---

## 2. Campos do "Modelo de conexao"

### 2.1 Ambiente

**Campo na tela:** `Ambiente`

**O que informar:**
- O ambiente da integracao no Sankhya.
- Exemplos comuns: `producao`, `homologacao`, `teste`.

**Observacao:**
- Esse campo define o contexto operacional da conexao.
- Use o valor que represente exatamente o ambiente fornecido pelo time responsavel pelo Sankhya.

### 2.2 Intervalo de atualizacao (segundos)

**Campo na tela:** `Intervalo de atualizacao (segundos)`

**O que informar:**
- A frequencia, em segundos, para rotinas automaticas de sincronizacao.

**Recomendacao pratica:**
- O valor padrao no sistema e `900` segundos, ou seja, 15 minutos.

**Observacao:**
- Esse campo e interno do AgroSaaS e nao e uma credencial do Sankhya.

### 2.3 URL base do gateway

**Campo na tela:** `URL base do gateway`

**O que informar:**
- A URL base do Gateway Sankhya.

**Exemplo:**
- `https://gateway.sankhya.com.br`

**Observacao:**
- Se a sua empresa usa uma URL diferente, informe o endereco oficial recebido para a sua integracao.

### 2.4 URL de autenticacao

**Campo na tela:** `URL de autenticação`

**O que informar:**
- O endpoint usado para autenticar a integracao.

**Exemplo:**
- `https://gateway.sankhya.com.br/authenticate`

**Observacao:**
- Em cenarios legados, pode existir fluxo com `/login`.
- Para configuracao nova, siga o endpoint de autenticacao do Gateway.

### 2.5 Identificador do cliente

**Campo na tela:** `Identificador do cliente`

**O que informar:**
- O `client_id` da aplicacao/integracao no Gateway Sankhya.

**Observacao:**
- Esse valor normalmente e fornecido pelo ambiente de integracao do ERP ou pela equipe responsavel pelo acesso tecnico.
- Nao use o nome do usuario humano aqui.

### 2.6 Senha

**Campo na tela:** `Senha`

**O que informar:**
- O `client_secret` da integracao no Gateway Sankhya.

**Observacao:**
- Este campo e sensivel.
- O sistema mascara o valor e nao exibe a senha em claro.
- Se a integracao ja estiver configurada e voce nao quiser trocar a senha, deixe o campo em branco.

### 2.7 X-Token

**Campo na tela:** `X-Token`

**O que informar:**
- O `x_token` exigido pelo Gateway Sankhya no fluxo atual.

**Observacao:**
- Este valor tambem e sensivel.
- Se a integracao ja tiver um token valido e voce nao quiser alterar, deixe em branco.

### 2.8 Token do login legado

**Campo na tela:** `Token do login legado`

**O que informar:**
- O `token` do modelo legado de autenticacao.

**Quando usar:**
- Apenas se o seu ambiente Sankhya ainda estiver no fluxo historico de login legado.

**Observacao:**
- Em configuracoes novas, normalmente este campo nao e usado.

### 2.9 AppKey do login legado

**Campo na tela:** `AppKey do login legado`

**O que informar:**
- A `appkey` do modelo legado de autenticacao.

**Quando usar:**
- Apenas no fluxo legado de login.

**Observacao:**
- Em configuracoes novas, normalmente este campo nao e usado.

---

## 3. Regra pratica de preenchimento

### Configuracao nova recomendada

Preencha:
- `Ambiente`
- `Intervalo de atualizacao (segundos)`
- `URL base do gateway`
- `URL de autenticacao`
- `Identificador do cliente`
- `Senha`
- `X-Token`

Deixe vazio:
- `Token do login legado`
- `AppKey do login legado`

### Configuracao legada

Preencha somente se o ambiente ainda depender do login historico:
- `Ambiente`
- `URL de autenticacao`
- `Token do login legado`
- `AppKey do login legado`
- e, se aplicavel, os demais campos historicos ja cadastrados no tenant

---

## 4. Onde ver os logs

### 4.1 Logs da integracao Sankhya

Na propria tela `/dashboard/settings/integracoes/erp`, veja:

- **Historico complementar**
- **Linha do tempo operacional**

Essas areas mostram os registros recentes de sincronizacao e os eventos operacionais da integracao.

### 4.2 Log de acesso do usuario na plataforma

Se a duvida for sobre acesso de usuarios ao sistema, use:

- `/dashboard/settings/sessoes` para suas sessoes e as da equipe
- `/dashboard/backoffice/audit` para auditoria administrativa

### 4.3 Log tecnico da integracao no backend

No backend, a integracao expoe os logs de sincronizacao em:

- `GET /integracoes/sankhya/logs`

---

## 5. Resumo rapido

| Campo | O que informar |
|---|---|
| Ambiente | ambiente do ERP, como `producao` ou `homologacao` |
| Intervalo de atualizacao | segundos entre sincronizacoes; padrao interno `900` |
| URL base do gateway | URL base do Gateway Sankhya |
| URL de autenticacao | endpoint de autenticacao, normalmente `/authenticate` |
| Identificador do cliente | `client_id` da integracao |
| Senha | `client_secret` da integracao |
| X-Token | `x_token` do Gateway |
| Token do login legado | token apenas do fluxo historico |
| AppKey do login legado | appkey apenas do fluxo historico |

---

## 6. Observacao final

Se houver qualquer divergencia entre o valor esperado pelo ERP e o valor exibido na tela, priorize a configuracao oficial fornecida pela equipe responsavel pelo Sankhya no seu ambiente.
