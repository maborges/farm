# OPS-INTELLIGENCE-11 — Auditoria de Estado Atual e Arquitetura Canônica

## Escopo e método

Auditoria somente leitura realizada em 2026-07-29. Nenhum código, migração ou contrato de produção foi alterado. Foram inspecionados o domínio `recommendations`, Alert Engine, Events/Outbox, Notifications, sync Campo, rota Web, migração e testes associados.

## Veredicto

O AgroSaaS **já possui um Recommendation Engine global canônico implementado**. Portanto, não é correto iniciar um novo épico criando outro motor, promover o serviço climático como núcleo, ou criar módulos paralelos.

O núcleo oficial é `services/api/recommendations/`; o clima já é um provider desse núcleo. A evolução correta é ativar e governar os caminhos produtivos restantes, preservando este módulo como única porta de persistência e lifecycle.

## Evidências confirmadas

| Capacidade | Evidência | Estado |
| --- | --- | --- |
| Contrato global e engine | `schemas.py`, `provider.py`, `registry.py`, `engine.py` | Implementado |
| Persistência, dedupe e lifecycle | `models.py`, `lifecycle_service.py`, migration `20260703_ops_intelligence_02_recommendations_foundation.py` | Implementado |
| Isolamento tenant | `tenant_id`, RLS com `FORCE ROW LEVEL SECURITY`, políticas CRUD e índice parcial por tenant/dedupe | Implementado |
| Providers | clima, agricultura, financeiro, pecuária, estoque, frota, ESG, wizard e campo em `recommendations/providers/` | Implementado |
| Query e lifecycle HTTP | `recommendations/router.py`, incluído por `main.py` em `/api/v1/recommendations` | Implementado |
| Consumo Web | `/dashboard/inteligencia-operacional/recomendacoes` e hook `use-recommendations` | Implementado |
| Consumo Campo offline | `recommendation_results` no `sync/pull`, snapshot Dexie e tela `/recomendacoes` | Implementado |
| Notificações | `RecommendationNotificationBridge`, com policy, dedupe e anti-spam | Implementado |
| Alertas | Alert Engine segue separado; providers não o utilizam como motor de recomendação | Correto |

## Respostas às perguntas arquiteturais

### Já existem mecanismos de recomendação distribuídos?

Sim. O inventário histórico mostra serviços locais em clima, agrícola, financeiro, frota, estoque/compras e wizard. Eles são as fontes de regras e sinais. No estado atual, os providers do domínio canônico já absorvem as principais regras, e `RecommendationResult` é o read model persistido oficial.

### Existe duplicação?

Existia duplicação conceitual antes da fundação global, e ainda há compatibilidades legadas a remover gradualmente:

- `ClimaRecommendationService` é legado; o Campo já lê recomendações persistidas e apenas projeta uma compatibilidade climática local.
- Alertas montados diretamente por serviços/dashboards e `services/api/notificacoes/alertas_engine.py` devem permanecer fora do fluxo de novas recomendações e ser consolidados sob o Alert Engine em trabalho próprio.
- Documentos históricos OPS-INTELLIGENCE-01 e ARCH-01 afirmavam que a implementação ainda não existia; este relatório e a atualização de status corrigem essa divergência documental.

Não há justificativa para uma segunda tabela, engine, registry, endpoint, scheduler ou mecanismo de notificações de recomendações.

### O Recommendation Engine climático deve evoluir para global?

Não. O `ClimaRecommendationService` não é o núcleo global: ele é específico a `RegistroClima`, operações climáticas e contratos legados. A regra climática já deve evoluir exclusivamente como `ClimaRecommendationProvider` dentro de `RecommendationEngine`.

### O que pode ser reutilizado?

- `Domain Events` e `Outbox`: gatilho confiável para converter fatos de domínio em avaliação de providers.
- Alert Engine: fonte de sinais e risco, sem transformar alerta em recomendação nem fundir seus lifecycles.
- `RecommendationProvider`: fronteira para regras de cada domínio, retornando somente `RecommendationCandidate`.
- `RecommendationLifecycleService`: persistência, dedupe, auditoria e transições humanas.
- `RecommendationNotificationBridge`: comunicação opcional, apenas para itens elegíveis.
- `RecommendationSchedulerService` e runner: base única para execução em lote, por tenant e com escopo controlado.
- RLS, RBAC existente, `TenantAuditLog`, sync Campo e TanStack Query: infraestrutura transversal já adotada.

## Arquitetura canônica preservada

```text
Fato de domínio / alerta / indicador
  -> Domain Event + Outbox (quando a reação for assíncrona)
  -> adaptador de sinal e OperationalContext
  -> RecommendationProvider do domínio
  -> RecommendationEngine
  -> RecommendationLifecycleService + RecommendationResult
  -> Web / sync Campo / notificação elegível
  -> decisão humana explícita
```

Responsabilidades mandatórias:

- Domínios produzem fatos, indicadores e regras; não persistem recomendações fora do motor.
- Providers avaliam e retornam candidatos; não notificam, não executam operação e não fazem lifecycle.
- O engine orquestra providers; o lifecycle materializa, deduplica e audita.
- Alertas detectam riscos; recomendações sugerem ação. Os dois lifecycles permanecem independentes.
- Web e Campo só consomem o read model. O Campo permanece offline-first e não reavalia providers no pull.
- Aceite ou execução de recomendação não autoriza mutação operacional automática.

## Lacunas reais para rollout produtivo

1. **Agendamento efetivo:** `RecommendationSchedulerService` e runner existem, mas não há referência de invocação no scheduler/background jobs do processo. É preciso conectar uma job tenant-aware e idempotente, sem criar scheduler paralelo.
2. **Caminho por eventos:** não há subscriber do barramento Events/Outbox que adapte eventos a `RecommendationSignal` e acione o engine. O contrato já comporta essa entrada; faltam mapeamentos explícitos e políticas de elegibilidade por evento.
3. **RBAC explícito:** as rotas exigem usuário autenticado e preservam RLS, mas a matriz de permissões específica de recomendações/lifecycle não está declarada no router. Definir permissões por ação antes de disponibilizar aceite, descarte e execução a todos os perfis.
4. **Documentação de rotas e eventos:** `agrosaas-routing-map.md` e o inventário de eventos não registram o módulo canônico e seus futuros eventos de lifecycle. Atualizá-los na entrega que conectar os fluxos produtivos.
5. **Operação do legado climático:** manter a projeção de compatibilidade somente enquanto consumidores antigos precisarem dela; nenhuma regra nova deve ser inserida no serviço climático legado.

## Próxima implementação incremental recomendada

**OPS-INTELLIGENCE-12 — Ativação produtiva controlada.** Primeiro auditar `core/background_jobs.py`, o modelo de execução por tenant e as políticas RBAC. Depois, em uma única entrega pequena:

1. registrar a job no scheduler existente;
2. executar providers por tenant/unidade com idempotência, lote e telemetria;
3. adicionar testes de RLS, dedupe, falha isolada e não execução automática;
4. publicar os eventos de lifecycle somente após definir o contrato no inventário;
5. executar `git diff --check`.

O subscriber Event/Outbox deve ser uma etapa posterior e separada, para não misturar regras de agenda com fan-out de eventos.
