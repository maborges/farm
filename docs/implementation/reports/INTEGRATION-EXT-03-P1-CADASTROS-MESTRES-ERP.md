# INTEGRATION-EXT-03 — Associações Externas P1 para Cadastros Mestres de ERP

## Escopo auditado

- [docs/architecture/INTEGRATION-ARCH-03-ASSOCIACAO-REGISTROS-EXTERNOS.md](/opt/lampp/htdocs/farm/docs/architecture/INTEGRATION-ARCH-03-ASSOCIACAO-REGISTROS-EXTERNOS.md)
- [docs/architecture/INTEGRATION-ARCH-04-PLANO-IMPLEMENTACAO-ASSOCIACAO-EXTERNA.md](/opt/lampp/htdocs/farm/docs/architecture/INTEGRATION-ARCH-04-PLANO-IMPLEMENTACAO-ASSOCIACAO-EXTERNA.md)
- [docs/implementation/reports/INTEGRATION-EXT-01-FUNDACAO-ASSOCIACAO-EXTERNA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/INTEGRATION-EXT-01-FUNDACAO-ASSOCIACAO-EXTERNA.md)
- [docs/implementation/reports/INTEGRATION-EXT-02-SANKHYA-P0-ASSOCIACAO-EXTERNA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/INTEGRATION-EXT-02-SANKHYA-P0-ASSOCIACAO-EXTERNA.md)
- [services/api/integracoes/models.py](/opt/lampp/htdocs/farm/services/api/integracoes/models.py)
- [services/api/integracoes/services/external_record_association_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/services/external_record_association_service.py)
- [services/api/integracoes/sankhya/services/external_association_helper.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/external_association_helper.py)
- [services/api/integracoes/sankhya/services/sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py)
- [services/api/integracoes/sankhya/services/nfe_financeiro_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/nfe_financeiro_service.py)
- [services/api/operacional/models/estoque.py](/opt/lampp/htdocs/farm/services/api/operacional/models/estoque.py)
- [services/api/financeiro/models/conciliacao.py](/opt/lampp/htdocs/farm/services/api/financeiro/models/conciliacao.py)
- [services/api/agricola/models/operacao_tipo_fase.py](/opt/lampp/htdocs/farm/services/api/agricola/models/operacao_tipo_fase.py)
- [services/api/tests/unit/integracoes/test_sankhya_external_association_p0.py](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_sankhya_external_association_p0.py)
- [services/api/tests/unit/integracoes/test_external_record_association_service.py](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_external_record_association_service.py)

## O que já existia

- `ExternalRecordAssociationService` com criação, atualização, conflito, reconciliação e histórico.
- `SankhyaExternalAssociationHelper` com P0 para Pessoas, Produtos, NFe, Financeiro e Unidade de Medida.
- `integration_external_record_links` e `integration_external_record_link_history` já materializadas.
- Modelos locais úteis para P1:
  - `Deposito`
  - `ContaBancaria`
  - `OperacaoTipoFase`

## O que foi reaproveitado

- Serviço transversal `ExternalRecordAssociationService`.
- Estrutura canônica da associação oficial.
- Contexto Sankhya já resolvido por `TenantIntegracao` + `MarketplaceIntegracao` + `IntegrationFeature`.
- Padrão de sincronização já usado no P0: staging local primeiro, associação oficial depois.

## O que foi estendido

### `SankhyaExternalAssociationHelper`

Foram adicionados métodos para P1:

- `sync_organizacao`
- `sync_deposito`
- `sync_conta_bancaria`
- `sync_centro_custo`
- `sync_centro_resultado`
- `sync_tipo_operacao`

Também foram adicionados apoios internos para:

- localizar depósito local por referência textual;
- localizar conta bancária local por banco/agência/conta;
- localizar tipo de operação local por `OperacaoTipoFase`;
- registrar associações pendentes para masters sem entidade local segura.

### Testes

Foram adicionados testes cobrindo:

- organização sem master local seguro;
- depósito com `CODLOCAL` e isolamento por tenant;
- depósito com `CODLOCAL` e isolamento por ambiente;
- conta bancária ativa com pendências auxiliares de banco/agência/carteira;
- centros de custo e resultado como pendência;
- tipo de operação com master local ativo e fallback pendente.

## O que foi criado

- Nenhuma migration nova.
- Nenhuma nova tabela.
- Nenhum endpoint público.
- Nenhum fluxo bidirecional.

## Entidades P1 auditadas

- Empresa
- Filial
- Estabelecimento
- Depósito
- Local de Estoque
- Conta Corrente
- Banco
- Agência
- Carteira
- Centro de Resultado
- Centro de Custo
- Tipo de Operação

## Entidades P1 implementadas

### Implementadas com vínculo ativo quando existe master local seguro

- Depósito
- Conta Corrente
- Tipo de Operação

### Implementadas como associação pendente quando não existe master local seguro

- Empresa
- Filial
- Banco
- Agência
- Carteira
- Centro de Custo
- Centro de Resultado

## Entidades marcadas como pendentes

- Empresa, porque não existe master local dedicado.
- Filial, porque não existe master local dedicado.
- Estabelecimento, porque não existe entidade local segura neste ponto.
- Banco, Agência e Carteira, porque não existe master local dedicado.
- Centro de Custo e Centro de Resultado, porque o AgroSaaS usa rateio operacional, mas não tem master dedicado.

## Premissas assumidas

- `Tenant` não foi tratado como substituto automático de Empresa.
- `UnidadeProdutiva` não foi tratada como Filial fiscal.
- `Deposito` representa o local logístico local e pode ser vinculado a `CODLOCAL`.
- `ContaBancaria` representa a conta corrente local e pode ser vinculada a `ContaCorrente` do ERP.
- `OperacaoTipoFase` é o único master local seguro para tipo de operação no estado atual.
- Quando não há master local seguro, a associação oficial deve ficar em `PENDING`, sem criar domínio novo.

## Riscos

- Depósito pode exigir validação semântica adicional se o payload Sankhya usar `CODLOCAL` para mais de um conceito operacional.
- Banco/agência/carteira continuam sem master local próprio; a associação existe, mas permanece como pendente até existir cadastro dedicado.
- Centro de custo e centro de resultado seguem sem master local próprio.
- Estabelecimento fiscal ainda não tem entidade local segura para vínculo ativo.

## Validações executadas

### Testes

```bash
services/api/.venv/bin/pytest services/api/tests/unit/integracoes/test_sankhya_external_association_p0.py -q
services/api/.venv/bin/pytest services/api/tests/unit/integracoes/test_external_record_association_service.py -q
```

Resultado:

- `13 passed`
- `11 passed`

### Banco e Alembic

```bash
git diff --check
cd services/api && .venv/bin/python -m alembic heads
cd services/api && .venv/bin/python -m alembic current
cd services/api && .venv/bin/python -m alembic upgrade head
```

Resultado:

- `git diff --check`: OK
- `alembic heads`: `20260706_integrations_external_record_links_pending_local (head)`
- `alembic current`: `20260706_integrations_external_record_links_pending_local (head)`
- `alembic upgrade head`: concluído sem erros

### Confirmação adicional

```sql
SELECT version_num FROM farms.alembic_version;
```

Resultado:

- `20260706_integrations_external_record_links_pending_local`

## Resultado final

- P1 foi implementado apenas onde havia base segura.
- Pendências ficaram registradas como associações oficiais `PENDING`.
- `ExternalRecordAssociationService` foi reutilizado; nenhuma infraestrutura paralela foi criada.
- Nenhuma API pública foi alterada.
- `Gateway-first` permaneceu inalterado.
- Staging Sankhya continuou separado da associação oficial.
- Nenhuma entidade P2 foi implementada.
- Nenhuma escrita bidirecional foi criada.
