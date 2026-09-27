# MATERIAL-REQUISITION-FLOW-01F1 — Certificação de Retornáveis, Atomicidade e Conciliação

Data: 2026-09-26  
Escopo: validação final do 01F, sem nova funcionalidade de negócio.  
Banco: PostgreSQL de desenvolvimento farms, schema farms; nunca produção.

## 1. Resumo executivo

As três lacunas de certificação do 01F foram executadas em PostgreSQL real:

1. retornável 3 recebido → 2 devolvido + 1 danificado;
2. rollback provocado durante devolução e reexecução posterior;
3. bloqueio de fechamento com posse/divergência e liberação após conciliação.

Todas passaram. O fluxo preserva a separação ENTREGA ≠ RECEBIMENTO ≠ CONSUMO.

O retornável não pode ser consumido, a devolução cria exatamente uma entrada física, dano não retorna automaticamente ao estoque, retry não duplica entrada, e uma operação com material pendente não fecha.

**Veredicto: GO. O 01G está autorizado.**

## 2. Ambiente

- PostgreSQL 16.15 em Ubuntu 24.04, ambiente de desenvolvimento.
- Banco/schema: farms/farms.
- Alembic: 20260925_material_requisition_01e (head).
- Runner: asyncpg via SQLAlchemy AsyncEngine, pool_size=2, max_overflow=0, pool_pre_ping=False, timeout de conexão de 30 segundos e search_path=farms.
- Prewarm do pool com duas conexões, conforme estabilização certificada no 01D3.
- Nenhuma prova foi executada em produção.

Suíte persistente adicionada:

services/api/tests/integration/operacional/test_requisicao_posse_01f1_integration.py

A suíte contém as três provas centrais desta fase e cleanup determinístico dos dados marcados T01F1.

## 3. Cenário retornável

O cenário real foi executado com natureza_item=RETORNAVEL.

| Fato | Quantidade |
|---|---:|
| Aprovada/reservada | 3 |
| Entregue | 3 |
| Recebida | 3 |
| Consumida | 0 |
| Devolvida | 2 |
| Danificada | 1 |
| Extraviada | 0 |
| Em posse | 0 |
| Status do item | CONCILIADO |

Fechamento: recebida = devolvida + danificada + extraviada, portanto 3 = 2 + 1 + 0.

## 4. Estoque no cenário retornável

| Etapa | Eventos | Movimentos físicos | Efeito |
|---|---:|---:|---:|
| Entrega de 3 | 1 ENTREGA | 1 SAIDA de 3 | saldo -3 |
| Recebimento de 3 | 1 RECEBIMENTO | 0 | sem alteração |
| Dano de 1 | 1 DANO | 0 | não volta ao estoque |
| Devolução de 2 | 1 DEVOLUCAO | 1 ENTRADA de 2 | saldo +2 |
| Retry da devolução | mesmo evento | mesmo movimento | sem alteração |

Saldo físico líquido: -3 + 2 = -1.

Não houve segunda saída, nem entrada referente à unidade danificada.

## 5. Proibição de consumo de retornável

Foi enviado comando real CONSUMO de 1 unidade para o item retornável. Resultado: REJEITADO por regra de domínio.

Após a rejeição:

- eventos CONSUMO: 0;
- movimentos adicionais: 0;
- saldo físico: inalterado;
- lote: inalterado;
- posse: inalterada;
- versão: sem efeito indevido.

A regra existe no backend e não depende apenas da interface Campo.

## 6. Retry da devolução

O comando de devolução de 2 unidades foi repetido com o mesmo client_operation_id.

Resultado:

- eventos DEVOLUCAO: 1;
- movimentos ENTRADA: 1;
- entrada física total: 2.

O segundo envio retornou o fato/movimento original. Não houve entrada de 4 unidades.

## 7. Rollback provocado da devolução

Foi injetada uma exceção no enqueue depois da preparação dos fatos da devolução e antes do commit transacional.

O snapshot anterior e posterior confirmou:

| Estado | Resultado após rollback |
|---|---|
| Evento DEVOLUCAO novo | 0 |
| Movimento ENTRADA novo | 0 |
| SaldoEstoque | original |
| LoteEstoque | original |
| Posse | original |
| Versão da requisição | original |
| Outbox | original |

Não restou evento órfão, movimento órfão, chave idempotente fantasma ou lock funcional. A mesma devolução foi executada depois normalmente e produziu exatamente um evento e uma entrada.

## 8. Fechamento com material pendente

Foi criada uma operação compatível com a requisição e mantida quantidade em posse. A tentativa de alterar a operação para REALIZADA foi rejeitada pelo guardrail canônico. O status permaneceu PLANEJADA.

Também foi validado o caso ENTREGUE=100, RECEBIDO=92, diferença=8, com em_posse=0. O fechamento continuou bloqueado. Posse zero isoladamente não caracteriza conciliação.

Após destinação integral, sem divergência ou recusa pendente e com os demais requisitos normais atendidos, o fechamento foi aceito.

## 9. Concorrência e regressões

A regressão de concorrência de posse do 01F permaneceu verde: duas sessões tentando consumir 60 sobre posse 100 resultaram em um sucesso, uma rejeição e posse final 40.

Resultados executados:

| Suíte | Resultado |
|---|---|
| 01F1 PostgreSQL real | 3 passed in 8.26s |
| 01D2 PostgreSQL real isolado | 1 passed in 5.25s |
| 01E PostgreSQL real | passou na rodada conjunta |
| 01F PostgreSQL real | passou na rodada conjunta |
| Unitários 01D/01E/01F | 17 passed in 2.09s |
| Campo Vitest | 5 files, 24 tests passed |
| Campo typecheck | PASS |
| Campo build | PASS |
| Import da aplicação | APP_IMPORT_OK |
| Ruff direcionado | PASS |
| git diff --check | PASS |

Uma rodada conjunta apresentou timeout de abertura de conexão no prewarm do teste 01D2. Não houve falha de asserção ou efeito parcial; a prova 01D2 foi repetida isoladamente e passou. O fato foi classificado como instabilidade transitória de infraestrutura/conectividade do runner, não como defeito funcional do 01F.

## 10. Tenant isolation

As provas de isolamento tenant e os testes de integração herdados do 01D/01E/01F permaneceram aprovados. O serviço exige tenant, identidade operacional e referências estruturadas; não foi encontrado caminho que permita destinar item, execução, lote ou depósito de outro tenant.

## 11. Cleanup e integridade do ambiente

Consulta direta ao PostgreSQL após as provas confirmou:

- requests T01F1: 0;
- events T01F1: 0;
- operations T01F1: 0;
- idle in transaction: 0;
- ungranted locks: 0.

Os dados temporários foram removidos e os saldos sintéticos utilizados pelos testes foram restaurados.

## 12. Respostas obrigatórias

A. O cenário PostgreSQL real de retornável 3 → 2 devolvido → 1 danificado passou?  
Sim, PASS.

B. Foi impossível registrar CONSUMO para RETORNAVEL no PostgreSQL real?  
Sim. O comando foi rejeitado sem efeitos persistidos.

C. A devolução das 2 unidades criou exatamente uma entrada física?  
Sim, uma ENTRADA de quantidade 2.

D. Retry da devolução retornável duplicou entrada?  
Não. Retornou o movimento original.

E. A unidade danificada reapareceu no estoque?  
Não. Dano gerou somente fato operacional.

F. A falha provocada da devolução deixou algum efeito parcial?  
Não. O rollback restaurou evento, movimento, saldo, lote, posse, versão e outbox.

G. Após rollback, a mesma devolução pôde ser executada normalmente?  
Sim, com uma única entrada física.

H. Uma operação com material ainda em posse consegue ser fechada?  
Não. O fechamento foi bloqueado.

I. Após conciliação completa, o bloqueio de material deixa de impedir o fechamento?  
Sim, desde que as demais regras normais sejam satisfeitas.

J. em_posse=0 com divergência pendente continua bloqueando?  
Sim.

K. Existe BLOCKING/HIGH funcional restante no 01F?  
Não foi identificado BLOCKING/HIGH funcional restante especificamente no 01F. A apropriação econômica pertence ao 01G.

L. Os fatos estão certificados para o 01G sem inferir consumo?  
Sim. Os eventos distinguem consumo, devolução, perda, dano e extravio.

## 13. Riscos e pendências

- A execução integrada continua dependente de PostgreSQL acessível e pode sofrer timeout transitório na abertura de conexões; o runner certificado com prewarm reduz o risco.
- A execução não implementa valoração, CostAllocation, DRE ou lançamento financeiro.
- A exceção administrativa de fechamento continua fora desta fase.

## 14. Veredicto

Todos os critérios centrais do 01F1 foram atendidos:

- retornável E2E real: PASS;
- consumo de retornável bloqueado: PASS;
- devolução com única entrada: PASS;
- retry sem duplicação: PASS;
- rollback íntegro: PASS;
- fechamento com pendência bloqueado: PASS;
- fechamento após conciliação: PASS;
- regressões 01D/01E/01F: PASS;
- tenant e Campo: PASS.

MATERIAL-REQUISITION-FLOW-01F1  
STATUS: GO

RETORNÁVEL E2E POSTGRESQL:  
PASS

CONSUMO DE RETORNÁVEL BLOQUEADO:  
PASS

DEVOLUÇÃO — ÚNICA ENTRADA FÍSICA:  
PASS

ROLLBACK PROVOCADO DA DEVOLUÇÃO:  
PASS

FECHAMENTO COM MATERIAL PENDENTE:  
BLOQUEADO

FECHAMENTO APÓS CONCILIAÇÃO:  
PASS

REGRESSÕES 01D/01E/01F:  
PASS

AUTORIZAÇÃO PARA 01G:  
SIM

PRÓXIMA FASE:  
MATERIAL-REQUISITION-FLOW-01G — Apropriação Econômica do Consumo Real

