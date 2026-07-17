# TERRITORY-ARCH-IMPACT-03B1 — Auditoria de Matrícula ligada a Área Rural

## 1. Resumo executivo

O resíduo R-01 foi auditado no código e no PostgreSQL real configurado pela API. A estrutura `farms.cadastros_areas_matriculas` era uma segunda via de escrita fundiária ligada a `AreaRural`, com CRUD backend ativo, mas sem consumidor Web, Campo, worker, integração ou relatório de runtime identificado.

No banco auditado a tabela possuía zero registros e nenhuma dependência externa. A classificação definitiva é:

```text
LEGADO_SEM_USO
```

Não há backfill, conflito ou dado exclusivo a preservar no ambiente auditado.

## 2. Ambiente

```text
SGBD: PostgreSQL
database: farms
schema/search_path: farms
Alembic antes da correção: 20260716_config_up_security_freeze
```

A URL do banco não foi registrada no relatório. A auditoria utilizou a configuração real carregada por `core.database` e somente consultas `SELECT`.

## 3. Inventário do código

| Camada | Estrutura | Situação antes da correção |
|---|---|---|
| Schema | `MatriculaCreate`, `MatriculaUpdate`, `MatriculaResponse` | Ativo |
| ORM | `MatriculaImovel` | Ativo |
| Tabela | `farms.cadastros_areas_matriculas` | Existente |
| Relação | `AreaRural.matriculas` | Ativa, `delete-orphan` |
| Service | `MatriculaService` | CRUD com commits internos |
| Router | `/{area_id}/matriculas` | GET/POST/PATCH/DELETE ativos |
| Web | chamadas às rotas | Nenhuma encontrada |
| Campo | chamadas às rotas | Nenhuma encontrada |
| Testes | comportamento CRUD | Ausente |
| Documentação | referências históricas/piloto | Presentes, algumas desatualizadas |

## 4. Papel e persistência

1. A tabela receptora era `farms.cadastros_areas_matriculas`.
2. O registro representava matrícula e documentação fundiária duplicada, não vínculo operacional.
3. `area_id` referenciava `farms.cadastros_areas_rurais.id`.
4. Não existia FK ou associação com `ImovelRural`.
5. Matrícula, cartório, comarca, CAR, NIRF, INCRA, CCIR, SNCR e ITR eram persistidos.
6. Existiam endpoints CRUD ativos no backend.
7. Não foram encontrados consumidores Web ou Campo.
8. O PostgreSQL possuía zero registros.
9. Não havia valores exclusivos fora de `ImovelRural` porque não havia linhas.
10. Não havia divergências de dados possíveis no ambiente auditado.
11. Não foi encontrado código de cópia entre a tabela e `ImovelRural`.
12. Documentos antigos citavam uso no piloto, mas não havia consumidor nem dado físico que comprovasse dependência atual.

## 5. Estrutura física

Colunas encontradas:

```text
id uuid NOT NULL PK
area_id uuid NOT NULL FK -> cadastros_areas_rurais.id ON DELETE CASCADE
numero_matricula varchar NOT NULL
cartorio varchar NULL
comarca varchar NULL
area_matricula_ha double precision NULL
car_numero varchar NULL
nirf varchar NULL
incra varchar NULL
ccir varchar NULL
ativo boolean NOT NULL
livro varchar NULL
folha varchar NULL
data_registro timestamptz NULL
sncr varchar NULL
itr_numero varchar NULL
```

Índices: PK em `id` e índice não único em `area_id`. Não havia `tenant_id` próprio nem RLS própria; o isolamento dependia da consulta prévia da `AreaRural` pai.

## 6. Dados físicos

| Métrica | Resultado |
|---|---:|
| Total | 0 |
| Ativos | 0 |
| Com matrícula | 0 |
| Com CAR | 0 |
| Com NIRF | 0 |
| Com CCIR | 0 |
| Com ITR | 0 |
| Tenants | 0 |
| Órfãos de AreaRural | 0 |

Não há soft delete; existe apenas o booleano `ativo`.

## 7. Dependências

Dependências de saída:

```text
area_id -> cadastros_areas_rurais.id ON DELETE CASCADE
```

Dependências de entrada encontradas no catálogo:

```text
índice ix_cadastros_areas_matriculas_area_id
TOAST interno do PostgreSQL
```

Não foram encontradas views, materialized views, triggers, funções, procedures ou FKs externas dependentes.

## 8. Consultas utilizadas

```sql
SELECT COUNT(*) AS total,
       COUNT(*) FILTER (WHERE ativo IS TRUE) AS ativos,
       COUNT(*) FILTER (WHERE car_numero IS NOT NULL AND btrim(car_numero) <> '') AS com_car,
       COUNT(*) FILTER (WHERE nirf IS NOT NULL AND btrim(nirf) <> '') AS com_nirf,
       COUNT(*) FILTER (WHERE ccir IS NOT NULL AND btrim(ccir) <> '') AS com_ccir,
       COUNT(*) FILTER (WHERE itr_numero IS NOT NULL AND btrim(itr_numero) <> '') AS com_itr
FROM farms.cadastros_areas_matriculas;

SELECT COUNT(*) FILTER (WHERE ar.id IS NULL) AS orfaos_area
FROM farms.cadastros_areas_matriculas m
LEFT JOIN farms.cadastros_areas_rurais ar ON ar.id = m.area_id;
```

Consultas de divergência foram preparadas pela cadeia `AreaRural -> UnidadeProdutiva -> ExploracaoRural -> PropriedadeImovel -> ImovelRural`; como o conjunto legado é vazio, todos os resultados são zero.

## 9. Classificação e decisão

```text
Classificação: LEGADO_SEM_USO
Backfill: NÃO NECESSÁRIO
Conflitos: NENHUM
Remoção controlada: AUTORIZADA
```

A migration de remoção deve abortar se encontrar qualquer linha em outro ambiente. Isso impede que a evidência deste banco seja aplicada cegamente a uma base divergente.

## 10. Veredicto

```text
GO
```

Há evidência suficiente para remover a segunda via fundiária sem perda de dados no ambiente auditado.
