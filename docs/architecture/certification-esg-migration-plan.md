# Plano de Migração Física do Domínio Consumidor Certificações/ESG

Status: Proposto
Data: 2026-06-21
Autores: AgroSaaS Architecture / Codex

## 1. Objetivo

Planejar a migration física do domínio consumidor Certificações/ESG sem criá-la ainda.

Este plano:
- parte dos contratos definidos em `certification-esg-contracts.md`;
- respeita o modelo conceitual de `certification-esg-domain-model.md`;
- não duplica dados territoriais/fundiários;
- não altera `Propriedade`, `Imóvel Rural` nem `PropriedadeImovel`;
- não usa `PlanoAcaoItem` financeiro/IA como contrato oficial;
- preserva compatibilidade com os modelos existentes até a transição.

## 2. Inventário De Migrations Relevantes

### 2.1 Relacionadas ao domínio adjacente

| Migration | Relevância | Observação |
| --- | --- | --- |
| `8c2e891d6ba9_caderno_campo.py` | alta | Base do caderno, evidências e timeline. |
| `56b72a50ad49_add_tenant_audit_log.py` | alta | Trilha de auditoria transversal. |
| `08c865830c43_checklist_agricola.py` | média | Indicador de padrão de checklist já existente no repositório. |
| `7109d2ac3e9e_checklist_agricola_templates_itens.py` | média | Referência de normalização de checklist. |
| `a4dc0640fdcf_add_lote_comercial_and_publica_foto.py` | alta | Base do passaporte comercial e snapshot público. |
| `2325278cb390_create_equipamento_calibracao.py` | média | Demonstra tabela dedicada para outro subdomínio de certificação. |
| `add_propriedade_imovel.py` | alta | Fundação territorial/fundiária oficial para consumo por certificações/ESG. |
| `b1c2d3e4f5a7_add_imoveis_avaliacoes.py` | alta | Lastro fundiário/documental adjacente. |

### 2.2 O que não existe ainda

- migrations oficiais para `ProgramaCertificacao`
- migrations oficiais para `ChecklistCertificacao`
- migrations oficiais para `CriterioCertificacao`
- migrations oficiais para `AvaliacaoCertificacao`
- migrations oficiais para `EvidenciaCertificacao`
- migrations oficiais para `NaoConformidade`
- migrations oficiais para `PlanoAcaoCertificacao`
- migrations oficiais para `RelatorioESG`
- migrations oficiais para `PassaporteRastreabilidade`

## 3. Tabelas Físicas Candidatas

### 3.1 `certificacao_programas`

**Responsabilidade**
- ciclo de vida de um programa, selo, norma ou iniciativa de conformidade.

**Campos obrigatórios**
- `id`
- `tenant_id`
- `propriedade_id`
- `imovel_rural_id`
- `propriedade_imovel_id`
- `nome`
- `tipo_programa`
- `status_programa`
- `data_inicio`
- `created_at`
- `updated_at`

**Campos opcionais**
- `pessoa_proprietario_id`
- `pessoa_responsavel_id`
- `organismo_certificador`
- `data_fim`
- `escopo`
- `observacoes`
- `numero_registro`

**FKs principais**
- `tenant_id -> tenants.id`
- `propriedade_id -> propriedades.id`
- `imovel_rural_id -> imoveis_rurais.id`
- `propriedade_imovel_id -> propriedade_imovel.id`
- `pessoa_proprietario_id -> pessoas.id`
- `pessoa_responsavel_id -> pessoas.id`

**Índices**
- `ix_certificacao_programas_tenant`
- `ix_certificacao_programas_propriedade`
- `ix_certificacao_programas_imovel`
- `ix_certificacao_programas_propriedade_imovel`
- índice por `status_programa`

**Constraints**
- unique parcial para evitar duplicidade ativa por escopo e programa
- check para vigência coerente

**RLS esperada**
- `ENABLE ROW LEVEL SECURITY`
- policies para `SELECT`, `INSERT`, `UPDATE`, `DELETE` por `app.current_tenant_id`
- `FORCE ROW LEVEL SECURITY`

**Compatibilidade**
- pode coexistir inicialmente com `CertificacaoPropriedade` até a transição

### 3.2 `certificacao_checklists`

**Responsabilidade**
- checklist por norma, versão e ciclo de auditoria.

**Campos obrigatórios**
- `id`
- `tenant_id`
- `programa_certificacao_id`
- `nome`
- `norma_versao`
- `status_checklist`
- `percentual_conformidade`
- `data_abertura`
- `created_at`

**Campos opcionais**
- `data_fechamento`
- `observacoes`
- `resultado_geral`

**FKs principais**
- `tenant_id -> tenants.id`
- `programa_certificacao_id -> certificacao_programas.id`

**Índices**
- `ix_certificacao_checklists_tenant`
- `ix_certificacao_checklists_programa`
- `ix_certificacao_checklists_status`

**Constraints**
- unique por `programa_certificacao_id + norma_versao + status_aberto` quando aplicável

**RLS esperada**
- aplicada por tenant

**Compatibilidade**
- pode conviver com checklists operacionais; não substitui `ChecklistModelo` imediatamente

### 3.3 `certificacao_criterios`

**Responsabilidade**
- unidade mínima de requisito auditável.

**Campos obrigatórios**
- `id`
- `tenant_id`
- `checklist_certificacao_id`
- `codigo`
- `descricao`
- `categoria`
- `peso`
- `obrigatorio`
- `status`
- `created_at`

**Campos opcionais**
- `observacoes`
- `referencia_normativa`

**FKs principais**
- `tenant_id -> tenants.id`
- `checklist_certificacao_id -> certificacao_checklists.id`

**Índices**
- `ix_certificacao_criterios_tenant`
- `ix_certificacao_criterios_checklist`
- `ix_certificacao_criterios_codigo`

**Constraints**
- unique por `checklist_certificacao_id + codigo`
- check em `peso >= 0`

**RLS esperada**
- por tenant

**Compatibilidade**
- substitui apenas a necessidade de critérios ad hoc espalhados

### 3.4 `certificacao_avaliacoes`

**Responsabilidade**
- avaliação de checklist/critério com nota, parecer e auditoria.

**Campos obrigatórios**
- `id`
- `tenant_id`
- `checklist_certificacao_id`
- `avaliador_pessoa_id`
- `data_avaliacao`
- `resultado_avaliacao`
- `nota`
- `created_at`

**Campos opcionais**
- `parecer`
- `observacoes`
- `retificado_por_id`
- `retificado_em`

**FKs principais**
- `tenant_id -> tenants.id`
- `checklist_certificacao_id -> certificacao_checklists.id`
- `avaliador_pessoa_id -> pessoas.id`
- `retificado_por_id -> usuarios.id` ou `pessoas.id` conforme padrão existente

**Índices**
- `ix_certificacao_avaliacoes_tenant`
- `ix_certificacao_avaliacoes_checklist`
- `ix_certificacao_avaliacoes_data`

**Constraints**
- check em resultado válido

**RLS esperada**
- por tenant

**Compatibilidade**
- não deve usar modelos financeiros como armazenamento final

### 3.5 `certificacao_evidencias`

**Responsabilidade**
- anexar prova documental, foto, assinatura, laudo, snapshot ou URL externa.

**Campos obrigatórios**
- `id`
- `tenant_id`
- `avaliacao_certificacao_id`
- `tipo_evidencia`
- `origem_documental`
- `hash_conteudo`
- `publica`
- `created_at`

**Campos opcionais**
- `arquivo_url`
- `snapshot_json`
- `snapshot_hash`
- `observacoes`
- `origin_type`
- `origin_id`
- `source_version`

**FKs principais**
- `tenant_id -> tenants.id`
- `avaliacao_certificacao_id -> certificacao_avaliacoes.id`

**Índices**
- `ix_certificacao_evidencias_tenant`
- `ix_certificacao_evidencias_avaliacao`
- `ix_certificacao_evidencias_publica`

**Constraints**
- check para `origin_type`/`origin_id` quando snapshot derivado

**RLS esperada**
- por tenant

**Compatibilidade**
- pode referenciar caderno, visitas técnicas, EPI e exportações por leitura

### 3.6 `certificacao_nao_conformidades`

**Responsabilidade**
- registrar desvios, falhas e pendências.

**Campos obrigatórios**
- `id`
- `tenant_id`
- `avaliacao_certificacao_id`
- `codigo`
- `descricao`
- `severidade_nao_conformidade`
- `status`
- `prazo_correcao`
- `created_at`

**Campos opcionais**
- `responsavel_pessoa_id`
- `evidencia_correcao_id`
- `fechada_em`
- `observacoes`

**FKs principais**
- `tenant_id -> tenants.id`
- `avaliacao_certificacao_id -> certificacao_avaliacoes.id`
- `responsavel_pessoa_id -> pessoas.id`
- `evidencia_correcao_id -> certificacao_evidencias.id`

**Índices**
- `ix_certificacao_nc_tenant`
- `ix_certificacao_nc_avaliacao`
- `ix_certificacao_nc_status`

**Constraints**
- check de severidade
- check de status

**RLS esperada**
- por tenant

**Compatibilidade**
- não deve migrar para plano de ação financeiro

### 3.7 `certificacao_planos_acao`

**Responsabilidade**
- ações corretivas e de melhoria vinculadas à não conformidade.

**Campos obrigatórios**
- `id`
- `tenant_id`
- `nao_conformidade_id`
- `descricao_acao`
- `status_plano_acao`
- `prioridade`
- `prazo`
- `created_at`

**Campos opcionais**
- `responsavel_pessoa_id`
- `conclusao_em`
- `comentarios`

**FKs principais**
- `tenant_id -> tenants.id`
- `nao_conformidade_id -> certificacao_nao_conformidades.id`
- `responsavel_pessoa_id -> pessoas.id`

**Índices**
- `ix_certificacao_planos_tenant`
- `ix_certificacao_planos_nc`
- `ix_certificacao_planos_status`

**Constraints**
- check em status e prioridade

**RLS esperada**
- por tenant

**Compatibilidade**
- substitui gradualmente qualquer uso de `PlanoAcaoItem` como compliance

### 3.8 `esg_relatorios`

**Responsabilidade**
- consolidar relatórios ESG versionados e publicados.

**Campos obrigatórios**
- `id`
- `tenant_id`
- `propriedade_id`
- `imovel_rural_id`
- `propriedade_imovel_id`
- `periodo_inicio`
- `periodo_fim`
- `score_total`
- `status_relatorio_esg`
- `versao`
- `created_at`

**Campos opcionais**
- `snapshot_base`
- `url_pdf`
- `published_at`
- `published_by_id`
- `observacoes`

**FKs principais**
- `tenant_id -> tenants.id`
- `propriedade_id -> propriedades.id`
- `imovel_rural_id -> imoveis_rurais.id`
- `propriedade_imovel_id -> propriedade_imovel.id`
- `published_by_id -> usuarios.id`

**Índices**
- `ix_esg_relatorios_tenant`
- `ix_esg_relatorios_propriedade`
- `ix_esg_relatorios_periodo`
- `ix_esg_relatorios_status`

**Constraints**
- unique por escopo + período + versão quando publicado

**RLS esperada**
- por tenant

**Compatibilidade**
- substitui gradualmente `ESGRelatorio` genérico

### 3.9 `rastreabilidade_passaportes`

**Responsabilidade**
- expor passaporte público/privado de origem e auditoria.

**Campos obrigatórios**
- `id`
- `tenant_id`
- `propriedade_id`
- `imovel_rural_id`
- `propriedade_imovel_id`
- `caderno_lote_comercial_id`
- `qr_code_token`
- `snapshot_json`
- `snapshot_hash`
- `status_passaporte`
- `gerado_em`

**Campos opcionais**
- `publico`
- `revogado_em`
- `revogado_por_id`
- `observacoes`

**FKs principais**
- `tenant_id -> tenants.id`
- `propriedade_id -> propriedades.id`
- `imovel_rural_id -> imoveis_rurais.id`
- `propriedade_imovel_id -> propriedade_imovel.id`
- `caderno_lote_comercial_id -> caderno_lotes_comerciais.id`
- `revogado_por_id -> usuarios.id`

**Índices**
- `ix_passaportes_tenant`
- `ix_passaportes_token`
- `ix_passaportes_status`

**Constraints**
- unique de `qr_code_token`
- check em status

**RLS esperada**
- por tenant, com eventual política pública apenas para snapshot publicado

**Compatibilidade**
- substitui gradualmente snapshots ad hoc

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

### Sugestão de valores

- `status_programa`: `DRAFT`, `ATIVO`, `EM_AUDITORIA`, `SUSPENSO`, `ENCERRADO`, `REVOGADO`
- `tipo_certificacao`: `GLOBALGAP`, `RAINFOREST`, `FAIRTRADE`, `ORGANICO`, `CERTIFICAMINAS`, `PROJETO_RAISES`, `OUTRO`
- `status_checklist`: `ABERTO`, `EM_ANDAMENTO`, `CONCLUIDO`, `REABERTO`, `CANCELADO`
- `resultado_avaliacao`: `APROVADO`, `APROVADO_COM_RESSALVAS`, `REPROVADO`, `PENDENTE`
- `tipo_evidencia`: `FOTO`, `PDF`, `ASSINATURA`, `LAUDO`, `SNAPSHOT`, `URL_EXTERNA`, `OUTRO`
- `severidade_nao_conformidade`: `BAIXA`, `MEDIA`, `ALTA`, `CRITICA`
- `status_plano_acao`: `PENDENTE`, `EM_ANDAMENTO`, `BLOQUEADO`, `CONCLUIDO`, `CANCELADO`
- `status_relatorio_esg`: `RASCUNHO`, `PUBLICADO`, `VENCIDO`, `REVOGADO`
- `status_passaporte`: `RASCUNHO`, `ATIVO`, `REVOGADO`, `EXPIRADO`
- `prioridade_plano_acao`: `BAIXA`, `MEDIA`, `ALTA`, `URGENTE`

## 5. Estratégia Para Modelos Existentes

| Modelo | Classificação | Estratégia |
| --- | --- | --- |
| `CertificacaoPropriedade` | compatibilidade somente leitura / adaptar depois | manter até o novo programa oficial existir; migrar por referência futura. |
| `ESGIndicador` | fora do domínio oficial / adaptar depois | usar como fonte de leitura histórica, mas não como contrato final. |
| `ESGRelatorio` | substituir gradualmente | novos relatórios devem escrever em `esg_relatorios`. |
| `LoteRastreabilidade` | manter com FK futura | permanece útil como ponte de leitura e rastreabilidade. |
| `CadernoLoteComercial` | manter com FK futura | permanece útil como snapshot/passaporte comercial. |
| `ChecklistModelo` | compatibilidade somente leitura | reaproveitar apenas para inspeções operacionais. |
| `ChecklistRealizado` | compatibilidade somente leitura | reaproveitar apenas como evidência operacional/inspeção. |
| `PlanoAcaoItem` | fora do domínio oficial | não usar como plano oficial de certificação. |
| `MRVProjeto` | legado histórico | não usar como oficial do domínio consumidor. |
| `MRVRelatorio` | legado histórico | não usar como oficial do domínio consumidor. |

## 6. Ordem Segura De Criação

1. `certificacao_programas`
2. `certificacao_checklists`
3. `certificacao_criterios`
4. `certificacao_avaliacoes`
5. `certificacao_evidencias`
6. `certificacao_nao_conformidades`
7. `certificacao_planos_acao`
8. `esg_relatorios`
9. `rastreabilidade_passaportes`

### Justificativa

- primeiro o agregado de programa;
- depois checklist e critérios;
- depois avaliação e evidência;
- depois não conformidade e ação;
- por fim relatórios e passaporte.

## 7. Uma Migration Ou Múltiplas

### Recomendação

**Migrations separadas por subdomínio, em lote coordenado, não uma única migration monolítica.**

### Motivo

- reduz blast radius;
- permite validar cada agregado;
- facilita rollback parcial;
- separa `certificacao_*`, `esg_*` e `passaporte_*`;
- respeita a maturidade desigual entre rastreabilidade, certificação e ESG.

### Sugestão prática

1. migration 1: `certificacao_programas` + enums base
2. migration 2: `certificacao_checklists` + `certificacao_criterios`
3. migration 3: `certificacao_avaliacoes` + `certificacao_evidencias`
4. migration 4: `certificacao_nao_conformidades` + `certificacao_planos_acao`
5. migration 5: `esg_relatorios`
6. migration 6: `rastreabilidade_passaportes`

## 8. Compatibilidade E Transição

### Compatibilidade curta

- manter leitura de `CertificacaoPropriedade`, `ESGIndicador`, `ESGRelatorio`, `LoteRastreabilidade`, `CadernoLoteComercial`, `ChecklistModelo`, `ChecklistRealizado`, `PlanoAcaoItem`, `MRVProjeto`, `MRVRelatorio`

### Estratégia de transição

- criar novos contratos sem quebrar leitura antiga;
- permitir fase de espelhamento apenas onde fizer sentido;
- depois migrar consumers para os novos nomes;
- por último descontinuar os modelos legados que perderem papel.

### O que não deve acontecer

- copiar CAR, matrícula, CCIR, ITR, NIRF ou SIGEF para as novas tabelas;
- usar `PlanoAcaoItem` como plano oficial;
- misturar território/fundiário com avaliação de certificação.

## 9. RLS Esperado

Todas as novas tabelas devem:

- ter `tenant_id` obrigatório;
- ter `ENABLE ROW LEVEL SECURITY`;
- ter policy para `SELECT`, `INSERT`, `UPDATE`, `DELETE`;
- usar `app.current_tenant_id`;
- usar `FORCE ROW LEVEL SECURITY` para endurecimento.

Para `rastreabilidade_passaportes`, pode haver exceção controlada para leitura pública de snapshot publicado, mas nunca para edição.

## 10. Conclusão

A próxima fase deve criar migrations separadas por subdomínio, começando pelo núcleo de certificação e depois ESG/passaporte.

A criação em blocos reduz risco e preserva a compatibilidade com os modelos legados até a conclusão da transição.
