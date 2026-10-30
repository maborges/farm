# DEEPFARMS-PRICING-01 — Auditoria de Impacto da Nova Estratégia Comercial

**Data da auditoria:** 30/10/2026  
**Escopo:** leitura do repositório; nenhum código de produção, banco, plano, assinatura ou configuração foi alterado.  
**Base de evidência:** fontes de `services/api` e `apps/web`; documentação comercial foi usada apenas como contexto, não como prova de execução.

## 1. Resumo executivo

O DeepFarms possui infraestrutura comercial relevante: catálogo de planos, módulos inclusos em JSON, tiers de profundidade, limites quantitativos, assinaturas de tenant, faturas, alteração de plano, cobrança manual e integrações com Stripe/Asaas no repositório. Gates de módulo, tier e limite aparecem no backend e há gate de interface. A migração não começa do zero.

A arquitetura comporta a transição para preço por porte, mas **não há hoje uma regra canônica nem um vínculo explícito entre assinatura e área faturável**. “Hectares” aparece em `PlanoAssinatura.limite_hectares`, `UnidadeProdutiva.area_total_ha`, área georreferenciada e em hierarquia de áreas com metragem manual/calculada, além da área explorada por vínculo rural. Os dados têm semânticas diferentes. A soma direta causaria dupla contagem; a fonte apropriada depende de definições comerciais ainda pendentes.

Maior risco: liberar módulos não se resume a alterar a vitrine. A autorização do backend consulta a união de módulos das assinaturas ativas e há gates de tier e limites. A UI e as respostas de sessão também derivam módulos e tier do plano. A alteração comercial deve mudar entitlements comerciais preservando permissões de usuário, contexto de tenant/unidade e controles de segurança.

Recomendação: **GO COM RESSALVAS** para desenho e descoberta; não iniciar rollout antes de definir área faturável, tratamento de contratos atuais, tabela comercial, política para área ausente/alterada e serviços adicionais. Para a primeira versão, o melhor equilíbrio técnico/comercial é **Modelo B**: hectares como critério principal com poucas franquias operacionais apenas quando custo variável comprovado justificar. Um piloto com contratos novos, simulação da área e cobrança sem alteração automática de legados reduz risco. Não há dados suficientes de custo por tenant para definir preços.

## 2. Convenções de classificação

| Nível | Interpretação |
|---|---|
| CRÍTICO | Pode comprometer isolamento, segurança, integridade financeira ou causar cobrança incorreta ampla. |
| ALTO | Alteração central e coordenada em contratos, autorização, cálculo ou cobrança. |
| MÉDIO | Mudança localizada ou de interface/operação com dependências administráveis. |
| BAIXO | Ajuste de apresentação/configuração sem mudança estrutural significativa. |
| SEM IMPACTO | Componente preservável para o escopo proposto. |

“Confirmado” indica código ou schema observado. “Não localizado” significa que a busca no repositório não confirmou o recurso; não prova inexistência fora do código versionado.

## 3. Diagnóstico do modelo comercial atual

### 3.1 Componentes e fluxo observado

| Etapa/componente | Evidência e responsabilidade | Impacto/ação futura |
|---|---|---|
| Catálogo | `services/api/core/models/billing.py`, `PlanoAssinatura`: `modulos_inclusos` JSON, `plan_tier`, `limite_hectares`, preço mensal/anual, limites de fazendas/categorias/usuários, trial, ativo e publicação site/CRM. | **ALTO — SIM.** Reutilizar o catálogo; definir representação da edição comercial e preço por hectares. |
| Assinatura | Mesmo arquivo, `AssinaturaTenant`: tenant, plano, tipo, ciclo, usuários contratados, status, Stripe ID, trial, datas de renovação/bloqueio. Comentário prevê múltiplas assinaturas tenant/grupo/add-on; constraint única por `(tenant_id,tipo_assinatura)` limita tipos iguais. | **ALTO — SIM.** Preservar status/histórico; definir compatibilidade. Não guarda hectares contratados nem snapshot de cálculo. |
| Faturas | Classe `Fatura` no mesmo arquivo contém assinatura, tenant, valor, vencimento, estado, comprovante e revisão. | **ALTO — SIM.** Registra valores faturados, mas não discrimina cálculo, versão de preço ou área observada. |
| Pricing progressivo | `core/models/plan_changes.py`, `PlanoPricing`, e `core/services/plan_pricing_service.py`: matriz por faixa de usuários, ciclo mensal/anual e cálculo progressivo. | **MÉDIO/ALTO — SIM.** Padrão reaproveitável, mas suas faixas são de usuários, não de hectares. |
| Alteração/upgrade/downgrade | `core/models/plan_changes.py` (`MudancaPlano`, `CobrancaAsaas`, `HistoricoBloqueio`) e `core/services/mudanca_plano_service.py`; rotas em `core/routers/plan_changes.py` e `backoffice_plan_changes.py`. Registra origem/destino, valor proporcional, pagamento e agendamento. | **ALTO — SIM.** Reutilizar ciclo e trilha; adaptar cálculo. Não registra snapshot de hectares/preço nessa solicitação. |
| Provisionamento | `core/services/onboarding_service.py`, `core/services/auth_service.py`, `core/routers/backoffice_tenants.py`. Fluxos criam tenant, plano e assinatura/trial; há TODO de cobrança recorrente no fluxo backoffice. | **ALTO — SIM.** Cotação aceita deve vincular versão/modelo comercial. Cobrir fluxos distintos. |
| Entitlements backend | `core/dependencies.py`, `_get_modulos_do_tenant` e `require_module`: une módulos de assinaturas elegíveis e responde 402 se módulo não estiver incluído; `require_tier` implementa profundidade. | **ALTO — SIM.** Alterar origem do entitlement essencial de forma centralizada; auditar endpoints com `require_module` e `require_tier`. |
| Limites backend | `require_limit` em `dependencies.py`; `core/services/unidade_produtiva_service.py::_check_limite_unidades` usa `max_fazendas`; outros limites são consumidos por componentes. | **ALTO — SIM.** Distinguir franquias de custo variável de diferenciação de acesso. |
| Claims/contexto | `core/services/auth_service.py` monta `modules` e `plan_tier`; `apps/web/src/hooks/use-has-module.ts` lê contexto de UI. | **MÉDIO/ALTO — SIM.** Sincronizar entitlement após mudança sem elevar permissões. |
| API cliente | `core/routers/billing.py`: `/billing/my-account`, `/invoices`, `/plans`, `/plans/landing`, `/upgrade`, `/limits`. Upgrade descreve solicitação e suporte, não checkout real nesse endpoint. | **MÉDIO — SIM.** Evoluir cotação/apresentação; preservar API para legado. |
| Backoffice | `core/routers/backoffice.py` lista/cria/edita/ativa planos; navegação e telas em `apps/web/src/app/(dashboard)/dashboard/backoffice`. | **MÉDIO/ALTO — SIM.** Exibir modelo, versão, área, aceite e exceção; preservar controles de staff. |
| Interface comercial | `apps/web/src/app/(dashboard)/dashboard/settings/billing/page.tsx`, `components/auth/new-subscription-wizard.tsx`, `components/billing/plan-change-dialog.tsx`, `change-plan-dialog.tsx`, `components/shared/module-gate.tsx`, `module-card.tsx`, `plan-usage-banner.tsx`. | **MÉDIO — SIM.** Alterar contratação nova e avisos de bloqueio por módulo; preservar UI de legado, cobrança e status. |
| Gateway | `core/services/stripe_service.py`, `asaas_service.py`; `core/routers/stripe_webhooks.py`, `webhooks_asaas.py`; fatura manual em `billing.py`. | **ALTO — INVESTIGAR.** Integrações existem, mas caminhos manuais/simulados e TODOs coexistem. Confirmar qual fluxo está ativo e reconciliado. |
| Estados/renovação | `core/services/assinatura_service.py`: máquina de estados, jobs de vencimento/carência/trial. | **MÉDIO — NÃO** para regra central. Reutilizar estados e carência; não criar ciclo de suspensão novo. |

**Fluxo confirmado por componentes:** contratação/onboarding ou backoffice → `AssinaturaTenant` vinculada a `PlanoAssinatura` → autenticação resolve plano, tier e módulos → `require_module`/`require_tier` e `require_limit` + permissões por usuário autorizam rotas → UI reflete plano/módulos → fatura/mudança e máquina de estados conduzem renovação/suspensão/cancelamento. O fluxo não é uniforme: coexistem fatura manual, checkout Stripe e cobrança Asaas em contextos diferentes. A integração ponta a ponta deve ser confirmada antes do rollout.

### 3.2 Tiers e planos efetivos

O “plano” também controla `plan_tier` (`BASICO`, `PROFISSIONAL`, `ENTERPRISE`, com alias legado no comentário), além de módulos e limites. “Todos os módulos incluídos” não elimina automaticamente restrições de profundidade. Deve-se decidir quais recursos avançados hoje protegidos por tier tornam-se essenciais, permanecem premium ou deixam o tier comercial. `docs/strategy/bundle-packages.md` descreve configurações aspiracionais, não prova planos ativos no banco. O seed `services/api/scripts/initial_load/seed_plans.py` também não é estado autoritativo de produção.

## 4. Matriz de impacto por módulo/serviço

A inclusão efetiva por plano depende dos registros configurados no banco, não consultados nesta auditoria.

| Área identificada | Situação/restrição observada | Classe | Impacto |
|---|---|---|---|
| CORE, cadastros e propriedades | Módulo base exigido por `require_module`; base operacional multiunidade. | A | **BAIXO**; manter CORE e definir limites cadastrais separadamente. |
| Agricultura, planejamento e caderno de campo | Gates como `A1_PLANEJAMENTO`; por exemplo `core/routers/reports.py`. | A, com ressalva | **ALTO**; inventariar gates e tiers; não liberar apenas na UI. |
| Pecuária | Rotas/serviços próprios; gates variam por endpoint. | A, com ressalva | **ALTO**; revisar subfuncionalidades, limites e recursos de alto volume. |
| Financeiro, custos, indicadores/DRE | Serviços próprios; `max_categorias_plano` observado. | A, com ressalva | **ALTO**; preservar permissões de aprovação/lançamento e decidir tiers avançados. |
| Estoque e compras | Áreas operacionais próprias e implantação assistida separada. | A/D | **MÉDIO/ALTO**; acesso essencial pode ser comum; implantação segue serviço contratado. |
| Frota | Área funcional integrada aos usos/talhões; custo por tenant não confirmado. | A | **MÉDIO**; revisar limites com base em capacidade/custo real. |
| Campo PWA/sincronização offline | Dispositivo mantém módulos/contexto e sincroniza eventos. | A/D | **ALTO**; medir tráfego, armazenamento, filas e suporte; entitlement não deve ampliar escopo local. |
| Planejamento e custos agrícolas | Gates e serviços em módulos próprios, dependentes de safra/talhão. | A | **ALTO**; rever profundidade e continuidade dos endpoints. |
| Rastreabilidade/ambiental | Telas e serviços especializados; link de billing no front não prova gate server-side. | A/D | **MÉDIO/ALTO**; mapear endpoints, mapas, documentos e licenças. |
| IA/créditos | `ia/usage_service.py`, `IACreditosPacote`, compra/solicitação e webhook. | D | **ALTO**; manter franquia/créditos se custo variável; crédito de IA não é crédito de assinatura. |
| Integrações ERP (Sankhya, SAP, TOTVS) e customizadas | Modelos/serviços por tenant e governança própria. | B | **ALTO**; contrato, credenciais, escopo e implantação independentes. Não mudar escopos TENANT/ESTABELECIMENTO/Unidade Produtiva por preço. |
| Implantação assistida/customizações | Fluxos de implantação e serviços especializados presentes. | B | **MÉDIO**; cobrar como serviço com escopo e aceite separados. |
| Administração global/backoffice/monitoramento | Rotas protegidas por `get_current_admin`, `require_permission` e `backoffice:*`. | C | **CRÍTICO** se confundido com entitlement de cliente; manter separado e sem alteração. |
| Funcionalidades sem gate ou custo confirmado | Não foi possível auditar individualmente todos os endpoints e dependências. | D | **ALTO**; inventariar antes de prometer “tudo incluído”. |

## 5. Propriedades, unidades produtivas e áreas

### 5.1 Estrutura observada

- `core/models/tenant.py`: tenant é proprietário/escopo dos dados, não sinônimo de produtor, imóvel ou assinatura.
- `core/models/unidade_produtiva.py`: `UnidadeProdutiva` (`unidades_produtivas`) tem `tenant_id`, `area_total_ha`, `area_total_calculada_ha` e geometria. “Fazenda” é alias histórico. `core/services/unidade_produtiva_service.py` calcula área georreferenciada quando há geometria e verifica `max_fazendas`.
- `core/cadastros/propriedades/propriedade_models.py`: `Propriedade` é cadastro ligado ao tenant. `ExploracaoRural` vincula propriedade e unidade produtiva, com natureza própria/arrendamento/parceria/comodato/posse, vigência e `area_explorada_ha` opcional.
- `core/cadastros/propriedades/models.py`: `AreaRural` (`cadastros_areas_rurais`) tem tenant/unidade, hierarquia `parent_id`, tipos, `area_hectares` e `area_hectares_manual` (`Numeric(12,4)`), geometria GeoJSON e status ativo. Abrange área produtiva, ambiental e infraestrutura; talhões/piquetes são subdivisões.
- `core/cadastros/propriedades/schemas.py`: hectares positivos quando informados, mas opcionais/nulos; tipo validado. Atualização permite alterar área e estado.
- `core/cadastros/propriedades/service.py::sumario_areas`: soma por categorias, dá precedência ao valor manual; predicado agrega raiz ou classes tipadas. Isso não é política validada para faturamento e pode sobrepor nós da hierarquia.
- `core/cadastros/propriedade_imovel/models.py` e `visao_service.py`: imóvel rural separado e vínculo com propriedade; não confundir propriedade, imóvel, unidade e área operacional.
- `PlanoAssinatura.limite_hectares` existe, mas não foi localizada aplicação geral como medidor da área atual faturável. Campo isolado não prova cálculo operacional por hectares.

### 5.2 Viabilidade e lacunas

**Viabilidade: média, condicionada a definição e governança de dados.** Hectares são unidade compreensível e estão disponíveis em partes do cadastro, mas não há fonte canônica equivalente a “área produtiva faturável da assinatura”. A soma exige regra e possivelmente snapshot/auditoria.

1. **Base:** área em produção/explorada ou área total? Excluir APP, reserva, infraestrutura? Como classificar agricultura e pecuária?
2. **Dupla contagem:** agregar um nível não sobreposto (ex.: folhas produtivas definidas); não somar imóvel, unidade, gleba e talhão ao mesmo tempo. Polígonos sobrepostos requerem validação ou cadastro mestre.
3. **Múltiplas propriedades/unidades:** somar apenas vínculos ativos cobertos pelo contrato. Assinatura hoje tem `tenant_id`, sem FK/lista explícita de unidades ou estabelecimentos. Não inferir escopo novo para ERP.
4. **Própria/arrendada/compartilhada:** usar vigência de `ExploracaoRural`; resolver rateio de área compartilhada entre tenants para evitar cobrança integral duplicada.
5. **Alteração no ciclo:** definir tolerância, data efetiva, aviso e contestação. Preferir cotação com fotografia da base aceita no começo do período e reavaliação na renovação, salvo aceite contratual para ajuste durante o ciclo.
6. **Auditoria:** guardar valor, áreas incluídas, regra/unidade, timestamp, ator/origem, geometria ou entrada manual, versão da tabela e cálculo ligado à cotação/fatura. `TenantAuditLog` existe, mas adequação ao histórico comercial detalhado precisa ser validada.
7. **Ausência/inconsistência:** mostrar “não calculado”, permitir confirmação/importação assistida; não converter `NULL` em zero nem cobrar estimativa sem aceite. Registrar exceção auditável.
8. **Unidades/precisão:** campos encontrados usam hectares (`ha`) como float ou Numeric; conferir origem/importação e rotas de atualização.

Não usar `UnidadeProdutiva.area_total_ha` ou o sumário atual diretamente na cobrança antes de definir a política. Cotação em simulação e reconciliação em piloto são pré-requisitos.

## 6. Comparação de modelos de precificação

| Critério | A — apenas hectares | B — hectares + franquias | C — híbrido por perfil | D — módulos atual |
|---|---|---|---|---|
| Simplicidade comercial | Alta se áreas/faixas forem claras | Alta/média; explicar poucas exceções | Média/baixa; perfis e pesos | Baixa para comparação, familiar aos legados |
| Justiça entre portes | Alta em tese, depende da área correta | Alta; ajusta custo variável comprovado | Potencialmente alta, mas classificação é controversa | Variável; cobra acesso, não porte |
| Previsibilidade | Média/alta após estabilizar a base | Alta com franquias e medição simples | Média; múltiplas variáveis | Média |
| Manipulação | Risco de subdeclaração/desatualização | Mesmo risco + consumo | Mais risco por autodeclaração de perfil | Menor quanto à área; incentiva compra seletiva |
| Experiência | Clara com área/data | Clara se poucas franquias | Exige explicar perfil e métricas | Complexidade de escolha de módulos |
| Compatibilidade | Média; área existe, falta snapshot/cálculo | Média; limites e uso têm precedentes | Baixa/média; dimensões novas | Alta; modelo atual |
| Manutenção/escala | Média; desafio é governança | Média/alta conforme medição | Alta | Média; catálogo/tier crescem |
| Parecer | Candidato após validação | **Recomendado para primeira versão** | Adiar até dados justificarem | Manter para legados |

Modelo B preserva hectares como métrica principal e permite controlar apenas custos variáveis demonstráveis, como créditos de IA, sincronização ou armazenamento se houver medição confiável. Não usar usuários como proxy de custo sem evidência; permissões por usuário independem do preço. Não definir preços finais sem pesquisa de disposição a pagar e dados de custo.

## 7. Contratos, assinaturas e créditos

`AssinaturaTenant` e `Fatura` preservam status, datas e valores emitidos; `MudancaPlano` registra origem/destino, proporcionalidade, pagamento e aplicação/agendamento. Isso permite coexistência, mas não se observou snapshot imutável de produto/entitlement, área de referência, versão de cálculo ou crédito financeiro geral.

- Não atualizar automaticamente `plano_id`, valores de catálogo, faturas antigas ou módulos de contratos ativos.
- Preservar condições antigas por ciclo/versão. Migração em renovação deve observar termos e comunicação/aceite; validade jurídica requer avaliação fora desta auditoria.
- Novas adesões usam produto por porte; manter plano antigo, cancelamento e suporte até migração voluntária/renovação aceita.
- Comparar os cenários explicitando módulos, área, valor e data efetiva; registrar aceite e trilha de auditoria.
- Há cupons (`core/models/cupom.py`) e créditos de IA, mas não foi localizado ledger geral de crédito monetário da assinatura.

### Programa Produtor Fundador DeepFarms

A busca por nome e condições “R$ 600/seis meses” não localizou implementação ou documento versionado confirmando o programa; as condições foram fornecidas no contexto. Faturas registram pagamentos, mas não saldo de crédito contratual, elegibilidade, expiração, consumo, titularidade, reembolso ou aplicação futura. Suporte arquitetural ao crédito **não está confirmado**. Tratar contribuição como instrumento separado até decidir regra e contabilização; não reutilizar crédito de IA ou cupom sem análise. Nenhuma regra de crédito foi implementada.

## 8. Impactos financeiros e operacionais

| Dimensão | Evidência | Lacuna |
|---|---|---|
| Armazenamento | Tenant tem uso/limite; `storage_service.py` incrementa uso em uploads. | Histórico, custo marginal, retenção e reconciliação por tenant. |
| Uso de módulos | `module_usage` e serviço incrementam contagens ao passar por `require_module`. | Cobertura completa, série histórica e associação a custo. |
| Usuários | quantidade contratada e contagem aparecem em limites/pricing. | Custo real, ativos simultâneos e necessidade comercial. |
| Campo/PWA | Dispositivos e sincronização offline existem. | Eventos/bytes, frequência, conflitos e custo de suporte. |
| Banco/operações | Multi-tenant com serviços e RLS. | CPU/IO, consultas, retenção, backup e custo marginal por cliente. |
| Integrações | Stripe, Asaas e conectores ERP no código. | Tarifas, custo de conector, implantação e volume. |
| Suporte/implantação | Fluxos de implantação, CRM e onboarding. | Horas por cliente, severidade e custo de implantação. |

Separar custos fixos da plataforma; variáveis por tenant (armazenamento, operações, sync, IA, mapas e terceiros quando medidos); custos por cliente (onboarding, suporte, treinamento); serviços especiais (ERP, migração, customização e implantação dedicada). Não há valores para estimar margem ou preço. Coletar ciclo representativo de uso, faturas de provedores, distribuição de hectares/perfis, suporte e margem-alvo aprovada.

Liberar módulos pode elevar uso e custos de IA, mapas, armazenamento e suporte, mas não implica consumo automático. Franquias devem ser transparentes, medidas e com alerta/consentimento de excedente; não bloquear essencial por estimativa não comprovada.

## 9. Segurança, isolamento e permissões

- `core/dependencies.py::require_module` consulta entitlement comercial e retorna 402; `require_permission`, `resolver_permissao_usuario` e `require_module_and_permission` cuidam de permissões e escopo de usuário. São controles diferentes.
- Contexto tenant é validado em `get_tenant_id` e associado à sessão por `SET LOCAL app.current_tenant_id` (`dependencies.py`). Serviços filtram `tenant_id`; migrations/guardrails tratam FKs compostas. Preservar RLS e isolamento.
- Rotas administrativas usam dependências administrativas/permissões próprias. Módulos universais não podem conceder `is_superuser`, `backoffice:*` nem acesso cruzado.
- Unidade produtiva/estabelecimento são escopos operacionais distintos. Preservar `require_estabelecimento`/`require_unidade_produtiva` e os escopos ERP TENANT/ESTABELECIMENTO/Unidade Produtiva.
- `ModuleGate` no frontend é conveniência visual. Removê-lo não libera backend corretamente; liberar entitlement tampouco elimina permissões do usuário.

**Risco CRÍTICO:** mudar globalmente `require_module` para ignorar assinatura/status ou inserir módulos administrativos em todos os tenants. Mitigar com catálogo comercial separado da autorização, inventário endpoint a endpoint e regressão de tenant A/B, usuário sem permissão, tenant suspenso e admin.

## 10. Interface e experiência

A página `settings/billing/page.tsx` mostra plano, módulos e limites; wizard seleciona plano; diálogos comparam mudanças; `ModuleGate` informa bloqueio por módulo; `plan-usage-banner` mostra consumo. Backoffice administra planos/assinaturas e cadastro territorial oferece propriedades/unidades/áreas.

Para novos contratos, exibir: essenciais incluídos; preço/faixa e área base; unidades/propriedades consideradas; fonte/data da área; opcionais/serviços especiais; como alterações afetam preço e data de cobrança. Preservar status, ciclo, vencimento, faturas e comprovantes. Legados mantêm bloqueios de módulo enquanto no modelo antigo.

Transformar mensagens “módulo não contratado/upgrade”, cards como decisão de compra, limites de hectares sem semântica e tiers contraditórios à promessa de essencial incluído. Reaproveitar faturas, histórico, estados, listagem descritiva de módulos e componentes territoriais. Não mostrar estimativa como valor faturável sem confirmação.

## 11. Estimativa de esforço

Estimativa de engenharia para implementação futura, não compromisso; assume regra decidida e sem migração contábil extraordinária.

| Área | Pessoa-dias | Premissa |
|---|---:|---|
| Especificar regra e mapear gates | 4–7 | Fechar A/B/C/D e endpoints/tier. |
| Área faturável, cotação, snapshot e auditoria | 8–15 | Agregação sem sobreposição, vínculos e inconsistências; maior incerteza. |
| Billing, mudança, renovação e coexistência | 6–12 | Reutiliza modelos; depende do gateway real. |
| Backoffice e exceções/contratos | 4–8 | Aceite, área, versão e comparação. |
| Checkout, onboarding e UI | 5–9 | Composição e vigência, mantendo legados. |
| Segurança e regressão funcional | 5–9 | Gates, permissões, RLS, PWA, ERP e isolamento. |
| **Total indicativo** | **32–60** | Aproximadamente 6–12 semanas de calendário para equipe pequena, com homologação. Não inclui integração nova, saneamento em larga escala nem trabalho jurídico/financeiro. |

Complexidade global **ALTA**, pela combinação de governança de área, contratos, billing e cobertura de gates. Impacto arquitetural **MÉDIO** se catálogo, assinatura, estados e gates forem preservados; **ALTO** se exigir ledger ou gateway novo.

## 12. Estratégia de migração recomendada

1. **Política e inventário:** definir hectares faturáveis, perfil misto, franquias, exceções, contratos legados e serviços extras; mapear gates e custos. Sem alterar segurança.
2. **Modo sombra:** calcular área/preço hipotéticos sem cobrança ou entitlement novo; validar sobreposição, vínculos e cadastro com produtores. Definir snapshot e aceite.
3. **Produto novo para adesões novas:** configurar entitlements essenciais; usar assinatura, faturas, estados, gateway validado e permissões atuais. Persistir evidência da área, faixa, versão e cotação aceita.
4. **Piloto e transição gradual:** legados inalterados até migração voluntária/renovação nos termos contratuais. Backoffice compara, registra aceite e permite correção/rollback; monitorar cobranças, suporte, uso e custo.
5. **Expandir com critérios:** corrigir divergências, confirmar segurança e custo, oferecer migração comunicada; descontinuar modelo antigo só sem contratos ativos dependentes.

Rollback: desabilitar venda do produto novo e voltar novas adesões ao produto anterior, preservando snapshots e faturas. Entitlements continuam vinculados à assinatura/modelo; nunca contornar gates de segurança.

## 13. Dependências e decisões comerciais pendentes

1. Definição contratual e fonte de hectare faturável; área produtiva, explorada ou total.
2. Faixas, arredondamento, reajuste, periodicidade, mínimo, mudança no ciclo e contestação; preços dependem de pesquisa/custos.
3. Regra para agricultura, pecuária e mista.
4. Quais tiers avançados, IA, satélite/mapas, rastreabilidade, armazenamento e uso estão incluídos.
5. Franquias para usuários/unidades/sync/terceiros somente se custo demonstrado.
6. Catálogo, SLA e aceite para ERP, implantação, customização e suporte especial.
7. Tratamento de planos, descontos, ciclos anuais, créditos, inadimplência e cancelamento legados.
8. Regra do Produtor Fundador: seis contribuições de R$ 600; pagamentos elegíveis, momento/assinatura de aplicação, validade, transferência, estorno e contabilização. Proposta não localizada no código.
9. Gateway autoritativo: boleto/comprovante, Asaas ou Stripe; checkout, recorrência, webhooks e conciliação.
10. Responsável por validação da área e evidências aceitáveis (polígono, documento, declaração, importação).

## 14. Recomendação arquitetural final

Reutilizar `PlanoAssinatura`, `AssinaturaTenant`, `MudancaPlano`, `Fatura`, gateway validado, auditoria e máquina de estados. Não usar a lista de módulos como mecanismo único de preço. Separar conceitualmente produto/modelo comercial contratado, entitlement de funcionalidades e limites/uso de custo variável. Persistir a área-base e versão da cotação aceita por período, com cálculo reproduzível e trilha.

Para coexistência, assinaturas legadas continuam com lista/tier/limites atuais; produto novo entrega módulos essenciais por configuração de entitlement e calcula preço por área. Backend mantém status, permissões individuais, escopo operacional e tenant em camadas próprias. Adaptar APIs/telas de forma compatível, evitando migração global imediata.

### Respostas executivas

**A.** Sim, com ressalvas: billing e gates existem; falta regra/vínculo/snapshot de área e coexistência versionada.  
**B.** Modelo B, hectares como métrica principal e poucas franquias comprovadas; Modelo D temporário para legados.  
**C.** Impacto arquitetural MÉDIO (potencial ALTO se novo ledger/gateway/escopo); implementação ALTA, 32–60 pessoa-dias nas premissas descritas.  
**D.** Preserváveis: RLS/contexto e identidade tenant, permissões/papéis, escopos de unidade/estabelecimento, isolamento ERP, estados de assinatura, histórico de faturas, armazenamento, operações de módulos e controles administrativos. Catálogo e assinatura também permanecem, possivelmente com extensões pequenas.  
**E.** Área ambígua/sobreposta; ausência de snapshot e trilha de cobrança; acoplamento de módulos/tiers ao plano; custo variável sem medição; fluxos divergentes de gateway; crédito fundador sem ledger; endpoints sem cobertura de gate confirmada.  
**F.** Definir regra → mapear gates/custos → simular área/preço → registrar cotação versionada e aceite → novas adesões com legados intactos → piloto → migração voluntária.  
**G.** Sim. Planos atuais permanecem enquanto novas adesões usam produto por porte, desde que modelo/versão sejam identificados e UI/backoffice mantenham fluxos distintos.  
**H.** As dez decisões da seção 13, especialmente área faturável, limites/adicionais, mudança no ciclo, contratos e crédito do Programa Produtor Fundador.

## Veredicto

**DEEPFARMS-PRICING-01**

**STATUS: GO COM RESSALVAS**  
**IMPACTO ARQUITETURAL: MÉDIO**  
**COMPLEXIDADE DE IMPLEMENTAÇÃO: ALTA**  
**RECOMENDAÇÃO: AJUSTAR PROPOSTA**

Avançar para especificação comercial e desenho técnico após fechar as decisões pendentes. Não habilitar cobrança por hectares antes de validar área-base, contratos, snapshots, custos, gateways e coexistência. Esta auditoria não implementou nem modificou funcionalidade.
