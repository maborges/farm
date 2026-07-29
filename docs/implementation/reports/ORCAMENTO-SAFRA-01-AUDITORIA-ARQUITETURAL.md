# ORCAMENTO-SAFRA-01 — Auditoria Arquitetural do Orçamento de Safra

**Data da auditoria:** 29/07/2026  
**Escopo:** leitura do código existente no workspace. Nenhuma regra de negócio foi alterada nesta auditoria.

## 1. Resumo executivo

O AgroSaaS já possui os blocos fundamentais para controlar o custo agrícola: `Safra`, itens de orçamento por safra, planejamento operacional, tarefas, operações executadas e `CostAllocation`. O maior ponto positivo é que o **realizado** tem uma fonte econômica central: a apropriação de custos por `ProductionUnit` em `CostAllocation`, consumida tanto pelo resumo de custos quanto pela DRE Agrícola v1.

Porém, o **orçamento** ainda é uma coleção mutável de `ItemOrcamentoSafra`, sem entidade-cabeçalho, sem versão, sem revisão formal, sem status de aprovação e sem vínculo explícito com fase, tarefa ou item do planejamento operacional. Assim, ele atende a um orçamento básico e itemizado, mas não preserva a linha de base necessária para gestão de uma safra de médio ou grande porte.

O planejamento operacional possui snapshots próprios de insumos, mão de obra e maquinário e atualiza `SafraTarefa.custo_estimado`; isso é adequado como detalhamento operacional, mas não está ligado formalmente a uma versão de orçamento. Há, portanto, risco de o planejamento passar a ser tratado como um segundo orçamento e de diferentes telas compararem o realizado contra valores previstos distintos.

**Veredicto:** **NO-GO** para considerar o modelo atual como orçamento estratégico versionado de safra.  
**Uso possível hoje:** **GO COM RESSALVAS** para orçamento estático, itemizado e sem histórico de revisão.

## 2. Estado atual

### 2.1 Orçamento de safra

Existe a tabela/modelo `agricola_orcamento_itens` / `ItemOrcamentoSafra`. Cada linha pertence diretamente a `safra_id`, podendo opcionalmente apontar para `cultivo_id` e `production_unit_id`. Possui categoria, quantidade, unidade, custo unitário e custo total.

Há snapshot do custo de origem no momento da criação do item: produto, máquina, pessoa ou serviço. A precedência do custo é ajuste manual, snapshot e custo legado. Isso preserva a referência de preço daquela **linha** enquanto ela existe.

Não existe no modelo uma entidade `OrcamentoSafra` persistida como cabeçalho. O objeto com esse nome presente em schemas/README é uma resposta agregada/documentação, não um agregado versionável no banco.

### 2.2 Planejamento operacional

`PlanoOperacional` agrupa tarefas de uma safra e registra seu estado operacional. Ele possui o campo `versao`, mas não há relação de versão anterior/próxima, mecanismo de clonagem, endpoint de revisão ou imutabilidade de versão aprovada.

O plano detalha insumos, mão de obra e maquinário por tarefa, com snapshots de disponibilidade e custos estimados. Ele reaproveita `SnapshotCustoService` para consultar os cadastros mestres, o que evita duplicar a lógica de captura de preço. Ao aplicar receita/operações no plano, o serviço atualiza `SafraTarefa.custo_estimado` com a soma de insumos e mão de obra planejados.

### 2.3 Execução e realizado

`SafraTarefa` suporta fase, talhão, quantidade e `custo_estimado`. A geração logística cria `OperacaoAgricola`; quando realizada, a operação possui `OperacaoExecucao` e gera/sincroniza `CostAllocation` quando há contexto econômico suficiente.

`CostAllocation` é o registro oficial de apropriação: identifica unidade produtiva, origem, categoria, valor, data e bases de rateio. Também recebe projeções de rateios financeiros (`FIN_RATEIO`). A DRE Agrícola v1 consolida custos a partir dele e evita duplicar despesas que já estejam representadas pela camada econômica superior.

### 2.4 Painéis e relatórios

O resumo de custos por safra usa `CostAllocation` para realizado e soma `ItemOrcamentoSafra.custo_total` para previsto; se não houver itens, usa `Safra.custo_previsto_ha` como fallback. A tela de orçamento consome a mesma resposta de orçamento previsto × realizado.

A DRE Agrícola v1 é deliberadamente realizada: usa receitas operacionais/comercialização e custos de `CostAllocation`; orçamento não é componente da DRE. Esse é o comportamento correto para evitar transformar previsão em resultado contábil/econômico realizado.

## 3. Evidências encontradas

| Área | Evidência no código | Papel atual |
|---|---|---|
| Orçamento | `services/api/agricola/a1_planejamento/models.py` — `ItemOrcamentoSafra` | Previsão itemizada diretamente na safra; sem cabeçalho ou versão. |
| Criação e alteração do orçamento | `services/api/agricola/a1_planejamento/service.py` — `criar_item`, `atualizar_item`, `deletar_item` | CRUD mutável, com `commit`; exclusão física do item. |
| Snapshot de custo | `services/api/agricola/a1_planejamento/snapshot_service.py` | Captura produto, máquina, pessoa e serviço para o item orçado. |
| Comparativo da safra | `services/api/agricola/a1_planejamento/service.py` — `get_orcamento` | Previsto por itens (ou fallback) e realizado por `CostAllocation`. |
| Planejamento operacional | `services/api/agricola/planejamento_operacional/models.py` | Plano, tarefas, insumos, mão de obra e maquinário planejados. |
| Refinamento operacional | `services/api/agricola/planejamento_operacional/service.py` | Snapshots e estimativas por tarefa; atualiza `SafraTarefa.custo_estimado`. |
| Fases | `services/api/agricola/safras/models.py` e `agricola/tarefas/models.py` | Safra tem ciclo/fase; tarefa tem `fase`; item de orçamento não tem fase. |
| Operação e execução | `services/api/agricola/operacoes/models.py` e `agricola/tarefas/service.py` | Tarefa gera operação; operação realizada tem execução e custo realizado. |
| Motor econômico | `services/api/agricola/custos/models.py`, `allocation_service.py` | `CostAllocation` centraliza apropriação por unidade produtiva. |
| Custos/Dashboard | `services/api/agricola/custos/service.py` e `apps/web/src/app/(dashboard)/dashboard/agricola/custos/CustosClient.tsx` | Realizado por allocation; previsto por itens, com fallback. |
| DRE | `services/api/agricola/dre/service.py` | Consolida realizado e aplica precedência para não duplicar fontes. |
| Rotas | `services/api/agricola/a1_planejamento/router.py` e `planejamento_operacional/router.py` | Há CRUD de itens e planos, mas não rota de revisão/versionamento de orçamento. |

### Responsabilidades atuais identificadas

| Pergunta | Responsável atual |
|---|---|
| Quem cria/altera orçamento? | `PlanejamentoService.criar_item` e `atualizar_item`; a interface chama as rotas de itens. |
| Quem calcula previsto? | `PlanejamentoService.get_orcamento` e `CustosService.get_resumo_safra`, pela soma de itens; ambos podem usar fallback de custo/ha. |
| Quem calcula realizado? | Fluxos operacionais/financeiros registram `CostAllocation`; serviços de custos e DRE o consolidam. |
| Quem alimenta Dashboard? | `CustosService` para custos; DRE Agrícola v1 para DRE e indicadores derivados. |
| Quem alimenta DRE? | `DREAgricolaV1Service`, com `CostAllocation` como fonte oficial de custos. |

## 4. Respostas às perguntas obrigatórias

1. **Existe um orçamento geral da safra?** Existe uma soma geral de itens vinculados à safra, mas não um agregado persistido de orçamento com identidade, status e linha de base.
2. **Existe orçamento por fase?** Não. `ItemOrcamentoSafra` não possui `fase`; somente tarefas e operações possuem contexto de fase.
3. **Existe duplicidade entre orçamento e planejamento?** Sim, potencial. Ambos armazenam quantidades e custos previstos, sem vínculo de origem, reconciliação ou hierarquia formal.
4. **Existe duplicidade entre planejamento e realizado?** O desenho de execução é apropriado — planejamento gera operação e o realizado vem de `CostAllocation` —, mas campos como `SafraTarefa.custo_estimado` e `OperacaoAgricola.custo_total` exigem disciplina para não serem apresentados como realizado antes da apropriação.
5. **O orçamento pode ser revisado?** Pode ser editado ou excluído tecnicamente por CRUD, mas não há revisão de negócio preservada.
6. **Existe histórico?** Há `created_at`/`updated_at` no item, mas não histórico de versões, autor da alteração, justificativa, valores anteriores ou exclusão lógica.
7. **Existe versionamento?** Não para orçamento. O campo `PlanoOperacional.versao` isolado não implementa versionamento de plano nem de orçamento.
8. **Existe snapshot?** Sim, por item de orçamento e por componentes do plano operacional. É snapshot de custo/referência, não snapshot completo e imutável de uma versão orçamentária.
9. **Existe risco de perder o orçamento original?** Sim. Atualização sobrescreve a linha e exclusão a remove fisicamente.
10. **O Dashboard utiliza qual valor?** O resumo de custos utiliza `CostAllocation` para realizado e a soma de `ItemOrcamentoSafra` para previsto; na ausência dos itens utiliza `Safra.custo_previsto_ha` como fallback.
11. **A DRE utiliza qual valor?** A DRE Agrícola v1 utiliza receitas e custos realizados; para custos, `CostAllocation`. Não utiliza orçamento, como deve ser.
12. **Como comparar previsto e realizado?** Hoje: soma atual dos itens versus soma de allocations, por safra e categoria. Não há comparação nativa entre inicial, revisão atual e realizado; fase/talhão/centro de custo não estão integralmente suportados no orçamento.
13. **Existem lacunas arquiteturais?** Sim: agregado de orçamento, versões/revisões, imutabilidade, aprovação, justificativa, vínculo com fase/plano/tarefa, regras de prevalência do previsto e visão comparativa multidimensional.
14. **Quais entidades devem ser reutilizadas?** `Safra`, `Cultivo`, `SafraTalhao`, `ProductionUnit`, `SafraTarefa`, `SafraTarefaNecessidade`, `PlanoOperacional`, seus itens planejados, `OperacaoAgricola`, `OperacaoExecucao`, `CostAllocation`, cadastros de produto/equipamento/pessoa/serviço e `Rateio`.
15. **Quais novas entidades realmente seriam necessárias?** Um agregado versionável de orçamento e suas versões/itens revisionados; uma ligação rastreável entre item orçamentário e detalhamento operacional. Não é necessária nova entidade de custo realizado.
16. **Existe acoplamento inadequado?** Sim, o plano operacional atualiza diretamente `SafraTarefa.custo_estimado`, mas não referencia uma versão orçamentária. Também há uso de custos/ha em `Safra`/`Cultivo` como fallback paralelo ao orçamento itemizado.
17. **Existe cálculo duplicado?** Sim, previsto é calculado pela soma de itens e também pode vir de `custo_previsto_ha`; há custos estimados em itens, tarefas e plano operacional. O realizado está melhor centralizado em `CostAllocation`.
18. **Existe risco de divergência financeira?** Sim, sobretudo se dashboards misturarem fallback de custo/ha, itens atuais e estimativas operacionais. A DRE reduz o risco para o realizado ao aplicar precedência sobre `CostAllocation`.
19. **O modelo suporta múltiplas revisões?** Não de forma auditável. Apenas alterações sucessivas no mesmo registro.
20. **O modelo atende produtor rural de médio e grande porte?** Não integralmente para governança orçamentária. Atende parte operacional e de apropriação real, mas não orçamento versionado, rastreável e comparável exigido nesse porte.

## 5. Lacunas arquiteturais

1. **Ausência de raiz do agregado:** itens não pertencem a uma versão de orçamento, somente à safra.
2. **Ausência de linha de base imutável:** não existe conceito de “Orçamento Inicial” aprovado.
3. **Revisão é edição, não evento:** não há motivo, responsável, data de revisão, relação com versão anterior nem diferenças registradas.
4. **Sem orçamento por fase:** a classificação por categoria não permite responder quanto foi inicialmente previsto, revisado e realizado em cada fase.
5. **Sem rastreabilidade de refinamento:** um insumo/tarefa do plano não aponta para a linha do orçamento que detalha, substitui ou amplia.
6. **Dimensões incompletas:** o item pode ter cultivo e unidade produtiva, mas não talhão explícito, fase, centro de custo, rateio planejado ou chave de origem do detalhamento.
7. **Sem regra única de previsto:** itens de orçamento, custo/ha de safra/cultivo e custos estimados de tarefas podem coexistir como respostas distintas para “qual é o previsto?”.
8. **Sem comparação inicial × atual:** o comparativo atual é somente orçamento vigente (mutável) × realizado.

## 6. Riscos

| Risco | Impacto | Severidade |
|---|---|---|
| Revisão sobrescrever orçamento original | Perda de base de decisão e de auditoria | Alta |
| Exclusão física de item | Impossibilidade de explicar desvios históricos | Alta |
| Plano tratado como segundo orçamento | Totais previstos conflitantes por tela/módulo | Alta |
| Fallback de custo/ha | Painel pode comparar realizado contra previsão não estruturada | Alta |
| Ausência de vínculo por fase/talhão | Desvio operacional não localizável no ciclo produtivo | Média/Alta |
| Snapshot de linha sem versão global | Não é possível reproduzir o orçamento completo em uma data | Alta |
| Estimativas misturadas ao realizado | Risco de interpretação financeira incorreta | Média |
| Custo sem allocation | DRE já alerta esse caso, mas há risco operacional até a correção | Média |

## 7. Modelo recomendado

Adotar a referência abaixo, mantendo o realizado no motor econômico atual:

```text
Safra
  └── OrcamentoSafra (agregado lógico; um orçamento estratégico por safra)
        ├── OrcamentoSafraVersao 1 — INICIAL, aprovada e imutável
        │     └── Itens por categoria, fase/dimensão e snapshots
        ├── OrcamentoSafraVersao 2 — REVISÃO
        │     └── Itens completos copiados/alterados, motivo e responsável
        └── OrcamentoSafraVersao N — REVISÃO

PlanoOperacional / SafraTarefa
  └── detalha e referencia item/versão orçamentária aplicável
        └── OperacaoAgricola → OperacaoExecucao → CostAllocation
                                              └── Dashboard e DRE (realizado)
```

### Entidades propostas

1. **`OrcamentoSafra`**: cabeçalho por `tenant_id` + `safra_id`, status e versão atual. Deve impedir dois orçamentos estratégicos ativos para a mesma safra, salvo regra explícita de cenários.
2. **`OrcamentoSafraVersao`**: número, tipo (`INICIAL`/`REVISAO`), status (`RASCUNHO`/`APROVADA`/`SUPERADA`), origem/versão anterior, data, criador, aprovador, motivo e observação.
3. **Itens versionados**: evoluir `ItemOrcamentoSafra` para pertencer a uma versão, ou criar item novo revisionado e migrar gradualmente. Deve preservar quantidade, valor, snapshots, categoria e dimensões.
4. **Vínculo de refinamento**: referência opcional do item de plano/tarefa ao item orçamentário da versão em vigor; permitir informar se é detalhamento, substituição ou acréscimo. Não deve copiar custo realizado.

### Dimensões mínimas do item orçamentário

Além de categoria e origem: `fase`, `cultivo_id`, `talhao_id` quando aplicável, `production_unit_id`, centro de custo quando o domínio estiver disponível, unidade, quantidade, valor unitário, total e snapshot de origem.

### Regras de negócio recomendadas

- A primeira versão aprovada é a referência **Inicial** e nunca pode ser alterada.
- Revisar significa criar nova versão a partir da anterior, com diferença auditável; não editar a versão aprovada.
- A versão aprovada mais recente é o **Planejado Atual**.
- O plano operacional pode criar/refinar necessidades, mas não muda o orçamento. Divergências devem gerar proposta de revisão ou variação explícita.
- O realizado continua vindo exclusivamente de `CostAllocation`; nem orçamento nem plano devem produzir total realizado por cálculo próprio.
- Dashboard deve expor: Inicial, Atual, Realizado, Desvio contra Inicial, Desvio contra Atual e percentual, sempre com a mesma granularidade disponível no escopo.
- DRE deve permanecer exclusivamente realizada. Orçamento pode aparecer em análise gerencial adjacente, nunca como lançamento da DRE.

## 8. Compatibilidade com a arquitetura existente

O modelo recomendado é compatível com a arquitetura atual porque reutiliza o encadeamento operacional e econômico já existente:

- `Safra` continua sendo o contexto superior.
- `PlanoOperacional` e `SafraTarefa` continuam sendo planejamento/refinamento, não motor de realizado.
- `OperacaoAgricola` e `OperacaoExecucao` continuam representando execução.
- `CostAllocation` continua sendo a única projeção econômica do realizado.
- `DREAgricolaV1Service` permanece somente leitura e não precisa receber novo cálculo de custos.

O ajuste principal é dar governança ao previsto e definir formalmente sua precedência. O snapshot já existente deve ser reaproveitado como parte dos itens versionados, não substituído por outro motor de captura de custos.

## 9. Impactos

| Camada | Impacto esperado na evolução futura |
|---|---|
| Dados | Introduzir cabeçalho/versões ou migrar itens para relação versionada; preservar itens existentes como versão inicial de transição. |
| Serviços | Separar comandos de rascunho, aprovação e revisão; tornar versões aprovadas imutáveis. |
| Planejamento operacional | Adicionar rastreabilidade ao orçamento e relatório de variação, sem recalcular realizado. |
| Custos/Dashboard | Padronizar a leitura de previsto na versão aprovada atual e expor inicial/atual/realizado. |
| DRE | Sem mudança de fonte econômica; apenas possível referência gerencial externa, sem misturar valores previstos. |
| Relatórios | Adicionar cortes por fase, talhão, categoria e centro de custo conforme a dimensão existir. |
| Migração de dados | Tratar itens atuais por safra como versão inicial, registrando proveniência de migração. |

## 10. Plano sugerido de evolução

1. **Definir contrato de domínio:** consolidar as definições de Inicial, Atual, Revisão, Planejamento Operacional e Realizado, incluindo precedência e estados.
2. **Modelar o agregado versionado:** cabeçalho, versão, itens e trilha de revisão; garantir uma versão inicial aprovada e uma versão atual aprovada por safra.
3. **Migrar sem perda:** converter os itens atuais em versões iniciais de transição, sem apagar snapshots existentes.
4. **Vincular o refinamento:** relacionar itens do plano/tarefa ao orçamento em vigor e registrar variações, sem duplicar `CostAllocation`.
5. **Consolidar leitura gerencial:** criar uma única projeção de previsto para dashboards com Inicial, Atual e Realizado por dimensão.
6. **Endurecer governança:** permissões, aprovação, justificativa obrigatória, trilha de auditoria e bloqueio de edição da versão aprovada.
7. **Cobrir cenários operacionais:** replantio, mudança de área, preço de fertilizante, operação adicional, contratação de terceiros, custo indireto e encerramento de safra.

## 11. Veredicto

### NO-GO

O sistema **não deve** ser considerado pronto para gestão orçamentária estratégica de safra com múltiplas revisões, preservação do orçamento original e comparação auditável Inicial × Atual × Realizado.

Há base sólida e reutilizável para evolução: orçamento itemizado com snapshots, planejamento operacional detalhado e motor econômico oficial por `CostAllocation`. A evolução deve concentrar-se em versionamento e governança do previsto, sem criar um segundo motor de custos nem alterar a DRE para incluir previsões.

## 12. Conformidade desta auditoria

- Nenhum código de aplicação foi alterado.
- Nenhuma migration foi criada ou alterada.
- Nenhuma API foi modificada.
- Nenhuma tela, frontend ou Campo PWA foi alterado.
- A única escrita desta etapa é este relatório.
- As conclusões foram baseadas exclusivamente no código e documentação já existentes no workspace auditado.
