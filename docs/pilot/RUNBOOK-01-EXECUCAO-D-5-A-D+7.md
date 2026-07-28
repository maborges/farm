# Runbook Oficial do Dry Run Assistido do Primeiro Piloto

Data: 2026-07-09

## 1. Papel deste documento

Este é o runbook operacional oficial do Dry Run assistido do primeiro piloto.

Ele executa o [PLANO-MESTRE-PILOTO-01.md](/opt/lampp/htdocs/farm/docs/pilot/PLANO-MESTRE-PILOTO-01.md) em ordem cronológica e referencia os documentos auxiliares já aprovados, sem criar fluxo paralelo.

Hierarquia documental:

1. Documento mestre: [PLANO-MESTRE-PILOTO-01.md](/opt/lampp/htdocs/farm/docs/pilot/PLANO-MESTRE-PILOTO-01.md)
2. Runbook operacional: [RUNBOOK-01-EXECUCAO-D-5-A-D+7.md](/opt/lampp/htdocs/farm/docs/pilot/RUNBOOK-01-EXECUCAO-D-5-A-D+7.md)
3. Checklist do cliente: [CHECKLIST-CLIENTE-01-PREPARACAO-IMPLANTACAO.md](/opt/lampp/htdocs/farm/docs/pilot/CHECKLIST-CLIENTE-01-PREPARACAO-IMPLANTACAO.md)
4. Parecer de prontidão: [PILOT-E2E-01-AUDITORIA-PRONTIDAO-OPERACIONAL-PONTA-A-PONTA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-E2E-01-AUDITORIA-PRONTIDAO-OPERACIONAL-PONTA-A-PONTA.md)

## 2. Escopo do Dry Run

Este Dry Run cobre:

- preparação do ambiente e dos responsáveis;
- tenant, owner/admin, onboarding e Wizard oficial;
- estrutura da fazenda e cadastros mínimos;
- safra e operação agrícola assistida;
- Campo PWA offline-first com perda e retomada de rede;
- estoque e apropriação de custo coerentes com a execução;
- colheita, romaneio e comercialização mínima;
- integração ERP via `/api/v1/integracoes/erp/*`;
- suporte técnico provider-specific via `/api/v1/integracoes/sankhya/*`;
- observabilidade, falhas controladas, evidências e decisão GO/NO-GO.

Fora de escopo deste Dry Run:

- exportação e cadeia avançada de café como requisito bloqueador;
- novos endpoints, novos serviços ou correções funcionais;
- automação ponta a ponta única;
- logs ERP genéricos; logs técnicos seguem provider-specific e suporte.

## 3. Arquitetura obrigatória a respeitar

Governança:

- `Tenant`, `Usuario`, `TenantUsuario`, Owner/Admin, onboarding oficial e RLS.

Implantação:

- Wizard em `/dashboard/implantacao/wizard` e `/api/v1/wizard/*`.

Operação:

- `UnidadeProdutiva`, propriedades, imóveis rurais, `PropriedadeImovel`, áreas, talhões, safras, estoque canônico, romaneio e comercialização.

Motor econômico (decisão consolidada em SOIL-PLAN-EXEC-04I/04J/04K/04M — não reabrir):

- cadeia oficial: `OperacaoAgricola -> OperacaoExecucao -> CostAllocation -> Dashboard -> DRE`;
- `ProductionUnit` é obrigatória e sua resolução é determinística (sem fallback por `.first()`/`created_at`);
- `CostAllocation` é a fonte econômica oficial; Dashboard e DRE leem exclusivamente de `CostAllocation`;
- a operação agrícola não cria mais `Despesa(OPERACAO_AGRICOLA)` (removido em 04I) — não validar nem esperar esse registro;
- Campo PWA usa exatamente o mesmo `OperacaoService` do Web, sem lógica paralela de custo;
- dados históricos de Dry Run anteriores (151 registros sem `CostAllocation`, ver SOIL-PLAN-EXEC-04L0) não foram e não devem ser reparados neste ciclo.

ERP:

- superfície comum em `/api/v1/integracoes/erp/*`;
- suporte e operações Sankhya provider-specific em `/api/v1/integracoes/sankhya/*`;
- `ErpReadinessService`, `IntegrationHealth`, `IntegrationJob`, `ExternalRecordAssociation`, timeline e diagnóstico.

Engines:

- Domain Events, Outbox, Alert Engine, Notification Engine e Recommendation Engine.

## 4. Documentos auxiliares obrigatórios

- [docs/runbooks/field-pwa-local-setup.md](/opt/lampp/htdocs/farm/docs/runbooks/field-pwa-local-setup.md)
- [docs/runbooks/estoque-implantacao-assistida.md](/opt/lampp/htdocs/farm/docs/runbooks/estoque-implantacao-assistida.md)
- [docs/implementation/checklists/domain-events-operational-checklist.md](/opt/lampp/htdocs/farm/docs/implementation/checklists/domain-events-operational-checklist.md)
- [docs/architecture/agrosaas-observability.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-observability.md)
- [docs/implementation/reports/PILOT-GOV-01-GUARDRAILS-IMPLANTACAO-ONBOARDING-ASSINATURA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-GOV-01-GUARDRAILS-IMPLANTACAO-ONBOARDING-ASSINATURA.md)
- [docs/implementation/reports/SANKHYA-AUTH-02-TEST-CONNECTION.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-AUTH-02-TEST-CONNECTION.md)
- [docs/implementation/reports/SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md)

## 5. Pré-condições técnicas

Antes de D-5, validar:

- branch e commit anotados no cabeçalho da execução;
- API acessível e migrations consistentes;
- Web acessível;
- Campo PWA instalável ou ambiente equivalente preparado;
- banco e schema `farms` disponíveis;
- worker de outbox e schedulers necessários ativos, quando a validação depender deles;
- tenant de teste criado ou pronto para criação pelos caminhos oficiais;
- usuários de teste definidos;
- local de armazenamento de evidências definido;
- credenciais e secrets substituídos por placeholders em qualquer registro.

Nunca registrar no runbook:

- senhas reais;
- tokens reais;
- client secrets;
- cabeçalhos sensíveis;
- URLs privadas de cliente.

Usar placeholders:

- `<OWNER_EMAIL>`
- `<OWNER_PASSWORD>`
- `<ERP_BASE_URL>`
- `<ERP_TOKEN_ALIAS>`
- `<TENANT_SLUG>`
- `<UNIDADE_PRODUTIVA_ID>`

## 6. Critérios de entrada

O Dry Run só pode começar se todos os itens abaixo estiverem atendidos:

- ambiente disponível e identificado;
- tenant válido;
- Owner/Admin acessível;
- checklist do cliente revisado;
- ao menos uma `UnidadeProdutiva` criada ou com passo explícito para criação;
- usuário operacional de campo definido;
- massa de dados mínima acordada;
- PWA instalável ou dispositivo preparado;
- ERP configurado ou formalmente dispensado para o ciclo;
- janela D-5 a D+7 reservada;
- responsáveis técnico, funcional, suporte e cliente confirmados;
- plano de contingência conhecido.

## 7. Massa de dados mínima controlada

Dados mínimos recomendados:

| Grupo | Mínimo |
| ----- | ------ |
| Governança | 1 tenant, 1 owner/admin, 1 usuário operacional |
| Estrutura | 1 propriedade, 1 unidade produtiva, 1 talhão ativo |
| Produção | 1 cultura de café, 1 safra ativa |
| Cadastros | 1 produto colhido, 1 insumo, 1 fornecedor, 1 cliente |
| Estoque | 1 depósito, 1 lote, 1 saldo inicial coerente |
| Operação | 1 atividade planejada ou equivalente operacional |
| Recursos | 1 máquina, 1 colaborador |
| Financeiro | 1 conta financeira ou estrutura mínima equivalente |
| Comercialização | 1 comercialização de teste no fluxo oficial |

Restrições:

- usar dados mínimos, realistas e rastreáveis;
- evitar dados pessoais ou fiscais reais;
- registrar IDs funcionais sem expor segredos.

## 8. Matriz de responsabilidades

| Papel | Responsabilidade principal |
| ----- | -------------------------- |
| Responsável técnico AgroSaaS | conduzir ambiente, APIs, ERP, suporte técnico e decisão técnica de continuidade |
| Responsável funcional AgroSaaS | conduzir roteiro, validações operacionais, evidências e aceite funcional |
| Owner/Admin do cliente | aprovar cadastros, go/no-go e continuidade da operação |
| Operador Web | executar passos de backoffice/tenant |
| Operador Campo PWA | executar operação offline e sincronização |
| Suporte/Backoffice | observar health, jobs, timeline, diagnóstico e logs provider-specific |
| Responsável ERP do cliente | validar credenciais, conexão e reconciliar dúvidas de origem |
| Decisor GO/NO-GO | formalizar avanço, ressalvas ou interrupção |

Nenhuma atividade crítica pode ficar sem responsável nomeado na execução real.

## 9. Convenção de evidências

Padrão de nome:

`DRYRUN-[CENARIO]-[PASSO]-[AAAA-MM-DD]-[SEQ]`

Exemplos:

- `DRYRUN-A-OWNER-LOGIN-2026-07-09-01`
- `DRYRUN-B-OFFLINE-PUSH-2026-07-09-03`
- `DRYRUN-D-ERP-DIAGNOSTICO-2026-07-09-02`

Tipos aceitos:

- captura de tela sem dados sensíveis;
- resposta de API sanitizada;
- identificador funcional;
- job/timeline/diagnóstico;
- movimento de estoque;
- apropriação de custo;
- lançamento financeiro;
- registro de sync;
- aceite do responsável.

## 10. Observabilidade durante o Dry Run

Tenant:

- telas funcionais do Wizard;
- console ERP em `/dashboard/settings/integracoes/erp`;
- indicadores de estoque, romaneio, comercialização e financeiro.

Backoffice/Suporte:

- health, jobs, timeline e diagnóstico do ERP;
- logs provider-specific em `/api/v1/integracoes/sankhya/logs`;
- trilha de incidentes, outbox, alertas, notificações e recomendações.

Separação obrigatória:

- tenant não precisa consumir log técnico bruto;
- suporte/backoffice mantém acesso aos logs provider-specific;
- `/api/v1/integracoes/erp/*` cobre o consumo comum do ERP.

## 11. Critérios de interrupção imediata

Interromper a execução se houver:

- quebra de isolamento entre tenants;
- inconsistência irreversível de estoque;
- duplicação financeira material;
- perda de dados offline sem recuperação;
- impossibilidade de restaurar sincronização;
- falha generalizada de autenticação;
- migration inconsistente;
- necessidade de ação destrutiva no banco;
- vazamento de credencial;
- comportamento não idempotente em operação crítica.

## 12. Critérios de sucesso

O Dry Run será aprovado apenas se:

- cenários A, B, D e E forem executados;
- cenário C for executado ao menos no escopo mínimo definido neste runbook;
- não houver violação multi-tenant;
- a operação offline sincronizar sem duplicidade;
- estoque e custos refletirem a execução real testada;
- colheita e romaneio preservarem origem por safra/talhão;
- ERP apresentar readiness, job e diagnóstico utilizáveis;
- engines não bloquearem a transação principal;
- falhas controladas puderem ser diagnosticadas e recuperadas;
- evidências forem coletadas;
- ressalvas forem registradas;
- a decisão final for formalizada.

## 13. Cobertura cronológica D-5 a D+7

### D-5

Objetivo:
validar governança, ambiente, acessos e preparação do cliente.

Passos:

1. Confirmar branch, commit, ambiente e local de evidências.
2. Validar tenant, owner/admin, assinatura e onboarding oficial.
3. Confirmar acesso ao Wizard.
4. Confirmar responsáveis e janela operacional.

Evidências:

- login do owner/admin;
- status do onboarding;
- acesso ao Wizard;
- checklist do cliente revisado.

### D-4

Objetivo:
validar estrutura produtiva e cadastros mínimos.

Passos:

1. Confirmar `UnidadeProdutiva`.
2. Validar propriedade, imóveis rurais e vínculo `PropriedadeImovel` quando aplicável.
3. Validar talhão, cultura e safra.
4. Confirmar depósito, produto, insumo, fornecedor, cliente e conta mínima.

Evidências:

- estrutura territorial;
- `UnidadeProdutiva` ativa;
- safra visível;
- depósitos e cadastros mínimos.

### D-3

Objetivo:
validar ERP e observabilidade básica.

Passos:

1. Executar teste de conexão do provider atual pelos fluxos aprovados.
2. Validar readiness e health na superfície ERP.
3. Executar sincronização controlada aprovada.
4. Conferir jobs, timeline, diagnóstico e associações.

Evidências:

- teste de conexão sanitizado;
- resposta de readiness/health;
- job criado;
- timeline/diagnóstico disponíveis.

### D-2

Objetivo:
preparar e validar Campo PWA.

Passos:

1. Preparar dispositivo conforme o runbook do Campo.
2. Validar ativação do usuário operacional.
3. Executar sync inicial.
4. Validar operação offline, fechamento e reabertura do aplicativo.

Evidências:

- dispositivo ativado;
- sync inicial concluído;
- evidência local criada;
- fila offline persistida.

### D-1

Objetivo:
fechar checklist e decidir entrada no Dry Run assistido.

Passos:

1. Reavaliar Wizard.
2. Confirmar ausência de bloqueio crítico.
3. Revisar massa mínima e responsáveis.
4. Formalizar GO/NO-GO para D0.

Evidências:

- resumo do Wizard;
- checklist mínimo;
- decisão assinada ou registrada.

### D0

Objetivo:
executar os cenários obrigatórios A-E.

### D+1 a D+7

Objetivo:
acompanhar operação assistida, pendências e correções não destrutivas.

Rotina diária:

1. Revisar jobs, timeline, health e diagnóstico.
2. Revisar estoque, custos e financeiro do escopo executado.
3. Revisar sincronizações do Campo.
4. Consolidar evidências e incidentes.
5. Reclassificar ressalvas e decidir continuidade.

## 14. Cenário A — preparação do cliente

Fluxo:

`tenant -> Owner -> onboarding -> Wizard -> propriedade -> unidade produtiva -> talhão -> safra -> cadastros mínimos -> readiness -> READY_FOR_GO_LIVE`

| Passo | Responsável | Interface | Resultado esperado | Evidência | Falha/contingência |
| ----- | ----------- | --------- | ------------------ | --------- | ------------------ |
| Validar tenant e owner | AgroSaaS + cliente | Web | tenant correto e owner autenticado | login e identificação do tenant | corrigir acesso ou interromper |
| Confirmar onboarding | AgroSaaS | `/api/v1/onboarding/*` e Web | onboarding oficial concluído | print/estado do onboarding | voltar ao fluxo oficial |
| Abrir Wizard | AgroSaaS + cliente | `/dashboard/implantacao/wizard` | Wizard acessível com estado coerente | resumo do Wizard | tratar bloqueio antes de avançar |
| Validar unidade produtiva | Cliente + AgroSaaS | Web/Wizard | `UnidadeProdutiva` ativa | print/listagem | sem unidade produtiva: NO-GO |
| Validar estrutura mínima | Cliente + AgroSaaS | cadastros | propriedade, talhão e safra válidos | prints/IDs | ajustar cadastros antes de D0 |
| Confirmar readiness | AgroSaaS | ERP/Wizard | operação apta ao piloto | resumo com elegibilidade | manter em D-1 se houver bloqueio |

## 15. Cenário B — operação agrícola

Fluxo:

`tarefas aprovadas (SafraTarefa) -> consolidação em Plano Operacional em lote -> aplicação de receita/insumos/mão de obra -> geração da operação planejada -> Campo PWA -> offline -> retomada de rede -> sync -> execução/cancelamento da tarefa -> estoque -> custo -> evento -> recomendação/alerta`

Cada passo abaixo deve seguir o fluxo obrigatório de validação: preparar cenário → executar fluxo → validar resultado esperado (interface) → validar persistência (banco) → validar regras de negócio → validar eventos → validar Dashboard → validar DRE → registrar evidências → classificar falha, se houver → prosseguir. Resposta correta apenas na interface nunca encerra um passo.

**Nota de escopo (2026-07-27):** os passos 1–5 abaixo cobrem o épico de Planejamento Operacional em Lote (`services/api/agricola/planejamento_operacional/`) e o submódulo `receitas_aplicacao`. No momento da redação desta atualização, backend (models/schemas/service/router/migration, registrado em `main.py`) está pronto mas ainda não commitado; frontend de cadastro de receitas e de seleção múltipla no plano ainda não foi implementado (ver `docs/brainstorm-receitas-aplicacao-planejamento-operacional.md`). Se o frontend ainda não estiver disponível quando este Dry Run for executado, os passos 3–4 podem ser testados via chamada direta ao endpoint (`POST /api/v1/agricola/planejamento-operacional/{plano_id}/aplicar-receita`) e registrados como ressalva, não como bloqueador.

Passos obrigatórios:

1. Selecionar um conjunto de `SafraTarefa` aprovadas da mesma safra/UP (idealmente tarefas-irmãs geradas por uma mesma análise de solo, um talhão cada) e consolidá-las em um Plano Operacional em lote (`PlanoOperacional`). Confirmar na interface (ou via `GET` do plano) o total consolidado por produto e a mão de obra total estimada, somando as tarefas selecionadas.
2. Confirmar que o plano permite aprovação/programação parcial: reservar/aprovar apenas as tarefas cujo insumo já está disponível em estoque, deixando as demais pendentes de compra (validar que o sistema não força tudo-ou-nada).
3. Cadastrar (ou reaproveitar) uma Receita de Aplicação (produto + dose/ha + mão de obra padrão) e aplicá-la em lote às tarefas selecionadas do plano via `aplicar-receita`. Validar que cada `PlanoOperacionalTarefaInsumo`/`PlanoOperacionalTarefaMaoObra` criado corresponde à dose × área do talhão (`AreaRural.area_hectares_manual|area_hectares`), e não a um valor fixo por tarefa.
4. Validar isolamento de tenant no `aplicar-receita`: tentar aplicar receita a um `plano_operacional_tarefa_id` de outro plano/tenant e confirmar rejeição (não deve ser possível cruzar planos).
5. A partir do plano consolidado e com receita aplicada, gerar a operação planejada (`PlanejarOperacaoRequest -> TarefaService.gerar_operacao_planejada`) vinculada a uma `ProductionUnit` resolvida deterministicamente (confirmar resolução antes de iniciar; se não houver `ProductionUnit` candidata, tratar como bloqueio do passo, não prosseguir por fallback).
6. Carregar os dados no Campo PWA (confirmar que o Campo consome o mesmo `OperacaoService` do Web, sem lógica paralela).
7. Desligar a conectividade.
8. Registrar no Campo PWA o retorno da tarefa: cobrir pelo menos dois desfechos em execuções separadas — (a) tarefa **executada** (com quantidade real de insumo/mão de obra, podendo divergir do planejado) e (b) tarefa **cancelada**/não executada (validar que o motivo de cancelamento é obrigatório e que nenhum estoque/custo é baixado indevidamente).
9. Fechar e reabrir o aplicativo.
10. Restabelecer a conectividade.
11. Executar o push e validar idempotência (reenviar o mesmo push e confirmar ausência de duplicidade), para os dois desfechos (executada e cancelada).
12. Validar a execução (`OperacaoExecucao`) e a geração de `CostAllocation` vinculada à `ProductionUnit` correta — apenas para a tarefa executada. Confirmar que a tarefa cancelada não gera `CostAllocation` nem movimento de estoque.
13. Confirmar reflexo em estoque (movimento/lote/saldo) apenas para a tarefa executada, e comparar a quantidade consumida real com a planejada pela receita (dose × área).
14. Confirmar reflexo no Dashboard (custo realizado por `ProductionUnit`) refletindo somente a tarefa executada.
15. Confirmar reflexo na DRE (a operação deve aparecer no escopo construído a partir de `ProductionUnit` com `CostAllocation`).
16. Confirmar que nenhuma `Despesa(OPERACAO_AGRICOLA)` foi criada pela operação (arquitetura removida em 04I).
17. Confirmar que o status da `SafraTarefa`/plano reflete corretamente cada desfecho (executada vs. cancelada) na tela de acompanhamento do plano.
18. Validar evento, recomendação ou alerta, quando aplicável.

Evidências:

- plano operacional consolidado (ID, tarefas incluídas, total por produto, mão de obra total);
- receita de aplicação usada e resultado do `aplicar-receita` (insumos/mão de obra gerados por tarefa);
- tentativa de IDOR entre planos/tenants no `aplicar-receita` (rejeitada);
- registro offline no dispositivo, para os dois desfechos (executada e cancelada);
- estado da fila antes e depois do reenvio;
- resposta de sync sanitizada;
- movimento de estoque (apenas tarefa executada) com comparação planejado vs. realizado;
- `CostAllocation` gerada (ID, `ProductionUnit`, valor) apenas para a tarefa executada;
- confirmação de ausência de `CostAllocation`/estoque para a tarefa cancelada, com motivo de cancelamento registrado;
- leitura de Dashboard refletindo o custo realizado;
- leitura de DRE refletindo a operação no período;
- evento/alerta/recomendação quando o fluxo o produzir.

## 16. Cenário C — colheita e comercialização

Fluxo mínimo deste Dry Run:

`colheita -> romaneio -> produto colhido -> comercialização -> transição de status -> entrega -> receita ou conta a receber -> reflexo financeiro`

Escopo testado nesta etapa:

- obrigatório:
  - romaneio;
  - preservação de origem por safra/talhão;
  - criação e leitura do produto colhido;
  - comercialização mínima no fluxo `RASCUNHO -> CONFIRMADO -> EM_TRANSITO -> ENTREGUE -> FINALIZADO`;
  - reflexo financeiro previsto pelo fluxo atual.
- assistido:
  - rentabilidade e conferência analítica;
  - validação operacional com acompanhamento do time funcional.
- fora do Dry Run:
  - exportação;
  - classificação avançada;
  - cadeia avançada de beneficiamento, salvo exigência explícita do piloto.

Se alguma etapa mínima falhar por limitação já conhecida e controlável, registrar como ressalva. Só vira bloqueador se comprometer integridade, estoque, financeiro ou rastreabilidade básica.

## 17. Cenário D — integração ERP

Fluxo:

`configuração -> teste de conexão -> readiness -> sincronização -> job -> associação externa -> health -> timeline -> diagnóstico -> falha -> reprocessamento`

Separação obrigatória:

- superfície ERP comum:
  - `GET /api/v1/integracoes/erp/status`
  - `GET /api/v1/integracoes/erp/health`
  - `GET /api/v1/integracoes/erp/jobs`
  - `GET /api/v1/integracoes/erp/timeline`
  - `GET /api/v1/integracoes/erp/diagnostico`
  - `GET /api/v1/integracoes/erp/associacoes/pendentes`
- provider-specific Sankhya:
  - autenticação;
  - teste de conexão técnico;
  - logs;
  - operações específicas.

Não exigir `/api/v1/integracoes/erp/logs` neste ciclo.

Evidências:

- teste de conexão sanitizado;
- readiness;
- job criado;
- health;
- timeline;
- diagnóstico;
- associação pendente ou reconciliada;
- reprocessamento ou retry validado quando houver falha controlada.

## 18. Cenário E — falhas controladas

### Campo PWA

- provocar perda de rede durante o uso;
- registrar uma operação offline;
- fechar e reabrir o aplicativo;
- restaurar a rede;
- reenviar;
- repetir o mesmo push para validar idempotência;
- observar falha e retomada, se ocorrer.

### Estoque

- tentar saída ou consumo com saldo insuficiente em ambiente controlado;
- validar bloqueio ou tratamento esperado;
- validar ajuste/estorno apenas se o fluxo oficial suportar o caso.

### ERP

- validar indisponibilidade controlada ou credencial inválida em ambiente seguro;
- observar job com falha, health, timeline e diagnóstico;
- validar retry ou reprocessamento permitido pelo fluxo existente.

### Engines

- observar que falha de notificação ou outbox não invalida a transação principal;
- validar que recomendação/alerta não duplica o efeito funcional.

### Wizard

- validar tentativa bloqueada sem `UnidadeProdutiva` ou com pendência crítica;
- confirmar que o Wizard impede avanço indevido.

Para cada falha, registrar:

- como foi provocada;
- resultado esperado;
- evidência;
- restauração do ambiente;
- decisão de continuar ou interromper.

## 19. Passos executáveis hoje com evidência no repositório

| Passo do Dry Run | Interface principal | Evidência de implementação |
| ---------------- | ------------------- | -------------------------- |
| Onboarding e owner | Web + `/api/v1/onboarding/*` | `services/api/core/routers/onboarding.py` |
| Wizard | `/dashboard/implantacao/wizard` + `/api/v1/wizard/*` | `services/api/wizard/router.py` e testes `services/api/tests/unit/wizard/test_wizard_api.py` |
| Campo PWA offline | PWA + `/api/v1/sync/*` | `apps/campo/src/lib/sync/*` e `services/api/tests/unit/agricola/test_field_pwa01_offline_sync.py` |
| Estoque | Web + `/api/v1/estoque/*` | `services/api/operacional/routers/estoque.py` e `apps/web/tests/e2e/estoque-implantacao-assistida.spec.ts` |
| Romaneio | Web + `/api/v1/agricola/romaneios/*` | `services/api/agricola/romaneios/router.py` e `services/api/tests/unit/agricola/test_romaneio_calculo.py` |
| Comercialização | Web + `/api/v1/comercializacoes/*` | `services/api/financeiro/comercializacao/router.py` e `services/api/tests/unit/financeiro/test_comercializacao.py` |
| ERP comum | Web + `/api/v1/integracoes/erp/*` | `services/api/integracoes/erp/router.py` e `services/api/tests/unit/integracoes/test_erp_router.py` |
| Engines | backend assíncrono | testes de outbox/notificações/recomendações |

## 20. Comandos de validação leves

Executar apenas em ambiente controlado e sem credenciais reais:

```bash
git status --short
git diff --check
cd services/api && .venv/bin/pytest tests/unit/wizard/test_wizard_api.py --collect-only -q
cd services/api && .venv/bin/pytest tests/unit/agricola/test_field_pwa01_offline_sync.py --collect-only -q
cd services/api && .venv/bin/pytest tests/smoke/test_estoque_implantacao_runbook.py --collect-only -q
cd services/api && .venv/bin/pytest tests/unit/financeiro/test_comercializacao.py --collect-only -q
cd services/api && .venv/bin/pytest tests/unit/integracoes/test_erp_router.py --collect-only -q
```

Esses comandos validam a existência e a coleta das peças críticas do roteiro. Não substituem a execução assistida do Dry Run.

## 20.1 Classificação de desvios por passo

Todo desvio observado em qualquer passo (não apenas ao final) deve ser classificado imediatamente em uma das cinco categorias, antes de decidir prosseguir:

- `CRÍTICA`: impede o piloto — perda de dados, quebra de RLS/isolamento entre tenants, inconsistência econômica (`CostAllocation`/Dashboard/DRE divergentes da execução), impossibilidade de concluir o fluxo, corrupção de dados. Interrompe a execução.
- `ALTA`: fluxo foi concluído, mas com forte impacto operacional (ex.: retrabalho manual relevante, dado incorreto que exige correção).
- `MÉDIA`: existe contorno operacional aceitável dentro do fluxo oficial.
- `BAIXA`: problema visual ou de usabilidade, sem efeito funcional ou econômico.
- `OBSERVAÇÃO`: melhoria futura identificada; não gera desenvolvimento neste épico nem bloqueia o Dry Run.

Cada desvio registrado deve conter: passo, camada afetada (interface/persistência/regra de negócio/evento/Dashboard/DRE), classificação, evidência e decisão (prosseguir, registrar ressalva ou interromper).

## 21. Encerramento e decisão

Ao final de D+7 consolidar:

- evidências coletadas;
- incidentes e ações corretivas;
- ressalvas abertas;
- pontos fora do escopo que permaneceram fora do teste;
- decisão final.

Classificação final:

- `GO`: cenários críticos aprovados sem bloqueador.
- `GO COM RESSALVAS`: roteiro executado com limitações controladas.
- `NO-GO`: houve falha que comprometeu segurança, isolamento, integridade, continuidade operacional, estoque, financeiro, sincronização ou governança.

## 22. Decisão operacional deste runbook

Decisão vigente:

- o Dry Run do primeiro piloto deve ser executado com este runbook como roteiro único;
- o plano mestre continua sendo a referência executiva;
- a operação deve ser assistida;
- logs técnicos seguem provider-specific e suporte/backoffice;
- a ausência de suíte única não impede este ciclo, desde que o roteiro manual seja seguido e as evidências sejam coletadas.
