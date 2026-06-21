# EXECUTION-23 - Fase 21 Normalizacao do Status de Nao Conformidade Certificacoes/ESG

## Objetivo
Normalizar fisicamente o status de nao conformidade do dominio Certificacoes/ESG antes da exposicao por API publica, usando enum nativo PostgreSQL.

## Estrategia adotada
- Estrategia escolhida: enum nativo PostgreSQL `status_nao_conformidade_enum`.
- Motivo: o dominio ja estava isolado por tenant/RLS, e o status textual era o unico ponto ainda dependente de disciplina de aplicacao.
- Escopo da migration: pequeno e localizado na coluna `status` de `certificacao_nao_conformidades`.

## Arquivos criados
- `services/api/migrations/versions/20260621_certificacao_esg_status_nao_conformidade.py`
- `docs/implementation/reports/EXECUTION-23-fase-21-status-nao-conformidade-certificacao-esg.md`

## Arquivos alterados
- `services/api/certificacoes_esg/models.py`
- `services/api/certificacoes_esg/schemas.py`
- `services/api/certificacoes_esg/service.py`
- `services/api/tests/unit/certificacoes_esg/test_schemas.py`
- `services/api/tests/unit/certificacoes_esg/test_service.py`

## Enum/constraint criada
- Enum nativo PostgreSQL: `status_nao_conformidade_enum`
- Alteracao aplicada em: `certificacao_nao_conformidades.status`

## Valores oficiais
- `ABERTA`
- `EM_ANALISE`
- `EM_CORRECAO`
- `RESOLVIDA`
- `CANCELADA`

## Ajustes de codigo
- `NaoConformidadeCertificacao.status` passou a ser enum nativo no model SQLAlchemy.
- `NaoConformidadeCertificacaoCreate.status` passou a usar `StatusNaoConformidade`.
- `NaoConformidadeStatusUpdate.status` passou a usar `StatusNaoConformidade`.
- `NaoConformidadeCertificacaoResponse.status` passou a usar `StatusNaoConformidade`.
- `CertificacoesESGService` passou a comparar e atualizar o status como enum.

## Testes executados
- `python3 -m py_compile services/api/certificacoes_esg/models.py services/api/certificacoes_esg/schemas.py services/api/certificacoes_esg/service.py services/api/migrations/versions/20260621_certificacao_esg_status_nao_conformidade.py services/api/tests/unit/certificacoes_esg/test_schemas.py services/api/tests/unit/certificacoes_esg/test_service.py services/api/tests/unit/test_certificacao_esg_bootstrap.py`
- `.venv/bin/pytest services/api/tests/unit/certificacoes_esg/test_schemas.py services/api/tests/unit/certificacoes_esg/test_service.py services/api/tests/unit/test_certificacao_esg_bootstrap.py -q`
- `.venv/bin/alembic current`
- `.venv/bin/alembic upgrade head`
- `.venv/bin/alembic downgrade -1`
- `.venv/bin/alembic upgrade head`
- `.venv/bin/alembic current`
- Inspecao SQL no banco PostgreSQL via `information_schema`, `pg_type`, `pg_policies` e `pg_indexes`
- `git diff --check` nos arquivos desta fase

## Resultado dos testes
- `py_compile`: passou
- `pytest`: `15 passed`
- `alembic current`: confirmou a head anterior e depois a nova head da migration tecnica
- `alembic upgrade head`: sucesso
- `alembic downgrade -1`: sucesso
- `alembic upgrade head` final: sucesso

## Resultado runtime
- Banco usado: PostgreSQL de desenvolvimento configurado em `services/api/.env.local`
- Schema ativo: `farms`
- O tipo nativo `status_nao_conformidade_enum` foi criado no schema `farms`
- A coluna `certificacao_nao_conformidades.status` foi convertida para o enum nativo
- RLS permaneceu habilitado e com policies tenant-aware nas tabelas do dominio

## Validacao SQL
- Tabela validada: `certificacao_nao_conformidades`
- Tipo validado: `status_nao_conformidade_enum`
- Policies validadas:
  - `certificacao_nao_conformidades_select_tenant`
  - `certificacao_nao_conformidades_insert_tenant`
  - `certificacao_nao_conformidades_update_tenant`
  - `certificacao_nao_conformidades_delete_tenant`
- Indices validados:
  - indices por `tenant_id`, `programa_id`, `checklist_id`, `criterio_id`, `avaliacao_id`, `evidencia_id`, `severidade`, `status`
  - indices compostos de tenant usados pela camada de consulta

## Necessidade de novas mudancas antes da API publica
- Nao ha necessidade de novas mudancas estruturais imediatas.
- O dominio agora tem o ponto fisico mais sensivel normalizado.
- A proxima etapa pode focar na exposicao controlada por router/API.

## Riscos encontrados
- `certificacao_nao_conformidades.status` segue sem transicao de estado formalizada na camada de dominio; isso pode ser refinado mais adiante.
- A migration depende de o banco de desenvolvimento estar acessivel; neste ambiente ela funcionou, mas a validacao exige permissao de rede do sandbox.

## Pendencias reais
- Nao existe API publica ainda.
- Nao existe frontend ainda.
- Nao existe validacao de transicao de status por maquina de estados.

## Recomendacao para a proxima fase
- Avancar para a exposicao publica controlada do dominio apenas depois de definir as transicoes aceitas para `status_nao_conformidade_enum` e consolidar os contratos HTTP.
