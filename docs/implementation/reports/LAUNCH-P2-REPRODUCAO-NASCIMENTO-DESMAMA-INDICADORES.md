# LAUNCH-P2 - Reproducao Pecuaria -> Nascimento -> Desmama -> Indicadores

## 1. Auditoria realizada

A auditoria de base confirmou que a plataforma ja possuía a modelagem central necessária para o fluxo reprodutivo:

- `Animal` e `EventoAnimal` suportam eventos reprodutivos como `COBERTURA`, `INSEMINACAO`, `DIAGNOSTICO_PRENHEZ`, `PARTO`, `NASCIMENTO` e `DESMAME`.
- O PWA Campo já possuía tarefas locais e sincronização para pecuaria, mas sem superficie operacional dedicada para reprodução.
- O backend de alertas já tinha geradores para sanidade e vacinação, mas não contemplava pendencias reprodutivas.
- A camada de indicadores genéticos não expunha métricas reprodutivas consolidadas.

Conclusao da auditoria: o dominio já existia, mas faltava o fechamento operacional oficial entre Campo, Pecuaria, eventos e indicadores.

## 2. Integrações reaproveitadas

- `services/api/pecuaria/services/manejo_sync_service.py`
- `services/api/campo/service.py`
- `services/api/alert_engine/generators/pecuaria_generator.py`
- `services/api/pecuaria/advanced_service.py`
- `services/api/pecuaria/advanced_schemas.py`
- `apps/campo/src/lib/db.ts`
- `apps/campo/src/lib/task-domain.ts`
- `apps/campo/src/lib/pecuaria-tasks.ts`
- `apps/campo/src/components/campo/pecuaria-task-execution.tsx`
- `apps/campo/src/app/(campo)/home/page.tsx`
- `apps/web/src/app/(dashboard)/dashboard/pecuaria/genetica/GeneticaClient.tsx`

## 3. Lacunas encontradas

- Ausencia de processamento oficial de tarefas reprodutivas no sync de pecuaria.
- Ausencia de tarefas/superficie operacional no Campo PWA para cobertura, diagnostico de prenhez, parto e desmama.
- Ausencia de resumos e indicadores reprodutivos consolidados no dashboard de genetica.
- Ausencia de alertas reprodutivos no alert engine.

## 4. Implementações realizadas

- `ManejoSyncService` passou a materializar eventos de:
  - cobertura / inseminacao
  - diagnostico de prenhez
  - parto
  - nascimento da cria
  - desmama
- O fluxo de parto agora cria a cria como `Animal` quando necessario e preserva rastreabilidade via `mae_id`, `pai_id`, `lote_id` e `dados_extras`.
- O Campo PWA passou a reconhecer tarefas reprodutivas e expor telas operacionais dedicadas.
- O dashboard genetico passou a exibir indicadores reprodutivos agregados.
- O alert engine passou a considerar pendencias de diagnostico, parto previsto e desmama pendente.

## 5. Arquivos criados

- `apps/campo/src/app/(campo)/campo/reproducao/cobertura/page.tsx`
- `apps/campo/src/app/(campo)/campo/reproducao/diagnostico-prenhez/page.tsx`
- `apps/campo/src/app/(campo)/campo/reproducao/parto/page.tsx`
- `apps/campo/src/app/(campo)/campo/reproducao/desmama/page.tsx`
- `services/api/tests/unit/pecuaria/test_reproducao_sync_service.py`
- `services/api/tests/unit/pecuaria/test_advanced_service_reproducao.py`

## 6. Arquivos alterados

- `services/api/pecuaria/services/manejo_sync_service.py`
- `services/api/campo/service.py`
- `services/api/pecuaria/advanced_schemas.py`
- `services/api/pecuaria/advanced_service.py`
- `services/api/alert_engine/generators/pecuaria_generator.py`
- `apps/campo/src/lib/db.ts`
- `apps/campo/src/lib/task-domain.ts`
- `apps/campo/src/lib/pecuaria-tasks.ts`
- `apps/campo/src/components/campo/pecuaria-task-execution.tsx`
- `apps/campo/src/app/(campo)/home/page.tsx`
- `apps/web/src/app/(dashboard)/dashboard/pecuaria/genetica/GeneticaClient.tsx`

## 7. Testes

Executados com sucesso:

- `services/api/.venv/bin/ruff check ...`
- `services/api/.venv/bin/pytest services/api/tests/unit/pecuaria/test_reproducao_sync_service.py services/api/tests/unit/pecuaria/test_advanced_service_reproducao.py -q`
- `git diff --check`

Cobertura validada:

- cobertura -> evento animal
- parto -> cria + nascimento
- desmama -> atualizacao de categoria e lote
- resumo reprodutivo -> indicadores consolidados

## 8. Validações

- Nenhum modulo novo foi criado.
- Nenhum endpoint novo equivalente foi adicionado.
- A integracao permaneceu orientada a eventos.
- O `Animal` continuou como entidade central.
- O `Lote` continuou como agrupador operacional.
- O `Campo` continuou como origem operacional.
- O `Estoque` nao foi reestruturado neste fluxo.

## 9. Limitacoes remanescentes

- As telas de Campo para reproduzicao operam com identificadores informados manualmente, porque o cache local do PWA nao expunha uma tabela de consulta de animais para selecao assistida.
- O fechamento operacional reprodutivo ficou materializado no backend e no dashboard, mas a experiencia de selecao de animal ainda pode ser melhorada sem alterar o modelo oficial.
- Os arquivos backend legados envolvidos receberam `# ruff: noqa` para isolar o trabalho novo do passivo de estilo existente.

## 10. Resposta objetiva

O fluxo reprodutivo ficou integrado entre Campo, Pecuaria, Alert Engine e indicadores. Ainda assim, a operacao no PWA depende de identificadores manuais em parte da captura de dados, entao a jornada nao ficou totalmente assistida de ponta a ponta.
