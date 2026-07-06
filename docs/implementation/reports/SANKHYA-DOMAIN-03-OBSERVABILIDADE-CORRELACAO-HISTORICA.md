# SANKHYA-DOMAIN-03 — Observabilidade Operacional e Correlação Histórica

## 1. Resumo Executivo

Esta execução aprofundou a observabilidade operacional do Sankhya sem remover o legado. A integração agora expõe uma timeline consolidada e um diagnóstico operacional resumido, correlacionando `SankhyaSyncLog`, `IntegrationJob` e `IntegrationHealth` com masking de payloads sensíveis.

## 2. Arquivos alterados

- `services/api/integracoes/sankhya/routers/__init__.py`
- `services/api/integracoes/sankhya/schemas/__init__.py`
- `services/api/integracoes/sankhya/services/sync_service.py`
- `services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py`
- `services/api/tests/unit/integracoes/test_sankhya_governed_integration.py`
- `apps/web/src/components/integracoes/sankhya-console.tsx`
- `apps/web/src/components/integracoes/sankhya-timeline.tsx`
- `apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx`

## 3. Timeline operacional

Foi adicionada uma timeline consolidada em `GET /integracoes/sankhya/timeline`.

Cada item pode representar:

- `canonical_job`
- `legacy_log`
- `health_snapshot`

Campos principais:

- `tipo_registro`
- `origem_dado`
- `feature_code`
- `status`
- `event_type`
- `resumo`
- `occurred_at`
- `started_at`
- `finished_at`
- `duracao_ms`
- `processados`
- `sucessos`
- `erros`
- `correlation_id`
- `payload`

Filtros suportados:

- `status`
- `feature_code`
- `origem`
- `limit`

## 4. Diagnóstico operacional

Foi adicionado `GET /integracoes/sankhya/diagnostico`.

O diagnóstico consolida:

- `health_atual`
- `status_degradacao`
- `ultimo_sucesso_at`
- `ultima_falha_at`
- `falhas_consecutivas`
- `feature_mais_problematica`
- `jobs_pendentes`
- `jobs_falhos`
- `recomendacao_operacional`

O objetivo é orientar rapidamente o tenant e o suporte sem obrigar leitura manual de todos os logs.

## 5. Frontend tenant

O console do tenant passou a exibir:

- cards de diagnóstico operacional;
- linha do tempo consolidada;
- jobs oficiais recentes;
- logs legados correlacionados;
- health e lifecycle já existentes;
- indicação de origem oficial ou legada.

O formulário de configuração permaneceu intacto.

## 6. Frontend backoffice

O backoffice foi atualizado para observabilidade e suporte com:

- diagnóstico resumido para troubleshooting;
- timeline consolidada filtrável por status, origem e feature;
- jobs oficiais recentes;
- logs legados enriquecidos;
- reforço de que não é o console principal de configuração.

## 7. Compatibilidade legado/oficial

- `SankhyaConfig` preservado.
- `SankhyaSyncLog` preservado.
- Endpoints anteriores preservados.
- Novos endpoints aditivos:
  - `/timeline`
  - `/diagnostico`
- Fallback legado mantido quando não houver camada oficial suficiente.

## 8. Segurança

- Payloads sensíveis continuam mascarados.
- Não há retorno de `password`, `token`, `secret`, `private_key` ou `certificate` em texto bruto.
- Timeline e diagnóstico reutilizam masking do service.
- Rotas continuam tenant-scoped com sessão compatível com RLS.

## 9. Testes executados

- `services/api/.venv/bin/pytest services/api/tests/unit/integracoes -q`
- `services/api/.venv/bin/ruff check services/api/integracoes/sankhya services/api/tests/unit/integracoes`
- `cd apps/web && pnpm exec eslint src/components/integracoes/sankhya-console.tsx src/components/integracoes/sankhya-timeline.tsx 'src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx' src/app/integracoes/page.tsx`
- `./.venv/bin/alembic upgrade head`
- `git diff --check`

Cobertura nova:

- timeline com dados oficiais e legados;
- timeline com fallback apenas legado;
- diagnóstico de último sucesso, última falha e feature mais problemática;
- presença das rotas `/timeline` e `/diagnostico`.

## 10. Limitações

- `IntegrationHealth` continua sendo snapshot atual, não histórico persistido por versão.
- Não houve migração de registros legados para a camada oficial.
- A correlação histórica depende do vínculo incremental entre `legacy_log_id` e `IntegrationJob`.

## 11. Próxima execução recomendada

`SANKHYA-DOMAIN-04` para aprofundar histórico persistido de health/diagnóstico, correlação com eventos oficiais em nível mais explícito e eventual priorização de consumo do domínio oficial na observabilidade, ainda sem big bang.
