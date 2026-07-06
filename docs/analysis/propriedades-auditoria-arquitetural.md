# Auditoria Arquitetural do Módulo Propriedades

Data da análise: 2026-06-20

Escopo:
- Apenas leitura de código e documentação.
- Nenhuma alteração de código, migration ou funcionalidade.

Fontes principais:
- [agrosaas-master-context.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-master-context.md)
- [agrosaas-ai-rules.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-ai-rules.md)
- [agrosaas-data-model.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-data-model.md)
- [agrosaas-routing-map.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-routing-map.md)
- [agrosaas-domain-map.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-domain-map.md)
- [agrosaas-engineering-playbook.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-engineering-playbook.md)

## Síntese Executiva

O código-base não trata "Propriedades" e "Imóveis Rurais" como a mesma coisa.

- `Propriedades` funciona como cadastro operacional/territorial da fazenda ou unidade produtiva.
- `Imóveis Rurais` já existe como módulo separado e concentra o domínio legal/patrimonial.
- O módulo `propriedades` contém também alguns campos fundiários e ambientais, o que cria sobreposição semântica.

Conclusão objetiva:
- O AgroSaaS **não deve criar um novo módulo separado chamado "Imóveis Rurais"**.
- O domínio legal já existe em `services/api/imoveis`.
- O que falta é **delimitar melhor fronteiras** entre:
  - `Propriedades` = unidade produtiva, território, geoespacial, operação.
  - `Imóveis Rurais` = matrícula, cartório, CAR, CCIR, ITR, documentação e contratos.

## Etapa 1 - Inventário do Módulo

### Backend

| Arquivo | Responsabilidade | Status |
|---|---|---|
| `services/api/core/cadastros/propriedades/models.py` | Modelo territorial hierárquico (`AreaRural`, `MatriculaImovel`, `RegistroAmbiental`, `Infraestrutura`, `ValorPatrimonial`) | Ativo |
| `services/api/core/cadastros/propriedades/schemas.py` | Schemas Pydantic do cadastro territorial e acessórios | Ativo |
| `services/api/core/cadastros/propriedades/router.py` | Rotas de áreas rurais, matrículas, registros ambientais, valores patrimoniais e infraestrutura | Ativo |
| `services/api/core/cadastros/propriedades/service.py` | Regras de negócio para hierarquia, agregação de área, matrículas e registros | Ativo |
| `services/api/core/cadastros/propriedades/propriedade_models.py` | Compatibilidade/legado do módulo de propriedades | Parcial / legado |
| `services/api/core/cadastros/propriedades/propriedade_schemas.py` | Compatibilidade/legado do módulo de propriedades | Parcial / legado |
| `services/api/core/cadastros/propriedades/propriedade_router.py` | Compatibilidade/legado de rotas | Parcial / legado |
| `services/api/core/cadastros/propriedades/propriedade_service.py` | Compatibilidade/legado de serviço | Parcial / legado |
| `services/api/core/cadastros/propriedades/propriedade_hierarquia_router.py` | Compatibilidade/legado de hierarquia | Parcial / legado |
| `services/api/core/cadastros/propriedades/hierarquia_service.py` | Serviço auxiliar da hierarquia territorial | Ativo |
| `services/api/imoveis/models/imovel.py` | Modelo legal/patrimonial do imóvel rural | Ativo |
| `services/api/imoveis/routers/imovel.py` | CRUD legal de imóveis rurais, cartório, benfeitorias | Ativo |
| `services/api/imoveis/routers/arrendamento.py` | Contratos de arrendamento e parceria rural | Ativo |
| `services/api/imoveis/routers/avaliacao.py` | Avaliação patrimonial dos imóveis | Ativo |
| `services/api/imoveis/services/imovel_service.py` | Regras do imóvel legal | Ativo |
| `services/api/imoveis/services/arrendamento_service.py` | Regras de arrendamento/parceria | Ativo |
| `services/api/imoveis/services/avaliacao_service.py` | Regras de avaliação patrimonial | Ativo |
| `services/api/imoveis/services/documento_service.py` | Gestão documental | Ativo |

### Frontend

| Arquivo | Responsabilidade | Status |
|---|---|---|
| `apps/web/src/app/(dashboard)/cadastros/propriedades/page.tsx` | Página de cadastro operacional de propriedades | Ativo |
| `apps/web/src/app/(dashboard)/cadastros/propriedades/propriedades-client.tsx` | Tela principal de cadastro/edição de fazendas e seus dados territoriais | Ativo |
| `apps/web/src/app/(dashboard)/cadastros/propriedades/[id]/page.tsx` | Detalhe da propriedade e sua estrutura | Ativo |
| `apps/web/src/app/(dashboard)/cadastros/propriedades/talhoes/page.tsx` | Georreferenciamento e áreas | Ativo |
| `apps/web/src/app/(dashboard)/dashboard/settings/propriedades/page.tsx` | Redirecionamento para o cadastro oficial | Ativo / redirecionamento |
| `apps/web/src/app/(dashboard)/dashboard/settings/propriedades/[id]/estrutura/page.tsx` | Estrutura territorial da fazenda | Ativo |
| `apps/web/src/app/(dashboard)/cadastros/imoveis/page.tsx` | Página do módulo legal de imóveis rurais | Ativo |
| `apps/web/src/app/(dashboard)/cadastros/imoveis/ImoveisClient.tsx` | Tela de imóveis, documentos, avaliações e arrendamentos | Ativo |
| `apps/web/src/app/(dashboard)/cadastros/imoveis/ArrendamentosClient.tsx` | Gestão de contratos | Ativo |
| `apps/web/src/app/(dashboard)/cadastros/imoveis/avaliacoes/page.tsx` | Visão de avaliações patrimoniais | Ativo |
| `apps/web/src/components/propriedade/*` | Componentes da UI do cadastro de propriedades | Ativo |
| `apps/web/src/lib/sidebar-config.ts` | Navegação separando `Propriedades` e `Imóveis Rurais` | Ativo |
| `apps/web/src/lib/permission-catalog.ts` | Catálogo de permissões separando `agricola` e `imoveis` | Ativo |

### Testes

| Arquivo | Responsabilidade | Status |
|---|---|---|
| `services/api/tests/unit/test_propriedade_models.py` | Testes de modelos | Ativo |
| `services/api/tests/unit/test_propriedade_schemas.py` | Testes de schemas | Ativo |
| `services/api/tests/unit/test_propriedade_router.py` | Testes de rotas | Ativo |
| `services/api/tests/unit/test_propriedade_service.py` | Testes de service | Ativo |
| `services/api/tests/unit/test_propriedade_migration.py` | Testes de migração | Ativo |
| `services/api/tests/test_imoveis_integration.py` | Integração do módulo de imóveis | Ativo |
| `services/api/tests/unit/imoveis/test_imovel_service.py` | Testes do serviço de imóveis | Ativo |
| `services/api/tests/unit/imoveis/test_arrendamento_router.py` | Testes de arrendamento | Ativo |
| `services/api/tests/unit/imoveis/test_avaliacao_router.py` | Testes de avaliação | Ativo |

## Etapa 2 - Análise de Domínio

### O conceito atual de Propriedade representa:

- [x] Imóvel Rural
- [x] Unidade Operacional
- [x] Centro de Resultado
- [x] Área Física
- [x] Todos os anteriores

### Justificativa

O conceito é híbrido, mas com pesos diferentes:

- Como **Unidade Operacional**, o código trata a propriedade como `UnidadeProdutiva`/fazenda, com seleção por `activeFazendaId`, telas de fazenda e estrutura territorial.
- Como **Área Física**, o modelo possui geometria, área total, APP, Reserva Legal, coordenadas e árvore de áreas.
- Como **Imóvel Rural**, o cadastro da propriedade já carrega CAR, NIRF, CCIR, SIGEF e CPF/CNPJ do responsável.
- Como **Centro de Resultado**, a ligação é indireta e inferida pelo uso transversal do `tenant_id`; não existe uma entidade contábil explícita de centro de resultado dentro do módulo.

Evidências:
- O cadastro de propriedade usa `UnidadeProdutiva` e não apenas `AreaRural`.
- O formulário da propriedade possui nome, tipo, CPF/CNPJ, município, UF, área total, APP, Reserva Legal, CAR, NIRF, CCIR e SIGEF.
- O módulo de áreas rurais possui hierarquia própria com glebas, talhões, áreas ambientais e infraestrutura.
- O módulo `imoveis` já assume explicitamente a função legal/patrimonial.

## Etapa 3 - Análise Cadastral

| Campo | Existe? | Obrigatório? | Origem |
|---|---|---|---|
| Nome da propriedade | Sim | Sim | `UnidadeProdutivaCreate.nome`; `AreaRural.nome`; UI de propriedade |
| Código interno | Parcial | Não | `AreaRural.codigo`; não há evidência forte de código interno oficial na propriedade principal |
| Município | Sim | Não | `UnidadeProdutivaCreate.municipio`; `ImovelRural.municipio`; UI |
| Estado | Sim | Não | `UnidadeProdutivaCreate.uf`; `ImovelRural.uf`; UI |
| País | Não | Não | Não identificado em propriedades/imóveis |
| Coordenadas | Sim | Não | `coordenadas_sede`, `AreaRural.centroide_lat/lng`, `ImovelRural.latitude/longitude`, `AreaRural.geometria` |
| Área total | Sim | Não | `UnidadeProdutivaCreate.area_total_ha`; `ImovelRural.area_total_ha`; `AreaRural.area_hectares` |
| Área agricultável | Parcial | Não | Derivada em UI como `area_total - APP - RL`; `ImovelRural.area_aproveitavel_ha` |
| Área preservação | Sim | Não | `area_app_ha` e `area_rl_ha`; tipos `APP` e `RESERVA_LEGAL` |
| Área APP | Sim | Não | `UnidadeProdutivaCreate.area_app_ha`; `ImovelRural.area_app_ha`; `AreaRural` tipo `APP` |
| Área Reserva Legal | Sim | Não | `UnidadeProdutivaCreate.area_rl_ha`; `ImovelRural.area_rl_ha`; `AreaRural` tipo `RESERVA_LEGAL` |

## Etapa 4 - Análise Fundiária

| Item | Classificação | Evidência |
|---|---|---|
| Matrícula | PARCIAL | `MatriculaImovel` em `propriedades` e `numero_matricula` em `imoveis` |
| Cartório | PARCIAL | `Cartorio` existe em `imoveis`; em `propriedades` há campos de matrícula/cartório sem entidade própria |
| CAR | IMPLEMENTADO | `UnidadeProdutivaCreate.codigo_car`, `ImovelRural.car_numero`, `permission-catalog` e UI de propriedades/imóveis |
| CCIR | IMPLEMENTADO | `UnidadeProdutivaCreate.ccir`, `ImovelRural.ccir_numero`, UI e modelos |
| ITR | PARCIAL | Há documentação e tipos de documento, mas não um lifecycle fundiário completo no núcleo de propriedades |
| NIRF | IMPLEMENTADO | `UnidadeProdutivaCreate.nirf` e `ImovelRural.nirf` |
| Georreferenciamento | IMPLEMENTADO | `AreaRural.geometria`, `ImovelRural.geometria`, `coordenadas_sede` |
| Proprietários | INEXISTENTE | Há CPF/CNPJ do responsável, mas não entidade estruturada de proprietário |
| Condôminos | INEXISTENTE | Não há modelo próprio |
| Posse | PARCIAL | `TipoImovel.POSSE` existe no módulo `imoveis` |
| Arrendamento | IMPLEMENTADO | `ContratoArrendamento` e `TipoContrato.ARRENDAMENTO` |
| Parceria Rural | IMPLEMENTADO | `TipoContrato.PARCERIA` |
| Comodato | INEXISTENTE | Não identificado |

## Etapa 5 - Análise Ambiental

| Item | Classificação | Evidência |
|---|---|---|
| APP | IMPLEMENTADO | Tipo `APP` em `AreaRural`; `area_app_ha` em `UnidadeProdutiva` e `ImovelRural` |
| Reserva Legal | IMPLEMENTADO | Tipo `RESERVA_LEGAL`; `area_rl_ha` |
| Nascentes | PARCIAL | Pode ser representado por `dados_extras` e registros ambientais, mas sem entidade oficial |
| Areas Restritas | PARCIAL | Estrutura ambiental e `dados_extras` permitem representar, mas sem modelagem dedicada |
| Licenças Ambientais | PARCIAL | `RegistroAmbiental` e tipos como `LICENCA_IBAMA`, `OUTORGA_AGUA`, `AIA` |
| Certificações | INEXISTENTE | Não há entidade ou fluxo dedicado no módulo analisado |
| ESG | INEXISTENTE | Não há modelagem dedicada no módulo analisado |

## Etapa 6 - Integração com Módulos

| Módulo | Integração | Dependência | Impacto |
|---|---|---|---|
| Agrícola | Direta | Alta | Alto |
| Pecuária | Direta | Média/Alta | Alto |
| Financeiro | Indireta | Média | Alto |
| Compras | Indireta | Média | Médio |
| Estoque | Indireta | Média | Médio |
| Frota | Indireta | Baixa/Média | Médio |
| RH | Indireta | Baixa | Baixo/Médio |
| Ambiental | Direta | Alta | Alto |
| CRM | Indireta ou inexistente | Baixa | Baixo |
| Comercialização | Indireta | Baixa/Média | Médio |
| Hedge | Inexistente | Baixa | Baixo |

Leitura técnica:
- O vínculo mais forte é com Agrícola, Pecuária e Ambiental.
- Financeiro depende da unidade produtiva como base de rateio e contexto, mas não há um centro econômico explícito dentro de propriedades.
- Compras, Estoque e Frota consomem o contexto operacional da fazenda em diversas telas e fluxos.

## Etapa 7 - Estrutura Territorial

### Suporte existente

- Propriedade / Unidade Produtiva
- Glebas
- Talhões
- Pastagens
- Benfeitorias
- Estradas
- Areas de Preservação

### Veredito

**A estrutura territorial é adequada? NÃO**

### Justificativa

- O backend cobre a estrutura mínima: `AREA_RURAL`, `GLEBA`, `TALHAO`, `AREA_OPERACIONAL`, `AREA_AMBIENTAL`, `APP`, `RESERVA_LEGAL` e `INFRAESTRUTURA`.
- O frontend, porém, já usa conceitos como `PASTAGEM` e `PROPRIEDADE` como raiz de árvore, o que indica drift semântico entre interface e backend.
- Não há modelagem oficial explícita para `Estradas`; isso fica implícito em `OUTROS` ou `dados_extras`.
- O modelo ainda está mais próximo de um núcleo operacional do que de um cadastro territorial universal.

## Etapa 8 - Análise Estratégica

### Recomendação

**A) NÃO. Evoluir Propriedades.**

### Justificativa técnica

- Já existe um módulo separado de `Imóveis Rurais` com rotas, modelos, serviços, telas e permissões próprias.
- Criar um novo módulo duplicaria domínio e aumentaria o risco de inconsistência.
- O `data model` oficial trata `Propriedades / Áreas Rurais` como entidade central de domínio operacional, não como um segundo módulo legal.
- O `routing map` e o `sidebar-config` já expõem os dois conceitos de forma separada.
- O banco já contém tabelas e migrações para ambos os mundos. Separar mais um módulo agravaria a fragmentação.

### Avaliação por critério

- Duplicação de domínio: alta
- Violação do Data Model: alta
- Impacto arquitetural: alto
- Impacto no Routing Map: alto
- Impacto no Frontend: alto
- Impacto no Banco: alto

### Leitura final

O problema real não é falta de módulo legal. O problema é fronteira difusa:

- `Propriedades` está absorvendo atributos fundiários e cadastrais.
- `Imóveis Rurais` já cobre o núcleo jurídico-patrimonial.

Portanto, o caminho correto é **refinar responsabilidades**, não criar um terceiro eixo redundante.

## Etapa 9 - Plano de Evolução do Módulo Propriedades

### Prioridade Alta

| Objetivo | Justificativa | Impacto | Complexidade |
|---|---|---|---|
| Normalizar a fronteira entre `Propriedades` e `Imóveis Rurais` | Reduz sobreposição de CAR, CCIR, NIRF, matrícula e documentos | Muito alto | Média |
| Consolidar a propriedade como unidade operacional/territorial | Evita que o módulo vire um segundo cadastro legal | Alto | Média |
| Alinhar UI, sidebar e permissões com o desenho oficial | Remove ambiguidade para usuário e time | Alto | Baixa/Média |

### Prioridade Média

| Objetivo | Justificativa | Impacto | Complexidade |
|---|---|---|---|
| Completar a cobertura cadastral da unidade produtiva | Município, UF, coordenadas, áreas e georreferenciamento precisam ficar consistentes | Alto | Média |
| Expandir a modelagem territorial | Melhor suporte a pastagens, estradas, benfeitorias e áreas ambientais | Alto | Média/Alta |
| Padronizar a árvore territorial entre backend e frontend | Evita drift entre `AreaRural` e a UI | Médio/Alto | Média |

### Prioridade Baixa

| Objetivo | Justificativa | Impacto | Complexidade |
|---|---|---|---|
| Aprofundar metadados ambientais | Nascentes, restrições, certificações e ESG não estão oficiais hoje | Médio | Média/Alta |
| Robustecer geoespacialmente com PostGIS | Melhora precisão e consultas espaciais | Médio | Alta |
| Melhorar relatórios de resumo territorial | Traz visibilidade de área total, produtiva, ambiental e infraestrutura | Médio | Média |

## Conclusão

### Situação atual

O AgroSaaS já possui dois blocos distintos:

- `Propriedades` para cadastro territorial e operacional da fazenda/unidade produtiva.
- `Imóveis Rurais` para o domínio legal, patrimonial e documental.

### Lacunas encontradas

- Sobreposição de dados cadastrais entre `propriedades` e `imoveis`.
- Falta de entidade oficial para proprietário/condômino.
- Cobertura parcial de ITR, matrícula e cartório no eixo `propriedades`.
- Lacunas em nascentes, restrições, certificações e ESG.
- Drift entre frontend e backend na árvore territorial.

### Riscos

- Duplicação de domínio e de manutenção.
- Divergência de fonte de verdade para CAR, NIRF, CCIR e matrícula.
- Confusão de uso para o usuário final.
- Maior custo de evolução do banco, rotas e telas.

### Recomendação arquitetural

- Manter `Propriedades` como unidade operacional/territorial.
- Manter `Imóveis Rurais` como módulo legal/patrimonial separado.
- Não criar um novo módulo adicional chamado `Imóveis Rurais`.
- Priorizar alinhamento semântico e redução de duplicidade.

### Roadmap de evolução

1. Definir fronteiras oficiais de domínio entre `Propriedades` e `Imóveis Rurais`.
2. Padronizar campos cadastrais e remover duplicações desnecessárias.
3. Completar a estrutura territorial e o mapa geoespacial.
4. Evoluir ambiental, documental e patrimonial de forma separada.
5. Revalidar frontend, permissões e documentação após a consolidação.

### Resposta final

**O AgroSaaS deve criar um módulo Imóveis Rurais?**

**Não.** O módulo já existe; a recomendação correta é **evoluir Propriedades** e preservar `Imóveis Rurais` como camada legal/patrimonial distinta.
