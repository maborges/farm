# EXECUTION-30 - Fase 28 Backend Funcional Relatorio ESG e Passaporte

## Resumo Executivo

Foi implementada a camada funcional interna do bloco `RelatorioESG` e `PassaporteRastreabilidade`, incluindo schemas Pydantic, services internos e testes unitários. A migration física já existia e permaneceu intacta nesta fase.

## Arquivos Criados

- `services/api/tests/unit/certificacoes_esg/test_relatorio_esg_schemas.py`
- `services/api/tests/unit/certificacoes_esg/test_passaporte_schemas.py`
- `services/api/tests/unit/certificacoes_esg/test_relatorio_passaporte_service.py`
- `docs/implementation/reports/EXECUTION-30-fase-28-backend-relatorio-esg-passaporte.md`

## Arquivos Alterados

- `services/api/certificacoes_esg/schemas.py`
- `services/api/certificacoes_esg/service.py`

## Schemas Criados

### Relatorio ESG

- `RelatorioESGCreate`
- `RelatorioESGUpdateStatus`
- `RelatorioESGResponse`
- `RelatorioESGIndicadorCreate`
- `RelatorioESGIndicadorResponse`
- `RelatorioESGEvidenciaCreate`
- `RelatorioESGEvidenciaResponse`

### Passaporte de Rastreabilidade

- `PassaporteRastreabilidadeCreate`
- `PassaporteRastreabilidadeUpdateStatus`
- `PassaporteRastreabilidadeResponse`
- `PassaporteRastreabilidadeEventoCreate`
- `PassaporteRastreabilidadeEventoResponse`
- `PassaporteRastreabilidadeEvidenciaCreate`
- `PassaporteRastreabilidadeEvidenciaResponse`

## Services Criados

### Relatorio ESG

- `criar_relatorio_esg`
- `listar_relatorios_esg`
- `atualizar_status_relatorio_esg`
- `adicionar_indicador_relatorio_esg`
- `vincular_evidencia_relatorio_esg`
- `listar_indicadores_relatorio_esg`
- `listar_evidencias_relatorio_esg`

### Passaporte

- `criar_passaporte_rastreabilidade`
- `listar_passaportes_rastreabilidade`
- `atualizar_status_passaporte_rastreabilidade`
- `adicionar_evento_passaporte`
- `vincular_evidencia_passaporte`
- `listar_eventos_passaporte`
- `listar_evidencias_passaporte`

## Regras Validadas

- `titulo` obrigatório e não vazio em relatórios e passaportes
- `periodo_fim >= periodo_inicio` quando ambos existem
- `versao >= 1`
- `snapshot_hash` obrigatório quando `snapshot_json` existe
- `publicado_em` obrigatório quando status é `PUBLICADO`
- `cancelado_em` obrigatório quando status é `CANCELADO`
- `revogado_em` obrigatório quando status é `REVOGADO`
- `valor >= 0` e `score >= 0` em indicadores
- `origem_tipo` e `origem_id` obrigatórios em eventos de passaporte
- tenant isolation aplicado em todas as consultas e vínculos
- bloqueio de fontes oficiais territoriais/fundiárias como origem para evidências

## Testes Executados

- `python3 -m py_compile services/api/certificacoes_esg/schemas.py services/api/certificacoes_esg/service.py services/api/tests/unit/certificacoes_esg/test_relatorio_esg_schemas.py services/api/tests/unit/certificacoes_esg/test_passaporte_schemas.py services/api/tests/unit/certificacoes_esg/test_relatorio_passaporte_service.py`
- `services/api/.venv/bin/pytest services/api/tests/unit/certificacoes_esg/test_relatorio_esg_schemas.py services/api/tests/unit/certificacoes_esg/test_passaporte_schemas.py services/api/tests/unit/certificacoes_esg/test_relatorio_passaporte_service.py -q`
- `services/api/.venv/bin/pytest services/api/tests/unit/certificacoes_esg/test_schemas.py services/api/tests/unit/certificacoes_esg/test_service.py services/api/tests/unit/test_certificacao_esg_bootstrap.py -q`

## Resultado dos Testes

- `17 passed`
- `15 passed`

## Necessidade de Migration

- Não houve necessidade de migration nesta fase

## Riscos Encontrados

- O worktree já possuía alterações fora do escopo desta fase
- Os enums físicos do bloco ESG/Passaporte foram validados na fase anterior e mantêm valores legados adicionais por compatibilidade

## Pendências Reais

- Nenhuma pendência bloqueante para avançar
- A API pública do bloco de relatório/passaporte ainda não foi exposta, conforme o escopo desta fase

## Recomendação para a Próxima Fase

- Avançar para a exposição pública protegida do bloco de relatório ESG e passaporte, reaproveitando os schemas e services aqui entregues
