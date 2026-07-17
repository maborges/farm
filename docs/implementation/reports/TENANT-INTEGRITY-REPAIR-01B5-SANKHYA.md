# TENANT-INTEGRITY-REPAIR-01B5 — Sankhya provider-specific

**Data:** 2026-07-17  
**Status:** CONCLUÍDO  
**Head aplicado:** `tenant_integrity_repair_01b5_sankhya`

## Escopo fechado

Esta fase alterou exclusivamente a integridade física de `tenant_id` em:

- `sankhya_config`
- `sankhya_sync_logs`
- `sankhya_pessoas`
- `sankhya_produtos`
- `sankhya_nfe`
- `sankhya_lancamentos_financeiros`
- `sankhya_tabelas`

Não houve consolidação, renomeação, remoção de estrutura provider-specific nem
alteração do Console ERP ou dos runtimes de integração.

## Preflight e saneamento

| Tabela | Linhas antes | Órfãos removidos | Linhas preservadas |
|---|---:|---:|---:|
| `sankhya_config` | 2 | 1 | 1 |
| `sankhya_sync_logs` | 9 | 7 | 2 |
| Demais tabelas | 0 | 0 | 0 |

Todos os valores existentes eram convertíveis para UUID. A migration aborta
antes de qualquer remoção caso encontre valor não conversível. O saneamento
remove somente registros cujo `tenant_id` não existe em `farms.tenants(id)`.

## Resultado físico

- 7 colunas convertidas de `varchar(50)` para `uuid`;
- 7 FKs para `farms.tenants(id)` criadas e validadas;
- `ON DELETE NO ACTION` nas 7 FKs;
- índices existentes em `tenant_id` preservados;
- models SQLAlchemy sincronizados com `Uuid(as_uuid=False)` para preservar o
  contrato Python atual baseado em strings;
- `tenant_fk_repair_01d` reposicionada após `01B5`, mantendo head único.

## Validação

- dry-run transacional completo e revertido antes da aplicação;
- `28 passed` nos guardrails `phase_01b5`;
- pós-check: 7/7 colunas UUID, 7/7 FKs validadas, zero FK CASCADE;
- configuração válida e dois logs válidos preservados.

## Observação operacional

O comando Alembic convencional permanece bloqueado por problema preexistente
da fase `01B3`: `integracoes/models.py` reutiliza uma instância de `ForeignKey`
em múltiplas colunas. Para não alterar o núcleo multiprovider fora deste escopo,
`01B5` foi aplicada atomicamente via `Alembic Operations`, com atualização da
versão no mesmo commit de banco.
