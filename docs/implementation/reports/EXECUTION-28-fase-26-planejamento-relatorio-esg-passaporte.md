# EXECUTION-28 - FASE 26 PLANEJAMENTO DO RELATÓRIO ESG E PASSAPORTE DE RASTREABILIDADE

Data: 2026-06-21

## Objetivo

Planejar o próximo bloco funcional do domínio Certificações/ESG para `RelatorioESG` e `PassaporteRastreabilidade`, sem implementar backend, frontend ou migration.

## Modelos revisados

- `ESGIndicador`
- `ESGRelatorio`
- `LoteRastreabilidade`
- `CadernoLoteComercial`
- `CadernoExportacao`
- `CertificacaoPropriedade`
- `CadernoCampoEntrada`
- `CadernoCampoFoto`
- `VisitaTecnica`
- `EPIEntrega`
- `TenantAuditLog`
- evidências, não conformidades e planos de ação

## Modelo conceitual proposto

- `RelatorioESG`
- `RelatorioESGIndicador`
- `RelatorioESGEvidencia`
- `PassaporteRastreabilidade`
- `PassaporteRastreabilidadeEvento`
- `PassaporteRastreabilidadeEvidencia`

## Política de snapshot definida

- Snapshot permitido na publicação de relatório, na publicação de passaporte e no congelamento de evidências.
- Hash obrigatório para versões publicadas.
- Snapshot nunca vira fonte oficial territorial/fundiária.
- Versionamento imutável por publicação.
- `publico` ou `privado` conforme política do tenant e do caso de uso.
- Trilha de auditoria obrigatória para geração, publicação, revogação e acesso.

## Status oficiais sugeridos

- `RelatorioESG`: `RASCUNHO`, `EM_REVISAO`, `PUBLICADO`, `CANCELADO`
- `PassaporteRastreabilidade`: `RASCUNHO`, `EM_VALIDACAO`, `PUBLICADO`, `REVOGADO`

## Necessidade provável de migration

Sim. Há necessidade provável de migration futura para normalizar os modelos canônicos e os fluxos de snapshot/publicação.

## Recomendação de lote

Recomendação: migration única para o bloco de publicação, desde que o escopo físico seja coeso. Se houver necessidade operacional, o plano admite subdivisão em base de publicação, passaporte e relatório/indicadores.

## Arquivos criados

- `docs/architecture/certification-esg-report-passport-plan.md`
- `docs/implementation/reports/EXECUTION-28-fase-26-planejamento-relatorio-esg-passaporte.md`

## Arquivos alterados

- Nenhum arquivo existente foi alterado nesta fase.

## Comandos executados

- `git status --short`
- `rg -n "ESGIndicador|ESGRelatorio|LoteRastreabilidade|CadernoLoteComercial|CadernoExportacao|CertificacaoPropriedade|RelatorioESG|PassaporteRastreabilidade|rastreabilidade|snapshot|hash" docs services/api apps/web`
- `alembic heads`
- `git diff --check`

## Resultado dos comandos

- `git status --short`: worktree já possuía mudanças pré-existentes fora do escopo.
- `rg`: confirmou que existem referências parciais e legadas suficientes para orientar a nova modelagem.
- `alembic heads`: head atual `20260621_certificacao_esg_status_nao_conformidade (head)`.
- `git diff --check`: sem problemas nos arquivos desta fase.

## Riscos encontrados

- Existe bastante legado adjacente em ESG, rastreabilidade e MRV, então a normalização futura precisa manter a separação entre referência e contrato canônico.
- Snapshots públicos exigem cuidado para não vazar dados territoriais/fundiários sensíveis.

## Pendências reais

- Não há implementação física do relatório ESG nem do passaporte.
- Não há migration nova.
- Não há API nem frontend para esse bloco.

## Recomendação para a próxima fase

- Aprovar este plano e avançar para a modelagem física do bloco de publicação em migration controlada, sem reaproveitar `PlanoAcaoItem` e sem criar nova fonte oficial territorial/fundiária.
