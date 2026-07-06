# Domínio Consumidor Certificações/ESG

Status: Proposto
Data: 2026-06-21
Autores: AgroSaaS Architecture / Codex

## 1. Objetivo

Modelar conceitualmente o domínio consumidor de Certificações/ESG antes de qualquer migration, API ou frontend.

Este domínio:
- consome `Propriedade`, `Imóvel Rural` e `PropriedadeImovel` como fontes oficiais;
- escreve apenas evidências, avaliações, auditorias, checklists, não conformidades, planos de ação e relatórios;
- não duplica CAR, matrícula, CCIR, ITR, NIRF, SIGEF nem dados territoriais;
- não altera os domínios territoriais/fundiários de origem.

## 2. Inventário Encontrado

### 2.1 Modelos, tabelas e serviços reais

| Item | Local | Classificação | Observação |
| --- | --- | --- | --- |
| `CertificacaoPropriedade` | `services/api/agricola/rastreabilidade/models.py` | Parcial | Usa `unidade_produtiva_id`, não modela o domínio consumidor oficial. |
| `LoteRastreabilidade` | `services/api/agricola/rastreabilidade/models.py` | Aproveitável | Passaporte de lote e leitura de certificações. |
| `CadernoLoteComercial` | `services/api/agricola/rastreabilidade/models.py` | Aproveitável | Snapshot imutável e suporte a rastreabilidade pública. |
| `ESGIndicador` | `services/api/enterprise/models/sprints_27_33.py` | Parcial | Modelo genérico e simplificado, sem governance própria do domínio consumidor. |
| `ESGRelatorio` | `services/api/enterprise/models/sprints_27_33.py` | Parcial | Útil como referência, mas ainda acoplado a uma modelagem enterprise genérica. |
| `MRVProjeto` / `MRVRelatorio` | `services/api/enterprise/models/sprints_27_33.py` | Legado / adjacente | Útil para carbono, mas não é o núcleo do domínio de certificações/ESG. |
| `TenantAuditLog` | `services/api/core/models/tenant_audit_log.py` | Aproveitável | Trilha transversal de escrita e auditoria. |
| `CadernoCampoEntrada` | `services/api/agricola/caderno/models.py` | Aproveitável | Fonte oficial de evidência operacional. |
| `CadernoCampoFoto` | `services/api/agricola/caderno/models.py` | Aproveitável | Evidência visual com metadados e flag pública. |
| `VisitaTecnica` | `services/api/agricola/caderno/models.py` | Aproveitável | Evidência técnica com assinatura e CARA/CREA. |
| `EPIEntrega` | `services/api/agricola/caderno/models.py` | Aproveitável | Evidência social e de segurança. |
| `CadernoExportacao` | `services/api/agricola/caderno/models.py` | Aproveitável | Snapshot documental assinado para certificação/auditoria. |
| `ChecklistModelo` / `ChecklistRealizado` | `services/api/operacional/models/checklist.py` | Aproveitável | Reutilizável para inspeções e liberações, mas ainda operacional. |
| `PlanoAcaoItem` | `services/api/financeiro/models/plano_acao.py` | Risco arquitetural | Resolve plano de ação em outro domínio; não deve virar o modelo oficial de compliance. |
| `PlanoAcaoOperacionalAgricola*` | `services/api/agricola/inteligencia_operacional/*` | Legado / adjacente | Pode inspirar priorização, mas não é o domínio oficial de conformidade. |
| `CARRegistro` / `DocumentoAmbiental` / `DocumentoLegal` | documentação de compliance | Aproveitável | Fonte de leitura para regularidade ambiental e fundiária. |

### 2.2 Documentos oficiais de apoio

| Documento | Classificação | Uso |
| --- | --- | --- |
| `docs/architecture/certification-esg-territorial-foundation.md` | Aproveitável | Define a fronteira de consumo sem domínio paralelo. |
| `docs/architecture/domains/certificacoes.md` | Aproveitável | Catálogo oficial inicial do domínio compartilhado. |
| `docs/architecture/cert-readiness-01-report.md` | Aproveitável | Diagnóstico de prontidão e gaps. |
| `docs/architecture/field-certification-01-report.md` | Aproveitável | Base de rastreabilidade, auditoria e certificação. |
| `docs/architecture/cert-implementation-01-passaporte-rastreabilidade.md` | Aproveitável | Modelo do passaporte e snapshot público. |
| `docs/architecture/cert-implementation-02-calibracao-sanitaria.md` | Aproveitável | Reuso de checklist e liberação sanitária. |
| `docs/architecture/field-core-journal-model.md` | Aproveitável | Define o caderno como núcleo de evidência operacional. |
| `apps/web/docs/contexts/rastreabilidade/enterprise/certificacoes.md` | Parcial | Modelo funcional de alto nível, ainda não normalizado em entidades oficiais do domínio consumidor. |
| `apps/web/docs/contexts/compliance/profissional/relatorios-esg.md` | Parcial | Bom mapa funcional de ESG, mas ainda com modelagem simplificada. |
| `docs/qwen/12-sprint-backlog-fase3.md` | Legado | Indicativo histórico, não fonte de verdade atual. |

## 3. Classificação Do Existente

### 3.1 Aproveitável

- `CadernoCampoEntrada`
- `CadernoCampoFoto`
- `VisitaTecnica`
- `EPIEntrega`
- `CadernoExportacao`
- `LoteRastreabilidade`
- `CadernoLoteComercial`
- `TenantAuditLog`
- `ChecklistModelo`
- `ChecklistRealizado`
- `CARRegistro` e documentos ambientais/legais como leitura de apoio

### 3.2 Parcial

- `CertificacaoPropriedade`
- `ESGIndicador`
- `ESGRelatorio`
- documentação funcional de certificações e ESG
- `apps/web/docs/contexts/rastreabilidade/enterprise/certificacoes.md`
- `apps/web/docs/contexts/compliance/profissional/relatorios-esg.md`

### 3.3 Legado

- `MRVProjeto`
- `MRVRelatorio`
- `PlanoAcaoOperacionalAgricola*`
- documentação de backlog histórico

### 3.4 Duplicado

- `PlanoAcaoItem` no financeiro, se usado como modelo oficial de compliance
- relatórios ESG genéricos se replicarem o que deve ser próprio do novo domínio consumidor

### 3.5 Risco Arquitetural

- reutilizar `CertificacaoPropriedade` como modelo final sem normalização
- usar `PlanoAcaoItem` financeiro para não conformidades de certificação
- usar `ESGRelatorio` genérico como verdade final do domínio
- converter questionários em fonte oficial territorial/fundiária
- criar uma nova representação de território dentro de Certificações/ESG

### 3.6 Inexistente

- `ProgramaCertificacao`
- `ChecklistCertificacao`
- `CriterioCertificacao`
- `AvaliacaoCertificacao`
- `EvidenciaCertificacao`
- `NaoConformidade`
- `PlanoAcao` do domínio de certificação
- `PassaporteRastreabilidade` como agregado oficial do consumidor

## 4. Modelo Conceitual Inicial

### 4.1 Visão Geral

```text
Propriedade
   └─< PropriedadeImovel >─ Imóvel Rural
             │
             └──> ProgramaCertificacao
                        ├──> ChecklistCertificacao
                        │        ├──> CriterioCertificacao
                        │        └──> AvaliacaoCertificacao
                        │                 ├──> EvidenciaCertificacao
                        │                 ├──> NaoConformidade
                        │                 │        └──> PlanoAcao
                        │                 └──> RelatorioESG
                        └──> PassaporteRastreabilidade
```

### 4.2 Entidades Propostas

#### ProgramaCertificacao

Responsabilidade:
- representar um programa, selo, norma ou iniciativa de conformidade;
- amarrar o escopo ao território e ao lastro fundiário;
- organizar o ciclo de vida da certificação.

Campos conceituais:
- `id`
- `tenant_id`
- `propriedade_id`
- `imovel_rural_id`
- `propriedade_imovel_id`
- `pessoa_proprietario_id` ou `pessoa_responsavel_id`, quando aplicável
- `nome`
- `tipo_programa`
- `organismo_certificador`
- `status`
- `data_inicio`
- `data_fim`
- `escopo`
- `observacoes`

#### ChecklistCertificacao

Responsabilidade:
- agrupar critérios de uma norma, versão ou auditoria;
- permitir preenchimento por programa.

Campos conceituais:
- `id`
- `tenant_id`
- `programa_certificacao_id`
- `nome`
- `norma_versao`
- `status`
- `percentual_conformidade`
- `data_abertura`
- `data_fechamento`

#### CriterioCertificacao

Responsabilidade:
- representar cada exigência auditável do checklist.

Campos conceituais:
- `id`
- `tenant_id`
- `checklist_certificacao_id`
- `codigo`
- `descricao`
- `categoria`
- `peso`
- `obrigatorio`
- `status`
- `observacoes`

#### AvaliacaoCertificacao

Responsabilidade:
- guardar a avaliação feita em um checklist ou critério;
- registrar aprovador, avaliador ou responsável técnico.

Campos conceituais:
- `id`
- `tenant_id`
- `checklist_certificacao_id`
- `avaliador_pessoa_id`
- `data_avaliacao`
- `resultado`
- `nota`
- `parecer`
- `observacoes`

#### EvidenciaCertificacao

Responsabilidade:
- anexar prova documental, foto, assinatura, laudo, snapshot ou URL externa.

Campos conceituais:
- `id`
- `tenant_id`
- `avaliacao_certificacao_id`
- `tipo_evidencia`
- `origem_documental`
- `arquivo_url`
- `hash_conteudo`
- `publica`
- `observacoes`

#### NaoConformidade

Responsabilidade:
- registrar divergência, falha ou pendência encontrada em auditoria.

Campos conceituais:
- `id`
- `tenant_id`
- `avaliacao_certificacao_id`
- `codigo`
- `descricao`
- `severidade`
- `status`
- `prazo_correcao`
- `responsavel_pessoa_id`
- `evidencia_correcao_id`

#### PlanoAcao

Responsabilidade:
- definir ações corretivas, responsáveis e vencimentos para não conformidades.

Campos conceituais:
- `id`
- `tenant_id`
- `nao_conformidade_id`
- `responsavel_pessoa_id`
- `descricao_acao`
- `prioridade`
- `status`
- `prazo`
- `conclusao_em`

#### RelatorioESG

Responsabilidade:
- consolidar score, indicadores e publicações ESG do domínio consumidor.

Campos conceituais:
- `id`
- `tenant_id`
- `propriedade_id`
- `imovel_rural_id`
- `propriedade_imovel_id`
- `periodo_inicio`
- `periodo_fim`
- `score_total`
- `status`
- `versao`
- `snapshot_base`
- `url_pdf`

#### PassaporteRastreabilidade

Responsabilidade:
- expor a cadeia documental e de origem para auditoria, comprador ou certificadora.

Campos conceituais:
- `id`
- `tenant_id`
- `propriedade_id`
- `imovel_rural_id`
- `propriedade_imovel_id`
- `caderno_lote_comercial_id`
- `qr_code_token`
- `snapshot_json`
- `snapshot_hash`
- `status`
- `publico`

## 5. Matriz De Leitura E Escrita

| Entidade | Escreve | Lê | Observações |
| --- | --- | --- | --- |
| `ProgramaCertificacao` | Certificações/ESG | Propriedade, Imóvel Rural, PropriedadeImovel, documentos, pessoas | Não altera as fontes oficiais. |
| `ChecklistCertificacao` | Certificações/ESG | ProgramaCertificacao | Domínio de governança e avaliação. |
| `CriterioCertificacao` | Certificações/ESG | ChecklistCertificacao | Critérios devem ser versionados. |
| `AvaliacaoCertificacao` | Certificações/ESG | Checklist, critérios, evidências, auditoria | Resultado de análise do domínio consumidor. |
| `EvidenciaCertificacao` | Certificações/ESG | Caderno, documentos, fotos, laudos, assinaturas | Pode referenciar snapshots públicos. |
| `NaoConformidade` | Certificações/ESG | Avaliação, critérios, evidências | Não deve virar erro territorial. |
| `PlanoAcao` | Certificações/ESG | Não conformidade, pessoas, prazos | Pode integrar notificações/IA no futuro. |
| `RelatorioESG` | Certificações/ESG | Propriedade, Imóvel Rural, documentos, pessoas, evidências | Produz score e versão. |
| `PassaporteRastreabilidade` | Certificações/ESG | Caderno, lote, certificações, documentos, vínculo oficial | Pode ser público, mas derivado. |

## 6. Regras De Ownership

1. Certificações/ESG escreve evidências, avaliações, auditorias, não conformidades, planos de ação e relatórios.
2. Certificações/ESG apenas lê dados territoriais e fundiários.
3. Certificações/ESG não altera `Propriedade`, `Imóvel Rural` nem `PropriedadeImovel`.
4. Questionários e checklists são instrumentos do domínio consumidor, nunca fonte oficial territorial/fundiária.
5. `tenant_id` é obrigatório em todas as entidades do domínio consumidor.
6. Quando houver referência a território ou lastro fundiário, a escrita continua no domínio original.

## 7. Probabilidade De Migration Futura

### Avaliação

**Sim, há necessidade provável de migration futura.**

### Motivo

As estruturas existentes são úteis, mas não representam ainda o modelo normalizado do domínio consumidor. Os pontos mais prováveis de migration futura são:

- criação das novas tabelas do domínio consumidor;
- eventual normalização ou substituição de `CertificacaoPropriedade`, `ESGIndicador` e `ESGRelatorio`;
- eventual separação de `PlanoAcao` de qualquer domínio financeiro/IA;
- definição de FKs explícitas para `propriedade_id`, `imovel_rural_id` e `propriedade_imovel_id`.

### O que não deve acontecer

- migration apenas para duplicar dados territoriais/fundiários;
- migration para transformar questionário em fonte oficial;
- migration para copiar CAR, matrícula ou documentos para o domínio consumidor.

## 8. Conclusão

O domínio consumidor Certificações/ESG já tem base funcional distribuída e bons pontos de reaproveitamento, mas ainda não tem uma modelagem oficial própria.

O próximo passo correto é transformar este desenho em contratos e, depois, em migration controlada do domínio consumidor, sempre preservando a hierarquia:

`Propriedade` → `PropriedadeImovel` → `Imóvel Rural`

e mantendo Certificações/ESG como domínio de consumo e prova documental.
