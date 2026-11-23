# EXECUTION-19 - Fase 17 Validacao Migration Certificacoes/ESG Lote 1

## Objetivo
Validar em runtime a migration do lote 1 de Certificações/ESG e integrar os novos models ao bootstrap central da API quando necessário.

## Escopo executado
- Revisao da nova head Alembic.
- Integracao do modulo `certificacoes_esg` ao bootstrap central de `core.models`.
- Criacao de teste minimo de metadata para o dominio novo.
- Tentativa de validacao runtime via Alembic.

## Resultado da validacao
- `alembic heads`: a nova head permanece como `20260621_certificacao_esg_lote1`.
- `python3 -m py_compile`: passou para os arquivos novos e para o bootstrap atualizado.
- `pytest tests/unit/test_certificacao_esg_bootstrap.py -q`: 1 teste passou.

## Validacao Alembic
Comandos tentados:
- `alembic current`
- `alembic upgrade head`
- `alembic downgrade -1`

Resultado:
- A validacao de runtime ficou bloqueada por indisponibilidade de conexao com o banco configurado em `services/api/.env.local`.
- A URL aponta para `postgresql+asyncpg://borgus:numsey01@192.168.0.2/farms`.
- Nao havia processo Postgres local ativo no ambiente, e os comandos Alembic nao conseguiram completar a conexao.
- Nao foi possivel confirmar upgrade/downgrade no schema `farms` neste runtime.

## Bootstrap de models
- O arquivo `services/api/core/models/__init__.py` foi atualizado para importar:
  - `ProgramaCertificacao`
  - `ChecklistCertificacao`
  - `CriterioCertificacao`
  - `AvaliacaoCertificacao`
- Isso registra as novas tabelas na `Base.metadata` e habilita `create_all`/autogenerate futuros.

## Teste criado
- `services/api/tests/unit/test_certificacao_esg_bootstrap.py`

## Riscos e pendencias
- Validacao runtime do Alembic pendente ate que o banco Postgres local esteja acessivel.
- O lote 2 do dominio segue pendente.
- `git diff --check` global ainda acusa whitespace legado fora do escopo.

## Recomendacao para o lote 2
- Subir/garantir acesso ao Postgres de desenvolvimento.
- Reexecutar `alembic current`, `upgrade head`, `downgrade -1`, `upgrade head`.
- Prosseguir com o lote 2 apenas apos confirmacao de ida e volta da migration do lote 1.

