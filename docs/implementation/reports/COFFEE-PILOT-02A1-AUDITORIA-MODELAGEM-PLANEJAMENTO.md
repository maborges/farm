# COFFEE-PILOT-02A.1 — Auditoria Arquitetural do Planejamento Operacional

**Data:** 06 de Julho de 2026
**Objetivo:** Determinar a modelagem arquitetural correta para incorporar o planejamento logístico ao AgroSaaS sem violar o isolamento do planejamento agronômico, sem criar tabelas novas e reaproveitando a fundação existente.

---

## 1. Respostas Diretas à Auditoria

**1. SafraTarefa deve continuar sendo exclusivamente agronômica?**
**Sim.** A `SafraTarefa` representa a *intenção* (ex: necessidade de 20kg/ha de Nitrogênio na fase de Vegetação). Misturar recursos logísticos (tratores, marcas de insumos) nela violaria o *Bounded Context* agronômico, acoplando decisões técnicas a disponibilidades de armazém.

**2. Produto previsto pertence à SafraTarefa ou a uma estrutura intermediária?**
Não pertence à `SafraTarefa`. O produto comercial (que movimenta estoque e tem custo financeiro real) pertence à camada de alocação logística (Ordem de Execução).

**3. Máquina prevista pertence à SafraTarefa?**
Não. Máquinas são ativos de frota geridos logisticamente.

**4. Operador previsto pertence à SafraTarefa?**
Não. Operadores são recursos de RH com disponibilidades de turno, independentes do agrônomo.

**5. É correto criar SafraTarefaInsumo?**
**Não.** Criar essa estrutura forçaria o agrônomo a agir como almoxarife, transformando a intenção agronômica em um controle de estoque prematuro e ferindo a arquitetura.

**6. Já existe alguma entidade que represente um plano operacional reutilizável?**
**Sim.** A entidade oficial `OperacaoAgricola` já conta com atributos logísticos pesados (`maquina_id`, `operador_id`, lista de `insumos` amarrada a `produto_id` e a possibilidade de assumir `status="PLANEJADA"`).

**7. É possível reutilizar Ordens de Serviço em modo "Planejado"?**
A tabela/entidade `OrdemServico` não existe ativamente na arquitetura de banco de dados do AgroSaaS (há apenas código morto residual em `/agricola/services`). Portanto, não há o que reutilizar dessa nomenclatura.

**8. É possível reutilizar OperacaoAgricola sem execução?**
**Sim.** O schema e o banco de dados permitem que a `OperacaoAgricola` nasça com o status modificado para "PLANEJADA" com uma `data_prevista`. O único percalço atual é a obrigatoriedade do campo `data_realizada` no banco de dados (`nullable=False`), exigindo que, no modo de planejamento, uma data temporária seja preenchida (geralmente espelhando a prevista) até que o apontamento real via Campo PWA aconteça.

**9. Existe outra entidade que já resolva esse problema?**
Não.

**10. Qual modelagem preserva melhor a arquitetura do AgroSaaS?**
Elevar a **`OperacaoAgricola`** ao papel oficial de Ordem de Serviço/Plano Logístico.

---

## 2. Recomendação Única de Arquitetura

A arquitetura correta do AgroSaaS para o Planejamento Operacional é um fluxo de **2 Camadas (Agronômico -> Logístico):**

1. **Camada Agronômica (Intenção):** Utilizar `SafraTarefa`. O agrônomo recomenda "Pulverização de Defensivo, Dose X, no Talhão Y".
2. **Camada Logística (Ordem de Serviço):** A partir da `SafraTarefa`, o gestor de operações gera uma **`OperacaoAgricola` com `status="PLANEJADA"`**.
   - É aqui que a `OperacaoAgricola` incorpora o `maquina_id` correto, o `operador_id` da escala, e os `InsumoOperacao` apontando exatamente para os `produto_id` do estoque.
3. **Camada de Execução (Apontamento):** O tratorista visualiza a `OperacaoAgricola` no **Campo PWA**. Após aplicar, ele ajusta as quantidades reais de insumo consumido e muda o status da própria `OperacaoAgricola` para `REALIZADA` (disparando finalmente a baixa no Estoque Sankhya via Outbox).

### Vantagens desta abordagem (ZERO tabelas novas):
- **Preserva Modelos Atuais:** Reaproveita 100% da `OperacaoAgricola` e seus `InsumosOperacao` já desenhados.
- **Mantém o Desacoplamento:** O agrônomo e o almoxarifado não interferem nas tabelas uns dos outros.
- **Integração Nativa:** Como os relatórios do PWA e módulos financeiros/Sankhya já escutam a `OperacaoAgricola`, bastará filtrar por status (`PLANEJADA` para previsões e empenhos de estoque, `REALIZADA` para debito final e custo realizado).
