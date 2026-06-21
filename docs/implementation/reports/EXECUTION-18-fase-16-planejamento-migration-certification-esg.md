# EXECUTION-18 - Fase 16 Planejamento da Migration do Domínio Consumidor Certificações/ESG

Data: 2026-06-21
Status: Concluída
Autores: AgroSaaS Architecture / Codex

## 1. Objetivo

Planejar tecnicamente a migration física do domínio consumidor Certificações/ESG, sem criá-la ainda.

## 2. Inventário De Migrations Relevantes

- `8c2e891d6ba9_caderno_campo.py`
- `56b72a50ad49_add_tenant_audit_log.py`
- `08c865830c43_checklist_agricola.py`
- `7109d2ac3e9e_checklist_agricola_templates_itens.py`
- `a4dc0640fdcf_add_lote_comercial_and_publica_foto.py`
- `2325278cb390_create_equipamento_calibracao.py`
- `add_propriedade_imovel.py`
- `b1c2d3e4f5a7_add_imoveis_avaliacoes.py`

## 3. Tabelas Candidatas

- `certificacao_programas`
- `certificacao_checklists`
- `certificacao_criterios`
- `certificacao_avaliacoes`
- `certificacao_evidencias`
- `certificacao_nao_conformidades`
- `certificacao_planos_acao`
- `esg_relatorios`
- `rastreabilidade_passaportes`

## 4. Enums Necessários

- `status_programa`
- `tipo_certificacao`
- `status_checklist`
- `resultado_avaliacao`
- `tipo_evidencia`
- `severidade_nao_conformidade`
- `status_plano_acao`
- `status_relatorio_esg`
- `status_passaporte`
- `prioridade_plano_acao`

## 5. Estratégia Para Modelos Existentes

- `CertificacaoPropriedade`: compatibilidade somente leitura / adaptar depois
- `ESGIndicador`: fora do domínio canônico / adaptar depois
- `ESGRelatorio`: substituir gradualmente
- `LoteRastreabilidade`: manter com FK futura
- `CadernoLoteComercial`: manter com FK futura
- `ChecklistModelo`: compatibilidade somente leitura
- `ChecklistRealizado`: compatibilidade somente leitura
- `PlanoAcaoItem`: fora do domínio canônico
- `MRVProjeto`: legado histórico
- `MRVRelatorio`: legado histórico

## 6. Ordem De Criação

1. `certificacao_programas`
2. `certificacao_checklists`
3. `certificacao_criterios`
4. `certificacao_avaliacoes`
5. `certificacao_evidencias`
6. `certificacao_nao_conformidades`
7. `certificacao_planos_acao`
8. `esg_relatorios`
9. `rastreabilidade_passaportes`

## 7. Migrations Única Ou Separada

- Recomendação: migrations separadas por subdomínio, em lote coordenado.
- Não usar uma migration monolítica.

## 8. Regras De Não Duplicação

- não copiar CAR;
- não copiar matrícula;
- não copiar CCIR;
- não copiar ITR;
- não copiar NIRF;
- não copiar SIGEF;
- não usar área operacional como verdade oficial nova;
- não usar `PlanoAcaoItem` financeiro/IA como plano oficial;
- snapshots só como evidência imutável.

## 9. Riscos Encontrados

- migrar o modelo errado antes da normalização completa;
- misturar modelos financeiros/IA com compliance;
- duplicar origem territorial/fundiária;
- colocar passaporte público em migration sem política de leitura adequada.

## 10. Pendências Reais

- decidir o primeiro lote de migrations a partir do plano aprovado;
- definir FKs e nomes exatos dos enums nos drafts técnicos;
- validar a compatibilidade de leitura dos modelos legados durante a transição.

## 11. Recomendação Para A Próxima Fase

- Avançar para a redação dos drafts de migration por subdomínio, sem executar a migration ainda.
- Priorizar primeiro o núcleo de certificação e depois ESG/passaporte, mantendo compatibilidade de leitura com os modelos atuais.

## 12. Arquivos Criados

- [docs/architecture/certification-esg-migration-plan.md](/opt/lampp/htdocs/farm/docs/architecture/certification-esg-migration-plan.md)
- [docs/implementation/reports/EXECUTION-18-fase-16-planejamento-migration-certification-esg.md](/opt/lampp/htdocs/farm/docs/implementation/reports/EXECUTION-18-fase-16-planejamento-migration-certification-esg.md)

## 13. Arquivos Alterados

- Nenhum arquivo de código.

## 14. Comandos Executados

- `git status --short`
- `ls services/api/migrations/versions`
- `rg -n "certificacao|certificação|esg|checklist|evidencia|auditoria|rastreabilidade|passaporte|plano_acao|nao_conformidade|mrv" services/api/migrations services/api docs`
- `alembic heads`
- `git diff --check`

## 15. Resultado Dos Comandos

- `git status --short`: worktree já continha alterações preexistentes fora do escopo; não foram alteradas.
- `ls services/api/migrations/versions`: confirmou grande volume de migrations existentes, incluindo base territorial, caderno, passaporte e checklist operacional.
- `rg`: confirmou inventário e conexão documental com certificações, ESG, rastreabilidade, plano de ação e MRV.
- `alembic heads`: retornou `add_propriedade_imovel (head)`.
- `git diff --check`: sem problemas nos arquivos criados nesta fase.
