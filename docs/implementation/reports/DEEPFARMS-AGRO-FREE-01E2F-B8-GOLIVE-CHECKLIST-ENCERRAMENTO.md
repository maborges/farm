# DEEPFARMS-AGRO-FREE-01E2F-B8 — Go-Live Controlado e Encerramento do Mercado

**Data da verificação:** 22/10/2026  
**Ambiente homologado:** equivalente local de pré-publicação, com build Next.js de produção, FastAPI real e proxy reverso de mesma origem equivalente ao Nginx  
**Referência funcional:** B7B, B7C e `DEEPFARMS-AGRO-FREE-01E2F-B7D-ENCERRAMENTO-INTEGRIDADE-MERCADO.md`  
**Veredicto:** **GO COM RESSALVAS**

## 1. Decisão

O módulo Mercado está tecnicamente apto à publicação controlada. Não foi encontrado defeito de integridade de preço, indisponibilidade de endpoint, exposição de segredo ou falha de rollback no procedimento preparado.

O veredicto permanece **GO COM RESSALVAS** porque duas providências operacionais ainda precisam ocorrer dentro da janela autorizada de publicação:

1. gerar e aprovar um commit/SHA imutável contendo o estado homologado; o workspace atual não possui uma referência de release que permita ao servidor obter exatamente este conteúdo;
2. instalar a unit `agrosaas-agro.service` e o vhost do Agro, pois o runbook atual cobre API, Web e Campo, mas ainda não registra o processo Next.js do Agro.

Essas providências não exigem alteração da arquitetura do Mercado, do catálogo, da ingestão, da conversão cambial ou do cache. Nenhuma delas foi executada nesta etapa, conforme a restrição da B8.

## 2. Checklist final

| Verificação | Resultado | Evidência |
|---|---:|---|
| Estado atual corresponde à B7D | **APROVADO** | Parser flexível por integridade, teste XLS × snapshot, 22 itens, 21 preços e cache v4 presentes; todas as regressões da B7D foram repetidas. |
| Build Next.js de produção | **APROVADO** | Next.js 16.1.6, 10 rotas estáticas geradas, exit code 0. |
| Testes unitários frontend | **APROVADO** | 127/127 em 9 arquivos. |
| Typecheck | **APROVADO** | `tsc --noEmit`, 0 erros. |
| Lint | **APROVADO** | `eslint src --ext .ts,.tsx`, 0 erros e 0 warnings. |
| Backend Mercado e ingestão | **APROVADO** | 14/14, incluindo paridade binária e preservação do snapshot válido. |
| PTAX, macro, IBGE, identidade e BYOK | **APROVADO** | 45/45; apenas warnings Pydantic preexistentes. |
| E2E completo | **APROVADO** | 24/24 em Chromium, executados em série após correção de duas expectativas legadas. |
| API no navegador, sem mock | **APROVADO** | `/catalogo` 200/22, `/precos` 200/21, `/precos/soja` 200 e `/precos/algodao` 404 explícito. |
| Desktop e mobile | **APROVADO** | 22 cards nas duas larguras; preço, unidade, fonte e data visíveis. |
| Conversão USD → EUR → GBP | **APROVADO** | 11 moedas; o preço original `R$ 134,98` da soja permaneceu inalterado nas três trocas. |
| Offline e recuperação | **APROVADO** | Snapshot salvo preservado, estado de dado salvo visível e recuperação automática ao voltar a rede. |
| Preço histórico, sem alegação de tempo real | **APROVADO** | “Semanal — Preço Médio Produtor”, referência 16/10/2026 e aviso “não cotação em tempo real”. |
| Build sem loopback ou segredo | **APROVADO** | Busca binária no artefato limpo sem API localhost, chave AWS/OpenAI, chave privada ou DSN PostgreSQL. |
| Atualização manual DERAL | **APROVADO COM PROCEDIMENTO** | `--dry-run` real aprovado em 22/10/2026; automação semanal continua pendência operacional separada. |
| Unit/vhost Agro em produção | **PENDENTE OPERACIONAL** | Templates e comandos preparados nas seções 10 e 11; não executados. |
| SHA imutável de publicação | **PENDENTE OPERACIONAL** | Deve ser criado e aprovado antes do deploy; commit/push não autorizados nesta etapa. |

## 3. Correspondência com a B7D

A conferência foi feita por conteúdo e comportamento porque não existe commit/tag exclusivo da B7D no workspace. Foram confirmados:

- a retificação documental da matriz DERAL no relatório B7B;
- `services/api/tests/unit/test_paridade_snapshot_deral.py` e a paridade do XLS oficial com o JSON;
- `totalItens` no contrato Pydantic e nas respostas públicas;
- validação frontend por schema, unicidade, lote, hash, data e metadado de contagem, sem lista rígida de 21 IDs;
- aceitação de lotes íntegros de 20, 21 e 22 itens nos testes unitários;
- cache offline `deepfarms_agro_mercado_precos_v4` e Service Worker `deepfarms-agro-v4`;
- catálogo com 22 commodities e 21 preços DERAL;
- algodão somente cadastral, sem valor monetário homologado;
- seletor compartilhado de 11 moedas e BRL sempre visível.

### Ajustes encontrados e aplicados na B8

| Arquivo | Ajuste | Motivo |
|---|---|---|
| `apps/agro/src/app/mercado/page.tsx` | Removido fallback compilável `http://127.0.0.1:8000`; o SSR só usa `AGRO_API_INTERNAL_ORIGIN` quando a infraestrutura a fornece. | Impedir loopback local dentro do artefato de publicação. |
| `apps/agro/next.config.ts` | Removido destino local padrão do rewrite; sem variável interna, o Nginx responde por `/api/v1`. | Manter o navegador em mesma origem e evitar configuração de desenvolvimento no build. |
| `apps/agro/tests/e2e/mercado-catalogo-expansao.spec.ts` | Expectativa ajustada de `CONAB / MAPA` para a sigla cadastrada `CONAB/MAPA`. | O teste antigo divergia do contrato e do card corretos. |
| `apps/agro/tests/e2e/mercado-ptax.spec.ts` | Espera de `networkidle` substituída por DOM carregado e card PTAX visível no cenário offline. | Evitar timeout causado por consultas assíncronas sem flexibilizar a asserção funcional. |

Nenhum preço, unidade, célula, hash, nome de commodity ou transformação monetária foi alterado na B8.

## 4. Contratos HTTP validados

As chamadas abaixo partiram tanto do servidor local quanto do Chromium, usando a mesma origem pública do frontend no navegador.

| Endpoint | HTTP | Contrato observado |
|---|---:|---|
| `/api/v1/public/mercado/catalogo` | 200 | `totalItens=22`, 22 itens; algodão com `valor=null` e estado cadastral. |
| `/api/v1/public/mercado/precos` | 200 | `totalItens=21`, 21 itens, uma data e um hash de documento. |
| `/api/v1/public/mercado/precos/soja` | 200 | R$ 134,98 por saca de 60 kg, DERAL/SEAB-PR, Paraná, `Rav!X12`, referência 16/10/2026. |
| `/api/v1/public/mercado/precos/algodao` | 404 | “Cotação pública para commodity 'algodao' não homologada”. |

Os payloads preservados estão em:

- [catalogo.json](evidencias/DEEPFARMS-AGRO-FREE-01E2F-B8/catalogo.json)
- [precos.json](evidencias/DEEPFARMS-AGRO-FREE-01E2F-B8/precos.json)
- [preco-soja.json](evidencias/DEEPFARMS-AGRO-FREE-01E2F-B8/preco-soja.json)
- [preco-algodao-404.json](evidencias/DEEPFARMS-AGRO-FREE-01E2F-B8/preco-algodao-404.json)
- [browser-homologacao.json](evidencias/DEEPFARMS-AGRO-FREE-01E2F-B8/browser-homologacao.json)

## 5. Integridade do catálogo e dos preços

| Métrica | Resultado |
|---|---:|
| Commodities cadastradas | 22 |
| Commodities com preço oficial | 21 |
| Commodities sem preço | 1 — Algodão em Pluma |
| Fonte do lote monetário | DERAL/SEAB-PR |
| Documento oficial | `https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls` |
| SHA-256 | `65582dc4c47c8993415dc71ee9af6ed69651b7279d65ab31f4316a1bc787dde1` |
| Data de referência | 16/10/2026 |
| Tipo temporal | Semanal — preço médio recebido pelo produtor |
| Transformação | Arredondamento decimal `ROUND_HALF_UP` para duas casas |

Em 22/10/2026, o comando de atualização em modo seguro baixou novamente a publicação oficial, obteve o mesmo hash, encontrou 21 células, aprovou o schema e encerrou com `DRY_RUN_CONCLUIDO`. Nenhum arquivo foi substituído.

## 6. Homologação visual e de rede

O Chromium acessou o build de produção por `http://127.0.0.1:3015`, um proxy reverso temporário que encaminhou `/api/` ao FastAPI real e as demais rotas ao Next.js final. Não houve `page.route`, mock ou interceptação de resposta no ensaio B8.

Resultados:

- 22 cards e 21 badges “Preço Público Real” no desktop;
- soja com `R$ 134,98`, unidade, DERAL/SEAB-PR e referência 16/10/2026;
- algodão sem `R$`, com “Preço indisponível” e acesso institucional CONAB/MAPA;
- o próprio navegador recebeu 200 para catálogo, preços e soja;
- o 404 do algodão foi provocado deliberadamente para validar a ausência de preço homologado;
- nenhum erro JavaScript de página;
- os erros de console registrados correspondem ao 404 deliberado e ao período em que a rede do contexto foi desligada;
- requisições abortadas correspondem à troca de moeda/navegação, que cancela consultas anteriores por `AbortController`.

Evidências visuais:

- [desktop completo](evidencias/DEEPFARMS-AGRO-FREE-01E2F-B8/01-desktop-mercado.png)
- [algodão indisponível](evidencias/DEEPFARMS-AGRO-FREE-01E2F-B8/02-algodao-indisponivel.png)
- [soja em USD](evidencias/DEEPFARMS-AGRO-FREE-01E2F-B8/03-soja-usd.png)
- [soja em EUR](evidencias/DEEPFARMS-AGRO-FREE-01E2F-B8/03-soja-eur.png)
- [soja em GBP](evidencias/DEEPFARMS-AGRO-FREE-01E2F-B8/03-soja-gbp.png)
- [estado offline com dado salvo](evidencias/DEEPFARMS-AGRO-FREE-01E2F-B8/04-offline-dado-salvo.png)
- [mobile completo](evidencias/DEEPFARMS-AGRO-FREE-01E2F-B8/05-mobile-mercado.png)
- [card da soja no mobile](evidencias/DEEPFARMS-AGRO-FREE-01E2F-B8/06-mobile-soja.png)

## 7. Conversão cambial

O seletor apresentou 11 moedas. A soja foi usada como controle do preço original:

| Moeda | Equivalente observado | BRL original |
|---|---:|---:|
| USD | US$ 26,85; PTAX 21/10/2026 | R$ 134,98 preservado |
| EUR | € 23,90; PTAX 22/10/2026 | R$ 134,98 preservado |
| GBP | £ 20,03; PTAX 22/10/2026 | R$ 134,98 preservado |

A troca ocorreu sem reload. A conversão é uma informação adicional; o valor DERAL em BRL permaneceu visível e inalterado.

## 8. Offline, cache e última versão válida

- O Service Worker usa cache `deepfarms-agro-v4`.
- Rotas `/api/` não são armazenadas pelo Service Worker.
- O snapshot íntegro de preços é persistido no storage versionado v4.
- Ao desligar a rede e recarregar `/mercado`, a tela exibiu “Exibindo dado salvo; a atualização da fonte está indisponível”.
- O card da soja conservou `R$ 134,98` e recebeu identificação de dado salvo.
- Ao restaurar a rede, o aviso desapareceu e o preço original permaneceu igual.
- `test_falha_de_validacao_preserva_ultimo_snapshot` comprovou que uma atualização inválida não substitui o arquivo anterior.
- Os testes frontend comprovaram que payload corrompido, truncado, duplicado ou contaminado não sobrescreve o cache válido.

## 9. Higiene do artefato de produção

Antes do build final, `.next` foi removido para eliminar caches de desenvolvimento. O build foi gerado sem `AGRO_API_INTERNAL_ORIGIN` local e os diretórios de produção `.next/server` e `.next/static`, excluído o subdiretório transitório `.next/dev` mantido por outro processo local, foram inspecionados por padrões.

| Padrão | Ocorrências no artefato |
|---|---:|
| `localhost:8000` ou `127.0.0.1:8000` | 0 |
| URL HTTP local | 0 |
| Access key AWS | 0 |
| Chave em formato `sk-...` | 0 |
| Chave privada PEM/OpenSSH | 0 |
| DSN PostgreSQL | 0 |

Não existe arquivo `.env*` na raiz de `apps/agro`. O valor `AGRO_API_INTERNAL_ORIGIN`, quando necessário em outro ambiente, é variável somente de servidor e não deve usar prefixo `NEXT_PUBLIC_`.

## 10. Preparação da publicação — não executada

### 10.1 Pré-condições obrigatórias

1. aprovar um commit imutável e substituir `<B8_COMMIT_SHA>` abaixo;
2. definir `<AGRO_HOST>` e validar o certificado TLS no fluxo já adotado pela infraestrutura;
3. confirmar os nomes reais das units no host; o runbook usa o prefixo `agrosaas-`;
4. salvar a revisão atualmente publicada antes de qualquer checkout;
5. confirmar que o working tree do servidor está limpo;
6. não executar migration: a B8 não contém alteração de banco.

### 10.2 Preparar código e build

```bash
sudo -iu agrosaas
cd /opt/agrosaas
test -z "$(git status --porcelain)"
git rev-parse HEAD | tee /opt/agrosaas-deploy/b8-previous.sha
git fetch --prune --tags
git checkout --detach <B8_COMMIT_SHA>

corepack pnpm install --frozen-lockfile
cd /opt/agrosaas/services/api
.venv/bin/pip install -e .

cd /opt/agrosaas
services/api/.venv/bin/pytest \
  services/api/tests/unit/test_precos_publicos.py \
  services/api/tests/unit/test_atualizar_snapshot_deral.py \
  services/api/tests/unit/test_ingest_deral_legado.py \
  services/api/tests/unit/test_paridade_snapshot_deral.py -q
pnpm --filter agro test
pnpm --filter agro typecheck
pnpm --filter agro lint
pnpm --filter agro build
exit
```

O build de produção deve ocorrer sem URL local em `NEXT_PUBLIC_*`. A variável `AGRO_API_INTERNAL_ORIGIN` pode permanecer ausente quando o Nginx encaminhar `/api/` ao FastAPI.

### 10.3 Unit systemd preparada

Arquivo proposto: `/etc/systemd/system/agrosaas-agro.service`.

```ini
[Unit]
Description=DeepFarms Agro PWA
After=network.target agrosaas-api.service

[Service]
Type=simple
User=agrosaas
WorkingDirectory=/opt/agrosaas/apps/agro
Environment=NODE_ENV=production
Environment=PATH=/home/agrosaas/.nvm/versions/node/v22.23.1/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/bin/bash -lc 'exec pnpm start'
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Comandos preparados:

```bash
sudo systemctl daemon-reload
sudo systemctl enable agrosaas-agro
sudo systemctl restart agrosaas-api agrosaas-agro
sudo systemctl is-active agrosaas-api agrosaas-agro
```

### 10.4 Vhost Nginx preparado

O Agro deve usar hostname próprio, pois o app não possui `basePath`. O bloco abaixo mantém frontend e API na mesma origem:

```nginx
server {
    listen 443 ssl http2;
    server_name <AGRO_HOST>;

    # Incluir aqui os caminhos de certificado gerenciados pelo fluxo TLS existente.

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    location / {
        proxy_pass http://127.0.0.1:3004;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Antes de ativar:

```bash
sudo cp /etc/nginx/conf.d/agrosaas-agro.conf /opt/agrosaas-deploy/agrosaas-agro.conf.previous
sudo nginx -t
sudo systemctl reload nginx
```

Se o arquivo ainda não existir, registrar essa condição no log da mudança em vez de executar o `cp`.

## 11. Smoke test pós-publicação — preparado, não executado

### 11.1 No servidor

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/api/v1/public/mercado/catalogo -o /tmp/b8-catalogo.json
curl -fsS http://127.0.0.1:8000/api/v1/public/mercado/precos -o /tmp/b8-precos.json
curl -fsS http://127.0.0.1:8000/api/v1/public/mercado/precos/soja -o /tmp/b8-soja.json
curl -fsS http://127.0.0.1:3004/mercado -o /tmp/b8-mercado.html

/opt/agrosaas/services/api/.venv/bin/python -c '
import json
catalogo = json.load(open("/tmp/b8-catalogo.json"))
precos = json.load(open("/tmp/b8-precos.json"))
soja = json.load(open("/tmp/b8-soja.json"))
assert catalogo["totalItens"] == len(catalogo["itens"]) == 22
assert precos["totalItens"] == len(precos["itens"]) == 21
assert {item["dataReferencia"] for item in precos["itens"]} == {"2026-10-16"}
assert soja["valor"] == 134.98 and soja["moeda"] == "BRL"
assert all(item["id"] != "algodao" for item in precos["itens"])
print("B8_SMOKE_API_OK")
'
```

### 11.2 Pela origem pública

```bash
export AGRO_PUBLIC_ORIGIN="https://<AGRO_HOST>"
curl -fsSI "${AGRO_PUBLIC_ORIGIN}/mercado"
curl -fsS "${AGRO_PUBLIC_ORIGIN}/api/v1/public/mercado/catalogo" -o /tmp/b8-public-catalogo.json
curl -fsS "${AGRO_PUBLIC_ORIGIN}/api/v1/public/mercado/precos" -o /tmp/b8-public-precos.json
curl -fsS "${AGRO_PUBLIC_ORIGIN}/sw.js" | grep 'deepfarms-agro-v4'

cd /opt/agrosaas/apps/agro
PLAYWRIGHT_BASE_URL="${AGRO_PUBLIC_ORIGIN}" \
  pnpm exec playwright test \
  tests/e2e/mercado-precos-reais.spec.ts \
  tests/e2e/mercado-catalogo-expansao.spec.ts \
  --workers=1
```

O operador deve ainda trocar USD → EUR → GBP no navegador, conferir que `R$ 134,98` permanece visível e repetir um reload offline depois da primeira carga completa.

## 12. Rollback — preparado, não executado

Não há migration na B8. O rollback de código não exige alteração ou restauração de banco.

### 12.1 Falha após atualizar uma instalação Agro existente

```bash
sudo -iu agrosaas
export B8_PREVIOUS_SHA="$(cat /opt/agrosaas-deploy/b8-previous.sha)"
cd /opt/agrosaas
git checkout --detach "${B8_PREVIOUS_SHA}"
corepack pnpm install --frozen-lockfile
cd /opt/agrosaas/services/api
.venv/bin/pip install -e .
cd /opt/agrosaas
pnpm --filter agro build
exit

sudo systemctl restart agrosaas-api agrosaas-agro
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl is-active agrosaas-api agrosaas-agro nginx
```

Depois do rollback, repetir o smoke da seção 11 contra a revisão anterior.

### 12.2 Falha na primeira publicação do Agro

```bash
sudo systemctl disable --now agrosaas-agro
sudo cp /opt/agrosaas-deploy/agrosaas-agro.conf.previous /etc/nginx/conf.d/agrosaas-agro.conf
sudo nginx -t
sudo systemctl reload nginx
```

Se não existia vhost anterior, remover o novo arquivo dentro da mudança aprovada, validar `nginx -t` e recarregar o Nginx. Os serviços Web, Campo e o banco comercial não participam desse rollback.

## 13. Atualização manual provisória do DERAL

**Responsável funcional:** Operações / Release Manager DeepFarms.  
**Responsável técnico de apoio:** Backend Mercado.  
**Cadência:** semanal, após a publicação do DERAL/SEAB-PR, e sempre que o painel sinalizar defasagem.  
**Automação:** pendência operacional separada; não criar cron sem monitoramento, alerta e rollback do snapshot.

Procedimento provisório:

1. preservar o XLS oficial e seu hash em diretório de evidências controlado;
2. executar primeiro `--dry-run` e exigir os eventos `PARSING_BIFF8_CONCLUIDO`, `VALIDACAO_ESQUEMA_APROVADA` e `DRY_RUN_CONCLUIDO` com 21 itens;
3. revisar data, semana, período, rótulos, unidades e hash;
4. executar a publicação atômica sem `--force`;
5. se houver novo arquivo datado, atualizar em revisão de código o `SNAPSHOT_PATH` de `precos_publicos.py` para o novo snapshot;
6. executar paridade, testes de API, frontend, build e smoke antes de liberar;
7. usar `--force` somente após revisão explícita quando a fonte alterar um arquivo já publicado para a mesma data;
8. em qualquer falha, não mudar o ponteiro ativo e manter a última versão válida.

Comandos provisórios:

```bash
sudo install -d -o agrosaas -g agrosaas -m 0750 /srv/agrosaas/deral-evidencias
sudo -iu agrosaas
export DERAL_DATA_REFERENCIA="AAAA-MM-DD"
curl --fail --location --proto '=https' --tlsv1.2 \
  'https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls' \
  -o "/srv/agrosaas/deral-evidencias/prp-${DERAL_DATA_REFERENCIA}.xls"
sha256sum "/srv/agrosaas/deral-evidencias/prp-${DERAL_DATA_REFERENCIA}.xls"

cd /opt/agrosaas
services/api/.venv/bin/python services/api/scripts/atualizar_snapshot_deral.py \
  --local-file "/srv/agrosaas/deral-evidencias/prp-${DERAL_DATA_REFERENCIA}.xls" \
  --dry-run

# Somente depois da revisão do dry-run:
services/api/.venv/bin/python services/api/scripts/atualizar_snapshot_deral.py \
  --local-file "/srv/agrosaas/deral-evidencias/prp-${DERAL_DATA_REFERENCIA}.xls"
```

O atualizador cria um arquivo datado de forma atômica, mas o serviço ainda aponta explicitamente para o snapshot ativo. Essa ativação manual é deliberadamente mantida no procedimento até que exista automação observável e reversível.

## 14. Riscos residuais

| Risco | Severidade | Mitigação |
|---|---:|---|
| Atualização automática semanal ainda ausente | Baixa operacional | Responsável, cadência e procedimento manual definidos na seção 13. |
| Ativação de novo snapshot exige alteração do ponteiro versionado | Média operacional | Revisão de código, paridade, testes e rollback preservam a última versão válida. |
| Estado homologado ainda sem SHA de release | Média operacional | Publicação bloqueada até aprovação de `<B8_COMMIT_SHA>`; SHA anterior é capturado antes do checkout. |
| Unit e vhost Agro ainda não instalados | Média operacional | Templates compatíveis com systemd/Nginx existentes e rollback de primeira instalação preparados. |
| BCB/IBGE podem sofrer indisponibilidade externa | Baixa | Estados de erro/offline e caches independentes foram aprovados; preços DERAL continuam em BRL. |
| Warnings Pydantic em módulos legados | Baixa técnica | 45 testes passaram; migração de APIs depreciadas fica fora do escopo do Mercado. |

## 15. Veredicto final

**GO COM RESSALVAS.**

O software, os dados, os endpoints, o build e a experiência desktop/mobile/offline estão aprovados. Os 21 preços de 16/10/2026 são exibidos como preços médios semanais históricos, jamais como tempo real; o algodão permanece sem cotação; e não há endereço local ou segredo exposto no artefato final.

A publicação pode ser autorizada depois que houver um SHA imutável aprovado e a mudança de infraestrutura incluir a unit/vhost Agro com o rollback descrito. A atualização automática DERAL permanece uma pendência operacional separada, mitigada pelo procedimento manual desta documentação.

Nenhum deploy, commit, push, migration ou alteração em produção foi executado na B8.
