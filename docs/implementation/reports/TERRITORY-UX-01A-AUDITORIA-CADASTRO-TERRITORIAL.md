# TERRITORY-UX-01A - Auditoria e Redesenho do Cadastro Territorial

Data da auditoria: 2026-07-17

## 1. Resumo executivo

A tela rotulada como "Propriedades" e o modal "Editar Propriedade" nao editam o model `Propriedade` como entidade principal. O fluxo principal edita `UnidadeProdutiva` na tabela `unidades_produtivas` e, quando ha dados fundiarios no submit, aciona um orquestrador (`CadastroCompletoService`) que pode criar ou atualizar tambem `Propriedade`, `ExploracaoRural`, `ImovelRural` e `PropriedadeImovel`.

O frontend mistura no mesmo formulario:

- dados operacionais da `UnidadeProdutiva`;
- alguns dados cadastrais que semanticamente pertencem a `Propriedade`;
- documentos fundiarios e area oficial que sao tratados via bloco `imovel_rural`;
- geolocalizacao operacional persistida em `UnidadeProdutiva.geometria`;
- leituras derivadas da visao territorial (`territorio.imovel_principal`).

Conclusao objetiva:

- a tela nao e um CRUD puro de `Propriedade`;
- a tela e um cadastro composto centrado em `UnidadeProdutiva`;
- o titulo "Editar Propriedade" esta semanticamente incorreto;
- a UX atual ainda embute premissa pratica de 1:1 com `imovel_principal`;
- as APIs existentes ja permitem reorganizar a experiencia sem alterar backend, desde que a edicao fundiaria saia da tela operacional ou fique apenas leitura.

Veredicto: **GO COM RESSALVAS**

Recomendacao de UX: **OPCAO B - Separacao progressiva**, com tela operacional da `UnidadeProdutiva` e bloco fundiario apenas leitura/linkado para `ImovelRural`, preservando fluxo assistido de cadastro inicial por passos.

## 2. Entidade real da tela

### Tela auditada

- Rota frontend: `/cadastros/propriedades`
- Arquivo da pagina: `apps/web/src/app/(dashboard)/cadastros/propriedades/page.tsx`
- Componente principal: `apps/web/src/app/(dashboard)/cadastros/propriedades/propriedades-client.tsx`
- Modal principal em uso: `PropriedadeDialog` inline no mesmo arquivo
- Componente paralelo nao utilizado: `apps/web/src/components/propriedade/propriedade-dialog.tsx`

### Titulo visual

- Lista: `Propriedades`
- Modal: `Editar Propriedade` / `Nova Propriedade`

### Endpoints GET usados pela tela

- `GET /api/v1/unidades-produtivas`
  - lista base usada para renderizar a grade e abrir edicao
- `GET /api/v1/unidades-produtivas/{id}`
  - usado para hidratar a fazenda ativa e apos create/update
- `GET /api/v1/cadastros/areas-rurais?unidade_produtiva_id={id}`
  - usado para calcular area mapeada e inferencias de fallback
- `GET /api/v1/billing/limits`
  - usado para limite de cadastro

Observacao: ao clicar em editar, nao ha fetch dedicado de `Propriedade`. O modal usa os dados da linha `UnidadeProdutiva`, enriquecidos por `territorio.imovel_principal` quando presentes.

### Endpoints de escrita usados pela tela

- `POST /api/v1/unidades-produtivas/cadastro-completo`
- `PUT /api/v1/unidades-produtivas/{id}/cadastro-completo`
- `DELETE /api/v1/unidades-produtivas/{id}`
- `POST /api/v1/unidades-produtivas/{id}/logo`

### Tipo TypeScript usado

- `CreateCadastroCompletoInput` / `UpdateCadastroCompletoInput` de `packages/zod-schemas/src/fazenda-schemas.ts`
- `UnidadeProdutiva` de `apps/web/src/types/global.d.ts`
- overlay de leitura: `territorio?: TerritoryReadView`

### Schema backend usado

- Router: `services/api/core/routers/unidades_produtivas.py`
- Input: `CadastroCompletoCreate` / `CadastroCompletoUpdate`
- Output: `UnidadeProdutivaResponse`

### Model ORM persistido

Entidade principal persistida:

- `core.models.unidade_produtiva.UnidadeProdutiva`

Entidades orquestradas condicionalmente:

- `core.cadastros.propriedades.propriedade_models.Propriedade`
- `core.cadastros.propriedades.propriedade_models.ExploracaoRural`
- `imoveis.models.imovel.ImovelRural`
- `core.cadastros.propriedade_imovel.models.PropriedadeImovel`

### Tabelas fisicas alteradas

- principal: `unidades_produtivas`
- adicionais condicionais:
  - `cadastros_propriedades`
  - `cadastros_exploracoes_rurais`
  - `imoveis_rurais`
  - `propriedade_imovel`

### Resposta objetiva

A tela edita:

- Propriedade? **PARCIAL**
- UnidadeProdutiva? **SIM**
- ImovelRural? **PARCIAL**
- CadastroCompleto? **SIM**
- uma composicao de varias entidades? **SIM**

Definicao mais precisa:

> A tela atual e um cadastro composto centrado em `UnidadeProdutiva`, com persistencia adicional opcional em `ImovelRural` e vinculo `PropriedadeImovel`, e com criacao/atualizacao implicita de `Propriedade` e `ExploracaoRural` via `CadastroCompletoService`.

## 3. Rota e componentes

### Arquivos principais auditados

- `apps/web/src/app/(dashboard)/cadastros/propriedades/page.tsx`
- `apps/web/src/app/(dashboard)/cadastros/propriedades/propriedades-client.tsx`
- `apps/web/src/app/(dashboard)/cadastros/propriedades/[id]/page.tsx`
- `apps/web/src/app/(dashboard)/cadastros/propriedades/[id]/propriedade-detalhe-client.tsx`
- `apps/web/src/components/territorial/territorial-visao.tsx`
- `apps/web/src/lib/hooks/use-territorial-visao.ts`
- `apps/web/src/lib/sidebar-config.ts`
- `apps/web/src/app/(dashboard)/cadastros/page.tsx`
- `apps/web/src/components/propriedade/propriedade-dialog.tsx` (paralelo legado/nao utilizado)

### Fluxo visual atual

1. Usuario entra em `/cadastros/propriedades`
2. Lista e metricas carregam `UnidadeProdutiva[]`
3. A coluna CAR e o modal leem `row.territorio?.imovel_principal`
4. O modal envia `unidade_produtiva` sempre
5. O modal envia `imovel_rural` apenas se houver documentos fundiarios preenchidos ou alteracao de area que exija justificativa
6. Se existir associacao principal conhecida, envia tambem `propriedade_imovel.id`

## 4. Endpoints

| Finalidade | Endpoint | Metodo | Observacao |
|---|---|---|---|
| Listagem operacional | `/api/v1/unidades-produtivas` | GET | Fonte principal da tela |
| Detalhe operacional | `/api/v1/unidades-produtivas/{id}` | GET | Retorna `territorio` por overlay |
| Areas da UP | `/api/v1/cadastros/areas-rurais?unidade_produtiva_id={id}` | GET | Base da area calculada/mapeada |
| Criacao composta | `/api/v1/unidades-produtivas/cadastro-completo` | POST | Cria UP e pode criar Propriedade/Exploracao/Imovel/Vinculo |
| Atualizacao composta | `/api/v1/unidades-produtivas/{id}/cadastro-completo` | PUT | Atualiza UP e pode atualizar Imovel/Vinculo |
| Exclusao | `/api/v1/unidades-produtivas/{id}` | DELETE | Exclui UP |
| Visao territorial read-only | `/api/v1/propriedades/{id}/visao-territorial` | GET | Ja existe e suporta separacao de UX |
| Visao fundiaria read-only | `/api/v1/imoveis-rurais/{id}/visao-fundiaria` | GET | Ja existe e suporta separacao de UX |

## 5. Matriz campo -> dominio

| Campo visual | Componente | Payload | Schema backend | Model | Tabela | Significado atual | Dominio correto |
|---|---|---|---|---|---|---|---|
| Nome | `Input register("nome")` | `unidade_produtiva.nome` | `UnidadeProdutivaCreate/Update` | `UnidadeProdutiva` | `unidades_produtivas` | Nome operacional exibido como propriedade | UNIDADE_PRODUTIVA |
| Tipo | `Select tipo_propriedade` | `unidade_produtiva.tipo_propriedade` | idem | `UnidadeProdutiva` | `unidades_produtivas` | Tipo de fazenda/sitio/chacara no contexto operacional | UNIDADE_PRODUTIVA |
| CPF/CNPJ | `Input cpf_cnpj` | `unidade_produtiva.cpf_cnpj` | idem | `UnidadeProdutiva` | `unidades_produtivas` | Documento cadastral acoplado a UP | AMBIGUO |
| Inscricao Estadual | `Input inscricao_estadual` | `unidade_produtiva.inscricao_estadual` | idem | `UnidadeProdutiva` | `unidades_produtivas` | Dado fiscal/cadastral acoplado a UP | AMBIGUO |
| CEP | `Input cep` | `unidade_produtiva.cep` | idem | `UnidadeProdutiva` | `unidades_produtivas` | Endereco da sede/operacao | UNIDADE_PRODUTIVA |
| Logradouro | `Input logradouro` | `unidade_produtiva.logradouro` | idem | `UnidadeProdutiva` | `unidades_produtivas` | Endereco da sede/operacao | UNIDADE_PRODUTIVA |
| Numero | `Input numero` | `unidade_produtiva.numero` | idem | `UnidadeProdutiva` | `unidades_produtivas` | Endereco da sede/operacao | UNIDADE_PRODUTIVA |
| Complemento | `Input complemento` | `unidade_produtiva.complemento` | idem | `UnidadeProdutiva` | `unidades_produtivas` | Endereco da sede/operacao | UNIDADE_PRODUTIVA |
| Bairro/Distrito | `Input bairro` | `unidade_produtiva.bairro` | idem | `UnidadeProdutiva` | `unidades_produtivas` | Endereco da sede/operacao | UNIDADE_PRODUTIVA |
| Municipio | `Input municipio` | `unidade_produtiva.municipio` | idem | `UnidadeProdutiva` | `unidades_produtivas` | Municipio operacional; tambem usado como fallback de imovel | AMBIGUO |
| UF | `Input uf` | `unidade_produtiva.uf` | idem | `UnidadeProdutiva` | `unidades_produtivas` | UF operacional; tambem usada como fallback de imovel | AMBIGUO |
| Codigo IBGE | `Input ibge_municipio_codigo` | `unidade_produtiva.ibge_municipio_codigo` | idem | `UnidadeProdutiva` | `unidades_produtivas` | Codigo do municipio da sede | UNIDADE_PRODUTIVA |
| Area informada | `Input area_total_ha` | `unidade_produtiva.area_total_ha` | idem | `UnidadeProdutiva` | `unidades_produtivas` | Area declarada pelo usuario na UP; tambem fallback para novo imovel | AMBIGUO |
| Area calculada | `Input disabled` | nao enviado diretamente | `UnidadeProdutivaResponse.area_total_calculada_ha` | `UnidadeProdutiva` | `unidades_produtivas` | Calculada a partir de `UnidadeProdutiva.geometria`; frontend tambem mostra area derivada de `AreaRural` em outras metricas | DERIVADO |
| APP | `Input area_app_ha` | `unidade_produtiva.area_app_ha` | idem | `UnidadeProdutiva` | `unidades_produtivas` | Referencia operacional na UP; pode influenciar imovel quando ha update composto | AMBIGUO |
| Reserva Legal | `Input area_rl_ha` | `unidade_produtiva.area_rl_ha` | idem | `UnidadeProdutiva` | `unidades_produtivas` | Referencia operacional na UP; pode influenciar imovel quando ha update composto | AMBIGUO |
| CAR | `Input codigo_car` | `imovel_rural.car_numero` | `CadastroCompletoImovelInput` | `ImovelRural` | `imoveis_rurais` | Documento fundiario exibido dentro da tela operacional | IMOVEL_RURAL |
| NIRF | `Input nirf` | `imovel_rural.nirf` | idem | `ImovelRural` | `imoveis_rurais` | Documento fundiario | IMOVEL_RURAL |
| CCIR | `Input ccir` | `imovel_rural.ccir_numero` | idem | `ImovelRural` | `imoveis_rurais` | Documento fundiario | IMOVEL_RURAL |
| SIGEF | `Input sigef_codigo` | `imovel_rural.sigef_codigo` | idem | `ImovelRural` | `imoveis_rurais` | Documento fundiario | IMOVEL_RURAL |
| Matricula | `Input numero_matricula` | `imovel_rural.numero_matricula` | idem | `ImovelRural` | `imoveis_rurais` | Documento fundiario | IMOVEL_RURAL |
| Latitude | `Input local state` | `unidade_produtiva.coordenadas_sede` | `UnidadeProdutivaCreate/Update` | `UnidadeProdutiva` | `unidades_produtivas` | Coordenada da sede/point manual | UNIDADE_PRODUTIVA |
| Longitude | `Input local state` | `unidade_produtiva.coordenadas_sede` | idem | `UnidadeProdutiva` | `unidades_produtivas` | Coordenada da sede/point manual | UNIDADE_PRODUTIVA |
| Logo | upload button | `POST /unidades-produtivas/{id}/logo` | n/a | `UnidadeProdutiva` | `unidades_produtivas` | Identidade visual da operacao | UNIDADE_PRODUTIVA |
| Status | `Switch ativo` | `unidade_produtiva.ativo` | idem | `UnidadeProdutiva` | `unidades_produtivas` | Status operacional | UNIDADE_PRODUTIVA |
| Geolocalizacao | `PropertyGeolocationDialog` | `unidade_produtiva.geometria` | idem | `UnidadeProdutiva` | `unidades_produtivas` | Perimetro da unidade produtiva | UNIDADE_PRODUTIVA |
| Area util estimada | calculada no client | nao enviado | n/a | n/a | n/a | `area_total_ha - APP - RL` | DERIVADO |

### Campos visuais ausentes do payload principal, mas visiveis em telas relacionadas

| Campo visual | Local | Significado atual | Dominio correto |
|---|---|---|---|
| Area aproveitavel | `propriedade-detalhe-client.tsx` | campo legado ainda exibido no detalhe; nao existe em `UnidadeProdutivaResponse` | LEGADO |

## 6. Origem dos documentos fundiarios

### De onde esses valores sao carregados

Na edicao:

- `codigo_car`, `nirf`, `ccir`, `sigef_codigo`, `numero_matricula` sao preenchidos a partir de `fazenda.territorio?.imovel_principal`
- a listagem tambem mostra CAR via `row.territorio?.imovel_principal?.car_numero`

Na leitura da UP:

- o backend injeta `territorio` com `TerritoryReadService`
- `territorio.imovel_principal` e resolvido a partir de `PropriedadeImovel` ativo e `vinculo_principal`

### Para onde sao enviados

No submit:

- a UI envia bloco `imovel_rural` somente se houver documentos ou alteracao de area com justificativa
- esse bloco vai para `CadastroCompletoService._resolver_imovel`

### Se fazem parte do payload da UP

- nao fazem parte do bloco `unidade_produtiva`
- fazem parte do payload composto `cadastro-completo`
- continuam, porem, sendo mostrados como se fossem atributos da "propriedade" operacional

### Se estao em bloco `imovel_rural`

- sim
- mapeamento atual:
  - `codigo_car` -> `imovel_rural.car_numero`
  - `ccir` -> `imovel_rural.ccir_numero`
  - `nirf` -> `imovel_rural.nirf`
  - `sigef_codigo` -> `imovel_rural.sigef_codigo`
  - `numero_matricula` -> `imovel_rural.numero_matricula`

### Se o backend os normaliza

- sim
- `CadastroCompletoInput` ainda aceita aliases legados e normaliza:
  - `codigo_car` -> `car_numero`
  - `ccir` -> `ccir_numero`

### Se criam ou atualizam `ImovelRural`

- sim
- se `imovel_rural.id` vier no payload, atualiza o imovel indicado
- se houver `propriedade_imovel.id`, resolve o imovel do vinculo
- se houver um unico vinculo principal ativo da propriedade, atualiza esse imovel
- se nao houver imovel resolvido, cria novo `ImovelRural`

### Se usam o imovel principal

- sim, por padrao de UI
- a interface so conhece `territorio.imovel_principal`

### Se utilizam `CadastroCompletoService`

- sim, sempre que o modal salva

### Se apenas aparecem por compatibilidade

- nao apenas
- eles sao exibidos por compatibilidade de leitura, mas tambem podem disparar escrita fundiaria real

### Se o usuario pode gerar divergencia

- sim
- porque a tela operacional permite editar documento fundiario sem expor claramente qual `ImovelRural` sera alterado

### Respostas objetivas

1. A tela grava diretamente em ImovelRural? **SIM, via orquestrador**
2. A tela cria um imovel automaticamente? **SIM**
3. A tela atualiza o imovel principal? **SIM, quando resolvido**
4. A tela assume que existe apenas um imovel? **PARCIAL, na UX sim**
5. O usuario consegue selecionar qual imovel sera alterado? **NAO**
6. O usuario percebe que esta alterando outra entidade? **NAO**
7. O fluxo e compativel com Propriedade N:N ImovelRural? **PARCIAL, backend sim; UX nao**

## 7. Comportamento do CadastroCompleto

### Criacao

`POST /unidades-produtivas/cadastro-completo`

1. cria `UnidadeProdutiva`
2. resolve ou cria `Propriedade`
3. resolve ou cria `ExploracaoRural`
4. resolve, atualiza ou cria `ImovelRural` se houver bloco `imovel_rural`
5. garante `PropriedadeImovel` se houver imovel

### Atualizacao

`PUT /unidades-produtivas/{id}/cadastro-completo`

1. atualiza `UnidadeProdutiva`
2. resolve `Propriedade`
3. resolve `ExploracaoRural`
4. resolve `ImovelRural` se houver bloco `imovel_rural`
5. resolve `PropriedadeImovel`

### Regras relevantes

- se houver multiplos vinculos ativos e a UI nao informar `imovel_rural.id` ou `propriedade_imovel.id`, o service pode falhar com erro de ambiguidade
- se nao houver imovel vinculado e o usuario preencher documentos, o service cria um novo `ImovelRural`
- `_payload_imovel()` usa fallbacks de `UnidadeProdutiva` para `nome`, `municipio`, `uf` e `area_total_ha`

Implicacao:

> O cadastro completo e tecnicamente composto, mas a UX nao separa os limites entre o que e operacional, o que e cadastral produtivo e o que e fundiario oficial.

## 8. Analise do aviso de convergencia

### Texto atual

> "Convergencia Territorial: Dados fundiarios informados serao vinculados automaticamente ao Imovel Rural correspondente na base oficial documental para consolidacao territorial e compliance ESG."

### Componente que renderiza

- `apps/web/src/app/(dashboard)/cadastros/propriedades/propriedades-client.tsx`
- dentro do bloco `Documentacao`

### Condicao de exibicao

- exibicao incondicional dentro do modal
- nao depende de haver 0, 1 ou N imoveis

### Fluxo backend correspondente

- `CadastroCompletoService._resolver_imovel()`
- `CadastroCompletoService._resolver_vinculo()`
- `TerritoryReadService` para leitura de `imovel_principal`

### Regra usada para encontrar o "imovel correspondente"

Ordem pratica:

1. `imovel_rural.id` explicito no payload
2. `propriedade_imovel.id` explicito no payload
3. unico `vinculo_principal` ativo da propriedade
4. se nao houver, tenta criar novo `ImovelRural`
5. se houver multiplos ativos sem principal unico, erro de ambiguidade

### Comportamento por cenario

- quando existe um imovel principal: atualiza esse imovel
- quando nao existe imovel: cria novo imovel e vinculo
- quando ha varios imoveis e um principal unico: atualiza o principal
- quando ha varios imoveis sem principal unico: erro e a UX nao oferece solucao
- em edicoes posteriores: continua reaplicando a logica acima
- sobrescrita: possivel para documentos e area quando o bloco `imovel_rural` e enviado

### Classificacao do aviso

**PARCIALMENTE_CORRETA**, com risco de ser **PERIGOSA** em cenarios N:N.

Justificativa:

- correta ao dizer que existe vinculacao automatica;
- incompleta porque nao informa qual imovel sera afetado;
- enganosa para propriedades com multiplos imoveis;
- omite que pode haver criacao automatica de novo `ImovelRural`;
- omite que o usuario nao escolhe explicitamente o alvo.

## 9. Analise de areas

### Area informada

- origem fisica: `UnidadeProdutiva.area_total_ha`
- unidade: hectares
- editavel: sim
- entidade persistida: `UnidadeProdutiva`
- consumidores:
  - listagem de propriedades
  - metricas do dashboard da tela
  - fallback para criacao/atualizacao de `ImovelRural`
  - detalhe da propriedade
- uso em custos/produtividade: indireto e ambiguo, pois a propria UI avisa que calculos devem considerar `AreaRural`

Classificacao: **indefinida / agregada com uso operacional**

### Area calculada

- origem fisica primaria da persistencia: `UnidadeProdutiva.area_total_calculada_ha`
- formula persistida: calculada a partir de `UnidadeProdutiva.geometria`
- formula visual adicional na tela: a listagem compara tambem com soma de `AreaRural` raiz via `/cadastros/areas-rurais`
- editavel: nao
- entidade persistida: `UnidadeProdutiva`
- consumidores:
  - modal
  - detalhe
  - metricas de estrutura

Classificacao: **geometria da UP**, nao soma de imoveis nem formula fundiaria oficial.

### APP e Reserva Legal

- origem atual do formulario: `UnidadeProdutiva.area_app_ha` e `UnidadeProdutiva.area_rl_ha`
- podem ser refletidas no `ImovelRural` quando o fluxo composto atualiza o imovel principal por campos compartilhados
- a visao fundiaria oficial tambem possui `ImovelRural.area_app_ha` e `ImovelRural.area_rl_ha`

Classificacao:

- fonte oficial do `ImovelRural` existe: **SIM**
- a tela operacional usa copia/duplicata de referencia na UP: **SIM**
- resultado auditado: **dado duplicado/ambiguo**

### Area util estimada

- origem: calculo client-side `area_total_ha - APP - RL`
- persistencia: nenhuma
- classificacao: **DERIVADO**

### Observacao operacional importante

A propria tela exibe aviso:

> "Valores referenciais. Para calculos, considere os valores no cadastro de cada Area Rural."

Isso confirma que os numeros da tela atual nao sao a fonte mais confiavel para operacao territorial detalhada.

## 10. Analise de endereco

Endereco atual representa, na pratica:

- sede operacional / endereco postal da `UnidadeProdutiva`

Evidencias:

- todos os campos persistem em `unidades_produtivas`
- o dialogo de geolocalizacao fala explicitamente em "Unidade Produtiva"
- `coordenadas_sede` e `geometria` pertencem a UP

Nao ha evidencia de que estes campos representem:

- endereco oficial do `ImovelRural`
- endereco fiscal fundiario
- cartorio
- centroides legais do imovel

Classificacao:

- endereco atual = **UNIDADE_PRODUTIVA**

## 11. Analise de localizacao

### Latitude/Longitude

- persistencia: `UnidadeProdutiva.coordenadas_sede`
- forma: string `"lat,lng"`
- semantica atual: ponto digitado/manual da sede operacional

Possivel reflexo fundiario:

- existe metodo `_sincronizar_imovel_principal_com_unidade()` que pode copiar coordenadas para `ImovelRural.latitude/longitude`
- porem a UX nao explicita isso

Classificacao:

- latitude/longitude atual = **ponto da sede operacional**

### Geolocalizacao

- componente: `PropertyGeolocationDialog`
- persistencia: `UnidadeProdutiva.geometria`
- rotulo textual do proprio componente:
  - "Geolocalizacao da Unidade Produtiva"
  - "Desenhe o perimetro da unidade produtiva"
  - "A area calculada e da fazenda inteira e nao da area operacional dos talhoes"

Classificacao:

- geometria atual = **operacional**

Risco:

- pode conflitar conceitualmente com `ImovelRural.geometria` se o usuario interpretar o poligono como limite legal do imovel

## 12. Linguagem da interface

### Como o produto nomeia o mesmo espaco

Labels auditados:

- `Propriedades`
- `Editar Propriedade`
- `Nova Propriedade`
- `Fazendas`
- `Fazendas & Unidades`
- `Minha Propriedade`
- `Cadastro legal`
- `Imoveis Rurais`
- `Visao Territorial`
- `Visao Fundiaria`
- `Produtores`

### Leitura provavel do usuario

No estado atual, "Propriedade" tende a significar:

- fazenda operacional;
- unidade produtiva do tenant;
- lugar onde a safra acontece;
- em alguns pontos, tambem o imovel legal.

Isso gera quatro choques semanticos:

1. menu chama `Propriedades`, mas CRUD real e de `UnidadeProdutiva`
2. permissao usa `tenant:fazendas`
3. catalogo de cadastros tambem exibe `Fazendas & Unidades`
4. documentos fundiarios aparecem no mesmo formulario operacional

Conclusao:

> O usuario nao recebe fronteira clara entre operacao agropecuaria, propriedade operacional e imovel rural oficial.

## 13. Alternativas de UX

| Opcao | Impacto no usuario | Impacto no piloto | Impacto backend | Impacto frontend | Compatibilidade | Risco de divergencia | Esforco | Recomendacao |
|---|---|---|---|---|---|---|---|---|
| A - Separacao imediata | Mudanca brusca, mas clara | Pode exigir ajuste de treinamento | Nenhum ou minimo | Medio | Alta | Baixo | Medio | Boa, mas mais agressiva |
| B - Separacao progressiva | Baixo atrito | Melhor para piloto | Nenhum | Medio | Alta | Medio/Baixo | Medio | **Recomendada** |
| C - Cadastro assistido composto | Boa para onboarding operacional | Muito boa se bem guiada | Nenhum se reutilizar APIs atuais | Medio/Alto | Alta | Medio | Medio/Alto | Recomendada como fase 02 |
| D - Manter como esta | Zero friccao imediata | Curto prazo facil | Nenhum | Nenhum | Baixa com N:N | Alto | Baixo | Nao recomendada |

### Leitura

- **Opcao B** resolve a confusao sem travar o piloto.
- **Opcao C** e adequada como fluxo inicial assistido, mas nao como edicao permanente no mesmo formulario misto.

## 14. Opcao recomendada

**OPCAO B - Separacao progressiva**

Proposta:

1. transformar a tela atual em `Editar Unidade Produtiva / Operacao`
2. remover a edicao direta de documentos fundiarios do formulario operacional
3. manter card de leitura do `imovel_principal` e dos `imoveis vinculados`
4. incluir acoes:
   - `Abrir Imovel Rural`
   - `Vincular imovel`
   - `Cadastrar novo imovel`
   - `Ver visao territorial`
5. reutilizar:
   - `GET /propriedades/{id}/visao-territorial`
   - `GET /imoveis-rurais/{id}/visao-fundiaria`
   - `GET /unidades-produtivas/{id}`
   - endpoints existentes de `ImoveisClient`

Ressalva:

- para criacao inicial do piloto, preservar um fluxo assistido em passos curtos, mas nao manter os documentos fundiarios como bloco editavel indistinto da operacao.

## 15. Wireframes textuais

### Tela A - Editar Unidade Produtiva / Operacao

```text
EDITAR UNIDADE PRODUTIVA

[Identificacao Operacional]
- Nome operacional
- Tipo
- CPF/CNPJ (se confirmado como dado da UP)
- Inscricao estadual (se confirmado como dado da UP)

[Endereco da Sede]
- CEP
- Logradouro
- Numero
- Complemento
- Bairro/Distrito
- Municipio
- UF
- Codigo IBGE

[Localizacao Operacional]
- Latitude da sede
- Longitude da sede
- [Abrir geolocalizacao]
- Area calculada pela geometria

[Indicadores Operacionais]
- Area informada
- Area calculada
- APP operacional de referencia
- Reserva legal de referencia
- Status
- Logo

[Imoveis vinculados]
- Imovel principal
  Matricula: ...
  CAR: ...
  Municipio oficial: ...
  Status documental: ...
  [Abrir imovel]

- Outros imoveis vinculados
  [Abrir]

[Acoes]
[+ Vincular imovel]
[+ Cadastrar novo imovel]
[Ver visao territorial]
```

### Tela B - Propriedade

```text
PROPRIEDADE

[Dados da Propriedade]
- Nome
- Dados cadastrais proprios
- Observacoes

[Exploracoes vinculadas]
- Unidade Produtiva
- Natureza
- Vigencia

[Imoveis vinculados]
- Lista de vinculos N:N
- Principal
- Tipo de vinculo
- Area vinculada
- Percentual vinculado
- Status documental
- [Abrir imovel]
- [Definir principal]
- [Vincular imovel]
```

### Tela C - Imovel Rural

```text
IMOVEL RURAL

[Identificacao Legal]
- Nome
- Municipio oficial
- UF oficial
- Matricula
- Cartorio
- CAR
- CCIR
- NIRF/CIB
- SIGEF

[Areas Oficiais]
- Area total oficial
- APP oficial
- Reserva Legal oficial

[Geometria Oficial]
- Poligono do imovel

[Documentos]
- Lista documental

[Vinculos Operacionais]
- Propriedades vinculadas
- Tipo de vinculo
- Principalidade
- Area vinculada
```

### Tela D - Imoveis Vinculados dentro da visao da Propriedade

```text
IMOVEIS VINCULADOS

- Fazenda Santa Clara
  Matricula: ...
  CAR: ...
  Area oficial: ...
  Tipo de vinculo: ...
  Principal: Sim/Nao
  [Abrir imovel] [Editar vinculo]

[+ Vincular imovel existente]
[+ Cadastrar novo imovel]
```

## 16. Impacto no piloto

O piloto nao deve reabrir onboarding de assinatura, mas precisa continuar permitindo:

1. cadastrar a operacao
2. informar a sede
3. cadastrar ou selecionar um `ImovelRural`
4. informar documentos oficiais
5. vincular o imovel a `Propriedade`
6. cadastrar areas e talhoes
7. iniciar a operacao

Recomendacao pratica para o piloto:

- cadastro assistido em **etapas** dentro do fluxo de `cadastros/propriedades`
- sem alterar backend
- com passos:
  1. Unidade Produtiva
  2. Imovel Rural
  3. Vinculo Propriedade-Imovel
  4. Areas e Talhoes

Isso reduz friccao sem perpetuar o formulario misto.

## 17. APIs reutilizaveis

Pode ser feito apenas no frontend? **SIM, com ressalvas**

APIs suficientes ja existentes:

- `GET /unidades-produtivas`
- `GET /unidades-produtivas/{id}`
- `POST /unidades-produtivas/cadastro-completo`
- `PUT /unidades-produtivas/{id}/cadastro-completo`
- `GET /cadastros/areas-rurais?unidade_produtiva_id={id}`
- `GET /propriedades/{id}/visao-territorial`
- `GET /imoveis-rurais/{id}/visao-fundiaria`
- endpoints do modulo `Imoveis Rurais` ja consumidos por `ImoveisClient`

Conclusao:

- nao ha necessidade comprovada de novo endpoint agregado nesta fase
- a reorganizacao pode reaproveitar `VisaoTerritorial`, `VisaoFundiaria` e o CRUD atual da UP

## 18. Arquivos potencialmente afetados

### Frontend

- `apps/web/src/app/(dashboard)/cadastros/propriedades/propriedades-client.tsx`
- `apps/web/src/app/(dashboard)/cadastros/propriedades/[id]/propriedade-detalhe-client.tsx`
- `apps/web/src/components/territorial/territorial-visao.tsx`
- `apps/web/src/lib/hooks/use-territorial-visao.ts`
- `apps/web/src/lib/sidebar-config.ts`
- `apps/web/src/app/(dashboard)/cadastros/page.tsx`
- `apps/web/src/types/global.d.ts`
- `apps/web/src/components/propriedade/propriedade-dialog.tsx` (se for removido ou reconciliado)

### Backend reutilizado, sem necessidade de mudanca nesta fase

- `services/api/core/routers/unidades_produtivas.py`
- `services/api/core/services/cadastro_completo_service.py`
- `services/api/core/services/unidade_produtiva_service.py`
- `services/api/core/services/territory_read_service.py`
- `services/api/core/cadastros/propriedade_imovel/visao_service.py`
- `services/api/core/cadastros/propriedades/visao_router.py`
- `services/api/imoveis/visao_router.py`

## 19. Testes planejados

### Fluxos operacionais

- UP sem imovel vinculado mostra card vazio e CTA para vincular
- UP com um imovel mostra leitura correta do principal sem editar documento
- edicao da sede nao altera documento fundiario
- edicao da geometria operacional nao altera geometria oficial do imovel
- mobile: cards e CTAs de vinculo/documentacao permanecem acessiveis

### Fluxos fundiarios

- Propriedade com varios imoveis lista todos os vinculos
- imovel vinculado a varias propriedades continua navegavel pela visao fundiaria
- multiplos imoveis sem principal nao quebram a tela; exibem estado ambiguo com CTA explicito
- usuario sem permissao fundiaria ve somente leitura ou CTA bloqueado
- imovel com documentacao incompleta mostra status documental sem editar pela tela operacional

### Areas

- area calculada operacional usa `UnidadeProdutiva.geometria`
- area operacional detalhada continua vindo de `AreaRural`
- APP/RL oficiais permanecem na visao fundiaria
- APP/RL operacionais, se mantidos, ficam marcados como referenciais

### PWA / Campo

- validar se `apps/campo` nao depende do texto/rota atual de "Propriedade"
- se houver consumo de labels compartilhados, cobrir regressao de nomenclatura

## 20. Veredicto

**GO COM RESSALVAS**

Justificativa:

- a arquitetura atual e as APIs existentes suportam a separacao correta de UX;
- o backend ja distingue `UnidadeProdutiva`, `Propriedade`, `ImovelRural` e `PropriedadeImovel`;
- o problema principal esta na fronteira de experiencia e linguagem;
- ha ambiguidade residual em area, APP/RL, endereco/municipio/UF e em documentos fundiarios dentro do formulario operacional;
- a UX atual ainda esconde uma premissa de principalidade/imovel unico ao usuario.

## 21. Checklist final

- A tela edita Propriedade? **PARCIAL**
- A tela edita UnidadeProdutiva? **SIM**
- A tela edita ImovelRural? **PARCIAL**
- O titulo da tela esta correto? **NAO**
- Documentos fundiarios podem ser removidos da tela operacional? **SIM**
- APP e RL possuem fonte oficial definida? **PARCIAL**
- Area informada possui semantica clara? **NAO**
- Area calculada possui formula comprovada? **SIM**
- Geometria atual e operacional ou fundiaria? **OPERACIONAL**
- O aviso de convergencia e correto? **PARCIAL**
- Ha premissa 1:1 escondida? **SIM**
- A interface suporta N:N? **NAO**
- Endpoints existentes sao suficientes? **SIM**
- Sera necessaria alteracao backend? **NAO**, para a reorganizacao frontend recomendada
- Melhor opcao de UX: **OPCAO B - Separacao progressiva**
- Proxima fase recomendada: **TERRITORY-UX-01B - Implementacao frontend da separacao operacional/fundiaria com cadastro assistido**

## 22. Validacoes executadas

- `git diff --check` -> sem erros de whitespace
- `git status --short` -> workspace ja estava sujo; nenhuma alteracao foi revertida
- buscas completas executadas para:
  - `Editar Propriedade`
  - `Convergência Territorial`
  - `Dados fundiários`
  - `area_total_ha`
  - `area_app_ha`
  - `area_rl_ha`
  - `codigo_car`
  - `car_numero`
  - `nirf`
  - `ccir`
  - `sigef`
  - `numero_matricula`
  - `coordenadas_sede`
  - `geometria`
  - `CadastroCompleto`
  - `sincronizar_imovel_principal`

