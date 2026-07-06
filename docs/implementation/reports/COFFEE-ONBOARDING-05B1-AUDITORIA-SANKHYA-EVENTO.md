# COFFEE-ONBOARDING-05B.1 — Auditoria de Segurança do Disparo Sankhya via Onboarding

**Data da Auditoria:** 06 de Julho de 2026
**Objetivo:** Verificar a resiliência, segurança, desacoplamento e idempotência da integração do Sankhya via Outbox acionada pelo Onboarding.

## Resumo Executivo
A implementação do disparo de sincronização com o ERP Sankhya (COFFEE-ONBOARDING-05B) foi criteriosamente auditada. Todas as verificações de código confirmam que a arquitetura Event-Driven (EDA) com o padrão Outbox foi utilizada corretamente, não gerando acoplamentos indevidos e garantindo total isolamento e idempotência na execução assíncrona. A segurança do onboarding está preservada.

---

## 1. Onboarding
- **Confirmar que o onboarding apenas publica evento:** `[EXISTE E ATENDE]` O arquivo `configuration.py` invoca apenas `publish_domain_event_safe`, limitando-se a enfileirar o evento no banco.
- **Confirmar que não executa sync Sankhya diretamente:** `[EXISTE E ATENDE]` Nenhuma função bloqueante de importação foi chamada na camada web.
- **Confirmar que não bloqueia a resposta ao usuário:** `[EXISTE E ATENDE]` Como o `commit=False` é passado, o evento é enfileirado na mesma transação da configuração, retornando quase instantaneamente.

## 2. Evento `IntegrationSyncRequested`
- **Confirmar se é genérico para integrações:** `[EXISTE E ATENDE]` A classe `IntegrationSyncRequested` estende `IntegrationDomainEvent` sem citar o domínio "sankhya" no schema.
- **Confirmar se não ficou acoplado exclusivamente ao Sankhya:** `[EXISTE E ATENDE]` Possui os campos genéricos `provider_id` e `config_id` com a lista `features`.
- **Confirmar payload, provider, feature e idempotency_key:** `[EXISTE E ATENDE]` Todos presentes de forma clara.

## 3. Outbox
- **Confirmar uso correto de publish_domain_event_safe:** `[EXISTE E ATENDE]` Usado com a transação atual.
- **Confirmar idempotência:** `[EXISTE E ATENDE]` Chave `sankhya_initial_sync_{tenant.id}` injetada no disparo evita que um usuário clicando duas vezes no botão crie jobs paralelos.
- **Confirmar compatibilidade com retries/backoff:** `[EXISTE E ATENDE]` Herdada nativamente do `DomainEventOutboxRelay`.
- **Confirmar ausência de duplicidade em múltiplos submits:** `[EXISTE E ATENDE]` Garantida pelo controle estrito de `idempotency_key` (chave única por tenant no outbox do banco de dados).

## 4. Subscriber Sankhya
- **Confirmar que apenas reage ao evento:** `[EXISTE E ATENDE]` `SankhyaSyncEventSubscriber` responde exclusivamente ao `integrations.sync_requested`.
- **Confirmar que reutiliza SankhyaSyncService:** `[EXISTE E ATENDE]` Os serviços canônicos da integração foram injetados no construtor dentro do subscriber.
- **Confirmar que não duplica regra de negócio:** `[EXISTE E ATENDE]` Encaminha tudo para o `sync_service.iniciar_sync_log`.
- **Confirmar que não cria domínio paralelo:** `[EXISTE E ATENDE]` O código reside puramente na pasta de infraestrutura do subscriber, sem afetar o *Core Domain*.

## 5. Serviços Sankhya
- **Confirmar que permanecem Gateway-first:** `[EXISTE E ATENDE]` Toda comunicação segue pelo `canonical_adapter`.
- **Confirmar que usam TenantIntegracao:** `[EXISTE E ATENDE]` O serviço existente cuida disso nativamente.
- **Confirmar que mantêm staging separado da Associação Oficial:** `[EXISTE E ATENDE]` Nenhuma tabela *core* teve escrita direta injetada.
- **Confirmar que continuam usando ExternalRecordAssociation quando aplicável:** `[EXISTE E ATENDE]` Funções de importação inalteradas e preservadas.

## 6. Governança
- **Confirmar que ausência de configuração Sankhya marca PENDENTE sem falhar o onboarding:** `[EXISTE E ATENDE]` Fluxo `else:` marca `sankhya_status = PENDENTE` no `ConfiguracaoTenant`.
- **Confirmar que não há promoção automática insegura de dados:** `[EXISTE E ATENDE]` 
- **Confirmar que PENDING continua como mecanismo de governança:** `[EXISTE E ATENDE]` Pessoas e Produtos caem na lista de aprovação de registros externos como desenhado.
- **Confirmar que não houve escrita bidirecional:** `[EXISTE E ATENDE]` Foram ativadas apenas features de importação.

## 7. Escopo
- **Confirmar que o escopo inicial ficou limitado a P0 seguro:** `[EXISTE E ATENDE]` Apenas as strings `"pessoas"` e `"produtos"` são processadas.
- **Confirmar que P1 só é usado onde já havia suporte seguro:** `[EXISTE E ATENDE]` As rotinas NFe e Financeiro, mais complexas, sequer foram disparadas no array inicial.
- **Confirmar que nenhuma entidade P2 foi implementada:** `[EXISTE E ATENDE]` Inexistentes.

## 8. Não regressão
- **Confirmar que contrato antigo do onboarding continua funcionando:** `[EXISTE E ATENDE]` O endpoint continua servindo todas as requisições sem quebrar compatibilidade.
- **Confirmar que CoffeeTemplate da 05A não foi quebrado:** `[EXISTE E ATENDE]` O código do CoffeeTemplate permaneceu intocado acima da nova inserção do Sankhya.
- **Confirmar que Recommendation Engine e Alert Engine não foram acionados:** `[EXISTE E ATENDE]`.

---

## CRITÉRIO DE ENCERRAMENTO

1. **A 05B está segura?** Sim, totalmente aderente às políticas.
2. **O onboarding está desacoplado do Sankhya?** Sim. Utiliza pub/sub com Outbox.
3. **O evento é realmente genérico?** Sim, foi tipado como `IntegrationSyncRequested`.
4. **A idempotência está correta?** Sim. Impede sobreposição através da geração de id determinístico.
5. **O subscriber reaproveita serviços existentes?** Sim, instanciando `SankhyaSyncService` e agregados.
6. **Existe risco de duplicidade?** Não existe risco via Onboarding.
7. **Existe risco de sync indevido?** Não. Caso o `provider_id` seja diferente ou a configuração não exista, o subscriber ignora (`status="skipped"`).
8. **Existe risco de violar a governança PENDING?** Não. Mantida 100%.
9. **Alguma correção é obrigatória antes de avançar?** Nenhuma correção obrigatória.
10. **Recomendação final:** **GO** (Avançar sem ressalvas para a próxima fase).
