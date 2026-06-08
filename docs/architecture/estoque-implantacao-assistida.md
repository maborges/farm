# Estoque - Implantacao Assistida

## Status

- Etapa atual: `ESTOQUE-IMP-01`
- Escopo desta entrega: diagnostico arquitetural e plano incremental
- Sem migration nesta etapa
- Sem alteracao de schema nesta etapa

## 1. Diagnostico do que ja existe no codigo

### Backend de estoque ativo

O modulo ativo de estoque ja existe em `services/api/operacional/*` e cobre o fluxo operacional normal:

- `services/api/operacional/models/estoque.py`
  - `Deposito`
  - `SaldoEstoque`
  - `LoteEstoque`
  - `EstoqueMovimento`
  - `RequisicaoMaterial`
  - `ReservaEstoque`
- `services/api/operacional/schemas/estoque.py`
  - requests e responses para entrada, saida, ajuste, transferencia, lotes, saldos e reservas
- `services/api/operacional/services/estoque_service.py`
  - `registrar_entrada`
  - `registrar_saida`
  - `registrar_ajuste`
  - `registrar_transferencia`
  - listagem de saldos, lotes, movimentacoes e auditoria
- `services/api/operacional/routers/estoque.py`
  - endpoints REST ativos do modulo

### Ledger canonico e fluxo de saldo inicial

Ha suporte estrutural forte para implantacao de saldo inicial no ledger:

- `services/api/migrations/versions/step18_estoque_movimentos.py`
  - a tabela `estoque_movimentos` aceita `tipo_movimento = 'SALDO_INICIAL'`
  - existe indice unico parcial `uq_estoque_movimentos_saldo_inicial`
  - o comentario da migration explicita: opening balances devem ser inseridos por runbook/service, nao por backfill automatico
- `services/api/operacional/services/estoque_ledger.py`
  - `registrar_ledger_estoque()` ja aceita `tipo_movimento='SALDO_INICIAL'`
  - o ledger e append-only

Conclusao: o sistema ja tem um conceito tecnico de saldo inicial no ledger, mas esse conceito ainda nao esta exposto como fluxo de implantacao assistida.

### Fluxos existentes relacionados, mas nao equivalentes

- Ajuste de inventario:
  - `services/api/operacional/services/estoque_service.py`
  - `registrar_ajuste()` corrige saldo atual e grava `tipo='AJUSTE'`
  - atende inventario fisico rotineiro, nao onboarding legado
- Entrada manual:
  - `registrar_entrada()` usa `tipo='ENTRADA'`
  - schema aceita `origem_tipo="INICIAL"`, mas isso nao garante trilha de implantacao
- Auditoria de movimentacao:
  - `get_auditoria_movimentacao()` ja existe no service
  - `core/services/audit_service.py` ja oferece `write_audit_log()`
- Validacoes multi-tenant:
  - `services/api/core/operational_context.py`
  - `validate_deposito_context()`
  - `validate_lote_context()`
  - validacoes de `unidade_produtiva`, `safra` e `production_unit`

### Upload/importacao existentes em outros dominios

Existem padroes reaproveitaveis para upload e importacao, mas nao em estoque:

- `services/api/operacional/services/frota_import_service.py`
  - importacao CSV simples com `csv.DictReader`
  - validacao por linha
  - retorno com contagem + erros
- `services/api/operacional/routers/frota.py`
  - endpoints `POST /frota/importar/abastecimentos`
  - endpoints `POST /frota/importar/manutencoes`
- `services/api/financeiro/routers/conciliacao.py`
  - fluxo de upload para pre-visualizacao de OFX antes de confirmar
- `services/api/financeiro/routers/integracao.py`
  - upload de OFX por conta bancaria

### Frontend de estoque atual

O frontend de estoque ativo fica principalmente em:

- `apps/web/src/app/(dashboard)/suprimentos/estoque/page.tsx`
- `apps/web/src/app/(dashboard)/suprimentos/saldos/page.tsx`

Hoje a interface cobre:

- saldos
- alertas
- entrada
- saida
- transferencia
- ajuste
- reserva
- cadastro manual de produto/deposito

Nao existe hoje tela de:

- upload de planilha
- template de importacao de estoque
- mapeamento de colunas
- preview de implantacao
- confirmacao de carga inicial

### O que foi procurado e nao encontrado

A varredura no codigo ativo nao encontrou implementacao pronta para estoque de:

- importacao CSV/Excel
- upload de planilhas de estoque
- template de importacao de estoque
- mapeamento de colunas de estoque
- onboarding de estoque
- sessao de pre-validacao ou preview de implantacao
- inventario inicial como submodulo de onboarding

Tambem nao foi encontrada UI ativa de configuracao de mapeamento de colunas em estoque. Em documentacao financeira ha mencao futura de "mapeamento configuravel", mas nao implementacao ativa reaproveitavel.

## 2. Funcionalidades reaproveitaveis

As seguintes pecas devem ser reaproveitadas em vez de duplicadas:

### Regras de dominio e seguranca

- `validate_deposito_context()` para garantir tenant e compatibilidade com unidade produtiva
- `validate_lote_context()` para lotes
- `_validar_unidade_produtiva()` de `EstoqueService`
- `_get_produto_or_fail()` de `EstoqueService`

### Escrita canonica no estoque

- `registrar_ledger_estoque()` como ponto unico de escrita no ledger
- `SaldoEstoque` como snapshot operacional
- `LoteEstoque` para casos em que o legado trouxer identificacao de lote

### Fluxos de correcoes e auditoria

- `write_audit_log()` para registro de confirmacao futura
- endpoints de consulta de saldos, lotes e movimentacoes para conferencias pos-implantacao

### Padrao de importacao

- `FrotaImportService` como referencia de:
  - leitura de arquivo
  - validacao por linha
  - acumulacao de erros
  - resposta resumida

### Componentes UI existentes

- `@/components/ui/*`
- `Dialog`, `Table`, `Badge`, `Input`, `Select`
- `apps/web/src/components/ui/data-table.tsx` pode ser util para preview/export futuro

## 3. Lacunas encontradas

### Lacunas funcionais

- nao existe submodulo de implantacao assistida em estoque
- nao existe upload de CSV/XLSX no modulo de estoque
- nao existe parser com deteccao de colunas
- nao existe mapeamento manual de colunas
- nao existe sugestao de correcao para produto/deposito nao encontrado
- nao existe preview persistido antes da confirmacao
- nao existe confirmacao em lote gerando saldo inicial com trilha propria

### Lacunas de modelagem/proveniencia

- o schema de estoque aceita `origem_tipo="INICIAL"` no request de entrada, mas isso nao e um fluxo formal de implantacao
- `services/api/operacional/services/estoque_ledger.py` normaliza `"INICIAL"` para `"MANUAL"`
- a constraint atual de `origem` em `estoque_movimentos` nao inclui `IMPLANTACAO`

Impacto:

- com o estado atual, uma implantacao acabaria parecendo entrada manual ou ajuste comum
- isso fere a regra de nao misturar implantacao com operacao normal

### Lacunas de UX/processo

- nao ha template padrao de importacao
- nao ha tela de conferencia por linha
- nao ha mecanismo para "produto nao encontrado, vincular ao produto existente"
- nao ha mecanismo para "deposito nao encontrado, vincular ao deposito existente"

## 4. Decisao se sera criado novo subdominio, service, router ou models

### Decisao arquitetural

A funcionalidade deve ser tratada como submodulo do Estoque e nao como modulo independente.

### Decisao de organizacao de codigo

Recomendacao:

- manter prefixo de rota em `/estoque/implantacao-assistida/*`
- criar arquivos dedicados, mas dentro do dominio operacional/estoque

Estrutura proposta:

- `services/api/operacional/schemas/estoque_implantacao.py`
- `services/api/operacional/services/estoque_implantacao_service.py`
- `services/api/operacional/routers/estoque_implantacao.py`

Motivo:

- evita inflar `estoque_service.py` com regras de importacao, preview e confirmacao
- preserva o modulo estoque como fonte de verdade
- facilita testes isolados

### Sobre models novos

Nesta etapa, nao criar models nem migration.

Para a implementacao futura, a recomendacao e introduzir persistencia de sessao de implantacao. Sem isso, o preview e a confirmacao ficam frageis para arquivos grandes, correcao iterativa, auditoria e retomada de processo.

## 5. Entidades propostas

Estas entidades sao propostas para etapas futuras. Nao serao criadas agora.

### `EstoqueImplantacaoSessao`

Responsabilidade:

- representar uma sessao de implantacao por tenant
- guardar metadados do arquivo e status do processamento

Campos sugeridos:

- `id`
- `tenant_id`
- `unidade_produtiva_id` nullable
- `status`
  - `UPLOAD_RECEBIDO`
  - `MAPEAMENTO_PENDENTE`
  - `VALIDADO_COM_ERROS`
  - `PRONTO_PARA_CONFIRMAR`
  - `CONFIRMADO`
  - `CANCELADO`
- `nome_arquivo`
- `hash_arquivo`
- `formato_arquivo`
- `cabecalhos_detectados` JSON
- `mapeamento_colunas` JSON
- `total_linhas`
- `total_validas`
- `total_com_erro`
- `criado_por`
- `confirmado_por`
- `confirmado_em`

### `EstoqueImplantacaoItem`

Responsabilidade:

- persistir cada linha interpretada do legado e seu status de validacao

Campos sugeridos:

- `id`
- `sessao_id`
- `linha_numero`
- `payload_original` JSON
- `produto_nome_original`
- `produto_codigo_original`
- `produto_id_resolvido`
- `deposito_nome_original`
- `deposito_id_resolvido`
- `unidade_original`
- `quantidade`
- `custo_unitario`
- `numero_lote`
- `data_validade`
- `production_unit_id` nullable
- `status_validacao`
  - `VALIDO`
  - `ERRO`
  - `CORRIGIDO`
  - `IGNORADO`
- `mensagens_validacao` JSON

### `EstoqueImplantacaoMovimento`

Opcional. Pode ser evitada se `origem_id` de `estoque_movimentos` apontar para `EstoqueImplantacaoSessao` ou `EstoqueImplantacaoItem`.

## 6. Endpoints propostos

Nao implementar agora. Proposta para etapas futuras:

### Sessao e upload

- `POST /estoque/implantacao-assistida/sessoes`
  - cria sessao e faz upload do arquivo
- `GET /estoque/implantacao-assistida/sessoes/{sessao_id}`
  - detalhe da sessao
- `GET /estoque/implantacao-assistida/sessoes/{sessao_id}/template`
  - baixa template CSV/XLSX

### Mapeamento e validacao

- `POST /estoque/implantacao-assistida/sessoes/{sessao_id}/mapear`
  - salva mapeamento de colunas
- `POST /estoque/implantacao-assistida/sessoes/{sessao_id}/validar`
  - executa validacoes
- `GET /estoque/implantacao-assistida/sessoes/{sessao_id}/preview`
  - preview consolidada
- `PATCH /estoque/implantacao-assistida/sessoes/{sessao_id}/itens/{item_id}`
  - correcao assistida de produto/deposito/unidade/lote

### Confirmacao

- `POST /estoque/implantacao-assistida/sessoes/{sessao_id}/confirmar`
  - gera `SALDO_INICIAL` ou movimento equivalente aprovado no desenho final
- `POST /estoque/implantacao-assistida/sessoes/{sessao_id}/cancelar`
  - cancela sessao sem gerar estoque

## 7. Fluxo funcional

Fluxo proposto:

1. Usuario acessa `Estoque > Implantacao Assistida`
2. Faz upload de CSV/XLSX
3. Sistema detecta cabecalhos e sugere mapeamento
4. Usuario confirma ou ajusta o mapeamento
5. Sistema valida:
   - produto
   - deposito
   - unidade
   - quantidade
   - custo
   - lote
   - unidade produtiva, quando aplicavel
6. Sistema gera preview:
   - linhas validas
   - linhas com erro
   - sugestoes simples de correcao
7. Usuario corrige pendencias criticas
8. Usuario confirma implantacao
9. Sistema grava movimentos canonicos de saldo inicial
10. Sistema grava auditoria de confirmacao
11. Sistema marca sessao como confirmada e disponibiliza relatorio

## 8. Regras de validacao

### Arquivo

- aceitar `csv` e `xlsx`
- rejeitar arquivo vazio
- rejeitar arquivo sem cabecalho legivel
- limitar volume por sessao

### Colunas minimas obrigatorias

Minimo operacional sugerido:

- identificador do produto
  - nome, codigo interno ou SKU
- deposito
  - nome ou codigo
- quantidade atual

Colunas opcionais:

- unidade
- custo unitario
- numero do lote
- data de validade
- unidade produtiva
- observacoes

### Produto

- deve pertencer ao mesmo `tenant_id`
- deve estar ativo ou explicitamente elegivel para estoque
- se nao encontrar match exato, sugerir candidatos por nome/codigo
- sem resolucao de produto, a linha nao pode ser confirmada

### Deposito

- deve pertencer ao mesmo `tenant_id`
- se a sessao estiver contextualizada por `unidade_produtiva_id`, o deposito deve ser compativel com essa unidade
- deposito inativo nao deve ser aceito por padrao

### Quantidade e custo

- quantidade deve ser maior que zero para implantacao
- custo unitario pode ser nulo
- custo negativo deve ser rejeitado

### Lote

- se houver lote, o lote deve ser criado ou vinculado de forma coerente ao produto e deposito
- validade menor que fabricacao deve ser rejeitada

### Confirmacao

- nao permitir confirmar sessao com erros bloqueantes
- confirmacao deve ser idempotente
- reprocessamento do mesmo arquivo deve ser detectavel por hash, sem impedir uso legitimo

## 9. Regras de seguranca multi-tenant

- toda sessao de implantacao deve carregar `tenant_id`
- todo produto resolvido deve ser validado no tenant
- todo deposito resolvido deve ser validado no tenant
- toda eventual `production_unit_id` deve ser validada no tenant e no contexto da sessao
- nao permitir referencias cross-tenant em nenhuma etapa do preview ou confirmacao
- usar os validadores ja existentes:
  - `validate_deposito_context()`
  - `validate_lote_context()`
  - validacoes de `unidade_produtiva`
- registrar usuario executor na confirmacao futura

## 10. Relacao com inventario, produtos, depositos e movimentacoes

### Inventario

- nao substituir o modulo de inventario fisico
- implantacao assistida e onboarding de saldo legado
- inventario fisico continuo segue como fluxo operacional distinto

### Produtos

- usar catalogo canonico de produtos ja existente
- nao criar produto automaticamente na etapa inicial
- em caso de falta de cadastro, a linha deve ser corrigida ou ignorada

### Depositos

- usar depositos existentes
- nao criar deposito automaticamente na confirmacao inicial
- eventual criacao assistida de deposito deve ser etapa separada e explicita

### Movimentacoes

Decisao recomendada:

- a confirmacao deve gerar `tipo_movimento = 'SALDO_INICIAL'`
- nao deve usar `ENTRADA` comum para implantacao
- nao deve usar `AJUSTE` comum como substituto da carga inicial

Observacao critica:

- hoje isso ainda nao fica 100% rastreavel porque `origem='IMPLANTACAO'` nao existe na constraint atual
- portanto, o sistema atual suporta o tipo `SALDO_INICIAL`, mas ainda nao suporta a melhor proveniencia para implantacao

## 11. O que nao implementar agora

- migration nesta etapa
- parser universal complexo de qualquer ERP legado
- importacao de historico completo de movimentacoes
- impacto automatico em financeiro operacional
- consumo agricola
- geracao de OS
- saidas operacionais
- conciliacao de estoque com talhao
- criacao automatica de produtos/depositos sem confirmacao explicita
- IA generativa para saneamento de cadastro

## 12. Plano incremental ESTOQUE-IMP-01 ate ESTOQUE-IMP-07

### `ESTOQUE-IMP-01`

- varredura do codigo existente
- diagnostico do modulo atual
- documento arquitetural

### `ESTOQUE-IMP-02`

- criar schemas e router do submodulo
- criar endpoint de template CSV
- criar endpoint de upload de sessao, inicialmente sem persistencia definitiva
- aceitar apenas CSV no primeiro corte

### `ESTOQUE-IMP-03`

- parser CSV
- deteccao de cabecalhos
- mapeamento de colunas
- preview em memoria ou persistida
- validacao de produto e deposito

### `ESTOQUE-IMP-04`

- persistencia de sessao e itens de implantacao
- correcao manual por linha
- sugestao de correspondencia de produto/deposito

### `ESTOQUE-IMP-05`

- confirmacao transacional
- geracao de `SALDO_INICIAL`
- gravacao de auditoria
- idempotencia da confirmacao

### `ESTOQUE-IMP-06`

- suporte a XLSX
- preview consolidada por deposito/produto
- relatorio final de implantacao

### `ESTOQUE-IMP-07`

- endurecimento de governanca
- trava de reexecucao
- indicadores de qualidade da implantacao
- refinamento de UX e testes end-to-end

## Decisao arquitetural final desta etapa

- O sistema ja possui modulo de estoque maduro e nao deve ser duplicado.
- O caminho correto e criar um submodulo de `Estoque > Implantacao Assistida`.
- A confirmacao futura deve gravar no ledger canonico usando `SALDO_INICIAL`.
- O estado atual do schema e quase suficiente, mas a proveniencia ainda nao diferencia implantacao de operacao normal de forma ideal.
- Por isso, nesta etapa nao e seguro implementar confirmacao definitiva sem antes desenhar a trilha de proveniencia e a sessao de implantacao.
- Portanto, `ESTOQUE-IMP-01` encerra em diagnostico + documento.

## Arquivos analisados nesta etapa

- `README.md`
- `CLAUDE.md`
- `CONTEXTO.md`
- `services/api/operacional/models/estoque.py`
- `services/api/operacional/schemas/estoque.py`
- `services/api/operacional/services/estoque_service.py`
- `services/api/operacional/services/estoque_ledger.py`
- `services/api/operacional/services/frota_import_service.py`
- `services/api/operacional/routers/estoque.py`
- `services/api/operacional/routers/frota.py`
- `services/api/core/operational_context.py`
- `services/api/core/services/audit_service.py`
- `services/api/migrations/versions/step18_estoque_movimentos.py`
- `services/api/tests/integration/operacional/test_estoque.py`
- `services/api/tests/unit/operacional/test_estoque_legacy_guardrail.py`
- `apps/web/src/app/(dashboard)/suprimentos/estoque/page.tsx`
- `apps/web/src/app/(dashboard)/suprimentos/saldos/page.tsx`
- `apps/web/src/hooks/use-estoque.ts`
- `apps/web/src/hooks/use-estoque-lotes.ts`
- `docs/contexts/estoque/enterprise/inventario-automatizado.md`
- `docs/contexts/core/integracoes-essenciais.md`

## Riscos principais

- usar `ENTRADA` ou `AJUSTE` comum para implantacao contaminaria a trilha operacional
- usar `origem='MANUAL'` para implantacao reduz auditabilidade
- confirmar sem sessao persistida dificulta retomada, suporte e auditoria
- criar produto/deposito automatico na implantacao aumenta risco de cadastro sujo
- ignorar `unidade_produtiva` pode misturar estoque entre contextos do tenant

