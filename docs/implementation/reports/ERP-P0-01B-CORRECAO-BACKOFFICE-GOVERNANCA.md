# ERP-P0-01B — Correção Backoffice Governança

## Resumo

Correção exclusiva de aderência entre a interface do Backoffice ERP e a suíte de testes de governança.

Nenhuma alteração foi feita em:

* arquitetura;
* runtime;
* contratos ERP;
* endpoints;
* adapter;
* capability matrix;
* `provider_definition`.

## Arquivos auditados

* `apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx`
* `services/api/tests/unit/integracoes/test_sankhya_governed_integration.py`

## Arquivos alterados

* `apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx`

## Causa da divergência

O teste `test_backoffice_nao_e_console_principal_da_configuracao` exigia a presença literal do texto:

* `Jobs canônicos`

A tela de backoffice mantinha a seção operacional de jobs, mas o título exibido havia sido alterado para:

* `Jobs recentes`

Ou seja, a divergência era apenas de copy estática na interface.

## Solução aplicada

Foi restaurada a nomenclatura esperada no título da seção já existente de jobs do backoffice:

* de `Jobs recentes`
* para `Jobs canônicos`

Nenhum componente novo foi criado.

Nenhum layout foi alterado.

Nenhum fluxo funcional foi alterado.

## Validações executadas

* `services/api/.venv/bin/pytest services/api/tests/unit/integracoes/test_sankhya_governed_integration.py -q`
* `npm run typecheck` em `apps/web`
* `git diff --check`

## Resultado

* suíte de governança do arquivo executado: **verde**
* typecheck frontend: **verde**
* diff check: **verde**

## Conclusão

A divergência estática entre interface e teste foi eliminada.

O P0-01 fica estabilizado sem impacto arquitetural ou operacional.
