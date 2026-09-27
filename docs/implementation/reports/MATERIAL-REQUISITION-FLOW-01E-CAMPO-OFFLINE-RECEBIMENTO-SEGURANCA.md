# MATERIAL-REQUISITION-FLOW-01E — Campo Offline, Recebimento e Segurança

## 1. Resumo

O fluxo canônico de recebimento foi implementado sem criar uma segunda saída de estoque. O Campo recebe uma projeção das entregas canônicas autorizadas, mantém essa projeção em Dexie, registra a conferência offline com client_operation_id estável e envia o comando pela sync_queue existente.

O backend valida a identidade operacional contextual (PessoaUsuario), o responsável ou delegado vigente, a requisição, o item, a entrega exata, a versão e a quantidade ainda pendente. O evento de recebimento/recusa é append-only e referencia explicitamente o evento ENTREGA.

Resultado validado:

- migration 01E upgrade → downgrade → upgrade em PostgreSQL de desenvolvimento: PASS;
- cenário real 100 entregue → 92 recebidos → divergência 8 → retry: PASS;
- movimento físico adicional no recebimento: ZERO;
- testes Campo offline/ACK/conflito: PASS;
- tentativa cross-tenant no comando de recebimento: REJECT;
- regressão transacional 01D2 isolada: PASS.

## 2. Arquitetura do Campo auditada

O 01E reutiliza a infraestrutura existente:

- Dexie: apps/campo/src/lib/db.ts;
- fila: sync_queue e enqueueSync em apps/campo/src/lib/sync/push.ts;
- pull: apps/campo/src/lib/sync/pull.ts;
- push/retry: apps/campo/src/lib/sync/push.ts;
- recuperação de IN_FLIGHT: apps/campo/src/lib/sync/worker.ts;
- sessão, logout e troca de usuário/tenant: apps/campo/src/lib/stores/session-store.ts;
- interface: apps/campo/src/components/campo/requisicoes-section.tsx.

Não foi criado um segundo mecanismo de sincronização.

## 3. Projeção backend → Campo

GET /campo/requisicoes passou a usar RequisicaoRecebimentoService.listar_para_campo e retorna somente requisições com entrega canônica e autorização operacional para o usuário do dispositivo.

O SyncService.pull também inclui requisicoes_materiais. A projeção contém requisição, operação, responsável, versão, item, natureza, quantidades aprovadas/entregues/recebidas/recusadas/pendentes/em posse e cada entrega com lote, depósito e evento de origem.

Arquivos principais:

- services/api/operacional/services/requisicao_recebimento_service.py;
- services/api/operacional/schemas/estoque.py;
- services/api/campo/router.py;
- services/api/campo/service.py;
- services/api/campo/schemas.py.

## 4. Recebimento canônico

O comando é POST /campo/requisicoes/{req_id}/receber.

O backend exige item_id, entrega_evento_id, quantidade recebida, resultado (RECEBIDO_INTEGRAL, RECEBIDO_PARCIAL, RECUSADO ou DIVERGENTE), base_version, client_operation_id e dispositivo_id autenticado.

O evento criado é RECEBIMENTO ou RECUSA, com evento_entrega_id, usuário, pessoa operacional, dispositivo, motivo, versão, correlação e provenance canônica.

O recebimento não importa nem altera EstoqueMovimento, SaldoEstoque, LoteEstoque ou ReservaEstoque.

## 5. Autorização responsável/delegado

O dispositivo é resolvido pelo token e o usuário efetivo vem de device.user_id. Campos usuario_id enviados pelo cliente não concedem autorização.

A sequência é:

tenant + usuário autenticado
→ PessoaUsuario ativo e vigente
→ Pessoa operacional
→ responsável direto da requisição
   OU
→ delegação DELEGADO vigente com pessoa_usuario_id

IdentidadeOperacionalService.validar_recebedor é reutilizado. Não há matching por e-mail, CPF, nome ou igualdade acidental de UUID.

O retry também revalida a identidade antes de devolver ACK. Assim, usuário B não pode reapresentar a chave de usuário A e obter autorização operacional.

### PIN

PIN local desbloqueia a ação no Campo e, online, a sessão do dispositivo é validada no backend. PIN não substitui PessoaUsuario, responsabilidade ou delegação. Offline, a operação conserva usuario_id e device_id da sessão local; ao sincronizar, o token/backend revalidam o contexto.

## 6. Resultados e divergências

Os resultados são fatos por item, não estados artificiais do cabeçalho:

- integral: recebida fecha a entrega;
- parcial: recebe quantidade menor, mantendo pendência;
- divergente: recebe quantidade menor com motivo obrigatório;
- recusada: registra RECUSA com motivo e quantidade recusada derivada da pendência.

Recusa não desfaz a entrega nem cria entrada física. Eventual retorno físico pertence ao 01F.

## 7. Posse operacional

Para o escopo 01E, a posse inicial é a quantidade recebida. A projeção prepara quantidade_em_posse para a equação futura, mas não implementa consumo, devolução, perda, dano, extravio ou conciliação final.

Exemplo validado:

Entregue: 100
Recebido: 92
Divergência: 8
Posse inicial: 92

## 8. Dexie e operação offline

Foram adicionadas as stores:

- requisicoes: projeção da requisição;
- requisicao_itens: projeção indexada por item;
- requisicao_operacoes: operações locais de recebimento.

Cada operação local registra tenant, usuário, dispositivo, requisição/item/entrega, quantidade e resultado, motivo, base_version, timestamp do dispositivo, client_operation_id estável e status local.

Fluxo:

pull → Dexie → conferência offline → sync_queue → push FIFO
     → ACK | CONFLICT | ERROR → projeção canônica local

O Campo não marca a operação como sincronizada antes do ACK.

## 9. Idempotência, retry e conflito

Em resposta perdida após commit, o Campo mantém a mesma chave e reenvia o mesmo payload. O backend consulta o fato existente e retorna o resultado original. A constraint tenant + client_operation_id é a proteção final; concorrência no mesmo contexto converge ao evento já confirmado.

Versão obsoleta retorna HTTP 409 com mensagem e projeção canônica. O Campo marca a operação como CONFLICT, atualiza o cache e não reenvia automaticamente como se fosse sucesso.

Payload incompatível para chave já utilizada é rejeitado.

## 10. Dois dispositivos

Dois dispositivos que tentarem conferir a mesma entrega não podem somar duas vezes: o primeiro comando confirmado atualiza a versão e a quantidade pendente; o segundo encontra versão obsoleta ou pendência esgotada e recebe conflito/erro controlado. O backend não aceita quantidade acima da entrega pendente.

## 11. Logout, troca de usuário e tenant

clearCacheTables limpa em uma transação as stores de requisições, itens, operações pendentes e sync_queue antes de efetivar nova sessão. saveSession executa a mesma limpeza quando muda usuário ou tenant. O resumo é preservado em aviso local para o usuário.

Isso impede que uma operação de A seja reenviada como B. A política atual privilegia isolamento seguro e remove pendências não sincronizadas durante a troca; não as reatribui silenciosamente. A retenção/quarentena UX dessas pendências fica como melhoria futura.

## 12. Consumível e retornável

natureza_item é preservada no snapshot local e na projeção. Tanto CONSUMIVEL quanto RETORNAVEL podem ser entregues e recebidos.

No 01E, retornável entra em posse operacional e não em consumo. Devolução, dano e extravio continuam fora do escopo e serão tratados no 01F.

## 13. Estoque físico — guardrail

O único movimento físico continua sendo a entrega 01D.

No recebimento:

- EstoqueMovimento: 0 novo;
- SaldoEstoque: sem alteração;
- LoteEstoque: sem alteração;
- ReservaEstoque: sem alteração.

O evento de recebimento referencia a entrega exata por evento_entrega_id; não há busca por produto/requisição nem baixa FIFO no Campo.

## 14. Tenant/RLS

O serviço filtra tenant em requisição, item, entrega, identidade, pessoa, operação e dispositivo. O contexto de sessão continua protegido pelas políticas tenant existentes. O teste PostgreSQL 01E tentou usar a requisição do Tenant A com contexto e usuário do Tenant B e recebeu EntityNotFoundError, sem criar evento ou alterar saldo.

O isolamento do cache é garantido pela limpeza por troca de tenant/usuário e pela projeção autorizada no pull.

## 15. Migration

Migration criada:

services/api/migrations/versions/20260925_material_requisition_01e.py

Alterações:

- evento_entrega_id nullable;
- resultado_conferencia nullable;
- índice tenant/evento de entrega;
- CHECK dos resultados de conferência;
- FK composta tenant-safe para o evento ENTREGA de origem.

Validação PostgreSQL de desenvolvimento, não produção:

- head inicial: 20260925_material_requisition_01d;
- upgrade 01d → 01e: PASS;
- downgrade 01e → 01d: PASS;
- upgrade final 01d → 01e: PASS;
- head final: 20260925_material_requisition_01e;
- colunas e constraints inspecionadas: PASS.

Nenhum backfill histórico foi executado.

## 16. Testes executados

Backend:

- testes direcionados 01C/01C1/01D/01E: 30 passed;
- import da aplicação: APP_IMPORT=PASS;
- PostgreSQL real 01E: 1 passed;
- PostgreSQL real 01D2 isolado: 1 passed;
- migration upgrade/downgrade/upgrade: PASS;
- git diff --check: PASS.

O teste 01E real cobre identidade operacional temporária controlada, entrega canônica de 100, conferência divergente de 92, pendência de 8, posse inicial de 92, retry da mesma chave, um evento de recebimento, um movimento físico original, zero movimento adicional e tentativa cross-tenant rejeitada.

Campo:

- typecheck: PASS;
- build PWA: PASS;
- testes existentes e 01E: 4 arquivos, 14 testes PASS;
- teste de logout/troca limpando stores de requisições: PASS;
- teste de perda de resposta e retry com mesma chave: PASS;
- teste de conflito com projeção canônica: PASS.

Lint:

O lint direcionado não ficou verde por pendências históricas já existentes em campo/router.py e operacional/schemas/estoque.py — principalmente Depends/Query, imports, tipos antigos e linhas longas — além de algumas linhas novas longas no teste. Não foram usados como evidência de regressão funcional. git diff --check permaneceu PASS.

A bateria combinada 01E+01D2 apresentou instabilidade de execução do runner após o 01E passar; as duas suítes foram executadas isoladamente com sucesso, e a regressão 01D2 isolada passou.

## 17. Compatibilidade legada

Os endpoints legados de retirada/devolução foram preservados para compatibilidade. O serviço legado de entrega rejeita requisições que já iniciaram o fluxo canônico, impedindo baixa duplicada. Para uma requisição ainda legada, o endpoint antigo continua sendo o fluxo físico legado, não o recebimento 01E.

O endpoint canônico de recebimento não delega para confirmar-retirada nem para registrar_saida.

## 18. Respostas obrigatórias

A. Recebimento altera estoque físico?
Não. Não cria movimento, não altera saldo, lote ou reserva.

B. Como provar quem recebeu?
O evento registra usuario_id, pessoa_operacional_id, dispositivo_id, timestamp, motivo, versão e correlação.

C. Como responsável/delegado são autorizados?
Por PessoaUsuario ativo/vigente, comparação com responsavel_pessoa_id ou delegação DELEGADO vigente com pessoa_usuario_id, tudo no backend.

D. PIN sozinho autoriza?
Não.

E. Como offline mantém autoria?
A operação grava usuário, tenant e dispositivo no payload local e a fila é limpa antes de troca de sessão; o backend autentica e revalida ao sincronizar.

F. Como retry não duplica?
client_operation_id estável, lookup idempotente, constraint tenant-safe e retorno do evento original.

G. Como dois dispositivos não duplicam?
Lock da requisição/item, lock da entrega, versão monotônica e validação da pendência restante.

H. Como parcial/divergência é representada?
Evento RECEBIMENTO com quantidade real, resultado_conferencia, motivo e projeção com entregue, recebido e pendente preservados.

I. Como retornável entra em posse?
Recebimento atualiza somente a posse projetada; não registra consumo. Devolução/dano/extravio são 01F.

J. Logout/troca reatribui operação?
Não. A fila/cache são limpos antes da nova sessão e a autoria não é trocada silenciosamente. A retenção futura em quarentena é pendência UX.

K. Existe caminho legado para confirmar recebimento fora do serviço canônico?
Não para requisições que iniciaram o fluxo canônico: o legado é bloqueado. Existe compatibilidade para requisições que ainda não iniciaram o fluxo canônico, mas isso representa entrega física legada, não confirmação 01E.

L. Algum recebimento cria movimento ou altera estoque/reserva?
Não. A prova PostgreSQL confirmou zero nova baixa.

## 19. Riscos e pendências

- Pendências offline são removidas com aviso em logout/troca; ainda não há quarentena recuperável.
- Não há UX completa de resolução posterior da divergência; isso pertence à devolução/conciliação do 01F.
- Lint global possui dívida preexistente fora do escopo funcional.
- Recebimento não fecha a operação/tarefa; bloqueio de encerramento com requisição não conciliada continua para fase apropriada.
- Não foi implementado consumo, devolução, perda, dano, extravio ou apropriação econômica.

## 20. Veredicto

O 01E está funcionalmente pronto para prosseguir, com a ressalva explícita de que a retenção recuperável de operações pendentes no logout/troca ainda não existe e que os fluxos de consumo/devolução continuam deliberadamente fora desta fase.

MATERIAL-REQUISITION-FLOW-01E
STATUS: GO COM RESSALVAS

CAMPO OFFLINE:
PASS

RECEBIMENTO CANÔNICO:
PASS

AUTORIZAÇÃO RESPONSÁVEL/DELEGADO:
PASS

IDEMPOTÊNCIA/SYNC:
PASS

NOVA BAIXA FÍSICA NO RECEBIMENTO:
ZERO

ISOLAMENTO TENANT:
PASS

AUTORIZAÇÃO PARA 01F:
SIM

PRÓXIMA FASE:
MATERIAL-REQUISITION-FLOW-01F — Consumo, Devolução, Retornáveis e Conciliação

