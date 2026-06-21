# Regras de Anticorrupcao dos Legados Territoriais do AgroSaaS

**Status:** APROVADA
**Categoria:** Arquitetura de Dominio
**Tipo:** Regra Arquitetural Imutavel
**Origem:** AGRI-DOMAIN-001, AGRI-DOMAIN-002, ADR-00XY, EXECUTION-07
**Ultima Revisao:** 2026-06-21

## 1. Objetivo

Impedir que espelhos legados, tabelas de apoio antigas e campos historicos voltem a ser tratados como fonte oficial do dominio territorial/fundiario.

Esta norma nao remove legados, nao altera migrations e nao quebra compatibilidade. Ela define limites de leitura, escrita e responsabilidade.

## 2. Principios

1. Propriedades e a fonte oficial operacional, territorial e produtiva.
2. Imoveis Rurais e a fonte oficial juridica, patrimonial, documental e fiscal.
3. PropriedadeImovel e a unica fonte oficial do vinculo N:N.
4. Legado historico pode ser lido para compatibilidade, mas nao pode virar fonte oficial.
5. Espelho legados nao podem ser alterados como se fossem master data.
6. Toda escrita deve ocorrer na origem oficial do dado.

## 3. Classificacao Oficial dos Pontos de Dados

| Ponto | Classe | Escrita permitida | Leitura permitida | Risco futuro |
|---|---|---|---|---|
| `Propriedades` / `AreaRural` / `ExploracaoRural` | Fonte oficial operacional | Sim | Sim | Baixo |
| `Imoveis Rurais` / `DocumentoLegal` / `ContratoArrendamento` / `AvaliacaoImovel` / `Cartorio` / `MatriculaImovelRural` | Fonte oficial fundiaria | Sim | Sim | Baixo |
| `PropriedadeImovel` | Fonte oficial de vinculacao | Sim | Sim | Baixo |
| `unidades_produtivas` com `codigo_car`, `nirf`, `ccir`, `sigef_codigo` | Compatibilidade historica | Nao para novos dados fundiarios | Sim, apenas leitura historica | Alto |
| `cadastros_areas_matriculas` | Compatibilidade historica / apoio legado | Nao para nova fonte oficial | Sim, ate saneamento futuro | Alto |
| `cadastros_areas_registros_ambientais` | Compatibilidade historica / apoio ambiental | Nao para nova fonte oficial | Sim, ate consolidacao futura | Medio |
| `core/routers/fazendas.py` | Shim de compatibilidade | Nao | Sim | Medio |

## 4. Regras de Escrita

### 4.1 Escrita operacional

- Apenas `Propriedades` e seus servicos oficiais podem criar ou atualizar informacoes territoriais operacionais.
- Nenhum fluxo de escrita pode usar `unidades_produtivas` como destino para CAR, CCIR, ITR, NIRF ou SIGEF.

### 4.2 Escrita fundiaria / documental

- Apenas `Imoveis Rurais` e seus servicos oficiais podem criar ou atualizar lastro documental e patrimonial.
- `DocumentoLegal`, `ContratoArrendamento`, `AvaliacaoImovel`, `Cartorio` e `MatriculaImovelRural` sao os pontos de escrita aprovados.
- `SIGEF` permanece como risco de consolidacao futura e nao pode ser tratado como fonte operacional.

### 4.3 Escrita de vinculacao

- Apenas `PropriedadeImovel` pode representar o relacionamento canonicamente persistido entre os dominios.
- A entidade de vinculo nao pode receber dados completos de documento, safra, producao ou titularidade.

## 5. Regras de Leitura

- Espelhos legados podem ser lidos para compatibilidade e historico.
- Leitura historica nao autoriza escrita.
- Leitura historica nao autoriza a criacao de nova fonte oficial.
- Frontend e backend devem sinalizar campos espelhados como derivado ou somente leitura.

## 6. Fontes Proibidas

E proibido tratar como master data:

- `unidades_produtivas.codigo_car`
- `unidades_produtivas.nirf`
- `unidades_produtivas.ccir`
- `unidades_produtivas.sigef_codigo`
- `cadastros_areas_matriculas.car_numero`
- `cadastros_areas_matriculas.nirf`
- `cadastros_areas_matriculas.ccir`
- `cadastros_areas_matriculas.itr_numero`
- `cadastros_areas_matriculas.cartorio`
- `cadastros_areas_matriculas.comarca`

## 7. Regras Imutaveis

- Nao introduzir nova escrita fundiaria em `Propriedades`.
- Nao introduzir nova escrita operacional em `Imoveis Rurais`.
- Nao armazenar documentos integrais em `PropriedadeImovel`.
- Nao elevar espelho legado a fonte oficial.
- Nao criar novo dominio de anticorrupcao paralelo.
- Nao remover legados sem ADR separada e validacao de impacto.

## 8. Riscos Monitorados

- Confusao entre leitura compatibilidade e escrita oficial.
- Persistencia de SIGEF apenas em legado.
- Reuso indevido de tabelas de apoio antigas como master data.
- Leituras cruzadas por frontend que parecam edicao.

