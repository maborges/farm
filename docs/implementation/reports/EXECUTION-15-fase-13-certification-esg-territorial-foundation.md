# EXECUTION-15 - Fase 13 Preparação do Domínio de Certificações e ESG sobre a Base Territorial/Fundiária

Data: 2026-06-21
Status: Concluída
Autores: AgroSaaS Architecture / Codex

## 1. Objetivo

Preparar o domínio de Certificações, ESG e Projeto Raízes sobre a base territorial/fundiária consolidada, sem criar duplicidade de dados e sem criar um novo domínio territorial paralelo.

## 2. Estratégia Aplicada

- Inventário documental e de código das funcionalidades relacionadas a certificações, ESG, documentos, auditorias, evidências, rastreabilidade, Projeto Raízes e produtores.
- Leitura da norma territorial/fundiária e dos mapas de domínio, dados e roteamento.
- Consolidação da fronteira arquitetural: Certificações/ESG consome território e fundiário, mas escreve apenas seus próprios artefatos.
- Formalização da decisão em documentação de arquitetura e ADR.

## 3. Funcionalidades Inventariadas

- Certificações agrícolas por propriedade/unidade produtiva.
- Checklists, requisitos por norma e acompanhamento de validade.
- Auditorias, não conformidades e planos de ação.
- Evidências documentais e snapshots imutáveis.
- Relatórios ESG e indicadores ambientais/sociais/governança.
- Documentos ambientais e legais, com histórico e alertas.
- Treinamentos e EPIs como evidências de conformidade social.
- Cadeia de custódia, passaporte comercial e rastreabilidade.
- Projeto Raízes como caso de uso de prova documental e origem.

## 4. Entidades e Fontes Oficiais Mapeadas

- `Propriedade`: fonte oficial do território operacional.
- `Imóvel Rural`: fonte oficial do lastro jurídico/fundiário/documental.
- `PropriedadeImovel`: vínculo canônico entre operação territorial e lastro fundiário.
- Documentos fundiários e ambientais: leitura de apoio para certificação/ESG.
- `Certificações/ESG`: domínio consumidor e escritor de evidências, auditorias, respostas, pareceres e snapshots.
- Pessoas, treinamentos e EPI: fonte de evidência social, não fonte territorial.

## 5. Arquivos Criados

- `docs/architecture/certification-esg-territorial-foundation.md`
- `docs/architecture/adr/ADR-00XZ-certification-esg-territorial-foundation.md`
- `docs/implementation/reports/EXECUTION-15-fase-13-certification-esg-territorial-foundation.md`

## 6. Arquivos Alterados

- Nenhum arquivo de código foi alterado nesta fase.

## 7. ADR

- Houve ADR.
- A decisão formalizada foi manter Certificações, ESG e Projeto Raízes como consumidores transversais da fundação territorial/fundiária, sem domínio paralelo.

## 8. Migration

- Não houve necessidade comprovada de migration nesta fase.
- O repositório já possui os elementos conceituais e estruturais para iniciar a implementação futura com leitura das fontes canônicas.

## 9. Testes Executados

- `git status --short`
- `rg -n "certificacao|certificação|esg|questionario|questionário|auditoria|evidencia|evidência|raizes|raízes|rastreabilidade|produtor" docs services/api apps/web`
- `alembic heads` em `/opt/lampp/htdocs/farm/services/api`
- `git diff --check`

## 10. Resultado dos Testes

- `git status --short`: evidenciou worktree com alterações preexistentes fora do escopo.
- `rg`: confirmou a existência de cobertura documental e de código para certificações, ESG, documentos, auditoria e rastreabilidade.
- `alembic heads`: retornou `add_propriedade_imovel (head)`, indicando base de migrations coerente para a fundação territorial/fundiária.
- `git diff --check`: sem problemas nos arquivos criados nesta fase.

## 11. Riscos Encontrados

- Dispersão histórica da documentação sobre certificações e ESG em múltiplos diretórios.
- Risco de futuros trabalhos tentarem criar uma fonte oficial paralela.
- Risco de ampliação indevida do escopo para backend/frontend antes da formalização da modelagem do domínio.

## 12. Pendências Reais

- Definir a modelagem concreta de Certificações/ESG quando houver demanda de implementação.
- Criar, em fase posterior, os agregados de leitura necessários para os relatórios do domínio.
- Validar se o domínio consumidor precisará de páginas ou APIs próprias, sem tocar na fundação territorial/fundiária.

## 13. Recomendação para a Próxima Fase

Avançar para a implementação incremental do domínio de Certificações/ESG como consumidor read-only da fundação territorial/fundiária, começando por:

1. contratos de leitura e agregados de consulta;
2. modelagem de checklists, evidências e auditorias;
3. validação de relatórios ESG e Projeto Raízes sobre a base canônica;
4. somente depois, avaliar necessidade de migration do domínio consumidor.
