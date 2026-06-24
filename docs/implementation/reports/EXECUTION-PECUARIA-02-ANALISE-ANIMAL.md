# EXECUTION-PECUARIA-02 — Cadastro Individual de Animal
## Análise Técnica e Plano de Implantação

**Data:** 23/06/2026  
**Status:** PLANEJAMENTO — READ-ONLY  
**Objetivo:** Viabilizar a operação do model Animal no backend e frontend.

---

## 1. Estado Atual

### Backend
* **Model `Animal`:** O model `pec_animais` existe (`services/api/pecuaria/animal/models.py`) e possui excelente abstração. Relacionamentos com `LoteAnimal`, `EventoAnimal` e auto-relacionamento (pai/mãe) estão definidos.
* **Campos no Model:** Possui identificadores (brinco, sisbov, microchip, nome), dados zootécnicos (espécie, categoria, raça, sexo, pelagem), datas (nascimento, entrada), estado (status, peso_atual_kg, data_ultima_pesagem) e financeiro (valor_aquisicao, valor_atual).
* **Enumerações:** `EspecieAnimal`, `SexoAnimal`, `CategoriaAnimal` e `StatusAnimal` estão bem estabelecidos.
* **Services/Schemas/Routers:** **Totalmente ausentes**. O model existe, mas a API não tem nenhuma rota para CRUD individual de animal.
* **Segurança:** O model suporta `tenant_id` e `unidade_produtiva_id`.

### Frontend
* **Navegação (sidebar):** Existe um link `/dashboard/pecuaria/animais` definido na `sidebar-config.ts` na seção "② Rebanho".
* **Dashboard (`page.tsx`):** Exibe métricas consolidadas por lote (cabeças, peso médio), mas os "Lotes Ativos" atualmente escondem a visão individual. Ações rápidas não incluem "Animais".
* **Lotes (`lotes/page.tsx`):** Trata Lotes de forma massiva, usando `quantidade_cabecas`. O conceito atual de "criar lote" pede "Qtd. de Cabeças", o que conflita conceitualmente com a adição um a um de instâncias `Animal` no Lote.

### Banco de Dados
* A tabela `pec_animais` existe e herda características do SQLAlchemy `Base`.
* FKs para `tenant_id`, `unidade_produtiva_id` e `lote_id` (on delete SET NULL) existem.
* Não possui `deleted_at` para soft-delete nativo do framework atual (embora o Plano 1 de Pecuária contemple adicionar).

---

## 2. Gaps Encontrados

1. **Backend - Inexistência da Camada de API:**
   - Não há `AnimalCreate`, `AnimalUpdate`, `AnimalResponse` (Schemas).
   - Não há `AnimalService` (Camada de Negócio).
   - Não há `animal.py` nos routers.
   - Consequentemente, a rota `GET /pecuaria/animais` simplesmente não existe.

2. **Frontend - Tela Inexistente:**
   - A página `/dashboard/pecuaria/animais/page.tsx` não existe. O menu da sidebar aponta para uma rota 404 (do Next.js).

3. **Inconsistência Conceitual em `LoteAnimal`:**
   - O Frontend atual cria Lotes pedindo `quantidade_cabecas` e `peso_medio_kg` (como entidades avulsas).
   - A introdução do Cadastro Individual exige que a quantidade de cabeças seja um `COUNT(animais)` atrelados ao lote, e não mais uma entrada arbitrária no input.

4. **Filtros e Paginação Ausentes no Backend para Pecuária:**
   - Será necessário um `AnimalFilter` genérico que suporte busca por brinco, lote, categoria e status.

---

## 3. Dependências

| Componente | Depende de | Status | Risco |
|------------|-----------|--------|-------|
| `AnimalService` | `BaseService` (core) | Criado | 🟢 Baixo |
| Migration `deleted_at` | Fase 1 do Plano Pecuária | Pendente | 🟢 Baixo |
| Página Frontend `/animais` | Componente `DataTable` (existente) | Pronto | 🟢 Baixo |
| Rota Sidebar `/animais` | `sidebar-config.ts` | Configurado | 🟢 Baixo |

---

## 4. Riscos

1. **Risco Arquitetural (Frontend vs Backend):** 🔴 ALTO
   - O lote atualmente permite registrar 100 cabeças digitando o número `100`. Se começarmos a cadastrar animais individualmente e vinculá-los ao lote, a soma dos animais individuais pode divergir do número `quantidade_cabecas` digitado manualmente.
   - **Mitigação:** `quantidade_cabecas` e `peso_medio_kg` no model `LoteAnimal` devem passar a ser tratados como *campos cacheados* (desnormalizados) calculados pelos `EventoAnimal` ou atualizados por listeners/triggers, desativando o input manual ou mantendo-o apenas para "Lotes Sem Detalhamento Individual" (modelo híbrido).

2. **Risco de Performance (Lista de Animais):** 🟡 MÉDIO
   - Fazendas grandes podem ter 20.000+ animais.
   - **Mitigação:** O Endpoint `GET /pecuaria/animais` precisa obrigatoriamente de paginação (`limit`, `skip`) desde o Dia 1.

3. **Risco de Acesso Multitenant:** 🟢 BAIXO
   - O `AnimalService` deve herdar de `BaseService` que já garante o isolamento por `tenant_id`.

---

## 5. Contratos Afetados

### Banco de Dados
* Nenhuma alteração estrutural no `pec_animais` é necessária apenas para o CRUD básico (assumindo que a migration de `deleted_at` sugerida no plano 1 será rodada antes).

### Frontend
* **Novas Telas:**
  - `apps/web/src/app/(dashboard)/dashboard/pecuaria/animais/page.tsx`
  - Componente modal `NovoAnimalModal`

### Backend APIs (Novos Contratos)
* `POST /api/v1/pecuaria/animais/`
* `GET /api/v1/pecuaria/animais/?page=1&page_size=50`
* `GET /api/v1/pecuaria/animais/{id}`
* `PATCH /api/v1/pecuaria/animais/{id}`
* `DELETE /api/v1/pecuaria/animais/{id}`

---

## 6. Estratégia de Implementação

### 1. Modelo Híbrido de Rebanho (Critico)
O AgroSaaS deve suportar duas modalidades:
- **Lote Fechado:** O usuário apenas diz "Lote A tem 50 cabeças", sem cadastro individual.
- **Lote Detalhado:** O usuário vincula instâncias de `Animal` ao lote.
O sistema deve lidar com isso aceitando que um lote possa não ter vínculos na tabela `pec_animais`, ou, se tiver, os eventos dos animais atualizam o contador do lote. Para o CRUD inicial do Animal, focaremos apenas em permitir que um `Animal` seja atrelado a um `lote_id` existente.

### 2. Padrão Visual (Frontend)
- Utilizar `PageHeader` com ícone `Beef`.
- Reutilizar `DataTable` com pesquisa rápida.
- Adicionar badges de cor para o `StatusAnimal` (Ex: ATIVO=Verde, VENDIDO=Azul, MORTO=Vermelho) e `CategoriaAnimal`.
- Botões de ações inline: "Detalhes", "Mover de Lote", "Pesagem Rápida" (para etapas futuras).

### 3. Schemas de API (Backend)
- Criar schemas que aproveitem as validações Enum do banco (`StatusAnimal`, etc).
- Fornecer um `AnimalFilter` que suporte querystring `q=` para pesquisa em `numero_brinco`, `numero_sisbov` e `nome`.

---

## 7. Sequência Recomendada

| Ordem | Etapa | Arquivo a Criar / Modificar |
|-------|-------|-----------------------------|
| 1 | **Schemas Pydantic** | `services/api/pecuaria/schemas/animal_schema.py` |
| 2 | **Serviço de Domínio** | `services/api/pecuaria/services/animal_service.py` |
| 3 | **Rotas da API** | `services/api/pecuaria/routers/animais.py` |
| 4 | **Registro da Rota** | `services/api/main.py` |
| 5 | **Frontend API Fetchers** | `apps/web/src/app/(dashboard)/dashboard/pecuaria/animais/page.tsx` |
| 6 | **Modal de Criação** | (Mesmo arquivo da listagem ou um component separado) |

---

## 8. Critérios de Aceitação

- [ ] A rota `GET /pecuaria/animais` retorna lista paginada de animais isolada por tenant e unidade produtiva.
- [ ] É possível criar um animal vinculando-o (ou não) a um `lote_id` válido da mesma fazenda.
- [ ] O frontend em `/dashboard/pecuaria/animais` carrega a `DataTable` de animais.
- [ ] A tabela frontend possui colunas: Brinco, Categoria, Sexo, Peso (kg), Lote Atual, Status.
- [ ] A pesquisa frontend consegue filtrar animais pelo número do brinco ou SISBOV.
- [ ] Nenhuma funcionalidade atual da tela de Lotes (`lotes/page.tsx`) é quebrada.
