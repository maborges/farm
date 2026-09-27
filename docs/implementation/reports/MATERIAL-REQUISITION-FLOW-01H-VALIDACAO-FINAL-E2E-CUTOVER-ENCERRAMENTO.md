# MATERIAL-REQUISITION-FLOW-01H — Validação Final E2E, Cutover e Encerramento

Data: 2026-09-26  
Ambiente: PostgreSQL real de desenvolvimento `farms/farms`; nenhuma prova utilizou produção.  
Head Alembic: `20260926_material_requisition_01g`.

## 1. Resumo executivo

O fluxo canônico foi validado ponta a ponta e está seguro para piloto controlado.

Passaram no PostgreSQL real:

- reserva, picking, entrega e bloqueio do legado: 01D2, 1 passed;
- recebimento sem movimento físico: 01E, 1 passed;
- posse, consumo, devolução, perda/dano/extravio e concorrência: 01F, 1 passed;
- retornável, rollback provocado e fechamento: 01F1, 3 passed;
- CostAllocation, DRE, Dashboard e idempotência econômica: 01G, 2 passed.

Durante esta fase foram corrigidos dois bloqueios de cutover encontrados na auditoria:

1. entrega legada agora é rejeitada quando já existe reserva canônica, mesmo sem picking/evento;
2. o FIFO legado da operação agora é rejeitado quando existe reserva, picking ou evento canônico.

Não restou BLOCKING/HIGH funcional. Permanecem ressalvas MEDIUM: PERDA/DANO/EXTRAVIO ainda não possuem classificação econômica própria e há dívida de lint backend nos arquivos do fluxo e em áreas legadas.

## 2. Arquitetura final

| Fato | Escritor canônico | Efeito físico | Efeito econômico |
|---|---|---:|---|
| RESERVA | `RequisicaoCanonicaService` | zero | zero |
| PICKING | `RequisicaoCanonicaService` | zero | zero |
| ENTREGA | `RequisicaoCanonicaService` | uma SAÍDA | zero custo definitivo |
| RECEBIMENTO | `RequisicaoRecebimentoService` | zero | zero |
| CONSUMO | `RequisicaoPosseService` | zero | `CostAllocation` |
| DEVOLUÇÃO | `RequisicaoPosseService` | uma ENTRADA | zero novo custo |
| PERDA/DANO/EXTRAVIO | `RequisicaoPosseService` | zero | classificação própria pendente |

O evento operacional é a fonte de verdade dos fatos; `EstoqueMovimento` representa somente os movimentos físicos; `CostAllocation` representa somente o consumo econômico canônico.

## 3. Cenário E2E principal

| Etapa | Quantidade | Resultado |
|---|---:|---|
| aprovado/reservado/separado | 100 kg | PASS |
| entregue | 100 kg | uma saída física |
| recebido | 100 kg | sem movimento físico |
| consumido | 80 kg | fato de consumo |
| devolvido | 20 kg | uma entrada física |
| em posse | 0 kg | PASS |
| status do item/requisição | conciliado/conciliada | PASS |

O cenário econômico usou R$ 5,00/kg: `80 × 5 = R$ 400,00`.

## 4. Estoque físico

Certificado:

- ENTREGA: exatamente uma `SAIDA` lógica de 100 kg;
- DEVOLUÇÃO: exatamente uma `ENTRADA` lógica de 20 kg;
- RECEBIMENTO: zero movimento;
- CONSUMO: zero movimento;
- PERDA/DANO/EXTRAVIO: zero movimento;
- CostAllocation: zero movimento.

Efeito líquido: `-100 + 20 = -80 kg`. Não há dupla baixa nem segunda entrada indevida.

## 5. Posse e conciliação

O consumo e a devolução somente operam sobre posse recebida, com lock transacional, versão e `client_operation_id`. A posse não ficou negativa em nenhuma prova.

O cenário divergente `ENTREGUE=100`, `RECEBIDO=92`, divergência de 8:

- destinou somente os 92 recebidos;
- não inventou consumo para os 8;
- não gerou custo para os 8;
- permaneceu não conciliado e bloqueou o fechamento mesmo com `em_posse=0`.

O cenário retornável `3 recebido → 2 devolvido + 1 danificado` resultou em consumo zero, uma entrada de 2, dano separado e posse zero. RETORNAVEL não pode ser consumido.

No cenário de perda `20 recebido → 17 consumido + 2 perdido + 1 devolvido`, a posse final foi zero e a apropriação econômica considerou somente 17. DANO e EXTRAVIO permaneceram fatos distintos, sem conversão econômica em consumo.

## 6. Campo offline

O Campo usa Dexie para requisições, itens e operações pendentes. Recebimento, consumo, devolução, perda, dano e extravio entram na `sync_queue`; o worker faz retry, ACK, conflito e atualização da projeção local.

Evidências executadas:

- 5 arquivos Vitest, 24 testes: PASS;
- typecheck: PASS;
- lint Campo: PASS;
- build Campo/PWA: PASS;
- `client_operation_id`, tenant, usuário, device, timestamp e token são enviados no comando;
- conflito retorna projeção atualizada e não confirma silenciosamente uma versão obsoleta.

Não foi simulada indisponibilidade física de rede; a transição offline/sync foi coberta pelo mecanismo certificado e pelos testes de fila/ACK/retry/conflito.

## 7. Idempotência e concorrência

Passaram:

- retry de reserva, picking, entrega, recebimento, consumo e devolução;
- duas entregas concorrentes para a mesma posse;
- duas destinações concorrentes sobre a mesma posse;
- dois workers econômicos para o mesmo consumo;
- rollback provocado antes do commit da devolução.

As constraints tenant-safe e a unicidade por evento impedem duplicação física, operacional e econômica.

## 8. Autorização

PASS para a matriz final:

- responsável direto: aceita;
- delegado vigente: aceita;
- delegado revogado: rejeitado;
- `PessoaUsuario` inexistente/inativo: rejeitado;
- usuário de outro tenant: rejeitado;
- device/PIN sem autorização operacional: rejeitado.

A identidade é resolvida no backend por tenant, usuário, pessoa e vigência; campos de identidade enviados pelo cliente não substituem o token/device autenticado.

## 9. Isolamento tenant

PASS nas fronteiras de requisição, item, depósito, lote, entrega, recebimento, `OperacaoExecucao`, consumo, devolução e `CostAllocation`.

As consultas e comandos filtram `tenant_id`; as relações críticas usam FKs compostas tenant-safe; o cenário cross-tenant foi rejeitado sem efeito físico ou econômico.

## 10. Apropriação econômica

O único fato econômico é `RequisicaoItemEvento.tipo_evento=CONSUMO`.

No cenário principal:

- entrega: 0 allocations;
- recebimento: 0 allocations;
- consumo de 80 kg: 1 `CostAllocation`, R$ 400,00;
- devolução de 20 kg: 0 nova allocation;
- retry/concorrência: 0 duplicação.

O custo unitário vem do `EstoqueMovimento SAIDA` exato da entrega, preservando lote e origem. Não há FIFO econômico novo no consumo.

## 11. DRE e Dashboard

PASS. DRE e Dashboard usam `CostAllocation` como fonte canônica para o custo realizado da operação. O cenário real refletiu R$ 400,00 e não somou entrega, recebimento, devolução ou agregado legado.

## 12. PERDA/DANO/EXTRAVIO

Decisão formal: **B — BACKLOG CONTROLADO**.

Justificativa técnica:

- os três fatos são persistidos e auditáveis separadamente;
- não são classificados como CONSUMO;
- não geram `CostAllocation source=REQUISICAO_CONSUMO`;
- não alteram saldo físico nem criam entrada/saída indevida;
- não comprometem posse, conciliação ou rastreabilidade;
- a ausência atual é de categoria/conta econômica própria, não de integridade operacional.

Backlog futuro recomendado: `MATERIAL-REQUISITION-FLOW-01G1`, exclusivamente para decidir categoria, conta e impacto econômico de PERDA/DANO/EXTRAVIO. A implementação futura não deve converter esses fatos retroativamente em consumo.

## 13. Legado e cutover

| Escritor/caminho | Classificação | Regra final |
|---|---|---|
| reserva/picking/entrega canônicos | CANÔNICO | fonte oficial do novo fluxo |
| recebimento/posse/consumo/devolução Campo | CANÔNICO | fila offline + endpoint canônico |
| `CostAllocation` do consumo | CANÔNICO | subscriber somente de consumo |
| entrega/retirada Web e Campo antigas | LEGADO NECESSÁRIO | permitido somente antes de marcador canônico |
| FIFO antigo de operação | LEGADO NECESSÁRIO | permitido somente fora de requisição canônica |
| registros classificados `LEGACY_*` | LEGADO SOMENTE HISTÓRICO / NECESSÁRIO | não entram no fluxo canônico |
| caminho legado após reserva/picking/evento canônico | LEGADO BLOQUEADO | rejeição sem movimento |
| escritor concorrente no caminho canônico | nenhum encontrado | PASS após os dois guardrails de 01H |

Critério estrutural: uma requisição pertence ao fluxo canônico quando possui reserva estruturada por `item_requisicao_id` ou qualquer evento canônico tenant-safe. A operação agrícola aplica a mesma regra para bloquear FIFO. A classificação `compatibilidade_legado` impede que registros históricos/legados sejam promovidos silenciosamente ao fluxo novo. Data isolada não é critério de cutover.

## 14. Histórico

PASS. A migration 01C classifica compatibilidade legada sem recalcular consumo; a 01G é estrutural, sem backfill econômico, CostAllocation retroativo, recálculo de DRE ou reclassificação de estoque histórico.

## 15. Outbox e observabilidade

PASS. Os eventos canônicos carregam `event_id`, `correlation_id`, `causation_id`, tenant, usuário, device e `client_operation_id`. Reserva, picking, entrega, recebimento e destinação enfileiram eventos transacionais; o subscriber econômico escuta somente `operational.material_request.consumo`.

Retry do subscriber é eventual e recuperável; a transação operacional não depende de entrega síncrona da Outbox. As provas de rollback não deixaram evento órfão, movimento órfão ou chave idempotente fantasma. Os vínculos requisição → entrega → recebimento → consumo → CostAllocation são investigáveis por IDs, eventos, logs e Outbox.

## 16. Migrations

PASS:

- `alembic heads`: um único head;
- `alembic current`: `20260926_material_requisition_01g (head)`;
- downgrade `01G → 01E`: PASS;
- upgrade `01E → 01G`: PASS;
- não foram alteradas migrations históricas.

## 17. Regressões e qualidade

| Verificação | Resultado |
|---|---|
| unitários de requisição + registry | 34 passed |
| regressões Campo/Outbox/economia direcionadas | 68 passed, 1 warning |
| PostgreSQL real 01D2 | 1 passed |
| PostgreSQL real 01E | 1 passed |
| PostgreSQL real 01F | 1 passed |
| PostgreSQL real 01F1 | 3 passed |
| PostgreSQL real 01G | 2 passed, 1 warning |
| Campo Vitest | 24 passed |
| Campo typecheck | PASS |
| Campo lint | PASS |
| Campo build | PASS |
| app import / py_compile | PASS |
| `git diff --check` | PASS |

O Ruff backend direcionado encontrou 305 achados de estilo/import/linhas longas/UP017/B904, concentrados nos services/testes do fluxo 01C–01F e em áreas legadas. São dívida de qualidade MEDIUM, sem falha funcional nas provas, e não foram mascarados nem tratados como defeito de infraestrutura. O warning Pydantic e o aviso de Browserslist também não alteraram o resultado funcional.

As primeiras tentativas de testes reais foram bloqueadas pelo sandbox de rede e por `ALLOW_ORIGINS` não exportado no `.env.local`; após execução autorizada e override somente no processo, todas as provas PostgreSQL passaram. Isso foi classificado como infraestrutura/configuração do runner.

## 18. Riscos

- MEDIUM: classificação econômica própria de PERDA/DANO/EXTRAVIO pendente em 01G1.
- MEDIUM: saneamento de Ruff backend pendente.
- LOW: CostAllocation é eventual após Outbox; retry é obrigatório no worker.
- LOW: ambiente de desenvolvimento pode sofrer timeout transitório na abertura de conexões.

## 19. Backlog

1. `MATERIAL-REQUISITION-FLOW-01G1`: classificação econômica própria de perda, dano e extravio.
2. Limpeza de Ruff nos services/testes do fluxo, sem alterar comportamento operacional certificado.
3. Manter monitoramento de Outbox pendente/orfã no piloto.

## 20. Perguntas obrigatórias

**A.** Existe algum ponto em que o mesmo material sofre duas saídas físicas? **Não.** Entrega é a única saída; legado é bloqueado após reserva/evento canônico.

**B.** Existe alguma segunda entrada física indevida? **Não.** Devolução idempotente cria exatamente uma entrada.

**C.** Recebimento altera estoque? **Não.** Registra custódia/posse.

**D.** Consumo altera estoque? **Não.** Registra fato e apropriação econômica.

**E.** Devolução gera exatamente uma entrada? **Sim.**

**F.** A posse pode ficar negativa? **Não.** Locks, saldo calculado e guardrails rejeitam excesso.

**G.** RETORNAVEL pode ser consumido? **Não.** O comando é rejeitado sem efeito.

**H.** Divergência pode desaparecer silenciosamente? **Não.** 8 kg divergentes mantêm a requisição não conciliada e bloqueiam fechamento.

**I.** Consumo econômico usa quantidade realmente consumida? **Sim.** 80 kg geram R$ 400,00.

**J.** Entrega ou recebimento geram CostAllocation? **Não.**

**K.** Pode existir CostAllocation duplicado para o mesmo evento? **Não.** Unicidade tenant/evento e retry concorrente foram certificados.

**L.** Existe escritor legado concorrendo com o canônico? **Não no mesmo fato após o marcador canônico.** O cutover bloqueia entrega, retirada e FIFO legados.

**M.** DRE e Dashboard refletem o consumo real sem dupla contagem? **Sim.** R$ 400,00.

**N.** Histórico foi alterado/recalculado? **Não.**

**O.** Campo offline preserva autoria e idempotência? **Sim.** Tenant, usuário, device, `client_operation_id`, ACK, retry e conflito são preservados.

**P.** Tenant isolation está preservado ponta a ponta? **Sim.**

**Q.** Operação pode fechar com material pendente? **Não.** Posse, divergência ou recusa pendente bloqueiam.

**R.** Qual é a decisão final sobre PERDA/DANO/EXTRAVIO? **BACKLOG CONTROLADO**, com fatos operacionais preservados e sem CostAllocation de consumo.

**S.** Existe algum BLOCKING/HIGH restante? **Não.**

**T.** O fluxo está seguro para piloto controlado? **Sim, com ressalvas e monitoramento do backlog 01G1/Outbox.**

## 21. Veredicto final

```text
MATERIAL-REQUISITION-FLOW-01H
STATUS: GO COM RESSALVAS

E2E PRINCIPAL:
PASS

ESTOQUE FÍSICO:
PASS

POSSE/CONCILIAÇÃO:
PASS

CAMPO OFFLINE:
PASS

IDEMPOTÊNCIA/CONCORRÊNCIA:
PASS

ISOLAMENTO TENANT:
PASS

APROPRIAÇÃO ECONÔMICA:
PASS

DRE/DASHBOARD:
PASS

CUTOVER LEGADO:
PASS

PERDA/DANO/EXTRAVIO:
BACKLOG CONTROLADO

BLOCKING/HIGH ABERTOS:
0

SEGURO PARA PILOTO CONTROLADO:
SIM

MATERIAL-REQUISITION-FLOW
STATUS DO ÉPICO:
CONCLUÍDO COM RESSALVAS
```
