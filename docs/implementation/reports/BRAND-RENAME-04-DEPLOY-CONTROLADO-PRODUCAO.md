# BRAND-RENAME-04 — Deploy Controlado DeepFarms em Produção

## 1. Resultado

O deploy em produção **não foi executado**. O gate pré-deploy HTTPS passou, mas o acesso SSH ao servidor expirou antes da confirmação dos serviços e da atualização do checkout.

## 2. SHAs

- SHA anterior local/referência de rollback: `27f4410349b663187e0805743d8566ecc985c4d3`.
- SHA candidato enviado ao GitHub: `7426d5446168438d4158cc076db201818fb9b965`.
- Branch: `main`.
- Push: passou para `origin/main`.
- SHA efetivamente implantado: **nenhum**.

## 3. Pre-deploy smoke

Executado antes do push/deploy:

- `https://api.deepfarms.com.br/docs`: HTTP 200.
- `https://api.deepfarms.com.br/openapi.json`: HTTP 200, JSON válido.
- `https://deepfarms.com.br/`: HTTP 200.
- `https://app.deepfarms.com.br/`: HTTP 200.
- `https://campo.deepfarms.com.br/`: HTTP 200.
- título OpenAPI atual: `AgroSaaS API`.

O resultado confirma que a versão atualmente publicada estava operacional e ainda não continha o novo título da API.

## 4. Preparação do código

O diff foi validado com `git diff --check`, o commit candidato foi criado e enviado ao GitHub. Não foi executada migration nem alteração de banco.

## 5. Web build

Não executado na produção, pois o acesso SSH falhou antes da atualização. Os builds locais da fase anterior passaram.

## 6. Campo build

Não executado na produção, pois o acesso SSH falhou antes da atualização. O build local anterior passou e regenerou o service worker pelo processo normal.

## 7. Serviços reiniciados e estado

Nenhum serviço foi reiniciado. Não foi possível consultar `agrosaas-api`, `agrosaas-web`, `agrosaas-campo` ou `agrosaas-worker` no servidor.

Tentativa realizada:

```text
ssh -o BatchMode=yes -o ConnectTimeout=10 agrosaas@179.127.30.25 ...
ssh: connect to host 179.127.30.25 port 22: Connection timed out
```

O runbook disponível documenta esses nomes históricos de systemd; eles não foram alterados.

## 8. API pós-deploy

Não aplicável: não houve deploy. O smoke HTTPS pós-deploy com título `DeepFarms API` deve ser executado após o acesso ao servidor e a atualização dos serviços.

## 9. Web e Campo pós-deploy

Não aplicável: os domínios responderam no smoke pré-deploy, mas nenhuma nova versão foi publicada.

## 10. E-mail e documentos

Não executados em produção. A configuração SMTP não foi alterada. Os testes locais anteriores confirmaram o fluxo de recuperação de senha e os builds locais concluídos.

## 11. Banco e infraestrutura

Não foram executados Alembic, migrations, alterações de RDS, schema, dados, DNS, SSL, Nginx, storage ou systemd. Nenhuma correção improvisada foi feita diretamente em produção.

## 12. Rollback

Não necessário, pois nenhuma mudança foi aplicada. O SHA de rollback permanece `27f4410349b663187e0805743d8566ecc985c4d3`.

## 13. Pendências

- liberar/corrigir acesso SSH ao servidor de produção;
- confirmar SHA e working tree atuais no servidor;
- confirmar estado dos serviços;
- executar build/restart conforme o procedimento produtivo;
- executar smoke HTTPS pós-deploy, incluindo título `DeepFarms API`;
- validar e-mail e documento novo em produção, se houver fluxo seguro.

As três falhas preexistentes de timezone do follow-up worker continuam classificadas como débito técnico separado.

## 14. Veredicto

**BRAND-RENAME-04 — STATUS: NO-GO**

O código foi commitado e enviado ao GitHub, e a produção atual estava saudável no smoke pré-deploy. Porém, o deploy não pode ser considerado concluído porque o servidor não foi acessível por SSH e nenhum componente foi atualizado. Não executar novas tentativas até restabelecer o acesso e repetir os gates de produção.

## 15. Retomada do deploy — 2026-09-11

### Causa corrigida do SSH e host correto

O bloqueio anterior foi causado pelo endpoint/usuário incorreto. A conexão correta foi confirmada com `ubuntu@ec2-56-126-104-183.sa-east-1.compute.amazonaws.com` usando `~/.ssh/deepfarms-pilot-key.pem`. O servidor respondeu como `ip-172-31-18-82`; o checkout monorepo é `/opt/deepfarms/farm`.

### Estado inicial, SHAs e serviços

- SHA atualmente implantado: `27f4410349b663187e0805743d8566ecc985c4d3`.
- `origin/main` após `git fetch`: `991fe1f0e966593fed2bd04ee6c04c94a8815e49`.
- Branch: `main`.
- Working tree: **não limpa**.
- Serviços `deepfarms-api`, `deepfarms-web`, `deepfarms-campo`, `deepfarms-worker`, `deepfarms-outbox` e `nginx`: `active`.

Foram encontrados `apps/web/next-env.d.ts`, `.env.production` dos componentes e backups operacionais no checkout remoto. Conforme a regra de segurança, nenhum arquivo foi sobrescrito.

### Pre-deploy smoke da retomada

`deepfarms.com.br`, `app.deepfarms.com.br`, `campo.deepfarms.com.br` e `/docs` da API retornaram HTTP 200. `/openapi.json` respondeu JSON com o título atual `AgroSaaS API`, confirmando a versão anterior operacional.

### Instalação, builds, restarts e pós-deploy

Não foram executados instalação de dependências, builds, restarts, smoke pós-deploy, teste de e-mail ou geração de documentos em produção. Não houve rollback.

### Banco e infraestrutura

Não foram executados Alembic/migrations nem alterações de RDS, schema, dados, DNS, SSL, Nginx, storage ou units systemd.

### Veredicto da retomada

**BRAND-RENAME-04 — STATUS: NO-GO**

A conexão SSH foi corrigida e o pre-deploy smoke passou, mas o working tree remoto contém alterações locais e arquivos operacionais não esperados. Para preservar esses dados e evitar sobrescrita destrutiva, o deploy foi interrompido antes da atualização, builds e restarts. É necessária revisão formal do checkout remoto antes de nova tentativa.

## 16. Retomada final e deploy — 2026-09-11

### Referência OPS-CHECKOUT-01A

O checkout foi previamente higienizado de forma controlada conforme `OPS-CHECKOUT-01A`. Arquivos `.env.production` e backups operacionais permaneceram preservados, sem reset ou clean.

### SHA final implantado

- SHA antes dos builds/deploy: `9e32e94bafefea08f9b6abec86b7910d2ad93d56`.
- SHA final confirmado no checkout após o deploy: `9e32e94bafefea08f9b6abec86b7910d2ad93d56`.
- `HEAD == origin/main`: confirmado antes da execução.

### Dependências

`pnpm install --frozen-lockfile` passou no monorepo, sem atualização ou upgrade de versões.

### Builds

- Web: `pnpm --filter web build`, com `NODE_OPTIONS=--max-old-space-size=1536`; passou com exit code 0.
- Campo: `pnpm --filter @agro/campo build`; passou com exit code 0.
- Campo confirmou manifest e regeneração automática do service worker pelo `next-pwa`; não houve edição manual de `sw.js`.

### Serviços reiniciados

Foram reiniciados somente os processos afetados:

- `deepfarms-api`;
- `deepfarms-web`;
- `deepfarms-campo`;
- `deepfarms-worker`;
- `deepfarms-outbox`.

`nginx` não foi reiniciado. Após os restarts, todos os seis serviços (`deepfarms-api`, `deepfarms-web`, `deepfarms-campo`, `deepfarms-worker`, `deepfarms-outbox` e `nginx`) ficaram `active`. O log da API registrou startup completo sem crash loop.

### Smoke pós-deploy

- API `/docs`: HTTP 200.
- API `/openapi.json`: HTTP 200.
- OpenAPI pós-deploy: `"title":"DeepFarms API"`.
- `https://deepfarms.com.br`: HTTP 200; HTML contém branding DeepFarms.
- `https://app.deepfarms.com.br`: HTTP 200; login e metadata exibem DeepFarms.
- `https://campo.deepfarms.com.br`: HTTP 200; HTML contém `DeepFarms Campo`.

Foi observada a permanência esperada de referências de asset `/logos/agrosaas-mark.svg` e do endereço operacional `contato@agrosaas.com.br`; ambos permanecem fora do escopo por compatibilidade/pendência de asset aprovado.

### E-mail e PDF/XLSX

Não foi disparado e-mail de teste nem gerado documento novo em produção nesta janela. A configuração SMTP não foi alterada. Os testes locais anteriores cobrem recuperação de senha; a validação visual de e-mail e documento permanece pendência não crítica.

### Estado final do checkout

O build gerou alterações locais esperadas em `apps/web/next-env.d.ts`, `apps/campo/next-env.d.ts` e `apps/campo/public/sw.js`, além dos untracked operacionais preservados. Não houve alteração funcional manual durante o deploy. Os artefatos gerados devem ser tratados conforme o procedimento normal do servidor; nenhum `reset --hard` foi executado.

### Banco, infraestrutura e rollback

Nenhuma migration, Alembic upgrade, alteração de RDS, schema, dados, DNS, SSL, Nginx, storage ou unit systemd foi executada. Nenhum rollback foi necessário.

## 17. Veredicto final

**BRAND-RENAME-04 — STATUS: GO COM RESSALVAS**

O deploy ocorreu com sucesso: API, OpenAPI, Web, Campo e serviços necessários estão operacionais após a atualização. As ressalvas restantes são não críticas: validação manual de e-mail/PDF/XLSX em produção, referências de asset antigo e arquivos gerados pelo build no checkout. Não há evidência de regressão de disponibilidade ou integridade.
