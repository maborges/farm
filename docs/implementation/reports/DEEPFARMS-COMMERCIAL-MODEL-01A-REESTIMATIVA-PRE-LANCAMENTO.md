# DEEPFARMS-COMMERCIAL-MODEL-01A — Reestimativa pré-lançamento

**Modalidade:** revisão documental e técnica, somente leitura quanto à aplicação. Este relatório é a única alteração produzida nesta tarefa; nenhum código, banco, migration, serviço ou configuração foi alterado.

**Base:** auditoria `DEEPFARMS-COMMERCIAL-MODEL-01-AUDITORIA-IMPACTO-CUSTO.md` e estruturas atuais do repositório, em 2026-10-31. Premissa atualizada pelo solicitante: o produto ainda não tem assinantes comerciais.

**Decisão de produto ainda aberta:** a estimativa separa acessos nomeados de acessos simultâneos. Nenhuma das opções está aprovada neste documento.

## 1. Resumo executivo

A estimativa provável original para a Alternativa B é **544 h**. Retirando a migração de contratos comerciais vigentes, negociação com assinantes atuais, proteção de preços legados e migração de faturamento comercial histórico, a nova estimativa provável é:

- **436 h com acessos nomeados**, redução de **108 h (19,9%)** frente às 544 h originais.
- **452 h com acessos simultâneos**, redução de **92 h (16,9%)** frente às 544 h originais. Este cenário acrescenta 16 h para enforcement concorrente de sessão e seus casos de corrida/offline em comparação ao modelo nomeado.

As novas faixas para acessos nomeados são **238 / 436 / 716 h** (mínimo/provável/máximo). Para acessos simultâneos, são **250 / 452 / 744 h**. A amplitude continua relevante porque a fonte e a regra de área cobrável, a semântica de acesso e o calendário de cobrança ainda não foram decididos.

**Não é necessário reconstruir billing.** Há modelos e fluxos utilizáveis de plano, assinatura, alteração de plano, fatura, gateway, sessão, onboarding e controles de limite. É necessário adicionar a regra de preço por área e o registro verificável de cotação/aceite/versão do contrato; ligar alteração de área e compra de acesso a recálculo confiável; e cobrir essas mudanças nos testes. As tabelas e migrations em uso devem continuar compatíveis com testes e dados de desenvolvimento.

### Custo provável de implementação

| Modelo de acesso | Horas prováveis | R$ 80/h | R$ 150/h | R$ 250/h |
|---|---:|---:|---:|---:|
| Nomeado | 436 | R$ 34.880 | R$ 65.400 | R$ 109.000 |
| Simultâneo | 452 | R$ 36.160 | R$ 67.800 | R$ 113.000 |

Valores de mão de obra sem impostos, contingência, assessoria comercial/jurídica, tarifas do gateway ou custos operacionais. Não se prevê nova infraestrutura nem duplicação de serviços existentes.

## 2. Base técnica e simplificação pré-lançamento

O código já contém `PlanoAssinatura`, `AssinaturaTenant`, `MudancaPlano`, `PlanoPricing`, `Fatura`, `CobrancaAsaas` e `SessaoAtiva`, além de rotas de billing, onboarding, alterações de plano, equipe e webhooks. A assinatura e a fatura são criadas nos fluxos existentes. A tabela `PlanoPricing` representa faixas de quantidade de usuários, não preço por hectares. `limite_hectares` é um campo do plano, mas não consolida área elegível nem constitui, por si só, uma fórmula comercial aplicada.

`usuarios_contratados` e `require_limit("max_usuarios")` já sustentam um limite de usuários cadastrados/ativos. `sessoes_ativas` registra sessões e heartbeat; isso não comprova aplicação de um limite simultâneo no login. Essa distinção é a principal diferença de custo entre as duas opções.

### Precisão sobre `tipo_assinatura` e multiplicidade

A auditoria de código confirma **um contrato principal por Tenant como convenção predominante**, mas também revela divergência que impede tratar o campo como enum consolidado:

| Valor | Evidência no código | Conclusão segura |
|---|---|---|
| `TENANT` | É o default Python do model; criação no `OnboardingService` e nos fluxos backoffice; billing, gates de módulo e vários serviços filtram por esse valor. | Valor canônico predominante para a assinatura principal da conta. |
| `ADICIONAL` | Consta no comentário do model e em comentários de migrations antigas; não foi encontrado fluxo de criação/compra que grave esse valor. | Intenção documentada para add-on, sem evidência de que o add-on esteja implementado como assinatura nessa tabela. |
| `PRINCIPAL` | Valor default de migrations históricas e ainda consultado por dois caminhos do router de onboarding, registrado no `main.py`; também aparece em fixture de teste. | Valor legado ainda referenciado. Está incompatível com o serviço atual de onboarding que cria `TENANT`; não deve ser considerado alias funcional sem normalização/validação. |
| `GRUPO` | Migrations antigas tentaram assinatura por grupo e há um lookup residual em `MudancaPlanoService`. A migration `rename_fazendas_to_unidades_produtivas` remove as tabelas de grupos e a coluna `grupo_fazendas_id`; a migration posterior atualiza o comentário do campo para `TENANT`/`ADICIONAL`. | Conceito de grupo não faz parte da estrutura atual do model e o lookup residual parece obsoleto. |

O campo ORM é `String(20)`, não enum, e não há `CheckConstraint` de valores no model. A constraint `uq_assinatura_tenant_tipo` limita a **uma linha por par `(tenant_id, tipo_assinatura)`**, sem considerar status; portanto também impede reutilizar uma segunda linha do mesmo tipo depois de uma linha cancelada, a menos que o fluxo reative/atualize a existente. A descrição da constraint diz “uma assinatura TENANT ativa”, mas a unicidade declarada é mais ampla: vale para qualquer status.

As migrations registram `PRINCIPAL` como server default histórico. A migration que atualiza o comentário para `TENANT`/`ADICIONAL` passa `existing_server_default='PRINCIPAL'`, sem trocar esse default. O model declara default Python `TENANT`, mas não `server_default`. Assim, inserts ORM atuais que usam o default ou definem explicitamente o valor tendem a escrever `TENANT`; inserts SQL que omitam a coluna podem receber `PRINCIPAL`, conforme o schema efetivamente migrado. **Sem consultar o banco de cada ambiente, não se afirma quais valores já estão gravados nem qual default está aplicado nele.**

**Conclusão para o modelo comercial:** não contar com múltiplas assinaturas `ADICIONAL` nem com assinaturas `GRUPO` para consolidar fazendas. O caminho suportado mais claro no código é uma assinatura `TENANT` por conta, enquanto a inclusão e cobrança de extras exigem regra/modelagem explicitamente aprovada. Os usos residuais de `PRINCIPAL` e `GRUPO`, o default de banco e a semântica de status devem ser reconciliados antes de lançar billing automático. Essa compatibilidade está contemplada nas entregas de persistência, billing e homologação; a revisão foi somente de leitura e não executou testes.

As ofertas e gates comerciais também estão distribuídos entre dados de plano, permissões de módulos/tier, catálogo no backend, constantes de pacotes na Web e seed de planos. A configuração do lançamento deve ter uma fonte aprovada e evitar valores divergentes entre apresentação, cálculo da API e billing. “Todos os módulos gerais incluídos” ainda precisa de definição; não se deve remover gates de módulos pagos nem tiers de profundidade antes dessa decisão.

**Simplificação segura antes do lançamento:** simplificar o catálogo e a política de novos contratos, não reconstruir o domínio. Publicar somente a oferta comercial aprovada; não manter fluxo de preço legado para assinantes que não existem; centralizar a cotação comercial na API e fazer Web/backoffice apresentarem o mesmo resultado. A matriz antiga por usuário pode deixar de ser aplicada a novas assinaturas quando a nova regra estiver pronta. Não apagar tabelas, colunas, migrations, rotas ou dados de desenvolvimento como parte dessa simplificação: primeiro é preciso provar que nenhuma aplicação, teste, seed, webhook ou fluxo interno ainda os utiliza. Não consolidar Tenant e identidade global do usuário por conveniência.

No banco, a alternativa de menor risco é estender as estruturas atuais com migration aditiva e reversível, se os novos campos de cotação, versão, aceite e vigência não couberem adequadamente nos registros já existentes. Não é necessário importar ou reconstruir faturas comerciais históricas; faturas de desenvolvimento e suas fixtures continuam sujeitas à compatibilidade de migrations e testes.

## 3. Reestimativa das 12 entregas

“Original” é a estimativa **provável** da auditoria. “Revisado — nomeado” é o cenário de referência para estimar o lançamento sem simultaneidade assumida. A coluna simultânea substitui o valor revisado daquela linha e mostra o total correspondente quando aplicável. As horas são esforço de implementação, revisão, testes e integração da respectiva frente, sem dupla contagem intencional.

| # | Entrega | Original provável (h) | Revisado nomeado min/prov/máx (h) | Simultâneo provável (h) | Diferença e justificativa |
|---:|---|---:|---:|---:|---|
| 1 | Serviço de preço por área, acessos e adicionais | 56 | 28 / 48 / 72 | 48 | −8. Continua sendo necessário cálculo determinístico por área e extras. Cai esforço de combinar contratos/preços antigos; precisa manter compatibilidade da API de billing/plano usada pelo sistema. |
| 2 | Persistência: cotação, aceite, versão de preço e vigência | 48 | 16 / 36 / 60 | 36 | −12. Ainda se registra a decisão comercial de cada nova contratação e alteração futura, com histórico imutável suficiente para explicar a fatura. Não há importação nem preservação de contratos comerciais legados. Migrations devem aceitar estado de desenvolvimento existente. |
| 3 | Cadastro e consolidação de propriedades/área elegível | 56 | 24 / 48 / 80 | 48 | −8. A regra de fonte, sobreposição, arrendamento/compartilhamento e vigência é igual sem base comercial. Reduzem-se conversões de base e reconciliação com cadastros de clientes; não se reduz a validação de área. |
| 4 | Controle de acesso | 48 | 20 / 32 / 52 | 48 | Nomeado: −16, aproveita convites/usuários ativos e limitações existentes, mas inclui associação Tenant, compra/remoção de assentos e recálculo. Simultâneo: mantém 48 h prováveis (32 / 48 / 80 h min/prov/máx); acrescenta enforcement no ciclo de sessão/login, corrida de logins, expiração, revogação e efeitos offline. |
| 5 | Venda/administração de acessos adicionais | 32 | 12 / 24 / 40 | 24 | −8. Compra, alteração, cancelamento e renovação dos adicionais continuam. Não haverá migração ou negociação individual de pacotes atuais. |
| 6 | Recálculo central, prévia, aceite e idempotência | 48 | 20 / 44 / 68 | 44 | −4. Recálculo continua obrigatório tanto quando muda a área quanto quando se contratam acessos adicionais. Removem-se apenas transições e salvaguardas de preço de uma carteira legada. |
| 7 | Billing, faturas, vigência e gateway existente | 56 | 20 / 40 / 68 | 40 | −16. Preserva-se cobrança futura, ajuste do valor, webhooks, idempotência, falhas e faturas do novo modelo com o gateway existente. Sai migração de faturamento histórico e compatibilidade de cobrança de contratos comerciais antigos. Política de prorrata ainda precisa ser aprovada. |
| 8 | Backoffice: catálogo, contratos, exceções e auditoria | 36 | 14 / 28 / 48 | 28 | −8. Ainda é necessário configurar a oferta, consultar cotação/aceite e auditar exceções de novos clientes. Saem fluxos para renegociar, classificar e preservar condição especial de assinantes atuais. |
| 9 | Interfaces do assinante: onboarding, billing, propriedade e aceite | 40 | 16 / 32 / 56 | 32 | −8. Novos produtores precisam informar/revisar área, entender preço e aceitar termos, incluindo alteração posterior. Não é preciso construir comunicação, aceite ou escolha de migração da base atual. |
| 10 | Campo PWA: estado de acesso e sync offline | 24 | 12 / 20 / 36 | 20 | −4. Continua obrigatório preservar fila local e sincronizar operações autorizadas quando a rede voltar. Reduz o cenário de coexistência de políticas contratuais antigas. |
| 11 | Testes automatizados e regressão multi-tenant/billing/offline | 64 | 40 / 60 / 96 | 60 | −4. Redução pequena: não há regressão de migração comercial, mas permanecem testes de segurança, RLS/tenant, billing/webhooks, autorização, assentos, mudanças de área e adicional, idempotência e Campo offline. |
| 12 | Homologação, compatibilidade e publicação controlada | 32 | 16 / 24 / 40 | 24 | −8. Sem rollout por coorte de contratos comerciais, comunicações ou reconciliação de faturas legadas. Continua homologação do onboarding ao pagamento, migrations sobre dados de desenvolvimento, regressão e publicação usando o processo atual. |
|  | **Total provável** | **544** | **238 / 436 / 716** | **452** | **−108 h nomeado / −92 h simultâneo** contra o provável original. |

### Faixas revisadas e custos

As faixas são planejamento, não orçamento fechado. Assumem decisões de negócio aprovadas antes da implementação, reuso dos serviços existentes e ausência de reconstrução de dados comerciais legados. O máximo inclui ambiguidade residual em cadastro/área, ajustes entre API/Web/Campo, integrações e retrabalho de compatibilidade.

| Modelo | Mínimo (h) | Provável (h) | Máximo (h) |
|---|---:|---:|---:|
| Acesso nomeado | 238 | 436 | 716 |
| Acesso simultâneo | 250 | 452 | 744 |

| Modelo | Taxa | Mínimo | Provável | Máximo |
|---|---:|---:|---:|---:|
| Nomeado | R$ 80/h | R$ 19.040 | R$ 34.880 | R$ 57.280 |
| Nomeado | R$ 150/h | R$ 35.700 | R$ 65.400 | R$ 107.400 |
| Nomeado | R$ 250/h | R$ 59.500 | R$ 109.000 | R$ 179.000 |
| Simultâneo | R$ 80/h | R$ 20.000 | R$ 36.160 | R$ 59.520 |
| Simultâneo | R$ 150/h | R$ 37.500 | R$ 67.800 | R$ 111.600 |
| Simultâneo | R$ 250/h | R$ 62.500 | R$ 113.000 | R$ 186.000 |

Comparação ao provável original de 544 h:

| Taxa | Original (544 h) | Revisado nomeado (436 h) | Revisado simultâneo (452 h) |
|---:|---:|---:|---:|
| R$ 80/h | R$ 43.520 | R$ 34.880 | R$ 36.160 |
| R$ 150/h | R$ 81.600 | R$ 65.400 | R$ 67.800 |
| R$ 250/h | R$ 136.000 | R$ 109.000 | R$ 113.000 |

## 4. Atividades eliminadas do escopo

- Inventário e classificação de contratos comerciais vigentes para decidir quais serão migrados.
- Negociação individual, aceite de transição ou comunicação de mudança de preço com assinantes comerciais existentes.
- Preservação de preço legado, grandfathering, exceções de renovação e convivência de novos e antigos preços por coorte.
- Conversão/importação de faturamento comercial histórico, conciliação de faturas antigas e reconstrução de cobrança passada.
- Rollout de migração comercial progressiva e suporte específico de conversão da base.

Isso **não** elimina migrações Alembic aditivas necessárias à evolução do esquema, compatibilidade dos modelos ativos, fixtures, seeds ou dados de desenvolvimento. Também não elimina histórico de cotação, aceite, preço e vigência para os contratos novos, nem a trilha de faturas gerada a partir do lançamento.

## 5. Atividades mantidas e obrigatórias para lançamento

- Resolver a conta comercial (Tenant ou agregador de múltiplos tenants) e a fonte da área cobrável; implementar consolidação sem dupla contagem entre unidades, propriedades, exploração e registros fundiários.
- Criar a regra canônica de preço por área, faixas/bordas, arredondamento, extras e composição de preço; a API é a autoridade para prévia e cobrança.
- Recalcular preço e exigir fluxo de prévia/aceite/vigência após alteração de área e contratação/alteração de acessos adicionais. Tornar eventos repetidos seguros com idempotência, e não cobrar usando somente estado de tela ou valores enviados pelo cliente.
- Persistir versão de preço/fórmula e base comercial aceita suficiente para explicar cobranças e resolver disputa futura.
- Emitir e processar cobrança nova usando gateway e fluxos existentes, tratar webhooks e falhas sem duplicar cobrança, e guardar fatura futura vinculada ao contrato vigente.
- Aplicar limites de usuários/assentos escolhidos sem enfraquecer RBAC, RLS, estado da assinatura ou permissões granulares.
- Manter sincronização Campo PWA offline e fila local; definir como mudança/expiração de acesso afeta operações já capturadas e sincronização posterior.
- Preservar migrations, modelos e dados de desenvolvimento ainda utilizados; testar upgrade de schema e fluxos de fixture sem reset destrutivo.
- Cobrir segurança, isolamento multi-tenant/RLS, billing, autorização/permissões e offline Campo antes de publicação.

## 6. Acessos: custo e diferença de comportamento

| Alternativa | Estimativa provável da entrega 4 | O que se limita | Efeito no lançamento |
|---|---:|---|---|
| **Usuários nomeados** | **32 h** | Contas ativas/vinculadas a um Tenant até os assentos comprados, com convites e remoção governados. | Menor custo e encaixe mais direto no limite de usuários ativos já usado. Não restringe uma pessoa nomeada a uma única sessão/dispositivo simultâneo. É a hipótese base da estimativa total, não uma decisão comercial. |
| **Usuários simultâneos** | **48 h** | Sessões consideradas ativas por Tenant (ou escopo definido) dentro do limite contratado. | Exige enforcement no login/criação de sessão, consistência sob logins concorrentes, definição de heartbeat/expiração e regra quando o limite é excedido. `SessaoAtiva` já existe, porém existência de tabela não prova que o teto esteja aplicado. |

No modelo simultâneo, uma pessoa pode precisar de mais de uma sessão e uma conta nomeada pode usar dispositivos diferentes; é preciso decidir a unidade de contagem, compartilhamento entre unidades, prazo de inatividade, encerramento remoto e comportamento no Campo sem rede. O custo incremental de 16 h é só a diferença da entrega de acesso e das integrações diretamente ligadas a ela; incerteza comercial pode deslocar outras linhas e está refletida na amplitude da faixa total.

## 7. Decisões comerciais que impedem estimativa mais precisa

1. **Assinante e consolidação:** cada Tenant é uma única conta comercial? Será possível consolidar propriedades de tenants distintos? Quem é responsável por aceitar preço e cobrança quando o mesmo usuário pertence a vários tenants?
2. **Área elegível:** qual entidade/campo é canônico (área operacional, explorada ou validada), quem confirma a informação, qual precedência de prova e como entram próprias, arrendadas, parceria, sazonais, compartilhadas, APP e Reserva Legal?
3. **Deduplicação e alteração:** como resolver polígonos e propriedades sobrepostos; mudança passa a valer na data do cadastro, da validação, do aceite ou no ciclo seguinte? Há revisão administrativa em casos ambíguos?
4. **Tabela de preço:** faixas, limites inclusivos/exclusivos, hectares fracionários, precisão e arredondamento, reajuste anual, periodicidade mensal/anual e descontos aprovados.
5. **Acessos adicionais:** usuários nomeados ou simultâneos; quantidade mínima incluída, preço unitário/pacote, alteração para baixo, ciclo de cobrança, usuários temporários/prestadores e compartilhamento entre unidades.
6. **Módulos no plano:** quais funcionalidades são gerais e incluídas em toda faixa? Quais continuam como add-on ou tier de profundidade? IA, clima, integrações e serviços com cobrança de terceiros precisam estar catalogados separadamente.
7. **Vigência financeira:** aumento ou redução de área/acessos altera preço imediatamente ou na renovação? Haverá prorrata, crédito, cobrança proporcional, período de carência ou grace period?
8. **Gateway e documento fiscal:** qual gateway existente será fonte de verdade para recorrência e adicionais; quais meios, webhooks, taxas, retries, nota fiscal e regras tributárias efetivamente serão habilitados?
9. **Onboarding e trial:** teste gratuito, momento de coletar área, exigência de comprovação, início de vigência e cobrança automática após o trial.
10. **Offline e sessão:** regra de autorização quando expirado/alterado offline, limite de sincronização posterior, modo de encerramento de sessão e política de grace period.

Sem essas decisões a estimativa continua ordem de grandeza. As faixas financeiras não incluem assessoria para resolver os itens comerciais, legais ou tributários.

## 8. Riscos remanescentes

- **Preço incorreto por área:** fontes territoriais distintas medem conceitos diferentes; cobrar com soma duplicada ou área não pertencente à operação comercial é risco de produto e disputa. A regra precisa ser explícita e auditável antes de automatizar cobrança.
- **Divergência entre catálogo e runtime:** configurações de planos e gates existem em mais de uma camada. Se catálogo, cálculo e billing divergirem, onboarding pode exibir preço diferente do faturado.
- **Cobrança após evento repetido ou concorrente:** edições repetidas de área, compra repetida de adicionais e webhooks duplicados podem gerar preço/estado/cobrança inconsistentes sem idempotência e transição atômica.
- **Limites de acesso mal definidos:** `usuarios_contratados` é descrito como simultâneo em partes do modelo, enquanto o gate existente conta usuários ativos; produto, UI e regra de acesso podem divergir.
- **Uso no Campo offline:** alterar acesso não pode descartar fila ou operação já capturada; permitir sincronização posterior não deve virar bypass de autorização.
- **Compatibilidade de desenvolvimento:** migrations e testes podem depender de colunas/valores que pareçam comerciais legados. Excluir tabelas/colunas antes de rastrear referências e dados de desenvolvimento causaria regressão desnecessária.
- **Gateway, fiscal e capacidade operacional:** contratos, tarifas, retries, documentos fiscais e baseline de volume/infra não foram verificados; nenhum custo operacional foi inferido nem nova infraestrutura foi incluída.

## 9. Menor escopo tecnicamente seguro para o modelo comercial completo

1. Aprovar as decisões bloqueadoras de conta, área, tabela de preço, extras, semântica de acesso, vigência, prorrata, gateway e módulos do lançamento.
2. Manter `Tenant`, `PlanoAssinatura`, `AssinaturaTenant`, `MudancaPlano`, `Fatura`, gateways, sessão, permissões e migrations existentes onde ainda usados. Fazer apenas migrations aditivas e preservar dados/fixtures de desenvolvimento.
3. Definir um catálogo de oferta publicado e uma única autoridade de cálculo na API; desligar os antigos preços por usuário para novas ofertas apenas quando consumidores ativos tiverem sido migrados e verificados. Não excluir estruturas antigas nesta entrega.
4. Implementar cálculo determinístico e versionado que consolide a área elegível, o plano/faixa e os adicionais, com validação de tenant e snapshot de cotação/aceite.
5. Usar o fluxo atual de assinatura/mudança e gateway para contratação e cobrança futura; acrescentar a transição necessária para alteração de área e extras com aceite, vigência, idempotência e fatura explicável. Não importar contratos nem faturas comerciais históricas.
6. Aplicar o acesso escolhido (nomeado ou simultâneo) no ponto de enforcement correto e propagar o estado ao Web e Campo sem enfraquecer RLS/RBAC nem perder fila offline.
7. Homologar onboarding, alteração de área, compra/cancelamento de adicionais, cotação→aceite→cobrança, webhooks/retries, isolamento RLS, permissões e sync offline; publicar pelo processo já existente, sem novo serviço, fila, banco ou cluster.

Esse é o menor caminho que entrega o **modelo comercial completo**. Uma simples mudança em valores de plano ou no campo `limite_hectares` não implementa consolidação, recálculo, aceite e cobrança segura.

## 10. Recomendação

Recomendo a Alternativa B em versão pré-lançamento, com **436 h prováveis se adotados usuários nomeados**. A decisão nomeado versus simultâneo deve ser tomada pelo produto antes de fechar o orçamento; se a escolha for simultânea, usar **452 h prováveis**. O cenário nomeado tem menor custo e utiliza mais diretamente o gate já existente de usuários ativos, mas deve ser escolhido conscientemente e descrito como assento por conta, não sessão concorrente.

Não recomendo reconstruir planos, assinaturas ou faturamento, nem apagar estruturas por não haver assinantes comerciais. O ganho de não ter base comercial está em remover migração comercial e simplificar as regras de lançamento. Compatibilidade técnica com dados e testes de desenvolvimento continua necessária. Depois de aprovadas as decisões comerciais, a implementação pode ocorrer no mesmo monólito e nos mesmos serviços existentes.

**Status:** reestimativa para revisão. Nenhuma implementação foi iniciada; aguarda aprovação.

## Referências examinadas

- `docs/implementation/reports/DEEPFARMS-COMMERCIAL-MODEL-01-AUDITORIA-IMPACTO-CUSTO.md` — auditoria e estimativa original.
- `services/api/core/models/billing.py` — planos, assinaturas e faturas.
- `services/api/core/models/plan_changes.py` e `services/api/core/services/plan_pricing_service.py` — faixas atuais por usuários e alterações de plano.
- Migrations `20240312_multi_subscription_rbac.py`, `eacd7ecdb359_fix_missing_assinaturas_tenant_columns.py`, `grupo_assinatura_refactor.py`, `rename_fazendas_to_unidades_produtivas.py` e `c853a6f175f1_add_logo_url_to_unidades_produtivas.py` — evolução e remoção do modelo de assinatura por grupo e defaults/comentários de tipo.
- `services/api/core/models/sessao.py`, `services/api/core/dependencies.py` e `services/api/core/routers/team.py` — sessões e limites de usuários.
- `services/api/core/models/unidade_produtiva.py` e `services/api/core/cadastros/propriedades/propriedade_models.py` — campos existentes de área operacional/explorada.
- `services/api/core/routers/billing.py`, `services/api/core/services/onboarding_service.py`, `services/api/core/services/mudanca_plano_service.py` e `services/api/core/routers/stripe_webhooks.py` — fluxos de billing e alteração existentes.
- `apps/web/src/lib/constants/pacotes.ts`, `apps/web/src/lib/constants/planos.ts`, `services/api/core/constants.py` e `services/api/scripts/initial_load/seed_plans.py` — configurações de plano/módulos em mais de uma camada.
- `docs/architecture/standards/AGRI-DOMAIN-001-territorial-fundiario.md` — fonte e relação entre domínio operacional e fundiário.
- `docs/CAMPO_PWA_01_ARQUITETURA_OFFLINE.md` — requisitos de sincronização offline do Campo.
