# PLANNING-LABOR-01 — Auditoria do Modelo de Mão de Obra no Planejamento/Orçamento

**Status:** Auditoria concluída — nenhuma implementação realizada nesta etapa.
**Escopo:** Planejamento, Orçamento, Templates, Tarefas, Operações, Execução, Custos, Dashboard, DRE.
**Motivação:** ambiguidade real encontrada em produção — 3 itens de mão de obra do orçamento da safra "Pimenta do Reino" (`quantidade=38`, `unidade="DIA"`) não permitem saber se representam 1 pessoa por 38 dias, uma equipe por menos dias, ou outra combinação. `observacoes` vazio, sem `origem_id` vinculado a colaborador. O custo bate (`38 × R$150,00 = R$5.700,00`), mas a composição é indeterminável pelo dado armazenado.

---

## 1. O que existe hoje (fatos, não interpretação)

| Camada | Model / Campo | Representação atual |
|---|---|---|
| Orçamento | `ItemOrcamentoSafra.quantidade` + `.unidade` (`agricola/a1_planejamento/models.py`) | Par único `Numeric(14,4)` + `String(20)` livre. Mesmo padrão para SEMENTE, MAO_DE_OBRA, SERVICO, MAQUINA — sem decomposição. |
| Templates | `OperationTemplateItem.dose_sugerida` + `.unidade` (`agricola/models/templates.py`) | Mesmo padrão: campo único + string livre nullable. |
| Tarefas | `SafraTarefaNecessidade.quantidade_tecnica` + `.unidade_referencia` (`agricola/tarefas/models.py`) | Mesmo padrão. |
| Operações | `OperacaoAgricola` (`agricola/operacoes/models.py`) | `operador_id` (FK única), `hora_inicio`/`hora_fim`, `area_aplicada_ha`, `custo_total`, `custo_por_ha`. Sem HH calculado. |
| Execução | `OperacaoExecucao.operador_id` (linha 94) | FK única para `cadastros_pessoas` — **não suporta equipe/múltiplos operadores**. Tem `unidade_medida_id` — FK normalizada (diferente do restante do fluxo). |
| Pessoas/RH | `ColaboradorRH.valor_diaria` + `.valor_hora` (`rh/models.py`, ambos `Float`) | Os dois valores já coexistem no cadastro. Escolha de qual usar no orçamento é feita por heurística de texto na unidade informada (`_capturar_pessoa`, `snapshot_service.py:97-124`) — não por regra de negócio. Não existe cadastro de "Equipe"/"Turma". |
| Frota | `FrotaCustoService` / `FrotaDashboardService._calcular_custo_por_hora` | Custo-hora **derivado dinamicamente**: `custo_total_acumulado / horímetro_atual` — não é um valor cadastrado fixo. Convive com custo-por-km para veículos rodoviários. |
| Custos | `CostAllocation` (`agricola/custos/models.py`) | `cost_category` é `String(32)` livre (default `"OUTROS"`), sem enum. `allocation_basis` é `Numeric` livre, sem unidade declarada no schema. |
| DRE | `dre/service.py::_consolidar_costs()` | Agrega `CostAllocation` só em `custos_diretos`/`custos_operacionais`. **Não existe rubrica "Mão de obra" isolada** — a granularidade se perde antes de chegar à DRE. |
| Produtividade | `Cultivo.produtividade_meta_sc_ha` / `_real_sc_ha` (`agricola/cultivos/models.py`) | Conceito de produtividade **existe, mas só para produção agrícola** (sacas/ha). Nenhum conceito equivalente para mão de obra ou máquina (covas/dia, ha/dia, HH/ha) foi encontrado em nenhum módulo. |
| Unidade de medida | Tabela `unidades_medida` (FK usada em `agricola/operacoes` e `agricola/cenarios`) | **Já existe infraestrutura normalizada de unidade**, mas não é usada no Orçamento, Templates nem Tarefas — esses três continuam com string livre. `pecuaria` usa string livre validada ad-hoc (terceiro padrão). |

**Conclusão do levantamento:** o sistema já tem 3 padrões de unidade coexistindo (FK normalizada em Operações/Cenários; string validada ad-hoc em Pecuária; string livre sem validação em Orçamento/Templates/Tarefas) e nenhum conceito de produtividade operacional (só agronômica). Isso não é specific de mão de obra — é uma fragmentação estrutural que a mão de obra apenas expôs primeiro, por ser o caso mais ambíguo.

---

## 2. Unidade oficial recomendada

**Homem-hora (HH)** como unidade canônica de armazenamento para consumo de mão de obra.

**Justificativa técnica:**
- HH é o único denominador que representa de forma não-ambígua tanto "1 pessoa × N horas" quanto "N pessoas × M horas" — basta multiplicar. "Dia" ou "diária" sozinho, como o bug real mostrou, não permite recuperar a composição.
- `ColaboradorRH` já tem `valor_hora` cadastrado (ao lado de `valor_diaria`) — não é um campo novo, é usar o que já existe como fonte primária de custo, em vez de decidir por heurística de texto.
- Alinha com Máquinas (ver §6) sob a mesma família de unidade (hora), permitindo que Planejamento some/compare custo de mão de obra e máquina na mesma operação sem conversão.
- "Diária" e "dia" continuam válidos **como forma de entrada** (ver §3) — não deixam de existir na UI, só deixam de ser a unidade *armazenada*.

**Não recomendado:** número de pessoas isolado (não captura duração) nem hectare (mistura escala de área com escala de recurso — hectare já existe como dimensão separada em `area_aplicada_ha`).

---

## 3. Produtividade — separada do consumo

Produtividade (ex.: `0,8 ha/dia`, `300 covas/dia`, `5 ha/hora`) **não deve ser armazenada como o registro de consumo**. Recomendação: produtividade é um atributo do **par Operação × Recurso** (não da pessoa, não da equipe isoladamente) — um índice de referência opcional usado para *calcular* a quantidade de HH necessária durante o planejamento, não para substituí-la.

Proposta de local: campo opcional em `OperationTemplateItem` (ex.: `produtividade_referencia` + `unidade_produtividade`, ambos nullable) usado só como calculadora de apoio na UI ("quantas HH preciso para plantar 2,55 ha a 300 covas/dia?"). O valor **persistido continua sendo HH** — produtividade nunca substitui a unidade canônica de consumo, evitando reintroduzir a ambiguidade que originou esta auditoria.

---

## 4. Equipes e conversões de entrada

**Não criar cadastro novo de "Equipe"/"Turma"** agora — isso é um domínio novo e o critério de aceite pede reaproveitamento máximo. Em vez disso: nos pontos onde hoje existe um único campo `quantidade`, adicionar dois campos explícitos e multiplicativos:

- `numero_pessoas` (Integer, default 1)
- `horas_por_dia` ou `dias` (conforme a entrada escolhida pelo usuário)

A UI permite entrada em Homem-dia, Pessoas × Dias, ou Horas — mas o sistema sempre **converte e persiste o produto em HH** (`numero_pessoas × horas × dias`). Isso resolve a pergunta original do usuário ("é homens por dia e por ha?") de forma estrutural: o dado deixa de ser ambíguo porque a composição fica em campos separados, não escondida dentro de uma "quantidade" única.

Conversão interna é responsabilidade do backend (não deixar a ambiguidade para o frontend nem para observações em texto livre).

---

## 5. Impacto no Planejamento

- Formulário de item de orçamento (categoria MAO_DE_OBRA) passa a pedir `numero_pessoas` + duração, com HH calculado e mostrado antes de salvar.
- Templates de operação (`OperationTemplateItem`) seguem o mesmo padrão — a "dose sugerida por ha" de mão de obra passa a ser HH/ha, não "dias/ha" (o que já corrigimos manualmente nesta sessão, mas de forma não estrutural).
- Necessita ajuste de UI no `agro-templates-manager.tsx` e na tela de detalhe de template (`[id]/page.tsx`) recém-criada — os 6 itens de mão de obra/serviço/maquinário lançados nesta sessão para "Plantio - Plano de Ação" ficam com unidade legada (`DIA`, `horas`, `HA`) e precisarão de correção quando este modelo for implementado.

## 6. Impacto na Execução

`OperacaoExecucao.operador_id` é FK única — **não suporta equipe na execução real**. Isso é uma lacuna real, mas resolvê-la (nova tabela associativa `operacao_execucao_operadores`) é escopo maior que esta auditoria. Recomendação: registrar como **gap de fase 2**, não bloquear a normalização de unidade por causa disso. No curto prazo, o planejado em HH pode ser comparado ao realizado usando `hora_inicio`/`hora_fim` × 1 operador (aproximação aceitável até a fase 2).

## 7. Impacto em Custos e DRE

- `CostAllocation.cost_category` (hoje string livre) deveria adotar os mesmos valores de `CategoriaOrcamento` (SEMENTE, FERTILIZANTE, DEFENSIVO, COMBUSTIVEL, MAO_DE_OBRA, SERVICO, SEGURO, OUTROS) — sem isso, nunca será possível abrir uma rubrica "Mão de obra" na DRE de forma confiável, porque a categoria nunca chega normalizada até lá.
- `dre/service.py::_consolidar_costs()` precisaria quebrar por `cost_category` para expor mão de obra/máquina/serviço separadamente — hoje tudo cai em `custos_diretos`/`custos_operacionais` agregados.
- `allocation_basis` (hoje `Numeric` livre sem unidade declarada) deveria, quando a alocação vier de mão de obra, carregar HH — mesma unidade canônica do consumo, permitindo rastrear "custo por HH" de ponta a ponta.

## 8. Máquinas

Recomenda-se **hora-máquina** como unidade canônica, pela mesma razão de HH: já é a direção natural do sistema (`FrotaCustoService` deriva custo-hora do histórico acumulado). Manter também custo-por-km para veículos rodoviários (já existe e atende um caso genuinamente diferente — deslocamento, não operação de campo). Não forçar tudo em hora — km é semanticamente correto para transporte.

## 9. Serviços terceirizados

**Não** forçar serviço contratado para HH — serviço é uma unidade comercial externa (por ha, diária, viagem, hora), definida pelo contrato com o terceiro, não pela produtividade interna. Manter `TipoServico.unidade_medida` como está conceitualmente, mas migrar de string livre para FK em `unidades_medida` (mesma correção estrutural do §10) para evitar erros de digitação — sem isso, replica-se o mesmo bug de enum "PLANEJAMENTO" vs "PLANEJADA" que já corrigimos em outro contexto nesta sessão.

## 10. Arquitetura — reaproveitamento, não invenção

**Achado central:** a infraestrutura de unidade normalizada **já existe** (`unidades_medida`, usada via FK em `agricola/operacoes` e `agricola/cenarios`). O trabalho não é criar um novo motor de unidades — é **estender o FK que já existe** para os três pontos que ainda usam string livre:

1. `ItemOrcamentoSafra.unidade` → `unidade_medida_id`
2. `OperationTemplateItem.unidade` → `unidade_medida_id`
3. `SafraTarefaNecessidade.unidade_referencia` → `unidade_medida_id`

Migração recomendada: **aditiva, não destrutiva** — adicionar a nova coluna FK nullable ao lado da string existente, popular por matching de texto onde possível, manter a string legada como fallback de leitura por um período de transição, sem quebrar safras já lançadas (ex.: Pimenta do Reino, já com 14 itens de orçamento e 10 tarefas usando o padrão antigo).

---

## 11. Arquivos afetados (caso a melhoria seja implementada)

**Backend:**
- `services/api/agricola/a1_planejamento/models.py`, `schemas.py`, `service.py`, `snapshot_service.py`
- `services/api/agricola/models/templates.py`, `agricola/templates/schemas.py`, `service.py`
- `services/api/agricola/tarefas/models.py`, `schemas.py`, `service.py`
- `services/api/agricola/operacoes/models.py`, `service.py` (equipe em execução — fase 2)
- `services/api/agricola/custos/models.py`, `allocation_service.py` (`cost_category` → enum)
- `services/api/agricola/dre/service.py` (quebra por categoria)
- `services/api/rh/models.py` (nenhuma mudança de schema, só de uso — `valor_hora` já existe)
- Nova migration Alembic (colunas FK nullable + backfill), com `op.execute("COMMIT")` após `run_sync()`.

**Frontend:**
- `apps/web/src/components/agricola/orcamento-safra.tsx`
- `apps/web/src/components/agricola/agro-templates-manager.tsx` e `apps/web/src/app/(dashboard)/agricola/templates/[id]/page.tsx`
- `apps/web/src/components/agricola/safra-tarefas.tsx`
- `packages/zod-schemas` (schemas de orçamento, template, tarefa)

## 12. Risco de regressão

Baixo, **se** a migração for aditiva (nova coluna nullable, string legada preservada). Risco médio se a decisão for migrar `quantidade`/`unidade` existentes in-place sem campo novo — dados históricos de mão de obra (como os da Pimenta do Reino) ficariam ambíguos para sempre, já que não há como inferir `numero_pessoas` retroativamente a partir de "38 DIA". Recomendação: **não tentar corrigir dados históricos automaticamente** — normalizar apenas novos lançamentos a partir da implementação, e marcar registros antigos como "unidade legada, sem decomposição disponível".

---

## 13. Respostas objetivas (resumo executivo)

| Pergunta | Resposta |
|---|---|
| Unidade oficial de mão de obra | **Homem-hora (HH)** |
| Produtividade | Separada do consumo; atributo opcional de referência em `OperationTemplateItem`, usada só para calcular HH na hora de planejar |
| Equipes | Não criar cadastro novo; usar `numero_pessoas` + duração como campos multiplicativos que geram HH |
| Mão de obra terceirizada | Tratar como `SERVICO`, unidade comercial própria (ha/diária/viagem/hora) — não forçar para HH |
| Máquinas | **Hora-máquina**, mantendo km para veículos rodoviários |
| Conversões | Sim — entrada flexível (dia, pessoas×dias, hora), conversão e persistência sempre em HH pelo backend |
| Impacto Planejamento | Formulários de orçamento/template passam a pedir `numero_pessoas` + duração |
| Impacto Execução | `OperacaoExecucao` não suporta equipe hoje — gap real, fase 2 |
| Impacto Orçamento | Elimina ambiguidade de "quantidade em DIA" já identificada em produção |
| Impacto DRE | Requer `cost_category` normalizado para abrir rubrica "Mão de obra" isolada — hoje inexistente |
| Arquivos afetados | Ver §11 |
| Risco de regressão | Baixo com migração aditiva; alto se tentar reinterpretar dados históricos automaticamente |
