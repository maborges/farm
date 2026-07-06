# PILOT-ERP-02 - Roteiro Oficial de Execução Assistida e Dry Run Café + Sankhya

Data: 2026-07-06

## 1. Objetivo

Este documento passa a ser o roteiro oficial para:

- Dry Run interno;
- homologação funcional;
- piloto assistido;
- Go-Live do primeiro cliente de café exportador com Sankhya.

Ele substitui a versão anterior do roteiro, preservando o que ainda é válido e refletindo o estado real atual da plataforma.

Base principal:

- [PILOT-ERP-01-SIMULACAO-CAFE-SANKHYA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-ERP-01-SIMULACAO-CAFE-SANKHYA.md)

## 2. Regras de escopo

- Não criar infraestrutura nova.
- Não criar módulos novos.
- Não criar sync bidirecional.
- Não criar staging novo.
- Não propor arquitetura nova.
- Trabalhar apenas com fluxos já existentes.
- Separar claramente o que é obrigatório, opcional e pós-piloto.

## 3. Auditoria consolidada

Documentos auditados para esta atualização:

- `docs/pilot/PILOT-ERP-02-ROTEIRO-EXECUCAO-ASSISTIDA-CAFE-SANKHYA.md`
- `docs/implementation/reports/PILOT-ERP-01-SIMULACAO-CAFE-SANKHYA.md`
- `docs/implementation/reports/COFFEE-ONBOARDING-01-AUDITORIA.md`
- `docs/implementation/reports/COFFEE-ONBOARDING-04-IMPLEMENTACAO-FASE1.md`
- `docs/implementation/reports/COFFEE-ONBOARDING-05A-COFFEE-TEMPLATE.md`
- `docs/implementation/reports/COFFEE-ONBOARDING-05B-SANKHYA-SYNC.md`
- `docs/implementation/reports/COFFEE-ONBOARDING-05C-OPERATION-TEMPLATES.md`
- `docs/implementation/reports/COFFEE-PILOT-01A1-WIZARD-CAFE.md`
- `docs/implementation/reports/COFFEE-PILOT-01A-PLANEJAMENTO-SAFRA.md`
- `docs/implementation/reports/COFFEE-PILOT-01B1-PRIMEIRA-SAFRA.md`
- `docs/implementation/reports/COFFEE-PILOT-02A1-AUDITORIA-MODELAGEM-PLANEJAMENTO.md`
- `docs/implementation/reports/COFFEE-PILOT-02A2-OPERACAO-PLANEJADA.md`
- `docs/implementation/reports/COFFEE-PILOT-02B-EXECUCAO-CAMPO.md`
- `docs/implementation/reports/COFFEE-PILOT-02B1-CORRECAO-BAIXA-ESTOQUE-PWA.md`
- `docs/implementation/reports/COFFEE-PILOT-02B2-AUDITORIA-POS-CORRECAO-PWA.md`
- `docs/implementation/reports/EXECUTION-WIZARD-07-GO-LIVE-ASSISTIDO-PILOTO.md`
- `docs/operations/outbox-worker.md`

## 4. Classificação do estado atual

| Item auditado | Situação | Observação operacional |
| --- | --- | --- |
| Onboarding Intent-Based | EXISTE E ATENDE | Fluxo em 3 passos por cultura, ERP e módulos já está em produção. |
| Seleção de Cultura Café | EXISTE E ATENDE | `CAFE` já dirige a preparação do tenant. |
| Seleção ERP Sankhya | EXISTE E ATENDE | `SANKHYA` já dispara a trilha de integração do onboarding. |
| CoffeeTemplate | EXISTE E ATENDE | `PhaseTemplates` de café já são copiados de forma idempotente. |
| OperationTemplates | EXISTE E ATENDE | `OperationTemplates` globais de café já são copiados de forma idempotente. |
| Geração automática no onboarding | EXISTE E ATENDE | O endpoint `/config/onboarding/configurar` já aplica templates e prepara a integração. |
| Sincronização assíncrona Gateway-first via Outbox | EXISTE E ATENDE | O onboarding publica `IntegrationSyncRequested` com chave idempotente e reaproveita o outbox/worker oficial. |
| Unidade Produtiva | EXISTE E ATENDE | Continua obrigatória para prontidão operacional. |
| Estrutura territorial | EXISTE E ATENDE | Propriedade, áreas e talhões já suportam a jornada do café. |
| Importação inicial controlada | EXISTE E ATENDE | Console Sankhya, jobs, health, logs e governança de pendências já existem. |
| Associações `PENDING` | EXISTE E ATENDE | Governança e reconciliação manual já estão implementadas. |
| Primeira safra | EXISTE E ATENDE | Criação da safra já reaproveita o fluxo oficial sem automação indevida. |
| Planejamento agronômico | EXISTE E ATENDE | `SafraTarefa` permanece como camada agronômica. |
| Operação planejada | EXISTE E ATENDE | `OperacaoAgricola` com status `PLANEJADA` já é a ordem de serviço logística. |
| Planejamento logístico | EXISTE E ATENDE | Máquina, operador e produto já pertencem à operação planejada, não à tarefa agronômica. |
| Campo PWA | EXISTE E ATENDE | Ativação, sync, caderno e execução offline-first já existem. |
| Correção PLANEJADA → REALIZADA | EXISTE E ATENDE | Estoque, custos e gatilhos já respeitam a transição correta. |
| Auditoria pós-correção | EXISTE E ATENDE | Relatório final aprovou a jornada PWA para piloto. |
| Recommendation Engine | EXISTE E ATENDE | Continua ativo após fatos operacionais reais. |
| Alert Engine | EXISTE E ATENDE | Continua ativo após fatos operacionais reais. |
| Dashboard, DRE e Rentabilidade | EXISTE E ATENDE | Painéis já refletem a cadeia operacional e econômica existente. |

## 5. Jornada oficial do cliente

Fluxo oficial atualizado:

1. Onboarding Intent-Based
2. Seleção da cultura Café
3. Seleção ERP Sankhya
4. Conclusão do onboarding
5. Aplicação automática do CoffeeTemplate
6. Aplicação automática dos OperationTemplates
7. Sincronização assíncrona Sankhya
8. Validação da Unidade Produtiva
9. Validação da Estrutura Territorial
10. Importação inicial controlada
11. Reconciliação das associações `PENDING`
12. Criação da primeira safra
13. Planejamento agronômico
14. Geração das operações planejadas
15. Planejamento logístico
16. Sincronização Campo PWA
17. Execução da operação
18. Conclusão da operação
19. Baixa de estoque FIFO
20. Custos
21. Financeiro
22. Integração Sankhya
23. Recommendation Engine
24. Alert Engine
25. Dashboard
26. Rentabilidade

## 6. Obrigatório, opcional e pós-piloto

Obrigatório para o Dry Run e para o primeiro cliente:

- onboarding por intenção concluído;
- cultura `CAFE` selecionada;
- ERP `SANKHYA` selecionado;
- CoffeeTemplate aplicado;
- OperationTemplates aplicados;
- `UnidadeProdutiva` válida;
- estrutura territorial válida;
- integração Sankhya validada;
- importação inicial executada;
- pendências `PENDING` críticas reconciliadas;
- primeira safra criada;
- planejamento agronômico concluído;
- operação planejada gerada;
- Campo PWA sincronizado;
- transição `PLANEJADA -> REALIZADA` validada;
- baixa FIFO, custos, financeiro, alertas e rentabilidade coerentes.

Opcional no piloto:

- ampliação de masters P1 além do necessário;
- comercialização completa além do fluxo mínimo do cliente;
- uso intensivo de contas bancárias, carteira e centros adicionais;
- jornada Campo PWA em todas as frentes operacionais, se o cliente começar só pelo backoffice.

Pós-piloto:

- expansão de coberturas P1/P2;
- otimizações de tipos de operação;
- aprofundamento societário empresa/filial;
- extensões de comercialização e automações adicionais.

## 7. Cronograma D-5 a D+7

### D-5

Objetivo:
Preparar tenant, acessos, onboarding e premissas do piloto.

Responsáveis:
Equipe AgroSaaS, administrador do cliente, TI do cliente.

Telas e rotas:

- `/login`
- `/selecionar-tenant`
- `/onboarding/configurar`
- `/dashboard/implantacao/wizard`

Dados mínimos:

- tenant;
- owner/admin;
- cultura principal;
- ERP principal;
- módulos selecionados.

Passos:

1. Acessar o tenant correto.
2. Concluir o onboarding por intenção.
3. Confirmar que o dashboard foi liberado.
4. Abrir o Wizard e verificar status inicial.

Validação:

- onboarding concluído;
- cultura e ERP persistidos;
- tenant operacional.

Critério de GO:

- owner/admin ativo;
- onboarding finalizado;
- Wizard acessível.

Critério de NO-GO:

- tenant incorreto;
- onboarding incompleto;
- acesso administrativo ausente.

Evidências:

- prints do onboarding;
- print do Wizard;
- registro do tenant e do usuário responsável.

### D-4

Objetivo:
Confirmar a fundação automática do tenant e a base territorial.

Responsáveis:
Equipe AgroSaaS, administrador do cliente.

Telas e rotas:

- `/dashboard/implantacao/wizard`
- `/cadastros/propriedades`
- cadastros de imóveis e áreas

Dados mínimos:

- `UnidadeProdutiva`;
- propriedade;
- áreas rurais;
- talhões.

Passos:

1. Validar `UnidadeProdutiva`.
2. Validar propriedade e vínculo territorial.
3. Confirmar áreas e talhões.
4. Registrar qualquer lacuna estrutural.

Validação:

- unidade produtiva ativa;
- estrutura mínima pronta;
- talhões disponíveis.

Critério de GO:

- território consistente.

Critério de NO-GO:

- ausência de unidade produtiva;
- ausência de talhão ou área operacional mínima.

Evidências:

- print do Wizard;
- print da fazenda;
- lista de talhões e áreas.

### D-3

Objetivo:
Validar a integração Sankhya e disparar a trilha inicial.

Responsáveis:
Equipe AgroSaaS, TI do cliente, responsável Sankhya.

Telas e rotas:

- `/dashboard/settings/integracoes/erp`
- outbox worker e logs operacionais

Dados mínimos:

- credenciais Sankhya;
- ambiente;
- configuração ativa da integração.

Passos:

1. Abrir o console Sankhya.
2. Confirmar status da configuração.
3. Executar teste de conexão.
4. Verificar jobs, health, logs e timeline.
5. Confirmar o processamento assíncrono do onboarding, quando aplicável.

Validação:

- teste de conexão aprovado;
- health coerente;
- configuração reconhecida.

Critério de GO:

- integração configurada e testada.

Critério de NO-GO:

- autenticação falhou;
- ambiente errado;
- configuração ausente.

Evidências:

- print do teste de conexão;
- snapshot de jobs/logs;
- IDs de eventos e jobs, quando houver.

### D-2

Objetivo:
Executar importação inicial e governança das associações.

Responsáveis:
Equipe AgroSaaS.

Telas e rotas:

- `/dashboard/settings/integracoes/erp`
- governança de pendências no console Sankhya

Dados mínimos:

- pessoas;
- produtos;
- vínculos oficiais P0;
- documentos e títulos relevantes do piloto.

Passos:

1. Executar importação inicial controlada.
2. Revisar pessoas, produtos e documentos importados.
3. Abrir pendências `PENDING`.
4. Reconciliar o que tiver vínculo local claro.
5. Registrar o que ficar pendente.

Validação:

- importação inicial concluída;
- vínculos P0 coerentes;
- pendências críticas tratadas.

Critério de GO:

- sem duplicidade silenciosa;
- pendências críticas sob controle.

Critério de NO-GO:

- pendência crítica sem destino claro;
- duplicidade relevante;
- importação parcial sem rastreabilidade.

Evidências:

- lista de pendências;
- reconciliações executadas;
- registros locais e externos vinculados.

### D-1

Objetivo:
Preparar a primeira safra e o plano operacional.

Responsáveis:
Equipe AgroSaaS, administrador do cliente, agrônomo/gestor.

Telas e rotas:

- `/agricola/safras`
- `/agricola/safras/[id]`
- `/tarefas/{tarefa_id}/planejar-operacao`
- `/agricola/operacoes`

Dados mínimos:

- safra;
- cultura;
- talhões;
- tarefas agronômicas;
- máquina, operador e insumos nas operações planejadas.

Passos:

1. Criar a primeira safra com confirmação explícita do usuário.
2. Validar cultura, área e talhões.
3. Revisar planejamento agronômico.
4. Gerar operações planejadas a partir das tarefas.
5. Completar a camada logística nas operações planejadas.

Validação:

- primeira safra criada;
- tarefas agronômicas coerentes;
- operações `PLANEJADA` geradas;
- logística associada.

Critério de GO:

- safra pronta;
- operação planejada disponível no backoffice e apta ao Campo.

Critério de NO-GO:

- safra incompleta;
- operação planejada sem operador, máquina ou insumo onde isso for indispensável.

Evidências:

- ID da safra;
- print do painel da safra;
- IDs das operações planejadas.

### D0

Objetivo:
Executar o primeiro ciclo operacional real.

Responsáveis:
Equipe AgroSaaS, operador de campo, administrador do cliente.

Telas e rotas:

- `apps/campo`: `/activate`, `/pin`, `/home`, `/sync`, `/campo/tarefa/[id]`, `/campo/aplicacao`, `/campo/colheita`, `/caderno`, `/recomendacoes`
- Web: `/dashboard/settings/integracoes/erp`, `/dashboard/agricola/operacoes`, `/dashboard/agricola/rastreabilidade`, `/dashboard/agricola/rentabilidade`

Dados mínimos:

- dispositivo ativado;
- sync inicial concluído;
- operação planejada disponível;
- insumos vinculados.

Passos:

1. Ativar o dispositivo Campo PWA.
2. Executar sync inicial.
3. Abrir a operação planejada.
4. Realizar a operação e sincronizar a conclusão.
5. Confirmar a transição `PLANEJADA -> REALIZADA`.
6. Validar a baixa FIFO, custos e eventos subsequentes.

Validação:

- operação concluída;
- estoque baixado corretamente;
- custo e financeiro coerentes;
- integração e eventos disparados sem duplicidade.

Critério de GO:

- transição operacional íntegra;
- sem baixa dupla;
- sem custo congelado;
- sem divergência crítica.

Critério de NO-GO:

- PWA não sincroniza;
- operação conclui sem efeitos de estoque;
- baixa ocorre ainda em `PLANEJADA`;
- erro grave de custo ou financeiro.

Evidências:

- print do PWA;
- ID da operação;
- movimentos de estoque;
- evidência do custo;
- logs/eventos/outbox.

### D+1 a D+3

Objetivo:
Estabilizar a cadeia operacional após o primeiro uso real.

Responsáveis:
Equipe AgroSaaS.

Checklist diário:

- jobs Sankhya;
- outbox;
- health;
- pendências `PENDING`;
- estoque;
- custos;
- financeiro;
- recommendation;
- alertas;
- dashboard.

### D+4 a D+7

Objetivo:
Validar repetibilidade e consistência da operação assistida.

Responsáveis:
Equipe AgroSaaS, cliente, operação de campo.

Checklist diário:

- nova sincronização;
- novas operações planejadas;
- execução real;
- rastreabilidade;
- rentabilidade;
- incidentes e correções.

## 8. Jornadas operacionais

### Jornada 1 - Implantação

Objetivo:
Concluir o onboarding e preparar o tenant.

Pré-requisitos:

- tenant criado;
- owner/admin ativo.

Telas:

- `/onboarding/configurar`
- `/dashboard/implantacao/wizard`

Rotas:

- `POST /config/onboarding/configurar`
- rotas do Wizard

Passos:

1. Selecionar cultura `CAFE`.
2. Selecionar ERP `SANKHYA`.
3. Selecionar módulos.
4. Concluir onboarding.

Resultado esperado:

- tenant pronto;
- onboarding marcado como completo.

Validação:

- cultura, ERP e módulos persistidos.

Critério de GO:

- onboarding finalizado sem erro.

Critério de NO-GO:

- falha de persistência;
- Wizard indisponível.

Evidências:

- print do onboarding;
- print do Wizard.

### Jornada 2 - Preparação da Fazenda

Objetivo:
Validar unidade produtiva e território.

Pré-requisitos:

- tenant operacional.

Telas:

- Wizard;
- propriedades;
- áreas rurais/talhões.

Rotas:

- rotas de propriedades, áreas e Wizard.

Passos:

1. Confirmar unidade produtiva.
2. Confirmar propriedade.
3. Confirmar talhões.

Resultado esperado:

- estrutura territorial pronta para a safra.

Validação:

- sem pendência estrutural crítica.

Critério de GO:

- território coerente.

Critério de NO-GO:

- falta de unidade ou talhão.

Evidências:

- lista de talhões;
- print da estrutura territorial.

### Jornada 3 - Integração ERP

Objetivo:
Validar Sankhya e importar a base mínima.

Pré-requisitos:

- integração configurada;
- acesso ao console.

Telas:

- `/dashboard/settings/integracoes/erp`

Rotas:

- endpoints do console Sankhya;
- governança de pendências.

Passos:

1. Testar conexão.
2. Confirmar status e health.
3. Executar importação inicial.
4. Revisar pendências `PENDING`.

Resultado esperado:

- integração funcional;
- dados mínimos importados.

Validação:

- pessoas, produtos e vínculos P0 disponíveis.

Critério de GO:

- sem bloqueio crítico de integração.

Critério de NO-GO:

- falha de conexão ou de rastreabilidade.

Evidências:

- jobs;
- health;
- reconciliações.

### Jornada 4 - Primeira Safra

Objetivo:
Criar a primeira safra real do cliente.

Pré-requisitos:

- território pronto.

Telas:

- `/agricola/safras`
- `/agricola/safras/[id]`

Rotas:

- rotas oficiais de safra.

Passos:

1. Criar a safra.
2. Associar cultura e talhões.
3. Confirmar área e metas.

Resultado esperado:

- safra criada em modo operacional.

Validação:

- ID de safra válido;
- sem duplicidade.

Critério de GO:

- safra pronta para planejamento.

Critério de NO-GO:

- safra inconsistente ou incompleta.

Evidências:

- ID e print da safra.

### Jornada 5 - Planejamento Agronômico

Objetivo:
Registrar a intenção agronômica.

Pré-requisitos:

- safra criada.

Telas:

- tarefas e checklist da safra;
- páginas de operações e acompanhamento.

Rotas:

- rotas de tarefas agronômicas.

Passos:

1. Revisar tarefas da safra.
2. Ajustar intenção agronômica.
3. Confirmar fase e datas previstas.

Resultado esperado:

- `SafraTarefa` pronta para conversão logística.

Validação:

- tarefas consistentes por fase e talhão.

Critério de GO:

- intenção agronômica clara.

Critério de NO-GO:

- tarefa sem talhão ou data mínima.

Evidências:

- IDs das tarefas;
- print do planejamento.

### Jornada 6 - Planejamento Logístico

Objetivo:
Gerar ordens de serviço reais.

Pré-requisitos:

- tarefa agronômica válida.

Telas:

- `/agricola/operacoes`
- páginas da safra com tarefas e operações

Rotas:

- `POST /tarefas/{tarefa_id}/planejar-operacao`

Passos:

1. Gerar a operação planejada.
2. Associar máquina, operador e insumos.
3. Revisar status `PLANEJADA`.

Resultado esperado:

- `OperacaoAgricola` pronta para execução.

Validação:

- operação planejada criada de forma idempotente.

Critério de GO:

- operação visível e pronta para o Campo.

Critério de NO-GO:

- falta de dados logísticos essenciais.

Evidências:

- ID da operação;
- print da ordem planejada.

### Jornada 7 - Execução Campo PWA

Objetivo:
Executar a ordem em campo e sincronizar corretamente.

Pré-requisitos:

- dispositivo ativado;
- operação planejada sincronizada.

Telas:

- `apps/campo`:
  - `/activate`
  - `/pin`
  - `/home`
  - `/sync`
  - `/campo/tarefa/[id]`
  - `/campo/aplicacao`
  - `/campo/colheita`
  - `/caderno`

Rotas:

- sync pull/push do Campo;
- `PATCH /operacoes/{id}`.

Passos:

1. Ativar dispositivo.
2. Sincronizar.
3. Abrir a tarefa/operação.
4. Executar.
5. Concluir como `REALIZADA`.

Resultado esperado:

- operação concluída com sync íntegro.

Validação:

- payload mínimo já aciona a baixa correta;
- retentativa não duplica.

Critério de GO:

- fluxo offline-first funcional.

Critério de NO-GO:

- sync falha;
- transição não dispara os efeitos reais.

Evidências:

- prints do PWA;
- IDs de sync e operação.

### Jornada 8 - Financeiro e Estoque

Objetivo:
Garantir que a execução real produziu reflexos corretos.

Pré-requisitos:

- operação `REALIZADA`.

Telas:

- estoque;
- DRE;
- custos;
- financeiro.

Rotas:

- rotas de estoque, despesas, receitas e DRE.

Passos:

1. Validar baixa FIFO.
2. Validar custo da operação.
3. Validar reflexo financeiro.

Resultado esperado:

- estoque, custo e financeiro coerentes.

Validação:

- sem baixa em `PLANEJADA`;
- sem baixa dupla;
- sem custo zero indevido em operação realizada.

Critério de GO:

- cadeia econômica consistente.

Critério de NO-GO:

- divergência de saldo ou custo.

Evidências:

- movimento de estoque;
- custo;
- registro financeiro correlato.

### Jornada 9 - Integrações e Eventos

Objetivo:
Validar a cadeia assíncrona e os fatos operacionais.

Pré-requisitos:

- operação realizada;
- integração ativa.

Telas:

- console Sankhya;
- logs e jobs.

Rotas:

- eventos/outbox;
- console Sankhya.

Passos:

1. Revisar backlog do outbox.
2. Confirmar processamento.
3. Confirmar efeitos esperados na integração Sankhya.

Resultado esperado:

- outbox processado;
- jobs de integração íntegros.

Validação:

- sem fila presa crítica;
- sem reprocesso indevido.

Critério de GO:

- cadeia assíncrona saudável.

Critério de NO-GO:

- backlog crítico;
- erro recorrente de subscriber ou relay.

Evidências:

- IDs de eventos;
- backlog;
- logs do worker.

### Jornada 10 - Gestão e Indicadores

Objetivo:
Validar a leitura gerencial final do piloto.

Pré-requisitos:

- fatos operacionais e econômicos concluídos.

Telas:

- dashboard;
- rastreabilidade;
- rentabilidade;
- recomendações.

Rotas:

- dashboards agrícolas e financeiros;
- recommendation e alerts.

Passos:

1. Revisar recommendation engine.
2. Revisar alert engine.
3. Revisar dashboard.
4. Revisar rentabilidade e rastreabilidade.

Resultado esperado:

- visão gerencial coerente com a execução real.

Validação:

- rentabilidade consistente;
- alertas e recomendações coerentes com os fatos.

Critério de GO:

- indicadores compatíveis com a operação executada.

Critério de NO-GO:

- dashboard inconsistente;
- rentabilidade incompatível com custos e estoque.

Evidências:

- prints do dashboard;
- prints de rentabilidade e rastreabilidade.

## 9. Execução do Dry Run

Para cada etapa do Dry Run registrar:

- horário de início;
- horário de término;
- tempo gasto;
- quantidade de cliques aproximada;
- dificuldade encontrada;
- incidente;
- severidade;
- observações;
- necessidade de intervenção técnica;
- evidências.

Modelo operacional:

| Jornada | Início | Término | Tempo | Cliques aprox. | Dificuldade | Incidente | Severidade | Intervenção técnica | Evidências | Observações |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Implantação |  |  |  |  |  |  |  |  |  |  |
| Preparação da Fazenda |  |  |  |  |  |  |  |  |  |  |
| Integração ERP |  |  |  |  |  |  |  |  |  |  |
| Primeira Safra |  |  |  |  |  |  |  |  |  |  |
| Planejamento Agronômico |  |  |  |  |  |  |  |  |  |  |
| Planejamento Logístico |  |  |  |  |  |  |  |  |  |  |
| Execução Campo PWA |  |  |  |  |  |  |  |  |  |  |
| Financeiro e Estoque |  |  |  |  |  |  |  |  |  |  |
| Integrações e Eventos |  |  |  |  |  |  |  |  |  |  |
| Gestão e Indicadores |  |  |  |  |  |  |  |  |  |  |

Tabela consolidada ao final:

| Jornada | Status | Tempo | Problemas | Severidade | Aprovado |
| --- | --- | --- | --- | --- | --- |
| Implantação |  |  |  |  |  |
| Preparação da Fazenda |  |  |  |  |  |
| Integração ERP |  |  |  |  |  |
| Primeira Safra |  |  |  |  |  |
| Planejamento Agronômico |  |  |  |  |  |
| Planejamento Logístico |  |  |  |  |  |
| Execução Campo PWA |  |  |  |  |  |
| Financeiro e Estoque |  |  |  |  |  |
| Integrações e Eventos |  |  |  |  |  |
| Gestão e Indicadores |  |  |  |  |  |

## 10. Plano de contingência

| Situação | Resposta |
| --- | --- |
| Onboarding falha | Repetir a submissão apenas após validar tenant, sessão e payload. |
| CoffeeTemplate ou OperationTemplates não aparecem | Validar persistência da intenção, verificar cópia idempotente e reprocessar onboarding apenas se seguro. |
| Sankhya sem configuração | Registrar `PENDENTE` e seguir para configuração manual no console antes do piloto. |
| Importação inicial com pendência crítica | Não avançar para safra operacional até reconciliar. |
| Operação planejada sem recurso essencial | Não enviar ao Campo. Corrigir no backoffice. |
| Campo PWA não sincroniza | Revalidar ativação, sync inicial e fila local antes de executar a operação real. |
| Operação `REALIZADA` sem baixa FIFO | Tratar como bloqueio crítico e interromper o dry run. |
| Outbox preso | Registrar backlog, analisar logs do worker e impedir aprovação até normalizar. |

## 11. Checklist final de homologação

□ Onboarding concluído

□ CoffeeTemplate aplicado

□ OperationTemplates aplicados

□ Unidade Produtiva validada

□ Estrutura territorial validada

□ Integração Sankhya validada

□ Importação inicial concluída

□ Associações reconciliadas

□ Primeira Safra criada

□ Planejamento Agronômico concluído

□ Operações Planejadas geradas

□ Planejamento Logístico validado

□ Campo PWA sincronizado

□ Operação executada

□ Estoque baixado corretamente

□ Custos apropriados

□ Financeiro consistente

□ Outbox processado

□ Sankhya sincronizado

□ Recommendation atualizado

□ Alert Engine atualizado

□ Dashboard consistente

□ Rentabilidade consistente

## 12. Conclusão

O roteiro oficial do piloto deixa de representar apenas um go-live assistido tradicional e passa a refletir a jornada real da plataforma atual:

- onboarding orientado por intenção;
- aplicação automática de templates de café;
- disparo assíncrono da integração Sankhya via outbox;
- primeira safra com confirmação explícita;
- separação correta entre planejamento agronômico e planejamento logístico;
- execução segura no Campo PWA;
- baixa FIFO, custos, financeiro e integrações protegidos pela transição correta de status;
- fechamento gerencial em recommendation, alertas, dashboard e rentabilidade.

Este é o guia único para Dry Run, homologação funcional, piloto assistido e Go-Live do primeiro cliente.

