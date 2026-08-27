# 06 — API e UX

## Prefixo

Rotas internas sob `/api/v1/quality/`, respeitando router/service/schema. Rotas públicas somente para passaporte já publicado, sob `/api/v1/public/`.

## Superfície inicial

- `GET/POST /protocols`
- `GET/PATCH /protocols/{id}`
- `POST /protocols/{id}/publish`
- `GET/POST /samples`
- `GET/POST /reports`
- `POST /reports/{id}/evaluate`
- `POST /reports/{id}/approve`
- `POST /reports/{id}/reanalyze`
- `GET /reports/{id}/explanation`
- `GET /lots/{lot_id}/quality`
- `GET /dashboards/quality`
- `POST /imports`

Os nomes finais devem ser confrontados com o routing map e com os routers de qualidade existentes antes de qualquer implementação.

## Telas Web

1. visão geral de qualidade;
2. protocolos e versões;
3. fila de amostras/laudos;
4. detalhe do lote e linha do tempo;
5. formulário de análise;
6. revisão técnica;
7. ajustes e bloqueios;
8. relatórios e exportação;
9. calibração de equipamentos.

## Campo PWA

O PWA deve persistir amostras e medições no Dexie, enviar pela fila `/api/v1/sync` e indicar claramente pendência, erro, conflito e aprovação. Não fazer fetch bloqueante como condição para salvar uma coleta.

## UX de decisão

O usuário deve visualizar imediatamente: resultado, classe, status, critérios fora do padrão, impacto no peso/preço e ação recomendada. A interface não deve esconder a origem ou a idade da medição.
