# SANKHYA-SYNC-01 - Escopo Piloto Café Exportador

Data: 2026-07-05

## Objetivo

Auditar o que já existe no AgroSaaS para Sankhya e desenhar o escopo mínimo de sincronização para um piloto com produtor de café exportador, sem implementar sync nesta etapa.

## Auditoria obrigatória

### Módulos Sankhya já existentes

O backend já possui módulo Sankhya com:

- router principal em [`services/api/integracoes/sankhya/routers/__init__.py`](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/routers/__init__.py)
- adapter canônico em [`services/api/integracoes/sankhya/services/canonical_adapter.py`](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/canonical_adapter.py)
- serviços de pessoas/produtos em [`services/api/integracoes/sankhya/services/sync_service.py`](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py)
- serviços de NFe/financeiro em [`services/api/integracoes/sankhya/services/nfe_financeiro_service.py`](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/nfe_financeiro_service.py)

### Adapter canônico atual

O adapter já cobre:

- criação/atualização da configuração canônica
- health snapshot
- eventos de integração
- jobs canônicos
- features canônicas
- políticas canônicas

E já deixa explícito um desenho futuro para `pedidos` e `estoque` como features baseadas em outbox. Referência:

- [`services/api/integracoes/sankhya/services/canonical_adapter.py#L51`](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/canonical_adapter.py#L51)
- [`services/api/integracoes/sankhya/services/canonical_adapter.py#L117`](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/canonical_adapter.py#L117)

### Entidades internas relacionadas

Foram auditadas as entidades internas abaixo:

- [`services/api/core/cadastros/pessoas/models.py`](/opt/lampp/htdocs/farm/services/api/core/cadastros/pessoas/models.py)
- [`services/api/core/cadastros/produtos/models.py`](/opt/lampp/htdocs/farm/services/api/core/cadastros/produtos/models.py)
- [`services/api/operacional/models/compras.py`](/opt/lampp/htdocs/farm/services/api/operacional/models/compras.py)
- [`services/api/operacional/models/estoque.py`](/opt/lampp/htdocs/farm/services/api/operacional/models/estoque.py)
- [`services/api/financeiro/models/plano_conta.py`](/opt/lampp/htdocs/farm/services/api/financeiro/models/plano_conta.py)
- [`services/api/financeiro/models/rateio.py`](/opt/lampp/htdocs/farm/services/api/financeiro/models/rateio.py)
- [`services/api/financeiro/models/despesa.py`](/opt/lampp/htdocs/farm/services/api/financeiro/models/despesa.py)
- [`services/api/financeiro/models/receita.py`](/opt/lampp/htdocs/farm/services/api/financeiro/models/receita.py)
- [`services/api/financeiro/models/nota_fiscal.py`](/opt/lampp/htdocs/farm/services/api/financeiro/models/nota_fiscal.py)
- [`services/api/financeiro/comercializacao/models.py`](/opt/lampp/htdocs/farm/services/api/financeiro/comercializacao/models.py)

## Classificação do domínio

| Item | Classificação | Evidência resumida |
|---|---|---|
| Fornecedores | EXISTE PARCIALMENTE | Há [`Fornecedor`](/opt/lampp/htdocs/farm/services/api/operacional/models/compras.py#L8) e vínculo com [`Pessoa`](/opt/lampp/htdocs/farm/services/api/core/cadastros/pessoas/models.py#L64), mas não há sincronização pronta para o modelo de fornecedor Sankhya. |
| Clientes | EXISTE PARCIALMENTE | Há [`Pessoa`](/opt/lampp/htdocs/farm/services/api/core/cadastros/pessoas/models.py#L64), [`Receita`](/opt/lampp/htdocs/farm/services/api/financeiro/models/receita.py#L9) e [`ComercializacaoCommodity`](/opt/lampp/htdocs/farm/services/api/financeiro/comercializacao/models.py#L20), mas cliente/comprador ainda aparece também como texto legado. |
| Produtos/insumos | EXISTE E ATENDE | [`Produto`](/opt/lampp/htdocs/farm/services/api/core/cadastros/produtos/models.py#L204) cobre insumos, EPI, peças, combustível e serviço. |
| Estoque | EXISTE E ATENDE | [`SaldoEstoque`](/opt/lampp/htdocs/farm/services/api/operacional/models/estoque.py#L21), [`LoteEstoque`](/opt/lampp/htdocs/farm/services/api/operacional/models/estoque.py#L34) e [`EstoqueMovimento`](/opt/lampp/htdocs/farm/services/api/operacional/models/estoque.py#L80) suportam saldo, rastreio e ledger. |
| Plano de contas | EXISTE E ATENDE | [`PlanoConta`](/opt/lampp/htdocs/farm/services/api/financeiro/models/plano_conta.py#L9) já tem hierarquia e categoria RFB. |
| Centro de custo | EXISTE PARCIALMENTE | Existe rateio por safra/talhão em [`Rateio`](/opt/lampp/htdocs/farm/services/api/financeiro/models/rateio.py#L8) e relatórios de centro de custos, mas não há entidade master de centro de custo dedicada. |
| Contas a pagar | EXISTE E ATENDE | [`Despesa`](/opt/lampp/htdocs/farm/services/api/financeiro/models/despesa.py#L9) cobre contas a pagar. |
| Contas a receber | EXISTE E ATENDE | [`Receita`](/opt/lampp/htdocs/farm/services/api/financeiro/models/receita.py#L9) cobre contas a receber. |
| Notas fiscais | EXISTE E ATENDE | [`NotaFiscal`](/opt/lampp/htdocs/farm/services/api/financeiro/models/nota_fiscal.py#L26) cobre NF interna; Sankhya também já tem [`SankhyaNFe`](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/models/__init__.py#L183). |
| Comercialização/contratos | EXISTE PARCIALMENTE | [`ComercializacaoCommodity`](/opt/lampp/htdocs/farm/services/api/financeiro/comercializacao/models.py#L20) fecha o ciclo de venda, mas a modelagem de contratos ainda é parcial para um outbound completo. |

## Escopo mínimo do piloto

### Entrar no piloto

1. Fornecedores.
2. Clientes/compradores.
3. Produtos e insumos.
4. Contas a pagar.
5. Contas a receber.
6. Notas fiscais.
7. Estoque somente no nível mínimo necessário para apoiar recebimento/baixa e rastreabilidade.

### Ficar fora do piloto inicial

1. Sincronização de pedidos comerciais completos.
2. Sincronização de contratos complexos de comercialização.
3. Qualquer sync de manufatura/processo avançado.
4. Fluxos financeiros bancários/conciliação.

## Direção de fluxo recomendada

### Sankhya -> AgroSaaS

Preferência para o piloto.

- fornecedores
- clientes/compradores
- produtos/insumos
- estoque
- contas a pagar
- contas a receber
- notas fiscais

Motivo: reduz risco operacional, evita conflito de edição e permite validar aderência cadastral antes de habilitar escrita reversa.

### AgroSaaS -> Sankhya

Não recomendado no MVP.

Aplicar somente em fase posterior, quando houver maturidade de:

- idempotência consolidada
- auditoria de divergência
- definição de fonte de verdade por entidade

### Bidirecional

Não recomendado no MVP.

### Somente leitura

Recomendado para a primeira entrega funcional do piloto.

## Prioridade MVP

### P0

- autenticação e configuração
- fornecedores
- clientes/compradores
- produtos/insumos
- contas a pagar
- contas a receber

### P1

- notas fiscais
- estoque mínimo necessário para rastreabilidade e conciliação operacional

### P2

- comercialização/contratos
- regras avançadas de estoque por lote/deposito
- outbound para Sankhya

## Riscos de duplicidade

### Fornecedores e clientes

Risco alto de duplicidade por:

- variação de razão social
- variação de nome fantasia
- múltiplos CPFs/CNPJs por cadastro legado

Mitigação:

- chave externa principal: `CODPARC`/`sankhya_id`
- chave secundária: CPF/CNPJ normalizado
- fallback: nome + documento + tenant

### Produtos/insumos

Risco alto por:

- código interno diferente entre sistemas
- mesma descrição com unidades diferentes
- variação de embalagem versus conteúdo

Mitigação:

- chave externa principal: `CODPROD`
- fallback: `codigo_interno` + `sku`
- validação de unidade de medida e NCM quando aplicável

### Estoque

Risco alto por:

- múltiplos depósitos
- lote versus saldo agregado
- remessas parciais

Mitigação:

- chave composta: `CODPROD + deposito + lote`
- tratar saldo como snapshot e movimento como ledger

### Contas a pagar e a receber

Risco médio/alto por:

- parcelas múltiplas
- títulos reemitidos
- mesmo documento com acréscimos/baixas parciais

Mitigação:

- chave composta: `CODPARC + NUMDOC + DESDOB`
- se houver, complementar com vencimento e valor

### Notas fiscais

Risco baixo quando a `chave_acesso` existe.

Mitigação:

- chave primária de idempotência: `chave_acesso`
- fallback: `numero + serie + emitente + tipo`

## Chaves externas e idempotência

- Fornecedor: `sankhya_id` / `CODPARC`
- Cliente: `sankhya_id` / `CODPARC`
- Produto: `CODPROD`
- Estoque: `CODPROD + deposito + lote`
- Conta a pagar: `CODPARC + NUMDOC + DESDOB`
- Conta a receber: `CODPARC + NUMDOC + DESDOB`
- Nota fiscal: `chave_acesso`
- Comercialização: `numero_contrato` + `commodity_id` + `comprador_id`

## Eventos e outbox

### Necessários agora

Para o piloto de leitura, os eventos já existentes do domínio de integração são suficientes:

- `integrations.configured`
- `integrations.credential_rotated`
- `integrations.health_changed`
- `integrations.sync_started`
- `integrations.sync_completed`
- `integrations.sync_failed`

### Recomendados para fase 2

Se houver escrita de AgroSaaS para Sankhya, usar outbox para:

- `pessoa` upsert
- `produto` upsert
- `estoque` movimentação
- `despesa` / `receita` exportação
- `nota fiscal` autorização/exportação
- `comercialização` confirmação

## Conclusão prática

Para o piloto do café exportador, o recorte mínimo seguro é:

1. leitura de cadastro Sankhya para fornecedores, clientes e produtos;
2. leitura de financeiro para contas a pagar/receber;
3. leitura de notas fiscais;
4. leitura de estoque apenas no nível necessário para rastreabilidade;
5. deixar comercialização/contratos e escrita reversa para fase posterior.

## Validação

Executado:

- `git diff --check`

Resultado:

- sem erros
