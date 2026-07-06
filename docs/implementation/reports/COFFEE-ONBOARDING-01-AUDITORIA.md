# COFFEE-ONBOARDING-01: Auditoria do Fluxo Atual

## 1. Auditoria da Arquitetura Base

### Backend
- **Tenant:** EXISTE E ATENDE. Isolamento consolidado.
- **Billing:** EXISTE E ATENDE.
- **Owner/Admin:** EXISTE E ATENDE.
- **Onboarding (Rotas base):** EXISTE PARCIALMENTE (a rota atual `POST /config/onboarding/configurar` recebe campos mecânicos em vez de intenções).
- **Wizard:** EXISTE PARCIALMENTE (Motor de pendências e checklist existe, mas falta o setup inicial baseado em intenção).
- **UnidadeProdutiva:** EXISTE E ATENDE.
- **Safra:** EXISTE E ATENDE.
- **Cultura:** EXISTE E ATENDE.
- **Templates (PhaseTemplates):** EXISTE E ATENDE.
- **Recommendation Engine:** EXISTE E ATENDE.
- **Alert Engine:** EXISTE E ATENDE.
- **Notification Engine:** EXISTE E ATENDE.
- **Integração ERP (Sankhya):** EXISTE E ATENDE (Gateway-first pronto para sync).
- **Associação Oficial:** EXISTE E ATENDE.
- **Scheduler:** EXISTE E ATENDE.
- **Campo PWA:** EXISTE E ATENDE.

### Frontend
- **Páginas de Onboarding:** EXISTE PARCIALMENTE (`configurar/page.tsx` focado em setup técnico).
- **Componentes:** EXISTE E ATENDE (shadcn/ui, Selects, Cards já disponíveis).
- **Formulários e Validações:** EXISTE E ATENDE (Zod + RHF padrão).
- **Estados (Zustand):** EXISTE E ATENDE.
- **Navegação e Feedback:** EXISTE E ATENDE.

---

## 2. Análise Crítica do Fluxo Atual

O fluxo atual pergunta: *Ano Agrícola, Unidade de Área, Fuso Horário, Moeda e Categorias Padrão.*

Para **cada** uma destas perguntas, aplicamos o checklist:

### A. Ano Agrícola
1. Precisa responder? **NÃO**
2. O sistema já sabe? Não inicialmente.
3. O navegador sabe? Não.
4. O ERP sabe? **SIM** (via integração).
5. O Template sabe? **SIM** (Template de Café define Julho a Junho).
6. Inferível? **SIM**.
7. Preenchível depois? Não, mas pode assumir default seguro.
8. Escondível em config? **SIM**.

### B. Unidade de Área
1. Precisa responder? **NÃO**
2. O sistema já sabe? Não.
3. O navegador sabe? Não.
4. O ERP sabe? **SIM** (Traz a unidade base, geralmente Hectare).
5. O Template sabe? Não.
6. Inferível? **SIM** (Hectare é padrão Brasil).
7. Preenchível depois? **SIM**.
8. Escondível em config? **SIM**.

### C. Fuso Horário e Moeda
1. Precisa responder? **NÃO**
2. O sistema já sabe? Não.
3. O navegador sabe? **SIM** (Fuso via Intl API).
4. O ERP sabe? **SIM** (Moeda base).
5. O Template sabe? Não.
6. Inferível? **SIM**.
7. Preenchível depois? **SIM**.
8. Escondível em config? **SIM**.

### D. Categorias Padrão
1. Precisa responder? **NÃO** (Deveria ser implícito).
2. O sistema já sabe? **SIM** (Plano de contas base existe).
3. O navegador sabe? Não.
4. O ERP sabe? **SIM** (Plano de Contas Sankhya substitui o padrão).
5. O Template sabe? **SIM** (Categorias otimizadas para café).
6. Inferível? **SIM**.
7. Preenchível depois? Não, mas assume-se SIM automático.
8. Escondível em config? **SIM**.

## 3. Resumo da Auditoria

O fluxo atual falha na experiência por tentar forçar um "Setup de ERP Clássico". 
O produtor quer gerenciar a safra, e o sistema pergunta sobre *timezone*. 

**Reaproveitamento:** Toda a camada de banco de dados, motor de templates, integração com Sankhya e sistema de alertas será **100% reaproveitada**.

**Extensão:** Apenas a rota de recepção do onboarding no backend será **estendida** para aceitar um payload de intenção (`cultura`, `erp`, `modulos`) e orquestrar a chamada aos serviços (já existentes) que criam os templates e engatilham o sync do ERP.

**Criação Nova:** Somente a **Interface (Frontend) do novo Wizard** (3 passos baseados em intenção) precisará ser criada, substituindo o componente atual.
