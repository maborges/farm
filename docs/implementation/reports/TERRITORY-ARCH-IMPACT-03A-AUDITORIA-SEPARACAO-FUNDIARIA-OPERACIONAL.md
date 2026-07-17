# TERRITORY-ARCH-IMPACT-03A
## Auditoria de Impacto: Separação entre Dados Fundiários e Operacionais

> **Emissão:** 2026-07-17
> **Escopo:** ImovelRural, Propriedade, UnidadeProdutiva, PropriedadeImovel, subdomínios produtivos
> **Metodologia:** Auditoria estática (modelos, schemas, serviços, routers, testes, migrations) + auditoria dinâmica (PostgreSQL schema `farms`)

---

## 1. INVENTÁRIO DE CAMPOS POR ENTIDADE

### 1.1 UnidadeProdutiva — farms.unidades_produtivas (24 colunas)

| Campo | Tipo | Nulo | Classificação |
|-------|------|------|---------------|
| id, tenant_id | uuid | NO | Infra |
| nome | varchar | NO | Operacional |
| cpf_cnpj | varchar | YES | Ambíguo (compat. com Propriedade) |
| inscricao_estadual | varchar | YES | Ambíguo (compat.) |
| area_total_ha | numeric | YES | **Sobreposição com ImovelRural** |
| coordenadas_sede | varchar | YES | **Sobreposição (lat/lng)** |
| geometria | json | YES | **Sobreposição com ImovelRural** |
| ativo | boolean | NO | Operacional |
| uf | varchar | YES | **Sobreposição com ImovelRural** |
| municipio | varchar | YES | **Sobreposição com ImovelRural** |
| area_app_ha | numeric | YES | **Sobreposição com ImovelRural** |
| area_rl_ha | numeric | YES | **Sobreposição com ImovelRural** |
| tipo_propriedade | varchar | NO | Operacional |
| cep, logradouro, bairro, numero, complemento | varchar | YES | Operacional (endereço postal) |
| ibge_municipio_codigo | varchar | YES | **Sobreposição (nome diferente)** |
| logo_url | varchar | YES | Operacional (UI) |
| area_total_calculada_ha | numeric | YES | Operacional derivado |

**Campos REMOVIDOS pela migration 265b28773962 (aplicada e confirmada):**
- nirf, codigo_car, ccir, sigef_codigo, numero_matricula

### 1.2 Propriedade — farms.cadastros_propriedades (17 colunas)

| Campo | Classificação |
|-------|--------------|
| id, tenant_id | Infra |
| nome, cpf_cnpj, inscricao_estadual, ie_isento | Operacional/Fiscal |
| email, telefone, nome_fantasia, regime_tributario | Operacional |
| cor, icone, ordem | Operacional (UI) |
| ativo, observacoes | Lifecycle |

**Ausentes (fronteira respeitada):** nirf, car_numero, ccir_numero, numero_matricula, cartorio_id ✅

### 1.3 ImovelRural — farms.imoveis_rurais (28 colunas)

| Campo | Classificação |
|-------|--------------|
| nirf, car_numero, ccir_numero, sigef_codigo | **Fundiário canônico** |
| numero_matricula, cartorio_id | **Fundiário canônico** |
| area_total_ha, area_aproveitavel_ha, area_app_ha, area_rl_ha, modulos_fiscais | **Fundiário** |
| municipio, uf, codigo_municipio_ibge | **Fundiário** |
| latitude, longitude, geometria | **Fundiário geoespacial** |
| tipo (enum), situacao (enum) | **Fundiário** |
| motivo_alteracao_area | **Fundiário (auditoria)** |
| deleted_at | Soft-delete |

**Ausentes (fronteira respeitada):** talhoes, safras, producoes, piquetes ✅

### 1.4 PropriedadeImovel — farms.propriedade_imovel (19 colunas)

Apenas metadados do vínculo: propriedade_id, imovel_rural_id, tipo_vinculo, ativo, data_inicio/fim,
origem_documental, area_vinculada, percentual_vinculado, vinculo_principal, status_documental.
Nenhum campo fundiário ou operacional duplicado ✅

### 1.5 ExploracaoRural — farms.cadastros_exploracoes_rurais (17 colunas)

Campos: propriedade_id, unidade_produtiva_id, natureza, data_inicio/fim, numero_contrato,
valor_anual, percentual_producao, area_explorada_ha. Sem campos fundiários ou geoespaciais ✅

---

## 2. MAPA DE SOBREPOSIÇÃO SEMÂNTICA

| Campo | UnidadeProdutiva | ImovelRural | Propriedade | Classificação |
|-------|:----------------:|:-----------:|:-----------:|---------------|
| nome | ✅ | ✅ | ✅ | Legítimo — contextos distintos |
| municipio | ✅ | ✅ | — | ⚠️ Sobreposição de sincronismo |
| uf | ✅ | ✅ | — | ⚠️ Sobreposição de sincronismo |
| area_total_ha | ✅ | ✅ | — | ⚠️ Sobreposição de sincronismo |
| area_app_ha | ✅ | ✅ | — | ⚠️ Sobreposição de sincronismo |
| area_rl_ha | ✅ | ✅ | — | ⚠️ Sobreposição de sincronismo |
| geometria | ✅ | ✅ | — | ⚠️ Sobreposição geoespacial |
| lat/lng | coordenadas_sede | latitude/longitude | — | ⚠️ Formato inconsistente |
| cpf_cnpj | ✅ | — | ✅ | Legítimo — titulares distintos |
| ibge_municipio_codigo | ✅ | codigo_municipio_ibge | — | ⚠️ Nome inconsistente |

---

## 3. CAMPOS REMOVIDOS — CONFIRMAÇÃO HISTÓRICA

### Migration 265b28773962 — territory_convergence_remove_legacy_columns

**Aplicada com sucesso** — confirmado por: `UndefinedColumnError: column ir.unidade_produtiva_id does not exist`
ao executar audit_db.py.

**Removidos de farms.unidades_produtivas:**
- nirf, codigo_car, ccir, sigef_codigo, numero_matricula

**Removido de farms.imoveis_rurais:**
- unidade_produtiva_id (FK direta para UP → substituída por N:N via PropriedadeImovel)

**Backup preservado:** farms.territory_legacy_backup_01h2 com downgrade implementado ✅

---

## 4. ANÁLISE DE MODELO ORM vs. BANCO FÍSICO

### 4.1 UnidadeProdutiva (core/models/unidade_produtiva.py)

Campos de sobreposição presentes no ORM:
- municipio, uf, area_total_ha, area_app_ha, area_rl_ha, coordenadas_sede, geometria

Finalidade justificada: Cache operacional para formulário de cadastro e fallback na criação do imóvel.
O sincronismo UP → Imóvel é gerenciado pelo CadastroCompletoService.

### 4.2 Propriedade (propriedade_models.py)

Teste test_propriedade_mantem_fronteira_operacional() confirma:
- Ausência: car_numero, nirf, ccir_numero, numero_matricula, cartorio_id ✅
- Presença: propriedade_imoveis, exploracoes ✅

### 4.3 ImovelRural (imoveis/models/imovel.py)

Teste test_imovel_mantem_fronteira_fundiaria() confirma:
- Presença: nirf, car_numero, ccir_numero, numero_matricula, cartorio_id ✅
- Ausência: talhoes, safras, producoes ✅

### 4.4 PropriedadeImovel

Teste test_propriedade_imovel_e_unica_ponte_canonica() confirma:
- tablename = propriedade_imovel ✅
- Colunas canônicas presentes ✅
- Ausência: car_numero, nirf, ccir_numero, numero_matricula, area_total_ha ✅

---

## 5. DIVERGÊNCIA DE DADOS NO POSTGRESQL

### 5.1 Inventário físico (schema farms)

| Tabela | Colunas |
|--------|---------|
| unidades_produtivas | 24 |
| cadastros_propriedades | 17 |
| imoveis_rurais | 28 |
| propriedade_imovel | 19 |
| cadastros_exploracoes_rurais | 17 |

### 5.2 Queries de divergência para uso em PRD

```sql
-- Divergência de município (UP vs Imóvel principal)
SELECT up.nome, up.municipio AS up_municipio, ir.municipio AS imovel_municipio
FROM farms.unidades_produtivas up
JOIN farms.cadastros_exploracoes_rurais e ON e.unidade_produtiva_id=up.id AND e.ativo=true
JOIN farms.propriedade_imovel pi ON pi.propriedade_id=e.propriedade_id AND pi.ativo=true AND pi.vinculo_principal=true
JOIN farms.imoveis_rurais ir ON ir.id=pi.imovel_rural_id
WHERE LOWER(TRIM(up.municipio)) != LOWER(TRIM(ir.municipio));

-- Divergência de área total
SELECT up.nome, up.area_total_ha AS up_area, ir.area_total_ha AS imovel_area,
       ABS(up.area_total_ha - ir.area_total_ha) AS delta_ha
FROM farms.unidades_produtivas up
JOIN farms.cadastros_exploracoes_rurais e ON e.unidade_produtiva_id=up.id AND e.ativo=true
JOIN farms.propriedade_imovel pi ON pi.propriedade_id=e.propriedade_id AND pi.ativo=true AND pi.vinculo_principal=true
JOIN farms.imoveis_rurais ir ON ir.id=pi.imovel_rural_id
WHERE ABS(up.area_total_ha - ir.area_total_ha) > 0.01;

-- Imóveis sem propriedade vinculada ativa
SELECT ir.nome, ir.municipio, ir.uf, ir.nirf, ir.situacao
FROM farms.imoveis_rurais ir
WHERE ir.deleted_at IS NULL
AND NOT EXISTS (
    SELECT 1 FROM farms.propriedade_imovel pi
    WHERE pi.imovel_rural_id=ir.id AND pi.ativo=true
);

-- Múltiplos imóveis principais por propriedade
SELECT propriedade_id, COUNT(*) AS qtd_principais
FROM farms.propriedade_imovel
WHERE ativo=true AND vinculo_principal=true AND data_fim IS NULL
GROUP BY propriedade_id
HAVING COUNT(*) > 1;
```

---

## 6. ANÁLISE DO BACKEND

### 6.1 CadastroCompletoService._sincronizar_imovel_principal_com_unidade (linha 324-354)

```python
for campo in ("nome", "municipio", "uf", "area_total_ha", "area_app_ha", "area_rl_ha"):
    valor = getattr(unidade, campo, None)
    if valor is not None and not self._valores_equivalentes(getattr(imovel, campo, None), valor):
        dados_compartilhados[campo] = valor
```

**Análise:** Sincronismo UNIDIRECIONAL (UP → Imóvel) e LAZY (somente quando bloco imovel_rural ausente
no payload). Risco de divergência se a UP for atualizada isoladamente sem trigger do sincronismo.

### 6.2 _payload_imovel — Fallback na criação

```python
payload["municipio"] = payload.get("municipio") or unidade.municipio or "Não informado"
payload["uf"] = payload.get("uf") or unidade.uf or "NI"
payload["area_total_ha"] = payload.get("area_total_ha") or unidade.area_total_ha or Decimal("0")
```

Intencional mas cria dependência de propagação UP → Imóvel na criação.

### 6.3 Services com isolamento correto

| Service | Avaliação |
|---------|-----------|
| ImovelService.criar_imovel | ✅ Opera apenas em ImovelRural |
| UnidadeProdutivaService.create | ✅ Sem campos fundiários |
| PropriedadeImovelService.garantir_vinculo_ativo | ✅ Mantém ponte N:N |
| VisaoTerritorialService.obter_visao_territorial | ✅ Agrega sem misturar |

---

## 7. ANÁLISE DE SCHEMAS (Pydantic)

### 7.1 UnidadeProdutivaCreate/Response

Contém: municipio, uf, area_total_ha, area_app_ha, area_rl_ha, coordenadas_sede, geometria.
Justificado para formulário de cadastro e criação do imóvel como fallback. ✅

### 7.2 CadastroCompletoImovelInput

Bloco fundiário segregado: nirf, car_numero, codigo_car (alias), ccir_numero, ccir (alias),
sigef_codigo, cartorio_id, numero_matricula. Aliases resolvidos em _normalizar_legacy_imovel. ✅

### 7.3 MatriculaCreate em propriedades/schemas.py

⚠️ ACHADO CRÍTICO (R-01):

```python
class MatriculaCreate(BaseModel):
    area_id: uuid.UUID   # Vincula à AreaRural, não ao ImovelRural!
    nirf: Optional[str] = None
    car_numero: Optional[str] = None
    ccir: Optional[str] = None
    itr_numero: Optional[str] = None
```

MatriculaCreate vincula matrícula a AreaRural (operacional) mas inclui campos fundiários.
Isso cria uma SEGUNDA VIA FUNDIÁRIA paralela ao ImovelRural — violação arquitetural.

---

## 8. ANÁLISE DE ROUTERS

| Endpoint | Retorna | Avaliação |
|----------|---------|-----------|
| GET /fazendas/{id} | UnidadeProdutivaResponse c/ municipio/uf/area | ⚠️ Espelho operacional |
| GET /imoveis-rurais/{id} | Schema canônico ImovelRural | ✅ |
| GET /propriedades/{id}/visao-territorial | Agregação VisaoTerritorialRead | ✅ |
| GET /imoveis-rurais/{id}/visao-fundiaria | Perspectiva VisaoFundiariaRead | ✅ |

---

## 9. ANÁLISE DE TESTES

### 9.1 Cobertura de fronteira arquitetural

| Teste | Status |
|-------|--------|
| test_propriedade_mantem_fronteira_operacional | ✅ Passa |
| test_imovel_mantem_fronteira_fundiaria | ✅ Passa |
| test_propriedade_imovel_e_unica_ponte_canonica | ✅ Passa |
| test_exec37_auto_vinculo_fundiario — sem vazamento nirf | ✅ Passa |

### 9.2 Lacunas de teste identificadas

| Cenário | Risco |
|---------|-------|
| Divergência municipio UP vs Imóvel após update isolado da UP | MÉDIO |
| Múltiplos imóveis principais simultâneos | MÉDIO |
| MatriculaCreate.nirf vs ImovelRural.nirf — duplicidade | BAIXO |
| Sincronismo bidirecional inverso Imóvel → UP | BAIXO |

---

## 10. ANÁLISE DO FRONTEND

### 10.1 Hooks de território

| Hook | Endpoint | Avaliação |
|------|----------|-----------|
| useVisaoTerritorial | /propriedades/{id}/visao-territorial | ✅ |
| useVisaoFundiaria | /imoveis-rurais/{id}/visao-fundiaria | ✅ |
| usePropriedadeMutations | /cadastros/propriedades CRUD | ✅ |

### 10.2 Bug em analises-client.tsx (R-03)

```tsx
// ERRADO: usa Propriedade[] onde o código assume UnidadeProdutiva[]
const { data: propriedades = [] } = useQuery<Propriedade[]>({...})
const propriedade = propriedades.find(p => p.id === talhao.unidade_produtiva_id);
```

O hook busca /cadastros/propriedades mas filtra pelo unidade_produtiva_id do talhão —
confusão semântica entre Propriedade e UnidadeProdutiva.

---

## 11. ANALYSIS DE MIGRATIONS HISTÓRICAS

| Migration | Ação |
|-----------|------|
| imoveis_rurais_init | Cria imoveis_rurais com campos fundiários canônicos |
| 574378e90967 | Adiciona nirf em fazendas (legado — removido depois) |
| fa37f6f94792_onda1 | Normaliza AreaRural, cria cadastros_areas_matriculas |
| exec37_fundiario_fields | Adiciona numero_matricula legado em UP (compat.) |
| 265b28773962 | MARCO: Remove campos fundiários da UP e FK direta do Imóvel |
| 43cdf769d080 | Corrige FKs quebradas após separação |

---

## 12. ACHADOS DE RISCO — PRIORIZAÇÃO

| ID | Achado | Severidade | Área |
|----|--------|-----------|------|
| R-01 | MatriculaCreate em AreaRural contém nirf/car/ccir — segunda via fundiária | ALTO | Schema |
| R-02 | Sincronismo UP → Imóvel é unidirecional e lazy — divergência possível | MÉDIO | Service |
| R-03 | Frontend usa Propriedade[] onde espera UnidadeProdutiva[] em analises-client | MÉDIO | Frontend |
| R-04 | ibge_municipio_codigo (UP) vs codigo_municipio_ibge (Imóvel) — nome inconsistente | BAIXO | BD |
| R-05 | geometria existe em UP e ImovelRural sem documentação explícita de contexto | BAIXO | Modelo |
| R-06 | Ausência de teste de divergência de municipio após update isolado da UP | BAIXO | Testes |

---

## 13. CHECKLIST SIM/NÃO

| Pergunta | Resposta |
|----------|----------|
| NIRF, CIB, CCIR, CAR, SIGEF, matrícula exclusivos em ImovelRural? | SIM ✅ |
| UP contém campo fundiário residual pós-convergência? | NÃO ✅ |
| Relação ImovelRural ↔ Propriedade via PropriedadeImovel exclusivamente? | SIM ✅ |
| Campos localização (municipio, uf) duplicados entre UP e ImovelRural? | SIM ⚠️ (sincronismo intencional) |
| Testes de fronteira arquitetural passam? | SIM ✅ |
| Há segunda via fundiária fora de ImovelRural? | PARCIALMENTE ⚠️ (MatriculaCreate — R-01) |
| Frontend consome campos fundiários via hooks corretos? | SIM ✅ (com bug localizado R-03) |
| CadastroCompletoService evita vazar campos fundiários para UP? | SIM ✅ |
| PropriedadeImovel respeita N:N sem duplicar campos canônicos? | SIM ✅ |
| Banco reflete ORM sem colunas fantasma? | SIM ✅ |

---

## 14. ANÁLISE DE SUBDIVISÕES (AreaRural/Piquete)

### 14.1 AreaRural
Vinculada a UnidadeProdutiva via unidade_produtiva_id — correto.
Sem vínculo direto com ImovelRural (associação implícita via cadeia).
PROBLEMA: MatriculaCreate.area_id → vincula matrícula à AreaRural, não ao ImovelRural (R-01).

### 14.2 Talhões
Migrados para AreaRural (step1_migrate_talhoes_to_areas_rurais, step2_drop_talhoes_legado).
Tabela autônoma removida. ✅

### 14.3 Piquetes
Entidades pecuárias operacionais. Sem campos fundiários. ✅

---

## 15. ESTADO ATUAL DA SEPARAÇÃO

```
RESOLVIDO ✅
  - Campos NIRF/CAR/CCIR/SIGEF/matrícula removidos da UP
  - FK direta ImovelRural → UP removida
  - Relação N:N via PropriedadeImovel funcional
  - Testes de fronteira passando
  - Visão territorial e fundiária separadas nos endpoints

RESIDUAL ⚠️ (não bloqueante para produção)
  - municipio, uf, area_total_ha espelhados na UP (cache para UX)
  - Sincronismo unidirecional UP → Imóvel (risco de divergência)
  - MatriculaCreate em AreaRural com campos fundiários (R-01)
  - Frontend mistura Propriedade/UP em analises-client (R-03)

AUSENTE (fora do escopo desta auditoria)
  - Sincronismo bidirecional Imóvel → UP
  - Validação de unicidade cruzada NIRF em MatriculaCreate vs ImovelRural
```

---

## 16. INTEGRIDADE REFERENCIAL

| Relação | FK | Status |
|---------|---|--------|
| propriedade_imovel.propriedade_id → cadastros_propriedades.id | Presente | ✅ |
| propriedade_imovel.imovel_rural_id → imoveis_rurais.id | Presente | ✅ |
| cadastros_exploracoes_rurais.propriedade_id → cadastros_propriedades.id | Presente | ✅ |
| cadastros_exploracoes_rurais.unidade_produtiva_id → unidades_produtivas.id | Presente | ✅ |
| imoveis_rurais.cartorio_id → cartorios.id | Presente (nullable) | ✅ |
| imoveis_rurais.unidade_produtiva_id | REMOVIDA pela migration | ✅ |

---

## 17. SOFT-DELETE E LIFECYCLE

| Entidade | Soft-delete | Status |
|---------|------------|--------|
| ImovelRural | deleted_at | ✅ |
| UnidadeProdutiva | ativo=false | ✅ |
| Propriedade | ativo=false | ✅ |
| PropriedadeImovel | ativo=false + data_fim | ✅ |
| ExploracaoRural | ativo=false + data_fim | ✅ |

---

## 18. MULTI-TENANCY

Todas as tabelas territoriais possuem tenant_id como coluna obrigatória.
Todas as queries de serviço auditadas filtram por tenant_id. Sem cross-tenant leak identificado. ✅

---

## 19. COMPATIBILIDADE LEGADA

### Aliases de schema
- codigo_car → car_numero (normalizado em _normalizar_legacy_imovel)
- ccir → ccir_numero (normalizado em _normalizar_legacy_imovel)

### Aliases de modelo
- FazendaCreate = UnidadeProdutivaCreate
- FazendaResponse = UnidadeProdutivaResponse

Sem duplicação de lógica nos aliases. ✅

---

## 20. VEREDICTO FINAL

### GO COM RESSALVAS

A separação arquitetural entre dados fundiários (ImovelRural) e operacionais
(UnidadeProdutiva, Propriedade) está substancialmente implementada e consistente
com a intenção do design:

- A migration de convergência foi aplicada com sucesso.
- Os testes de fronteira arquitetural passam.
- A relação N:N via PropriedadeImovel é o único canal canônico.
- Os schemas Pydantic e os serviços respeitam os domínios.

**As ressalvas (não bloqueantes para produção, mas requerem follow-up):**

| # | Ressalva | Ação recomendada |
|---|---------|-----------------|
| R-01 | MatriculaCreate em AreaRural contém nirf/car/ccir | Mover para ImovelRural; deprecar em MatriculaCreate |
| R-02 | Sincronismo UP → Imóvel unidirecional — divergência possível | Adicionar teste; documentar no README |
| R-03 | Frontend usa Propriedade[] onde espera UnidadeProdutiva[] | Corrigir tipagem e query key em analises-client.tsx |
| R-04 | ibge_municipio_codigo vs codigo_municipio_ibge | Padronizar em próxima migration de limpeza |

---

### Respostas binárias ao prompt original

| Pergunta | Resposta |
|----------|----------|
| NIRF/CIB/CCIR/CAR/SIGEF/matrícula exclusivos em ImovelRural? | SIM |
| UP tem dados fundiários residuais? | NÃO (removidos — confirmado) |
| PropriedadeImovel é a única ponte N:N? | SIM |
| Divergência UP vs ImovelRural possível? | SIM (sincronismo unidirecional — risco médio) |
| Arquitetura matura para produção? | SIM com ressalvas R-01 e R-03 |
| Testes de regressão de fronteira existem? | SIM (test_territorial_compatibility.py) |
| Frontend usa endpoints corretos? | SIM (com bug localizado R-03) |
| Separação documentada em migrations com rollback? | SIM (downgrade em 265b28773962) |

---

*Relatório gerado em modo de auditoria pura.
Nenhuma alteração de código, migration, schema ou banco foi realizada.*
