# Governanca Documental Territorial e Fundiaria do AgroSaaS

**Status:** APROVADA
**Categoria:** Arquitetura de Dominio
**Tipo:** Regra Arquitetural Imutavel
**Origem:** AGRI-DOMAIN-001, AGRI-DOMAIN-002, ADR-00XX e EXECUTION-06
**Ultima Revisao:** 2026-06-21

## 1. Objetivo

Definir a governanca documental oficial do dominio territorial/fundiario do AgroSaaS, deixando explicito:

- onde cada documento vive hoje;
- quem e dono da informacao;
- quem apenas consome ou espelha;
- qual e a fonte da verdade;
- quais documentos sao criticos para auditoria, ESG, certificacao, Due Diligence e Projeto Raizes;
- quais campos permanecem legados e quais nao podem virar nova fonte oficial.

Esta norma nao cria novo dominio, nao cria nova tabela e nao exige migracao adicional neste momento.

## 2. Escopo

### 2.1 Documentos fundiarios e juridicos

- CAR
- CCIR
- ITR
- NIRF
- SIGEF
- Matriculas
- Cartorios
- Contratos
- Avaliacoes

### 2.2 Evidencias territoriais e ambientais correlatas

- APP
- Reserva Legal
- Licencas Ambientais
- Arquivos geoespaciais
- Historicos de documento
- Historico patrimonial

### 2.3 Evidencias operacionais relacionadas

- Documentos de exploracao rural
- Registros de operacao territorial
- Arquivos de suporte ao cadastro operacional

## 3. Inventario Documental Consolidado

| Documento | Onde esta hoje | Entidade proprietaria | Entidades consumidoras | Dominio responsavel | Criticidade | Obrigatorio | Auditavel |
|---|---|---|---|---|---|---|---|
| CAR | `imoveis_documentos` (`DocumentoLegal` tipo `CAR`), `imoveis_rurais.car_numero`; legado em `unidades_produtivas.codigo_car` e `cadastros_areas_matriculas.car_numero` | Imoveis Rurais | Propriedades, Ambiental, Certificacoes, Raizes | Fundiario / documental | Alta | Sim | Sim |
| CCIR | `imoveis_documentos` (`DocumentoLegal` tipo `CCIR`), `imoveis_rurais.ccir_numero`; legado em `unidades_produtivas.ccir` e `cadastros_areas_matriculas.ccir` | Imoveis Rurais | Propriedades, Fiscal, Contratos, Raizes | Fundiario / fiscal | Alta | Sim | Sim |
| ITR | `imoveis_documentos` (`DocumentoLegal` tipo `ITR_DITR`); legado em `cadastros_areas_matriculas.itr_numero` | Imoveis Rurais | Financeiro, Fiscal, Compliance | Fundiario / fiscal | Alta | Sim | Sim |
| NIRF | `imoveis_rurais.nirf`; legado em `unidades_produtivas.nirf` e `cadastros_areas_matriculas.nirf` | Imoveis Rurais | Propriedades, Fiscal, Compliance | Fundiario / fiscal | Alta | Sim | Sim |
| SIGEF | legado em `unidades_produtivas.sigef_codigo`; ainda sem campo canonicamente consolidado em `imoveis_rurais` | Imoveis Rurais | Propriedades, Georreferenciamento, Raizes | Fundiario / geoespacial | Alta | Sim | Parcial | 
| Matriculas | `imoveis_matriculas`, `imoveis_rurais.numero_matricula`, legado em `cadastros_areas_matriculas.numero_matricula` | Imoveis Rurais | Propriedades, Arrendamentos, Due Diligence, Raizes | Fundiario / registral | Alta | Sim | Sim |
| Cartorios | `imoveis_cartorios`, `imoveis_rurais.cartorio_id`, legado em `cadastros_areas_matriculas.cartorio` | Imoveis Rurais | Matriculas, Contratos, Compliance | Fundiario / registral | Alta | Sim | Sim |
| Contratos de arrendamento / parceria | `imoveis_arrendamentos` | Imoveis Rurais | Financeiro, Compliance, Propriedades, Raizes | Fundiario / contratual | Alta | Conforme caso | Sim |
| Avaliacoes patrimoniais | `imoveis_avaliacoes` | Imoveis Rurais | Financeiro, Garantias, Raizes | Fundiario / patrimonial | Alta | Conforme caso | Sim |
| APP / Reserva Legal | `cadastros_areas_registros_ambientais`; espelhos em `imoveis_rurais.area_app_ha` e `imoveis_rurais.area_rl_ha` | Compartilhado | Ambiental, ESG, Certificacoes, Raizes | Compartilhado | Alta | Sim | Sim |
| Arquivos geoespaciais | `cadastros_arquivos_geo` | Propriedades | Ambiental, Geoprocessamento, Auditoria | Territorial operacional | Media | Conforme caso | Sim |
| Documentos de exploracao | `cadastros_documentos_exploracao`; `exploracoes_rurais.documento_s3_key` e `documento_tipo` | Propriedades | Operacao, Auditoria, Compliance operacional | Territorial operacional | Media | Conforme caso | Sim |
| Historico documental | `imoveis_documentos_historico`, `cadastros_areas_valores_patrimoniais` | Respectiva origem | Auditoria, Compliance, Raizes | Compartilhado | Alta | Sim | Sim |

## 4. Fonte da Verdade

### 4.1 Fonte documental fundiaria

O dominio `Imoveis Rurais` e a fonte oficial para:

- titularidade;
- matricula;
- cartorio;
- CAR;
- CCIR;
- ITR;
- NIRF;
- SIGEF;
- contratos fundiarios;
- avaliacoes patrimoniais.

### 4.2 Fonte operacional territorial

O dominio `Propriedades` e a fonte oficial para:

- area rural operacional;
- glebas;
- talhoes;
- pastagens;
- infraestrutura;
- manejo;
- safra;
- producao;
- documentos operacionais de exploracao.

### 4.3 Fonte de vinculacao

`PropriedadeImovel` e a unica fonte oficial do relacionamento entre os dois dominios.

Ela nao deve armazenar:

- documento integral;
- matricula completa;
- cartorio completo;
- titularidade completa;
- safra;
- producao;
- operação;
- arquivo binario.

## 5. Duplicidades e Conflitos Identificados

### 5.1 Duplicidades legadas

- `unidades_produtivas.codigo_car` duplica a prova legal do CAR.
- `unidades_produtivas.nirf` duplica a origem fundiaria.
- `unidades_produtivas.ccir` duplica a origem fundiaria.
- `unidades_produtivas.sigef_codigo` concentra um identificador fundiario/geoespacial que deveria ser formalizado no dominio fundiario.
- `cadastros_areas_matriculas.car_numero`, `nirf`, `ccir`, `itr_numero`, `cartorio`, `comarca` mantem espelhos historicos do lastro legal.

### 5.2 Conflitos evitados pela norma

- Propriedades nao pode virar repositório de CAR, CCIR, ITR ou matricula.
- Imoveis Rurais nao pode virar repositório de talhoes, safras, producao ou infraestrutura operacional.
- PropriedadeImovel nao pode virar tabela documental nem tabela territorial.

## 6. Matriz de Governanca

| Regra | Decisao |
|---|---|
| Uma informacao possui uma unica fonte oficial | Sim |
| Espelhos legados podem existir durante compatibilidade | Sim, como leitura e transicao |
| Espelhos legados podem ser editados livremente | Nao |
| PropriedadeImovel pode armazenar documentos completos | Nao |
| A rastreabilidade deve chegar ao Imovel Rural | Sim |
| A governanca documental exige nova migracao agora | Nao |

## 7. Requisitos Futuros

### 7.1 ESG

- prova legal da origem territorial;
- prova de area APP e Reserva Legal;
- evidencia documental auditavel;
- trilha de alteracoes com historico preservado.

### 7.2 Certificacoes

- rastreio de lastro fundiario;
- validacao de CAR, CCIR, ITR e matriculas;
- evidencias exportaveis para auditorias.

### 7.3 Due Diligence e Compliance Fundiario

- cadeia documental completa;
- relacao entre operação e lastro legal;
- historico de vigencia de vinculos;
- evidencias de origem e alteracao.

### 7.4 Projeto Raizes

- rastreabilidade ate o Imovel Rural;
- prova documental do lastro legal;
- prova de origem da producao;
- base para auditoria publica ou semi-publica.

## 8. Necessidade de Migração

Nenhuma migracao adicional e exigida por esta fase.

Motivo:

- a convergencia estrutural ja existe;
- a ponte oficial `PropriedadeImovel` ja esta em vigor;
- os documentos continuam segregados por dominio;
- a tarefa atual e de governanca documental e consistente com o estado fisico existente.

Eventual limpeza definitiva dos espelhos legados em `unidades_produtivas` e `cadastros_areas_matriculas` deve ser tratada em ciclo futuro, com ADR propria e validacao de impacto.

## 9. Regras Imutaveis

- CAR, CCIR, ITR, NIRF, SIGEF, matriculas e cartorios pertencem ao dominio fundiario.
- Talhoes, glebas, pastagens, infraestrutura e safra pertencem ao dominio operacional.
- PropriedadeImovel e a unica ponte oficial N:N.
- Nenhuma entidade de ponte deve armazenar documento integral.
- Nenhum dominio pode criar nova fonte oficial para o mesmo dado.
- Dados espelhados so podem existir como leitura ou compatibilidade, nunca como nova verdade.
- Toda evidencia documental relevante deve ser auditavel.
- Toda cadeia de rastreabilidade deve alcançar o Imovel Rural.

## 10. Disciplina de Leitura e Escrita

Esta governanca documental opera junto das Regras de Anticorrupcao dos Legados Territoriais.

### 10.1 Fontes oficiais de escrita

- `Propriedades` para territorio operacional.
- `Imoveis Rurais` para lastro documental e fundiario.
- `PropriedadeImovel` para o vinculo oficial.

### 10.2 Fontes de compatibilidade

- `unidades_produtivas` com `codigo_car`, `nirf`, `ccir`, `sigef_codigo`.
- `cadastros_areas_matriculas`.
- `cadastros_areas_registros_ambientais`.
- shims ou rotas legadas mantidas por transicao.

### 10.3 Regras de uso

- compatibilidade nao e fonte oficial;
- legado historico nao pode ser editado como master data;
- o backend deve priorizar a origem oficial quando houver conflito;
- o frontend deve exibir campos espelhados como derivados ou somente leitura.
