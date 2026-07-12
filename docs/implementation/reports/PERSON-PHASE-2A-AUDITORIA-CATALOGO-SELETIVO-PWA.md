# PERSON-PHASE-2A — Auditoria Técnica do Catálogo Seletivo de Pessoas no Campo PWA

## Objetivo
Determinar exatamente como o Campo PWA deve receber, armazenar, atualizar e utilizar offline o catálogo mínimo de Pessoas elegíveis para execução operacional em cada Unidade Produtiva autorizada ao usuário.

---

## 1. Estado Atual do Sync

**Auditoria do Campo PWA (`db.ts` e `pull.ts`):**
- **Catálogos Atuais Sincronizados:** O sistema atualmente sincroniza `colaboradores` na tabela `db.colaboradores`.
- **Payload Recebido:** `id`, `nome`, `cpf` (PII sensível), `cargo`.
- **Filtro por UP/Tenant:** A sincronização no `pull.ts` não demonstra filtragem contextual por Unidade Produtiva para os colaboradores, substituindo globalmente a store `db.colaboradores` (`await db.colaboradores.bulkPut(...)`).
- **Atualização e Incremental:** O processo atual é destrutivo (`await db.colaboradores.clear()`) seguido de um replace total (full sync), e não se baseia em versionamento, cursores (`updated_at` até existe na query string `last_sync_at`, mas a substituição do catálogo é total).

---

## 2. Fonte de Verdade

A fonte principal do catálogo operacional é a combinação do agregado central de cadastro:
`Pessoa` + `PessoaRelacionamento` + `TipoRelacionamento`.

**Avaliação:**
- `ColaboradorRH` **não** é a identidade operacional. O envio de `colaboradores` deve ser **descontinuado** do payload de sync, pois mistura conceitos financeiros/RH com contexto operacional do campo.
- O uso de `Usuario` como executor também está descartado arquiteturalmente (separação IAM vs Operacional).
- **Decisão:** A Fase 2 deve substituir o catálogo atual. A entidade `ColaboradorRH` deixará de ser sincronizada para dar lugar a uma **projeção de leitura específica** para o PWA offline baseada nos relacionamentos ativos das Pessoas nas Unidades Produtivas do usuário.

---

## 3. Contrato de Elegibilidade e Resolução por UP

Apenas Pessoas com um `PessoaRelacionamento` ativo e vinculadas à UP devem descer para o PWA.

**Critérios Resolvidos:**
- O filtro deve cruzar `unidade_produtiva_id` autorizadas com os relacionamentos de cada pessoa.
- `ativo_desde` <= Data Atual (Servidor).
- `ativo_ate` >= Data Atual (Servidor) ou `null` (vigente por prazo indeterminado).
- O backend deve resolver a elegibilidade **no momento do pull**, usando a data de sincronização como referência determinística para montar o catálogo offline. Limitação conhecida: lançamentos retroativos no PWA com pessoas que já expiraram seu vínculo não aparecerão no seletor, exigindo conexão para o backend realizar a verificação no momento do envio.

---

## 4. Tratamento de Relacionamentos Tenant-Wide

Relacionamentos com `unidade_produtiva_id = NULL` (tenant-wide).

**Decisão Conservadora para o Piloto:**
Atualmente não há metadados consistentes em `TipoRelacionamento` que permitam distinguir um papel global-administrativo de um global-operacional autorizado ao PWA.
- **Regra:** **Sincronizar somente relacionamentos explicitamente vinculados a uma Unidade Produtiva**.
- Impactos temporários: Papéis legítimos como "Engenheiro Agrônomo" ou "Diretor de Operações" com escopo Tenant-Wide não aparecerão no PWA offline. Caso precisem operar o aplicativo, deve-se criar `PessoaRelacionamento` específico em cada UP desejada. 

---

## 5. Tratamento de Múltiplos Papéis por Pessoa e Unidade

Uma Pessoa pode possuir múltiplos relacionamentos válidos em uma mesma UP (ex: MOTORISTA e OPERADOR_MAQUINA).

**Estrutura Escolhida:** **Estrutura projetada por Unidade**

```json
{
  "id": "UP1-PESSOA1",
  "pessoa_id": "...",
  "nome_exibicao": "João",
  "unidade_produtiva_id": "UP1",
  "papeis": ["MOTORISTA", "OPERADOR_MAQUINA"]
}
```

**Justificativa:**
- **Simplicidade Dexie:** Fica extremamente simples realizar o fetch de todas as pessoas elegíveis para a tela atual: `db.pessoas_operacionais.where("unidade_produtiva_id").equals(currentUP)`.
- **Prevenção de Conflitos:** Evita sobrescritas quando a mesma pessoa atua em múltiplas UPs que sofrem sync simultâneo.

---

## 6. Payload Mínimo e LGPD

O payload atual sofre de excessos e quebra princípios LGPD na visão móvel (exposição de CPF).

**Payload Mínimo Aprovado:**
- `id` (Chave primária composta `pessoa_id` + `unidade_produtiva_id` para o Dexie).
- `pessoa_id`.
- `nome_exibicao` (Suficiente para operação, dispensando o nome civil completo que é PII restrito).
- `unidade_produtiva_id`.
- `papeis` (Array de códigos dos tipos de relacionamento).
- Sem campos de versão/`updated_at` por enquanto, mantendo o bulk replace offline para simplificação da store de catálogo.

**Anotação PII:** Extirpar o campo CPF, logradouros ou documentos, protegendo a empresa e o trabalhador.

---

## 7. Decisão Dexie

Será criada a nova store `pessoas_operacionais`.

- **Chave Primária:** `id` (Composta: `unidade_produtiva_id` + `pessoa_id`).
- **Índices:** `unidade_produtiva_id` (Crucial para o `PessoaSelect` da tela atual do PWA).
- **Versão do Dexie:** Atualização para `this.version(14)`.
- **Comportamento da Migração:**
  - `caderno_events`, `caderno_server_events`, `sync_queue` e `caderno_drafts` **DEVEM SER PRESERVADOS**.
  - A tabela legada `colaboradores` pode ser abandonada ou declarada vazia.

---

## 8. Decisão de Endpoint e Contrato Backend

O endpoint legado `/cadastros/pessoas` possui uma resposta rica com vários dados irrelevantes ao cenário de sincronização offline leve. Já o endpoint atual `GET /sync/pull` centraliza os pulls.

**Decisão:** Reutilizar a arquitetura de payloads do **`GET /sync/pull`**.
- Adicionar o bloco `pessoas_operacionais: []` no `SyncPullPayload`.
- O endpoint de sync deve receber a sessão e calcular `PessoaRelacionamento` ativo baseado no contexto das fazendas vinculadas ao `Device` (ou `Usuario`).
- O bloco `colaboradores` deve ser limpo/removido do contrato.
- A projeção evita sobrecarga na API de CRUD `/cadastros/pessoas` e centraliza o escopo de payloads offline no serviço de sincronização dedicado.

---

## 9. Autorização e Isolamento

- O backend injetará implicitamente no pull-sync o mapeamento da tabela `UnidadeProdutivaUsuario`.
- Apenas UPs autorizadas para o usuário logado terão pessoas materializadas na projeção do sync.
- Fica proibido exportar relacionamentos de UPs não acessíveis ou informações de Tenants adjacentes, coibindo vazamento de inteligência.

---

## 10. Seleção Offline no PWA (`PessoaSelect`)

Substituição do Componente Atual Placeholder:
- **Catálogo vazio / Não sincronizado:** O select deve ficar desabilitado indicando status "Baixando catálogo operacional..." ou "Nenhuma pessoa autorizada nesta unidade".
- **Busca Contextual:** Quando houver UP selecionada na página de Caderno, o componente usará `useLiveQuery` no Dexie com `db.pessoas_operacionais.where({ unidade_produtiva_id: currentUP })`.
- **Múltiplos Papéis:** O seletor exibirá o `nome_exibicao`. Em sub-rótulo opcional ou tooltip, poderá listar os `papeis`.
- **Troca de Unidade:** Se o rascunho (draft) mudar de UP1 para UP2, o formulário deve limpar o valor de `executado_por_pessoa_id` automaticamente, forçando nova seleção compatível com a UP2.

---

## 11. Sincronização e Conflitos Offline

- **Pessoa expirada/removida no backend e lançada em PWA Offline:**
  O backend receberá um push com `executado_por_pessoa_id` que já não possui vínculo válido no dia/hora do evento.
  **Ação Backend:** O backend valida de maneira rigorosa a vigência com base na data da ocorrência (`data_registro`).
  **Conflito:** Caso não seja válido, o apontamento não é gravado oficialmente e o `sync_status` do PWA passa para `CONFLICT` com a mensagem `conflict_reason: "Executor não possui permissão ou contrato vigente na data do evento"`. O usuário visualiza o evento bloqueado na fila e deve editá-lo para re-atribuir o executor localmente.

---

## 12. Compatibilidade

- **Drafts antigos e Filas Antigas:** Como o `executado_por_pessoa_id` sempre foi uma string livre (UUID ou nulo), apontamentos velhos continuarão trafegando no Push sem romper a API.
- PWA novo vs API antiga: PWA novo não encontrará o bloco `pessoas_operacionais` no payload. O componente `PessoaSelect` aparecerá vazio, mas a operação continuará elegível caso o campo seja opcional no formulário.
- Nenhuma migration complexa destruirá os apontamentos já feitos.

---

## 13. Plano de Implementação

- **PERSON-PHASE-2B — Contrato backend:**
  Ajuste do `SyncService.pull_sync()` para resolver o cruzamento de PessoaRelacionamento e injetar `pessoas_operacionais` no output; remoção limpa do bloco de `colaboradores`.
- **PERSON-PHASE-2C — Persistência Dexie:**
  Update de versão (v14) adicionando a store `pessoas_operacionais`. Atualização de `pull.ts` para processar a substituição dos registros da store baseado no UP_ID.
- **PERSON-PHASE-2D — Seletor offline:**
  Desenvolvimento do novo `PessoaSelect` no frontend, consumindo Dexie reativamente e integração com o contexto do `useCadernoStore` (troca de UP).
- **PERSON-PILOT-02 — Dry Run offline:**
  Geração em campo testando expiração, múltiplas UPs e tratamento de payload mínimo sem PII.

---

## 14. Riscos e Impacto no Piloto

- **Risco:** Falta de Papéis Tenant-Wide dificultar a atuação de gestores em unidades pequenas na fase de implantação. Mitigação: Forçar atribuição de `PessoaRelacionamento` em todas as UPs para engenheiros por enquanto.
- **Risco:** LGPD compliance prejudicada se o CPF não for removido do backend no sync antes de rollout. Mitigação: Alta prioridade para a Phase-2B.
- **Impacto Piloto:** O piloto operacional de Caderno pode prosseguir, com o alerta de que o executor não será validado de maneira fluida e automática sem o campo de seletor.

---

## Veredictos Obrigatórios

| Item Auditado | Veredicto |
| --- | --- |
| **backend atual** | **NO GO** (vaza CPF no sync, exporta ColaboradorRH) |
| **endpoint atual** | **NO GO** |
| **elegibilidade por UP** | **GO COM RESSALVAS** (necessário projetar no pull sync) |
| **múltiplos papéis** | **GO COM RESSALVAS** (banco suporta perfeitamente, pendente PWA/Dexie) |
| **tenant-wide** | **NO GO** (exclusão intencional e conservadora no PWA para Fase 2) |
| **payload LGPD** | **NO GO** |
| **Dexie** | **NO GO** (store desatualizada baseada em Colaborador flat) |
| **pull** | **NO GO** (código obsoleto importando Colaboradores) |
| **seletor offline** | **NO GO** (estático/placeholder) |
| **compatibilidade** | **GO** (não introduz quebra dura de apontamentos legados) |
| **prontidão para implementação** | **GO** (arquitetura totalmente mapeada) |
| **prontidão do piloto atual** | **GO COM RESSALVAS** (permite registrar sem executor estruturado temporariamente) |
