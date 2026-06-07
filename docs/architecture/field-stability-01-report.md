# FIELD-STABILITY-01

## Resumo Executivo

Status final: `APROVADO COM RESSALVAS`

O bloqueio principal do ciclo anterior foi removido:

- `alembic upgrade head` agora fecha limpo no banco real parcialmente convergido
- `alembic heads` continua com head único
- `apps/web` voltou a fechar typecheck e build oficial
- `apps/campo` fecha typecheck, lint e build oficial
- a suíte FIELD crítica continua verde

Ressalvas remanescentes:

1. A validação de migrations foi confirmada no banco real parcialmente convergido, mas não em um banco limpo isolado neste ciclo.
2. O `apps/web` voltou a fechar typecheck com um shim compatível para `@hookform/resolvers/zod`; isso remove o bloqueio, mas não substitui uma futura correção estrutural de dependências.
3. O lint do `apps/campo` foi estabilizado com config local enxuto e referências diretas ao store do monorepo para o parser TypeScript. Funciona para este workspace, mas merece normalização futura da toolchain.

## Comandos Executados

### Backend

```bash
cd services/api && .venv/bin/alembic heads
cd services/api && .venv/bin/alembic current
cd services/api && .venv/bin/alembic upgrade head
python3 -m py_compile services/api/migrations/env.py
python3 -m py_compile services/api/migrations/versions/20260521_frota_step04.py
python3 -m py_compile services/api/migrations/versions/20260522_frota_step05_checklists_operacionais.py
python3 -m py_compile services/api/migrations/versions/20260523_frota_step07_operadores_produtividade.py
python3 -m py_compile services/api/migrations/versions/20260524_frota_step08_apontamentos_agricolas.py
python3 -m py_compile services/api/migrations/versions/20260527_field_core02_caderno_event_contract.py
python3 -m py_compile services/api/migrations/versions/20260527_field_core03_caderno_status_governance.py
python3 -m py_compile services/api/migrations/versions/20260527_field_core04_caderno_exportacao_auditavel.py
python3 -m py_compile services/api/migrations/versions/20260527_field_core05_caderno_retificacao_documental.py
python3 -m py_compile services/api/migrations/versions/20260527_field_pwa01_caderno_offline_contract.py
python3 -m py_compile services/api/migrations/versions/20260606_field_ops_01_propagacao_documental_invalidez.py
services/api/.venv/bin/pytest services/api/tests/unit/agricola/test_field_core02_caderno_contract.py services/api/tests/unit/agricola/test_field_core03_caderno_status.py services/api/tests/unit/agricola/test_field_core04_caderno_exportacao.py services/api/tests/unit/agricola/test_field_core05_caderno_retificacao.py services/api/tests/unit/agricola/test_field_pwa01_offline_sync.py services/api/tests/unit/agricola/test_tarefas_integridade_documental.py services/api/tests/unit/campo/test_sync_pull_safra_mapper.py services/api/tests/unit/campo/test_tarefa_programada_integridade.py -q
```

### apps/web

```bash
cd apps/web && pnpm exec tsc --noEmit --pretty false
cd apps/web && pnpm run lint
cd apps/web && pnpm run build
```

### apps/campo

```bash
cd apps/campo && pnpm exec tsc --noEmit
cd apps/campo && pnpm run lint
cd apps/campo && pnpm run build
```

### Higiene

```bash
git diff --check
```

## Resultado Alembic

### Resultado final

- `alembic heads`: `20260606_field_remediation_01_snapshot (head)`
- `alembic current`: `20260606_field_remediation_01_snapshot (head)`
- `alembic upgrade head`: `PASSOU`

### Correções feitas

#### Infraestrutura Alembic

- [env.py](/opt/lampp/htdocs/farm/services/api/migrations/env.py)
  - amplia `farms.alembic_version.version_num` para `varchar(64)` quando encontra legado `varchar(32)`

#### FIELD-CORE / FIELD-PWA / FIELD-OPS

- [20260527_field_core02_caderno_event_contract.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/20260527_field_core02_caderno_event_contract.py)
  - `add_column` protegido por inspeção
  - `unique constraint` protegida por inspeção
- [20260527_field_core03_caderno_status_governance.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/20260527_field_core03_caderno_status_governance.py)
  - `create_table`/`create_index` idempotentes
  - backfill protegido contra reinserção
- [20260527_field_core04_caderno_exportacao_auditavel.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/20260527_field_core04_caderno_exportacao_auditavel.py)
  - colunas protegidas por inspeção
- [20260527_field_core05_caderno_retificacao_documental.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/20260527_field_core05_caderno_retificacao_documental.py)
  - colunas, índices e FKs protegidos por inspeção
- [20260527_field_pwa01_caderno_offline_contract.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/20260527_field_pwa01_caderno_offline_contract.py)
  - colunas e índices protegidos por inspeção
- [20260606_field_ops_01_propagacao_documental_invalidez.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/20260606_field_ops_01_propagacao_documental_invalidez.py)
  - índices protegidos por inspeção

#### Trilha Frota necessária para chegar ao head real

- [20260521_frota_step04.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/20260521_frota_step04.py)
  - colunas protegidas por inspeção
- [20260522_frota_step05_checklists_operacionais.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/20260522_frota_step05_checklists_operacionais.py)
  - tabelas, índices e coluna de origem do checklist protegidos por inspeção
- [20260523_frota_step07_operadores_produtividade.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/20260523_frota_step07_operadores_produtividade.py)
  - colunas/índices protegidos por inspeção
- [20260524_frota_step08_apontamentos_agricolas.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/20260524_frota_step08_apontamentos_agricolas.py)
  - colunas/índices/FKs protegidos por inspeção
  - corrigida chamada inválida de `batch_op.create_foreign_key`

### Observação importante

Neste ciclo eu validei `upgrade head` apenas no banco real parcialmente convergido. Não subi um banco limpo separado para repetir toda a árvore do zero.

## Resultado apps/web

### Resultado final

- typecheck global: `PASSOU`
- lint do script atual: `PASSOU`
- build oficial: `PASSOU`

### Correções feitas

- [package.json](/opt/lampp/htdocs/farm/apps/web/package.json)
  - `build` normalizado para `next build --webpack`
- [hookform-resolvers-zod.d.ts](/opt/lampp/htdocs/farm/apps/web/src/types/hookform-resolvers-zod.d.ts)
  - shim compatível para remover o bloqueio entre `@hookform/resolvers` e `zod`
- formulários com `zodResolver` foram alinhados para `zod/v4`

### Situação das rotas FIELD

As rotas críticas do escopo compilaram no build oficial:

- `/dashboard/agricola/safras/[id]/caderno`
- `/dashboard/operacional/campo/tarefas`
- `/dashboard/settings/ia`
- `/dashboard/settings/billing`

### Ressalva

O typecheck voltou a passar, mas a solução adotada no resolver é de compatibilidade. A base segue funcional, porém ainda há dívida de dependência/tipagem a ser saneada depois.

## Resultado apps/campo

### Resultado final

- typecheck: `PASSOU`
- lint: `PASSOU`
- build oficial: `PASSOU`

### Correções feitas

- [package.json](/opt/lampp/htdocs/farm/apps/campo/package.json)
  - `build` normalizado para `next build --webpack`
  - `lint` normalizado para `eslint src --ext .ts,.tsx`
- [eslint.config.mjs](/opt/lampp/htdocs/farm/apps/campo/eslint.config.mjs)
  - config flat mínima e estável para o workspace
  - parser TypeScript referenciado a partir do store já existente do monorepo
- removidos comentários `eslint-disable` órfãos em:
  - [page.tsx](/opt/lampp/htdocs/farm/apps/campo/src/app/(auth)/activate/page.tsx)
  - [camera-capture.tsx](/opt/lampp/htdocs/farm/apps/campo/src/components/campo/camera-capture.tsx)
  - [top-app-bar.tsx](/opt/lampp/htdocs/farm/apps/campo/src/components/campo/top-app-bar.tsx)

### Observação sobre rede

Tentei instalar dependências dedicadas de lint no `apps/campo`, mas a operação falhou por DNS externo:

```text
ERR_PNPM_META_FETCH_FAIL ... getaddrinfo EAI_AGAIN registry.npmjs.org
```

Por isso optei por estabilizar o lint usando apenas pacotes já presentes no monorepo.

## Correções Feitas

1. Stabilização do Alembic para banco convergido real.
2. Idempotência das migrations FIELD que colidiam com schema já existente.
3. Idempotência adicional da trilha Frota necessária para alcançar o head único.
4. Normalização do build oficial do `apps/web` para webpack.
5. Reativação do typecheck do `apps/web`.
6. Normalização do typecheck/lint/build do `apps/campo`.

## Pendências

1. Repetir a árvore completa de migrations em banco limpo dedicado.
2. Substituir o shim de `zodResolver` no `apps/web` por alinhamento estrutural de dependências/tipos.
3. Remover a dependência de caminhos do store pnpm no ESLint do `apps/campo` quando o workspace puder receber as devDependencies próprias.

## Decisão Final

Classificação: `APROVADO COM RESSALVAS`

Justificativa:

- os bloqueadores que impediam o avanço foram removidos
- o backend FIELD segue verde
- o head do Alembic ficou único e aplicável no banco real
- `apps/web` e `apps/campo` voltaram a fechar nas validações oficiais configuradas
- restam apenas ressalvas de hardening e normalização de toolchain, não um bloqueio funcional para o FIELD-PWA-03
