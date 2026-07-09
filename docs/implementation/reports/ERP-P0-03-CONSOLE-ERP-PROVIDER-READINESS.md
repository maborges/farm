# ERP-P0-03 - Console ERP Provider Readiness

## Resumo executivo

O console do tenant em `/dashboard/settings/integracoes/erp` foi evoluido para exibir a prontidao real do provider ERP com base no contrato canonico ja materializado no runtime.

O que mudou:

* o payload de configuracao passou a expor `provider_definition`, `feature_schema`, `sync_schema`, `health_schema`, `provider_code`, `provider_name` e `provider_display_name`;
* o payload de status passou a trazer `prioridade`, `batch_size` e `timeout_seconds` das policies canonicas;
* a interface passou a mostrar provider atual, modelo de conexao, capability matrix, policies, health, pendencias e prontidao do piloto restrito;
* as credenciais permanecem mascaradas.

Nao foram criadas nova rota, novo endpoint, novo runtime ou novo console paralelo.

## Arquivos auditados

* `apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx`
* `apps/web/src/components/integracoes/sankhya-console.tsx`
* `apps/web/src/components/integracoes/sankhya-timeline.tsx`
* `services/api/integracoes/sankhya/routers/__init__.py`
* `services/api/integracoes/sankhya/services/auth_service.py`
* `services/api/integracoes/sankhya/services/sync_service.py`
* `services/api/integracoes/sankhya/services/canonical_adapter.py`
* `services/api/integracoes/sankhya/schemas/__init__.py`
* `services/api/integracoes/models.py`
* `services/api/tests/unit/integracoes/test_sankhya_governed_integration.py`
* `services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py`

## Arquivos alterados

* `apps/web/src/components/integracoes/sankhya-console.tsx`
* `services/api/integracoes/sankhya/routers/__init__.py`
* `services/api/integracoes/sankhya/schemas/__init__.py`
* `services/api/integracoes/sankhya/services/sync_service.py`
* `services/api/tests/unit/integracoes/test_sankhya_governed_integration.py`

## Confirmacao da auditoria Gateway Sankhya

Confirmado:

* o acesso ao provider atual continua sendo mediado por Gateway;
* o endpoint de autenticacao continua sendo `/authenticate`;
* os parametros esperados seguem sendo `sankhya_environment`, `sankhya_api_base_url`, `sankhya_auth_url`, `sankhya_client_id`, `sankhya_client_secret` e `sankhya_x_token`;
* o health depende da autenticacao correta no Gateway;
* tokens, secrets e X-Token continuam mascarados e nao sao expostos em tela ou log da interface.

Nao foi encontrada divergencia estrutural entre o contrato materializado e a leitura feita pelo console apos o ajuste. A divergencia encontrada era a ausencia de exposicao desse contrato na resposta consumida pela UI.

## Como o console consome o contrato canonico

O console continua consumindo os endpoints oficiais existentes:

* `/integracoes/sankhya/config`
* `/integracoes/sankhya/status`
* `/integracoes/sankhya/health`
* `/integracoes/sankhya/jobs`
* `/integracoes/sankhya/logs`
* `/integracoes/sankhya/timeline`
* `/integracoes/sankhya/diagnostico`
* `/integracoes/sankhya/associacoes/pendentes`

Agora o backend injeta no payload de configuracao os campos canonicos vindos do `MarketplaceIntegracao` materializado pelo adapter:

* `provider_definition`
* `feature_schema`
* `sync_schema`
* `health_schema`
* `connection_schema`
* `credential_schema`

A UI passa a ler esses campos para renderizar:

* provider atual;
* modelo de conexao;
* capability matrix;
* policies resumidas;
* health;
* prontidao para piloto restrito.

## Como o console evita hardcode de Sankhya

* O texto visivel foi generalizado para `Integrações ERP`, `Provider atual`, `Modelo de conexão`, `Capabilities`, `Policies`, `Health` e `Prontidão do piloto restrito`.
* Sankhya aparece apenas como provider atual e como namespace tecnico dos endpoints existentes.
* O componente nao recalcula uma regra paralela; ele apenas apresenta o contrato canônico retornado pelo runtime.

## Como o console evita exposicao de credenciais

* `client_secret` e `x_token` sao tratados como campos mascarados.
* A tela mostra apenas placeholders e flags de configuracao.
* O payload de teste e de configuracao nao imprime segredos.
* O backend continua retornando apenas mascaras e flags de presenca.

## Como o readiness P0 foi exibido

O console passou a consolidar o piloto restrito usando:

* provider configurado;
* health atual;
* capability matrix P0;
* policies ativas para features P0.

O estado exibido foi classificado como:

* `Apto ao piloto`
* `Pendente`
* `Bloqueado`

com lista de pendencias. Essa leitura segue o runtime oficial exposto pelo backend, sem criar regra nova no frontend.

## Duplicidades evitadas

* Nao foi criada nova rota.
* Nao foi criado novo endpoint.
* Nao foi criado novo runtime.
* Nao foi criada nova policy.
* Nao foi criada nova tabela.
* Nao foi criado novo console paralelo.
* Nao foi criado segundo modelo de capability.

## Lacunas remanescentes

* O namespace tecnico do componente ainda e `SankhyaConsole`, embora a UX esteja generica.
* O console segue usando os endpoints do provider atual; a abstração multi-provider continua sendo responsabilidade da arquitetura e do runtime existente.
* A area de sincronizacao manual e de timeline continua presas ao provider atual, o que e aceitavel para o P0 mas ainda nao representa um console totalmente agnostico em nivel de implementação.

## Testes executados

Backend:

```bash
services/api/.venv/bin/pytest services/api/tests/unit/integracoes/test_sankhya_governed_integration.py -q
```

Resultado:

* `13 passed`

Frontend:

```bash
npm run typecheck
```

Resultado:

* concluido com sucesso

Validacao estrutural:

```bash
git diff --check
```

Resultado:

* sem divergencias

## Veredicto final

**GO COM RESSALVAS**

Motivo:

* o console agora consome o contrato canonico e mostra prontidao real do provider;
* a exposicao de gateway, health, capabilities, policies e pendencias foi consolidada;
* a ressalva e que a implementacao ainda usa namespaces e endpoints do provider atual, o que e esperado para o P0, mas nao constitui ainda um console multi-provider completamente desacoplado.
