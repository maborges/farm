# EXECUTION-20 - Fase 18 Validacao Runtime do Alembic e RLS Certificacoes/ESG Lote 1

## Banco usado na validacao
- PostgreSQL configurado em `services/api/.env.local`
- Host: `192.168.0.2`
- Database: `farms`
- Schema: `farms`

## Resultado da conectividade
- A porta `5432` respondeu.
- Houve oscilacao temporaria de conexao durante a validacao.
- O problema foi reduzido limpando sessoes extras do usuario `borgus` no banco de validacao.

## Ciclo Alembic executado
- `alembic heads`
- `alembic current`
- `alembic upgrade head`
- `alembic current`
- `alembic downgrade -1`
- `alembic current`
- `alembic upgrade head`
- `alembic current`

## Resultado do ciclo Alembic
- `alembic heads`: `20260621_certificacao_esg_lote1 (head)`
- `alembic current`: confirmou `20260621_certificacao_esg_lote1 (head)` apos a subida final.
- `alembic upgrade head`: concluido com sucesso.
- `alembic downgrade -1`: concluido com sucesso.
- A migration nova pode subir e descer sem quebrar o estado do banco.

## Validacao fisica no schema `farms`
- Tabelas validadas:
  - `certificacao_programas`
  - `certificacao_checklists`
  - `certificacao_criterios`
  - `certificacao_avaliacoes`
- Enums validados:
  - `status_programa_enum`
  - `tipo_certificacao_enum`
  - `status_checklist_enum`
  - `resultado_avaliacao_enum`
  - `tipo_evidencia_enum`
  - `severidade_nao_conformidade_enum`
  - `prioridade_plano_acao_enum`
  - `status_plano_acao_enum`
  - `status_relatorio_esg_enum`
  - `status_passaporte_enum`
- Constraints validadas:
  - `ck_certificacao_avaliacoes_nota_nao_negativa`
  - `ck_certificacao_criterios_peso_nao_negativo`
  - `ck_certificacao_checklists_percentual_conformidade`
  - FKs principais nas quatro tabelas
- Indices validados:
  - indices de `tenant_id`, FKs e indices compostos do lote 1
- `alembic_version` confirmou a head nova.

## Validacao RLS
- RLS habilitado nas quatro tabelas.
- RLS forcado nas quatro tabelas.
- Policies existentes para `SELECT`, `INSERT`, `UPDATE` e `DELETE`.
- Teste cross-tenant validado:
  - tenant de origem viu a linha inserida
  - tenant diferente nao viu a linha
  - insert cross-tenant foi bloqueado com `InsufficientPrivilegeError`

## Integracao de models
- Os models do lote 1 continuam integrados em `services/api/core/models/__init__.py`.

## Riscos encontrados
- O banco de validacao oscilou com timeout de conexao durante a sessao.
- Havia varias sessoes inativas do proprio ciclo de validacao; foi necessario limpa-las.
- Existe um ajuste minimo em uma migration anterior (`b1c2d3e4f5a7_add_imoveis_avaliacoes.py`) para evitar recriacao de enum nativo durante o upgrade.

## Pendencias reais
- Lote 2 de Certificacoes/ESG ainda nao foi iniciado.
- Convem manter monitoramento do volume de sessoes de validacao para nao repetir os timeouts.

## Recomendacao objetiva
- Pode avancar para o lote 2, desde que o banco de validacao permanezca acessivel e o ciclo Alembic continue repetivel.

