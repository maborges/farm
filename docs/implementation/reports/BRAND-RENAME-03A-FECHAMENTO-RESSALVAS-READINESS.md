# BRAND-RENAME-03A — Fechamento das Ressalvas de Readiness

## 1. Correção de `react-hook-form`

Foi confirmado uso direto em vários componentes de `apps/web/src`. A dependência já estava disponível na versão `7.71.2` no lockfile e era usada pelo Campo e pelos peers de `@hookform/resolvers`. Ela foi declarada diretamente em `apps/web/package.json` como `7.71.2` e registrada no importer `apps/web` do `pnpm-lock.yaml`, sem upgrade global.

`pnpm install --frozen-lockfile` passou com lockfile atualizado e sem resolução adicional.

## 2. Arquivos alterados

Nesta fase foram alterados somente:

- `apps/web/package.json`;
- `pnpm-lock.yaml`;
- este relatório.

As alterações anteriores do BRAND-RENAME-02 permanecem no working tree. Não houve branding adicional nesta fase.

## 3. Typecheck Web

`npm run typecheck` em `apps/web`: passou.

O erro em `propriedades-client.tsx:487` deixou de aparecer após a instalação correta das dependências. A comparação com `HEAD` confirmou que o código dessa linha não foi alterado pelo BRAND-RENAME-02; a falha original era consequência do ambiente/dependência incompleta, não uma regressão de branding.

## 4. Lint Web

`npm run lint` em `apps/web`: passou.

## 5. Build Web

`npm run build` em `apps/web`: passou com exit code 0. O build compilou e gerou as rotas. Os avisos de `Dynamic server usage` relacionados a `cookies` durante prefetch são comportamento/pendência preexistente e não falha de build nem regressão do rebranding.

## 6. API startup/smoke

Uvicorn iniciou com `main:app` em `127.0.0.1:18080`, registrando `Application startup complete` e shutdown limpo. O `curl` executado de outro processo do sandbox não conseguiu acessar a porta devido ao isolamento de rede entre processos; portanto não houve confirmação HTTP local de `/docs` e `/openapi.json`.

O título configurado é `DeepFarms API`, e a alteração não modifica rotas, schemas ou operation IDs. Recomenda-se repetir o smoke HTTP em ambiente equivalente à produção antes do deploy.

## 7. OpenAPI

`services/api/main.py` mantém `title="DeepFarms API"`. Não foram encontrados sinais de alteração contratual. O endpoint `/openapi.json` não pôde ser consultado pelo isolamento do sandbox, apesar do startup completo.

## 8. Testes backend

Executado:

```text
.venv/bin/python -m pytest \
  test_password_recovery.py \
  tests/unit/notifications/test_email_adapter.py \
  tests/unit/notifications/test_notification_dispatcher_email.py \
  tests/test_followup_worker_step133.py \
  tests/unit/agricola/test_field_core04_caderno_exportacao.py \
  tests/unit/agricola/test_caderno_exportacao_operacoes.py -q
```

Resultado: **24 passed, 3 failed**.

As três falhas são em `tests/test_followup_worker_step133.py`, com `TypeError: can't compare offset-naive and offset-aware datetimes`, na linha preexistente `atrasado = sol.proximo_followup_em < now`. O arquivo foi alterado no BRAND-RENAME-02 somente em texto de assunto; não houve mudança nessa lógica. Classificação: **PREEXISTENTE**, sem evidência de regressão BRAND-RENAME.

O teste isolado anterior de recuperação de senha também passou: `1 passed`.

## 9. Diff final

- `git diff --check`: passou.
- `git diff --stat` e `git diff --name-only`: revisados.
- O diff desta fase é restrito à declaração de dependência, lockfile e relatório; os demais arquivos pertencem à implementação BRAND-RENAME-02 já em andamento.
- O Campo não foi alterado nesta fase. A evidência BRAND-RENAME-03 continua válida: typecheck, lint e build Campo passaram; o service worker foi regenerado pelo build normal.

## 10. Guardrails

Nenhuma migration, banco, RDS, DNS, SSL, Nginx, storage, systemd, URL legada, SMTP operacional, namespace, enum ERP, `client_system`, package name `agrosaas-api` ou relatório histórico foi alterado nesta fase. Nenhum `DeepAgro` novo foi introduzido.

## 11. Pendências remanescentes

- confirmar `/docs` e `/openapi.json` via HTTP em ambiente equivalente à produção;
- tratar separadamente as três falhas preexistentes de timezone do follow-up;
- executar os testes direcionados restantes de notificações/PDF/XLSX em pipeline de merge, se exigido pelo release;
- manter a pendência de asset visual oficial DeepFarms em fase própria.

## 12. Veredicto

**BRAND-RENAME-03A — STATUS: GO COM RESSALVAS**

As ressalvas de dependência e typecheck Web foram eliminadas: instalação, typecheck, lint e build Web passaram. O startup da API foi confirmado, sem evidência de exceção causada pelo rebranding. As falhas restantes são preexistentes e independentes, mas o smoke HTTP da API e a confirmação final dos testes adicionais ainda devem ocorrer no ambiente de merge/produção.

Não executar deploy nesta fase.
