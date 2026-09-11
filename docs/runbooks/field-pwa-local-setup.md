# Field PWA - Runbook de ambiente local

## DeepFarms — Guia de Inicialização dos Serviços

> Ambiente: Windows 11 + WSL2 (Ubuntu) + pnpm monorepo  
> Estrutura: `/opt/lampp/htdocs/farm/`

---

## Pré-requisitos

- Celular e PC na **mesma rede Wi-Fi**
- `cloudflared` instalado em `/usr/local/bin/cloudflared`
- Port forwarding WSL2 → Windows configurado (portas 3000, 3002, 8000)
- Todos os comandos abaixo são executados no **WSL2**, salvo indicação contrária

---

## 1. API (Backend Python — porta 8000)

```bash
cd /opt/lampp/htdocs/farm/services/api
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Aguarde a mensagem:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## 2. Frontend Web (Next.js — porta 3000)

Em um **novo terminal WSL2**:

```bash
cd /opt/lampp/htdocs/farm
pnpm --filter web dev
```

Aguarde a mensagem:
```
▲ Next.js 16.1.6 (webpack)
✓ Ready in ...
```

---

## 3. Frontend Campo — PWA (Next.js — porta 3002)

### 3.1 Build de produção

O PWA exige build de produção — o Service Worker **não é registrado em modo dev**.

```bash
cd /opt/lampp/htdocs/farm
pnpm --filter @agro/campo build
```

> Refaça o build sempre que alterar código ou variáveis de ambiente.

### 3.2 Iniciar servidor de produção

Em um **novo terminal WSL2**:

```bash
cd /opt/lampp/htdocs/farm/apps/campo
node_modules/.bin/next start -p 3002
```

Aguarde a mensagem:
```
▲ Next.js 16.1.6
✓ Ready on http://0.0.0.0:3002
```

---

## 4. Túneis HTTPS para teste no celular (Cloudflare)

O PWA exige HTTPS para registrar o Service Worker. Os túneis abaixo expõem os serviços locais via URL pública.

> Execute cada comando em um terminal WSL2 separado.

### 4.1 Túnel da API

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

Anote a URL gerada, ex: `https://xxxx.trycloudflare.com`

### 4.2 Atualizar variável de ambiente do Campo

Substitua pela URL gerada no passo 4.1:

```bash
echo "NEXT_PUBLIC_API_URL==https://personals-diamond-calls-island.trycloudflare.com" > /opt/lampp/htdocs/farm/apps/campo/.env.local
```

Refaça o build (passo 3.1) após atualizar o `.env.local`.

### 4.3 Túnel do Campo (PWA)

```bash
cloudflared tunnel --url http://127.0.0.1:3002
```

Anote a URL gerada, ex: `https://yyyy.trycloudflare.com`

### 4.4 Túnel do Frontend Web (opcional)

```bash
cloudflared tunnel --url http://127.0.0.1:3000
```

---

## 5. Acesso no celular

| Serviço       | URL                              |
|---------------|----------------------------------|
| Frontend Web  | `https://yyyy.trycloudflare.com` |
| Campo (PWA)   | `https://zzzz.trycloudflare.com` |

> As URLs mudam a cada vez que o `cloudflared` é reiniciado.  
> Para URLs fixas, crie uma conta gratuita em [dashboard.ngrok.com](https://dashboard.ngrok.com) ou [dash.cloudflare.com](https://dash.cloudflare.com) e configure um túnel persistente.

---

## 6. Resolução de problemas comuns

### Porta já em uso

```bash
fuser -k 3002/tcp   # libera porta 3002
fuser -k 3000/tcp   # libera porta 3000
fuser -k 8000/tcp   # libera porta 8000
```

### PWA não instala no celular

- Confirme que está acessando via `https://` (não `http://`)
- Verifique se o `manifest.json` está acessível: `https://url/manifest.json`
- No Chrome Android: menu (⋮) → "Adicionar à tela inicial"

### Túnel cai (Error 1033)

O servidor local parou. Verifique se o `next start` ainda está rodando e reinicie o `cloudflared`.

### `[PWA] PWA support is disabled`

Mensagem normal em modo `dev`. Use sempre `next build` + `next start` para testar o PWA.

---

## Resumo de terminais necessários

| Terminal | Comando                                      |
|----------|----------------------------------------------|
| 1        | API Python (`uvicorn`)                       |
| 2        | Frontend Web (`pnpm --filter web dev`)       |
| 3        | Campo produção (`next start -p 3002`)        |
| 4        | Túnel API (`cloudflared ... 8000`)           |
| 5        | Túnel Campo (`cloudflared ... 3002`)         |
| 6        | Túnel Web, opcional (`cloudflared ... 3000`) |
