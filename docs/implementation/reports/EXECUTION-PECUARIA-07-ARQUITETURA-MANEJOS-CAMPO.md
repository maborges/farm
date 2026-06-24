# EXECUTION-PECUARIA-07 — ARQUITETURA DE MANEJOS PECUÁRIOS INTEGRADOS AO CAMPO

## 1. Inventário Atual

* **Pecuária:** `Animal`, `LoteAnimal`, `EventoAnimal` (histórico inalterável) e `ManejoLote` já estão criados. Há suporte robusto a cálculos (ex: GMD em pesagens) atrelado diretamente ao `Animal`.
* **Campo:** `TarefaCampo` já suporta o `module="pecuaria"`. Trabalha perfeitamente em modo *offline-first* gerando `dados` dinâmicos (JSONB), capturando o operador, dispositivo, geolocalização e controle de conflitos via timestamps de sincronização.
* **Operacional:** Não possui "Ordens de Serviço" aplicáveis ao mundo biológico (OS atual do sistema é estritamente de Oficina/Manutenção de Máquinas).

---

## 2. Decisão de Domínio

1. **Deve existir uma entidade própria chamada `ManejoPecuarioProgramado`?**  
   **Não.** O `ManejoLote` (já existente) atuará perfeitamente como o agrupador de *Planejamento* (ex: "Protocolo de Vacinação Novilhas"), enquanto a `TarefaCampo` atua como o envelope de *Execução Física*.
2. **`TarefaCampo` já é suficiente como entidade de planejamento?**  
   **Não.** A `TarefaCampo` é a ponta da lança no app (direcionada a um peão, num tablet). Um planejamento de manejo de 5.000 cabeças pode despachar 5 `TarefasCampo` para 5 peões diferentes trabalhando em currais simultâneos.
3. **`ManejoLote` deve continuar existindo?**  
   **Sim.** Sendo o pacote gerencial de backoffice.
4. **`EventoAnimal` deve sempre ser append-only?**  
   **Absolutamente sim.** Ele é o ledger inegociável de auditoria e rastreabilidade individual.
5. **Eventos de lote devem gerar eventos individuais?**  
   **Sim,** sempre que o rebanho for *Detalhado* (controle por brincos).
6. **Como lidar com lotes agregados vs. lotes detalhados?**  
   * **Agregado (Controle de Cabeças):** A tarefa altera o saldo zootécnico (estoque de cabeças) do Lote e consome insumos globalmente. Não gera `EventoAnimal` pois não há identificador individual.
   * **Detalhado (Controle Individual):** O payload do campo carrega a matriz de `animal_id`. Gera `EventoAnimal` rastreável para cada brinco individual e baixa o estoque proporcionalmente.

---

## 3. Fluxo Oficial Recomendado

### Fluxo 1 — Manejo Planejado
1. **Planejamento:** O Gestor no ERP cria um `ManejoLote` (ex: "Pesagem de Desmame").
2. **Despacho:** O Backend gera uma ou mais `TarefaCampo` (origem=`PROGRAMADA`, module=`pecuaria`, type=`PESAGEM`).
3. **Coleta:** O app Campo recebe a tarefa, o operador vai ao curral e lança N pesos sem internet. 
4. **Sincronização:** Quando com sinal, o tablet envia o status para `CONCLUIDA` e manda os dados `JSONB`.
5. **Materialização:** O `ManejoSyncService` lê os arrays do JSON, gera em *bulk* N instâncias de `EventoAnimal`, engatilhando os recálculos de peso atual e GMD na tabela `Animal`. Os dados refletem no Dashboard em tempo real.

### Fluxo 2 — Manejo Espontâneo (Ad-Hoc)
1. O peão, rondando no pasto, vê um bezerro ferido. 
2. No app, abre "Nova Tarefa Pecuária" (origem=`MANUAL`, type=`MEDICACAO`).
3. Sincroniza com o ERP. O `ManejoSyncService` capta que a tarefa foi enviada sem planejamento-pai, mas processa a inserção do `EventoAnimal` na ficha do indivíduo de forma idêntica. Mantém auditoria total.

### Fluxo 3 — Manejo em Lote Agregado (Ex: Vacinação 300 cabeças)
1. A `TarefaCampo` aponta o `lote_id`, a `quantidade_cabecas` afetadas e a vacina.
2. Não há IDs de animais. O sistema abate do Almoxarifado o volume total ($300 \times dose$) e atualiza o custo da arroba base do Lote, mantendo o histórico de manejo anexado unicamente à tabela do Lote.

### Fluxo 4 — Manejo em Lote Detalhado (Ex: Pesagem Individual 120 Cab.)
1. A `TarefaCampo` retorna uma matriz contendo exatamente o mapeamento de 120 IDs animais com seus 120 respectivos pesos.
2. A materialização utiliza *Bulk Insert* (`session.add_all()`), reduzindo o Custo de I/O de N+1 queries. O GMD é processado on-the-fly de forma escalonada. 

---

## 4. Contratos JSONB Sugeridos (`TarefaCampo.dados`)

### 4.1 Pesagem (`type: "PESAGEM"`)
```json
{
  "lote_id": "uuid",
  "data_evento": "2026-06-23T10:00:00Z",
  "animais": [
    {
      "animal_id": "uuid",
      "numero_brinco": "1001",
      "peso_kg": 250.5,
      "observacao": "Bezerro refugo"
    }
  ]
}
```

### 4.2 Vacinação (`type: "VACINACAO"`)
```json
{
  "lote_id": "uuid",
  "produto_id": "uuid_vacina",
  "dose": 2.0,
  "unidade_medida": "ML",
  "via_aplicacao": "SUBCUTANEA",
  "data_evento": "2026-06-23T10:00:00Z",
  "cabecas_lote_agregado": null, 
  "animais_ids": ["uuid_animal_1", "uuid_animal_2"] 
}
```

### 4.3 Transferência de Lote (`type: "TRANSFERENCIA_LOTE"`)
```json
{
  "lote_origem_id": "uuid",
  "lote_destino_id": "uuid",
  "data_transferencia": "2026-06-23T10:00:00Z",
  "motivo": "Mudança para Terminação",
  "animais_ids": ["uuid_1", "uuid_2"]
}
```

---

## 5. Estratégia de Materialização (`EventoAnimal`)

* **`ManejoSyncService`:** Um serviço arquitetado em `pecuaria/services`, ativado de forma assíncrona (via job/fila ou hooks pós-commit do módulo Campo). 
* **O Processo:** Recebe a `TarefaCampo` concluída e processa o parsing e o Bulk Insert dos `EventoAnimal`. Desvincula a latência da requisição HTTP de sincronização do tablet do processamento da regra de negócio zootécnica pesada. 
* **Tolerância a Lotes Grandes (Ex: 1000 cabeças):** Dividido em chunks de processamento para poupar a memória do PostgreSQL.

---

## 6. Estratégia de Idempotência e Rastreabilidade

### Campos a serem criados no Ledger (`EventoAnimal`)
* `tarefa_campo_id` (UUID) - **Obrigatório**. Atesta a prova material da execução no campo.
* `operador_id` (UUID) - **Obrigatório**. Puxado automaticamente do executor da tarefa.

### Como garantir que um evento não se duplique? (Idempotência)
* Criar uma restrição `UNIQUE(animal_id, tarefa_campo_id, tipo)` na tabela `pec_eventos_animal`.
* Se o tablet por erro de rede reenviar a mesma tarefa concluída, o banco barra o *Insert* secundário de forma estrutural nativa sem requerer checks de código pesados.

### Campos delegados exclusivamente para `TarefaCampo`
* A fim de evitar poluição zootécnica, dados operacionais e de device (`dispositivo_id`, `latitude`, `longitude`, `client_created_at`) não precisam existir na Pecuária. A Pecuária sabe apenas a Biologia. O Campo sabe a Operação. O `tarefa_campo_id` faz a ponte.

---

## 7. Roadmap Técnico

**Fase A — Fundação Zootécnica (Base Backend)**
* Criar a migration inserindo `tarefa_campo_id` e `operador_id` em `EventoAnimal`.
* Implementar a constraint de Idempotência *Unique*.

**Fase B — Motor de Sincronização e Parse (Worker Backend)**
* Desenvolver `ManejoSyncService`.
* Definir parsers de leitura do JSON para materialização e bulk insert.
* Gatilhos de Integração com Estoque (para baixar vacinas e insumos automaticamente a partir da operação).

**Fase C — Planejamento no Backoffice (Frontend Web)**
* UI para criar `ManejoLote` com telas agendando pesagens ou vacinações para N animais ou lotes, disparando as tarefas para o serviço de retaguarda.

**Fase D — Execução no Front do Campo (Mobile / Offline)**
* Desenvolver componentes de forms reativos à propriedade `module=pecuaria` do módulo Campo.

---

## 8. Riscos e Mitigações

| Risco | Impacto | Mitigação |
| :--- | :--- | :--- |
| **Duplicação de Eventos** por falha de Sync (Re-try offline) | Alto (Peso e Custo dobrado) | Constraint nativa de BD `UNIQUE(animal_id, tarefa_campo_id, tipo)`. |
| **Baixa Incorreta de Estoque** | Severo (Ruptura Física) | Validar estoques e emitir notificação de *Tarefa Concluída Parcialmente com Exceção de Insumo* em vez de travar o GMD biológico. |
| **Performance N+1 em currais de 2000 cabeças** | Médio | *Bulk insert* estrito, proibição de salvar evento em laços `for` isolados. O parser deve carregar todos os dados pra ram e realizar apenas 1 commit relacional. |
| **Integridade de `lotes_agregados`** | Médio | Validar rigidamente se a Tarefa não envia IDs num lote agregado, ou vice e versa. |

---

## 9. Próxima Execução Recomendada

Sugerimos focar estritamente na **Fase A (Fundação Zootécnica)**: Ajustar a entidade `EventoAnimal` para comportar a integração `tarefa_campo_id` e a segurança `UNIQUE` de idempotência. Isso garantirá a infraestrutura antes de conectarmos o JSON e os Workers.
