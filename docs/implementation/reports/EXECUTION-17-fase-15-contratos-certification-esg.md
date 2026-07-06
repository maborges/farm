# EXECUTION-17 - Fase 15 Contratos do Domínio Consumidor Certificações/ESG

Data: 2026-06-21
Status: Concluída
Autores: AgroSaaS Architecture / Codex

## 1. Objetivo

Formalizar os contratos de leitura e escrita do domínio consumidor Certificações/ESG antes de qualquer implementação física.

## 2. Contratos Definidos

- `ProgramaCertificacao`
- `ChecklistCertificacao`
- `CriterioCertificacao`
- `AvaliacaoCertificacao`
- `EvidenciaCertificacao`
- `NaoConformidade`
- `PlanoAcaoCertificacao`
- `RelatorioESG`
- `PassaporteRastreabilidade`

## 3. Regras Principais

- Certificações/ESG escreve evidências, avaliações, auditorias, não conformidades, planos de ação e relatórios.
- Certificações/ESG lê `Propriedade`, `Imóvel Rural`, `PropriedadeImovel`, documentos fundiários, exploração rural, produtor/pessoa, caderno de campo, visitas técnicas, EPIs e evidências operacionais.
- Certificações/ESG não duplica CAR, matrícula, CCIR, ITR, NIRF, SIGEF ou área operacional como fonte oficial.
- Snapshots são permitidos apenas como evidência imutável com origem, data e hash.

## 4. Modelos Existentes Classificados

- `CertificacaoPropriedade`: compatibilidade / parcial
- `ESGIndicador`: adaptar
- `ESGRelatorio`: substituir
- `LoteRastreabilidade`: manter
- `CadernoLoteComercial`: manter
- `ChecklistModelo`: compatibilidade
- `ChecklistRealizado`: compatibilidade
- `PlanoAcaoItem`: não usar como oficial
- `MRVProjeto`: legado
- `MRVRelatorio`: legado

## 5. Matriz Oficial

| Contrato | Tipo | Escreve? | Lê fontes territoriais? | Substitui modelo atual? | Migration futura? |
| --- | --- | --- | --- | --- | --- |
| `ProgramaCertificacao` | novo | Sim | Sim | Não | Sim |
| `ChecklistCertificacao` | novo | Sim | Indiretamente | Não | Sim |
| `CriterioCertificacao` | novo | Sim | Não | Não | Sim |
| `AvaliacaoCertificacao` | novo | Sim | Indiretamente | Não | Sim |
| `EvidenciaCertificacao` | novo | Sim | Sim | Não | Sim |
| `NaoConformidade` | novo | Sim | Indiretamente | Não | Sim |
| `PlanoAcaoCertificacao` | novo | Sim | Indiretamente | Sim, em relação ao uso de `PlanoAcaoItem` | Sim |
| `RelatorioESG` | novo | Sim | Sim | Sim, em relação a `ESGRelatorio` genérico | Sim |
| `PassaporteRastreabilidade` | novo | Sim | Sim | Sim, em relação ao snapshot ad hoc | Sim |

## 6. Estratégia De Snapshot

- Permitido ao publicar relatório ESG, passaporte de rastreabilidade ou evidência auditável.
- Metadados obrigatórios: `tenant_id`, `origin_type`, `origin_id`, `created_at`, `created_by` ou `responsavel_pessoa_id`, `source_version`, `snapshot_hash`, `scope`, `publico`.
- Snapshot não substitui os contratos territoriais/fundiários e não vira fonte oficial.
- A origem deve ser rastreável por FK quando possível, ou por `origin_type` + `origin_id` quando derivada de agregação documental.

## 7. Necessidade Provável De Migration Futura

- Sim, há necessidade provável de migration futura.
- Motivo: os contratos oficiais ainda não existem fisicamente e os modelos atuais são apenas parcamente aderentes ao que o domínio consumidor precisa.
- A migration futura deve normalizar o domínio consumidor sem tocar na base territorial/fundiária.

## 8. Arquivos Criados

- [docs/architecture/certification-esg-contracts.md](/opt/lampp/htdocs/farm/docs/architecture/certification-esg-contracts.md)
- [docs/implementation/reports/EXECUTION-17-fase-15-contratos-certification-esg.md](/opt/lampp/htdocs/farm/docs/implementation/reports/EXECUTION-17-fase-15-contratos-certification-esg.md)

## 9. Arquivos Alterados

- Nenhum arquivo de código ou API foi alterado.

## 10. Comandos Executados

- `git status --short`
- `rg -n "CertificacaoPropriedade|ESGIndicador|ESGRelatorio|LoteRastreabilidade|CadernoLoteComercial|ChecklistModelo|ChecklistRealizado|PlanoAcaoItem|MRVProjeto|MRVRelatorio" docs services/api apps/web`
- `alembic heads`
- `git diff --check`

## 11. Resultado Dos Comandos

- `git status --short`: worktree já tinha alterações preexistentes fora do escopo; nenhuma foi modificada.
- `rg`: confirmou a presença dos modelos e documentos relevantes.
- `alembic heads`: retornou `add_propriedade_imovel (head)`.
- `git diff --check`: sem problemas nos arquivos criados nesta fase.

## 12. Riscos Encontrados

- Usar `PlanoAcaoItem` financeiro/IA como plano oficial de certificação.
- Persistir contratos simplificados como verdade final.
- Duplicar CAR, matrícula ou área operacional em snapshots ou tabelas novas.
- Misturar contrato com implementação antes da migration planejada.

## 13. Pendências Reais

- Aprovar o desenho conceitual como base para a migration técnica futura.
- Decidir o tratamento definitivo de `CertificacaoPropriedade`, `ESGIndicador` e `ESGRelatorio`.
- Criar schemas e contratos físicos somente após a próxima aprovação arquitetural.

## 14. Recomendação Para A Próxima Fase

- Seguir para a fase de planejamento da migration técnica do domínio consumidor, sem tocar na base territorial/fundiária.
- Antes disso, revisar o destino de compatibilidade dos modelos existentes e o contrato de `RelatorioESG` / `PassaporteRastreabilidade` para reduzir retrabalho.
