# LAUNCH-P2.1 - Selecao Assistida de Animais no Campo PWA

## 1. Auditoria realizada

A auditoria confirmou que o Campo PWA ja possuía a infraestrutura offline necessária:

- `Dexie` / IndexedDB como base local.
- `sync/pull` para popular caches do servidor.
- `lotes` e demais entidades de apoio no cache.
- Telas reprodutivas ja existentes com captura local e sincronizacao posterior.

O gap restante era objetivo: as telas reprodutivas ainda dependiam de digitação manual de identificadores para matriz, reprodutor, pai e cria.

## 2. Componentes reutilizados

- `apps/campo/src/lib/db.ts`
- `apps/campo/src/lib/sync/pull.ts`
- `apps/campo/src/components/campo/ui.tsx`
- `apps/campo/src/app/(campo)/campo/reproducao/*`
- `services/api/campo/service.py`

## 3. Lacunas encontradas

- Ausencia de cache local de `Animal` no IndexedDB do Campo.
- Ausencia de sincronizacao do catalogo de animais no `pull`.
- Ausencia de componente de selecao assistida offline para os formulários reprodutivos.

## 4. Implementacoes realizadas

- Adicionado cache local de `Animal` no IndexedDB, sem criar cache paralelo.
- Complementado o `sync/pull` para trazer animais autorizados do backend e persistir no cache local.
- Complementado o backend de `campo` para incluir a listagem de animais no payload de sincronizacao.
- Criado componente reutilizavel de selecao assistida por busca offline:
  - pesquisa por identificacao
  - pesquisa por brinco
  - pesquisa por nome
  - pesquisa por lote
- Substituidas as entradas manuais nas telas reprodutivas por selecao assistida.

## 5. Arquivos criados

- `apps/campo/src/components/campo/animal-picker.tsx`

## 6. Arquivos alterados

- `apps/campo/src/lib/db.ts`
- `apps/campo/src/lib/sync/pull.ts`
- `services/api/campo/service.py`
- `apps/campo/src/app/(campo)/campo/reproducao/cobertura/page.tsx`
- `apps/campo/src/app/(campo)/campo/reproducao/diagnostico-prenhez/page.tsx`
- `apps/campo/src/app/(campo)/campo/reproducao/parto/page.tsx`
- `apps/campo/src/app/(campo)/campo/reproducao/desmama/page.tsx`

## 7. Testes e validacoes

Executados com sucesso:

- `pnpm typecheck`
- `pnpm lint`
- `ruff check services/api/campo/service.py`
- `git diff --check`

## 8. Resultado tecnico

O operador agora consegue:

- sincronizar o catalogo local de animais;
- buscar animais offline por identificacao, brinco, nome ou lote;
- escolher matriz, reprodutor, pai e cria sem digitar IDs manualmente;
- manter o fluxo reprodutivo com o mesmo contrato de sincronizacao e o mesmo modelo canonico de `Animal`.

## 9. Limitacoes remanescentes

- A selecao assistida depende do cache local atualizado via sincronizacao previa. Sem sync inicial, o operador nao tera a lista de animais em cache.
- Nao foi criado nenhum endpoint novo, nenhum modelo novo e nenhum cache paralelo.

## 10. Conclusao

A limitação operacional apontada na LAUNCH-P2 foi removida: a operação reprodutiva no Campo PWA agora é assistida por busca local offline, preservando a arquitetura offline-first e a integração orientada a eventos.
