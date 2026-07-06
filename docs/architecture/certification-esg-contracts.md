# Contratos do Domínio Consumidor Certificações/ESG

Status: Proposto
Data: 2026-06-21
Autores: AgroSaaS Architecture / Codex

## 1. Objetivo

Formalizar os contratos de leitura e escrita do domínio consumidor Certificações/ESG antes de qualquer implementação física.

Este documento define:
- responsabilidade;
- campos mínimos;
- campos proibidos;
- entidades referenciadas;
- perfis de criação, atualização e leitura;
- regras de `tenant_id`;
- regras de auditoria;
- relação com `Propriedade`, `Imóvel Rural` e `PropriedadeImovel`;
- destino arquitetural dos modelos existentes;
- estratégia de snapshot.

## 2. Princípios

1. Certificações/ESG é domínio consumidor, não fonte oficial territorial.
2. Certificações/ESG apenas lê `Propriedade`, `Imóvel Rural` e `PropriedadeImovel`.
3. Certificações/ESG pode escrever evidências, avaliações, auditorias, não conformidades, planos de ação e relatórios.
4. Certificações/ESG não armazena CAR, matrícula, CCIR, ITR, NIRF, SIGEF nem geometria territorial oficial.
5. Snapshots são evidência imutável, não verdade oficial substitutiva.
6. Todo registro do domínio consumidor precisa carregar `tenant_id`.

## 3. Contratos Conceituais

### 3.1 ProgramaCertificacao

**Responsabilidade**
- Representar um programa, selo, norma ou iniciativa de conformidade.

**Campos mínimos**
- `id`
- `tenant_id`
- `propriedade_id`
- `imovel_rural_id`
- `propriedade_imovel_id`
- `nome`
- `tipo_programa`
- `status`
- `data_inicio`
- `observacoes`

**Campos proibidos**
- CAR
- matrícula
- CCIR
- ITR
- NIRF
- SIGEF
- geometria oficial territorial
- área operacional como fonte oficial

**Entidades referenciadas**
- `Propriedade`
- `Imóvel Rural`
- `PropriedadeImovel`
- `Pessoa` / produtor, quando aplicável

**Quem pode criar**
- gestão de certificação
- compliance
- produtor/gestor autorizado

**Quem pode atualizar**
- gestão de certificação
- compliance

**Quem pode apenas ler**
- auditor externo
- produtor/diretor
- compradores autorizados
- consumidores internos conforme RBAC

**Regras de tenant_id**
- obrigatório
- imutável após criação
- sempre filtrado em listagens e agregações

**Regras de auditoria**
- criação, edição, alteração de status e encerramento precisam gerar trilha

**Relação com Propriedade**
- referência de escopo operacional

**Relação com Imóvel Rural**
- referência de lastro legal/fundiário

**Relação com PropriedadeImovel**
- vínculo oficial entre escopo e lastro

### 3.2 ChecklistCertificacao

**Responsabilidade**
- Agrupar critérios de uma norma, versão ou auditoria.

**Campos mínimos**
- `id`
- `tenant_id`
- `programa_certificacao_id`
- `nome`
- `norma_versao`
- `status`
- `percentual_conformidade`
- `data_abertura`

**Campos proibidos**
- dados fundiários oficiais
- CAR
- matrícula
- geometria oficial
- dados financeiros alheios ao checklist

**Entidades referenciadas**
- `ProgramaCertificacao`

**Quem pode criar**
- gestão de certificação
- compliance

**Quem pode atualizar**
- gestão de certificação
- auditor designado

**Quem pode apenas ler**
- produtor/diretor
- auditor
- comprador autorizado

**Regras de tenant_id**
- obrigatório
- particiona todos os critérios do checklist

**Regras de auditoria**
- abertura, reabertura, fechamento e reclassificação exigem trilha

**Relação com Propriedade / Imóvel Rural / PropriedadeImovel**
- apenas leitura derivada para contextualização

### 3.3 CriterioCertificacao

**Responsabilidade**
- Representar cada exigência auditável.

**Campos mínimos**
- `id`
- `tenant_id`
- `checklist_certificacao_id`
- `codigo`
- `descricao`
- `categoria`
- `peso`
- `obrigatorio`
- `status`

**Campos proibidos**
- identificação territorial oficial
- CAR
- matrícula
- dados de titularidade completos, exceto quando necessário como referência de leitura

**Entidades referenciadas**
- `ChecklistCertificacao`

**Quem pode criar**
- gestão de certificação
- compliance

**Quem pode atualizar**
- gestão de certificação
- auditor designado

**Quem pode apenas ler**
- auditor
- gestor
- produtor/diretor

**Regras de tenant_id**
- obrigatório

**Regras de auditoria**
- toda mudança de peso, descrição ou obrigatoriedade deve ser auditável

### 3.4 AvaliacaoCertificacao

**Responsabilidade**
- Registrar a avaliação feita sobre um checklist ou critério.

**Campos mínimos**
- `id`
- `tenant_id`
- `checklist_certificacao_id`
- `avaliador_pessoa_id`
- `data_avaliacao`
- `resultado`
- `nota`
- `parecer`

**Campos proibidos**
- CAR
- matrícula
- dados oficiais fundiários
- qualquer dado territorial duplicado

**Entidades referenciadas**
- `ChecklistCertificacao`
- `Pessoa`

**Quem pode criar**
- auditor
- responsável técnico
- gestor de certificação

**Quem pode atualizar**
- auditor designado
- gestor de certificação

**Quem pode apenas ler**
- produtores autorizados
- compliance

**Regras de tenant_id**
- obrigatório

**Regras de auditoria**
- criação e retificação devem gerar log e histórico

### 3.5 EvidenciaCertificacao

**Responsabilidade**
- Anexar prova documental, foto, assinatura, laudo, snapshot ou URL externa.

**Campos mínimos**
- `id`
- `tenant_id`
- `avaliacao_certificacao_id`
- `tipo_evidencia`
- `origem_documental`
- `arquivo_url`
- `hash_conteudo`
- `publica`

**Campos proibidos**
- não deve armazenar origem oficial territorial como dado primário
- não deve substituir documentação fundiária oficial

**Entidades referenciadas**
- `AvaliacaoCertificacao`
- `CadernoCampoEntrada`
- `CadernoCampoFoto`
- `VisitaTecnica`
- `EPIEntrega`
- `CadernoExportacao`

**Quem pode criar**
- gestão de certificação
- compliance
- auditor

**Quem pode atualizar**
- somente metadados permitidos e até o momento de publicação

**Quem pode apenas ler**
- auditor
- compliance
- comprador autorizado, se `publica = true`

**Regras de tenant_id**
- obrigatório

**Regras de auditoria**
- criação, publicação e revogação devem ser auditadas

**Relação com Propriedade / Imóvel Rural / PropriedadeImovel**
- apenas leitura derivada

### 3.6 NaoConformidade

**Responsabilidade**
- Registrar desvio, falha ou pendência encontrada em auditoria.

**Campos mínimos**
- `id`
- `tenant_id`
- `avaliacao_certificacao_id`
- `codigo`
- `descricao`
- `severidade`
- `status`
- `prazo_correcao`

**Campos proibidos**
- qualquer campo territorial oficial duplicado
- CAR
- matrícula
- IDs de documentos fundiários como origem de verdade

**Entidades referenciadas**
- `AvaliacaoCertificacao`
- `EvidenciaCertificacao`
- `Pessoa`

**Quem pode criar**
- auditor
- gestor de certificação

**Quem pode atualizar**
- compliance
- responsável designado

**Quem pode apenas ler**
- gestor
- produtor/diretor
- auditor

**Regras de tenant_id**
- obrigatório

**Regras de auditoria**
- abertura, alteração, fechamento e verificação devem ser rastreados

### 3.7 PlanoAcaoCertificacao

**Responsabilidade**
- Definir ações corretivas, responsáveis e vencimentos para não conformidades.

**Campos mínimos**
- `id`
- `tenant_id`
- `nao_conformidade_id`
- `responsavel_pessoa_id`
- `descricao_acao`
- `prioridade`
- `status`
- `prazo`
- `conclusao_em`

**Campos proibidos**
- uso de `PlanoAcaoItem` financeiro/IA como contrato oficial
- dados territoriais oficiais

**Entidades referenciadas**
- `NaoConformidade`
- `Pessoa`

**Quem pode criar**
- compliance
- gestor de certificação

**Quem pode atualizar**
- responsável designado
- compliance

**Quem pode apenas ler**
- auditor
- gestor
- produtor/diretor

**Regras de tenant_id**
- obrigatório

**Regras de auditoria**
- toda mudança de status, prazo ou responsável deve ser auditável

### 3.8 RelatorioESG

**Responsabilidade**
- Consolidar score, indicadores e publicação ESG do domínio consumidor.

**Campos mínimos**
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

**Campos proibidos**
- CAR como dado copiado
- matrícula como dado copiado
- área operacional como verdade oficial independente

**Entidades referenciadas**
- `Propriedade`
- `Imóvel Rural`
- `PropriedadeImovel`
- `DocumentoAmbiental`
- `DocumentoLegal`
- `CadernoExportacao`
- `EPIEntrega`
- `VisitaTecnica`

**Quem pode criar**
- compliance
- gestor ESG

**Quem pode atualizar**
- até publicação; após publicado, só nova versão

**Quem pode apenas ler**
- produtor/diretor
- auditor
- comprador autorizado

**Regras de tenant_id**
- obrigatório

**Regras de auditoria**
- versão, publicação e revogação precisam de histórico

### 3.9 PassaporteRastreabilidade

**Responsabilidade**
- Expor a cadeia documental e de origem para auditoria, comprador ou certificadora.

**Campos mínimos**
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
- `gerado_em`

**Campos proibidos**
- CAR como cópia oficial
- matrícula como cópia oficial
- dados de operação sensíveis como fonte oficial pública

**Entidades referenciadas**
- `CadernoLoteComercial`
- `LoteRastreabilidade`
- `CadernoExportacao`
- `CertificacaoPropriedade` apenas como referência legada/compatível

**Quem pode criar**
- sistema de certificação/rastreabilidade

**Quem pode atualizar**
- somente publicação controlada e revogação controlada

**Quem pode apenas ler**
- auditor
- comprador autorizado
- público, se o snapshot for explicitamente público

**Regras de tenant_id**
- obrigatório

**Regras de auditoria**
- geração, publicação, revogação e acesso sensível devem ser auditáveis

## 4. Contratos Somente Leitura

### 4.1 Propriedade

Leitura permitida:
- identificação da propriedade
- área operacional
- infraestrutura
- talhões e glebas
- vínculos operacionais com o imóvel

Leitura proibida como cópia:
- CAR
- matrícula
- CCIR
- ITR
- NIRF
- SIGEF

### 4.2 Imóvel Rural

Leitura permitida:
- titularidade
- matrícula
- cartório
- CAR
- CCIR
- ITR
- NIRF
- SIGEF
- documentos fundiários

Leitura proibida como cópia:
- área operacional oficial
- talhões
- produção
- safra

### 4.3 PropriedadeImovel

Leitura permitida:
- vínculo oficial
- tipo de vínculo
- vigência
- origem documental
- área vinculada
- percentual vinculado

Leitura proibida como cópia:
- duplicação de território ou lastro fundiário

### 4.4 Documentos Fundiários

Leitura permitida:
- número
- status
- validade
- origem
- arquivo
- versão

### 4.5 Exploração Rural

Leitura permitida:
- dados operacionais da propriedade
- hierarquia de áreas
- áreas produtivas

### 4.6 Produtor / Pessoa

Leitura permitida:
- nome
- documento, quando necessário
- vínculo com propriedade ou responsável técnico

### 4.7 Caderno de Campo

Leitura permitida:
- entradas
- fotos
- visitas técnicas
- entregas de EPI
- exportações

### 4.8 Visitas Técnicas

Leitura permitida:
- data
- RT
- CREA
- observações

### 4.9 EPIs

Leitura permitida:
- entrega
- validade
- assinatura

### 4.10 Fotos / Evidências Operacionais

Leitura permitida:
- URL
- data de captura
- metadados geográficos
- flags de publicação

## 5. Destino Arquitetural Dos Modelos Existentes

| Modelo | Classificação | Destino |
| --- | --- | --- |
| `CertificacaoPropriedade` | compatibilidade / parcial | manter por enquanto como ponte legada, mas não como oficial final |
| `ESGIndicador` | adaptar | reaproveitar conceitualmente para o futuro `RelatorioESG`, mas não como contrato final |
| `ESGRelatorio` | substituir | serve de referência, porém o contrato oficial futuro deve ser novo |
| `LoteRastreabilidade` | manter | é útil como passaporte de lote e origem |
| `CadernoLoteComercial` | manter | snapshot e passaporte comercial continuam válidos |
| `ChecklistModelo` | compatibilidade | reaproveitável para inspeções, sem virar checklist oficial de certificação |
| `ChecklistRealizado` | compatibilidade | reaproveitável para validações operacionais e sanitárias |
| `PlanoAcaoItem` | não usar como oficial | modelo financeiro/IA não deve ser o contrato oficial do domínio consumidor |
| `MRVProjeto` | legado | relacionado a carbono/MRV, não ao núcleo de certificação |
| `MRVRelatorio` | legado | relacionado a carbono/MRV, não ao núcleo de certificação |

## 6. Matriz Oficial

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

## 7. Regras De Não Duplicação

1. Não armazenar CAR em Certificações/ESG.
2. Não armazenar matrícula em Certificações/ESG.
3. Não armazenar área operacional como fonte oficial.
4. Não armazenar vínculo posse/uso fora de `PropriedadeImovel`.
5. Snapshots podem existir apenas como evidência imutável, com origem e data.
6. Questionários nunca viram fonte oficial territorial/fundiária.
7. `PlanoAcaoItem` financeiro/IA não é o contrato oficial de certificação.

## 8. Estratégia De Snapshot

### Quando é permitido

- ao publicar relatório ESG;
- ao publicar passaporte de rastreabilidade;
- ao congelar evidência para auditoria;
- ao fechar avaliação ou auditoria relevante.

### Metadados obrigatórios

- `tenant_id`
- `origin_type`
- `origin_id`
- `created_at`
- `created_by` ou `responsavel_pessoa_id`
- `source_version`
- `snapshot_hash`
- `scope`
- `publico`

### O que não pode virar fonte oficial

- snapshot não substitui `Propriedade`
- snapshot não substitui `Imóvel Rural`
- snapshot não substitui `PropriedadeImovel`
- snapshot não substitui CAR, matrícula, CCIR, ITR, NIRF ou SIGEF

### Como rastrear origem

- por FKs explícitas ao objeto origem quando existir
- por `origin_type` + `origin_id` quando o snapshot vier de agregação documental
- por hash e timestamp de geração
- por versão do contrato que o gerou

## 9. Necessidade De Migration Futura

Há necessidade provável de migration futura.

Motivos:
- o contrato oficial ainda não existe fisicamente;
- os modelos existentes são parciais, legados ou de compatibilidade;
- haverá necessidade de normalização para `ProgramaCertificacao`, `ChecklistCertificacao`, `CriterioCertificacao`, `AvaliacaoCertificacao`, `EvidenciaCertificacao`, `NaoConformidade`, `PlanoAcaoCertificacao`, `RelatorioESG` e `PassaporteRastreabilidade`.

Não há necessidade de migration nesta fase.

## 10. Conclusão

Os contratos de Certificações/ESG devem nascer separados dos modelos financeiros, de MRV e dos modelos legados simplificados.

O próximo passo correto é a migration técnica do domínio consumidor, mas somente depois de aprovar a normalização deste contrato e sem tocar na fundação territorial/fundiária.
