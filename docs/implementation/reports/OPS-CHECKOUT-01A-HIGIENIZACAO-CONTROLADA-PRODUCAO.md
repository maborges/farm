# OPS-CHECKOUT-01A — Higienização Controlada e Fast-Forward de Produção

## 1. SHA inicial

- Checkout inicial: `27f4410349b663187e0805743d8566ecc985c4d3`.
- Branch: `main`.
- Checkout: `/opt/deepfarms/farm`.

## 2. `origin/main` efetivo

Após `git fetch origin`, o alvo efetivo era `9e32e94bafefea08f9b6abec86b7910d2ad93d56`, que havia avançado desde a auditoria anterior.

## 3. Arquivos operacionais preservados

Foram confirmados antes do fast-forward e permaneceram presentes depois:

- `apps/web/.env.production`;
- `apps/campo/.env.production`;
- `services/api/.env.production`;
- `services/api/.env.production.bak-storage-20260911`;
- `services/api/events/outbox_worker.py.bak-20260910`;
- `services/api/events/outbox_worker.py.bak-before-fix`;
- `services/api/integracoes/openweather/worker.py.bak-before-final-fix`;
- `services/api/integracoes/openweather/worker.py.bak-before-greenlet-fix`.

Nenhum conteúdo sensível foi exibido ou versionado.

## 4. Verificação de colisões

Cada um dos oito caminhos untracked foi consultado com `git ls-tree -r --name-only origin/main -- <caminho>`. Resultado: **nenhuma colisão** com arquivo versionado em `origin/main`.

## 5. Restauração de `next-env.d.ts`

Foi restaurado somente `apps/web/next-env.d.ts` com `git restore --source=HEAD -- apps/web/next-env.d.ts`. A alteração era a diferença gerada pelo Next entre `./.next/types/routes.d.ts` e `./.next/dev/types/routes.d.ts`. Após a restauração, não restaram tracked modificados.

Nenhum `.env.production`, backup ou outro arquivo foi restaurado, removido ou movido.

## 6. Fast-forward

Com os arquivos operacionais preservados e sem colisões, foi executado:

```text
git pull --ff-only origin main
```

Resultado: fast-forward de `27f44103` para `9e32e94b` concluído com sucesso.

## 7. SHA final

- `HEAD`: `9e32e94bafefea08f9b6abec86b7910d2ad93d56`.
- `origin/main`: `9e32e94bafefea08f9b6abec86b7910d2ad93d56`.
- `HEAD == origin/main`: **sim**.

## 8. Working tree final

Não há tracked modificados nem conflito. O `git status --short` final contém somente os oito untracked operacionais conhecidos e classificados como configuração/backups. O objetivo de zero tracked modificados foi atingido sem exigir working tree absolutamente vazia.

## 9. Ausência de deploy nesta fase

Não foram executados `pnpm install`, build Web, build Campo, restart de serviços, migration, Alembic, smoke pós-deploy, alteração Nginx ou alteração systemd. Nenhum arquivo foi apagado e nenhum segredo foi exposto.

## 10. Veredicto

**OPS-CHECKOUT-01A — STATUS: GO**

O checkout está alinhado a `origin/main`, sem tracked modificados ou colisões, e todos os `.env.production` e backups foram preservados. Está pronto para a retomada do BRAND-RENAME-04 a partir da instalação reproduzível de dependências e dos builds, em etapa separada.
