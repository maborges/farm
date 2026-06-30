# RC-01C — AUDITORIA DE FORNECEDOR: PESSOA × FORNECEDOR

## 1. Resumo executivo

A codebase atual nao trata `Fornecedor` como entidade totalmente independente, mas tambem nao opera de ponta a ponta apenas com `Pessoa`.

As evidencias encontradas mostram uma arquitetura de transicao:

- `Pessoa` ja existe como base canônica para fornecedores em `services/api/core/cadastros/pessoas/`.
- o modulo de compras possui `Fornecedor` em `compras_fornecedores`, com `pessoa_id` opcional e campos proprios comerciais.
- o CRUD de fornecedor em compras chama `salvar_fornecedor_legado()`, que resolve ou cria `Pessoa` e garante o papel `FORNECEDOR`.
- cotacoes, pedidos e analytics de compras continuam operando majoritariamente por `fornecedor_nome` textual.
- financeiro aceita `pessoa_id`, mas ainda mantem `fornecedor` texto livre por compatibilidade.
- estoque e recebimento preservam rastreabilidade textual do fornecedor em formularios e notas.

Conclusao objetiva:

- a arquitetura encontrada e `Modelo D`: `Fornecedor` funciona como wrapper operacional de `Pessoa`, mantendo metadados especificos de compras;
- para a versao 1.0, a evidencia recomenda `Opcao D`: criar antes uma camada canônica de resolucao de fornecedor para preservar compatibilidade com Compras, Estoque, Financeiro e dados legados.

## 2. Inventario

| Conceito | Model/Tabela | Owner | FK para Pessoa? | Dados duplicados? | Uso | Risco |
| --- | --- | --- | ---: | ---: | --- | --- |
| Pessoa | `Pessoa` / `cadastros_pessoas` | Core Cadastros | N/A | N/A | Cadastro mestre de pessoas e organizacoes | Medio |
| TipoRelacionamento | `TipoRelacionamento` / `cadastros_tipos_relacionamento` | Core Cadastros | N/A | Nao | Catalogo de papeis, inclui `FORNECEDOR` | Baixo |
| PessoaRelacionamento | `PessoaRelacionamento` / `cadastros_pessoa_relacionamentos` | Core Cadastros | N/A | Nao | Papel `FORNECEDOR` por pessoa | Medio |
| Fornecedor | `Fornecedor` / `compras_fornecedores` | Compras | Sim, opcional no model | Sim | Cadastro operacional de fornecedor | Alto |
| SolicitacaoCompra | `SolicitacaoCompra` / `compras_solicitacoes` | Compras | Nao | Nao | Gatilho de cotacao e pedido | Medio |
| CotacaoCompra | `CotacaoCompra` / `compras_cotacoes` | Compras | Nao | Sim | Cotacoes por `fornecedor_nome` | Alto |
| PedidoCompra | `PedidoCompra` / `compras_pedidos` | Compras | Nao | Sim | Pedido operacional por `fornecedor_nome` | Alto |
| CotacaoFornecedor | `CotacaoFornecedor` / `compras_pedidos_cotacoes` | Compras | Indireta via `fornecedor_id` | Nao | Resposta de fornecedor vinculada ao cadastro operacional | Medio |
| RecebimentoParcial | `RecebimentoParcial` / `compras_recebimentos` | Compras | Nao | Nao | Entrada de compra e NF | Medio |
| DevolucaoFornecedor | `DevolucaoFornecedor` / `compras_devolucoes` | Compras | Indireta via `fornecedor_id` | Nao | Reversao operacional | Medio |
| Despesa | `Despesa` / `fin_despesas` | Financeiro | Sim, opcional | Sim | Contas a pagar com `pessoa_id` ou `fornecedor` textual | Alto |
| Estoque recebimento | `ItemRecebimento.numero_lote_fornecedor` + formularios | Estoque/Compras | Nao | Parcial | Rastreabilidade de lote e NF | Medio |
| Fornecedor textual em estoque | formulario web de entrada | Estoque Web | Nao | Sim | Entrada manual de estoque | Alto |

## 3. Models

### 3.1 `Pessoa`, `TipoRelacionamento` e `PessoaRelacionamento`

Arquivo: `services/api/core/cadastros/pessoas/models.py`

Evidencias principais:

- `Pessoa` e descrita como entidade central;
- a docstring afirma explicitamente que papeis como fornecedor ficam em `PessoaRelacionamento`;
- `TipoRelacionamento.codigo` aceita `FORNECEDOR`;
- `PessoaRelacionamento` e o pivot entre pessoa e papel.

Leitura arquitetural:

- o desenho mestre do dominio ja posiciona `Pessoa` como base canônica;
- `FORNECEDOR` ja existe formalmente como papel, nao como conceito externo ao dominio de pessoas.

### 3.2 `Fornecedor`

Arquivo: `services/api/operacional/models/compras.py`

Evidencias:

- tabela `compras_fornecedores`
- campos:
  - `nome_fantasia`
  - `razao_social`
  - `cnpj_cpf`
  - `pessoa_id` nullable
  - `email`
  - `telefone`
  - `condicoes_pagamento`
  - `prazo_entrega_dias`
  - `avaliacao`

Leitura arquitetural:

- `Fornecedor` mantem dados que tambem cabem em `Pessoa`, `PessoaDocumento` e `PessoaContato`;
- ao mesmo tempo, concentra metadados de compras como prazo, condicoes e avaliacao;
- nao e apenas uma tabela espelho vazia, nem um master data isolado.

### 3.3 Cotacoes e pedidos

Ainda em `services/api/operacional/models/compras.py`:

- `CotacaoCompra` usa `fornecedor_nome` e `fornecedor_contato`
- `PedidoCompra` usa `fornecedor_nome` e `fornecedor_contato`
- `CotacaoFornecedor` usa `fornecedor_id`
- `DevolucaoFornecedor` usa `fornecedor_id`

Leitura arquitetural:

- o modulo de compras mistura dois modelos:
  - cadastro operacional com `fornecedor_id`
  - fluxo transacional e analitico por `fornecedor_nome`

### 3.4 Financeiro

Arquivo: `services/api/financeiro/models/despesa.py`

Evidencias:

- `pessoa_id` opcional com comentario "Fornecedor/prestador cadastrado"
- campo legado `fornecedor` textual
- docstring explicita compatibilidade:
  - vinculo com fornecedor cadastrado via `pessoa_id`
  - fallback por texto livre

Leitura arquitetural:

- financeiro nao exige fornecedor canônico;
- ha suporte nativo a dupla representacao.

## 4. Tabelas

Tabelas principais auditadas:

- `cadastros_pessoas`
- `cadastros_pessoas_documentos`
- `cadastros_pessoas_contatos`
- `cadastros_tipos_relacionamento`
- `cadastros_pessoa_relacionamentos`
- `compras_fornecedores`
- `compras_solicitacoes`
- `compras_cotacoes`
- `compras_pedidos`
- `compras_pedidos_cotacoes`
- `compras_recebimentos`
- `compras_devolucoes`
- `fin_despesas`

Evidencia importante de consolidacao em andamento:

- `services/api/operacional/services/fornecedores_service.py` cria e reutiliza `Pessoa`;
- `services/api/tests/unit/operacional/test_backfill_fornecedores.py` e `services/api/tests/unit/operacional/test_consolidar_fornecedores_duplicados.py` mostram que o projeto ja possui trilhas de backfill e consolidacao documental/testada.

Isso indica uma direcao arquitetural clara, mas ainda nao concluida em todos os consumidores.

## 5. Rotas

Arquivos auditados:

- `services/api/operacional/routers/compras.py`
- `services/api/financeiro/routers/despesas.py`
- `services/api/core/cadastros/pessoas/router.py`

### 5.1 CRUD de fornecedor

Evidencias em `compras.py`:

- `GET /compras/fornecedores`
- `POST /compras/fornecedores`
- `GET /compras/fornecedores/{id}`
- `PUT /compras/fornecedores/{id}`

Todas as criacoes e atualizacoes passam por:

- `salvar_fornecedor_legado(session, tenant.id, **data.model_dump())`

Leitura arquitetural:

- o modulo de compras nao cria fornecedor puramente isolado;
- ele sempre tenta resolver a pessoa canônica por documento ou nome e vincular `pessoa_id`.

### 5.2 Fluxos de cotacao e pedido

Evidencias:

- `CotacaoSolicitacaoCreate` recebe `fornecedor_nome`
- `PedidoCompraResponse` devolve `fornecedor_nome`
- historico, ranking, recomendacao e analytics operam sobre `fornecedor_nome`

Leitura arquitetural:

- a camada transacional de compras ainda nao depende do cadastro canônico de fornecedor para operar;
- a resolucao canonica nao esta presente nesses fluxos.

### 5.3 Financeiro

Evidencias:

- `POST /financeiro/despesas/` aceita `DespesaCreate`
- schema permite `pessoa_id` opcional e `fornecedor` texto livre

Leitura arquitetural:

- financeiro ainda aceita fornecedor textual sem exigir `Pessoa` nem `Fornecedor`.

## 6. Frontend Web

Arquivos auditados:

- `apps/web/src/app/(dashboard)/dashboard/operacional/fornecedores/FornecedoresClient.tsx`
- `apps/web/src/app/(dashboard)/dashboard/operacional/pedidos-compra/page.tsx`
- `apps/web/src/app/(dashboard)/operacional/compras/[id]/page.tsx`
- `apps/web/src/components/compras/CotacaoSolicitacaoDialog.tsx`
- `apps/web/src/app/(dashboard)/dashboard/financeiro/despesas/page.tsx`
- `apps/web/src/app/(dashboard)/cadastros/pessoas/_components/pessoa-form-dialog.tsx`
- `apps/web/src/app/(dashboard)/suprimentos/estoque/_components/EstoqueDialogs.tsx`

### 6.1 Tela de fornecedores

Evidencias:

- o formulario envia apenas:
  - `nome_fantasia`
  - `cnpj_cpf`
  - `email`
  - `telefone`
  - `condicoes_pagamento`
  - `prazo_entrega_dias`
  - `avaliacao`
- nao expõe `pessoa_id`

Leitura:

- a UX trabalha com `Fornecedor` como cadastro operacional proprio;
- a ponte para `Pessoa` fica invisivel, encapsulada no backend.

### 6.2 Compras e cotacoes

Evidencias:

- `CotacaoSolicitacaoDialog.tsx` usa `fornecedor_nome` e `fornecedor_contato`
- `pedidos-compra/page.tsx` mantem listagem de fornecedores, mas os pedidos e cotacoes nao exigem `fornecedor_id`
- `operacional/compras/[id]/page.tsx` consulta fornecedores, mas a tela e contratos continuam misturando nome e id

Leitura:

- a UX de compras ainda opera, em grande parte, pelo nome do fornecedor;
- o cadastro operacional existe, mas nao e a ancora universal dos fluxos.

### 6.3 Financeiro

Evidencias:

- `dashboard/financeiro/despesas/page.tsx` pede `fornecedor` como texto livre
- nao ha seletor de `Pessoa` ou `Fornecedor`

Leitura:

- o frontend financeiro ainda reforca a compatibilidade legada.

### 6.4 Estoque

Evidencias:

- `EstoqueDialogs.tsx` possui campo `fornecedor` textual na entrada manual

Leitura:

- estoque ainda preserva fornecedor textual fora do cadastro canônico.

### 6.5 Cadastro central de pessoas

Evidencia:

- o formulario de pessoa identifica o tipo `FORNECEDOR` em `tiposRel`

Leitura:

- a UI central de pessoas ja reconhece fornecedor como papel do dominio `Pessoa`.

## 7. Testes

Arquivos auditados:

- `services/api/tests/integration/operacional/test_compras.py`
- `services/api/tests/unit/operacional/test_fornecedores_service.py`
- `services/api/tests/unit/operacional/test_backfill_fornecedores.py`
- `services/api/tests/unit/operacional/test_compras_financeiro_integration.py`
- `services/api/tests/test_compras_lote_integration.py`

### 7.1 CRUD de fornecedor

Os testes de integracao validam que:

- criar fornecedor gera `pessoa_id`
- o mesmo documento reutiliza a mesma `Pessoa`
- o mesmo fluxo evita duplicar `compras_fornecedores`
- existe isolamento por tenant

### 7.2 Service de fornecedor

Os testes unitarios validam que:

- `resolve_fornecedor()` cria `Pessoa`, `PessoaDocumento`, `PessoaContato` e garante relacionamento `FORNECEDOR`
- `salvar_fornecedor_legado()` reutiliza registro legado e atualiza campos comerciais

### 7.3 Backfill

Os testes de backfill validam:

- vinculacao por documento
- vinculacao por nome com menor confianca
- criacao de nova `Pessoa` quando nao ha match

### 7.4 Integracao compras -> financeiro

Os testes mostram que:

- a despesa automatica de compra pode ser criada com `fornecedor_nome`
- o fluxo financeiro aceita essa compatibilidade

Conclusao:

- os testes confirmam que a canonicidade de `Pessoa` existe no cadastro;
- os mesmos testes confirmam que a plataforma ainda protege fortemente os fluxos legados por nome/documento/texto.

## 8. Fluxos

### 8.1 Cadastro de fornecedor

Fluxo real encontrado:

`payload compras -> salvar_fornecedor_legado() -> resolve_fornecedor() -> Pessoa + papel FORNECEDOR -> compras_fornecedores`

Conclusao:

- cadastro de fornecedor novo ja passa por `Pessoa` no backend.

### 8.2 Solicitacao / cotacao

Fluxo real:

`SolicitacaoCompra -> CotacaoCompra(fornecedor_nome) -> analytics/historico/ranking`

Conclusao:

- cotacao nao depende do cadastro operacional de fornecedor.

### 8.3 Pedido / recebimento

Fluxo real:

`CotacaoCompra(fornecedor_nome) -> PedidoCompra(fornecedor_nome) -> RecebimentoParcial -> Estoque`

Conclusao:

- o pedido continua textual no eixo fornecedor;
- rastreabilidade de estoque vem por pedido/NF/lote, nao por fornecedor canônico.

### 8.4 Compra -> financeiro

Fluxo real:

`PedidoCompra -> _resolver_fornecedor_financeiro() -> DespesaCreate(pessoa_id?, fornecedor texto) -> fin_despesas`

Detalhe importante:

- se o sistema encontra `Fornecedor` por `nome_fantasia`, tenta preencher `pessoa_id`
- se nao encontra, preserva apenas o nome textual

Conclusao:

- existe resolucao canônica parcial, mas com fallback estrutural para texto.

### 8.5 Cadastro central

Fluxo real potencial:

`Pessoa -> PessoaRelacionamento(FORNECEDOR) -> uso operacional em compras`

Conclusao:

- esse e o fluxo arquitetural desejado pelo dominio;
- ainda nao e o fluxo universal consumido por compras, estoque e financeiro.

## 9. Arquitetura encontrada

Classificacao: **Modelo D**

> `Fornecedor` e wrapper operacional de `Pessoa`. `Pessoa` e o mestre, mas `Fornecedor` mantem metadados especificos de compras.

Justificativa baseada na codebase:

- `fornecedores_service.py` sempre resolve `Pessoa` e garante o papel `FORNECEDOR`;
- o CRUD de fornecedor encapsula esse comportamento;
- `Fornecedor` guarda campos comerciais e operacionais que nao estao diretamente projetados na tabela base de pessoas;
- cotacoes, pedidos e financeiro ainda aceitam ou dependem de nome textual, logo o sistema nao esta plenamente consolidado em `Pessoa`.

Resposta objetiva para "o que e Fornecedor hoje?":

- nao e apenas um cadastro mestre isolado;
- nao e ainda apenas um papel puro de `Pessoa`;
- e um wrapper operacional com ponte ativa para `Pessoa`, coexistindo com fluxos textuais legados.

## 10. Riscos

Riscos estruturais identificados:

- fornecedor sem `Pessoa` em registros antigos ou fluxos laterais
- `Pessoa` com papel fornecedor sem registro operacional em `compras_fornecedores`
- divergencia entre `cnpj_cpf` em `Fornecedor` e `PessoaDocumento`
- divergencia entre `email`/`telefone` em `Fornecedor` e `PessoaContato`
- cotacao e pedido sem fornecedor canônico, apenas textual
- despesa financeira sem `pessoa_id`, apenas com `fornecedor` texto livre
- entrada manual de estoque com fornecedor textual sem vinculo mestre
- analytics por `fornecedor_nome`, sujeitos a duplicidade sem normalizacao
- rastreabilidade incompleta entre compra, estoque e financeiro quando o match por nome falha

Risco adicional:

- tornar `Pessoa` obrigatoria globalmente agora, sem camada de resolucao, quebraria contratos implícitos em cotacoes, pedidos, estoque e despesas.

## 11. Decisao

Decisao escolhida: **Opcao D — Criar camada de resolucao canônica de fornecedor antes de tornar vínculo obrigatório.**

Justificativa:

- o cadastro de fornecedor novo ja aponta para `Pessoa` como base correta;
- a aplicacao inteira ainda nao consome essa base de forma uniforme;
- compras, estoque e financeiro ainda preservam fornecedor textual em fluxos criticos;
- a canonicidade existe no cadastro, mas nao no ciclo completo de operacao.

Resposta objetiva ao objetivo desta auditoria:

`Fornecedor` nao deve permanecer como entidade totalmente independente a longo prazo. Tambem nao e seguro tratá-lo imediatamente como papel puro e obrigatorio de `Pessoa` em todos os fluxos. Antes disso, deve existir uma camada canônica de resolucao de fornecedor.

## 12. Plano recomendado

Plano documental recomendado, sem implementacao nesta execucao:

1. Criar um resolver canônico de fornecedor com prioridade explicita:
   `Fornecedor.pessoa_id -> match por documento -> match por nome controlado -> fallback textual`.
2. Introduzir esse resolver primeiro nos consumidores de menor risco:
   - compras -> financeiro
   - dashboards/analytics
   - contas a pagar
3. Mapear todos os pontos que ainda usam apenas `fornecedor_nome` ou `fornecedor` textual.
4. Preservar `Fornecedor` como wrapper operacional para metadados comerciais:
   - condicoes de pagamento
   - prazo de entrega
   - avaliacao
5. Tornar `Pessoa` obrigatoria para novos fornecedores apenas quando:
   - cotacoes e pedidos puderem resolver fornecedor canônico sem regressao;
   - financeiro e estoque aceitarem metadados canônicos sem depender de texto livre como fonte primaria;
   - os testes cobrirem compatibilidade com dados antigos e com deduplicacao por documento/nome.

## 13. Pergunta final obrigatoria

**Para a versao 1.0 do AgroSaaS, `Fornecedor` nao deve continuar como entidade operacional totalmente isolada, mas tambem nao deve ser convertido diretamente em papel puro e obrigatorio de `Pessoa` em todos os fluxos. A evidencia da codebase indica que deve existir antes uma camada canônica de resolucao de fornecedor para preservar compatibilidade com Compras, Estoque, Financeiro e dados legados.**
