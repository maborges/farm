# EXECUTION-29 - Fase 27 Migration Relatorio ESG e Passaporte de Rastreabilidade

## Resumo Executivo

Foi concluída a migration física do bloco canônico de `RelatorioESG` e `PassaporteRastreabilidade`, com integração dos novos models SQLAlchemy ao bootstrap da API e validação runtime completa via Alembic no PostgreSQL do projeto.

## Arquivos Criados

- `services/api/migrations/versions/20260621_certificacao_esg_relatorio_passaporte.py`
- `docs/implementation/reports/EXECUTION-29-fase-27-migration-relatorio-esg-passaporte.md`

## Arquivos Alterados

- `services/api/certificacoes_esg/models.py`
- `services/api/core/models/__init__.py`
- `services/api/tests/unit/test_certificacao_esg_bootstrap.py`

## Modelagem Física Entregue

### Tabelas criadas

- `esg_relatorios`
- `esg_relatorio_indicadores`
- `esg_relatorio_evidencias`
- `rastreabilidade_passaportes`
- `rastreabilidade_passaporte_eventos`
- `rastreabilidade_passaporte_evidencias`

### Enums criados / reutilizados

- `tipo_evento_passaporte_enum` criado fisicamente na migration
- `status_relatorio_esg_enum` reutilizado e expandido com `CANCELADO`
- `status_passaporte_enum` reutilizado e expandido com `EM_VALIDACAO` e `PUBLICADO`

### Campos e regras principais

- `RelatorioESG`
  - `titulo` obrigatório e não vazio
  - `periodo_fim >= periodo_inicio` quando ambos existirem
  - `versao >= 1`
  - `snapshot_hash` obrigatório quando status é `PUBLICADO`
  - `publicado_em` obrigatório quando status é `PUBLICADO`
  - `cancelado_em` obrigatório quando status é `CANCELADO`

- `RelatorioESGIndicador`
  - `nome` obrigatório e não vazio
  - `valor >= 0` quando informado
  - `score >= 0` quando informado

- `RelatorioESGEvidencia`
  - vínculo direto do relatório com evidências da certificação

- `PassaporteRastreabilidade`
  - `titulo` obrigatório e não vazio
  - `versao >= 1`
  - `snapshot_hash` obrigatório quando status é `PUBLICADO`
  - `publicado_em` obrigatório quando status é `PUBLICADO`
  - `revogado_em` obrigatório quando status é `REVOGADO`
  - vínculos opcionais com `programa`, `propriedade`, `imóvel rural`, `propriedade_imovel`, `lote_rastreabilidade` e `caderno_lotes_comerciais`

- `PassaporteRastreabilidadeEvento`
  - `titulo` obrigatório e não vazio
  - `origem_tipo` e `origem_id` obrigatórios
  - `snapshot_hash` obrigatório quando `snapshot_json` existir

- `PassaporteRastreabilidadeEvidencia`
  - vínculo direto entre passaporte e evidência

### FKs principais

- `tenant_id` em todas as tabelas
- `programa_id` em relatórios e passaportes
- `propriedade_id`, `imovel_rural_id`, `propriedade_imovel_id` em relatórios e passaportes
- `responsavel_pessoa_id` em relatórios e passaportes
- `created_by` em relatórios e passaportes
- `relatorio_id` e `evidencia_id` nas tabelas de vínculo do relatório
- `passaporte_id` e `evidencia_id` nas tabelas de vínculo do passaporte
- `lote_rastreabilidade_id` e `caderno_lote_comercial_id` em `rastreabilidade_passaportes`

### Índices

Os índices esperados foram criados e validados no runtime, incluindo:

- `tenant_id`
- `status`
- `publico`
- `programa_id`
- `propriedade_id`
- `imovel_rural_id`
- `propriedade_imovel_id`
- `relatorio_id`
- `passaporte_id`
- `evidencia_id`
- `tipo_evento`
- compostos `tenant_id + status`
- compostos `tenant_id + publico`

### RLS

Foi habilitado e validado em runtime:

- `ENABLE ROW LEVEL SECURITY`
- `FORCE ROW LEVEL SECURITY`
- policies `SELECT`, `INSERT`, `UPDATE` e `DELETE` tenant-aware em todas as seis tabelas

## Bootstrap Atualizado

- `services/api/core/models/__init__.py` passou a importar:
  - `RelatorioESG`
  - `RelatorioESGIndicador`
  - `RelatorioESGEvidencia`
  - `PassaporteRastreabilidade`
  - `PassaporteRastreabilidadeEvento`
  - `PassaporteRastreabilidadeEvidencia`

- `services/api/tests/unit/test_certificacao_esg_bootstrap.py` passou a validar as seis novas tabelas na metadata

## Comandos Executados

- `git status --short`
- `alembic heads`
- `python3 -m py_compile services/api/certificacoes_esg/models.py services/api/migrations/versions/20260621_certificacao_esg_relatorio_passaporte.py`
- `services/api/.venv/bin/pytest services/api/tests/unit/test_certificacao_esg_bootstrap.py -q`
- `timeout 20s /opt/lampp/htdocs/farm/.venv/bin/alembic current`
- `timeout 120s /opt/lampp/htdocs/farm/.venv/bin/alembic upgrade head`
- `timeout 120s /opt/lampp/htdocs/farm/.venv/bin/alembic downgrade -1`
- `timeout 120s /opt/lampp/htdocs/farm/.venv/bin/alembic upgrade head`
- Consultas SQL em `pg_tables`, `pg_type`, `pg_policy`, `pg_indexes` e `information_schema.columns`
- `git diff --check`

## Resultado dos Testes

- `pytest services/api/tests/unit/test_certificacao_esg_bootstrap.py -q`: `1 passed`
- `py_compile`: passou
- `git diff --check` global: encontrou whitespace legado fora do escopo em arquivos já sujos do worktree
- `git diff --check` focalizado nos arquivos desta fase: sem problemas

## Resultado Alembic Runtime

- `alembic current`: validado antes e depois do ciclo
- `alembic upgrade head`: concluído com sucesso
- `alembic downgrade -1`: concluído com sucesso
- `alembic upgrade head`: concluído com sucesso

### Estado físico validado

- As seis tabelas novas existem no schema `farms`
- Os enums físicos relevantes existem e contêm os valores esperados
- As policies RLS existem para as seis tabelas

## Riscos Encontrados

- O worktree já estava sujo com alterações fora do escopo desta fase
- O `git diff --check` global acusou trailing whitespace legado em arquivos não tocados nesta fase
- O enum legado físico ainda contém valores históricos antigos além dos novos valores oficiais, o que é aceitável no momento porque a migração reutiliza o tipo existente e expandiu-o sem recriá-lo

## Pendências Reais

- Nenhuma pendência bloqueante para avançar para a fase seguinte
- Se for desejado, uma fase posterior pode limpar/normalizar os valores históricos remanescentes nos enums legados, desde que isso seja tratado com cautela por causa de compatibilidade

## Recomendação para a Próxima Fase

- Avançar para o próximo bloco funcional do domínio de Certificações/ESG, mantendo o padrão de migration pequena, validação runtime e RLS tenant-aware
