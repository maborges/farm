# Validacao do Fluxo de Aquisicao Step 97.1

**Data:** 2026-05-01  
**Escopo:** `apps/web` e fluxos correlatos ja existentes  
**Restricao:** sem alteracao de codigo, banco ou comportamento

## 1. Resumo executivo

O fluxo de aquisicao existente nao e um funil unico. Hoje o produto opera com **dois caminhos de entrada distintos**:

1. **Fluxo SaaS direto**  
   `Landing -> Login -> Register -> /onboarding/assinante -> Login automatico -> Dashboard`

2. **Fluxo de ativacao comercial/lead**  
   `Link de ativacao -> /onboarding/ativar -> Checkout Stripe -> /onboarding/sucesso -> Login -> Dashboard`

O principal problema estrutural e que a UX e a arquitetura nao contam a mesma historia:

- a landing vende trial e "comecar gratis", mas envia para `/login`, nao para `/register`;
- o cadastro principal cria tenant e assinatura direto, mas joga o usuario para `/dashboard` sem onboarding real orientado;
- existe onboarding tecnico (`/onboarding/configurar`), mas o guard depende de um campo que nao esta sendo populado no store do frontend;
- existe tambem um endpoint `/onboarding/status`, mas ele nao esta sendo usado pelo frontend.

Resultado: o sistema tem capacidade tecnica para criar conta e autenticar, mas **nao transforma o primeiro acesso em geracao clara de valor**.

## 2. Fluxo real mapeado

### 2.1 Landing

Arquivo-base: `apps/web/src/app/page.tsx`

Fluxo atual:

- CTA `Entrar` -> `/login`
- CTA `Comecar gratis` -> `/login`
- CTA `Ver demonstracao` -> `/login`
- CTA dos planos -> `/login`

Observacao:

- a landing nao leva o usuario diretamente para `/register`;
- o discurso comercial sugere inicio imediato, mas o destino padrao e a tela de login.

### 2.2 Login

Arquivos-base:

- `apps/web/src/app/(auth)/login/page.tsx`
- `apps/web/src/components/auth/login-form.tsx`

Fluxo atual:

- usuario informa email e senha;
- frontend chama `POST /auth/login`;
- em seguida chama `GET /auth/me`;
- define cookies e estado do store;
- redireciona para `/dashboard`.

Pontos relevantes:

- o login escolhe o primeiro tenant retornado por `/auth/me` como contexto padrao;
- se for superadmin sem tenant, o dashboard mostra estado especifico de backoffice;
- existe link secundario para `/register`;
- existe link para `/forgot-password`.

### 2.3 Cadastro

Arquivos-base:

- `apps/web/src/app/(auth)/register/page.tsx`
- `apps/web/src/components/auth/register-form.tsx`
- `services/api/core/routers/onboarding.py`
- `services/api/core/services/onboarding_service.py`

Fluxo atual:

1. Step 1: dados pessoais e senha.
2. Step 2: nome do produtor, CPF/CNPJ opcional, escolha de plano.
3. Validacao opcional de documento em `GET /onboarding/verificar-documento/{documento}`.
4. Criacao efetiva em `POST /onboarding/assinante`.
5. Backend cria:
   - usuario global;
   - tenant;
   - vinculo owner;
   - assinatura;
   - fatura apenas em cenarios pagos com trial;
6. Backend autentica imediatamente e devolve token.
7. Frontend chama `/auth/me`, seta sessao e envia usuario para `/dashboard`.

Observacao importante:

- o cadastro visivel na UI **nao usa** `POST /auth/register`;
- o endpoint `POST /auth/register` existe, mas cria so usuario global e o proprio comentario no service registra que **nao cria tenant padrao**.

### 2.4 Primeiro acesso

Arquivos-base:

- `apps/web/src/app/(dashboard)/layout.tsx`
- `apps/web/src/components/auth/session-guard.tsx`
- `apps/web/src/components/auth/onboarding-guard.tsx`
- `apps/web/src/app/(dashboard)/dashboard/page.tsx`

Fluxo esperado:

- `SessionGuard` exige token;
- `OnboardingGuard` deveria mandar para `/onboarding/configurar` se `tenant.onboarding_configuracao_completo === false`;
- usuario autenticado chega em `/dashboard`.

Fluxo real observado por leitura:

- o store grava `tenant` manualmente no login e no register;
- esse `tenant` inclui `id`, `nome`, `documento`, `slug`, `dominio_customizado`, `branding`;
- o campo `onboarding_configuracao_completo` existe no tipo TS, mas **nao e preenchido** no `setSession` do login nem do register;
- portanto o `OnboardingGuard` depende de um sinal que, no fluxo principal analisado, nao entra no payload.

Conclusao:

- o onboarding tecnico existe, mas o disparo automatico dele aparenta estar fragil ou inoperante no fluxo principal.

### 2.5 Dashboard / onboarding

Arquivos-base:

- `apps/web/src/app/onboarding/configurar/page.tsx`
- `services/api/core/routers/configuration.py`
- `services/api/core/routers/onboarding.py`

O sistema tem dois conceitos de onboarding:

1. **Onboarding comercial de aquisicao**
   - cadastro/ativacao da conta
   - escolha de plano
   - trial ou checkout

2. **Onboarding operacional**
   - ano agricola
   - unidade de area
   - fuso
   - moeda
   - categorias padrao

Problema:

- o onboarding operacional existe em `/onboarding/configurar`;
- o backend marca `tenant.onboarding_configuracao_completo = True` ao concluir;
- tambem existe `GET /onboarding/status`;
- mas a UX principal nao orienta o usuario explicitamente para isso no primeiro acesso.

## 3. Redirecionamentos e telas intermediarias

### 3.1 Fluxo SaaS direto

`/` -> `/login` -> `/register` -> `POST /onboarding/assinante` -> `/dashboard`

Telas intermediarias:

- landing
- login
- register 3 passos
- dashboard

Redirecionamentos:

- landing para login
- login para dashboard
- register para dashboard

### 3.2 Fluxo de ativacao comercial

`/onboarding/ativar?token=...` -> checkout Stripe -> `/onboarding/sucesso` -> `/login` -> `/dashboard`

Telas intermediarias:

- ativacao com confirmacao de dados
- checkout externo
- sucesso
- login
- dashboard

Redirecionamentos:

- ativacao para checkout externo
- sucesso para login
- login para dashboard

### 3.3 Fluxo de autenticacao protegida

Qualquer rota protegida em `(dashboard)`:

- sem token -> `SessionGuard` redireciona para `/login`
- com token -> permanece no dashboard
- com tenant marcado como onboarding incompleto -> deveria ir para `/onboarding/configurar`, mas isso depende de dado hoje nao claramente abastecido

## 4. Dependencias de dados

### 4.1 Para login funcionar

Dependencias:

- usuario global existente;
- `senha_hash` valida;
- usuario ativo;
- se houver tenant ativo, perfil e contexto acessivel;
- assinatura para enriquecer `plan_tier`, limites e modulos.

### 4.2 Para cadastro principal funcionar

Dependencias:

- plano ativo em `/billing/plans`;
- perfil owner padrao sem tenant;
- servico de onboarding e auth operacionais;
- disponibilidade de documento, se informado.

### 4.3 Para o usuario ver valor apos entrar

Dependencias:

- tenant ativo;
- ao menos um contexto retornado em `/auth/me`;
- idealmente ao menos uma fazenda;
- preferencialmente onboarding operacional concluido;
- dados iniciais ou CTA claro para primeira acao.

## 5. Criacao automatica de tenant e estado inicial

## 5.1 Cadastro principal

No fluxo de `/onboarding/assinante`, sim:

- tenant e criado automaticamente;
- usuario vira owner;
- assinatura e criada;
- usuario ja entra autenticado.

Porem:

- o service `register_new_tenant()` **nao cria fazenda inicial**;
- a primeira fazenda autorizada depende do que existir depois;
- o store do frontend monta `defaultTenant.fazendas.map(...)`, mas isso pode resultar em lista vazia.

Impacto:

- o usuario pode entrar com tenant criado, assinatura criada, mas sem estrutura operacional pronta para uso imediato.

## 5.2 Cadastro tecnico `/auth/register`

No endpoint `POST /auth/register`, nao:

- cria apenas usuario global;
- nao cria tenant;
- nao cria assinatura;
- nao gera valor de produto sozinho.

Hoje esse caminho parece ser secundario ou legado para aquisicao principal.

## 6. Avaliacao de UX

### 6.1 Existe onboarding?

**Sim, tecnicamente existe**, mas esta fragmentado:

- onboarding comercial no cadastro/ativacao;
- onboarding operacional em `/onboarding/configurar`;
- onboarding por convite em `/onboarding/convites/...`.

### 6.2 Existe orientacao clara?

**Parcial e insuficiente.**

- o register mostra steps visuais;
- a ativacao por token tambem explica o passo atual;
- mas depois do cadastro/login, o usuario e jogado para um dashboard generico.

### 6.3 Existe CTA de primeira acao?

**Fraco no primeiro acesso.**

O dashboard principal mostra:

- modulos;
- cards com upsell;
- links para relatorios.

Mas nao mostra, de forma evidente:

- "cadastre sua primeira propriedade";
- "configure sua fazenda";
- "conclua seu onboarding";
- "crie sua primeira safra";
- "lance seu primeiro movimento de estoque".

Resultado:

- o sistema assume maturidade operacional do usuario logo no primeiro acesso;
- a geracao de valor nao e guiada.

## 7. Problemas identificados

### 7.1 CRITICO

#### 1. Landing direciona "Comecar gratis" para login, nao para cadastro

Impacto:

- adiciona friccao logo na primeira acao;
- usuario novo chega numa tela pensada para usuario existente;
- reduz taxa de conversao de topo de funil.

Base:

- `apps/web/src/app/page.tsx`

#### 2. OnboardingGuard depende de `tenant.onboarding_configuracao_completo`, mas o store nao popula esse campo no fluxo principal

Impacto:

- onboarding operacional pode ser pulado sem intencao;
- usuario entra no dashboard sem configuracao inicial;
- a plataforma perde a chance de orientar o primeiro valor.

Base:

- `apps/web/src/components/auth/onboarding-guard.tsx`
- `apps/web/src/components/auth/login-form.tsx`
- `apps/web/src/components/auth/register-form.tsx`
- `apps/web/src/types/global.d.ts`

#### 3. Cadastro cria conta e assinatura, mas nao garante estrutura operacional inicial visivel

Impacto:

- usuario entra "com conta pronta", mas sem fazenda, sem dados e sem CTA claro;
- percepcao de produto vazio no primeiro acesso.

Base:

- `services/api/core/services/onboarding_service.py`
- `apps/web/src/app/(dashboard)/dashboard/page.tsx`

### 7.2 ALTO

#### 4. Existem dois fluxos principais de aquisicao com narrativas diferentes

Fluxos:

- cadastro direto com trial / assinatura;
- ativacao por token com checkout.

Impacto:

- naming, expectativa e jornada ficam inconsistentes;
- onboarding, trial e pagamento nao seguem a mesma historia de produto.

#### 5. Dashboard inicial e um hub de modulos, nao uma experiencia de primeiro valor

Impacto:

- exige que o usuario entenda sozinho por onde comecar;
- aumenta abandono no primeiro acesso;
- dificulta demonstrar valor em menos de 5 minutos.

#### 6. O cadastro pede muitas informacoes antes de mostrar valor

Itens:

- dados pessoais;
- usuario;
- senha;
- CPF;
- telefone;
- nome do produtor;
- CPF/CNPJ;
- plano;
- ciclo.

Impacto:

- o formulario vira pesado para topo de funil;
- a promessa de "dashboard pronto em segundos" fica fragil.

### 7.3 MEDIO

#### 7. Existe endpoint `/onboarding/status`, mas ele nao e usado para conduzir a UI

Impacto:

- duplicidade conceitual;
- risco de divergencia entre estado real do backend e redirecionamento do frontend.

#### 8. O caminho para cadastro esta escondido na landing e depende de passar antes pelo login

Impacto:

- navegacao pouco intuitiva;
- descoberta ruim para visitante frio.

#### 9. O fluxo de ativacao termina em `/login`, nao em entrada automatica ou retomada contextual

Impacto:

- adiciona um passo a mais apos sucesso comercial;
- quebra continuidade entre pagamento e uso.

### 7.4 BAIXO

#### 10. Naming de onboarding e aquisicao ainda esta disperso

Exemplos:

- `register`
- `assinante`
- `ativar`
- `configurar`
- `create-subscription`

Impacto:

- aumenta custo cognitivo interno e futuro custo de refinamento de UX.

## 8. Classificacao geral de friccao e abandono

| Etapa | Situacao atual | Risco |
|---|---|---|
| Landing -> primeira acao | CTA principal leva para login | ALTO |
| Login de usuario novo | tela correta para existente, errada para aquisicao | ALTO |
| Cadastro | robusto, mas longo | ALTO |
| Pos-cadastro | entra no dashboard sem orientacao | CRITICO |
| Onboarding operacional | existe, mas sem garantia de disparo | CRITICO |
| Pos-pagamento no fluxo de ativacao | volta para login | MEDIO |

## 9. Conclusoes praticas

### 9.1 O que ja funciona

- autenticacao principal existe;
- cadastro com criacao de tenant e assinatura existe;
- trial/plano existe;
- ativacao via token existe;
- onboarding operacional existe;
- dashboard protegido e funcional.

### 9.2 O que falta para o fluxo virar aquisicao SaaS forte

- um caminho unico e claro de entrada;
- reduzir ambiguidade entre login e cadastro;
- garantir onboarding real apos cadastro;
- converter primeiro acesso em primeira acao concreta;
- evitar dashboard generico antes da geracao de valor.

## 10. Recomendacao priorizada para proximo step

### Prioridade 1

- alinhar CTA principal da landing com cadastro real, nao login.

### Prioridade 2

- corrigir a fonte de verdade do onboarding inicial:
  - ou popular `onboarding_configuracao_completo` no tenant do store;
  - ou usar `/onboarding/status` como criterio real.

### Prioridade 3

- criar jornada de primeiro valor apos cadastro:
  - concluir configuracao;
  - cadastrar primeira propriedade/fazenda;
  - criar primeira safra ou primeiro centro operacional;
  - registrar primeira operacao.

### Prioridade 4

- revisar o cadastro para reduzir friccao de topo de funil sem quebrar billing.

## 11. Diagnostico final

O sistema **nao esta bloqueado tecnicamente para aquisicao**, mas o fluxo atual ainda e mais um conjunto de caminhos funcionais do que um funil SaaS otimizado.

Hoje o maior risco nao e falta de tela. O maior risco e este:

> o usuario consegue entrar, mas nao fica obvio como gerar valor imediatamente.

Esse e o ponto central de abandono identificado nesta validacao.
