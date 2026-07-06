# Checklist de Revisão - Ownership Cross-Módulo

## Objetivo

Evitar que novas funcionalidades criem tabelas, cadastros ou fluxos paralelos para entidades que já possuem fonte oficial definida no SaaS agro.

Este checklist deve ser usado antes de aprovar PRs, histórias técnicas, novas migrations, novos models, novos routers ou novos fluxos de integração entre módulos.

## Base obrigatória

- `docs/contexts/step48-cross-module-ownership-context.md`
- `docs/contexts/step49-cross-module-migration-plan-context.md`

Qualquer exceção precisa citar explicitamente o Step 48, explicar por que a fonte oficial atual não atende e documentar ownership, consumidores, plano de migração e risco de duplicidade.

## Regra geral

Antes de criar qualquer tabela, model, schema, service, router ou fluxo operacional, responder:

1. A entidade já existe no Step 48?
2. O novo requisito é uma entidade nova ou uma especialização de uma entidade oficial?
3. O módulo pode consumir a fonte oficial por FK, id lógico ou `origem_tipo/origem_id`?
4. Existe tabela legada que deve ser tratada apenas como compatibilidade?
5. A mudança cria novo cadastro, novo estoque, novo financeiro ou nova geografia produtiva em paralelo?

Se a resposta indicar duplicidade, não criar nova tabela. Integrar com a fonte oficial ou abrir decisão arquitetural específica.

## Verificações por entidade

### Pessoa, fornecedor, cliente e prestador

- [ ] Não criar tabela local de `fornecedores`, `clientes` ou `prestadores`.
- [ ] Usar `cadastros_pessoas` como fonte oficial.
- [ ] Representar papel via relacionamento/papel de pessoa.
- [ ] Em Compras, tratar `compras_fornecedores` como legado em migração para pessoa com papel `FORNECEDOR`.
- [ ] Em Vendas, Financeiro e Fiscal, evitar texto livre quando houver pessoa oficial.

Fonte oficial: `services/api/core/cadastros/pessoas/models.py`.

### Produto, insumo e cultura

- [ ] Não criar catálogo local de produto, insumo, peça ou cultura por módulo.
- [ ] Usar `cadastros_produtos` para produto/insumo.
- [ ] Usar `cadastros_culturas` para cultura agrícola.
- [ ] Não criar `insumos_agricolas`, `insumos_pecuarios`, `produtos_estoque` ou equivalentes locais.
- [ ] Tratar `services/api/agricola/cadastros/models.py` (`culturas`) como legado a depreciar.

Fonte oficial: `services/api/core/cadastros/produtos/models.py`.

### Fazenda, unidade produtiva e área rural

- [ ] Não criar nova tabela `fazendas`.
- [ ] Usar `unidades_produtivas` para fazenda/unidade produtiva.
- [ ] Usar `cadastros_areas_rurais` para área rural, talhão, piquete, curral e estruturas territoriais.
- [ ] Não criar geografia produtiva separada em Agricultura ou Pecuária.
- [ ] Tratar `pec_piquetes` como legado em migração para área rural tipo `PIQUETE`.

Fontes oficiais:

- `services/api/core/models/unidade_produtiva.py`
- `services/api/core/cadastros/propriedades/models.py`

### Equipamento, máquina e veículo

- [ ] Não criar `maquina_veiculo`, `frota_maquinarios` ou cadastro local de máquinas/veículos.
- [ ] Usar `cadastros_equipamentos`.
- [ ] Preferir `equipamento_id` em novos contratos.
- [ ] Tratar `maquinario_id` apenas como alias de compatibilidade quando necessário.
- [ ] Consolidar custos de Frota/Máquinas por equipamento oficial.

Fonte oficial: `services/api/core/cadastros/equipamentos/models.py`.

### Estoque, movimentação, saldo e lote

- [ ] Não criar estoque agrícola, estoque pecuário, estoque de frota ou ledger por módulo.
- [ ] Usar `estoque_movimentos` como ledger oficial para novos fluxos.
- [ ] Usar `estoque_saldos` para saldo operacional reconciliável.
- [ ] Usar `estoque_lotes` para lote/rastreabilidade.
- [ ] Todo novo fluxo operacional deve informar `origem_tipo/origem_id`, exceto lançamento manual documentado.

Fonte oficial: `services/api/operacional/models/estoque.py`.

### Financeiro, receita e despesa

- [ ] Não criar financeiro agrícola, pecuário, de frota ou comercial paralelo.
- [ ] Usar `fin_receitas` e `fin_despesas`.
- [ ] Padronizar `origem_tipo/origem_id` em novos fluxos de Pecuária, Frota, Compras e Vendas.
- [ ] Não criar `lancamento_financeiro` físico sem RFC/plano de migração.
- [ ] Não confundir plano de contas com centro de custo gerencial.

Fontes oficiais:

- `services/api/financeiro/models/receita.py`
- `services/api/financeiro/models/despesa.py`

### Piquete, talhão e curral

- [ ] Não criar tabelas separadas de piquete, talhão ou curral para novos fluxos.
- [ ] Usar `cadastros_areas_rurais` com tipo adequado.
- [ ] Em Pecuária, preferir `area_id` para lotes e manejos.
- [ ] Em Agricultura, manter talhões dentro da hierarquia de área rural.
- [ ] APIs legadas podem manter aliases, mas novas integrações devem usar a fonte oficial.

Fonte oficial: `services/api/core/cadastros/propriedades/models.py`.

## Checklist para PR

- [ ] O PR cita a fonte oficial da entidade compartilhada.
- [ ] O PR não adiciona tabela paralela para entidade já oficial.
- [ ] O PR não adiciona migration para cadastro duplicado.
- [ ] O PR não cria estoque ou financeiro isolado por módulo.
- [ ] O PR não cria fornecedor/cliente/prestador fora de `cadastros_pessoas`.
- [ ] O PR não cria produto/insumo/cultura fora dos cadastros oficiais.
- [ ] O PR usa `equipamento_id` para Frota/Máquinas em novos contratos.
- [ ] O PR usa `area_id`/área rural oficial para talhão, piquete e curral em novos contratos.
- [ ] O PR preserva compatibilidade apenas quando o Step 48/49 indicam legado existente.
- [ ] Qualquer exceção cita o Step 48 e documenta ownership, consumidores, risco e plano de migração.

## Nomes que exigem atenção especial

Novos models ou tabelas com os nomes abaixo devem ser bloqueados ou justificados como exceção arquitetural:

- `fazendas`
- `fornecedores`
- `clientes`
- `produtos_estoque`
- `insumos_agricolas`
- `estoque_agricola`
- `estoque_pecuario`
- `maquina_veiculo`

Exceções já mapeadas como legado ou fonte oficial não autorizam recriação em novos módulos.
