# AUDIT-FIX-04.12 — Discovery Estoque UI

Este documento compila o diagnóstico e mapeamento arquitetural do módulo de Estoque, o primeiro "Colosso Operacional" analisado para migração RSC.

## 1. Estrutura da Página Atual
- **Arquivo:** `apps/web/src/app/(dashboard)/suprimentos/estoque/page.tsx`
- **Tamanho:** 1651 linhas de código — extrema densidade e acoplamento.
- **Tabs/Abas:** Posição (Saldos), Reservas, Histórico (Movimentações), Produtos, Depósitos.
- **Componentes Acoplados (In-file):**
  - Diversos diálogos: `EstoqueEntradaDialog`, `EstoqueSaidaDialog`, `EstoqueTransferenciaDialog`, `EstoqueAjusteDialog`, `NovoProdutoDialog`, `NovoDepositoDialog`, `NovaReservaDialog`.
  - Múltiplas instâncias de `DataTable` e filtragens manuais via estado (com `useState`).

## 2. Dados Consumidos (Endpoints Identificados)
O componente varre simultaneamente uma vasta quantidade de endpoints, gerando um imenso *Waterfall* no Client:
- `GET /estoque/saldos`
- `GET /estoque/alertas`
- `GET /cadastros/produtos`
- `GET /estoque/depositos`
- `GET /estoque/reservas`
- `GET /estoque/movimentacoes`
- `GET /safras`

Todos (exceto produtos globais) fortemente dependentes do estado global `activeFazendaId`.

## 3. Estados Críticos & Mutações
- **Mutações Operacionais (Risco Ledger):** Entrada, Saída, Transferência e Ajuste.
- **Mutações de Bloqueio (Reservas):** Criar Reserva, Consumir Reserva (gera saída), Cancelar Reserva (libera saldo).
- **Mutações Cadastrais:** Criar Produto, Criar Depósito.
- **Invalidação de Cache:** A função `invalidateAll()` é invocada massivamente para forçar o recálculo dos saldos ao longo das tabs após qualquer mutação.

## 4. Riscos de Migração Identificados
Devido à natureza *Mission-Critical* do Estoque, os riscos de uma refatoração brusca incluem:
- **Quebra do Ledger Financeiro:** Modificar formulários de Entrada/Saída para _Server Actions_ de forma precipitada pode causar dupla submissão em redes lentas, inflacionando o saldo da fazenda.
- **Vazamento de Escopo (Cross-Tenant/Fazenda):** Todas as queries baseiam-se em `activeFazendaId`. O Server Component precisa resolver esse parâmetro corretamente para não hidratar a tabela com saldos de outra unidade produtiva.
- **Perda de Estado Complexo:** Mover o controle de Abas (`Tabs`) para a URL pode ser lento; manter no Client State local previne repinturas totais durante trocas de aba.

## 5. Estratégia de Decomposição (Arquitetura Alvo)
A solução requer um fatiamento agressivo para evitar um Client Component de 1600 linhas.
- **`page.tsx` (RSC Shell):** Componente servidor enxuto.
- **`EstoqueClient.tsx` (Root Client Component):** Casca que gerencia as abas ativas, filtros globais e o `invalidateAll()`.
- **Subcomponentes (`/components/estoque/`):**
  - `SaldosTab.tsx`, `ReservasTab.tsx`, `HistoricoTab.tsx`
  - Formulários/Modais externalizados: `MovimentacaoForms.tsx` (Entrada, Saída, Transferência, Ajuste).

## 6. Dados que Podem Vir do Server (`apiFetchServer`)
- Saldos (`/estoque/saldos`)
- Movimentações Iniciais (limite 200)
- Produtos e Depósitos base para selects
*(Garantindo o uso de `Promise.allSettled` para permitir carregamento mesmo com falhas parciais de RBAC).*

## 7. Dados que Devem Permanecer Client-Side
- Mutações (useMutation e form submit) para preservar validações locais (Zod).
- Busca paginada/filtros na aba de Histórico.
- Gerenciamento dinâmico de safras se a filtragem for alterada pelo usuário.

## 8. Plano de Migração Gradual
Recomenda-se fatiar a refatoração do Estoque nas seguintes ondas independentes:

- **AUDIT-FIX-04.13:** Decomposição visual. Extrair modais, abas e diálogos para arquivos `.tsx` separados dentro de uma sub-pasta, ainda renderizados sob o `page.tsx` original com `use client`. **Objetivo:** Reduzir para < 300 linhas o arquivo raiz sem mudar fluxo de dados.
- **AUDIT-FIX-04.14:** Conversão RSC. O `page.tsx` (agora limpo) vira Server Component (`apiFetchServer` + `initialData`) e o `EstoqueClient` assume a interatividade restante.
- **AUDIT-FIX-04.15:** Otimização de Performance e Infinite Scroll/Paginamento real nas tabelas de histórico que podem estourar com os anos.
