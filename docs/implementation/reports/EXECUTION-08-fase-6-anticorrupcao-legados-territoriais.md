# EXECUTION-08 - Fase 6 Disciplina de Leitura/Escrita e Anticorrupcao dos Legados da Convergencia Propriedades x Imoveis Rurais

## Objetivo

Impedir que espelhos legados e tabelas de apoio antigas continuem sendo interpretados como fonte oficial no dominio territorial/fundiario.

## Status

Fase 6 concluida com sucesso.

## O que foi consolidado

### Fonte oficial operacional

- `Propriedades`, `AreaRural` e `ExploracaoRural` continuam sendo a origem oficial do territorio operacional.

### Fonte oficial fundiaria

- `Imoveis Rurais`, `DocumentoLegal`, `ContratoArrendamento`, `AvaliacaoImovel`, `Cartorio` e `MatriculaImovelRural` continuam sendo a origem oficial do lastro juridico/documental.

### Fonte oficial de vinculacao

- `PropriedadeImovel` continua sendo a unica ponte canonica N:N.

### Legados e compatibilidade

- `unidades_produtivas` permanece apenas como compatibilidade historica para campos como `codigo_car`, `nirf`, `ccir` e `sigef_codigo`.
- `cadastros_areas_matriculas` e `cadastros_areas_registros_ambientais` permanecem como suportes historicos e nao podem virar master data.
- A nova norma de anticorrupcao deixa isso explicito.

## Arquivos criados nesta fase

- `docs/architecture/territorial-legacy-anticorruption-rules.md`
- `docs/implementation/reports/EXECUTION-08-fase-6-anticorrupcao-legados-territoriais.md`
- `services/api/tests/unit/test_territorial_anticorruption.py`
- `services/api/tests/integration/test_territorial_anticorruption.py`

## Arquivos alterados nesta fase

- `docs/architecture/agricultural-land-document-governance.md`
- `docs/implementation/reports/EXECUTION-07-fase-5-governanca-documental-territorial.md`

## Comandos executados

- `git status --short`
- `.venv/bin/alembic -c services/api/alembic.ini heads`
- `sed -n` e `rg -n` nos modelos, services, schemas e documentos territoriais/fundiarios
- `.venv/bin/pytest services/api/tests/unit/test_territorial_anticorruption.py services/api/tests/integration/test_territorial_anticorruption.py -q`
- `.venv/bin/pytest services/api/tests/unit/test_territorial_anticorruption.py services/api/tests/integration/test_territorial_anticorruption.py services/api/tests/unit/test_document_governance.py services/api/tests/integration/test_document_governance.py services/api/tests/unit/test_territorial_compatibility.py services/api/tests/integration/test_territorial_convergence_compatibility.py -q`

## Resultado dos testes

- Suite nova de anticorrupcao: `9 passed`
- Suite cruzada de anticorrupcao + governanca documental + compatibilidade territorial: `11 passed`

## Pontos legados identificados

- `unidades_produtivas.codigo_car`
- `unidades_produtivas.nirf`
- `unidades_produtivas.ccir`
- `unidades_produtivas.sigef_codigo`
- `cadastros_areas_matriculas`
- `cadastros_areas_registros_ambientais`
- `core/routers/fazendas.py` como shim de compatibilidade

## Riscos reais

- `SIGEF` ainda depende de consolidação fisica futura no dominio fundiario canonico.
- Espelhos legados podem ser reintroduzidos como fonte oficial se novos consumidores ignorarem a norma.
- Rotas e telas antigas podem continuar sugerindo edicao em dados que agora devem ser somente leitura/compatibilidade.

## Necessidade de migrations adicionais

Nao. Esta fase e puramente normativa e de protecao arquitetural.

## Pendencias reais

- Validacao pela arquitetura e por produto.
- Eventual saneamento fisico dos espelhos legados, se aprovado em ADR futura.

## Recomendacao para a proxima fase

Manter a escrita restrita as fontes oficiais, manter os espelhos somente como compatibilidade historica e, se houver necessidade de remoção fisica, abrir um ciclo separado com ADR propria.

## Correcoes de consistencia

- O relatorio da Fase 5 foi ajustado para registrar que os testes foram aprovados.
- O texto final nao deixa mais pendencia automatica ficticia.
