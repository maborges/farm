# PERSON-PHASE-0 — Contrato de Rastreabilidade e Campo PWA

Este documento é o adendo formativo do `PERSON-EXEC-PLAN-01`. Ele oficializa as regras de negócio para as implementações subsequentes do domínio de Pessoas no AgroSaaS, especificamente para Caderno de Campo, Sincronização PWA e Transição RH.

## 1. Fonte de Verdade do Executor (Caderno de Campo)

**Análise do Contexto:**
A entidade `CadernoCampoEntrada` não é um mero log de projeção. Ela é um **agregado principal independente**. Embora possa referenciar uma `OperacaoAgricola` (via `operacao_id`), existem atividades puramente geradas no PWA offline sem vínculo a uma execução formal (ex: observação de praga manual, visita técnica rápida).
O executor não pode depender estritamente de `OperacaoExecucao`.

**Decisão Oficial: Alternativa C — Modelo Híbrido Controlado**

O `CadernoCampoEntrada` deve possuir **executor próprio**, mas com regra estrita de herança:
- **Novo Campo:** `executado_por_pessoa_id (UUID, nullable=True, FK cadastros_pessoas.id)`.
- **Regra de Precedência:**
  1. Se a entrada é gerada manualmente (Web/PWA), o campo `executado_por` dita quem atuou fisicamente.
  2. Se a entrada é gerada automaticamente por uma `OperacaoAgricola`, o motor copia o `operador_id` da operação para o `executado_por_pessoa_id` do Caderno, consolidando a fonte em tempo de escrita e evitando JOINS complexos nos relatórios.
- **Obrigatoriedade:** Será opcional em banco (para suportar o legado), porém exigido na interface do PWA durante apontamentos físicos (ex: Colheita).

## 2. Matriz de Rastreabilidade

Conceitos oficiais:
- **Executor Físico:** Identidade Operacional (`Pessoa`).
- **Registrador:** Identidade de Login (`Usuario`). Quem operou o teclado/app.

| Fluxo | Agregado Principal | Executor | Registrador | Aprovador | Origem Automática |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Operação Agrícola** | `OperacaoAgricola` | `operador_id` (Pessoa) | `created_by` implícito | N/A | ERP / Integração |
| **Execução Agrícola** | `OperacaoExecucao` | `operador_id` (Pessoa) | `created_by` implícito | `status` manual | Balança / Sensor |
| **Caderno de Campo** | `CadernoCampoEntrada`| `executado_por_pessoa_id` | `usuario_id` (Sessão) | `status_evento` | PWA Offline |
| **EPI Entrega** | `EPIEntrega` | `colaborador_id` (RH) | `created_by` implícito | N/A | N/A |

## 3. Contrato de Sincronização Seletiva (Campo PWA)

O PWA não deve utilizar hardcode de códigos (ex: `IN ('AGRONOMO')`) diretamente no frontend.
A elegibilidade ocorrerá pelo metadado do catálogo `TipoRelacionamento`. 

**Regra de Elegibilidade:**
Uma `Pessoa` é sincronizada se possuir um `PessoaRelacionamento` que cumpra *todas* as condições:
1. `ativo_ate` nulo ou no futuro (Vigente).
2. Vinculado a uma `unidade_produtiva_id` que o usuário logado possui acesso **OU** `unidade_produtiva_id IS NULL` (Tenant-Wide).
3. (Opcional Futuro) O `TipoRelacionamento` possuir `sistema=True` ou um metadado classificatório que indique perfil operacional. Na Fase 2, todas as Pessoas ativas nas fazendas do usuário serão enviadas (filtro puramente territorial).

**Payload Mínimo do Offline (`colaboradores` -> `pessoas_operacionais`):**
O PWA passará a receber:
- `id` (`pessoa_id`)
- `nome` (`nome_exibicao`)
- `cpf` (Excluído. Substituído por `cargo/papel` da tabela pivô para minimização).
- `unidade_produtiva_id` (Para filtro no dropdown).
- **Sem Documentos. Sem PII financeiro.**

## 4. Contrato de Transição Pessoa × ColaboradorRH

O AgroSaaS reconhece que `ColaboradorRH` atua como um wrapper especializado para processar horas trabalhadas, diárias e integração com contabilidade, não como identidade central.

- **Legado:** Cadastros antigos mantêm seu funcionamento inalterado nas áreas de Folha/Custos, independentemente de possuírem `pessoa_id`.
- **Novos Registros:** A criação de um novo `ColaboradorRH` na API será uma operação atômica em transação (não event-driven) que irá instanciar a `Pessoa` base e, em seguida, o `ColaboradorRH`.
- **EPIEntrega:** Continua consumindo `ColaboradorRH`, sem migração no piloto, garantindo estabilidade do módulo jurídico/SST.

## 5. Eventos de Domínio

Os eventos ligados ao ciclo de Pessoas não serão implementados nesta Fase 0 ou no Piloto, uma vez que o sync do PWA ocorre via Polling nativo (`pull.ts`) na inicialização/online, não exigindo Outbox para *push* em tempo real. Eventos como `PessoaAnonimizada` ficam programados para a RC (Release Candidate), quando CRM e módulos legados necessitarão de reatividade à LGPD.

---
**Critérios para Inicialização das PRs (Pull Requests):**
A Fase 1 (alteração do schema do Caderno de Campo) pode ser iniciada imediatamente, focada unicamente na injeção de `executado_por_pessoa_id` em `caderno_campo_entradas` e sua exposição no endpoint de sync.
