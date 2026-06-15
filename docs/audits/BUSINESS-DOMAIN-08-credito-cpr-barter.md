# Auditoria de Arquitetura – BUSINESS‑DOMAIN‑08 – Crédito, CPR e Barter Multicultura

> **Objetivo**: Avaliar o estado atual do código‑fonte e da documentação relativas ao domínio de Crédito, CPR e Barter, identificar lacunas, riscos e propor direções de evolução arquitetural.

---

## 1. Visão Geral do Domínio

O domínio **Crédito, CPR e Barter** tem como objetivo permitir que produtores rurais recebam linhas de crédito, realizem **CPR (Cédula de Produto Rural)** e façam operações de **Barter** (troca de insumos por produção).  Ele interage com os módulos já existentes de **Financeiro**, **Contratos**, **Estoque**, **CRM** e **Parcerias**.

### Principais Conceitos de Negócio
- **Limite de Crédito** – valor máximo que o produtor pode movimentar em uma operação de crédito.
- **Adiantamento** – liberação antecipada de recursos ao produtor, normalmente vinculada a um contrato.
- **Barter** – acordo de troca de insumos (ex.: fertilizantes) por produtos colhidos.
- **CPR Física** – título físico que representa a entrega futura de commodity.
- **CPR Financeira** – título que representa a obrigação financeira de pagamento futuro.
- **Exposição Comercial** – risco da empresa frente ao volume de crédito concedido.
- **Garantia/Colateral** – ativos que asseguram o pagamento do crédito.
- **Vínculo com Contrato** – relacionamento entre crédito/CPR e o contrato de fornecimento.
- **Vínculo com Estoque** – integração entre crédito/CPR e o módulo de estoque para controle de garantias.

---

## 2. Inventário de Existência (Matriz Final)

| Feature | Status | Evidência (arquivo / classe / endpoint) | Observação |
|---|---|---|---|
| **Limite de Crédito** | NÃO EXISTE NO CÓDIGO | – | Não há modelo, serviço ou documento encontrado. |
| **Adiantamento** | NÃO EXISTE NO CÓDIGO | – | Nenhum modelo, service ou rota encontrada. |
| **Barter** | NÃO EXISTE NO CÓDIGO | – | Não há documentação nem código‑fonte. |
| **CPR Física** | NÃO EXISTE NO CÓDIGO | – | Não há arquivos nem rotas. |
| **CPR Financeira** | NÃO EXISTE NO CÓDIGO | – | Não há arquivos nem rotas. |
| **Exposição Comercial** | NÃO EXISTE NO CÓDIGO | – | Não encontrado `services/api/financeiro/services/exposure_service.py`. |
| **Garantia/Colateral** | NÃO EXISTE NO CÓDIGO | – | Não há modelos nem serviços. |
| **Vínculo com Contrato** | NÃO EXISTE NO CÓDIGO | – | Nenhum código ou documento encontrado. |
| **Vínculo com Estoque** | EXISTE NO CÓDIGO | Modelo `services/api/estoque/models/commodity.py` (uso de commodity) – porém **sem integração** com crédito/CPR. | Integração pendente. |

---

## Validação de Evidências e Anti‑Duplicação

### Evidências Verificadas
| Caminho | Tipo | Existe? | Trecho/Conceito Encontrado |
|---|---|---|---|
| `docs/financeiro/limite-credito.md` | documento | Não | – |
| `docs/barter/barter-overview.md` | documento | Não | – |
| `docs/contratos/vinculo-credito-contrato.md` | documento | Não | – |
| `services/api/estoque/models/commodity.py` | modelo | Sim | Classe `Commodity` representando itens de estoque. |

### Matriz Anti‑Duplicação
| Entidade proposta | Domínio dono provável | Já existe equivalente? | Deve ser nova entidade? | Pode ser extensão? | Observação |
|---|---|---|---|---|---|
| CreditLimit | Crédito | Não | Sim | – | Necessário para controle de limites de crédito. |
| CreditExposure | Crédito | Não | Sim | – | Calcula exposição comercial. |
| AdvancePayment | Crédito | Não | Sim | – | Representa adiantamentos. |
| CommodityPurchaseRight | CPR | Não | Sim | – | Direito de compra de commodity futura. |
| BarterAgreement | Barter | Não | Sim | – | Formaliza troca de insumos por produção. |
| BarterItem | Barter | Não | Sim | – | Item individual em acordo de barter. |
| Collateral | Crédito | Não | Sim | – | Garantia associada a crédito. |
| Guarantee | Crédito | Não | Sim | – | Similar a Collateral, pode ser tratado conjuntamente. |
| RiskPolicy | Crédito | Não | Sim | – | Política de risco para limites e exposições. |

---

## 3. Riscos e Lacunas Identificadas

| Risco | Probabilidade | Impacto | Mitigação Proposta |
|---|---|---|---|
| **Ausência de modelo de limite de crédito** – o cálculo de risco de crédito não tem base de dados. | Alta | Impede concessão de crédito, gera risco de exposição não controlada. | Definir modelo `CreditLimit` e serviço de cálculo; iniciar com design conceitual. |
| **Nenhum endpoint de adiantamento** – fluxo de liberação impossível. | Média | Falha ao atender necessidade de fluxo de caixa dos produtores. | Planejar API `POST /credit/advance` e service associado. |
| **Barter sem implementação** – acordo de troca não pode ser operacionalizado. | Média | Perda de oportunidade comercial. | Criar modelo `BarterAgreement` e rotas básicas de CRUD. |
| **CPR (física/financeira) inexistente** – incapacidade de emitir títulos rurais. | Alta | Não atende requisitos regulatórios e de mercado. | Projetar entidades `PhysicalCpr` e `FinancialCpr` com integração ao estoque e contabilidade. |
| **Exposição Comercial não monitorada** – risco de crédito descontrolado. | Alta | Possível incorrência de perdas financeiras. | Implementar serviço de cálculo de exposição usando limites e contratos existentes. |
| **Garantia/Colateral ausente** – falta de segurança para crédito. | Média | Aumento da vulnerabilidade a inadimplência. | Definir modelo `Collateral` e relacioná‑lo ao crédito. |
| **Vínculo com Contrato apenas documental** – ausência de verificações automáticas. | Média | Dados inconsistentes entre módulos de contrato e crédito. | Implementar serviço de validação de vínculo e eventos de sincronização. |
| **Integração estoque‑crédito inexistente** – estoque não usado como garantia. | Alta | Perda de controle de ativos que poderiam servir como colateral. | Criar camada de integração que consuma `Commodity` como garantia. |

---

## 4. Recomendações de Evolução Arquitetural

1. **Definir um *Domain Model* centralizado** – criar um pacote `services/api/credito/models/` contendo as entidades acima (CreditLimit, Advance, BarterAgreement, PhysicalCpr, FinancialCpr, Collateral, Exposure).
2. **Camada de Serviços** – `services/api/credito/services/` responsável por regras de negócio, validações de crédito, cálculo de exposição e gerenciamento de garantias.
3. **API Layer** – rotas REST em `services/api/credito/routers/` seguindo a convenção existente (padrão `router = APIRouter()`), utilizando **TanStack Query** no frontend para consumo.
4. **Integração com Estoque** – criar um *domain event* que, ao registrar um crédito, verifique disponibilidade de commodity e registre a garantia.
5. **Documentação e Contratos** – manter arquivos Swagger/OpenAPI atualizados e gerar esquemas **Zod** compartilhados (`packages/zod-schemas/credito/`).
6. **Segurança** – aplicar as regras do *mandatory‑secure‑web‑skills* nos novos endpoints (validação de entrada, controle de acesso, prevenção de injeção).
7. **Roadmap de Implementação** – priorizar: (a) modelo de limite de crédito, (b) serviço de exposição, (c) vínculo contrato‑crédito, (d) integração estoque‑garantia, (e) Barter, (f) CPR.

---

## 5. Próximos Passos (Curto Prazo)

- Consolidar a **matriz de inventário** em um artefato CSV para rastreamento.
- Elaborar *design de domínio* (UML) detalhando relacionamentos entre as novas entidades e os módulos existentes.
- Agendar revisões de segurança para cada serviço antes de sua implementação (uso do plugin **securecoder**).
- Atualizar o **README** do repositório com a nova seção “Crédito, CPR e Barter”.

---

*Este documento foi gerado em conformidade com as regras de linguagem (pt‑br) e das políticas de auditoria definidas nas regras de negócio.*
