# MATERIAL-REQUISITION-FLOW-01C — Fundação de domínio

## 1. Resumo executivo

O 01C implementa a fundação estrutural aprovada no desenho canônico 01B, sem fazer cutover do fluxo legado. Foram adicionados:

- enums canônicos para natureza do item, fatos por item, responsabilidade e classificação legada;
- origem operacional estruturada e validação tenant-safe;
- diário append-only `RequisicaoItemEvento`;
- versionamento monotônico no agregado `RequisicaoMaterial`;
- idempotência por `tenant_id + client_operation_id`;
- vínculo tenant-safe entre `ReservaEstoque` e `ItemRequisicao`;
- histórico de responsabilidade/delegação;
- referência opcional do evento operacional no ledger `EstoqueMovimento`;
- constraints, RLS, trigger append-only e migration incremental;
- testes direcionados da fundação.

Não foram implementados picking, entrega canônica, Campo offline, consumo/devolução completos, CostAllocation por consumo, DRE ou cutover dos endpoints atuais.

Veredicto: **GO COM RESSALVAS** para a fundação 01C. A implementação não autoriza iniciar 01D em produção: a validação online da migration ainda depende de ambiente de banco disponível e o relacionamento seguro `User ↔ Pessoa/Operador` continua sem uma relação canônica comprovada para autorizar recebimento por responsável/delegado.

## 2. Decisões implementadas

As decisões D01–D06 foram aplicadas conforme o 01B:

- o recebedor futuro será o responsável operacional ou delegado previamente autorizado;
- encerramento com requisição não conciliada continua fora desta fase;
- perda, dano e extravio permanecem fatos distintos de consumo;
- `usuario_id` identifica a identidade autenticada e `pessoa_operacional_id` identifica a pessoa operacional, sem cadastro paralelo;
- ferramenta de baixo valor pode ser representada como `RETORNAVEL`, por quantidade;
- dados legados não geram recebimento, consumo, custo ou movimento físico por inferência.

## 3. Arquitetura herdada do 01A/01B

O fluxo atual possuía `RequisicaoMaterial`, `ItemRequisicao`, `RequisicaoConfirmacao`, `ReservaEstoque` e `EstoqueMovimento`, mas não possuía diário de fatos por item, origem operacional completa, vínculo reserva-item, versionamento ou idempotência canônica. O 01C cria esses contratos sem substituir os comandos legados.

O caminho econômico oficial permanece:

```text
OperacaoAgricola → OperacaoExecucao → CostAllocation → DRE/Dashboard
```

O 01C não altera a quantidade usada por CostAllocation.

## 4. Arquivos alterados e criados

### Domínio e serviço

- `services/api/operacional/domain/requisicao_material.py`
- `services/api/operacional/services/requisicao_fundacao_service.py`
- `services/api/operacional/models/estoque.py`
- `services/api/operacional/schemas/estoque.py`
- `services/api/operacional/services/estoque_service.py`

### Relacionamentos tenant-safe

- `services/api/agricola/safras/models.py`
- `services/api/agricola/tarefas/models.py`
- `services/api/agricola/planejamento_operacional/models.py`
- `services/api/agricola/operacoes/models.py`
- `services/api/core/cadastros/pessoas/models.py`

Esses modelos receberam constraints `(tenant_id, id)` para permitir FKs compostas sem alterar seus identificadores.

`operacional/models/estoque.py` também registra explicitamente os módulos-pai antes da configuração antecipada dos mappers. Isso evita falha de ordem de importação quando o app configura Produto antes de carregar todo o catálogo de modelos.

### Banco e testes

- `services/api/migrations/versions/20260924_material_requisition_01c.py`
- `services/api/tests/unit/operacional/test_requisicao_fundacao_01c.py`
- `services/api/tests/unit/operacional/test_requisicao_fundacao_migration_static.py`

## 5. Contrato canônico de enums

Em `operacional/domain/requisicao_material.py`:

- `NaturezaItem`: `CONSUMIVEL`, `RETORNAVEL`;
- `TipoRequisicaoItemEvento`: `SEPARACAO`, `ENTREGA`, `RECEBIMENTO`, `RECUSA`, `CONSUMO`, `DEVOLUCAO`, `PERDA`, `DANO`, `EXTRAVIO`, `AJUSTE_AUTORIZADO`;
- `CompatibilidadeLegado`: `LEGACY_OPEN`, `LEGACY_DELIVERED`, `LEGACY_RETURNED`;
- `PapelResponsabilidade`: `RESPONSAVEL`, `DELEGADO`.

Os valores também são protegidos por `CHECK CONSTRAINT` no banco.

## 6. Origem operacional estruturada

`RequisicaoMaterial` passou a suportar, quando conhecidos:

- `safra_id`;
- `safra_tarefa_id`;
- `plano_operacional_tarefa_id`;
- `operacao_agricola_id`;
- `responsavel_pessoa_id`.

`origem_tipo`/`origem_id` foram preservados para legado e integrações genéricas. Não são a única origem quando a operação estruturada é conhecida.

`RequisicaoFundacaoService.validar_origem` verifica existência no tenant e consistência entre safra, tarefa, plano, operação e pessoa. A geração automática existente continua criando uma requisição por operação e agora propaga safra, tarefa e responsável da operação. A geração de requisição não foi reescrita e não houve nova constraint de unicidade que pudesse impedir requisições complementares legítimas.

A fase/tarefa de planejamento continua derivada da origem canônica da operação quando essa origem existe; `OperacaoExecucao` não foi colocado no cabeçalho da requisição.

## 7. `RequisicaoItemEvento`

Foi criada a tabela `estoque_requisicao_item_eventos`, com:

- tenant, requisição e item;
- tipo, quantidade e unidade;
- snapshots de produto, lote e depósito;
- operação e execução opcional;
- usuário autenticado, pessoa operacional e dispositivo;
- timestamps do servidor e do dispositivo;
- motivo, correlação e causação;
- `client_operation_id`, versão e `provenance`.

O evento é um diário operacional por item, não um segundo ledger físico. A migration instala trigger que rejeita `UPDATE` e `DELETE`; correções futuras deverão usar evento compensatório ou `AJUSTE_AUTORIZADO`.

As FKs compostas obrigatórias são tenant-safe. Para referências opcionais compostas foi usado `NO ACTION`, preservando o `tenant_id`; `SET NULL` em uma FK composta poderia nulificar também a coluna de tenant e quebrar o isolamento.

## 8. Versionamento

Foi escolhida uma única versão monotônica no agregado `RequisicaoMaterial.version`, iniciada em 1. Não foi criada uma segunda versão independente no item.

Ao registrar um evento canônico, o serviço bloqueia requisição e item, valida a versão esperada quando fornecida, grava o evento com a próxima versão e atualiza o agregado na mesma transação.

O contrato aceita `versao_requisicao_esperada`. Versão obsoleta é rejeitada com `BusinessRuleError`. O campo persistido no diário é `versao_requisicao`, isto é, a versão resultante daquele fato.

## 9. Idempotência e concorrência

O diário possui unique constraint:

```text
(tenant_id, client_operation_id)
```

O mesmo comando retorna o evento existente quando o payload essencial coincide. Reutilização da chave para item, tipo, quantidade ou unidade diferentes é rejeitada.

O serviço faz uma segunda leitura da chave depois do lock do agregado, cobrindo retry concorrente após o primeiro comando liberar a transação. A constraint de banco permanece como última proteção. Comando sem `client_operation_id` não é idempotente; a obrigatoriedade para Campo offline fica para a fase 01E.

`RequisicaoConfirmacao` também recebeu `device_id`, `client_operation_id`, versão, resultado e correlação, mantendo o histórico existente e preparando ACK futuro.

## 10. Natureza dos itens

`ItemRequisicao.natureza_item` é um snapshot histórico e aceita somente `CONSUMIVEL`, `RETORNAVEL` ou `NULL`.

- Insumos criados pela geração automática atual são classificados como `CONSUMIVEL`, pois vêm de `InsumoOperacao`.
- Criação manual pode informar a natureza.
- Dados históricos e ferramentas existentes não são reclassificados automaticamente.
- `NULL` significa classificação desconhecida/legada, não consumo implícito.

Máquinas e equipamentos patrimonializados continuam fora deste fluxo.

## 11. Reserva

`ReservaEstoque.item_requisicao_id` foi adicionado como referência tenant-safe a `ItemRequisicao`, preservando os vínculos já existentes com planejamento/referência.

A migration cria índice e FK, mas não altera reserva, consumo parcial, liberação ou cancelamento. Esses comportamentos pertencem à 01D e não foram antecipados.

## 12. Responsabilidade e delegação

Foi criada `RequisicaoResponsabilidadeHistorico`, com:

- requisição;
- `usuario_id` autenticado;
- `pessoa_operacional_id` opcional e tenant-safe;
- papel `RESPONSAVEL` ou `DELEGADO`;
- concedente;
- vigência e revogação temporal;
- motivo.

Não foi criado relacionamento paralelo `Usuario ↔ Pessoa`. A auditoria do código não comprovou uma FK canônica segura entre essas identidades. Portanto, a tabela registra evidência contextual, mas a autorização efetiva de recebimento ainda precisa ser fechada no 01D/01E antes de permitir que um terceiro receba.

## 13. Ledger de estoque

`EstoqueMovimento` recebeu `requisicao_item_evento_id` opcional e FK tenant-safe. Isso prepara a relação:

```text
evento operacional → movimento físico
```

Nenhum movimento histórico foi associado por inferência. O 01C não gera saída, entrada, reserva física, consumo ou devolução. O ledger permanece append-only conforme arquitetura existente.

Em particular, o evento de consumo futuro não deverá gerar segunda baixa quando a saída física já tiver ocorrido na entrega.

## 14. Compatibilidade legada

A migration adiciona `RequisicaoMaterial.compatibilidade_legado` e classifica somente o cabeçalho existente:

- `LEGACY_RETURNED`: há devolução comprovada;
- `LEGACY_DELIVERED`: status entregue ou quantidade entregue comprovada;
- `LEGACY_OPEN`: status aberto conhecido;
- `NULL`: não foi possível classificar com segurança.

O backfill de `ItemRequisicao.tenant_id` copia apenas o tenant da requisição correspondente, por necessidade estrutural. Não cria evento, movimento, recebimento, consumo, lote, responsável, custo ou DRE.

`ENTREGUE` legado comprova no máximo entrega/saída conforme os dados atuais. Não é convertido automaticamente em consumo. Devolução legada é preservada como informação legada e não permite inferir recebimento item a item nem consumo residual.

## 15. Domain Events / Outbox

O serviço de fundação emite, na mesma transação do evento, somente:

```text
operational.material_request.item_event_recorded
```

O evento referencia `RequisicaoItemEvento` e carrega tipo, requisição, item e chave idempotente. Não foram criados dez eventos de lifecycle sem consumidor concreto.

O Outbox não torna eventual a atualização física do estoque; no 01C não há atualização física associada ao diário. A integração física deverá ocorrer transacionalmente nas fases de entrega/devolução.

## 16. Multi-tenancy e RLS

As novas tabelas têm:

- `tenant_id` obrigatório;
- FK para tenant;
- FKs compostas para requisição, item, operação, execução e pessoa quando aplicável;
- índices tenant-scoped;
- RLS habilitado e forçado;
- políticas de leitura, inserção, atualização e exclusão por `app.current_tenant_id`.

O trigger append-only protege o diário mesmo contra mutações normais de aplicação. A validação de serviço também filtra explicitamente requisição, item, produto, depósito, lote, execução, pessoa e dispositivo pelo tenant. Usuário autenticado permanece identidade global; isso não substitui a futura autorização por pessoa/responsabilidade.

## 17. Migration

Migration criada:

```text
services/api/migrations/versions/20260924_material_requisition_01c.py
revision: 20260924_material_requisition_01c
down_revision: 20260915_merge_documentos_fiscais
```

Ela é incremental, não edita migration histórica, não remove colunas e contém downgrade reversível para as estruturas adicionadas.

`alembic heads` confirmou `20260924_material_requisition_01c` como head. A geração offline `alembic upgrade head --sql` não chegou ao 01C porque uma migration histórica anterior (`8c2e891d6ba9_caderno_campo.py`) usa `sa.inspect` incompatível com a conexão mock do modo offline. `alembic check` também não pôde validar o banco: a conexão async ao PostgreSQL foi bloqueada pelo ambiente (`PermissionError: Operation not permitted`). Nenhuma migration foi executada em produção ou neste turno.

## 18. Testes e validações

Passaram:

- 11 testes direcionados da fundação 01C;
- schema de quantidade/tipo/natureza;
- retry idempotente e rejeição de payload incompatível;
- versão obsoleta;
- estrutura de constraints e migration;
- compilação Python dos arquivos alterados;
- lint direcionado (`E9`, `F401`, `F821`, `E501`) dos arquivos novos;
- lint estrutural (`E9`, `F821`) dos modelos e serviços alterados;
- carregamento dos modelos sem erro de registro;
- `git diff --check`.

No conjunto diretamente relacionado executado, houve `141 passed`, `1 skipped` e `5 failed`. As falhas não foram introduzidas pelos arquivos do 01C e ficaram documentadas como pendências de ambiente/base existente:

- fixture de teste financeiro cria `SimpleNamespace` sem `solicitante_id` para um caminho legado;
- guardrail legado encontra `MovimentacaoEstoque` em `fix_imports.py`;
- guardrails globais existentes encontram FKs CASCADE/índices ausentes em tabelas fora do escopo 01C.

O teste existente `test_registry_is_idempotent_and_reproducible` também mantém a expectativa fixa de 373 tabelas. Com as duas tabelas intencionais do 01C, o registry passou a registrar 375; o teste não foi alterado, conforme a regra desta fase de não modificar testes existentes. A importação completa do app, entretanto, foi validada com `registered=375` e sem erro de mapper.

Essas falhas impedem declarar a suíte global verde, mas não invalidaram os 11 testes da fundação.

## 19. Impacto sobre comportamento atual

Não foram alterados:

- endpoints atuais de entrega, confirmação e devolução;
- telas Web;
- Campo/PWA;
- Dexie e sincronização;
- estados legados;
- baixa física do estoque;
- consumo/devolução operacional;
- CostAllocation, DRE ou Dashboard.

O fluxo legado continua sendo o caminho runtime. A validação de origem foi adicionada à criação manual e a geração automática passa a preencher contexto estruturado; não houve cutover para o serviço de eventos.

## 20. Riscos e pendências

### HIGH/BLOCKING para 01D

- O banco real ainda precisa executar upgrade/downgrade em ambiente seguro. A validação estrutural não substitui essa prova.
- O relacionamento canônico `User ↔ Pessoa/Operador` não foi comprovado. Sem essa decisão técnica, não é seguro autorizar recebimento por responsável/delegado no Campo.
- O comportamento operacional de `ReservaEstoque` ainda não mudou; 01D deverá definir reserva, picking, entrega e liberação sem duplicidade.

### MEDIUM

- A idempotência de confirmações está preparada, mas o protocolo ACK/retry offline pertence à 01E.
- Os snapshots de lote e depósito são validados no serviço de eventos; movimentos físicos e reconciliação por quantidade ainda não foram implementados.
- Produtos globais (`tenant_id NULL`) continuam permitidos conforme catálogo atual; produtos de outro tenant são rejeitados.

### OBSERVAÇÃO

- A classificação legada `NULL` é deliberada quando não há evidência. Não deve ser transformada em consumo ou recebimento sem fonte documental.

## 21. Prontidão para 01D

A fundação de banco, contrato e serviço está suficientemente definida para continuar o desenho incremental. Porém, 01D não deve ser promovida para execução contra dados reais enquanto não forem concluídos:

1. upgrade/downgrade em banco de teste real;
2. correção ou decisão formal sobre a migration histórica que impede o modo offline;
3. decisão segura sobre `User ↔ Pessoa/Operador`;
4. testes de integração tenant/RLS sobre as novas tabelas;
5. plano de autorização de responsável/delegado.

## 22. Veredicto

```text
MATERIAL-REQUISITION-FLOW-01C
STATUS: GO COM RESSALVAS
PRÓXIMA FASE RECOMENDADA: 01D — Reserva, picking e entrega canônica,
somente após validar a migration no banco e resolver o vínculo User × Pessoa.
```

O 01C não possui cutover prematuro nem inventa consumo histórico. A ressalva é material: sem identidade operacional segura e sem upgrade real validado, não é seguro autorizar a entrega canônica ponta a ponta.
