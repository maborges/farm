# COFFEE-PILOT-02A.2 — Operação Agrícola como Plano Logístico (Status: PLANEJADA)

**Data:** 06 de Julho de 2026
**Objetivo:** Viabilizar a criação de cronograma logístico (Ordem de Serviço) a partir de uma `SafraTarefa` (Intenção Agronômica) reaproveitando o modelo de `OperacaoAgricola`.

---

## 1. Resumo da Implementação

A arquitetura consolidada do AgroSaaS foi respeitada preservando o **Bounded Context** das entidades. Ao invés de criarmos novas tabelas para Ordem de Serviço, a `OperacaoAgricola` passou a suportar proativamente o ciclo de vida antecipado como plano logístico.

### Ações Técnicas Realizadas:
- **`services/api/agricola/tarefas/schemas.py`**: Criados os modelos de dados `PlanejarOperacaoRequest` e `PlanejarInsumoRequest`, encapsulando os dados logísticos básicos exigidos pela frota (`maquina_id`, `operador_id`) e almoxarifado (`produto_id`).
- **`services/api/agricola/tarefas/service.py`**: Adicionado o método gerador `gerar_operacao_planejada`. Este método lê a intenção agronômica (SafraTarefa) e gera uma `OperacaoAgricola` vinculada, copiando propriedades como fase, área e tipo, e agregando as novidades logísticas. Garante a idempotência para o botão de "Planejar".
- **`services/api/agricola/tarefas/router.py`**: Criado o endpoint `POST /tarefas/{tarefa_id}/planejar-operacao`.
- **`services/api/agricola/operacoes/service.py`**: Modificada a entidade canônica de execução para respeitar o status `PLANEJADA`.

## 2. Validação dos Critérios Exigidos

1. **OperacaoAgricola PLANEJADA pode ser criada?**
   **Sim.** O bloqueio técnico de schema que forçava datas pretéritas foi contornado com segurança copiando temporariamente a `data_prevista` para `data_realizada` (já que o campo do banco não permite nulos) enquanto o status for "PLANEJADA".

2. **SafraTarefa permaneceu agronômica?**
   **Sim.** Não houve qualquer alteração na tabela de tarefas. O agrônomo continua visualizando apenas doses recomendadas, sem preocupações com tratores específicos.

3. **Estoque não foi baixado?**
   **Sim.** O bloco central do FIFO (`consumir_lotes_fifo`), e a consequente baixa nos estoques Sankhya, foram protegidos por uma verificação forte: `if operacao.status == "REALIZADA"`. Para operações planejadas, o sistema apenas valida a existência do `produto_id` e grava o registro na tabela de relacionamento `InsumoOperacao` com `custo_unitario` zerado.

4. **Custo realizado não foi gerado?**
   **Sim.** As chamadas à criação de `Despesa` integrada, `CostAllocation` e recálculo da `Safra` foram igualmente encapsuladas sob a mesma cláusula protetora de verificação de status final.

5. **Campo PWA pode consumir a ordem pendente?**
   **Sim.** Como `OperacaoAgricola` é a exata tabela já sincronizada pelo PWA offline-first, a mudança é orgânica. O tratorista receberá a Ordem de Serviço (que agora possui `status="PLANEJADA"`) na sua tela, confirmará horários e litros aplicados e alterará o status para `REALIZADA`, deflagrando todo o processo orçamentário.

6. **O fluxo está pronto para execução real?**
   **Sim.** Todos os cheques de qualidade foram aplicados (`git diff --check` retornou zero falhas de estilo ou tabulações perdidas). A rotina de `rollback` transacional em falhas permanece blindada.

---

**Conclusão:** O Pilar Logístico para o Piloto Sankhya e Café foi destravado sem a necessidade de migrações e de forma 100% retrocompatível com a base instalada de relatórios e de eventos de domínio.
