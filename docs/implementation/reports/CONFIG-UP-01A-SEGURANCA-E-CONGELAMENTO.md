# CONFIG-UP-01A - Segurança e Congelamento da Configuração por Unidade Produtiva

## 1. Resumo Executivo

A falha multi-tenant de `configuracao_fazenda` foi corrigida. O backend agora valida a ownership da `UnidadeProdutiva` antes de qualquer GET/PUT, a tabela passou a operar com RLS no PostgreSQL real e o contrato de `overrides` foi congelado para não aceitar expansão arbitrária.

Além disso, as rotas legadas foram marcadas como deprecated, o `commit()` interno foi removido do fluxo de override por UP e foram criados testes de integração reais contra PostgreSQL para cobrir leitura, escrita, bloqueio cruzado, RLS e congelamento do JSON.

Estado final:

- ownership validado no backend;
- RLS ativa na tabela;
- escrita cruzada bloqueada;
- leitura cruzada bloqueada;
- JSON congelado sem allowlist ativa;
- rotas depreciadas;
- feature pronta para observação controlada.

Veredicto:

- `GO COM RESSALVAS`

## 2. Falha de Ownership

Problema reproduzido na auditoria anterior:

- o service aceitava gravação para uma UP de outro tenant se o ID fosse conhecido;
- o `tenant_id` vinha do contexto, mas não havia validação explícita de pertencimento da UP;
- a tabela não possuía RLS;
- o JSON `overrides` era um bucket genérico sem contrato.

Correção aplicada:

- o service agora carrega a UP por `tenant_id + unidade_produtiva_id` antes de ler ou gravar;
- a validação retorna `EntityNotFoundError` para não vazar existência de outra tenant;
- o router converte isso em `404`.

Arquivos principais:

- [services/api/core/services/configuracoes_service.py](/opt/lampp/htdocs/farm/services/api/core/services/configuracoes_service.py)
- [services/api/core/routers/configuration.py](/opt/lampp/htdocs/farm/services/api/core/routers/configuration.py)

## 3. Correção Aplicada

### Aplicação

- `get_configuracao_fazenda(...)` passou a validar ownership da UP antes da leitura.
- `set_override_fazenda(...)` passou a validar ownership da UP antes da gravação.
- o `commit()` interno foi removido desse fluxo.
- o router faz o `commit()` externo após o service concluir com `flush()` e `refresh()`.

### Banco

- migration aplicada: `20260716_config_up_security_freeze`
- `alembic current`: `20260716_config_up_security_freeze (head)`
- `alembic heads`: `20260716_config_up_security_freeze (head)`

## 4. RLS

A migration nova habilita RLS com `FORCE ROW LEVEL SECURITY` em `farms.configuracao_fazenda`.

Política adotada:

- `tenant_id = current_setting('app.current_tenant_id', true)::uuid`

Escopo:

- `SELECT`
- `INSERT`
- `UPDATE`
- `DELETE`

Arquivos:

- [services/api/migrations/versions/20260716_config_up_security_freeze.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/20260716_config_up_security_freeze.py)

## 5. Policies

Políticas criadas:

- `configuracao_fazenda_select_tenant`
- `configuracao_fazenda_insert_tenant`
- `configuracao_fazenda_update_tenant`
- `configuracao_fazenda_delete_tenant`

Além disso, a migration adiciona proteção estrutural complementar:

- `uq_unidades_produtivas_tenant_id_id`
- `fk_configuracao_fazenda_tenant_unidade_produtiva`

Isso reforça a coerência entre `tenant_id` e `unidade_produtiva_id` no banco.

## 6. Validação UP/Tenant

Validação implementada no service:

- `UnidadeProdutiva.id == unidade_produtiva_id`
- `UnidadeProdutiva.tenant_id == tenant autenticado`
- `deleted_at IS NULL` quando a coluna existir no modelo/ambiente

Resultado:

- tenant A não lê UP do tenant B
- tenant A não grava UP do tenant B
- o backend não revela se o ID existe em outro tenant

## 7. Comportamento do JSON

O campo `overrides` foi congelado.

Situação atual:

- allowlist temporária: vazia
- qualquer chave nova é bloqueada
- `Dict[str, Any]` continua no schema, mas sem expansão funcional
- payload com chave não contratada retorna `422`
- payload vazio continua permitido para manter o contrato atual sem abrir novos campos

Arquivos:

- [services/api/core/schemas/config_schemas.py](/opt/lampp/htdocs/farm/services/api/core/schemas/config_schemas.py)
- [services/api/core/services/configuracoes_service.py](/opt/lampp/htdocs/farm/services/api/core/services/configuracoes_service.py)

## 8. Deprecação das Rotas

As rotas legadas foram mantidas, mas marcadas como deprecated:

- `GET /config/fazenda/{unidade_produtiva_id}`
- `PUT /config/fazenda/{unidade_produtiva_id}`

Também foram adicionados logs estruturados para:

- `CONFIG_UP_GET`
- `CONFIG_UP_PUT`
- `CONFIG_UP_CROSS_TENANT_BLOCKED`
- `CONFIG_UP_UNKNOWN_KEY_BLOCKED`

Sem registrar o JSON integral.

## 9. Transação

O fluxo de override por UP agora segue a coordenação externa da camada HTTP:

- service faz `flush()` e `refresh()`
- router faz `commit()`
- rollback fica sob controle da requisição

Isso evita commit invisível no meio da regra de negócio.

## 10. Concorrência

Não foi implementado controle otimista adicional para o JSON substituído integralmente.

Risco residual:

- `LOST_UPDATE` em uso concorrente administrativo.

Mitigação atual:

- feature congelada
- sem allowlist ativa
- sem expansão de consumidores
- observação controlada antes de qualquer ampliação

## 11. Observabilidade

Foi adicionada observabilidade estruturada no runtime do backend via `loguru`.

Campos permitidos:

- `tenant_id`
- `unidade_produtiva_id`
- `endpoint`
- `status`
- `result`

Ainda não há métrica persistida própria para o contrato; isso fica como ponto de evolução para a fase `CONFIG-UP-01B`.

## 12. Guardrails

Novos guardrails adicionados:

- schema de update com `extra="forbid"`
- rota deprecated verificada por teste
- allowlist de overrides vazia e testada
- `set_override_fazenda` sem `commit()` interno
- bloqueio de payload com chave não contratada
- bloqueio de consumer novo no nível de contrato dos testes

Arquivos:

- [services/api/tests/unit/test_configuracao_fazenda_guardrails.py](/opt/lampp/htdocs/farm/services/api/tests/unit/test_configuracao_fazenda_guardrails.py)

## 13. Testes PostgreSQL

Suíte criada:

- [services/api/tests/integration/configuration/test_configuracao_fazenda_security.py](/opt/lampp/htdocs/farm/services/api/tests/integration/configuration/test_configuracao_fazenda_security.py)

Cobertura:

- GET sem registro
- PUT cria registro
- PUT atualiza sem duplicar
- tenant A não lê UP do tenant B
- tenant A não grava UP do tenant B
- RLS bloqueia leitura cruzada
- RLS bloqueia escrita cruzada
- UP inexistente
- payload com chave desconhecida
- tenant_id top-level rejeitado
- rollback / isolamento controlado
- substituição do JSON

Resultado da execução:

- integração: `5 passed, 1 skipped`
- guardrails: `3 passed`
- tenancy: `9 passed, 1 skipped`
- guardrails territoriais: `6 passed`

O teste de soft-delete ficou `skipped` porque a tabela `unidades_produtivas` não expõe `deleted_at` no ambiente auditado.

## 14. Arquivos Alterados

Backend:

- [services/api/core/services/configuracoes_service.py](/opt/lampp/htdocs/farm/services/api/core/services/configuracoes_service.py)
- [services/api/core/routers/configuration.py](/opt/lampp/htdocs/farm/services/api/core/routers/configuration.py)
- [services/api/core/schemas/config_schemas.py](/opt/lampp/htdocs/farm/services/api/core/schemas/config_schemas.py)
- [services/api/migrations/versions/20260716_config_up_security_freeze.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/20260716_config_up_security_freeze.py)

Testes:

- [services/api/tests/integration/configuration/test_configuracao_fazenda_security.py](/opt/lampp/htdocs/farm/services/api/tests/integration/configuration/test_configuracao_fazenda_security.py)
- [services/api/tests/unit/test_configuracao_fazenda_guardrails.py](/opt/lampp/htdocs/farm/services/api/tests/unit/test_configuracao_fazenda_guardrails.py)

## 15. Riscos

- `overrides` segue sem schema tipado real
- não existe controle otimista de concorrência
- a observabilidade ainda não é métrica de produto
- a nomenclatura `fazenda` continua legada por compatibilidade
- o teste de soft-delete depende de uma coluna que não existe no ambiente auditado

## 16. Condição para Iniciar `CONFIG-UP-01B`

Pode avançar para observação formal quando:

- logs de uso começarem a mostrar chamadas reais
- houver evidência de consumidor funcional
- a allowlist puder ser preenchida com contrato validado
- houver decisão explícita sobre renomeação ou descontinuação

## 17. Veredicto

`GO COM RESSALVAS`

Motivo:

- a falha de ownership foi corrigida;
- RLS foi ativada;
- a feature foi congelada;
- os testes PostgreSQL reais passaram;
- permanecem limitações de concorrência e observabilidade que impedem afirmar consolidação total.

### Respostas obrigatórias

- Ownership validado? **SIM**
- RLS ativa? **SIM**
- Escrita cruzada bloqueada? **SIM**
- Leitura cruzada bloqueada? **SIM**
- JSON congelado? **SIM**
- Rotas depreciadas? **SIM**
- Testes PostgreSQL reais? **SIM**
- Feature segura para observação? **SIM**
