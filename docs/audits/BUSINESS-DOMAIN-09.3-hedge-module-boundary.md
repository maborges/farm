# Auditoria — BUSINESS-DOMAIN-09.3: Hedge Module Boundary

> Data: 2026-06-14  
> Status: **CONCLUÍDA**  
> Base aprovada: BUSINESS-DOMAIN-09.2  
> Regra: Somente inventário e análise. Nenhuma implementação.

---

## AJUSTE 1 — HedgePosition precisa ser tabela ou projeção calculada?

### Evidências coletadas

Os dados que alimentam o cálculo de exposição já existem e estão em tabelas ativas:

| Dado | Tabela | Status |
|---|---|---|
| Produção estimada | `cultivos.produtividade_meta_sc_ha` × `cultivo_areas.area_ha` | ✅ EXISTE E ATENDE |
| Vendas confirmadas | `financeiro_comercializacoes` (`quantidade`, `status`, `commodity_id`) | ✅ EXISTE E ATENDE |
| Hedge registrado | `hedge_registros` (`quantidade`, `tipo`, `contrato_id`) | ⚠️ EXISTE PARCIALMENTE — tabela revertida |
| Instrumento | `contratos_futuros` (`quantidade`, `tipo_posicao`, `status`) | ⚠️ EXISTE PARCIALMENTE — tabela revertida |
| Estoque físico | `estoque_saldos` (`quantidade_atual`) | ✅ EXISTE E ATENDE |

### Análise: Opção A vs Opção B

**Opção A — Tabela `hedge_positions` persistida**

| Prós | Contras |
|---|---|
| Histórico de posição ao longo do tempo | Nova migration obrigatória |
| Suporte nativo a MtM (V2) sem re-consultar tudo | Risco de dessincronização com fontes (estoque, comercialização) |
| Permite notificações e alertas (V2) | Overhead de manutenção no MVP |

**Opção B — Projeção calculada (view lógica / query)**

| Prós | Contras |
|---|---|
| Sem migration nova no MVP | Sem histórico de posição |
| Sempre consistente com os dados-fonte | Recálculo a cada request (aceitável em volume MVP) |
| Zero risco de divergência entre estado e dados | Inviável para MtM e alertas automáticos (V2) |

### ✅ Recomendação

**MVP: Opção B — Projeção calculada.**

- O volume de dados em MVP (dezenas de operações, não milhares) torna o recálculo por request aceitável.
- Evita criar uma nova tabela que pode divergir das fontes.
- Preparar o schema de resposta já compatível com o que será persistido em V2, facilitando a migração.
- **V2:** evoluir para Opção A (tabela materializada com atualização incremental por evento).

> **Conclusão:** `HedgePosition` no MVP é um objeto de valor calculado (resultado de query), não uma entidade persistida.

---

## AJUSTE 2 — HedgeExposure: Entidade ou Serviço de Cálculo?

### Análise

A exposição de hedge é definida pela fórmula:

```
exposicao_bruta      = Σ (cultivo.produtividade_meta_sc_ha × cultivo_area.area_ha)
ja_vendido           = Σ comercializacao.quantidade WHERE status IN [CONFIRMADO, ENTREGUE, FINALIZADO]
ja_hedgeado          = Σ contrato_futuro.quantidade WHERE status = 'aberto'
exposicao_liquida    = exposicao_bruta - ja_vendido - ja_hedgeado
percentual_cobertura = (ja_hedgeado / exposicao_bruta) × 100
```

Todos os dados-fonte já existem. Nenhuma persistência adicional é necessária para o cálculo.

### ✅ Recomendação por versão

| Versão | Papel de HedgeExposure |
|---|---|
| **MVP** | Serviço de cálculo (`HedgeExposureService`) — método que executa a query de consolidação e retorna o DTO de exposição. **Não é entidade.** |
| **V2** | Projeção materializada — snapshot persistido com `calculated_at`, para histórico e feeds de MtM. |

> **Conclusão:** No MVP, `HedgeExposure` é exclusivamente um serviço de cálculo, não uma entidade.

---

## AJUSTE 3 — ContratoFuturo é necessário ou HedgeRegistro basta?

### Inventário completo de ContratoFuturo

| Artefato | Arquivo | Evidência | Observação |
|---|---|---|---|
| **Model** | `services/api/enterprise/models/sprints_27_33.py` L399 | `class ContratoFuturo(Base)` | Existe no código |
| **Service** | `services/api/enterprise/services/sprints_27_33_service.py` L229 | `HedgingService.criar_contrato()` | Existe |
| **Endpoint** | `services/api/enterprise/routers/sprints_27_33_router.py` L208 | `POST /sprints27-33/hedging/contratos` | Existe, mas protegido por `EXT_IA` |
| **Migration (upgrade)** | `migrations/versions/fase3_sprints27_33_final.py` L265 | `op.create_table('contratos_futuros', ...)` | Existe no upgrade |
| **Migration (downgrade)** | `migrations/versions/fase3_sprints27_33_final.py` L402 | `op.drop_table('contratos_futuros')` | Tabela **REVERTIDA** — não está ativa |
| **FK de HedgeRegistro** | `hedge_registros.contrato_id → contratos_futuros.id` | Migration L300 | HedgeRegistro depende de ContratoFuturo |
| **Telas frontend** | — | Nenhum componente encontrado | **NÃO EXISTE** |
| **Testes** | — | Nenhum teste encontrado | **NÃO EXISTE** |
| **Consumidores externos** | — | Nenhum outro módulo importa ContratoFuturo | **Uso exclusivo dentro de enterprise/** |

### Análise: ContratoFuturo é necessário?

**Sem ContratoFuturo, HedgeRegistro perde o vínculo com:**
- `commodity` específico da operação (string livre em `ContratoFuturo.commodity`)
- `mercado` (B3, CBOT)
- `mes_vencimento` do contrato
- `tipo_posicao` (compra/venda)
- `status` do contrato (aberto, encerrado, liquidado)

**Se HedgeRegistro fosse o único:**
- Precisaria absorver todos esses campos diretamente.
- Perderia a capacidade de agrupar múltiplos registros de hedge no mesmo contrato futuro (ex.: vários lotes de soja no contrato SJC N27).

### ✅ Decisão

**`ContratoFuturo` deve permanecer.** É a entidade que representa o instrumento de hedge (o contrato com o mercado). `HedgeRegistro` representa cada operação realizada dentro desse contrato.

Sem `ContratoFuturo`, `HedgeRegistro` vira uma entidade sobrecarregada que mistura instrumento + operação, violando o princípio de separação de responsabilidades.

**Tabela de responsabilidades:**

| Entidade | Responsabilidade |
|---|---|
| `ContratoFuturo` | O instrumento — qual contrato, qual mercado, qual commodity, qual vencimento |
| `HedgeRegistro` | A operação — quanto foi hedgeado, a que preço, em que data, com qual resultado |

---

## AJUSTE 4 — Auditoria do Acoplamento com EXT_IA

### Por que o hedge depende de EXT_IA?

**Evidência direta:**

```python
# services/api/enterprise/routers/sprints_27_33_router.py — L16
router = APIRouter(
    prefix="/sprints27-33",
    tags=["Sprints 27-33"],
    dependencies=[Depends(require_module("EXT_IA"))]  # ← acoplamento incorreto
)
```

O router `sprints_27_33_router.py` agrupa **todos** os endpoints dos Sprints 27 a 33 (MRV, ESG, Piscicultura, Confinamento, Genética, **Hedging**, IoT, ILPF) em um único router com `require_module("EXT_IA")`.

Isso significa que qualquer cliente que quiser usar hedge precisa ter contratado `EXT_IA` (IA Agrônoma — R$ 799,00/mês), mesmo que não use nenhuma funcionalidade de IA.

### Módulo correto para Hedge

```python
# core/constants.py — L88
FINANCEIRO_HEDGING = "F4_HEDGING"  # Hedging, Futuros, Barter
```

O módulo `F4_HEDGING` já está **definido e catalogado** em `core/constants.py` com:
- Nome: `"Hedging e Futuros"`
- Descrição: `"Proteção B3, barter, contratos futuros"`
- Dependências: `[CORE, F1_TESOURARIA]`
- Preço base: `R$ 599,00/mês`

### Endpoints afetados pelo acoplamento incorreto

| Endpoint | Localizado em | Módulo atual (errado) | Módulo correto |
|---|---|---|---|
| `POST /sprints27-33/hedging/contratos` | `sprints_27_33_router.py` L208 | `EXT_IA` | `F4_HEDGING` |
| `POST /sprints27-33/hedging/registros` | `sprints_27_33_router.py` L223 | `EXT_IA` | `F4_HEDGING` |

### Causa raiz do acoplamento

O router foi criado como um agrupamento temporário de funcionalidades dos Sprints 27–33, todos colocados sob `EXT_IA` por conveniência de desenvolvimento. Isso cria um acoplamento comercial incorreto: hedge passa a custar R$ 799/mês em vez de R$ 599/mês.

### ✅ Solução arquitetural (a implementar, não agora)

Os endpoints de hedge devem ser extraídos do `sprints_27_33_router.py` para um router próprio protegido por `require_module("F4_HEDGING")`. Os demais endpoints (MRV, ESG, IoT etc.) permanecem em seus respectivos módulos.

---

## AJUSTE 5 — MVP Mínimo Implementável

### Entidades obrigatórias

| Entidade | Situação | Ação necessária |
|---|---|---|
| `ContratoFuturo` | Existe no código; migration revertida | Reativar migration |
| `HedgeRegistro` | Existe no código; migration revertida | Reativar migration; adicionar campos de contexto |
| `HedgePosition` | **NÃO existe** | Criar como DTO/objeto de valor calculado — **sem migration** |
| `HedgeExposureService` | **NÃO existe** | Criar como service de query — **sem migration** |

### Migrations obrigatórias

| Migration | Ação | Justificativa |
|---|---|---|
| `contratos_futuros` | Reativar (re-criar) | Base do instrumento de hedge |
| `hedge_registros` | Reativar (re-criar) com coluna `safra_id` | Contexto agrícola obrigatório para cálculo de exposição |
| `hedge_positions` | **NÃO criar no MVP** | Posição é calculada, não persistida |

### Endpoints obrigatórios (MVP)

| Método | Caminho | Módulo | Descrição |
|---|---|---|---|
| `POST` | `/hedge/contratos` | `F4_HEDGING` | Cria/cadastra instrumento futuro |
| `POST` | `/hedge/registros` | `F4_HEDGING` | Registra operação de hedge vinculada ao contrato |
| `GET` | `/hedge/posicao` | `F4_HEDGING` | Retorna posição calculada por `safra_id` + `commodity` |
| `GET` | `/hedge/exposicao` | `F4_HEDGING` | Retorna exposição líquida calculada |

### Telas obrigatórias (MVP)

| Tela | Tipo | Dados exibidos |
|---|---|---|
| Lista de Contratos Futuros | Leitura + criação | Instrumento, mercado, commodity, quantidade, vencimento, status |
| Registros de Hedge | Leitura + criação | Por contrato, tipo, quantidade, preço, data |
| Painel de Exposição | Somente leitura | Produção estimada, vendido, hedgeado, exposição líquida, % cobertura |

### O que NÃO deve ser implementado no MVP (backlog V2+)

| Item | Versão |
|---|---|
| Tabela `hedge_positions` persistida | V2 |
| `HedgeMarkToMarket` | V2 |
| `HedgeMarginCall` | V2 |
| Barter como hedge natural | V2 |
| CPR como colateral | V2 |
| `HedgePolicy` / `RiskPolicy` | V3 |
| `HedgeRiskMetric` (VaR, CVaR) | V3 |
| Integração com bolsas externas | V4 |
| Derivativos complexos | V4 |

---

## Conclusão Final

| Questão | Resposta definitiva |
|---|---|
| **HedgePosition precisa ser tabela no MVP?** | ❌ Não — projeção calculada (Opção B) |
| **HedgeExposure é entidade ou serviço?** | Serviço de cálculo no MVP; entidade materializada em V2 |
| **ContratoFuturo deve permanecer?** | ✅ Sim — representa o instrumento; sem ele, HedgeRegistro fica sobrecarregado |
| **Por que hedge depende de EXT_IA?** | Agrupamento temporário de sprints em um único router incorreto |
| **Qual módulo correto para hedge?** | `F4_HEDGING` — já definido em `core/constants.py` |
| **Domínio pronto para implementação?** | ✅ Sim, com as 4 ações preparatórias abaixo |

### 4 Ações Preparatórias Antes da Implementação

| # | Ação | Tipo |
|---|---|---|
| 1 | Reativar migrations de `contratos_futuros` e `hedge_registros` | Migration |
| 2 | Adicionar coluna `safra_id` (UUID, FK para `safras.id`) em `contratos_futuros` | Migration (alter table) |
| 3 | Criar router dedicado `/hedge` com `require_module("F4_HEDGING")` | Código |
| 4 | Criar `HedgeExposureService` com query de consolidação | Código |
