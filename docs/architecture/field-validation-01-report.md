# FIELD-VALIDATION-01

## Resumo Executivo

Status final: `BLOQUEADO`

A fundação FIELD continua funcional no backend e no PWA/Campo em runtime validado por build e suíte direcionada. Os cenários centrais de contrato canônico, governança de status, exportação, retificação, invalidação e sync offline passaram na suíte FIELD.

Os dois bloqueadores remanescentes são estruturais:

1. `alembic upgrade head` ainda não aplica limpo em banco parcialmente convergido. A validação revelou um legado real de schema fora da trilha Alembic. O primeiro erro de `alembic_version varchar(32)` foi corrigido na infraestrutura, mas novas colisões seguem aparecendo em migrations FIELD-CORE antigas quando o banco já contém objetos equivalentes.
2. `apps/web` não fecha typecheck. Há uma incompatibilidade ampla entre `zod` e `@hookform/resolvers` afetando dezenas de formulários, inclusive telas fora e dentro do escopo FIELD. O build fecha apenas porque `ignoreBuildErrors` está ativo.

Com isso, a base não está pronta para liberar `FIELD-PWA-03`.

## Comandos Executados

### Backend

```bash
cd services/api && .venv/bin/alembic heads
cd services/api && .venv/bin/alembic current
cd services/api && .venv/bin/alembic upgrade head
python3 -m py_compile services/api/agricola/caderno/models.py services/api/agricola/caderno/router.py services/api/agricola/caderno/schemas.py services/api/agricola/caderno/service.py services/api/campo/schemas.py services/api/campo/service.py services/api/ia/growth_service.py
python3 -m py_compile services/api/migrations/env.py
python3 -m py_compile services/api/migrations/versions/20260527_field_core02_caderno_event_contract.py
python3 -m py_compile services/api/migrations/versions/20260527_field_core03_caderno_status_governance.py
services/api/.venv/bin/pytest services/api/tests/unit/agricola/test_field_core02_caderno_contract.py services/api/tests/unit/agricola/test_field_core03_caderno_status.py services/api/tests/unit/agricola/test_field_core04_caderno_exportacao.py services/api/tests/unit/agricola/test_field_core05_caderno_retificacao.py services/api/tests/unit/agricola/test_field_pwa01_offline_sync.py services/api/tests/unit/agricola/test_tarefas_integridade_documental.py services/api/tests/unit/campo/test_sync_pull_safra_mapper.py services/api/tests/unit/campo/test_tarefa_programada_integridade.py -q
services/api/.venv/bin/pytest services/api/tests/unit/campo/test_sync_pull_safra_mapper.py services/api/tests/unit/agricola/test_field_pwa01_offline_sync.py services/api/tests/unit/agricola/test_field_core04_caderno_exportacao.py services/api/tests/unit/agricola/test_field_core05_caderno_retificacao.py services/api/tests/unit/agricola/test_tarefas_integridade_documental.py services/api/tests/unit/campo/test_tarefa_programada_integridade.py -q
```

### Frontend Web

```bash
cd apps/web && pnpm exec tsc --noEmit
cd apps/web && pnpm run lint
cd apps/web && pnpm run build
cd apps/web && pnpm exec next build --webpack
```

### Frontend Campo

```bash
cd apps/campo && pnpm run typecheck
cd apps/campo && pnpm run lint
cd apps/campo && pnpm exec eslint src --ext .ts,.tsx
cd apps/campo && pnpm run build
cd apps/campo && pnpm exec next build --webpack
```

### Higiene

```bash
git diff --check
```

## Backend

### Resultado

- `alembic heads`: `20260606_field_remediation_01_snapshot (head)`
- `alembic current`: ainda mostra base parcialmente fora da trilha FIELD (`step45_tarefas_invalidacao` e `20260520_frota_step02`)
- `py_compile`: passou nos módulos críticos e nos arquivos de migration ajustados
- suíte FIELD direcionada: `46 passed in 56.78s`
- suíte FIELD complementar: `36 passed in 42.41s`

### O que funcionou

- Contrato canônico do caderno
- Governança de status
- Exportação oficial e auditoria
- Retificação documental
- Invalidação com propagação documental
- Sync offline do PWA
- Reconciliação inbound do caderno
- Isolamento por tenant nos testes exercitados

### Bloqueios encontrados

#### 1. `alembic_version` legado com comprimento insuficiente

O `upgrade head` falhou inicialmente ao tentar inserir revision IDs maiores que 32 caracteres.

Erro observado:

```text
value too long for type character varying(32)
INSERT INTO alembic_version (version_num) VALUES ('20260606_campo_tarefas_invalidacao')
```

Correção mínima aplicada:

- `services/api/migrations/env.py` agora amplia `farms.alembic_version.version_num` para `varchar(64)` antes de rodar migrations PostgreSQL legadas.

#### 2. Migrations FIELD-CORE antigas não são seguras em banco parcialmente convergido

Após a correção acima, novas falhas apareceram porque a base real já contém parte do schema FIELD:

Erros observados:

```text
DuplicateColumnError: column "tipo_evento" of relation "caderno_campo_entradas" already exists
DuplicateTableError: relation "caderno_evento_status_historico" already exists
DuplicateColumnError: column "modo_exportacao" of relation "caderno_exportacoes" already exists
```

Correções mínimas aplicadas:

- `20260527_field_core02_caderno_event_contract.py`
  - `add_column` protegido por inspeção de colunas existentes
  - criação da `uq_caderno_campo_origem_evento` protegida por inspeção de constraints
- `20260527_field_core03_caderno_status_governance.py`
  - `create_table` e `create_index` protegidos por inspeção
  - backfill protegido contra reinserção duplicada por `caderno_entrada_id`

Conclusão:

- ainda existem outras migrations FIELD-CORE com a mesma fragilidade de idempotência em banco convergido
- o problema deixou de ser “head múltiplo” e passou a ser “migração não reaplicável/reatribuível com segurança”

## apps/web

### Resultado

- `pnpm exec tsc --noEmit`: falhou
- `pnpm run lint`: passou no script atual
- `pnpm run build`: falhou com Turbopack root inference
- `pnpm exec next build --webpack`: passou

### Achados

#### 1. Typecheck bloqueado por incompatibilidade ampla `zod` x `@hookform/resolvers`

O problema é transversal e não restrito ao FIELD. Foram encontrados erros em dezenas de formulários.

Indicador coletado:

- ocorrências de `useForm`/`zodResolver` no web: `56`

Padrão de erro:

```text
No overload matches this call
Argument of type 'ZodObject<...>' is not assignable ...
The types of '_zod.version.minor' are incompatible
Type '3' is not assignable to type '0'
```

Impacto:

- o build de produção só passa porque `apps/web/next.config.ts` está com `typescript.ignoreBuildErrors = true`
- isso impede classificar o web como validado

#### 2. Build padrão com Turbopack não está confiável

O comando padrão `pnpm run build` falhou com:

```text
Next.js inferred your workspace root, but it may not be correct.
We couldn't find the Next.js package (next/package.json) from the project directory: /opt/lampp/htdocs/farm/apps/web/src/app
```

O fallback com `next build --webpack` funcionou e gerou as rotas críticas do escopo:

- `/dashboard/agricola/safras/[id]/caderno`
- `/dashboard/operacional/campo/tarefas`
- `/dashboard/settings/ia`
- `/dashboard/settings/billing`

Conclusão:

- as rotas críticas são compiláveis em runtime
- a disciplina de build oficial do app ainda não está estável

## apps/campo

### Resultado

- `pnpm run typecheck`: passou
- `pnpm run lint`: falhou
- `pnpm exec eslint src --ext .ts,.tsx`: falhou por ausência de `eslint.config.*`
- `pnpm run build`: falhou no sandbox com erro interno do Turbopack
- `pnpm exec next build --webpack`: passou

### Achados

#### 1. O app está compilável e as rotas principais do Campo foram geradas

Rotas geradas no build webpack:

- `/`
- `/home`
- `/campo/tarefa/[id]`
- `/caderno`
- `/sync`
- `/campo/aplicacao`
- `/campo/colheita`
- `/campo/pesagem`
- `/campo/vacinacao`

Isso cobre home, tarefas por detalhe operacional, caderno e sync.

#### 2. O script de lint está quebrado para a stack atual

Erro observado:

```text
Invalid project directory provided, no such directory: /opt/lampp/htdocs/farm/apps/campo/lint
```

Isso indica que `next lint` não está compatível com a versão atual do Next ou com a forma de invocação do workspace.

#### 3. O projeto também não tem configuração flat de ESLint

Erro observado com `eslint` direto:

```text
ESLint couldn't find an eslint.config.(js|mjs|cjs) file
```

Conclusão:

- o app Campo está operacionalmente compilável
- a camada de lint não está preparada para a stack atual

## Cenários Integrados

### Cenário A

`Criar tarefa -> executar -> operação -> evento canônico -> aprovar -> consolidar -> exportar oficial -> assinar`

Status: `VALIDADO POR TESTE`

Cobertura principal:

- `test_field_core04_caderno_exportacao.py`
- `test_field_core05_caderno_retificacao.py`
- `test_tarefas_integridade_documental.py`

### Cenário B

`Evento offline no PWA -> sync -> PENDENTE_APROVACAO -> aprovar no web -> pull no PWA -> refletir status oficial`

Status: `VALIDADO POR TESTE`

Cobertura principal:

- `test_field_pwa01_offline_sync.py`
- `test_sync_pull_safra_mapper.py`
- `test_field_core03_caderno_status.py`

### Cenário C

`Invalidar tarefa concluída -> propagar para caderno -> timeline web -> pull no PWA -> exportação auditoria`

Status: `VALIDADO PARCIALMENTE`

Cobertura:

- backend e reconciliação: validados por teste
- web/campo em runtime: build webpack confirma presença das rotas e dos componentes compiláveis
- bloqueio residual: disciplina oficial de typecheck/build do web ainda não fecha

### Cenário D

`Retificar evento -> nova versão vigente -> exportação oficial usa vigente -> auditoria mostra cadeia`

Status: `VALIDADO POR TESTE`

Cobertura principal:

- `test_field_core05_caderno_retificacao.py`

## Bloqueadores

1. `alembic upgrade head` ainda não aplica limpo em banco parcialmente convergido.
2. `apps/web` falha no typecheck em larga escala por incompatibilidade entre schema/resolver.

## Alertas

1. `apps/web` depende de `ignoreBuildErrors = true` para build de produção.
2. `apps/web` falha no build padrão via Turbopack e só fecha com `--webpack`.
3. `apps/campo` compila, mas a camada de lint está quebrada na stack atual.
4. O problema de migration não é mais branching; agora é idempotência de migrations em bases já convergidas manualmente.

## Melhorias

1. Unificar a stack `zod`/`@hookform/resolvers` do `apps/web` antes de qualquer novo ciclo do PWA.
2. Normalizar a estratégia oficial de build dos frontends: Turbopack ou webpack, mas sem fallback implícito.
3. Tornar todo o bloco FIELD-CORE idempotente em migrations históricas críticas para suportar bancos parcialmente convergidos.
4. Atualizar a infraestrutura de lint do `apps/campo` para a convenção atual do Next/ESLint.

## Decisão Final

Classificação: `BLOQUEADO`

Justificativa objetiva:

- o runtime e os testes do núcleo FIELD estão bons
- o PWA/Campo compila e a reconciliação inbound segue íntegra
- porém a trilha de migrations ainda não aplica limpo em base real parcialmente convergida
- e o `apps/web` não atende o critério mínimo de typecheck sem bypass

`FIELD-PWA-03` não deve ser iniciado antes de:

1. estabilizar `alembic upgrade head` em banco convergido
2. remover o bloqueio amplo de typecheck no `apps/web`
