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
