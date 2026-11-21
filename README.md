# DeepFarms - Plataforma de Gestão Rural Modular

Sistema avançado para gestão de fazendas, focado em produtividade, isolamento de dados (multi-tenancy) e interface de alta performance.

## Leitura Inicial

A ordem oficial de leitura para agentes de IA vive em **`docs/architecture/ai-bootstrap.md`** — não repetida aqui.

Manual operacional da Plataforma Balança: [docs/MANUAL_BALANCA.md](docs/MANUAL_BALANCA.md).
Manual do Usuário da Plataforma (Documentação e Portal Interativo `/manual`): [docs/manual-usuario/README.md](docs/manual-usuario/README.md).

Utilize português (pt-BR) para documentos e interações com o usuário, com acentuação correta e linguagem não técnica nas explicações.

> A fonte oficial do frontend web é `apps/web/`. O backend principal fica em `services/api` e os contratos compartilhados em `packages/`.

## Deploy em produção

O servidor de produção é acessado pelo usuário `ubuntu`, com a chave privada
local autorizada. O checkout do monorepo fica em `/opt/deepfarms/farm`.

```bash
ssh -i ~/.ssh/deepfarms-pilot-key.pem ubuntu@ec2-56-126-104-183.sa-east-1.compute.amazonaws.com
```

### Preparação para qualquer atualização

No servidor, confirme o estado antes de alterar o checkout. Só execute o
`git pull` depois de preservar e classificar toda alteração local — em especial
arquivos `.env.production`, backups e artefatos operacionais gerados pelo build.

```bash
cd /opt/deepfarms/farm
git fetch origin main
git status --short
systemctl is-active deepfarms-api deepfarms-web deepfarms-campo deepfarms-worker deepfarms-outbox nginx
git pull --ff-only origin main
```

Se `git status --short` não estiver vazio, interrompa o procedimento e resolva
o estado do checkout antes do `pull`. Não use `git reset --hard`, `git clean`
nem remova arquivos de ambiente ou backups para forçar a atualização.

Se o `pnpm-lock.yaml` ou algum `package.json` mudou, atualize as dependências
do workspace uma vez antes de atualizar Web ou Campo:

```bash
cd /opt/deepfarms/farm
pnpm install --frozen-lockfile
```

### Atualização individual de cada módulo

Execute primeiro a preparação acima. Em seguida, aplique somente o bloco do
módulo que recebeu alteração. Quando houver migration, atualize a API antes dos
consumidores que usam o banco.

#### API e migrations

Use para mudanças em `services/api/` ou em migrations. O restart inclui a API
e os dois processos que executam código Python do backend.

```bash
cd /opt/deepfarms/farm/services/api
./.venv/bin/alembic upgrade head
sudo systemctl restart deepfarms-api deepfarms-worker deepfarms-outbox
curl -fsS http://127.0.0.1:8000/docs >/dev/null && echo "API OK"
```

#### Painel Web

Use para mudanças em `apps/web/` ou nos pacotes compartilhados consumidos pelo
painel.

```bash
cd /opt/deepfarms/farm
NODE_OPTIONS=--max-old-space-size=1536 pnpm --filter web build
sudo systemctl restart deepfarms-web
curl -fsS http://127.0.0.1:3000/ >/dev/null && echo "Web OK"
```

#### PWA Campo

Use para mudanças em `apps/campo/` ou nos pacotes compartilhados consumidos
pelo PWA.

```bash
cd /opt/deepfarms/farm
pnpm --filter @agro/campo build
sudo systemctl restart deepfarms-campo
curl -fsS http://127.0.0.1:3002/ >/dev/null && echo "Campo OK"
```

#### Workers

Use quando a alteração estiver apenas em `scripts/run_worker.py`,
`background_worker` ou `events/outbox_worker`, sem mudanças de schema/API.

```bash
cd /opt/deepfarms/farm
sudo systemctl restart deepfarms-worker deepfarms-outbox
systemctl is-active deepfarms-worker deepfarms-outbox
```

#### Verificação final

Após qualquer atualização, confirme que todos os serviços permanecem ativos.
Para um deploy completo, valide também os três endereços públicos.

```bash
systemctl is-active deepfarms-api deepfarms-web deepfarms-campo deepfarms-worker deepfarms-outbox nginx
curl -fsS https://deepfarms.com.br/ >/dev/null && echo "Site OK"
curl -fsS https://app.deepfarms.com.br/ >/dev/null && echo "App OK"
curl -fsS https://campo.deepfarms.com.br/ >/dev/null && echo "Campo público OK"
```

### Primeiro deploy

Use este roteiro somente em um servidor novo, depois de instalar Git, Python
3.12, Node.js 22, Corepack/pnpm, PostgreSQL, Nginx e criar as units systemd
`deepfarms-api`, `deepfarms-web`, `deepfarms-campo`, `deepfarms-worker` e
`deepfarms-outbox`. A configuração detalhada de sistema, banco, Nginx e units
está no [runbook de produção](docs/runbooks/deploy-les-svrbo-ap01.md).

O deploy é nativo no servidor, com processos gerenciados por `systemd`.

Como o usuário que executará a aplicação, faça o clone e instale as
dependências:

```bash
sudo mkdir -p /opt/deepfarms
sudo chown ubuntu:ubuntu /opt/deepfarms
git clone <URL_DO_REPOSITORIO> /opt/deepfarms/farm
cd /opt/deepfarms/farm
corepack enable
pnpm install --frozen-lockfile
cd services/api
python3.12 -m venv .venv
./.venv/bin/pip install --upgrade pip setuptools wheel
./.venv/bin/pip install -e .
```

Crie `services/api/.env.production` e os arquivos de ambiente de Web e Campo a
partir dos valores seguros do ambiente. Eles contêm segredos e não devem ser
versionados nem copiados para o README. Com o banco acessível e as variáveis
configuradas, construa e publique a primeira versão:

```bash
cd /opt/deepfarms/farm/services/api
./.venv/bin/alembic upgrade head

cd /opt/deepfarms/farm
NODE_OPTIONS=--max-old-space-size=1536 pnpm --filter web build
pnpm --filter @agro/campo build

sudo systemctl daemon-reload
sudo systemctl enable --now deepfarms-api deepfarms-web deepfarms-campo deepfarms-worker deepfarms-outbox
systemctl is-active deepfarms-api deepfarms-web deepfarms-campo deepfarms-worker deepfarms-outbox nginx
```

Finalize usando a verificação final acima. Não é necessário reiniciar o Nginx
em deploys de código; faça isso somente quando sua configuração tiver mudado e
após validar com `sudo nginx -t`.

## Arquitetura do Sistema

Monorepo dividido em:
- **apps/web**: Interface Next.js 16 com shadcn/ui e Zustand.
- **apps/campo**: PWA de campo offline-first, extensão oficial do Caderno de Campo.
- **../balanca-platform/station**: PWA de estação de balança offline-first (pesagem de carga e animais), desacoplado dos demais módulos.
- **services/api**: Backend Python com FastAPI, SQLAlchemy e PostgreSQL.
- **../balanca-platform/service**: Serviço independente de pesagem, estações, operadores,
outbox Observer e conciliação; o DeepFarms fala com ele somente por contrato HTTP.
- **../balanca-platform/contracts**: Contratos próprios da integração da Balança.
- **packages/zod-schemas**: Contratos compartilhados do DeepFarms.

Inventário técnico completo (versões, libs, infra): `docs/architecture/architecture-inventory.md`.

## Módulos Implementados

- Identidade e Multi-Tenancy (auth, RBAC, onboarding, convites)
- Gestão Agrícola e Pecuária (talhões, safras, análise de solo, DRE por safra)
- Templates e Governança de fase de safra
- Alertas e Recomendações financeiras automáticas
- Suprimentos e Compras (reposição automática, cotações, análise de melhor fornecedor)
- Frota (manutenção preventiva, custos operacionais, benchmarks)
- Copiloto Financeiro e IA (simulação, plano de ação, autopilot adaptativo)
- Growth & A/B Testing, Telemetria de UX adaptativa
- Hedge de commodities (Mark-to-Market, exposição física × financeira)
- Vínculo territorial/fundiário (Propriedade ↔ Imóvel Rural)
- Balança (pesagem de carga e animais, offline-first, serviço desacoplado consumido por colheita/compras/vendas/pecuária)
- TARA (adapter HTTP versionado, ordens, pesagens, eventos, webhooks e ativação de estações)

Detalhamento de cada feature, decisões e histórico de implementação: `docs/CHANGELOG.md` (não faz parte da leitura padrão — consulte apenas quando precisar entender por que algo foi construído de determinada forma).

## Features

### Seletor de Produtos e Navegação Integrada nas Landing Pages (DeepFarms Gestão & Agro)
- **Descrição curta:** Componente segmentado (`ProductSwitcher`) e fundo padronizado com efeito fade (`LandingHeroBackground`) integrados aos cabeçalhos e seções de destaque das landing pages (`/` e `/agro`), eliminando discrepâncias visuais de degradê, assegurando transição suave em fade vertical para o fundo da página e permitindo ao usuário alternar com clareza entre a plataforma empresarial e o aplicativo móvel gratuito.
- **Fluxo de funcionamento:**
  1. O visitante acessa a página inicial (`/`) ou a página de ferramentas do produtor (`/agro`).
  2. O cabeçalho apresenta o seletor segmentado em pílula com os dois módulos (`🏢 Gestão Rural` e `📱 Agro Ferramentas [Grátis]`), onde o módulo atual permanece em destaque (`aria-current="page"`, fundo sólido e sombra suave) e o outro atua como link direto com hover intuitivo.
  3. No mobile, o seletor é exibido de forma adaptada no menu de navegação; no desktop, integra-se junto à marca sem poluir as ações de conversão (`Entrar`, `Começar grátis` e `Abrir aplicativo`).
  4. Ambas as páginas compartilham o mesmo background com degradê atmosférico e efeito de fade vertical suave (`LandingHeroBackground`), garantindo continuidade e fluidez visual ao alternar entre elas.

### Acesso Assistido e Suporte Operacional a Assinantes (Impersonação de Tenant)
- **Descrição curta:** Mecanismo seguro, auditado e com isolamento de licenças que permite a operadores administrativos (`super_admin`, `admin` e `suporte`) do Backoffice acessar temporariamente o ambiente de qualquer assinante (`tenant`) com perfil de proprietário (`owner`) para prestar suporte técnico, diagnosticar problemas e verificar configurações, com modo Somente Leitura por padrão, alternância para Modo Edição sob demanda com justificativa, e retorno imediato ao Backoffice sem necessidade de efetuar logout.
- **Fluxo de funcionamento:**
  1. **Início da Sessão de Acesso Assistido (`POST /api/v1/backoffice/impersonate/start`):** O operador do Backoffice localiza o assinante na tela de Gestão de Assinantes (`/dashboard/backoffice/tenants`), na listagem de Assinantes (`/dashboard/backoffice/assinantes`) ou diretamente no chamado de suporte (`/dashboard/backoffice/support`). Ao clicar em "Acessar como Assinante", abre o diálogo `ImpersonateTenantDialog`, onde seleciona o modo inicial (`READ_ONLY` como padrão ou `READ_WRITE`), a categoria e a justificativa obrigatória do atendimento (mínimo 5 caracteres).
  2. **Emissão de Token com Escopo de Tenant e Proteção de Licença (`ImpersonationService.start_impersonation`):** O backend valida a permissão `backoffice:impersonate` do operador e a atividade do tenant, registra a sessão em `admin_impersonations` e gera log em `admin_audit_log`. Emite um JWT com claims `impersonating: true`, `role: "owner"`, `session_required: false` (garantindo que o acesso do suporte **não consuma vaga simultânea** do cliente na tabela `SessaoAtiva`), contexto RLS para o tenant e o plano contratado do cliente.
  3. **Preservação de Sessão via Cookies (`apps/web/src/app/actions/auth.ts`):** O painel web salva o token de backoffice original em um cookie seguro `backoffice_return_token` e grava a rota de origem em `backoffice_return_path`. O cookie `token` passa a conter o token de impersonação, redirecionando o operador de forma transparente para o `/dashboard` do cliente.
  4. **Experiência Visual e Modo Somente Leitura (`ImpersonationBanner`):** Uma barra fixa no topo da interface sinaliza que o operador está em modo de Acesso Assistido, exibindo o nome do cliente, badge com o modo ativo e ações. Em modo `READ_ONLY`, qualquer tentativa de mutação no banco (`POST`, `PUT`, `PATCH`, `DELETE`) é imediatamente interceptada e bloqueada pelo backend com HTTP 403 Forbidden ("Modo Somente Leitura ativo na sessão de suporte").
  5. **Alternância Dinâmica de Modo (`PATCH /api/v1/backoffice/impersonate/mode`):** Caso seja necessário efetuar correções no ambiente do assinante, o operador clica em "Habilitar Edição" no banner, informa a justificativa formal e o backend registra a alteração em auditoria, reemitindo o token com `impersonation_mode: "READ_WRITE"`. O operador pode retornar voluntariamente a `READ_ONLY` a qualquer instante.
  6. **Retorno Imediato ao Backoffice (`POST /api/v1/backoffice/impersonate/stop`):** Ao concluir o atendimento, o operador clica no botão "Voltar ao Backoffice" presente no banner superior. O backend grava a data/hora de término em `admin_impersonations`, o frontend restaura o token original através da Server Action `stopImpersonationCookies()` e redireciona o operador de volta à tela do Backoffice de onde partiu, mantendo intacta sua sessão administrativa original.
- **Bugfixes Focados:**
  * **Problema Corrigido:** Ao iniciar acesso assistido clicando em "Entrar como assinante", o operador era redirecionado inesperadamente para a tela de `/login` em vez de ser direcionado ao `/dashboard` do assinante. O problema ocorria porque o endpoint `/auth/me` tentava resolver a identidade exclusivamente na tabela `AdminUser` pelo `user_id` da claim `sub` (que no login padrão do DeepFarms provém da tabela `usuarios`), gerando 404 e acionando o fallback de logout do client. Além disso, o Zustand e o localStorage no client não eram sincronizados imediatamente com o novo token de impersonação antes da transição de página.
  * **Comportamento Esperado:** O `/auth/me` resolve o operador de forma transparente em `AdminUser` (por ID ou email) e em `Usuario` global, ativa o contexto do tenant sob RLS e retorna os dados de impersonação sem falhas. O diálogo no frontend atualiza o Zustand store e os cookies antes do redirecionamento, permitindo que o suporte entre diretamente na página principal (`/dashboard`) do assinante em modo assistido.
  * **Problema Corrigido:** Ao acessar `/dashboard` como Administrador SaaS sem impersonação (ou durante o carregamento de contexto com suporte), rotas de módulos operacionais como `/api/v1/pecuaria/dashboard/resumo-executivo` disparavam erro HTTP 403 Forbidden. Isso ocorria porque: (1) no frontend, o `page.tsx` disparava queries do tenant mesmo para o Administrador global quando havia tenant residual no storage; (2) no backend, `require_module` não consultava as claims de módulos da sessão de suporte, `require_tier` não liberava o suporte e `get_unidade_produtiva_context` exigia vínculo individual do operador na tabela de fazendas do cliente; e (3) o middleware RLS não extraía `tenant_id` enviado via header `x-tenant-id`.
  * **Comportamento Esperado:** Para o Administrador global sem impersonação, o frontend exibe o estado de boas-vindas com atalhos para o Backoffice e bloqueia disparos de queries de tenant. Para operadores em acesso assistido (impersonação), `require_module`, `require_tier` e `get_unidade_produtiva_context` reconhecem a permissão ampla de suporte para navegar nas unidades produtivas e módulos do cliente sem barreiras indevidas de 403.

### Política de Preços e Pacotes All-In por Perfil Produtivo, Hectares Equivalentes (HEq), Acessos Simultâneos e Checkout Composto
- **Descrição curta:** Política comercial unificada onde todos os 5 pacotes oficiais (*Familiar*, *Pequeno Produtor*, *Médio Produtor*, *Grande Produtor* e *Grupo*) entregam 100% dos módulos da plataforma (`ALL_MODULES`), precificados pela capacidade operacional em **Hectares Equivalentes (HEq)** — com isenção integral de áreas de preservação ambiental (`APP` e `Reserva Legal`), ponderação por vocação cultural, não duplicação em consórcio ou sucessão *Safra + Safrinha* e integração Lavoura-Pecuária (ILP) — somada à quantidade de **acessos simultâneos web** contratados (com isenção total do aplicativo **DeepFarms Campo** e desconto de 20% na licença adicional anual).
- **Fluxo de funcionamento:**
  1. **5 Perfis Produtivos All-In (`seed_plans.py` e `seed_plan_pricing.py`):** Todos os pacotes habilitam 100% dos módulos nativos operacionais, gerenciais, fiscais e de inteligência (`ALL_MODULES`, `plan_tier = "ENTERPRISE"`), diferenciando-se pela franquia de área produtiva equivalente (`100`, `500`, `2.000`, `6.000` ha ou ilimitado no *Grupo*), limite de propriedades (`1`, `2`, `5`, `10` ou ilimitado) e franquia base de acessos simultâneos web inclusos (`1`, `2`, `5`, `10` e `20`). As extensões corporativas `EXT_IOT` (*Integração IoT*) e `EXT_ERP` (*Bridge ERP Corporativo*) são opcionais, contratadas à parte (`EXTENSOES_CONTRATADAS_A_PARTE`) e podem ser selecionadas diretamente no simulador para compor a mensalidade/anuidade (com 20% de desconto no plano Anual).
  2. **Cálculo Justo de Hectares Equivalentes (`PlanoPricingService.calcular_hectares_equivalentes_operacao` e `calcular_consumo_capacidade_tenant`):**
     - **Isenção Ambiental (`0.0x`):** Áreas cadastradas como `APP`, `RESERVA_LEGAL` ou `AREA_AMBIENTAL` em `AreaRural` são 100% isentas e jamais consomem a franquia de hectares contratada (`AreaRuralService._validar_limite_hectares_area`).
     - **Fator de Intensidade por Cultura:** Áreas de Pastagem/Silvicultura aplicam fator `0.5x`; Grãos/Anuais aplicam `1.0x`; Café/Perenes/Citros/Cana/Algodão aplicam `2.5x`; e Hortifrúti aplica `4.0x` (com teto de proteção que impede que culturas intensivas em pequenas áreas forcem mudança desproporcional de faixa).
     - **Múltiplas Culturas no Mesmo Talhão (Consórcio ou Sucessão Safra + Safrinha):** Quando o mesmo `AreaRural` possui dois ou mais `Plantio` na mesma `Safra` (seja em consórcio ou em 1ª e 2ª safra), a área física do talhão **não é somada em duplicidade**, prevalecendo apenas o maior fator cultural do ano agrícola naquele talhão.
     - **Fazenda Mista (Agricultura + Pecuária / ILP):** A franquia comporta até `2,0 cabeças/ha` sem custo extra de área; apenas o rebanho ativo que exceder a lotação padrão é convertido à razão de `2 cabeças excedentes = 1 HEq`.
  3. **Controle de Acessos Simultâneos Web e Isenção do App Campo (`AuthService._verificar_disponibilidade_licenca_simultanea` e `CampoService._make_device_jwt`):** O cadastro de membros na equipe é ilimitado; o controle incide apenas sobre sessões simultâneas ativas (`SessaoAtiva`) no painel web (`escopo_produto="web"`). Tokens de dispositivos e operadores do aplicativo **DeepFarms Campo** (`apps/campo`) emitem `product_scope: "campo"` e `session_required: false`, ficando 100% livres da contagem de acessos simultâneos.
  4. **Tabelas Progressivas de Licenças Adicionais com Desconto Anual (`PlanoPricingService.calcular_preco_total`):** Acessos simultâneos web acima da franquia base são precificados por faixas progressivas específicas de cada pacote (`PlanoPricing`). No ciclo `ANUAL`, o pacote base concede 2 meses grátis (economia de 16,7%) e as licenças adicionais de usuário recebem **20% de desconto** acumulativo.
  5. **Simulador Transparente Antes do Cadastro e Checkout Composto no Stripe (`POST /api/v1/billing/plans/simular` e `StripeService.montar_line_items_compostos`):** Na seção de planos da Landing Page (`/`) e **logo no Passo 1 do fluxo de criação de conta (`/register`) — antes de solicitar qualquer dado cadastral ou credencial do produtor**, a plataforma apresenta o aviso transparente de como a mensalidade/anuidade é calculada e disponibiliza o simulador interativo (Área Total, Reserva Legal/APP isenta, Cultura/Atividade principal, Rebanho Bovino para ILP e Acessos Simultâneos Web), exibindo imediatamente o pacote ideal recomendado, o extrato itemizado (Pacote Base + Licenças Extras + App Campo Isento R$ 0,00) e a economia anual. Somente após conferir e aprovar o valor no Passo 1 o produtor avança ao Passo 2 para preencher seus dados cadastrais. Ao contratar via Stripe (`criar_checkout_assinatura`), a sessão de Checkout recebe `line_items` compostos separados (item 1: Pacote Base; item 2: Licenças Adicionais de Acesso Simultâneo Web com `quantity = usuarios_adicionais`) e metadados auditáveis (`plano_codigo`, `ciclo`, `usuarios_contratados`, `usuarios_adicionais`), sincronizados automaticamente no webhook `checkout.session.completed`.

### Controle de Ativação de Módulos e Extensões (IoT / ERP) nos Pacotes
- **Descrição curta:** O Backoffice pode ativar ou desativar qualquer módulo do catálogo (exceto o Núcleo `CORE`). Módulos inativos deixam de aparecer nos pacotes, e as extensões `EXT_IOT` (*Integração IoT*) e `EXT_ERP` (*Bridge ERP Corporativo*), quando inativas, ficam visíveis como "Indisponível" mas não podem ser selecionadas, cobradas nem contratadas.
- **Fluxo de funcionamento:**
  1. **Ativação no Backoffice (`/dashboard/backoffice/modules`):** Cada card de módulo tem um switch Ativo/Inativo que chama `POST /api/v1/backoffice/modules/{module_id}/toggle-status`. O status fica salvo como override `ativo` em `ConfiguracaoSaaS` (chave `backoffice:module_catalog`). O `CORE` não pode ser desativado (HTTP 422).
  2. **Filtro nos pacotes (`ModuloMetadata.filtrar_modulos_ativos`):** `GET /billing/plans`, `GET /billing/plans/landing`, `GET /backoffice/plans`, `GET /billing/my-account` e o simulador (`total_modulos_liberados`) retornam `modulos_inclusos` sem os módulos inativos. Ao criar ou editar um plano no Backoffice, os módulos inativos também são removidos antes de salvar.
  3. **Catálogo público (`GET /api/v1/billing/modules/catalog`):** Retorna `modulos_ativos`, `modulos_inativos` e a lista de `extensoes` com o status `ativo`. O cadastro (`/register`) usa esse retorno para filtrar os módulos dos pacotes e bloquear as extensões inativas (card desabilitado, checkbox `disabled`, badge "Indisponível"). Uma extensão marcada antes de ser desativada sai do cálculo automaticamente.
  4. **Validação no backend:** `OnboardingService.register_new_tenant` recusa com HTTP 400 qualquer pedido que inclua uma extensão inativa, e `POST /billing/invoices/{id}/checkout-stripe` ignora extensões inativas ao montar os `line_items` do Stripe.

### Visualização e Ocultação de Senha (PasswordInput) e Harmonização de Diálogos
- **Descrição curta:** Implementação de componente padronizado `PasswordInput` com botão interativo para alternar a visibilidade de senha (mostrar/ocultar) em todos os formulários da aplicação, acompanhado da conformidade do diálogo de alteração de senha às diretrizes de design system.
- **Fluxo de funcionamento:**
  1. **Componente Reutilizável (`PasswordInput`):** Componente baseado em `Input` nativo com estado local para alternância de tipo (`password` / `text`), botão de alternância com ícones contextuais (`Eye` e `EyeOff`), acessibilidade via `aria-label` e padding interno protegido (`pr-9`), com total compatibilidade para React Hook Form (`forwardRef`).
  2. **Disponibilização Universal:** Integrado nos formulários de Login (`/login`), Registro inicial (`/register`), Ativação de conta (`/ativar-conta`), Aceite de convite (`/convite/aceitar`), Redefinição de senha (`/reset-password`), Diálogo de alteração de senha (`ChangePasswordDialog`), Gestão de usuários do Backoffice (`/dashboard/backoffice/admin-users`), Criação de assinantes/tenants e Assinatura eletrônica de requisições.
  3. **Harmonização do Diálogo de Senha:** O modal `ChangePasswordDialog` passa a utilizar `DialogBody`, `DialogFooter`, cabeçalho semântico e botões outline com cantos `rounded-sm`.

### Cadastro Manual de Assinantes no Backoffice com Política Comercial All-In
- **Descrição curta:** Alinhamento do fluxo de criação administrativa de assinantes (`/dashboard/backoffice/assinantes`) com a nova política comercial All-In, incorporando dimensionamento agronômico por Hectares Equivalentes (HEq), contratação de licenças web adicionais com precificação progressiva, catálogo dinâmico de extensões opcionais (`EXT_IOT` e `EXT_ERP`) com validação de status ativo e geração automática da primeira fatura calculada.
- **Fluxo de funcionamento:**
  1. **Abertura e Pré-Preenchimento (`assinantes-client.tsx`):** O operador administrativo aciona o botão "Novo Assinante", que reseta o formulário e pré-seleciona o primeiro pacote comercial ativo com franquia mínima de usuários (`usuarios_contratados`).
  2. **Auxiliar de Dimensionamento HEq (Opcional):** Permite informar a área total da fazenda, área ambiental/APP isenta, vocação cultural (fator de 0.5x a 4.0x) e rebanho ILP (cabeças excedentes). O sistema calcula instantaneamente o HEq e sugere o pacote All-In mais adequado com ação rápida de "Aplicar".
  3. **Seleção de Extensões Opcionais com Validação de Catálogo:** O formulário consome `GET /api/v1/billing/modules/catalog` para recuperar preços atualizados de `EXT_IOT` e `EXT_ERP`. Caso alguma extensão esteja desativada globalmente no Backoffice, o card é exibido desabilitado com o badge "Inativo no Catálogo", impedindo sua seleção.
  4. **Composição Financeira em Tempo Real:** Exibe um resumo discriminado do pacote base, licenças adicionais, extensões e total estimado (mensal ou anual com desconto de 2 meses grátis e 20% off nos adicionais), além da indicação clara de agendamento de cobrança pós-trial.
  5. **Persistência e Fatura no Backend (`POST /api/v1/backoffice/tenants`):** O backend valida a existência e ativação do plano e das extensões solicitadas, grava `branding={"extensoes_contratadas": [...]}` no `Tenant` e gera a `Fatura` inicial em estado `ABERTA` com vencimento ajustado ao período de trial (ou 3 dias caso sem trial), refletindo exatamente os valores contratados.

### Correção: Sessões Vencidas Exibidas como Ativas (`/dashboard/settings/sessoes`)
- **Problema corrigido:** As listagens `GET /api/v1/auth/sessions/me` e `GET /api/v1/auth/sessions/team` consideravam apenas `status = 'ATIVA'`, exibindo como ativas sessões cujo `expira_em` já havia passado; a lista da equipe mostrava somente o apelido do usuário.
- **Comportamento esperado:** As duas listagens filtram também por `expira_em > agora` (UTC). A lista da equipe exibe `usuario_nome` (`nome_completo`, com fallback para apelido e username).

### Blindagem de Isolamento Multi-Tenant e PostgreSQL RLS (Hardening Pré-Deploy)
- **Descrição curta:** Correção estrutural das políticas de Row-Level Security (RLS) do PostgreSQL, unificação da injeção de sessão (`Depends(get_session)`), propagação parametrizada de `app.current_tenant_id` em rotas web, dispositivos de campo (`device_token`), workers de eventos (`domain_event_outbox`) e motor de alertas, além do ajuste da regra `R1` do linter de segurança multi-tenant.
- **Fluxo de funcionamento:**
  1. **Políticas RLS Seguras (`20261102_rls_policies_hardening` e `baseline_contract.py`):** Todas as 188 políticas do contrato de baseline utilizam `NULLIF(current_setting('app.current_tenant_id', true), '')::uuid`, evitando falhas de conversão `DataError` quando conexões do pool têm a GUC resetada para string vazia `''`.
  2. **Proteção de Escrita em Modelos Globais:** Em `modelos_fitossanitarios` e `modelos_zoosanitarios`, a cláusula `OR (tenant_id IS NULL)` permanece restrita à política `FOR SELECT`, enquanto `INSERT`, `UPDATE` e `DELETE` exigem correspondência estrita com `app.current_tenant_id`.
  3. **Leitura Pública de Passaportes ESG:** As políticas `FOR SELECT` de `rastreabilidade_passaportes`, `rastreabilidade_passaporte_eventos` e `rastreabilidade_passaporte_evidencias` autorizam leitura anônima exclusivamente quando o passaporte está marcado como `publico = true` e `status = 'PUBLICADO'`.
  4. **Sessão Única e Resiliente por Requisição:** Todos os routers utilizam `Depends(get_session)` (eliminando o *split-session* com `Depends(get_db)`), autenticadores de dispositivos de campo (`_get_device_from_token`) e tokens `is_superuser` com `tenant_id` ativam `_activate_session_tenant`, e falhas de telemetria em `require_module` executam `rollback()` seguido de reativação do contexto RLS.
  5. **Workers e Serviços Assíncronos:** `DomainEventOutboxService` e `AlertLifecycleService` configuram o contexto via `set_config('app.current_tenant_id', :tenant_id, true)` parametrizado e sincronizam `session.info["tenant_id"]`, preservando o RLS após `commit()`/`rollback()` e permitindo que o worker de outbox processe filas multi-tenant sob RLS.
- **Bugfixes Focados:**
  * **Problema Corrigido:** As políticas de `INSERT`, `UPDATE` e `DELETE` de `modelos_fitossanitarios` e `modelos_zoosanitarios` continham `OR (tenant_id IS NULL)`, permitindo alteração ou exclusão de modelos globais por qualquer sessão. **Comportamento Esperado:** Apenas `SELECT` permite ler registros com `tenant_id IS NULL`; operações de escrita exigem `tenant_id` idêntico ao `app.current_tenant_id`.
  * **Problema Corrigido:** 82 rotas misturavam `Depends(get_db)` com `Depends(get_session)`, abrindo duas conexões distintas e executando queries em conexão sem `app.current_tenant_id`, enquanto a regra `R1` do `lint_tenant_safety.py` buscava `Depends(get_session)` por engano. **Comportamento Esperado:** Todas as rotas compartilham a mesma `AsyncSession` via `Depends(get_session)` e o linter valida `Depends(get_db)` com zero violações `R1`.
  * **Problema Corrigido:** Rotas autenticadas por `device_token` (`campo/router.py` e `agricola/caderno/router.py`), requisições de `is_superuser` com `tenant_id` e o `require_module` (quando a telemetria falhava sem `rollback()`) deixavam a sessão sem contexto RLS ou em transação abortada. **Comportamento Esperado:** Contexto RLS ativado e mantido de forma íntegra em todos os fluxos.

### UI/UX Adaptativa Multi-Dispositivo e Design System Unificado — Painel Web (`apps/web`), PWA Agro (`apps/agro`) e PWA Campo (`apps/campo`)
- **Descrição curta:** Arquitetura de UI/UX adaptativa e Design System unificado (Verde Esmeralda Agro `#006B3D`, superfícies neutras orgânicas, bordas `rounded-sm`, botões `outline`/`sm` e suporte a Dark/Light Mode) que espelha os componentes personalizados de `components/ui` do módulo `apps/web` no módulo `apps/agro` (`Button`, `Badge`, `Card`, `CardAction`, `Input`, `PasswordInput`, `Label`, `Alert`, `Skeleton`, `Separator`, `Tabs`, `ToggleGroup`, `Table`, `Select`, `Dialog`, `Sheet`, `Tooltip`, `DropdownMenu`, `ConfirmDialog`, `Checkbox`, `Collapsible`, `Avatar`, `StatusBadge`, `Progress`, `ScrollArea` e `Textarea`), identifica em tempo de execução onde `apps/web`, `apps/agro` e `apps/campo` estão sendo executados (`mobile`, `tablet` ou `desktop`; modo instalado `standalone` vs `browser`; `ios`, `android` ou `other`) e adapta automaticamente a navegação, cabeçalhos, barras laterais, densidade de toque e ergonomia nativa.
- **Fluxo de funcionamento:**
  1. Ao carregar `apps/web`, `apps/agro` ou `apps/campo`, o provedor `DeviceContextProvider` avalia sinais reais do dispositivo (largura de viewport, `matchMedia("(pointer: coarse)")`, `matchMedia("(display-mode: standalone)")`, `navigator.standalone` no iOS e `userAgent`) através do motor puro `device-detection.ts`.
  2. **Em Smartphones (`mobile`, `< 768px`):** A interface assume comportamento de aplicativo nativo com barra superior contextual (exibindo botão de retorno, título da sub-rota ativa, módulo e unidade produtiva selecionada), dock inferior fixo (`BottomNav` / `MobileBottomNav`) com `safe-area-inset-bottom`, seletores de Produtor/Propriedade integrados à gaveta móvel, lançadores rápidos de apontamento e bloqueio de *overscroll* de navegador.
  3. **Em Tablets (`tablet`, `768px–1023px` ou iPadOS/Android Tablet):** A barra inferior de celular dá lugar à barra lateral (`AdaptiveSidebar` / `AppSidebar`) iniciada automaticamente em modo **Navigation Rail** retrátil por ícones, liberando área útil vertical e apresentando seletores e formulários como modais centralizados (`centered-dialog`).
  4. **Em Desktops (`desktop`, `>= 1024px` com ponteiro fino):** A barra lateral expande os menus separados por módulo contratado que se expandem conforme selecionados, exibindo no rodapé da barra lateral e na barra superior o diagnóstico do ambiente detectado (`PWA`, `Mobile`, `Tablet` ou `Web`), alternância imediata de tema Claro/Escuro e grades operacionais multi-colunas.

### DeepFarms Agro — Correções Críticas de Sessão, Cotas e Preparação de Staging (AGRO-ADMIN-01H1)
- **Descrição curta:** Implementação das correções críticas levantadas na auditoria integrada AGRO-ADMIN-01G, contemplando o endpoint leve de heartbeat com cookies HttpOnly para a PWA Agro, reserva atômica de cotas de provedores de clima no Redis com rollback em falha upstream, eliminação do fallback de JWT_SECRET_KEY em staging/produção para a PLATFORM_CREDENTIALS_MASTER_KEY, recalibração estrita da matriz de homologação para 27.3% (3/11 aprovados com evidências auditadas) e provisionamento de artefatos efêmeros de staging.
- **Fluxo de funcionamento:**
  1. **Heartbeat Seguro da PWA Agro:** Durante o uso ativo do aplicativo `apps/agro`, o hook e o componente cliente `SessionHeartbeat` monitoram eventos de interação do usuário (cliques, toques, rolagem) e estado de visibilidade da janela. Quando o usuário está ativo em primeiro plano e com rede disponível, despacha periodicamente uma requisição para `POST /api/v1/auth/heartbeat`. O endpoint autentica o usuário via cookie HttpOnly (`deepfarms_agro_session` ou `deepfarms_session`), valida o header `X-Agro-CSRF`, verifica se o usuário está ativo no banco (rejeitando inativos com HTTP 403), confirma se a sessão existe e está ativa (rejeitando expiradas ou revogadas com HTTP 401) e aplica throttling de 60 segundos em memória para evitar gravações redundantes de I/O no PostgreSQL. Sessões válidas têm seu `ultimo_heartbeat` e `expira_em` renovados conforme a política de timeout de inatividade. Em background (aba oculta) ou offline, o heartbeat é pausado, evitando sessões artificiais.
  2. **Controle Atômico de Cotas de Clima:** No `DynamicWeatherOrchestrator`, antes de despachar chamadas a provedores meteorológicos com limites contratados (ex: WeatherAPI e OpenWeather), o `ClimaCache` executa um script Lua atômico no Redis (`reserve_monthly_quota`). O script valida se o consumo do mês corrente está abaixo do limite contratado; se estiver, incrementa atomicamente o contador. Caso ocorra erro de rede, timeout upstream ou exceção transitória, o orquestrador executa imediatamente o `rollback_quota_reservation`, estornando a cota reservada e impedindo cobranças indevidas de franquia por falhas do provedor externo. Além disso, fallbacks públicos para provedores comerciais sem licença explícita são recusados (`is_provider_authorized_for_public`).
  3. **Isolamento de Chave Mestra de Credenciais:** Em `PlatformWeatherCredentialsService`, o método de derivação KEK v2 (`_derive_platform_kek`) e o validador de inicialização (`validate_master_key_configuration`) impõem obrigatoriedade estrita da variável `PLATFORM_CREDENTIALS_MASTER_KEY` (mínimo de 16 caracteres) em ambientes de staging e produção. O fallback silencioso para `JWT_SECRET_KEY` foi sumariamente eliminado nesses ambientes, levantando `RuntimeError` em caso de ausência. A rotina assíncrona `reencrypt_all_credentials_to_canonical_kek` garante recifragem atômica de credenciais legadas para o KEK v2 com auditoria completa.
  4. **Matriz de Homologação Baseada em Evidências:** A matriz do dashboard executivo (`/backoffice/agro/dashboard/homologacao` e indicador resumo) foi corrigida para refletir apenas itens com aprovação comprovada por evidências verificáveis: 3 itens APROVADOS (Item 5 — Parser XLS Oficial BIFF8/OLE2; Item 10 — Integridade de Catálogos Globais; Item 11 — Tipagem Estrita TypeScript e Testes Web/Agro), totalizando exatamente 27.3% de conclusão. Itens dependentes de infraestrutura física dedicada (PostgreSQL 16 e Redis 7) foram fixados como PENDENTES, e itens com validação puramente local (Chave mestra física, proveniência DERAL sem mTLS, concorrência multi-worker) foram fixados como EM VALIDAÇÃO.
  5. **Infraestrutura Descartável de Staging:** Foram criados os artefatos `infrastructure/staging/docker-compose.agro-staging.yml`, `infrastructure/staging/.env.staging.example`, `scripts/staging/validate_isolation.py`, `scripts/staging/up.sh` e `scripts/staging/down.sh`. O validador rejeita sumariamente qualquer inicialização caso variáveis apontem para RDS, ElastiCache ou S3 de produção, ou caso as portas não estejam restritas a `127.0.0.1`.

- **Bugfixes Focados:**
  * **Problema Corrigido:** O indicador de usuários ativos do DeepFarms Agro no Dashboard de Observabilidade exibia contagens defasadas ou inconsistentes devido à ausência de um ciclo seguro de heartbeat para sessões autenticadas via cookie HttpOnly. **Comportamento Esperado:** O endpoint `POST /api/v1/auth/heartbeat` autentica de forma segura via cookie HttpOnly com proteção CSRF e throttling, renovando `ultimo_heartbeat` e alimentando com precisão os indicadores de usuários simultâneos no Backoffice sem expor tokens ao JavaScript.
  * **Problema Corrigido:** Provedores de previsão de tempo podiam estourar a franquia mensal de faturamento sob tráfego concorrente (*race condition* TOCTOU) ou perder cotas em falhas de rede do upstream sem receber resposta. **Comportamento Esperado:** Reserva atômica no Redis antes da chamada externa via script Lua e rollback automático em falhas, garantindo teto orçamentário estrito por provedor e observabilidade de bloqueio.
  * **Problema Corrigido:** Credenciais climáticas de produção realizavam fallback silencioso para a chave de autenticação web `JWT_SECRET_KEY`. **Comportamento Esperado:** Bloqueio mandatório com `RuntimeError` em staging/produção caso `PLATFORM_CREDENTIALS_MASTER_KEY` não esteja explicitamente configurada.
  * **Problema Corrigido:** O dashboard executivo apresentava 63.6% de homologação com base em aprovações presumidas e validações locais simplificadas. **Comportamento Esperado:** Percentual real de 27.3% estritamente calculado sobre itens homologados com evidências auditadas, com pendências de infraestrutura física explicitamente demarcadas para homologação em staging na fase 01H2.

- **Descrição curta:** Consulta e exibição resiliente de séries macroeconômicas oficiais do Banco Central do Brasil (Meta Selic, IPCA mensal, IPCA 12 meses e cotação Euro PTAX comercial) na aba Mercado do DeepFarms Agro (`apps/agro`).
- **Fluxo de funcionamento:**
  1. O usuário acessa `/mercado` no PWA DeepFarms Agro.
  2. O cliente consulta o endpoint público `GET /api/v1/public/mercado/indicadores-macro` via cache local em `localStorage` para exibição instantânea offline-first.
  3. No backend FastAPI, a requisição passa por rate-limiting por IP e consulta a camada de cache em dois níveis (L1 memória do processo com lock atômico *single-flight* contra *stampede* + L2 Redis com TTL de 30 minutos).
  4. O serviço opera de forma totalmente desacoplada, sem autenticação, sem conexões com o banco comercial PostgreSQL (`db_pool_size=3`).
  5. Se o SGS/BCB responder com sucesso, os dados são padronizados e cacheados. Se o BCB estiver temporariamente indisponível ou em janela de manutenção, o serviço ativa o fallback transparente da última observação válida de até 30 dias.
  6. No frontend, os indicadores são apresentados em cards responsivos com formatação pt-BR (`% a.a.`, `% a.m.`, `% 12M`, `R$`), badges de estado (online/cache/offline/defasado) e datas de referência explícitas.

### Mercado Público — Inteligência e Estatísticas Agropecuárias Oficiais (IBGE/SIDRA)
- **Descrição curta:** Consulta pública e gratuita de estatísticas oficiais de produção agropecuária (PAM — Produção Agrícola Municipal, PPM — Pesquisa da Pecuária Municipal e LSPA — Levantamento Sistemático da Produção Agrícola) via API SIDRA do IBGE na aba Mercado do DeepFarms Agro (`apps/agro`).
- **Fluxo de funcionamento:**
  1. O usuário seleciona cultura agrícola (ex: soja, milho, café, trigo, arroz), rebanho (ex: bovinos, suínos, galináceos, ovinos) ou produção animal (leite, ovos, mel) no card de Inteligência do IBGE.
  2. O usuário define o nível de abrangência territorial: Brasil (Nacional), Estado (UF) ou Município (com lista carregada sob demanda e cacheada por 7 dias). Para lavouras elegíveis, é possível alternar entre a série anual consolidada (PAM) e a estimativa mensal da safra em andamento (LSPA).
  3. O cliente web consulta os endpoints anônimos `GET /api/v1/public/mercado/ibge/catalogo`, `/municipios/{uf}` e `/estatisticas` via `localStorage` com suporte offline imediato.
  4. O backend valida os parâmetros contra uma lista estrita de produtos, tabelas e UFs homologadas (proteção contra injeção e requisições arbitrárias ao IBGE), sem consumir nenhuma sessão do banco comercial PostgreSQL.
  5. As consultas utilizam cache em dois níveis (Redis compartilhado com fallback em memória L1) com proteção de concorrência por lock distribuído *single-flight* e taxa limite de 60 requisições/min por IP. Em caso de indisponibilidade externa do SIDRA, o sistema ativa fallback automático com os últimos dados oficiais conhecidos.
  6. No frontend, são exibidos cards com métricas de Produção (t ou cabeças), Área Plantada e Colhida (ha) e Rendimento Médio (kg/ha), acompanhados do link oficial para a tabela correspondente no portal SIDRA e aviso regulatório esclarecendo que as estatísticas de produção não constituem cotação de preços.

### Mercado Público — Preços Públicos Reais de Commodities (DERAL e CONAB)
- **Descrição curta:** Apresentação de preços agropecuários reais nos cards de commodities da aba Mercado do DeepFarms Agro (`apps/agro`), consumindo levantamentos oficiais de preços médios recebidos pelos produtores junto a órgãos públicos governamentais (DERAL/SEAB-PR e CONAB/MAPA), com explicitação de unidade comercial, praça de coleta, data de referência e distinção metodológica rigorosa.
- **Fluxo de funcionamento:**
  1. O usuário acessa a seção de commodities em `/mercado` no PWA DeepFarms Agro.
  2. O cliente web busca dados cacheados em `localStorage` para renderização imediata sem latência e realiza requisição assíncrona ao endpoint anônimo `GET /api/v1/public/mercado/precos`.
  3. No backend FastAPI, a consulta usa cache L1 e reconcilia o identificador do snapshot ativo entre processos no máximo uma vez por minuto, para refletir atualizações publicadas pelo worker sem exigir reinício da API.
  4. São disponibilizados preços médios reais de comercialização para Soja (sc 60 kg), Milho (sc 60 kg), Café Arábica (sc 60 kg), Boi Gordo (@ 15 kg), Trigo (sc 60 kg), Arroz (sc 50 kg) e Feijão Carioca (sc 60 kg). Para produtos sem cotação aberta oficial (ex: Algodão pluma), é mantido o status transparente de consulta na fonte oficial homologada (CEPEA/ESALQ).
  5. Os cards do frontend exibem o valor numérico em reais (`R$`), unidade de medida, praça de referência (ex: Paraná estadual ou média nacional CONAB), identificação da instituição responsável e aviso metodológico esclarecendo que os dados caracterizam levantamento estatístico de preços médios recebidos pelos produtores, diferenciando-se de cotações físicas em tempo real e de contratos futuros em bolsas.
  6. Também foi corrigido o comportamento da Meta Selic (BCB SGS série 432), garantindo filtro temporal estrito para evitar a exibição de reuniões futuras do Copom.

### Mercado Público — Expansão Controlada do Catálogo de Commodities (DERAL/SEAB-PR)
- **Descrição curta:** Expansão orientada a dados do catálogo público de commodities na aba Mercado do DeepFarms Agro (`apps/agro`), substituindo a lista estática de 8 cards por um catálogo dinâmico com 22 commodities, 21 preços reais auditados do DERAL/SEAB-PR, segregação de URLs institucionais e download de planilhas, e pipeline atômico de snapshots.
- **Fluxo de funcionamento:**
  1. O usuário acessa `/mercado` no PWA DeepFarms Agro.
  2. A página Next.js 16 (RSC) busca os metadados cadastrais e cotações no endpoint público `GET /api/v1/public/mercado/catalogo` e passa as 22 commodities estruturadas para o componente cliente via props.
  3. No backend FastAPI, o catálogo dinâmico é construído combinando metadados agronômicos e o snapshot oficial auditado (`deral-prp-YYYY-MM-DD.json`), operando com cache em memória L1 e proteção de concorrência por lock assíncrono, mantendo total retrocompatibilidade com os endpoints `/precos` e `/precos/{commodity_id}`.
  4. O catálogo organiza 22 commodities em 7 categorias principais de mercado: Grãos e Cereais (Soja, Milho, Trigo, Arroz, Aveia Branca, Canola, Cevada, Amendoim), Café (Café Arábica), Pecuária (Boi Gordo, Boi Magro, Vaca em Pé, Frango Vivo, Suíno, Leite, Ovos), Leguminosas (Feijão Carioca, Feijão Preto), Fibras (Algodão em Pluma), Cana e Derivados (Cana-de-Açúcar) e Outros (Mandioca Industrial, Erva-Mate).
  5. 21 commodities exibem preço público real comprovado célula a célula na aba `Rav` do arquivo oficial do DERAL (`prp.xls`), acompanhado de hash SHA-256 e período de apuração semanal. O Algodão em Pluma permanece referenciado como Link Homologado junto à CONAB/MAPA, sem cotações simuladas.
  6. Para eliminar o download involuntário de planilhas binárias, a interface segrega estritamente o botão de navegação principal ("Consultar no DERAL" -> página web informativa em `agricultura.pr.gov.br/deral/precos`) do link secundário de download ("Baixar planilha oficial (.xls)" -> arquivo bruto `prp.xls` com indicação de download e ícone de planilha).
  7. O pipeline isolado `services/api/scripts/atualizar_snapshot_deral.py` executa o download seguro via HTTPS com verificação rigorosa de certificados TLS, decodifica registros binários BIFF8 (`struct` nativo da stdlib), quantiza valores decimais com `ROUND_HALF_UP`, valida os contratos Pydantic e grava o snapshot de forma atômica (`replace`), preservando o arquivo ativo em caso de qualquer falha de rede ou integridade.
  8. O `background_worker` consulta automaticamente a planilha oficial a cada seis horas. O parser encontra produtos por rótulo e unidade, sem depender de linhas fixas; só importa, aprova com identidade técnica auditável e ativa semanas posteriores após validar HTTPS, hash, período e as 21 commodities. Falhas mantêm o snapshot ativo anterior. A API reconcilia o novo snapshot sem reiniciar.

### Mercado Público — Integração Reativa da Conversão Cambial nos Cards de Commodities
- **Descrição curta:** Integração reativa e desacoplada entre a seleção de moeda do PtaxCard e os 21 preços públicos reais de commodities do DERAL/SEAB-PR, exibindo o equivalente cambial convertido sem recarregar a página e preservando o preço oficial em BRL como principal.
- **Fluxo de funcionamento:**
  1. O usuário acessa a aba Mercado (`/mercado`) no PWA DeepFarms Agro.
  2. O seletor de moedas já existente no `PtaxCard` disponibiliza 11 moedas oficiais suportadas pelo Banco Central do Brasil (USD, EUR, GBP, JPY, CAD, CHF, AUD, CNY, ARS, CLP, ZAR).
  3. Ao selecionar uma moeda, a micro-store reativa centralizada baseada em `useSyncExternalStore` sincroniza a preferência monetária atomicamente entre todos os componentes da página e entre abas via evento de janela `storage`, sem duplicar seletores nem recarregar a aplicação.
  4. A conversão matemática pura (`valorConvertido = valorBRL / cotacaoVenda`) é calculada dinamicamente sobre a cotação oficial de venda PTAX, aplicando a convenção internacional de formatação (2 casas decimais padrão e arredondamento inteiro para moedas sem centavos como JPY e CLP).
  5. Os cards de commodities exibem de forma destacada e inalterada o preço oficial em reais (`R$ / unidade`), acompanhado imediatamente abaixo pelo equivalente cambial (`Equiv.: ≈ [Símbolo] [Valor] / [unidade física original]`) e pela indicação da taxa PTAX oficial utilizada.
  6. Em caso de ausência de cotação ou falha de conectividade, a interface mantém intacto o valor em BRL e exibe mensagem discreta de indisponibilidade ("Câmbio indisponível para [MOEDA]"), prevenindo layout shifts (`min-h-[92px]`) e garantindo tolerância offline completa.

### Mercado Público — Saneamento do Catálogo e Homologação Final de Commodities (DERAL/SEAB-PR)
- **Descrição curta:** Consolidação da integridade cadastral e ingestão unificada do catálogo público de commodities, adequando nomenclaturas comerciais oficiais (Café Beneficiado (Produtor), Feijão de Cor, Cevada em Grão, Leite (Produtor)), consolidando o extrator nativo BIFF8 e unificando o contrato de 22 commodities (21 preços públicos reais e 1 link institucional sem cotação simulada) com cache offline v4.
- **Fluxo de funcionamento:**
  1. A reconciliação do catálogo sanitizou quatro nomenclaturas comerciais para alinhamento estrito com o levantamento DERAL: `cafe-arabica` passou a exibir "Café Beneficiado (Produtor)", `feijao` passou a exibir "Feijão de Cor", `cevada` passou a exibir "Cevada em Grão" e `leite` passou a exibir "Leite (Produtor)", mantendo seus identificadores canônicos intactos para preservar a estabilidade de rotas e caches.
  2. O pipeline de atualização de dados foi consolidado exclusivamente no script `services/api/scripts/atualizar_snapshot_deral.py`, utilizando parser nativo BIFF8 (`struct` stdlib) com validação rígida de cabeçalhos ("Rav!X2" == "MÉDIA", "PREÇOS MÉDIOS SEMANAIS") e validação de schema via Pydantic (`SnapshotDeral`). O script legado de ingestão foi neutralizado com saída de segurança (`exit code 2`) para impedir sobreposições acidentais de snapshots.
  3. O endpoint anônimo `GET /api/v1/public/mercado/precos` e o catálogo dinâmico entregam exatamente 21 preços comprovados célula a célula na aba `Rav` do arquivo oficial do DERAL (`prp.xls`), enquanto a commodity Algodão em Pluma permanece explicitamente marcada com status de link homologado CONAB/MAPA, sem valores numéricos artificiais ou cotações simuladas.
  4. O cache local do frontend foi promovido para `deepfarms_agro_mercado_precos_v4`, descartando automaticamente versões parciais legadas (v1 a v3) e validando estritamente a presença integral dos 21 preços antes de persistir em `localStorage`.
  5. A homologação automatizada integrada confirma conformidade ponta a ponta através de 13 testes unitários no backend (Pytest), 116 testes unitários no frontend (Vitest) e 12 testes end-to-end (Playwright) cobrindo conversão cambial reativa, persistência offline, responsividade móvel e auditoria dos 21 preços reais.


### Mercado Público — Integridade Criptográfica do Cache Offline e Paridade Binária DERAL
- **Descrição curta:** Aprimoramento da resiliência do cache offline do catálogo de commodities (desacoplamento da cardinalidade fixa de 21 itens, validação de proveniência, integridade contra payloads truncados via `totalItens` e prevenção de contaminação cruzada de datas/hashes) e teste automatizado de paridade binária entre planilhas oficiais DERAL (`.xls`) e snapshots JSON.
- **Fluxo de funcionamento:**
  1. A validação de cache offline em `apps/agro/src/lib/mercado/precos.ts` foi desacoplada de uma lista rígida de 21 IDs, passando a aceitar qualquer quantidade de commodities legítimas (20, 21, 22 ou N) com base em integridade estrutural, unicidade de slugs canônicos, valores monetários positivos finitos e datas/hashes válidos.
  2. Para prevenir a persistência de respostas truncadas ou incompletas, o backend FastAPI e o frontend Next.js 16 compartilham a extensão retrocompatível `totalItens`; o cache só é atualizado se a quantidade de itens válidos conferir exatamente com o total esperado informado pelo serviço.
  3. Foi implementada validação de consistência em lote (*batch consistency*), garantindo que todos os itens pertençam à mesma data de apuração (`dataReferencia`) e ao mesmo arquivo de origem (`documentoHashSha256`), prevenindo contaminação cruzada entre diferentes semanas ou versões de cotação.
  4. Em caso de falha de validação ou payload corrompido, o cliente mantém intacto o último snapshot válido persistido em cache, garantindo continuidade da operação offline.
  5. Um teste automatizado independente de paridade binária (`test_paridade_snapshot_deral.py`) valida célula a célula os dados extraídos da planilha oficial DERAL (`deral-prp-2026-10-16.xls`) contra o snapshot JSON publicado, utilizando aritmética de precisão fixa (`Decimal` com arredondamento `ROUND_HALF_UP`) e verificação de SHA-256 da fonte primária.

### Identidade Individual Segregada (DeepFarms Agro)
- **Descrição curta:** Fundação de autenticação e gerenciamento de contas individuais para o aplicativo DeepFarms Agro (`apps/agro`), operando em repositório persistente segregado sem criação de tenants comerciais e com zero consumo de conexões do pool PostgreSQL do SaaS DeepFarms.
- **Fluxo de funcionamento:**
  1. O usuário anônimo navega livremente pelo PWA Agro em `/`, `/mercado`, `/clima` e `/calculadoras` sem qualquer barreira de autenticação.
  2. Caso opte por criar uma conta individual ou fazer login, o usuário acessa `/conta` através do cabeçalho ou menu móvel inferior.
  3. No cadastro (`POST /api/v1/agro/auth/register`), a requisição é atendida pelo módulo `services/api/agro_identity`, conectado ao banco SQLite segregado em diretório persistente protegido fora do código-fonte (`data/agro_identity/agro_identity.db`) com permissões estritas (`0700` no diretório e `0600` nos arquivos `.db`, `-wal`, `-shm`) e modo WAL (`journal_mode=WAL; busy_timeout=5000`) para suportar múltiplos workers Uvicorn sem contenção de locks.
  4. Um código de verificação criptográfico de 6 dígitos é despachado exclusivamente para o e-mail cadastrado (sem qualquer exposição em respostas públicas HTTP, schemas ou logs) e validado no endpoint `POST /api/v1/agro/auth/verify-email` (com suporte a reenvio via `/resend-verification`).
  5. O serviço emite tokens JWT segregados (`iss: "deepfarms:agro:auth"`, `aud: "deepfarms:agro:app"`, `account_type: "INDIVIDUAL_FREE"`) e injeta um cookie HttpOnly seguro (`deepfarms_agro_session`, SameSite=Lax), protegendo a sessão contra XSS e garantindo que nenhum token sensível seja persistido em `localStorage`.
  6. Proteção ativa contra CSRF tradicional e CSRF inter-subdomínios (`verify_agro_csrf`): mutações autenticadas via cookie têm seus cabeçalhos `Origin`/`Referer` validados contra a topologia estrita (`agro.deepfarms.com.br`, `api.deepfarms.com.br`, `app.deepfarms.com.br`, `campo.deepfarms.com.br`), bloqueando requisições forjadas originadas de outros subdomínios ou da web externa.
  7. Um guardrail isolado no backend (`verify_commercial_jwt_guardrail`) rejeita tokens individuais com HTTP 403 Forbidden antes de injetar `get_session`, assegurando que zero conexões do pool restrito de 3 conexões do PostgreSQL comercial sejam consumidas.
  8. O módulo implementa rate limiting distribuído atômico via Redis com fallback resiliente para memória de processo local (proteção contra brute force: 5 tentativas incorretas / 15 min de lockout), fluxo seguro de recuperação de senha com token de uso estritamente único transmitido exclusivamente por e-mail, revogação imediata de todas as sessões ativas do usuário ao alterar a senha, e rotina de backup online e restauração a quente com atestação de integridade física (`PRAGMA integrity_check`).

### Cofre BYOK e Proxy Seguro de Cotações (DeepFarms Agro)
- **Descrição curta:** Infraestrutura segura de cofre de credenciais externas com Envelope Encryption (AES-256-GCM + DEK individual efêmera + KEK versionada via KMS) e camada de Proxy Delegado para consulta de cotações agropecuárias com isolamento de cache por usuário, rate limiting, mitigação absoluta de SSRF e separação estrita de contratos FÍSICO vs FUTURO.
- **Fluxo de funcionamento:**
  1. O usuário individual autenticado acessa os recursos de BYOK sob o prefixo `/api/v1/agro/byok`.
  2. O cofre individual armazena as chaves de API externas utilizando Envelope Encryption de 2 camadas: uma DEK (*Data Encryption Key*) individual e efêmera de 256 bits gerada por segredo sob AES-256-GCM com AAD (`user_id + provider_slug`), cifrada sob uma KEK (*Key Encryption Key*) versionada derivada por usuário via HKDF-SHA256 e gerenciada por KMS.
  3. A rotação de chaves KMS (`POST /api/v1/agro/byok/credentials/rotate-keys`) re-encapsula a DEK sob a nova versão de KEK em tempo $O(1)$ sem necessitar decifrar nem reencriptar o payload dos dados brutos.
  4. O cofre opera em migrações versionadas exclusivas (`agro_schema_versions` no banco SQLite segregado `data/agro_identity/agro_identity.db`), sem criar tabelas nem colunas no banco comercial PostgreSQL.
  5. As respostas da API e os logs nunca expõem a chave em claro, retornando apenas metadados mascarados (`mascaraChave`: `••••••••1234`).
  6. Para compliance e auditoria regulatória, provedores externos reais (`TWELVE_DATA`, `POLYGON`, `IBKR`) são mantidos desabilitados (`DESABILITADO_LICENCA`) com avisos detalhados sobre restrições contratuais de redistribuição da CME/ICE, utilizando o conector `SIMULATED` para homologação funcional ponta a ponta sem serviços pagos.
  7. O Proxy BYOK valida preventivamente contra SSRF (catálogo estrito e fechado de provedores e commodities, com rejeição de URLs arbitrárias, esquemas locais e IPs privados) e aplica rate limiting dedicado por usuário e por provedor (30 req/min com fallback em memória).
  8. O cache privado de cotações (`agro:byok:quote:{user_id}:{provider_slug}:{commodity}:{tipo_mercado}`) possui TTL de 60 segundos e é estritamente isolado por usuário, nunca colidindo nem compartilhando dados com o cache público (`agro:ptax:*`, `agro:public:mercado:*`).
  9. O contrato de cotações padroniza as respostas separando rigorosamente Mercado FÍSICO nacional (ex: Soja Paranaguá em R$/sc 60kg, Milho Campinas, Boi Gordo SP em R$/@) de Mercado FUTURO internacional e B3 (CBOT ZS em US$ cents/bushel, B3 CCM, B3 BGI), com identificador explícito de titularidade (`titularidadeByok = f"BYOK-{user_id.hex[:8]}-{provider_slug}"`).

### Clima Público — Fundação Técnica do Backend Meteorológico (DeepFarms Agro)
- **Descrição curta:** Fundação de backend meteorológico público e resiliente (`services/api/public_clima`), com endpoint anônimo de previsão horária (24h) e diária (7d), quantização geográfica em grid espacial (~5,5 km), cache em dois níveis (Redis + memória local), controle de concorrência single-flight, proteção de taxa (rate limiting), fallback de contingência e isolamento absoluto de banco comercial e credenciais pagas.
- **Fluxo de funcionamento:**
  1. Qualquer cliente anônimo consulta o endpoint público `GET /api/v1/public/clima/previsao?lat={lat}&lon={lon}` sem autenticação, sem JWT e sem resolução de tenant.
  2. As coordenadas geográficas são validadas (-90 a 90 de latitude e -180 a 180 de longitude) e quantizadas segundo a política de grid espacial `GeoGridPolicy` (passo padrão de 0.05° ≈ 5,5 km), garantindo chave de cache padronizada e agregando consultas de propriedades vizinhas.
  3. A requisição é filtrada pela camada de proteção contra abusos (`ClimaCache.allow_request`), com limite configurável de 60 requisições por minuto por IP/bucket em Redis com fallback transparente em memória de processo.
  4. O serviço verifica o cache recente (`agro:clima:v1:fresh:{lat_grid}:{lon_grid}`) com TTL configurável (padrão de 1800s / 30 minutos). Em caso de cache hit, a resposta é entregue instantaneamente com cabeçalho `X-Cache-Status: HIT` e `emCache: true`.
  5. Em caso de cache miss, o serviço adquire um lock atômico distribuído *single-flight* no nó do grid (`agro:clima:v1:lock:{lat_grid}:{lon_grid}`) para evitar rajadas redundantes de chamadas externas (*thundering herd*). Requisições concorrentes aguardam a liberação do lock e consomem o resultado recém-gravado.
  6. A consulta upstream é mediada pelo adaptador de provedores `OpenMeteoAdapter`, que possui trava estrita de conformidade regulatória: requisições externas não licenciadas são rejeitadas preventivamente (`open_meteo_licensed=False`), impedindo consumo indevido de APIs de terceiros em produção sem contrato comercial. Para testes e desenvolvimento, o conector `SyntheticFixtureAdapter` fornece fixtures determinísticas com flag explícita `dadosSinteticos=True`.
  7. Se o provedor externo falhar ou sofrer timeout, o serviço recupera o último dado válido registrado (`agro:clima:v1:last:{lat_grid}:{lon_grid}`) com validade estendida de contingência e entrega o payload com flag `desatualizado: true` e status operacional `DEGRADADO`, garantindo continuidade do serviço.
  8. O domínio opera com zero sessões SQLAlchemy, zero acesso ao PostgreSQL corporativo (`db_pool_size=3`), e nenhuma reutilização de credenciais dos tenants comerciais (ex: OpenWeather).

### Clima Público — Catálogo Territorial e Seleção de Localidades (DeepFarms Agro)
- **Descrição curta:** Catálogo oficial dos 5.571 municípios brasileiros (IBGE / SIRGAS 2000), busca anônima de localidades sem distinção de acentos ou caixa, geolocalização por GPS mediante consentimento explícito e persistência local versionada com validação de schema na aba Clima do DeepFarms Agro (`apps/agro`).
- **Fluxo de funcionamento:**
  1. O usuário acessa a aba Clima (`/clima`) no PWA DeepFarms Agro (`apps/agro`).
  2. O cliente lê a preferência salva em `localStorage` sob a chave versionada `deepfarms_agro_clima_localidade_v1`. Se houver localidade salva, o schema é rigorosamente validado em tempo de execução (`tipoOrigem`, `municipio`, `uf`, `latitude`, `longitude`, `codigoIbge`); dados corrompidos ou em schemas obsoletos são descartados de forma segura.
  3. A localidade ativa é exibida em card de destaque indicando a cidade, UF, coordenadas e a origem da referência: Centroide Municipal oficial (IBGE) ou Coordenadas GPS (coletadas sob consentimento), preservando a distinção de que o centroide representa a sede municipal e não a localização exata de talhões rurais.
  4. Para selecionar ou alterar o município, o usuário aciona o seletor modal responsivo (`SeletorLocalidadeModal`) com suporte a teclado (Escape, Enter, Tab) e leitores de tela (ARIA).
  5. A busca por texto dispara consulta assíncrona ao endpoint anônimo `GET /api/v1/public/clima/municipios?q={texto}&uf={UF}` com *debounce* de 300 ms.
  6. No backend FastAPI (`services/api/public_clima`), o catálogo em memória com todos os 5.571 municípios indexados realiza busca insensível a acentos e caixa, desempate estável de municípios homônimos (com badge visual destacando a UF), suporte a paginação (`limite` padrão 20, máx 100) e validação estrita de parâmetros (rejeição de UFs inexistentes com HTTP 422), sem consumir conexões de banco de dados comercial PostgreSQL.
  7. O usuário pode optar pelo botão "Usar minha localização", que aciona a Geolocation API do navegador estritamente sob clique consciente e sem monitoramento contínuo em segundo plano. Em caso de permissão negada, timeout ou indisponibilidade de sinal, a interface apresenta mensagem honesta e instrui o usuário a prosseguir pela busca manual.
  8. A preferência selecionada é sincronizada reativamente entre componentes e abas do navegador via `useSyncExternalStore` e evento `storage`, mantendo a página `/clima` pronta para consumo da previsão meteorológica sem enviar coordenadas ao SaaS comercial ou a serviços de analytics de terceiros.

### Clima Público — Dashboard Meteorológico e Previsão do Tempo (DeepFarms Agro)
- **Descrição curta:** Visualização integrada de condições meteorológicas atuais, projeção horária das próximas 24 horas para apoio ao planejamento de pulverização e manejo, previsão semanal dos próximos 7 dias, governança de dados sintéticos e cache offline versionado na aba Clima do DeepFarms Agro (`apps/agro`).
- **Fluxo de funcionamento:**
  1. O usuário acessa a página `/clima` no DeepFarms Agro. Se já possuir localidade salva (município IBGE ou GPS consentido), o dashboard meteorológico é iniciado automaticamente; caso contrário, é apresentado o prompt orientador para escolha territorial na base oficial do IBGE.
  2. O cliente consulta o cache local versionado em `localStorage` sob a chave `deepfarms_agro_clima_previsao_v1:{lat_grid}_{lon_grid}` para renderização instantânea (offline-first).
  3. Simultaneamente ou mediante clique em "Atualizar", o frontend dispara requisição same-origin com `AbortController` e controle de race conditions ao endpoint público `GET /api/v1/public/clima/previsao?lat={lat}&lon={lon}`.
  4. O painel de condições atuais exibe temperatura, sensação térmica, umidade relativa, velocidade e direção do vento na rosa dos ventos, rajadas, probabilidade e volume de chuva, acompanhados da data/hora de referência meteorológica e do fuso local.
  5. A projeção de 24 horas apresenta fita horizontal responsiva com suporte a scroll touch no mobile, detalhando o comportamento horário atmosférico. A previsão diária sintetiza os próximos 7 dias com temperaturas mín/máx, probabilidades de chuva e intensidade do vento.
  6. A interface gerencia 9 estados operacionais explícitos (Nenhuma Localidade, Carregando/Skeleton, Sucesso, Dados Desatualizados, Offline com Cache, Offline sem Cache, Provedor Não Licenciado com HTTP 503, Erro Temporário de Servidor HTTP 500/502 e Limite Excedido HTTP 429), impedindo que falhas sejam mascaradas como previsão vazia.
  7. É mantida transparência regulatória integral com badges explícitos para dados modelados vs observados, identificação inequívoca de fixtures de teste (`dadosSinteticos=True`), distinção entre centroides municipais e coordenadas de talhão, e card agrometeorológico esclarecendo que os parâmetros atmosféricos constituem estimativas de modelo e não substituem avaliação agronômica in-situ.

### Clima Público — Arquitetura Multi-Provedor e Preparação OpenWeather One Call 3.0 (DeepFarms Agro)
- **Descrição curta:** Arquitetura desacoplada e plugável para integração de fontes meteorológicas externas (Open-Meteo e OpenWeather One Call API 3.0), modelo de custos para escala de 100 a 5.000 DAU, e refinamento de interface com mensagens acolhedoras e sem exposição de códigos HTTP ou jargões de licenciamento ao produtor rural.
- **Fluxo de funcionamento:**
  1. O backend público de clima (`services/api/public_clima`) implementa o protocolo canônico `WeatherProvider`, viabilizando múltiplos adaptadores externos intercambiáveis via factory `_init_weather_provider()` e variável de ambiente `CLIMA_ACTIVE_PROVIDER` (`OPEN_METEO` ou `OPENWEATHER`).
  2. Foi implementado o conector `OpenWeatherOneCallAdapter`, preparado especificamente para o endpoint oficial One Call API 3.0 (`/data/3.0/onecall`), com normalização de velocidade de vento (m/s para km/h), probabilidades de precipitação (0..1 para 0..100%), mapeamento completo de ícones e horizonte de 24h horárias e 7 dias semanais.
  3. Por conformidade estrita de governança e isolamento entre o SaaS comercial e o app gratuito, os adaptadores mantêm barreiras ativas (`ProviderUnlicensedError`) quando a chave de API ou a flag de licenciamento comercial próprio não estiverem ativas, impedindo o uso indevido de contas sem contratação explícita.
  4. Na interface (`apps/agro`), as telas de indisponibilidade e atualização foram aprimoradas para eliminar mensagens jurídicas complexas e códigos numéricos como `(HTTP 503)` e `(HTTP 429)`. Quando o provedor está em processo de configuração técnica, o produtor visualiza *"Serviço Meteorológico em Atualização"* com orientações calmas e botão de rechecagem, enquanto detalhes diagnósticos e rastros upstream permanecem salvaguardados nos logs do sistema (`console.info`).
  5. Relatório técnico comparativo de 6 provedores, análise de modelos de custos e dimensionamento financeiro encontram-se documentados em `docs/implementation/reports/DEEPFARMS-AGRO-FREE-01F-CLIMA-01E-AVALIACAO-PROVEDORES.md`.

### Clima Público — Integração Controlada WeatherAPI (Piloto DeepFarms Agro)
- **Descrição curta:** Integração homologada do provedor WeatherAPI como candidato principal para o piloto meteorológico do DeepFarms Agro, com suporte nativo aos planos Free (3 dias) e Starter (7 dias), janela horária contínua de 24 horas transpondo a meia-noite, controle de consumo e cotas mensais, métricas operacionais sem exposição de segredos e preservação integral dos adaptadores Open-Meteo e OpenWeather.
- **Fluxo de funcionamento:**
  1. O backend público de clima (`services/api/public_clima`) inclui o conector `WeatherAPIAdapter` compatível com o contrato `WeatherProvider`, selecionado via `CLIMA_ACTIVE_PROVIDER=WEATHERAPI` e mantido desabilitado por padrão (`WEATHERAPI_ENABLED=False`) até homologação contratual e inserção de credencial autorizada.
  2. O conector consome o endpoint oficial `v1/forecast.json` com coordenadas da localidade selecionada, normalizando temperaturas, umidade, ventos (km/h) e rajadas sem conversões artificiais, probabilidades de chuva e códigos meteorológicos para a iconografia do sistema.
  3. A projeção de 24 horas horárias constrói uma esteira contínua a partir do horário de referência, selecionando horas subsequentes dos dias retornados para transpor a meia-noite local sem quebras de sequência temporal.
  4. O sistema detecta dinamicamente a amplitude de previsão diária retornada (3 dias para o plano Free e 7 dias para o Starter), adaptando os títulos e badges no frontend sem interpolações ou preenchimentos sintéticos artificiais.
  5. A camada de cache (`ClimaCache`) incorpora telemetria operacional com contadores de chamadas upstream, cache hits, cache misses, erros e bloqueio interno de cota mensal configurável (`WEATHERAPI_MONTHLY_QUOTA_LIMIT`), protegendo o projeto contra cobranças de excedentes.
  6. Todas as respostas de erro documentadas da WeatherAPI (códigos 1002, 1005, 1006, 2006, 2007, 2008, 2009 e 9999) são mapeadas para exceções controladas com mensagens amigáveis na interface e sanitização total de logs e bundles (ausência de vazamento da API Key).
  7. A interface pública exibe a atribuição obrigatória vinculada (*"Powered by WeatherAPI.com"*) e reforça o aviso agrometeorológico de responsabilidade técnica para operações críticas de campo.

### Identidade Global DeepFarms — Integração Definitiva do Agro e Backoffice (AGRO-ADMIN-01B2B)
- **Descrição curta:** Integração unificada das contas gratuitas do DeepFarms Agro à infraestrutura canônica de identidade global baseada em PostgreSQL (`usuarios`, `sessoes_ativas`, `AuthService`), com sessões HttpOnly, proteção anti-CSRF, isolamento por escopos de produto, integração com o cofre BYOK e governança completa no Backoffice Administrativo.
- **Fluxo de funcionamento:**
  1. O produtor rural acessa a aba "Conta" (`/conta`) no PWA DeepFarms Agro (`apps/agro`) ou cria uma nova conta individual gratuita via `POST /api/v1/auth/register-free`.
  2. O backend central registra a identidade diretamente na tabela global `usuarios`, sem exigir dados corporativos (CPF/CNPJ) nem criar tenants artificiais, sob rate limiting estrito (5 req/min) e proteção anti-enumeração de e-mail.
  3. A autenticação (`POST /api/v1/auth/login`) emite cookies de sessão HttpOnly SameSite=Lax (`deepfarms_agro_session` e `deepfarms_session`) e registra a sessão em `sessoes_ativas` (`tenant_id = null`).
  4. Mutações autenticadas por cookie exigem proteção anti-CSRF através de validação de origem (`Sec-Fetch-Site`, `Origin`/`Referer`) e header customizado `X-Agro-CSRF: 1`.
  5. Os guardrails de autorização (`verify_commercial_jwt_guardrail`) bloqueiam contas gratuitas (`INDIVIDUAL_FREE`, escopo `["agro:free"]`) de acessarem módulos comerciais do SaaS, enquanto usuários comerciais do SaaS recebem escopo estendido `["saas", "agro:free"]` permitindo acesso irrestrito ao Agro.
  6. O encerramento de sessão (`POST /api/v1/auth/logout`) revoga atomicamente a sessão em `sessoes_ativas`, invalida caches temporários e limpa os cookies HttpOnly.
  7. O cofre BYOK de cotações (`/api/v1/agro/byok/*`) aceita tokens e cookies da identidade central, vinculando a titularidade criptográfica ao UUID global do produtor sob Envelope Encryption (AES-256-GCM + DEK 256 bits + KEK versionada).
  8. No Backoffice Administrativo (`/backoffice`), o endpoint `GET /api/v1/backoffice/users` permite filtrar e buscar usuários por tipo de conta (`account_type="INDIVIDUAL_FREE"` vs `"COMMERCIAL"`) com exibição clara de produtos contratados; o dashboard (`/dashboard/stats`) consolida métricas separadas de usuários gratuitos e comerciais; e o bloqueio de usuário desativa imediatamente todas as sessões ativas correspondentes.
  9. As ferramentas públicas (Clima, Mercado PTAX, Indicadores BCB, SIDRA e Calculadoras) permanecem 100% públicas, sem qualquer dependência de autenticação ou de banco de dados.

### Identidade Global Agro — Homologação Final e Persistência Canônica BYOK (AGRO-ADMIN-01B2C)
- **Descrição curta:** Homologação rigorosa dos 12 fluxos ponta a ponta da identidade unificada, migração da persistência do Cofre BYOK para a tabela canônica `farms.usuario_byok_credenciais` no PostgreSQL central com Envelope Encryption, desacoplamento completo do SQLite legado e veredicto técnico documentado.
- **Fluxo de funcionamento:**
  1. A homologação do PostgreSQL foi estruturada via suíte E2E automatizada com validação offline de DDL transacional (`alembic --sql`) no dialeto PostgreSQL nativo para a migration `20261022_agro_admin_01b1_session_nullable.py` (tornando `sessoes_ativas.tenant_id` nullable e criando a tabela `farms.usuario_byok_credenciais`), preservando integralmente o banco compartilhado de desenvolvimento contra contaminação.
  2. A persistência de credenciais BYOK de cotações (`POST /api/v1/agro/byok/credentials`) foi transferida de forma definitiva para o modelo `UsuarioByokCredential` do PostgreSQL (`core.models.usuario_byok.py`), vinculando a chave via chave estrangeira com deleção em cascata (`ON DELETE CASCADE`) ao `farms.usuarios.id`.
  3. A proteção criptográfica emprega Envelope Encryption em duas camadas: a chave secreta é cifrada localmente com chave de dados descartável (DEK de 256 bits sob AES-256-GCM), a qual é cifrada com a chave mestre corporativa (KEK derivada via HKDF-SHA256), registrando não-ambiguamente a titularidade do produtor (`BYOK-{usuario_id[:8]}`) nas consultas proxy de mercado (`/api/v1/agro/byok/cotacoes/*`).
  4. O desacoplamento do SQLite legado (`data/agro_identity/agro_identity.db`) foi consolidado: a inicialização no startup FastAPI permanece desativada (`ENABLE_LEGACY_AGRO_DB=False`), o roteador legado foi deprecado, e os 266 registros sintéticos legados foram isolados sem migração artificial, mantendo os arquivos intactos no disco.
  5. A suíte ponta a ponta homologou os 12 fluxos canônicos: cadastro gratuito com resposta anti-enumeração (202 Accepted), confirmação de e-mail, login com emissão de cookies de sessão HttpOnly SameSite=Lax, consulta e edição de perfil (`/me`), gravação e leitura segura no cofre BYOK, cotação por proxy autenticado, logout com limpeza de cookies, revogação de sessão em `sessoes_ativas`, bloqueio administrativo de usuário no Backoffice com término síncrono de sessões, bloqueio efetivo de autenticação subsequente (403 Forbidden), guardrails impedindo acesso de usuário gratuito a recursos comerciais e acesso anônimo ininterrupto às ferramentas públicas de Clima e Mercado.
  6. A matriz de regressão consolidou aprovação em 100% dos testes automatizados (109 testes backend e 155 testes frontend, totalizando 264 testes verdes).

### Backoffice Agro — Gestão de Produtores, Auditoria e Conversão Comercial (AGRO-ADMIN-01D)
- **Descrição curta:** Painel administrativo completo para governança operacional de contas individuais gratuitas do DeepFarms Agro (`/dashboard/backoffice/agro/usuarios`), com busca server-side e filtros por status e BYOK, inspeção de sessões ativas e credenciais de cofre (sem expor segredos), bloqueio/desbloqueio com encerramento de sessões, revogação avulsa e conversão atômica para assinante comercial mantendo rigorosamente o UUID e credenciais originais do produtor.
- **Fluxo de funcionamento:**
  1. O operador do Backoffice acessa o menu lateral "DeepFarms Agro -> Produtores Agro" (`/dashboard/backoffice/agro/usuarios`).
  2. O backend disponibiliza `GET /api/v1/backoffice/agro/usuarios` filtrando estritamente produtores sem tenant comercial (`Usuario.id.not_in(commercial_tenants)`), suportando paginação server-side, busca por texto (nome, e-mail, username, CPF) e filtros de situação (ativo, bloqueado) e posse de credenciais BYOK.
  3. No modal de detalhes (`GET /api/v1/backoffice/agro/usuarios/{id}`), o operador visualiza dados cadastrais, últimas sessões ativas com IP/heartbeat, credenciais do cofre BYOK mascaradas (com Envelope Encryption preservado e zero vazamento de segredos) e histórico recente de ações administrativas.
  4. O operador pode alternar o status do produtor (`POST /api/v1/backoffice/agro/usuarios/{id}/toggle-status`), bloqueando a conta e encerrando imediatamente todas as suas sessões ativas, ou revogar sessões avulsas (`DELETE /api/v1/backoffice/agro/usuarios/{id}/sessions`), registrando tuplas em `AdminAuditLog` com IP e dados auditados.
  5. Pelo botão de promoção comercial (`POST /api/v1/backoffice/agro/usuarios/{id}/converter-comercial`), o operador provisiona atomicamente um novo Tenant comercial, vincula o produtor como proprietário (`is_owner=True`) e gera uma assinatura no plano escolhido (via catálogo `/api/v1/backoffice/agro/planos`), preservando estritamente seu identificador UUID e credenciais de login originais.

### Backoffice Agro — Fundação de Configurações Dinâmicas, RBAC e Auditoria (AGRO-ADMIN-01E2)
- **Descrição curta:** Fundação segura para governança e administração tipada de parâmetros do DeepFarms Agro (`/dashboard/backoffice/agro/configuracoes`), com RBAC administrativo estrito, controle de concorrência com versionamento otimista, auditoria atômica em `AdminAuditLog`, cache em dois níveis (memória L1 + Redis Pub/Sub com fallback seguro) e correção definitiva da exposição de rotas genéricas do SaaS.
- **Fluxo de funcionamento:**
  1. O operador do Backoffice acessa a rota `/dashboard/backoffice/agro/configuracoes` (com link direto na barra lateral sob o grupo DeepFarms Agro).
  2. O backend disponibiliza `GET /api/v1/backoffice/agro/configuracoes`, exigindo a permissão RBAC `backoffice:agro:config:view`. Usuários com perfil suporte possuem acesso de leitura aos parâmetros não sensíveis, enquanto tentativas de acesso por usuários anônimos ou produtores gratuitos (`INDIVIDUAL_FREE`) são rejeitadas com HTTP 401/403.
  3. Parâmetros críticos são tipados estritamente via esquemas Pydantic dedicados (`agro:clima:config`, `agro:mercado:config`, `agro:mensagens:avisos`, `agro:feature_flags`). Payloads com valores inválidos (ex: timeouts fora do intervalo, ordens de contingência repetidas ou formatos incorretos) são sumariamente rejeitados com HTTP 422 sem alterar a base persistente.
  4. Mutações (`PUT /api/v1/backoffice/agro/configuracoes/{chave}`) exigem a permissão `backoffice:agro:config:edit` e controle de concorrência otimista (`expected_revision`). Caso outro operador tenha alterado a configuração simultaneamente, a requisição é rejeitada com HTTP 409 Conflict, orientando o recarregamento dos dados.
  5. Toda alteração bem-sucedida persiste atomicamente na mesma transação o registro em `configuracoes_saas` (com metadados de revisão e autor) e a trilha de auditoria em `AdminAuditLog` com IP, user-agent e sanitização criptográfica obrigatória (dados anteriores e novos mascarados para impedir vazamento de senhas ou chaves de API).
  6. A consistência entre nós e workers é garantida por cache L1 com TTL de 30 segundos e invalidação distribuída via Redis canal `agro:config:events`. Na ausência ou queda do Redis, o serviço opera de forma degradada resiliente no cache local sem perda de configuração persistida no banco.
  7. Os endpoints SaaS legados `GET /config/saas` e `PUT /config/saas/{chave}` foram completamente blindados com RBAC (`backoffice:config:view` e `backoffice:config:edit`), mascaramento recursivo de dados sensíveis e auditoria automática, eliminando a vulnerabilidade SEC-03.

### Backoffice Agro — Provedores Climáticos, Credenciais e Contingência (AGRO-ADMIN-01E3)
- **Descrição curta:** Administração dinâmica de adaptadores meteorológicos (WeatherAPI, OpenWeather e Open-Meteo) pelo Backoffice (`/dashboard/backoffice/agro/provedores`), com cofre seguro de credenciais criptografadas em repouso (AES-256-GCM via chave derivada HKDF), hot-swap de provedores em tempo de execução sem restart de Uvicorn, cadeia de fallback resiliente com contingência em cache stale, proteção e telemetria de cotas com alertas a 80% e 95%, e testes de conectividade em tempo real.
- **Fluxo de funcionamento:**
  1. O operador administrativo acessa `/dashboard/backoffice/agro/provedores` através da barra lateral do Backoffice no grupo DeepFarms Agro.
  2. O backend disponibiliza `GET /api/v1/backoffice/agro/provedores`, exigindo a permissão RBAC `backoffice:agro:config:view`. A resposta consolida a situação operacional de cada adaptador (ONLINE, SEM_CREDENCIAL, NAO_LICENCIADO, COTA_EXCEDIDA), a ordem de fallback, métricas de chamadas mensais e credenciais mascaradas (`••••••••abcd`), garantindo que nenhum segredo seja exposto nas respostas da API ou em logs.
  3. No cadastro ou rotação de credenciais (`POST /api/v1/backoffice/agro/provedores/credentials`), o operador informa a nova chave de API, exigindo a permissão restrita `backoffice:agro:credentials:manage`. O serviço `PlatformWeatherCredentialsService` cifra o segredo em repouso com AES-256-GCM sob chave derivada por HKDF da chave mestra da plataforma, gravando na tabela `configuracoes_saas` (`chave="agro:credentials:clima"`), completamente segregado do cofre individual BYOK (`usuario_byok_credenciais`), e registra auditoria atômica sem vazamento de segredos em `AdminAuditLog`.
  4. O operador pode testar a conectividade em tempo real com qualquer provedor (`POST /api/v1/backoffice/agro/provedores/test-connection`) antes da ativação, medindo a latência real de ida e volta (ms) e recebendo diagnósticos sem expor chaves ou consumir cotas pagas excessivas.
  5. A alteração de provedor ativo e da cadeia de fallback (`PUT /api/v1/backoffice/agro/provedores/config`) exige `backoffice:agro:config:edit` e valida travas de segurança: proíbe a ativação de WeatherAPI e OpenWeather sem credenciais válidas, e proíbe a ativação pública de Open-Meteo sem licença comercial homologada. A aplicação é imediata via `DynamicWeatherOrchestrator` sem restart do servidor FastAPI/Uvicorn, sincronizada entre workers por invalidação via Redis canal `agro:config:events`.
  6. Em caso de falha do provedor primário (timeout, erro 5xx, 401/403 de credencial ou cota mensal atingida), o orquestrador aciona automaticamente o fallback percorrendo ordenadamente a cadeia de provedores configurada. Se todos os provedores upstream falharem, o sistema serve transparentemente a previsão válida mais recente do cache de contingência (`ClimaCache.get_last`), marcando `desatualizado=true` e status `DESATUALIZADO`, preservando integralmente o contrato canônico `ClimaPrevisaoResponse`.
  7. O modo de emergência pode ser ativado manualmente pelo operador (`POST /api/v1/backoffice/agro/provedores/contingency/toggle`, permissão `backoffice:agro:contingency:trigger`), desviando todo o tráfego público para o adaptador de emergência selecionado com justificativa obrigatória registrada em log de auditoria.

### Backoffice Agro — Mercado, PTAX, DERAL e Governança de Fontes Oficiais (AGRO-ADMIN-01E4)
- **Descrição curta:** Governança operacional e monitoramento de fontes públicas de mercado (BCB PTAX, BCB SGS, IBGE SIDRA e DERAL/SEAB-PR) no Backoffice (`/dashboard/backoffice/agro/mercado`), com pipeline transacional de ingestão, validação de integridade SHA-256 e schema contra o catálogo canônico de 21 commodities, versionamento atômico em `ConfiguracaoSaaS`, controle estrito de ativação e rollback seguro de snapshots, auditoria atômica em `AdminAuditLog` e proteção contra manipulação arbitrária de cotações oficiais.
- **Fluxo de funcionamento:**
  1. O operador do Backoffice acessa `/dashboard/backoffice/agro/mercado` (disponível na barra lateral sob o grupo DeepFarms Agro).
  2. A tela exibe o painel de governança operacional de fontes oficiais com cartões de status em tempo real para BCB PTAX, BCB Séries SGS, IBGE SIDRA e DERAL/SEAB-PR, indicando status de conectividade, tempo de resposta (ms), intervalo de cache (TTL), limites de defasagem (staleness) e metadados da última consulta/apuração.
  3. O operador pode ajustar parâmetros operacionais de cache e limites de tolerância a defasagem (`PUT /api/v1/backoffice/agro/mercado/config`), exigindo a permissão RBAC `backoffice:agro:market:update` e controle de concorrência otimista (`expected_revision`). A governança proíbe terminantemente a edição manual de preços, cotações ou índices oficiais para preservar a autenticidade dos dados governamentais.
  4. Para atualização do levantamento de preços agropecuários do DERAL, o operador realiza o upload de nova planilha ou snapshot JSON (`POST /api/v1/backoffice/agro/mercado/deral/upload`). O pipeline valida: formato permitido (.json, .xlsx, .xls), limite de tamanho (100 B a 5 MB), integridade criptográfica SHA-256 sobre os bytes brutos e conformidade estrutural completa com o catálogo canônico de 21 commodities (rejeitando valores negativos, nulos, NaN ou commodities faltantes).
  5. O snapshot validado é persistido transacionalmente no PostgreSQL em `ConfiguracaoSaaS` (`agro:deral:snap:{id}` e índice `agro:deral:snapshots:index`), garantindo disponibilidade multi-worker e sobrevivência a recriações de containers sem depender do filesystem efêmero.
  6. A ativação do snapshot (`POST /api/v1/backoffice/agro/mercado/deral/snapshots/{id}/activate`) é atômica, registra o histórico de rollback, atualiza o ponteiro em `AgroConfigService` com bloqueio contra injeções diretas arbitrárias, invalida o cache L1 em memória da API pública e gera registro detalhado em `AdminAuditLog`.
  7. Em caso de anomalia no levantamento ativado, o operador pode acionar o rollback imediato (`POST /api/v1/backoffice/agro/mercado/deral/snapshots/{id}/rollback`), restaurando o snapshot anterior com histórico completo e invalidação instantânea do cache público.

### Backoffice Agro — Hardening de Snapshots DERAL, Publicação Distribuída e Fontes Oficiais (AGRO-ADMIN-01E4A)
- **Descrição curta:** Hardening rigoroso de autenticidade governamental, proveniência e integridade forense de snapshots DERAL/SEAB-PR, parsing binário BIFF8 (.xls) nativo, publicação atômica em transação única de banco, consistência distribuída multi-worker e consumo dinâmico de parâmetros operacionais pelas APIs públicas (PTAX, SGS, SIDRA e DERAL).
- **Fluxo de funcionamento:**
  1. O operador envia uma planilha oficial do DERAL (`.xls`) ou envelope estruturado (`.json`) em `POST /api/v1/backoffice/agro/mercado/deral/upload`. Extensões não homologadas (`.xlsx`) são expressamente rejeitadas com erro 400.
  2. O backend valida os bytes brutos: se `.xls`, utiliza `xlrd` para decodificar o binário BIFF8 OLE2, valida a aba `Rav`, confere cabeçalhos e extrai as 21 commodities com arredondamento decimal HALF_UP. Os bytes binários originais são preservados integralmente em Base64 para fins de auditoria e custódia.
  3. O sistema segrega quatro estados: Integridade Criptográfica (SHA-256), Origem Declarada, Origem Verificada (conferência estrita contra domínios governamentais homologados `*.pr.gov.br`, `*.agricultura.pr.gov.br`, `*.seab.pr.gov.br`) e Aprovação Administrativa Formal (`estado_aprovacao = 'APROVADO'`).
  4. Um administrador com permissão `agro:market:write` avalia e homologa o snapshot em `POST /api/v1/backoffice/agro/mercado/deral/snapshots/{id}/approve` com justificativa obrigatória registrada em `AdminAuditLog`. Snapshots em `PENDENTE` ou com falha de proveniência não podem ser ativados no serviço público.
  5. A ativação em `POST /api/v1/backoffice/agro/mercado/deral/snapshots/{id}/activate` ocorre em transação única atômica (`update_config(commit=False)` + `session.commit()`), garantindo que índice, configuração e auditoria sejam gravados conjuntamente sem risco de ponteiro fantasma ou commits parciais.
  6. Para auditoria forense, novos endpoints permitem verificar a integridade recalculada dos bytes armazenados (`GET /deral/snapshots/{id}/verify-integrity`) e realizar o download fiel do arquivo original (`GET /deral/snapshots/{id}/download-raw`).
  7. Em ambiente distribuído, workers recuperados realizam reconciliação automática diretamente pelo banco de dados (`sync_active_snapshot_from_db`), mantendo resiliência total mesmo se o Redis estiver indisponível.
  8. Os serviços públicos de mercado (`PtaxService`, `IndicadoresMacroService`, `IbgeSidraService` e `PrecosPublicosService`) aplicam alterações de TTL e acatam flags de desabilitação em tempo de execução sem reinício de processo.

### Backoffice Agro — Bibliotecas Globais, Avisos, Feature Flags e Integração Final (AGRO-ADMIN-01E5)
- **Descrição curta:** Conclusão da fase AGRO-ADMIN-01E permitindo governar pelo Backoffice comercial as bibliotecas globais compartilhadas (Commodities, Culturas Agrícolas, Unidades de Medida e Conversões), mensagens institucionais temporizadas, avisos regulatórios invioláveis e feature flags operacionais com efeito real no DeepFarms Agro (PWA).
- **Fluxo de funcionamento:**
  1. No Backoffice comercial em `/dashboard/backoffice/agro/bibliotecas`, administradores gerenciam commodities, culturas e unidades de medida com estrito isolamento multi-tenant (`tenant_id = NULL`, `sistema = True`). Operadores do Agro são impedidos de visualizar ou modificar cadastros privados de clientes comerciais.
  2. A integridade referencial dos catálogos é estritamente resguardada: tentativas de exclusão física de commodities ou unidades vinculadas a conversões ativas ou registros operacionais são rejeitadas com HTTP 409 Conflict, orientando o administrador a desativar o registro (`ativo = False`).
  3. A criação de novos registros canônicos valida a unicidade de códigos e nomes globais contra duplicidades acidentais e audita todas as mutações com registro estruturado em `AdminAuditLog`.
  4. Em `/dashboard/backoffice/agro/configuracoes`, o painel administrativo governa o ciclo de vida de comunicados institucionais (`POST`, `PUT`, `DELETE` em `/api/v1/backoffice/agro/configuracoes/mensagens`), permitindo definir título, conteúdo, classificação (`REGULATORIO`, `URGENTE`, `MANUTENCAO`, `COMUNICADO`, `NOVIDADE`), prioridade e janelas de vigência temporal com simulação prévia (`preview`).
  5. Os avisos legais obrigatórios (DERAL, PTAX, BCB e IBGE) são preservados de maneira inviolável, impedindo sua remoção ou esvaziamento por ações administrativas.
  6. O aplicativo gratuito DeepFarms Agro consome a configuração pública de bootstrap via `GET /api/v1/public/agro/config`, filtrando automaticamente mensagens ativas e vigentes no instante atual, exibindo banners de utilidade pública no cabeçalho e mantendo suporte offline com cache seguro em `localStorage`.
  7. As feature flags operacionais (`clima_enabled`, `mercado_enabled`, `byok_enabled`, `ibge_enabled`) são aplicadas diretamente nos endpoints públicos: desabilitar clima retorna HTTP 503 na previsão; desabilitar mercado marca PTAX com status administrativo preservando contratos; desabilitar IBGE bloqueia catálogo estatístico; e desabilitar BYOK restringe operações do cofre de credenciais.

### Backoffice Agro — Dashboard Executivo, Observabilidade e Governança Operacional (AGRO-ADMIN-01F)
- **Descrição curta:** Painel unificado de monitoramento executivo, observabilidade e governança operacional do DeepFarms Agro no Backoffice comercial (`/dashboard/backoffice/agro`), consolidando métricas agregadas de produtores gratuitos sem exposição de dados pessoais (LGPD), telemetria de tráfego e cache de APIs públicas (Clima, Mercado, BYOK), saúde dos provedores meteorológicos e fontes oficiais de mercado, motor dinâmico de alertas operacionais e matriz de conformidade das 11 pendências técnicas de homologação com evidências verificáveis.
- **Fluxo de funcionamento:**
  1. O administrador ou operador do Backoffice acessa o console unificado em `/dashboard/backoffice/agro` através da barra lateral de navegação (`DeepFarms Agro` -> `Painel Executivo`). O acesso é estritamente protegido pelo RBAC global (`backoffice:agro:view`, `backoffice:agro:metrics:view`), impedindo o ingresso de produtores rurais gratuitos ou administradores de tenants comerciais sem privilégios de plataforma.
  2. A tela exibe no topo botões de atalho rápido para as 5 subconsoles operacionais implementadas nas fases anteriores (Produtores `01D`, Configurações `01E2`, Clima `01E3`, Mercado & DERAL `01E4`, Bibliotecas Globais `01E5`), seguidos por 5 cards executivos de síntese (Total de Produtores Gratuitos, Novos Hoje/7d/30d, Hit-Rate de Cache Meteorológico, Fontes Oficiais Operacionais e Índice de Homologação Concluída).
  3. O endpoint `GET /api/v1/backoffice/agro/dashboard/resumo` agrega os dados reais de produtores filtrando exclusivamente contas gratuitas (`is_superuser == False` e fora de qualquer `TenantUsuario`), garantindo isolamento total em relação a clientes corporativos comerciais. Também consolida a contagem de credenciais ativas no cofre BYOK e usuários ativos nas últimas 24h/7d a partir do batimento de sessões (`SessaoAtiva`).
  4. Na aba "Usuários & Adoção", o endpoint `GET /api/v1/backoffice/agro/dashboard/usuarios-evolucao` fornece a série temporal diária dos últimos 30 dias com volume de novos ingressos e total acumulado, complementada pela distribuição de status (Ativos vs Bloqueados) e adoção de provedores BYOK por chave configurada.
  5. Nas abas "Clima & Cotas" e "Mercado & Fontes", o painel consolida a saúde dos adaptadores upstream (`PlatformWeatherCredentialsService`, `ClimaCache`), volume de chamadas, taxa de cache hits/misses, timeouts e contingências ativas, além da situação operacional das 4 fontes oficiais de cotações (PTAX/BCB, SGS/BCB, SIDRA/IBGE e DERAL/SEAB-PR), identificando o snapshot semanal ativo e sua defasagem em dias.
  6. Na aba "Incidentes & Alertas", o endpoint `GET /api/v1/backoffice/agro/dashboard/alertas` avalia dinamicamente e sem poluição de banco as condições do ecossistema: indisponibilidade de Redis compartilhado, ativação de contingência meteorológica, acúmulo de timeouts upstream, defasagem de snapshot DERAL superior a 14 dias e desativação de feature flags críticas.
  7. Na aba "Homologação (11 Itens)", o endpoint `GET /api/v1/backoffice/agro/dashboard/homologacao` audita de forma auditável e auditada as 11 pendências técnicas obrigatórias de governança (KMS/Master Key, Licenciamento de Provedores, Contabilização de Cotas, Proveniência DERAL, Parser XLS Oficial, PostgreSQL Real, Redis Real, Sincronização Multi-Worker, Retenção de Bytes Originais, Integridade de Catálogos Globais e Build/Testes Integrados Web/Agro), classificando cada item como APROVADO (com evidência técnica no código e suíte de testes), EM VALIDAÇÃO ou PENDENTE.

### Acompanhamento Fenológico Inteligente da Safra (`/agricola/safras/[id]/fenologia`)
- **Descrição curta:** Reformulação completa da experiência de monitoramento e registro fenológico por talhão na safra, introduzindo painel de KPIs agronômicos, pipeline horizontal de desenvolvimento da cultura (escala BBCH), filtros dinâmicos com busca por texto, ação de registro rápido diretamente nos cards de talhão, alerta visual para talhões desatualizados (> 15 dias), integração real de grupos de talhões e visualização consolidada em `DataTable` com suporte a pesquisa e exportação para PDF e Excel.
- **Fluxo de funcionamento:**
  1. O usuário acessa a safra e clica no atalho **Fenologia** (`/agricola/safras/[id]/fenologia`).
  2. O topo da tela apresenta 4 cards de síntese: Total de Talhões/Área (ha), Talhões Monitorados (% de cobertura), Estágio Predominante da cultura e Talhões que requerem atenção/visita.
  3. A barra de desenvolvimento da cultura exibe visualmente todos os estágios BBCH cadastrados para a cultura em sequência horizontal, indicando a quantidade de talhões em cada fase e permitindo filtrar talhões ao clicar diretamente no estágio.
  4. Na visão em Cards, cada talhão exibe seu estágio atual, data e tempo relativo da última observação, indicador de alerta para talhões sem visita há mais de 15 dias e botão de registro rápido ("+ Registrar") que abre o modal com o talhão já pré-selecionado.
  5. O histórico do talhão foi linearizado em uma linha do tempo vertical à esquerda (eliminando o layout confuso em zigue-zague).
  6. Pela barra de ferramentas, o usuário pode alternar entre a visão de **Cards** e a visão de **Tabela** (`DataTable`), mantendo paridade 1:1 na quantidade de talhões exibidos e filtros sincronizados. Na visão de tabela, o usuário pode visualizar a situação atual de cada talhão (com atalho para registrar e modal de histórico) ou alternar para o histórico completo de observações com exportação para PDF e Excel conforme as diretrizes do sistema.
  7. A aba **Grupos de Talhões** e o registro em lote por grupo agora estão totalmente integrados à API da safra.

### Auto-Provisionamento Resiliente do Perfil Owner no Onboarding
- **Descrição curta:** Eliminação do erro 500 no cadastro de novos assinantes por incompatibilidade de case ("owner" vs "Owner") ou ausência prévia da carga inicial de perfis, implementando busca tolerante e provisionamento automático do perfil global do sistema.
- **Fluxo de funcionamento:**
  1. Durante a criação de uma nova conta no DeepFarms (`register_new_tenant`), o sistema busca o perfil global do proprietário utilizando tanto o ID canônico de implantação quanto busca case-insensitive por `Owner`, `owner` ou `proprietario`.
  2. Caso o banco de dados não possua o perfil cadastrado (ex.: implantação recente ou banco sem execução prévia de scripts manuais), o `OnboardingService` auto-provisiona o perfil global `Owner` com permissões completas de forma transparente e idempotente.
  3. O script `seed_perfis.py` foi atualizado para ser não-destrutivo e tolerante a perfis pré-existentes, atualizando permissões e descrições sem disparar exceções de conflito.

### Mudança de Plano com Cobrança Pro-Rata via Stripe
- **Descrição curta:** Integração completa do fluxo de upgrade de plano e adição de acessos simultâneos com cobrança pro-rata via Stripe Checkout, unificando `/billing/upgrade`, `/billing/mudancas-plano/solicitar`, pagamento de faturas em aberto e efetivação automática via webhook.
- **Fluxo de funcionamento:**
  1. Ao solicitar upgrade pela tela de faturamento (`/dashboard/settings/billing` → `POST /api/v1/billing/upgrade`) ou pelo modal de alteração de plano (`POST /api/v1/billing/mudancas-plano/solicitar`), o `MudancaPlanoService` verifica se a assinatura já possui pagamento confirmado (`_assinatura_ja_paga`).
  2. **Assinatura em `TRIAL` ou sem pagamento prévio (`PENDENTE_PAGAMENTO`/`PENDENTE` sem fatura `PAGA`):** qualquer solicitação anterior pendente e todas as faturas `ABERTA` anteriores são canceladas automaticamente (`CANCELADA`), uma nova fatura `ABERTA` é gerada com o valor integral do novo plano mantendo o vencimento do período de testes, e a alteração é aplicada imediatamente (`status = "aplicado"`) sem cobrar diferença imediata.
  3. **Assinatura já paga (`ATIVA` ou com fatura `PAGA`):** o sistema calcula a diferença proporcional (pro-rata) aos dias restantes do ciclo, gera a fatura complementar da diferença e cria o checkout Stripe (`mode="payment"`) pelo valor exato da diferença. Ao confirmar no webhook (`checkout.session.completed`), o backend quita a fatura complementar, aplica o novo plano/limites e sincroniza a assinatura recorrente no Stripe (`proration_behavior="none"`).

### Painel Café: Qualidade (SCA/ABIC) × Preço × Margem
- **Descrição curta:** Correlação entre classificação de qualidade do lote de café (pontuação SCA e bebida), custo de produção por saca da safra, preço de venda comercializado e margem financeira, destacando o prêmio de qualidade obtido por cafés especiais (`SCA ≥ 80`).
- **Fluxo de funcionamento:**
  1. O endpoint `GET /api/v1/beneficiamento/qualidade-margem?safra_id=<uuid>` (módulo `A5_COLHEITA`, liberado em todos os pacotes All-In por tamanho de propriedade) consolida os lotes da safra, rateia o custo total da safra pelas sacas beneficiadas e cruza com os preços de venda registrados em `ComercializacaoCommodity` vinculados ao lote (`dados_extras["lote_beneficiamento_id"]`).
  2. O serviço calcula margem por saca (`R$/sc` e `%`), agrupa os indicadores por tipo de bebida e computa o prêmio percentual de preço dos lotes especiais (`SCA ≥ 80`) em relação aos lotes convencionais.
  3. Na interface `/agricola/safras/[id]/beneficiamento`, o componente `BeneficiamentoCafe` exibe os 4 cards-resumo (`Custo Médio / Saca`, `Preço Médio Especial`, `Preço Médio Convencional`, `Prêmio Qualidade`), chips agrupados por bebida e a tabela comparativa lote a lote.

### Portal de Carteira do Consultor (Multi-Tenant)
- **Descrição curta:** Visão consolidada para consultores e produtores com múltiplos tenants vinculados, exibindo propriedades, safras ativas, alertas abertos e última visita técnica com troca de contexto em 1 clique.
- **Fluxo de funcionamento:**
  1. O endpoint `GET /api/v1/auth/my-tenants/resumo` (`CarteiraService.obter_resumo_carteira`) consulta exclusivamente os tenants onde o usuário possui vínculo `TenantUsuario` ativo e consolida em lote (`GROUP BY tenant_id`) safras em andamento, notificações não lidas e data da última `VisitaTecnica`.
  2. Na interface `/dashboard/carteira` (`CarteiraClient`), acessível também pelo atalho **"Ver Carteira Completa"** no `TenantSwitcher` da topbar, o usuário filtra suas contas e acessa qualquer propriedade diretamente via `switchTenantContext`.

### Pecuária Econômica (Leite e Corte)
- **Descrição curta:** Indicadores econômicos e zootécnicos reais para pecuária leiteira (`L/vaca/dia`, `R$/L` e margem por litro) e pecuária de corte (`UA/ha`, `@/ha` e custo total por arroba).
- **Fluxo de funcionamento:**
  1. Em `PecuariaAdvancedService.resumo_leite` (`GET /api/v1/pecuaria/leite/dashboard`), o backend cruza `ProducaoLeite`, plantel de vacas leiteiras ativas (`VACA_LEITE`) e custos alocados/lançamentos (`PECUARIA_LEITE`), exibindo `producao_media_por_vaca_dia`, `custo_por_litro`, `preco_medio_litro` e `margem_por_litro` em `/dashboard/pecuaria/leite`.
  2. Em `LoteIndicadoresService` e `PecuariaDashboardResumoService` (`GET /api/v1/pecuaria/dashboard/resumo`), o backend calcula `lotacao_ua_ha`, `arrobas_por_hectare`, `custo_nutricao_total` e `custo_total_por_arroba` com base na área dos piquetes (`AreaRural`) e custos vinculados, exibidos nos cards econômicos de `/dashboard/pecuaria`.

### Planos de Ação Gerenciais (Indicador → Ação)
- **Descrição curta:** Conversão de prioridades e gargalos operacionais/econômicos em planos de ação persistidos, com responsável, meta, prazo e acompanhamento de status (`ABERTO`, `EM_ANDAMENTO`, `ATRASADO`, `CONCLUIDO`).
- **Fluxo de funcionamento:**
  1. Os endpoints `GET/POST/PATCH/DELETE /api/v1/planos-acao` (`PlanoAcaoService`) persistem ações na tabela `planos_acao_gerenciais` com isolamento estrito por `tenant_id`, derivação automática de atraso quando o prazo expira e registro de `concluido_em` + `resultado_obtido`.
  2. Em `/dashboard/agricola/prioridades`, cada card possui o botão **"Gerar Plano de Ação"**; a gestão completa fica centralizada em `/dashboard/planos-acao`.

### Score Consolidado de Maturidade da Fazenda
- **Descrição curta:** Nota executiva determinística de 0 a 100 em 4 pilares (*Operacional*, *Agronômico/Zootécnico*, *Econômico* e *Financeiro*) com histórico mensal e recomendações diretas.
- **Fluxo de funcionamento:**
  1. O endpoint `GET /api/v1/dashboard/maturidade` (`MaturidadeService.calcular_e_registrar`) calcula as notas dos 4 pilares a partir dos registros reais do tenant (funcionando com dados parciais agrícolas, pecuários ou mistos), persiste o snapshot mensal em `maturidade_snapshots` e calcula a tendência em relação ao mês anterior.
  2. No painel executivo `/dashboard`, o card `DashboardMaturidadeCard` exibe a nota geral, barras por pilar e links diretos para os módulos que puxam a nota para baixo.

### DeepFarmIA Multi-Provider com Failover Automático
- **Descrição curta:** Camada de inteligência artificial desacoplada de um único fornecedor, permitindo operar com **Anthropic**, **OpenAI**, **Google Gemini (Free Tier)**, **Groq (Free Tier)** ou **Ollama**, mantendo fallback determinístico quando offline ou sem cota.
- **Fluxo de funcionamento:**
  1. O cliente central (`services/api/ia/anthropic_client.py`) lê `IA_PROVIDER` do ambiente (`services/api/.env.local` em dev ou `services/api/.env.production` em produção).
  2. Com `IA_PROVIDER=auto`, o sistema tenta automaticamente os provedores configurados na ordem **`anthropic` → `openai` → `gemini` → `groq` → `ollama`** com failover em caso de erro ou limite de cota; também é possível fixar um provedor específico (`IA_PROVIDER=groq`, `openai`, `gemini`, `anthropic` ou `ollama`).
  3. Caso nenhum provedor esteja disponível ou a cota mensal do tenant seja atingida, o sistema retorna análises determinísticas (`fonte: "DETERMINISTICO"`) sem interromper o uso da DRE Operacional.

### Hierarquia Territorial Flexível e Áreas Produtivas Unificadas (Agrícola + Pecuária)
- **Descrição curta:** Flexibilização da hierarquia territorial (`GLEBA → TALHAO / PIQUETE`) e unificação dos fluxos transversais (custeio, estoque e App Campo) por áreas produtivas (`TIPOS_AREA_PRODUTIVA`) em vez de exigir exclusivamente `TALHAO`.
- **Fluxo de funcionamento:**
  1. Em `core/cadastros/propriedades/models.py`, `GLEBA` aceita diretamente `TALHAO`, `PIQUETE` e `AREA_AMBIENTAL`; `TALHAO` aceita diretamente `SUBTALHAO`, `ZONA_MANEJO`, `PIQUETE` (ILPF) e `AREA_OPERACIONAL` (opcional).
  2. O endpoint `GET /api/v1/cadastros/areas-rurais` aceita `apenas_produtivas=true` (`TALHAO`, `PIQUETE`, `SUBTALHAO`, `ZONA_MANEJO`, `AREA_OPERACIONAL`), utilizado por Estoque (`EstoqueDialogs`), Tarefas/App Campo (`campo/service.py`, `tarefa-drawer.tsx`) e Relatórios Financeiros (`relatorio_service.py`).
  3. A tela `/dashboard/pecuaria/piquetes` foi consolidada como painel de consulta zootécnica, direcionando a manutenção estrutural para `/cadastros/propriedades`.
  4. Na tela de **Georreferenciamento** (`/cadastros/propriedades/talhoes`), todas as áreas produtivas podem ter sua geometria desenhada, editada, limpa em rascunho (`Limpar Desenho`) ou removida permanentemente (`Desmarcar Região`, via `PATCH /api/v1/cadastros/areas-rurais/{area_id}` com `geometria`, `area_hectares`, `centroide_lat` e `centroide_lng` explicitamente zerados como `null`).
  5. **Cadastro de Áreas, Limite Ciente da Hierarquia (ILPF) e Limpeza de Polígono (`/cadastros/propriedades` e `/cadastros/propriedades/[id]`):**
     - *Área obrigatória e indicador para Piquetes:* `PIQUETE`, `SUBTALHAO` e `ZONA_MANEJO` passaram a exigir o campo `Área (ha) *` no formulário de áreas da propriedade (`/cadastros/propriedades/[id]`), acompanhados do card contador de **Piquetes** na aba de Estrutura de Áreas.
     - *Validação de limite ciente da hierarquia (`AreaRuralService._validar_limite_hectares_area`):* áreas produtivas primárias ligadas diretamente à `GLEBA` (`TALHAO`, `PIQUETE`, etc.) somam seus hectares entre si contra a área total da propriedade e o `limite_hectares` do pacote contratado; subdivisões internas/ILPF (como `PIQUETE`, `SUBTALHAO` ou `ZONA_MANEJO` filhos de um `TALHAO`) validam apenas contra a área do próprio `TALHAO` pai, evitando dupla contagem no limite do plano e em `sumario_areas`.
     - *Problema corrigido (Limpar Área Geométrica):* ao clicar em **Limpar desenho** no mapa da Unidade Produtiva ou em **Limpar Desenho** em `/cadastros/propriedades/talhoes`, o botão **Confirmar** / **Salvar** ficava desabilitado e o payload omitia `geometria: null` na edição.
     - *Comportamento esperado:* quando havia polígono prévio, o botão **Confirmar** / **Salvar** permanece habilitado após limpar o desenho, preservando `geometria: null` no payload (`PUT /unidades-produtivas/{id}/cadastro-completo` e `PATCH /cadastros/areas-rurais/{id}`) para remover o polígono salvo e zerar a área geométrica calculada.

### Simulador Comparativo de Viabilidade de Investimentos Agro (VPL, TIR, Payback e TMA)
- **Descrição curta:** Analisador financeiro de CapEx integrado ao módulo Financeiro (`④ Gestão Financeira` → `/dashboard/financeiro/viabilidade`), com composição da **TMA** (capital próprio + Plano Safra + risco agro), cálculo de **Payback Simples/Descontado**, **VPL**, **TIR**, **TIRM** (para fluxos não convencionais), comparativo lado a lado de projetos e exportação PDF/Excel.
- **Fluxo de funcionamento:**
  1. O usuário acessa **Viabilidade (VPL/TIR)** na seção `④ Gestão Financeira` (`/dashboard/financeiro/viabilidade`), onde pode compor e aplicar a **TMA** ponderando participação e custo do capital próprio vs. financiamento rural + prêmio de risco (`POST /api/v1/financeiro/viabilidade/calcular-tma`).
  2. O portfólio permite carregar templates prontos do agro (*Pivô Central*, *Expansão de Silo*, *Pulverizador Autopropelido*, *Abertura de Área*) via `GET /api/v1/financeiro/viabilidade/templates` ou personalizar investimento inicial, prazo máximo aceitável, valor residual e fluxos anuais.
  3. Ao clicar em **Simular Comparativo** (`POST /api/v1/financeiro/viabilidade/simular`), `ViabilidadeFinanceiraService` calcula VPL, TIR, TIRM, Índice de Lucratividade, Payback Simples e Payback Descontado, sinalizando fluxos não convencionais (múltiplas inversões de sinal) e recomendando o projeto com maior VPL positivo.
  4. A interface exibe o resumo executivo, gráfico comparativo de VPL, curva de recuperação do capital e tabelas `DataTable` com busca e exportação para PDF e Excel.

### Detector de Custo da Decisão Reativa e Vales de Capital de Giro (`/dashboard/financeiro/fluxo-caixa`)
- **Descrição curta:** Evolução do Fluxo de Caixa mensal para antecipar meses com saldo acumulado projetado negativo ("Vales de Caixa") e quantificar o custo financeiro de recorrer a crédito emergencial caro em vez de planejar o capital de giro via Plano Safra.
- **Fluxo de funcionamento:**
  1. O endpoint `GET /api/v1/relatorios/fluxo-caixa` (`RelatorioService.fluxo_caixa` + `ViabilidadeFinanceiraService.analisar_decisao_reativa_fluxo`) aceita `saldo_inicial`, `taxa_credito_planejado_aa` (padrão `8,5%`) e `taxa_credito_reativo_aa` (padrão `24,0%`), calculando mês a mês `saldo_projetado`, `saldo_acumulado_projetado` e a flag `em_vale_caixa`.
  2. Quando há déficit projetado (`saldo_acumulado_projetado < 0`), o retorno inclui `analise_decisao_reativa` com o valor do pior vale, meses em déficit, antecedência até o primeiro vale, nível de risco (`SAUDAVEL`, `ALERTA` ou `CRITICO`) e economia obtida ao antecipar o crédito planejado (`custo_decisao_reativa`).
  3. Em `/dashboard/financeiro/fluxo-caixa`, o usuário visualiza um horizonte padrão de 6 meses (alternável para Mês Atual ou 12 Meses), ajusta saldo inicial e taxas de crédito em tempo real, acompanha a curva de caixa em gráfico e exporta o detalhamento mensal via `DataTable` em PDF ou Excel.

### Governança Financeira CapEx nos Planos de Ação e Maturidade ESG (`/dashboard/planos-acao` e `/dashboard`)
- **Descrição curta:** Integração do motor de viabilidade (`VPL`, `TIR`, `Payback Descontado`) aos Planos de Ação Gerenciais e ao pilar Financeiro ("G" de Governança ESG) do Score Consolidado de Maturidade.
- **Fluxo de funcionamento:**
  1. Ao cadastrar ou editar um plano em `/dashboard/planos-acao`, o usuário pode informar investimento estimado, retorno anual, horizonte, TMA e payback máximo (`PlanoAcaoCreate`/`PlanoAcaoUpdate`); `PlanoAcaoService` retorna automaticamente o resumo `viabilidade` (`vpl`, `tir_aa`, `payback_descontado_anos`, `veredito_final`).
  2. No cálculo do Score de Maturidade (`GET /api/v1/dashboard/maturidade`), `MaturidadeService._avaliar_governanca_capex` avalia a carteira CapEx do tenant, exibe o status `governanca_financeira` (`SEM_CAPEX`, `SOLIDA` ou `ATENCAO`) em `DashboardMaturidadeCard` e ajusta a nota do pilar Financeiro quando há aportes avaliados (`+15` para carteira viável ou `-15` para projetos inviáveis em aberto).

### Preço de Equilíbrio Econômico por TMA (`VPL = 0`) e Sensibilidade Cambial (`/dashboard/financeiro/hedge/exposicao`)
- **Descrição curta:** Calculadora de preço mínimo por saca remunerando o custo de oportunidade (`TMA`) versus equilíbrio contábil, com simulação de sensibilidade cambial e recomendação comercial de trava em Hedge.
- **Fluxo de funcionamento:**
  1. O endpoint `POST /api/v1/financeiro/viabilidade/preco-equilibrio-tma` (`ViabilidadeFinanceiraService.calcular_preco_equilibrio_tma`) capitaliza o custo total da safra pela TMA no ciclo produtivo, calcula `preco_equilibrio_contabil_sc`, `preco_equilibrio_tma_sc`, `vpl_safra_atual` e gera cenários cambiais (`Dólar -10%`, `Base`, `Dólar +10%`) com ação recomendada (`TRAVAR_MARGEM`, `ATENCAO_TMA` ou `DEFESA_CAIXA`).
  2. O componente reutilizável `PrecoEquilibrioTmaCard` integra o cálculo diretamente em **Exposição Física × Financeira (Hedge)** e na tela de **Viabilidade (VPL/TIR)**.

### Correção: Erro de Renderização em Custeio Agrícola (`/agricola/custos`)
- **Problema corrigido:** ao acessar `/agricola/custos` sem safras cadastradas, durante a transição inicial da consulta dependente ou em falha da API `/api/v1/custos/safra/{safra_id}`, o componente lia `relatorio.fonte_apuracao` antes de validar a existência de `relatorio`, lançando `TypeError: Cannot read properties of undefined (reading 'fonte_apuracao')`.
- **Comportamento esperado:** a tela protege a renderização do selo de fonte de apuração, aguarda corretamente o carregamento da safra selecionada, exibe estados vazios ou de erro amigáveis quando não há safras ou há falha na consulta, e ordena as categorias de custo sem mutar o cache em memória.

### Monitoramento Vegetativo NDVI (`/dashboard/agricola/ndvi` e `/agricola/safras/[id]/ndvi`)
- **Descrição curta:** Consolidação real do vigor vegetativo por propriedade e área produtiva (`Talhão`, `Piquete`, `Subtalhão`, `Zona de Manejo`), com mapa georreferenciado MapLibre colorido por faixa de NDVI, gráfico de série temporal, alertas automáticos de queda/estresse/nuvem, registro e exclusão manual (`POST /api/v1/ndvi/registro-manual`, `DELETE /api/v1/ndvi/{id}`) e exportação via `DataTable` para PDF/Excel.
- **Fluxo de funcionamento:**
  1. Ao abrir `/dashboard/agricola/ndvi` (ou via menu **Agrícola → Índices de Vegetação (NDVI)**), `NdviDashboardClient` consulta `GET /api/v1/ndvi/resumo` filtrado pela propriedade ativa e período selecionado (30, 90, 180 dias ou completo) juntamente com os polígonos de áreas produtivas em `GET /api/v1/cadastros/areas-rurais?apenas_produtivas=true`.
  2. `NdviMapView` renderiza os polígonos no MapLibre coloridos pelo último índice registrado de cada área; clicar no polígono, em um alerta ou na tabela consolidada foca o respectivo talhão na seção de análise temporal (`NdviTalhao`).
  3. Produtores e agrônomos registram ou removem leituras NDVI calculadas externamente (QGIS, drone ou provedor) no componente `NdviTalhao`, recalculando automaticamente média da propriedade, tendência e alertas.
- **Bugfix focado:**
  * **Problema corrigido:** a tela `/dashboard/agricola/ndvi` exibia dados mockados fixos e botões sem ação; o componente `NdviTalhao` acionava um endpoint mock de sincronização satelital retornando sucesso fictício; e `/agricola/safras/[id]/ndvi` enviava o `id` do vínculo `safra_talhoes` em vez de `area_id` (`cadastros_areas_rurais.id`) ao consultar ou salvar `ImagemNDVI`.
  * **Comportamento esperado:** `/dashboard/agricola/ndvi` opera integralmente com dados reais do PostgreSQL; `/agricola/safras/[id]/ndvi` mapeia `area_id` corretamente via `mapSafraTalhoesParaNdvi`; e `POST /api/v1/ndvi/sincronizar/{talhao_id}` retorna HTTP 501 orientando o registro manual enquanto a integração automática Sentinel-2 não está configurada.

### Correção e Padronização: Legibilidade de Alertas em `/agricola/fenologia` e Mensagens Globais (Light/Dark)
- **Problema corrigido:** o aviso "Nenhuma safra ativa" em `/agricola/fenologia` (e alertas equivalentes em outras páginas) usava cores fixas claras (`bg-amber-50`) e herdava `text-foreground` nos títulos `<h5>`, deixando título e descrição ilegíveis no modo escuro e inconsistentes entre páginas.
- **Comportamento esperado:** todas as mensagens de alerta utilizam as variantes semânticas padronizadas do componente `Alert` (`default`, `info`, `warning`, `success` e `destructive`) com tokens dedicados para modo claro e escuro e contraste compatível com WCAG AA.

### Padronização de Cards e KPIs (Light/Dark Mode)
- **Descrição curta:** Padronização global do componente `Card` (`default`, `muted`, `info`, `warning`, `success`, `destructive` e `brand`) e dos cartões de indicadores (`KPICard`, `StatCard` e KPIs da frota) com bordas `rounded-sm`, proteção automática de contraste para títulos e cabeçalhos (`h1–h6`) e tokens dedicados aos modos claro e escuro.
- **Fluxo de funcionamento:**
  1. Os cartões de destaque, status e KPIs em todos os módulos (Agrícola, Pecuária, Financeiro, RH, Suprimentos, Frota, IA e Configurações) passam a utilizar variantes semânticas e tons padronizados, eliminando fundos fixos claros sem suporte ao tema escuro e cantos arredondados fora do padrão visual (`rounded-sm`).
  2. Headings (`h1–h6`) e descrições dentro de cartões coloridos ou institucionais (`variant="brand"`, `info`, `warning`, `success`, `destructive`) recebem automaticamente cores de alto contraste (WCAG AA), evitando títulos escuros ilegíveis sobre fundos verdes ou alertas.
  3. A consistência visual e de contraste é protegida continuamente pela suíte de contratos e guardrails em `apps/web/src/components/ui/card.test.tsx`.

### Modelos Fitossanitários Base (Referência Embrapa/UFV) e Trava de Uso Personalizado
- **Descrição curta:** Biblioteca opcional de 78 modelos-base globais (37 das 38 culturas canônicas de `seed_culturas.py`; apenas `Sisal` fica de fora por ter patossistema oportunista de ferimentos e déficit hídrico) referenciados em literatura pública da Embrapa e UFV (`scripts/initial_load/seed_modelos_fitossanitarios.py`), acompanhada de trava no motor climático para que modelos globais atuem exclusivamente como templates para cópia, nunca como cálculo automático em produção.
- **Fluxo de funcionamento:**
  1. Os modelos globais (`tenant_id IS NULL`) carregam agente causal, fonte institucional, URL de referência (`http://`/`https://` validado no backend e frontend) e observação de triagem dentro de `regras_risco.metadados`, exibidos nos modais de Modelos Fitossanitários (`/dashboard/agricola/clima/inteligencia/modelos` e `/backoffice/clima/modelos`) e preservados nas edições.
  2. O produtor visualiza os modelos padrão do sistema ao habilitar *"Listar itens do sistema"*, copia um modelo-base para o seu tenant e ajusta os limiares com o responsável agronômico antes de utilizá-lo no painel fitossanitário.
- **Bugfix Focado:**
  * **Problema corrigido:** o aviso em `/dashboard/agricola/clima/inteligencia/modelos` informava que somente modelos personalizados entram na inteligência agrícola, mas `ClimaService._calcular_risco_doencas()` consultava e avaliava modelos globais automaticamente mesmo quando o tenant não havia copiado nenhum modelo.
  * **Comportamento esperado:** `_calcular_risco_doencas()` avalia estritamente os modelos do tenant atual (`SEM_MODELO_APLICAVEL` quando o tenant ainda não personalizou regras), garantindo que modelos globais sirvam apenas como referência.
- **Bugfix Focado (RLS de Catálogo Global no Backoffice e Seeds):**
  * **Problema corrigido:** sob `FORCE ROW LEVEL SECURITY`, todas as policies de escrita (`INSERT`, `UPDATE`, `DELETE`) de `modelos_fitossanitarios` e `modelos_zoosanitarios` exigiam `tenant_id = current_tenant_id`, bloqueando também a carga inicial de modelos globais (`tenant_id IS NULL`) e a gestão via Backoffice administrativo.
  * **Comportamento esperado:** a migration `20261119_rls_global_catalog_admin_write` cria policies permissivas nominativas restritas ao owner da tabela e roles dedicadas de catálogo (`df_catalog_admin`, `deepfarms_catalog_admin`) exigindo `tenant_id IS NULL` e ausência de `app.current_tenant_id`, enquanto rotas de Backoffice utilizam `get_catalog_admin_session` (`CATALOG_ADMIN_DATABASE_URL`, fail-closed com HTTP 503 em modo restrito) e tenants comuns permanecem impedidos de escrever registros globais.

### Modelos Zoossanitários Base (Referência Embrapa) e Trava de Uso Personalizado
- **Descrição curta:** Biblioteca opcional de 10 modelos-base globais de estresse térmico (ITH clássico) cobrindo todas as espécies pecuárias canônicas (`Bovino de Leite`, `Bovino de Corte`, `Ovino`, `Caprino`, `Equino`, `Suíno`, `Aves de Corte`, `Aves de Postura`, `Bubalino` e `Asinino`) referenciados em publicações técnicas da Embrapa (`scripts/initial_load/seed_modelos_zoosanitarios.py`), acompanhada de trava no motor climático pecuário para que modelos globais atuem exclusivamente como referência para cópia.
- **Fluxo de funcionamento:**
  1. Os modelos globais (`tenant_id IS NULL`) armazenam limiares validados (`0 < nivel_medio < nivel_alto < nivel_critico <= 100`), fonte institucional, URL `https://` validada e observação de triagem dentro de `regras_risco` e `regras_risco.metadados`, exibidos nos modais de `/dashboard/pecuaria/clima/inteligencia/modelos` e preservados durante edições do produtor.
  2. O produtor visualiza os modelos padrão do sistema ao habilitar *"Listar itens do sistema"*, copia explicitamente o modelo desejado para o seu tenant e ajusta os limiares com o responsável técnico antes de utilizá-lo na Inteligência Pecuária.
- **Bugfix Focado:**
  * **Problema corrigido:** `InteligenciaPecuariaService.analisar_estresse_termico()` chamava `get_or_copy_model()`, copiando e avaliando modelos globais automaticamente sem autorização do tenant; `ModeloZoosanitarioService.copy_global_to_tenant()` executava `commit=False` descartando a cópia persistida ao final da requisição; e `get_all_models()` não deduplicava espécies já personalizadas sobre os modelos globais.
  * **Comportamento esperado:** `analisar_estresse_termico()` consulta exclusivamente `get_tenant_model()` e retorna `None` quando o tenant ainda não habilitou modelo para a espécie; `copy_global_to_tenant()` valida regras, faz upsert com `deepcopy`, comita e atualiza o registro retornado; e `get_all_models()` deduplica por `(especie, tipo_risco)` priorizando personalizações do tenant.

### Correção: Renderização de /operacional (Painel da Frota) em Produção
- **Problema corrigido:** a rota `/operacional` (`apps/web/src/app/(dashboard)/operacional/page.tsx`) era um Server Component passando referências de componentes de ícone (`lucide-react`) em `actions` diretamente para o Client Component `QuickActionGrid`, causando erro de serialização RSC em produção (`Functions cannot be passed directly to Client Components`).
- **Comportamento esperado:** `apps/web/src/app/(dashboard)/operacional/page.tsx` delega a renderização ao Client Component `OperacionalDashboardClient` (`apps/web/src/components/operacional/operacional-dashboard-client.tsx`), eliminando o erro de fronteira Server → Client e carregando o Painel Operacional & Frota normalmente.

### Pecuária — Modo Híbrido de Lotes (Por Lote / Individual), Custo Real da Arroba e Valor de Mercado
- **Descrição curta:** Suporte híbrido para gestão de lotes pecuários no modo coletivo (`POR_LOTE`, sem obrigatoriedade de brinco individual) ou individual (`INDIVIDUAL`), acompanhado da consolidação completa de custos (aquisição, sanidade, nutrição e outros), cálculo de arrobas produzidas, break-even (R$/@) e estimativa de valor de mercado com base na cotação de boi gordo (`public_mercado` ou cotação personalizada no lote).
- **Fluxo de funcionamento:**
  1. Na criação ou edição de lotes (`/dashboard/pecuaria/lotes`), o produtor escolhe o modo de gestão, piquete, rendimento de carcaça (padrão 50%), peso inicial médio, valor de aquisição e cotação manual opcional.
  2. Manejos coletivos (`NASCIMENTO`, `COMPRA`, `MORTE`, `VENDA`, `ABATE`, `PESAGEM`) em lotes `POR_LOTE` atualizam automaticamente o saldo de cabeças, valor de aquisição e peso médio, calculando GMD coletivo e arrobas produzidas.
  3. O painel executivo (`/dashboard/pecuaria`) e o drawer de indicadores de lote consolidam cabeças, UA real (`peso_total / 450`), lotação, custos operacionais, break-even e margem bruta estimada.
- **Bugfix Focado:**
  * **Problema corrigido:** o cálculo de custo por arroba nos serviços de lote e dashboard multiplicava por 15 sobre o peso vivo (subestimando pela metade em carcaça 50%), o dashboard executivo considerava apenas custos sanitários e o painel web exibia totais de cabeças/UA divergentes entre `LoteAnimal` e `pec_animais`.
  * **Comportamento esperado:** ambos os serviços utilizam `arroba_utils` (`peso_vivo * rendimento_carcaca_pct / 100 / 15`), somam sanidade, nutrição e outros custos sobre rebanho híbrido e alimentam integralmente os cartões do `/dashboard/pecuaria`.

### Pecuária — Importação de Planilhas (.xlsx / .csv / .xls) de Lotes, Animais e Pesagens
- **Descrição curta:** Fluxo em wizard para carga em lote de lotes pecuários, animais individuais e pesagens (individuais ou coletivas) com pré-visualização dry-run, remapeamento de colunas, templates baixáveis (`.xlsx`/`.csv`) e blindagem contra ataques em arquivos de planilha.
- **Fluxo de funcionamento:**
  1. Em `/dashboard/pecuaria/importar` (com atalhos em Lotes, Meus Animais e Painel Pecuária), o produtor escolhe o tipo de carga (`LOTES`, `ANIMAIS` ou `PESAGENS`), baixa o modelo `.xlsx` ou `.csv` preenchido e envia sua planilha (até 5 MB e 5.000 linhas).
  2. A etapa de pré-visualização (`/api/v1/pecuaria/importacoes/preview`) analisa os dados em memória sem gravar no banco, sugere mapeamento automático de sinônimos pt-BR, classifica cada linha (`CRIAR`, `ATUALIZAR`, `IGNORAR`, `ERRO`) e permite remapeamento manual ou exportação de erros em CSV sanitizado.
  3. Na confirmação (`/api/v1/pecuaria/importacoes/executar`), os registros são persistidos em transação única por fazenda, criando lotes individuais automaticamente (quando habilitado), materializando contagem/peso médio de lotes e atualizando histórico de pesagens para GMD, com proteção contra XXE/DTD, Zip Slip, Zip Bomb e CSV Formula Injection.

### Bloco 3: Manejo Coletivo Híbrido no App Campo (Offline-First)
- **Descrição curta:** Execução offline no aplicativo de campo (`apps/campo`) de manejos coletivos e híbridos (`PESAGEM`, `VACINACAO`, `MORTE_REGISTRO`, `NASCIMENTO_LOTE`, `MOVIMENTACAO_LOTE` e `MEDICACAO_ANIMAL`) com sincronização em idempotência com o backend (`api`) e telas web padronizadas (`apps/web`).
- **Fluxo de funcionamento:**
  1. O sync pull (`GET /api/v1/campo/sync/pull`) entrega os lotes com `modo_gestao` (`POR_LOTE` ou `INDIVIDUAL`), `peso_medio_kg` e `area_id` para cache offline no IndexedDB/Dexie.
  2. No PWA de campo (`/pecuaria`), Pesagem e Vacinação adaptam o fluxo para lotes coletivos (por quantidade de cabeças e peso médio/total) ou individuais, e os fluxos de Movimentação entre Pastos/Áreas, Medicação/Ocorrência Clínica, Nascimento em Lote e Morte/Baixa gravam tarefas locais para operação offline.
  3. Ao sincronizar (`POST /api/v1/campo/sync`), o backend processa cada tarefa de forma idempotente (`ManejoCampoColetivoService`), atualiza saldo de estoque, lotação do lote e custo unitário para indicadores econômicos, com acompanhamento nas interfaces web de `/dashboard/pecuaria/manejo` e `/dashboard/pecuaria/sync-campo`.

### Atualização Controlada do PWA Campo
- **Descrição curta:** Ciclo de vida controlado de Service Worker (`skipWaiting: false` com `SKIP_WAITING` sob demanda e cabeçalhos `no-cache` para `/sw.js`, `/workbox-*` e `/manifest.json`) com detecção automática de nova versão e botão manual em `/sync` sem perder registros offline do IndexedDB.
- **Fluxo de funcionamento:**
  1. Ao retomar o aplicativo (`visibilitychange`), reconectar à internet (`online`) ou verificar manualmente em `/sync`, o cliente consulta o servidor por atualizações do Service Worker.
  2. Quando há nova build aguardando ativação, o banner **"Nova versão disponível — Atualizar"** aparece nas telas de PIN e operação mantendo o banco local Dexie/IndexedDB intacto.
  3. Ao tocar em **"Atualizar"**, o cliente envia `{ type: "SKIP_WAITING" }` ao Service Worker aguardando e recarrega a interface apenas quando a nova versão assume o controle.

### Fontes de Mercado Resilientes, Sync/CSV DERAL e Cotações Regionais
- **Descrição curta:** Painel multi-fonte e multi-região (`Produto × UF/Município/Praça × Fonte de Dados`) que combina os 20 Núcleos Regionais e a Média Semanal do DERAL/SEAB-PR (`MSA`/`%MSA`), a referência regional de todas as 27 UFs e municípios da PAM/IBGE convertida para a unidade comercial do produto (`R$/saca`, `R$/@`, `R$/t`), canais institucionais (`CEPEA/ESALQ`, `CONAB/MAPA`, `B3`) e múltiplas fontes locais por Fazenda/Tenant (Cooperativas e Frigoríficos) com cálculo de faixa `Mín / Média / Máx` e modo de média consensual.
- **Fluxo de funcionamento:**
  1. O catálogo público (`/api/v1/public/mercado/precos`, `/catalogo` e `/cotacoes-regiao`) permite filtrar por **Produto, Região (27 UFs + 20 Núcleos Regionais DERAL-PR + Municípios IBGE) e Fonte de Dados**, exibindo em cada card do `apps/agro` todas as fontes lado a lado com faixa `Mín · Média · Máx` e dispersão percentual entre fontes/praças.
  2. No Backoffice (`/dashboard/backoffice/agro/mercado`), administradores podem baixar o modelo CSV das 21 commodities (`GET /api/v1/backoffice/agro/mercado/deral/template.csv`), importar correções (`.json`, `.csv` ou `.xls`) com proteção contra injeção de fórmulas e cálculo automático de variação contra o snapshot anterior, ou acionar a sincronização oficial HTTPS (`POST /api/v1/backoffice/agro/mercado/deral/sync`).
  3. Em `/cadastros/commodities`, cada produtor cadastra **múltiplas fontes e praças regionais** por commodity na **Fazenda ativa** ou **Grupo/Tenant** (`GET/PUT/DELETE /api/v1/cadastros/commodities/cotacoes-regionais`), compara Cooperativas, Frigoríficos e Núcleos DERAL com faixa `Mín / Média / Máx`, escolhe usar uma fonte específica ou a **Média Consensual das Fontes (`MEDIA_FONTES`)** e alimenta automaticamente a Pecuária (`Override de Lote > Cotação Regional da Fazenda > Cotação Regional do Tenant > DERAL/SEAB-PR`).

## Conceitos-Chave: Propriedade, Talhão e Unidade Produtiva


- **Propriedade / Unidade Produtiva**: cadastro mestre da fazenda (nome, tipo, documentos, endereço, áreas, geometria).
- **Área Rural (Talhão / Piquete / Subtalhão)**: divisão física dentro da gleba — base unificada para solo, caderno de campo, pastagens, estoque, custeio e NDVI.
- **Production Unit da safra**: vínculo `cultivo + área + participação` dentro de uma safra específica.
- **Fluxo**: cadastra-se a propriedade em `/cadastros/propriedades` → organiza-se glebas, talhões e/ou piquetes → safras, pecuária, estoque, campo e custeio operam sobre essas áreas produtivas.

Regras completas de fronteira territorial/fundiária: `docs/architecture/agrosaas-domain-map.md`.

### Integração TARA

O DeepFarms acessa a Plataforma TARA exclusivamente por HTTP em
`/api/v1/integracoes/tara`. A configuração por tenant é persistida no domínio
canônico de integrações; o segredo do API Client é armazenado criptografado e
nunca é retornado ao frontend ou aos logs. O cliente envia `X-Tenant-ID`,
`X-Balanca-Client-ID` e `X-Balanca-Client-Secret` em todas as chamadas.

Rotas principais: `PUT/GET /config`, `POST /clients`, `POST /orders`,
`GET /orders/{id}`, `GET /weighings`, `POST /weighings/sync`, `GET /events`,
`GET/PUT /webhooks`, `POST /webhooks/replay` e `POST /stations/activate`.
A sincronização de pesagens preserva o cursor opaco no banco e só o avança
após processar cada página com sucesso. O diagnóstico de teste de conexão (`POST /config/testar-conexao`) emite mensagens claras e amigáveis em caso de falha de conexão ou credenciais inválidas, com diagnóstico inline e dicas práticas de resolução em `/dashboard/settings/integracoes/tara`.

## Referência Oficial FIELD-CORE

Arquitetura consolidada do Caderno de Campo (governança, cadeia documental, papel do PWA): `docs/architecture/field-core-final-governance.md`.

## Como Executar

Execute cada bloco em um terminal separado, mantendo o backend ativo antes dos workers e das aplicações web.
Para a Balança, a ordem recomendada é: banco/migrations, backend DeepFarms,
serviço independente, configuração do conector, worker, backoffice web, PWA da
estação e Bridge do indicador.

### Mapa de Portas e Serviços (Sem Conflitos)

| Serviço / Aplicação | Diretório | Tecnologia | Porta | Observação |
| :--- | :--- | :--- | :---: | :--- |
| **DeepFarms API** (Backend Monolito) | `services/api` | FastAPI / Python | **8000** | Documentação interativa em `/docs` |
| **Serviço Balança** (Independente) | `balanca-platform/service` | FastAPI / Python | **8010** | Healthcheck em `/healthz` |
| **DeepFarms Web** (Painel Comercial) | `apps/web` | Next.js | **3000** | Acesso ao SaaS multi-tenant comercial |
| **PWA de Campo** | `apps/campo` | Next.js | **3002** | Operação offline-first de campo |
| **PWA Estação Balança** | `balanca-platform/station` | Next.js | **3003** | Interface de pesagem na estação |
| **PWA DeepFarms Agro** | `apps/agro` | Next.js | **3004** | Acesso gratuito: PTAX, Mercado e BYOK |
| **Ponte Eletrônica Balança (Bridge)** | `balanca-platform/bridge` | Python / Serial | **8321** | Conexão com indicador físico de pesagem |
| **Redis** | Local / Docker | Redis | **6379** | Cache distribuído L2 e rate-limiting |
| **PostgreSQL** | Local / Docker | PostgreSQL | **5432** | Banco comercial (`agrosaas`) |
| **SQLite Segregado Agro** | `data/agro_identity` | SQLite (WAL) | *Arquivo* | Banco de identidades individuais e BYOK |


### 1. Aplicar migrations do banco

O que faz: atualiza o schema PostgreSQL para o head atual antes de iniciar a API.

```bash
cd /opt/lampp/htdocs/farm/services/api
./.venv/bin/alembic upgrade head
```

### 2. Iniciar o backend FastAPI

O que faz: sobe a API em `http://localhost:8000` e disponibiliza a documentação em `/docs`.

```bash
cd /opt/lampp/htdocs/farm/services/api
./start_server.sh
```

Para iniciar manualmente sem o script:

```bash
cd /opt/lampp/htdocs/farm/services/api
./.venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Verificar a API

O que faz: confirma que o processo FastAPI está respondendo antes de iniciar os consumidores.

```bash
curl -fsS http://localhost:8000/docs >/dev/null && echo "API OK"
```

### 4. Iniciar o worker de automações

O que faz: executa o scheduler de automações do DeepFarms usando o virtualenv oficial da API.

```bash
cd /opt/lampp/htdocs/farm
./services/api/.venv/bin/python scripts/run_worker.py
```

### 5. Iniciar o Outbox em desenvolvimento

O que faz: processa continuamente os eventos pendentes de um tenant específico. Substitua o UUID pelo tenant desejado.

```bash
cd /opt/lampp/htdocs/farm/services/api
PYTHONPATH=. .venv/bin/python -m events.outbox_worker run --loop --tenant-id SEU_TENANT_ID
```

Não execute este modo simultaneamente com o cron global para o mesmo conjunto de tenants.

### 6. Iniciar o frontend Web

O que faz: sobe o painel administrativo em `http://localhost:3000`.

```bash
cd /opt/lampp/htdocs/farm/apps/web
pnpm run dev
```

Se houver lock antigo do Next.js:

```bash
rm -f /opt/lampp/htdocs/farm/apps/web/.next/dev/lock
```

### 7. Iniciar o PWA de Campo

O que faz: sobe a aplicação offline-first de campo em `http://localhost:3002`.

```bash
cd /opt/lampp/htdocs/farm/apps/campo
pnpm run dev
```

A primeira ativação usa `/activate` → `/pin`; depois, a aplicação abre em `/home`.

### 8. Iniciar o PWA de Balança

O que faz: sobe a aplicação de estação de pesagem em `http://localhost:3003`.

```bash
cd /opt/lampp/htdocs/balanca-platform
pnpm install
cd station
pnpm run dev
```

Para encaminhar a estação ao serviço independente, crie
`/opt/lampp/htdocs/balanca-platform/station/.env.local` a partir de
`/opt/lampp/htdocs/balanca-platform/station/.env.example` e preencha:

    BALANCA_SERVICE_URL=http://127.0.0.1:8010
    BALANCA_SERVICE_CLIENT_ID=client-id-do-agrosaas
    BALANCA_SERVICE_CLIENT_SECRET=segredo-do-agrosaas
    BALANCA_TENANT_ID=UUID_DO_TENANT_DA_ESTACAO

As credenciais não devem usar o prefixo NEXT_PUBLIC e não devem ser enviadas
ao navegador. O proxy Next.js adiciona os headers no servidor.

### 9. Iniciar o PWA DeepFarms Agro

O que faz: sobe o aplicativo gratuito do produtor rural (calculadoras, PTAX, indicadores de mercado BCB/IBGE e cofre BYOK) em `http://localhost:3004`.

```bash
cd /opt/lampp/htdocs/farm/apps/agro
pnpm run dev
```

Ou a partir da raiz do monorepo:

```bash
pnpm --filter agro dev
```

### 10. Iniciar o serviço independente da Balança

O que faz: disponibiliza a API consumida pela estação e pelo DeepFarms. A
instalação pode ser feita separadamente do backend principal.

Comandos:

    cd /opt/lampp/htdocs/balanca-platform/service
    python3 -m venv .venv
    ./.venv/bin/pip install -r requirements.txt
    cp .env.example .env
    set -a; source .env; set +a
    psql --set=ON_ERROR_STOP=1 "$BALANCA_DATABASE_URL" -f migrations/000_platform_foundation.sql
    psql --set=ON_ERROR_STOP=1 "$BALANCA_DATABASE_URL" -f migrations/001_service_tables.sql
    psql --set=ON_ERROR_STOP=1 "$BALANCA_DATABASE_URL" -f migrations/002_security_identity.sql
    psql --set=ON_ERROR_STOP=1 "$BALANCA_DATABASE_URL" -f migrations/003_contingency.sql
    ./start_server.sh

### 10.1. Configurar o DeepFarms para usar a Balança independente

No arquivo de ambiente do backend, informe a URL e as credenciais de cliente
emitidas pelo backoffice da Balança.
Esses valores ficam somente no servidor:

    BALANCA_SERVICE_URL=http://127.0.0.1:8010
    BALANCA_SERVICE_CLIENT_ID=client-id-do-agrosaas
    BALANCA_SERVICE_CLIENT_SECRET=segredo-emitido-pelo-backoffice

Reinicie o backend depois de alterar o ambiente. Sem essas três variáveis, as
operações de pesagem do DeepFarms são recusadas e nenhum banco local de Balança
é utilizado como fallback.

Para receber as confirmações por webhook, configure também o segredo HMAC da
Conta no DeepFarms e aponte o destino da Conta na TARA para:

    BALANCA_WEBHOOK_ACCOUNT_SECRETS_JSON={"account_uuid":"segredo-compartilhado-com-a-tara"}
    POST /api/v1/integracoes/balanca/events

O endpoint valida a assinatura sobre método, caminho, timestamp e corpo bruto,
deduplica por `event_id` e só confirma com `204` após publicar o evento nos
subscribers internos. Falhas de processamento retornam erro para que a TARA
faça retry; reentregas já registradas continuam sendo aceitas como sucesso.

O primeiro usuário do backoffice é criado com
`/opt/lampp/htdocs/balanca-platform/service/bootstrap_admin.py`.
Depois do login em `/v1/auth/login`, o administrador emite uma credencial para
cada consumidor em `/v1/admin/api-clients`; o DeepFarms recebe somente seu
`client_id` e segredo, que devem ser rotacionados ou revogados pelo backoffice
quando necessário.

### 10.2. Contingência por pendrive

O serviço Balança aceita pacotes físicos assinados em
`POST /v1/contingency/import`. A estação pode exportar o arquivo para um
pendrive; o backoffice importa o arquivo pela interface que consuma essa API
ou pelo utilitário `/opt/lampp/htdocs/balanca-platform/service/import_contingency.py`. O recurso pertence
ao serviço Balança e pode ser utilizado por qualquer cliente integrado, não
somente pelo DeepFarms. O lote original, a assinatura, a sequência e o resultado
de cada pesagem são preservados para auditoria e reprocessamento.

### 10.3. Iniciar o worker da Balança

O worker entrega os eventos Observer pendentes por HTTP ou arquivo JSONL.
Configure no .env do serviço BALANCA_OUTBOX_TENANT_ID e um dos destinos:

    BALANCA_OUTBOX_TARGET_URL=https://cliente.exemplo/api/eventos
    BALANCA_OUTBOX_TARGET_API_KEY=chave-do-consumidor

ou:

    BALANCA_OUTBOX_FILE_PATH=/var/lib/balanca/outbox/eventos.jsonl

Em desenvolvimento:

    cd /opt/lampp/htdocs/balanca-platform/service
    ./.venv/bin/python run_worker.py

Em produção, instale balanca-outbox.service.example como serviço systemd.

### 11. Iniciar a ponte eletrônica da balança

O que faz: conecta o indicador físico ou simulador à aplicação da balança pela porta `8321`.

```bash
cd /opt/lampp/htdocs/balanca-platform/bridge
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp config.yaml.example config.yaml
# Edite config.yaml com a porta serial ou host/porta TCP do indicador.
./.venv/bin/python -m balanca_bridge.main
```

Para usar o simulador em vez do indicador físico:

```bash
cd /opt/lampp/htdocs/balanca-platform/bridge
./.venv/bin/python simulator.py
```

Para instalar a Bridge como serviço no computador da balança:

    cd /opt/lampp/htdocs/balanca-platform/bridge
    sudo ./install.sh

Em uma rede sem internet, prepare previamente o wheelhouse em uma máquina
conectada:

    cd /opt/lampp/htdocs/balanca-platform/bridge
    ./prepare-offline-bundle.sh /tmp/balanca-bridge-wheelhouse

Transfira o diretório para a estação e instale usando:

    BALANCA_BRIDGE_WHEELHOUSE=/caminho/wheelhouse sudo -E ./install.sh

O instalador preserva o config.yaml existente. Para atualizar, execute o
mesmo instalador; a configuração local e a fila do PWA não são apagadas.

### 12. Executar o Outbox global no cron

O que faz: percorre os tenants ativos, ativa o contexto RLS de cada tenant e processa lotes de 50 eventos. Retorna `0` sem falhas e `1` quando algum tenant falha.

Validar sem processar eventos:

```bash
cd /opt/lampp/htdocs/farm/services/api
PYTHONPATH=. .venv/bin/python -m events.outbox_worker --help
PYTHONPATH=. .venv/bin/python -m py_compile scripts/run_outbox_global.py
```

Executar manualmente:

```bash
cd /opt/lampp/htdocs/farm/services/api
PYTHONPATH=. .venv/bin/python scripts/run_outbox_global.py
echo "exit_code=$?"
```

Configurar o log e o cron:

```bash
sudo install -d -o borgus -g borgus /var/log/farm
crontab -e
```

Adicione a linha abaixo. A execução a cada 5 minutos evita sobreposição em ambientes com muitos tenants; `flock` impede duas execuções simultâneas:

```cron
*/5 * * * * /usr/bin/flock -n /tmp/farm-outbox.lock /bin/bash -lc 'cd /opt/lampp/htdocs/farm/services/api && PYTHONPATH=. .venv/bin/python scripts/run_outbox_global.py >> /var/log/farm/outbox.log 2>&1'
```

Confirmar instalação e acompanhar logs:

```bash
crontab -l
tail -f /var/log/farm/outbox.log
```

### 12.1. Gerar o pacote offline da estação

Com a máquina de empacotamento conectada:

    cd /opt/lampp/htdocs/balanca-platform/station
    npm run package:offline

Transfira o diretório gerado em `/opt/lampp/htdocs/balanca-platform/station/dist` para a estação. A primeira
ativação e a sincronização inicial precisam ocorrer com rede disponível. Não
apague o IndexedDB durante uma atualização, pois ele contém as pesagens
pendentes.

### 12.2. Verificar a instalação completa

Execute as verificações abaixo:

    curl -fsS http://127.0.0.1:8000/docs >/dev/null && echo "DeepFarms API OK"
    curl -fsS http://127.0.0.1:8010/healthz && echo "Balanca service OK"
    curl -fsS http://127.0.0.1:8010/readyz && echo "Balanca database OK"
    curl -I http://127.0.0.1:3000
    curl -I http://127.0.0.1:3002
    curl -I http://127.0.0.1:3003
    curl -I http://127.0.0.1:3004
    systemctl status balanca-bridge.service --no-pager

Na estação, confirme: ativação do terminal, login do operador, leitura estável
da Bridge, criação do ticket offline, fila pendente e reprocessamento após
restaurar a rede.

### 13. Parar os processos de desenvolvimento

O que faz: encerra a API e os servidores Next.js iniciados por este workspace.

```bash
# mata processo na porta
lsof -i :8000
kill 12345

# força kill
lsof -i :8000
kill -9 12345

# mata processos pelo nome
pkill -f "uvicorn|next dev"
```
