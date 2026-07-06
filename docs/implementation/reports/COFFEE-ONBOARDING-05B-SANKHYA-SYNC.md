# COFFEE-ONBOARDING-05B — Sincronização Sankhya no Onboarding

**Data:** 06 de Julho de 2026  
**Status:** Concluído com Sucesso

## 1. Resumo Executivo
Foi concluída a implementação da etapa 05B, que integra o Onboarding de novos clientes (Tenant) diretamente ao sistema ERP Sankhya através de um mecanismo assíncrono. O disparo é efetuado quando o Wizard envia a intenção com `erp = "SANKHYA"`, mantendo todas as diretrizes de governança e reuso de infraestrutura estipuladas.

## 2. Abordagem (Event-Driven e Idempotente)
Com a adoção do padrão EDA (Event-Driven Architecture) via *Outbox Pattern*, a sincronização atende plenamente ao requisito de disparar processos longos (como integração ERP) sem onerar ou bloquear a resposta do Onboarding ao cliente.

- **Evento `IntegrationSyncRequested`**: Criado o evento no domínio genérico de integrações (`integracoes.events`).
- **Idempotência**: Durante o cadastro do evento no banco (função `publish_domain_event_safe`), foi definida uma chave fixa atrelada ao `tenant_id` (`sankhya_initial_sync_<tenant_id>`), evitando a criação de múltiplos jobs em retentativas ou cliques duplos do Wizard.

## 3. Worker e Subscriber (`SankhyaSyncEventSubscriber`)
- Um novo Event Subscriber (`integracoes.sankhya.subscribers.SankhyaSyncEventSubscriber`) foi acoplado à arquitetura de eventos do projeto (`@register_event_subscriber`).
- Responsabilidade OBRIGATÓRIA: Não cria novos domínios ou serviços próprios. Reutiliza estritamente `SankhyaSyncService`, `SankhyaPessoaService` e `SankhyaProdutoService` que já possuíam a governança correta (via `TenantIntegracao` e `ExternalRecordAssociation`).
- **Tolerância a falhas**: O próprio `DomainEventOutboxRelay` garante *retries* controlados com *backoff* exponencial caso ocorra um erro pontual na API do ERP ou na gravação do Log.

## 4. Onboarding (`configuration.py`)
No término do onboarding, a lógica implementa o seguinte fluxo:
1. Detecta `erp == "SANKHYA"`.
2. Avalia a persistência da configuração da integração.
3. Existindo a configuração: despacha via evento (`features=["pessoas", "produtos"]`).
4. Não existindo a configuração: marca status `sankhya_status = PENDENTE` no `ConfiguracaoTenant`, abrindo porta para a UX direcionar o usuário à página de configuração Sankhya posteriormente.

## 5. Diretrizes e Regras Seguidas
- **Não criar serviço novo**: `[✓] ATENDIDO` (Apenas uma classe Subscriber baseada na infra).
- **Não criar tabela/migration**: `[✓] ATENDIDO`.
- **Reutilizar infra outbox/worker**: `[✓] ATENDIDO`.
- **Idempotência do Job Inicial**: `[✓] ATENDIDO` (Garantida pelo Outbox idempotency_key).
- **Não chamar alert/recommendation engine**: `[✓] ATENDIDO`.

**Próximos Passos:** Validar a Fase 2 de governança e mapeamento do Calendário Agrícola, em convergência aos `OperationTemplates` do Onboarding.
