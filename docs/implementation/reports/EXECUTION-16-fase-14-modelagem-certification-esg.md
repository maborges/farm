# EXECUTION-16 - Fase 14 Modelagem Inicial do Domínio Consumidor Certificações/ESG

Data: 2026-06-21
Status: Concluída
Autores: AgroSaaS Architecture / Codex

## 1. Objetivo

Modelar o domínio consumidor de Certificações/ESG antes de qualquer migration, API ou frontend.

## 2. Inventário Encontrado

- Certificações, ESG, auditorias, evidências, checklists, questionários, não conformidades, planos de ação, relatórios, rastreabilidade e Projeto Raízes foram inventariados em documentação funcional, rotas e models existentes.
- O backend já possui assets úteis em `CadernoCampo`, `Rastreabilidade`, `TenantAuditLog`, `ChecklistModelo/ChecklistRealizado` e relatórios/documentos de compliance.
- Existem estruturas legadas ou adjacentes em `enterprise/models/sprints_27_33.py` e em `PlanoAcaoItem` que não devem ser tratadas como o modelo oficial final.

## 3. Classificação Do Existente

- **Aproveitável**: `CadernoCampoEntrada`, `CadernoCampoFoto`, `VisitaTecnica`, `EPIEntrega`, `CadernoExportacao`, `LoteRastreabilidade`, `CadernoLoteComercial`, `TenantAuditLog`, `ChecklistModelo`, `ChecklistRealizado`.
- **Parcial**: `CertificacaoPropriedade`, `ESGIndicador`, `ESGRelatorio`, documentação funcional de certificações e ESG.
- **Legado**: `MRVProjeto`, `MRVRelatorio`, `PlanoAcaoOperacionalAgricola*`, backlog histórico.
- **Duplicado**: `PlanoAcaoItem` financeiro se for usado como modelo oficial de compliance.
- **Risco arquitetural**: reutilização direta de modelos simplificados como verdade final do domínio consumidor.
- **Inexistente**: `ProgramaCertificacao`, `ChecklistCertificacao`, `CriterioCertificacao`, `AvaliacaoCertificacao`, `EvidenciaCertificacao`, `NaoConformidade`, `PlanoAcao` próprio de certificação, `PassaporteRastreabilidade` oficial.

## 4. Modelo Conceitual Proposto

Entidades propostas:
- `ProgramaCertificacao`
- `ChecklistCertificacao`
- `CriterioCertificacao`
- `AvaliacaoCertificacao`
- `EvidenciaCertificacao`
- `NaoConformidade`
- `PlanoAcao`
- `RelatorioESG`
- `PassaporteRastreabilidade`

Fronteiras de escrita:
- Certificações/ESG escreve evidências, avaliações, auditorias, não conformidades, planos de ação e relatórios.
- Certificações/ESG lê dados territoriais e fundiários.
- Certificações/ESG não altera `Propriedade`, `Imóvel Rural` nem `PropriedadeImovel`.

## 5. Entidades E Responsabilidades

- `ProgramaCertificacao`: agrupa selo, norma e ciclo de conformidade.
- `ChecklistCertificacao`: agrupa critérios por norma/versão.
- `CriterioCertificacao`: representa cada exigência auditável.
- `AvaliacaoCertificacao`: registra resultado da análise.
- `EvidenciaCertificacao`: anexa prova documental ou snapshot.
- `NaoConformidade`: registra desvio identificado.
- `PlanoAcao`: acompanha correção.
- `RelatorioESG`: consolida score e relatório ESG.
- `PassaporteRastreabilidade`: expõe a cadeia documental e de origem.

## 6. Matriz De Leitura E Escrita

| Entidade | Escreve | Lê | Observações |
| --- | --- | --- | --- |
| `ProgramaCertificacao` | Certificações/ESG | Propriedade, Imóvel Rural, PropriedadeImovel, pessoas, documentos | Referencia a base oficial. |
| `ChecklistCertificacao` | Certificações/ESG | ProgramaCertificacao | Usa norma e versão. |
| `CriterioCertificacao` | Certificações/ESG | ChecklistCertificacao | Deve ser versionável. |
| `AvaliacaoCertificacao` | Certificações/ESG | Checklist, critérios, evidências | Resultado de auditoria. |
| `EvidenciaCertificacao` | Certificações/ESG | Caderno, documentos, fotos, laudos, assinaturas | Ativo de prova. |
| `NaoConformidade` | Certificações/ESG | Avaliação, critérios, evidências | Não é dado territorial. |
| `PlanoAcao` | Certificações/ESG | Não conformidade, pessoas, prazos | Pode integrar notificações depois. |
| `RelatorioESG` | Certificações/ESG | Propriedade, Imóvel Rural, documentos, pessoas, evidências | Relatório derivado. |
| `PassaporteRastreabilidade` | Certificações/ESG | Caderno, lote, certificações, documentos, vínculo oficial | Snapshot público/privado. |

## 7. Necessidade Provável De Migration Futuro

- Há necessidade provável de migration futura para materializar o modelo oficial do domínio consumidor.
- Não houve necessidade de migration nesta fase, porque o objetivo foi apenas a modelagem inicial.
- A migração futura deve criar entidades do domínio consumidor sem duplicar fontes oficiais territoriais/fundiárias.

## 8. Arquivos Criados

- [docs/architecture/certification-esg-domain-model.md](/opt/lampp/htdocs/farm/docs/architecture/certification-esg-domain-model.md)
- [docs/implementation/reports/EXECUTION-16-fase-14-modelagem-certification-esg.md](/opt/lampp/htdocs/farm/docs/implementation/reports/EXECUTION-16-fase-14-modelagem-certification-esg.md)

## 9. Arquivos Alterados

- Nenhum arquivo de código foi alterado.

## 10. Comandos Executados

- `git status --short`
- `rg -n "certificacao|certificação|esg|questionario|questionário|auditoria|evidencia|evidência|checklist|nao_conformidade|não conformidade|plano_acao|plano de ação|relatorio|relatório|rastreabilidade|passaporte|raizes|raízes" docs services/api apps/web`
- `alembic heads`
- `git diff --check`

## 11. Resultado Dos Comandos

- `git status --short`: worktree já estava com alterações preexistentes fora do escopo; nenhuma foi mexida.
- `rg`: confirmou que existem assets reais e funcionais para certificação, ESG, caderno, checklist, plano de ação, auditoria e rastreabilidade.
- `alembic heads`: retornou `add_propriedade_imovel (head)`.
- `git diff --check`: sem problemas nos arquivos criados nesta fase.

## 12. Riscos Encontrados

- Usar os modelos simplificados atuais como se fossem o domínio oficial final.
- Misturar plano de ação financeiro/IA com plano de ação de certificação.
- Tratar questionários como origem territorial/fundiária.
- Duplicar CAR, matrícula ou documentos em entidades novas.

## 13. Pendências Reais

- Definir migrations quando a modelagem passar da fase conceitual para a fase estrutural.
- Definir contratos de API do domínio consumidor.
- Definir telas de cadastro, checklist e auditoria.
- Normalizar a relação entre os modelos legados atuais e o futuro modelo oficial.

## 14. Recomendação Para A Próxima Fase

Avançar para a formalização contratual do domínio consumidor:

1. definir schemas e contratos de leitura/escrita;
2. decidir o destino de `CertificacaoPropriedade`, `ESGIndicador` e `ESGRelatorio`;
3. planejar a migration do domínio consumidor;
4. só depois iniciar backend e frontend próprios.
