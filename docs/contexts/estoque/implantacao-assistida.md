# Contexto: Implantação Assistida de Estoque

## Propósito

Submódulo de estoque voltado à entrada assistida de dados legados para início rápido de operação, sem migrar histórico completo.

## Escopo funcional atual

- template CSV oficial
- preview com aliases e mapeamento explícito
- validação por tenant
- sessão persistida de implantação
- correção assistida por linha
- revalidação
- aptidão para confirmação
- confirmação transacional
- gravação canônica em `SALDO_INICIAL`
- proveniência explícita `IMPLANTACAO`
- auditoria da trilha da sessão
- frontend operacional completo

## Regras invariantes

- toda sessão é tenant-scoped;
- não há match cross-tenant de produto ou depósito;
- não há uso de `ENTRADA`, `AJUSTE` ou `MANUAL` para confirmar implantação;
- itens `IGNORADO` não entram na confirmação;
- itens com `ERRO` bloqueiam confirmação;
- a sessão confirmada ou cancelada fica bloqueada para edição.

## Permissões

- `estoque:implantacao_assistida:view`
- `estoque:implantacao_assistida:list`
- `estoque:implantacao_assistida:create`
- `estoque:implantacao_assistida:edit`
- `estoque:implantacao_assistida:approve`
- `estoque:implantacao_assistida:delete`
- `tenant:audit:view` para consulta de auditoria

## Proveniência canônica

Na confirmação, cada item confirmável gera movimento em `estoque_movimentos` com:

- `tipo_movimento = SALDO_INICIAL`
- `origem = IMPLANTACAO`
- `origem_id` apontando para o contexto da implantação

Compatibilidade preservada:

- a constraint de origem mantém `LEGADO` para dados históricos já suportados;
- a implantação nova usa exclusivamente `IMPLANTACAO`.

## UX operacional

- `ERRO` em vermelho
- `AVISO` em amarelo
- `VALIDA`/`CORRIGIDO` em verde
- confirmação bloqueada até aptidão positiva
- checkbox obrigatório informando gravação como `SALDO_INICIAL`
- links pós-confirmação para saldos, movimentações e auditoria

## Cobertura de testes atual

- unitários do service
- integração HTTP do fluxo principal
- testes de estoque/ledger relacionados
- Playwright mínimo do fluxo crítico do frontend

## Riscos residuais

- ainda não há suíte visual/regressão ampla do frontend;
- warnings de Pydantic v2 seguem fora do escopo deste submódulo;
- o ambiente local pode conter schema pré-criado por testes antigos, exigindo migrations idempotentes, já tratadas nas revisions da implantação.
