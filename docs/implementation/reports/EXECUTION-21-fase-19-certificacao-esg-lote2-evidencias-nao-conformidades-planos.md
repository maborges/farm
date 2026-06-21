# EXECUTION-21 - Fase 19 Certificacoes/ESG Lote 2: Evidencias, Nao Conformidades e Planos de Acao

## Objetivo
Implementar e validar o nucleo fisico do lote 2 do dominio consumidor Certificacoes/ESG, sem reaproveitar o modelo financeiro/IA de planos de acao e sem duplicar dados territoriais/fundiarios.

## Arquivos criados
- `services/api/certificacoes_esg/models.py` foi expandido com:
  - `EvidenciaCertificacao`
  - `NaoConformidadeCertificacao`
  - `PlanoAcaoCertificacao`
- `services/api/migrations/versions/20260621_certificacao_esg_lote2.py`
- `services/api/tests/unit/test_certificacao_esg_bootstrap.py` foi ampliado para cobrir o lote 2

## Tabelas criadas
- `certificacao_evidencias`
- `certificacao_nao_conformidades`
- `certificacao_planos_acao`

## Enums reutilizados
- `tipo_evidencia_enum`
- `severidade_nao_conformidade_enum`
- `prioridade_plano_acao_enum`
- `status_plano_acao_enum`

## FKs principais
- `certificacao_evidencias`
  - `tenant_id`
  - `programa_id`
  - `checklist_id`
  - `criterio_id`
  - `avaliacao_id`
  - `propriedade_id`
  - `imovel_rural_id`
  - `propriedade_imovel_id`
  - `responsavel_pessoa_id`
- `certificacao_nao_conformidades`
  - `tenant_id`
  - `programa_id`
  - `checklist_id`
  - `criterio_id`
  - `avaliacao_id`
  - `evidencia_id`
  - `propriedade_id`
  - `imovel_rural_id`
  - `propriedade_imovel_id`
  - `responsavel_pessoa_id`
- `certificacao_planos_acao`
  - `tenant_id`
  - `programa_id`
  - `nao_conformidade_id`
  - `evidencia_id`
  - `responsavel_pessoa_id`
  - `propriedade_id`
  - `imovel_rural_id`
  - `propriedade_imovel_id`

## Constraints
- `btrim(titulo) <> ''` nas tres tabelas
- `snapshot_json IS NULL OR snapshot_hash IS NOT NULL`
- `arquivo_url IS NULL OR arquivo_hash IS NOT NULL`
- `origem_tipo IS NOT NULL AND origem_id IS NOT NULL`
- `prazo_correcao IS NULL OR prazo_correcao >= detectada_em`
- `resolvida_em IS NULL OR resolvida_em >= detectada_em`
- `concluido_em IS NULL OR concluido_em >= created_at`
- `btrim(status) <> ''` na tabela de nao conformidades

## Indices
- Indices individuais nas FKs requisitadas
- Indices compostos por `tenant_id` + status/prioridade/prazo quando aplicavel
- Indices por `tipo_evidencia` e `publico` em evidencias
- Indices por `severidade` e `prazo_correcao` em nao conformidades
- Indices por `prioridade` e `prazo` em planos de acao

## RLS implementado
- `ENABLE ROW LEVEL SECURITY`
- `FORCE ROW LEVEL SECURITY`
- Policies `SELECT`, `INSERT`, `UPDATE`, `DELETE` em todas as tres tabelas
- Acesso cross-tenant bloqueado com `InsufficientPrivilegeError`

## Resultado Alembic runtime
- `alembic heads`: `20260621_certificacao_esg_lote2 (head)`
- `alembic current`: confirmou `20260621_certificacao_esg_lote2 (head)`
- `alembic upgrade head`: sucesso
- `alembic downgrade -1`: sucesso
- `alembic upgrade head`: sucesso novamente

## Resultado dos testes
- `python3 -m py_compile`: passou
- `pytest services/api/tests/unit/test_certificacao_esg_bootstrap.py -q`: `1 passed`
- `git diff --check` nos arquivos desta fase: sem problemas

## Riscos encontrados
- A validacao runtime depende da disponibilidade do banco de desenvolvimento e pode oscilar por excesso de sessoes abertas.
- O lote 2 introduz muitas colunas opcionais e FKs polimorficas; a camada de aplicacao futura precisa validar consistencia de origem.

## Pendencias reais
- Ainda nao ha API, schema Pydantic ou frontend para as novas entidades.
- Os fluxos de negocio de evidencias, nao conformidades e planos de acao seguem pendentes de implementacao.

## Recomendacao para a proxima fase
- Prosseguir com o lote 3 apenas depois de confirmar que as novas tabelas estao sendo consumidas pela aplicacao sem violar o isolamento por tenant e sem reaproveitar `PlanoAcaoItem` legado.

