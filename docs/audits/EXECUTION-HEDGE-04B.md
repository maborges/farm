# Auditoria e Fechamento: EXECUTION-HEDGE-04B

## Escopo Realizado
A visualização do Mark-to-Market de Hedge foi devidamente implementada com leitura de backend e UI de frontend alinhada à performance do AgroSaaS.

### Componentes Entregues
1. **Endpoint Backend:** Rota `GET /api/v1/financeiro/hedge/snapshots` adicionada ao Router para consumo das posições consolidadas em `HedgeSnapshotService.listar_snapshots`. Conta com limit e offset.
2. **Página Frontend RSC:** Rota Server-Side em `/dashboard/financeiro/hedge/mtm` puxando a primeira carga de dados via `apiFetchServer` sem gerar Layout Shifts.
3. **MtMClient:** Painel com Cards executivos somando o PnL Não Realizado e Quantidade Aberta no client-side a partir do Tanstack.
4. **Data Table:** Uso estrito do nosso `components/ui/data-table.tsx` nativo, formatando moedas e cores de lucro e prejuízo.
5. **Enriquecimento:** Os Snapshots não continham o nome da Safra nem da Commodity. Estes foram enriquecidos dinamicamente no `useMemo` juntando as requests de `/safras` e `/contratos` sem modificar o response model do Backend.
6. **Testes:**
   - E2E Playwright de carregamento da página de MTM.
   - Integração do Backend para filtros de paginação e limit/offset.

## Limitações do MVP Visual
- Não há gráficos de tendências longas na tela de MTM, seguindo o padrão de exibir apenas o último status (D-0 ou anterior válido) dentro do painel.
- O DataTable renderiza as últimas 100 posições ou utiliza busca/ordenação simples local, sem delegar sort dinâmico ao back para manter velocidade de resposta no MVP.

## Riscos Remanescentes
- Nenhuma correção do `HedgePositionSnapshot` pode ser feita via UI. Qualquer erro requer acesso de banco ou refazer cotações e disparar o Job via bash (previsto).

## Recomendação para HEDGE-V2.2
Com o Mark-to-Market estabilizado, o próximo passo natural para amadurecimento (HEDGE-V2.2 ou V3) seria integrar alertas em Background baseados nesses snapshots. Ex: "Safra de Soja com PnL acumulado negativo em -25%, deseja rolar posição?".
Outro ponto seria incluir um Gráfico Multi-Line no próprio `MtMClient`, plotando o histórico de variação da `CotacaoCommodity` vs `preco_contratado` por contrato_futuro_id ao clicar em uma linha da DataTable.
