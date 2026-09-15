# TRAINING-CURRICULUM-01 — Auditoria de Fluxos e Estrutura da Academia DeepFarms

**Data da auditoria:** 2026-09-14
**Escopo:** leitura do monorepo `/opt/lampp/htdocs/farm`
**Alterações de produto:** nenhuma
**Veredicto:** **GO COM RESSALVAS**

## 1. Resumo executivo

A DeepFarms possui um núcleo funcional suficiente para começar a desenhar a Academia e uma POC controlada de vídeos: Core/implantação, cadastros, estrutura territorial, safra, planejamento, tarefas/operações, Campo/PWA, estoque/compras, colheita/pós-colheita, financeiro, custos/DRE e indicadores. O fluxo operacional agrícola documentado e apoiado por código é:

```text
Plano sugerido → aprovação humana → tarefa → operação/execução
→ consumo/estoque → custo/CostAllocation → DRE → analytics → prioridades
```

Esse encadeamento está explicitamente declarado em `docs/architecture/agricultural-operational-cycle.md` e possui evidências em routers, services e testes. Há também fluxos de compra/recebimento, requisição/entrega, colheita/romaneio/beneficiamento, pecuária/manejo e integração ERP.

As principais ressalvas para treinamento são:

- `Tarefa` e `OperaçãoAgricola` são caminhos relacionados, mas não equivalentes: concluir tarefa, especialmente no Campo, não garante baixa de estoque nem lançamento financeiro; a operação realizada é o caminho confirmado para consumo/custo.
- O orçamento de safra é itemizado e mutável, mas não possui agregado versionado/aprovação/histórico confiável. A auditoria existente recomenda não ensinar “revisão orçamentária” como processo fechado.
- O Campo é offline-first e depende de `sync/pull`/`sync/push`, reconciliação e estados de erro; a gravação automatizada deve começar apenas com fixtures controladas.
- A interface ainda contém caminhos globais e contextuais concorrentes. A página `/aprendizado` existente é um conjunto de atalhos para telas, não uma Academia estruturada.
- Contabilidade complexa, alguns caminhos Enterprise, integrações externas e parte de RH/ambiental devem ficar fora da primeira leva de vídeos operacionais.

Portanto, a Academia pode iniciar a curadoria e a POC de gravação de um subconjunto seguro, mas não deve prometer cobertura integral do produto nem transformar a árvore de menus em currículo.

## 2. Metodologia

Foi feita auditoria somente leitura, cruzando:

1. rotas e páginas em `apps/web` e `apps/campo`;
2. registro de routers em `services/api/main.py`;
3. routers, services, models e schemas de cada domínio;
4. testes unitários, integração, E2E e smoke;
5. documentação de arquitetura, contextos, guias, runbooks e relatórios de implementação;
6. divergências entre documentação histórica, UI e comportamento suportado no código.

O código foi tratado como evidência primária para existência de comportamento; a documentação foi usada para semântica, dependências e decisões já consolidadas. Documentos de implementação foram tratados como evidência histórica e não como prova automática de que cada afirmação continua válida.

Não foram executadas migrations, não houve acesso/escrita em banco, não foram instaladas dependências, não foi implementado Playwright, nem qualquer pipeline de vídeo.

## 3. Inventário dos módulos/domínios encontrados

| Módulo/domínio real | O que o usuário faz | Evidência principal | Leitura funcional |
|---|---|---|---|
| Comece por aqui / Core SaaS | autentica, escolhe tenant, configura implantação e acessos | `services/api/main.py:295-321`; `apps/web/src/app/(auth)/login/page.tsx`; `docs/contexts/core/_implantation-workflow.md` | **Confirmado** |
| Unidade produtiva e território operacional | cadastra fazenda/unidade, áreas, glebas, talhões e visão territorial | `main.py:346-367`; `docs/architecture/agrosaas-domain-map.md`; `docs/guias/hierarquia-propriedade-fazenda-gleba-talhao-piquete.md` | **Confirmado com ressalvas** pela fronteira com imóveis |
| Imóveis rurais/fundiário | registra titularidade, matrícula, CAR, documentos, arrendamentos e avaliações | `main.py:360-365`; `docs/architecture/standards/AGRI-DOMAIN-001-territorial-fundiario.md`; `docs/contexts/imoveis/` | **Confirmado com ressalvas**; jurídico e operacional são domínios distintos |
| Pessoas, equipe e RH | cadastra clientes, fornecedores, funcionários, diárias, SST e eSocial | `main.py:348,550`; `services/api/rh/schemas.py`; `docs/contexts/pessoas/` | **Confirmado** no essencial; Enterprise parcial |
| Produtos, unidades e cadastros mestres | cadastra produtos/insumos, culturas, commodities, unidades de medida e tipos de operação | `main.py:355-359,369`; `apps/web/src/app/(dashboard)/backoffice/tabelas/`; `docs/contexts/estoque/essencial/cadastro-produtos.md` | **Confirmado** |
| Agrícola / safra | cria safra, vincula talhões, muda fases e consulta a safra | `main.py:466-479`; `apps/web/src/app/(dashboard)/agricola/safras/page.tsx:42-60`; `services/api/tests/integration/agricola/test_safras.py` | **Confirmado** |
| Planejamento agrícola | orçamento básico, plano operacional, necessidades e cenários | `main.py:491,500-502`; `docs/implementation/reports/ORCAMENTO-SAFRA-01-AUDITORIA-ARQUITETURAL.md`; testes de planejamento | **Confirmado com ressalvas** |
| Solo/agricultura de precisão/clima | registra análise, recomenda, consulta NDVI/previsão e clima | `main.py:486-490,510-511`; `docs/implementation/reports/SOIL-PLAN-EXEC-01-AUDITORIA-LAUDO-PLANEJAMENTO-EXECUCAO-CUSTOS.md`; `docs/guias/GUIA-USUARIO-DADOS-CLIMATICOS.md` | análise/NDVI/clima confirmados; cadeia completa é parcial |
| Operações/tarefas/caderno | planeja trabalho, executa, registra evidência e caderno | `main.py:480,499-503`; `apps/campo/src/app/(campo)/tarefas/page.tsx`; `docs/guias/manual-lancamentos-campo-consumo-financeiro-rastreabilidade.md` | **Confirmado com ressalvas** |
| Campo/PWA offline | sincroniza contexto, executa tarefas, lança aplicação/colheita/pesagem/manejo | `services/api/campo/router.py:624-699`; `services/api/campo/service.py:691-1455`; `apps/campo/src/app/(campo)/sync/page.tsx` | **Confirmado com fixtures** |
| Estoque | implanta saldo inicial, recebe, movimenta, conta, ajusta e rastreia lotes | `main.py:324-326`; `apps/web/src/app/(dashboard)/suprimentos/page.tsx:44-99`; testes `test_estoque*`, `test_fifo_estoque.py` | **Confirmado** no essencial |
| Requisições e compras | solicita, aprova, separa/entrega, compra, recebe parcialmente e devolve | `main.py:329-330`; `docs/implementation/reports/LAUNCH-W4-REQUISICAO-OS-CAMPO-ESTOQUE-FINANCEIRO-RENTABILIDADE.md`; `services/api/tests/integration/operacional/test_compras.py` | **Confirmado com ressalvas** |
| Frota/oficina/abastecimento | cadastra equipamento, controla jornada, checklist, combustível e manutenção | `main.py:322,327,331-335`; `apps/web/src/app/(dashboard)/operacional/page.tsx:17-73`; testes de frota | **Confirmado** |
| Colheita/pós-colheita | registra produto colhido, romaneio, qualidade e beneficiamento | `main.py:482-485`; testes `test_beneficiamento*`, `test_qualidade_romaneio.py`; `docs/implementation/reports/LAUNCH-W3-COLHEITA-ESTOQUE-COMERCIALIZACAO-FINANCEIRO.md` | **Confirmado com ressalvas** |
| Lotes/rastreabilidade/certificação | consulta origem, aplicações, cadeia de custódia e passaporte público | `main.py:495-497,529`; `apps/web/src/app/p/rastreabilidade/[token]/page.tsx`; `docs/contexts/rastreabilidade/` | **Confirmado com ressalvas** |
| Financeiro/econômico | lança receitas/despesas, contas, concilia, consulta custos, DRE e rentabilidade | `main.py:554-577`; `docs/architecture/agricultural-operational-cycle.md`; testes financeiros e `test_dre_v1_endpoint.py` | **Confirmado** no realizado; orçamento ressalvado |
| Comercialização/hedge | registra venda/romaneio, contratos, exposição e MTM | `main.py:573-574`; `apps/web/src/app/(dashboard)/dashboard/financeiro/hedge/`; testes Enterprise hedge | **Confirmado com ressalvas** |
| Pecuária | cadastra animais/lotes/piquetes, maneja, pesa, vacina, reproduz, leite/confinamento | `main.py:555-564`; `apps/web/src/app/(dashboard)/dashboard/pecuaria/`; `services/api/tests/integration/test_pecuaria.py` | **Confirmado** em subfluxos; cadeia econômica varia |
| Ambiental/ESG/carbono | gerencia CAR, outorgas, alertas, emissões, projetos, evidências e relatórios | `main.py:577`; `apps/web/src/app/(dashboard)/dashboard/ambiental/`; `docs/contexts/compliance/` | **Confirmado com ressalvas**; forte dependência documental |
| Integrações | configura/testa ERP, OpenWeather, Sankhya, balança e IoT | `main.py:538-549`; `apps/web/src/app/integracoes/`; `docs/implementation/reports/INTEGRATIONS-LIFECYCLE-01-CICLO-DE-VIDA-INTEGRACOES.md` | **Confirmado com ressalvas**; provider/configuração dependem do tenant |
| Notificações/recomendações/IA | recebe alertas, recomendações, diagnóstico e prioridades | `main.py:551-553`; `services/api/recommendations/`; `apps/web/src/app/(dashboard)/dashboard/inteligencia-operacional/` | **Confirmado como apoio à decisão**, não execução automática |
| Contabilidade/Enterprise legado | busca lançamentos contábeis, integrações complexas e BI | `main.py:533-537,547-548` | **Parcial / não implementado em partes**; routers comentados são evidência de exclusão da primeira trilha |

## 4. Mapa dos principais fluxos operacionais

| Fluxo | Início | Etapas principais | Resultado | Módulos envolvidos | Status | Evidências |
|---|---|---|---|---|---|---|
| Implantar uma operação rural | onboarding/tenant autenticado | login/tenant → unidade produtiva → território → equipe/produtos/equipamentos → configurações | ambiente mínimo pronto para operar | Core, território, pessoas, cadastros | **CONFIRMADO COM RESSALVAS** | `docs/contexts/core/_implantation-workflow.md`; `main.py:295-367` |
| Estruturar território e fundiário | cadastro de propriedade/imóvel | propriedade operacional → áreas/talhões → imóvel/documentos → vínculo N:N quando aplicável → visões | território operacional e lastro jurídico separados | Territorial, Fundiário, ESG | **CONFIRMADO COM RESSALVAS** | `docs/architecture/standards/AGRI-DOMAIN-001-territorial-fundiario.md`; `main.py:352-365` |
| Preparar cadastro operacional | tabelas/cadastros | pessoas → produtos/unidades → fornecedores/clientes → equipamentos → plano de contas | referências disponíveis para lançamentos | Cadastros, RH, Frota, Financeiro, Estoque | **CONFIRMADO** | `docs/workflow-gestao-safra.md`, fase 0; `docs/contexts/estoque/essencial/` |
| Planejar safra | lista de safras | criar safra → vincular talhões/cultivos → planejar operações/necessidades → orçamento/cenário → aprovação humana | plano utilizável como base de tarefas | Agrícola, Planejamento, Financeiro | **CONFIRMADO COM RESSALVAS** | `docs/workflow-gestao-safra.md`; `docs/implementation/reports/ORCAMENTO-SAFRA-01-AUDITORIA-ARQUITETURAL.md` |
| Analisar solo e decidir tratamento | análise de solo da safra/talhão | coletar/registrar laudo → calcular indicadores → gerar recomendação/prescrição → decisão técnica → operação | recomendação documentada; execução continua humana | Solo, Agrícola, Planejamento, Estoque, Operação | **CONFIRMADO COM RESSALVAS** | `docs/implementation/reports/SOIL-PLAN-EXEC-01-AUDITORIA-LAUDO-PLANEJAMENTO-EXECUCAO-CUSTOS.md`; `test_prescricoes_vra.py` |
| Executar operação agrícola com custo | safra/talhão ou tarefa | criar/selecionar operação → marcar realizada → informar recursos/insumos → registrar execução → baixa/consumo → apropriar custo | operação rastreada, estoque reduzido quando aplicável e custo disponível | Agrícola, Campo, Estoque, Financeiro, Caderno | **CONFIRMADO** | `docs/architecture/agricultural-operational-cycle.md`; `docs/guias/manual-lancamentos-campo-consumo-financeiro-rastreabilidade.md`; testes de cost allocation |
| Executar tarefa simples | tarefas da safra ou Campo | criar tarefa → atribuir → iniciar → concluir/invalidar | tarefa e auditoria de execução | Agrícola, Operacional, Campo | **CONFIRMADO COM RESSALVAS** | `docs/guias/manual-lancamentos-campo-consumo-financeiro-rastreabilidade.md`; `services/api/campo/router.py:454-507` |
| Executar no Campo offline | dispositivo ativado | pull de contexto → operar sem rede → persistir localmente → push → materializar efeitos → tratar erro/retry | estado local e servidor reconciliados | Campo, Agrícola, Pecuária, Caderno | **CONFIRMADO COM FIXTURES** | `services/api/campo/router.py:624-699`; `services/api/campo/service.py:691-1455`; testes Campo |
| Abastecer e manter frota | painel da frota | equipamento → jornada/checklist → abastecimento → manutenção/ordem → custo/indicador | disponibilidade, consumo e custo de ativo | Frota, Oficina, Financeiro, Operação | **CONFIRMADO** | `apps/web/src/app/(dashboard)/operacional/page.tsx:17-73`; `main.py:322,327,331-335` |
| Requisitar e comprar insumo | requisição/compras | requisitar → aprovar → separar/entregar ou cotar → aprovar pedido → receber/devolver | material disponível ou baixado, com rastreabilidade de origem | Compras, Estoque, Operacional, Financeiro | **CONFIRMADO COM RESSALVAS** | `LAUNCH-W4...md`; `services/api/tests/integration/operacional/test_compras.py` |
| Colher e fechar produção | safra em colheita | registrar colheita/produto → romaneio/pesagem → qualidade → lote → beneficiamento/armazenagem | produção e lote rastreáveis; possível receita | Agrícola, Campo, Balança, Estoque, Comercialização, Financeiro | **CONFIRMADO COM RESSALVAS** | `LAUNCH-W3...md`; `test_beneficiamento_generico.py`; `test_romaneio_balanca_integration.py` |
| Vender produção | lote/romaneio ou comercialização | comprador/contrato → venda/romaneio → emissão/registro financeiro quando configurado | comercialização registrada e receita/reflexos | Comercialização, Financeiro, Estoque, Rastreabilidade | **CONFIRMADO COM RESSALVAS** | `docs/contexts/comercializacao/`; `main.py:482-485,573` |
| Gerir caixa e resultado | dashboard financeiro/DRE | contas/plano → receitas/despesas → pagar/receber → conciliar → custos/DRE → rentabilidade | visão de realizado e indicadores econômicos | Financeiro, Agrícola, Analítico | **CONFIRMADO** para realizado | `main.py:554-577`; `test_dre_v1_endpoint.py`; ciclo operacional oficial |
| Gerir pecuária | rebanho/lotes | cadastrar animal → lotear/piquetear → manejo sanitário/reprodutivo/nutricional → pesagem/produção → indicadores | histórico e indicadores do rebanho | Pecuária, Campo, Estoque, Financeiro | **CONFIRMADO COM RESSALVAS** | `services/api/pecuaria/services/`; `test_pecuaria.py`; telas em `dashboard/pecuaria` |
| Gerir conformidade ambiental | dashboard ambiental | CAR/outorga/documento → alerta/evidência → não conformidade → plano/relatório/passaporte | evidência e acompanhamento de compliance | Ambiental, Territorial/Fundiário, ESG | **CONFIRMADO COM RESSALVAS** | `main.py:354,577`; `docs/contexts/compliance/`; telas ambientais |
| Configurar integração ERP/clima/balança | configurações | selecionar/configurar provider → testar → sincronizar/acompanhar job → reconciliar | dados externos associados ao tenant | Integrações, Cadastros, Financeiro, Clima, Balança | **CONFIRMADO COM RESSALVAS** | `main.py:538-549`; `docs/implementation/reports/INTEGRATIONS-LIFECYCLE-01-CICLO-DE-VIDA-INTEGRACOES.md` |

### 4.1 Atores, estados e regras que devem aparecer no ensino

- **Produtor/gestor:** configura contexto, aprova plano, acompanha resultado e decide prioridades.
- **Agrônomo/técnico:** interpreta solo, recomenda tratamento, define operação e valida resultado agronômico.
- **Operador de campo:** executa tarefa/operação, registra evidências e trabalha no PWA.
- **Almoxarife/compras:** controla saldo, requisição, compra, recebimento, separação e devolução.
- **Financeiro:** mantém plano de contas, receitas/despesas, pagamentos/recebimentos, conciliação e leitura do realizado.
- **Responsável pecuário/RH/ambiental:** atua nos subfluxos próprios, respeitando permissões e módulos contratados.

Estados educacionalmente relevantes: `PLANEJADA`, fases `PREPARO_SOLO`, `PLANTIO`, `DESENVOLVIMENTO`, `COLHEITA`, `POS_COLHEITA`, `ENCERRADA`, além de estados de tarefa, pedido, requisição, sync e aprovação. A regra central é que recomendação/prioridade não executa operação: aprovação humana cria a tarefa, a execução gera evidência e o custo nasce da apropriação oficial.

## 5. Fluxos transversais entre módulos

| Cadeia confirmada | Efeito e evidência | Como ensinar |
|---|---|---|
| Operação agrícola → estoque → custo → DRE/analytics | operação realizada pode consumir insumos; `CostAllocation` é a apropriação oficial e a DRE usa realizado | uma aula de fluxo, com uma operação simples e validação em estoque/custos |
| Tarefa/OS → requisição → entrega → estoque → financeiro/rentabilidade | entrega reduz estoque; relatório `LAUNCH-W4...md` documenta passagem de safra/origem | separar tarefa da aula de consumo; demonstrar vínculo de origem |
| Colheita → romaneio/pesagem → produto/lote → beneficiamento → comercialização/receita | testes de produto colhido, romaneio, beneficiamento e integração balança | um processo pós-colheita com ressalva de configuração |
| Solo → recomendação/prescrição → planejamento → operação → custo | há testes e relatórios específicos, mas a decisão é humana e nem toda recomendação implica execução | ensinar “interpretar e decidir”, não prometer automação |
| Campo offline → sync → materialização agrícola/pecuária → caderno | `sync_push` processa efeitos e deixa falhas para retry; `sync_pull` entrega contexto e tombstones | aula específica de sync, com cenário determinístico |
| Pessoa/fornecedor/produto → compras/estoque/financeiro | cadastros mestres são compartilhados por múltiplos módulos | conceitos curtos antes de compras e financeiro |
| Propriedade ↔ imóvel rural → rastreabilidade/ESG | vínculo oficial é N:N, com ownership operacional e jurídico separados | duas microaulas: território operacional e documentação fundiária |
| Clima/OpenWeather → resumo/alerta/recomendação | rotas climáticas e integração existem; ingestão depende de provider/configuração | aula de leitura de previsão/alerta; configuração como CUSTOMER |
| ERP/Sankhya → pessoa/produto/jobs → cadastro canônico | políticas controlam execução e modos de sync; importação de pessoas por ID tem contrato próprio | aula avançada e manualmente revisada |

## 6. Matriz de aderência dos fluxos

| Fluxo | UI/rota | API/router | service/domínio | persistência/efeito | teste/documentação | Classificação |
|---|---|---|---|---|---|---|
| Login/tenant/implantação | presente | `auth`, `onboarding`, `team`, `configuration` registrados | Core/RBAC | tenant, sessão, configuração | testes `integration/core` e runbook Core | **CONFIRMADO** |
| Safra/fases/talhões | `/agricola/safras` e contexto da safra | `router_safras`, `router_cultivos`, `router_talhoes` | modelos/services Agrícola | Safra, Cultivo, vínculo de área | `test_safras.py`, workflow agrícola | **CONFIRMADO** |
| Orçamento de safra | telas globais/contextuais | planejamento/A1 | itens e snapshots | item mutável, sem versão de negócio | `ORCAMENTO-SAFRA...` | **CONFIRMADO COM RESSALVAS** |
| Plano sugerido/aprovação/tarefa | telas de planejamento/tarefas | recomendações, prioridades, tarefas | ciclo operacional oficial | tarefa e origem | testes de recomendações/tarefas | **CONFIRMADO COM RESSALVAS** |
| Operação/execução/consumo/custo | execução da safra e Campo | operações, caderno, campo sync | execução + allocation | estoque, custo, evento | testes de cost allocation e guias | **CONFIRMADO** |
| Estoque/contagem/FIFO/lotes | suprimentos | estoque, contagem, implantação | estoque service | movimentos/lotes/saldos | `test_estoque*`, FIFO | **CONFIRMADO** |
| Compras/requisição/recebimento | suprimentos/compras | compras, requisições | compras/estoque | pedido, recebimento, movimento | `test_compras.py`, LAUNCH-W4 | **CONFIRMADO COM RESSALVAS** |
| Colheita/romaneio/beneficiamento | Agrícola e Campo | produto colhido, romaneio, qualidade, beneficiamento | pós-colheita | lotes, produto, qualidade | testes agrícolas e LAUNCH-W3 | **CONFIRMADO COM RESSALVAS** |
| Financeiro/DRE/rentabilidade | dashboard financeiro/custos | financeiro, custos, DRE, rentabilidade | `CostAllocation`, DRE v1 | lançamentos e agregações | testes financeiro/agricola | **CONFIRMADO** no realizado |
| PWA Campo | home/tarefa/sync/aplicação/colheita | `/sync/pull`, `/sync/push`, Campo | processamento idempotente/retry | cache local + tarefa/evento remoto | testes Campo/PWA | **CONFIRMADO COM FIXTURES** |
| Pecuária | dashboard pecuária e Campo | lotes, animais, manejos, sync | manejo, pesagem, reprodução | animais, lotes, eventos | `test_pecuaria.py` e testes específicos | **CONFIRMADO COM RESSALVAS** |
| Ambiental/ESG | dashboard ambiental | ambiental e certificações | CAR, alertas, evidências, relatórios | documentos/evidências | testes ESG e compliance docs | **CONFIRMADO COM RESSALVAS** |
| Integrações externas | `/integracoes/*` e settings | ERP, Sankhya, OpenWeather, Tara, IoT | providers/jobs/policies | jobs, políticas, vínculos externos | relatórios ERP/integration | **CONFIRMADO COM RESSALVAS** |
| Contabilidade Enterprise | rotas comentadas em parte | alguns routers não registrados | migração/refatoração AsyncSession | não há caminho completo único | routing map e `main.py:533-548` | **PARCIAL / NÃO IMPLEMENTADO** |

## 7. GAPs de fluxo/UX encontrados

Os itens abaixo são observações para revisão; nenhum foi corrigido nesta fase.

1. **GAP DE FLUXO/UX PARA REVISÃO — Academia atual é atalho de telas.** `apps/web/src/app/(dashboard)/aprendizado/page.tsx:8-16` exibe quatro cartões e o botão “Abrir tela”; não há módulo → processo → assunto → microaula, busca, tags ou ajuda contextual.
2. **GAP DE FLUXO/UX PARA REVISÃO — rotas globais versus contexto da safra.** `docs/guias/workflow-agricultura.md` descreve telas globais e `/agricola/safras/{id}/*`; isso precisa ser explicitado no ensino para o usuário não alternar entre caminhos sem entender o contexto.
3. **GAP DE FLUXO/UX PARA REVISÃO — tarefa não deixa claro o efeito econômico.** A documentação de lançamentos afirma que tarefa isolada não garante estoque/financeiro; a operação realizada é o caminho de cadeia completa. A aula deve tornar essa decisão visível.
4. **GAP DE FLUXO/UX PARA REVISÃO — orçamento versus planejamento operacional.** `ORCAMENTO-SAFRA-01-AUDITORIA-ARQUITETURAL.md` registra itens mutáveis, snapshots e ausência de versão/aprovação formal. Não usar “aprovar orçamento” como resultado confirmado sem ressalva.
5. **GAP DE FLUXO/UX PARA REVISÃO — feedback do sync.** `services/api/campo/router.py:657-699` preserva falhas de efeitos colaterais para retry. A gravação precisa mostrar estados `PENDING/ERROR/DONE` reais e não assumir conclusão imediata.
6. **GAP DE FLUXO/UX PARA REVISÃO — múltiplos entry points para suprimentos.** A página de suprimentos expõe saldos, almoxarifado, implantação assistida, compras, lotes e requisições (`.../suprimentos/page.tsx:44-99`); o curso deve organizar por objetivo, não por cartão.
7. **GAP DE FLUXO/UX PARA REVISÃO — territorial/fundiário.** Propriedade é operacional; imóvel rural é jurídico/documental; o vínculo N:N não deve ser ensinado como duplicação de cadastro.
8. **GAP DE FLUXO/UX PARA REVISÃO — branding histórico.** Há documentação e assets legados com AgroSaaS/FarmOS; o material novo desta Academia deve usar somente DeepFarms, sem search-and-replace nesta auditoria.
9. **GAP DE FLUXO/UX PARA REVISÃO — estados de produção não são universais.** O ciclo da UI de safra mostra fases agrícolas, enquanto pecuária, compras, sync e financeiro possuem estados próprios; uma aula transversal deve definir o contexto de cada estado.
10. **GAP DE FLUXO/UX PARA REVISÃO — dependência de feature gates/permissões.** Módulos ambientais, ERP, ESG e Enterprise podem não estar visíveis para todos os tenants; a trilha deve distinguir pré-requisito funcional de acesso contratado.

## 8. Estrutura proposta da Academia DeepFarms

### 8.1 Taxonomia

```text
Academia DeepFarms
├── 00 Comece por Aqui
├── 01 Implantação e Cadastros
│   ├── Processo: acessar e preparar o ambiente
│   ├── Processo: estruturar território e cadastros mestres
│   └── Processo: configurar Campo e integrações
├── 02 Agrícola: Safra e Planejamento
│   ├── Processo: criar e contextualizar a safra
│   ├── Processo: planejar atividades e custos
│   └── Processo: usar solo, clima e monitoramento
├── 03 Operação e Campo
│   ├── Processo: transformar plano em execução
│   ├── Processo: operar online/offline
│   └── Processo: consumo, frota e evidências
├── 04 Estoque, Compras e Pós-Colheita
│   ├── Processo: saldo e movimentação
│   ├── Processo: requisição, compra e recebimento
│   └── Processo: colheita, lotes e beneficiamento
├── 05 Financeiro e Comercialização
│   ├── Processo: receitas, despesas e contas
│   ├── Processo: custos/DRE/rentabilidade
│   └── Processo: venda, romaneio e hedge
├── 06 Pecuária
├── 07 Ambiental, ESG e Rastreabilidade
└── 08 Gestão, Indicadores e Recomendações
```

Cada aula deve possuir uma única identidade curricular e múltiplas relações de busca/contexto. Não criar uma cópia por rota.

### 8.2 Campos mínimos do catálogo

`id`, módulo, processo, assunto, objetivo, tipo, resumo, duração, público, automação, pré-requisito funcional, pré-requisito pedagógico, rotas relacionadas, entidades, palavras-chave e evidências do fluxo.

## 9. Catálogo inicial de microaulas

| ID | Módulo | Processo/Assunto | Aula | Tipo | Duração | Público | Automação | Pré-requisitos |
|---|---|---|---|---|---:|---|---|---|
| DF-00.01 | Comece por Aqui | Visão do produto | Conheça a DeepFarms | CONCEITO | 3 min | BOTH | MANUAL_REVIEW_REQUIRED | nenhum |
| DF-00.02 | Comece por Aqui | Navegação por objetivo | Encontre um processo sem seguir o menu inteiro | COMO FAZER | 2 min | BOTH | AUTOMATION_READY | login |
| DF-01.01 | Implantação | Identidade e acesso | Entrar, selecionar tenant e entender perfis | COMO FAZER | 3 min | CUSTOMER | AUTOMATION_WITH_FIXTURES | usuário/tenant de demonstração |
| DF-01.02 | Implantação | Unidade produtiva | Cadastrar a unidade/fazenda operacional | COMO FAZER | 4 min | CUSTOMER | AUTOMATION_WITH_FIXTURES | tenant |
| DF-01.03 | Implantação | Território | Organizar propriedade, áreas, glebas e talhões | FLUXO | 5 min | BOTH | AUTOMATION_WITH_FIXTURES | unidade produtiva |
| DF-01.04 | Implantação | Fundiário | Diferenciar imóvel rural de propriedade operacional | CONCEITO | 3 min | BOTH | MANUAL_REVIEW_REQUIRED | estrutura territorial recomendada |
| DF-01.05 | Cadastros | Pessoas e parceiros | Cadastrar pessoa, fornecedor e comprador | COMO FAZER | 4 min | CUSTOMER | AUTOMATION_WITH_FIXTURES | tenant |
| DF-01.06 | Cadastros | Produtos e equipamentos | Preparar insumos, unidades e ativos para operar | FLUXO | 5 min | CUSTOMER | AUTOMATION_WITH_FIXTURES | pessoa/unidade |
| DF-01.07 | Configuração | Estoque inicial | Implantar saldo inicial sem misturar com operação normal | COMO FAZER | 4 min | CUSTOMER | AUTOMATION_WITH_FIXTURES | produto, depósito |
| DF-02.01 | Agrícola | Safra | Criar uma safra e entender suas fases | COMO FAZER | 4 min | BOTH | AUTOMATION_WITH_FIXTURES | unidade, cultura |
| DF-02.02 | Agrícola | Safra | Vincular talhões e contexto produtivo | COMO FAZER | 3 min | CUSTOMER | AUTOMATION_WITH_FIXTURES | safra, talhões |
| DF-02.03 | Agrícola | Planejamento | Montar planejamento operacional da safra | FLUXO | 5 min | CUSTOMER | AUTOMATION_WITH_FIXTURES | safra contextualizada |
| DF-02.04 | Agrícola | Orçamento | Interpretar previsto, estimado e realizado | GESTÃO | 4 min | CUSTOMER | MANUAL_REVIEW_REQUIRED | safra e itens orçados |
| DF-02.05 | Agrícola | Solo | Registrar análise e ler recomendação | FLUXO | 5 min | BOTH | AUTOMATION_WITH_FIXTURES | safra/talhão, laudo |
| DF-02.06 | Agrícola | Clima/NDVI | Consultar previsão, alertas e monitoramento | GESTÃO | 4 min | BOTH | AUTOMATION_WITH_FIXTURES | unidade/configuração provider quando aplicável |
| DF-03.01 | Operação | Tarefas | Criar, iniciar, concluir e invalidar uma tarefa | COMO FAZER | 4 min | CUSTOMER | AUTOMATION_WITH_FIXTURES | safra/perfil |
| DF-03.02 | Operação | Operação agrícola | Registrar operação realizada com recursos | COMO FAZER | 5 min | CUSTOMER | AUTOMATION_WITH_FIXTURES | safra, talhão, produto/estoque se houver |
| DF-03.03 | Operação | Cadeia econômica | Ver consumo, estoque, custo e reflexo financeiro | FLUXO | 5 min | BOTH | AUTOMATION_WITH_FIXTURES | operação realizada, estoque, plano de contas |
| DF-03.04 | Campo | Offline-first | Executar tarefa sem rede e sincronizar | FLUXO | 5 min | CUSTOMER | AUTOMATION_COMPLEX | dispositivo ativado, fixture de sync |
| DF-03.05 | Frota | Abastecimento | Registrar abastecimento e consultar consumo | COMO FAZER | 4 min | CUSTOMER | AUTOMATION_WITH_FIXTURES | equipamento, combustível |
| DF-03.06 | Frota | Manutenção | Acompanhar disponibilidade e manutenção preventiva | FLUXO | 4 min | CUSTOMER | AUTOMATION_WITH_FIXTURES | equipamento/plano |
| DF-04.01 | Suprimentos | Requisição | Solicitar, aprovar e entregar material | FLUXO | 5 min | CUSTOMER | AUTOMATION_WITH_FIXTURES | produto, estoque, perfil |
| DF-04.02 | Suprimentos | Compras | Criar pedido e receber parcialmente | FLUXO | 5 min | CUSTOMER | AUTOMATION_WITH_FIXTURES | fornecedor, produto |
| DF-04.03 | Pós-colheita | Colheita/lote | Registrar colheita, romaneio e lote | FLUXO | 5 min | CUSTOMER | AUTOMATION_WITH_FIXTURES | safra, talhão, produto |
| DF-04.04 | Pós-colheita | Beneficiamento | Registrar qualidade e beneficiamento | COMO FAZER | 5 min | CUSTOMER | AUTOMATION_WITH_FIXTURES | lote/produto colhido |
| DF-05.01 | Financeiro | Lançamentos | Registrar receita e despesa corretamente | COMO FAZER | 5 min | BOTH | AUTOMATION_WITH_FIXTURES | plano de contas, pessoa |
| DF-05.02 | Financeiro | DRE/custos | Ler custo agrícola, DRE e rentabilidade | GESTÃO | 5 min | BOTH | MANUAL_REVIEW_REQUIRED | lançamentos/allocations de demonstração |
| DF-05.03 | Comercialização | Venda | Registrar comercialização e acompanhar receita | FLUXO | 5 min | CUSTOMER | AUTOMATION_WITH_FIXTURES | comprador, produção/romaneio |
| DF-06.01 | Pecuária | Rebanho | Cadastrar animal e organizar lote/piquete | FLUXO | 5 min | CUSTOMER | AUTOMATION_WITH_FIXTURES | propriedade, lote/piquete |
| DF-06.02 | Pecuária | Manejo | Registrar manejo, pesagem e indicador | FLUXO | 5 min | CUSTOMER | AUTOMATION_COMPLEX | rebanho, dispositivo se Campo |
| DF-07.01 | Rastreabilidade | Passaporte | Consultar a cadeia de um lote | GESTÃO | 4 min | BOTH | AUTOMATION_WITH_FIXTURES | lote com eventos |
| DF-07.02 | Ambiental/ESG | Evidência | Registrar evidência e acompanhar não conformidade | FLUXO | 5 min | CUSTOMER | MANUAL_REVIEW_REQUIRED | módulo/permissão ambiental |
| DF-08.01 | Gestão | Indicadores | Transformar DRE e analytics em decisão | GESTÃO | 5 min | BOTH | MANUAL_REVIEW_REQUIRED | dados de safra/financeiro |
| DF-08.02 | Gestão | Recomendações | Interpretar recomendação e prioridade sem automatizar execução | CONCEITO | 3 min | BOTH | MANUAL_REVIEW_REQUIRED | resultados analíticos |

## 10. Trilha recomendada para novos usuários

Sequência baseada nas dependências observadas, não na ordem do sidebar:

1. `DF-00.01` e `DF-00.02`: propósito, canais e navegação por objetivo.
2. `DF-01.01`–`DF-01.03`: tenant, unidade e território operacional.
3. `DF-01.05`–`DF-01.07`: cadastros mestres e estoque inicial.
4. `DF-02.01`–`DF-02.03`: safra, talhões e planejamento.
5. `DF-03.01`–`DF-03.03`: tarefa, operação e cadeia de consumo/custo.
6. `DF-03.04`–`DF-03.06`: Campo, frota e execução diária.
7. `DF-04.01`–`DF-04.04`: suprimentos, colheita e pós-colheita.
8. `DF-05.01`–`DF-05.03`: financeiro, resultado e comercialização.
9. `DF-08.01`–`DF-08.02`: gestão, indicadores e recomendações.
10. Trilhas opcionais: `DF-01.04` fundiário, `DF-02.05` solo, `DF-02.06` clima, `DF-06.*` pecuária, `DF-07.*` ESG e integrações.

Pré-requisito funcional não significa que todas as aulas anteriores sejam obrigatórias. Por exemplo, alguém pode assistir `DF-05.01` diretamente se já possuir plano de contas e permissões.

## 11. Aula 00.01 — Conheça a DeepFarms

**Objetivo:** explicar em poucos minutos que a DeepFarms conecta contexto rural, execução de campo e gestão econômica, sem ensinar cadastros detalhados.

**Tour visual recomendado:**

1. `/dashboard`: visão do dia, alertas e indicadores;
2. `/agricola/dashboard` ou `/agricola/safras`: safra como contexto produtivo;
3. uma visão contextual `/agricola/safras/{id}/dashboard` ou `/agricola/safras/{id}/operacoes`;
4. `/dashboard/operacional`: execução, frota e tarefas;
5. `/suprimentos`: estoque, compras e requisições;
6. `/dashboard/financeiro` e custos/DRE: consequência econômica;
7. `/campo/home` e `/campo/sync`: operação offline, apenas como visão conceitual;
8. opcionalmente passaporte público `/p/rastreabilidade/{token}` para demonstrar rastreabilidade.

**Mensagem central:** o usuário começa configurando o contexto, planeja, executa, registra evidências/consumo, acompanha custos e usa indicadores para decidir o próximo ciclo. A aula não deve abrir formulários nem explicar todos os menus.

**Tipo/público/duração:** CONCEITO, BOTH, 3 minutos.
**Automação:** `MANUAL_REVIEW_REQUIRED`, pois rotas podem depender de dados, permissões e módulos contratados; usar fixture visual congelada antes de automatizar.

## 12. Classificação PUBLIC / CUSTOMER / BOTH

| Classe | Conteúdo |
|---|---|
| **PUBLIC** | Nenhuma aula operacional detalhada foi classificada como exclusivamente pública nesta primeira proposta; o conteúdo público deve nascer de recortes de conceito/gestão. |
| **BOTH** | visão geral, navegação por objetivo, território versus fundiário, safra/fases, análise de solo, clima/NDVI, cadeia consumo→custo, lançamentos/resultado, passaporte e indicadores. |
| **CUSTOMER** | implantação do tenant, cadastros, estoque inicial, planejamento interno, tarefas, Campo offline, frota, requisições, compras, beneficiamento, pecuária operacional, ESG com dados do cliente e integrações. |

A classificação é editorial; não cria infraestrutura nem assume que uma aula CUSTOMER possa expor dados reais.

## 13. Pré-requisitos funcionais e pedagógicos

| Aula/processo | Pré-requisito funcional | Pré-requisito pedagógico recomendado |
|---|---|---|
| Safra | tenant, unidade, cultura e talhão conforme operação | entender território e cadastros mestres |
| Planejamento | safra contextualizada, talhões/cultivo e permissões | aula de safra |
| Operação com consumo | safra/talhão, produto e saldo de estoque quando aplicável, plano de contas para reflexo financeiro | tarefa versus operação |
| Campo | dispositivo ativado, contexto previamente sincronizado, operador/PIN e fixture | operação online antes de offline |
| Compras | fornecedor, produto, unidade/depósito e perfil de aprovação | estoque e requisição |
| Colheita/beneficiamento | safra, talhão, produto colhido/lote e eventualmente balança | operação e estoque |
| DRE/rentabilidade | lançamentos/CostAllocation e período com dados | cadeia econômica |
| Pecuária | propriedade, animais/lotes/piquetes e permissões | conceito de rebanho |
| ESG | módulo/permissão, propriedade/imóvel/documentos conforme recurso | território/fundiário |
| Integrações | provider/configuração, credenciais/política e tenant elegível | processo interno que será integrado |

## 14. Viabilidade de automação via Playwright

| Classe | Aulas indicadas | Condição |
|---|---|---|
| `AUTOMATION_READY` | DF-00.02 e consultas estáveis de dashboard/listagem | fixture fixa, login preparado e resultado visual estável |
| `AUTOMATION_WITH_FIXTURES` | cadastros, safra, tarefa, operação, estoque, compras, frota, financeiro básico e pós-colheita | dados isolados por tenant, IDs/ordem previsíveis e limpeza/reseed fora do escopo desta fase |
| `AUTOMATION_COMPLEX` | Campo offline, pecuária com sync, integrações, balança e fluxos com jobs | controlar relógio, rede, retry, sincronização e efeitos assíncronos |
| `MANUAL_REVIEW_REQUIRED` | aula 00.01, orçamento, DRE/indicadores, recomendações, fundiário e ESG | conteúdo depende de interpretação, permissões, dados agregados ou documentação jurídica |

Para cada cenário futuro, registrar: rota inicial, estado inicial, dados, ações, resultado, verificações e pontos de espera. O fluxo de Campo deve cobrir pelo menos pull, ação offline, push, materialização, erro e retry; uma gravação que mostre apenas a tela local é insuficiente.

## 15. Riscos para produção automatizada

- dados de demonstração não determinísticos por estado de tenant, ordem e datas;
- jobs/outbox/recomendações assíncronos alterando o momento em que um resultado aparece;
- estados de sync que podem permanecer em erro e exigir retry;
- feature gates e permissões que ocultam módulos/ações;
- dependência de provider externo (OpenWeather, ERP, balança, IoT);
- divergência entre rota global e rota contextual da safra;
- campos financeiros que só geram efeito quando plano de contas e contexto econômico existem;
- conteúdo de orçamento que pode ser interpretado como aprovado/versionado quando não é;
- dados jurídicos/ambientais inadequados para fixtures públicas;
- nomenclatura histórica AgroSaaS/FarmOS nos assets/documentos, enquanto o material novo deve dizer DeepFarms;
- componentes Client e carregamentos assíncronos que podem causar espera/variação visual;
- automação de menus em vez de automação de objetivo concreto, gerando vídeos longos e frágeis.

## 16. Recomendações para TRAINING-VIDEO-01

1. Começar com uma POC limitada a `DF-00.01`, `DF-02.01`, `DF-03.02`, `DF-03.03`, `DF-04.01` e `DF-05.02`.
2. Antes de gravar Campo, definir fixture e contrato de estados de sync; não usar ambiente real.
3. Não produzir ainda aula de “aprovação/versionamento de orçamento”, “contabilidade integrada” ou “integração ERP automática” como fluxo fechado.
4. Para cada vídeo, validar o resultado em mais de uma camada: tela, resposta/API, persistência/efeito e relatório/teste existente.
5. Gravar microaulas por objetivo, com uma aula conceitual curta quando uma decisão de domínio for necessária.
6. Usar a sequência do item 10 para onboarding e tags/rotas/entidades para acesso avulso.
7. Manter uma matriz de cenário separada do currículo: uma aula pode ter mais de um cenário, e um cenário pode ser reutilizado por aulas relacionadas.
8. Revisar visualmente todos os fluxos `MANUAL_REVIEW_REQUIRED` antes de qualquer renderização em lote.

## 17. Pendências que precisam de decisão humana

- aprovar se a primeira trilha cobre apenas agrícola/estoque/financeiro ou também pecuária/ambiental;
- definir o tenant e a massa de demonstração oficial, sem dados pessoais/reais;
- decidir se “orçamento” será ensinado como previsão itemizada atual ou mantido fora da primeira produção;
- decidir o nível público de conceitos de território, clima, DRE e rastreabilidade;
- validar a rota canônica a ser gravada quando há entrada global e entrada contextual;
- confirmar quais módulos/feature gates estarão disponíveis no tenant de gravação;
- definir política editorial para termos históricos e garantir que o material novo use DeepFarms;
- escolher se a POC inclui sincronização offline real ou começa por fluxos conectados;
- validar com produto/implantação a ordem de papéis: gestor, agrônomo, operador, estoque e financeiro;
- confirmar quais integrações possuem ambiente sandbox determinístico para futura gravação.

## 18. Veredicto

### GO COM RESSALVAS

Os fluxos centrais são suficientemente compreendidos para iniciar a arquitetura/POC de vídeos e validar o formato de microaulas. O encadeamento agrícola-operacional-econômico tem documentação normativa, serviços, efeitos e testes que permitem ensinar objetivos concretos.

As ressalvas impedem um **GO** irrestrito: orçamento não é governado por versões, tarefa e operação possuem efeitos diferentes, Campo/sync é assíncrono, integrações dependem de configuração externa e há áreas parciais/Enterprise. Esses fluxos devem permanecer fora da primeira produção ou receber revisão manual explícita.

Este veredicto não autoriza iniciar `TRAINING-VIDEO-01` automaticamente; o relatório deve ser apresentado para análise, conforme solicitado.

### Arquivos criados/alterados nesta auditoria

- Criado: `docs/implementation/reports/TRAINING-CURRICULUM-01-AUDITORIA-FLUXOS-ACADEMIA-DEEPFARMS.md`
- Alterados: nenhum arquivo de código, banco, migration, frontend, infraestrutura ou integração.
