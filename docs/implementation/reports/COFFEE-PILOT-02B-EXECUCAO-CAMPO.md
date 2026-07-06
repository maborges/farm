# COFFEE-PILOT-02B — Auditoria da Execução Operacional via Campo PWA

**Data:** 06 de Julho de 2026
**Objetivo:** Validar a resiliência e corretude da jornada de sincronização de uma Operação Agrícola a partir do status `PLANEJADA` (nascida no Backoffice/Web) até sua conclusão como `REALIZADA` via Campo PWA.

---

## 1. Mapeamento do Fluxo e Gatilhos

O fluxo de sincronização do PWA utiliza o endpoint genérico `PATCH /operacoes/{id}` (`OperacaoService.atualizar`).
A jornada teórica segue: PWA envia `{ status: "REALIZADA" }` -> Service atualiza status -> Gatilhos de Custo, Estoque e Sankhya são acionados.

## 2. Respostas da Auditoria

### 1. Todo o fluxo já existe?
**Sim.** A API suporta atualizações parciais (`PATCH`) que o PWA utiliza para sincronizar operações. A camada de integração (Outbox, Financeiro, Caderno de Campo) já se encontra orquestrada ao final do serviço de operações.

### 2. Existe algum bloqueio? (CRÍTICO)
**SIM. Existe um Bloqueio Grave na Baixa de Estoque.**
Quando o PWA sincroniza apenas a mudança de status (`status: "REALIZADA"`), sem enviar explicitamente a lista de `insumos` e sem alterar a `area_aplicada_ha`, a flag interna `precisa_reprocessar_insumos` no `OperacaoService.atualizar` resulta em `False`.
**Consequência:** O método `_aplicar_insumos_na_operacao` não é chamado. A operação se torna `REALIZADA`, mas o estoque físico e contábil (Sankhya) **nunca é baixado** e o custo de FIFO não é apurado para os insumos que haviam sido planejados.
**Outro Bloqueio Relacionado:** Se o produtor simplesmente editar a quantidade de um insumo de uma operação ainda `PLANEJADA` via interface Web, o sistema acionará `_aplicar_insumos_na_operacao` (porque `insumos_payload` não é None), e esse método executa o FIFO incondicionalmente, **baixando o estoque prematuramente**. 

### 3. Existe acoplamento inadequado?
**Sim.** Há uma duplicação perigosa da lógica de consumo FIFO. Ela existe de forma imperativa dentro de `OperacaoService.criar` e de forma apartada dentro de `_aplicar_insumos_na_operacao` (chamada pelo `atualizar`). Isso viola o princípio de responsabilidade única e causou a discrepância citada no bloqueio.

### 4. Existe duplicidade?
**Sim.** Conforme acima, a orquestração de FIFO de insumos está duplicada entre `criar` e `_aplicar_insumos_na_operacao`.

### 5. Existe risco de concorrência offline?
**Baixo/Moderado.** Se múltiplos dispositivos atualizarem a mesma operação simultaneamente, a ausência de um lock pessimista no banco para o ID da operação durante o `atualizar` pode gerar "race conditions". Contudo, as validações de lote (Estoque) possuem garantias transacionais razoáveis.

### 6. Existe risco de sincronização duplicada?
**Mitigado.** O PWA pode retentar a requisição. Contudo, o sistema checa `if novo_status == "REALIZADA" and status_anterior != "REALIZADA":` antes de acionar a criação oficial no Caderno de Campo, protegendo a mensageria de domínios externos de disparos duplos de conclusão.

### 7. Existe risco de baixa dupla no estoque?
**Baixo.** A função `_reverter_movimentos_estoque_operacao` limpa ativamente os movimentos prévios antes de reaplicar os novos insumos em caso de edição de uma operação já realizada. Contudo, é uma operação de estorno pesado. 

### 8. Existe risco de custo duplicado?
**Baixo.** A rotina `_sincronizar_efeitos_operacao` sempre busca a alocação de custo e a despesa financeira já existentes (`_buscar_despesa_existente`), procedendo com `UPDATE` ao invés de `INSERT`.

### 9. Existe risco de evento duplicado?
**Baixo.** O Caderno de Campo (que notifica Recommendation/Alert Engines) e o webhook pro Sankhya só nascem na transição confirmada de status.

### 10. A jornada está pronta para piloto?
**NÃO.** O piloto falhará miseravelmente no aspecto logístico-financeiro. 
Os dois cenários a seguir ocorrerão em campo se a jornada for liberada hoje:
- Edição de Insumo no Plano = Baixa indevida de estoque antes da hora.
- Conclusão da Ordem no Campo (PWA) sem mexer no insumo = Estoque congelado eternamente, safra com rentabilidade superestimada (custo subestimado).

---

## 3. Conclusão e Recomendação
É estritamente necessário realizar um refatoramento focado em `OperacaoService.atualizar` e `_aplicar_insumos_na_operacao` antes de iniciarmos o piloto. 
**Requisitos da Correção (Próxima Fase):**
1. Adicionar o gatilho `novo_status == "REALIZADA" and status_anterior != "REALIZADA"` dentro da avaliação de `precisa_reprocessar_insumos`.
2. Adicionar guarda de segurança `if operacao.status == "REALIZADA":` dentro de `_aplicar_insumos_na_operacao` para impedir que edições durante o status de `PLANEJADA` mexam no estoque.
