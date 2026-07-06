# DB-MIGRATION-FIX-02 — Auditoria e Correção Segura da Divergência Sankhya

## Escopo auditado

- [services/api/migrations/versions/fase3_sankhya.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/fase3_sankhya.py)
- [services/api/migrations/versions/1795966a0c0a_merge_all_heads.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/1795966a0c0a_merge_all_heads.py)
- [services/api/migrations/versions/20260704_sankhya_gateway_auth.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/20260704_sankhya_gateway_auth.py)
- estado físico do schema `farms`
- estado lógico em `farms.alembic_version`

## Estado atual do Alembic no início da auditoria

- `alembic heads`: `20260706_integrations_external_record_links_pending_local`
- `alembic current`: `20260703_ops_intelligence_02_recommendations_foundation`
- `alembic upgrade head`: falhava em `20260704_sankhya_gateway_auth`
- erro: `UndefinedTableError: relation "sankhya_config" does not exist`

## Ordem real das migrations Sankhya

### Cadeia identificada

1. `fase3_sankhya`
2. `1795966a0c0a_merge_all_heads`
3. cadeia posterior até `20260703_ops_intelligence_02_recommendations_foundation`
4. `20260704_sankhya_gateway_auth`
5. `20260706_integrations_external_record_links`
6. `20260706_integrations_external_record_links_pending_local`

### Implicação

Quando o banco estava em `20260703_ops_intelligence_02_recommendations_foundation`, a fundação física da Sankhya já deveria existir há muito tempo. O erro não era de ordem lógica das migrations atuais, e sim de divergência histórica entre o banco físico e a cadeia já registrada pelo Alembic.

## Objetos esperados por `fase3_sankhya`

### Tabelas

- `sankhya_config`
- `sankhya_sync_logs`
- `sankhya_pessoas`
- `sankhya_produtos`
- `sankhya_nfe`
- `sankhya_lancamentos_financeiros`
- `sankhya_tabelas`

### Índices

- `ix_sankhya_config_id`
- `ix_sankhya_config_tenant_id`
- `ix_sankhya_sync_logs_id`
- `ix_sankhya_sync_logs_tenant_id`
- `ix_sankhya_sync_logs_created_at`
- `ix_sankhya_pessoas_id`
- `ix_sankhya_pessoas_tenant_id`
- `ix_sankhya_pessoas_sankhya_id`
- `ix_sankhya_produtos_id`
- `ix_sankhya_produtos_tenant_id`
- `ix_sankhya_produtos_sankhya_id`
- `ix_sankhya_nfe_id`
- `ix_sankhya_nfe_tenant_id`
- `ix_sankhya_nfe_sankhya_id`
- `ix_sankhya_nfe_chave_acesso`
- `ix_sankhya_lancamentos_financeiros_id`
- `ix_sankhya_lancamentos_financeiros_tenant_id`
- `ix_sankhya_lancamentos_financeiros_sankhya_id`
- `ix_sankhya_tabelas_id`
- `ix_sankhya_tabelas_tenant_id`

### Constraints relevantes

- PKs em todas as tabelas
- unique `sankhya_config.tenant_id`
- FK `sankhya_sync_logs.config_id -> sankhya_config.id`
- índices únicos em identificadores externos esperados

## Estado físico encontrado antes da correção

### Busca em todos os schemas

Foi verificado se `sankhya_config` existia em outro schema.

Resultado:

- `sankhya_config`: não existia em nenhum schema
- `sankhya_*`: nenhuma tabela existia em nenhum schema

### Dados existentes

Como as tabelas `sankhya_*` não existiam fisicamente, não havia dados a preservar dentro desse conjunto.

## Causa provável

O histórico do Alembic avançou por uma cadeia que pressupunha `fase3_sankhya` já aplicada, mas a fundação física da integração Sankhya nunca foi materializada no banco auditado.

Em termos práticos:

- o Alembic considerava a linha histórica Sankhya como parte do passado;
- o banco físico não possuía nenhum dos objetos-base dessa linha;
- `20260704_sankhya_gateway_auth` tentou alterar `sankhya_config`, mas a tabela nunca existiu fisicamente.

## Plano de correção avaliado

### Alternativas consideradas

1. aplicar correção física direta equivalente a `fase3_sankhya`
2. criar migration de convergência nova
3. tornar `20260704_sankhya_gateway_auth` defensiva
4. usar `stamp`

### Alternativa escolhida

Foi escolhida a correção física direta no banco, reproduzindo a fundação de `fase3_sankhya` no schema `farms`.

### Motivo

Essa foi a alternativa mais segura porque:

- não havia tabelas `sankhya_*` parciais para reconciliar;
- não havia dados a preservar nessas tabelas;
- `fase3_sankhya` já deveria estar logicamente aplicada no histórico;
- a correção precisava apenas alinhar o estado físico com o histórico já consolidado;
- não foi necessário mascarar o problema com `stamp`.

## Correção aplicada

### Objetos criados no schema `farms`

Foram criadas, com estrutura compatível com `fase3_sankhya`:

- `sankhya_config`
- `sankhya_sync_logs`
- `sankhya_pessoas`
- `sankhya_produtos`
- `sankhya_nfe`
- `sankhya_lancamentos_financeiros`
- `sankhya_tabelas`

Também foram criados os índices e a FK esperados pela migration-base.

### Comandos executados

- auditoria de existência de `sankhya_*` e `sankhya_config` no PostgreSQL
- criação direta das tabelas e índices ausentes no schema `farms`
- reexecução de:

```bash
cd services/api
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m alembic current
.venv/bin/python -m alembic heads
```

## Risco

### Risco de perda de dados

- inexistente para o conjunto `sankhya_*`, porque as tabelas não existiam

### Risco estrutural

- baixo
- a correção apenas materializou fisicamente objetos que já deveriam existir pelo histórico lógico do banco

## Resultado

### Verificação física

Após a correção, passaram a existir no schema `farms`:

- `sankhya_config`
- `sankhya_lancamentos_financeiros`
- `sankhya_nfe`
- `sankhya_pessoas`
- `sankhya_produtos`
- `sankhya_sync_logs`
- `sankhya_tabelas`

### Validação Alembic

- `alembic heads`: `20260706_integrations_external_record_links_pending_local`
- `alembic upgrade head`: concluído com sucesso
- `alembic current`: `20260706_integrations_external_record_links_pending_local (head)`

## Arquivos alterados

Nenhuma migration do repositório foi alterada.

Foi criado apenas este relatório:

- [docs/implementation/reports/DB-MIGRATION-FIX-02-SANKHYA-CONVERGENCIA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/DB-MIGRATION-FIX-02-SANKHYA-CONVERGENCIA.md)

## Conclusão

A divergência Sankhya foi corrigida com sucesso.

O problema não estava nas migrations novas, nem em `Gateway-first`, nem na sincronização. O banco físico apenas não continha a fundação histórica da Sankhya que o Alembic já pressupunha aplicada.

Com a convergência realizada:

- o histórico lógico e o estado físico voltaram a ficar compatíveis;
- `upgrade head` voltou a avançar normalmente;
- o banco chegou ao head atual sem uso de `stamp head` e sem perda de dados.
