# TENANT-INTEGRITY-REPAIR-01D — Auditoria Final

## Resumo da auditoria

Auditoria exclusivamente de leitura realizada sobre a migration existente
`tenant_fk_repair_01d` e sobre o catálogo atual do PostgreSQL.

| Questão | Conclusão |
|---|---|
| A `01D` altera tabelas já modificadas? | Não altera nenhuma FK criada em `01B2`–`01B5`, pois essas 29 FKs usam `NO ACTION` e o filtro seleciona somente `CASCADE`. Há sobreposição com oito tabelas tratadas em `01C`, mas apenas nas FKs diretas antigas `tenant_id → tenants(id)`; as FKs compostas da `01C` não são selecionadas. |
| Recriação desnecessária de FK | Não. O catálogo contém exatamente 200 FKs diretas `CASCADE`, sem duplicatas, e todas precisam mudar para cumprir o objetivo da `01D`. |
| `ON DELETE` já absorvido | As fases `01B2`–`01B5` já criaram suas FKs com `NO ACTION`; a `01D` as ignora corretamente. Nenhuma das 200 conversões `CASCADE → RESTRICT` foi absorvida pelas fases anteriores. |
| Operação obsoleta | Nenhuma operação executável do `upgrade()` tornou-se obsoleta. Apenas a observação textual de que existiriam duas FKs `NO ACTION` está desatualizada: atualmente existem 31. |
| Segurança do upgrade | A lógica SQL permanece correta: as 200 FKs estão validadas, pertencem ao schema `farms`, usam exclusivamente `tenant_id → tenants(id)`, não são deferrable e não possuem regras especiais de `MATCH` ou `ON UPDATE` que seriam perdidas. |
| `down_revision` | Correto no working tree auditado: `tenant_integrity_repair_01b5_sankhya`. O grafo resulta em `01B4 → 01B5 → 01D`, com head único em `tenant_fk_repair_01d`. |
| Conflito com o banco atual | Não há conflito físico: `farms.alembic_version` está em `tenant_integrity_repair_01b5_sankhya`; há 200 FKs `CASCADE`, 31 `NO ACTION`, zero `RESTRICT` e zero FK direta para `tenants` pendente de validação. |

## Operações ainda válidas

- Selecionar dinamicamente somente FKs diretas para `farms.tenants(id)` com
  `ON DELETE CASCADE`.
- Recriar as 200 constraints preservando tabela, nome e coluna
  `tenant_id`, alterando apenas a regra para `ON DELETE RESTRICT`.
- Criar as constraints como `NOT VALID` e validá-las no mesmo upgrade.
- Preservar integralmente as 31 FKs atuais com `ON DELETE NO ACTION`, incluindo
  todas as FKs implantadas em `01B2`–`01B5`.
- Não tocar nas FKs compostas implantadas em `01C`, pois elas não referenciam
  diretamente `farms.tenants`.

## Operações obsoletas

Nenhuma operação executável do `upgrade()` está obsoleta.

A referência descritiva a apenas duas FKs `NO ACTION` está desatualizada, mas
não interfere na seleção dinâmica nem no resultado da migration.

## Riscos encontrados

- As operações `ALTER TABLE ... DROP/ADD CONSTRAINT` adquirem locks fortes. Como
  as 200 alterações ocorrem na mesma transação, os locks permanecem até o
  commit; a janela de manutenção prevista no plano original continua
  obrigatória. No banco auditado, a maior tabela selecionada tem cerca de
  2,2 MB, reduzindo o risco atual de duração da validação.
- O `downgrade()` é amplo: converte toda FK `RESTRICT` para `tenants` existente
  no momento do rollback, e não apenas as constraints alteradas pelo upgrade.
  Um rollback imediato alcançaria as mesmas 200 FKs, pois atualmente existem
  zero FKs `RESTRICT`; após mudanças futuras, o downgrade pode abranger FKs que
  não pertencem à `01D`.
- O carregamento convencional do ambiente Alembic está bloqueado antes da
  execução da migration por `sqlalchemy.exc.InvalidRequestError: This
  ForeignKey already has a parent` em `integracoes/models.py`. A SQL da `01D`
  não causa esse erro, mas o comando `alembic current` não completa no estado
  auditado.
- O encadeamento `01B5 → 01D` e o arquivo da migration `01B5` estão corretos no
  working tree auditado, porém ainda não constam no `HEAD` Git atual. Executar
  a partir de outro checkout pode restaurar o encadeamento antigo e conflitar
  com o banco já posicionado em `01B5`.

## Recomendação

**GO COM RESSALVAS**

O `upgrade()` da `tenant_fk_repair_01d` permanece tecnicamente correto e não
conflita com as fases encerradas `01C` e `01B2`–`01B5`. A execução deve usar
exatamente o grafo auditado, ocorrer na janela de manutenção já prevista e
utilizar um caminho Alembic capaz de carregar a migration. O `downgrade()` não
deve ser tratado como rollback genérico após mudanças posteriores de schema.
