# PILOT-00A - Auditoria de Implantacao

## Escopo

Auditoria exclusivamente de codebase para identificar a sequencia de implantacao do AgroSaaS, o conjunto minimo de cadastros para iniciar operacao e as dependencias entre modulos.

Nao houve alteracao de codigo.

## Base da auditoria

Fontes principais consultadas:

- [/opt/lampp/htdocs/farm/services/api/main.py](/opt/lampp/htdocs/farm/services/api/main.py)
- [/opt/lampp/htdocs/farm/services/api/core/routers/auth.py](/opt/lampp/htdocs/farm/services/api/core/routers/auth.py)
- [/opt/lampp/htdocs/farm/services/api/core/routers/onboarding.py](/opt/lampp/htdocs/farm/services/api/core/routers/onboarding.py)
- [/opt/lampp/htdocs/farm/services/api/core/routers/configuration.py](/opt/lampp/htdocs/farm/services/api/core/routers/configuration.py)
- [/opt/lampp/htdocs/farm/services/api/core/schemas/unidade_produtiva_input.py](/opt/lampp/htdocs/farm/services/api/core/schemas/unidade_produtiva_input.py)
- [/opt/lampp/htdocs/farm/services/api/core/routers/unidades_produtivas.py](/opt/lampp/htdocs/farm/services/api/core/routers/unidades_produtivas.py)
- [/opt/lampp/htdocs/farm/services/api/core/cadastros/propriedades/propriedade_models.py](/opt/lampp/htdocs/farm/services/api/core/cadastros/propriedades/propriedade_models.py)
- [/opt/lampp/htdocs/farm/services/api/core/cadastros/propriedades/service.py](/opt/lampp/htdocs/farm/services/api/core/cadastros/propriedades/service.py)
- [/opt/lampp/htdocs/farm/services/api/core/cadastros/propriedade_imovel/service.py](/opt/lampp/htdocs/farm/services/api/core/cadastros/propriedade_imovel/service.py)
- [/opt/lampp/htdocs/farm/services/api/imoveis/models/imovel.py](/opt/lampp/htdocs/farm/services/api/imoveis/models/imovel.py)
- [/opt/lampp/htdocs/farm/services/api/imoveis/routers/imovel.py](/opt/lampp/htdocs/farm/services/api/imoveis/routers/imovel.py)
- [/opt/lampp/htdocs/farm/services/api/agricola/safras/schemas.py](/opt/lampp/htdocs/farm/services/api/agricola/safras/schemas.py)
- [/opt/lampp/htdocs/farm/services/api/agricola/production_units/schemas.py](/opt/lampp/htdocs/farm/services/api/agricola/production_units/schemas.py)
- [/opt/lampp/htdocs/farm/services/api/operacional/schemas/estoque.py](/opt/lampp/htdocs/farm/services/api/operacional/schemas/estoque.py)
- [/opt/lampp/htdocs/farm/services/api/operacional/routers/estoque_implantacao.py](/opt/lampp/htdocs/farm/services/api/operacional/routers/estoque_implantacao.py)
- [/opt/lampp/htdocs/farm/services/api/financeiro/schemas/receita_schema.py](/opt/lampp/htdocs/farm/services/api/financeiro/schemas/receita_schema.py)
- [/opt/lampp/htdocs/farm/services/api/financeiro/schemas/despesa_schema.py](/opt/lampp/htdocs/farm/services/api/financeiro/schemas/despesa_schema.py)
- [/opt/lampp/htdocs/farm/services/api/financeiro/routers/planos_conta.py](/opt/lampp/htdocs/farm/services/api/financeiro/routers/planos_conta.py)
- [/opt/lampp/htdocs/farm/services/api/core/services/configuracoes_service.py](/opt/lampp/htdocs/farm/services/api/core/services/configuracoes_service.py)
- [/opt/lampp/htdocs/farm/apps/web/src/components/auth/onboarding-guard.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/auth/onboarding-guard.tsx)
- [/opt/lampp/htdocs/farm/apps/web/src/app/onboarding/configurar/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/onboarding/configurar/page.tsx)
- [/opt/lampp/htdocs/farm/services/api/pecuaria/routers/lotes.py](/opt/lampp/htdocs/farm/services/api/pecuaria/routers/lotes.py)
- [/opt/lampp/htdocs/farm/services/api/pecuaria/schemas/animal_schema.py](/opt/lampp/htdocs/farm/services/api/pecuaria/schemas/animal_schema.py)
- [/opt/lampp/htdocs/farm/services/api/pecuaria/schemas/pesagem_schema.py](/opt/lampp/htdocs/farm/services/api/pecuaria/schemas/pesagem_schema.py)
- [/opt/lampp/htdocs/farm/services/api/pecuaria/schemas/piquete_schema.py](/opt/lampp/htdocs/farm/services/api/pecuaria/schemas/piquete_schema.py)
- [/opt/lampp/htdocs/farm/services/api/operacional/routers/frota.py](/opt/lampp/htdocs/farm/services/api/operacional/routers/frota.py)
- [/opt/lampp/htdocs/farm/services/api/operacional/schemas/frota.py](/opt/lampp/htdocs/farm/services/api/operacional/schemas/frota.py)

## Resumo executivo

O menor caminho para uma fazenda comecar a operar nao e o mesmo que o caminho para usar todos os modulos.

O fluxo real de liberacao observado no codigo e:

1. Criar usuario.
2. Criar tenant/assinatura.
3. Completar onboarding tecnico do tenant.
4. Criar a primeira unidade produtiva.
5. A partir disso, cadastrar o que for necessario por modulo.

O ponto mais importante da auditoria:

- O sistema bloqueia o acesso ao dashboard enquanto o onboarding nao estiver completo.
- O onboarding so fica completo quando existe tenant ativo e ao menos uma fazenda/unidade produtiva ativa.
- A criacao de `UnidadeProdutiva` ja auto-cria a estrutura raiz de areas.

## Sequencia oficial de implantacao

### Fase 1 - Acesso e tenant

1. Criar usuario global.
2. Criar tenant/assinatura.
3. Selecionar contexto do tenant.
4. Garantir que o tenant esteja ativo e com onboarding concluido.

### Fase 2 - Configuracao inicial obrigatoria

5. Executar o wizard de onboarding.
6. Definir ano agricola.
7. Definir unidade de area.
8. Definir fuso horario.
9. Definir moeda.
10. Aplicar categorias padrao do sistema, quando aceitas.

### Fase 3 - Base operacional minima

11. Criar a primeira `UnidadeProdutiva`.
12. Aproveitar a estrutura raiz criada automaticamente:
   - `AREA_RURAL`
   - `INFRAESTRUTURA`

### Fase 4 - Base territorial e patrimonial

13. Criar `Propriedade`, se o fluxo patrimonial/legal for usado.
14. Criar `ImovelRural`, se o fluxo fundiario/legal for usado.
15. Criar `PropriedadeImovel`, se for necessario formalizar o vinculo canonico.
16. Detalhar a arvore territorial:
   - glebas
   - talhoes
   - areas operacionais
   - piquetes
   - areas ambientais
   - infraestrutura filha
17. Registrar matriculas e registros ambientais, se o negocio exigir.

### Fase 5 - Cadastros gerais de suporte

18. Cadastrar pessoas.
19. Cadastrar produtos.
20. Cadastrar culturas e commodities.
21. Cadastrar centros de custo.
22. Cadastrar plano de contas.
23. Cadastrar fornecedores, clientes e demais parceiros.

### Fase 6 - Estoque

24. Criar depositos.
25. Criar lotes.
26. Registrar estoque inicial.
27. Regular validades e saldos.

### Fase 7 - Agricultura

28. Criar talhoes/areas produtivas.
29. Criar safra.
30. Criar cultivo.
31. Criar production units.
32. Registrar operacoes, caderno e romaneios.

### Fase 8 - Pecuaria

33. Criar piquetes, quando houver pastejo.
34. Criar lotes de animais.
35. Cadastrar animais.
36. Registrar pesagens, sanidade e reproducao.

### Fase 9 - Maquinas, RH e Financeiro

37. Cadastrar equipamentos e implementos.
38. Cadastrar colaborador, funcao e equipe.
39. Cadastrar contas bancarias.
40. Registrar receitas e despesas.
41. Consolidar fluxo de caixa e relatorios.

## Menor conjunto de cadastros para iniciar operacao

### Obrigatorio para liberar o sistema

- Usuario
- Tenant
- Onboarding concluido
- Uma `UnidadeProdutiva` ativa

### Obrigatorio para a operacao diaria minima

Depende do modulo que sera usado primeiro:

- Agricultura:
  - ao menos uma area/talhao
  - uma safra
  - um cultivo
- Estoque:
  - produto
  - deposito
- Financeiro:
  - plano de contas
- Pecuaria:
  - lote ou piquete, conforme a estrategia de manejo
- Maquinas:
  - maquinario
- RH:
  - colaborador, se houver apontamento ou equipe

## Dependencias entre modulos

### Administracao

| Modulo | Depende de | Obrigatorio? | Opcional? | Pode configurar depois? | Circular? | Redundancia? |
|---|---|---:|---:|---:|---:|---:|
| Tenant | Usuario global | Sim | Nao | Nao | Nao | Nao |
| Usuarios | Tenant | Sim para equipe | Sim para piloto solo | Sim | Nao | Parcial, porque owner ja resolve o inicio |
| Perfis | Tenant / backoffice | Nao no piloto minimo | Sim | Sim | Nao | Sim, porque existem perfis globais e permissões granulares |
| Permissoes | Perfil | Nao no piloto minimo | Sim | Sim | Nao | Sim, ha sobreposicao entre perfil e permissao por modulo |

### Estrutura

| Modulo | Depende de | Obrigatorio? | Opcional? | Pode configurar depois? | Circular? | Redundancia? |
|---|---|---:|---:|---:|---:|---:|
| UnidadeProdutiva | Tenant | Sim | Nao | Nao | Nao | Nao |
| Estrutura de areas | UnidadeProdutiva | Sim para agricultura/pecuaria | Sim para go-live administrativo | Sim | Nao | Sim, porque raizes sao auto-criadas |
| Propriedade | Tenant | Nao no minimo operacional | Sim | Sim | Nao | Sim, se o foco inicial for operacional e nao patrimonial |
| ImovelRural | UnidadeProdutiva | Nao no minimo operacional | Sim | Sim | Nao | Parcial, pois cobre a mesma realidade da fazenda por outra lente |
| PropriedadeImovel | Propriedade + ImovelRural | Nao no minimo operacional | Sim | Sim | Nao | Sim, e um vinculo canonico adicional |
| Talhoes | Estrutura de areas | Sim para agricultura | Sim para outros modulos | Sim | Nao | Nao |
| Piquetes | Estrutura de areas | Sim para pecuaria a pasto | Sim | Sim | Nao | Nao |
| Infraestrutura | UnidadeProdutiva | Nao | Sim | Sim | Nao | Sim, pois a root ja nasce automaticamente |

### Cadastros gerais

| Modulo | Depende de | Obrigatorio? | Opcional? | Pode configurar depois? | Circular? | Redundancia? |
|---|---|---:|---:|---:|---:|---:|
| Pessoas | Tenant | Nao no minimo | Sim | Sim | Nao | Nao |
| Produtos | Tenant | Sim para estoque/compras | Sim para inicio manual | Sim | Nao | Nao |
| Culturas | Tenant | Sim para agricultura | Sim | Sim | Nao | Nao |
| Commodities | Produtos/culturas | Nao no minimo | Sim | Sim | Nao | Parcial |
| Safras | Talhoes/areas | Sim para agricultura | Nao | Nao no ciclo agricola | Nao | Nao |
| Fornecedores | Pessoas/tenant | Nao no minimo | Sim | Sim | Nao | Nao |
| Clientes | Pessoas/tenant | Nao no minimo | Sim | Sim | Nao | Nao |
| Centros de custo | Tenant | Nao no minimo | Sim | Sim | Nao | Parcial, util para rateios/financeiro |
| Plano de contas | Tenant | Sim para financeiro | Nao para go-live administrativo | Pode configurar depois, mas antes de lancar financeiro | Nao | Nao |

### Estoque

| Modulo | Depende de | Obrigatorio? | Opcional? | Pode configurar depois? | Circular? | Redundancia? |
|---|---|---:|---:|---:|---:|---:|
| Deposito | UnidadeProdutiva | Sim para operar estoque | Nao | Nao se houver movimentacao | Nao | Nao |
| Estoque inicial | Produto + Deposito | Sim para operar fisicamente | Nao | Pode depois, mas antes de consumo real | Nao | Nao |
| Lotes | Produto + Deposito | Opcional no inicio | Sim | Sim | Nao | Parcial, porque lote replica parte do controle de saldo |
| Validades | Lote | Opcional | Sim | Sim | Nao | Nao |
| Implantacao assistida | Produto + Deposito + mapeamento CSV | Nao | Sim | Sim | Nao | Sim, porque e um fluxo de carga assistida e nao o fluxo normal |

### Agricultura

| Modulo | Depende de | Obrigatorio? | Opcional? | Pode configurar depois? | Circular? | Redundancia? |
|---|---|---:|---:|---:|---:|---:|
| Safra | Pelo menos uma area/talhao | Sim | Nao | Nao no ciclo agricola | Nao | Nao |
| Cultivo | Safra + area | Sim para uso agricola | Nao | Nao no ciclo agricola | Nao | Nao |
| Production Unit | Cultivo + area | Sim para custo/apontamento detalhado | Nao | Pode depois, mas antes de apontar custo operacional | Nao | Nao |
| Caderno | Operacoes | Sim se houver rastreabilidade operacional | Nao | Pode depois | Nao | Nao |
| Romaneios | Operacoes/colheita | Nao no inicio | Sim | Sim | Nao | Nao |

### Pecuaria

| Modulo | Depende de | Obrigatorio? | Opcional? | Pode configurar depois? | Circular? | Redundancia? |
|---|---|---:|---:|---:|---:|---:|
| Piquete | Estrutura de areas | Sim para pastejo rotacionado | Sim | Sim | Nao | Nao |
| Lote | Tenant + unidade produtiva | Sim para organizar rebanho | Nao | Nao se houver rebanho ativo | Nao | Nao |
| Animal | Lote opcional, mas exige identificador | Sim para controle individual | Nao | Pode depois, desde que o lote exista | Nao | Nao |
| Pesagem | Animal | Nao sem animal | Nao | Sim | Nao | Nao |
| Sanidade | Animal / lote | Nao no minimo | Sim | Sim | Nao | Nao |
| Reproducao | Animal | Nao no minimo | Sim | Sim | Nao | Nao |

### Maquinas

| Modulo | Depende de | Obrigatorio? | Opcional? | Pode configurar depois? | Circular? | Redundancia? |
|---|---|---:|---:|---:|---:|---:|
| Equipamentos | Tenant +, idealmente, unidade produtiva | Nao no minimo | Sim | Sim | Nao | Nao |
| Implementos | Equipamento ou cadastro correlato | Nao no minimo | Sim | Sim | Nao | Nao |
| Oficina | Equipamentos | Nao no minimo | Sim | Sim | Nao | Nao |
| Abastecimento | Equipamento + estoque/combustivel | Nao no minimo | Sim | Sim | Nao | Nao |

### RH

| Modulo | Depende de | Obrigatorio? | Opcional? | Pode configurar depois? | Circular? | Redundancia? |
|---|---|---:|---:|---:|---:|---:|
| Colaboradores | Tenant | Nao no minimo | Sim | Sim | Nao | Nao |
| Equipes | Colaboradores | Nao no minimo | Sim | Sim | Nao | Nao |
| Funcoes | Tenant | Nao no minimo | Sim | Sim | Nao | Nao |

### Financeiro

| Modulo | Depende de | Obrigatorio? | Opcional? | Pode configurar depois? | Circular? | Redundancia? |
|---|---|---:|---:|---:|---:|---:|
| Plano de contas | Tenant | Sim para lancar receitas/despesas | Nao | Pode ser configurado depois, mas antes do uso financeiro | Nao | Nao |
| Contas bancarias | Tenant | Nao para entrada inicial | Sim | Sim | Nao | Nao |
| Centros de custo | Tenant | Nao no minimo | Sim | Sim | Nao | Parcial, porque tambem aparece em outros modulos |
| Fluxo de caixa | Lancamentos financeiros | Sim para visao gerencial | Nao | Nao se o financeiro for usado | Nao | Nao |

## Dependencias ocultas

1. O onboarding do frontend e bloqueado por `/onboarding/status`.
2. O status de onboarding considera completo quando o tenant esta ativo e existe ao menos uma fazenda ativa.
3. `UnidadeProdutiva` cria a arvore raiz de `AreaRural` automaticamente.
4. `ImovelRural` depende de `UnidadeProdutiva` e pode acionar vinculo canônico com `PropriedadeImovel`.
5. `PropriedadeImovel` exige `Propriedade` e `ImovelRural` existentes ao mesmo tempo.
6. `Safra` exige ao menos uma forma de definicao de cultivo/talhao.
7. `Cultivo` e `ProductionUnit` dependem de area real cadastrada.
8. `Receita` e `Despesa` nao validam sem `PlanoConta`.
9. O wizard de onboarding marca configuracao inicial como concluida, mas nao cria fazenda automaticamente.
10. O fluxo assistido de estoque nao e o mesmo que a movimentacao normal de estoque; ele exige CSV, mapeamento e sessao de implantacao.

## Bloqueios reais de implantacao

- Nao existe acesso util ao dashboard sem onboarding completo.
- Nao existe operacao agricola real sem ao menos uma unidade produtiva.
- Nao existe operacao de safra sem area/talhao.
- Nao existe lancamento financeiro sem plano de contas.
- Nao existe controle de estoque minimo sem deposito e produto.
- Nao existe pecuaria individual sem animal identificado.
- Existem bloqueios por modulo e por plano:
  - `O1_FROTA`
  - `O2_ESTOQUE`
  - `O3_COMPRAS`
  - `F1_TESOURARIA`
  - `P1_REBANHO`
  - `P2_GENETICA`
  - `P3_CONFINAMENTO`
  - `P4_LEITE`
  - `PlanTier.PROFISSIONAL` e `PlanTier.ENTERPRISE` em frota

## Cadastros que podem ser feitos depois

- Perfis e permissões finas
- Equipe completa de usuarios
- Propriedade e vinculos fundiarios
- Cartorios e documentos legais
- Centros de custo detalhados
- Produtos complementares e marcas/modelos
- Lotes de estoque, validades e inventario detalhado
- Romaneios e rastreabilidade avancada
- Piquetes e manejo zootecnico detalhado
- Oficina, manutencao preventiva e abastecimento
- Contas bancarias e conciliacao
- Integracoes e automacoes

## Redundancias identificadas

- `UnidadeProdutiva` e `ImovelRural` descrevem o mesmo ativo por lentes diferentes: operacional e legal.
- `PropriedadeImovel` replica um vinculo que muitas vezes o proprio `ImovelRural` ja representa de forma pratica.
- O wizard de onboarding e a criacao de `UnidadeProdutiva` possuem sobreposicao parcial de configuracao inicial, mas nao fazem a mesma coisa.
- `Categoria` padrao do onboarding e `PlanoConta` do financeiro nao sao equivalentes; a interface pode induzir confusao.

## UX e friccoes

### Cadastros dificeis

- `ImovelRural` por causa de dados legais e validacoes de area.
- `PropriedadeImovel` por exigir duas entidades previas e regras de principalidade.
- `EstoqueImplantacaoAssistida` por depender de CSV, mapeamento e validacao em etapas.
- `Plano de contas` por exigir leitura contabil antes do uso financeiro.
- `Safra` e `ProductionUnit` por dependerem de areas bem formadas.

### Telas confusas

- Tela de onboarding com termos proximos demais de configuracao operacional.
- Tela de cadastro de imoveis pode parecer independente, mas depende de fazenda.
- Tela de estoque assistido e um fluxo separado do estoque normal.
- O cadastro de categorias do onboarding pode ser confundido com plano de contas.

### Passos redundantes

- Criar `UnidadeProdutiva` e depois repetir parte da configuracao territorial manualmente sem necessidade.
- Criar `Propriedade` e `ImovelRural` sem claridade para o usuario sobre qual e o ativo oficial.
- Cadastrar categorias de produto e depois configurar produtos sem uma ordem guiada.

### Dependencias escondidas

- O onboarding nao cria a fazenda.
- O dashboard nao libera sem a fazenda ativa.
- O financeiro nao funciona sem plano de contas.
- A agricultura nao anda sem area.
- O estoque nao anda sem deposito.

### Mensagens pouco claras

- "Nao foi possivel detectar o tenant ativo" e util tecnicamente, mas pouco orienta o usuario final.
- Falhas em `require_module` e `require_tier` tendem a parecer indisponibilidade, nao bloqueio de configuracao.

## Tempo estimado de configuracao

Estimativa baseada apenas nos fluxos encontrados no codigo, nao em medicao real:

- Tenant + onboarding + primeira fazenda: 15 a 30 minutos se os dados estiverem prontos.
- Primeiro go-live operacional minimo com um modulo principal configurado:
  - agricultura: 45 a 90 minutos
  - estoque: 45 a 90 minutos
  - financeiro: 30 a 60 minutos apos existir plano de contas
- Implantacao inicial mais realista para piloto, com fazenda, areas basicas, catalogo minimo, deposito e plano de contas: 2 a 4 horas.
- Se incluir fundiario/legal, estoque importado e pecuaria, a janela sobe para 4 a 8 horas.

## Oportunidade clara para um futuro Wizard

Existe oportunidade objetiva para um Assistente de Implantacao.

### Ordem ideal do wizard

1. Usuario e tenant
2. Nome da fazenda/unidade produtiva
3. Dados territoriais minimos
4. Unidade de area, ano agricola, fuso e moeda
5. Ativacao de categorias padrao
6. Criacao do primeiro deposito
7. Criacao do primeiro talhao
8. Criacao do primeiro plano de contas
9. Importacao assistida de estoque
10. Opcional: propriedade, imovel e vinculo canonico

### Por que vale a pena

- O sistema tem dependencias escondidas que hoje aparecem tarde.
- O onboarding atual libera o tenant, mas nao prepara a operacao real.
- Ha sobreposicao entre configuracao, cadastro e uso.
- O wizard pode reduzir retrabalho em:
  - fazenda
  - areas
  - deposito
  - plano de contas
  - primeiro cultivo ou rebanho

## Respostas objetivas

### 1. Qual e a sequencia oficial de implantacao do AgroSaaS?

Tenant -> usuario -> onboarding -> unidade produtiva -> estrutura territorial -> cadastros gerais -> estoque/agricultura/pecuaria/maquinas/RH/financeiro conforme uso.

### 2. Quanto tempo um novo cliente leva para configurar a plataforma?

Pelo codigo, entre 2 e 4 horas para uma implantacao inicial util de piloto, podendo cair para menos de 1 hora se o uso for apenas administrativo e com poucos dados.

### 3. Quais cadastros sao realmente obrigatorios?

- Usuario
- Tenant
- Onboarding completo
- UnidadeProdutiva
- E, por modulo:
  - talhao/area para agricultura
  - deposito e produto para estoque
  - plano de contas para financeiro
  - animal/lote para pecuaria

### 4. Quais podem ser feitos posteriormente?

Perfis, permissoes, propriedade, imovel, vinculo fundiario, contas bancarias, centros de custo, detalhamento de estoque, pecuaria avancada, frota, RH completo e integracoes.

### 5. Existem dependencias ocultas?

Sim. As principais sao:

- onboarding -> fazenda ativa
- fazenda -> areas raiz automaticas
- safra -> talhao/area
- receita/despesa -> plano de contas
- estoque -> deposito + produto
- imovel -> unidade produtiva
- propriedade-imovel -> propriedade + imovel

### 6. Existe algum bloqueio para implantacao?

Sim. O dashboard e os modulos sao bloqueados por onboarding incompleto, por feature flags de modulo e, em frota, por limite de plano.

### 7. Existe alguma oportunidade clara para um futuro Assistente de Implantacao (Wizard)?

Sim. O wizard e altamente justificavel porque a plataforma tem muitos passos dependentes e algumas validacoes aparecem tarde demais para o usuario.

