# EXECUTION-07 - Fase 5 Consolidacao Documental e Operacional da Convergencia Propriedades x Imoveis Rurais

## Objetivo

Consolidar a governanca documental do dominio territorial/fundiario, validar a separacao entre fonte operacional, fonte documental e fonte de vinculacao, e confirmar que nao ha necessidade de nova migracao nesta fase.

## Status

Fase 5 concluida com sucesso.

## O que foi consolidado

### Dominio documental fundiario

- `Imoveis Rurais` permanece como fonte oficial de CAR, CCIR, ITR, NIRF, matriculas, cartorios, contratos e avaliacoes.
- `DocumentoLegal`, `ContratoArrendamento`, `AvaliacaoImovel`, `Cartorio` e `MatriculaImovelRural` continuam concentrados no dominio fundiario.

### Dominio operacional territorial

- `Propriedades` permanece como fonte oficial de area rural operacional, glebas, talhoes, infraestrutura e evidencias de exploracao.
- `AreaRural`, `ExploracaoRural`, `DocumentoExploracao`, `RegistroAmbiental` e `ArquivoGeo` continuam representando a camada operacional.

### Vinculo canonic

- `PropriedadeImovel` permanece como unica ponte N:N.
- A entidade nao armazena documentos completos nem lastro fundiario completo.

## Matriz documental consolidada

Documento auditado na nova norma:

- CAR
- CCIR
- ITR
- NIRF
- SIGEF
- Matriculas
- Cartorios
- Contratos
- Avaliacoes
- APP
- Reserva Legal
- Licencas Ambientais
- Arquivos geoespaciais
- Historicos de documento

## Arquivos criados nesta fase

- `docs/architecture/agricultural-land-document-governance.md`
- `docs/architecture/adr/ADR-00XY-governanca-documental-territorial.md`
- `docs/implementation/reports/EXECUTION-07-fase-5-governanca-documental-territorial.md`
- `services/api/tests/unit/test_document_governance.py`
- `services/api/tests/integration/test_document_governance.py`

## Arquivos alterados nesta fase

Nenhum arquivo de codigo legado foi alterado nesta fase. Apenas novos documentos, testes e este relatorio foram adicionados.

## Comandos executados

- `git status --short`
- `.venv/bin/alembic -c services/api/alembic.ini heads`
- `sed -n` e `rg -n` nos modelos, services e documentos territoriais/fundiarios
- `.venv/bin/pytest services/api/tests/unit/test_document_governance.py services/api/tests/integration/test_document_governance.py -q`
- `.venv/bin/pytest services/api/tests/unit/test_document_governance.py services/api/tests/integration/test_document_governance.py services/api/tests/unit/test_territorial_compatibility.py services/api/tests/integration/test_territorial_convergence_compatibility.py -q`

## Resultado da analise

- Os modelos atuais ja separam a fonte oficial operacional da fonte oficial fundiaria.
- Os espelhos legados ainda existem em `unidades_produtivas` e em tabelas antigas de apoio, mas nao exigem nova migration para esta fase.
- `PropriedadeImovel` permanece corretamente limitada ao papel de vinculacao.
- A nova norma documental nao introduz novos campos nem novas tabelas.

## Testes executados

### Validados nesta fase

- `services/api/tests/unit/test_document_governance.py`
- `services/api/tests/integration/test_document_governance.py`

Resultado:

- `6 passed`
- Validacao cruzada territorial/documental: `11 passed`

## Riscos encontrados

- Espelhos legados ainda persistem em tabelas antigas e podem induzir leitura incorreta se tratados como fonte oficial.
- `SIGEF` ainda nao esta consolidado fisicamente no dominio fundiario canonicamente definido.
- A separacao de escrita entre dominio oficial e compatibilidade precisa continuar sendo observada por backend e frontend.

## Pendencias reais

- Validar a nova documentacao com o time de arquitetura.
- Manter o plano futuro de saneamento dos espelhos legados fora desta fase.

## Necessidade de migrations adicionais

Nao. Esta fase nao identifica necessidade de nova migration.

## Recomendacao para a proxima fase

Seguir para o reforco da disciplina de escrita e leitura nos dominios existentes, mantendo a fonte documental em `Imoveis Rurais`, a fonte operacional em `Propriedades` e o vinculo em `PropriedadeImovel`.

## Respostas objetivas

1. Arquivos criados: listados acima.
2. Arquivos alterados: nenhum legado.
3. Testes executados: suite documental e suite cruzada territorial/documental.
4. Resultado dos testes: aprovados.
5. Necessidade de migrations adicionais: nao.
6. Riscos encontrados: espelhos legados e SIGEF nao consolidado.
7. Pendencias reais: validacao com arquitetura e produto.
8. Recomendacao para a proxima fase: aplicar disciplina de leitura/escrita e anticorrupcao dos legados, sem remover compatibilidade.
