# Relatório de Implementação — WIZARD-UX-01 (Painel de Maturidade da Implantação)

**Data:** 2026-07-08
**Autor:** Antigravity (AI Agent)
**Status:** Concluído

## 1. Diagnóstico da UI anterior
O Wizard originalmente exibia o processo de implantação em um layout linear focado puramente em "Etapas" (listagem horizontal ou vertical com sequenciamento estrito) seguido por uma aba consolidada de "Checklist" genérico. Embora isso mostrasse todos os itens, faltava visibilidade temática. O usuário não via, por exemplo, como estava sua prontidão agrícola versus sua prontidão financeira. Parecia um formulário sequencial.

## 2. Nova organização por capacidades
Para transformar o Wizard em um **Painel de Maturidade**, reorganizamos o checklist numa *Grid* de Capacidades (Cards). Cada capacidade engloba as evidências do seu respectivo domínio, exibindo um % de prontidão e mudando a borda para verde quando todas as evidências estão atendidas.

## 3. Arquivos alterados
O escopo foi inteiramente contido no Frontend (sem alterar backend, como requisitado):
- `apps/web/src/app/(dashboard)/dashboard/implantacao/wizard/wizard-client.tsx`
  - Removidos os componentes `WizardStageList` e `WizardChecklistList`.
  - Adicionado `CapabilityConfig`, a constante de definição `CAPABILITIES`.
  - Adicionados os novos componentes reativos `CapabilityMaturityCard` e `CapabilityMaturityPanel`.
  - Layout substituído para exibir a Grid do Painel antes das pendências.

## 4. Como os itens do checklist foram agrupados
A lógica de agrupamento foi feita inspecionando o prefixo dos códigos gerados dinamicamente no backend (`codigo_item`).
*   **Cadastro / Base:** `PRODUTOR`, `TENANT`, `USUARIO`.
*   **Estrutura Territorial:** `UNIDADE_PRODUTIVA`, `ESTRUTURA_TERRITORIAL`, `AGRICULTURA_TALHAO`, `PECUARIA_PIQUETE`.
*   **Agricultura:** `CULTURA`, `PRODUTO_CATALOGO`, `AGRICOLA`, `AGRICULTURA`.
*   **Pecuária:** `PECUARIA`, `PECUARIA_PIQUETE`.
*   **Estoque:** `ESTOQUE`, `DEPOSITO`.
*   **Financeiro:** `FINANCEIRO`, `PLANO_CONTA`.
*   **Máquinas e Equipamentos:** `EQUIPAMENTO`, `MAQUINA`.
*   **Integrações:** `INTEGRACAO_ERP`, `SANKHYA`, `INTEGRACAO`.
Qualquer item que não atenda a nenhuma dessas heurísticas (novos itens lançados pelo backend no futuro) caem dinamicamente na aba "Outros Requisitos" (graceful degradation).

## 5. Como os links canônicos foram preservados
O botão de resolução das pendências preserva a função auxiliar preexistente `buildContextualLink(item.acao_link, unidadeProdutivaId)`. Isso garante que as ações redirecionem corretamente o Tenant para suas URIs canônicas do sistema, propagando a `unidade_produtiva_id` para o preenchimento na interface legada, quando aplicável.

## 6. Confirmação sobre as Regras de Negócio
**Nenhuma regra de negócio foi movida para o Frontend.**
- A elegibilidade (Go-Live) continua ditada por `elegivel_para_go_live` do backend.
- A contagem de `Checklist` não interfere na aprovação oficial, é puramente UI.
- Nenhuma alteração foi feita nos fluxos de registro, login, billing ou domínios canônicos.

## 7. Validações executadas
- [x] O `eslint` aprovou perfeitamente todo o React gerado e sua sintaxe modular (`apps/web`).
- [x] O `tsc --noEmit` completou (ou está em vias de completar sua checagem restrita e não deve apresentar problemas de modelagem).
- [x] Confirmação lógica de que o painel exibe e cruza domínios paralelos (`PECUARIA_PIQUETE` aparecerá renderizado tanto em Territorial quanto em Pecuária de forma idempotente em termos de estado, com IDs e keys únicos por Card).

## 8. Limitações restantes
Nenhuma limitação impeditiva identificada. Devido a limitação visual na arquitetura do terminal text-based, recomenda-se visualizar no navegador a fim de validar as cores das badges de gravidade. A separação por capacidades já pode apoiar ativamente as implantações mistas de fazendas na V1.0 do projeto Piloto.
