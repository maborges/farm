# MASTERDATA-02 — Camada Oficial de Resolução de Cultura

## 1. Resumo executivo

Esta execução implementou uma camada única e reutilizável de resolução de Cultura no backend, sem migração de banco, sem remoção de legado e sem quebra de compatibilidade.

Resultado:

- `ProdutoCultura` / `cadastros_culturas` permanece como fonte oficial.
- Foi criado um resolver central de leitura em `services/api/core/services/cultura_resolution_service.py`.
- O `HedgeService` passou a usar o resolver central no fallback de cultura, preservando a priorização operacional por `Cultivo.commodity_id`.
- O frontend de baixo risco em `apps/web/src/hooks/use-agricola.ts` passou a priorizar `/cadastros/culturas`, com fallback para `/agricola/cadastros/culturas`.
- O Campo PWA continuou compatível com `safra.cultura` e ganhou suporte passivo a metadados oficiais opcionais.

Não foi alterado:

- banco de dados;
- migrations;
- models legados;
- rotas legadas;
- payloads incompatíveis;
- `SafraService`, `CultivoService`, `RomaneioService`, `ColheitaService`, `Comercialização`, `Onboarding` e `Wizard`.

---

## 2. Reauditoria antes da implementação

Foi feita revalidação local do estado dos módulos auditados em `MASTERDATA-01`:

- `services/api/agricola/`
- `services/api/core/cadastros/produtos/`
- `services/api/financeiro/hedge/`
- `services/api/financeiro/comercializacao/`
- `apps/web/`
- `apps/campo/`

Conclusão da reauditoria:

- A estratégia do `MASTERDATA-01` continuava válida.
- O catálogo oficial seguia em `cadastros_culturas`.
- O legado continuava ativo.
- Havia inclusive alteração local pré-existente em `services/api/financeiro/hedge/service.py` já alinhada à priorização por `Cultivo`, o que não invalidou a estratégia.

---

## 3. Arquitetura adotada

### Localização

Serviço criado em:

- `services/api/core/services/cultura_resolution_service.py`

Motivo:

- o resolver é transversal a múltiplos módulos;
- ele não cria novo domínio;
- ele reutiliza o `core` como ponto comum de master data e serviços compartilhados.

### Responsabilidade

O serviço:

- resolve cultura oficial em modo somente leitura;
- respeita `tenant_id`;
- nunca grava;
- nunca altera banco;
- nunca atualiza registros;
- nunca remove compatibilidade.

### Contrato interno

O resolver retorna um objeto explícito com:

- `status`
- `source`
- `cultura_id`
- `nome`
- `nome_cientifico`
- `matched_text`
- `cultivo_id`
- `safra_id`

Status possíveis implementados:

- `RESOLVED`
- `NOT_FOUND`
- `MULTIPLE`

Isso permite uso futuro por Hedge, Wizard, PWA e outros módulos sem lançar exceção quando não houver resolução.

---

## 4. Ordem oficial de resolução implementada

A prioridade implementada segue a ordem definida no escopo:

1. `Cultivo.cultivar_id` -> `ProdutoCultura`
2. `Cultivo.cultura` textual -> `ProdutoCultura`
3. `Safra.cultura` textual -> `ProdutoCultura`
4. sem resolução -> `NOT_FOUND`

Observação adicional:

- para contextos de safra com múltiplos resultados conflitantes, o serviço retorna `MULTIPLE`.

---

## 5. Consumidores migrados nesta execução

### 5.1 Backend — Hedge

Arquivo:

- `services/api/financeiro/hedge/service.py`

Mudança:

- `HedgeService` agora instancia `CulturaResolutionService`.
- O fluxo de `_resolver_commodity_da_safra` continua:
  1. primeiro tenta derivar por `Cultivo.commodity_id`;
  2. se não houver commodity derivável, usa o resolver central para obter a cultura;
  3. só então tenta casar a cultura com `Commodity.nome` / `Commodity.codigo`.

Impacto:

- o comportamento operacional prioritário do hedge foi preservado;
- a camada central passou a ser o único fallback oficial de cultura nesse módulo.

### 5.2 Frontend — Hook agrícola

Arquivo:

- `apps/web/src/hooks/use-agricola.ts`

Mudança:

- `useCulturas()` agora prioriza `/cadastros/culturas`;
- em caso de falha, mantém fallback para `/agricola/cadastros/culturas`.

Impacto:

- novos fluxos consumidores do hook passam a preferir o catálogo oficial;
- a compatibilidade com a rota legada foi preservada.

### 5.3 Campo PWA

Arquivos:

- `apps/campo/src/lib/db.ts`
- `apps/campo/src/lib/sync/pull.ts`

Mudança:

- `CachedSafra` passou a aceitar campos opcionais:
  - `cultura_id`
  - `cultura_nome`
  - `cultura_source`
- o sync pull passou a armazenar esses metadados quando existirem.

Impacto:

- `safra.cultura` continua sendo aceita e armazenada;
- não houve quebra de payload;
- o PWA fica preparado para consumir metadata oficial futura sem alteração incompatível.

---

## 6. Consumidores ainda legados

Continuam sem migração nesta execução:

- `SafraService`
- `CultivoService`
- `RomaneioService`
- `ColheitaService`
- `Comercialização`
- `Onboarding`
- `Wizard`

Motivo:

- o escopo exigia migração apenas de baixo risco;
- esses fluxos ainda têm dependência mais ampla de compatibilidade textual e exigem etapa posterior controlada.

---

## 7. Arquivos alterados

- `services/api/core/services/cultura_resolution_service.py`
- `services/api/tests/unit/core/test_cultura_resolution_service.py`
- `services/api/financeiro/hedge/service.py`
- `services/api/tests/integration/enterprise/test_hedge_mvp.py`
- `apps/web/src/hooks/use-agricola.ts`
- `apps/campo/src/lib/db.ts`
- `apps/campo/src/lib/sync/pull.ts`

---

## 8. Testes adicionados e cobrindo o escopo

Novo arquivo:

- `services/api/tests/unit/core/test_cultura_resolution_service.py`

Cobertura implementada:

- resolução por `cultivar_id`
- fallback por `Cultivo.cultura`
- fallback por `Safra.cultura`
- retorno `NOT_FOUND` quando nada existe
- compatibilidade com dado antigo: cultivo sem mapeamento oficial e fallback para safra

Cobertura adicional no hedge:

- `services/api/tests/integration/enterprise/test_hedge_mvp.py`
  - teste garantindo uso do resolver central no fallback do hedge

---

## 9. Validações executadas

### Backend

Executado:

- `services/api/.venv/bin/pytest services/api/tests/unit/core/test_cultura_resolution_service.py services/api/tests/integration/enterprise/test_hedge_mvp.py -q`

Resultado:

- `21 passed`

Executado:

- `services/api/.venv/bin/ruff check services/api/core/services/cultura_resolution_service.py services/api/tests/unit/core/test_cultura_resolution_service.py`

Resultado:

- `All checks passed!`

### Frontend

Executado:

- `pnpm --dir apps/web exec eslint src/hooks/use-agricola.ts`
- `pnpm --dir apps/campo exec eslint src/lib/db.ts src/lib/sync/pull.ts`

Resultado:

- sem erros reportados

### Diff

Executado:

- `git diff --check`
- `git -C apps/web diff --check`

Resultado:

- sem erros

---

## 10. Limitações

1. O arquivo `services/api/financeiro/hedge/service.py` possui passivo pré-existente de `ruff` fora do escopo desta execução.
2. Por esse motivo, o lint Python foi validado estritamente no novo serviço e no novo teste, não no arquivo inteiro legado do hedge.
3. Não houve migração de consumidores mais sensíveis como safra, romaneio e colheita.
4. O resolver central ainda não expõe endpoint público, por decisão de escopo.

---

## 11. Critérios de aceite

### Nenhuma migration criada?

Sim.

### Nenhum model removido?

Sim.

### Nenhuma rota removida?

Sim.

### Nenhum endpoint quebrado?

Não foi identificado endpoint quebrado no escopo alterado.

### Nenhum payload alterado de forma incompatível?

Sim.

No PWA, apenas campos opcionais foram aceitos/adicionados.

### ProdutoCultura permaneceu como fonte oficial?

Sim.

### Safra.cultura continua funcionando?

Sim.

Ela continua sendo usada como fallback e compatibilidade.

### Cultivo.cultura continua funcionando?

Sim.

Ela continua sendo usada como segunda prioridade de resolução.

### A resolução prioriza cultivar_id?

Sim.

### Hedge passou a utilizar o resolver central?

Sim.

### O frontend legado continua compatível?

Sim.

Há fallback explícito para a rota legada.

### O Campo PWA continua compatível?

Sim.

`safra.cultura` continua preservada.

### Não houve regressão funcional?

No escopo validado, não houve evidência de regressão:

- testes backend passaram;
- lints executados no escopo novo passaram;
- diffs estão limpos.

---

## 12. Conclusão objetiva

**Após esta execução, o AgroSaaS possui uma única camada oficial de resolução de Cultura, reutilizável por todos os módulos, permitindo que novos fluxos utilizem o catálogo oficial (`ProdutoCultura`) enquanto a compatibilidade com Safra, Cultivo, Hedge, Campo PWA e dados legados permanece preservada, preparando a plataforma para a futura consolidação definitiva do domínio Cultura.**

Com a ressalva correta:

- essa camada oficial já existe e está pronta para reuso;
- a consolidação definitiva dos consumidores ainda deve ser feita em etapas posteriores, sem remover o legado prematuramente.
