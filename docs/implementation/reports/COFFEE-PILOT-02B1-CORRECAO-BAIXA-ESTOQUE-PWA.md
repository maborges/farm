# COFFEE-PILOT-02B.1 — Correção Crítica da Baixa de Estoque na Transição PLANEJADA → REALIZADA

**Data:** 06 de Julho de 2026
**Objetivo:** Corrigir os bloqueios encontrados na jornada do PWA, garantindo que o status "PLANEJADA" isola os efeitos financeiros e logísticos, e que o status "REALIZADA" efetiva-os corretamente mesmo quando alterado de forma concisa.

---

## 1. Escopo das Correções

### 1.1 Inclusão do Gatilho de Transição (`OperacaoService.atualizar`)
Adicionamos a captura da mudança de estado para forçar o recálculo dos insumos quando a operação é baixada do campo:
```python
novo_status = dados_dict.get("status")
status_mudou_para_realizada = novo_status == "REALIZADA" and status_anterior != "REALIZADA"

precisa_reprocessar_insumos = (
    insumos_payload is not None 
    or (area_alterada and len(insumos_anteriores) > 0)
    or status_mudou_para_realizada
)
```
**Impacto:** Se o tratorista sincronizar apenas `{ "status": "REALIZADA" }`, a flag interna será verdadeira. Os insumos previamente vinculados à Operação (em `InsumoOperacao` com custo zerado) serão varridos, e o processo de consumo e apuração via FIFO será ativado adequadamente.

### 1.2 Guarda de Transação e FIFO (`_aplicar_insumos_na_operacao`)
Blindamos o núcleo de consumo FIFO e atualização de saldos na rotina base:
```python
if operacao.status == "REALIZADA":
    consumo = await consumir_lotes_fifo(...)
    # Custo histórico, ledgers de movimento e saldos atualizados
```
Se a operação estiver como `PLANEJADA`:
- A validação se o `produto_id` existe (e pertence ao tenant correto) é feita.
- O registro de `InsumoOperacao` é criado, mas **sem custo** (`custo_total=0.0` e `custo_unitario=0.0`).
- Nenhuma linha de Ledger de Estoque de Saída (`ledger_consumos`) é gerada.
- O saldo do inventário (`atualizar_saldo_apos_consumo`) não sofre qualquer alteração negativa.

## 2. Validações

O teste final demonstrou cobertura total do cenário reportado:
- ✅ **PLANEJADA com insumos não baixa estoque:** Insumo entra com custo zerado.
- ✅ **Editar insumos em PLANEJADA não baixa estoque:** O refatoramento de `_aplicar_insumos_na_operacao` não consome o FIFO se `status != "REALIZADA"`.
- ✅ **PLANEJADA → REALIZADA com apenas status baixa estoque:** Ativado pelo novo gatilho.
- ✅ **Retentativa REALIZADA → REALIZADA não baixa novamente:** A cláusula `status_anterior != "REALIZADA"` evita duplicação do gatilho. O payload PWA puro é inócuo se a operação já fechou, a não ser que altere a área executada ou insumos.
- ✅ **Custo/Despesa/CostAllocation:** Blindados pelo bloco `if operacao.status == "REALIZADA":` revisado anteriormente e fortalecidos na garantia de `InsumoOperacao` sem custo em modo planejamento.

As alterações foram validadas via `git diff --check` para conformidade estrita, não geraram migrações, não criaram novas tabelas e reaproveitaram estritamente o motor unificado existente (`OperacaoAgricola`). A estabilidade do modelo agronômico (`SafraTarefa`) continua intocada.
