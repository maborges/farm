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
| B | Tarefa multi-talhão | RESOLVIDO (2026-08-15) | Sim | Sim | — | — | — | — | — | — | — | `agricola/tarefas/service.py::TarefaService.criar_multi_talhao`, endpoint `POST /agricola/safras/{safra_id}/tarefas/multi-talhao` | Fechado via fan-out (Seção 21) |
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
- **B. Operações agrícolas**: núcleo genérico via `OperacaoAgricola.tipo/subtipo` cobre teoricamente todas as subcategorias (preparo/plantio/desenvolvimento), mas a granularidade real depende do catálogo (`OperacaoTipoFaseService`), não auditado a fundo — classificado PARCIAL por falta de confirmação, não por ausência de motor. Fitossanitário tem módulo dedicado de monitoramento de pragas/doenças com NDE. Colheita e romaneio maduros e integrados a estoque. Pós-colheita/beneficiamento é **específico a café** (nomenclatura ABIC/SCA) — para outras culturas é GAP de generalização. ~~**GAP confirmado**: `SafraTarefa` sem `talhao_id` não gera `OperacaoAgricola` (hard-stop em `tarefas/service.py:632-636`)~~ — **RESOLVIDO em 2026-08-15** via fan-out (Seção 21). Suspeita de duplicação entre módulos `amostragem_solo/` e `analises_solo/` não resolvida — recomenda-se 2ª auditoria pontual.

## 5. Cobertura Pecuária (C)

Arquitetura dupla deliberada: `EventoAnimal` (individual, enum `TipoEvento` amplo) e `ManejoLote` (coletivo). A maioria das operações da lista C está coberta em ambos os níveis (entrada, movimentação, pesagem, vacina/vermífugo, reprodução, desmama, venda, mortalidade). **GAPs reais**: castração ausente do enum de eventos; alimentação/suplementação só modelada em confinamento, não a pasto; homem-hora de manejo não distinto de apontamento de máquina. **Duplicação confirmada**: `ConfinamentoLote.ganho_medio_diario` (Float, `enterprise/models/sprints_27_33.py:253`) segue divergente de `pecuaria/services/gmd_utils.py::calcular_gmd()` — zero call-sites cruzados, confirma memória. Ordenha é módulo desacoplado do fluxo de eventos padrão. Reprodução tem dois caminhos (eventos básicos vs. módulo de genética/acasalamento) sem integração confirmada.

## 6. Máquinas e Equipamentos (D)

Módulo maduro e bem integrado: cadastro, alocação, apontamento de uso vinculado a `safra_id`/`talhao_id`/`operacao_id`/`production_unit_id`, horímetro/km, abastecimento, manutenção preventiva/corretiva (via `OrdemServico`/`RegistroManutencao`), custo/hora centralizado em `frota_dashboard_detail_service.py`. **GAP real**: nenhuma distinção entre ferramenta de baixo valor e ativo patrimonial depreciável no cadastro de `Equipamento` (só `valor_aquisicao`). Peças de manutenção não confirmadas como integradas ao estoque geral.

## 7. Mão de Obra (E)

Três camadas coexistem por design (estimativa no plano, equipe planejada, execução real) — arquitetura correta, não duplicação acidental. Diária e empreitada cobertos e ligados a safra. **GAP real**: apontamento de mão de obra manual sem uso de equipamento (capina, colheita manual) não tem fluxo dedicado — `ApontamentoUso` exige `equipamento_id` NOT NULL, então trabalho manual puro cai fora desse caminho e depende de `LancamentoDiaria`/`Empreitada`, que são registros 1:1 colaborador-lançamento, sem tabela de equipe associada a uma operação. Múltiplos trabalhadores na mesma operação é, portanto, PARCIAL (suportado por N registros, não por relação estruturada).

## 8. Estoque/Insumos (F)

Fluxo completo entrada/recebimento/depósito/lote/transferência/requisição/retirada/devolução, com separação real entre retirada física e "entrega"/consumo produtivo. FIFO implementado (`estoque_fifo.py`, ordenação por `data_fabricacao`). **GAPs confirmados**: (1) sem tipo de movimento "PERDA" dedicado — cai em ajuste genérico; (2) sem módulo de inventário/contagem cíclica formal; (3) ~~**migração Float→Decimal incompleta**~~ — **RESOLVIDO em 2026-08-15** (Seção 21.4): `SaldoEstoque`, `LoteEstoque`, `ItemRequisicao` e `ReservaEstoque` migrados para `Numeric`, alinhados a `EstoqueMovimento`; (4) vínculo `operacao_execucao_id` no ledger é opcional (nullable), não obrigatório — risco de saída de estoque sem produção vinculada. **Bug pré-existente descoberto durante a migração (5), não relacionado a Float/Numeric**: constraint `ck_estoque_movimentos_origem` no banco não inclui `'PECUARIA_VACINACAO'`, apesar de migrations mais recentes (`20260803_estoque_mov_origem_requisicao.py`) tentarem incluí-la — indício de duas cadeias de migration divergentes (`step24_estoque_movimentos_origem_legado.py` descende de uma branch diferente). Quebra o fluxo de materialização de vacinação em estoque (`ManejoSyncService.processar_tarefa_campo`). Não corrigido nesta rodada — fora do escopo desta tarefa, recomenda-se investigação dedicada da árvore de migrations.

## 9. Compras (G)

Cadeia completa Requisição→Cotação→Aprovação→Pedido→Recebimento→Estoque→Financeiro, com integração real confirmada (mesmo evento de recebimento materializa estoque e despesa financeira, não dois triggers separados). **GAPs**: "necessidade" automática por estoque mínimo não conectada à criação de solicitação; compra de serviços terceirizados sem modelagem própria; combustível e máquinas/equipamentos tratados como produto genérico, sem segregação de ativo/depreciação no fluxo de compra.

## 10. Custos e Financeiro (H)

`CostAllocation` (Numeric) é a apropriação econômica oficial conforme domain-map. **Duplicação re-investigada em 2026-08-15 (ver Adendo, Seção 21.3)**: `Rateio` (`financeiro/models/rateio.py`) coexiste com `CostAllocation`, mas a investigação a fundo mostrou que **não há double-counting ativo hoje** — `Rateio` já é projetado automaticamente e de forma idempotente para `CostAllocation` (`source='FIN_RATEIO'`, `fin_rateio_id`), confirmado 1:1 exato em produção (4 rateios ↔ 4 allocations projetadas, zero sobreposição). O `Float` de `Rateio.valor_rateado`/`percentual` foi corrigido para `Numeric` nesta mesma data. Risco residual, menor do que originalmente classificado: o relatório "Centro de Custos" (`financeiro/services/relatorio_service.py::centro_custos`) lê `Rateio` diretamente, sem unificação com `CostAllocation` — não duplica hoje (relatório isolado), mas pode divergir se algum dia for combinado com o DRE agrícola. Contas a pagar/receber não têm classe dedicada (usa `Despesa`/`Receita`). Depreciação e custos indiretos formais não localizados. Custo planejado×realizado existe a nível de `Cultivo` mas não como relatório consolidado único confirmado.

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
| Rateio vs CostAllocation | Re-investigado 2026-08-15: projeção automática idempotente, sem double-counting; Float→Numeric corrigido | `financeiro/models/rateio.py:8` vs `agricola/custos/models.py:11`, `agricola/custos/allocation_service.py::registrar_allocations_fin_rateio` | BAIXO (era ALTO) |
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
- ~~Tarefa multi-talhão (`SafraTarefa.talhao_id is None`) não gera `OperacaoAgricola`~~ — **RESOLVIDO em 2026-08-15** (Adendo Seção 21). Nenhum GAP CRÍTICO permanece aberto desta auditoria.

**ALTO**
- 3 sistemas de alertas com ponte apenas parcial/unidirecional — risco de alerta "preso" sem chegar ao sino em updates.
- CAR com dois models concorrentes e suspeita de funcionalidade rica (APP, desmatamento, CCIR) não servida pelo router ativo.
- Vínculo `operacao_execucao_id` opcional no ledger de estoque — saída pode ficar sem produção vinculada.
- Infraestrutura fixa (estradas, cercas, poços, galpões) sem workflow de manutenção/custo — só frota móvel tem.
- **NOVO (descoberto em 2026-08-15)**: constraint `ck_estoque_movimentos_origem` no banco desatualizada (não inclui `'PECUARIA_VACINACAO'`), quebrando materialização de vacinação em estoque — indício de cadeias de migration divergentes (Seção 8, Seção 21.4).

**BAIXO (rebaixado em 2026-08-15)**
- ~~Rateio (Float) vs CostAllocation (Numeric) sem exclusividade garantida~~ — investigação confirmou projeção idempotente sem double-counting; `Float` corrigido para `Numeric` (Seção 21.3). Risco residual: relatório "Centro de Custos" ainda lê `Rateio` bruto, sem unificação com `CostAllocation`.
- ~~Float ainda presente em `SaldoEstoque`, `LoteEstoque`, `ItemRequisicao`, `ReservaEstoque`~~ — **RESOLVIDO em 2026-08-15** (Seção 21.4): migrado para `Numeric`, alinhado a `EstoqueMovimento`.

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

1. ~~**Duplicação econômica sem guardrail**: convivência ativa de Rateio e CostAllocation sem mecanismo que impeça o mesmo fato ser rateado duas vezes~~ — **RE-AVALIADO em 2026-08-15** (Seção 21.3): existe guardrail (`fin_rateio_id` + `source='FIN_RATEIO'` + constraint de idempotência), confirmado sem double-counting em produção. Risco residual rebaixado a BAIXO: relatório "Centro de Custos" ainda não unificado com `CostAllocation`.
2. ~~**Migração de tipos incompleta**: parte do domínio de estoque ainda usa `Float`~~ — **RESOLVIDO em 2026-08-15** (Seção 21.4): `SaldoEstoque`, `LoteEstoque`, `ItemRequisicao`, `ReservaEstoque` migrados para `Numeric`, junto com o fix já aplicado em `Rateio` (Seção 21.3). Nenhuma tabela de valor monetário/quantidade conhecida ainda usa `Float`.
3. **Shadowing de pacote Python em `ambiental/`**: arquivo `models.py` e pacote `models/` coexistindo no mesmo namespace é um padrão frágil, propenso a import ambíguo e funcionalidade "fantasma".
4. **Cadeia de "lote" com 3+ nomenclaturas** (ProdutoColhido/LoteBeneficiamento/LoteRastreabilidade/CadernoLoteComercial) aumenta risco de drift entre etapas se alguma atualização não propagar.
5. **Sistemas de alertas fragmentados**: mesmo com ponte parcial, a arquitetura de 3 motores aumenta custo de manutenção e risco de comportamento inconsistente entre eles.
6. ~~**Elo Produção→Resultado quebrado**~~ — **RESOLVIDO em 2026-08-15**: backend calcula custo/margem por lote por 3 vias (Seção 21), fonte oficial decidida (Alternativa C) e já consumida em frontend (tela Produtos Colhidos). Risco residual restrito: DRE/dashboard ainda não consomem a Alternativa A/C — nada impede hoje que uma tela futura use B como se fosse o número final.
7. ~~**Hard-stop de tarefa multi-talhão**~~ — **RESOLVIDO em 2026-08-15** (Seção 21.2): fan-out em N `SafraTarefa` por talhão, sem tocar no modelo de custo/PU. Risco residual: `talhoes_ids` só existe no backend, sem tela de criação multi-talhão no frontend ainda.
8. **NOVO (descoberto em 2026-08-15)**: constraint `ck_estoque_movimentos_origem` desatualizada no banco (falta `'PECUARIA_VACINACAO'`), quebrando a materialização de vacinação em estoque — sintoma de cadeias de migration divergentes (`step24_estoque_movimentos_origem_legado.py` vs `20260803_estoque_mov_origem_requisicao.py`). Não é causado pela migração Float→Numeric desta rodada; recomenda investigação dedicada da árvore de migrations do módulo de estoque (Seção 21.4).

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
1. ~~Investigar e decidir formalmente (produto, não código): Rateio vs CostAllocation~~ — **CONCLUÍDO em 2026-08-15** (Seção 21.3): investigação encontrou projeção automática idempotente já em produção (sem double-counting); `Rateio` migrado de `Float` para `Numeric`. Decisão de produto: manter os dois models (fontes/granularidades diferentes — despesa financeira vs. custo operacional), com `Rateio` permanecendo a origem e `CostAllocation` a agregação oficial. Próximo passo derivado (não crítico): unificar o relatório "Centro de Custos" para ler via `CostAllocation`.
2. ~~Completar a migração Float→Numeric nas 4 tabelas de estoque identificadas~~ — **CONCLUÍDO em 2026-08-15** (Seção 21.4): `SaldoEstoque`, `LoteEstoque`, `ItemRequisicao`, `ReservaEstoque` migrados, junto com ~20 pontos de aritmética em `estoque_service.py`/`estoque_fifo.py`/`compras_service.py`/`agricola/operacoes/service.py` corrigidos para não misturar `Decimal`+`float`. Descoberto durante a correção (não relacionado): constraint `ck_estoque_movimentos_origem` desatualizada, quebrando fluxo de vacinação — recomenda-se investigação dedicada da árvore de migrations de estoque como próximo passo.
3. Confirmar/relatar (2ª auditoria pontual) o shadowing em `ambiental/models.py` vs `ambiental/models/car.py` e decidir qual é o vivo.
4. ~~Endereçar o GAP crítico de custo/margem por lote comercializado~~ — **CONCLUÍDO em 2026-08-15** (Seção 21). ~~Decidir a fonte oficial~~ — **CONCLUÍDO em 2026-08-15**: Alternativa C é a fonte oficial (ver Seção 21). Próximos passos derivados: (i) implementar consumo em frontend usando os endpoints de C; (ii) avaliar tornar `ComercializacaoCommodity.produto_colhido_id` obrigatório (hoje `nullable`).
5. ~~Resolver o hard-stop de tarefa multi-talhão~~ — **CONCLUÍDO em 2026-08-15** (Seção 21): adotado fan-out (dividir a tarefa por talhão), não `OperacaoAgricola` multi-área. Próximo passo derivado: expor `talhoes_ids` no frontend de criação de tarefa (hoje só backend).
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

- **Consumo em frontend parcial**: a tela de Produtos Colhidos (lista + detalhe, consumindo a fonte oficial C) foi implementada em 2026-08-15 (`apps/web/.../produtos-colhidos/`). O formulário de nova comercialização já exige seleção do lote. Ainda faltam: consumo do fan-out multi-talhão (Seção 21.2) e da margem por lote (Alternativa A) em telas de DRE/dashboard.
- **`ComercializacaoCommodity.produto_colhido_id` obrigatório desde 2026-08-15**: resolvido — ver Seção 21.2 abaixo. Comercializações anteriores a essa data sem vínculo (4 registros de teste identificados) seguem fora do rateio por lote, reportadas como aviso `COMERCIALIZACAO_SEM_LOTE_VINCULADO` no DRE — decisão consciente de não fazer backfill (não há dado suficiente no model para inferir o lote correto).
- **Sem backfill histórico**: lotes/comercializações/tarefas anteriores a 2026-08-15 não recebem os novos campos/estrutura automaticamente.

## 21.1 — Adendo (2026-08-15) — `produto_colhido_id` obrigatório na criação

Fecha a recomendação derivada da Seção 20 item 4: `ComercializacaoCreate.produto_colhido_id` passou de opcional para obrigatório (validação Pydantic — erro 422 se ausente). A coluna no banco **permanece `nullable=True`**, sem migration, para não quebrar os registros de teste já existentes sem vínculo (investigação encontrou 4 de 14 comercializações no banco de desenvolvimento com o campo nulo, todas fixtures de teste — o model não guarda `safra_id`/`talhao_id` próprios, então não há como inferir automaticamente o lote correto para backfill). Frontend (`financeiro/comercializacoes/page.tsx`) atualizado para exigir a seleção do lote antes do submit.

## 21.2 — Adendo (2026-08-15) — Hard-stop de tarefa multi-talhão resolvido

Fecha o segundo GAP CRÍTICO da auditoria original (Seções 4, 17, 20): `SafraTarefa` sem `talhao_id` não gerava `OperacaoAgricola` (`BusinessRuleError` em `TarefaService.gerar_operacao_planejada`). Investigação encontrou 3 de 58 `SafraTarefa` em produção já afetadas (nenhuma em status `APROVADA`, então sem bloqueio ativo no momento da correção).

- **Decisão de abordagem**: fan-out (1 tarefa multi-talhão → N `SafraTarefa`, uma por talhão), não "operação multi-área". Justificativa: `OperacaoAgricola.talhao_id` é `NOT NULL`, e `ProductionUnit`/`CostAllocation`/`OperacaoExecucao` são todos ancorados a 1 talhão por vez — redesenhar isso para suportar rateio entre múltiplas `ProductionUnit`s por operação mexeria nos models centrais do fluxo econômico recém-estabilizado pelas Alternativas A/B/C (Seção 21). O padrão de fan-out já existe no código: `PlanoOperacional` documenta explicitamente "um plano cobre tarefas de vários talhões... o fluxo econômico oficial continua sendo gerado tarefa por tarefa" — a correção estende esse mesmo princípio para criação avulsa de tarefa.
- **Evidência**: `TarefaCreate.talhoes_ids` (novo campo, `agricola/tarefas/schemas.py`); `TarefaService.criar_multi_talhao()` (`agricola/tarefas/service.py`) — gera `grupo_geracao_id` compartilhado e cria N `SafraTarefa`; `criar()` simples agora exige `talhao_id` (rejeita `None`); endpoint `POST /agricola/safras/{safra_id}/tarefas/multi-talhao` (`agricola/tarefas/router.py`).
- **Cobertura**: nenhum caller existente (`analises_solo/service.py`, `planejamento_operacional/service.py`) foi afetado — todos já passavam `talhao_id` explícito. As 3 tarefas órfãs legadas não foram tocadas (nenhuma `APROVADA`, sem risco imediato, sem dado suficiente para saber quais talhões pretendiam cobrir).
- **Testes**: `tests/integration/agricola/test_tarefa_multi_talhao.py` (4 casos: fan-out correto com `grupo_geracao_id` compartilhado, rejeição de `criar()` sem talhão, rejeição de `criar_multi_talhao()` sem lista, rejeição com os dois campos preenchidos).
- **O que permanece em aberto**: `talhoes_ids` ainda não é consumido no frontend de criação de tarefa (só backend).

## 21.3 — Adendo (2026-08-15) — Duplicação Rateio vs CostAllocation re-investigada e rebaixada

Fecha o item ALTO da Seção 17/18/20: duplicação econômica entre `Rateio` (`financeiro/models/rateio.py`) e `CostAllocation` (`agricola/custos/models.py`), classificada na auditoria original como "confirmada e ativa, risco real de double-counting".

- **Achado principal**: a investigação a fundo mostrou que **não há dupla contabilização de fato hoje**. A arquitetura já é um sistema de origem→projeção: toda `Despesa` criada com `Rateio` é automaticamente projetada para `CostAllocation` por `registrar_allocations_fin_rateio()` (`agricola/custos/allocation_service.py`), com marca de proveniência (`source='FIN_RATEIO'`, `fin_rateio_id`) e guarda de idempotência (`NOT EXISTS` no `INSERT...SELECT`). Constraint de banco (`step19_cost_allocations.py`) garante consistência entre `source` e `fin_rateio_id`. Em produção: 4 `Rateio` ↔ 4 `CostAllocation` projetadas (1:1 exato), zero despesa com rateio E allocation direta concorrente.
- **Correção aplicada**: `Rateio.valor_rateado`/`percentual` migrados de `Float` para `Numeric(15,2)`/`Numeric(7,4)` — `financeiro/models/rateio.py`, migration `20260815_rateio_float_para_numeric.py` (`op.execute("COMMIT")` após `alter_column`, `postgresql_using` para cast seguro dos dados existentes).
- **Decisão de produto**: manter os dois models — não são duplicação acidental, são granularidades diferentes (`Rateio` = despesa financeira R$→safra/talhão; `CostAllocation` = apropriação de custo por `ProductionUnit`, de múltiplas fontes além de despesas). Unificá-los eliminaria a distinção útil entre "lançamento financeiro de origem" e "apropriação econômica agregada".
- **Risco residual (rebaixado de ALTO para BAIXO)**: o relatório "Centro de Custos" (`financeiro/services/relatorio_service.py::centro_custos`) lê `Rateio` diretamente, sem qualquer verificação cruzada com `CostAllocation` — não duplica hoje porque é um relatório isolado (não soma nada vindo de `CostAllocation`), mas ficaria inconsistente se um dia for combinado com o DRE agrícola. Não endereçado nesta rodada — fix de baixo risco/esforço, mas mexe em relatório financeiro já em uso; recomenda-se tratar isoladamente se/quando houver necessidade real de visão combinada.
- **Testes**: suíte `tarefa`/`despesa`/`rateio` (`tests/test_operational_workflow_governance_step08.py`, `tests/test_dre_agricola_v1.py`) roda sem regressão após a migration. 15 falhas de integração pré-existentes em `test_despesas.py`/`test_launch_core01_operational_cost_engine.py` (permissão 403, mocks quebrados) reconfirmadas idênticas em código não modificado via `git stash` — não relacionadas a esta mudança.

## 21.4 — Adendo (2026-08-15) — Migração Float→Numeric em estoque concluída

Fecha o item ALTO restante da Seção 8/17/18/20: `SaldoEstoque`, `LoteEstoque`, `ItemRequisicao` e `ReservaEstoque` (`operacional/models/estoque.py`) ainda usavam `Float`, enquanto `EstoqueMovimento` (o ledger) já usava `Numeric`.

- **Achado principal**: investigação mostrou que o código já convertia todo valor para `float` nativo do Python na leitura, independente do tipo da coluna no banco (`Numeric` ou `Float`) — ou seja, só trocar o tipo da coluna sem tocar a aritmética não eliminaria o erro de arredondamento de fato, só o armazenamento. Optado por escopo cirúrgico (trocar tipo de coluna + corrigir os pontos que quebrariam) em vez de reescrever toda a aritmética para `Decimal` nativo (~2080 linhas em `estoque_service.py`/`estoque_fifo.py`, alto risco).
- **Migração de schema**: 9 colunas migradas (`quantidade_atual`/`quantidade_reservada` em `SaldoEstoque`; `quantidade_inicial`/`quantidade_atual`/`custo_unitario` em `LoteEstoque`; `quantidade_solicitada`/`quantidade_aprovada`/`quantidade_entregue`/`quantidade_devolvida` em `ItemRequisicao`; `quantidade` em `ReservaEstoque`) — `Numeric(18,6)` para quantidades, `Numeric(15,6)` para custo unitário, seguindo a precisão já usada em `EstoqueMovimento`. Migration `20260815_estoque_float_para_numeric.py`.
- **Correção de código necessária (confirma a memória `project_ledger_estoque_float.md`: "fix real exige refatoração ampla")**: a troca de tipo isolada quebrou em runtime (`TypeError: unsupported operand type(s) for -=: 'decimal.Decimal' and 'float'`) em ~20 pontos de aritmética `+=`/`-=`/`sum()` em `operacional/services/estoque_service.py`, `operacional/services/estoque_fifo.py`, `operacional/services/compras_service.py` e `agricola/operacoes/service.py`, todos corrigidos para normalizar para `float` explicitamente antes de operar (mesma convenção já usada no resto do código-base), sem reescrever para `Decimal` nativo.
- **Bug pré-existente descoberto durante a correção, não relacionado**: constraint `ck_estoque_movimentos_origem` no banco não inclui `'PECUARIA_VACINACAO'`, apesar de uma migration mais recente (`20260803_estoque_mov_origem_requisicao.py`) tentar incluí-la — sintoma de cadeias de migration divergentes (`step24_estoque_movimentos_origem_legado.py` descende de uma branch diferente). Quebra `ManejoSyncService.processar_tarefa_campo` para vacinação. **Não corrigido nesta rodada** — fora do escopo desta tarefa (Float→Numeric), registrado como novo item ALTO (Seção 17/18) para investigação dedicada da árvore de migrations.
- **Testes**: 49 testes de regressão de estoque/FIFO/compras/DRE passando (`test_fifo_estoque.py`, `test_valuation_guardrails.py`, `test_estoque_reposicao.py`, `test_compras_guardrails.py`, `test_e2e_colheita_completa.py`, `test_dre_agricola_v1.py`, `test_compras_lote_integration.py`, `test_operacao_reversao_economica.py`, `test_alertas_estoque_minimo_contextual.py`). 11 falhas em testes de vacinação pecuária (`test_lote_resumo_sanitario.py`, `test_manejo_sync_service.py`, `test_sync_pecuaria_integration.py`) isoladas à mesma causa raiz do bug pré-existente acima (`ck_estoque_movimentos_origem`), não à migração Float→Numeric.

---

## STATUS DA COBERTURA OPERACIONAL: **PARCIAL**

A aplicação cobre com solidez a maior parte do ciclo agrícola, pecuário, de máquinas e de mão de obra, com um núcleo arquitetural coerente (ProductionUnit/CostAllocation/OperacaoAgricola). Os dois GAPs CRÍTICOS originais (elo Produção→Resultado quebrado, e hard-stop de tarefa multi-talhão) foram resolvidos em 2026-08-15 (Seção 21) — nenhum ponto de ruptura formal (hard-stop de código) permanece identificado por esta auditoria. A duplicação Rateio vs CostAllocation, antes classificada ALTO, foi re-investigada e rebaixada a BAIXO (Seção 21.3) — não há double-counting ativo. A migração Float→Numeric em estoque foi concluída (Seção 21.4) — nenhuma tabela de valor monetário/quantidade conhecida ainda usa `Float`. O status segue **PARCIAL**, não "ADEQUADA/MADURA", porque 3 sistemas de alertas fragmentados, o CAR com dois models concorrentes, e o bug de migration recém-descoberto (`ck_estoque_movimentos_origem` quebrando vacinação) continuam colocando em risco a confiabilidade/disponibilidade de fluxos operacionais específicos — riscos pontuais, não mais sistêmicos de tipo de dado ou double-counting.

### Resposta objetiva

**Sim, com as duas lacunas mais críticas já fechadas.** A aplicação consegue representar ponta a ponta Planejamento→Execução→Recursos→Estoque→Produção→Resultado Econômico para a totalidade dos cenários operacionais mapeados nesta auditoria (agrícola genérico — inclusive multi-talhão via fan-out —, pecuária individual/coletiva, frota, mão de obra em diária/empreitada), **incluindo custo/margem por lote comercializado** (Seção 21). Nenhum hard-stop de código impede formalmente um cenário operacional legítimo até o momento desta atualização.

A confiabilidade dos números de custo segue sob risco — não por ausência de funcionalidade, mas por qualidade/consistência dos dados — pela coexistência ativa e não reconciliada de dois motores de rateio (Rateio-Float vs CostAllocation-Numeric) e pela migração incompleta de tipos monetários em estoque. Quanto ao custo por lote: a fonte oficial já foi decidida (Alternativa C, Seção 21) e o frontend já a consome (tela Produtos Colhidos); resta apenas expandir esse consumo para DRE/dashboard e para o novo fluxo multi-talhão.
