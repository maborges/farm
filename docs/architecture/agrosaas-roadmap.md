# AGROSAAS ROADMAP

Roadmap oficial extraído do estado da base de código (routers, models e integrações mapeadas).

## CLASSIFICAÇÕES
* **IMPLEMENTADO**: Código existente em produção e rotas ativas.
* **EM DESENVOLVIMENTO**: Rotas criadas, integração pendente ou comentadas temporariamente.
* **PLANEJADO**: Listado no domínio mas sem código consolidado de back/front.
* **FUTURO**: Conceitual.
* **DESCARTADO**: Abandonado.

---

## AGRUPAMENTO DE MÓDULOS

### 1. Core SaaS (Backoffice, Billing, Auth)
- **Status**: IMPLEMENTADO
- **Prioridade**: Alta | **Impacto**: Alto | **Complexidade**: Alta
- Componentes: RBAC, Tenants, Autenticação JWT, Planos de Assinatura.

### 2. Agrícola & Agricultura de Precisão
- **Status**: IMPLEMENTADO
- **Prioridade**: Alta | **Impacto**: Alto | **Complexidade**: Alta
- Componentes: Safras, Cultivos, Talhões, Operações, Amostragem Solo (VRA), NDVI.

### 3. Pecuária
- **Status**: IMPLEMENTADO
- **Prioridade**: Média | **Impacto**: Alto | **Complexidade**: Média
- Componentes: Lotes, Manejos.

### 4. Financeiro & Hedge
- **Status**: IMPLEMENTADO
- **Prioridade**: Alta | **Impacto**: Alto | **Complexidade**: Alta
- Componentes: Despesas, Receitas, Conciliação, NFe, Comercializações, Contratos de Hedge.

### 5. Estoque & Compras
- **Status**: IMPLEMENTADO
- **Prioridade**: Alta | **Impacto**: Alto | **Complexidade**: Média
- Componentes: Movimentos, Cadastro Oficial de Insumos/Produtos.

### 6. Frota & Oficina
- **Status**: IMPLEMENTADO
- **Prioridade**: Alta | **Impacto**: Médio | **Complexidade**: Média
- Componentes: Abastecimento, Checklists, Apontamentos.

### 7. CRM
- **Status**: IMPLEMENTADO
- **Prioridade**: Média | **Impacto**: Médio | **Complexidade**: Média
- Componentes: Gestão de Ofertas e pipeline base.

### 8. RH
- **Status**: IMPLEMENTADO
- **Prioridade**: Média | **Impacto**: Médio | **Complexidade**: Média
- Componentes: Colaboradores, Acessos básicos.

### 9. IA & Diagnóstico
- **Status**: IMPLEMENTADO
- **Prioridade**: Alta | **Impacto**: Alto | **Complexidade**: Alta
- Componentes: Identificação de Pragas e Tratamentos via IA, Auditoria IA no Backoffice.

### 10. Integrações / IoT
- **Status**: IMPLEMENTADO / EM DESENVOLVIMENTO
- **Prioridade**: Média | **Impacto**: Alto | **Complexidade**: Alta
- Componentes: John Deere, Case IH, New Holland (Ativos). SAP/Contabilidade (EM DESENVOLVIMENTO - Comentados no repo aguardando refatoração).

### 11. Ambiental & Rastreabilidade
- **Status**: IMPLEMENTADO
- **Prioridade**: Média | **Impacto**: Médio | **Complexidade**: Média
- Componentes: Gestão ambiental e emissão de lote rastreável.

### 12. Marketplace / B2B
- **Status**: PLANEJADO / FUTURO
- **Prioridade**: Baixa | **Impacto**: Alto | **Complexidade**: Alta
- Componentes: (Ausentes na API atual de forma nativa além da conexão B2B básica).
