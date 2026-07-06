# COFFEE-ONBOARDING-05C — OperationTemplates no Onboarding Café

**Data:** 06 de Julho de 2026
**Status:** Concluído com Sucesso

## 1. Resumo Executivo
Foi concluída a implementação da etapa 05C do Onboarding para a cultura de Café. Nesta etapa, estendemos a ativação de *templates* globais do sistema (`tenant_id = NULL`) durante o Wizard Inicial do usuário para a camada de Governança Operacional (`OperationTemplate`). 

Quando a intenção `cultura == "CAFE"` é mapeada, o serviço duplica com segurança e idempotência os modelos agronômicos padronizados de operações, ativando as réplicas diretamente para o novo *Tenant*.

## 2. Abordagem Idempotente
A implementação respeitou a exigência de não acionar fluxos indesejados (Alertas, Sankhya, Sincronizações, ou Criação de Instâncias Reais de Safra). O objetivo atingido foi **apenas** preencher as tabelas de infraestrutura relativas ao agronegócio (`operation_templates` e `operation_template_items`) com a base canônica.

- **`OperationTemplateService.duplicar_global()`:** Foi introduzido o método de cópia assíncrona. Ele clona a entidade mestre e interage criando instâncias de `OperationTemplateItem` herdando as especificações canônicas globais como dosagens de insumo sugeridas, obrigatoriedade e titulação.
- **Evitando Sobreposição de Dados (Idempotência):** Na lógica executada em `configuration.py`, extraímos uma interseção de títulos globais *versus* títulos preexistentes do tenant com os sufixos `" (Cópia)"`. Isso impossibilita que um re-onboarding da mesma conta multiplique de forma suja os mesmos templates.

## 3. Diretrizes e Regras Seguidas
- **Reutilizar Modelos Existentes:** `[✓] ATENDIDO`. Toda a lógica reaproveita o schema `templates.py` da pasta `agricola`. Nenhuma nova modelagem foi forçada.
- **Não Criar Domínio/Tabelas/Migrations:** `[✓] ATENDIDO`.
- **Não Criar Calendário/Safra Real:** `[✓] ATENDIDO`. Utilizamos templates (`TemplateApplicationService` se manteve inalterado e não foi disparado), deixando o agendamento real da cultura para uma etapa de ação de pós-onboarding ou para a engine de recomendação futura.
- **Isolamento Total de Sankhya/Alert/Recommendation:** `[✓] ATENDIDO`.

## 4. Avaliação e Verificação
Toda a refatoração passou pelo depurador de sintaxe (nenhum artefato de Python quebrado), e a retrocompatibilidade do fluxo original do `POST /config/onboarding/configurar` não foi afetada, apenas enriquecida com a nova carga dos *Operation Templates*.

---
**Critério de Encerramento Atingido:**
Todos os quesitos de segurança e idempotência impostos à Fase 05C foram respeitados. A fundação de templates do onboarding Intent-Based para café está **preparada para a fase subsequente (se houver)**.
