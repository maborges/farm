# OPERATIONS-GAP-01 — Auditoria de Cobertura das Operações Agropecuárias

> Auditoria somente-leitura (audit-before-code). Nenhum código, migration, model, endpoint ou frontend foi alterado. Evidências coletadas por 5 investigações paralelas de código real (models/services/routers/migrations), não por nomes de arquivo.
> Data: 2026-08-14 · Escopo: `/opt/lampp/htdocs/farm` (backend `services/api/`, frontend `apps/web/`, PWA `apps/campo/`)

---

## 1. Resumo Executivo

A aplicação já implementa a espinha dorsal completa da cadeia **Planejamento → Execução → Recursos → Estoque → Custos → Produção → Comercialização**, com um núcleo bem desenhado (`Safra` → `Cultivo`/`CultivoArea` → `SafraTarefa` → `OperacaoAgricola`/`OperacaoExecucao` → `InsumoOperacao`/`EstoqueMovimento` → `CostAllocation`/`ProductionUnit` → `ProdutoColhido`/`RomaneioColheita` → `ComercializacaoCommodity`). Pecuária, frota/máquinas e mão de obra têm modelagem madura e, em geral, ligada a safra/talhão/operação.

Os problemas dominantes **não são ausência de funcionalidade**, e sim: (a) **duplicações econômicas paralelas ainda vivas** (Rateio-Float vs CostAllocation-Numeric; 3 sistemas de alertas; 2 modelos de CAR); (b) **migração incompleta Float→Numeric** em estoque (saldo, lote, requisição); (c) ~~elo final quebrado: não existe custo/margem por lote comercializado~~ — **RESOLVIDO em 2026-08-15** (ver Adendo, Seção 21): implementadas 3 alternativas complementares de custo/margem por lote (rateio sob demanda no DRE, snapshot de custo na colheita, tabela de junção auditável com override manual); (d) módulos específicos-a-café (beneficiamento) sem generalização para outras culturas; (e) gaps pontuais reais (castração, mão de obra manual sem equipamento, infraestrutura fixa sem manutenção, embalagens/receituário).

O Campo PWA é arquitetura offline genuína (Dexie + outbox), reusa a API, mas não cobre mão de obra/estoque como fluxo offline dedicado.

## 2. Arquitetura Operacional Encontrada

- **Pivô econômico**: `ProductionUnit` (`agricola/production_units/models.py`) = safra+cultivo+área; liga `OperacaoAgricola.production_unit_id` a `CostAllocation`.
- **Planejamento**: `SafraTarefa` (unitário, por talhão) é a fonte oficial que materializa `OperacaoAgricola` via `TarefaService.gerar_operacao_planejada`; `PlanoOperacional` é agrupador administrativo em lote, deliberadamente não substitui o fluxo unitário (docstring explícita).
- **Execução**: `OperacaoAgricola`/`OperacaoExecucao` (genéricos por `tipo`/`subtipo` string) é o registro físico único; cobre teoricamente toda a lista B via catálogo, não por classe dedicada por atividade.
- **Recursos**: `InsumoOperacao` (estoque), `ApontamentoUso` (frota/operador), mão de obra via `LancamentoDiaria`/`Empreitada`/`PlanoOperacionalTarefaMaoObra`.
- **Estoque**: módulo `operacional/` (não há pasta `estoque/` própria) — `EstoqueMovimento`, `LoteEstoque`, `Deposito`, FIFO em `estoque_fifo.py`.
- **Custos**: `CostAllocation` (`agricola/custos/models.py`, Numeric) é o "ownership oficial" segundo o domain-map; `Rateio` (`financeiro/models/rateio.py`, Float) é sistema paralelo ainda ativo.
- **Produção/Comercialização**: `ProdutoColhido` → `RomaneioColheita` → (café) `LoteBeneficiamento` → `LoteRastreabilidade`/`CadernoLoteComercial` → `ComercializacaoCommodity`.
- **Campo PWA**: `apps/campo/` (Next.js separado), Dexie/IndexedDB com 14 migrações de schema, outbox (`sync/push.ts`) com retry/backoff, reusa endpoints do backend.

## 3. Matriz de Cobertura (amostra consolidada — ver seções 4–14 para detalhamento item a item)

| Domínio | Operação/Capacidade | Status | Planejamento | Execução | Recursos | Estoque | Custos | Financeiro | Produção | DRE/Dashboard | Campo PWA | Evidência | GAP |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | Safra/ciclo produtivo | COBERTO | Sim | Sim | — | — | — | — | — | Parcial | Sim | `agricola/safras/models.py:38` | — |
| A | Orçamento de safra | DUPLICADO-PARALELO | Sim (2 vias) | — | — | Sim | Parcial | — | — | Não confirmado | — | `schemas.py` ItemOrcamento vs `planejamento_operacional/models.py:99` | Reconciliação não confirmada |
| B | Preparo/Plantio/Desenvolvimento (genérico) | PARCIAL | Sim | Sim | Sim | Sim | Sim | — | — | — | Sim | `operacoes/models.py:8` tipo/subtipo string livre | Catálogo real não auditado |
| B | Fitossanitário/monitoramento | COBERTO | Sim | Sim | Sim | Sim | Sim | — | — | — | Sim | `monitoramento/models.py:8` | — |
| B | Colheita/romaneio | COBERTO | Sim | Sim | Sim | Sim | Sim | — | Sim | Parcial | Sim | `colheita/models.py:20`, `romaneios/models.py:8` | — |
| B | Pós-colheita/beneficiamento | PARCIAL (café-only) | Sim | Sim | Sim | Sim | Parcial | — | Sim | — | — | `beneficiamento/models.py:9` | Não generalizado p/ outras culturas |
| B | Análise de solo | DUPLICADO-PARALELO suspeito | Sim | Sim | — | — | — | — | — | — | — | `amostragem_solo/` vs `analises_solo/` | Confirmar overlap |
| B | Tarefa multi-talhão | GAP CONFIRMADO | Sim | Não | — | — | — | — | — | — | — | `tarefas/service.py:632-636` BusinessRuleError | Hard-stop |
| C | Animal individual | COBERTO | — | Sim | Sim | — | — | — | — | — | Sim | `pecuaria/animal/models.py:144` | — |
| C | Lote/rebanho coletivo | COBERTO | — | Sim | Sim | — | — | — | — | — | Sim | `animal/models.py:93`, `manejo.py` | — |
| C | Castração | GAP | — | Não | — | — | — | — | — | — | — | `TipoEvento` sem CASTRACAO | Enum incompleto |
| C | Confinamento/GMD | DUPLICADO-PARALELO CONFIRMADO | — | Sim | Sim | — | Sim | — | Sim | — | — | `enterprise/models/sprints_27_33.py:253` vs `gmd_utils.py` | 0 call-sites cruzados |
| C | Ordenha | DESACOPLADO | — | Sim | — | — | — | — | Sim | Sim | — | `pecuaria/routers/leite.py` | Não usa EventoAnimal |
| D | Cadastro/alocação/uso máquina | COBERTO | Sim | Sim | Sim | Parcial | Sim | — | — | Sim | Sim | `equipamentos/models.py:47`, `apontamento.py:17` | — |
| D | Manutenção frota | COBERTO | Sim | Sim | Sim | Parcial | Sim | — | — | — | — | `operacional/models/frota.py` | Peças sem estoque confirmado |
| D | Ferramenta baixo-valor vs patrimonial | GAP | — | — | — | — | — | — | — | — | — | `Equipamento.valor_aquisicao` único campo | Sem flag distintiva |
| E | Diária/empreitada | COBERTO | Sim | Sim | Sim | — | Sim | — | — | — | Não confirmado | `rh/models.py:104,137` | — |
| E | Homem-hora manual (sem equip.) | GAP | Parcial | Não | — | — | — | — | — | — | Não | `ApontamentoUso` exige equipamento_id NOT NULL | Sem apontamento manual dedicado |
| E | Múltiplos trabalhadores/operação | PARCIAL | — | Parcial | — | — | — | — | — | — | — | `LancamentoDiaria`/`Empreitada` 1:1 | Sem tabela de equipe |
| F | Entrada/saída/transferência/FIFO | COBERTO | — | Sim | — | Sim | Sim | — | — | — | Não confirmado | `estoque_fifo.py`, `estoque_service.py` | — |
| F | Perda (tipo de movimento) | GAP | — | — | — | Não | — | — | — | — | — | `_normalizar_origem` sem "PERDA" | Cai em ajuste genérico |
| F | Inventário físico geral | GAP | — | — | — | Parcial | — | — | — | — | — | Sem módulo de contagem cíclica | — |
| F | Float→Decimal (saldo/lote/requisição) | GAP CONFIRMADO | — | — | — | Sim (viola padrão) | — | — | — | — | — | `operacional/models/estoque.py` SaldoEstoque/LoteEstoque/ItemRequisicao=Float | Viola CLAUDE.md §4.2 |
| G | Requisição→Cotação→Aprovação→Pedido→Recebimento | COBERTO | Sim | Sim | — | Sim | — | Sim | — | — | — | `operacional/services/compras.py` (múltiplas linhas) | — |
| G | Serviços terceirizados (compra) | GAP | — | — | — | — | — | Não | — | — | — | Sem modelagem de compra de serviço | — |
| H | Custo realizado (CostAllocation) | COBERTO | — | Sim | — | Sim | Sim | — | — | Parcial | — | `agricola/custos/models.py:11` Numeric | — |
| H | Rateio financeiro (Rateio) | DUPLICADO-PARALELO CONFIRMADO | — | — | — | — | Sim | Sim | — | — | — | `financeiro/models/rateio.py:8` Float | Coexiste c/ CostAllocation |
| H | Depreciação | GAP | — | — | — | — | Não | — | — | — | — | Sem grep positivo | — |
| H | Contas a pagar/receber (classe dedicada) | PARCIAL | — | — | — | — | — | Sim (via Despesa/Receita) | — | — | — | `financeiro/models/despesa.py:9`, `receita.py:9` | Sem classe própria |
| I | Produção/romaneio | COBERTO | — | Sim | — | Sim | — | — | Sim | Parcial | Sim | `colheita/models.py`, `romaneios/models.py:8` | — |
| I | Beneficiamento café | PARCIAL | — | Sim | — | Sim | Parcial | — | Sim | — | — | `beneficiamento/models.py:9` | Só café |
| I | Comercialização/contrato/venda | COBERTO | — | Sim | — | Sim | — | Sim | Sim | Parcial | — | `financeiro/comercializacao/models.py` | — |
| I | Custo do lote / margem do lote | RESOLVIDO (2026-08-15) | — | — | — | Sim | Sim | Sim | Sim | Parcial | Não | `agricola/dre/service.py::_ratear_custos_por_lote`, `agricola/colheita/models.py::custo_unitario_producao`, `agricola/custos/lote_allocation_service.py` | Fechado backend; falta consumo em frontend/dashboard |
| I | Rastreabilidade | DUPLICADO-PARALELO suspeito | — | Sim | — | — | — | — | Sim | — | — | `LoteRastreabilidade` vs `CadernoLoteComercial` | Uso ativo não confirmado |
| J | Manutenção de frota (móvel) | COBERTO | Sim | Sim | Sim | Parcial | Sim | — | — | Sim | — | `operacional/models/frota.py` | — |
| J | Infraestrutura fixa (estrada/cerca/poço) | GAP | — | — | — | — | — | — | — | — | — | Sem model dedicado | Só Benfeitoria cadastral, sem manutenção |
| J | Irrigação/bombas/reservatórios | PARCIAL/ISOLADO | Parcial | Parcial | — | — | — | — | — | — | — | `ndvi_avancado/models/irrigacao.py:10` | Mal posicionado (dentro de NDVI) |
| K | CAR | DUPLICADO-PARALELO CONFIRMADO | — | — | — | — | — | — | — | — | — | `ambiental/models.py:56` vs `ambiental/models/car.py:35` | Shadowing de pacote suspeito |
| K | NDVI | GAP (mockado) | — | — | — | — | — | — | — | — | — | `ndvi/service.py:12-19` retorna string fixa | Mock explícito |
| K | Receituário/embalagens | GAP não confirmado | — | — | — | — | — | — | — | — | — | Não lido a fundo | Necessita 2ª passada |

*(Matriz completa por item das listas A–K está nos relatórios de evidência das seções 4–14; a tabela acima prioriza itens com classificação não-COBERTO ou com achados relevantes, para manter o documento tratável.)*

## 4. Cobertura Agrícola (A/B)

- **A. Planejamento**: Safra com máquina de fases e histórico versionado (`SafraFaseHistorico`) — COBERTO. Vínculo safra↔área tem 3 pontos concorrentes (`Safra.talhao_id` legado, `SafraTalhao` N:N, `CultivoArea`) — risco de dessincronia mas funcional. Orçamento tem dois sistemas (item de safra vs. plano operacional em lote) sem reconciliação automática confirmada — DUPLICADO-PARALELO a investigar. Metas de produtividade e planejado×realizado já nativos em `Cultivo` (`produtividade_meta_sc_ha` vs `produtividade_real_sc_ha`). Serviços terceirizados como categoria própria — não confirmado. Revisão/versionamento do orçamento é campo incremental simples (`PlanoOperacional.versao`), não audit trail completo.
- **B. Operações agrícolas**: núcleo genérico via `OperacaoAgricola.tipo/subtipo` cobre teoricamente todas as subcategorias (preparo/plantio/desenvolvimento), mas a granularidade real depende do catálogo (`OperacaoTipoFaseService`), não auditado a fundo — classificado PARCIAL por falta de confirmação, não por ausência de motor. Fitossanitário tem módulo dedicado de monitoramento de pragas/doenças com NDE. Colheita e romaneio maduros e integrados a estoque. Pós-colheita/beneficiamento é **específico a café** (nomenclatura ABIC/SCA) — para outras culturas é GAP de generalização. **GAP confirmado**: `SafraTarefa` sem `talhao_id` não gera `OperacaoAgricola` (hard-stop em `tarefas/service.py:632-636`), reconfirma memória `project_gap_tarefa_multitalhao.md`. Suspeita de duplicação entre módulos `amostragem_solo/` e `analises_solo/` não resolvida — recomenda-se 2ª auditoria pontual.

## 5. Cobertura Pecuária (C)

Arquitetura dupla deliberada: `EventoAnimal` (individual, enum `TipoEvento` amplo) e `ManejoLote` (coletivo). A maioria das operações da lista C está coberta em ambos os níveis (entrada, movimentação, pesagem, vacina/vermífugo, reprodução, desmama, venda, mortalidade). **GAPs reais**: castração ausente do enum de eventos; alimentação/suplementação só modelada em confinamento, não a pasto; homem-hora de manejo não distinto de apontamento de máquina. **Duplicação confirmada**: `ConfinamentoLote.ganho_medio_diario` (Float, `enterprise/models/sprints_27_33.py:253`) segue divergente de `pecuaria/services/gmd_utils.py::calcular_gmd()` — zero call-sites cruzados, confirma memória. Ordenha é módulo desacoplado do fluxo de eventos padrão. Reprodução tem dois caminhos (eventos básicos vs. módulo de genética/acasalamento) sem integração confirmada.

## 6. Máquinas e Equipamentos (D)

Módulo maduro e bem integrado: cadastro, alocação, apontamento de uso vinculado a `safra_id`/`talhao_id`/`operacao_id`/`production_unit_id`, horímetro/km, abastecimento, manutenção preventiva/corretiva (via `OrdemServico`/`RegistroManutencao`), custo/hora centralizado em `frota_dashboard_detail_service.py`. **GAP real**: nenhuma distinção entre ferramenta de baixo valor e ativo patrimonial depreciável no cadastro de `Equipamento` (só `valor_aquisicao`). Peças de manutenção não confirmadas como integradas ao estoque geral.

## 7. Mão de Obra (E)

Três camadas coexistem por design (estimativa no plano, equipe planejada, execução real) — arquitetura correta, não duplicação acidental. Diária e empreitada cobertos e ligados a safra. **GAP real**: apontamento de mão de obra manual sem uso de equipamento (capina, colheita manual) não tem fluxo dedicado — `ApontamentoUso` exige `equipamento_id` NOT NULL, então trabalho manual puro cai fora desse caminho e depende de `LancamentoDiaria`/`Empreitada`, que são registros 1:1 colaborador-lançamento, sem tabela de equipe associada a uma operação. Múltiplos trabalhadores na mesma operação é, portanto, PARCIAL (suportado por N registros, não por relação estruturada).

## 8. Estoque/Insumos (F)

Fluxo completo entrada/recebimento/depósito/lote/transferência/requisição/retirada/devolução, com separação real entre retirada física e "entrega"/consumo produtivo. FIFO implementado (`estoque_fifo.py`, ordenação por `data_fabricacao`). **GAPs confirmados**: (1) sem tipo de movimento "PERDA" dedicado — cai em ajuste genérico; (2) sem módulo de inventário/contagem cíclica formal; (3) **migração Float→Decimal incompleta** — `EstoqueMovimento` já usa `Numeric`, mas `SaldoEstoque`, `LoteEstoque`, `ItemRequisicao` e `ReservaEstoque` continuam `Float`, violação viva do CLAUDE.md §4.2 (reconfirma `project_ledger_estoque_float.md`, com detalhe fino de quais tabelas faltam); (4) vínculo `operacao_execucao_id` no ledger é opcional (nullable), não obrigatório — risco de saída de estoque sem produção vinculada.

## 9. Compras (G)

Cadeia completa Requisição→Cotação→Aprovação→Pedido→Recebimento→Estoque→Financeiro, com integração real confirmada (mesmo evento de recebimento materializa estoque e despesa financeira, não dois triggers separados). **GAPs**: "necessidade" automática por estoque mínimo não conectada à criação de solicitação; compra de serviços terceirizados sem modelagem própria; combustível e máquinas/equipamentos tratados como produto genérico, sem segregação de ativo/depreciação no fluxo de compra.

## 10. Custos e Financeiro (H)

`CostAllocation` (Numeric) é a apropriação econômica oficial conforme domain-map. **Duplicação confirmada e ativa**: `Rateio` (`financeiro/models/rateio.py`, Float) coexiste sem unificação (reconfirma `project_rateio_unificacao_adiada.md`) — sem guardrail de exclusividade visto no código, existe risco real de double-counting se ambos forem usados para o mesmo fato. Contas a pagar/receber não têm classe dedicada (usa `Despesa`/`Receita`). Depreciação e custos indiretos formais não localizados. Custo planejado×realizado existe a nível de `Cultivo` mas não como relatório consolidado único confirmado.

## 11. Produção/Pós-colheita (I)

Cadeia Talhão→Operação→Colheita→Produção→Beneficiamento→Lote→Classificação está implementada e conectada a estoque (`ProdutoColhido`→`RomaneioColheita`→`LoteBeneficiamento`, com FKs cruzadas). Beneficiamento é específico a café. Três nomenclaturas de "lote" coexistem ao longo da cadeia (não confirmado como acidental — parecem etapas distintas com FKs entre si, mas geram risco de drift).

## 12. Comercialização (I cont.)

`ComercializacaoCommodity` cobre contrato/pedido/venda/pagamento com integração a estoque (baixa de `ProdutoColhido`) e financeiro (gera receita). **GAP CRÍTICO RESOLVIDO em 2026-08-15** (ver Adendo, Seção 21, para o detalhamento completo): a lacuna de custo/margem por lote comercializado, identificada nesta auditoria e aprofundada em `OPERATIONS-GAP-01-DEEPDIVE-CUSTO-MARGEM-LOTE.md`, foi fechada com 3 alternativas complementares implementadas — (A) rateio sob demanda no DRE, (B) snapshot de custo unitário gravado na colheita, (C) tabela de junção auditável com override manual. A receita da venda agora tem caminho de custo associado por três vias distintas, cobrindo diferentes necessidades (consulta pontual, performance/estabilidade histórica, auditoria/ajuste manual). Rastreabilidade tem dois modelos sobrepostos (`LoteRastreabilidade` genérico vs `CadernoLoteComercial` assinado) cujo uso ativo não foi confirmado — GAP não relacionado, segue aberto.

## 13. Infraestrutura (J)

Manutenção madura existe **apenas para frota móvel** (veículos/implementos). Infraestrutura fixa (estradas, cercas, galpões, poços, reservatórios) tem apenas cadastro estático (`Benfeitoria` em `imoveis/` e, possivelmente duplicado, em `core/cadastros/propriedades/`) sem workflow de manutenção, custo ou apropriação — GAP real, sem equivalente a `OrdemServico`/`PlanoManutencao` de frota. Irrigação está mal posicionada dentro do módulo `ndvi_avancado`, isolada do restante de infraestrutura.

## 14. Ambiental/Compliance (K)

CAR tem **dois modelos concorrentes** (`ambiental/models.py::RegistroCAR` vs `ambiental/models/car.py::CAR`), com indício de shadowing de pacote Python (arquivo `models.py` vs pacote `models/` no mesmo namespace) — o router ativo parece usar apenas o primeiro, deixando funcionalidade rica (monitoramento de APP, sobreposição, desmatamento, CCIR) modelada mas não servida — DUPLICADO-PARALELO/possível código morto, requer confirmação dedicada. Outorgas hídricas cobertas e expostas via router. Certificações têm dois sistemas paralelos por escopos aparentemente distintos (rastreabilidade agrícola vs. ESG corporativo) — não confirmado overlap. NDVI é mock explícito confirmado (`ndvi/service.py:12-19`, retorna string fixa, comentário `# Mock logic`). Receituário/embalagens/inspeções não foram confirmados nesta rodada — recomenda-se 2ª passada dedicada.

## 15. Integração Web × API × Campo PWA

Campo PWA (`apps/campo/`, Next.js separado) tem arquitetura offline genuína: Dexie/IndexedDB com 14 migrações de schema, outbox pattern completo (`sync/push.ts`, fila com status PENDING/IN_FLIGHT/DONE/FAILED, retry com backoff, tratamento de conflito), reusa a API do backend (não replica regras de negócio). Cobre agrícola, pecuária e apontamento de máquina. **GAP MÉDIO**: mão de obra e estoque não têm `TaskType` dedicado no enum offline — sem fluxo de apontamento offline próprio. `processar_tarefa_campo` confirmado como única implementação (`pecuaria/services/manejo_sync_service.py:45`), não é duplicação. Backend expõe `sugerir_produtos_orcamento` (`planejamento_operacional/service.py:582`) mas o frontend web (`AddInsumoDialog`) nunca o chama — DESACOPLADO confirmado, causa raiz é frontend, não ausência de backend.

## 16. Duplicações e Fluxos Paralelos

| Duplicação | Status | Evidência | Severidade |
|---|---|---|---|
| Rateio (Float) vs CostAllocation (Numeric) | Confirmado, ativo | `financeiro/models/rateio.py:8` vs `agricola/custos/models.py:11` | ALTO |
| 3 sistemas de alertas (alert_engine / notificacoes.AlertasEngine / dispersos) | Confirmado, parcialmente conectado | `alert_engine/service.py:150-183` espelha unidirecionalmente em `Notificacao` só na criação | ALTO |
| notificacoes/ vs notifications/ | Confirmado, mas com ponte funcional (`recommendations/notification_bridge.py:11-22`) | — | MÉDIO |
| ConfinamentoLote.ganho_medio_diario vs gmd_utils | Confirmado, 0 call-sites cruzados | `enterprise/models/sprints_27_33.py:253` | MÉDIO |
| CAR: RegistroCAR vs CAR (pacote) | Confirmado, suspeita de shadowing | `ambiental/models.py:56` vs `ambiental/models/car.py:35` | ALTO |
| amostragem_solo/ vs analises_solo/ | Suspeita, não resolvida | — | MÉDIO (investigar) |
| LoteRastreabilidade vs CadernoLoteComercial | Suspeita, uso ativo não confirmado | `agricola/rastreabilidade/models.py` | BAIXO/MÉDIO |
| Orçamento de safra: item-de-safra vs plano-operacional-em-lote | Confirmado, sem reconciliação automática vista | `schemas.py` vs `planejamento_operacional/models.py:99` | MÉDIO |
| Rotas antigas/legadas coexistindo | Refutado — nenhuma rota `_old/_legacy/_v2` encontrada | `main.py` uniformemente `/api/v1/*` | — |
| Talhoes legado → AreaRural | Confirmado dropado, sem `class Talhao` ORM ativa | `migrations/versions/step2_drop_talhoes_legado.py` | — (resolvido) |

## 17. GAPs Classificados por Severidade

**CRÍTICO**
- ~~Custo/margem por lote comercializado inexistente~~ — **RESOLVIDO em 2026-08-15** (Seção 12, Adendo Seção 21).
- Tarefa multi-talhão (`SafraTarefa.talhao_id is None`) não gera `OperacaoAgricola` — hard-stop que impede execução/apontamento de um cenário operacional legítimo (Seção 4). **Segue aberto.**

**ALTO**
- Rateio (Float) vs CostAllocation (Numeric) sem exclusividade garantida — risco de dupla contabilização de custo.
- Float ainda presente em `SaldoEstoque`, `LoteEstoque`, `ItemRequisicao`, `ReservaEstoque` — viola padrão do projeto e é fonte potencial de erro de arredondamento em valores de estoque.
- 3 sistemas de alertas com ponte apenas parcial/unidirecional — risco de alerta "preso" sem chegar ao sino em updates.
- CAR com dois models concorrentes e suspeita de funcionalidade rica (APP, desmatamento, CCIR) não servida pelo router ativo.
- Vínculo `operacao_execucao_id` opcional no ledger de estoque — saída pode ficar sem produção vinculada.
- Infraestrutura fixa (estradas, cercas, poços, galpões) sem workflow de manutenção/custo — só frota móvel tem.

**MÉDIO**
- Beneficiamento pós-colheita específico a café, sem generalização para outras culturas.
- Mão de obra manual sem equipamento sem apontamento dedicado; múltiplos trabalhadores por operação sem tabela de equipe.
- Ordenha desacoplada do fluxo padrão de eventos pecuários.
- Reprodução com dois caminhos (eventos básicos vs. genética/acasalamento) sem integração confirmada.
- Sem tipo de movimento "PERDA" dedicado no estoque; sem inventário/contagem cíclica formal.
- Orçamento de safra com dois sistemas sem reconciliação confirmada.
- `sugerir_produtos_orcamento` implementado no backend mas nunca chamado pelo frontend (`AddInsumoDialog`).

**BAIXO**
- Sem distinção ferramenta de baixo valor vs ativo patrimonial em `Equipamento`.
- Peças de manutenção de frota não confirmadas como integradas ao estoque geral.
- Compra de serviços terceirizados sem modelagem própria (cai em produto genérico).
- Contas a pagar/receber sem classe dedicada (usa Despesa/Receita).

**OBSERVAÇÃO**
- Castração ausente do enum `TipoEvento` pecuário.
- NDVI confirmado mockado (`ndvi/service.py`), estrutural, decisão de produto pendente (Nestlé/café gap já mapeado).
- Suspeita de duplicação `amostragem_solo/` vs `analises_solo/` — recomenda investigação dedicada.
- Depreciação de ativos não localizada no código.
- Receituário/embalagens/inspeções de compliance não confirmados nesta rodada — necessita 2ª passada.

## 18. Riscos Arquiteturais

1. **Duplicação econômica sem guardrail**: convivência ativa de Rateio e CostAllocation sem mecanismo que impeça o mesmo fato ser rateado duas vezes.
2. **Migração de tipos incompleta**: parte do domínio de estoque já é `Numeric`, parte ainda `Float` — inconsistência que pode mascarar bugs de arredondamento em relatórios financeiros.
3. **Shadowing de pacote Python em `ambiental/`**: arquivo `models.py` e pacote `models/` coexistindo no mesmo namespace é um padrão frágil, propenso a import ambíguo e funcionalidade "fantasma".
4. **Cadeia de "lote" com 3+ nomenclaturas** (ProdutoColhido/LoteBeneficiamento/LoteRastreabilidade/CadernoLoteComercial) aumenta risco de drift entre etapas se alguma atualização não propagar.
5. **Sistemas de alertas fragmentados**: mesmo com ponte parcial, a arquitetura de 3 motores aumenta custo de manutenção e risco de comportamento inconsistente entre eles.
6. ~~**Elo Produção→Resultado quebrado**~~ — **RESOLVIDO em 2026-08-15**: backend agora calcula custo/margem por lote por 3 vias (Seção 21), e a fonte oficial foi decidida (Alternativa C — ver Seção 21). Risco residual: a decisão ainda não foi aplicada em nenhuma UI, então nada impede hoje que um desenvolvedor consuma A ou B como se fosse o número final — o guardrail é documental, não técnico.

## 19. Funcionalidades Existentes que Devem Ser Preservadas

- Arquitetura de planejamento em duas camadas (SafraTarefa unitário + PlanoOperacional em lote) — desenho deliberado, não remover.
- Separação individual/coletivo em pecuária (`EventoAnimal` vs `ManejoLote`) — cobre os dois modos de operação pedidos.
- FIFO de estoque (`estoque_fifo.py`) e separação retirada física × consumo produtivo — corretos e não devem ser colapsados.
- `ProductionUnit` como pivô entre planejamento e custo — núcleo do princípio arquitetural avaliado, já convergente.
- Outbox pattern do Campo PWA — implementação robusta, referência para futuras extensões offline.
- Materialização única no recebimento de compras (mesmo evento gera estoque + despesa) — evita duplicação, preservar esse padrão ao estender outros fluxos.
- `SafraFaseHistorico` como audit trail de transição de fase — padrão bom a replicar em outros domínios que hoje só têm campo incremental (ex. versionamento de orçamento).

## 20. Recomendação de Próximos Passos

Sem propor refatoração ampla, e em ordem de exposição de risco/esforço:
1. Investigar e decidir formalmente (produto, não código): Rateio vs CostAllocation — qual é o caminho único daqui pra frente.
2. Completar a migração Float→Numeric nas 4 tabelas de estoque identificadas (escopo cirúrgico, já mapeado).
3. Confirmar/relatar (2ª auditoria pontual) o shadowing em `ambiental/models.py` vs `ambiental/models/car.py` e decidir qual é o vivo.
4. ~~Endereçar o GAP crítico de custo/margem por lote comercializado~~ — **CONCLUÍDO em 2026-08-15** (Seção 21). ~~Decidir a fonte oficial~~ — **CONCLUÍDO em 2026-08-15**: Alternativa C é a fonte oficial (ver Seção 21). Próximos passos derivados: (i) implementar consumo em frontend usando os endpoints de C; (ii) avaliar tornar `ComercializacaoCommodity.produto_colhido_id` obrigatório (hoje `nullable`).
5. Resolver o hard-stop de tarefa multi-talhão (decisão de produto: dividir a tarefa por talhão vs. permitir OperacaoAgricola multi-área).
6. Fazer 2ª passada dedicada em: `amostragem_solo` vs `analises_solo`; receituário/embalagens/compliance; contas a pagar/receber; custos indiretos/depreciação — itens não confirmados por escopo desta auditoria.

---

## 21. Adendo (2026-08-15) — Resolução do GAP crítico de custo/margem por lote

Esta seção documenta o fechamento do GAP CRÍTICO original ("Custo/margem por lote comercializado inexistente", Seções 3.I e 12), investigado em profundidade em `OPERATIONS-GAP-01-DEEPDIVE-CUSTO-MARGEM-LOTE.md` e implementado em 3 commits sequenciais no mesmo dia. As três alternativas descritas no deep-dive foram todas implementadas, cada uma cobrindo uma necessidade distinta — não são mutuamente exclusivas.

### Alternativa A — Rateio sob demanda no DRE (sem persistência)

- **O que faz**: estende `DREAgricolaV1Service.gerar()` (`agricola/dre/service.py`) para ratear o custo de cada `ProductionUnit` entre os lotes vendidos no período, proporcional à quantidade movimentada, calculado em memória a cada chamada — sem migration, sem novo campo.
- **Evidência**: `agricola/dre/service.py::_ratear_custos_por_lote` (novo método); `agricola/dre/schemas.py::DRELoteMargem`; campos `margem_por_lote`/`lotes_sem_vinculo` em `DREAgricolaResponse`.
- **Cobertura**: consulta pontual, sempre atualizada (reflete `CostAllocation` lançados a qualquer momento), mas recalculada a cada request — não serve para performance em relatórios frequentes nem congela histórico.
- **Testes**: `tests/unit/agricola/test_dre_lote_margem.py` (3 casos unitários), `tests/test_dre_agricola_v1.py::test_dre_v1_rateia_custo_por_lote_proporcional_a_quantidade` (integração com banco real).

### Alternativa B — Snapshot de custo unitário na colheita (imutável)

- **O que faz**: grava `custo_unitario_producao` em `ProdutoColhido` no momento da criação do lote (fechamento de romaneio ou entrada manual), calculado como custo acumulado do PU até a data / quantidade acumulada até a data. Uma vez gravado, não muda — estável para histórico, mas pode subestimar custo se houver lançamentos posteriores com atraso (risco já documentado no deep-dive).
- **Evidência**: campo `custo_unitario_producao` em `agricola/colheita/models.py`; helper `calcular_custo_unitario_snapshot()` em `agricola/custos/service.py`; migration `20260815_produto_colhido_custo_unitario.py`; chamado em `agricola/romaneios/service.py::RomaneioService.criar` e `agricola/colheita/service.py::ProdutoColhidoService.criar`.
- **Cobertura**: PU ambíguo (consórcio) ou inexistente → campo fica `NULL`, não bloqueia a criação do lote. Sem backfill de lotes históricos (decisão de escopo).
- **Testes**: `tests/integration/agricola/test_produto_colhido_custo_snapshot.py` (5 casos: cálculo correto, PU ambíguo, PU inexistente, custo lançado após a data ignorado, wiring em `ProdutoColhidoService.criar`).

### Alternativa C — Tabela de junção auditável com override manual

- **O que faz**: nova tabela `agricola_produto_colhido_cost_allocations` persiste o vínculo explícito entre cada lote e cada `CostAllocation`, com percentual/valor atribuído. Populada por reconciliação sob demanda (não cron) que recalcula as linhas `AUTOMATICO` (delete+recreate, idempotente) sem tocar em linhas `MANUAL` — permite ajuste humano auditado (exige justificativa) sem perder o cálculo automático original.
- **Evidência**: model `ProdutoColhidoCostAllocation` em `agricola/custos/models.py`; `agricola/custos/lote_allocation_service.py` (`reconciliar_alocacoes_lote`, `aplicar_override_manual`, `obter_custo_alocado`); migration `20260815_produto_colhido_cost_allocation.py`; endpoints `POST/GET /agricola/produtos-colhidos/{id}/{reconciliar-custos,custos,custos/override}` em `agricola/colheita/router.py` (override restrito a `agronomo`/`admin`).
- **Cobertura**: a mais completa das três — auditável, versionável, sobrevive a custos lançados com atraso (basta reconciliar de novo). Sem job automático de reconciliação (decisão de escopo — roda sob demanda via endpoint).
- **Testes**: `tests/integration/agricola/test_produto_colhido_cost_allocation.py` (5 casos: rateio proporcional exato, idempotência, override não sobrescrito por reconciliação, validação de justificativa obrigatória, falha com PU ambíguo).

### Decisão de fonte oficial (2026-08-15)

Para evitar repetir o padrão de "motores paralelos sem guardrail" já visto em Rateio vs. CostAllocation (Seção 16/18), fica formalmente decidido:

- **Alternativa C (tabela de junção auditável) é a fonte oficial** de custo/margem por lote comercializado, para qualquer relatório, exportação, dashboard ou tela de auditoria. É a única que (i) sobrevive a `CostAllocation` lançados após a colheita via reconciliação sob demanda, e (ii) tem trilha de auditoria (`origem_calculo`, `justificativa`) para ajuste manual. Consumidores que precisam do número "final" devem ler `obter_custo_alocado()` / `GET /agricola/produtos-colhidos/{id}/custos`, acionando `reconciliar_alocacoes_lote()` quando o dado estiver desatualizado.
- **Alternativa B (snapshot na colheita) é informativa, não oficial** — representa "custo de produção até a data de colheita", útil como indicador rápido e imutável, mas não deve ser apresentada como margem final porque ignora custos lançados depois (secagem, armazenagem, frete). Qualquer UI que exiba `custo_unitario_producao` deve rotulá-lo como estimativa na colheita, não como custo definitivo.
- **Alternativa A (rateio on-demand no DRE) é uma view de conveniência**, mantida por já estar integrada ao `DREAgricolaV1Service` e não exigir chamada extra — mas seu resultado pode divergir de C se a reconciliação de C não tiver rodado após novos lançamentos. Não é fonte oficial fora do contexto do próprio DRE.

Consequência prática: ao construir qualquer tela ou relatório de custo/margem por lote, o frontend deve consumir os endpoints de C; A e B seguem existindo como estão, sem obrigação de convergência automática entre si.

### O que permanece em aberto após esta resolução

- **Sem consumo em frontend**: os três mecanismos são só backend; nenhuma tela consome os novos campos/endpoints ainda — inclusive a fonte oficial (C) recém-decidida.
- **`ComercializacaoCommodity.produto_colhido_id` continua `nullable`**: comercializações sem esse vínculo seguem fora do rateio por lote (reportadas como aviso `COMERCIALIZACAO_SEM_LOTE_VINCULADO` no DRE) — tornar obrigatório é decisão de produto separada, ainda não tomada.
- **Sem backfill histórico**: lotes/comercializações anteriores a 2026-08-15 não recebem os novos campos automaticamente.

---

## STATUS DA COBERTURA OPERACIONAL: **PARCIAL**

A aplicação cobre com solidez a maior parte do ciclo agrícola, pecuário, de máquinas e de mão de obra, com um núcleo arquitetural coerente (ProductionUnit/CostAllocation/OperacaoAgricola). O GAP crítico original (elo final Produção→Resultado quebrado) foi resolvido em 2026-08-15 (Seção 21), mas o status permanece **PARCIAL** — não "ADEQUADA/MADURA" — porque duplicações econômicas ativas sem guardrail (Rateio-Float vs CostAllocation-Numeric, 3 sistemas de alertas) e a migração incompleta Float→Numeric em estoque continuam colocando em risco a confiabilidade dos números de custo/resultado, e o hard-stop de tarefa multi-talhão ainda impede um cenário operacional legítimo.

### Resposta objetiva

**Parcialmente, com a lacuna mais crítica já fechada.** A aplicação consegue representar ponta a ponta Planejamento→Execução→Recursos→Estoque→Produção→Resultado Econômico para a maioria dos cenários operacionais comuns (agrícola genérico, pecuária individual/coletiva, frota, mão de obra em diária/empreitada), **incluindo agora custo/margem por lote comercializado** (Seção 21). Um ponto concreto de ruptura formal permanece, com evidência de código:

1. **Tarefas multi-talhão**: `SafraTarefa` sem `talhao_id` único não consegue gerar `OperacaoAgricola` (hard-stop explícito em código), impedindo a execução/apontamento formal desse cenário.

Adicionalmente, a confiabilidade dos números de custo segue sob risco pela coexistência ativa e não reconciliada de dois motores de rateio (Rateio-Float vs CostAllocation-Numeric) e pela migração incompleta de tipos monetários em estoque. Quanto ao custo por lote: a fonte oficial já foi decidida (Alternativa C, Seção 21), mas o guardrail ainda é apenas documental — nenhuma UI consome os endpoints ainda, então a decisão precisa ser respeitada manualmente até haver frontend.
