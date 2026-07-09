# Relatorio - Wizard de Implantacao Go-Live

Data: 2026-07-08

## Objetivo

Definir o passo a passo de cadastros necessario para deixar um tenant pronto para operar no AgroSaaS, com foco em melhorar a experiencia do usuario no wizard de configuracao em `/dashboard/implantacao/wizard`.

Este relatorio consolida:

- Cadastros obrigatorios e recomendados para operacionalizar o tenant.
- Funcionalidade de cada cadastro.
- Rota web e endpoint de API relacionados.
- Dependencias entre cadastros para montar um workflow guiado.
- Criterios minimos de validacao para go-live.
- Sugestoes de UX e produto para evoluir o wizard.

## Premissas

- O tenant ja existe e o usuario esta autenticado.
- O wizard deve operar sempre no contexto do `tenant_id` e da `unidade_produtiva_id` ativa quando aplicavel.
- O go-live minimo nao deve depender de equipe completa, convites, billing ou configuracoes administrativas externas ao dominio operacional.
- As etapas condicionais devem respeitar os modulos habilitados no tenant: agricultura, pecuaria, estoque, financeiro e frota/maquinas.
- Cadastros fundiarios, commodities, integracoes e documentos complementam a operacao, mas nao devem bloquear o go-live minimo se o modulo principal ja consegue registrar operacoes.

## Fluxo Recomendado

1. Diagnostico do tenant e modulos habilitados.
2. Decisao de implantacao: carga manual ou carga via ERP.
3. Se houver ERP, identificar qual ERP sera usado e quais cadastros serao carregados por integracao.
4. Cadastro da unidade produtiva ativa.
5. Cadastro da estrutura territorial.
6. Cadastro das atividades produtivas e catalogos base.
7. Configuracao dos modulos operacionais habilitados.
8. Revisao das pendencias bloqueantes e recomendadas.
9. Liberacao go-live.
10. Estabilizacao com tarefas pos-go-live.

## Decisao Inicial Obrigatoria

Logo apos o cadastramento do tenant, o wizard deve fazer uma pergunta obrigatoria:

- O tenant fara a implantacao com carga manual ou com carga via ERP?

Se a resposta for `carga via ERP`, o wizard deve pedir antes de qualquer cadastro operacional:

- ERP utilizado.
- Escopo da carga inicial.
- Quais entidades serao importadas.
- Se a carga sera carga unica, sincronizacao recorrente ou modelo hibrido.
- Responsavel pela homologacao da importacao.

Essa decisao e opcional do ponto de vista de produto, mas obrigatoria do ponto de vista de fluxo. O usuario precisa escolher explicitamente antes de seguir, porque essa escolha muda a ordem da implantacao e a experiencia do wizard.

## Workflow de Dependencias

```text
Tenant ativo
  -> Definir estrategia de carga
    -> Manual
      -> Seguir fluxo de cadastros no wizard
    -> ERP
      -> Identificar ERP
      -> Definir entidades importadas
      -> Executar carga inicial
      -> Validar dados importados
  -> Unidade produtiva ativa
    -> Areas rurais
      -> Talhoes, se agricultura
        -> Culturas
          -> Safras
            -> Vinculo safra-talhoes
              -> Operacoes agricolas
      -> Piquetes, se pecuaria
        -> Operacao pecuaria
    -> Depositos, se estoque
      -> Produtos
        -> Saldos e movimentacoes de estoque
    -> Plano de contas, se financeiro
      -> Lancamentos e rateios financeiros
    -> Equipamentos, se frota/maquinas
      -> Abastecimentos, manutencoes e apontamentos
    -> Pessoas e equipe operacional
      -> Responsaveis, fornecedores, clientes e operadores
```

## Minimo Para Go-Live

| Condicao | Cadastro minimo | Quando bloqueia |
| --- | --- | --- |
| Tenant operacional | Tenant ativo e usuario owner/admin com acesso | Sempre |
| Estrategia de carga definida | Usuario escolheu entre fluxo manual ou ERP | Sempre |
| ERP identificado | Nome do ERP e escopo de importacao definidos | Quando o usuario optar por carga via ERP |
| Unidade produtiva | Pelo menos uma unidade produtiva ativa | Sempre |
| Territorio | Pelo menos uma area rural ativa | Sempre |
| Agricultura | Pelo menos um talhao, cultura e safra vinculada | Quando agricultura estiver habilitada |
| Pecuaria | Pelo menos um piquete ou area pecuaria | Quando pecuaria estiver habilitada |
| Estoque | Pelo menos um deposito ativo e catalogo minimo de produtos | Quando estoque estiver habilitado |
| Financeiro | Plano de contas ativo ou seed aplicado | Quando financeiro estiver habilitado |
| Frota/maquinas | Pelo menos um equipamento ativo | Quando frota/maquinas estiver habilitado |
| Pessoas/equipe | Owner ativo; demais usuarios progressivos | Nao deve bloquear go-live minimo |

## Matriz de Cadastros

| Ordem | Etapa wizard | Cadastro | Funcionalidade | Rota web | Endpoint API | Pre-requisitos | Criterio minimo |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Diagnostico | Tenant e assinatura operacional | Confirma que o cliente possui tenant valido, plano ativo e modulos contratados. | `/onboarding`, `/dashboard/settings/tenant`, `/dashboard/settings/billing` | `/api/v1/onboarding/status`, endpoints de tenant/billing | Usuario autenticado e tenant criado | Tenant ativo e usuario com permissao de administracao |
| 2 | Diagnostico | Estrategia de carga inicial | Coleta a decisao do cliente entre carga manual e carga via ERP, definindo o fluxo do wizard. | `/dashboard/implantacao/wizard` | Recomendado criar `/api/v1/wizard/workflow` ou persistencia equivalente | Tenant ativo | Usuario escolheu explicitamente manual ou ERP |
| 3 | Integracoes | ERP utilizado | Identifica qual ERP sera integrado e habilita a trilha de importacao de cadastros. | `/configuracoes/integracoes` | Validar endpoint especifico da integracao | Estrategia de carga = ERP | ERP definido quando houver carga via ERP |
| 4 | Integracoes | Escopo da carga ERP | Define quais entidades serao importadas pelo ERP: produtos, estoques, contas correntes, plano de contas e demais cadastros. | `/configuracoes/integracoes` | Validar endpoint especifico da integracao | ERP identificado | Escopo da importacao homologado antes da carga |
| 5 | Unidade produtiva | Unidade produtiva / propriedade | Representa a fazenda, filial rural ou unidade operacional usada como recorte principal das operacoes. | `/cadastros/propriedades` | `/api/v1/unidades-produtivas`, `/api/v1/cadastros/propriedades` | Tenant ativo | Existe ao menos uma unidade produtiva ativa para o tenant |
| 6 | Territorio | Estrutura territorial / areas rurais | Organiza glebas, areas, setores e demais recortes fisicos vinculados a unidade produtiva. | `/cadastros/propriedades/[id]`, `/cadastros/propriedades/talhoes` | `/api/v1/cadastros/areas-rurais` | Unidade produtiva ativa | Existe ao menos uma area rural ativa |
| 7 | Agricultura | Talhoes | Define as areas produtivas agricolas usadas em safra, operacoes, planejamento e custos por hectare. | `/cadastros/propriedades/talhoes` | `/api/v1/cadastros/areas-rurais?tipo=TALHAO` | Unidade produtiva ativa e estrutura territorial | Existe ao menos um talhao ativo quando agricultura estiver habilitada |
| 8 | Pecuaria | Piquetes | Define areas de manejo pecuario usadas para lotacao, movimentacao e manejo animal. | `/dashboard/pecuaria/piquetes` | `/api/v1/cadastros/areas-rurais?tipo=PIQUETE` | Unidade produtiva ativa e estrutura territorial | Existe ao menos um piquete ativo quando pecuaria estiver habilitada |
| 9 | Agricultura | Culturas e variedades | Cadastra culturas produtivas e variedades usadas em safras, planejamento, fenologia e indicadores agronomicos. | `/dashboard/agricola/cadastros/culturas` | `/api/v1/cadastros/culturas` | Modulo agricultura habilitado | Existe ao menos uma cultura ativa antes da criacao da safra |
| 10 | Agricultura | Safras | Cria o ciclo agricola operacional, com cultura, ano safra, status, metas e unidade produtiva. | `/agricola/safras` | `/api/v1/safras` | Unidade produtiva ativa, talhoes e cultura | Existe ao menos uma safra planejada ou em andamento |
| 11 | Agricultura | Vinculo safra-talhoes | Relaciona a safra aos talhoes cultivados para permitir planejamento, operacoes, estoque aplicado e rentabilidade. | `/agricola/safras/[id]/production-units`, `/agricola/safras/[id]` | `/api/v1/safras/{id}/talhoes` | Safra criada e talhoes ativos | Safra possui ao menos um talhao vinculado |
| 12 | Catalogos | Categorias, marcas e modelos de produto | Estrutura o catalogo para padronizar produtos, insumos, sementes, defensivos, fertilizantes e materiais. | `/cadastros/tabelas/categorias-produto`, `/cadastros/tabelas/marcas`, `/cadastros/tabelas/modelos` | `/api/v1/cadastros/categorias-produto`, `/api/v1/cadastros/marcas`, `/api/v1/cadastros/modelos-produto` | Tenant ativo | Recomendado antes de produtos; pode ser seedado |
| 13 | Catalogos | Produtos | Cadastra ou importa itens usados por estoque, compras, operacoes agricolas, pecuaria e custos. | `/cadastros/produtos` | `/api/v1/cadastros/produtos` | Categorias/marcas/modelos recomendados, ou ERP definido para importacao | Existe catalogo minimo quando agricultura ou estoque estiver habilitado |
| 14 | Estoque | Depositos | Define almoxarifados, fazendas-deposito e pontos de armazenagem para saldos e movimentacoes. | `/suprimentos/estoque` | `/api/v1/estoque/depositos` | Unidade produtiva ativa | Existe ao menos um deposito ativo quando estoque estiver habilitado |
| 15 | Estoque | Saldos e movimentacoes iniciais | Inicializa saldo fisico-financeiro dos produtos e habilita entrada, saida, transferencia, reserva e requisicao. Pode vir de carga ERP ou ajuste manual. | `/suprimentos/estoque`, `/estoque/movimentacoes/[id]` | `/api/v1/estoque/saldos`, `/api/v1/estoque/movimentacoes` | Deposito ativo e produtos cadastrados/importados | Recomendado para operar estoque; saldo zero pode ser aceito no go-live |
| 16 | Financeiro | Contas correntes | Define contas financeiras operacionais para recebimentos, pagamentos, conciliacao e saldos. Pode ser carga manual ou importada do ERP. | Rota frontend a validar | Endpoint API a validar | Modulo financeiro habilitado e estrategia de carga definida | Recomendado antes da operacao financeira assistida |
| 17 | Financeiro | Plano de contas | Define a estrutura contabil-gerencial usada em lancamentos, custos, receitas, DRE e rateios. Pode ser criado manualmente, seedado ou importado do ERP. | `/dashboard/financeiro/planos-conta` | `/api/v1/financeiro/planos-conta`, `/api/v1/financeiro/planos-conta/seed` | Modulo financeiro habilitado | Plano de contas minimo criado, seed aplicado ou carga ERP concluida |
| 18 | Pessoas | Pessoas e parceiros | Cadastra fornecedores, clientes, produtores, colaboradores e demais partes relacionadas. | `/cadastros/pessoas` | `/api/v1/cadastros/pessoas` | Tenant ativo | Recomendado para compras, vendas, contratos e responsaveis; nao bloqueia go-live minimo |
| 19 | Pessoas | Tipos de relacionamento | Padroniza vinculos entre pessoas, unidades, contratos e operacoes. | `/cadastros/tipos-relacionamento` | `/api/v1/cadastros/tipos-relacionamento` | Pessoas/parceiros quando houver relacionamento | Recomendado para governanca cadastral |
| 20 | Frota/maquinas | Equipamentos e frota | Cadastra maquinas, implementos, veiculos e ativos usados em operacoes, abastecimentos e manutencoes. | `/cadastros/equipamentos` | `/api/v1/cadastros/equipamentos` | Unidade produtiva ativa e modulo frota/maquinas habilitado | Existe ao menos um equipamento ativo quando frota/maquinas estiver habilitado |
| 21 | Frota/maquinas | Documentos de equipamentos | Controla documentos, vencimentos e anexos operacionais da frota. | `/cadastros/equipamentos/[id]/documentos` | `/api/v1/frota/documentos` | Equipamento cadastrado | Recomendado pos-go-live |
| 22 | Fundiario | Imoveis rurais | Cadastra imoveis, documentos fundiarios, CAR, CCIR, NIRF e informacoes legais. | `/cadastros/imoveis` | `/api/v1/imoveis` | Unidade produtiva/propriedade recomendada | Nao bloqueia operacao basica; relevante para compliance |
| 23 | Fundiario | Vinculo propriedade-imovel | Relaciona a unidade produtiva operacional aos imoveis rurais juridicos. | `/cadastros/imoveis/[id]/visao-fundiaria` | `/api/v1/propriedade-imovel` | Imovel rural e unidade produtiva | Recomendado para governanca fundiaria |
| 24 | Comercializacao | Commodities | Padroniza commodities, classificacoes, cotacoes e conversoes de unidade. | `/cadastros/commodities` | `/api/v1/cadastros/commodities` | Tenant ativo; culturas/safras recomendadas | Recomendado para comercializacao e analises de preco |
| 25 | Equipe | Equipe, perfis e acessos | Gerencia usuarios, convites, perfis e permissao por unidade produtiva. | `/dashboard/settings/team`, `/dashboard/settings/team/profiles` | `/api/v1/team/users`, `/api/v1/team/invite`, `/api/v1/team/roles` | Owner/admin ativo | Progressivo; equipe incompleta nao deve impedir go-live minimo |

## Carga Inicial Via ERP

Quando o usuario optar por ERP, o wizard deve tratar a integracao como trilha primaria de implantacao de dados mestres.

Entidades citadas como prioritarias para carga via ERP:

- Produtos.
- Estoques e saldos iniciais.
- Contas correntes.
- Plano de contas.

Entidades que tambem podem entrar na mesma trilha, se o ERP suportar:

- Pessoas e parceiros.
- Centros de custo e estruturas financeiras.
- Equipamentos.
- Cadastros auxiliares de catalogo.

Fluxo recomendado:

1. Perguntar se existe ERP logo apos o cadastro do tenant.
2. Se sim, identificar qual ERP sera usado.
3. Definir o escopo da carga inicial por entidade.
4. Executar importacao.
5. Validar consistencia da carga.
6. Mostrar ao usuario o que veio do ERP e o que ainda precisa de complemento manual.
7. Somente depois seguir para validacoes de go-live dos modulos.

Regra de UX:

- O wizard nao deve assumir carga manual por padrao sem perguntar.
- O wizard deve deixar o usuario decidir.
- Quando ERP for escolhido, os cards de cadastro precisam mudar de "criar cadastro" para "configurar importacao" ou "validar dados importados".

## Observacoes Sobre o Wizard Atual

- O checklist atual valida unidade produtiva, estrutura territorial, talhao, piquete, deposito, plano de contas, catalogo de produtos e equipamentos.
- Ha mapeamento tecnico para `CHECK_CULTURA` e `CHECK_INTEGRACAO_ERP`, mas estes itens precisam ser revisados para garantir que estejam presentes na definicao formal do checklist se forem realmente parte do fluxo.
- O alvo atual previsto para cultura deve ser conferido: o frontend encontrado usa `/dashboard/agricola/cadastros/culturas`, enquanto o target tecnico pode apontar para `/cadastros/culturas`. Recomenda-se alinhar o CTA ou criar alias de rota.
- A etapa `EQUIPE` existe no wizard como opcional. Isso esta correto para go-live minimo: convites e equipe completa nao podem bloquear a primeira operacao do tenant.
- As validacoes devem sempre usar recorte por `tenant_id` e, quando aplicavel, por `unidade_produtiva_id` ativa para evitar mensagens falsas de "nao existe unidade produtiva ativa".

## Proposta de Workflow Para UX

### Tela 1 - Diagnostico

Mostrar:

- Tenant identificado.
- Pergunta obrigatoria sobre uso de ERP.
- Unidade produtiva ativa selecionada, se existir.
- Modulos habilitados.
- Workflow gerado dinamicamente conforme os modulos.
- Pendencias bloqueantes e recomendadas.

Acao recomendada:

- Se o usuario informar uso de ERP, abrir imediatamente a etapa de identificacao do ERP e escopo de carga.
- Se nao houver unidade produtiva ativa, abrir CTA direto para criar a unidade.
- Se houver mais de uma unidade produtiva, exigir escolha explicita antes de avaliar cadastros dependentes.

### Tela 2 - Cadastros Essenciais

Agrupar por dependencia:

- Unidade produtiva.
- ERP e escopo de carga, quando aplicavel.
- Estrutura territorial.
- Talhoes ou piquetes conforme modulo.
- Produtos, depositos e plano de contas conforme modulo.

Cada card deve mostrar:

- Status: pendente, pronto, recomendado ou ignorado por modulo desabilitado.
- Motivo tecnico da pendencia.
- Dependencias bloqueantes.
- CTA principal.
- Tipo de origem: manual ou ERP.
- Tempo estimado.
- Opcao de seed quando aplicavel.

### Tela 3 - Operacao Inicial

Validar se o tenant ja consegue executar uma primeira rotina:

- Agricultura: criar safra, vincular talhoes e registrar operacao.
- Pecuaria: usar piquete em manejo.
- Estoque: registrar entrada ou ajuste inicial.
- Financeiro: registrar lancamento com plano de contas.
- Frota: usar equipamento em operacao ou apontamento.

### Tela 4 - Revisao Go-Live

Separar claramente:

- Bloqueantes: impedem operacao minima.
- Recomendados: melhoram qualidade e governanca.
- Pos-go-live: podem ser feitos depois sem travar uso.

## Sugestoes de Evolucao

1. Criar endpoint `/api/v1/wizard/workflow` que retorne os nos do workflow, dependencias, status, CTA e motivo da pendencia.
2. Exibir o contexto ativo do wizard no topo: tenant, estrategia de carga, ERP selecionado, unidade produtiva, modulos habilitados e usuario executor.
3. Adicionar etapa obrigatoria "Uso de ERP" logo no inicio do wizard.
4. Adicionar modo "criar sem sair do wizard" para unidade produtiva, talhao, piquete, deposito, produto, plano de contas e equipamento.
5. Quando ERP for escolhido, trocar o CTA por "configurar importacao", "executar carga" e "validar importacao".
6. Oferecer seeds assistidos para plano de contas, categorias de produto, culturas comuns e deposito padrao quando o usuario optar por fluxo manual.
7. Mostrar "proximo melhor passo" com base na primeira dependencia bloqueante, em vez de listar todos os erros simultaneamente.
8. Registrar telemetria do wizard: etapa iniciada, etapa concluida, CTA clicado, erro de validacao, tipo de carga escolhido e tempo ate go-live.
9. Diferenciar mensagem tecnica de mensagem ao usuario. Exemplo: "Cadastre uma unidade produtiva ativa para continuar" e, em detalhes, "CHECK_UNIDADE_PRODUTIVA retornou 0 registros ativos para tenant/unidade atual".
10. Adicionar auditoria de contexto para cada reavaliacao: `tenant_id`, `unidade_produtiva_id`, modulos avaliados, estrategia de carga, ERP selecionado e totais encontrados por verificador.
11. Transformar equipe/acessos em trilha progressiva pos-go-live, com lembrete, sem bloquear a liberacao operacional minima.
12. Alinhar todos os CTAs do checklist com rotas reais do frontend e adicionar testes estaticos para evitar targets quebrados.

## Regras de Bloqueio Recomendadas

| Checklist | Bloqueia go-live | Condicao |
| --- | --- | --- |
| Estrategia de carga | Sim | Sempre, porque o wizard precisa saber se deve guiar cadastro manual ou integracao ERP |
| ERP identificado | Sim | Quando o usuario optar por ERP |
| `CHECK_UNIDADE_PRODUTIVA` | Sim | Sempre |
| `CHECK_ESTRUTURA_TERRITORIAL` | Sim | Sempre, pois o tenant precisa de recorte fisico minimo |
| `CHECK_AGRICULTURA_TALHAO` | Sim | Somente com agricultura habilitada |
| `CHECK_PECUARIA_PIQUETE` | Sim | Somente com pecuaria habilitada |
| `CHECK_CULTURA` | Sim | Somente com agricultura habilitada, antes da safra |
| `CHECK_PRODUTO_CATALOGO` | Sim | Com agricultura ou estoque habilitado |
| `CHECK_ESTOQUE_DEPOSITO` | Sim | Somente com estoque habilitado |
| `CHECK_FINANCEIRO_PLANO_CONTA` | Sim | Somente com financeiro habilitado |
| `CHECK_EQUIPAMENTO_CADASTRO` | Sim | Somente com frota/maquinas habilitado |
| `CHECK_INTEGRACAO_ERP` | Nao por padrao | Bloquear apenas se integracao for contratual e marcada como obrigatoria |
| Equipe/convites | Nao | Deve ser recomendacao progressiva |

## Backlog Tecnico Sugerido

1. Alinhar `CHECK_CULTURA` entre checklist, engine, targets e frontend.
2. Criar etapa persistida para capturar a decisao `manual x ERP` logo apos o tenant.
3. Validar se `/configuracoes/integracoes` existe no frontend; caso contrario, ajustar o CTA para a rota real.
4. Criar testes unitarios para garantir que todos os `action_targets` apontem para rotas existentes ou aliases registrados.
5. Padronizar verificadores para retornarem contagem, exemplos de registros encontrados e escopo usado na consulta.
6. Criar um contrato JSON do workflow para o frontend renderizar a jornada sem hardcode.
7. Adicionar logs estruturados em `/wizard/checklist/reavaliar` para diagnosticar falsos negativos de unidade produtiva ativa.
8. Incluir no contrato do workflow a origem do dado: `manual`, `erp`, `seed` ou `hibrido`.
