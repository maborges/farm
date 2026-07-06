# LAUNCH-W2 - Plantio, Campo, Estoque, Financeiro e Rentabilidade

## 1. Auditoria realizada

Foi auditado o fluxo de plantio no backend agrícola, no PWA Campo e nos pontos de integração documental/rastreável já existentes.

Constatações principais:

- O backend já fechava a cadeia operacional em `services/api/agricola/operacoes/service.py`, com consumo FIFO, atualização de saldo, geração de `Despesa`, `CostAllocation` e caderno oficial.
- O backend já reconhecia `PLANTIO` como evento oficial em `services/api/agricola/caderno/service.py`.
- O PWA Campo já possuía execução offline, sync e caderno oficial em `apps/campo/src/lib/caderno-offline.ts` e `apps/campo/src/app/(campo)/caderno/page.tsx`.
- Havia um desvio de UX/mapeamento no PWA: `PLANTIO_REGISTRO` era convertido para `OBSERVACAO` no fluxo offline, apesar de o backend já tratar plantio como evento oficial.
- O detalhe da tarefa no Campo e o hub do PWA não exibiam `PLANTIO_REGISTRO` com label amigável.

## 2. Integrações reaproveitadas

- `OperacaoService` em `services/api/agricola/operacoes/service.py`
- `CadernoCampoService` e mapeamento oficial de evento em `services/api/agricola/caderno/service.py`
- FIFO e saldo de estoque em `services/api/operacional/services/estoque_fifo.py` e `services/api/operacional/services/estoque_saldo.py`
- `Despesa` e rastreabilidade financeira já existentes em `services/api/financeiro/models/despesa.py`
- PWA offline-first em `apps/campo/src/lib/task-factory.ts`
- Sync de caderno em `apps/campo/src/lib/caderno-offline.ts` e `apps/campo/src/app/(campo)/caderno/page.tsx`

## 3. Lacunas encontradas

- O PWA convertia `PLANTIO_REGISTRO` para `OBSERVACAO` antes do envio ao caderno oficial.
- O detalhe da tarefa no Campo não mostrava `PLANTIO_REGISTRO` como `Plantio`.
- O hub do PWA não mostrava `PLANTIO_REGISTRO` com label amigável.

## 4. Implementações realizadas

- Corrigido o mapeamento de `PLANTIO_REGISTRO` para `PLANTIO` no offline sync do Campo.
- Corrigido o label de `PLANTIO_REGISTRO` no detalhe de tarefa do Campo.
- Corrigido o label de `PLANTIO_REGISTRO` no hub do PWA.
- Adicionado teste de regressão para confirmar que o evento oficial de plantio continua sendo emitido como `PLANTIO`.

## 5. Arquivos alterados

- `apps/campo/src/lib/caderno-offline.ts`
- `apps/campo/src/app/(campo)/campo/tarefa/[id]/page.tsx`
- `apps/campo/src/app/(campo)/home/page.tsx`
- `services/api/tests/unit/agricola/test_field_core02_caderno_contract.py`

## 6. Testes e validações

- `pnpm --dir apps/campo run typecheck`
- `services/api/.venv/bin/pytest services/api/tests/unit/agricola/test_field_core02_caderno_contract.py -k plantio -q -s`
- `git diff --check`

Resultado:

- Typecheck do Campo: aprovado.
- Teste regressivo de plantio: aprovado.
- `git diff --check`: sem erros.

## 7. Limitações remanescentes

- A suíte completa do arquivo `services/api/tests/unit/agricola/test_field_core02_caderno_contract.py` depende de fixtures de banco que não conseguem abrir socket neste sandbox, então a execução integral não foi concluída aqui.
- Não foi criado novo módulo, endpoint ou serviço; o fechamento foi feito apenas por ajuste de integração e apresentação.

