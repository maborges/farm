# INTEGRATION-EXT-02 — Sankhya P0 com Associação Externa

## Escopo aplicado

Esta entrega conectou o Sankhya P0 à infraestrutura transversal de Associação Externa implementada em `INTEGRATION-EXT-01`.

Entidades P0 integradas:

- Pessoa / Parceiro Sankhya (`CODPARC`)
- Produto / Produto Sankhya (`CODPROD`)
- NFe / Documento Fiscal (`CHAVEACESSO`)
- Financeiro / Título (`chave composta`)
- Unidade de Medida
- Natureza / Plano Financeiro

## Reaproveitado

- `ExternalRecordAssociation`
- `ExternalRecordAssociationHistory`
- `ExternalRecordAssociationService`
- runtime canônico Sankhya (`TenantIntegracao`, `IntegrationFeature`, `IntegrationJob`, `IntegrationHealth`)
- staging `sankhya_*`

## Estendido

- fundação de associação externa para aceitar pendência sem `local_record_id` resolvido
- serviços Sankhya de pessoas, produtos, NFe e financeiro para registrar o vínculo oficial após persistir o staging

## Criado

- `SankhyaExternalAssociationHelper`
- migration complementar para permitir `local_record_id` nulo em associações pendentes
- suíte de testes unitários do Sankhya P0 com Associação Externa

## Regras efetivamente aplicadas

### Pessoas

- usa `CODPARC` como identificador externo oficial
- valida CPF/CNPJ como chave secundária
- ativa a associação quando encontra uma `Pessoa` local única e segura
- marca conflito quando o mesmo `CODPARC` passa a apontar para outro registro local

### Produtos

- usa `CODPROD` como identificador externo oficial
- considera `codigo_interno`, `sku`, `codigo_barras`, unidade e descrição como apoio de reconciliação
- ativa a associação quando encontra um `Produto` local único e seguro

### NFe

- usa `CHAVEACESSO` como chave forte
- registra `NUNOTA` ou `CODNEG`, `NUMNOTA`, `SERIE` e `MODNOTA` como chaves secundárias
- evita duplicidade silenciosa de nota

### Financeiro

- não usa `DESDOB` isolado como chave duradoura
- usa chave composta com:
  - `TIPO`
  - `CODPARC`
  - `NUMDOC`
  - `DESDOB`
  - `DTVENC`
  - `VLRDESDOB`
  - `CODEMP`
  - `CODFILIAL`
- ativa a associação somente quando encontra `Despesa` ou `Receita` local com correspondência segura

### Unidade de Medida

- cria associação oficial para a unidade Sankhya
- não assume equivalência automática por texto
- mantém status `PENDING` quando não existe correspondência local segura
- reconcilia para `ACTIVE` quando a unidade local passa a existir com equivalência segura

### Natureza / Plano

- usa `CODNAT` quando disponível
- associa com `PlanoConta` apenas quando encontra regra segura por código
- mantém pendência quando não há correspondência segura

## Premissas do piloto

- `CODEMP` e `CODFILIAL` são gravados na associação quando presentes no payload Sankhya
- quando o payload não traz esses campos, a associação fica escopada por tenant, configuração e ambiente
- para o piloto atual, isso preserva a premissa operacional de cenário monoempresa/monofilial enquanto os campos não forem obrigatórios no payload

## O que permaneceu pendente

- unidade de medida sem equivalência segura continua pendente
- natureza/plano sem código compatível continua pendente
- não houve implementação de P1/P2
- não houve escrita bidirecional
- não houve criação de endpoints, telas ou contratos públicos

## Conflitos esperados

- `CODPARC` existente apontando para outra `Pessoa`
- `CODPROD` existente apontando para outro `Produto`
- NFe já associada a outro documento local
- título financeiro externo já associado a outro lançamento local no mesmo tenant/configuração/ambiente

## Separação entre staging e vínculo oficial

- `sankhya_*` continua sendo staging/espelho técnico
- a referência oficial para equivalência entre registro local e registro Sankhya passou a ser `integration_external_record_links`

## Validações executadas

- `services/api/tests/unit/integracoes/test_sankhya_external_association_p0.py`
- `services/api/tests/unit/integracoes/test_external_record_association_service.py`
- `services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py`
- `services/api/tests/unit/integracoes/test_sankhya_gateway_auth_service.py`
- `services/api/tests/unit/integracoes/test_sankhya_gateway_test_connection.py`
- `services/api/tests/unit/integracoes/test_integrations_foundation_models.py`
- `services/api/tests/unit/integracoes/test_integrations_operational_models.py`
- `git diff --check`

## Resultado

- Sankhya P0 passou a usar Associação Externa como vínculo oficial
- staging permaneceu separado
- Gateway-first permaneceu inalterado
- nenhuma API pública foi modificada
- nenhuma entidade P1/P2 foi implementada
- nenhum comportamento bidirecional foi criado
