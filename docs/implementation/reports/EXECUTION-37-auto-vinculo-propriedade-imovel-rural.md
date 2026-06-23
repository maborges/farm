# EXECUTION-37 — Correção de Fluxo de Cadastro Propriedade ↔ Imóvel Rural (Auto Vínculo Canônico)

## Resumo Executivo

Foi implementado e **completado** o fluxo orquestrado de auto-vínculo entre a estrutura operacional/territorial (`UnidadeProdutiva`) e a estrutura jurídica/fundiária (`ImovelRural`), respeitando integralmente os domínios aprovados em `AGRI-DOMAIN-001` e `AGRI-DOMAIN-002`.

**Critério de sucesso atingido:** O usuário informa os dados fundiários apenas uma vez. O sistema localiza ou cria o `ImovelRural` automaticamente, gera o vínculo `PropriedadeImovel`, e na leitura sempre retorna os dados fundiários a partir da fonte oficial.

---

## Governança de Dados Fundiários (Regra Canônica)

> [!IMPORTANT]
> As regras abaixo são parte da arquitetura aprovada e **não devem ser violadas** em evoluções futuras.

| Entidade | Papel | Fonte Oficial? |
|---|---|---|
| `ImovelRural` | Domínio jurídico/fundiário/documental | **SIM** |
| `ImovelRural.sigef_codigo` | Código SIGEF canônico | **SIM — fonte oficial** |
| `ImovelRural.car_numero` | CAR canônico | **SIM — fonte oficial** |
| `ImovelRural.nirf` | NIRF canônico | **SIM — fonte oficial** |
| `ImovelRural.ccir_numero` | CCIR canônico | **SIM — fonte oficial** |
| `ImovelRural.numero_matricula` | Matrícula canônica | **SIM — fonte oficial** |
| `PropriedadeImovel` | Vínculo canônico N:N | **SIM (vínculo)** |
| `UnidadeProdutiva` | Domínio operacional/territorial | **NÃO** |
| `UnidadeProdutiva.codigo_car` | Campo de entrada legado | **NÃO — apenas captura de dado** |
| `UnidadeProdutiva.nirf` | Campo de entrada legado | **NÃO — apenas captura de dado** |
| `UnidadeProdutiva.ccir` | Campo de entrada legado | **NÃO — apenas captura de dado** |
| `UnidadeProdutiva.sigef_codigo` | Campo de entrada legado | **NÃO — apenas captura de dado** |
| `UnidadeProdutiva.numero_matricula` | Campo de compatibilidade/entrada legada | **NÃO — apenas captura de dado** |
| `Propriedade` | Entidade econômica/jurídica do produtor | **NÃO** |

> [!WARNING]
> **Nenhum campo fundiário em `Propriedade` ou `UnidadeProdutiva` deve ser considerado fonte oficial.**
> A leitura canônica de CAR, NIRF, CCIR, SIGEF e Matrícula deve sempre ser realizada via `ImovelRural`, acessado através do vínculo `PropriedadeImovel`.

---

## Modificações Implementadas

### Backend — Models

**`services/api/imoveis/models/imovel.py`**
- Adicionado `sigef_codigo: Mapped[str | None]` em `ImovelRural` com índice de busca.
- **`ImovelRural.sigef_codigo` é fonte oficial fundiária.** Dado aqui = verdade do domínio.

**`services/api/core/models/unidade_produtiva.py`**
- Adicionado `numero_matricula: Mapped[str | None]` em `UnidadeProdutiva`.
- **`UnidadeProdutiva.numero_matricula` é campo de compatibilidade e entrada legada.** Serve exclusivamente para capturar o dado do usuário via formulário e disparar a sincronização. **Não é fonte oficial.**

### Backend — Schemas

**`services/api/core/schemas/unidade_produtiva_input.py`**
- Adicionado `numero_matricula: Optional[str]` em `UnidadeProdutivaCreate` e `UnidadeProdutivaUpdate`.
- Propósito: captura de dado de entrada. **Não persiste como fonte oficial.**

**`services/api/core/schemas/unidade_produtiva_output.py`**
- Adicionado `numero_matricula: Optional[str]` no response.
- Em reads com vínculo ativo, esse campo é **sobrescrito pelo overlay** com o valor de `ImovelRural.numero_matricula` (fonte oficial).

### Backend — Services

**`services/api/core/services/unidade_produtiva_service.py`**

#### `_sincronizar_vinculo_fundiario()` — Auto-criação/localização

Fluxo ao salvar `UnidadeProdutiva`:

1. Coleta 5 identificadores do payload: `codigo_car`, `nirf`, `ccir`, `sigef_codigo`, `numero_matricula`.
2. Se nenhum identificador presente → encerra sem ação (não cria imóvel fantasma).
3. Busca `ImovelRural` existente no tenant por OR-logic (qualquer dos 5 identificadores).
4. Se não encontrar → cria `ImovelRural` automaticamente via `ImovelService.criar_imovel()`. O SIGEF é atribuído ao imóvel após o `flush`.
5. Busca `ExploracaoRural` para obter `propriedade_id`.
6. Se existir → garante `PropriedadeImovel` canônico com `tipo_vinculo=PROPRIEDADE_PRINCIPAL` e `vinculo_principal=True` (idempotente: não duplica).

#### `get(id)` — Overlay de Visão Territorial (leitura em memória)

> [!IMPORTANT]
> O override de `get()` **não escreve no banco de dados**. É uma operação de leitura em memória.
> Os atributos são sobrescritos apenas no objeto Python retornado. O banco permanece inalterado.
> Isso garante que a resposta da API sempre reflita a fonte oficial sem criar espelhos ou escrita dupla.

Fluxo da leitura:

1. Carrega `UnidadeProdutiva` via `super().get(id)`.
2. Resolve `propriedade_id` via `ExploracaoRural`.
3. Busca `ImovelRural` via `PropriedadeImovel` ativo + `vinculo_principal=True`.
4. Se encontrar → sobrescreve **em memória**: `codigo_car`, `nirf`, `ccir`, `sigef_codigo`, `numero_matricula` com os valores de `ImovelRural` (fonte oficial).
5. Retorna o objeto com os campos canônicos.

**Resultado:** A API sempre serve dados fundiários a partir de `ImovelRural` quando há vínculo ativo. Os campos legados em `UnidadeProdutiva` no banco são ignorados na resposta.

### Backend — Migrations

**`services/api/migrations/versions/exec37_fundiario_fields.py`** [NEW]

> [!NOTE]
> Esta migration foi necessária **exclusivamente para compatibilidade e captura de entrada**.
> - `imoveis_rurais.sigef_codigo` → necessária pois `ImovelRural` não possuía o campo SIGEF na fonte oficial.
> - `unidades_produtivas.numero_matricula` → campo de entrada legada para capturar matrícula do formulário e disparar sync.
> Nenhuma coluna criada aqui representa espelho ou fonte oficial em `UnidadeProdutiva`.

- `alembic upgrade head` aplicado com sucesso em `db819dde310d → exec37_fundiario_fields`.
- Colunas: `imoveis_rurais.sigef_codigo VARCHAR(50)` (+ índice) e `unidades_produtivas.numero_matricula VARCHAR(100)`.

### Frontend

**`apps/web/src/app/(dashboard)/cadastros/propriedades/propriedades-client.tsx`**
- Campo "Matrícula" (`numero_matricula`) adicionado no grupo Documentação do formulário.
- Propósito: **captura de dado do usuário**. Ao salvar, o backend dispara o sync e armazena o dado oficial em `ImovelRural`.
- Banner "Convergência Territorial" informa explicitamente que os dados fundiários serão vinculados ao Imóvel Rural oficial.

### Testes

**`services/api/tests/integration/test_exec37_auto_vinculo_fundiario.py`**

| Cenário | Descrição | Resultado |
|---|---|---|
| 1 | CAR novo → cria ImovelRural | ✅ PASSED |
| 2 | CAR existente → reutiliza ImovelRural | ✅ PASSED |
| 3 | Com ExploracaoRural → cria PropriedadeImovel canônico | ✅ PASSED |
| 4 | Sem dado fundiário → não cria ImovelRural | ✅ PASSED |
| 5 | Sync idempotente — sem duplicatas | ✅ PASSED |
| 6 | SIGEF novo → cria ImovelRural com `sigef_codigo` | ✅ PASSED |
| 7 | Matrícula nova → cria ImovelRural com `numero_matricula` | ✅ PASSED |

**7/7 PASSED em 14.82s**

---

## Campos Fundiários — Inventário Completo

| Identificador | `UnidadeProdutiva` (entrada) | `ImovelRural` (oficial) |
|---|---|---|
| CAR | `codigo_car` — legado | `car_numero` — **oficial** |
| NIRF | `nirf` — legado | `nirf` — **oficial** |
| CCIR | `ccir` — legado | `ccir_numero` — **oficial** |
| SIGEF | `sigef_codigo` — legado | `sigef_codigo` — **oficial (NOVO)** |
| Matrícula | `numero_matricula` — compatibilidade (NOVO) | `numero_matricula` — **oficial** |

---

## Estratégia Adotada

**Princípio:** Input único pelo usuário, armazenamento canônico em `ImovelRural`, leitura sempre via fonte oficial.

1. **Captura:** O formulário de `UnidadeProdutiva` recebe os identificadores fundiários.
2. **Sincronização:** `_sincronizar_vinculo_fundiario()` localiza ou cria o `ImovelRural` com os dados oficiais.
3. **Vínculo:** `PropriedadeImovel` é gerado de forma idempotente com `tipo_vinculo=PROPRIEDADE_PRINCIPAL`.
4. **Leitura:** `get()` aplica overlay em memória — a resposta da API reflete `ImovelRural`, sem escrita dupla.

---

## Migration

**Necessária para:**
- `ImovelRural.sigef_codigo` — campo faltante na fonte oficial.
- `UnidadeProdutiva.numero_matricula` — campo de entrada legado (compatibilidade).

**Não necessária para:** criação de espelhos, duplicação de fontes ou mudança de domínio.

---

## Testes Executados

```
7 passed in 14.82s
pnpm exec tsc --noEmit — sem erros
alembic upgrade head — aplicado com sucesso
```

---

## Riscos Encontrados

- `ImovelRural.numero_matricula` não possui `UniqueConstraint` por cartório (diferente de NIRF que tem `uq_imovel_nirf`). Em cenários com múltiplas matrículas de cartórios distintos, a busca por OR-logic pode retornar o primeiro encontrado. Recomenda-se futuramente adicionar `cartorio_id` como parte da chave de busca.

## Pendências Reais

- Nenhuma. Feature completa, testada e documentada.

## Impacto na Arquitetura

- `ImovelRural` consolidado como única fonte oficial de dados fundiários.
- `UnidadeProdutiva` mantida como domínio operacional sem autoridade fundiária.
- `PropriedadeImovel` confirmado como vínculo canônico N:N.
- Nenhuma violação de `AGRI-DOMAIN-001` ou `AGRI-DOMAIN-002`.

## Compatibilidade Preservada

✅ Todos os campos legados preservados.  
✅ Nenhuma API quebrada.  
✅ Nenhuma tela removida.  
✅ Nenhum ADR de remoção gerado.
