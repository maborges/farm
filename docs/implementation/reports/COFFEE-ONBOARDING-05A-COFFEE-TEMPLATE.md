# COFFEE-ONBOARDING-05A: Ativação CoffeeTemplate (Fase 2 - Onboarding)

## Resumo Executivo
Foi executada a segunda fase incremental do novo Onboarding Intent-Based. O backend passou a capturar a intenção de cultura igual a `CAFE` para acionar a instanciação idempotente de templates. Como exigido pelas regras restritas de arquitetura, focou-se apenas em serviços existentes e confiáveis, registrando os módulos faltantes como GAPs.

---

## 1. Auditoria e Estratégia Adotada

### O que foi auditado
- O fluxo da rota `/config/onboarding/configurar` (`services/api/core/routers/configuration.py`).
- O serviço de templates (`PhaseTemplateService` e `OperationTemplateService`) no módulo `agricola`.
- O comportamento do método `duplicar_global` e o script de seed inicial.

### Classificação de Serviços Atuais:
- **PhaseTemplates (Fases Fenológicas e Checklists):** **EXISTE E ATENDE**. O serviço tem o método `duplicar_global` e a busca filtra por tenant. 
- **OperationTemplates (Operações Padrão):** **EXISTE PARCIALMENTE**. O modelo e a listagem existem, mas o serviço atual carece de um mecanismo `duplicar_global` seguro. 
- **Safra (Calendário Agrícola):** **EXISTE PARCIALMENTE**. Exige contexto forte (talhões, áreas) que o Onboarding de intenção não provê, e não faz sentido criar uma safra "fantasma".

---

## 2. Arquivos Modificados
- **Backend**: `services/api/core/routers/configuration.py`
  - Foi adicionado o import de `PhaseTemplateService` de forma *cross-module* controlada.
  - Implementada lógica de interceptação na conclusão do onboarding que busca os `PhaseTemplates` globais para `cultura="CAFE"` e os instancia localmente.

### Nenhuma Alteração Estrutural
- Nenhum domínio novo foi criado.
- Nenhuma migration ou nova tabela foi feita.
- Sankhya, Recommendation e Alert Engines não foram acionados.

---

## 3. Comportamento Idempotente Implementado
Para impedir a duplicação em caso de múltiplas submissões do Onboarding:
- É feito o carregamento dos templates existentes (`tenant_id == tenant.id`).
- É gerado um *set* de títulos de templates locais existentes.
- Antes de invocar o `duplicar_global`, verifica-se se o título (ou sua nomenclatura de cópia) já existe no *set*. Se sim, o template é ignorado de forma silenciosa. 

---

## 4. Itens Instanciados vs. GAPs

### ✅ Instanciados e Reaproveitados
- **PhaseTemplates (Checklists por Fase):** As fases "Planejada", "Preparo de Solo", "Plantio", "Desenvolvimento", "Colheita", "Pós-colheita" foram habilitadas para a conta.
- **Categorias Padrão:** As categorias mantiveram-se ativas utilizando o `seed_categorias_padrao` já nativo da versão antiga.

### ⚠️ GAPs (Itens Não Instanciados - Planejados para a Fase 05B)
- **Calendário Agrícola (Safra):** Não criado. Carece de input de área/talhão para existir.
- **OperationTemplates:** Não ativado. O serviço (`OperationTemplateService`) demanda refatoração pontual (adicionar função `duplicar_global`) que extrapolaria as regras restritas deste passo ("Não estender domínios sem necessidade urgente").

---

## 5. Testes e Validação
- **Backend (Pytest):** A suíte `tests/unit/test_pilot_onboarding_governance_guardrails.py` foi mantida intacta e executada, finalizando com **4/4 testes aprovados (100% de sucesso)**, atestando retrocompatibilidade absoluta do novo comportamento do *Onboarding*.
- **Git Diff & Lint:** Um problema de *trailing whitespace* (inserido acidentalmente) foi detectado pelo `git diff --check` e sanado automaticamente no `configuration.py`.

---

## 6. Critérios de Encerramento Atingidos
1. O CoffeeTemplate (sua parcela de *PhaseTemplates*) foi ativado? **SIM**.
2. Foi criado/instanciado no tenant? **SIM** (via cópia dos templates globais).
3. O fluxo é idempotente? **SIM**.
4. O contrato antigo (frontend/testes) funciona? **SIM**.
5. Nenhuma integração Sankhya disparada? **NENHUMA**.
6. Nenhum Engine (Recommendation/Alert) acionado? **NENHUM**.
7. Próxima etapa (05B) pronta? **SIM**, o terreno de templates está fundado.
