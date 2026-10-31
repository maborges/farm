# INITIAL-LOAD-01 — Auditoria da cobertura de catálogos

**Escopo:** inspeção do repositório, sem consultas a bancos, execução de seeds ou alteração da aplicação.  
**Resultado:** avaliação do `initial_load` e das quatro tabelas de monitoramento/fitossanitários solicitadas.

## Resumo executivo

O `run.py` executa oito grupos de carga global. O catálogo de pragas, doenças e plantas daninhas (`monitoramento_catalogo`) tem seed próprio e contém no código 31 entradas globais, mas é opcional e não é chamado pelo orquestrador. Isso corresponde aos 31 registros globais ativos informados para a Hostinger. Já `modelos_fitossanitarios` é um cadastro de regras de risco que aceita modelos globais e por tenant; não há seed nem conjunto padrão de regras no código. Sem regras, o motor climático retorna uma lista vazia de riscos de doenças, sem impedir os demais fluxos da aplicação.

`monitoramento_pragas` é registro operacional da avaliação de campo e deve ser criado durante o uso. `pragas_doencas` pertence a um fluxo de IA diagnóstica legado/incompleto: sua migration histórica define um catálogo de diagnósticos, mas o modelo ORM atual não contém esses atributos e o endpoint associado é um stub. Não há evidência suficiente para carregá-la como catálogo de implantação.

**Conclusão:** o catálogo de monitoramento está coberto por seed independente; não há evidência que justifique adicionar `monitoramento_pragas` ou `pragas_doencas` à carga inicial. `modelos_fitossanitarios` é uma lacuna somente para disponibilizar a análise climática de risco fitossanitário com regras globais. Antes de homologar esse recurso, deve haver decisão agronômica e validação das regras; não se recomenda inventar regras nem criar seed sem essa validação. Para homologação da plataforma e dos fluxos gerais, não há bloqueador de carga inicial comprovado neste escopo.

## 1. Como a carga inicial está organizada

`services/api/scripts/initial_load/run.py:27-72` registra os modelos com `register_models()` e `configure_mappers()` e executa oito etapas: catálogos revisados; perfis; planos; culturas; parâmetros de solo; estágios CRM; base de conhecimento; identidade administrativa e templates de e-mail. O runner não chama o seed do catálogo fitossanitário nem o seed de checklists.

`services/api/scripts/initial_load/README.md:39-57` documenta como opcionais por módulo as cargas de agronomia, commodities, tabelas de produto, produtos, catálogo fitossanitário e checklists. Também orienta a ordem marcas/modelos antes de produtos e fornece o comando manual do seed de checklists. `seed_dev.py`, `seed.py`, `seed_plan_pricing.py`, `seed_crm_ofertas.py` e `test_map_configs.py` são explicitamente excluídos de implantação por serem demonstração, dados comerciais não aprovados ou fixture que modifica tenant.

| Componente de implantação | Classificação | Evidência / observação |
|---|---|---|
| Oito etapas do `run.py` | **COBERTO** | Etapas executadas em `initial_load/run.py:27-72`; dados e propósito descritos em `initial_load/README.md:7-37`. |
| Catálogo global de monitoramento | **INDEPENDENTE** | `initial_load/seed_catalogo_monitoramento.py`; não aparece nas oito etapas. |
| Templates globais de checklist | **INDEPENDENTE** | `initial_load/seed_checklist_templates.py`; README informa execução manual e caráter opcional. |
| Regras globais de risco fitossanitário | **PENDENTE para o recurso de risco climático** | A tabela/modelo e CRUD existem, mas não foi localizado seed ou catálogo de regras padrão. |
| Observações de monitoramento de campo | **SOB DEMANDA** | São criadas com tenant, safra, talhão e data a partir da operação. |
| `pragas_doencas` / cadastro do fluxo IA diagnóstico | **LEGADO / REVISAR** | A rota não implementa leitura/escrita útil; divergência entre migration e ORM. Não tratar como seed sem decisão funcional. |
| Seeds de desenvolvimento/demonstração | **LEGADO para implantação** | Excluídos explicitamente pelo README. |

## 2. Diagnóstico das quatro tabelas

### 2.1 `farms.monitoramento_catalogo` — catálogo global e customizável

- **Modelo:** `MonitoramentoCatalogo`, em `services/api/agricola/monitoramento/catalogo_model.py:9-29`. Registra tipo (`PRAGA`, `DOENCA`, `PLANTA_DANINHA`), nomes, cultura, unidade, NDE opcional, `tenant_id` e `is_system`.
- **Finalidade/consumidores:** `MonitoramentoCatalogoService.listar()` combina itens do tenant com itens de sistema globais (`tenant_id IS NULL`, `is_system IS TRUE`) em `services/api/agricola/monitoramento/service.py:18-46`. A rota de leitura é `/catalogo` em `services/api/agricola/monitoramento/router.py:44-54`. O formulário de monitoramento pode referenciar `catalogo_id`; `MonitoramentoService.criar()` usa o item para preencher nomes, tipo, unidade e NDE em `service.py:77-91`.
- **Criação:** existe edição/criação de entradas do tenant no endpoint `/catalogo` (`router.py:57-69`) e administração de entradas globais pelo backoffice (`services/api/core/routers/backoffice_tabelas.py:643-684`). O seed também cria somente entradas globais.
- **Seed:** `services/api/scripts/initial_load/seed_catalogo_monitoramento.py:13-47,53-87` define 31 entradas e não preenche NDE (`None`) por falta de validação técnica. Seu identificador de idempotência é `(tipo, nome_popular, cultura)` entre registros globais de sistema (`:53-87`). O script chama `register_models()` e `configure_mappers()` antes da consulta (`:90-99`) e confirma em um commit ao final (`:53-87`). Não está no `run.py`, embora o README o reconheça como carga opcional (`initial_load/README.md:39-42`).
- **Escopo/risco:** o seed limita a busca a `tenant_id IS NULL` e `is_system IS TRUE`, não altera entradas já existentes e adiciona as ausentes. A verificação é idempotente em execuções sequenciais; não há restrição única correspondente no modelo, portanto duas execuções concorrentes não têm garantia de impedir duplicatas. Não foi encontrada operação de exclusão/atualização no seed. Em falha antes do commit, a sessão não deve confirmar parcialmente a transação; o script, porém, não tem `rollback()` explícito no tratamento de exceção.
- **Migration:** `services/api/migrations/versions/abbf2ef99219_monitoramento_catalogo_nde.py:42-62` cria a estrutura, sem inserir referências. `0a0db412c2c8_tabelas_sistema_tenant_nullable.py:44-48` permite `tenant_id=NULL` para registros globais. Migrations são estruturais, não substituem o seed.
- **Estado conhecido:** este relatório considera como contexto informado pelo solicitante os 31 registros globais ativos na Hostinger; não houve consulta para confirmar o banco. O total e a composição do contrato do seed correspondem a 13 pragas, 10 doenças e 8 plantas daninhas.

**Classificação: INDEPENDENTE — carga já contemplada por seed separado.** Recomenda-se manter a execução explícita desse seed quando o módulo de monitoramento de campo for habilitado; não é necessário criar outro seed nem duplicar entradas no runner para responder à lacuna atual.

### 2.2 `farms.monitoramento_pragas` — registros operacionais de campo

- **Modelo:** `MonitoramentoPragas`, em `services/api/agricola/monitoramento/models.py:8-47`.
- **Finalidade:** guarda avaliações datadas associadas obrigatoriamente a `tenant_id`, `safra_id` e `talhao_id`, com infestação, NDE observado, decisão, evidências e vínculo opcional ao catálogo (`catalogo_id`). Portanto é dado de operação de uma fazenda, não catálogo de referência global.
- **Consumidores/criação:** endpoint `POST /` passa os dados à `MonitoramentoService.criar()` e confirma o registro em `router.py:74-89`. O serviço preenche dados do catálogo e o tenant (`service.py:71-115`); a listagem filtra pelo tenant e safra (`service.py:166-174`). Dashboard consome avaliações que atingiram NDE (`agricola/dashboard/service.py:158-168`).
- **Dependências:** requer tenant, safra, talhão e, opcionalmente, um catálogo. A migration `abbf2ef99219_monitoramento_catalogo_nde.py:120-126` adiciona a FK de `catalogo_id` com `SET NULL`.
- **Seed/migration:** migrations criam a estrutura; não foi localizada carga de observações padrão. A criação depende de ações de usuário/atividade de campo.

**Classificação: SOB DEMANDA.** Não deve receber registros artificiais na carga de implantação.

### 2.3 `farms.modelos_fitossanitarios` — regras configuráveis de risco

- **Modelo:** `ModeloFitossanitario`, em `services/api/agricola/climatico/models.py:71-93`. Cada regra contém cultura, doença e `regras_risco` JSON; `tenant_id` é nullable e o modelo aceita registros globais. O campo `is_global` existe no ORM, mas o serviço determina o escopo a partir de `tenant_id` (`service.py:480-485`).
- **Finalidade/consumo:** `ClimaService._calcular_risco_doencas()` busca culturas ativas e registros climáticos e depois carrega modelos por tenant e globais (`services/api/agricola/climatico/service.py:261-328`). Para cada modelo, avalia as regras JSON e forma probabilidade/nível (`:329-346,368-430`). Se não houver modelos aplicáveis, retorna `[]` (`:326-327`); a análise geral continua, mas esse bloco de risco de doenças fica sem resultados.
- **Global versus tenant:** o endpoint de listagem combina regras do tenant e globais e prioriza o tenant (`climatico/service.py:446-486`). O tenant pode criar regras; regras globais só podem ser mantidas pelo backoffice, e cópias para tenant são explícitas (`climatico/service.py:508-558`, `router.py:128-176,182-213`). Assim, a tabela é **configurável por tenant e pela plataforma**, não exclusivamente um catálogo global imutável.
- **Seed/dados fixos:** não foi encontrado `seed_modelos_fitossanitarios` nem criação de instâncias `ModeloFitossanitario` em scripts de carga. O exemplo de formato JSON em `models.py:89-90` é comentário, não um conjunto de regras. A rotina `scripts/migrate_modelos_tenant.py` migra linhas existentes de SQLite para outra estrutura; não é carga inicial de catálogo nem seed de implantação (`:45-50`).
- **Migrations:** `services/api/migrations/versions/fb09b95925e1_add_modelofitossanitario.py:19-40` cria a tabela e índice, sem dados. `20260823_clima_inteligencia_integrity.py:29-69` adiciona escopo tenant/global, índices parciais de unicidade e RLS; também não insere modelos.
- **Idempotência/risco:** não existe seed a avaliar. O schema migrado prevê unicidade separada para regras globais e por tenant (`20260823_clima_inteligencia_integrity.py:54-69`). Uma futura carga deverá filtrar o escopo global e usar chave `(cultura, doença)` conforme as restrições; deve validar a forma esperada de `regras_risco` e adotar transação/rollback. As regras alteram uma indicação fitossanitária, por isso exigem origem e validação agronômica; valores ilustrativos não devem ser apresentados como padrão técnico.

**Classificação: PENDENTE apenas se a homologação incluir a análise climática de risco fitossanitário; caso contrário, REVISAR/adiar a decisão funcional.** O uso de modelos globais está previsto no código, porém sua ausência degrada esse recurso específico, não bloqueia a carga geral. O tenant também pode configurar regras via aplicação, mas o caminho requer acesso ao endpoint do módulo e conhecimento técnico dos limiares.

### 2.4 `farms.pragas_doencas` — fluxo de IA diagnóstica legado/incompleto

- **Modelo atual:** `PragasDoencas`, em `services/api/ia_diagnostico/models/pragas_doencas.py:12-23`, declara apenas `id`, `tenant_id`, `created_at` e `updated_at`. Não há relacionamento ORM explícito no arquivo.
- **Migration histórica:** `services/api/migrations/versions/fase2_ia_iot.py:23-37` define um catálogo com `nome`, `nome_cientifico`, `tipo`, `descricao`, `sintomas`, culturas afetadas e imagem. A mesma migration relaciona tratamentos/diagnósticos a esse catálogo (`:39-75`). Posteriormente, `tenant_integrity_repair_01b2_onda1.py:18-49` inclui a tabela em um reparo de tipo/FK para `tenant_id`; a migration histórica e o ORM atual demonstram deriva estrutural que precisa ser reconciliada antes de depender desse fluxo.
- **Consumidores:** o router `services/api/ia_diagnostico/routers/pragas_doencas.py:21-40` declara listagem e criação, mas retorna `[]` e `{}` com os comentários “Implementar lógica aqui”. A pesquisa não encontrou consumo operacional de `PragasDoencas` fora da declaração/import do próprio modelo. O router está sob o módulo `EXT_IA` e tier `PROFISSIONAL` (`:11-18`).
- **Dados:** não foi encontrado seed, conjunto fixo de referências ou inserção dessa tabela nas migrations. A migration cria estrutura; não carrega dados.

**Classificação: LEGADO / REVISAR, não PENDENTE de seed.** Evidência atual não sustenta que o fluxo esteja funcional ou que este registro seja o catálogo usado por monitoramento. O cadastro funcional de pragas/doenças para o monitoramento agrícola é `monitoramento_catalogo`, com modelo, endpoints e seed distintos. Antes de considerar `pragas_doencas` como catálogo de implantação, é necessária decisão sobre a implementação/uso dessa estrutura e alinhamento ORM/migration; isso está fora da correção mínima de carga inicial.

## 3. Catálogo global versus dados operacionais

| Tabela | Natureza comprovada no código | Precisa de seed de implantação? |
|---|---|---|
| `monitoramento_catalogo` | Catálogo comum de pragas, doenças e plantas daninhas, com entradas globais e customizações de tenant. | Há seed independente existente; carregá-lo quando o módulo for adotado. |
| `monitoramento_pragas` | Observação de campo pertencente a tenant, safra e talhão. | Não. Criada pela operação. |
| `modelos_fitossanitarios` | Regras JSON configuráveis globalmente e por tenant, consumidas pela análise climática. | Só para habilitar o motor com regras globais validadas. Não há seed atualmente. |
| `pragas_doencas` | Tabela histórica do módulo IA diagnóstico; API atual é stub e modelo não corresponde à migration inicial. | Não com evidência atual. Confirmar o destino funcional antes de qualquer carga. |

## 4. Segurança, ordem e idempotência

1. **Ordem:** o catálogo de monitoramento não depende de outros registros semânticos no seed; sua FK `tenant_id` é nula para dados globais, e `catalogo_id` em avaliações é opcional. Se carga de `modelos_fitossanitarios` for aprovada, depende apenas de tabela/migrations já aplicadas, não do catálogo de monitoramento. O runner inicial sempre registra os modelos antes das etapas; os scripts independentes de catálogo e checklist também chamam o registro central e `configure_mappers()` (`seed_catalogo_monitoramento.py:90-99`; `seed_checklist_templates.py:171-180`).
2. **Isolamento:** seed do catálogo filtra e grava somente `tenant_id=NULL`, `is_system=True`; os registros operacionais levam `tenant_id` obrigatório. Modelos fitossanitários têm `tenant_id` opcional e consultas explícitas do serviço separam dados do tenant e globais.
3. **Idempotência/concorrência:** o seed atual do catálogo insere apenas chaves ausentes e não reescreve nem exclui linhas existentes. A idempotência é sequencial; sem constraint única equivalente no modelo visível, não fica provada a proteção contra execuções simultâneas. Não há necessidade de mudar isso para corrigir cobertura. Seed futuro de regras deve apoiar-se na unicidade global/tenant que a migration posterior cria e ser transacional.
4. **Transação/falha:** o seed de catálogo confirma após percorrer entradas, em um único commit (`seed_catalogo_monitoramento.py:53-87`). Não foi localizado rollback explícito em bloco `except`; uma falha deve abortar a transação ainda não confirmada, mas a garantia deve ser verificada por teste se o seed for alterado. Nenhum seed foi executado nesta auditoria.
5. **RLS:** a migration de integridade dos modelos fitossanitários configura políticas RLS para a tabela (`20260823_clima_inteligencia_integrity.py:20-27,69`). Uma carga futura deve observar o contexto/permissões usados pelo processo de implantação; esta auditoria não testou conexão nem políticas em banco.

## 5. Lacunas e recomendação mínima

### Lacunas comprovadas

- **Cobertura do fluxo de risco fitossanitário climático:** há implementação consumidora e endpoints para modelos, mas nenhum seed ou regra padrão foi localizado. Sem modelos aplicáveis, o método retorna lista vazia. Isso é uma lacuna de conteúdo do recurso, não falha do `run.py` nem indisponibilidade geral do sistema.
- **Visibilidade do seed de monitoramento no processo de implantação:** o seed de `monitoramento_catalogo` existe, mas está fora do orquestrador e depende de execução separada. Como a tabela já tem, segundo o contexto fornecido, as 31 entradas previstas, não é uma carga faltante na instalação atual; em implantações futuras deve-se manter documentada a execução manual ou decidir incluí-lo explicitamente no fluxo modular.

### Não são lacunas de carga

- Não popular `monitoramento_pragas` com observações fictícias.
- Não inserir automaticamente `pragas_doencas` enquanto o endpoint for stub e a discrepância ORM/migration não for resolvida.
- Não copiar as 31 entradas de `monitoramento_catalogo` para `modelos_fitossanitarios`: os modelos são regras com estrutura e finalidade diferentes.

### Plano mínimo recomendado

1. **Nenhuma mudança imediata no runner nem nos seeds** para `monitoramento_pragas` ou `pragas_doencas`.
2. Para o módulo de monitoramento agrícola, continuar usando o seed independente `initial_load/seed_catalogo_monitoramento.py`; seus NDEs permanecem nulos até validação técnica, conforme o próprio contrato do script.
3. Antes de homologar a funcionalidade que exibe risco de doenças na análise climática, decidir se ela será habilitada na implantação. Se sim, obter e validar regras por cultura/doença com responsável agronômico, depois especificar uma carga global idempotente para `modelos_fitossanitarios`; não fabricar thresholds a partir do comentário de exemplo.
4. Tratar a implementação e a deriva de schema de `pragas_doencas` em revisão funcional/técnica própria antes de incluí-la em qualquer inventário de catálogo obrigatório.

## 6. Veredicto

**GO COM RESSALVAS.** A cobertura do `monitoramento_catalogo` está implementada por seed independente e, conforme o estado informado, já executada com 31 globais ativos. As demais tabelas não devem ser tratadas como uma carga inicial pendente: `monitoramento_pragas` é operacional, e `pragas_doencas` está sem fluxo funcional comprovado. A ressalva é específica: se a homologação incluir o cálculo climático de risco fitossanitário, a ausência de modelos globais validados deixará `risco_doencas` sem resultados; decidir e validar essa carga antes de homologar esse recurso. Nenhuma alteração de código foi feita e nenhum seed ou banco foi acessado.
