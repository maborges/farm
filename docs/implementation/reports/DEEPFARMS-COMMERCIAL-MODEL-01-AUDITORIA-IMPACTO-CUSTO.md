# DEEPFARMS-COMMERCIAL-MODEL-01 — Auditoria de impacto e custo

**Modalidade:** auditoria somente leitura.

**Base:** código do repositório em 2026-10-31. Nenhum banco, dado de produção, configuração ou serviço externo foi consultado ou modificado.
**Premissas comerciais:** valores e faixas da proposta fornecida pelo solicitante; não foram gravados nem tratados como preços aprovados.

## 1. Resumo executivo

O modelo é **tecnicamente viável com evolução controlada**, reutilizando `PlanoAssinatura`, `AssinaturaTenant`, `MudancaPlano`, `Fatura`, os gates de módulo e a trilha de sessões atuais. Não há necessidade comprovada de substituir todo o domínio de billing ou criar uma segunda assinatura.

Há, porém, lacunas reais antes de cobrar por área e acessos adicionais:

- O contrato atual pertence ao `Tenant`; não existe entidade explícita de assinante/produtor que agregue vários tenants. `Usuario` é identidade global e pode pertencer a tenants distintos. A proposta precisa definir se um tenant é sempre uma conta de produtor ou se uma assinatura poderá consolidar propriedades distribuídas por tenants.
- A área operacional pode estar em `UnidadeProdutiva.area_total_ha`, na área georreferenciada, em `ExploracaoRural.area_explorada_ha` ou em relações fundiárias. A norma territorial impede usar imóvel rural e propriedade operacional como fontes intercambiáveis. Hoje não há regra de elegibilidade comercial nem soma consolidada aplicada ao plano.
- A tabela `sessoes_ativas` já registra sessões por token e tenant, mas o login não consulta nem aplica `usuarios_contratados` como teto simultâneo. O gate `max_usuarios` limita convites/usuários ativos, não sessões concorrentes.
- A aplicação tem diversos bloqueios comerciais de módulo e de profundidade por `plan_tier`. Permissões RBAC, acesso por unidade, RLS, estado da assinatura e controles de segurança continuam necessários, mesmo que os módulos gerais passem a constar em todos os planos.
- O sistema possui solicitação/simulação e cobrança por Asaas para mudanças, mas não registra de forma completa e imutável o preço calculado, o preço aceito, o valor faturado e a vigência do novo contrato após uma alteração de área.

**Estimativa para a alternativa recomendada (B):** 300 h mínimo, 544 h provável e 908 h máximo, incluindo desenvolvimento, testes de regressão e homologação/publicação. A R$ 150/h, o cenário provável é R$ 81.600 antes de contingência; com reserva de 25%, R$ 102.000. Não há custo operacional adicional de infraestrutura mensurável no código; taxas de pagamento, suporte e consumo variável dependem de contratos e volume não fornecidos.

**Recomendação:** GO COM RESSALVAS para decidir e detalhar a evolução controlada; não é autorização para implementação. Primeiro devem ser decididas a identidade do assinante, a definição de área elegível, a semântica de acesso e a política de migração/prorrata. Não há dados reais acessíveis nesta auditoria para estimar MRR, margem ou retorno da base atual.

## 2. Diagnóstico do modelo comercial atual

### 2.1. Entidades e escopo do assinante

| Conceito | Implementação encontrada | Consequência para a proposta |
|---|---|---|
| Tenant/conta | `Tenant` contém nome, documento, contato, branding e identificador da conta. | É o escopo proprietário da assinatura e da maioria dos dados operacionais. O código não prova que cada Tenant sempre equivale a uma pessoa produtora. |
| Usuário autenticado | `Usuario` é identidade global, com e-mail único. | Não é sinônimo de produtor nem de Tenant. |
| Associação de usuário | `TenantUsuario` associa usuário, tenant, perfil, proprietário e status. Uma pessoa pode ter mais de um vínculo tenant. | Uma pessoa que administra várias contas não consolida automaticamente as assinaturas nem suas áreas. |
| Assinatura | `AssinaturaTenant` referencia um Tenant e um plano. Há tipos `TENANT`/`ADICIONAL`, além de ciclo e status. | A assinatura única por produtor encaixa-se diretamente somente se o Tenant for formalmente a conta comercial consolidada. |
| Propriedade operacional | `UnidadeProdutiva` é tenant-scoped e tem `area_total_ha`, `area_total_calculada_ha`, tipo e status. | É uma fonte operacional existente, mas pode representar arrendamento/parceria e pode se sobrepor com cadastro territorial relacionado. |
| Cadastro territorial | `Propriedade` e `ExploracaoRural` representam propriedade e vínculo de exploração; este último inclui natureza, vigência e `area_explorada_ha`. | Fornecem contexto de área explorada/contratada, mas exigem reconciliação com unidades produtivas antes de somar. |
| Imóvel rural | É o domínio jurídico/fundiário, com relação N:N via `PropriedadeImovel`. O vínculo tem `area_vinculada` e `percentual_vinculado`. | Não deve ser somado diretamente como se fosse uma área operacional única: um imóvel pode se ligar a mais de uma propriedade e o percentual/vínculo pode expressar compartilhamento. |

Evidências: `Tenant` em `services/api/core/models/tenant.py`; identidade e associação em `services/api/core/models/auth.py:8-72`; criação de usuário, Tenant, owner e assinatura em `services/api/core/services/onboarding_service.py:40-137`; assinatura vinculada a Tenant em `services/api/core/models/billing.py:78-142`; área operacional em `services/api/core/models/unidade_produtiva.py:9-67`; exploração em `services/api/core/cadastros/propriedades/propriedade_models.py:30-84`; vínculo fundiário em `services/api/core/cadastros/propriedade_imovel/models.py:31-105`.

A norma `docs/architecture/standards/AGRI-DOMAIN-001-territorial-fundiario.md:30-105` declara Propriedades como fonte operacional, Imóveis Rurais como fonte fundiária e exige relação N:N. Para cobrança, deve-se definir uma área de exploração comercial consolidada por período, e não somar todos os campos/entidades. Uma regra mínima futura precisa:

1. Escolher uma fonte canônica para hectares elegíveis e uma prioridade/fallback explícita.
2. Usar propriedades/unidades ativas e vínculos de exploração vigentes na data de cálculo.
3. Contabilizar somente área explorada pelo assinante, conforme a política para própria, arrendada, parceria e compartilhada.
4. Não somar simultaneamente `area_total_ha`, polígonos calculados, talhões, `area_explorada_ha` e áreas de imóveis vinculados.
5. Resolver sobreposição espacial ou declarar que o produtor confirma a área consolidada; o modelo atual não contém um procedimento comercial de deduplicação comprovado.

### 2.2. Planos, preço, módulos e limites existentes

- `PlanoAssinatura` já contém preço mensal/anual, módulos incluídos, tier, `limite_hectares`, limite mínimo/máximo de usuários, máximo de fazendas, canais de publicação e trial (`services/api/core/models/billing.py:9-75`).
- `AssinaturaTenant` já contém plano, ciclo, status, `usuarios_contratados`, início/renovação e vínculo opcional com cobrança Stripe (`billing.py:78-142`). Embora o comentário descreva múltiplas assinaturas adicionais, a constraint única `(tenant_id, tipo_assinatura)` permite somente uma linha por tipo e tenant; adicionais por pacote/quantidade precisam caber na assinatura ou ter representação contratual compatível, sem assumir que o esquema atual já representa vários add-ons independentes.
- `PlanoPricing` tem matriz de valores progressivos **por faixa de quantidade de usuários**, não por hectares (`services/api/core/models/plan_changes.py:19-57`). `PlanoPricingService` valida quantidades e soma os preços por faixa (`services/api/core/services/plan_pricing_service.py:19-160,253-319`). Ela não representa diretamente a tabela proposta de preço fixo por faixa de área mais adicionais de acesso.
- `MudancaPlano` guarda origem/destino, quantidade de usuários, valor calculado/proporcional, status, solicitante, aprovação e aplicação (`services/api/core/models/plan_changes.py:60-185`). O serviço de mudança calcula diferença entre planos e usuários, cria solicitação e posteriormente atualiza plano e `usuarios_contratados` (`services/api/core/services/mudanca_plano_service.py:57-124,126-200,360-379`).
- `Fatura` persiste valor, vencimento, status e referência da assinatura (`services/api/core/models/billing.py:145-165`). Não é, por si só, um registro completo da versão do preço contratado ou da fórmula/área que originou a cobrança.
- A API lista planos ativos do banco e expõe uma seleção separada dos planos publicados no site (`services/api/core/routers/billing.py:218-238`). Backoffice mantém cadastro comercial e conversão de leads (`services/api/core/routers/backoffice_tenants.py`, `backoffice_crm_ofertas.py`). Onboarding cria tenant/assinatura e fatura do trial em `onboarding_service.py:116-149`.
- Há fontes paralelas que podem divergir: catálogo/preços de módulos no backend (`services/api/core/constants.py:54-62,134-411`), pacotes estáticos no Web (`apps/web/src/lib/constants/pacotes.ts:1-16,49-92`) e snapshot de planos de carga inicial (`services/api/scripts/initial_load/seed_plans.py:17-48`). A API de catálogo pode usar o banco como fonte, mas não se pode assumir que as telas e cálculos estáticos tenham a mesma fonte de verdade.

**Área:** `limite_hectares` existe no plano e no schema, mas a busca do código mostra uso na definição/edição e não um gate operacional que compare área consolidada. Os gates identificados para limites são `max_fazendas`, `max_usuarios`, categorias e armazenamento (`services/api/core/dependencies.py:1144-1230`). Criação de unidade usa `max_fazendas` (`services/api/core/routers/unidades_produtivas.py:42,50,126`; também `UnidadeProdutivaService._check_limite_unidades()` em `services/api/core/services/unidade_produtiva_service.py:31-67`). Portanto, trocar limite de quantidade de fazendas por área requer regra nova e mudança de API/fluxo, não apenas preencher `limite_hectares`.

### 2.3. Módulos comerciais versus acesso operacional

O backend define módulos vendáveis em `Modulos` e `ModuloMetadata.CATALOGO` (`services/api/core/constants.py:54-112,134-411`). Dependências `require_module()` consultam os módulos da assinatura e respondem 402 quando não contratado (`services/api/core/dependencies.py:625-703`); também existe `require_tier()` para profundidade funcional (`dependencies.py:705-785`). O inventário encontra centenas de usos/referências de `require_module`, sem fazer uma contagem de rotas únicas.

O frontend replica IDs e metadados em `apps/web/src/lib/constants/modulos.ts:6-56,72-130`, além de aplicar visibilidade por módulo/tier (`apps/web/src/hooks/use-has-tier.ts:13-49`, `use-visible-navigation.ts`). Essa replicação precisa ser tratada para não exibir uma função como incluída enquanto a API a bloqueia.

| Tipo de bloqueio | Exemplos no código | Tratamento proposto sob “todos os módulos gerais incluídos” |
|---|---|---|
| Comercial por módulo | `require_module`, `require_any_module`, `require_all_modules`; módulos e extensões no plano. | Preservar o mecanismo e incluir nos planos os módulos gerais efetivamente disponíveis. Manter separáveis extensões externas pagas, ERP/IoT e serviços especiais conforme decisão comercial. |
| Comercial por tier | `require_tier`, `PlanTier` e hooks Web. | Definir quais profundidades passam a fazer parte de todos os planos. Se não houver diferenciação de produto, remover só gates comerciais de tier; nunca usar tier como autorização de segurança. |
| Limites operacionais | máximo de unidades, usuários, categorias, storage. | Continuar ativos se a proposta mantiver limites; substituir somente os limites explicitamente abolidos, com política de transição. |
| Segurança/tenant | RLS, claims, perfis RBAC e permissões tenant/unidade. | Permanecem obrigatórios e independentes do pacote comercial. Ter o módulo contratado não concede permissão de usuário nem acesso a qualquer propriedade. |
| Disponibilidade funcional | Algumas rotas/módulos podem estar incompletos, externos ou não configurados. | Não vender como recurso operacional simplesmente porque o ID consta no catálogo; inventariar disponibilidade e pré-requisitos antes de publicar a lista comum. |

Um catálogo interno marca IA, IoT, ERP, avaliação, hedging e outros recursos com preços-base ou como extensão, mas isso não confirma implementação operacional, licença, custo efetivo nem que o preço esteja sendo cobrado hoje. Esses valores de constantes não são usados aqui como cotação comercial.

### 2.4. Faturamento e fluxo atual de mudanças

O fluxo existente oferece simulação e solicitação. `POST /billing/mudancas-plano/simular` retorna valores e condições; `/solicitar` registra a mudança e pode criar cobrança Asaas (`services/api/core/routers/plan_changes.py:30-121`). A aplicação do upgrade/downgrade altera o plano e usuários na assinatura (`mudanca_plano_service.py:360-379`).

Isso é uma base reutilizável, mas difere do fluxo proposto em pontos materiais:

- Hoje a quantidade negociada é `usuarios_destino`; não é a área consolidada nem pacote de assentos adicionais.
- Não foi encontrado evento central/idempotente que recompute preço em todos os eventos de propriedade citados na proposta.
- Não há confirmação persistida específica do assinante para a nova área/preço antes de aumento por cadastro/alteração territorial.
- A fatura guarda valor e vencimento, mas não snapshots de área, tabela de preços, adicionais, versão da fórmula ou aceite correspondente.
- O serviço calcula proporcional usando diferença mensal e dias restantes, mas um aumento por área ocorrido durante ciclo precisa definir vigência, cotação/aceite, prorrata e próximo vencimento sem editar faturas emitidas.
- A existência de referências a Stripe e Asaas não permite confirmar credenciais, modalidade contratual, taxas, status operacional dos gateways ou reconciliação em produção; nada disso foi testado.

## 3. Inventário técnico com evidências

| Componente | Evidência principal | Reuso e lacuna |
|---|---|---|
| Planos | `services/api/core/models/billing.py:9-75`; `/billing/plans` em `core/routers/billing.py:218-238` | Reusar entidade/catalogação. Novo contrato precisa precificação por área e módulos comuns sem duplicar catálogo em arquivos estáticos. |
| Assinatura | `billing.py:78-142` | Reusar uma assinatura principal por Tenant; definir se assinante = Tenant. Não criar tabela paralela de assinatura. |
| Precificação existente | `core/models/plan_changes.py:19-57`; `core/services/plan_pricing_service.py:19-160` | Serviço isolado reutilizável como referência, mas sua dimensão é quantidade de usuários, não hectares/adicionais. Alterar sem reinterpretar dados históricos. |
| Mudança e trilha comercial | `core/models/plan_changes.py:60-185`; `core/services/mudanca_plano_service.py:57-124,126-200,360-379` | Reutilizar estados e aprovação/pagamento; estender para valor/área aceitos, vigência e idempotência. |
| Cobrança/faturas | `core/models/billing.py:145-165`; `core/services/asaas_service.py`; `core/routers/webhooks_asaas.py` | Reusar gateways/webhooks existentes. Custos e funcionamento em produção não verificados. Preservar faturas e eventos existentes. |
| Usuário/tenant/RBAC | `core/models/auth.py:8-72`; `core/models/tenant.py` | `Usuario` global e `TenantUsuario` controla vínculo e perfil. Não fundir identidade, assinatura e produtor sem decisão de domínio. |
| Área operacional | `core/models/unidade_produtiva.py:9-67`; `core/cadastros/propriedades/propriedade_models.py:60-84` | Reutilizar valores cadastrados após política de consolidação e vigência; hoje não formam base comercial única. |
| Propriedade–imóvel | `core/cadastros/propriedade_imovel/models.py:31-105`; norma AGRI-DOMAIN-001 | Não usar somatório jurídico paralelo ao operacional; deduplicar com relações oficiais e regras de uso. |
| Cadastro de unidade | `core/services/unidade_produtiva_service.py:31-67`; `core/routers/unidades_produtivas.py` | Atualiza/cria unidade com gate de quantidade de unidades; incluir ponto de cálculo e aceite não é configuração simples. |
| Sessões | `core/models/sessao.py:8-118`; token/sessão em `core/services/auth_service.py:350-385,470-497`; heartbeat e validação em `core/routers/auth.py:91-178`, `core/dependencies.py:320-365` | Reaproveita persistência, expiração/revogação e heartbeat. Ainda falta aplicação concorrente do teto comercial no login. |
| Limite de usuários atuais | `core/dependencies.py:1209-1229`; convite em `core/routers/team.py:293` | Gate conta `TenantUsuario` ativo para impedir novos vínculos; não conta sessões. O nome “simultâneo” no billing não muda esse comportamento. |
| Web assinante | `apps/web/src/components/billing/change-plan-dialog.tsx`; `apps/web/src/app/(dashboard)/dashboard/settings/billing/page.tsx` | Já mostra planos/limites e confirmação da solicitação. Ainda usa dados de plano e quantidade de usuários, sem fluxo de revisão de área consolidada. |
| Backoffice | `apps/web/src/app/(dashboard)/dashboard/backoffice/plans/page.tsx`; `services/api/core/routers/backoffice_tenants.py`; `backoffice_plan_changes.py` | Reusar CRUD e gestão de mudanças. Incluir configuração de faixas/preços e trilha de aceite. |
| Onboarding | `services/api/core/services/onboarding_service.py:40-149`; `core/routers/onboarding.py` | Cria primeiro Usuario, Tenant, vínculo Owner e assinatura. Deve coletar/confirmar dados de área sem assumir que o usuário representa uma única entidade produtora. |
| Campo PWA | `apps/campo` e `docs/CAMPO_PWA_01_ARQUITETURA_OFFLINE.md`; sync API | Mantém operação local e sincroniza depois. Revogar/alterar assentos não pode apagar ou descartar operação offline já registrada; o que pode continuar offline e sincronizar precisa ser explicitado. |

**Limitação do inventário:** os arquivos do PWA Campo foram localizados pela arquitetura e fluxo de sincronização, mas a auditoria não fez análise linha a linha de todos os formulários/sync handlers. Não há evidência de que o PWA aplique licença de assento no dispositivo offline. A estimativa considera um ajuste de compatibilidade, não uma reescrita.

## 4. Matriz de impacto arquitetural

| Componente | Situação atual | Mudança necessária | Classe | Complexidade | Risco |
|---|---|---|---|---|---|
| Entidade assinante e Tenant | Assinatura por Tenant; usuários globais vinculados a um ou mais tenants. | Decidir e validar se Tenant será a conta do produtor; se um produtor unir vários tenants, modelar ownership/agrupamento, autorização e RLS antes da consolidação. | Regra de domínio/API e possivelmente banco | Alta | Alto |
| Faixas/limites de área | Campo de hectares existe, sem consolidação nem enforcement comercial identificado. | Definir limites inclusivos e regra para áreas decimais; hoje há lacunas nas faixas propostas entre 20 e 21, 100 e 101, 300 e 301, etc. Definir hectares inteiros ou intervalos contínuos. | Regra de negócio/API | Alta | Alto |
| Consolidação de propriedades | Área em fontes operacionais e de exploração diferentes. | Definir fonte única, elegibilidade de próprios/arrendados/parceria/compartilhados, vigência, deduplicação e governança de dado confirmado. | Regra de negócio/API/migration possível | Alta | Alto |
| Plano e módulos comuns | Planos guardam listas de módulos; dezenas de gates comerciais; `plan_tier` afeta funcionalidades. | Preencher módulos gerais nos planos e manter os gates de segurança. Revisar gates de tier e disponibilidade real, e tirar divergência entre backend/Web. | Configuração/regra de negócio/interfaces | Média/Alta | Alto |
| Limite de acessos | Sessões registradas; limite atual de usuários ativos do tenant. | Decidir usuários nomeados, sessões concorrentes ou dispositivos; se simultâneo, validar atomicidade no login, usuários distintos e sessões expiradas. | Regra/API; banco possivelmente já suficiente | Alta | Alto |
| Adicionais de acesso | `usuarios_contratados` e alteração por mudança de plano existem. | Produto e preço dos pacotes adicionais, contratação, renovação, cancelamento, compatibilidade de cobrança e vigência. | Regra/API/Backoffice/Web | Média/Alta | Médio/Alto |
| Cálculo central | Pricing atual isolado por faixa de usuários. | Criar cálculo versionado e determinístico por área + adicionais + extras, com uma única implementação de backend e contrato de cotação. | Regra/API e possível banco | Alta | Alto |
| Recálculo em eventos | Nenhum mecanismo central observado para eventos de composição/área. | Disparar após cadastro, edição, desativação/desvinculação e alteração de extra; idempotência e concorrência; manter cotação e aceite pendentes se houver aumento. | Novo mecanismo indispensável | Alta | Alto |
| Contrato e vigência | Plano/ciclo e timestamps; solicitações guardam valores calculados. | Distinguir calculado, contratado e faturado; gravar versão da regra, base de área, aceite, vigência e preservar snapshot da fatura. Aplicar apenas na vigência acordada. | Banco/migration e regra | Alta | Alto |
| Faturamento | Faturas, Asaas, eventos e mudanças de plano existentes. | Integrar novo delta e adicionais sem recalcular fatura emitida; tratar webhook idempotente, falha e reconciliação. | Regra/API/migration possível | Alta | Alto |
| Web/backoffice | Billing, editor de planos, conversão CRM já existem. | Prévia de área/preço, aceite do aumento, gestão de adicionais, exceções corporativas e histórico/auditoria. | Interface/API | Média | Médio |
| Campo PWA | Offline-first com fila de sincronização. | Definir políticas de sessão/licença no offline, grace period e sincronização de operações previamente autorizadas. | API/Campo | Média/Alta | Alto |
| RLS/RBAC | Tenant/RLS e perfil por tenant/unidade existem. | Preservar invariantes; qualquer consolidação de tenants exige novo modelo de autorização seguro, não consultas cross-tenant irrestritas. | Segurança | Alta | Alto |
| Infraestrutura | FastAPI, PostgreSQL e Redis no stack; KVM4 informado pelo solicitante. | Não há necessidade comprovada de nova infraestrutura. Medir baseline e carga antes de ajustar capacidade. | Nenhuma alteração comprovada | Baixa por ora | Incerto |

## 5. Riscos e bloqueadores de decisão

1. **Definição de produtor assinante (bloqueador comercial/técnico):** se múltiplos estabelecimentos ou unidades estiverem no mesmo Tenant, a arquitetura se encaixa sem agrupar assinaturas. Se as propriedades hoje forem tenants diferentes, a proposta não pode ser entregue com simples alteração de preço: haverá decisões de ownership, migração, administração e RLS multi-tenant.
2. **Área cobrável e duplicidade:** a norma territorial e o modelo não garantem que cada unidade, exploração e vínculo fundiário correspondam a áreas não sobrepostas. Cobrar sobre `area_total_ha` sem reconciliação pode duplicar arrendamentos compartilhados ou incorporar APP/reserva/área não explorada sem autorização comercial.
3. **Definição das bordas:** a tabela proposta usa faixas inteiras, mas a área é decimal (4 casas na unidade operacional). Exemplos de lacunas: 20,0001–20,9999 ha, 100,0001–100,9999 ha, e equivalentes nas demais bordas. “Até 20” seguido de “21–100” não define essas áreas.
4. **“Acessos simultâneos” não está implementado:** login cria registro de sessão sem checar um teto de assinatura. Um usuário pode ter mais de uma sessão/token; sessões de diferentes frontends e dispositivos precisam de semântica inequívoca. Campo offline não obedece uma revogação em tempo real enquanto desconectado.
5. **Transição de assinantes atuais:** não foram consultados dados de produção, preços vigentes, ofertas customizadas nem faturas. Migração gradual precisa preservar preço/condições contratadas, escolher opt-in/renovação e não alterar cobrança passada.
6. **Aumento automático exige consentimento e prova:** mudanças de área não podem aumentar valor faturado antes de exibir nova base/valor e registrar aceite. Um evento repetido não pode criar múltiplas cobranças.
7. **Fontes paralelas de preço:** backend, catálogo estático do Web e seed/snapshot têm funções diferentes e podem divergir. Um cálculo com regras duplicadas quebraria o requisito de valor único entre interface, API e billing.
8. **Módulo não equivale a recurso disponível:** vários IDs são descritos como extensões ou dependem de provedores, licença, credenciais ou componentes em desenvolvimento. “Todos os módulos” precisa ser limitado ao que está implementado e habilitável; RBAC/RLS jamais deve ser removido como parte da oferta.
9. **Custos variáveis e suporte:** não existem nesta auditoria dados de gateway, atendimento, armazenamento por assinante, tickets ou custo de APIs que permitam margem líquida ou ponto de equilíbrio real.

## 6. Viabilidade de acessos simultâneos

`SessaoAtiva` armazena um token hash único, usuário, tenant, unidade ativa, heartbeat, expiração e status (`services/api/core/models/sessao.py:8-118`). O fluxo de autenticação cria sessões (`auth_service.py:350-385,470-497`); o backend valida/revoga sessão e o heartbeat renova expiração (`core/dependencies.py:320-365`; `core/routers/auth.py:91-178`). Isso fornece base para medir sessões.

Não se comprovou enforcement do limite simultâneo no login. `require_limit("max_usuarios")` conta vínculos ativos `TenantUsuario` e é aplicado ao endpoint de convites/equipe (`core/dependencies.py:1209-1229`; `core/routers/team.py:293`). A assinatura contém `usuarios_contratados`, porém esse valor é propagado às claims e consumido na simulação de mudança, sem contagem de sessões concorrentes no ponto de autenticação.

| Alternativa | Como conta | Vantagens | Limitações/risco | Adequação |
|---|---|---|---|---|
| Usuários nomeados | Membros ativos de `TenantUsuario`; cobrança por assento permitido. | Simples, auditável, previsível para produtor e equipe; funciona entre propriedades do mesmo tenant. | Não restringe quantas sessões/dispositivos um usuário abre; exige política para convites e desativação. | **Mais recomendável para primeira versão.** O código já tem associação e gate de membros. |
| Usuários simultâneos | Usuários distintos com sessão ativa/heartbeat vigente por tenant. | Corresponde literalmente à tabela comercial; assentos podem ser compartilhados em turnos. | Precisa contar usuários distintos, expirados e usuários com múltiplos tokens; corrida em logins simultâneos exige reserva atômica/lock; cliente pode se sentir desconectado. Não funciona como bloqueio instantâneo offline. | Viável, mas custa mais e requer regras claras de exceções e suporte. |
| Dispositivos autorizados | Dispositivos registrados por usuário/tenant. | Limita compartilhamento de senha e parque de terminais; bom para segurança no Campo. | Device ID pode mudar/ser falsificado; dispositivos compartilhados e troca/substituição exigem fluxo de gestão. Não mede pessoas logadas. | Complemento de segurança/licença, não substituto direto de seats. |

**Recomendação:** vender assentos por usuários nomeados (quantidade padrão mais adicionais) no MVP comercial. Manter gestão de sessão como segurança, com limite de sessões por usuário/regra de desconexão configurável, sem prometer “simultaneidade” como se já estivesse implementada. Se a simultaneidade for requisito irredutível, implementar contabilização por usuário único com reserva transacional no login e comportamento offline que preserve dados locais e sincronize operações previamente autorizadas após reconexão.

## 7. Modelo de cálculo e recálculo recomendado

Sem implementação nesta fase, a forma compatível com o domínio existente seria:

```text
valor_calculado = preço_da_faixa(area_elegível_consolidada, versão_comercial)
                + adicionais_de_assentos_ativos
                + serviços_especiais_contratados
```

Manter quatro valores com momentos distintos:

| Valor | Significado e persistência recomendada |
|---|---|
| Calculado | Cotação derivada da área elegível, adicionais e versão da tabela. Inclui timestamp, entradas e detalhamento reproduzível. |
| Contratado | Valor/formato aceito pelo assinante, referência do aceite e data; continua vigente até a próxima alteração aceita ou data contratual definida. |
| Faturado | Snapshot imutável do valor realmente emitido em cada fatura; nunca atualizar retroativamente. |
| Vigência | Data/hora em que mudança aceita passa a valer e ciclo ao qual se aplica; upgrades/downgrades seguem política declarada. |

Fluxo recomendado: eventos territoriais marcam a assinatura como “requer recálculo”; um serviço central calcula idempotentemente; redução pode ser cotada para a renovação seguinte conforme contrato; aumento produz prévia vinculada à composição e exige aceite explícito; somente após aceite cria alteração contratual com vigência futura/permitida e billing; emissão usa snapshot daquele ciclo. O serviço não deve emitir cobrança nova a cada save de propriedade. A mudança de referência deve registrar o evento, origem e operador.

Isso é uma recomendação de domínio. A escolha da vigência de aumento/downgrade, prorrata diária, tolerância de alteração de área e tratamento de disputa depende de decisão comercial e jurídica, não verificável no repositório.

## 8. Estimativa de horas — alternativa B

Faixas de planejamento para uma equipe que conhece o monorepo, sem dupla contagem entre funcionalidades e testes. Mínimo pressupõe decisões fechadas, uso dos fluxos existentes e nenhuma migração de clientes entre tenants; máximo inclui retrabalho em dados ambíguos e compatibilidade entre contratos/API/Web/Campo. Homologação envolve ambientes e aceite funcional, não compra de serviços.

| Entrega | Mínimo (h) | Provável (h) | Máximo (h) | Dependências |
|---|---:|---:|---:|---|
| Backend: serviço determinístico de preços por área, assentos e serviços | 32 | 56 | 88 | Bordas das faixas, regra de área e catálogo aprovado |
| Banco/migrations: snapshot de cotação, aceite, versão de preço e vigência | 24 | 48 | 80 | Decisão de contrato e política de histórico |
| Cadastro/consolidação de propriedades e área elegível | 32 | 56 | 96 | Assinante/Tenant, fonte de área, arrendamento/compartilhamento e deduplicação |
| Controle de acessos/sessões | 24 | 48 | 80 | Decisão nomeado vs simultâneo vs dispositivo; concorrência e offline |
| Venda/administração dos pacotes adicionais | 16 | 32 | 56 | Definição de produto, cancelamento, renovação e valor contratado |
| Recálculo central e fluxo de prévia/aceite/idempotência | 28 | 48 | 80 | Área e versionamento da fórmula |
| Billing, faturas, vigência, prorrata e gateways existentes | 32 | 56 | 96 | Regras comerciais e integração contratada habilitada |
| Backoffice (preços, contratos, exceções, auditoria) | 20 | 36 | 60 | Modelo de preço e permissões administrativas |
| Interfaces do assinante (onboarding, billing, propriedade e aceite) | 20 | 40 | 72 | API estável e revisão UX |
| Campo PWA (estado de acesso e sync sem perda de fila offline) | 12 | 24 | 48 | Política de revogação/grace period e contrato da sync API |
| Testes automatizados e regressão multi-tenant/billing/offline | 40 | 64 | 100 | Regras aprovadas e ambiente de teste representativo |
| Homologação, compatibilidade, rollout e publicação controlada | 20 | 32 | 52 | Deploy process existente, migração/rollout aprovado e checklist comercial |
| **Total** | **300** | **544** | **908** | |

Justificativa: os objetos e rotas de plano, assinatura, mudanças, faturas e sessão existem; por isso não se estima construção do zero. A principal carga está em fonte de área e ownership, na transição contrato/cobrança, enforcement de acesso que hoje não existe e cobertura de integração Web/API/Campo. A estimativa não inclui assessoria jurídica, saneamento manual de cadastro nem mudança de infraestrutura.

**Caminho crítico:** decidir identidade do assinante → definir área elegível e bordas → serviço de preço com versionamento → cotação/aceite/vigência → faturamento e aplicação dos limites → migração progressiva → homologação e publicação. A decisão de “simultâneos” também é pré-requisito para acesso, mas pode ser desmembrada se o MVP usar usuários nomeados.

**Duração indicativa:** a 40 h/semana de uma pessoa integral, B equivale a 7,5 / 13,6 / 22,7 pessoa-semanas. É esforço, não prazo de calendário; decisões, revisão, dependências de gateway e dados de clientes podem prolongar o cronograma. Duas pessoas podem paralelizar Web/Backoffice e parte do backend, mas não encurtam a cadeia de regras/contrato.

**Complexidade geral: ALTA.** Percentual de código reutilizável não foi estimado em porcentagem: não há contagem objetiva comparável de componentes “prontos”, e reuso de modelos não equivale a reuso das regras comerciais.

## 9. Estimativa financeira de implementação

Taxas abaixo são premissas de simulação fornecidas pelo solicitante, não cotações de fornecedores. Valores são horas da tabela B multiplicadas pela taxa; não incluem impostos, contratação jurídica, serviços externos ou custos operacionais.

| Taxa | Mínimo: 300 h | Provável: 544 h | Máximo: 908 h |
|---:|---:|---:|---:|
| R$ 80/h | R$ 24.000 | R$ 43.520 | R$ 72.640 |
| R$ 150/h | R$ 45.000 | R$ 81.600 | R$ 136.200 |
| R$ 250/h | R$ 75.000 | R$ 136.000 | R$ 227.000 |

**Contingência recomendada:** reservar 25% da estimativa provável, sobretudo para reconciliação de área, contratos existentes, gateways e testes offline. Sobre 544 h são 136 h adicionais; investimento provável com reserva: 680 h ou R$ 54.400 / R$ 102.000 / R$ 170.000 às taxas de R$ 80 / R$ 150 / R$ 250. A reserva não é esforço já identificado e não deve ser somada novamente à faixa máxima de 908 h.

| Natureza de custo | Estimativa |
|---|---|
| Implementação, testes e homologação | Tabela acima |
| Serviços externos | Não mensurável sem contrato/uso de Asaas/Stripe, provedores de APIs e eventuais módulos pagos. Reusar gateways existentes não prova tarifa nem habilitação. |
| Operação recorrente adicional de infraestrutura | Não mensurável; não há baseline de uso, telemetria, preços de hosting/armazenamento/backup nem teste de capacidade associado. Nenhum novo serviço é comprovadamente necessário. |
| Atendimento/suporte e inadimplência | Não mensurável sem volume de chamados, SLA, ticket médio e dados de cobrança. |

**Implementação assistida por IA:** pode reduzir horas de boilerplate, documentação e testes iniciais, mas não elimina decisão de domínio, revisão de segurança, compatibilidade de contratos, testes em ambiente isolado, homologação com cobrança nem responsabilidade de aprovação. Não há métricas internas de produtividade ou consumo de tokens nesta auditoria; portanto não atribuo percentual de economia nem custo de IA comprovado. Recomendo não reduzir orçamento de revisão/homologação com base apenas em geração de código.

## 10. Impacto operacional e infraestrutura

O stack existente tem FastAPI, PostgreSQL e Redis; a arquitetura documenta Celery/worker, mas não foi medida a operação atual da Hostinger nesta auditoria. A VPS KVM 4 foi informada pelo solicitante, porém CPU, RAM efetivamente provisionada, uso, conexões PostgreSQL, latência, filas e concorrência não foram coletados. Não é possível declarar a capacidade para uma base nova de produtores.

| Componente | Efeito provável | Evidência/limite da conclusão |
|---|---|---|
| FastAPI | Uma cotação por evento relevante e validação de acesso podem adicionar leitura/transação; o custo deve ser baixo se recálculo ocorrer só em mudanças de área/contrato. | Não medido; evitar calcular a área em toda requisição. |
| PostgreSQL/RLS | Mais tenants e entidades elevam linhas, índices, sessões de banco e consultas; sessões atuais já são consultadas para validar tokens. | Sem métricas de volume/latência, não se prova saturação nem folga. Toda nova consulta deve manter RLS e `tenant_id`. |
| Redis | Pode ser usado nos caches existentes; não há necessidade comprovada de novo Redis ou cluster. | Sem taxa de hit/memória e sem projeção de sessões. Não se propõe mudar cache. |
| Workers/Celery | Recálculo assíncrono pode suavizar eventos em lote, mas introduz fila, estado pendente e reconciliação. | A auditoria não prova que uma tarefa comercial equivalente já esteja registrada. Reutilizar worker, se aprovado, em vez de criar infraestrutura. |
| Next.js Web | Atualizar páginas de billing/onboarding e estado de cache após aceite. | Custo coberto nas interfaces/backoffice. |
| Campo PWA | Aumento de base pode elevar uploads sincronizados em rajadas; mudança de assento não deve perder fila local. | Sem teste de carga/sync e sem política offline de licença comprovada. |
| Armazenamento/backups | Mais produtores ampliam dados e documentos; custo segue tamanho/retention. | Sem inventário de ocupação, retenção ou preço, custo não mensurável. |
| Provedores externos | IA/IoT/ERP e serviços climáticos/mercado podem ter quota/custo por utilização; cobrança separada exige medição/limite por tenant. | O catálogo identifica extensões, mas termos/custos não foram consultados. |

**Mínimo antes de escalar:** coletar baseline (CPU/RAM, pool de conexões, latência p95, consultas/tenant, uso Redis, fila e storage), instrumentar novas métricas de cotação e acessos negados, executar teste controlado contra volumes de usuários reais previstos e rever limites. Não se recomenda migrar ou acrescentar serviços neste estágio.

## 11. Simulação econômica do novo modelo

### 11.1. Dados reais e fórmulas

Não foi fornecido export agregado de clientes, assinaturas, planos, valores realmente contratados/faturados, inadimplência, cancelamento ou área. O acesso ao banco de produção foi explicitamente evitado. Assim, os valores abaixo são **cenários aritméticos ilustrativos, não previsão ou evidência de demanda**.

Para uma base real, calcular:

```text
Preço médio novo = Σ (% da base na faixa i × preço da faixa i)
                 + Σ (% de adesão ao adicional j × preço adicional j)

MRR contratado(t) = Σ mensalidade contratada vigente dos assinantes ativos em t
MRR recebido(t) = MRR contratado(t) × (1 − inadimplência do período)
ARR run-rate(t) = 12 × MRR contratado(t)
Margem de contribuição = MRR recebido − gateway − custos variáveis de API/storage/suporte
```

Migração integral: `ΔMRR = Σ(preço novo aceito − mensalidade atual por cliente)`, preservando termos e vigência.

Migração gradual: para cada coorte, usar o preço antigo até a data de aceite/renovação e o novo depois; não multiplicar toda a base pelo novo valor no mesmo mês.

Com base inicial `N0`, novos clientes pagos `g` por mês e churn mensal `c`, sem entrada de upgrades e com coortes homogêneas: `N_t = N0(1−c)^t + g × [1−(1−c)^t]/c`. Em `c=0`, o segundo termo é `g×t`.
Ponto de equilíbrio exige margem e custos: `clientes equivalentes = investimento / contribuição líquida mensal por cliente`. Usar receita bruta como ponto de equilíbrio superestima retorno.

### 11.2. Cenários ilustrativos de aquisição (sem base inicial)

As premissas foram explicitadas para mostrar sensibilidade; devem ser substituídas por dados e pesquisa de mercado antes da decisão de preço. Assumo novos clientes pagos por mês, sem `N0`, coortes adquiridas no início do mês, cobrança mensal, cancelamento uniforme e inadimplência aplicada como redução de recebimento. Não incluo impostos, taxas gateway, custo de suporte, custo variável nem Corporate sob proposta.

| Cenário (hipótese) | Novos pagos/mês | Churn mensal | Inadimplência | Mix de faixas assumido (Familiar/Pequeno/Intermediário/Médio/Avançado/Grande) | Adicional assumido | ARPU bruto hipotético |
|---|---:|---:|---:|---|---|---:|
| Conservador | 10 | 5% | 8% | 50% / 35% / 12% / 3% / 0% / 0% | 10% compram +1 por R$ 39 | R$ 289,90 |
| Base | 30 | 3% | 5% | 25% / 35% / 25% / 10% / 4% / 1% | 25% compram +3 por R$ 99 | R$ 449,75 |
| Otimista | 60 | 2% | 3% | 12% / 28% / 30% / 16% / 10% / 4% | 40% compram +5 por R$ 149 | R$ 642,60 |

Com essas hipóteses, a projeção de base e receita é:

| Cenário | Mês | Clientes ativos calculados | MRR contratado bruto | MRR recebido após inadimplência assumida | ARR run-rate bruto | Recebimentos acumulados hipotéticos até o mês |
|---|---:|---:|---:|---:|---:|---:|
| Conservador | 12 | 92 | R$ 26.650 | R$ 24.518 | R$ 319.799 | R$ 174.259 |
| Conservador | 24 | 142 | R$ 41.050 | R$ 37.766 | R$ 492.606 | R$ 562.636 |
| Base | 12 | 306 | R$ 137.694 | R$ 130.810 | R$ 1.652.333 | R$ 897.637 |
| Base | 24 | 519 | R$ 233.233 | R$ 221.571 | R$ 2.798.791 | R$ 3.090.172 |
| Otimista | 12 | 646 | R$ 415.023 | R$ 402.572 | R$ 4.980.277 | R$ 2.713.544 |
| Otimista | 24 | 1.153 | R$ 740.699 | R$ 718.478 | R$ 8.888.384 | R$ 9.673.776 |

**Nota de precisão:** clientes apresentados são arredondados para leitura; valores financeiros usam a quantidade fracionária esperada pela fórmula. Valores Corporate e clientes existentes foram excluídos. Os resultados não comprovam aquisição de 10, 30 ou 60 assinantes mensais nem margem rentável.

**Leitura:** o cenário mostra que aquisição e mix dominam o resultado; não deve ser interpretado como TAM ou projeção comercial. Para comparação de “manter preço atual”, a fórmula é a receita contratada/recebida atual agregada por coorte. Sem sua distribuição de assinantes e contratos, não há valor numérico honesto. Para migração gradual, aplicar a taxa de adesão mensal decidida sobre essa base real.

### 11.3. Recuperação do investimento (piso de receita bruta)

Com o custo provável de R$ 81.600 a R$ 150/h, a divisão simples por uma mensalidade proposta indica meses de assinante bruto equivalentes, sem custos, inadimplência ou churn: Familiar 415; Pequeno 275; Intermediário 165; Médio 103; Avançado 69; Grande 41. Com reserva de 25% (R$ 102.000): 518, 344, 206, 128, 86 e 52, respectivamente. Isso **não é ponto de equilíbrio**: representa somente receita bruta acumulada equivalente. Corporate não pode ser calculado sem preço da proposta e demais custos. Ponto de equilíbrio e prazo de retorno reais permanecem não mensuráveis até conhecer mix, margem de contribuição, churn, inadimplência e migração da base atual.

## 12. Comparação das alternativas

Estimativas são ordem de grandeza e não substituem escopo validado. Custos aplicam as mesmas três taxas ilustrativas, sem contingência.

| Alternativa | Benefícios | Limitações e riscos | Esforço min/provável/máx | Custo provável (R$ 80 / 150 / 250 por h) | Prazo provável, 1 pessoa a 40 h/semana |
|---|---|---|---:|---:|---:|
| **A — Adaptação mínima** | Configurar planos e aproveitar `limite_hectares`, `max_fazendas`, sessões e billing existentes; chega mais rápido a um piloto manual. | `limite_hectares` não consolida nem bloqueia área; pacote adicional/aceite/versão de cálculo não cabem em configuração; simultaneidade ainda não aplicada; manter duas fontes de preço pode causar cobrança divergente. Só aceitável para prova interna sem automação de cobrança por área. | 100 / 180 / 300 h | R$ 14.400 / R$ 27.000 / R$ 45.000 | 4,5 pessoa-semanas |
| **B — Evolução controlada (recomendada)** | Reusa domínio atual e adiciona preço por área, extras, aceite, snapshot de contrato/fatura e recálculo centralizado, mantendo RLS/RBAC e históricos. | Exige decisões de assinante/área e migrations compatíveis; maior trabalho e homologação. | 300 / 544 / 908 h | R$ 43.520 / R$ 81.600 / R$ 136.000 | 13,6 pessoa-semanas |
| **C — Reestruturação ampla** | Poderia redesenhar billing, grupos de produtor, catálogo, contratos e cobranças numa estrutura uniforme. | Não há evidência de que o domínio atual impeça a evolução; migração de assinantes/faturas e risco de regressão muito maiores. Provável duplicação de recursos existentes. | 600 / 960 / 1.500 h | R$ 76.800 / R$ 144.000 / R$ 240.000 | 24 pessoa-semanas |

A faixa estimada de C é um envelope comparativo, não escopo fechado. Não é recomendada sem prova de que os tenants atuais não possam representar contas comerciais de produtores ou de que o billing existente não possa ser estendido.

## 13. Recomendação técnica e comercial

Recomendo **B**, com uma primeira entrega limitada a preço por área consolidada e assentos nomeados, sem simultaneidade estrita no primeiro release. Isso preserva a estrutura atual e resolve as lacunas essenciais de contrato e cobrança sem uma reescrita ampla.

Sequência recomendada após aprovação:

1. Definir se o Tenant é a conta comercial indivisível do produtor e como lidar com uma pessoa que participa de múltiplos tenants.
2. Aprovar a definição de área elegível, fonte de verdade, casas decimais/bordas, tipos de uso e fluxo para áreas não verificadas.
3. Decidir se módulos gerais serão todos incluídos independentemente de tier; separar extensões pagas e deixar RBAC/RLS e permissões operacionais intocados.
4. Preferir usuários nomeados aos limites de sessões simultâneas. Confirmar regras de convite/assentos adicionais e usuários prestadores temporários.
5. Aprovar preço, reajuste, aumento/downgrade, aceite, vigência, prorrata, proteção contratual da base existente e política de migração gradual.
6. Implementar cálculo único na API, com snapshot/versionamento e aceite; usar o Web apenas para apresentar o mesmo cálculo retornado pela API.
7. Validar billing/teste de webhooks, isolamento RLS por tenant, histórico de faturas imutável, alteração simultânea de propriedades e uso offline antes de rollout.

## 14. Decisões pendentes e itens não verificados

- O assinante é pessoa física/jurídica representada por `Tenant`, ou a assinatura deve agrupar mais de um Tenant?
- A área cobrável é área total registrada, área explorada, área produtiva ou área informada/validada? APP e Reserva Legal são incluídas? Qual evidência tem precedência?
- Como tratar propriedade compartilhada, arrendamento parcial, parceria, exploração sazonal, imóvel com múltiplos talhões e geometria que intersecta outra área?
- Como definir intervalos entre valores inteiros para áreas com frações?
- Acessos adicionais significam usuários nomeados, logins simultâneos, sessão por dispositivo ou alguma combinação? Qual política offline e de sessão excedente?
- Quais módulos são “gerais” e realmente disponíveis no lançamento? IA, clima, integrações, serviços externos pagos e tiers de profundidade precisam de catálogo comercial aprovado.
- Qual preço/condição dos clientes existentes e se a migração será opt-in, na renovação ou por negociação?
- Qual gateway será fonte de verdade em novas cobranças recorrentes e quais taxas/contratos estão ativos?
- Dados de assinantes ativos, preços contratados, faturado e pago, cancelamento, inadimplência e distribuição de áreas não foram consultados; não há análise de MRR atual, ARR atual, ticket atual ou margem real.
- Capacidade e custo atual da KVM4, uso de API/DB/Redis/worker, consumo de storage, backups e suporte não foram medidos.
- Não foi feita pesquisa de mercado, validação de elasticidade, benchmark de concorrentes, análise jurídica/tributária ou parecer de profissional de faturamento.
- Não foram executados testes automatizados nem smoke tests; escopo foi auditoria somente leitura e produção de relatório.

## 15. Veredicto final

**DEEPFARMS-COMMERCIAL-MODEL-01**

- **VIABILIDADE TÉCNICA:** ALTA, condicionada à definição da conta assinante e área elegível.
- **COMPLEXIDADE:** ALTA.
- **ESFORÇO PROVÁVEL:** 544 horas para a alternativa B (300–908 h).
- **CUSTO ESTIMADO:** R$ 81.600 provável a R$ 150/h; R$ 102.000 com reserva de 25%. Faixa sem contingência: R$ 24.000–R$ 227.000 dependendo de esforço e taxa.
- **CUSTO OPERACIONAL ADICIONAL:** NÃO MENSURÁVEL com as evidências disponíveis; não há necessidade comprovada de infraestrutura nova.
- **PRINCIPAIS RISCOS:** identidade do assinante versus Tenant; consolidação/deduplicação de áreas; simultaneidade e Campo offline; consentimento/vigência de aumentos; divergência entre preço estático, API e billing; migração de contratos existentes sem dados reais.
- **ALTERNATIVA RECOMENDADA:** B — Evolução controlada.
- **STATUS:** GO COM RESSALVAS para decisão de investimento e detalhamento; NO-GO para cobrança automática baseada em área antes de resolver os bloqueadores de decisão. Nenhuma implementação foi iniciada.

**Vale a pena implementar?** Sim, potencialmente: a mudança pode reduzir a barreira de entrada para pequenos produtores mantendo cobrança escalonada para áreas maiores, e a arquitetura tem pontos úteis de reuso. Mas a justificativa econômica ainda não está comprovada. Recomendo investir primeiro na alternativa B após resolver as decisões listadas e validar o mix/ticket com uma migração gradual. Com os dados atuais, não é responsável afirmar payback ou margem; uma configuração rápida (A) não entregaria recálculo e consentimento confiáveis, e uma reestruturação (C) não tem justificativa demonstrada.
