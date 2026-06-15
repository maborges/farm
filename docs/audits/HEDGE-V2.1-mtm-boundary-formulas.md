# Auditoria e Fechamento de Escopo: HEDGE-V2.1

## 1. Validação: CotacaoCommodity

O modelo atual de `CotacaoCommodity` foi inventariado e avaliado:
- **Modelo:** `id, commodity_id, data, preco, moeda, fonte, created_at`.
- **Respostas:**
  - *Atende preço de fechamento diário?* Sim, o campo `data` associado a `preco` forma a série temporal do fechamento.
  - *Precisa de campo tipo_cotacao/mercado?* Não para o MVP. A `fonte` resolve o provedor e a associação será manual.
  - *Precisa de campo vencimento?* Idealmente sim para futuros, mas para respeitar a regra de "Não alterar código/banco" no MVP, a precificação pode ser lançada na data de referência desejada no momento do snapshot, ou usar aproximação de mercado Spot como proxy dependendo da necessidade do cliente. Na V2.2, deverá nascer um modelo derivado para Séries de Futuros por Vencimento.
  - *Precisa de campo moeda/unidade?* A `moeda` já consta. A `unidade` decorre da tabela `Commodity`.

## 2. Resoluções Finais e Aprovações

- **Fórmula de MtM Aprovada:** SIM. Sinais opostos para VENDA e COMPRA conforme padrões contábeis e financeiros.
- **Unidade Canônica Aprovada:** SIM. Exigida uniformidade rigorosa via aplicação. Sem conversões complexas on-the-fly.
- **Moeda do MVP Aprovada:** SIM. Mesmo par de moeda (Same Currency MTM). Multi-currency diferido para V2.2.
- **Modelo de Snapshot Aprovado:** SIM. O `HedgePositionSnapshot` detalhado no documento de domínio está homologado para refletir granularidade por *Contrato* e possibilitar idemptotência de recálculo diário.

## 3. Riscos Mapeados

1. **Erros de Escala (Unidade/Moeda):** Risco de distorção absurda do PnL (Multiplicar tonelada vs preço de saca). Resolvido pela trava de segurança na API (Unidade Obrigatória Idêntica).
2. **Duplicidade:** Resolvido com unique constraint no banco (`tenant_id`, `contrato_hedge_id`, `data_referencia`) e operação via UPSERT (Insert on Conflict Update).
3. **Preço Ausente (Feriados):** Risco de Snapshot dar 0. O Job diário precisa puxar a regra D-1 caso `Cotacao` do dia não exista, mantendo o PnL estável no final de semana.

## 4. Conclusão Final

- Fórmula aprovada.
- Unidade canônica aprovada.
- Moeda do MVP aprovada.
- Modelo de snapshot aprovado.

**Parecer Técnico:** A arquitetura lógica não apresenta falhas ou violações. Está enxuta, resiliente para o MVP e aderente ao design do sistema existente.
**Status:** EXECUTION-HEDGE-04 ESTÁ AUTORIZADO.
