# BRAND-RENAME-03 — Validação Técnica e Readiness de Deploy

## 1. Resumo executivo

A validação técnica da implementação BRAND-RENAME-02 foi concluída sem alterações de código nesta fase. O build Web e o build Campo terminaram com sucesso. O Campo regenerou `public/sw.js` automaticamente pelo processo PWA. O typecheck Campo, lint Campo, lint Web e o teste de recuperação de senha passaram.

O typecheck Web continua bloqueado por dependência ausente no workspace e por um erro de tipagem independente do rebranding. O smoke de importação da API não completou dentro do limite do ambiente, portanto a inicialização deve ser confirmada em ambiente operacional antes do deploy.

## 2. Revisão do diff

`git diff --stat`, `git diff --name-only` e `git diff --check` foram executados. O diff contém somente alterações textuais da fase 02 e o `sw.js` regenerado pelo build do Campo. Não há migrations novas ou alteradas. Não foram alterados paths, schemas, operation IDs, namespaces técnicos, URLs legadas, SMTP operacional, DNS, SSL, Nginx, RDS ou storage.

Os arquivos `next-env.d.ts` modificados automaticamente pelos builds foram restaurados ao conteúdo anterior; não fazem parte da entrega.

## 3. Investigação de `react-hook-form`

`react-hook-form` é importado por vários componentes Web, mas não está declarado em `apps/web/package.json`. A versão `7.71.2` existe no `pnpm-lock.yaml` como peer/transitive dependency de outros pacotes, não como dependência direta do importer Web. A instalação local está, portanto, inconsistente com o uso efetivo do código; trata-se de problema de configuração/dependência do repositório, não causado pelo rebranding. Nenhuma dependência foi adicionada nesta fase.

## 4. Investigação de `propriedades-client.tsx`

O erro reportado é `Property 'message' does not exist on type 'unknown'`, em `propriedades-client.tsx:487`, na leitura de `firstError?.message`. A comparação com `HEAD` mostra o mesmo código e a mesma linha no estado anterior à fase 02; o diff BRAND-RENAME-02 não toca esse arquivo. É uma falha preexistente e independente do rebranding. Não foi corrigida.

## 5. Web typecheck/lint/build

- `npm run typecheck`: falhou por múltiplas importações não resolvidas de `react-hook-form` e pelo erro preexistente em `propriedades-client.tsx`.
- `npm run lint`: passou.
- `npm run build`: passou com exit code 0. O Next informou `Skipping validation of types`; os erros de typecheck não foram mascarados como resolvidos.

## 6. Campo typecheck/lint/build

- `npm run typecheck`: passou.
- `npm run lint`: passou.
- `npm run build`: passou.
- O build registrou a regeneração automática de `apps/campo/public/sw.js` pelo `next-pwa`.
- O manifest mantém `name: "DeepFarms Campo"` e o ícone legado `AgroSaaS-icone.webp`, deliberadamente preservado por ausência de asset DeepFarms aprovado.

## 7. Testes backend executados

- `.venv/bin/python -m pytest test_password_recovery.py -q`: 1 passed.
- O teste confirma o fluxo de recuperação de senha sem alteração da política SMTP global.
- Não foram executados testes completos de notificações/PDF/XLSX/follow-up por ausência de uma execução segura e rápida da suíte específica; devem ser executados no pipeline de validação do merge.

## 8. OpenAPI/API smoke

O título configurado em `services/api/main.py` é `DeepFarms API`. A alteração não toca rotas, schemas ou operation IDs. O comando de importação `from main import app` não completou no limite de 8 segundos no ambiente local, sem produzir erro funcional; o smoke de startup permanece pendência de ambiente.

## 9. Busca anti-regressão

A busca pelas variantes de AgroSaaS e por `DeepAgro` foi executada. As ocorrências restantes correspondem a MANTER/REVISAR, incluindo contratos, chaves técnicas, URLs legadas, SMTP, assets antigos, paths históricos e relatórios históricos. Nenhuma nova ocorrência de `DeepAgro` foi criada.

## 10. Situação dos assets

O branding textual está em DeepFarms. Não foi encontrado asset oficial DeepFarms aprovado para substituir os assets visuais antigos. Nenhum logo/ícone foi inventado; os consumidores continuam apontando para assets legados de forma deliberada. A necessidade de asset oficial é pendência separada de branding visual.

## 11. Arquivos protegidos

Não foram alterados migrations, schemas de banco, `apps/web/src/proxy.ts`, URLs legadas persistidas, identificadores técnicos, parâmetros operacionais SMTP, `/tmp/agrosaas_uploads`, `/opt/deepfarms/storage` ou arquivos históricos. `apps/campo/public/sw.js` foi somente regenerado pelo build, nunca editado manualmente.

## 12. Banco e migrations

Nenhuma migration foi criada ou alterada. Não houve acesso ou alteração no RDS, tabelas, dados persistidos, RLS, policies ou contratos de banco.

## 13. Impacto de deploy

- Web: rebuild e restart/reload do serviço.
- Campo: rebuild e restart/reload; o service worker deve ser gerado pelo build.
- API: restart para carregar OpenAPI e textos de e-mail/PDF.
- Worker: restart se carregar os módulos de follow-up/notificação alterados.
- Outbox: restart se carregar o adapter alterado.
- DNS, SSL, Nginx, storage e systemd: sem alteração.

Nenhum deploy foi executado.

## 14. Pendências

- corrigir a instalação/configuração de `react-hook-form` no workspace em tarefa própria;
- executar typecheck Web após a dependência estar disponível;
- confirmar smoke de startup da API em ambiente equivalente à produção;
- executar testes direcionados restantes e validação visual;
- obter asset DeepFarms oficial em fase separada.

## 15. Veredicto

**BRAND-RENAME-03 — STATUS: GO COM RESSALVAS**

Não há evidência de regressão causada pelo rebranding: Web build, Campo build, Campo typecheck/lint, Web lint e recuperação de senha passaram. Contudo, não é `GO` irrestrito para produção porque o typecheck Web depende de uma instalação inconsistente, o smoke da API não foi concluído e ainda faltam testes direcionados adicionais. Não executar deploy até essas ressalvas serem tratadas ou formalmente aceitas.
