# MASTERDATA-01 — Auditoria Profunda do Domínio Cultura

## 1. Resumo executivo

O domínio `Cultura` está parcialmente consolidado, mas ainda não está totalmente unificado.

Estado real encontrado na codebase:

- Existe um catálogo novo e arquiteturalmente preferível em `cadastros_culturas`, modelado por `ProdutoCultura`.
- Existe uma estrutura legada paralela em `agricola/cadastros`, com model e router próprios para `culturas`.
- Os fluxos operacionais críticos não usam apenas catálogo oficial:
  - `Safra` ainda persiste `cultura` textual.
  - `Cultivo` persiste `cultura` textual e opcionalmente `cultivar_id` para `cadastros_culturas`.
  - `Hedge` resolve commodity primeiro por `Cultivo.commodity_id` e depois faz fallback por `Safra.cultura`.
  - `Campo PWA` sincroniza `safra.cultura` textual.
- O frontend principal já tende ao catálogo novo (`/cadastros/culturas`), mas ainda há consumidor ativo da rota legada (`/agricola/cadastros/culturas`).

Conclusão segura:

- A fonte oficial recomendada para novos fluxos e para o futuro Wizard deve ser `ProdutoCultura` / tabela `cadastros_culturas`.
- A estrutura legada ainda é necessária para compatibilidade.
- Não é seguro consolidar escrita nem remover legado nesta execução.
- Decisão tomada: **Opção A — apenas auditoria e plano seguro**.

Resposta curta à pergunta central:

**Sabemos qual entidade deve ser usada pelo Wizard e pelos novos fluxos: `ProdutoCultura` / `cadastros_culturas`. Porém ainda não é seguro tratar essa entidade como substituição completa do legado sem uma etapa posterior de compatibilidade e migração controlada.**

---

## 2. Entidades encontradas

| Conceito | Model/Tabela | Owner | Status | Uso atual | Risco |
| --- | --- | --- | --- | --- | --- |
| Cultura legada | `agricola.cadastros.models.Cultura` / `culturas` | Agricultura legado | Ativo na codebase | CRUD legado e consumidor frontend legado | Alto |
| Cultura oficial | `core.cadastros.produtos.models.ProdutoCultura` / `cadastros_culturas` | Core Cadastros | Ativo | Catálogo principal em telas novas, solo e cultivos | Baixo |
| Safra.cultura textual | `agricola.safras.models.Safra.cultura` | Agricultura | Legado compatível | Filtro, exibição, fallback, sync PWA | Alto |
| Cultivo.cultura textual | `agricola.cultivos.models.Cultivo.cultura` | Agricultura | Híbrido/compatível | Obrigatório na criação operacional | Alto |
| Cultivo.cultivar_id | `agricola.cultivos.models.Cultivo.cultivar_id` -> `cadastros_culturas.id` | Agricultura + Core | Oficial parcial | Ponte para catálogo oficial | Médio |
| Cultivo.commodity_id | `agricola.cultivos.models.Cultivo.commodity_id` -> `cadastros_commodities.id` | Agricultura + Core | Oficial operacional | Base de hedge e colheita | Médio |
| Commodity | `core.cadastros.commodities.models.Commodity` / `cadastros_commodities` | Core Cadastros | Oficial | Comercialização, hedge, produto colhido, romaneio | Baixo |
| Produto | `core.cadastros.produtos.models.Produto` / `cadastros_produtos` | Core Cadastros | Oficial | Insumos e estoque de entrada | Baixo |
| ProdutoColhido | `agricola.colheita.models.ProdutoColhido` / `agricola_produtos_colhidos` | Agricultura | Ativo | Usa `commodity_id`, não usa cultura direta | Médio |
| Contrato Hedge | `financeiro.hedge.models.ContratoFuturo` | Financeiro/Hedge | Híbrido | Usa `commodity_id` e ainda mantém `commodity` textual | Médio |
| Comercialização | `financeiro.comercializacao.models.ComercializacaoCommodity` | Financeiro/Comercialização | Oficial por commodity | Usa `commodity_id` e opcionalmente `produto_colhido_id` | Baixo |

---

## 3. Tabelas e models

### 3.1 Catálogo oficial identificado

Evidências:

- `services/api/core/cadastros/produtos/models.py`
  - `ProdutoCultura.__tablename__ = "cadastros_culturas"`
  - comentário do model: "Migrado de agricola/cadastros/models.py (tabela 'culturas')."
- `services/api/core/cadastros/produtos/router.py`
  - CRUD em `/cadastros/culturas`
- `services/api/core/routers/backoffice_tabelas.py`
  - CRUD sistêmico/global para culturas baseadas em `ProdutoCultura`
- `services/api/agricola/analises_solo/service.py`
  - solo já resolve cultura por `ProdutoCultura`, com lookup por `cultura_id` ou `cultura_nome`

Interpretação:

- `cadastros_culturas` é a estrutura que já carrega intenção arquitetural de catálogo mestre.
- É a única estrutura que também suporta extensões agronômicas e backoffice sistêmico.

### 3.2 Estrutura legada ainda ativa

Evidências:

- `services/api/agricola/cadastros/models.py`
  - `Cultura.__tablename__ = "culturas"`
- `services/api/agricola/cadastros/router.py`
  - CRUD ativo em `/culturas`
- `services/api/main.py`
  - router agrícola legado ainda incluído na aplicação

Interpretação:

- O legado não foi removido da codebase.
- Ainda existe superfície pública ativa para cadastro de cultura fora do catálogo oficial.

### 3.3 Inconsistência estrutural relevante

Evidência crítica:

- `services/api/migrations/versions/ed0688180f35_onda2_produtos_commodities.py`
  - cria `cadastros_culturas`
  - migra dados de `culturas`
  - executa `op.drop_table('culturas')`

Mas ao mesmo tempo:

- o model legado `agricola/cadastros/models.py` continua ativo;
- o router legado continua ativo;
- o frontend ainda possui consumidor legado.

Conclusão:

- Há **drift entre intenção de migration e estado lógico da aplicação**.
- Não é seguro assumir que a estrutura legada está efetivamente desativada em todos os ambientes.

---

## 4. Rotas

### 4.1 Rotas oficiais

- `services/api/core/cadastros/produtos/router.py`
  - `GET /cadastros/culturas`
  - `POST /cadastros/culturas`
  - `PATCH /cadastros/culturas/{cultura_id}`
  - `DELETE /cadastros/culturas/{cultura_id}`
- `services/api/core/routers/backoffice_tabelas.py`
  - `GET /culturas`
  - `POST /culturas`
  - `PATCH /culturas/{cultura_id}`
  - `DELETE /culturas/{cultura_id}`
  - parâmetros de solo por cultura

### 4.2 Rotas legadas

- `services/api/agricola/cadastros/router.py`
  - `GET /culturas/`
  - `POST /culturas/`
  - `PATCH /culturas/{id}`
  - `DELETE /culturas/{id}`

Risco:

- Existem dois pontos de CRUD de cultura com modelos distintos.
- Isso permite divergência funcional e de dados entre catálogo oficial e legado.

---

## 5. Frontend

### 5.1 Frontend já orientado ao catálogo oficial

Evidências:

- `apps/web/src/components/agricola/safra-create-dialog.tsx`
  - consulta `/cadastros/culturas`
- `apps/web/src/app/(dashboard)/agricola/planejamento/page.tsx`
  - consulta `/cadastros/culturas`
- `apps/web/src/app/(dashboard)/dashboard/agricola/page.tsx`
  - consulta `/cadastros/culturas`
- `apps/web/src/components/cadastros/tabelas-reusable/culturas-reusable.tsx`
  - usa `/cadastros/culturas` ou `/backoffice/tabelas/culturas`

### 5.2 Consumidor legado ainda ativo

Evidência:

- `apps/web/src/hooks/use-agricola.ts`
  - `useCulturas()` chama `apiFetch("/agricola/cadastros/culturas")`

Conclusão:

- O frontend não está totalmente consolidado.
- O Wizard deve usar apenas o catálogo oficial, mas não é seguro descontinuar a rota legada nesta execução.

### 5.3 Modelo de UI ainda fortemente textual

Evidências recorrentes em páginas e tipos:

- `SafraOption.cultura?: string | null`
- `CultivoOption.cultura: string`
- várias telas de safra, dashboard e financeiro exibem `cultura` textual

Impacto:

- O frontend ainda trata `cultura` como valor exibível de primeira classe, não como entidade totalmente resolvida por ID.

---

## 6. Campo PWA

Evidência:

- `apps/campo/src/lib/sync/pull.ts`
  - payload de `safras` contém `cultura?: string | null`
  - mapper persiste `cultura: s.cultura ?? undefined`

Conclusão:

- O Campo PWA ainda depende diretamente de `Safra.cultura`.
- Qualquer consolidação que remova ou altere o papel desse campo sem transição quebrará sync, cache local e UX offline.

---

## 7. Testes existentes

### 7.1 Testes ainda amarrados ao modelo textual/legado

Evidências:

- `services/api/tests/integration/agricola/test_safras.py`
  - payloads de criação usam `cultura`
  - filtros de listagem usam `?cultura=SOJA`
- múltiplos testes unitários/integrados inserem `safras.cultura` diretamente
- múltiplos testes criam `cultivos` com `cultura` textual
- testes de sync/PWA também esperam `safra.cultura`

### 7.2 Testes que confirmam a ponte operacional via commodity

Evidências:

- `services/api/tests/integration/enterprise/test_hedge_mvp.py`
  - `_resolver_commodity_da_safra` prioriza `Cultivo.commodity_id`
- `services/api/tests/unit/agricola/test_produto_colhido.py`
  - `ProdutoColhido` exige `commodity_id`

Conclusão:

- O conjunto de testes confirma que o sistema está em estado híbrido.
- Ainda não há evidência de que o legado possa ser removido com segurança.

---

## 8. Fluxos dependentes

### 8.1 Criação de Safra

Evidências:

- `services/api/agricola/safras/service.py`
  - fluxo novo aceita `cultivos`
  - fluxo legado aceita `talhao_ids`
  - `Safra.cultura` recebe a cultura do primeiro cultivo ou `dados.cultura`
  - `Cultivo` é criado com `cultura`, `cultivar_id` e `commodity_id`

Leitura objetiva:

- `Safra` ainda não usa apenas `ProdutoCultura`.
- `Safra.cultura` permanece como espelho textual legado.
- O fluxo oficial novo já suporta `cultivar_id`, mas não o torna exclusivo.

### 8.2 Criação de Cultivo

Evidências:

- `services/api/agricola/cultivos/models.py`
  - `cultura` textual é obrigatória
  - `cultivar_id` é opcional
  - `commodity_id` é opcional

Leitura objetiva:

- O modelo operacional atual exige texto e apenas complementa com vínculo oficial.
- `cultivar_id` ainda não substituiu `cultura`.

### 8.3 Romaneio / Colheita

Evidências:

- `services/api/agricola/romaneios/models.py`
  - `RomaneioColheita.commodity_id`
- `services/api/agricola/romaneios/service.py`
  - tenta derivar por commodity
  - ainda usa fallback textual por `safra.cultura`
- `services/api/agricola/colheita/models.py`
  - `ProdutoColhido` usa `commodity_id`

Leitura objetiva:

- Colheita e romaneio são commodity-centric.
- Cultura participa mais como contexto/fallback do que como chave principal.

### 8.4 Comercialização

Evidências:

- `services/api/financeiro/comercializacao/models.py`
  - usa `commodity_id`
  - opcionalmente `produto_colhido_id`

Leitura objetiva:

- Comercialização usa commodity oficial.
- Não depende de `Cultura` como entidade central.

### 8.5 Hedge

Evidências:

- `services/api/financeiro/hedge/service.py`
  - primeiro resolve por `Cultivo.commodity_id`
  - se não houver commodity única, faz fallback por `Safra.cultura`
- `apps/web/src/app/(dashboard)/dashboard/financeiro/hedge/contratos/commodity-resolution.ts`
  - replica a mesma lógica: primeiro `commodity_id` dos cultivos; fallback textual por `cultura`

Leitura objetiva:

- Hedge já está alinhado à arquitetura correta de derivar por `Cultivo`.
- Mas ainda depende de fallback textual para compatibilidade.

### 8.6 Wizard / Onboarding

Conclusão segura:

- O Wizard não deve usar a rota legada nem a tabela legada como fonte de cadastro novo.
- O Wizard deve trabalhar com:
  1. `cadastros_culturas` como catálogo de cultura
  2. `cadastros_commodities` como catálogo de mercado
  3. `Cultivo` como ponte entre safra, cultura, área e commodity
- O Wizard não deve assumir que `Safra.cultura` é a fonte de verdade; esse campo deve ser tratado como compatibilidade/espelho textual.

---

## 9. Fonte oficial recomendada

### 9.1 Fonte oficial para novos fluxos

**Fonte oficial recomendada: `core.cadastros.produtos.models.ProdutoCultura` / `cadastros_culturas`.**

Justificativa baseada na codebase:

- já possui CRUD dedicado;
- já possui backoffice sistêmico;
- já é referenciada por `Cultivo.cultivar_id`;
- já é usada por análises de solo;
- carrega intenção explícita de substituição do legado;
- está posicionada em `core`, não em módulo agrícola local.

### 9.2 Papel da Commodity

**`Commodity` é entidade independente, não dona de `Cultura`.**

Justificativa:

- hedge, comercialização e produto colhido dependem de commodity;
- `Cultivo` liga cultura operacional a commodity de mercado;
- não há evidência de que "commodity gera cultura";
- a modelagem aponta para entidades independentes conectadas por `Cultivo`.

### 9.3 Papel de `Safra.cultura`

**`Safra.cultura` deve ser tratada como campo legado/backward compatibility, não como nova fonte de verdade.**

Justificativa:

- continua sendo preenchida em `SafraService`;
- continua sendo consumida por PWA, filtros, exibição e fallbacks;
- não fornece relacionamento oficial por si só.

---

## 10. Riscos

1. Duplicidade real de catálogos
   - `culturas` legado e `cadastros_culturas` coexistem na aplicação.

2. Drift migration x aplicação
   - migration `ed0688180f35` declara remoção de `culturas`, mas model/router legado seguem ativos.

3. Dependência textual disseminada
   - `Safra.cultura` e `Cultivo.cultura` ainda aparecem em testes, PWA, filtros e frontend.

4. Superfície pública duplicada
   - duas famílias de endpoints de cultura podem causar divergência silenciosa.

5. Compatibilidade com hedge e romaneio
   - embora commodity seja prioridade, ambos ainda aceitam/precisam de fallback textual em cenários legados.

---

## 11. Decisão tomada

**Opção A — Apenas auditoria e plano seguro**

Motivos:

- existe risco alto de regressão funcional;
- há consumidores ativos do legado;
- há forte acoplamento de testes a campos textuais;
- a coexistência de model/router legado com migration de remoção indica que a base ainda não está pronta para consolidação segura nesta execução;
- não havia evidência suficiente para alterar escrita/leitura central sem tocar múltiplos fluxos fora do escopo permitido.

---

## 12. Implementações

Nenhuma implementação de código foi realizada.

Motivo:

- qualquer consolidação mínima útil exigiria definir uma camada de resolução e depois escolher pontos de adoção;
- os pontos mais valiosos de adoção (`Safra`, `Cultivo`, `Hedge`, `Romaneio`, sync PWA, hooks frontend`) ainda estão espalhados e com forte dependência de compatibilidade;
- sem um pacote coordenado de transição, a mudança seria cosmética ou arriscada.

---

## 13. Arquivos alterados

- `docs/implementation/reports/MASTERDATA-01-AUDITORIA-CULTURA-OFICIAL.md`

---

## 14. Validações executadas

Como não houve alteração de código operacional:

- não foi executado `pytest` de backend;
- não foi executado `eslint` ou `typecheck` de frontend;
- não foi executado `ruff`.

Validação aplicável:

- revisão estática da codebase por busca, leitura de models, services, routers, migrations, frontend, PWA e testes.

---

## 15. Limitações

1. A auditoria foi baseada exclusivamente na codebase local.
2. Não houve inspeção direta do banco em execução.
3. Não houve execução de fluxos end-to-end.
4. A coexistência entre migration e model legado sugere que diferentes ambientes podem estar em estados distintos.

---

## 16. Plano futuro de migração

### Fase 1 — Congelar a fonte para novos fluxos

- Todo novo fluxo de cadastro deve usar apenas `/cadastros/culturas`.
- Todo novo fluxo de onboarding/wizard deve gravar `cultivar_id` quando aplicável.
- `Safra.cultura` e `Cultivo.cultura` continuam sendo preenchidos como espelho textual de compatibilidade.

### Fase 2 — Introduzir resolução oficial explícita

Criar, em execução futura, uma camada de resolução de cultura com prioridade:

1. `Cultivo.cultivar_id` -> `ProdutoCultura`
2. fallback `Cultivo.cultura`
3. fallback `Safra.cultura`

Essa camada deve ser usada primeiro em leitura, não em remoção de legado.

### Fase 3 — Migrar consumidores

Migrar gradualmente:

- hooks frontend ainda legados;
- endpoints que listam/filtram cultura;
- sync e payloads do Campo PWA;
- relatórios e dashboards que hoje dependem só de texto.

### Fase 4 — Auditoria de dados e cobertura

Antes de remover qualquer legado:

- provar que não há divergência relevante entre `culturas` e `cadastros_culturas` nos ambientes ativos;
- cobrir com testes os cenários híbridos;
- confirmar que `Safra`, `Cultivo`, `Romaneio`, `Hedge`, `Comercialização` e PWA não dependem mais de fallback textual.

### Fase 5 — Depreciação controlada

Somente depois:

- despublicar rota legada;
- remover dependências de leitura;
- avaliar remoção de models/campos legados em execução separada.

---

## Respostas objetivas aos critérios de aceite

### A estrutura atual de Cultura foi mapeada profundamente?

Sim.

Foram auditados backend, migrations, frontend, Campo PWA e testes relacionados a `Cultura`, `ProdutoCultura`, `cultura`, `cultivar_id` e `commodity_id`.

### Nenhuma remoção destrutiva foi feita?

Sim.

Nenhuma remoção foi realizada.

### Nenhuma migration destrutiva foi criada?

Sim.

Nenhuma migration foi criada.

### A fonte oficial recomendada foi justificada por evidência?

Sim.

`ProdutoCultura` / `cadastros_culturas` foi justificada por modelagem, rotas, backoffice, uso em solo e vínculo por `Cultivo.cultivar_id`.

### Os fluxos críticos de Safra, Cultivo, Romaneio, Comercialização e Hedge foram considerados?

Sim.

Todos foram auditados e descritos neste relatório.

### O futuro Wizard terá uma orientação clara sobre qual Cultura usar?

Sim.

O Wizard deve usar `cadastros_culturas` como catálogo de cultura e nunca a rota legada como fonte nova de cadastro.

### Se houver código, ele é compatível com dados legados?

Não se aplica.

Não houve mudança de código.

### Se não houver código, o plano de migração está claro e acionável?

Sim.

O plano foi estruturado em cinco fases, começando por congelamento da fonte oficial e só depois migração de consumidores.

---

## Pergunta final obrigatória

**Após esta execução, sabemos com segurança qual entidade de Cultura deve ser usada pelo Assistente de Implantação e pelos novos fluxos do AgroSaaS, sem quebrar Safra, Cultivo, Romaneio, Comercialização, Hedge e dados legados?**

**Sim, para novos fluxos a entidade correta é `ProdutoCultura` / `cadastros_culturas`. Não, ainda não é seguro tratar essa entidade como substituição completa do legado. Portanto, o Wizard já pode adotar a fonte oficial, mas a plataforma ainda precisa de uma transição controlada antes de consolidar totalmente o domínio Cultura sem dependências legadas.**
