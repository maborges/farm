# PILOT-03 — Simulação Operacional de uma Fazenda de Café Exportadora

Data da auditoria: 2026-07-01

## 1. Resumo Executivo

Esta simulação responde à pergunta operacional: se uma fazenda de café exportadora começar a usar o AgroSaaS amanhã, como ficará sua rotina durante uma safra completa usando apenas o que já existe hoje.

Fato encontrado:

- o AgroSaaS já cobre a espinha dorsal da operação agrícola cafeeira: implantação via Wizard, estrutura territorial, safra/cultivo/talhão, operações de campo, colheita, romaneios, beneficiamento de café, rastreabilidade por lote, comercialização, custos, DRE e rentabilidade;
- existe integração real com Sankhya para pessoas, produtos, NFe e financeiro, com backend e tela web de operação;
- o `apps/campo` cobre bem a rotina móvel de campo e colheita offline.

Limitação encontrada:

- a plataforma ainda não cobre uma operação exportadora full-scope ponta a ponta com logística internacional, documentação de embarque, Incoterm, porto, container, booking e governança específica de exportação;
- parte do pós-colheita especializado continua concentrada no Web;
- a operação econômica está forte por safra, talhão e `ProductionUnit`, mas não aparece como trilha oficial explícita por lote exportador.

Recomendação:

- o primeiro piloto pode avançar se o escopo for: operação cafeeira, pós-colheita, rastreabilidade, comercialização básica e integração administrativa seletiva com Sankhya;
- não deve ser prometido ao cliente um projeto de exportação internacional ponta a ponta na fase inicial.

## 2. Jornada operacional completa

### Etapa 1 — Implantação

Fato encontrado:

- a implantação operacional já possui fluxo oficial via Wizard, com `ImplantacaoOperacional`, etapas oficiais, checklist automático e bloqueio de go-live sem `UnidadeProdutiva`, área, talhão, depósito, plano de contas e catálogo mínimo de produtos em [services/api/wizard/services.py](/opt/lampp/htdocs/farm/services/api/wizard/services.py:59) e [services/api/wizard/checklist_engine.py](/opt/lampp/htdocs/farm/services/api/wizard/checklist_engine.py:60);
- o frontend do Wizard existe em `/dashboard/implantacao/wizard`, sustentado pela API `/api/v1/wizard`.

Leitura operacional:

- o cliente consegue começar pelo Tenant já provisionado, entrar no Wizard, criar a unidade produtiva, estruturar áreas, validar talhões, depósito, máquinas e financeiro mínimo;
- propriedades e imóveis rurais pertencem ao fluxo territorial mais amplo, mas o go-live mínimo do Wizard está centrado na unidade operacional.

Status da etapa:

- backend: existe;
- frontend: existe;
- API: existe;
- fluxo completo: existe para implantação operacional base;
- adaptação: sim, se o cliente exigir prontidão exportadora já no onboarding;
- interrupção: não para a base da fazenda.

### Etapa 2 — Planejamento agrícola

Fato encontrado:

- `Safra` e `Cultivo` existem com rotas próprias em [services/api/agricola/safras/router.py](/opt/lampp/htdocs/farm/services/api/agricola/safras/router.py:22) e [services/api/agricola/cultivos/router.py](/opt/lampp/htdocs/farm/services/api/agricola/cultivos/router.py:18);
- `Cultivo` suporta `cultivar_id`, `cultivar_nome`, `commodity_id` e `espacamento_cm` em [services/api/agricola/cultivos/models.py](/opt/lampp/htdocs/farm/services/api/agricola/cultivos/models.py:15);
- café existe como cultura oficial em [services/api/scripts/seed_culturas.py](/opt/lampp/htdocs/farm/services/api/scripts/seed_culturas.py:357) e [services/api/core/cadastros/produtos/models.py](/opt/lampp/htdocs/farm/services/api/core/cadastros/produtos/models.py:388);
- há orçamento e itens de planejamento por safra em [services/api/agricola/a1_planejamento/router.py](/opt/lampp/htdocs/farm/services/api/agricola/a1_planejamento/router.py:21).

Leitura operacional:

- o gerente agrícola consegue abrir a safra, vincular cultivos, associar cultivar e distribuir áreas;
- a plataforma suporta planejamento agrícola, mas não encontrei uma camada cafeeira específica para idade do cafezal, bloco varietal avançado e cronograma perene detalhado.

Status da etapa:

- backend: existe;
- frontend: existe parcialmente;
- API: existe;
- fluxo completo: parcial;
- workaround: parte do detalhamento agronômico fino ainda pode exigir disciplina operacional externa.

### Etapa 3 — Operação agrícola

Fato encontrado:

- a API de operações agrícolas permite registrar operações, listar, exportar caderno e gerenciar tipos em [services/api/agricola/operacoes/router.py](/opt/lampp/htdocs/farm/services/api/agricola/operacoes/router.py:25);
- a tela web de operações existe em [apps/web/src/app/(dashboard)/dashboard/agricola/operacoes/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/agricola/operacoes/page.tsx:1);
- o `apps/campo` possui tela de caderno offline em [apps/campo/src/app/(campo)/caderno/page.tsx](/opt/lampp/htdocs/farm/apps/campo/src/app/(campo)/caderno/page.tsx:1) e aplicação em [apps/campo/src/app/(campo)/campo/aplicacao/page.tsx](/opt/lampp/htdocs/farm/apps/campo/src/app/(campo)/campo/aplicacao/page.tsx:1);
- as operações integram estoque, máquinas e custo operacional no backend.

Leitura operacional:

- o encarregado e o operador conseguem executar pulverização, adubação, inspeções e registros de campo pelo PWA;
- o gestor consegue revisar isso no Web com custo, área aplicada, tipos de operação e insumos;
- esta é uma das partes mais sólidas da rotina.

Status da etapa:

- backend: existe;
- frontend: existe no Web e no PWA;
- API: existe;
- fluxo completo: existe para operação agrícola geral;
- necessidade de Sankhya: não;
- necessidade de planilha: baixa.

### Etapa 4 — Colheita

Fato encontrado:

- o PWA possui fluxo offline de colheita por talhão com quantidade, umidade, fotos e GPS em [apps/campo/src/app/(campo)/campo/colheita/page.tsx](/opt/lampp/htdocs/farm/apps/campo/src/app/(campo)/campo/colheita/page.tsx:1);
- romaneios possuem lógica específica para café e geram `ProdutoColhido` automaticamente em [services/api/agricola/romaneios/service.py](/opt/lampp/htdocs/farm/services/api/agricola/romaneios/service.py:18) e [services/api/agricola/romaneios/service.py](/opt/lampp/htdocs/farm/services/api/agricola/romaneios/service.py:156);
- existe router de romaneios em [services/api/agricola/romaneios/router.py](/opt/lampp/htdocs/farm/services/api/agricola/romaneios/router.py:17).

Leitura operacional:

- o operador registra a colheita no campo;
- o responsável consolida romaneios no backend;
- a produção passa a ter lastro físico e econômico dentro da arquitetura oficial.

Status da etapa:

- backend: existe;
- frontend: existe parcialmente, com força maior no PWA;
- API: existe;
- fluxo completo: existe para colheita e geração de produto colhido;
- workaround: parte da consolidação continua mais administrativa que guiada.

### Etapa 5 — Pós-colheita

Fato encontrado:

- existe módulo dedicado de beneficiamento de café com secagem, blend, qualidade, armazenamento e venda em [services/api/agricola/beneficiamento/models.py](/opt/lampp/htdocs/farm/services/api/agricola/beneficiamento/models.py:9), [services/api/agricola/beneficiamento/service.py](/opt/lampp/htdocs/farm/services/api/agricola/beneficiamento/service.py:35) e [services/api/agricola/beneficiamento/router.py](/opt/lampp/htdocs/farm/services/api/agricola/beneficiamento/router.py:20);
- a tela web de beneficiamento existe em [apps/web/src/app/(dashboard)/dashboard/agricola/beneficiamento/BeneficiamentoClient.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/agricola/beneficiamento/BeneficiamentoClient.tsx:1);
- o modelo cobre umidade, peneira, bebida, SCAA, defeitos, perdas e armazém.

Leitura operacional:

- esta fazenda consegue operar secagem, beneficiamento, classificação e armazenagem no AgroSaaS;
- esse é um diferencial concreto para café;
- o ponto fraco é que esta jornada está concentrada no Web, não no PWA.

Status da etapa:

- backend: existe;
- frontend: existe no Web;
- API: existe;
- fluxo completo: existe para beneficiamento e classificação;
- necessidade de Sankhya: não;
- necessidade de planilha: baixa a média, dependendo do padrão de qualidade interno.

### Etapa 6 — Comercialização

Fato encontrado:

- `ComercializacaoCommodity` existe com contrato, comprador, entrega, NF-e, status e vínculo com `ProdutoColhido` em [services/api/financeiro/comercializacao/models.py](/opt/lampp/htdocs/farm/services/api/financeiro/comercializacao/models.py:20);
- a API existe em [services/api/financeiro/comercializacao/router.py](/opt/lampp/htdocs/farm/services/api/financeiro/comercializacao/router.py:15);
- a confirmação de comercialização gera `Receita` e evita dupla contagem com romaneios na DRE em [services/api/financeiro/comercializacao/service.py](/opt/lampp/htdocs/farm/services/api/financeiro/comercializacao/service.py:143) e [services/api/agricola/dre/service.py](/opt/lampp/htdocs/farm/services/api/agricola/dre/service.py:341).

Leitura operacional:

- o produtor consegue vender café, vincular a commodity, gerar receita e refletir isso no financeiro e na DRE;
- o que não encontrei foi a camada específica de exportação internacional.

Status da etapa:

- backend: existe;
- frontend: existe parcialmente no ecossistema financeiro/agro;
- API: existe;
- fluxo completo: existe para comercialização básica;
- fluxo exportador: não existe como trilha oficial completa.

### Etapa 7 — Integração Sankhya

Fato encontrado:

- a integração Sankhya está registrada no app principal em [services/api/main.py](/opt/lampp/htdocs/farm/services/api/main.py:508);
- há router com configuração, status, logs e sincronizações em [services/api/integracoes/sankhya/routers/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/routers/__init__.py:27);
- há serviços reais de sincronização e cliente WS em [services/api/integracoes/sankhya/services/sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py:16);
- existe tela web de integração em [apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx:1).

Leitura operacional:

- AgroSaaS pode operar como mestre operacional agrícola;
- Sankhya pode seguir como mestre administrativo, fiscal e parte financeira;
- a integração existe, mas não deve ser posicionada como trilha crítica do piloto de campo.

Status da etapa:

- backend: existe;
- frontend: existe;
- API: existe;
- fluxo completo: parcial;
- necessidade de Sankhya: média, se o cliente quiser refletir cadastros e financeiro corporativo;
- necessidade manual: ainda existe para partes não mapeadas do escopo exportador.

### Etapa 8 — ESG

Fato encontrado:

- a rastreabilidade agrícola possui cadeia do lote, certificações e passaporte em [services/api/agricola/rastreabilidade/router.py](/opt/lampp/htdocs/farm/services/api/agricola/rastreabilidade/router.py:18);
- a tela web exibe certificações, lotes e cadeia completa em [apps/web/src/app/(dashboard)/dashboard/agricola/rastreabilidade/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/agricola/rastreabilidade/page.tsx:1);
- testes cobrem passaporte e vínculo com `ProdutoColhido` e `LoteBeneficiamento` em [services/api/tests/unit/agricola/test_cert_gap01_passaporte.py](/opt/lampp/htdocs/farm/services/api/tests/unit/agricola/test_cert_gap01_passaporte.py:1).

Leitura operacional:

- o auditor e o gestor de qualidade conseguem montar cadeia de origem, certificações e evidências do lote;
- isso atende bem um piloto de rastreabilidade e conformidade básica;
- não encontrei um domínio exportador específico de compliance internacional.

### Etapa 9 — Rentabilidade

Fato encontrado:

- a arquitetura econômica oficial segue `OperationalCostAllocationService -> CostAllocation -> DRE -> Rentabilidade`;
- a DRE agrícola oficial consome `Receita` e `CostAllocation` e evita duplicidade com romaneio versus comercialização em [services/api/agricola/dre/service.py](/opt/lampp/htdocs/farm/services/api/agricola/dre/service.py:341);
- custos operacionais estão ancorados na porta oficial `OperationalCostAllocationService` em [services/api/agricola/custos/operational_cost_service.py](/opt/lampp/htdocs/farm/services/api/agricola/custos/operational_cost_service.py:1).

Leitura operacional:

- o proprietário consegue chegar a custo por safra, custo por talhão, DRE e rentabilidade agrícola;
- o que ainda não aparece como camada madura é rentabilidade exportadora por lote comercial internacional.

## 3. Evidências encontradas

| Tema | Evidência |
| --- | --- |
| Wizard e checklist de implantação | [services/api/wizard/services.py](/opt/lampp/htdocs/farm/services/api/wizard/services.py:59), [services/api/wizard/checklist_engine.py](/opt/lampp/htdocs/farm/services/api/wizard/checklist_engine.py:60) |
| Cultura café | [services/api/scripts/seed_culturas.py](/opt/lampp/htdocs/farm/services/api/scripts/seed_culturas.py:357), [services/api/core/cadastros/produtos/models.py](/opt/lampp/htdocs/farm/services/api/core/cadastros/produtos/models.py:388) |
| Cultivo e cultivar | [services/api/agricola/cultivos/models.py](/opt/lampp/htdocs/farm/services/api/agricola/cultivos/models.py:15), [services/api/agricola/cultivos/router.py](/opt/lampp/htdocs/farm/services/api/agricola/cultivos/router.py:18) |
| Planejamento | [services/api/agricola/a1_planejamento/router.py](/opt/lampp/htdocs/farm/services/api/agricola/a1_planejamento/router.py:21) |
| Operações agrícolas | [services/api/agricola/operacoes/router.py](/opt/lampp/htdocs/farm/services/api/agricola/operacoes/router.py:25), [apps/web/src/app/(dashboard)/dashboard/agricola/operacoes/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/agricola/operacoes/page.tsx:1) |
| Caderno e PWA | [apps/campo/src/app/(campo)/caderno/page.tsx](/opt/lampp/htdocs/farm/apps/campo/src/app/(campo)/caderno/page.tsx:1), [apps/campo/src/app/(campo)/campo/colheita/page.tsx](/opt/lampp/htdocs/farm/apps/campo/src/app/(campo)/campo/colheita/page.tsx:1) |
| Romaneios e `ProdutoColhido` | [services/api/agricola/romaneios/service.py](/opt/lampp/htdocs/farm/services/api/agricola/romaneios/service.py:18), [services/api/agricola/romaneios/service.py](/opt/lampp/htdocs/farm/services/api/agricola/romaneios/service.py:156) |
| Beneficiamento de café | [services/api/agricola/beneficiamento/models.py](/opt/lampp/htdocs/farm/services/api/agricola/beneficiamento/models.py:9), [services/api/agricola/beneficiamento/service.py](/opt/lampp/htdocs/farm/services/api/agricola/beneficiamento/service.py:35), [apps/web/src/app/(dashboard)/dashboard/agricola/beneficiamento/BeneficiamentoClient.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/agricola/beneficiamento/BeneficiamentoClient.tsx:1) |
| Rastreabilidade e certificações | [services/api/agricola/rastreabilidade/router.py](/opt/lampp/htdocs/farm/services/api/agricola/rastreabilidade/router.py:18), [apps/web/src/app/(dashboard)/dashboard/agricola/rastreabilidade/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/agricola/rastreabilidade/page.tsx:1) |
| Comercialização | [services/api/financeiro/comercializacao/models.py](/opt/lampp/htdocs/farm/services/api/financeiro/comercializacao/models.py:20), [services/api/financeiro/comercializacao/router.py](/opt/lampp/htdocs/farm/services/api/financeiro/comercializacao/router.py:15), [services/api/financeiro/comercializacao/service.py](/opt/lampp/htdocs/farm/services/api/financeiro/comercializacao/service.py:103) |
| DRE e rentabilidade | [services/api/agricola/dre/service.py](/opt/lampp/htdocs/farm/services/api/agricola/dre/service.py:341), [services/api/agricola/custos/operational_cost_service.py](/opt/lampp/htdocs/farm/services/api/agricola/custos/operational_cost_service.py:1) |
| Sankhya | [services/api/integracoes/sankhya/routers/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/routers/__init__.py:27), [services/api/integracoes/sankhya/services/sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py:16), [apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx:1) |

## 4. Matriz de aderência operacional

| Etapa | Executa hoje | Grau de aderência | Evidências | Necessita Sankhya | Observações |
| --- | --- | --- | --- | --- | --- |
| Implantação base | Sim | Alta | Wizard + checklist automático | Não | Boa para go-live operacional da fazenda. |
| Planejamento agrícola | Sim, com limites | Média | Safra, cultivo, planejamento | Não | Falta camada perene cafeeira mais profunda. |
| Operações de campo | Sim | Alta | Operações A2 + PWA caderno/aplicação | Não | Um dos pontos mais fortes. |
| Colheita | Sim | Alta | PWA colheita + romaneios | Não | Boa aderência operacional. |
| Pós-colheita | Sim | Alta | Beneficiamento de café | Não | Forte no Web, fraco no PWA. |
| Classificação de qualidade | Sim | Alta | Peneira, bebida, SCAA, defeitos | Não | Bom para piloto de qualidade e lote. |
| Comercialização básica | Sim | Média/Alta | `ComercializacaoCommodity` | Opcional | Atende venda; não cobre exportação full-scope. |
| Exportação internacional | Não integralmente | Baixa | Ausência de fluxo específico | Sim, parcialmente | Não prometer ponta a ponta. |
| ESG e certificações | Sim, com limites | Média/Alta | Rastreabilidade e certificações | Não | Forte para cadeia e passaporte. |
| DRE e rentabilidade | Sim | Alta | DRE agrícola v1 + custos oficiais | Opcional | Melhor por safra/talhão/PU do que por lote exportador. |

## 5. Jornada das personas

| Persona | Objetivo | Atividades | Módulos/telas | Dificuldades |
| --- | --- | --- | --- | --- |
| Proprietário | Ver operação e resultado | acompanhar go-live, produção, comercialização e rentabilidade | Wizard, DRE, rastreabilidade, comercialização | exportação internacional ainda fora do fluxo oficial |
| Gerente agrícola | Planejar e executar safra | safra, cultivo, operações, romaneios, beneficiamento | Web agrícola, PWA caderno/colheita | parte do planejamento cafeeiro fino ainda é genérica |
| Encarregado | Organizar execução diária | distribuir trabalho, revisar apontamentos, consolidar romaneios | PWA, operações, romaneios | troca entre PWA e Web no pós-colheita |
| Operador de campo | Registrar atividade | aplicação, caderno, colheita, fotos, GPS, sync | `apps/campo` | pós-colheita e comercialização ficam fora do PWA |
| Administrativo | Apoiar cadastro e integração | produtos, cadastros, Sankhya, documentos | Backoffice, integrações ERP | integração não cobre todo o universo exportador |
| Financeiro | Receitas, despesas e fechamento | comercialização, financeiro, DRE | financeiro + DRE | parte da governança pode continuar compartilhada com Sankhya |
| Auditor | Validar origem e conformidade | certificações, cadeia, evidências, passaporte | rastreabilidade | compliance exportador internacional não está completo |
| Gestor de exportação | Fechar operação exportadora | lotes, qualidade, contratos, entrega | beneficiamento, comercialização, rastreabilidade | falta fluxo nativo de exportação ponta a ponta |

## 6. Pontos de atrito

| Ponto de atrito | Classificação | Leitura |
| --- | --- | --- |
| Troca PWA → Web após colheita para consolidar romaneios e beneficiamento | Médio | o campo funciona bem, mas o pós-colheita é mais administrativo |
| Troca Web agrícola → Web financeiro na comercialização | Baixo | esperado para a arquitetura atual |
| Dependência de Web para rastreabilidade, certificações e passaporte | Médio | aceitável para piloto administrativo |
| Dependência de Sankhya para parte administrativa/fiscal/financeira corporativa | Médio | coerente com o posicionamento AgroSaaS operacional + ERP corporativo |
| Ausência de fluxo oficial de exportação internacional | Alto | principal limite para cliente exportador full-scope |
| Necessidade de disciplina manual em planejamento cafeeiro fino | Médio | por ausência de trilha perene especializada |
| Ausência de pós-colheita especializado no PWA | Médio | não bloqueia piloto, mas reduz aderência de operação móvel |

## 7. Dependências do Sankhya

Fato encontrado:

- a integração Sankhya já existe para pessoas, produtos, NFe e financeiro.

Leitura recomendada para o piloto:

- permanece no AgroSaaS: implantação operacional, estrutura territorial, safra, cultivos, talhões, operações, colheita, romaneios, beneficiamento, rastreabilidade, custos e análise agrícola;
- permanece no Sankhya: parte administrativa corporativa, fiscal, contábil e rotinas ERP mais amplas;
- pode ser sincronizado: pessoas, produtos, NFe, partes do financeiro;
- ainda depende de integração/manual: qualquer fluxo exportador que extrapole comercialização agrícola básica.

## 8. Dependências manuais

- detalhamento cafeeiro perene mais profundo, quando o cliente exigir gestão agronômica muito especializada;
- governança operacional exportadora fora da comercialização básica;
- parte da conciliação entre operação agro e processo administrativo corporativo;
- eventual consolidação de indicadores por lote exportável, quando isso for exigido como visão principal.

## 9. Pontos fortes

- Wizard já organiza implantação real da fazenda;
- operação de campo e colheita estão bem cobertas por Web + PWA;
- romaneio e `ProdutoColhido` dão lastro físico consistente;
- beneficiamento de café é um módulo específico e valioso;
- rastreabilidade e passaporte de lote são fortes para auditoria e certificação;
- arquitetura econômica está madura para custos, DRE e rentabilidade agrícola;
- integração Sankhya é real, não apenas prevista.

## 10. Lacunas críticas

- inexistência de fluxo oficial de exportação internacional ponta a ponta;
- ausência de camada explícita para operação logística/documental exportadora;
- rentabilidade não aparece como trilha oficial específica por lote exportador;
- prontidão do piloto cai se o cliente exigir que AgroSaaS substitua o ERP no início.

## 11. Lacunas não críticas

- planejamento cafeeiro perene mais profundo;
- pós-colheita especializado no PWA;
- maior fluidez entre operação de campo e administração pós-colheita;
- cobertura mais orientada a gestor de exportação no frontend.

## 12. Escopo recomendado para o piloto

### Deve entrar obrigatoriamente

- Wizard e implantação da fazenda;
- unidade produtiva, áreas, talhões, depósitos e máquinas;
- safra, cultivo e operações agrícolas;
- PWA para caderno, aplicação e colheita;
- romaneios;
- beneficiamento de café;
- rastreabilidade, certificações e passaporte;
- comercialização básica;
- DRE e rentabilidade agrícola;
- integração Sankhya somente onde já estiver madura e não for trilha crítica.

### Pode ficar para segunda fase

- aprofundamento de planejamento cafeeiro perene;
- dashboards especializados de exportação;
- evolução de rentabilidade por lote exportável;
- expansão operacional do pós-colheita no PWA.

## 13. O que não deve ser prometido

- substituição imediata do Sankhya como ERP corporativo completo;
- operação exportadora internacional ponta a ponta dentro do AgroSaaS atual;
- automação nativa de documentação logística/exportadora;
- go-live sem disciplina manual complementar em pontos específicos de exportação.

## 14. Veredicto final

Se este produtor começar a usar o AgroSaaS na próxima segunda-feira, a rotina dele poderá funcionar assim:

- a fazenda entra pelo Wizard, organiza unidade produtiva, áreas, talhões, estoque básico, máquinas e financeiro mínimo;
- o gerente monta safra e cultivos de café;
- a equipe trabalha no campo com PWA para caderno, aplicação e colheita;
- a colheita gera romaneios e produto colhido;
- o pós-colheita segue no Web com secagem, beneficiamento, classificação, lote, armazenagem e rastreabilidade;
- a venda pode ser registrada com reflexo em receita, DRE e rentabilidade;
- o Sankhya continua ao lado, sustentando o administrativo e o fiscal.

Conclusão objetiva:

- para uma safra de café com foco em operação agrícola, pós-colheita, rastreabilidade e gestão econômica, o AgroSaaS está apto para um primeiro piloto controlado;
- para um projeto já vendido como plataforma completa de exportação internacional integrada ao ERP em regime mission-critical, ainda não está pronto.
