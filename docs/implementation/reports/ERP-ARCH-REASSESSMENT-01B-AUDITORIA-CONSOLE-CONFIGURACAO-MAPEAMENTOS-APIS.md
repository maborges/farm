# ERP-ARCH-REASSESSMENT-01B — Auditoria do Console Operacional, Configuração Técnica, APIs Consumidas e Mapeamento de Campos AgroSaaS × ERP

## 1. Resumo executivo

### Veredictos

#### Configuração

`GO COM RESSALVAS`

#### Transparência operacional

`INSUFICIENTE`

#### Piloto

`GO COM RESSALVAS`

### Síntese

O formulário de configuração ainda existe no código e continua sendo renderizado no console oficial do tenant. Ele não foi removido.

O problema observado não é “ausência estrutural” do componente, e sim uma combinação de fatores:

- dependência silenciosa do `schema` para renderização útil dos campos;
- seção de configuração posicionada depois de blocos extensos do console;
- ausência de mensagem específica quando o `schema` falha ou retorna vazio;
- drift de contrato entre `schema`, `UI`, `payload de save` e `backend`;
- parte das informações operacionais relevantes existe apenas em código provider-specific e não é exposta ao tenant.

Em termos práticos:

- o card `Configuração da integração` sempre existe depois que o wrapper do provider é montado;
- os campos só aparecem quando o `schema` vem carregado com `connection_schema.fields` e/ou `credential_schema.fields`;
- se o `schema` não vier, o card continua visível, mas sem os campos, sem erro específico e com CTAs ainda ativos;
- isso produz a percepção operacional de que “os campos sumiram”.

### Causa raiz principal

Não há evidência de que o formulário tenha sido removido.

Há evidência de:

- `SCHEMA_FETCH_FAILURE`
- `SILENT_ERROR`
- `CONFIG_SECTION_ORDER`
- `TYPE_CONTRACT_DRIFT`

Há também drift importante no contrato de configuração:

- `legacy_auth_model` é declarado no schema e renderizado, mas o backend ignora;
- `ultimo_teste`, `teste_status`, `ultimo_sync` são declarados no schema e renderizados como editáveis, mas não pertencem ao payload aceito de configuração;
- `sync_interval` é apresentado na UI como minutos, enquanto o backend o trata operacionalmente como segundos.

## 2. Contexto

Esta auditoria aprofunda a auditoria anterior:

- `ERP-ARCH-REASSESSMENT-01-AUDITORIA-DEFINITIVA-MULTIPROVIDER.md`

Escopo desta execução:

- página oficial `/dashboard/settings/integracoes/erp`
- `ErpConsole`
- `SankhyaConsole`
- `DynamicErpConsole`
- endpoints internos consumidos
- schema e config provider-specific
- visualização de associações, chaves e APIs
- fontes reais de mapeamento AgroSaaS × ERP

Sem alterações de código, testes, models, migrations, endpoints ou abstrações.

## 3. Fluxo oficial

## 3.1 Diagrama textual

`/dashboard/settings/integracoes/erp`  
→ [page.tsx](../../../../apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx)  
→ `ErpConsole`  
→ `GET /integracoes/erp/status`  
→ se `404`: `ErpProviderSelector`  
→ seleção do provider  
→ `ERP_PROVIDER_CONSOLES[slug]`  
→ `SankhyaConsole`  
→ `DynamicErpConsole(providerSlug="sankhya", endpoints=...)`  
→ `Promise.all` com:
  - `GET /integracoes/erp/providers/{provider_slug}/schema`
  - `GET /integracoes/erp/diagnostico`
  - `GET /integracoes/sankhya/config`
  - `GET /integracoes/erp/status`
  - `GET /integracoes/erp/health`
  - `GET /integracoes/erp/jobs`
  - `GET /integracoes/sankhya/logs`
  - `GET /integracoes/erp/timeline`
→ render do console completo  
→ card `Configuração da integração`  
→ campos só se `schema.connection_schema.fields` e/ou `schema.credential_schema.fields` existirem

## 3.2 Conclusão do fluxo

O console depende de duas resoluções:

1. resolução do provider pelo `ErpConsole`;
2. resolução útil do formulário pelo `DynamicErpConsole`, que depende do `schema`.

Sem `schema`, o console ainda monta, mas o formulário deixa de ser funcional/visível em conteúdo.

## 4. Página

Arquivo:

- [page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx)

Características:

- client component indireto, pois importa `ErpConsole` client-side
- renderiza `PageHeader`
- renderiza `ErpConsole`
- não possui guard explícito no componente
- não possui suspense explícito
- não possui error boundary local explícito
- não usa query params
- não faz redirect

Páginas relacionadas encontradas:

- [page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx)
- [page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx)

Conclusão:

- existe uma página oficial do tenant;
- existe uma página separada de backoffice;
- não há terceira “página paralela” do console ERP no tenant.

## 5. `ErpConsole`

Arquivo:

- [erp-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp-console.tsx)

## 5.1 Estado inicial

`ErpConsole` mantém:

- `selectedProviderSlug`

E consulta:

- `GET /integracoes/erp/status`

## 5.2 Tratamento de status

### `404`

Tratado explicitamente com:

- `return { notFound: true }`

Resultado visual:

- mostra `ErpProviderSelector`

### `401/403`

Não há tratamento específico. Qualquer erro diferente de `404` cai no estado:

- `error`
- renderiza `Alert` genérico “Erro ao carregar o status da integração”

### `500/rede`

Também cai no `error` genérico.

## 5.3 Condições de renderização

Condições principais:

1. `isLoading` → skeleton
2. `error` → alert de erro
3. `statusData?.notFound && !selectedProviderSlug` → provider selector
4. `!slugToRender` → provider selector
5. `!ProviderWrapper` → alert de provider sem suporte visual
6. caso contrário → wrapper do provider

## 5.4 Respostas objetivas

1. O formulário aparece para tenant sem integração: `sim, após selecionar provider`
2. O formulário aparece antes do primeiro save: `sim, se o schema carregar`
3. Existe retorno antecipado do componente: `sim`
4. Existe condição específica do Sankhya: `sim, via registry e único wrapper`
5. Existe diferença entre `ErpConsole`, `SankhyaConsole` e `DynamicErpConsole`: `sim`

Conclusão:

O `ErpConsole` não remove o formulário. Ele apenas controla:

- seleção de provider
- suporte do wrapper
- carregamento inicial de status

## 6. `SankhyaConsole`

Arquivo:

- [sankhya-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/sankhya-console.tsx)

Props efetivamente passadas ao `DynamicErpConsole`:

- `providerSlug="sankhya"`
- `endpoints.getConfig="/integracoes/sankhya/config"`
- `endpoints.saveConfig="/integracoes/sankhya/config"`
- `endpoints.testConnection="/integracoes/sankhya/config/testar-conexao"`
- `endpoints.sync(tipo)="/integracoes/sankhya/sync/{tipo}"`
- `endpoints.getLogs="/integracoes/sankhya/logs?limit=10"`
- `operationalConfig.manualSyncCapabilities=["pessoas","produtos"]`
- `operationalConfig.fullSyncAction.code="completo"`
- `operationalConfig.adapterLabel="Conector Sankhya"`

### Respostas

1. O endpoint de configuração ainda é fornecido: `sim`
2. O endpoint de schema ainda é fornecido: `indiretamente, pelo próprio DynamicErpConsole`
3. Alguma prop obrigatória ficou ausente: `não para o fluxo atual Sankhya`
4. Existe diferença entre tipos e props reais: `sim`
5. Existe fallback que impede o formulário: `não diretamente`

Observação crítica:

`saveConfig` existe na prop, mas `DynamicErpConsole.handleSave()` não usa `endpoints.saveConfig`; ele usa `endpoints.getConfig` como destino do `POST`.

No Sankhya isso não quebra porque GET e POST usam o mesmo path `/integracoes/sankhya/config`.

Classificação:

- `TYPE_CONTRACT_DRIFT`

## 7. `DynamicErpConsole`

Arquivo:

- [erp-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp-console.tsx)

## 7.1 Dados carregados

`Promise.all` carrega:

- `schema`
- `diagnosis`
- `config`
- `status`
- `health`
- `jobs`
- `logs`
- `timeline`

Via:

- `fetchJson()`

## 7.2 Comportamento de `fetchJson`

`fetchJson()`:

- chama `apiFetch`
- engole qualquer erro
- retorna `null`

Isso é central para a auditoria.

### Consequência

Se `schema` falha:

- não há erro específico de schema para o usuário;
- `schema` vira `null`;
- o card de configuração continua existindo;
- os campos não renderizam.

## 7.3 Condição de loading

Só entra no spinner global quando:

- `loading && !status && !config && !schema`

Se `status` vier e `schema` falhar:

- não há spinner;
- não há erro específico;
- a página segue normal.

## 7.4 Condição de erro

`loadError` só vira a mensagem principal quando nenhum core data vier:

- `schemaData || configData || statusData || healthData || diagnosisData`

Se apenas `status` vier:

- `loadError = null`

Conclusão:

Um erro de `schema` pode desaparecer silenciosamente.

## 7.5 Condição real de renderização do formulário

O card `Configuração da integração` sempre é renderizado depois que o `DynamicErpConsole` chega ao JSX principal.

Os campos só renderizam se:

- `schema?.connection_schema?.fields?.length`
- `schema?.credential_schema?.fields?.length`

Logo:

1. O formulário é sempre montado: `não`
2. É montado apenas quando `schema` existe: `sim`
3. É montado apenas quando `config` existe: `não`
4. Existe condição como `configNotFound`: `não`
5. Existe condição que mostra apenas provider selector: `isso acontece no ErpConsole, antes`
6. Existe erro de schema engolido: `sim`
7. A seção foi deslocada para o fim da página: `sim`
8. Está dentro de componente recolhível fechado: `não`
9. Existe CSS que a oculta: `não encontrado`
10. Existe problema evidente de chave React/montagem: `não encontrado`

## 7.6 Ordem visual real

Ordem atual confirmada:

1. cabeçalho visual do console
2. alert introdutório
3. resumo do ERP / readiness
4. `ErpCapabilityCenter`
5. `ErpSyncCenter`
6. `AssociationCenter`
7. `Configuração da integração`
8. `Diagnóstico operacional`
9. `Linha do tempo operacional`

Conclusão:

- a `Configuração da integração` continua presente;
- não foi removida;
- está abaixo de blocos extensos e pode exigir rolagem excessiva;
- isso agrava a descoberta do formulário.

Classificação:

- `CONFIG_SECTION_ORDER`
- `UX_DISCOVERABILITY`

## 8. Condição de renderização

## 8.1 Para tenant sem integração

Fluxo:

- `/integracoes/erp/status` → `404`
- `ErpProviderSelector`
- selecionar `sankhya`
- `SankhyaConsole`
- `DynamicErpConsole`
- `schema` pode carregar mesmo sem `config`

Resultado:

- o formulário deveria aparecer antes do primeiro save, desde que o schema carregue.

## 8.2 Para configuração incompleta

`GET /integracoes/sankhya/config` pode retornar `404`.

Mesmo assim:

- o schema pode carregar;
- os campos podem aparecer;
- `config` continua `null`.

Resultado:

- o console suporta configuração inicial incompleta.

## 8.3 Para integração conectada

- o formulário continua acessível;
- `config` carrega valores atuais;
- secrets aparecem mascarados por flags de `_configured` e `_mask`.

## 8.4 Para tenant legado

O fluxo preserva:

- `ws_url`
- `username`
- `password`
- `sankhya_token`
- `sankhya_appkey`

Mas o `schema` também expõe campos inadequados como editáveis.

## 9. Schema

Endpoint:

- `GET /api/v1/integracoes/erp/providers/{provider_slug}/schema`

Implementação:

- [router.py](/opt/lampp/htdocs/farm/services/api/integracoes/erp/router.py)

Permissão:

- `integrations:view`

Regras:

- provider precisa existir
- `provider_type == "ERP"`
- `ativa == true`

Payload real:

- `provider`
- `schema_version`
- `connection_schema`
- `credential_schema`

## 9.1 Schema Sankhya atual

Origem:

- [canonical_adapter.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/canonical_adapter.py)

`connection_schema.fields`:

- `sankhya_environment`
- `sankhya_api_base_url`
- `sankhya_auth_url`
- `auth_model`
- `sync_interval`
- `ws_url`
- `ultimo_teste`
- `teste_status`
- `ultimo_sync`

`credential_schema.fields`:

- `sankhya_client_id`
- `sankhya_client_secret`
- `sankhya_x_token`
- `sankhya_token`
- `sankhya_appkey`
- `username`
- `password`
- `legacy_auth_model`

## 9.2 Conclusão do schema

O endpoint de schema funciona conceitualmente e entrega os campos esperados do provider Sankhya.

O problema não é “endpoint inexistente”.

O problema é:

- fragilidade do consumo no frontend;
- ausência de erro explícito de schema;
- schema contendo campos que não deveriam ser editáveis ou nem sequer persistíveis no fluxo atual.

## 10. Configuração

Endpoints reais do Sankhya:

- `GET /integracoes/sankhya/config`
- `POST /integracoes/sankhya/config`
- `POST /integracoes/sankhya/config/testar-conexao`

Wrapper passa:

- `getConfig=/integracoes/sankhya/config`
- `saveConfig=/integracoes/sankhya/config`
- `testConnection=/integracoes/sankhya/config/testar-conexao`

Mas o console chama:

- load: `GET endpoints.getConfig`
- save: `POST endpoints.getConfig`
- test: `POST endpoints.testConnection`

## 10.1 Tratamento de status do endpoint

### `GET /config`

- `404`: engolido por `fetchJson`, vira `null`
- `403`: engolido por `fetchJson`, vira `null`
- `500`: engolido por `fetchJson`, vira `null`

### `POST /config`

- `422`: cai em `apiFetch` e gera toast com `error.message`
- `403`: idem
- `500`: idem

### `POST /config/testar-conexao`

- `403`: toast de erro
- `422/500`: toast de erro

Conclusão:

O endpoint de config funciona no backend, mas o carregamento inicial da config é silencioso quando falha.

## 11. Permissões

Backend protege:

- schema: `integrations:view`
- config GET: `integrations:view`
- config POST: `integrations:configure`
- test connection: `integrations:test`
- sync: `integrations:sync`
- jobs/logs/timeline: `integrations:logs:view`

Frontend:

- não esconde o formulário por permissão;
- também não diferencia visualmente “sem permissão” em `save/test`.

Classificação:

- `PERMISSION_GUARD` no backend
- `SILENT_ERROR`/UX incompleta no frontend para 403 em load

## 12. Estados

### Formulário oculto

Quando:

- `schema == null` ou sem `fields`

### Formulário desabilitado

Não há desabilitação granular de campos.

### Acesso negado

Só aparece no ato de salvar/testar, por toast de erro.

### Schema indisponível

Não possui feedback específico.

## 13. Erros

Erros silenciosos encontrados:

- `fetchJson().catch -> null`
- `loadError` depende de ausência total de dados, não de falha parcial
- `schema` nulo não gera mensagem específica
- `config` nula não gera mensagem específica

Erros não silenciosos:

- `handleSave` usa toast
- `handleTestConnection` usa toast
- `ErpConsole` mostra alert para erro global de status

Conclusão:

O principal problema operacional é `SILENT_ERROR` em falha parcial.

## 14. Ordem visual

A ordem anterior ainda existe em essência, com `Configuração da integração` depois de `Readiness`, `Capability Center`, `Sync Center` e `Association Center`.

Resposta objetiva:

- a Configuração Base continua presente: `sim`
- foi substituída: `não`
- foi removida: `não`
- está abaixo de lista extensa: `sim`
- o usuário precisa rolar excessivamente: `sim, dependendo do volume do centro de capabilities`
- existe âncora para configuração: `sim`
- o botão `Configurar` aponta para o ID correto: `sim`
- o ID visual existe: `sim`
- há IDs duplicados: `não encontrado`
- a navegação por hash funciona: `sim, por `#erp-configuracao` e também por `focusSection()`

## 15. CTA

CTAs relevantes:

| CTA | Componente | Evento/destino | Condição |
| --- | --- | --- | --- |
| `Configurar integração` | `ErpProviderSelector` | `onSelect(slug)` | provider suportado no registry |
| `Voltar para escolher outro ERP` | `ErpConsole` | `setSelectedProviderSlug(null)` | provider selecionado em sessão sem status |
| `Configurar` | `CapabilityCard` / `CapabilityDetails` | `focusSection("erp-configuracao")` ou `#erp-configuracao` | `canConfigure` |
| `Salvar dados` | `DynamicErpConsole` | `handleSave()` | sempre no card |
| `Testar comunicação` | `DynamicErpConsole` | `handleTestConnection()` | sempre no card |
| `Atualizar situação` | `DynamicErpConsole` | `loadConsole()` | sempre no card |
| `Ver pendências` | capability details/card | `#erp-associations` | `canReconcile` |

Conclusão:

Não há evidência de âncora quebrada. O problema é visibilidade/descoberta e dependência silenciosa do schema.

Classificação:

- `BROKEN_ANCHOR`: `não`
- `CONFIG_SECTION_ORDER`: `sim`

## 16. Âncoras

IDs confirmados:

- `erp-capability-center`
- `erp-associations`
- `erp-configuracao`
- `erp-diagnostico`

Resultado:

- âncoras de configuração e associações existem;
- não há discrepância entre `configurationTargetId` e `id`.

## 17. Campos

## 17.1 Matriz de campos reais

| Campo real | Schema declara | UI renderiza | FormData contém | Save envia | Backend persiste | Reload retorna |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `sankhya_environment` | sim | sim | sim | sim | sim | sim |
| `sankhya_api_base_url` | sim | sim | sim | sim | sim | sim |
| `sankhya_auth_url` | sim | sim | sim | sim | sim | sim |
| `auth_model` | sim | sim | sim | sim | sim | sim |
| `sync_interval` | sim | sim | sim | sim | sim | sim |
| `ws_url` | sim | sim | sim | sim | sim | sim |
| `sankhya_client_id` | sim | sim | sim | sim | sim | sim |
| `sankhya_client_secret` | sim | sim | sim | sim se alterado | sim | não valor bruto, apenas flags/mask |
| `sankhya_x_token` | sim | sim | sim | sim se alterado | sim | não valor bruto, apenas flags/mask |
| `sankhya_token` | sim | sim | sim | sim se alterado | sim | não valor bruto, apenas flags/mask |
| `sankhya_appkey` | sim | sim | sim | sim se alterado | sim | não valor bruto, apenas flags/mask |
| `username` | sim | sim | sim | sim | sim | sim |
| `password` | sim | sim | sim | sim se alterado | sim | não valor bruto, apenas mask/flag |
| `legacy_auth_model` | sim | sim | sim | sim | não | não |
| `ultimo_teste` | sim | sim | sim | sim | não como input de config | sim como leitura runtime |
| `teste_status` | sim | sim | sim | sim | não como input de config | sim como leitura runtime |
| `ultimo_sync` | sim | sim | sim | sim | não como input de config | sim como leitura runtime |

## 17.2 Achados

Problemas de contrato:

- `legacy_auth_model` é renderizado, mas não faz parte de `SankhyaConfigCreate`; o backend ignora por `extra="ignore"`.
- `ultimo_teste`, `teste_status`, `ultimo_sync` são expostos como campos de formulário, mas não são campos de entrada de configuração.
- isso induz a percepção de que são configuráveis quando não são.

Classificação:

- `TYPE_CONTRACT_DRIFT`

## 18. Persistência

Persistência real da configuração:

- backend aceita `SankhyaConfigCreate`
- `POST /integracoes/sankhya/config`
- cria ou atualiza `SankhyaConfig`
- sincroniza estrutura canônica via `SankhyaCanonicalAdapter`

Conclusão:

O backend de configuração existe e persiste os campos técnicos reais.

## 19. Reload

Reload real:

- `GET /integracoes/sankhya/config`
- serializa via `SankhyaConfigSerializer.to_response()`
- enriquece com provider contract via `_provider_contract_payload()`

Limitação:

- reload não devolve segredos em claro;
- devolve apenas flags e masks;
- isso está correto;
- mas o frontend ainda depende de chaves `sankhya_*`.

## 20. Mapeamento de registros

Fonte real:

- `ExternalRecordAssociation`
- `ExternalRecordAssociationHistory`
- `SankhyaExternalAssociationHelper`

O que o usuário vê hoje:

- capability
- entidade interna
- ID interno
- entidade externa
- ID externo
- status
- ambiente
- histórico
- reconciliação

## 21. Mapeamento de campos

Não existe hoje um contrato persistido de “field mapping” do tipo:

- `nome ↔ NOMEPARC`
- `documento ↔ CGC_CPF`

Existe, hoje:

- mapeamento de registros materializados;
- chaves e campos usados no helper provider-specific;
- labels e ownership em catálogo frontend;
- documentação implícita em código.

Conclusão:

- `FIELD_MAPPING_NOT_MODELED`
- `RECORD_ASSOCIATION_ONLY`

## 22. Chaves

Chaves Sankhya reais encontradas:

| Capability | Entidade AgroSaaS | Campo/ID AgroSaaS | Entidade ERP | Chave ERP | Origem do mapeamento |
| --- | --- | --- | --- | --- | --- |
| pessoas | `Pessoa` | `id`, documento | `Parceiro` | `CODPARC`, `CGC_CPF` | `SankhyaExternalAssociationHelper.sync_pessoa` |
| produtos | `Produto` | `id`, código/sku | `Produto` | `CODPROD` | `sync_produto` |
| produtos | `UnidadeMedida` | `id/código` | `Unidade` | `UNIDADE` | `sync_unidade_medida` |
| nfe | `NotaFiscal` | `id`, chave de acesso | `NFe` | `CHAVEACESSO`, `NUNOTA`, `NUMNOTA`, `SERIE` | `sync_nfe` |
| financeiro | `Receita`/`Despesa` | `id` | `TituloFinanceiro` | combinação com `TIPO`, `CODPARC`, `NUMDOC`, `DESDOB`, `DTVENC`, `VLRDESDOB`, `CODNAT` | `sync_financeiro` |
| organização | estruturas internas | ids internos | empresa/filial ERP | `CODEMP`, `CODFILIAL` | `sync_organizacao` |
| estoque/admin | `Deposito` | `id` | local | `CODLOCAL` | `sync_deposito` |
| financeiro apoio | `ContaBancaria` | `id` | conta/banco/agência/carteira | `CODBANCO`, `CODAGENCIA`, `CONTA`, `CARTEIRA` | helper |
| financeiro apoio | `PlanoConta`/natureza | `id` | natureza/tipo operação | `CODNAT`, `CODTIPOPER` | helper |

O console hoje não mostra esse catálogo explicitamente.

Classificação:

- `KEY_MAPPING_NOT_EXPOSED`

## 23. Ownership

Ownership visível hoje:

- parcial, derivado de `capability-labels.ts`
- mostrado em `Capability Details`

Mas é:

- inferido por catálogo frontend;
- não derivado do runtime do provider.

Classificação:

- `OWNERSHIP_NOT_EXPOSED` no sentido de contrato runtime formal
- existe exposição parcial de rótulo operacional

## 24. Direção

Direção visível hoje:

- parcial, em `Capability Details`
- derivada de `capability matrix` ou fallback frontend

Problema:

- ainda não representa um descriptor formal runtime-only do provider;
- pode ser inferida por fallback.

Classificação:

- `DIRECTION_NOT_EXPOSED` de forma robusta

## 25. APIs internas

### Core ERP

| Área visual | Método | Endpoint | Provider-specific | Usuário consegue visualizar? |
| --- | --- | --- | ---: | ---: |
| status | GET | `/integracoes/erp/status` | não no nome, sim no runtime | não explicitamente |
| health | GET | `/integracoes/erp/health` | idem | não explicitamente |
| jobs | GET | `/integracoes/erp/jobs?limit=5` | idem | não explicitamente |
| timeline | GET | `/integracoes/erp/timeline?limit=12` | idem | não explicitamente |
| diagnóstico | GET | `/integracoes/erp/diagnostico` | idem | não explicitamente |
| associações lista | GET | `/integracoes/erp/associacoes` | parcialmente | não explicitamente |
| associações resumo | GET | `/integracoes/erp/associacoes/resumo` | parcialmente | não explicitamente |
| reconciliar | POST | `/integracoes/erp/associacoes/{id}/reconciliar` | parcialmente | não explicitamente |
| provider schema | GET | `/integracoes/erp/providers/{slug}/schema` | não | não explicitamente |

### Provider-specific

| Área visual | Método | Endpoint | Provider-specific | Usuário consegue visualizar? |
| --- | --- | --- | ---: | ---: |
| get config | GET | `/integracoes/sankhya/config` | sim | não explicitamente |
| save config | POST | `/integracoes/sankhya/config` | sim | não explicitamente |
| test connection | POST | `/integracoes/sankhya/config/testar-conexao` | sim | não explicitamente |
| sync pessoas | POST | `/integracoes/sankhya/sync/pessoas` | sim | não explicitamente |
| sync produtos | POST | `/integracoes/sankhya/sync/produtos` | sim | não explicitamente |
| sync completo | POST | `/integracoes/sankhya/sync/completo` | sim | não explicitamente |
| logs | GET | `/integracoes/sankhya/logs?limit=10` | sim | não explicitamente |

Conclusão:

- o console usa essas APIs;
- o usuário não enxerga um inventário explícito delas.

Classificação:

- `API_INVENTORY_NOT_EXPOSED`

## 26. APIs externas

### Autenticação

| Capability | Operação | Service/adapter | Método externo | Path externo | Ativa hoje |
| --- | --- | --- | --- | --- | ---: |
| gateway auth | OAuth client credentials | `SankhyaGatewayAuthService` | `POST` | `auth_url` configurada, com tentativa de payload JSON/form | sim |
| gateway auth | legacy login | `SankhyaGatewayAuthService` | `POST` | `auth_url` ou fallback `.../login` | sim |

### WS/serviços externos Sankhya

| Capability | Operação | Service/adapter | Método externo | Path externo | Ativa hoje |
| --- | --- | --- | --- | --- | ---: |
| pessoas | importar PF | `SankhyaPessoaService` | SOAP/WS | `PessoaFisica.findAll` | sim |
| pessoas | importar PJ | `SankhyaPessoaService` | SOAP/WS | `PessoaJuridica.findAll` | sim |
| produtos | importar | `SankhyaProdutoService` | SOAP/WS | `Produto.findAll` | sim |
| nfe | exportar | `SankhyaNFeService` | SOAP/WS | `NFe.save` | sim |
| nfe | importar entrada | `SankhyaNFeService` | SOAP/WS | `NFe.findEntradaByPeriodo` | sim |
| financeiro | exportar contas pagar | `SankhyaFinanceiroService` | SOAP/WS | operação financeira via `SankhyaWSClient` | sim |
| financeiro | exportar contas receber | `SankhyaFinanceiroService` | SOAP/WS | operação financeira via `SankhyaWSClient` | sim |
| financeiro | importar lançamentos | `SankhyaFinanceiroService` | SOAP/WS | operação financeira via `SankhyaWSClient` | sim |

Conclusão:

Existe material suficiente para apresentar ao tenant nomes funcionais sanitizados das operações externas, sem exibir URL completa sensível nem headers.

## 27. Association Center

Arquivos:

- [association-center.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp/association-center.tsx)
- [association-details-sheet.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp/association-details-sheet.tsx)

### O que o usuário consegue visualizar

1. capability: `sim`
2. entidade interna: `sim`
3. ID interno: `sim`
4. entidade externa: `sim`
5. ID externo: `sim`
6. status: `sim`
7. provider: `não explicitamente`
8. histórico: `sim`
9. reconciliação: `sim`
10. payload original: `não`
11. chaves indexadas do payload: `parcialmente`, no sheet
12. ownership: `não`
13. direção: `não`
14. transformação: `não`
15. mostra apenas associações já materializadas: `sim`

Conclusão:

O Association Center resolve vínculos materializados de registros, não mapeamento explícito de campos.

Classificação:

- `RECORD_ASSOCIATION_ONLY`

## 28. Capability Details

Arquivo:

- [capability-details.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp/capability-details.tsx)

O que já existe:

- ownership resumido
- direção
- modo de atualização
- executor label
- jobs relacionados
- timeline
- resumo de associações
- informações técnicas sanitizadas

O que falta:

- catálogo explícito de chaves AgroSaaS × ERP
- mapeamento de campos
- inventário funcional de APIs internas e externas por capability

Conclusão:

`Capability Details` é o melhor local já existente para receber:

- ownership;
- direção;
- chaves;
- campos;
- APIs sanitizadas.

## 29. Backoffice

Arquivo:

- [page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx)

Hoje o backoffice:

- usa endpoints ERP para status/health/jobs/timeline/diagnóstico;
- usa logs Sankhya diretamente;
- comunica que a configuração principal é do tenant;
- ainda é o lugar mais próximo de observabilidade técnica.

Divisão adequada confirmada:

- tenant: configuração, capabilities, associações, sync, status
- backoffice: payload técnico, logs, auditoria técnica mais profunda

## 30. UX

## 30.1 Cenários

### Tenant sem integração

- seletor aparece: `sim`
- formulário após selecionar: `sim, se schema carregar`
- configuração visível: `sim, condicional ao schema`

### Configuração incompleta

- formulário visível: `sim, se schema carregar`
- CTA continuar: `indiretamente, via card e capability actions`

### Configuração conectada

- formulário acessível: `sim`
- secrets mascarados: `sim`
- CTA testar novamente: `sim`

### Credencial inválida

- formulário acessível: `sim`
- mensagem: `sim, por toast`

### Provider desconhecido

- fallback seguro: `sim`
- nenhuma tela falsa: `sim`

### Usuário sem permissão

- mensagem clara no load: `não`
- ocultação silenciosa no load: `sim, potencialmente`

## 30.2 Teste conceitual de navegação

1. abrir a página  
2. `status 404`  
3. escolher Sankhya  
4. carregar `schema`  
5. renderizar formulário  
6. salvar  
7. `status` passa a existir  
8. recarregar  
9. abrir console conectado  
10. localizar formulário  
11. editar URL  
12. testar conexão

Ponto onde o fluxo deixa de apresentar a configuração:

- quando o `schema` não carrega ou carrega sem `fields`;
- quando o usuário não percebe que a configuração está abaixo do bloco extenso de capabilities/associações;
- quando o `schema` expõe campos que não persistem, fazendo parecer que “não funcionam”.

## 31. Segurança

Pontos corretos:

- segredos não retornam em claro;
- masks e flags são usadas;
- payload bruto não é exposto ao tenant;
- detalhes sensíveis ficam reservados ao backoffice/suporte.

Pontos a manter:

- não expor URL completa privada de cliente;
- não expor headers/tokens;
- não expor stack/payload bruto;
- só expor API externa em nome funcional sanitizado.

## 32. Impacto no piloto

### Formulário de configuração ausente

Classificação:

- estruturalmente: `NON_BLOCKING`
- para tenant afetado por falha silenciosa de schema: `PILOT_P1`
- se impedir ajuste de URL/credencial em produção real: `PILOT_BLOCKER`

### Mapeamento de campos não visível

Classificação:

- não bloqueia a conexão;
- `P1` para autonomia operacional;
- relevante antes de reconciliação assistida em massa.

### APIs não visíveis

Classificação:

- não bloqueante para execução;
- importante para transparência e suporte;
- deve ser sanitizado.

## 33. Relação com core repair

| Correção futura | Fase |
| --- | --- |
| contrato runtime de provider para config/operations/descriptors | `ERP-CORE-REPAIR-01A` |
| resolução real de provider | `ERP-CORE-REPAIR-01B` |
| convergência config/load/save | `ERP-CORE-REPAIR-01D` |
| restauração/estabilização da seção de configuração | `ERP-CORE-REPAIR-01E.1` |
| transparência operacional em capability details | `ERP-CORE-REPAIR-01E.2` |
| integração de chaves/associações com Association Center | `ERP-CORE-REPAIR-01E.3` |
| observabilidade e inventário sanitizado de APIs | `ERP-CORE-REPAIR-01F` |

## 34. Achados classificados

| ID | Achado | Classificação | Prioridade |
| --- | --- | --- | --- |
| B01 | formulário ainda existe no `DynamicErpConsole` | `NO_GAP` | `P3` |
| B02 | campos dependem silenciosamente do `schema` | `SCHEMA_FETCH_FAILURE` | `P1` |
| B03 | erro de schema é engolido por `fetchJson` | `SILENT_ERROR` | `P1` |
| B04 | card de configuração fica abaixo de seções extensas | `CONFIG_SECTION_ORDER` | `P1` |
| B05 | CTA/âncora estão corretos | `NO_GAP` | `P3` |
| B06 | `legacy_auth_model` é renderizado mas não persiste | `TYPE_CONTRACT_DRIFT` | `P1` |
| B07 | `ultimo_teste`, `teste_status`, `ultimo_sync` são renderizados como editáveis | `TYPE_CONTRACT_DRIFT` | `P1` |
| B08 | `sync_interval` possui semântica UI/backend desalinhada | `TYPE_CONTRACT_DRIFT` | `P1` |
| B09 | tenant vê associações de registros, não mapeamento de campos | `RECORD_ASSOCIATION_ONLY` | `P2` |
| B10 | catálogo de chaves existe só em código provider-specific | `KEY_MAPPING_NOT_EXPOSED` | `P2` |
| B11 | inventário de APIs não é exposto ao tenant | `API_INVENTORY_NOT_EXPOSED` | `P2` |
| B12 | ownership/direction existem parcialmente por catálogo frontend | `OWNERSHIP_NOT_EXPOSED` | `P2` |

## 35. Causa raiz

### Por que os campos de configuração não aparecem

Porque a renderização útil dos campos depende do `schema`, e o frontend trata falha de schema como `null` sem feedback específico.

Em paralelo:

- a seção de configuração foi mantida no final da página;
- o usuário pode não localizá-la rapidamente;
- parte do schema atual ainda contém campos impróprios para edição.

### Falha é frontend, backend ou contrato

Resposta:

- backend de schema/config existe;
- falha principal de experiência é frontend;
- causa estrutural mais profunda é drift de contrato frontend/backend/schema.

## 36. Decisões

1. O formulário de configuração ainda existe: `sim`
2. Componente que o renderiza: `DynamicErpConsole`
3. Condição para aparecer: `schema com fields`
4. API de schema funciona conceitualmente: `sim`
5. API de config funciona conceitualmente: `sim`
6. A falha principal é frontend, com drift contratual: `sim`
7. O problema afeta tenant sem ERP: `pode afetar, se schema falhar`
8. Afeta configuração incompleta: `sim`
9. Afeta integração conectada: `sim, para edição`
10. Afeta tenant legado: `sim, inclusive com campos legados`
11. É bloqueador universal do piloto: `não`
12. Onde o usuário vê associações hoje: `Association Center` e `AssociationDetailsSheet`
13. Ele vê campos ou apenas registros: `apenas registros materializados`
14. Existe modelo de mapeamento de campos: `não`
15. Existe catálogo de chaves: `em código, não na UI`
16. Existe inventário de APIs: `em código, não na UI`
17. O que já pode ser exibido sem backend novo:
   - chaves por capability
   - ownership
   - direção
   - nomes funcionais de APIs internas e externas
   - labels de operações
18. O que exige contrato novo:
   - descriptor formal de operations/endpoints do provider
   - descriptor formal de field/key mapping
19. Deve existir editor ou apenas visualização: `apenas visualização, nesta fase`
20. Primeira correção recomendada: estabilizar a seção de configuração com tratamento explícito de schema e alinhar o contrato de campos.

## 37. Plano incremental

### ERP-CORE-REPAIR-01A

- contrato formal de provider para:
  - configuração
  - operations
  - capability descriptors
  - keys/ownership/direction

### ERP-CORE-REPAIR-01B

- resolução real de provider

### ERP-CORE-REPAIR-01D

- convergência load/save/reload de configuração
- limpar drift entre schema e payload aceito

### ERP-CORE-REPAIR-01E.1

- restauração/estabilização da seção de configuração
- erro explícito para schema indisponível
- sem mover para tela paralela

### ERP-CORE-REPAIR-01E.2

- transparência operacional em `Capability Details`
- expor:
  - chaves
  - campos somente leitura
  - ownership
  - direção
  - APIs sanitizadas

### ERP-CORE-REPAIR-01E.3

- integrar melhor `Association Center`
- expor vínculos materializados com nomes operacionais de chave

## 38. Arquivos prováveis

- [erp-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp-console.tsx)
- [sankhya-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/sankhya-console.tsx)
- [provider-config-payload.ts](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp/provider-config-payload.ts)
- [types.ts](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp/types.ts)
- [capability-details.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp/capability-details.tsx)
- [capability-details-view-model.ts](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp/capability-details-view-model.ts)
- [association-center.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp/association-center.tsx)
- [association-details-sheet.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp/association-details-sheet.tsx)
- [router.py](/opt/lampp/htdocs/farm/services/api/integracoes/erp/router.py)
- [canonical_adapter.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/canonical_adapter.py)
- [sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py)

## 39. Testes necessários

- caracterização do fluxo `status 404 -> selector -> wrapper -> schema -> form`
- teste de erro explícito quando schema falha
- teste garantindo que o card não fique vazio sem mensagem
- teste para `legacy_auth_model` não aparecer como persistível se continuar não suportado
- teste para campos runtime (`ultimo_teste`, `teste_status`, `ultimo_sync`) não aparecerem como editáveis
- teste de consistência entre `saveConfig` prop e endpoint realmente usado
- teste de `sync_interval` com semântica unificada
- teste de visualização de chaves/associações sem expor payload sensível

## 40. Veredicto

### Configuração

`GO COM RESSALVAS`

Motivo:

- o formulário ainda existe;
- o backend de configuração existe;
- mas a renderização depende silenciosamente do schema e o contrato de campos está desalinhado.

### Transparência operacional

`INSUFICIENTE`

Motivo:

- o tenant vê associações materializadas;
- não vê claramente catálogo de chaves, campos, ownership e inventário de APIs;
- parte dessa informação existe apenas em código ou em catálogo frontend inferido.

### Piloto

`GO COM RESSALVAS`

Motivo:

- a conexão e operação Sankhya continuam viáveis;
- a ausência aparente dos campos não decorre de remoção estrutural do formulário;
- porém a seção de configuração e a transparência operacional ainda precisam estabilização antes de escalar autonomia do administrador do tenant.

