# Foundation Certificações, ESG e Projeto Raízes

Status: Proposto
Data: 2026-06-21
Autores: AgroSaaS Architecture / Codex

## 1. Objetivo

Consolidar a base arquitetural para Certificações, ESG e Projeto Raízes sobre a fundação territorial/fundiária já estabilizada no AgroSaaS.

Esta camada:
- consome dados oficiais de `Propriedade`, `Imóvel Rural` e `PropriedadeImovel`;
- preserva a separação entre território operacional e lastro fundiário;
- evita duplicação de CAR, matrícula, CCIR, ITR, NIRF, SIGEF e demais documentos fundiários;
- mantém evidências, respostas, auditorias e pareceres no próprio domínio de Certificações/ESG.

## 2. Inventário Funcional Existente

### 2.1 Certificações

Há capacidade funcional de certificação distribuída em vários pontos do produto:

- `apps/web/docs/contexts/rastreabilidade/enterprise/certificacoes.md`
- `docs/architecture/domains/certificacoes.md`
- `docs/architecture/cert-readiness-01-report.md`
- `docs/architecture/field-certification-01-report.md`
- `services/api/agricola/rastreabilidade/router.py`
- `services/api/agricola/rastreabilidade/service.py`
- `services/api/agricola/rastreabilidade/models.py`

O que já existe:
- cadastro e acompanhamento de certificações por propriedade/unidade produtiva;
- checklists e auditorias conceituais;
- vinculação a lotes, snapshots e passaportes;
- leitura de certificados em páginas públicas de rastreabilidade;
- governança documental para suportar auditoria externa.

### 2.2 ESG

O ESG já está descrito como camada transversal:

- `apps/web/docs/contexts/compliance/profissional/relatorios-esg.md`
- `docs/architecture/domains/certificacoes.md`
- `docs/architecture/cert-readiness-01-report.md`
- `services/api/enterprise/models/sprints_27_33.py`

O que já existe:
- relatórios ESG de leitura/geração;
- indicadores ambientais, sociais e de governança;
- integração de leitura com CAR, documentos ambientais, EPIs e treinamentos;
- proposta de selos e relatórios versionados.

### 2.3 Questionários e Checklists

Os questionários não aparecem como fonte oficial territorial. Eles existem como instrumentos de conformidade do domínio de certificações e compliance:

- `apps/web/docs/contexts/rastreabilidade/enterprise/certificacoes.md`
- `apps/web/docs/contexts/compliance/essencial/documentos-ambientais.md`
- `apps/web/docs/contexts/pessoas/profissional/treinamentos.md`
- `apps/web/docs/contexts/pessoas/essencial/epi-seguranca.md`

Leitura prática:
- checklists, auditorias e planos de ação pertencem a Certificações/ESG;
- respostas de questionário são evidência do domínio consumidor, não dado territorial oficial.

### 2.4 Auditorias

Auditoria já tem lastro documental e operacional:

- `docs/architecture/cert-readiness-01-report.md`
- `docs/architecture/field-certification-01-report.md`
- `docs/architecture/cert-implementation-01-passaporte-rastreabilidade.md`
- `services/api/core/models/tenant_audit_log.py`
- `services/api/agricola/rastreabilidade/service.py`

O que já existe:
- trilha de auditoria;
- snapshots imutáveis;
- logs de escrita;
- cadeia de custódia e passaporte comercial;
- apoio a auditoria de exportação e conformidade.

### 2.5 Evidências

As evidências já são tratadas como ativos do domínio de conformidade:

- fotos e snapshots no caderno de campo;
- documentos ambientais e legais;
- assinaturas e protocolos de exportação;
- arquivos de certificação vinculados a imutabilidade documental.

Fontes relevantes:
- `apps/web/docs/contexts/compliance/essencial/documentos-ambientais.md`
- `apps/web/docs/contexts/pessoas/essencial/epi-seguranca.md`
- `docs/architecture/cert-implementation-01-passaporte-rastreabilidade.md`
- `services/api/agricola/rastreabilidade/service.py`

### 2.6 Projeto Raízes

Projeto Raízes já aparece como caso de uso de rastreabilidade comercial e conformidade:

- `docs/architecture/cert-readiness-01-report.md`
- `docs/architecture/field-certification-01-report.md`
- `docs/architecture/cert-implementation-01-passaporte-rastreabilidade.md`
- `apps/web/docs/contexts/rastreabilidade/enterprise/certificacoes.md`

Leitura prática:
- Projeto Raízes consome a cadeia de custódia, a documentação fundiária e a base territorial;
- não cria uma nova fonte oficial territorial.

### 2.7 Produtores e Pessoas

Os consumidores humanos da base de certificação/ESG são:

- produtor/diretor;
- gerente de fazenda;
- agrônomo/RT;
- gestor de certificação;
- analista de compliance;
- auditor externo;
- comprador/trading;
- técnico de segurança;
- RH/administrativo.

Referências:
- `apps/web/docs/contexts/rastreabilidade/enterprise/certificacoes.md`
- `apps/web/docs/contexts/pessoas/profissional/treinamentos.md`
- `apps/web/docs/contexts/pessoas/essencial/epi-seguranca.md`
- `apps/web/docs/contexts/compliance/profissional/relatorios-esg.md`

## 3. Fontes Oficiais e Consumidores

| Necessidade | Fonte Oficial | Entidade Consumidora | Pode Escrever? |
| --- | --- | --- | --- |
| CAR | Imóvel Rural | Certificações / ESG | Não |
| Matrícula / cartório | Imóvel Rural | Certificações / ESG | Não |
| CCIR / ITR / NIRF / SIGEF | Imóvel Rural | Certificações / ESG | Não |
| Área operacional | Propriedade | Certificações / ESG | Não |
| Glebas / talhões / infraestrutura | Propriedade | Certificações / ESG | Não |
| Vínculo posse/uso | PropriedadeImovel | Certificações / ESG | Não |
| Evidência de auditoria | Certificações / ESG | Certificações / ESG | Sim |
| Questionário / checklist | Certificações / ESG | Certificações / ESG | Sim |
| Auditoria / parecer | Certificações / ESG | Certificações / ESG | Sim |
| Treinamento / EPI | Pessoas / RH | Certificações / ESG | Não |

## 4. Matriz de Dependência

| Necessidade | Fonte Oficial | Entidade Consumidora | Pode Escrever? |
| --- | --- | --- | --- |
| CAR | Imóvel Rural | Certificação/ESG | Não |
| Área operacional | Propriedade | Certificação/ESG | Não |
| Vínculo posse/uso | PropriedadeImovel | Certificação/ESG | Não |
| Evidência de auditoria | Certificação/ESG | Certificação/ESG | Sim |
| Questionário | Certificação/ESG | Certificação/ESG | Sim |

## 5. Limites Arquiteturais

1. Certificações/ESG podem ler dados territoriais e fundiários.
2. Certificações/ESG não podem duplicar CAR, matrícula, CCIR, ITR, NIRF ou SIGEF.
3. Certificações/ESG não podem substituir `PropriedadeImovel`.
4. Evidências, respostas, pareceres e auditorias pertencem ao domínio de Certificação/ESG.
5. O domínio consumidor pode armazenar snapshot, score, status e histórico próprio.
6. O domínio consumidor não pode se tornar fonte oficial territorial ou fundiária.

## 6. Estrutura de Consumo Recomendado

### 6.1 Leitura upstream

Certificações/ESG deve consumir:
- identificação da propriedade;
- geometria/área operacional;
- vínculo canônico com imóvel rural;
- documentos fundiários e ambientais;
- titulares e representantes legais quando necessários para auditoria;
- EPIs, treinamentos e evidências humanas quando o requisito da certificação exigir.

### 6.2 Escrita local

Certificações/ESG pode escrever apenas:
- questionários;
- respostas;
- evidências;
- auditorias;
- não conformidades;
- planos de ação;
- scores;
- snapshots;
- pareceres;
- selos internos;
- históricos de conformidade.

### 6.3 Leitura derivada

Os relatórios do domínio podem derivar:
- score ESG;
- status de prontidão;
- checklist por norma;
- cadeia de custódia;
- prontidão para exportação;
- aderência ao Projeto Raízes.

## 7. Avaliação de Maturidade

Estruturalmente, a base já é suficiente para iniciar a implementação sem migration adicional de fundação.

Motivos:
- as entidades de território/fundiário já existem;
- a cardinalidade oficial já está definida;
- as rotas agregadas já consomem as fontes canônicas;
- há documentação funcional para certificações, ESG, documentos e rastreabilidade;
- já existem snapshots e trilhas para auditoria.

O que ainda pode ser necessário em fases futuras:
- ajuste fino de modelos de dados do domínio de certificação;
- novas telas de gestão de checklist/auditoria;
- integração mais formal com selos e programas externos;
- reforços de relatórios e exportação.

## 8. Recomendação de Evolução

1. Formalizar o domínio de Certificações/ESG como consumidor transversal.
2. Reusar a base territorial/fundiária sem duplicação de dados.
3. Colocar questionários, evidências e auditorias no domínio consumidor.
4. Tratar Projeto Raízes como caso de uso de leitura e prova documental.
5. Evitar criação de nova fonte oficial territorial ou fundiária.

## 9. Conclusão

A arquitetura do AgroSaaS já suporta a preparação do domínio de Certificações, ESG e Projeto Raízes sobre a fundação territorial/fundiária existente.

O caminho correto é de consumo read-only das fontes oficiais, com escrita restrita ao domínio de conformidade, sem migration obrigatória neste momento.
