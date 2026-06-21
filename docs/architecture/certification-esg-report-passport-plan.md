# Certificação/ESG - Plano de Relatório ESG e Passaporte de Rastreabilidade

Status: Proposto  
Data: 2026-06-21  
Autores: AgroSaaS Architecture / Codex

## 1. Objetivo

Planejar o próximo bloco funcional do domínio consumidor de Certificações/ESG: `RelatorioESG` e `PassaporteRastreabilidade`.

Este plano não implementa backend, frontend, models físicos nem migration. Ele consolida a modelagem conceitual final, a política de snapshot e a estratégia de evolução física para uma futura migration controlada.

## 2. Contexto Arquitetural

O AgroSaaS já consolidou:

- `Propriedade` como fonte oficial operacional/territorial;
- `Imóvel Rural` como fonte oficial jurídica/fundiária/documental;
- `PropriedadeImovel` como vínculo canônico `N:N`;
- Certificações/ESG como domínio consumidor;
- evidências, não conformidades e planos de ação como escrita local do domínio consumidor;
- visões territoriais/fundiárias read-only e APIs agregadas;
- rastreabilidade comercial e snapshots públicos para lotes.

O novo bloco deve consumir essas bases sem criar uma nova fonte oficial territorial ou fundiária.

## 3. Modelos Existentes Revisados

### 3.1 Diretos e adjacentes

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
- evidências, não conformidades e planos de ação recém-criados

### 3.2 Leitura arquitetural desses modelos

- `ESGIndicador` e `ESGRelatorio` são referências parciais, úteis como insumo de normalização, mas não canônicas.
- `LoteRastreabilidade` e `CadernoLoteComercial` já carregam o padrão de snapshot imutável e passaporte de origem.
- `CadernoExportacao` é a melhor base de referência para PDF/assinatura/hash/documentação congelada.
- `CertificacaoPropriedade` é ponte legada, não contrato final.
- `TenantAuditLog` é a trilha transversal de auditoria a ser mantida.

## 4. Modelo Conceitual Final

### 4.1 `RelatorioESG`

Responsabilidade:

- consolidar leitura, score, trilha documental e publicação ESG do domínio consumidor.

Campos conceituais:

- `id`
- `tenant_id`
- `propriedade_id`
- `imovel_rural_id`
- `propriedade_imovel_id`
- `periodo_inicio`
- `periodo_fim`
- `versao`
- `status`
- `publico`
- `score_total`
- `score_ambiental`
- `score_social`
- `score_governanca`
- `snapshot_base`
- `snapshot_hash`
- `url_pdf`
- `gerado_em`
- `publicado_em`
- `revogado_em`

Relação com o domínio:

- consome `Propriedade`, `Imóvel Rural`, `PropriedadeImovel`;
- consome `CadernoCampoEntrada`, `CadernoCampoFoto`, `VisitaTecnica`, `EPIEntrega`, `CadernoExportacao`;
- consome `EvidenciaCertificacao`, `NaoConformidade`, `PlanoAcaoCertificacao`;
- não escreve em entidades territoriais/fundiárias;
- não duplica CAR, matrícula, CCIR, ITR, NIRF, SIGEF ou área operacional.

### 4.2 `RelatorioESGIndicador`

Responsabilidade:

- detalhar os indicadores do relatório ESG em nível de item.

Campos conceituais:

- `id`
- `tenant_id`
- `relatorio_esg_id`
- `codigo`
- `nome`
- `categoria`
- `valor`
- `unidade`
- `meta`
- `peso`
- `fonte_tipo`
- `fonte_id`
- `snapshot_json`
- `snapshot_hash`

Regras:

- indicador é derivado do relatório;
- não se torna fonte oficial territorial;
- `snapshot_json` é somente evidência imutável da versão gerada.

### 4.3 `RelatorioESGEvidencia`

Responsabilidade:

- conectar o relatório ESG às evidências, anexos e peças documentais que o suportam.

Campos conceituais:

- `id`
- `tenant_id`
- `relatorio_esg_id`
- `evidencia_certificacao_id`
- `origem_tipo`
- `origem_id`
- `tipo_vinculo`
- `snapshot_json`
- `snapshot_hash`

Regras:

- vínculo apenas de leitura/derivação para publicação;
- não substitui a evidência original;
- não pode virar uma nova cópia oficial do documento.

### 4.4 `PassaporteRastreabilidade`

Responsabilidade:

- expor a cadeia documental e de origem para auditoria, comprador ou certificadora.

Campos conceituais:

- `id`
- `tenant_id`
- `propriedade_id`
- `imovel_rural_id`
- `propriedade_imovel_id`
- `caderno_lote_comercial_id`
- `codigo_publico`
- `status`
- `publico`
- `snapshot_json`
- `snapshot_hash`
- `gerado_em`
- `publicado_em`
- `revogado_em`

Relação com o domínio:

- consome `CadernoLoteComercial` e `LoteRastreabilidade`;
- pode referenciar `CadernoExportacao` como base documental;
- pode enxergar `CertificacaoPropriedade` apenas como compatibilidade legada;
- não duplica território ou lastro fundiário.

### 4.5 `PassaporteRastreabilidadeEvento`

Responsabilidade:

- registrar os eventos relevantes do passaporte, como geração, publicação, atualização controlada, revogação e acesso auditável.

Campos conceituais:

- `id`
- `tenant_id`
- `passaporte_rastreabilidade_id`
- `evento_tipo`
- `evento_status`
- `descricao`
- `origem_tipo`
- `origem_id`
- `snapshot_json`
- `snapshot_hash`
- `created_at`
- `created_by`

### 4.6 `PassaporteRastreabilidadeEvidencia`

Responsabilidade:

- relacionar passaporte com evidências suportadas pelo domínio.

Campos conceituais:

- `id`
- `tenant_id`
- `passaporte_rastreabilidade_id`
- `evidencia_certificacao_id`
- `relatorio_esg_id` opcional
- `origem_tipo`
- `origem_id`
- `snapshot_json`
- `snapshot_hash`

## 5. Dados Apenas Lidos

O bloco novo deve ler, e nunca duplicar como fonte oficial:

- `Propriedade`
- `Imóvel Rural`
- `PropriedadeImovel`
- Caderno de campo
- Lotes
- Comercialização/exportação
- Evidências de certificação
- Não conformidades
- Planos de ação

### Leitura permitida por categoria

- **Propriedade**: área operacional, infraestrutura, hierarquia de áreas, contexto produtivo.
- **Imóvel Rural**: titularidade, matrícula, documentos fundiários, CAR, CCIR, ITR, NIRF, SIGEF.
- **PropriedadeImovel**: vínculo canônico, vigência, área vinculada, percentual vinculado.
- **Caderno de campo**: entradas, fotos, visitas, EPI, exportações.
- **Lotes**: origem física e cadeia de custódia.
- **Comercialização/exportação**: origem documental e lastro comercial.
- **Certificações/ESG**: evidências, NCs e planos.

## 6. Política de Snapshot

### 6.1 Quando o relatório ESG gera snapshot

- na publicação do relatório;
- na alteração controlada de versão;
- ao congelar o material auditável para entrega a cliente, auditor ou comprador.

### 6.2 Quando o passaporte gera snapshot

- na geração do passaporte;
- na publicação controlada;
- ao revogar ou arquivar versões anteriores.

### 6.3 Campos permitidos no snapshot

- identificadores de origem;
- período de vigência;
- status da versão;
- score e indicadores derivados;
- relação com evidências;
- URL ou referência documental;
- hashes e metadados de integridade;
- timestamp de geração;
- autor gerador ou responsável.

### 6.4 Campos proibidos como fonte oficial

- CAR como cópia oficial;
- matrícula como cópia oficial;
- CCIR, ITR, NIRF e SIGEF como cópia oficial;
- área operacional como fonte oficial independente;
- vínculo posse/uso fora de `PropriedadeImovel`.

### 6.5 Hash obrigatório

Todo snapshot publicado deve carregar:

- `snapshot_hash`;
- `snapshot_version`;
- `created_at`;
- `created_by` ou `responsavel_pessoa_id`;
- `origin_type`;
- `origin_id`.

### 6.6 Versionamento

- cada publicação gera uma nova versão imutável;
- versões anteriores permanecem auditáveis;
- revogação não apaga o histórico;
- o estado atual aponta apenas para a versão ativa.

### 6.7 Público / Privado

- relatório ESG pode ser privado ou público, conforme estratégia do tenant;
- passaporte de rastreabilidade pode ser público quando explicitamente aprovado;
- o snapshot público deve omitir dados sensíveis que não são necessários para autenticidade.

### 6.8 Trilha de auditoria

Devem ser auditáveis:

- geração;
- alteração de status;
- publicação;
- revogação;
- acesso público;
- exportação;
- snapshot refresh.

## 7. Status Oficiais Sugeridos

### `RelatorioESG`

- `RASCUNHO`
- `EM_REVISAO`
- `PUBLICADO`
- `CANCELADO`

### `PassaporteRastreabilidade`

- `RASCUNHO`
- `EM_VALIDACAO`
- `PUBLICADO`
- `REVOGADO`

## 8. Estratégia de Modelagem Física Futura

Há necessidade provável de migration futura.

### Motivos

- os modelos canônicos ainda não existem fisicamente;
- os modelos existentes são parciais, legados ou compatíveis;
- a estrutura nova depende de versionamento e snapshots próprios;
- a publicação exige constraints, enums e trilha de auditoria dedicadas.

## 9. Recomendações de Migration

Recomendação: `migration` em lote único para o bloco de publicação, com sub-tabelas no mesmo ciclo.

### Por que lote único

- `RelatorioESG` e `PassaporteRastreabilidade` compartilham a mesma lógica de snapshot, publicação e auditoria;
- evitam duplicação de enums, policies e helpers;
- reduzem o risco de inconsistência entre relatórios e passaportes.

### Quando dividir

Se a implementação física exigir ritmos diferentes de entrega, a divisão aceitável é:

1. lote técnico de base de publicação;
2. lote técnico de passaporte;
3. lote técnico de relatórios e indicadores.

Mas a recomendação padrão continua sendo uma migration única, desde que o escopo físico permaneça coeso.

## 10. Conclusão

O AgroSaaS já possui base suficiente para modelar o bloco de `RelatorioESG` e `PassaporteRastreabilidade` sem inventar nova fonte oficial territorial/fundiária.

O passo correto agora é apenas aprovação arquitetural deste plano. A implementação física deve vir depois, com migration controlada e sem alterar a fundação canônica de território, imóvel rural e vínculo `PropriedadeImovel`.
