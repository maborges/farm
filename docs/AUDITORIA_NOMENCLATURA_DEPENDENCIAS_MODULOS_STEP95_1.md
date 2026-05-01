# Auditoria de Nomenclatura e Dependencias dos Modulos SaaS — Step 95.1

## 1. Objetivo

Mapear como modulos, planos, pacotes, tiers, features, permissoes e slugs tecnicos estao nomeados hoje no sistema, identificar dependencias estruturais entre eles e estimar o risco de qualquer melhoria futura de naming.

Escopo desta auditoria:

- sem alteracao de codigo;
- sem alteracao de schema;
- sem alteracao de banco;
- sem alteracao de frontend;
- apenas mapeamento, classificacao e recomendacoes.

## 2. Resumo Executivo

O runtime atual do SaaS se apoia em dois eixos canônicos:

1. `modulos_inclusos` no plano/assinatura para controlar quais modulos estao contratados;
2. `plan_tier` para controlar profundidade de acesso, especialmente features mais avancadas.

Hoje existem quatro camadas de nomenclatura convivendo em paralelo:

- identificadores tecnicos de modulo como `A1_PLANEJAMENTO`, `P1_REBANHO`, `F1_TESOURARIA`;
- labels comerciais e de UI como `A1 Planejamento`, `Profissional`, `Enterprise`;
- nomenclatura de pacote no frontend como `BASICO`, `PROFISSIONAL`, `EMPRESA`;
- material legado/historico com termos como `Essencial`, `Premium`, `Bronze/Prata/Ouro`, `Básico/Pro`.

Conclusao principal:

- `A1_PLANEJAMENTO` e demais codigos por letra+numero sao hoje identificadores tecnicos canônicos de modulo;
- `BASICO`, `PROFISSIONAL`, `ENTERPRISE` sao hoje os tiers canônicos de runtime;
- `PREMIUM` e alias legado de compatibilidade;
- nomes comerciais de pacote/plano ainda nao estao unificados entre backend, frontend, seeds e documentacao.

Consequencia pratica:

- mudar labels comerciais e relativamente barato;
- mudar `plan_tier`, `modulos_inclusos`, codigos de modulo, permissoes ou contratos de billing e caro e exige migration/compatibilidade.

## 3. Fontes Inspecionadas

Fontes principais de runtime:

- `services/api/core/constants.py`
- `services/api/core/dependencies.py`
- `services/api/core/models/billing.py`
- `services/api/core/routers/billing.py`
- `services/api/core/routers/backoffice.py`
- `services/api/core/services/mudanca_plano_service.py`
- `apps/web/src/lib/constants/modulos.ts`
- `apps/web/src/lib/constants/planos.ts`
- `apps/web/src/lib/constants/pacotes.ts`
- `apps/web/src/lib/permissions.ts`
- `apps/web/src/lib/permission-catalog.ts`
- `apps/web/src/hooks/use-has-module.ts`
- `apps/web/src/hooks/use-has-tier.ts`
- `apps/web/src/components/shared/module-gate.tsx`
- `apps/web/src/lib/stores/app-store.ts`
- `apps/web/src/types/global.d.ts`

Fontes de compatibilidade, seeds ou historico:

- `services/api/scripts/seed_plans.py`
- `services/api/scripts/seed_plan_pricing.py`
- `services/api/migrations/versions/4492badc2748_add_plan_changes_and_dynamic_pricing.py`
- `services/api/migrations/versions/5563c3f1a6d4_add_plan_tier_limits_crm_sessions.py`
- `services/api/migrations/versions/rbac_granular_permissions.py`
- `docs/contexts/step35-enterprise-tier-normalization-context.md`
- `docs/contexts/core/planos-assinatura.md`
- `docs/PRODUTO_SAAS_ESTRUTURA_COMERCIAL_STEP94.md`
- `docs/PRICING_E_CONVERSAO_STEP95.md`

## 4. Mapa das Nomenclaturas Existentes

### 4.1 Modulos

Fonte canônica de runtime:

- backend: `services/api/core/constants.py` classe `Modulos`
- frontend: `apps/web/src/lib/constants/modulos.ts`
- types: `apps/web/src/types/global.d.ts`

Padrao atual:

- Agricola: `A1_PLANEJAMENTO`, `A2_CAMPO`, `A3_DEFENSIVOS`, `A4_PRECISAO`, `A5_COLHEITA`
- Pecuaria: `P1_REBANHO`, `P2_GENETICA`, `P3_CONFINAMENTO`, `P4_LEITE`
- Financeiro: `F1_TESOURARIA`, `F2_CUSTOS_ABC`, `F3_FISCAL`, `F4_HEDGING`
- Operacional: `O1_FROTA`, `O2_ESTOQUE`, `O3_COMPRAS`
- Core/imoveis/RH/ambiental/extensoes: `CORE`, `IMOVEIS_*`, `RH*`, `AM*`, `EXT_*`

Classificacao:

- `A1_PLANEJAMENTO`, `P1_REBANHO`, `F1_TESOURARIA` etc.: identificador tecnico, enum implícito, modulo contratado
- `Planejamento de Safra`, `Controle de Rebanho`, `Tesouraria`: label comercial/UI

### 4.2 Tiers

Fonte canônica de runtime:

- backend: `services/api/core/constants.py` classe `PlanTier`
- frontend: `apps/web/src/lib/constants/planos.ts`

Tiers atuais:

- `BASICO`
- `PROFISSIONAL`
- `ENTERPRISE`
- `PREMIUM` como alias legado para `ENTERPRISE`

Classificacao:

- `BASICO`, `PROFISSIONAL`, `ENTERPRISE`: enum tecnico e tier/plano
- `PREMIUM`: alias tecnico legado de compatibilidade
- `Básico`, `Profissional`, `Enterprise`: labels de UI/comercial

### 4.3 Planos

Fonte principal:

- modelo: `services/api/core/models/billing.py` tabela `planos_assinatura`
- CRUD/API: `services/api/core/routers/backoffice.py`, `services/api/core/routers/billing.py`

Campos relevantes:

- `nome`
- `descricao`
- `modulos_inclusos`
- `plan_tier`
- `preco_mensal`
- `preco_anual`
- `limite_usuarios_minimo`
- `limite_usuarios_maximo`
- `limite_hectares`
- `max_fazendas`
- `disponivel_site`
- `disponivel_crm`

Classificacao:

- `PlanoAssinatura`: entidade tecnica de billing
- `nome`: label comercial do plano
- `plan_tier`: tier tecnico
- `modulos_inclusos`: contrato tecnico de modulos

### 4.4 Pacotes

Fonte principal:

- `apps/web/src/lib/constants/pacotes.ts`

Pacotes frontend:

- `BASICO`
- `PROFISSIONAL`
- `EMPRESA`

Relacao declarada:

- `PacoteId` e um conceito frontend/comercial
- cada pacote associa `tier` + lista de `modulos` + preco + limites

Classificacao:

- `BASICO`, `PROFISSIONAL`, `EMPRESA` nesse arquivo: pacote comercial frontend
- `nome: "Básico" | "Profissional" | "Empresa"`: label comercial

Observacao:

- `EMPRESA` nao e o mesmo identificador do tier `ENTERPRISE`, mas representa esse tier no frontend de pacotes.

### 4.5 Features

Formas observadas:

- recursos granulares no catalogo de permissoes, ex. `agricola:planejamento`, `financeiro:dre`, `estoque:lotes`
- tracking e prompts de monetizacao no frontend, ex. `agricola.beneficiamento`, `agricola.rastreabilidade.lotes`

Classificacao:

- chaves como `agricola:planejamento`: recurso/permissao
- chaves como `agricola.beneficiamento`: identificador de feature em UI/telemetria

### 4.6 Permissoes

Fontes:

- `apps/web/src/lib/permissions.ts`
- `apps/web/src/lib/permission-catalog.ts`
- migration `rbac_granular_permissions.py`

Padrao atual:

- backoffice: `backoffice:plans:view`
- tenant: `tenant:billing:view`
- catalogo granular por dominio: `agricola:planejamento:create`, `estoque:saldo:view`

Classificacao:

- strings `modulo:recurso:acao`: permissao tecnica
- `granted`, `permissions`, wildcards `tenant:*`: contrato tecnico de RBAC

### 4.7 Slugs e codigos tecnicos

Encontrados:

- modulos: `A1_PLANEJAMENTO`, `O2_ESTOQUE`, `EXT_ERP`
- tiers: `BASICO`, `PROFISSIONAL`, `ENTERPRISE`
- tipo de assinatura: `TENANT`, `ADICIONAL`
- ciclo: `MENSAL`, `ANUAL`
- status: `ATIVA`, `TRIAL`, `PENDENTE_PAGAMENTO`, `SUSPENSA`, `CANCELADA`, `BLOQUEADA`
- mudanca: `UPGRADE_PLANO`, `DOWNGRADE_COMPLETO` etc.

Classificacao:

- todos acima sao identificadores tecnicos de runtime e/ou persistencia

## 5. Onde os Termos Solicitados Aparecem

### 5.1 `A1`

Aparece como:

- abreviacao de modulo agricola em docs e UI
- parte do identificador tecnico `A1_PLANEJAMENTO`
- label comercial `A1 Planejamento` em Step 94/95 e em paginas da landing/billing

Classificacao dominante:

- `A1` sozinho: label abreviado e documentacao
- `A1_PLANEJAMENTO`: identificador tecnico

### 5.2 `A1_PLANEJAMENTO`

Aparece em:

- `services/api/core/constants.py`
- `apps/web/src/lib/constants/modulos.ts`
- `services/api/core/routers/reports.py`
- `ModuleGate` e layouts/paginas agricolas

Classificacao:

- identificador tecnico canônico de modulo
- modulo contratado
- dependencia de gate

### 5.3 `Básico`

Aparece em:

- label de tier no frontend
- `apps/web/src/lib/constants/pacotes.ts`
- `seed_plan_pricing.py`
- UI de billing

Classificacao:

- label comercial/UI
- em alguns pontos, nome de pacote/plano

### 5.4 `Essencial`

Aparece majoritariamente em:

- `docs/architecture/AgroSaaS-Manual.md`
- `docs/contexts/core/planos-assinatura.md`
- material estrategico/funcional legado

Classificacao:

- documentacao e naming historico
- nao e o tier canônico atual de runtime

### 5.5 `Profissional`

Aparece em:

- tier tecnico `PROFISSIONAL`
- label comercial `Profissional`
- pacote frontend `PROFISSIONAL`

Classificacao:

- tecnico e comercial ao mesmo tempo, com acoplamento alto

### 5.6 `Premium`

Aparece em:

- `PlanTier.PREMIUM` e alias legado
- docs de normalizacao do Step 35
- alguns trechos de teste/comentario/UI historicos

Classificacao:

- alias tecnico legado
- texto residual em documentacao/UI

### 5.7 `Enterprise`

Aparece em:

- tier tecnico `ENTERPRISE`
- labels comerciais
- Step 35 como nome canônico do tier topo

Classificacao:

- tecnico e comercial

### 5.8 `Agricultura`, `Pecuária`, `Financeiro`, `Estoque`, `Frota`, `CRM`

Aparecem como:

- labels de UI e navegacao
- dominios funcionais em documentacao
- categorias de modulo
- em `CRM`, tambem como subproduto real de backoffice comercial

Classificacao:

- `Agricultura`, `Pecuária`, `Financeiro`, `Frota`, `Estoque`: labels de dominio/modulo
- `CRM`: dominio funcional real, mas nao esta modelado hoje como `moduleId` comercializavel equivalente a `A1_*`/`P1_*`

## 6. Dependencias Estruturais Mapeadas

### 6.1 Plano -> pacote

Estado atual:

- no backend, `PlanoAssinatura` e a entidade real de comercializacao;
- no frontend, `pacotes.ts` cria um conceito paralelo de pacote.

Conclusao:

- nao existe hoje uma entidade unica de banco chamada `pacote`;
- pacote e composicao de frontend/documentacao;
- plano e a entidade canônica de billing.

### 6.2 Pacote -> modulo

Fonte:

- `apps/web/src/lib/constants/pacotes.ts`

Regras observadas:

- cada pacote lista `modulos`;
- `CORE` e obrigatorio;
- dependencias de modulo sao assumidas;
- `EMPRESA` inclui extensoes `EXT_*`.

### 6.3 Modulo -> feature

Fontes:

- `ModuleGate`
- `require_module()`
- paginas/componentes que combinam `useHasModule()` com `useHasTier()`

Exemplos:

- `A5_COLHEITA` + `PROFISSIONAL` para beneficiamento
- `A5_COLHEITA` + `ENTERPRISE` para rastreabilidade
- `A4_PRECISAO` + `ENTERPRISE` para VRA

Conclusao:

- modulo habilita o bloco funcional;
- tier aprofunda o que o modulo contratado pode fazer.

### 6.4 Feature -> permissao

Ha dois modelos convivendo:

1. feature gate de monetizacao por modulo/tier;
2. RBAC por permissao granular.

Exemplo conceitual:

- monetizacao: `require_module("A1_PLANEJAMENTO")`
- permissao operacional: `agricola:planejamento:create`

Conclusao:

- feature nao mapeia 1:1 para permissao;
- ela costuma depender de modulo/tier e depois de RBAC.

### 6.5 Modulo -> tier minimo

Nao existe uma tabela unica formalizada, mas a combinacao aparece no codigo/testes:

- `A5_COLHEITA` + `PROFISSIONAL` para beneficiamento
- `A5_COLHEITA` + `ENTERPRISE` para rastreabilidade
- `A4_PRECISAO` + `ENTERPRISE` para VRA
- `A2_CAMPO` + `PROFISSIONAL` para agronomo/chat/RAT
- `EXT_IA` + `PROFISSIONAL` em endpoints de IA

Conclusao:

- tier minimo esta espalhado em gates de rotas e componentes;
- nao ha ainda um catalogo central unificado modulo -> tier minimo.

### 6.6 Billing -> assinatura -> plano

Cadeia canônica:

- `AssinaturaTenant.plano_id` -> `PlanoAssinatura.id`
- `PlanoAssinatura.plan_tier`
- `PlanoAssinatura.modulos_inclusos`

Uso em runtime:

- `require_module()` consulta os `modulos_inclusos` de assinaturas ativas/trial
- `require_tier()` resolve `plan_tier` via claim JWT ou consulta de assinatura/plano
- `MudancaPlanoService` usa `plano_origem_id` e `plano_destino_id`

### 6.7 Frontend -> `useHasTier` / `useHasModule` / `ModuleGate`

Fluxo atual:

- store guarda `modules` e `plan_tier` por contexto de tenant
- `useHasModule()` le `activeModules()`
- `useHasTier()` le `activePlanTier()`
- `ModuleGate` bloqueia renderizacao do modulo
- componentes avancados ainda combinam `useHasTier()`

Conclusao:

- o frontend ja espelha corretamente a arquitetura backend de modulo + tier;
- o problema atual e naming/comercial, nao mecanismo de gate.

## 7. Inconsistencias Encontradas

### 7.1 Mesmo conceito com nomes diferentes

Casos principais:

- topo de tier: `PREMIUM` vs `ENTERPRISE`
- tier de entrada: `Essencial` vs `BASICO`
- plano/pacote topo: `Empresa` vs `Enterprise`
- seeds de planos: `Bronze (Essencial)`, `Prata (Profissional)`, `Ouro (Empresarial)`
- seed de pricing: `Básico`, `Pro`, `Enterprise`
- Step 94/95: `A1 Planejamento`, `Profissional`, `Enterprise`

Risco:

- alto para billing/seeds quando houver carga de dados real;
- medio para frontend e docs;
- baixo quando restrito a texto de apresentacao.

### 7.2 Nomes comerciais misturados com identificadores tecnicos

Exemplos:

- `A1` e usado como modulo, plano e porta de entrada comercial;
- `Profissional` e usado como tier e tambem como nome de pacote;
- `Enterprise` e usado como tier e tambem como oferta comercial;
- `A1 Planejamento` em UI de billing representa um plano comercial, mas `A1_PLANEJAMENTO` e modulo tecnico.

Risco:

- medio a alto, porque a semantica fica ambigua para futuras migracoes e para analytics.

### 7.3 `Premium` vs `Enterprise`

Estado:

- Step 35 definiu `ENTERPRISE` como nome canônico;
- `PREMIUM` permanece apenas para compatibilidade.

Risco:

- baixo para leitura;
- alto se novas features voltarem a gravar `PREMIUM` como valor novo.

### 7.4 `A1` vs `Básico` vs `Essencial`

Estado:

- `A1` hoje indica modulo agricola/entrada comercial;
- `BASICO` e o tier tecnico atual;
- `Essencial` sobrevive em documentacao historica.

Risco:

- alto para comunicacao e roadmap;
- medio para frontend;
- baixo para backend se mantido so como label.

### 7.5 `Agricultura` como modulo vs plano/pacote

Estado:

- Agricultura e um dominio/modulo comercial;
- `A1_PLANEJAMENTO` e um modulo tecnico especifico dentro do bloco agricola;
- `A1 Planejamento` tambem esta sendo usado como nome de oferta de entrada.

Risco:

- medio, porque o cliente pode confundir bloco agricola com plano inteiro.

### 7.6 Modulos operacionais confundidos com tiers

Estado:

- modulos `F1/F2`, `A1/A2`, `P1/P2` representam contratacao funcional;
- tier `BASICO/PROFISSIONAL/ENTERPRISE` representa profundidade de recurso;
- parte da documentacao antiga ainda trata `{MODULO}_E`, `{MODULO}_P1`, `{MODULO}_E1`.

Risco:

- alto em futuras evolucoes se a equipe voltar ao modelo antigo de tier por modulo.

## 8. Avaliacao de Risco por Tipo de Melhoria

### 8.1 Risco baixo

Mudancas limitadas a:

- labels em landing, cards, comparativos;
- copy de UI;
- documentacao comercial;
- badges, subtitulos e descricoes.

Exemplos:

- trocar `Empresa` por `Enterprise` em telas de marketing;
- remover `Essencial` de docs comerciais recentes;
- exibir `A1 Planejamento` apenas como nome de oferta.

### 8.2 Risco medio

Mudancas em:

- constantes de frontend;
- `pacotes.ts`;
- labels de billing page;
- tipagens TS e filtros/normalizadores;
- seeds ainda nao considerados definitivos.

Exemplos:

- unificar `EMPRESA` para `ENTERPRISE` no frontend;
- separar melhor `tier label` de `plan name`;
- reclassificar `A1 Planejamento` como nome de plano e nao de modulo.

### 8.3 Risco alto

Mudancas em:

- `services/api/core/constants.py`
- `services/api/core/models/billing.py`
- `plan_tier` persistido
- `modulos_inclusos`
- migrations
- JWT claims `plan_tier`, `modules`
- regras de `require_module()` / `require_tier()`
- billing, assinatura, mudanca de plano, CRM e seeds produtivos

Exemplos:

- renomear `A1_PLANEJAMENTO` para outro codigo;
- renomear `BASICO` para `ESSENCIAL` no banco;
- alterar contratos de permissao, claims ou modulos persistidos.

## 9. O que Manter como Identificador Interno

Recomendacao:

- manter `A1_PLANEJAMENTO`, `A2_CAMPO`, `P1_REBANHO`, `F1_TESOURARIA` etc. como codigos internos;
- manter `BASICO`, `PROFISSIONAL`, `ENTERPRISE` como tiers tecnicos;
- manter `CORE` e demais `modulos_inclusos` como contrato de monetizacao;
- manter permissoes no padrao `modulo:recurso:acao`;
- manter `PREMIUM` apenas como alias de leitura, nunca como valor novo de escrita.

Justificativa:

- esses nomes ja atravessam backend, frontend, JWT, testes, gates, billing e possivelmente dados persistidos.

## 10. O que Padronizar como Label Comercial

Recomendacao pratica:

- usar um unico conjunto comercial para venda:
  - plano/entrada: `A1 Planejamento`
  - crescimento: `Profissional`
  - topo: `Enterprise`
- usar dominios como grupos de valor, nao como plano:
  - `Agricultura`
  - `Pecuária`
  - `Financeiro`
  - `Estoque`
  - `Frota`
  - `CRM`

Regra proposta:

- modulo tecnico continua com codigo;
- plano comercial recebe nome humano;
- tier continua invisivel ao usuario quando nao for necessario;
- pacote nao deve competir semanticamente com modulo.

## 11. O que Nunca Renomear sem Migration

Nao renomear sem plano formal de compatibilidade:

- `plan_tier` persistido em `planos_assinatura`
- valores `BASICO`, `PROFISSIONAL`, `ENTERPRISE`
- alias legado `PREMIUM` sem camada de leitura garantida
- `modulos_inclusos`
- codigos `A1_PLANEJAMENTO`, `P1_REBANHO`, `F1_TESOURARIA`, `O2_ESTOQUE` etc.
- claims JWT `plan_tier` e `modules`
- strings usadas por `require_module()` e `require_tier()`
- contratos de `MudancaPlano`, `AssinaturaTenant` e `PlanoAssinatura`
- chaves de permissao e wildcards RBAC

Motivo:

- qualquer alteracao aqui pode quebrar gates, assinaturas ativas, CRM, onboarding, testes e analytics.

## 12. Proposta de Glossario Canonico

### 12.1 Tecnico

- `Modulo`: identificador contratavel como `A1_PLANEJAMENTO`, `O2_ESTOQUE`
- `PlanTier`: profundidade de acesso `BASICO`, `PROFISSIONAL`, `ENTERPRISE`
- `PlanoAssinatura`: produto de billing persistido no banco
- `modulos_inclusos`: contrato de modulos ativos do plano
- `Permissao`: string RBAC `modulo:recurso:acao`

### 12.2 Comercial

- `Plano comercial`: nome exibido ao cliente, ex. `A1 Planejamento`, `Profissional`, `Enterprise`
- `Pacote`: composicao comercial para landing/comparativo; nao e hoje entidade canônica de banco
- `Dominio`: frente de valor como `Agricultura`, `Pecuária`, `Financeiro`, `Estoque`, `Frota`, `CRM`

### 12.3 Compatibilidade

- `PREMIUM`: somente alias legado de `ENTERPRISE`
- `Essencial`: termo historico de documentacao, nao recomendado para runtime novo
- `Bronze/Prata/Ouro`, `Pro`, `Empresarial`: nomenclaturas antigas ou de seed, nao canônicas

## 13. Recomendacoes Praticas de Melhoria Futura

### 13.1 Curto prazo

- padronizar toda copy nova em `A1 Planejamento`, `Profissional`, `Enterprise`;
- remover `Premium` de UI nova;
- marcar `Essencial`, `Bronze/Prata/Ouro`, `Pro` e `Empresarial` como legado em docs/seeds.

### 13.2 Medio prazo

- separar explicitamente em frontend:
  - `tier tecnico`
  - `nome comercial do plano`
  - `pacote comercial`
- revisar `apps/web/src/lib/constants/pacotes.ts` para nao misturar `EMPRESA` com `ENTERPRISE`;
- revisar `seed_plans.py` e `seed_plan_pricing.py` para convergir naming antes de uso produtivo definitivo.

### 13.3 Alto impacto, fazer apenas com projeto de refactor

- centralizar matriz `modulo -> tier minimo -> labels comerciais`;
- criar fonte canônica unica para catalogo comercial de planos/pacotes;
- se houver renome de codigos tecnicos, executar migration + compatibilidade + replay de claims + ajuste de seeds/tests.

## 14. Conclusao

O sistema ja possui base estrutural consistente para monetizacao:

- modulo contratado via `modulos_inclusos`;
- profundidade via `plan_tier`;
- gates coerentes em backend e frontend.

O principal problema atual nao e arquitetura, e semantica:

- nomes comerciais, pacotes e termos historicos ainda se sobrepoem aos identificadores tecnicos.

Recomendacao final:

- preservar integralmente os identificadores tecnicos atuais;
- unificar o discurso comercial em cima de um glossario simples;
- tratar qualquer refactor de `plan_tier`, `moduleId`, permissao ou billing como mudanca de alto risco com migration explicita.
