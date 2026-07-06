# Guia do Usuário - Implantação da Safra de Café

Documento: PILOT-06  
Público: administrador do cliente e usuários responsáveis pela implantação  
Escopo: primeiro acesso ao AgroSaaS até a visualização dos primeiros resultados da safra de café  
Status: guia operacional baseado nas telas e fluxos existentes

## 0. Antes de começar

Este guia mostra o caminho prático para colocar uma fazenda de café em operação no AgroSaaS.

Ele não substitui o Plano Mestre, o Runbook ou o Checklist do Cliente. Ele traduz esses documentos para uma sequência simples de uso dentro do sistema.

O piloto aprovado considera:

- O cliente é um produtor de café com perfil exportador.
- O ERP Sankhya é a origem principal de cadastros administrativos e financeiros definidos para o piloto.
- O AgroSaaS é a origem principal dos dados da fazenda, talhões, operação agrícola, Campo PWA, alertas, recomendações e resultados agronômicos.
- A integração Sankhya do piloto é Sankhya para AgroSaaS.
- O piloto não faz escrita bidirecional no Sankhya.
- Documentos avançados, faturamento, cancelamentos e contratos completos ficam fora do escopo inicial do piloto.

## Auditoria das telas e fluxos existentes

| Área auditada | Menu ou rota principal | Situação | O que existe hoje | Limitação para o usuário |
| --- | --- | --- | --- | --- |
| Primeiro acesso e login | `/login`, `/register`, `/convite/aceitar`, `/selecionar-tenant` | EXISTE E ATENDE | Login, cadastro, aceite de convite e seleção de ambiente. | O acesso depende de usuário, ambiente da empresa e permissões já provisionados. |
| Ativação e onboarding inicial | `/onboarding/ativar`, `/onboarding/configurar`, `/onboarding/sucesso` | EXISTE E ATENDE | Configuração inicial com ano agrícola, unidade de área, fuso, moeda e categorias padrão. | Se o ambiente ativo não for detectado, o usuário precisa fazer login novamente. |
| Wizard de implantação | `/dashboard/implantacao/wizard` | EXISTE E ATENDE | Estados, progresso, checklist, pendências, motivos de bloqueio e ações de go-live. | O Wizard não substitui os cadastros. Ele valida evidências e prontidão. |
| Unidade Produtiva | Serviço de unidades produtivas e telas de fazendas/propriedades | EXISTE PARCIALMENTE | Entidade e validação obrigatória no Wizard. | A criação pode ser conduzida em telas de fazenda/propriedade ou operação assistida, conforme configuração do ambiente. |
| Propriedades | Minha Propriedade > Propriedades, `/cadastros/propriedades` | EXISTE E ATENDE | Cadastro e gestão das propriedades rurais. | Dados fundiários detalhados podem depender da tela de Imóveis Rurais. |
| Imóveis rurais | Imóveis Rurais > Imóveis Rurais, `/cadastros/imoveis` | EXISTE E ATENDE | Cadastro legal com NIRF, CAR, CCIR, documentação e filtros. | Vínculo com propriedade deve ser conferido durante a implantação assistida se houver dúvida. |
| Estrutura de áreas | Propriedade > Estrutura, componentes de hierarquia | EXISTE E ATENDE | Área Rural, Gleba, Talhão, Área Operacional, APP, Reserva Legal, Infraestrutura, Sede, Armazém, Curral e Outros. | O resultado do Wizard exige pelo menos área rural e talhão para agricultura. |
| Talhões e georreferenciamento | Minha Propriedade > Georreferenciamento, `/cadastros/propriedades/talhoes` | EXISTE E ATENDE | Visualização e edição de geometria dos talhões no mapa. | O desenho correto depende de coordenadas ou ajuste manual pelo usuário/equipe. |
| Pessoas e parceiros | Pessoas & Parceiros > Pessoas & Parceiros, `/cadastros/pessoas` | EXISTE E ATENDE | Clientes, fornecedores, colaboradores e outros vínculos. | Dados sensíveis usam controle de acesso e podem exigir permissão específica. |
| Produtos e insumos | Insumos & Ativos > Catálogo de Produtos, `/cadastros/produtos` | EXISTE E ATENDE | Produto, tipo, categoria, princípio ativo, fabricante, unidade, estoque mínimo e preço médio. | Duplicidades importadas ou cadastradas manualmente exigem conferência operacional. |
| Commodities | Minha Propriedade > Commodities, `/cadastros/commodities` | EXISTE E ATENDE | Cadastro de produtos agropecuários. | Deve ser conferido para café quando usado em comercialização e relatórios. |
| Safras | Agricultura > Safras, `/agricola/safras` | EXISTE E ATENDE | Listagem, KPIs, filtro por fase, criação e acesso ao painel da safra. | A safra só fica útil se houver talhões e cultivo configurados. |
| Safra de café | `/agricola/safras/[id]` | EXISTE E ATENDE | Cultivo, talhões, área, cultivar, meta de produtividade, período, fase, checklist, tarefas, fenologia e cenário base quando houver. | A cultura Café precisa existir no cadastro de culturas para seleção no formulário. |
| Operações agrícolas | Agricultura > Operações Consolidadas, Caderno de Campo, Romaneios, Beneficiamento | EXISTE PARCIALMENTE | Telas para acompanhar registros, caderno, colheita e pós-colheita. | Alguns lançamentos podem entrar pelo Campo PWA ou operação assistida, conforme rotina do piloto. |
| Campo PWA | Web: `/dashboard/operacional/campo/*`; Campo: `/activate`, `/pin`, `/home`, `/sync`, `/caderno`, `/campo/aplicacao`, `/campo/colheita` | EXISTE E ATENDE | Dispositivos, tarefas, ativação por código, PIN, sincronização, operação offline, aplicação, colheita e caderno. | O dispositivo só opera depois de ativado e sincronizado. |
| Estoque | Estoque & Suprimento > Saldos, Almoxarifado, Lotes, Requisições, Implantação Assistida | EXISTE E ATENDE | Saldos, lotes, requisições, estoque mínimo, almoxarifado e implantação assistida. | Saldo inicial precisa ser conferido antes de depender de baixa automática. |
| Financeiro | Financeiro > Painel, Receitas, Despesas, Planos de Conta, Lançamentos, DRE | EXISTE E ATENDE | Receitas, despesas, plano de contas, lançamentos, fluxo de caixa e DRE operacional. | Resultados dependem de dados importados do Sankhya ou lançados corretamente. |
| Custos agrícolas | Agricultura > Custeio Agrícola, `/agricola/custos` | EXISTE E ATENDE | Custo realizado, orçamento planejado e visão por safra. | O custo por talhão/operação depende de apropriação correta dos lançamentos. |
| Rentabilidade agrícola | Agricultura > Rentabilidade Agrícola, `/dashboard/agricola/rentabilidade` | EXISTE E ATENDE | Rentabilidade derivada da DRE agrícola, filtros por safra, fazenda e unidade operacional. | Requer plano compatível e dados de custo, receita, produção e área. |
| DRE agrícola | Agricultura > DRE Agrícola v1, `/dashboard/agricola/dre` | EXISTE E ATENDE | Visão econômica oficial para resultado agrícola. | Se faltar receita, custo ou produção, a DRE fica parcial. |
| Alertas e recomendações | Inteligência Operacional, Recomendações, Central de Inteligência | EXISTE E ATENDE | Recomendações, alertas executivos e orientações persistidas no Campo PWA. | A qualidade depende de dados sincronizados e regras disponíveis para o ambiente. |
| Integração Sankhya | Configurações > Integrações > ERP Sankhya, `/dashboard/settings/integracoes/erp` | EXISTE E ATENDE | Configuração, teste de conexão, saúde da integração, diagnóstico, execuções, histórico técnico, linha do tempo e sincronização manual. | O console atual usa URL do Web Service, usuário e senha. A estratégia de acesso pelo Gateway e campos técnicos completos seguem os relatórios Sankhya do piloto. |

## 1. Visão geral da jornada

A implantação completa segue esta ordem:

1. Primeiro acesso ao AgroSaaS.
2. Ativação da conta e seleção do ambiente.
3. Configuração inicial do ambiente da empresa.
4. Início do Wizard de Implantação.
5. Criação ou validação da Unidade Produtiva.
6. Cadastro da propriedade e dos imóveis rurais.
7. Estruturação da fazenda em glebas, talhões, áreas operacionais e infraestrutura.
8. Configuração da integração Sankhya e teste de conexão.
9. Conferência dos cadastros mestres.
10. Criação da safra de café.
11. Associação de talhões, cultivar, área e meta de produtividade.
12. Preparação do Campo PWA.
13. Registro da operação diária.
14. Conferência de estoque, custos e financeiro.
15. Acompanhamento de alertas e recomendações.
16. Visualização de DRE e rentabilidade da safra.

Resultado esperado: ao final da implantação, o usuário consegue acessar a safra de café, acompanhar atividades, sincronizar registros de campo, conferir custos e visualizar indicadores econômicos quando houver dados suficientes.

## 2. Primeiro acesso

### Onde acessar

- Tela de login: `/login`.
- Tela de cadastro: `/register`.
- Aceite de convite: `/convite/aceitar`.
- Seleção de ambiente: `/selecionar-tenant`.

### Quem deve acessar primeiro

O primeiro acesso deve ser feito pelo Owner/Admin do cliente.

Esse usuário normalmente é responsável por:

- aceitar o convite;
- selecionar o ambiente correto;
- concluir a configuração inicial;
- iniciar o Wizard;
- acompanhar pendências;
- aprovar a liberação para go-live.

### Passo a passo

1. Acesse o endereço do AgroSaaS informado pela equipe.
2. Entre na tela de login.
3. Informe e-mail e senha.
4. Se houver mais de um ambiente, selecione o ambiente correto.
5. Confirme se o nome da empresa aparece no ambiente selecionado.
6. Se o sistema direcionar para onboarding, conclua a configuração inicial antes de tentar usar o dashboard.

### Campos e validações esperadas

| Campo | O que preencher | Validação esperada |
| --- | --- | --- |
| E-mail | E-mail cadastrado ou convidado | Deve existir no ambiente ou convite. |
| Senha | Senha definida pelo usuário | Deve ser válida. |
| Tenant | Ambiente da empresa | Deve estar ativo e vinculado ao usuário. |

### Mensagens comuns

| Mensagem ou situação | O que significa | Como resolver |
| --- | --- | --- |
| Usuário ou senha inválidos | Credencial incorreta ou usuário sem acesso | Conferir e-mail, redefinir senha ou acionar suporte. |
| Seleção de ambiente | Usuário pertence a mais de um ambiente | Escolher o ambiente da empresa piloto. |
| Onboarding pendente | Configuração inicial ainda não foi concluída | Ir para o onboarding e concluir as etapas. |
| Não foi possível detectar o ambiente ativo | O navegador não está com ambiente válido | Fazer login novamente. |

## 3. Onboarding inicial

### Onde acessar

- `/onboarding/configurar`.

### O que o usuário verá

A tela apresenta a Configuração Inicial em 5 etapas:

| Etapa | Campo ou decisão | O que fazer |
| --- | --- | --- |
| Ano Agrícola | Início e fim | Para café, usar o calendário definido pelo cliente. O padrão do sistema é julho a junho. |
| Unidade de Área | Hectare ou alqueires | Usar hectare se não houver orientação diferente. |
| Fuso e Moeda | Fuso horário e Real Brasileiro | Para a maioria das fazendas, usar São Paulo/Brasília e BRL. |
| Categorias | Carregar categorias padrão | Manter marcado para iniciar com categorias comuns. |
| Revisão | Conferência final | Confirmar se tudo está correto antes de concluir. |

### Botões disponíveis

- `Anterior`.
- `Próximo`.
- `Concluir Configuração`.

### Resultado esperado

Ao clicar em `Concluir Configuração`, o sistema salva a configuração e direciona o usuário para o dashboard.

### Se o dashboard estiver bloqueado

O dashboard pode ficar restrito quando:

- o ambiente da empresa não foi identificado;
- a configuração inicial não foi concluída;
- o Wizard ainda tem pendências críticas;
- a Unidade Produtiva não existe;
- os dados mínimos de implantação não foram informados.

Nesse caso, o usuário deve acessar o Wizard e corrigir as pendências indicadas.

## 4. Wizard de implantação

### Onde acessar

Menu: Dashboard > Implantação > Wizard  
Rota: `/dashboard/implantacao/wizard`

### Para que serve

O Wizard é o painel de controle da implantação. Ele mostra:

- status da implantação;
- etapa atual;
- progresso geral;
- checklist mínimo;
- pendências críticas;
- motivos de bloqueio;
- elegibilidade para go-live;
- ações permitidas no momento.

### Estados do Wizard

| Estado | Significado para o usuário | Ação esperada |
| --- | --- | --- |
| Não iniciado | A implantação ainda não foi aberta | Clicar em `Iniciar implantação`. |
| Em progresso | A implantação está em andamento | Corrigir pendências e avançar na preparação. |
| Pausado | A implantação foi parada temporariamente | Clicar em `Retomar` quando puder continuar. |
| Bloqueado | Existe impedimento estrutural | Resolver pendências críticas antes de continuar. |
| Pronto para go-live | Requisitos mínimos atendidos | Validar com equipe e iniciar go-live. |
| Go-live | Operação assistida iniciada | Acompanhar primeira operação real. |
| Estabilização | Pós-go-live em acompanhamento | Monitorar rotina e resolver ajustes. |
| Concluído | Implantação encerrada com sucesso | Seguir operação normal. |
| Cancelado | Implantação encerrada sem continuidade | Acionar a equipe AgroSaaS. |

### Etapas oficiais do Wizard

| Ordem | Etapa | Objetivo | Situação no piloto |
| --- | --- | --- | --- |
| 1 | Diagnóstico | Abrir e registrar contexto inicial | EXISTE E ATENDE |
| 2 | Unidade Produtiva | Garantir fazenda/unidade ativa | EXISTE E ATENDE |
| 3 | Território | Garantir estrutura de área rural | EXISTE E ATENDE |
| 4 | Atividades | Garantir cadastros básicos | EXISTE E ATENDE |
| 5 | Agricultura | Garantir talhão quando agricultura está habilitada | EXISTE E ATENDE |
| 6 | Pecuária | Exigida apenas se pecuária estiver habilitada | EXISTE E ATENDE, mas normalmente dispensada no piloto café |
| 7 | Estoque | Garantir depósito quando estoque está habilitado | EXISTE E ATENDE |
| 8 | Financeiro | Garantir plano de contas quando financeiro está habilitado | EXISTE E ATENDE |
| 9 | Máquinas | Garantir equipamento se frota/máquinas estiver habilitado | EXISTE E ATENDE |
| 10 | Equipe | Cadastro de equipe quando aplicável | EXISTE PARCIALMENTE |
| 11 | Revisão | Conferência final | EXISTE E ATENDE |
| 12 | Go-live | Entrada em operação assistida | EXISTE E ATENDE |
| 13 | Estabilização | Primeira semana de operação | EXISTE E ATENDE |

### Checklist mínimo validado pelo sistema

| Item | O que o sistema verifica | Bloqueia? |
| --- | --- | --- |
| Unidade Produtiva | Existe pelo menos uma Unidade Produtiva ativa | Sim, crítico |
| Estrutura territorial | Existe pelo menos uma Área Rural ativa | Pode bloquear a prontidão |
| Talhão agrícola | Se Agricultura estiver habilitada, existe pelo menos um talhão | Sim, crítico |
| Depósito | Se Estoque estiver habilitado, existe pelo menos um depósito ativo | Pode bloquear a prontidão |
| Plano de contas | Se Financeiro estiver habilitado, existe plano de contas ativo | Pode bloquear a prontidão |
| Catálogo de produtos | Se Agricultura ou Estoque estiverem habilitados, existe produto ativo | Pode bloquear a prontidão |
| Equipamento | Se Frota/Máquinas estiver habilitado, existe equipamento ativo | Pode bloquear conforme escopo |

### Botões e ações do Wizard

| Botão | Quando aparece | O que faz |
| --- | --- | --- |
| Iniciar implantação | Wizard ainda não iniciado | Cria a implantação do ambiente da empresa. |
| Reavaliar checklist | Wizard ativo | Reprocessa as validações automáticas. |
| Pausar | Em progresso | Pausa a implantação. |
| Bloquear | Em progresso | Registra bloqueio operacional. |
| Marcar pronto para go-live | Em progresso e apto | Marca prontidão para go-live. |
| Retomar | Pausado ou bloqueado | Retoma a implantação. |
| Desbloquear | Bloqueado | Remove status de bloqueio se as condições permitirem. |
| Iniciar go-live | Pronto para go-live | Inicia operação assistida. |
| Iniciar estabilização | Go-live | Entra no acompanhamento pós-go-live. |
| Concluir | Estabilização | Finaliza a implantação. |
| Cancelar | Em estados permitidos | Encerra a implantação sem continuar. |

### Como corrigir uma pendência

1. Leia o item pendente no Wizard.
2. Identifique o cadastro relacionado.
3. Acesse o menu correspondente.
4. Cadastre ou corrija o dado.
5. Volte ao Wizard.
6. Clique em `Reavaliar checklist`.
7. Confirme se o item mudou para `Atendido` ou `Dispensado`.

## 5. Unidade Produtiva

### O que é

Unidade Produtiva é a fazenda ou unidade operacional usada pelo AgroSaaS para organizar dados, usuários, áreas, estoque, operações e relatórios.

Ela é obrigatória porque o sistema precisa saber a qual fazenda pertencem:

- talhões;
- depósitos;
- produtos em estoque;
- tarefas de campo;
- registros de aplicação;
- colheitas;
- custos;
- resultados.

### Como validar

1. Acesse o Wizard.
2. Verifique o item `CHECK_UNIDADE_PRODUTIVA`.
3. Se estiver pendente, confirme com a equipe se a fazenda já foi criada.
4. Acesse as telas de fazendas/propriedades disponíveis no ambiente.
5. Cadastre ou valide a fazenda.
6. Volte ao Wizard e clique em `Reavaliar checklist`.

### Resultado esperado

O Wizard deve mostrar `Unidade Produtiva ativa encontrada`.

### Exemplo

| Campo | Exemplo |
| --- | --- |
| Nome | Fazenda Santa Rita |
| Município | Carmo de Minas |
| UF | MG |
| Uso no piloto | Unidade principal da safra Café 2026 |

## 6. Estrutura da fazenda

### Sequência recomendada

1. Cadastrar a propriedade.
2. Cadastrar o imóvel rural.
3. Conferir vínculo entre propriedade e imóvel rural.
4. Criar a área rural principal.
5. Criar glebas.
6. Criar talhões.
7. Criar áreas operacionais, se usadas.
8. Criar infraestrutura relevante.
9. Criar ou conferir depósitos.

### Propriedades

Menu: Minha Propriedade > Propriedades  
Rota: `/cadastros/propriedades`

Use esta tela para cadastrar a fazenda operacional.

Campos esperados variam conforme o cadastro, mas a conferência deve cobrir:

- nome da propriedade;
- município;
- UF;
- área;
- status ativo;
- vínculo com ambiente/unidade produtiva.

Exemplo: `Fazenda Santa Rita`.

### Imóveis rurais

Menu: Imóveis Rurais > Imóveis Rurais  
Rota: `/cadastros/imoveis`

Use esta tela para a parte legal/fundiária.

Campos e informações auditadas:

- nome do imóvel;
- município;
- situação;
- NIRF;
- CAR;
- CCIR;
- documentação legal;
- vínculo com fazenda/unidade produtiva.

Botões encontrados:

- criar novo imóvel;
- editar;
- excluir;
- visualizar;
- filtrar por nome, município ou situação.

Mensagem comum: `Preencha os campos obrigatórios`.

### Estrutura hierárquica de áreas

A estrutura existente suporta:

| Tipo | Uso prático no café |
| --- | --- |
| Área Rural | Agrupa as áreas da propriedade. |
| Gleba | Divisão territorial maior, muitas vezes associada a matrícula ou setor. |
| Talhão | Unidade principal de plantio e acompanhamento. |
| Área Operacional | Subdivisão operacional para manejo. |
| Subtalhão | Subdivisão administrativa de talhão, se usada. |
| Zona de Manejo | Recorte para manejo diferenciado. |
| APP | Área de Preservação Permanente. |
| Reserva Legal | Área ambiental obrigatória. |
| Infraestrutura | Agrupa benfeitorias físicas. |
| Sede | Administração, casa ou escritório. |
| Armazém | Galpão, armazém ou depósito físico. |
| Outros | Estruturas não classificadas. |

### Talhões

Menu: Minha Propriedade > Georreferenciamento  
Rota: `/cadastros/propriedades/talhoes`

Use esta tela para visualizar e editar a geometria dos talhões.

Para o piloto café, cadastre pelo menos um talhão. Sem talhão, o Wizard bloqueia Agricultura.

Exemplo:

| Talhão | Cultivar | Área |
| --- | --- | --- |
| Talhão 01 | Mundo Novo | 12,50 ha |
| Talhão 02 | Catuaí | 8,20 ha |
| Talhão 03 | Bourbon Amarelo | 5,80 ha |

### Depósitos

Os depósitos aparecem no contexto de Estoque e Almoxarifado.

Exemplos para café:

- Depósito Central de Insumos;
- Galpão de Fertilizantes;
- Armazém de Café Beneficiado;
- Depósito de Defensivos.

Se Estoque estiver habilitado, o Wizard exige ao menos um depósito ativo.

## 7. Integração Sankhya

### Onde acessar

Menu: Configurações > Integrações > ERP Sankhya  
Rota: `/dashboard/settings/integracoes/erp`

### O que a tela mostra

A tela `ERP Sankhya` mostra:

- configuração operacional;
- conexão e credenciais;
- status e ciclo de vida da integração;
- saúde detalhada da integração;
- diagnóstico operacional;
- funcionalidades e políticas habilitadas;
- sincronização manual;
- execuções;
- histórico técnico;
- linha do tempo operacional.

### Campos exibidos no console atual

| Campo | O que significa |
| --- | --- |
| URL do Web Service | Endereço do serviço Sankhya configurado para o ambiente. |
| Usuário | Usuário autorizado para integração. |
| Senha ou nova senha | Credencial protegida. Nunca é exibida em texto puro. |
| Intervalo de sincronização | Tempo entre sincronizações quando aplicável. |

### Botões disponíveis

| Botão | Uso |
| --- | --- |
| Salvar configuração | Salva URL, usuário, senha e intervalo. |
| Testar conexão | Valida se o AgroSaaS consegue autenticar/conectar. |
| Atualizar status | Recarrega status, saúde da integração e diagnóstico. |
| Sincronizar pessoas | Inicia sincronização manual de pessoas. |
| Sincronizar produtos | Inicia sincronização manual de produtos. |
| Sincronização completa | Inicia sincronização manual completa permitida pela implementação atual. |

### Como testar a conexão

1. Acesse `Configurações > Integrações > ERP Sankhya`.
2. Confira a URL do Web Service.
3. Confira o usuário.
4. Informe a senha somente se for a primeira configuração ou se precisar trocar.
5. Clique em `Salvar configuração`.
6. Clique em `Testar conexão`.
7. Aguarde o retorno.
8. Clique em `Atualizar status`.
9. Verifique `Health atual`, `Último sucesso`, `Última falha` e `Falhas consecutivas`. Na tela, `Health atual` significa a saúde atual da integração.

### Como interpretar o resultado

| Resultado | Interpretação | Ação |
| --- | --- | --- |
| Sucesso | Conexão validada | Prosseguir para carga/conferência. |
| Erro ao salvar | Configuração incompleta ou inválida | Conferir campos e permissões. |
| Erro ao testar conexão | URL, credencial, rede ou permissão incorreta | Acionar responsável pelo ERP/Sankhya. |
| DISCONNECTED | Integração sem conexão | Verificar Gateway, URL e credenciais. |
| AUTH_ERROR | Falha de autenticação | Conferir usuário, senha, Client ID, Client Secret ou X-Token conforme ambiente. |
| CONFIG_ERROR | Configuração inconsistente | Revisar parâmetros de integração. |
| DEGRADED | Funciona parcialmente | Acompanhar histórico técnico e execuções com falha. |

### Termos da integração em linguagem simples

| Termo | Explicação |
| --- | --- |
| Ambiente | Indica se a integração aponta para homologação, produção ou outro ambiente autorizado. |
| Base URL | Endereço principal usado para comunicação com o Sankhya. |
| Auth URL | Endereço usado para autenticação. |
| Client ID | Identificador da aplicação autorizada no Sankhya. |
| Client Secret | Senha técnica da aplicação. Deve ser mantida em sigilo. |
| X-Token | Token técnico exigido por alguns ambientes. Deve ser mantido em sigilo. |
| Gateway | Caminho oficial usado para autenticar e acessar a integração no piloto. |

### O que será sincronizado no piloto

O escopo aprovado é leitura e carga inicial Sankhya para AgroSaaS, principalmente:

- pessoas;
- clientes;
- fornecedores;
- produtos;
- insumos;
- plano de contas;
- financeiro;
- notas fiscais quando priorizadas no piloto;
- dados necessários para conferência operacional.

### O que não será sincronizado no piloto

Não faz parte do escopo inicial:

- escrita de documentos no Sankhya;
- faturamento automático;
- cancelamento de documentos;
- contratos documentais completos;
- pipeline bidirecional;
- escrita AgroSaaS para Sankhya.

## 8. Cadastros mestres

### Clientes, fornecedores e parceiros

Menu: Pessoas & Parceiros > Pessoas & Parceiros  
Rota: `/cadastros/pessoas`

O usuário deve conferir:

- cliente exportador;
- compradores;
- fornecedores de insumos;
- transportadoras, se usadas;
- representantes, se usados;
- colaboradores, se usados na operação.

Campos auditados em detalhes de pessoa:

- nome de exibição;
- base legal LGPD;
- CNPJ;
- razão social;
- nome fantasia;
- inscrição estadual;
- CPF;
- nome completo;
- RG;
- data de nascimento;
- dados pessoais com controle de acesso.

Botões encontrados:

- nova pessoa;
- visualizar;
- editar;
- salvar;
- cancelar;
- voltar;
- acessar dados pessoais quando autorizado.

### Produtos e insumos

Menu: Insumos & Ativos > Catálogo de Produtos  
Rota: `/cadastros/produtos`

Campos principais:

- nome;
- tipo;
- categoria;
- princípio ativo;
- referência do fabricante;
- descrição;
- marca cadastrada;
- modelo;
- marca em texto livre;
- fabricante;
- unidade de estoque;
- conteúdo por embalagem;
- unidade do conteúdo;
- código interno;
- estoque mínimo;
- preço médio.

Botões encontrados:

- novo produto;
- salvar;
- cancelar;
- editar.

Mensagens encontradas:

- `Produto cadastrado com sucesso`;
- `Produto atualizado com sucesso`;
- `Erro ao cadastrar produto`;
- `Erro ao atualizar produto`.

### O que fazer em caso de duplicidade

1. Não crie outro cadastro manual.
2. Pesquise pelo nome, CNPJ, código interno ou fabricante.
3. Confira se a duplicidade veio do Sankhya ou de cadastro manual.
4. Defina com a equipe qual registro ficará ativo.
5. Evite usar registros duplicados em safra, estoque ou financeiro até a limpeza.

## 9. Safra de café

### Onde acessar

Menu: Agricultura > Safras  
Rota: `/agricola/safras`

### Criar nova safra

1. Acesse `Agricultura > Safras`.
2. Clique em `Nova Safra`.
3. Informe o `Ano Agrícola`.
4. Adicione pelo menos um `Cultivo`.
5. Selecione a cultura `Café`.
6. Informe o cultivar, se aplicável.
7. Adicione os talhões.
8. Informe a área plantada em hectares.
9. Informe meta de produtividade em sacas por hectare, se houver.
10. Informe início da ocupação.
11. Informe fim da ocupação, se já souber.
12. Clique em `Criar Safra`.

### Campos da safra

| Campo | Obrigatório | Exemplo |
| --- | --- | --- |
| Ano Agrícola | Sim | 2026 ou 2025/26 |
| Cultura | Sim | Café |
| Cultivar | Não | Mundo Novo, Catuaí, Bourbon Amarelo |
| Talhão | Sim | Talhão 01 |
| Área a plantar | Sim | 12,50 ha |
| Meta de produtividade | Não | 35 sc/ha |
| Consorciado | Não | Marcar somente se houver cultivo compartilhado |
| Início da ocupação | Sim | 2026-01-01 |
| Fim da ocupação | Não | Informar se houver previsão |

### Validações encontradas

| Validação | Mensagem esperada |
| --- | --- |
| Ano agrícola inválido | Use o formato AAAA ou AAAA/AA. |
| Cultura vazia | Informe a cultura. |
| Sem talhão | Adicione ao menos um talhão. |
| Área zerada | Deve ser maior que 0. |
| Área maior que o talhão | Máximo igual à área do talhão. |
| Data de início vazia | Data de início é obrigatória. |

### Depois de criar

Acesse a safra criada. A tela mostra:

- título da safra;
- cultura;
- cultivar;
- fase atual;
- cultivos;
- área total;
- atualização;
- cenário base, quando houver;
- timeline;
- checklist da fase;
- tarefas;
- fenologia;
- histórico de fases;
- observações.

## 10. Operação agrícola

### Planejamento

Use:

- Agricultura > Safras;
- Agricultura > Orçamento de Safra;
- Agricultura > Custeio Agrícola;
- Agricultura > Tarefas dentro da safra.

O objetivo é definir o que será feito na safra:

- tratos culturais;
- aplicações;
- monitoramento;
- colheita;
- insumos previstos;
- custos previstos;
- metas.

### Aplicações e tratos culturais

Podem ser acompanhados por:

- Web: Agricultura > Caderno de Campo e Operações Consolidadas;
- Campo PWA: `/campo/aplicacao`.

No Campo PWA, a tela de aplicação solicita:

- talhão;
- produto;
- quantidade;
- observação opcional;
- localização/GPS quando disponível.

Resultado esperado: o registro fica salvo localmente e pronto para sincronizar quando houver conexão.

### Colheita

Pode ser registrada pelo Campo PWA:

- Rota: `/campo/colheita`.

Campos auditados:

- talhão;
- quantidade;
- observação opcional.

Resultado esperado: a colheita fica salva localmente e sincroniza quando o dispositivo tiver internet.

### Romaneios

Menu: Agricultura > Romaneios de Colheita  
Rota: `/agricola/romaneios`

Use para acompanhar registros de colheita e movimentações relacionadas à produção.

### Beneficiamento

Menu: Agricultura > Beneficiamento  
Rota: `/agricola/beneficiamento`

Use quando o processo de pós-colheita estiver no escopo operacional do piloto.

### Custos gerados

Os custos aparecem quando:

- há despesas importadas ou lançadas;
- há consumo de estoque apropriado;
- há custos vinculados à safra;
- há rateio correto por unidade, talhão ou operação.

## 11. Campo PWA

### Preparar o dispositivo no Web

Menu: Operacional > Campo > Dispositivos  
Rota: `/dashboard/operacional/campo/dispositivos`

Passo a passo:

1. Clique em `Novo dispositivo`.
2. Informe `Nome do Dispositivo`.
3. Selecione `Operador Responsável`.
4. Informe validade em dias.
5. Marque as fazendas que o dispositivo pode acessar.
6. Clique em `Gerar Código de Ativação`.
7. Copie o código.
8. Repasse ao operador.

Campos e validações:

| Campo | Validação |
| --- | --- |
| Nome do Dispositivo | Nome obrigatório, mínimo de 2 caracteres. |
| Operador Responsável | Obrigatório. |
| Fazendas do dispositivo | Selecionar ao menos uma fazenda. |
| Validade | Entre 1 e 365 dias. |

### Ativar no Campo PWA

Rota: `/activate`

O operador deve:

1. Abrir o Campo PWA no dispositivo.
2. Digitar o código de ativação.
3. Criar um PIN de 6 dígitos.
4. Confirmar o PIN.
5. Clicar em `Ativar dispositivo`.

Validações encontradas:

- código de ativação deve ter ao menos 6 caracteres;
- código de ativação deve ter no máximo 8 caracteres;
- PIN deve ter 6 dígitos;
- PIN deve conter apenas números;
- PINs precisam conferir.

### Uso diário do Campo PWA

Rota principal: `/home`

A tela inicial mostra:

- botão para sincronização;
- recomendações operacionais;
- tarefas por domínio;
- registros offline recentes;
- nova atividade.

Rotas principais:

| Tela | Rota | Uso |
| --- | --- | --- |
| Sincronização | `/sync` | Ver fila local, reenviar falhas e resolver conflitos. |
| Caderno | `/caderno` | Registro manual de ocorrências e evidências. |
| Aplicação | `/campo/aplicacao` | Registrar aplicação agrícola. |
| Colheita | `/campo/colheita` | Registrar colheita. |
| Tarefa | `/campo/tarefa/[id]` | Executar tarefa programada. |
| Recomendações | `/recomendacoes` | Consultar orientações sincronizadas. |

### Fluxo offline esperado

1. Operador acessa Campo.
2. Sincroniza antes de sair para o talhão.
3. Seleciona a fazenda ativa.
4. Vai para o talhão.
5. Registra aplicação, colheita ou ocorrência.
6. O dispositivo fica sem internet.
7. O registro permanece salvo localmente.
8. O operador volta para área com sinal.
9. Acessa `/sync`.
10. Reenvia itens pendentes ou aguarda sincronização.
11. Os dados aparecem no Web após processamento.

### Recuperação de falhas

Na tela `/sync`, o operador consegue ver:

- itens com erro;
- itens em conflito;
- fila local;
- botão de reenviar quando disponível.

Se houver conflito, não apague o registro. Acione o responsável pelo piloto.

## 12. Estoque

### Onde acessar

Menu: Estoque & Suprimento

Rotas principais:

- `/suprimentos/saldos`;
- `/suprimentos/estoque`;
- `/suprimentos/lotes`;
- `/suprimentos/requisicoes`;
- `/suprimentos/estoque/implantacao-assistida`.

### Conferir saldo inicial

1. Acesse `Estoque & Suprimento > Saldos de Estoque`.
2. Confira produto, depósito e saldo.
3. Ajuste estoque mínimo quando aplicável.
4. Verifique alertas de saldo baixo.
5. Se necessário, use implantação assistida de estoque.

### Depósitos

Confirme se os depósitos usados na operação existem e estão ativos.

Exemplo:

- Depósito Central de Insumos;
- Defensivos;
- Fertilizantes;
- Armazém de Café.

### Requisições

Menu: Estoque & Suprimento > Requisições

Campos auditados:

- fazenda;
- origem;
- OS ou tarefa vinculada;
- data de necessidade;
- observações;
- produto;
- quantidade;
- quantidade aprovada;
- depósito de saída.

Botões encontrados:

- nova requisição;
- adicionar item;
- cancelar;
- criar;
- aprovar;
- recusar;
- concluir.

### Divergências de estoque

| Situação | Causa provável | Ação |
| --- | --- | --- |
| Produto sem saldo | Saldo inicial não foi lançado ou importado | Conferir Sankhya e implantação assistida. |
| Depósito não aparece | Depósito não cadastrado ou inativo | Cadastrar/ativar depósito e reavaliar Wizard. |
| Baixa não aparece | Registro ainda não sincronizou ou não gerou movimento | Conferir Campo PWA, fila de sincronização e histórico técnico. |
| Saldo negativo | Consumo lançado sem entrada suficiente | Corrigir estoque inicial ou movimentação. |

## 13. Financeiro e custos

### Onde acessar

Menu: Financeiro

Rotas principais:

- `/dashboard/financeiro`;
- `/dashboard/financeiro/receitas`;
- `/dashboard/financeiro/despesas`;
- `/dashboard/financeiro/planos-conta`;
- `/dashboard/financeiro/lancamentos`;
- `/dashboard/financeiro/dre`;
- `/dashboard/financeiro/relatorios`;
- `/dashboard/financeiro/nf-e`.

### O que conferir

| Área | Conferência |
| --- | --- |
| Plano de contas | Deve existir se Financeiro estiver habilitado. |
| Receitas | Vendas ou recebimentos relacionados à safra. |
| Despesas | Compras, serviços, mão de obra e custos operacionais. |
| Lançamentos | Classificação por safra, centro de custo e categoria. |
| DRE | Resultado consolidado. |
| NF-e/NFP-e | Notas fiscais quando estiverem no escopo do piloto. |

### Notas fiscais

A tela de NF-e/NFP-e possui cadastro manual com campos:

- tipo;
- número;
- série;
- emitente;
- CPF/CNPJ emitente;
- destinatário;
- documento do destinatário;
- UF;
- produto/descrição;
- NCM;
- quantidade;
- unidade;
- valor dos produtos;
- valor ICMS;
- valor total.

No piloto, a escrita avançada de documentos no Sankhya não faz parte do escopo inicial.

### Custos agrícolas

Menu: Agricultura > Custeio Agrícola  
Rota: `/agricola/custos`

A tela mostra:

- safra selecionada;
- custo total realizado;
- orçamento planejado;
- origem dos lançamentos;
- histórico.

Para o custo da safra aparecer corretamente, os lançamentos precisam estar associados à safra, talhão, operação ou unidade operacional.

## 14. Alertas e recomendações

### Onde ver no Web

Menus relacionados:

- Agricultura > Central de Inteligência;
- Agricultura > Recomendações;
- Inteligência Operacional > Recomendações;
- Dashboard Executivo da safra;
- Alertas Executivos da safra.

### Onde ver no Campo PWA

Rota: `/recomendacoes`

A tela do Campo mostra:

- recomendações persistidas no dispositivo;
- filtros por domínio, status e prioridade;
- leitura operacional da recomendação selecionada.

### Como agir

| Tipo | O que fazer |
| --- | --- |
| Informativo | Ler e acompanhar. |
| Atenção | Conferir dados da safra, talhão ou operação. |
| Crítico | Acionar responsável e registrar ação corretiva. |
| Recomendação operacional | Executar ou planejar tarefa conforme orientação. |

Alertas e recomendações dependem de dados suficientes. Se nada aparecer no início, isso pode ser normal.

## 15. Resultados da safra

### Onde acessar

Menu: Agricultura > Rentabilidade Agrícola  
Rota: `/dashboard/agricola/rentabilidade`

Menu: Agricultura > DRE Agrícola v1  
Rota: `/dashboard/agricola/dre`

### Filtros disponíveis na rentabilidade

- safra;
- fazenda;
- unidade operacional.

### Indicadores exibidos quando há dados

| Indicador | Interpretação |
| --- | --- |
| Receita líquida | Valor de receita considerado no resultado. |
| Margem | Relação entre resultado operacional e receita líquida. |
| Área total | Soma das áreas do recorte selecionado. |
| Eficiência econômica | Indicador econômico derivado da DRE. |
| Volume total | Produção real ou estimada. |
| Valor médio de venda | Receita dividida pelo volume, quando disponível. |
| Custo operacional total | Custos diretos/operacionais consolidados. |
| Resultado por saca | Resultado dividido pelo total de sacas. |
| Ranking por unidade operacional | Comparação de unidades/talhões quando houver dados. |
| Warnings | Avisos de inconsistência ou dados incompletos. |

### Caminho mínimo para aparecer resultado

1. Safra criada.
2. Cultura Café selecionada.
3. Talhões vinculados.
4. Área informada.
5. Operações registradas.
6. Consumo de insumos ou despesas apropriadas.
7. Colheita/produção registrada.
8. Receita ou comercialização registrada.
9. DRE consolidada.
10. Rentabilidade calculada.

### Quando a rentabilidade fica zerada

Isso normalmente ocorre quando:

- ainda não há receita;
- ainda não há custo apropriado;
- não há produção real ou estimada;
- a safra não foi selecionada no filtro;
- os talhões não estão vinculados ao cultivo;
- a DRE não conseguiu consolidar o recorte.

## 16. Exemplo completo - Fazenda de café

### Contexto

Cliente: Fazenda Santa Rita  
Cultura: Café  
Safra: Café 2026  
ERP: Sankhya  
Unidade Produtiva: Fazenda Santa Rita  
Depósito principal: Depósito Central de Insumos

### Passo a passo

1. O Owner/Admin acessa `/login`.
2. Seleciona o ambiente da Fazenda Santa Rita.
3. O sistema direciona para `/onboarding/configurar`.
4. O usuário define ano agrícola de julho a junho.
5. Mantém unidade de área em hectare.
6. Mantém fuso São Paulo/Brasília e moeda BRL.
7. Mantém categorias padrão marcadas.
8. Clica em `Concluir Configuração`.
9. Acessa `/dashboard/implantacao/wizard`.
10. Clica em `Iniciar implantação`.
11. O Wizard aponta Unidade Produtiva pendente.
12. A equipe cria ou valida `Fazenda Santa Rita`.
13. O usuário acessa `Minha Propriedade > Propriedades`.
14. Confere a propriedade Fazenda Santa Rita.
15. Acessa `Imóveis Rurais > Imóveis Rurais`.
16. Confere CAR, CCIR, município e documentação.
17. Cria a estrutura territorial.
18. Cria `Gleba Norte`.
19. Cria `Talhão 01 - Mundo Novo`.
20. Cria `Talhão 02 - Catuaí`.
21. Cria `Depósito Central de Insumos`.
22. Acessa `Configurações > Integrações > ERP Sankhya`.
23. Informa URL, usuário e senha autorizados.
24. Clica em `Salvar configuração`.
25. Clica em `Testar conexão`.
26. Confirma saúde da integração com sucesso.
27. Executa sincronização de pessoas e produtos, se autorizada para o piloto.
28. Acessa `Pessoas & Parceiros` e confere fornecedores e clientes.
29. Acessa `Catálogo de Produtos` e confere insumos.
30. Acessa `Agricultura > Safras`.
31. Clica em `Nova Safra`.
32. Informa `2026`.
33. Seleciona cultura `Café`.
34. Informa cultivar `Mundo Novo`.
35. Vincula `Talhão 01`.
36. Informa área de 12,50 ha.
37. Informa meta de 35 sc/ha.
38. Adiciona outro cultivo ou talhão se necessário.
39. Clica em `Criar Safra`.
40. Acessa a safra criada.
41. Confere checklist, tarefas e fenologia.
42. Acessa `Operacional > Campo > Dispositivos`.
43. Clica em `Novo dispositivo`.
44. Cria `Tablet Operador João`.
45. Seleciona o operador.
46. Seleciona Fazenda Santa Rita.
47. Gera código de ativação.
48. O operador abre o Campo PWA.
49. Informa o código.
50. Cria PIN de 6 dígitos.
51. Sincroniza antes de ir ao talhão.
52. No talhão, registra uma aplicação.
53. O registro fica salvo offline.
54. Ao voltar para internet, abre `/sync`.
55. Sincroniza os dados.
56. No Web, o gestor confere o Caderno de Campo.
57. Confere se houve baixa ou necessidade de ajuste de estoque.
58. Confere custos agrícolas.
59. Registra ou importa receita/comercialização quando ocorrer venda.
60. Acessa `Rentabilidade Agrícola`.
61. Seleciona Safra Café 2026.
62. Analisa margem, custo, receita e resultado por saca, quando houver dados suficientes.

## 17. Problemas comuns

| Problema | Causa provável | Como resolver |
| --- | --- | --- |
| Dashboard bloqueado | Onboarding ou Wizard incompleto | Concluir onboarding, abrir Wizard e corrigir pendências. |
| Unidade Produtiva ausente | Fazenda ainda não criada/ativada | Criar ou validar a fazenda e reavaliar checklist. |
| Checklist incompleto | Dados mínimos faltando | Ler item pendente, corrigir cadastro e clicar em `Reavaliar checklist`. |
| Sankhya não conecta | URL, credencial, ambiente ou Gateway incorreto | Conferir com responsável pelo ERP e repetir teste de conexão. |
| Campo não sincroniza | Sem internet, dispositivo expirado ou fila com erro | Abrir `/sync`, reenviar, conferir validade e acionar suporte se houver conflito. |
| Produto duplicado | Importação e cadastro manual criaram registros parecidos | Não usar ambos; definir registro oficial com equipe. |
| Talhão não aparece na safra | Talhão não cadastrado como tipo TALHÃO ou sem área | Conferir estrutura da propriedade e georreferenciamento. |
| Cultura Café não aparece | Cadastro de cultura incompleto | Conferir `Culturas e Variedades` ou acionar operação assistida. |
| Safra sem resultado | Falta custo, receita, produção ou vínculo com talhão | Conferir operações, estoque, financeiro e DRE. |
| Rentabilidade zerada | DRE sem dados suficientes | Conferir receita, custo, produção e filtros. |
| Alerta não aparece | Ainda não há dados ou regra aplicável | Continuar operação e confirmar configuração com equipe. |
| Depósito não aparece | Depósito não cadastrado/ativo | Criar depósito e reavaliar Wizard. |
| Go-live bloqueado | Pendência crítica aberta | Resolver item crítico antes de iniciar go-live. |

## 18. Glossário rápido

| Termo | Explicação simples |
| --- | --- |
| Tenant | Nome técnico para o ambiente da empresa dentro do AgroSaaS. No uso diário, chame de ambiente. |
| Unidade Produtiva | Fazenda ou unidade operacional usada para organizar os dados. |
| Propriedade | Cadastro da fazenda como operação rural. |
| Imóvel Rural | Cadastro legal/fundiário, com documentos como CAR, CCIR e matrícula. |
| Gleba | Divisão territorial maior dentro da propriedade. |
| Talhão | Área de plantio acompanhada na safra. |
| Área Operacional | Subdivisão usada para organizar o trabalho de campo. |
| Safra | Ciclo agrícola acompanhado pelo sistema. |
| Insumo | Produto usado na operação, como fertilizante, defensivo ou corretivo. |
| Estoque | Controle de produtos, saldos, depósitos e movimentações. |
| Romaneio | Registro de colheita, carga, entrega ou movimentação da produção. |
| Custo por saca | Custo total dividido pela quantidade de sacas produzidas. |
| Rentabilidade | Resultado econômico da safra após receitas e custos. |
| Sankhya | ERP usado pelo cliente para cadastros, financeiro e documentos. |
| Campo PWA | Aplicativo de campo que funciona mesmo com internet instável. |
| Go-live | Liberação oficial para começar a operação real assistida. |

## Referências oficiais usadas

- `docs/pilot/PLANO-MESTRE-PILOTO-01.md`
- `docs/pilot/RUNBOOK-01-EXECUCAO-D-5-A-D+7.md`
- `docs/pilot/CHECKLIST-CLIENTE-01-PREPARACAO-IMPLANTACAO.md`
- `docs/implementation/reports/PILOT-03-AUDITORIA-EXECUCAO-IMPLANTACAO.md`
- `docs/implementation/reports/SANKHYA-SYNC-01-ESCOPO-PILOTO-CAFE.md`
- `docs/implementation/reports/SANKHYA-SYNC-02-MAPEAMENTO-OFICIAL.md`
- `docs/implementation/reports/SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md`
- `docs/implementation/reports/SANKHYA-AUTH-03-VALIDACAO-ESPECIFICACAO-TECNICA.md`

## Limites importantes para o usuário

- O guia não promete sincronização bidirecional com Sankhya.
- O guia não promete faturamento, cancelamento ou escrita de documentos no ERP durante o piloto.
- O resultado econômico depende de dados reais de custo, produção e receita.
- O Campo PWA precisa ser ativado, sincronizado e usado corretamente para que registros apareçam no Web.
- O Wizard é obrigatório para go-live e deve ser usado como referência de prontidão.
- Quando uma tela existir parcialmente, a equipe AgroSaaS deve conduzir a operação assistida sem criar fluxo paralelo.
