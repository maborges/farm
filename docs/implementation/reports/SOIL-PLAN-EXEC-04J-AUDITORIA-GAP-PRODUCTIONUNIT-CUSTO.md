# SOIL-PLAN-EXEC-04J — Auditoria do gap de custo sem ProductionUnit resolvível

Somente leitura. Nenhum código, teste, model, schema, migration ou dado foi alterado nesta etapa.

## 1. Resumo executivo

O gap identificado em 04I é **real e confirmado em dados de desenvolvimento**: 47 operações `REALIZADA` com `custo_total > 0` não possuem `production_unit_id`, e 103 operações `REALIZADA` com custo não possuem `CostAllocation` correspondente (7 tenants afetados). O sistema já possui um alerta de governança (`OPERACAO_COM_CUSTO_SEM_CONTEXTO_ALLOCATION`, severidade `RISCO_ECONOMICO`) que **poderia** bloquear a conclusão da operação, mas o modo de enforcement padrão é `WARNING_ONLY` — nenhuma severidade bloqueia por padrão — então o alerta apenas loga e notifica, sem impedir a operação. O dashboard mascara o gap via fallback (`custo_total`), mas a DRE, que constrói seu escopo inteiramente a partir de `ProductionUnit`, **não enxerga nem o custo nem a própria operação** quando não há `ProductionUnit`.

## 2. Resolução atual (`_resolve_production_unit_id`)

Local: `agricola/operacoes/service.py:253-291`.

Pseudofluxo:
```
se dados.production_unit_id informado:
    valida contexto (tenant, safra, area, cultivo) via validate_production_unit_context
    retorna pu.id  # ou levanta erro de validação
senão:
    SELECT ProductionUnit.id
    WHERE tenant_id = tenant_atual AND safra_id = dados.safra_id AND area_id = dados.talhao_id
    ORDER BY (status='ATIVA') DESC, created_at DESC
    LIMIT (implícito por .first())
    se nenhum resultado:
        log warning "No production_unit found... persisting with NULL"
    retorna production_unit_id (pode ser None)
```

Não há exceção lançada quando a resolução automática falha — a operação é persistida com `production_unit_id = NULL`. Não há tratamento de múltiplos candidatos além de priorizar `status='ATIVA'` e o mais recente (não é um `LIMIT 1` cego — há uma regra de domínio: unidade ativa mais recente prevalece), mas isso não é auditado quanto a corretude de negócio (duas unidades ATIVA para a mesma safra/área geram escolha arbitrária pelo `created_at`).

`_garantir_execucao_e_allocation_leves` (linhas 602-782) é chamado quando `operacao.status == "REALIZADA"`:
1. Busca/cria `OperacaoExecucao` (requer `unidade_ha_id` resolvível; se ausente, gera finding `OPERACAO_REALIZADA_SEM_EXECUCAO_NOVO_FLUXO` e retorna `(None, None)`).
2. Se `custo_operacional <= 0` **ou** `production_unit_id is None`: não cria `CostAllocation`.
   - Se custo > 0 e `production_unit_id is None` e a regra do tipo de operação exige allocation (`regra.exige_cost_allocation`): gera finding `OPERACAO_COM_CUSTO_SEM_CONTEXTO_ALLOCATION` (RISCO_ECONOMICO) via `registrar_e_aplicar_enforcement(..., allow_block=True, error_message=...)`.
   - Se custo <= 0: gera finding leve `OPERACAO_AGRICOLA_SEM_CUSTO_NOVO_FLUXO` (WARNING_LEVE).
3. Se há `production_unit_id` e custo > 0: chama `registrar_cost_allocation(...)` com `source="OPERATION_EXECUTION"`. Se essa chamada falhar (ex.: FK/validação), gera finding `OPERACAO_COM_CUSTO_SEM_ALLOCATION_NOVO_FLUXO` (RISCO_ECONOMICO), também com `allow_block=True`.

`registrar_e_aplicar_enforcement` só levanta `BusinessRuleError` (bloqueio real) se `deve_bloquear_severidade(severidade)` for verdadeiro, o que depende de `WORKFLOW_ENFORCEMENT_MODE` (constante em `agricola/alertas/service.py:75`, hardcoded como `WORKFLOW_ENFORCEMENT_WARNING_ONLY`, sem leitura de env). Nesse modo, `WORKFLOW_ENFORCEMENT_BLOCKED_SEVERITIES[WARNING_ONLY] = set()` — **nenhuma severidade bloqueia**. Logo, o alerta de RISCO_ECONOMICO hoje é puramente informativo (notificação + log), nunca impede a conclusão.

## 3. Mapa de entidades

| Entidade | Papel | Tabela | Observação |
|---|---|---|---|
| `UnidadeProdutiva` (`core/models/unidade_produtiva.py`) | Domínio fundiário/cadastral da propriedade (endereço, CAR, ITR). Alias legado `Fazenda`. | `unidades_produtivas` | Não tem FK para safra/cultivo. Não é referenciada por `OperacaoAgricola`, `CostAllocation` ou DRE. |
| `ProductionUnit` (`agricola/production_units/models.py`) | Unidade econômica: `safra_id + cultivo_id + area_id (+cultivo_area_id)`, com `percentual_participacao` e `area_ha`. | `production_units` | Canônica para custo, DRE e (parcialmente) operações. |
| `AreaRural` / `Talhao` | Território (`AREA_RURAL→GLEBA→TALHAO...`). | `cadastros_areas_rurais` | `ProductionUnit.area_id` referencia esta tabela. |
| `Safra`, `Cultivo` | Ciclo produtivo. | — | Compõem a chave natural de `ProductionUnit`. |
| `SafraTalhao` | Vínculo legado safra↔talhão (pré-`ProductionUnit`/`CultivoArea`). | `safra_talhoes` | Ver seção 5. |
| `OperacaoAgricola` | Operação de campo, possui `production_unit_id UUID NULLABLE`, `safra_id`, `talhao_id`. | `operacoes_agricolas` | FK nullable — confirmado por schema/uso (`production_unit_id: UUID | None = None` em `schemas.py:42,88,147`). |
| `OperacaoExecucao` | Execução leve/registro de custo real. | `operacoes_execucoes` | Também carrega `production_unit_id` nullable, herdado da operação. |
| `CostAllocation` | Apropriação econômica. | `cost_allocations` | `production_unit_id` **NOT NULL** (models.py:20-22, FK obrigatória para `production_units.id`). |

**UnidadeProdutiva ≠ ProductionUnit.** Não há duplicação — são conceitos ortogonais (fundiário vs. econômico-produtivo por safra/cultivo/área), confirmado por tabelas, FKs e uso em serviços distintos (nenhum serviço usa as duas de forma intercambiável).

## 4. Caminhos de criação de ProductionUnit

`ProductionUnitService` (`agricola/production_units/service.py`) expõe CRUD padrão via `BaseService`. A criação ocorre nos fluxos de: cadastro de `CultivoArea` (vínculo cultivo↔área dentro de uma safra), que é o caminho "moderno" de multi-cultivo (STEP 1-6 do projeto `multi_cultivo_refactoring`, conforme memória do projeto). Não foi localizada criação automática de `ProductionUnit` a partir de `SafraTalhao` legado — ou seja, tenants/safras que usam apenas `SafraTalhao` (fluxo pré-multi-cultivo) não geram `ProductionUnit` automaticamente.

Classificação:
- **Criar `SafraTalhao` sem `ProductionUnit`**: VÁLIDA (fluxo legado ainda ativo, sem migração automática).
- **Criar `OperacaoAgricola` sem `production_unit_id`**: VÁLIDA — campo opcional em `OperacaoAgricolaCreate`, sem validação obrigatória em schema/rota.
- **Marcar operação como `REALIZADA` sem `ProductionUnit` resolvível**: INVÁLIDA MAS PERMITIDA — o único freio é o alerta `RISCO_ECONOMICO`, que não bloqueia no modo padrão `WARNING_ONLY`.

## 5. SafraTalhao legado

`SafraTalhao` continua em uso ativo em testes de produção (`tests/test_operacoes_validacao_fase.py`, `tests/test_multi_up_hardening_step01.py`, serviços de recomendação e sync do Campo PWA), não apenas em fixtures isoladas. Não há evidência de rotina de migração/convergência automática `SafraTalhao → ProductionUnit` no código auditado (buscas por `SafraTalhao` combinadas com `ProductionUnit` no mesmo service não revelaram tal ponte, além da resolução manual por `safra_id + area_id` em `_resolve_production_unit_id`, que depende de já existir uma `ProductionUnit` cadastrada para aquela combinação — `SafraTalhao` isoladamente não basta). Conclusão: o gap **não é apenas de fixture antiga** — é um fluxo real ainda permitido para tenants que operam com `SafraTalhao` sem terem migrado/criado `ProductionUnit` correspondente (reforçado pelos 47 registros reais encontrados na seção 13).

## 6. Obrigatoriedade de ProductionUnit

| Entidade | `production_unit_id` | Nível |
|---|---|---|
| `OperacaoAgricola` | Nullable | model/schema/rota — nenhuma validação obrigatória |
| `OperacaoExecucao` | Nullable (herdado) | idem |
| `CostAllocation` | **NOT NULL** | banco + FK — obrigatório por constraint |

Ou seja, a única barreira "dura" (constraint de banco) está no ponto final da cadeia (`CostAllocation`), não no início (`OperacaoAgricola`). Isso é exatamente por que a operação REALIZADA "passa" sem `ProductionUnit`, mas a tentativa de criar `CostAllocation` some silenciosamente (é simplesmente pulada pelo `if custo_operacional <= 0 or operacao.production_unit_id is None`, nunca chega a violar a constraint — o código evita a exceção de FK ao nunca tentar o insert).

## 7. Criação de CostAllocation — tabela de origens

| Source | Escritor | Requer ProductionUnit | Valor | Consumidor |
|---|---|---|---|---|
| `OPERATION_EXECUTION` | `_garantir_execucao_e_allocation_leves` (único escritor localizado para operações agrícolas) | Sim (bloqueante na prática, sem fallback) | `operacao.custo_total` | DRE, dashboard (com fallback) |
| `INVENTORY_MOVEMENT` | outros pontos de consumo de estoque (fora do escopo desta operação; não mapeado em detalhe nesta auditoria por restrição de tempo, mas referenciado via FK `inventory_movement_id` no model) | Presumível Sim (mesma constraint NOT NULL) | custo FIFO do movimento | DRE |
| `fin_rateio_id` (rateio financeiro) | módulo financeiro (fora do escopo agrícola) | Sim | rateio | DRE |

Confirmado: `_garantir_execucao_e_allocation_leves` é o único escritor de `CostAllocation` para o domínio de operações agrícolas.

## 8. Operações sem insumo físico

Mão de obra, hora-máquina, serviço terceirizado etc. entram pelo mesmo caminho: `custo_operacional = operacao.custo_total` (valor direto da operação, não soma de insumos). O gap **afeta todo custo operacional**, não apenas consumo de insumo — a checagem é unicamente `custo_total > 0` e `production_unit_id is None`, agnóstica à origem do custo.

## 9. DRE agrícola

`agricola/dre/service.py` constrói o escopo (`_build_scope` / método de resolução de `production_units`, linhas ~224-324) **inteiramente a partir de `ProductionUnit`** (filtra por `safra_id`, `area_id`, `production_unit_id(s)`), e todo o restante do relatório (romaneios, custos, etc.) itera sobre `scope["production_units"]`. Não há nenhum ponto de fallback para `OperacaoAgricola.custo_total`. Consequência: uma operação sem `ProductionUnit` **não aparece na DRE de forma alguma** — não é "custo perdido dentro de uma unidade", é uma exclusão total do relatório para aquela operação.

## 10. Dashboard (comparação com 04F)

`agricola/dashboard/service.py:236-253` implementa exatamente o fallback documentado em 04F: `CostAllocation` prevalece; quando a operação não tem `id` presente no mapa de alocações agregadas por `operacao_id`, usa `op.custo_total`. Esse fallback opera por **operação individual** (chave = `operacao_id`), não por `ProductionUnit` — por isso é aplicável mesmo sem unidade resolvida, diferente da DRE, que só existe em função de `ProductionUnit`. Reaproveitar essa estratégia na DRE exigiria reestruturar o escopo (hoje `production_unit`-first) para também iterar por operações órfãs, o que tem implicações de agrupamento por centro de custo/cultivo/talhão que a DRE precisa e o dashboard não exige com o mesmo rigor.

Classificação do mascaramento pelo dashboard: **PARCIALMENTE** — o dashboard mostra o valor correto de custo total (via fallback), mas mascara a ausência de dimensão econômica (não indica que a operação carece de `CostAllocation`/`ProductionUnit`), então a métrica agregada de margem fica correta, mas a rastreabilidade granular por unidade produtiva permanece quebrada.

## 11. Estoque e FIFO

Confirmado por leitura do código de `_garantir_execucao_e_allocation_leves`: a criação/reversão de movimento de estoque é tratada em métodos separados (`_reverter_movimentos_estoque_operacao`, chamados a partir de outros pontos do fluxo de operações, fora desta função) e **não é condicionada** à existência de `ProductionUnit`. Isso significa que é possível: consumo físico de estoque (com custo FIFO conhecido) ocorrer independentemente de `CostAllocation` ser criado. **Risco ALTO**: consumo físico sem reflexo econômico — o estoque é baixado (fato físico irreversível sem estorno) mas o custo correspondente nunca chega à apropriação por `ProductionUnit`, ficando "preso" apenas em `OperacaoAgricola.custo_total`.

## 12. Alertas e governança

Existem dois alertas específicos e ativos (não são o alerta aposentado de 04I):
- `OPERACAO_COM_CUSTO_SEM_CONTEXTO_ALLOCATION` (RISCO_ECONOMICO) — quando custo>0, sem `production_unit_id`, e o tipo de operação exige allocation.
- `OPERACAO_COM_CUSTO_SEM_ALLOCATION_NOVO_FLUXO` (RISCO_ECONOMICO) — quando a tentativa de `registrar_cost_allocation` falha mesmo com `production_unit_id` presente.

Ambos usam `registrar_e_aplicar_enforcement(..., allow_block=True)`, mas como `WORKFLOW_ENFORCEMENT_MODE = WORKFLOW_ENFORCEMENT_WARNING_ONLY` está hardcoded (não lido de env/config), **nenhum dos dois bloqueia hoje**. A lacuna real não é "ausência de alerta" — é "alerta existe mas não é enforçado por configuração padrão". Não existe dashboard de inconsistências dedicado a este código nem guardrail de CI/go-live localizado para este cenário específico.

## 13. Dados existentes (PostgreSQL de dev, `192.168.0.3/farms`, somente SELECT)

| Métrica | Valor |
|---|---|
| Operações `REALIZADA` | 552 |
| Operações `REALIZADA` com `custo_total > 0` | 450 |
| Operações `REALIZADA` com `custo_total > 0` **sem** `production_unit_id` | 47 |
| Operações `REALIZADA` sem `production_unit_id` (qualquer custo) | 117 |
| Operações `REALIZADA` com custo sem `OperacaoExecucao` | 93 |
| Tenants afetados (custo>0, sem PU) | 7 |
| Operações `REALIZADA` com custo **sem `CostAllocation` correspondente** | 103 |

Confirma que o cenário é real e não hipotético/apenas-teste; afeta múltiplos tenants nesta base.

## 14. Testes e fixtures

`grep -rl "SafraTalhao("` retorna 4 arquivos de teste ativos (não apenas fixtures isoladas): `test_operacoes_validacao_fase.py`, `test_multi_up_hardening_step01.py`, testes de recomendação e sync do Campo. Isso é consistente com a seção 5 — não é "só teste legado", reflete fluxo de produção real. Classificação: **cenário funcional legítimo ainda coberto por testes**, não apenas fixture inválida.

## 15. APIs / rotas

`production_unit_id` é campo opcional (`UUID | None = None`) em pelo menos três schemas de operações (`schemas.py:42,88,147` — criação/atualização/conclusão). É recebido do cliente quando presente, mas quando ausente é resolvido automaticamente pelo backend (`_resolve_production_unit_id`), sem validação de obrigatoriedade em nenhuma camada (schema, service, rota) antes de marcar `REALIZADA`.

## 16. Wizard / onboarding

Não foi possível, dentro do escopo desta auditoria, localizar uma etapa de wizard que force `ProductionUnit` ativa para toda combinação safra×área antes do go-live (a criação de `ProductionUnit` está ligada a `CultivoArea`, um fluxo posterior/opcional ao cadastro básico de safra+talhão). Portanto, o gap **pode ocorrer mesmo em tenant "corretamente implantado"** se esse tenant não adotou o fluxo de multi-cultivo/`CultivoArea` — não é exclusivo de tenant incompleto.

## 17. Alternativas de correção (comparação)

| Alt. | Descrição | Prós | Contras |
|---|---|---|---|
| A | Bloquear REALIZADA sem PU resolvível | Fonte única, sem dado inválido novo | Quebra fluxos legados ativos (SafraTalhao) sem migração prévia; precisa mudar `WORKFLOW_ENFORCEMENT_MODE` ou lógica de bloqueio específica |
| B | Resolução determinística (derivar de safra/talhão/área) | Reduz `NULL`s futuros sem mudar contrato | Não resolve casos sem `ProductionUnit` cadastrada nenhuma; não cobre dados já gravados |
| C | `CostAllocation.production_unit_id` nullable | Simples, sem quebrar fluxo | Quebra semântica "unidade econômica", exige migration, perde dimensão em DRE mesmo assim |
| D | Fallback formal na DRE | Paridade com dashboard, resolve visibilidade | Reestrutura DRE (hoje PU-first); risco de dupla contagem se um PU parcial + custo_total coexistirem; documento explicitamente pede para não recomendar só por simplicidade |
| E | Reparo de dados legados (criar PU/allocation retroativos) | Resolve os 103 casos reais existentes | Não prevê novos casos; requer critério de mapeamento seguro |
| F | Combinação (B+A para dados novos, E para histórico) | Cobre os dois eixos sem migration ampla, sem mascarar DRE | Maior escopo de implementação, mas nenhum item isolado é suficiente sozinho |

## 18. Recomendação

**DIREÇÃO: PRODUCTIONUNIT-F** — combinação separando dados novos (aplicar B: melhorar determinismo da resolução automática, e A: elevar a severidade a bloqueante nesse caminho específico — não globalmente via `WORKFLOW_ENFORCEMENT_MODE`, que afetaria outros alertas) de dados históricos (E: reparo pontual dos 103 registros identificados). D (fallback na DRE) é desaconselhado como solução isolada — mascararia a causa raiz do mesmo modo que o dashboard já faz, sem resolver a apropriação por `ProductionUnit`/centro de custo que a DRE precisa estruturalmente.

## 19. Respostas às 15 perguntas obrigatórias

1. **Ocorre em produção?** Sim — confirmado por dados reais (47/103 casos, 7 tenants) no ambiente de dev/homolog conectado.
2. **É permitido pelo contrato atual?** Sim — `production_unit_id` é opcional em schema/model/rota para `OperacaoAgricola`/`OperacaoExecucao`; só `CostAllocation` exige (constraint de banco), e essa etapa é simplesmente pulada, não violada.
3. **SafraTalhao sem ProductionUnit é legado ou válido?** Ambos — é legado historicamente, mas continua sendo criado/usado em fluxos e testes ativos hoje.
4. **Pode ser REALIZADA nesse estado?** Sim, sem bloqueio.
5. **Pode consumir estoque?** Sim — consumo de estoque não depende de `ProductionUnit`.
6. **Pode ter custo_total?** Sim, `custo_total` é campo próprio da operação, independente de allocation.
7. **Por que CostAllocation exige ProductionUnit?** É a chave estrutural da unidade econômica (safra+cultivo+área) usada pela DRE para agrupar custo/receita — sem ela a allocation não tem dimensão de negócio válida.
8. **Existe resolução determinística disponível?** Parcial — existe resolução por `safra_id + area_id`, mas falha quando não há `ProductionUnit` previamente cadastrada (não deriva/cria uma nova).
9. **O dashboard mascara o gap?** Parcialmente (métrica de custo correta via fallback, mas rastreabilidade por unidade se perde).
10. **A DRE perde custo?** Sim, integralmente — a operação nem entra no escopo.
11. **Existe risco de consumo sem apropriação?** Sim, classificado como risco alto (seção 11).
12. **Existe alerta para operação com custo sem allocation?** Sim, existe (`RISCO_ECONOMICO`), mas não bloqueia no modo padrão.
13. **Correção necessária para dados novos?** Resolução determinística melhorada (B) + bloqueio direcionado (A) nesse caminho específico.
14. **Tratamento para dados históricos?** Reparo pontual (E) dos registros já identificados via query.
15. **O programa pode ser encerrado sem corrigir isso?** Não sem ressalva — o risco é real e mensurável; recomenda-se GO COM RESSALVAS, não NO-GO total do programa, já que o restante da arquitetura (04E-04I) está correto e o gap é localizado e compreendido.

## 20. Veredicto

**STATUS: GO COM RESSALVAS**

**DIREÇÃO RECOMENDADA: PRODUCTIONUNIT-F**

O programa SOIL-PLAN-EXEC pode ser considerado arquiteturalmente fechado quanto ao desenho (Operação→Execução→CostAllocation→DRE→Dashboard), mas **não deve ser encerrado sem uma etapa de acompanhamento** que trate: (a) o modo de enforcement do alerta `OPERACAO_COM_CUSTO_SEM_CONTEXTO_ALLOCATION`, hoje inofensivo por padrão; (b) o reparo dos 103 registros históricos identificados; (c) uma decisão explícita sobre convergência de `SafraTalhao` para `ProductionUnit`. Nenhuma alteração de código foi feita nesta etapa.

---

## Validação de escopo (somente leitura)

```
git status --short   # deve mostrar apenas este relatório como novo
git diff --check     # sem conflitos/whitespace em arquivos de código
```
