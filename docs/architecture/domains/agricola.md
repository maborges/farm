# Domínio Agrícola do AgroSaaS

**Status:** Documento canônico do domínio  
**Base normativa:** [AGRI-DOMAIN-001](/opt/lampp/htdocs/farm/docs/architecture/standards/AGRI-DOMAIN-001-territorial-fundiario.md), [AGRI-DOMAIN-002](/opt/lampp/htdocs/farm/docs/architecture/standards/AGRI-DOMAIN-002-propriedade-imovel.md)  
**Evidências principais:** [Routing Map](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-routing-map.md), [Master Context](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-master-context.md), [Domain Map](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-domain-map.md), [Data Model](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-data-model.md)

## 1. Visão Geral

O Domínio Agrícola é o contexto operacional, produtivo e analítico do AgroSaaS. Ele concentra o ciclo de vida da safra, o manejo por talhão, a execução de operações, o registro de apontamentos, a colheita, a formação de romaneios, a apuração de custos e a análise de rentabilidade.

Este domínio não é o dono da titularidade fundiária, da documentação legal do imóvel, nem da cadeia jurídica do território. Essa responsabilidade pertence aos domínios [Propriedades](/opt/lampp/htdocs/farm/docs/architecture/standards/AGRI-DOMAIN-001-territorial-fundiario.md) e [Imóveis Rurais](/opt/lampp/htdocs/farm/docs/architecture/standards/AGRI-DOMAIN-001-territorial-fundiario.md).

### Papel no AgroSaaS

- Orquestrar o ciclo produtivo da agricultura.
- Transformar território operacional em execução rastreável.
- Consolidar produtividade, custo, rentabilidade e indicadores agronômicos.
- Servir de base para rastreabilidade, certificações e Projeto Raízes.

### Dependências obrigatórias

- Propriedades, para a referência territorial de talhões, glebas, pastagens e infraestrutura.
- Imóveis Rurais, para a origem fundiária, documental e legal.
- Financeiro, para despesas, receitas, rateios, DRE e rentabilidade.
- Operacional, para frota, abastecimento, estoque e apontamentos de apoio.
- Ambiental e Certificações, para requisitos de conformidade e auditoria.
- Pecuária, quando houver compartilhamento de área, produção ou unidade econômica.

## 2. Objetivo

O objetivo do Domínio Agrícola é garantir que a operação de campo seja modelada como um fluxo coerente e auditável, desde o planejamento até a saída do produto, preservando:

- vínculo com a safra;
- vínculo com o talhão;
- vínculo com a unidade produtiva;
- vínculo com a produção colhida;
- vínculo com custo e resultado;
- vínculo com rastreabilidade documental.

## 3. Subdomínios

| Subdomínio | Objetivo | Responsabilidades | Entidades principais | Integrações | Status |
|---|---|---|---|---|---|
| Planejamento Agrícola | Planejar o ciclo produtivo e suas fases | Criar templates de fase, tarefas, gates e planos de ação | `PhaseTemplate`, `PhaseTemplateChecklistItem`, `PhaseTemplateTask`, `PhaseGateRule`, `OperationTemplate`, `OperationTemplateItem`, `OperationDependency`, `SafraTarefa` | Safras, Operações, Checklist, Caderno | PARCIAL |
| Safras | Controlar o ciclo agrícola | Gerenciar fases, status, histórico e associação com talhões e cultivos | `Safra`, `SafraTalhao`, `SafraFaseHistorico` | Propriedades, Cultivos, Operações, Rentabilidade | IMPLEMENTADO |
| Culturas e Cultivos | Estruturar a unidade de negócio dentro da safra | Modelar cultura, cultivar, janela de ocupação e indicadores do cultivo | `Cultivo`, `CultivoArea`, catálogos de cultura e commodity | Safras, Talhões, NDVI, Solo, Planejamento | IMPLEMENTADO |
| Talhões e Unidades de Produção | Operacionalizar a área de campo | Relacionar área, safra, cultivo e unidade econômica | `ProductionUnit`, `StatusConsorcioArea`, `SafraTalhaoGrupo`, `SafraTalhaoGrupoItem` | Propriedades, Financeiro, Operações, DRE | IMPLEMENTADO |
| Operações Agrícolas | Registrar a execução de campo | Capturar operação, execução, insumos, operador, clima, localização e custo | `OperacaoAgricola`, `OperacaoExecucao`, `InsumoOperacao`, `OperacaoTipoFase` | Estoque, Frota, Apontamentos, Safras | IMPLEMENTADO |
| Apontamentos e Caderno de Campo | Consolidar evidências operacionais | Registrar evento, foto, retificação, visita técnica, EPI e exportação documental | `CadernoCampoEntrada`, `CadernoCampoFoto`, `CadernoEventoStatusHistorico`, `VisitaTecnica`, `EPIEntrega`, `CadernoExportacao` | Operações, Segurança, Certificações, Raízes | IMPLEMENTADO |
| Colheita e Romaneios | Controlar a saída física da produção | Registrar peso, qualidade, destino e origem da colheita | `RomaneioColheita`, `ProdutoColhido` | Estoque, Comercialização, Rastreabilidade | IMPLEMENTADO |
| Beneficiamento | Processar pós-colheita | Rastrear entrada, secagem, rendimento, classificação e saída | `LoteBeneficiamento`, `LoteBeneficiamentoRomaneio` | Romaneios, Estoque, Comercialização | IMPLEMENTADO |
| Custos e Rentabilidade | Calcular resultado econômico | Consolidar custos alocados, margem, resultado e KPI financeiro-agronômico | `CostAllocation`, `DREAgricolaV1Service`, `RentabilidadeAgricolaV1Service`, `BenchmarkAgricolaV1Service`, `EficienciaOperacionalAgricolaV1Service` | Financeiro, Operações, Estoque, Frota | IMPLEMENTADO |
| Agricultura de Precisão | Apoiar decisão agronômica | Consumir NDVI, mapas e prescrição em taxa variável | `ImagemNDVI`, `PrevisaoProdutividade`, `PrescricaoVRA`, `MapasFertilidade`, `Amostras`, `AnaliseSolo` | Sensoriamento, Solo, Máquinas, Irrigação | IMPLEMENTADO |
| Fenologia e Monitoramento | Observar evolução da cultura e risco fitossanitário | Registrar estágio fenológico, pragas, doenças, alertas e diagnóstico | `FenologiaEscala`, `SafraFenologiaRegistro`, `MonitoramentoPragas`, `MonitoramentoCatalogo` | IA, Defensivos, Recomendação, Checklist | IMPLEMENTADO |
| Inteligência Agrícola | Gerar leitura gerencial do campo | Produzir dashboard, diagnóstico, priorização, recomendações, cenários e previsões | `SafraCenario`, `SafraCenarioUnidade`, serviços de `diagnostico`, `recomendacoes`, `prioridades`, `benchmark`, `eficiencia`, `previsoes` | DRE, Safras, Operações, NDVI, Solo | IMPLEMENTADO |
| Rastreabilidade Agrícola | Encadear origem da produção | Criar lote, cadeia de rastreio e passaporte público | `LoteRastreabilidade`, `CadernoLoteComercial`, rotas públicas de rastreio | Colheita, Comercialização, Certificações, Raízes | IMPLEMENTADO |

## 4. Entidades

### 4.1 Núcleo do domínio

| Entidade | Responsabilidade | Ownership | Relacionamentos principais | Fonte da verdade |
|---|---|---|---|---|
| `Safra` | Representar o ciclo agrícola superior | Agrícola | `Cultivo`, `SafraTalhao`, `SafraFaseHistorico`, `SafraTarefa`, `SafraCenario` | Agrícola |
| `Cultivo` | Representar a unidade de negócio dentro da safra | Agrícola | `Safra`, `CultivoArea` | Agrícola |
| `CultivoArea` | Vincular cultivo a um talhão e a uma análise de solo | Agrícola | `Cultivo`, `AreaRural`, `AnaliseSolo` | Agrícola, com referência territorial do talhão |
| `ProductionUnit` | Unificar safra + cultivo + área como unidade econômica | Agrícola | `Safra`, `Cultivo`, `AreaRural`, `CultivoArea` | Agrícola |
| `SafraTalhao` | Associação N:N entre safra e talhão | Agrícola | `Safra`, `AreaRural` | Agrícola, com referência territorial do talhão |
| `SafraFaseHistorico` | Registrar transições de fase da safra | Agrícola | `Safra` | Agrícola |
| `SafraTarefa` | Planejar e controlar intenção de execução | Agrícola | `Safra`, `ProductionUnit`, `AreaRural`, `OperacaoAgricola`, `AnaliseSolo` | Agrícola |
| `OperacaoAgricola` | Registrar a execução real de campo | Agrícola | `Safra`, `Cultivo`, `ProductionUnit`, `AreaRural`, `SafraTarefa` | Agrícola |
| `OperacaoExecucao` | Registrar o detalhamento da execução | Agrícola | `OperacaoAgricola`, `ProductionUnit` | Agrícola |
| `InsumoOperacao` | Registrar insumos consumidos em uma operação | Agrícola | `OperacaoAgricola`, estoque, cadastros de produto | Agrícola |
| `RomaneioColheita` | Registrar a colheita e sua qualidade | Agrícola | `Safra`, `Cultivo`, `ProductionUnit`, `AreaRural`, `ProdutoColhido` | Agrícola |
| `ProdutoColhido` | Representar o lote físico colhido e classificado | Agrícola | `Safra`, `AreaRural`, `RomaneioColheita`, `Commodity` | Agrícola |
| `LoteBeneficiamento` | Controlar o processamento pós-colheita | Agrícola | `Safra`, `Cultivo`, `RomaneioColheita`, `ProdutoColhido` | Agrícola |
| `CostAllocation` | Alocar custo por unidade de produção | Agrícola | `ProductionUnit`, `OperacaoExecucao`, `EstoqueMovimento`, `Rateio` | Agrícola, derivado de Financeiro e Operações |
| `ImagemNDVI` | Armazenar imagem e índice de vigor | Agrícola | `AreaRural` | Agrícola |
| `PrevisaoProdutividade` | Estimar produtividade por área | Agrícola | `Safra`, `AreaRural` | Agrícola |
| `AnaliseSolo` | Guardar resultado analítico do solo | Agrícola | `AreaRural`, `ProductionUnit` | Agrícola |
| `PrescricaoVRA` | Prescrever aplicação em taxa variável | Agrícola | `AreaRural`, `Safra`, `UnidadeProdutiva` | Agrícola |
| `MonitoramentoPragas` | Registrar avaliação fitossanitária | Agrícola | `Safra`, `AreaRural`, `SafraFenologiaRegistro` | Agrícola |
| `SafraCenario` | Simular resultado econômico e produtivo | Agrícola | `Safra`, `SafraCenarioUnidade` | Agrícola |
| `SafraCenarioUnidade` | Simular uma unidade econômica dentro do cenário | Agrícola | `SafraCenario`, `ProductionUnit` | Agrícola |

### 4.2 Entidades de apoio e governança operacional

| Entidade | Responsabilidade | Ownership | Relacionamentos principais | Fonte da verdade |
|---|---|---|---|---|
| `PhaseTemplate` | Definir governança de fase | Agrícola | `PhaseTemplateChecklistItem`, `PhaseTemplateTask`, `PhaseGateRule` | Agrícola |
| `OperationTemplate` | Definir plano operacional padrão | Agrícola | `OperationTemplateItem`, `OperationDependency` | Agrícola |
| `OperacaoTipoFase` | Validar fase permitida para cada tipo de operação | Agrícola | `OperacaoAgricola` | Agrícola |
| `SafraChecklistItem` | Checklist canônico por fase da safra | Agrícola | `Safra`, `PhaseTemplateChecklistItem` | Agrícola |
| `CadernoCampoEntrada` | Ledger documental do campo | Agrícola | `Safra`, `AreaRural`, `OperacaoAgricola` | Agrícola |
| `CadernoCampoFoto` | Evidência fotográfica de campo | Agrícola | `CadernoCampoEntrada` | Agrícola |
| `CadernoEventoStatusHistorico` | Histórico de estados do caderno | Agrícola | `CadernoCampoEntrada` | Agrícola |
| `VisitaTecnica` | Registro técnico assinado | Agrícola | `Safra`, `AreaRural` | Agrícola |
| `EPIEntrega` | Evidência de segurança para operação de campo | Operacional / apoio agrícola | `OperacaoAgricola`, trabalhador | Operacional, não fundiário |
| `CadernoExportacao` | Exportar snapshot documental | Agrícola | `Safra`, `AreaRural`, assinatura e hash | Agrícola |
| `FenologiaEscala` | Catálogo de estágios fenológicos | Agrícola | `SafraFenologiaRegistro` | Agrícola |
| `SafraTalhaoGrupo` | Agrupar talhões para manejo conjunto | Agrícola | `SafraTalhaoGrupoItem` | Agrícola |
| `LoteRastreabilidade` | Gerar lote rastreável | Agrícola | `Safra`, `AreaRural` | Agrícola |
| `CertificacaoPropriedade` | Guardar certificação vinculada à unidade produtiva | Compartilhado com certificações | `UnidadeProdutiva` | Compartilhado |
| `CadernoLoteComercial` | Encadear lote comercial com produto e beneficiamento | Agrícola / comercial | `ProdutoColhido`, `LoteBeneficiamento`, comercialização | Agrícola |

### 4.3 Entidades de referência territorial

O Domínio Agrícola consome, mas não possui, a entidade territorial `AreaRural` e suas variações hierárquicas. Essa área pertence ao domínio Propriedades. O mesmo vale para qualquer entidade fundiária ou documental do imóvel rural.

## 5. Fluxos

### Fluxo oficial de negócio

| Ordem | Fluxo | Descrição |
|---|---|---|
| 1 | Planejamento | O template de fase ou operação gera a intenção de execução na safra. |
| 2 | Safra | A safra é criada, evolui de fase e recebe talhões, cultivos e unidades produtivas. |
| 3 | Manejo | Operações e tarefas são planejadas e executadas sobre talhões e unidades produtivas. |
| 4 | Apontamento | O caderno de campo captura evidências, fotos, status e retificações. |
| 5 | Monitoramento | NDVI, solo, fenologia e pragas qualificam a condição agronômica. |
| 6 | Colheita | O romaneio registra peso, qualidade, origem e destino. |
| 7 | Pós-colheita | O beneficiamento converte romaneio em lote classificado. |
| 8 | Custo | O custo é alocado por unidade econômica e consolidado. |
| 9 | Resultado | DRE, rentabilidade, benchmark e eficiência consolidam o desempenho. |
| 10 | Rastreabilidade | O lote e o passaporte documental permitem auditoria de origem. |

### Cadeia operacional recomendada

```text
Planejamento
↓
Safra
↓
Cultivo / ProductionUnit
↓
Talhão
↓
Operação / Apontamento
↓
Colheita / Romaneio
↓
Produto Colhido / Beneficiamento
↓
Custo / Rentabilidade / DRE
↓
Rastreabilidade / Certificação
```

### Transições normativas da safra

O código evidencia a sequência de fases:

```text
PLANEJADA → PREPARO_SOLO → PLANTIO → DESENVOLVIMENTO → COLHEITA → POS_COLHEITA → ENCERRADA
```

## 6. Eventos

Os eventos abaixo são a forma canônica de leitura do domínio. Nem todos estão publicados como event bus explícito; parte deles é inferida das transições e serviços existentes.

| Evento | Gatilho | Consumidores típicos | Evidência |
|---|---|---|---|
| `SafraCriada` | Inclusão de nova safra | Planejamento, operações, painéis | `services/api/agricola/safras/models.py` |
| `SafraFaseAlterada` | Mudança de fase da safra | Checklist, tarefas, alertas | `services/api/agricola/safras/models.py` |
| `SafraTarefaGerada` | Template ou solo cria tarefa | Operações, aprovação | `services/api/agricola/tarefas/models.py`, `services/api/agricola/models/templates.py` |
| `SafraTarefaAprovada` | Aprovação de tarefa | Operações | `services/api/agricola/tarefas/models.py` |
| `OperacaoAgricolaExecutada` | Execução gravada | Caderno, custo, rastreabilidade | `services/api/agricola/operacoes/models.py` |
| `ApontamentoRegistrado` | Entrada no caderno | Auditoria, compliance, exportação | `services/api/agricola/caderno/models.py` |
| `VisitaTecnicaRegistrada` | Visita assinada | Diagnóstico, recomendação, ESG | `services/api/agricola/caderno/models.py` |
| `ChecklistConcluido` | Itens da fase fechados | Gate de fase | `services/api/agricola/checklist/models.py` |
| `AnaliseSoloRegistrada` | Laudo de solo inserido | Prescrição, tarefa, recomendação | `services/api/agricola/analises_solo/models.py` |
| `PrescricaoVraGerada` | Mapa/prescrição criado | Máquinas, execução, rastreabilidade | `services/api/agricola/amostragem_solo/models/prescricoes_vra.py` |
| `ImagemNdviRecebida` | Captura NDVI armazenada | Monitoramento, alertas | `services/api/agricola/ndvi/models.py` |
| `MonitoramentoPragaRegistrado` | Observação fitossanitária | Diagnóstico, defensivos, alerta | `services/api/agricola/monitoramento/models.py` |
| `RomaneioColheitaGerado` | Registro de colheita | Produto colhido, beneficiamento, comercialização | `services/api/agricola/romaneios/models.py` |
| `ProdutoColhidoCriado` | Lote físico classificado | Estoque, comercialização, passaporte | `services/api/agricola/colheita/models.py` |
| `BeneficiamentoConsolidado` | Lote pós-colheita fechado | Comercialização, rastreabilidade | `services/api/agricola/beneficiamento/models.py` |
| `CustoAlocado` | Rateio consolidado | DRE, rentabilidade, benchmark | `services/api/agricola/custos/models.py` |
| `DREAgricolaCalculada` | Fechamento da apuração | Financeiro, indicadores | `services/api/agricola/dre/service.py` |
| `RentabilidadeCalculada` | Resultado agrícola consolidado | Gestão, diretoria | `services/api/agricola/rentabilidade/service.py` |
| `BenchmarkAgricolaGerado` | Comparativos oficiais | Gestão, eficiência | `services/api/agricola/benchmark/service.py` |
| `LoteRastreavelGerado` | Passaporte ou lote rastreável criado | Certificação, Raízes, público | `services/api/agricola/rastreabilidade/models.py`, `services/api/agricola/rastreabilidade/public_router.py` |

## 7. Integrações

| Módulo | Integração | Dependência | Impacto |
|---|---|---|---|
| Propriedades | Talhões, glebas, áreas, infraestrutura | Alta | Define a geometria operacional da safra |
| Imóveis Rurais | Origem fundiária, documental e legal | Alta | Sustenta rastreabilidade e compliance |
| Pecuária | Pastagens, lotes, manejo e unidade mista | Média | Compartilhamento de área e produção |
| Financeiro | Despesas, receitas, rateios, DRE, comercialização | Alta | Sustenta custo e resultado |
| Estoque | Insumos, lotes, movimentação, beneficiamento | Alta | Liga operação a abastecimento e saída física |
| Compras | Entrada de insumos e reposição | Média | Alimenta execução e custo |
| Frota | Abastecimento, máquina, ordem de serviço | Alta | Opera custos e evidência de campo |
| Ambiental | Licenças, ESG, carbono, recuperação | Média | Amplia conformidade e auditoria |
| Certificações | GlobalG.A.P., RTRS e equivalentes | Alta | Usa rastreabilidade e snapshot documental |
| Projeto Raízes | Passaporte, origem e cadeia de custódia | Alta | Exige trilha completa até o imóvel rural |

## 8. Regras de Negócio

1. Toda operação agrícola deve pertencer a uma safra.
2. Toda operação agrícola deve estar associada a um talhão ou unidade equivalente.
3. Todo romaneio deve ter origem territorial identificável.
4. Todo produto colhido deve ter cadeia de origem preservada.
5. Todo custo agrícola deve poder ser alocado a uma unidade produtiva.
6. Toda safra deve possuir histórico de fase.
7. Toda tarefa de safra deve possuir origem clara, seja template, solo ou criação manual.
8. Nenhum dado fundiário ou documental do imóvel rural deve ser editado pelo domínio agrícola.
9. O domínio agrícola pode consumir a área do talhão, mas não redefinir sua titularidade.
10. O domínio agrícola pode derivar indicadores, mas não criar fonte paralela de verdade.
11. O caderno de campo é ledger operacional e não substitui documentos legais.
12. A rastreabilidade pública deve ser derivada de dados oficiais e imutáveis.
13. O vínculo com Imóveis Rurais deve ser preservado indiretamente por meio do domínio territorial.
14. O modelo deve suportar sobreposição de áreas, manejo misto e unidades econômicas compostas.
15. Qualquer exceção documental deve permanecer auditável.

## 9. Fronteiras

### Pertence ao Domínio Agrícola

- Safras;
- Cultivos;
- Talhões como referência operacional;
- Operações de campo;
- Apontamentos e caderno;
- Colheita e romaneios;
- Beneficiamento;
- Custos agrícolas;
- Rentabilidade;
- NDVI, solo, fenologia e monitoramento;
- Cenários, benchmark, eficiência e diagnóstico agrícola;
- Rastreabilidade da produção;
- Templates de fase e operação.

### Não pertence ao Domínio Agrícola

- Titularidade fundiária;
- Matrículas, cartórios, CAR, CCIR, ITR, NIRF e SIGEF;
- Contratos jurídicos completos;
- Proprietários, condôminos e procuradores como fonte oficial;
- RH corporativo;
- Financeiro corporativo não agrícola;
- Compliance legal do imóvel rural;
- Cadastro territorial canônico.

### Fronteira de consumo

O domínio agrícola consome a área e a geometria de `AreaRural`, mas a origem dessa informação é o domínio territorial. O mesmo vale para titularidade, documentação e demais atributos fundiários do imóvel.

## 10. Roadmap

| Funcionalidade | Status | Observação |
|---|---|---|
| Safras | IMPLEMENTADO | Núcleo consolidado com fase e histórico. |
| Cultivos | IMPLEMENTADO | Unidade de negócio dentro da safra. |
| Talhões | IMPLEMENTADO | Referência territorial já consumida pelo domínio. |
| Operações agrícolas | IMPLEMENTADO | Inclui execução, insumos e origem documental. |
| Apontamentos e caderno | IMPLEMENTADO | Ledger operacional e exportação documental. |
| Romaneios | IMPLEMENTADO | Origem da colheita e qualidade. |
| Colheita e produto colhido | IMPLEMENTADO | Base da rastreabilidade e comercialização. |
| Beneficiamento | IMPLEMENTADO | Pós-colheita com lote e blend. |
| Custos agrícolas | IMPLEMENTADO | Alocação e consolidação operacionais. |
| Rentabilidade | IMPLEMENTADO | Derivado de DRE agrícola e produção. |
| DRE agrícola | IMPLEMENTADO | Serviço oficial de apuração. |
| NDVI | IMPLEMENTADO | Sensoriamento e vigor vegetativo. |
| Amostragem de solo | PARCIAL | Estrutura existe, mas parte dos modelos ainda é scaffold. |
| Prescrição VRA | PARCIAL | Integração funcional existente, mas ainda concentrada em apoio técnico. |
| Fenologia | IMPLEMENTADO | Catálogo e séries de observação presentes. |
| Monitoramento fitossanitário | IMPLEMENTADO | Integração com alerta e diagnóstico. |
| Planejamento agrícola | PARCIAL | Existe template e tarefa, mas a governança ainda é evolutiva. |
| Benchmark e eficiência | IMPLEMENTADO | Serviços oficiais derivados de DRE e rentabilidade. |
| Diagnóstico e recomendações | IMPLEMENTADO | Presença de rotas e serviços dedicados. |
| Cenários | IMPLEMENTADO | Modelagem de simulação por safra e unidade. |
| Rastreabilidade pública | IMPLEMENTADO | Passaporte e consulta pública existentes. |
| ESG e certificações nativas | PARCIAL | Há suporte documental e de rastreabilidade, mas a modelagem ESG completa deve ser integrada a normas canônicas. |

## Conclusão

O Domínio Agrícola do AgroSaaS já cobre o núcleo operacional do campo, a apuração de custos e resultado, a agricultura de precisão e a rastreabilidade produtiva. A fronteira correta é clara: o domínio agrícola executa, mede e explica a produção; o domínio territorial e fundiário define a base legal e documental dessa produção.

Como regra de arquitetura, o Domínio Agrícola não pode criar uma fonte paralela para propriedade, imóvel rural ou titularidade. Ele deve consumir essas informações por referência e manter sua responsabilidade centrada em safra, operação, produtividade, qualidade, custo, rastreabilidade e inteligência agronômica.
