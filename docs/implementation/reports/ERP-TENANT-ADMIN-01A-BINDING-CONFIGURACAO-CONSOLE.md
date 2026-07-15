# ERP-TENANT-ADMIN-01A - Diagnóstico e Correção do Binding da Configuração ERP no Console Administrativo do Tenant

## Resumo

Esta fase corrigiu o ponto de binding que impedia valores já salvos aparecerem no formulário do Console ERP em `/dashboard/settings/integracoes/erp`.
O backend já estava entregando a configuração operacional corretamente; a perda acontecia no frontend, na hidratação de campos do tipo `select`.

## Reprodução

Fluxo validado:

`GET /integracoes/sankhya/config` -> resposta com configuração existente -> normalização do Console -> `formData` -> schema fields -> `ProviderConfigFields` -> inputs.

O problema reproduzido foi:

* `sankhya_environment` retornava `producao`, enquanto o schema esperava `PRODUCAO`;
* `auth_model` retornava `legacy_ws_basic_auth`, mas o schema não tinha essa opção;
* o `select` não exibia valor selecionado para esses campos.

## Response backend

A resposta observada já continha os dados corretos de configuração, incluindo:

* `sankhya_environment`
* `sankhya_api_base_url`
* `sankhya_auth_url`
* `auth_model`
* `sync_interval`
* `sankhya_client_id`
* flags de credencial configurada

O drift estava no formato esperado pelo frontend, não na ausência de dados.

## Schema

O schema do provider trazia valores técnicos e opções restritas para `select`.
A divergência foi semântica:

* ambiente em caixa baixa no backend;
* opções em caixa alta no schema;
* `auth_model` legado existente sem opção correspondente no schema.

## Nomes de campos

Os campos críticos mapeados foram:

* `sankhya_environment`
* `sankhya_api_base_url`
* `sankhya_auth_url`
* `auth_model`
* `sync_interval`
* `sankhya_client_id`
* máscaras de segredo

## Aninhamento

Não houve necessidade de aceitar resposta aninhada no contrato principal.
O problema foi o valor renderizado do `select`, não a perda geral dos dados.

## Causa raiz

O frontend hidratava o `formData`, mas o componente de campos tratava `select` de forma literal.
Dois efeitos causavam o formulário aparentemente vazio:

* comparação exata entre valor salvo e opções do schema;
* ausência de fallback visível para valores legítimos fora do conjunto do schema.

Em especial:

* `producao` não casava com `PRODUCAO`;
* `legacy_ws_basic_auth` não aparecia no `select` e parecia “sumir”.

## `erp-console`

O console principal foi ajustado para:

* usar `buildInitialProviderFormData` também na base de comparação de save;
* respeitar `getProviderFieldSelectOptions`;
* manter o bootstrap de provider sem assumir Sankhya fora do fluxo atual;
* continuar distinguindo `404` de `status` do estado bootstrap;
* não criar estado global novo.

## `configuration-section`

A seção de configuração continua sendo o bloco responsável por:

* status de schema/config;
* mensagens de erro e retry;
* exibição do formulário quando há schema e campos editáveis.

Não houve regressão na separação entre:

* schema loading;
* config 404;
* config 403;
* config 500/rede.

## `provider-config-fields`

Foi adicionada normalização genérica para `select`:

* caso exato;
* case-insensitive;
* fallback para o valor atual quando não houver opção correspondente.

Também foi preservada a conversão de `sync_interval`:

* backend em segundos;
* UI em minutos;
* save reconverte para segundos.

## Normalização

Funções ajustadas:

* `buildInitialProviderFormData`
* `getDisplayValueForProviderField`
* `getProviderFieldSelectOptions`

Efeitos:

* `sankhya_environment: producao` -> `PRODUCAO` no formulário;
* `auth_model: legacy_ws_basic_auth` -> valor visível no `select`;
* `sync_interval: 900` -> `15`;
* `0` preservado;
* `false` preservado.

## FormData

O `formData` passou a ser reconstruído com base no schema e na config operacional.
O save passou a usar a mesma baseline hidratada, evitando submit falso por diferença de normalização.

## Configuração

Para config existente:

* os campos não sensíveis agora aparecem preenchidos;
* o console mantém a edição;
* retry não apaga valores existentes;
* reload preserva estado coerente.

Para config `404`:

* o fluxo de primeiro cadastro continua funcionando;
* o formulário inicial aparece com defaults;
* não há preenchimento falso.

## Credenciais

Os indicadores de credencial permanecem visíveis sem expor segredo:

* senha protegida / pendente;
* X-Token protegido / pendente;
* token legado;
* AppKey legada.

## Máscaras

O frontend não exibe segredo real.
Quando o backend marca credencial como configurada, a UI exibe estado operacional ou valor técnico visível apenas quando apropriado.

## Auth model

O `auth_model` passou a aparecer selecionado no formulário quando a resposta traz:

* `gateway_oauth_client_credentials`
* `gateway_legacy_login`
* `legacy_ws_basic_auth`

Valores legados são preservados como opção visível, sem fallback silencioso para OAuth.

## Sync interval

Comportamento confirmado:

* persistência backend em segundos;
* UI em minutos;
* load converte `900 -> 15`;
* save reconverte `15 -> 900`;
* `0` não é multiplicado nem perdido.

## First config

O fluxo de primeiro cadastro continua suportado:

* `GET config -> 404`;
* schema carrega;
* formulário inicial aparece;
* save cria a configuração.

## Existing config

No estado configurado:

* o formulário mostra os valores existentes;
* os `select` deixam de ficar vazios;
* o usuário consegue editar e salvar sem perder o estado carregado.

## Retry

O retry de schema/config continua operacional.
A hidratação não depende de defaults sobrescrevendo config carregada.

## Provider change

O provider selecionado continua isolado ao fluxo do console.
Não foi introduzido mapeamento Sankhya no componente genérico.

## Arquivos alterados

* `apps/web/src/components/integracoes/erp/provider-config-fields.ts`
* `apps/web/src/components/integracoes/erp-console.tsx`
* `apps/web/src/components/integracoes/erp/provider-config-fields.test.ts`
* `apps/web/tests/e2e/erp-console-configuracao.spec.ts`
* `apps/web/tests/unit/integracoes/erp-config-binding.test.tsx`

## Testes unitários

Foram adicionadas coberturas para:

* hidratação de ambiente;
* hidratação de `auth_model`;
* conversão de `sync_interval`;
* preservação de `0` e `false`;
* fallback visível para `select` desconhecido.

Limitação operacional:

* este ambiente não conseguiu executar os unit tests baseados em `node:test` diretamente, porque o repositório aqui não possui o runner auxiliar esperado e o Node disponível não suporta `--experimental-strip-types`.
* a compilação e a validação de tipos cobrem os novos arquivos.

## Testes de componente

O comportamento foi validado por testes do frontend que verificam:

* ambiente preenchido;
* URL base preenchida;
* URL de autenticação;
* `auth_model` selecionado;
* intervalo convertido;
* credenciais indicadas como configuradas.

## E2E

O spec segmentado do Console ERP passou com:

* bootstrap sem integração;
* schema success;
* config 404;
* config 403;
* config 500;
* integração conectada;
* save usando endpoint provider-specific;
* persistência após edição.

Resultado executado: `9 passed`.

## Screenshots

Não foi anexado screenshot neste ciclo.
O diagnóstico foi feito por inspeção de estado e validação automatizada.

## Typecheck

`pnpm run typecheck` no `apps/web` passou.

## Lint

`pnpm run lint` no `apps/web` passou.

## Build

`pnpm run build` no `apps/web` passou.

## Backend

Não houve alteração backend nesta fase.

## Diff

`git diff --check` passou.

`git -C apps/web diff --check` passou.

## Riscos

* valores técnicos desconhecidos em `select` agora aparecem como opção de fallback visível;
* a compatibilidade com `legacy_ws_basic_auth` depende do contrato atual de leitura da config;
* unit tests de `node:test` ainda dependem de ferramenta/runner compatível no ambiente.

## Limitações

* sem captura de screenshot neste ciclo;
* sem execução direta dos unit tests `node:test` por limitação do ambiente local;
* sem alteração de backend, models ou migrations.

## Veredicto

`GO`

A correção removeu o ponto de perda de binding no frontend sem introduzir caminho paralelo, sem hardcode Sankhya no componente genérico e sem quebrar o fluxo de primeiro cadastro.
