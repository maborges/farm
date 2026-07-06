# COFFEE-ONBOARDING-02: Plano de Refatoração (Intent-Based)

## 1. Visão Geral do Novo Fluxo (Intent-Based)

O onboarding passará de um formulário mecânico para um "Entrevistador Silencioso". A arquitetura não será modificada, mas a *orquestração* dos serviços existentes será mudada.

### Passo 1: "O que você produz?"
- **UI:** Seleção visual de Cultura (Café, Soja, Milho, Pecuária, Outros).
- **Ação em background:** O sistema seleciona o `PhaseTemplate` correto (ex: *CoffeeTemplate*). O template define implicitamente o Ano Agrícola (Jul/Jun) e carrega as Categorias Padrão focadas no café.

### Passo 2: "Como você trabalha hoje?"
- **UI:** Seleção de ERP/Método (Sankhya, TOTVS, Planilhas, Nenhum).
- **Ação em background:** Se "Sankhya" for selecionado, o sistema engatilha a fila de integração (já existente em `Integração ERP Gateway-first`). Não pergunta Fuso Horário, pois importará a parametrização corporativa do Sankhya.

### Passo 3: "O que você deseja controlar?"
- **UI:** Multi-seleção de Módulos (Custos, Financeiro, Campo, etc).
- **Ação em background:** O sistema ativa/desativa os sub-menus dinâmicos no Mega Menu e liga os módulos do *Alert Engine* e *Recommendation Engine* pertinentes ao que foi escolhido.

---

## 2. Orquestração do Backend

Nenhum módulo novo será criado. O `OnboardingService` será modificado para:

1. Receber o payload: `{ cultura: "CAFE", erp: "SANKHYA", modulos: ["CUSTOS", "CAMPO"] }`.
2. **Aplicar Templates:** Chamar o `TemplateService.instantiate_culture_template(tenant_id, "CAFE")`.
3. **Parametrizar Defaults:** Salvar silenciosamente o *Fuso Horário* (via header/navegador) e a *Unidade de Área* (Hectare).
4. **Acionar Integração:** Caso ERP seja Sankhya, postar evento `SyncErpRequested` no Outbox/Message Queue, para que o worker puxe *Fazendas, Talhões e Plano de Contas*.
5. **Finalizar Onboarding:** Marcar Tenant como `READY`.

---

## 3. Classificação de Esforço e Impacto

| O que será feito | Classificação | O que muda |
|------------------|---------------|-------------|
| **Telas Frontend** | **CRIAR** | Substituir `configurar/page.tsx` pela nova UI Intent-based. Nenhuma lógica complexa, apenas UI. |
| **Endpoint API** | **ESTENDER** | Alterar o contrato de `POST /config/onboarding/configurar` para receber a intenção em vez de configs técnicas. |
| **Motor de Templates** | **REAPROVEITAR**| Zero mudanças. Já temos suporte a templates por cultura. Apenas chamá-lo no onboarding. |
| **Integração ERP** | **REAPROVEITAR**| Zero mudanças. O worker do Sankhya já existe e funciona via gateway. |
| **Tabelas de Config** | **REAPROVEITAR**| Zero mudanças nas tabelas. Apenas injetar os valores *default* (HA, BRL). |

## 4. O Resultado Final (Pós-Onboarding)

Ao terminar os 3 cliques, o produtor de café exportador verá:
1. Seu dashboard pré-montado.
2. Seu "Centro de Custos" (Fazendas/Talhões) sendo carregado do Sankhya no fundo.
3. Seus módulos de "Beneficiamento" e "Alertas de Rentabilidade" já ativos.
4. Nenhuma tela vazia.
