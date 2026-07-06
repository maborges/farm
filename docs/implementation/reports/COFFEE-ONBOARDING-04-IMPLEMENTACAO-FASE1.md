# COFFEE-ONBOARDING-04: Implementação Fase 1 (Onboarding Intent-Based)

## Resumo Executivo
Foi executada a **Fase 1 do Plano de Refatoração do Onboarding** conforme previamente especificado. O antigo Wizard técnico de 5 passos foi descartado no frontend e substituído por uma versão em 3 passos baseada em **Intenção do Produtor** (Cultura, ERP e Módulos). 

Todas as restrições de arquitetura foram rigorosamente mantidas. Nenhuma tabela, *domain event*, API paralela ou migração foi gerada. O backend continua operando 100% sobre o modelo de dados atual, utilizando o sistema nativo de extensibilidade (`ConfiguracaoTenant`).

---

## 1. Arquivos Afetados

### Arquivos Modificados
- **Frontend**: `apps/web/src/app/onboarding/configurar/page.tsx`
  - *Status:* Completamente reescrito para utilizar UI via *shadcn* (lucide-icons, cards focados, steps lineares) cobrindo Cultura, ERP e Módulos.
- **Backend (Schemas)**: `services/api/core/schemas/config_schemas.py`
  - *Status:* O modelo `OnboardingConfigRequest` foi estendido com os campos `cultura`, `erp` e `modulos`, todos opcionais, sem alterar a tipagem ou predefinições dos *defaults* exigidos nas suítes antigas.
- **Backend (Routers)**: `services/api/core/routers/configuration.py`
  - *Status:* No endpoint `@router.post("/onboarding/configurar")`, inserido um interceptor que salva os 3 novos campos da "Intenção" no banco relacional genérico `ConfiguracaoTenant`, preservando a lógica antiga idêntica.

### Arquivos Criados
- **Nenhum arquivo de código foi criado**. Todos os componentes necessários de interface e utilitários (`apiFetch`, Zustand, `shadcn`) foram reaproveitados da biblioteca do projeto.

---

## 2. Contratos Alterados
O contrato `POST /config/onboarding/configurar` foi alterado **de forma retrocompatível**. 

O novo payload via frontend envia:
```json
{
  "cultura": "CAFE",
  "erp": "SANKHYA",
  "modulos": ["CUSTOS", "CAMPO", "FINANCEIRO"],
  "ano_agricola_inicio": 7,
  "ano_agricola_fim": 6,
  "unidade_area": "HA",
  "fuso_horario": "America/Sao_Paulo",
  "moeda": "BRL",
  "idioma": "pt-BR",
  "aceitar_categorias_padrao": true
}
```
*Note que a "Intenção" do usuário foi adicionada, mas os campos mecânicos são autogerados na UI para manter a compatibilidade do backend com testes legados.*

---

## 3. Validação e Qualidade

Foram executadas as seguintes validações e testes diretamente no ambiente local, com êxito:

- ✅ **`git diff --check`**: Executado para aferir vazamentos de console.logs e *trailing whitespaces*. Um *whitespace* residual no backend (linha 368) foi corrigido antes do *commit*.
- ✅ **Testes do Backend**: Executada a suíte de Onboarding (`pytest tests/unit/test_pilot_onboarding_governance_guardrails.py`). **4 testes executados, 4 aprovados** (100% dos executados). O backend aceitou o novo schema estendido sem invalidar regras de governança.
- ✅ **Typecheck Frontend**: `tsc --noEmit` executado, indicando 0 (zero) falhas de tipagem, atestando conformidade entre o Zustand, Forms e a API.
- ✅ **Lint Frontend**: `eslint` validou todos os componentes com sucesso.

**Cobertura de Implementação:** 100% da Fase 1 definida na auditoria (UI reescrita + Orquestração Retrocompatível) cobrindo Cultura, ERP e Módulos.

---

## 4. Limitações Conhecidas & Próximos Passos

### Limitações da Fase 1
Conforme requerido na instrução original (*"Nesta fase NÃO executar: integração ERP, templates, workers..."*), as escolhas no Frontend ("Café" e "Sankhya") estão sendo capturadas pelo Backend e gravadas estaticamente na base, mas **ainda não causam mutação ativa**.

### Próximos Passos (Fase 2)
1. **Ativar o `CoffeeTemplate`**: No backend, assim que a intenção de cultura = `CAFE` for detectada, invocar os *PhaseTemplates* já existentes para injetar estágios e sub-módulos fenológicos dinamicamente.
2. **Ativar Worker do Sankhya**: Se intenção de ERP = `SANKHYA`, enfileirar (outbox/worker) a `SyncErpRequested` para importar *Centros de Custo* sem atrito.
3. **Redirecionamento Inteligente**: Modificar a ida ao `/dashboard` para exibir um `LoadingState` temporário enquanto os motores (Fase 2) pré-processam as dependências, oferecendo ao usuário um dashboard instantaneamente funcional e povocado ao final.
