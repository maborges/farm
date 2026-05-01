# Estabilizacao Frontend Step 97.4

**Data:** 2026-05-01  
**Escopo:** `apps/web`  
**Objetivo:** estabilizar o ambiente local do frontend e garantir o funcionamento do proxy `/api/v1` antes de repetir a validacao real do onboarding.

## 1. Resumo executivo

O ambiente frontend local foi estabilizado com sucesso.

O ponto central foi substituir o uso implicito de Turbopack no `next dev` por `webpack`, porque o ambiente anterior apresentava panics internos e corrompia a validacao real do fluxo.

Resultado final:

- `next dev` sobe sem panic de Turbopack;
- `/` responde `200`;
- `/register` responde `200`;
- `/login` responde `200`;
- `/api/v1/billing/plans` via proxy do Next responde `200`;
- ambiente pronto para repetir o Step 97.3.

## 2. Acoes executadas

### 2.1 Limpeza de cache local

Arquivos removidos:

- `apps/web/.next`
- `apps/web/tsconfig.tsbuildinfo`

Objetivo:

- eliminar cache corrompido do Next/Turbopack;
- remover artefatos antigos de TypeScript;
- forcar recompilacao limpa.

### 2.2 Validacao de configuracao

Arquivos revisados:

- `apps/web/next.config.ts`
- `apps/web/.env.local`
- `apps/web/src/app/api/v1/[...path]/route.ts`

Confirmacoes:

- `BACKEND_URL=http://127.0.0.1:8000`
- `NEXT_PUBLIC_API_URL=/api/v1`
- o proxy `src/app/api/v1/[...path]/route.ts` encaminha corretamente para `${BACKEND_URL}/api/v1/...`

### 2.3 Workaround confiavel aplicado

Mudanca realizada:

- `apps/web/package.json`

Antes:

- `next dev`

Depois:

- `next dev --webpack`

Motivo:

- evitar a instabilidade do Turbopack observada no Step 97.3;
- tornar a inicializacao local confiavel por padrao;
- nao depender de flag manual em cada execucao.

## 3. Validacoes executadas

### 3.1 Backend direto

Validacao:

- `GET http://127.0.0.1:8000/api/v1/billing/plans`

Resultado:

- `200`

### 3.2 Frontend proxy

Validacao:

- `GET http://127.0.0.1:3000/api/v1/billing/plans`

Resultado:

- `200`

Observacao:

- isso confirmou que o problema anterior nao era mais o backend;
- a camada proxy do Next passou a encaminhar corretamente.

### 3.3 Rotas publicas

As rotas foram validadas no contexto correto de host local (`Host: localhost:3000`), porque o middleware trata `127.0.0.1` como dominio customizado.

Resultados finais:

- `GET /` -> `200`
- `GET /register` -> `200`
- `GET /login` -> `200`

Observacao:

- durante a primeira compilacao a saida do dev server mostrou `HEAD ... 404` transitorios para rotas ainda nao compiladas;
- depois da compilacao completa, as mesmas rotas responderam `200`.
- isso e comportamento de warm-up do ambiente dev, nao falha persistente do app.

## 4. Evidencias observadas no dev server

Saida relevante do `next dev --webpack`:

- `Next.js 16.1.6 (webpack)`
- `Ready in 3.2s`
- `GET /api/v1/billing/plans 200`
- `HEAD / 200`
- `HEAD /login 200`
- `HEAD /register 200`

Importante:

- nao houve novo panic do Turbopack;
- o proxy voltou a responder com sucesso.

## 5. Problema raiz identificado

O bloqueio do Step 97.3 estava associado ao ambiente local do frontend em desenvolvimento:

- cache corrompido em `.next`;
- instabilidade especifica de Turbopack;
- falha indireta do proxy `/api/v1` durante esse estado.

O backend nao era a causa principal.

## 6. Classificacao

### Resolvido

- **CRITICO:** proxy `/api/v1` falhando no frontend local
- **CRITICO:** `next dev` instavel com panics de Turbopack
- **ALTO:** impossibilidade de repetir a validacao real do onboarding

### Residual / conhecido

- **BAIXO:** o middleware local exige host coerente com `localhost`, entao testes por `127.0.0.1` puro podem cair no rewrite de dominio customizado e gerar `404` falso.

## 7. Estado final

O ambiente local ficou pronto para repetir a validacao real do onboarding com estas premissas:

- backend em `127.0.0.1:8000`
- frontend em `3000`
- comando padrao:

```bash
cd /opt/lampp/htdocs/farm/apps/web
npm run dev -- --port 3000
```

ou simplesmente:

```bash
cd /opt/lampp/htdocs/farm/apps/web
npm run dev
```

se a porta `3000` estiver livre.

## 8. Conclusao

O Step 97.4 atingiu o objetivo.

O frontend local e o proxy Next foram estabilizados sem alterar backend, onboarding, schema ou regra de negocio. O ambiente agora esta em condicao tecnica de repetir o Step 97.3 com validacao real de usuario de teste.
