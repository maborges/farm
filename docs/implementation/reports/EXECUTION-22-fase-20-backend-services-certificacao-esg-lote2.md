# EXECUTION-22 - Fase 20 Backend Funcional Certificacoes/ESG Lote 2: Schemas e Services

## Objetivo
Implementar schemas Pydantic e services internos para evidencias, nao conformidades e planos de acao do dominio consumidor Certificacoes/ESG, sem expor API publica e sem alterar migrations.

## Arquivos criados
- `services/api/certificacoes_esg/schemas.py`
- `services/api/certificacoes_esg/service.py`
- `services/api/tests/unit/certificacoes_esg/test_schemas.py`
- `services/api/tests/unit/certificacoes_esg/test_service.py`
- `docs/implementation/reports/EXECUTION-22-fase-20-backend-services-certificacao-esg-lote2.md`

## Arquivos alterados
- `services/api/certificacoes_esg/models.py`
- `services/api/core/models/__init__.py`

## Schemas criados
- `EvidenciaCertificacaoCreate`
- `EvidenciaCertificacaoResponse`
- `NaoConformidadeCertificacaoCreate`
- `NaoConformidadeStatusUpdate`
- `NaoConformidadeCertificacaoResponse`
- `PlanoAcaoCertificacaoCreate`
- `PlanoAcaoStatusUpdate`
- `PlanoAcaoCertificacaoResponse`

## Services criados
- `CertificacoesESGService`
  - `criar_evidencia`
  - `listar_evidencias`
  - `criar_nao_conformidade`
  - `atualizar_status_nao_conformidade`
  - `criar_plano_acao`
  - `atualizar_status_plano_acao`
  - `listar_planos_acao`

## Regras validadas
- `titulo` nao vazio nas entidades criadas
- `origem_tipo` e `origem_id` obrigatorios para evidencias
- `snapshot_hash` obrigatorio quando `snapshot_json` existe
- `arquivo_hash` obrigatorio quando `arquivo_url` existe
- bloqueio de fontes oficiais territoriais/fundiarias em `origem_tipo`
- `prazo_correcao >= detectada_em` quando informado
- `resolvida_em >= detectada_em` quando informado
- `concluido_em >= created_at` quando informado
- `created_by` resolvido pelo usuario atual quando nao for informado
- filtragem por `tenant_id` em todas as consultas
- bloqueio de acesso cross-tenant na camada de service

## Integracao de bootstrap
- O bootstrap central `services/api/core/models/__init__.py` passou a importar:
  - `EvidenciaCertificacao`
  - `NaoConformidadeCertificacao`
  - `PlanoAcaoCertificacao`
- Os modelos do lote 1 permaneceram integrados.

## Ajustes de modelagem
- Corrigido o tipo do campo `origem_id` em `EvidenciaCertificacao` para `sa.Uuid(as_uuid=True)`.

## Testes executados
- `python3 -m py_compile services/api/certificacoes_esg/models.py services/api/certificacoes_esg/schemas.py services/api/certificacoes_esg/service.py services/api/tests/unit/certificacoes_esg/test_schemas.py services/api/tests/unit/certificacoes_esg/test_service.py services/api/core/models/__init__.py`
- `alembic heads`
- `.venv/bin/pytest services/api/tests/unit/certificacoes_esg/test_schemas.py services/api/tests/unit/certificacoes_esg/test_service.py services/api/tests/unit/test_certificacao_esg_bootstrap.py -q`
- `git diff --check --` nos arquivos desta fase

## Resultado dos testes
- `py_compile`: passou
- `alembic heads`: `20260621_certificacao_esg_lote2 (head)`
- `pytest`: `14 passed`
- `git diff --check`: sem problemas nos arquivos desta fase

## Necessidade de migration
- Nao houve necessidade de nova migration nesta fase.
- A base fisica do lote 2 ja existe; esta fase concentrou a camada de contrato e aplicacao.

## Riscos encontrados
- A tabela de planos de acao usa `prazo` nao nulo no banco; o service aplica um prazo padrao quando o campo nao vem informado para manter o contrato funcional.
- O status de nao conformidade continua como texto livre no modelo fisico, entao a disciplina de valores validos depende da camada de aplicacao.
- As consultas de listagem estao cobertas por tenant, mas a validacao de consistencia de referencias polimorficas ainda pode precisar de refinamento em fases futuras.

## Pendencias reais
- Nao existe API publica para estes contratos.
- Nao existe frontend para criacao/consulta operacional desses registros.
- Nao foi feita harmonizacao do dominio de status de nao conformidade com um enum nativo no banco.

## Recomendacao para a proxima fase
- Avancar para a exposicao controlada por router/API apenas depois de revisar os contratos publicos e definir se `NaoConformidade.status` deve permanecer textual ou migrar para enum em uma fase tecnica posterior.
