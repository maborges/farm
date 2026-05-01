# Validacao Real do Onboarding Step 97.3

**Data:** 2026-05-01  
**Objetivo:** validar ponta a ponta o fluxo real `landing -> register -> onboarding -> dashboard -> primeira acao`.  
**Resultado geral:** **falha apos o onboarding**, por inconsistencia entre o wizard de configuracao inicial e a regra do endpoint `GET /api/v1/onboarding/status`.

## 1. Escopo executado

Validacao realizada em ambiente local com:

- frontend `apps/web` em `http://localhost:3000`
- backend `services/api` via `http://127.0.0.1:8000/api/v1`
- navegador headless real com Playwright
- sem alteracao de schema ou regra de negocio durante a validacao

Observacao:

- o bug anterior de cadastro com `documento = ''` foi corrigido antes desta rodada;
- esta execucao foi feita ja com a migration `step27_tenant_documento_nullable` aplicada.

## 2. Preparacao do ambiente

Validacoes iniciais:

- `GET http://127.0.0.1:8000/api/v1/billing/plans` -> `200`
- `GET http://localhost:3000/api/v1/billing/plans` -> `200`
- `GET http://localhost:3000/register` -> `200`

Conclusao:

- backend e proxy do frontend estavam operacionais;
- o fluxo real podia ser executado a partir da landing.

## 3. Fluxo executado passo a passo

### 3.1 Landing

Executado:

- abrir `http://localhost:3000/`
- clicar no CTA `Comecar gratis`

Resultado:

- sucesso
- redirect para `http://localhost:3000/register`

### 3.2 Cadastro

Executado:

- preenchimento real do formulario de cadastro
- selecao de plano
- confirmacao de criacao da conta

Dados usados:

- email: `test+onboarding-20260501150335@agrosaas.com`
- username: `onb05011503`
- senha: segura de teste
- nome do produtor: `Teste Step97.3 20260501150335`
- documento do produtor: em branco

Resultado:

- sucesso
- conta criada sem erro `500`
- redirect para `/onboarding/configurar`

Evidencia:

- `POST /api/v1/onboarding/assinante` deixou de falhar
- a navegacao avancou para `http://localhost:3000/onboarding/configurar`

### 3.3 Pos-cadastro

Executado:

- validacao do redirect imediato apos criacao da conta

Resultado:

- sucesso
- usuario novo nao caiu direto no dashboard
- foi corretamente direcionado para `/onboarding/configurar`

### 3.4 Onboarding

Executado:

- avancar pelas 5 etapas do wizard de configuracao inicial
- concluir em `Concluir Configuracao`

Resultado aparente:

- sucesso de UI
- redirect temporario para `/dashboard`

Evidencia:

- a pagina navegou para `http://localhost:3000/dashboard`

### 3.5 Pos-onboarding

Resultado real:

- **falha critica**

Comportamento observado:

- apos chegar em `/dashboard`, o fluxo nao estabilizou na tela
- a navegacao voltou para `http://localhost:3000/onboarding/configurar`
- o bloco de primeiro valor do dashboard nao chegou a ficar utilizavel

Ponto exato da quebra:

- o dashboard e alcancado
- mas o guard de onboarding volta a considerar o tenant como incompleto
- o usuario fica preso no ciclo `onboarding/configurar -> dashboard -> onboarding/configurar`

### 3.6 Dashboard e primeira acao

Nao validados com sucesso.

Motivo:

- o dashboard nao permaneceu carregado tempo suficiente para executar o CTA de primeiro valor
- nao foi possivel concluir `Criar fazenda`, `Criar safra` ou `Criar operacao` dentro do fluxo principal

## 4. Causa identificada

### 4.1 Regra do endpoint `GET /api/v1/onboarding/status`

O backend hoje considera:

- `etapa1_produtor`: tenant ativo existe
- `etapa2_propriedade`: existe ao menos 1 fazenda ativa
- `etapa3_equipe`: existe mais de 1 usuario ativo
- `completo = etapa1 and etapa2`

Ou seja:

- **o onboarding so e considerado completo se o tenant ja tiver uma fazenda**

### 4.2 O wizard `POST /api/v1/config/onboarding/configurar`

O wizard atual faz:

- salvar configuracoes gerais
- opcionalmente carregar categorias padrao
- marcar `tenant.onboarding_configuracao_completo = True`

O wizard **nao cria fazenda**.

Consequencia:

- a UI conclui o onboarding de configuracao
- mas o endpoint `GET /api/v1/onboarding/status` continua retornando incompleto
- o `OnboardingGuard` volta a redirecionar para `/onboarding/configurar`

## 5. Evidencias tecnicas

### 5.1 Navegacao observada

- `URL_LANDING=http://localhost:3000/`
- `URL_REGISTER=http://localhost:3000/register`
- `URL_ONBOARDING=http://localhost:3000/onboarding/configurar`
- `URL_DASHBOARD=http://localhost:3000/dashboard`
- estado final da execucao: `CURRENT_URL=http://localhost:3000/onboarding/configurar`

### 5.2 Requests relevantes

- `GET /api/v1/billing/plans` -> `200`
- `POST /api/v1/onboarding/assinante` -> sucesso funcional
- `POST /api/v1/config/onboarding/configurar` -> sucesso funcional implícito pela navegacao para `/dashboard`

### 5.3 Observacao sobre `GET /api/v1/onboarding/status`

As chamadas manuais feitas dentro do browser por `fetch()` simples retornaram `401` porque nao carregavam o header de autenticacao do app store. Isso **nao** foi a causa-raiz da falha principal.

A causa-raiz foi confirmada pela leitura do backend:

- `services/api/core/routers/onboarding.py`
- `services/api/core/routers/configuration.py`

## 6. Problemas encontrados

### CRITICO

#### 1. Fluxo de onboarding entra em loop logico apos concluir a configuracao inicial

Sintoma:

- usuario conclui o wizard
- e redirecionado para `/dashboard`
- mas o guard o manda de volta para `/onboarding/configurar`

Impacto:

- bloqueia a chegada estavel ao dashboard
- impede a primeira geracao de valor
- quebra o fluxo de aquisicao mesmo com cadastro bem-sucedido

### CRITICO

#### 2. Definicao de onboarding completo nao bate com o que o wizard realmente coleta

Sintoma:

- `onboarding/status` exige fazenda ativa
- `onboarding/configurar` nao cria fazenda

Impacto:

- o sistema exige um prerequisito que o proprio wizard nao resolve
- usuario novo fica preso sem caminho consistente para completar a jornada

### BAIXO

#### 3. Requests estaticas abortadas apareceram no navegador, mas nao foram o bloqueio principal

Sintoma:

- alguns `net::ERR_ABORTED` em assets/chunks

Impacto:

- ruido de runtime
- nao foi a causa da falha decisiva nesta rodada

## 7. Classificacao final

| Etapa | Status | Severidade |
|---|---|---|
| Landing | ok | BAIXO |
| CTA `Comecar gratis -> /register` | ok | BAIXO |
| Cadastro real | ok | BAIXO |
| Redirect pos-cadastro para onboarding | ok | BAIXO |
| Conclusao visual do onboarding | ok | BAIXO |
| Permanencia estavel no dashboard | falhou | CRITICO |
| CTA de primeiro valor | nao validado | ALTO |
| Primeira acao real | nao validada | ALTO |

## 8. Usuario de teste e cleanup

Usuario criado:

- `test+onboarding-20260501150335@agrosaas.com`

Status:

- conta criada com sucesso
- mantida na base como dado de teste identificavel pelo prefixo `test+onboarding-`

Cleanup:

- nao executado nesta rodada
- registro ficou marcado explicitamente como teste pelo proprio email

## 9. Conclusao

O Step 97.3 **ainda nao foi validado com sucesso**.

O bug anterior de cadastro foi resolvido:

- o usuario ja consegue sair da landing
- preencher o cadastro
- criar conta real
- entrar no wizard de onboarding

A nova falha real agora esta depois disso:

- o onboarding de configuracao inicial termina
- mas o backend so considera onboarding completo quando ja existe fazenda ativa
- como o wizard nao cria fazenda, o `OnboardingGuard` volta a redirecionar para `/onboarding/configurar`

Estado atual:

- problema de ambiente: resolvido
- problema de cadastro com documento vazio: resolvido
- problema bloqueante atual: **inconsistencia entre o criterio de `onboarding/status` e o escopo do wizard de onboarding**

Conclusao pratica:

- o sistema ainda **nao esta pronto** para a evolucao pos-onboarding
- o proximo ajuste necessario deve alinhar a definicao de onboarding completo com a jornada real do usuario novo
