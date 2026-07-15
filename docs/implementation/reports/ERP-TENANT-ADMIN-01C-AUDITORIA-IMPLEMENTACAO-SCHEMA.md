# ERP-TENANT-ADMIN-01C — Auditoria da Implementação do Schema Editável do Provider Sankhya

## Escopo

Auditoria exclusivamente de leitura sobre a cadeia:

Provider -> schema publicado -> console ERP -> formulário -> payload -> persistência -> reload -> runtime.

Nenhuma correção foi aplicada nesta auditoria.

## Arquitetura encontrada

- O provider Sankhya publica contrato declarativo no backend via `MarketplaceIntegracao.connection_schema` e `MarketplaceIntegracao.credential_schema`.
- A origem desses schemas é o provider Sankhya em [services/api/integracoes/sankhya/services/canonical_adapter.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/canonical_adapter.py:322).
- O endpoint público que expõe o schema é [services/api/integracoes/erp/router.py](/opt/lampp/htdocs/farm/services/api/integracoes/erp/router.py:139).
- O frontend carrega o schema desse endpoint e monta o formulário dinamicamente em:
  - [apps/web/src/components/integracoes/erp-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp-console.tsx:329)
  - [apps/web/src/components/integracoes/erp/provider-config-fields.ts](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp/provider-config-fields.ts:69)
  - [apps/web/src/components/integracoes/erp/configuration-section.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp/configuration-section.tsx:74)
- O save monta payload somente a partir dos fields publicados em [apps/web/src/components/integracoes/erp/provider-config-payload.ts](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp/provider-config-payload.ts:12).
- O backend aceita o payload editável em [services/api/integracoes/sankhya/schemas/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/schemas/__init__.py:11) e persiste via [services/api/integracoes/sankhya/services/sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py:848).
- O runtime operacional usa a configuração legada `sankhya_config` sobreposta com credencial canônica em [services/api/integracoes/sankhya/services/sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py:374).

## 1. Schema do provider

### Endpoint auditado

- `GET /api/v1/integracoes/erp/providers/sankhya/schema`
- Existe em [services/api/integracoes/erp/router.py](/opt/lampp/htdocs/farm/services/api/integracoes/erp/router.py:139)
- Retorno esperado: `200`
- Evidência executável: teste `test_obter_schema_do_provider_erp_ativo_retorna_200` em [services/api/tests/unit/integracoes/test_erp_router.py](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_erp_router.py:618)

### Resultado

- Existe: sim
- Retorna 200: sim, coberto por teste unitário
- `connection_schema.fields`: sim
- `credential_schema.fields`: sim
- Schema vazio: não

### Fields publicados

| Campo | Label | Tipo | Obrigatório | Sensível | Somente leitura | Opções | Origem do valor |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `sankhya_environment` | Ambiente Sankhya | `select` | sim | não | não | `producao`, `homologacao`, `sandbox` | `SankhyaConfig.environment`, com default `producao` |
| `sankhya_api_base_url` | URL base da API | `url` | sim | não | não | n/a | `SankhyaConfig.api_base_url`, com fallback de exibição para `ws_url` |
| `sankhya_auth_url` | URL de autenticação | `url` | sim | não | não | n/a | `SankhyaConfig.auth_url` |
| `auth_model` | Modelo de autenticação | `select` | não | não | não | `gateway_oauth_client_credentials`, `gateway_legacy_login`, `legacy_ws_basic_auth` | derivado por `SankhyaGatewayAuthService.auth_model()` |
| `ws_url` | URL WS | `url` | não | não | não | n/a | `SankhyaConfig.ws_url` |
| `sync_interval` | Intervalo de sincronização (minutos) | `integer` | sim | não | não | n/a | `SankhyaConfig.sync_interval` em segundos; UI exibe minutos |
| `sankhya_client_id` | Client ID | `string` | não | não | não | n/a | `SankhyaConfig.client_id` |
| `sankhya_client_secret` | Client Secret | `secret` | não | sim | não | n/a | segredo persistido; reload expõe só máscara |
| `sankhya_x_token` | X-Token | `secret` | não | sim | não | n/a | segredo persistido; reload expõe só máscara |
| `sankhya_token` | Token legado | `secret` | não | sim | não | n/a | segredo persistido; reload expõe só máscara |
| `sankhya_appkey` | AppKey | `secret` | não | sim | não | n/a | segredo persistido; reload expõe só máscara |
| `username` | Usuário | `string` | não | não | não | n/a | `SankhyaConfig.username` |
| `password` | Senha | `secret` | não | sim | não | n/a | segredo persistido; reload expõe só máscara |

Origem da publicação: [services/api/integracoes/sankhya/services/canonical_adapter.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/canonical_adapter.py:322).

## 2. Fonte dos fields

- Os fields são definidos no provider: sim
- Hardcoded no frontend: não
- Montados no router: não
- Carregados de JSON externo: não
- Construídos manualmente no backend: sim, por `ProviderFieldDefinition`

Arquivo responsável:

- [services/api/integracoes/sankhya/services/canonical_adapter.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/canonical_adapter.py:322)

Como chegam ao endpoint:

- O adapter grava/atualiza `connection_schema` e `credential_schema` no registro `MarketplaceIntegracao` em [services/api/integracoes/sankhya/services/canonical_adapter.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/canonical_adapter.py:948)
- O router apenas lê e devolve em [services/api/integracoes/erp/router.py](/opt/lampp/htdocs/farm/services/api/integracoes/erp/router.py:157)

Duplicação existente:

- Sim
- A lista de campos existe em dois contratos:
  - schema declarativo publicado pelo provider
  - schema de entrada do save `SankhyaConfigCreate`

## 3. Paridade: schema x payload x persistência x runtime

### Tabela de paridade

| Campo | Schema | Payload | Persistência | Runtime |
| --- | --- | --- | --- | --- |
| `sankhya_environment` | sim | sim | `sankhya_config.environment` + `connection_payload` | usado |
| `sankhya_api_base_url` | sim | sim | `sankhya_config.api_base_url` + `connection_payload` | usado; pode fallback para `ws_url` |
| `sankhya_auth_url` | sim | sim | `sankhya_config.auth_url` + `connection_payload` | usado em OAuth e legacy login; não usado em WS basic |
| `auth_model` | sim | sim | inferido no legado operacional + `connection_payload` | usado |
| `ws_url` | sim | sim | `sankhya_config.ws_url` + `connection_payload` | usado em legados; em OAuth vira fallback da base |
| `sync_interval` | sim | sim | `sankhya_config.sync_interval` + `connection_payload` | usado |
| `sankhya_client_id` | sim | sim | `sankhya_config.client_id` + `connection_payload` | usado em OAuth; no legacy login funciona como alias de `username` no save |
| `sankhya_client_secret` | sim | sim | `sankhya_config.client_secret` + credencial canônica | usado em OAuth; no legacy login funciona como alias de `password` no save |
| `sankhya_x_token` | sim | sim | `sankhya_config.x_token` + credencial canônica | usado em OAuth |
| `sankhya_token` | sim | sim | `sankhya_config.token` + credencial canônica | usado em legacy login |
| `sankhya_appkey` | sim | sim | `sankhya_config.appkey` + credencial canônica | usado em legacy login |
| `username` | sim | sim | `sankhya_config.username` + `connection_payload` | usado nos modelos legados |
| `password` | sim | sim | `sankhya_config.password` + credencial canônica | usado nos modelos legados; em OAuth pode ser salvo sem efeito operacional |

### Respostas objetivas

- Existe field publicado que o backend ignora: sim, de forma condicional por `auth_model`
- Existe field persistido que não aparece no schema: sim, mas são metadados ou legado não editável, por exemplo `ativo`, `ultimo_teste`, `teste_status`, `ultimo_sync`, flags/masks de segredos, `provider_definition`, `feature_schema`
- Existe field editável que não chega ao runtime: sim, em alguns modelos

### Achados de paridade

1. `password` é publicável e editável em qualquer contexto, mas no modelo `gateway_oauth_client_credentials` não participa da autenticação operacional.
2. `username` é publicável sempre, mas em `gateway_oauth_client_credentials` é zerado no normalize e não compõe o runtime.
3. `sankhya_token` e `sankhya_appkey` ficam mortos em OAuth.
4. `sankhya_client_id`, `sankhya_client_secret` e `sankhya_x_token` ficam mortos em `legacy_ws_basic_auth`.
5. Em `gateway_legacy_login`, `sankhya_client_id` e `sankhya_client_secret` podem ser aproveitados como aliases de `username` e `password`, o que cria semântica híbrida.

## 4. Console ERP

Componentes auditados:

- [apps/web/src/components/integracoes/erp-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp-console.tsx:281)
- [apps/web/src/components/integracoes/erp/configuration-section.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp/configuration-section.tsx:74)
- [apps/web/src/components/integracoes/erp/provider-config-fields.ts](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp/provider-config-fields.ts:69)

Respostas objetivas:

- O formulário aparece: sim
- Aparece só o resumo: não
- Existe fallback silencioso: não no `ConfigurationSection`; os estados são explícitos
- Existe bloqueio de renderização: sim, proposital, se o schema falha ou não há fields editáveis
- Existe estado "schema vazio": sim, explícito
- Existe hardcode Sankhya: sim
- Existe `if provider == sankhya`: no shell genérico não há `if` explícito com esse texto, mas há dependência estrutural de Sankhya

Evidências:

- `showForm = schemaState.status === "success" && hasEditableFields` em [configuration-section.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp/configuration-section.tsx:74)
- Estados explícitos `loading`, `forbidden`, `error`, `empty`, `config_forbidden`, `config_error`, `config_not_found` em [configuration-section.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp/configuration-section.tsx:77)
- Fields runtime-only e `legacy_auth_model` são filtrados em [provider-config-fields.ts](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp/provider-config-fields.ts:7)

Hardcodes encontrados no console:

- `providerSlug = "sankhya"` default em [erp-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp-console.tsx:281)
- fallback visual `currentErpLabel || "Sankhya"` em [erp-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp-console.tsx:560)
- resumo de configuração usando `config.sankhya_*` em [erp-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp-console.tsx:810)
- wrapper dedicado em [apps/web/src/components/integracoes/sankhya-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/sankhya-console.tsx:1)

## 5. Auth model

Respostas objetivas:

- É publicado: sim
- É editável: sim
- As opções estão corretas: sim, backend e frontend convergem para 3 opções
- Existe valor legado: sim, `legacy_ws_basic_auth`
- Existe fallback escondido: sim
- Existe valor aceito pelo backend que não aparece no frontend: não

Fallback escondido identificado:

- Se `auth_model` não vier no save, o backend infere o modelo com base nas credenciais informadas ou no estado atual em [services/api/integracoes/sankhya/services/sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py:549)

Conclusão:

- `auth_model` funciona, mas não é contrato estritamente obrigatório em runtime, porque o backend ainda possui inferência implícita.

## 6. URLs

URLs auditadas:

- `sankhya_api_base_url`
- `sankhya_auth_url`
- `ws_url`

Respostas objetivas:

- Todas aparecem: sim
- São editáveis: sim
- São persistidas: sim
- São recarregadas: sim
- O runtime usa exatamente essas URLs: não, usa com fallback/derivação

Fallbacks observados:

- Em OAuth, `ws_url` assume `api_base_url` se ausente
- Em legacy login, `auth_url` cai para `api_base_url` ou `ws_url` se ausente
- Em legacy login, `api_base_url` cai para `ws_url` ou `auth_url`
- Em WS basic, `api_base_url` cai para `ws_url`

Conclusão:

- As URLs são editáveis e operacionais, mas o runtime não é um espelho literal do formulário; ele normaliza e deriva valores.

## 7. Credenciais

Credenciais publicadas no schema:

- `sankhya_client_id`
- `sankhya_client_secret`
- `sankhya_x_token`
- `sankhya_token`
- `sankhya_appkey`
- `username`
- `password`

Respostas objetivas:

- Quais aparecem: todas as acima
- Quais permanecem ocultas: `client_secret`, `x_token`, `token`, `appkey`, `password`
- Quais realmente são utilizadas pelo runtime: depende do `auth_model`
- Existe campo morto: sim, de forma condicional

Uso real por modelo:

- `gateway_oauth_client_credentials`
  - usa `sankhya_api_base_url`, `sankhya_auth_url`, `sankhya_client_id`, `sankhya_client_secret`, `sankhya_x_token`
  - ignora `sankhya_token`, `sankhya_appkey`, `username`
  - `password` pode ser salvo, mas não participa da autenticação
- `gateway_legacy_login`
  - usa `sankhya_auth_url`, `sankhya_token`, `sankhya_appkey`, `username`, `password`
  - aceita `sankhya_client_id` e `sankhya_client_secret` como aliases de `username` e `password`
  - ignora `sankhya_x_token`
- `legacy_ws_basic_auth`
  - usa `ws_url`, `username`, `password`
  - ignora `sankhya_auth_url`, `sankhya_client_secret`, `sankhya_x_token`, `sankhya_token`, `sankhya_appkey`

## 8. Save

Fluxo auditado:

- editar -> salvar -> reload -> nova leitura

Evidências:

- Save no frontend em [erp-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp-console.tsx:457)
- Payload dinâmico em [provider-config-payload.ts](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp/provider-config-payload.ts:12)
- Reload pós-save em [erp-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp-console.tsx:486)
- E2E de save/reload em [apps/web/tests/e2e/erp-console-configuracao.spec.ts](/opt/lampp/htdocs/farm/apps/web/tests/e2e/erp-console-configuracao.spec.ts:377) e [apps/web/tests/e2e/erp-console-configuracao.spec.ts](/opt/lampp/htdocs/farm/apps/web/tests/e2e/erp-console-configuracao.spec.ts:729)

Respostas objetivas:

- Existe perda de dados: não evidenciada no fluxo coberto
- Existe campo ignorado: sim, condicional por `auth_model`
- Existe campo que muda de valor: sim, `sync_interval` muda de minutos na UI para segundos na persistência
- Existe recriptografia desnecessária: não no fluxo normal de reload, porque segredo mascarado/inalterado não é reenviado
- Existe rotação de credencial: sim, quando segredo realmente muda

Observações:

- O frontend evita reenvio de segredo mascarado ou inalterado em [provider-config-payload.ts](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp/provider-config-payload.ts:28)
- O backend marca rotação quando houve alteração real de segredo em [services/api/integracoes/sankhya/services/sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py:885)
- Há evidência de evento `integrations.credential_rotated` em [services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py:353)

## 9. Teste de conexão

Respostas objetivas:

- O botão aparece: sim, quando há schema carregado e endpoint habilitado
- Usa exatamente o payload salvo: sim, usa a configuração operacional persistida
- Cria payload temporário: não

Evidência:

- Frontend envia `POST` sem body em [erp-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp-console.tsx:496)
- Backend lê `_get_operational_config(tenant_id)` em [services/api/integracoes/sankhya/services/sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py:1045)

## 10. Runtime

Auditoria de runtime:

- `SankhyaSyncService`: usa `_get_operational_config`
- `SankhyaGatewayAuthService`: determina `auth_model` e valida credenciais
- `canonical_adapter`: projeta conexão canônica, credencial canônica e payload de runtime

Resposta objetiva:

- O runtime utiliza exatamente os valores do formulário: não
- Existe fallback oculto: sim

Fallbacks relevantes:

- inferência de `auth_model`
- aliases `client_id -> username` e `client_secret -> password` no legacy login
- derivação entre `api_base_url`, `auth_url` e `ws_url`
- sobreposição da credencial canônica em cima da config legada

## 11. Hardcodes

### Legítimos

- Uso de `sankhya_*` dentro do provider Sankhya no backend
- Wrapper `SankhyaConsole`
- Endpoints provider-specific do console Sankhya

### Arquiteturalmente incorretos

- `DynamicErpConsole` com default `providerSlug = "sankhya"`
- fallback visual `"Sankhya"` no console genérico
- cards de resumo lendo diretamente `config.sankhya_*`
- tipo `ErpConsoleConfig` modelado com shape Sankhya em [apps/web/src/components/integracoes/erp/types.ts](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp/types.ts:94)
- registry de consoles com apenas `sankhya` em [erp-provider-registry.ts](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp/erp-provider-registry.ts:1)

## 12. Duplicações

Existe mais de uma fonte da verdade: sim

Duplicações encontradas:

1. Contrato de campos duplicado entre schema publicado e schema aceito pelo save
2. Conexão persistida tanto em `sankhya_config` quanto em `tenant_integracoes.connection_payload`
3. Credenciais persistidas em colunas legadas criptografadas e também em `integration_credentials`
4. Metadata de credencial mascarada também aparece dentro de `connection_payload`

Impacto:

- aumenta risco de drift entre schema, payload e runtime
- multiplica pontos de fallback

## 13. Multiprovider

Resposta objetiva:

- Se amanhã existir TOTVS, o console genérico não está pronto de forma limpa

Justificativa técnica:

- o carregamento do schema é genérico
- a montagem dos campos editáveis é genérica
- porém o shell visual, o tipo de config, os cards-resumo, o registry e o wrapper operacional ainda dependem de Sankhya

Conclusão:

- multiprovider: parcialmente preparado no contrato
- multiprovider: não preparado no console e no shape de configuração

## 14. Testes encontrados

### Backend

- [services/api/tests/unit/integracoes/test_erp_router.py](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_erp_router.py)
- [services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py)
- [services/api/tests/unit/integracoes/test_sankhya_gateway_test_connection.py](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_sankhya_gateway_test_connection.py)
- [services/api/tests/unit/integracoes/test_sankhya_governed_integration.py](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_sankhya_governed_integration.py)
- [services/api/tests/unit/integracoes/test_sankhya_paridade_config.py](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_sankhya_paridade_config.py)
- [services/api/tests/unit/integracoes/test_erp_bootstrap_tardio.py](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_erp_bootstrap_tardio.py)
- [services/api/tests/unit/integracoes/test_sankhya_diagnostico_timezone.py](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_sankhya_diagnostico_timezone.py)
- [services/api/tests/unit/integracoes/test_sankhya_legacy_reconciliation.py](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_sankhya_legacy_reconciliation.py)

### Frontend unit

- [apps/web/src/components/integracoes/erp/provider-config-fields.test.ts](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp/provider-config-fields.test.ts)
- [apps/web/src/components/integracoes/erp/provider-config-payload.test.ts](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp/provider-config-payload.test.ts)
- [apps/web/src/components/integracoes/erp/configuration-section.test.ts](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp/configuration-section.test.ts)
- [apps/web/src/components/integracoes/erp/provider-console-endpoints.test.ts](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp/provider-console-endpoints.test.ts)
- [apps/web/src/components/integracoes/erp-console.test.ts](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp-console.test.ts)
- [apps/web/tests/unit/integracoes/erp-config-binding.test.tsx](/opt/lampp/htdocs/farm/apps/web/tests/unit/integracoes/erp-config-binding.test.tsx)

### Frontend E2E

- [apps/web/tests/e2e/erp-console-configuracao.spec.ts](/opt/lampp/htdocs/farm/apps/web/tests/e2e/erp-console-configuracao.spec.ts)

### Cobertura pedida

- teste unitário do schema: sim
- teste do save: sim
- teste do reload: sim
- teste do `auth_model`: sim
- teste do primeiro cadastro: sim
- teste do tenant legado: sim
- E2E: sim

## 15. Frontend

Execuções realizadas:

- `pnpm typecheck`: ok
- `pnpm lint`: ok
- `pnpm build`: ok

Limitação:

- o script `pnpm lint` do projeto atual não faz varredura global do frontend; ele executa o conjunto configurado pelo próprio `package.json`

## 16. Backend

Execuções realizadas:

- `pytest` relacionado ao ERP/Sankhya: ok, `94 passed in 19.79s`
- `ruff` relacionado ao ERP/Sankhya: falhou

Falhas de `ruff` diretamente no escopo auditado:

- imports não usados e variáveis não usadas em `services/api/integracoes/sankhya/routers/__init__.py`
- linha longa em `services/api/integracoes/sankhya/schemas/__init__.py`

## 17. Diff

Execuções realizadas:

- `git diff --check`: ok
- `git -C apps/web diff --check`: ok

Observação:

- o worktree está sujo, mas sem erro de whitespace/merge-marker nessas checagens

## Problemas encontrados

1. O contrato é editável e funcional, mas não é estritamente isomórfico ao runtime por causa dos fallbacks.
2. `password` pode ser persistido mesmo em OAuth, sem efeito operacional.
3. O console dito genérico ainda contém acoplamento visível ao shape Sankhya.
4. Há duplicação de fontes da verdade entre schema, DTO de save, persistência legada e persistência canônica.
5. `ruff` não está limpo no escopo auditado.

## Conformidades

1. O schema do provider existe e não está vazio.
2. O endpoint público do schema ERP está implementado.
3. O formulário realmente é montado a partir do schema publicado.
4. O payload do save é derivado dos fields editáveis do schema.
5. O save recarrega a configuração após persistência.
6. O teste de conexão usa a configuração salva, não estado temporário do form.
7. Há cobertura automatizada de schema, save, reload, `auth_model`, bootstrap tardio e tenant legado.

## Riscos

1. Drift entre schema publicado e schema aceito no backend.
2. Drift entre persistência legada e canônica.
3. Expansão para multiprovider pode quebrar no console genérico por acoplamento residual com Sankhya.
4. Campos condicionais expostos fora do contexto do `auth_model` podem confundir operação e suporte.

## Pendências

1. Remover hardcodes Sankhya do shell genérico do console ERP.
2. Reduzir duplicação entre schema publicado e contrato de save.
3. Revisar campos sempre expostos mas condicionalmente mortos.
4. Sanear passivos de `ruff`.

## Limitações da auditoria

1. O retorno `200` do endpoint do schema foi confirmado por implementação e teste unitário, não por chamada HTTP contra servidor local em execução.
2. A auditoria não alterou dados reais de tenant nem executou chamadas externas ao Sankhya.
3. A avaliação de runtime foi feita por código e testes locais.

## Veredicto

### Veredicto final

**GO COM RESSALVAS**

### Motivo

A implementação do schema editável do provider Sankhya está concluída no que diz respeito a publicação do schema, renderização do formulário, save, reload e uso operacional da configuração persistida. Porém a fase ainda deixa ressalvas arquiteturais relevantes:

- fallbacks ocultos no runtime
- campos condicionalmente mortos
- acoplamento residual do console genérico a Sankhya
- duplicação de contratos e persistência
- `ruff` não limpo no escopo auditado
