# EXECUTION-WIZARD-07 — GO-LIVE ASSISTIDO E OPERAÇÃO PILOTO

## Escopo implementado

Esta execução manteve a arquitetura do Wizard e adicionou suporte operacional para o primeiro piloto controlado, com foco em clareza de bloqueios e prontidão de go-live.

Entradas principais:

* enriquecimento do payload `GET /api/v1/wizard/status`;
* exibição explícita de motivos de bloqueio no frontend;
* destaque visual para checklist mínimo faltante;
* destaque visual para pendências críticas abertas;
* indicação clara de operação assistida e estabilização;
* inclusão do acesso ao Wizard no menu lateral do dashboard.

## Decisões tomadas

1. O backend continua sendo a fonte da verdade para prontidão e go-live.
2. O frontend não replica regra de negócio e apenas consome os motivos calculados pelo backend.
3. O `status` do Wizard passou a expor:
   * `motivos_bloqueio`;
   * `itens_checklist_faltantes`;
   * `pendencias_criticas`.
4. O Wizard ficou navegável pelo menu:
   * `Configurações -> Wizard de Implantação`

## Rotas envolvidas

Rotas consumidas/impactadas:

* `GET /api/v1/wizard/status`
* `POST /api/v1/wizard/iniciar`
* `GET /api/v1/wizard/etapas`
* `GET /api/v1/wizard/checklist`
* `POST /api/v1/wizard/checklist/reavaliar`
* `GET /api/v1/wizard/pendencias`
* `POST /api/v1/wizard/pronto-go-live`
* `POST /api/v1/wizard/go-live`
* `POST /api/v1/wizard/estabilizar`
* `POST /api/v1/wizard/concluir`
* `POST /api/v1/wizard/pausar`
* `POST /api/v1/wizard/retomar`
* `POST /api/v1/wizard/bloquear`
* `POST /api/v1/wizard/desbloquear`
* `POST /api/v1/wizard/cancelar`

## Checklist operacional de piloto

Itens mínimos explicitamente observados para o piloto:

* `UnidadeProdutiva` ativa e vinculada;
* checklist mínimo satisfeito a partir do estado real do tenant;
* ausência de pendências críticas abertas;
* status fora de `BLOCKED`;
* avanço por `READY_FOR_GO_LIVE` antes de `GO_LIVE`.

## Critérios de go-live assistido

O go-live assistido permanece bloqueado quando ocorrer qualquer um destes cenários:

* ausência de `unidade_produtiva_id`;
* checklist mínimo não satisfeito;
* pendência crítica aberta;
* implantação em `BLOCKED`;
* transição fora da ordem oficial da State Engine.

## Critérios de estabilização

A estabilização é tratada como fase posterior ao `GO_LIVE`, com leitura explícita no frontend e manutenção da fonte de verdade no backend.

O tenant somente deve avançar nessa fase quando:

* o go-live tiver sido iniciado oficialmente;
* os bloqueios estruturais tiverem sido resolvidos;
* o Owner/Admin conseguir acompanhar pendências e checklist remanescentes sem ambiguidade.

## Limitações

* esta execução não implementa automações adicionais;
* não cria scheduler, notificações ou outbox para o Wizard;
* não altera onboarding, billing, auth, convites ou tenant provisioning;
* não adiciona nova migration.

## Validações executadas

Executar:

* `pytest services/api/tests/unit/wizard -q`
* `ruff check services/api/wizard services/api/tests/unit/wizard`
* `cd apps/web && pnpm exec eslint <arquivos alterados>`
* `cd apps/web && pnpm exec tsc --noEmit`
* `git diff --check`

Se alguma validação falhar ou não concluir no ambiente, registrar no fechamento da execução.

## Próximos passos

1. validar o Wizard com tenant real do piloto controlado;
2. revisar mensagens e terminologia com equipe de implantação;
3. iniciar a fase de uso assistido em produção controlada;
4. somente depois avaliar automações adicionais ou integrações de observabilidade.
