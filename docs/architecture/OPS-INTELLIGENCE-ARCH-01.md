# OPS-INTELLIGENCE-ARCH-01

## Arquitetura Canônica do Motor Global de Recomendações

## Status

- Tipo: arquitetura canônica em operação controlada.
- Núcleo oficial: `services/api/recommendations/`.
- Estado: fundação, providers, persistência, lifecycle, API, consumidores Web/Campo e notificações já estão implementados.
- Consolidação: scheduler, Event/Outbox e RBAC estão ativos; a compatibilidade climática legada foi auditada e permanece controlada enquanto houver consumidores.

## Resumo Executivo

O AgroSaaS já possui um Motor Global de Recomendações. `services/api/recommendations/` é a única fronteira oficial para gerar, persistir, deduplicar, expor e acompanhar recomendações operacionais.

O clima participa desse motor por `ClimaRecommendationProvider`. O serviço climático legado (`services/api/agricola/climatico/recommendation_service.py`) não é, e não deve se tornar, o núcleo global.

O trabalho restante é conectar de forma produtiva o scheduler e os gatilhos Event/Outbox, explicitar RBAC do lifecycle e retirar compatibilidades legadas quando não houver consumidores. Não se deve criar outro engine, registry, tabela, API, read model, scheduler ou fluxo de notificações.

## Veredicto Arquitetural

Preservar o motor global existente, com providers especializados por domínio:

```text
Fato de domínio / alerta / indicador
  -> OperationalContext + RecommendationSignal
  -> RecommendationProvider do domínio
  -> RecommendationEngine
  -> RecommendationLifecycleService
  -> RecommendationResult persistido
  -> Web / sync Campo / notificação elegível
  -> decisão humana explícita
```

`Alert Engine` e `Recommendation Engine` são complementares, mas independentes:

- alerta detecta, materializa risco e mantém seu próprio lifecycle;
- recomendação organiza uma ação sugerida e mantém lifecycle próprio;
- uma recomendação não é um alerta, e um alerta não autoriza execução automática.

## Domínio Oficial Implementado

### Núcleo e contratos

| Componente | Evidência | Responsabilidade |
| --- | --- | --- |
| `RecommendationEngine` | `services/api/recommendations/engine.py` | Orquestra providers, contabiliza a execução e entrega candidatos ao lifecycle. |
| `RecommendationProvider` | `services/api/recommendations/provider.py` | Contrato abstrato; avalia contexto e sinais, retornando somente `RecommendationCandidate`. |
| Registry | `services/api/recommendations/registry.py` e `providers/__init__.py` | Registro explícito e único dos providers. |
| `OperationalContext` e `RecommendationSignal` | `services/api/recommendations/schemas.py` | Contratos de entrada tenant-aware para recorte operacional e sinais. |
| `RecommendationCandidate` | `services/api/recommendations/schemas.py` | Contrato de saída do provider antes da persistência. |
| `RecommendationResult` | `services/api/recommendations/models.py` | Read model persistido oficial da recomendação. |
| `RecommendationLifecycleService` | `services/api/recommendations/lifecycle_service.py` | Criação/atualização, dedupe, transições e auditoria. |
| `RecommendationSchedulerService` e runner | `services/api/recommendations/scheduler.py` e `runner.py` | Execução controlada por tenant, unidade, domínio, lote e `dry_run`. |
| Notification bridge | `services/api/recommendations/notification_bridge.py` | Tradução opcional de itens novos, ativos e elegíveis para o dispatcher oficial. |
| Router e query layer | `services/api/recommendations/router.py` e `query_service.py` | Listagem, detalhe, métricas e ações explícitas de lifecycle. |

### Persistência, isolamento e lifecycle

As tabelas oficiais são `recommendation_results` e `recommendation_lifecycle_events`, criadas pela migration `20260703_ops_intelligence_02_recommendations_foundation.py`.

- ambas possuem `tenant_id`, RLS habilitado e `FORCE ROW LEVEL SECURITY`;
- o dedupe é único para recomendações ativas por `tenant_id + dedupe_key`;
- o lifecycle suporta `CREATED`, `VIEWED`, `ACCEPTED`, `DISMISSED`, `POSTPONED`, `EXECUTED`, `EXPIRED`, `AUTO_EXPIRED`, `SUPERSEDED` e `REOPENED`;
- cada alteração de lifecycle gera evento próprio e trilha de auditoria;
- `RecommendationResult` é o único read model canônico; fontes de domínio não devem materializar cópias paralelas.

### Providers existentes

O registry padrão já registra os seguintes providers em `services/api/recommendations/providers/`:

- `ClimaRecommendationProvider`;
- `AgriculturaRecommendationProvider`;
- `FinanceiroRecommendationProvider`;
- `PecuariaRecommendationProvider`;
- `EstoqueRecommendationProvider`;
- `FrotaRecommendationProvider`;
- `ESGRecommendationProvider`;
- `WizardRecommendationProvider`;
- `CampoRecommendationProvider`.

Cada provider especializa regras e fontes do próprio domínio. Ele não é dono de persistência, lifecycle, notificação, execução operacional ou UI.

### Consumidores integrados

- **API:** `services/api/recommendations/router.py`, incluído em `/api/v1/recommendations`, fornece leitura, métricas e ações de lifecycle autenticadas.
- **Web:** `/dashboard/inteligencia-operacional/recomendacoes`, `apps/web/src/hooks/use-recommendations.ts` e `recommendations-dashboard-client.tsx` consomem o read model e expõem ações explícitas.
- **Campo:** `services/api/campo/service.py` projeta `recommendation_results` no `sync/pull`; o PWA mantém snapshot Dexie em `recomendacoes_operacionais` e o consome em `/recomendacoes`. O pull não reavalia providers.
- **Notificações:** `RecommendationNotificationBridge` reutiliza `NotificationDispatcher` e sua policy/dedupe. Apenas recomendações novas, ativas, não expiradas e de prioridade `HIGH` ou `URGENT` são elegíveis.
- **Eventos reativos:** `RecommendationEventSubscriber` é registrado no `EventSubscriberRegistry` oficial, recebe a entrega do `DomainEventOutboxRelay` e delega o mapeamento a `RecommendationEventMapper`. A primeira ativação cobre `campo.sync.falha` para o provider `campo`; o subscriber produz `RecommendationSignal` e `OperationalContext`, aplica RLS e chama o `RecommendationEngine` existente. Ele não contém regras de provider, persistência direta ou dispatch direto de notificações.

## Diretrizes de Reuso

Reutilizar a infraestrutura existente sem criar fluxos paralelos:

- `Domain Events` e `Outbox` para gatilhos assíncronos confiáveis;
- Alert Engine como produtor de risco/sinal quando aplicável, sem fundir os domínios;
- `RecommendationProvider` para regras de domínio;
- `RecommendationLifecycleService` para persistência, dedupe e auditoria;
- `RecommendationSchedulerService` para processamento em lote;
- `RecommendationNotificationBridge` para comunicação elegível;
- RLS, `tenant_id`, RBAC existente, `TenantAuditLog`, sync Campo e consumidores Web atuais.

O serviço climático legado pode ser mantido somente como compatibilidade temporária para consumidores antigos. Regras novas de clima pertencem exclusivamente ao `ClimaRecommendationProvider`.

## Guardrails Mandatórios

- Não criar segundo `RecommendationEngine`.
- Não criar segundo registry de providers.
- Não criar segunda tabela/read model de recommendation results.
- Não criar scheduler paralelo; integrar o `RecommendationSchedulerService` ao mecanismo de jobs existente.
- Não criar fluxo paralelo de notificações; reutilizar o notification bridge e dispatcher oficiais.
- Providers não persistem diretamente.
- Providers não notificam diretamente.
- Providers não executam mutações operacionais.
- Web e Campo somente consomem o read model; o Campo continua offline-first e não roda providers durante `sync/pull`.
- Recomendações não executam operações automaticamente; aceite e execução são decisões humanas explícitas ou fluxos assistidos já governados por outro domínio.
- Alertas e recomendações mantêm dedupe, lifecycle e auditoria independentes.
- Toda consulta, persistência e job deve preservar `tenant_id`, RLS e RBAC.

## Roadmap Arquitetural Restante

### OPS-INTELLIGENCE-12 — Ativação produtiva controlada

Conectar o `RecommendationSchedulerService` ao scheduler/background job existente, com execução tenant-aware, lotes, idempotência, telemetria e isolamento de falhas.

### OPS-INTELLIGENCE-13 — Subscriber Event/Outbox

Ativado para `campo.sync.falha` por meio do Outbox e barramento oficiais. Próximas ativações devem exigir contrato publicado com tenant, escopo e dados suficientes, preservando o mapper e o subscriber canônicos.

### OPS-INTELLIGENCE-14 — RBAC explícito de lifecycle

Ativado no router oficial com `RecommendationAuthorizationService`, reutilizando `TenantUsuario`, `PerfilAcesso`, `FazendaUsuario` e `TenantPermissions`. As ações humanas usam permissões `recommendations:*` e validam a unidade produtiva real da recomendação; scheduler, subscriber e lifecycle automático continuam caminhos internos sem identidade humana.

### OPS-INTELLIGENCE-15 — Retirada gradual de compatibilidades legadas

Auditoria concluída. `ClimaRecommendationService` permanece como compatibilidade necessária: a rota `/climatico/recomendacoes/{unidade_produtiva_id}` é pública no backend e o dashboard climático Web ainda a consome. O Campo já usa `recommendation_results` e apenas projeta seu formato climático offline. Não houve remoção porque o provider global não tem paridade contratual por operação (`PULVERIZACAO`, `COLHEITA`, `ADUBACAO`, `GERAL`). A retirada só é autorizada após migrar o consumidor Web para o read model oficial, definir a paridade funcional aprovada e comprovar ausência de consumidores.

## Decisão Final

O Motor Global de Recomendações já está implementado e deve ser preservado como infraestrutura única do domínio assistido. A evolução autorizada é ativar, governar e simplificar o que já existe — nunca recriar sua fundação.
