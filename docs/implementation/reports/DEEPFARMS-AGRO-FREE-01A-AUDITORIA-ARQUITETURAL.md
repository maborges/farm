# DEEPFARMS-AGRO-FREE-01A — Auditoria arquitetural e plano de implementação

Data: 16/10/2026. Escopo: auditoria estática do monorepo e consulta a fontes oficiais externas. Nenhuma implementação, migration, consulta ao banco ou alteração de infraestrutura foi executada.

**Classificação:** F = fato observado no código; D = informação documental, sem confirmação operacional nesta auditoria; R = recomendação; H = hipótese de dimensionamento. Caminhos são relativos à raiz do repositório; os números indicam linhas da versão auditada. Não foram lidos arquivos de segredos. Alterações preexistentes do workspace foram preservadas.

## 1. Resumo executivo

**GO COM RESSALVAS.** Recomenda-se aplicativo independente em `apps/agro`, servido em `https://agro.deepfarms.com.br`, com serviços no monólito FastAPI. A landing institucional permanece em `apps/web` e divulga o aplicativo por link e QR code.

A escolha resulta da existência de dois aplicativos com finalidades e autenticação diferentes e de Service Workers próprios. Incorporar o Agro ao Web compartilharia deploy e escopo de cache; incorporá-lo ao Campo misturaria consultas públicas com sincronização operacional autenticada.

É possível reutilizar identidade global, utilitários, padrões visuais, clientes de integração e mecanismos de execução. Entretanto, eventos, outbox, alertas e notificações atuais são vinculados a tenant. Web Push ainda é um canal não implementado. Não há um feed agrícola completo e comprovadamente licenciado pronto para publicação.

O acesso anônimo não deve criar usuário, tenant ou assinatura. O cadastro opcional deve reutilizar `Usuario`, com dados pessoais isolados por proprietário e credencial específica do Agro. A conversão comercial cria ou vincula tenant apenas no fluxo comercial explícito.

Bloqueadores de lançamento: autorização de redistribuição dos dados; separação verificável de credenciais e RLS; implementação real de Push; confirmação de capacidade e topologia AWS; aprovação de orçamento. Gratuidade ao usuário não elimina caráter comercial do produto de aquisição.

## 2. Inventário e evidências

| ID | Observação | Evidência |
|---|---|---|
| E01 F | pnpm contempla `apps/*` e `packages/*`; apps Web e Campo, sem app Agro nos manifests inventariados | `pnpm-workspace.yaml:1`; `apps/web/package.json:1`; `apps/campo/package.json:1` |
| E02 F | Web: Next 16.1.6, React 19, TanStack Query, Zustand, Tailwind, shadcn, next-themes. Campo inclui Dexie e next-pwa; versões de Zod/RHF diferem | manifests E01; `apps/web/src/components/providers.tsx:55` |
| E03 F | Pacotes existentes: types, zod-schemas, utils; não foi identificado pacote UI compartilhado | `packages/types/package.json:1`; `packages/zod-schemas/package.json:1`; `packages/utils/package.json:1` |
| E04 F | Landing está no Web, carrega planos e contém CTAs comerciais e tracker | `apps/web/src/app/page.tsx:349`, `Home:522`, CTAs `:552`, `LandingTracker:1108` |
| E05 F | Proxy diferencia domínios oficiais/customizados; não é sozinho uma barreira de autenticação | `apps/web/src/proxy.ts:31` |
| E06 F | Manifest Web inicia em dashboard; Campo inicia em raiz; ambos listam SVG como ícone | `apps/web/src/app/manifest.ts:3`; `apps/campo/public/manifest.json:1` |
| E07 F | SW Web faz cache amplo de GET same-origin; não contém exclusão explícita de APIs ou respostas privadas nesse handler | `apps/web/public/sw.js:12`; registro `apps/web/src/components/pwa/service-worker-registration.tsx:5` |
| E08 F | Campo usa next-pwa, API NetworkOnly e cache genérico NetworkFirst; offline operacional tem Dexie e sync próprios | `apps/campo/next.config.ts:5`; `apps/campo/src/lib/db.ts:1`; `apps/campo/src/lib/sync/worker.ts:1` |
| E09 F | Build Web ignora erros TS; Dockerfile constrói explicitamente Web, não qualquer workspace | `apps/web/next.config.ts:6`; `Dockerfile.web:12`, `:37`, `:42` |
| E10 F | Clima comercial exige tenant, unidade e permissões; não é API pública reutilizável diretamente | `services/api/agricola/climatico/router.py:21`, `:64`, `:99` |
| E11 F | Cliente OpenWeather consome current e forecast 2.5; adapter canônico gerencia configuração, jobs e eventos por tenant | `services/api/integracoes/openweather/services.py:161`, `:198`, `:219`, `:224`; `client.py:3` apenas reexporta cliente |
| E12 F | Identidade global separada da associação comercial | `services/api/core/models/auth.py:8` (`Usuario`), `:54` (`TenantUsuario`) |
| E13 F | Há registro de usuário sem criar tenant e login com proteções existentes, mas login consulta vínculos/configuração comercial | `services/api/core/services/auth_service.py:69` (`register_user`), `:90` (`authenticate_user`), `:119` |
| E14 F | Sessão injeta contexto tenant; resolução de tenant aceita seleção por header e pode escolher único vínculo quando token não contém tenant | `services/api/core/dependencies.py:62`, `:143`, `:200`, `:274`, `:325` |
| E15 F | Clima possui migrations ENABLE/FORCE RLS e políticas USING/WITH CHECK com contexto seguro | `services/api/migrations/versions/20260820_clima_rls.py:17`; `20260820_clima_rls_safe_context.py:15`, `:61` |
| E16 F | Engine usa search_path farms; listener connect mostrado ajusta isolamento, não instala sozinho contexto de usuário | `services/api/core/database.py:21`, `:35`, `:64` |
| E17 F | Growth já recebe eventos públicos sem tenant; limitador é memória por processo e hash IP é SHA256 sem segredo | `services/api/growth/models.py:11`; `services/api/growth/router.py:20`, `:43`, `:90`; `apps/web/src/lib/landing-tracking.ts:4`, `:99` |
| E18 F | Evento e outbox exigem tenant; outbox tem FK tenant não nula, estados, tentativas e agendamento | `services/api/events/base.py:12`; `services/api/events/outbox_model.py:35`, `:53`, `:82` |
| E19 F | Notificações exigem tenant; PUSH é tratado pelo NoopNotificationAdapter e retorna NOT_IMPLEMENTED | `services/api/notifications/base.py:37`; `services/api/notifications/adapters.py:76` |
| E20 F | Alertas/scheduler operam com contexto tenant/unidade; worker existente executa OpenWeather e alertas em loop asyncio | `services/api/alert_engine/models.py:92`; `scheduler.py:78`; `services/api/automacoes/worker.py:113` |
| E21 F | Há workers de automações, background e outbox no Compose; não há serviços Campo, PostgreSQL ou Redis nesse arquivo de produção | `docker-compose.prod.yml:1`, `:20`, `:32`, `:45`, `:60` |
| E22 F | CotacaoService depende de tenant; CEPEA presume URL/token; B3 é placeholder; fetch CBOT usa TIME_SERIES_DAILY com símbolos que não comprovam contrato futuro | `services/api/core/cadastros/commodities/cotacao_service.py:45`, `:60`, `:90`, `:104` |
| E23 F | Existem catálogo de unidades e conversão por commodity; exemplo de SACA_60KG com fator 15 é contraditório e não deve virar regra pública | `packages/utils/src/constants/unidades.ts:6`; `services/api/core/cadastros/commodities/conversao.py:12`, `:20`, `:50` |
| E24 D | Relatório posterior registra domínios institucionais/app/campo/API e serviços deepfarms + nginx ativos; há trechos anteriores de tentativa frustrada | `docs/implementation/reports/BRAND-RENAME-04-DEPLOY-CONTROLADO-PRODUCAO.md:102`, `:156`, `:163` |
| E25 D | Documentação genérica cita AWS/RDS/Redis e topologias alternativas, várias presumidas. Runbook antigo não representa automaticamente AWS atual | `docs/architecture/agrosaas-deployment-architecture.md:11`, `:18`, `:25`, `:48`; `docs/AWS_MINIMAL_SETUP.md:14`; `docs/runbooks/deploy-les-svrbo-ap01.md:955` |

Limites: código de migration não comprova política aplicada, grants ou ausência de BYPASSRLS em produção. Compose não comprova processos ativos. Não foram executados testes, builds ou chamadas de ingestão nesta fase; podem gerar artefatos ou escritas. Não foi constatado vazamento em produção; E07 é risco estático de cache a impedir no Agro.

## 3. Matriz REUTILIZAR / ADAPTAR / CRIAR / NÃO UTILIZAR

| Decisão | Elemento | Condição |
|---|---|---|
| REUTILIZAR | Workspace pnpm, types, formatadores, logos, tokens visuais | Contratos mínimos; sem dependências do dashboard |
| ADAPTAR | Componentes UI Web, tema, Query provider | Extrair primitives úteis para pacote UI; evitar import entre apps e duplicação integral |
| ADAPTAR | Cliente OpenWeather e domínio integracoes | Separar transporte/normalização de configuração e persistência tenant |
| ADAPTAR | Usuario e serviços de autenticação | Novo contexto de sessão Agro; sem vínculo ou cobrança implícitos |
| ADAPTAR | Growth/tracking | Taxonomia Agro, consentimento, limites distribuídos e validação de payload |
| ADAPTAR | Events/outbox/notifications/alert_engine | Escopo de proprietário explícito e compatibilidade com contratos comerciais |
| CRIAR | apps/agro, manifesto, SW, rotas públicas e privadas | Origem e caches próprios |
| CRIAR | Projeção pública de clima/mercado e preferências pessoais | Dados públicos separados de registros comerciais |
| CRIAR | Adapter Web Push e ciclo de subscriptions | VAPID, revogação, expiração, retry, observabilidade |
| ADAPTAR | Conversões existentes | Revisão dimensional e fatores versionados; Decimal para dinheiro |
| NÃO UTILIZAR | Tenant gratuito coletivo ou tenant artificial por visitante | Não representa domínio nem garante isolamento pessoal |
| NÃO UTILIZAR | APIs climáticas/financeiras tenant como endpoints anônimos | Não remover dependências de permissão |
| NÃO UTILIZAR | SW Web amplo, Dexie/sync operacional inteiro | Compartilhariam dados e ciclo operacional inadequados |
| NÃO UTILIZAR | Placeholder B3/CBOT como feed válido; seeds/mock como mercado | Ausência deve aparecer como indisponibilidade |
| NÃO UTILIZAR | API gratuita não comercial, scraping não autorizado | Licença é gate de produto |

## 4. Alternativas arquiteturais

| Alternativa | Vantagem | Desvantagem | Veredicto |
|---|---|---|---|
| Área em apps/web | Menos build e deploy inicial | Acoplamento à sessão, manifest e SW existentes; regressão comercial | Não recomendada |
| Módulo em apps/campo | Base offline pronta | Ativação, PIN e sync de operação incompatíveis com consulta anônima | Rejeitada |
| apps/agro + monólito existente | Identidade PWA e releases independentes; reaproveita domínios | Novo frontend/processo e adaptações de escopo | Recomendada |
| Novo frontend e novo backend completo | Isolamento operacional forte | Duplica identidade, integração e operação | Adiar; somente com evidência de escala |
| Frontend estático em CDN | Pouco consumo de CPU | Exige decidir export estático, proxy/API/CORS e autenticação | Alternativa de hospedagem futura, não pressuposto atual |

## 5. Arquitetura recomendada

Fluxo proposto:

```text
Landing Web -> agro.deepfarms.com.br -> apps/agro
                                       | shell/IndexedDB próprios
                                       v
                       API FastAPI: fachada /api/v1/agro
                         | público            | autenticado
                    snapshots públicos    preferências por Usuario
                         |                    |
                         +--- integracoes ----+
                         |                    |
                    provedores          workers/events
                                              |
                                        notifications/Push
```

`services/api/agro` seria domínio de experiência pública e preferências, não um segundo domínio de integração. HTTP externo, credenciais, normalização, cotas e jobs ficam em `integracoes`; novos adapters BCB/Open-Meteo/mercado entram ali. A extração de cliente deve manter compatibilidade dos consumidores comerciais.

Endpoints propostos, ainda inexistentes: GET `/agro/public/localidades`, `/clima`, `/mercado`; GET/PATCH `/agro/me/preferencias`; CRUD de locais, regras e subscriptions em `/agro/me/...`. Não expor proxy genérico nem parâmetros livres de provedor.

Persistência proposta: snapshots públicos com proveniência/licença; preferências, locais favoritos, regras e subscriptions com `usuario_id`. Não criar Propriedade/UnidadeProdutiva para representar um favorito meteorológico. Cache público não contém coordenadas associadas a identidade nem dados de fazendas comerciais.

Chave de clima inclui provedor, versão, célula/localidade, parâmetros e fuso. Deduplicar chamadas concorrentes; TTL inicial de 60 minutos, ajustável à atualização real. Cache de moeda acompanha boletins; mercado acompanha publicação da fonte. Guardar `source_updated_at`, `fetched_at`, `valid_until`, fonte e status. Falha preserva último snapshot com indicação de desatualização; não prorroga validade artificialmente.

Dados públicos podem ser cacheados em Redis/CDN quando licença permitir. Respostas pessoais: private/no-store no HTTP; persistência offline explícita por usuário, limpeza no logout. Nunca cachear tokens.

**Eventos:** E18–E20 impedem reutilização direta. Recomenda-se evolução aditiva dentro dos mesmos módulos, com envelope discriminado TENANT/USER/PUBLIC, validação de ownership e contratos legados preservados. Planejar armazenamento do escopo USER separado da outbox tenant, compartilhando mecanismo de relay, retries e métricas; não tornar tenant nullable indiscriminadamente. Essa tabela distinta justifica-se pela fronteira de autorização, não por novo domínio de integração. Uma ADR e testes devem fechar o desenho antes da fase de alertas.

Executar avaliação de regras no backend a cada snapshot novo, agrupada por localidade/ativo, com histerese, cooldown, janela de silêncio, validade e deduplicação por regra/versão/janela. Usar lease/lock para impedir schedulers duplicados. Compartilhar infraestrutura de workers, mas aplicar limites de concorrência e filas/lotes por produto para não atrasar automações pagas. Falhas isoladas, retries com backoff e dead-letter. Aceitação pelo servidor Push não comprova exibição no aparelho.

## 6. Landing e instalação

1. CTA “Conheça o DeepFarms Agro — gratuito” na landing e página explicativa; separá-lo dos CTAs atuais de teste comercial.
2. Link e QR code para origem Agro com UTMs permitidas; nunca JWT, email ou localização na URL.
3. Abrir consulta sem login. Solicitar geolocalização apenas após ação do usuário; oferecer pesquisa manual equivalente.
4. Na origem Agro, oferecer instalação. Android/Chromium: detectar `beforeinstallprompt` e acioná-lo por gesto; fallback com instrução de menu. Evento não é garantido. [Google: instalação](https://web.dev/learn/pwa/installation-prompt).
5. iOS: orientar compartilhamento/adicionar à tela de início, adaptando instruções à versão. Para Web Push, suportar apps na tela inicial em iOS/iPadOS 16.4+, com permissão solicitada após interação. [WebKit](https://webkit.org/blog/13878/).
6. Manifest próprio com id estável, start_url, scope, display standalone, nome/cores e PNG 192/512, maskable e apple-touch-icon. HTTPS e SW na mesma origem. Não reaproveitar manifest do dashboard.
7. Offline abre shell e último snapshot disponível, com horário, fonte e validade. Sem carga anterior, mostrar indisponibilidade. Após vencimento, apresentar dado histórico, nunca previsão atual. Atualização de SW preserva consistência de assets.
8. Cadastro opcional somente para sincronização e alertas. Push recusado mantém todas as consultas.

A landing não instala silenciosamente uma PWA de outra origem. Não prometer Background Sync ou Periodic Sync como scheduler. Alertas dependem de rede, permissões e restrições do sistema operacional.

Métricas: visita, clique CTA, abertura Agro, instalação solicitada, appinstalled onde disponível, primeira abertura standalone, ativação, retenção D1/D7/D30, cadastro, alerta habilitado e conversão comercial confirmada no backend. Não equiparar clique a instalação nem início standalone a instalação comprovada universal. Definir denominadores por coorte e consentimento; deduplicar eventos. Reutilizar growth, sem segundo stack analítico.

## 7. Usuários, segurança e privacidade

**Anônimo:** consulta pública e favoritos locais; não emitir credencial SaaS. Backend público usa role com acesso apenas a projeções públicas, sem SELECT sobre tabelas tenant.

**Identificado:** reutilizar Usuario global. Sessão Agro possui audience/issuer e chaves ou verificador isolados, scopes mínimos e revogação. Reusar hashing/recuperação de identidade sem reutilizar indiscriminadamente token comercial. E14 resolve tenant por vínculo mesmo sem claim tenant: omitir tenant_id não basta para isolamento. Tokens Agro devem ser rejeitados por APIs comerciais, inclusive para usuário que também seja assinante. Troca de contexto exige fluxo explícito.

**RLS:** tabelas pessoais com ENABLE/FORCE RLS e USING/WITH CHECK por usuario_id derivado exclusivamente de sessão validada. SET LOCAL por transação, incluindo retomadas após commit; pool sem resíduo de contexto. Roles runtime sem superuser/BYPASSRLS. FKs/uniques preservam proprietário. Dados públicos têm grants mínimos; ingestão usa papel distinto. Manter políticas comerciais inalteradas. Formalizar ADR para ampliar as regras arquiteturais hoje centradas em tenant, aproveitando precedente de identidade/growth globais, sem bypass.

**Abuso:** rate limiting distribuído por IP confiável, usuário e rota; limites separados para login, busca, cadastros e Push; quotas globais de provedor e hard budget. Valores iniciais propostos: consultas públicas 60/min/IP com burst pequeno; busca 10/min; até cinco locais e dez regras por conta, ajustáveis por teste. IP compartilhado rural demanda tolerância. Payloads limitados, paginação, coordenadas válidas, timeout, circuit breaker e URLs externas não controladas pelo cliente. Subscriptions Push exigem proteção SSRF, HTTPS, bloqueio de IP privado/metadata e validação de redirecionamentos/DNS. CORS restrito não substitui autenticação. Cookies host-only Secure/HttpOnly, CSRF em mutações, CSP e validação de origem.

**LGPD:** minimizar coleta; município basta por padrão, localização precisa é opcional; não exigir CPF. Explicar finalidade antes de pedir permissão. Separar autorização de Push, localização e marketing; revogação simples. Não atribuir anonimato ao hash de IP atual. Proposta de retenção: eventos identificáveis 90 dias, agregados posteriormente; logs operacionais 30 dias, sujeitos a validação jurídica e obrigações aplicáveis. Exportação/exclusão das preferências, subscriptions e dados Agro não deve apagar automaticamente identidade ainda necessária a contratos comerciais. Registrar base legal por finalidade e avaliar transferência internacional a provedores. Analytics opcional condicionado à escolha aplicável; consultas não dependem de marketing. [Orientação ANPD](https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia_orientativo_cookies_e_protecao_de_dados_pessoais).

## 8. Provedores e licenciamento

Verificação documental em 16/10/2026; preços/termos devem ser reconfirmados na contratação. Não foi contratada nenhuma dependência.

| Fonte | Cobertura, frequência e qualidade | Limites/custo observado | Licença, cache e decisão |
|---|---|---|---|
| Open-Meteo | Global; variáveis horárias e diárias, sete dias padrão; modelo não representa medição da propriedade | Free: 600/min, 5.000/h, 10.000/dia, 300 mil/mês; Standard 1 milhão/mês. Preço monetário não exposto no texto recuperado | API free exclui uso comercial/promocional. Plano comercial candidato; dados CC BY 4.0 permitem adaptação/redistribuição com atribuição. Cache com proveniência |
| OpenWeather | Cliente atual usa forecast de cinco dias em passos de três horas; não satisfaz previsão horária e sete dias sozinho | Página atual apresenta One Call 4.0, 1.000 chamadas/dia grátis e US$0,0015 excedente; 3.0 aparece deprecated. Planos weather começam em US$40/mês | Página lista ODbL; validar licença do produto contratado, atribuição, bases derivadas e retenção. Chave/contrato comercial existente não está comprovado |
| BCB/PTAX | Compra/venda USD, boletins e histórico; referência oficial, não ticker contínuo nem preço executável | Acesso público; quota/SLA não confirmados. Poll por boletim, cache diário e calendário útil | Dataset declara ODbL; atribuir e avaliar obrigações sobre base derivada. Candidato MVP “Dólar PTAX” |
| AwesomeAPI | Câmbio e histórico via API; validar origem, atraso e metodologia | Documentação remete a planos/chaves; preço/quota contratual não confirmados | Documentação técnica não comprova licença de redistribuição/offline. Alternativa condicionada |
| CEPEA | Indicadores brasileiros para produtos-alvo, conforme praça/metodologia e publicação de cada série | Custo/API de redistribuição não comprovados | Política exige autorização formal, excetua widget e proíbe transmissão de séries no uso padrão. Negociar explicitamente histórico, cache, offline, derivados e alertas |
| CONAB | Pesquisa de mais de 130 produtos, diferentes localidades/níveis; séries de frequência própria | Portal público; API estável, quotas e custo de automação não comprovados | Validar licença do dataset específico e exportação autorizada; página pública não comprova licença para qualquer base. Candidata a referência, sem prometer preço diário |
| B3 / distribuidor autorizado | Futuros com contrato/vencimento; não preço físico de porteira | Contratação e valores sob análise comercial | Tempo real/delay e UP2DATA têm regras de distribuição. Fora do MVP de baixo custo até aprovação |

Fontes oficiais: [Open-Meteo termos](https://open-meteo.com/en/terms), [planos](https://open-meteo.com/en/pricing), [documentação](https://open-meteo.com/en/docs); [OpenWeather preços](https://openweathermap.org/price); [BCB dataset](https://dadosabertos.bcb.gov.br/pt_BR/dataset/dolar-americano-usd-todos-os-boletins-diarios); [AwesomeAPI](https://docs.awesomeapi.com.br/api-de-moedas); [CEPEA política](https://cepea.org.br/br/politica-de-direitos-autorais-1.aspx); [CONAB preços](https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/precos-agropecuarios); [B3 FAQ](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/distribuidores/perguntas-frequentes/), [UP2DATA](https://b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/up2data/central-de-ajuda/contratacao-e-precos.htm).

Recomendação: comparar Open-Meteo comercial com ampliação contratual OpenWeather; escolher um provider inicial, sem pagar dois antes de necessidade comprovada. Não hospedar modelos meteorológicos próprios no MVP. Testar qualidade em localidades de diferentes regiões brasileiras, altitude e fusos, confrontando previsões e observações disponíveis; não declarar precisão agronômica sem validação.

Mercado deve publicar commodity/variedade, praça, moeda, unidade, classificação FISICO/FUTURO/FINANCEIRO, metodologia, data da fonte, captura e atraso. Futuro inclui bolsa e vencimento. Robusta/conilon não deve ser confundido com arábica. Nunca converter ticker de ação ou ETF em preço físico. Variação compara mesma série e base, sem preencher feriados com negócios inexistentes.

Para cada fornecedor obter prova de permissão para exibição pública, usuários anônimos, cache servidor/dispositivo, retenção histórica, cálculos derivados, alertas e atribuição. Sem autorização, omitir feed ou oferecer link externo; widget não equivale a API nem a permissão de cache.

## 9. MVP

**MVP A — utilidade pública:** app instalável, tema claro/escuro, localidades locais, clima horário e sete dias conforme contrato, estados de validade/offline, calculadoras, PTAX explicitamente rotulada, landing e métricas mínimas. Mercado agrícola só entra com licença e sem placeholders.

**MVP B — relacionamento:** cadastro gratuito, sincronização de preferências, alertas climáticos e metas de preço de séries autorizadas, Push e controles de privacidade. A divisão reduz risco; MVP A não equivale ao atendimento integral do escopo A–F.

Se o lançamento exigir soja, milho, arábica, robusta e boi simultaneamente, contrato/cobertura das cinco séries é gate. Ausência de fonte não autoriza substituir silenciosamente por futuros. Sem feed, calculadora aceita preço informado pelo usuário, identificado como entrada manual.

Calculadoras offline com fórmula versionada:
- quantidade destino = quantidade origem × fator documentado;
- BRL = USD × taxa BRL/USD; indicar compra/venda, referência e data;
- preço líquido por unidade = preço de referência convertido + prêmio/desconto − frete por unidade − despesas fixas por unidade − encargos percentuais sobre base explicitada.
- frete R$/t para R$/saca = frete × massa da saca em kg / 1.000.

Exigir massa da saca, variante regional de alqueire e commodity para bushel; não presumir fatores universais. Arredondar na apresentação, testar dimensionalidade e mostrar memória de cálculo. Resultado é estimativa, sem substituir oferta comercial. Alertas de geada/chuva são riscos baseados em modelo, não confirmação de ocorrência; regras e limiares dependem de revisão agronômica.

## 10. Backlog priorizado

| Prioridade/épico | Entrega | Dependência | Esforço H |
|---|---|---|---|
| P0 — decisões e licenças | ADR identidade/ownership/eventos, contratos e limites de escopo | Produto, segurança, fornecedores | 4–6 pessoa-dias |
| P0 — fundação Agro | Workspace, UI compartilhada mínima, shell/manifest/SW/tema | ADR frontend | 6–9 |
| P0 — dados públicos | Extração adapters, snapshots, cache, proveniência e quotas | Licenças | 7–10 |
| P0 — calculadoras | Funções puras, fatores e fórmulas revisadas | Validação de domínio | 3–5 |
| P0 — aquisição | Landing, instruções, QR e métricas consentidas | Agro navegável | 3–4 |
| P1 — identidade pessoal | Sessão Agro, owner-RLS, preferências, sync/exclusão | ADR segurança | 6–9 |
| P1 — alertas e Push | Escopo USER, execução backend, subscription e adapter | Identidade, fontes válidas | 8–12 |
| P0/P1 — homologação/operação | Isolamento, carga, aparelhos, deploy/rollback e painéis | Todas as anteriores | 6–9 |

Total base: **43–64 pessoa-dias**; com contingência de 20–30%, **52–83 pessoa-dias**. Prazo indicativo de 8–12 semanas com dois profissionais e apoio parcial de QA/DevOps/produto; contratações podem estender calendário. Estimativa inclui implementação futura, não autorização.

## 11. Infraestrutura, dependências e riscos

Incrementos propostos: DNS/certificado para Agro; vhost Nginx; build/imagem e processo próprios; rotas de API permitidas; observabilidade por produto; eventual Redis para quotas/cache se instância atual não estiver disponível. Não pressupor necessidade de ECS, EKS, RDS novo ou ElastiCache novo.

A documentação mistura systemd e Compose. Antes do deploy, inventariar em leitura a topologia real: região, instância, memória/CPU, banco, pool, Redis, TLS, DNS, upstreams, backups, egress, logs e versão dos serviços. Sem isso, capacidade livre é H, não fato. `Dockerfile.web` não constrói Agro automaticamente. Build em CI evita disputar memória com produção. Novo app precisa typecheck próprio; não herdar ignoreBuildErrors.

Manter HTTPS, cache longo apenas para assets com hash; manifest/SW revalidáveis. API privada sem cache compartilhado; evitar reescrita ampla que exponha rotas administrativas. Secrets apenas backend. Reutilizar correlação e logs estruturados; acompanhar idade dos dados, hit ratio, erro/latência provider, custo por localidade, backlog, dedup, expiração Push, p95 público e impacto no ERP.

| Risco | Impacto | Tratamento/gate |
|---|---|---|
| Redistribuição sem licença | Retirada do produto/custo imprevisto | Aprovação documental por fonte |
| Token Agro alcança tenant associado | Exposição comercial | Separação criptográfica/contextual e testes negativos |
| Alteração ampla em outbox/RLS | Regressão em clientes | Escopo aditivo, compatibilidade e rollout por flag |
| Tráfego público satura monólito | Degradação de assinantes | Cache, limites, pool/concurrency e kill switch |
| Previsão velha ou unidade errada | Decisões inadequadas | Validade explícita, normalização e revisão de domínio |
| Push duplicado/atrasado | Perda de confiança | Dedup, TTL, cooldown e métricas sem prometer entrega |
| Documentação diverge do runtime | Deploy incorreto | Inventário operacional antes de implantação |

Rollback futuro: desligar ingestão/alertas Agro por flag, remover tráfego do novo upstream e restaurar imagem anterior; manter serviços comerciais. Migrations futuras devem ser aditivas e compatíveis; não depender de downgrade destrutivo. Aprovação de produção separada desta auditoria.

## 12. Esforço e custos operacionais

Orçamento é estimativa, não cotação AWS. Região, capacidade e contratos existentes não foram confirmados. Custos AWS variam com instância, transferência e serviços; fechar cálculo na região real. [AWS EC2 preços](https://aws.amazon.com/ec2/pricing/on-demand/).

H: cada célula/localidade ativa gera 24 atualizações/dia, um request por atualização e 30 dias/mês. 100 localidades = 72.000 requests/mês; 1.000 = 720.000; 10.000 = 7,2 milhões. Usuários compartilham snapshots, não credenciais. Chamadas ponderadas por variáveis/modelos/localidades podem superar requests HTTP.

H de comparação One Call, aplicando tarifa pública observada e uso diário uniforme: 100 localidades = (2.400−1.000) × 30 × US$0,0015 = **US$63/mês**; 1.000 localidades = **US$1.035/mês**. Não inclui geocoding, impostos, contratos especiais nem garante adequação de licença. Open-Meteo exige cotação monetária atual; volumes acima permitem comparar enquadramento, não custo final.

| Componente | Reserva H/mês no piloto | Observação |
|---|---|---|
| Compute/cache incremental compartilhado | US$0–60 | Zero só com folga medida; inclui reserva, não novo serviço garantido |
| Logs, storage, tráfego e backup incrementais | US$5–40 | Limites/retention precisam existir |
| Clima | Contrato Open-Meteo ou cenário OpenWeather | Não assumir zero comercial |
| Moeda BCB | Sem tarifa publicada identificada | Persistência/tráfego não são zero |
| Mercado físico/futuros | Sob proposta | Não estimável responsavelmente sem direitos definidos |
| Push | Sem intermediário pago proposto | Compute/egress/manutenção permanecem |
| Manutenção | 2–4 pessoa-dias/mês H | Após estabilização; atendimento e incidentes extras |

Piloto de 100 localidades: infraestrutura **US$5–100/mês + clima + mercado + tributos**; usando apenas o cenário tarifário One Call acima, **US$68–163/mês + mercado/tributos**, condicionado a direitos e recursos necessários. Não é orçamento aprovado. Alertar em 50/80/100% da verba; limitar localidades monitoradas, ajustar cadência ao modelo e impedir consumo ilimitado.

Custo de desenvolvimento = 52–83 pessoa-dias × diária interna/contratada. Não foi inventada diária comercial.

## 13. Plano de testes futuro

- Contratos de providers: schemas, unidades, timezone, 429/timeout, ausência parcial, mudança de licença/proveniência, calendário e atualização fora de ordem.
- Calculadoras: invariância dimensional, ida/volta, taxas zero/negativas inválidas, quantidade zero, frete por tonelada/saca, percentuais e arredondamento.
- PostgreSQL real com roles de runtime: usuário A/B, tenant A/B, anônimo, usuário gratuito também assinante; SELECT/INSERT/UPDATE/DELETE e FKs; contexto após commit/rollback/reuso de pool. SQLite não comprova RLS.
- Auth: token Agro rejeitado em rotas comerciais, inclusive X-Tenant-Id e único vínculo; expiração/revogação, CSRF, cookie, enumeração de conta e rate limiting multiprocesso.
- Eventos: retry/crash após envio, idempotência, dead-letter, leases, justiça entre produtos, regras com dados vencidos, 404/410 de subscription e rotação VAPID.
- PWA em Android Chrome e iPhone/iPad físicos: instalação, abertura standalone, permissão negada/revogada, app fechado, modo avião, cache ausente/vencido, atualização SW, logout/troca de usuário e quota/evicção IndexedDB.
- Carga: cache frio/quente, alta cardinalidade de coordenadas, concorrência em miss, provider indisponível e orçamento máximo; observar ERP simultaneamente.
- Regressão: suites existentes de OpenWeather, clima, auth, events/outbox/notifications, alert_engine, growth e Campo; checks TS/build separados.
- Acessibilidade e UX: contraste claro/escuro, teclado/leitor de tela, rede móvel lenta, timestamps legíveis, pesquisa sem localização e consulta sem cadastro.

## 14. Critérios de aceite

1. Build e deploy próprios do Agro; nenhum compartilhamento de SW/cache pessoal com Web ou Campo.
2. Consultas e calculadoras acessíveis sem cadastro ou assinatura.
3. Horizonte/variáveis climáticas contratados demonstrados; snapshots com fonte e validade, sem dado fictício.
4. As cinco commodities só são anunciadas como disponíveis após cobertura e licença; PTAX não é apresentada como spot em tempo real.
5. Registro opcional não cria TenantUsuario/tenant/assinatura implicitamente.
6. Matriz de isolamento integral passa em PostgreSQL com role real; token Agro não acessa SaaS.
7. Alertas avaliados backend; Push real em aparelhos suportados, dedup/revogação verificadas e entrega tratada como best effort.
8. Permissões recusadas não bloqueiam uso público; privacidade/retention/exportação/exclusão validadas.
9. Limites de gasto e abuso funcionam entre processos; nenhum segredo em JS ou logs.
10. Metas propostas: p95 de leitura pública com cache abaixo de 500 ms no backend; ausência de regressão superior a 10% no p95 do ERP sob carga acordada; metas devem ser medidas no ambiente de homologação.
11. Landing e funil distinguem interesse, instalação observável e conversão comercial confirmada.
12. Contratos, custos, capacidade, rollback e responsável operacional aprovados antes do lançamento.

## 15. Veredicto

**GO COM RESSALVAS para seguir à aprovação do plano; não é autorização de implementação ou produção.**

A arquitetura comporta o aplicativo sem novo backend independente e sem duplicar integrações. Os maiores trabalhos são a fronteira de identidade/ownership, a adaptação de eventos e Push e a contratação de dados publicáveis.

**NO-GO para publicação** enquanto licenças, isolamento, orçamento e capacidade não estiverem comprovados. É possível aprovar MVP A limitado, declarando funcionalidades adiadas; não apresentar esse recorte como cumprimento integral de A–F.

Auditoria encerrada na entrega deste relatório. Implementação, migrations e mudanças de produção aguardam aprovação explícita.
