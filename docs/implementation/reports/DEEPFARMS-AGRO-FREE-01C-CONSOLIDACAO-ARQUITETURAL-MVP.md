# DEEPFARMS-AGRO-FREE-01C — Consolidação Arquitetural, Segurança e Planejamento do MVP

**Data:** 16/10/2026  
**Escopo:** Harmonização arquitetural, fechamento de divergências técnicas, especificação de segurança (Identidade e RLS), modelagem de dados definitiva, infraestrutura, estratégia de produto e roadmap executável para o aplicativo gratuito **DeepFarms Agro** (`apps/agro`).  
**Modo:** Somente leitura. Nenhuma alteração em código de produção, migrations, banco de dados ou infraestrutura foi realizada.  
**Classificação metodológica:**
- **F (Fato):** Observação confirmada diretamente no código-fonte, configurações ou arquivos do repositório, com indicação de arquivo e linha.
- **D (Documental):** Informação extraída de relatórios prévios (01A e 01B) ou documentações técnicas.
- **R (Recomendação):** Diretriz de engenharia de software e arquitetura consolidada.
- **H (Hipótese):** Estimativa analítica de capacidade, custos ou esforço de desenvolvimento.

---

## 1. Resumo Executivo

**Veredicto Consolidado:** **GO COM RESSALVAS PARA O PLANO EXECUTIVO.**

A presente auditoria consolida e pacifica as diretrizes das auditorias `DEEPFARMS-AGRO-FREE-01A` (Fundação e Utilitário) e `DEEPFARMS-AGRO-FREE-01B` (Comunidade e Chat), resolvendo inconsistências críticas de segurança, concorrência, infraestrutura e modelagem de dados.

### Principais Resoluções Arquiteturais:
1. **Blindagem de Identidade e Segurança:** A hipótese da auditoria 01B de que omitir `tenant_id` ou defini-lo como `null` no JWT isolaria as rotas comerciais é **FALSA** à luz do código real. Foi constatado em `core/dependencies.py:332` e `:416` que o backend resolve automaticamente para o único tenant ativo do usuário se o token omitir a claim. A consolidação estabelece isolamento criptográfico por **Audience estrita (`aud: "deepfarms-agro"`)** e verificação explícita em todas as dependências comerciais, bloqueando acessos cruzados.
2. **Harmonização de RLS:** Implementação do contexto transacional `app.current_usuario_id` via `SET LOCAL` para tabelas pessoais e comunitárias, executando `SET LOCAL app.current_tenant_id = ''` concomitantemente. Isso garante que requisições do Agro operem em modo *fail-closed* caso tentem acessar dados comerciais.
3. **Resolução de Fórum vs. Chat:** A inconsistência do relatório 01B (que previa grupos interativos no MVP mas atribuía esforço zero a mensageria) foi resolvida pela adoção da **Opção C**: Grupos no MVP funcionam como **canais com publicações e comentários assíncronos via REST**, estruturados sobre um modelo de dados linear unificado que receberá streaming em tempo real na Fase 4 sem necessidade de refatoração de tabelas.
4. **Premissa de Infraestrutura e Redis:** Corrigiu-se a premissa de que Redis seria necessário apenas a partir de 1.000 usuários. A necessidade de Redis Pub/Sub decorre da **topologia de processos (múltiplos workers Uvicorn)**, e não do volume de cadastros. Para o MVP inicial assíncrono (Fases 1 a 3), o PostgreSQL é autossuficiente; o Redis torna-se pré-requisito técnico apenas quando da ativação de WebSockets multi-worker na Fase 4.
5. **Faseamento Executivo em 4 MVPs:**
   - **MVP 1 — DeepFarms Agro Utilitário:** PWA, acesso anônimo, clima horário/7 dias, PTAX/mercado autorizado, calculadoras offline e landing.
   - **MVP 2 — Identidade e Diretório:** Cadastro gratuito pessoal, perfil do produtor, preferências de privacidade, busca territorial/cultural e solicitação de contato consentida.
   - **MVP 3 — Comunidade:** Grupos temáticos e regionais oficiais, injeção de boletins, postagens e debates assíncronos via REST, e moderação.
   - **MVP 4 — Chat e Notificações Avançadas:** Chat privado 1:1 em tempo real, Web Push VAPID real, sincronização offline no IndexedDB e Redis Pub/Sub.

---

## 2. Matriz de Decisões 01A × 01B

| Dimensão | Auditoria 01A (Utilitário) | Auditoria 01B (Comunidade/Chat) | Decisão Consolidada 01C |
|---|---|---|---|
| **Localização do Frontend** | Novo app em `apps/agro` (`agro.deepfarms.com.br`) | Mantém `apps/agro` | **`apps/agro` independente**, com build, Service Worker e manifest próprios. |
| **Backend / Monólito** | Serviços no FastAPI existente sob `/api/v1/agro` | Fachada `/api/v1/community` no FastAPI | **Domínios modulares unificados** no FastAPI: `/api/v1/agro` (utilitários) e `/api/v1/community` (social). |
| **Identidade Global** | Reutilizar `Usuario` sem criar `Tenant` | Reutilizar `Usuario` sem criar `Tenant` | **Reutilizar `Usuario`** exclusivamente; usuários gratuitos possuem `tenant_id = null`. |
| **Isolamento de Token** | Alertou que dependências comerciais resolvem tenant por vínculo (E14) | Supôs que `tenant_id: null` bastava para isolar | **Audience estrita (`aud: "deepfarms-agro"`)** obrigatória; dependências comerciais rejeitam tokens Agro. |
| **Modelo de RLS** | RLS por `usuario_id` com `SET LOCAL` | RLS por `usuario_id` com `SET LOCAL` | **`app.current_usuario_id` transacional** com zeramento explícito de `app.current_tenant_id`. |
| **Interação em Grupos** | Não abordada | Classificada como debate em grupos, esforço 0 d/p no MVP | **Opção C:** Publicações assíncronas via REST no MVP 3, preparadas para tempo real no MVP 4. |
| **Web Push (VAPID)** | Funcionalidade P1 para alertas de geada/chuva | Bloqueador P0 para chat privado em tempo real | **MVP 1-3:** In-app e polling suave; **MVP 4:** Web Push VAPID obrigatório para chat privado. |
| **Papel do Redis** | Opcional no início | Obrigatório a partir de 1.000 usuários | **Desacoplado de volume:** Redis exigido apenas quando houver múltiplos workers com WebSocket na Fase 4. |
| **Dados de Mercado** | Rejeição estrita de placeholders; PTAX permitida | Foco no compartilhamento de cotações autorizadas | **PTAX no MVP 1**; séries físicas (soja/milho/boi/café) somente após licenciamento formal. |

---

## 3. Divergências Identificadas e Respectivas Resoluções

### Divergência 1: Isolamento de Tokens e Resolução Automática de Tenant
- **Divergência:** A auditoria 01B afirmou que omitir `tenant_id` no JWT bastava para proteger o SaaS comercial. A auditoria 01A alertou que `core/dependencies.py` resolve tenant mesmo sem claim.
- **Evidência no Código:** Em `services/api/core/dependencies.py:324-340` (`get_tenant_id`) e `:408-430` (`get_current_tenant`), caso `claims.get("tenant_id")` seja nulo, o código executa:
  ```python
  if len(tenant_ids) == 1:
      resolved_tenant_id = tenant_ids[0]
      await _activate_session_tenant(session, resolved_tenant_id)
      return resolved_tenant_id
  ```
  Se um assinante comercial utilizar o DeepFarms Agro, seu token gratuito seria promovido silenciosamente para o seu tenant comercial caso enviado a rotas SaaS!
- **Resolução Definitiva:**
  1. O endpoint de emissão de token do Agro (`/api/v1/auth/agro/login` e `/register`) emitirá JWT com claim obrigatória **`aud: "deepfarms-agro"`**.
  2. A dependência comercial `get_current_user_claims` em `core/dependencies.py:207` será atualizada para validar `audience="deepfarms-saas"`. Tokens com audience `deepfarms-agro` serão rejeitados na decodificação com HTTP 401.
  3. O fallback de resolução automática por único tenant em `get_tenant_id` será condicionado expressamente à verificação da audience SaaS.

### Divergência 2: Inconsistência entre Grupos Interativos e Mensageria no MVP
- **Divergência:** Na auditoria 01B, a Alternativa A previa grupos temáticos com "comentários e debates", mas a estimativa de esforço atribuía 0 pessoa-dias a chat/mensagens.
- **Análise Técnica:** Um chat em tempo real (mesmo restrito a grupos) requer WebSocket/SSE, listeners, controle de estado de conexão e tratamento de concorrência. Se o esforço era zero, a implementação seria impraticável.
- **Resolução Definitiva:**
  - Separação formal entre **Fórum Assíncrono (MVP 3)** e **Chat em Tempo Real (MVP 4)**.
  - No MVP 3, grupos funcionam como fóruns temáticos assíncronos via HTTP REST (Opção C). O produtor publica tópicos ou relatos e responde a publicações existentes. Não há WebSockets nem Redis envolvidos nessa fase.

### Divergência 3: Premissa de Escala para Adoção do Redis
- **Divergência:** A auditoria 01B atrelou a introdução do Redis à contagem de usuários cadastrados (1.000 usuários).
- **Análise Técnica:** A necessidade de Redis Pub/Sub em aplicações WebSocket independe da quantidade de usuários cadastrados; depende da **topologia de processos**. Dois usuários conectados a dois workers Uvicorn distintos já não conseguem trocar mensagens se o gerenciador de conexões residir na memória do processo (`self._rooms` em `support_ws.py:31`).
- **Resolução Definitiva:**
  - Enquanto a aplicação operar assincronamente via REST (MVPs 1 a 3), o PostgreSQL atende integralmente à persistência e consulta sem necessidade de Redis.
  - O Redis Pub/Sub será implantado obrigatoriamente como parte do épico de **Chat em Tempo Real (MVP 4)**, sincronizado com o dimensionamento de múltiplos workers no Compose de produção.

---

## 4. Arquitetura Consolidada

A arquitetura final do DeepFarms Agro é estruturada em camadas independentes, garantindo integridade de dados e proteção ao ERP comercial:

```text
+--------------------------------------------------------------------------------------------------+
|                                  CAMADA DE CLIENTES (FRONTEND)                                   |
|                                                                                                  |
|   +---------------------------------------+      +-------------------------------------------+   |
|   |   apps/web (deepfarms.com.br)         |      |   apps/agro (agro.deepfarms.com.br)       |   |
|   |   - Landing Comercial & Planos        |      |   - PWA Autônomo (Offline First / Dexie)  |   |
|   |   - Dashboard ERP SaaS (Assinantes)   |      |   - Utilitário: Clima, PTAX, Calculadoras |   |
|   |   - Next 16 / React 19 / shadcn       |      |   - Social: Diretório, Grupos, Chat       |   |
|   +-------------------+-------------------+      +---------------------+---------------------+   |
+-----------------------|------------------------------------------------|-------------------------+
                        | HTTPS (JWT SaaS)                               | HTTPS / WSS (JWT Agro)
                        v                                                v
+--------------------------------------------------------------------------------------------------+
|                                    GATEWAY & PROXY (NGINX)                                       |
|                                                                                                  |
|   - vhost comercial: api.deepfarms.com.br                                                        |
|   - vhost agro:      agro-api.deepfarms.com.br (ou path /api/v1/agro & /community)              |
|   - Rate Limiting diferenciado por rota e por IP                                                 |
+---------------------------------------+----------------------------------------------------------+
                                        |
                                        v
+--------------------------------------------------------------------------------------------------+
|                                   BACKEND FASTAPI (MONÓLITO)                                     |
|                                                                                                  |
|   +--------------------------------------+      +--------------------------------------------+   |
|   |   Domínios Comerciais (SaaS)         |      |   Domínios Livres (Agro / Community)       |   |
|   |   - /api/v1/fazendas                 |      |   - /api/v1/agro/public (Clima/PTAX/Calc)  |   |
|   |   - /api/v1/financeiro               |      |   - /api/v1/community/perfis (Diretório)   |   |
|   |   - /api/v1/pecuaria / agricola      |      |   - /api/v1/community/grupos (Fórum)       |   |
|   |   - Exige: aud="deepfarms-saas"      |      |   - /api/v1/community/chat (Tempo Real M4) |   |
|   |   - Contexto: app.current_tenant_id  |      |   - Exige: aud="deepfarms-agro"            |   |
|   |                                      |      |   - Contexto: app.current_usuario_id       |   |
|   +------------------+-------------------+      +---------------------+----------------------+   |
+----------------------|------------------------------------------------|--------------------------+
                       |                                                |
                       +-----------------------+------------------------+
                                               |
                                               v
+--------------------------------------------------------------------------------------------------+
|                                CAMADA DE PERSISTÊNCIA & EVENTOS                                  |
|                                                                                                  |
|   +----------------------------------------+      +------------------------------------------+   |
|   |   PostgreSQL (Schema 'farms')          |      |   Redis (A partir do MVP 4)              |   |
|   |   - Tabelas Comerciais (RLS por Tenant)|      |   - Pub/Sub para Chat em Tempo Real      |   |
|   |   - Tabelas Comunitárias (RLS por User)|      |   - Cache de Presença de Sockets         |   |
|   |   - Snapshots Públicos (Sem RLS)       |      |   - Rate Limiting distribuído            |   |
|   +----------------------------------------+      +------------------------------------------+   |
|                                                                                                  |
|   +------------------------------------------------------------------------------------------+   |
|   |   Worker de Notificações Push (Web Push VAPID / Asyncio Queue -> Futuro Celery)          |   |
+--------------------------------------------------------------------------------------------------+
```

---

## 5. Modelo de Identidade e Autorização

### 5.1. Estrutura do Token JWT Agro vs. SaaS

Para assegurar isolamento completo, instituímos especificações divergentes de token validadas na assinatura:

| Claim JWT | Token Comercial (DeepFarms SaaS) | Token Gratuito (DeepFarms Agro) |
|---|---|---|
| `iss` (Issuer) | `https://auth.deepfarms.com.br` | `https://auth.deepfarms.com.br` |
| `aud` (Audience) | **`"deepfarms-saas"`** | **`"deepfarms-agro"`** |
| `sub` (Subject) | `uuid` do `Usuario` | `uuid` do `Usuario` |
| `tenant_id` | `uuid` do `Tenant` (Obrigatório) | **`null`** (Explícito) |
| `scopes` | `["saas:operator", "tenant:read", ...]` | `["agro:profile", "agro:community"]` |
| `app_origin` | `"web"` ou `"campo"` | `"agro"` |

### 5.2. Sessão e Recuperação
- A tabela `sessoes_ativas` (`services/api/core/models/sessao.py:8`, E06) possui vínculo legado com `tenant_id`. Para usuários do Agro, a validação de sessão em cache (`dependencies.py:215`) continuará baseada no hash do token (`token_hash`) no Redis ou cache LRU em memória, sem depender da persistência em `sessoes_ativas` até que uma migration torne `tenant_id` formalmente opcional na tabela de sessão.

### 5.3. Matriz de Testes Negativos de Autenticação

Estes testes devem ser implementados antes do lançamento do MVP 2:

| Cenário de Teste Negativo | Entrada | Comportamento Esperado | Código HTTP |
|---|---|---|---|
| **TN-01** | Token Agro enviado para rota comercial (`/api/v1/fazendas`) | Rejeição por falha de Audience (`aud != deepfarms-saas`) | **401 Unauthorized** |
| **TN-02** | Token Agro de usuário que é assinante enviado para rota comercial | Não deve executar fallback de único tenant; rejeição imediata | **401 Unauthorized** |
| **TN-03** | Token Agro com `tenant_id` forjado no payload | Assinatura HMAC rejeita token adulterado | **401 Unauthorized** |
| **TN-04** | Header `X-Tenant-Id` injetado com Token Agro em rota comercial | Token rejeitado antes da leitura do header | **401 Unauthorized** |
| **TN-05** | Token SaaS comercial enviado para rota pública Agro | Aceito apenas para leitura comunitária com identidade `sub`, ignorando o `tenant_id` | **200 OK** |
| **TN-06** | Usuário desativado (`ativo = False` em `Usuario`) com token Agro válido | Bloqueio imediato na validação de usuário | **401 Unauthorized** |
| **TN-07** | Acesso anônimo a endpoint de criação de perfil | Bloqueio por ausência de credencial | **401 Unauthorized** |

---

## 6. Estratégia de RLS e Isolamento

### 6.1. Variáveis de Contexto Transacional
No PostgreSQL, todo acesso via FastAPI opera sob transação assíncrona.
- Para rotas **Comerciais**:
  ```sql
  SET LOCAL app.current_tenant_id = '<tenant_uuid>';
  SET LOCAL app.current_usuario_id = '<usuario_uuid>';
  ```
- Para rotas **Agro / Comunidade**:
  ```sql
  SET LOCAL app.current_tenant_id = '';
  SET LOCAL app.current_usuario_id = '<usuario_uuid>';
  ```
- Para consultas **Públicas / Anônimas**:
  ```sql
  SET LOCAL app.current_tenant_id = '';
  SET LOCAL app.current_usuario_id = '';
  ```

### 6.2. Diretrizes de Construção de Políticas RLS
1. **Regra Fail-Closed:** Toda política deve utilizar `NULLIF(current_setting('app.current_usuario_id', true), '')`. Se o contexto estiver vazio, a expressão avalia como nula e a consulta retorna zero registros.
2. **Prevenção de Recursão:** Políticas de RLS em tabelas como `membros_grupo` ou `participantes_conversa` não devem fazer subconsultas circulares sobre si mesmas. As permissões de leitura mútua devem utilizar tabelas de junção planas ou funções SECURITY DEFINER de escopo restrito.
3. **Imutabilidade de Políticas Comerciais:** Nenhuma política existente nas tabelas do ERP (`registros_clima`, `fazendas`, `talhoes`, `lancamentos_financeiros`) será modificada.

---

## 7. Modelo de Dados Revisado

O modelo de dados da comunidade foi corrigido e estruturado em estrita correspondência com os 4 MVPs. A inconsistência numérica do relatório 01B foi eliminada: são **9 tabelas no total**, divididas entre MVP 2, MVP 3 e MVP 4.

```mermaid
classDiagram
    class PerfilProdutor {
        UUID id PK
        UUID usuario_id UK
        String nome_exibicao
        String estado_uf
        String municipio
        String codigo_ibge
        JSONB culturas
        JSONB interesses
        Boolean ativo
    }
    class PreferenciaPrivacidade {
        UUID id PK
        UUID usuario_id UK
        String visibilidade_perfil
        String exibir_localizacao
        String permitir_contato
    }
    class SolicitacaoContato {
        UUID id PK
        UUID remetente_id
        UUID destinatario_id
        String status
        DateTime created_at
    }
    class ConexaoProdutor {
        UUID id PK
        UUID usuario_menor_id
        UUID usuario_maior_id
        DateTime created_at
    }
    class GrupoComunitario {
        UUID id PK
        String nome
        String slug UK
        String tipo
        String estado_uf
        Boolean is_oficial
    }
    class MembroGrupo {
        UUID id PK
        UUID grupo_id
        UUID usuario_id
        String papel
        String status
    }
    class PublicacaoGrupo {
        UUID id PK
        UUID grupo_id
        UUID autor_id
        BigInt seq_id
        String tipo_conteudo
        Text conteudo
        JSONB payload_extra
    }
    class BloqueioUsuario {
        UUID id PK
        UUID bloqueador_id
        UUID bloqueado_id
    }
    class DenunciaAbuso {
        UUID id PK
        UUID denunciante_id
        String alvo_tipo
        UUID alvo_id
        String motivo
        String status
    }

    PerfilProdutor --> PreferenciaPrivacidade : 1:1
    SolicitacaoContato --> ConexaoProdutor : gera
    GrupoComunitario --> MembroGrupo : contem
    GrupoComunitario --> PublicacaoGrupo : possui
```

### 7.1. Entidades do MVP 2 (Identidade e Diretório)
1. **`perfil_produtores`:** Dados públicos e profissionais do produtor (Nome de exibição, bio, UF, Município, Código IBGE, Culturas principais [JSONB], Interesses [JSONB], verificação).
2. **`preferencias_privacidade_comunidade`:** Chaves de controle pessoal (`visibilidade_perfil` [PUBLICO, APENAS_CONTATOS, OCULTO], `exibir_localizacao` [MUNICIPIO_UF, APENAS_UF, NENHUMA], `permitir_solicitacao_contato` [TODOS, NINGUEM]).
3. **`solicitacoes_contato`:** Pedidos bilaterais de conexão com status (`PENDENTE`, `ACEITA`, `RECUSADA`, `CANCELADA`) e mensagem de introdução.
4. **`conexoes_produtores`:** Vínculo consentido entre dois produtores. Chave única composta e ordenada `(usuario_menor_id, usuario_maior_id)` para impedir duplicação bidirecional.
5. **`bloqueios_usuarios`:** Tabela de bloqueio unilateral mútuo para blindagem contra assédio.
6. **`denuncias_abuso`:** Registro de denúncias para análise da equipe de moderação.

### 7.2. Entidades do MVP 3 (Comunidade e Fórum Assíncrono)
7. **`grupos_comunitarios`:** Grupos oficiais/regionais curados (Nome, slug, descrição, tipo [REGIONAL_ESTADO, REGIONAL_MUNICIPIO, TEMATICO_CULTURA], regras de postagem).
8. **`membros_grupo`:** Associação de membros e moderadores (`grupo_id`, `usuario_id`, papel [ADMIN, MODERADOR, MEMBRO], status [ATIVO, MUTADO, BANIDO]).
9. **`publicacoes_grupo`:** Fluxo de publicações e comentários assíncronos (`id`, `grupo_id`, `autor_id`, `parent_id` [para respostas/comentários], `tipo_conteudo` [TEXTO, CLIMA_SHARE, COTACAO_SHARE], `conteudo`, `seq_id` [monotônico], `client_message_id` [idempotência]).

### 7.3. Entidades Reservadas para Evolução (MVP 4 — Chat Privado)
- **`conversas_comunidade`** e **`participantes_conversa`**: Adicionadas na Fase 4 para gerenciar sessões privadas 1:1.
- **`mensagens_privadas`**: Tabela especializada para chat direto, evitando misturar conversas confidenciais com postagens públicas de fórum.

### 7.4. Avaliação Crítica de Sequenciamento e Idempotência
- **Uso de BIGSERIAL:** Em ambientes PostgreSQL particionados ou clusters com replicação multi-master, `BIGSERIAL` pode apresentar saltos em rollbacks. No monólito atual em instância única gerenciada, o uso de `BIGSERIAL` para `seq_id` por grupo/canal é plenamente aceitável e eficiente para ordenação estrita e reconciliação de mensagens perdidas (`after_seq`).
- **Idempotência:** A restrição única `UNIQUE(grupo_id, client_message_id)` garante proteção absoluta contra reenvios duplicados causados por oscilações de conectividade 3G/4G no campo.

---

## 8. Definição de Fórum versus Chat

Avaliamos as três alternativas conceituais para os grupos do DeepFarms Agro:

| Critério de Comparação | Opção A: Fórum Assíncrono Puro | Opção B: Chat em Tempo Real | Opção C: Fórum Assíncrono Preparado para Real-Time (RECOMENDADA) |
|---|---|---|---|
| **Natureza da Interação** | Tópicos e Respostas (estilo feed/fórum) | Mensagens instantâneas em fluxo contínuo | Postagens/comentários lineares via REST |
| **Protocolo de Rede** | HTTP REST padrão | WebSocket / SSE persistente | HTTP REST no MVP; WebSocket na Fase 4 |
| **Dependência de Infra** | Somente PostgreSQL | PostgreSQL + Redis Pub/Sub | PostgreSQL no MVP; Redis no MVP 4 |
| **Experiência do Usuário** | Excelente para conteúdo técnico | Ruidosa e caótica em grupos grandes | Excelente para debates e boletins |
| **Custo de Moderação** | Baixo (leitura assíncrona) | Crítico (exige monitoramento 24/7) | Baixo e escalável |
| **Retrabalho Futuro** | Alto (incompatível com chat) | Zero | **Zero (modelo de dados unificado)** |

**Decisão Consolidada:** Adota-se a **Opção C**. Os grupos no MVP 3 operam como fóruns técnicos curados pela DeepFarms, com alimentação automática de boletins de cotações e clima. O modelo relacional (`publicacoes_grupo`) é desenhado linearmente com `seq_id` e `client_message_id`, permitindo que na Fase 4 o mesmo canal receba eventos via WebSocket sem alteração estrutural.

---

## 9. Notificações e Eventos

### 9.1. Segregação de Notificações: TENANT vs. USER
Para resolver o acoplamento identificado em E17 e E18 (`services/api/notifications/base.py:41`), o sistema de notificações será refatorado para suportar escopo dual:
```python
class NotificationScope(str, Enum):
    TENANT = "TENANT"
    USER = "USER"

class NotificationEvent(BaseModel):
    scope: NotificationScope = NotificationScope.TENANT
    tenant_id: UUID | None = None          # Obrigatório se scope == TENANT
    recipient_user_id: UUID | None = None  # Obrigatório se scope == USER
    # ... demais campos preservados
```

### 9.2. Matriz de Canais de Notificação por Fase

| Tipo de Notificação | MVP 1 | MVP 2 | MVP 3 | MVP 4 | Canal de Entrega |
|---|---|---|---|---|---|
| **Alerta Meteorológico Crítico** | In-app | In-app | In-app | In-app + Push | Polling/Query -> Web Push (M4) |
| **Solicitação de Contato** | — | In-app | In-app | In-app + Push | In-app no bell -> Web Push (M4) |
| **Boletim de Grupo Oficial** | — | — | In-app | In-app | Feed do grupo |
| **Mensagem de Chat Privado** | — | — | — | **Web Push** | Web Push VAPID obrigatório |

### 9.3. Entrega Real de Web Push
A confirmação de envio retornada por um gateway de push (FCM, Apple APNs ou Mozilla) atesta unicamente a **aceitação do payload pelo servidor do fornecedor**. Não comprova a renderização física no aparelho (dispositivos em modo economia de bateria, sem sinal ou com permissões revogadas no SO não exibem o push imediatamente). O chat deve tratar o Push como mecanismo de despertar assíncrono (*best effort*), e não como garantia de entrega da mensagem.

---

## 10. Infraestrutura e Escalabilidade

### 10.1. Estado Comprovado vs. Premissas Futuras

| Componente | Estado Comprovado no Repositório | Premissa / Recomendação para Escala |
|---|---|---|
| **Processos API** | 1 processo Uvicorn (`docker-compose.prod.yml:6-12`) | Escalar para 2–4 workers Uvicorn por container |
| **Pool PostgreSQL** | `pool_size = 3`, `max_overflow = 2` (E10) | Elevar para `pool_size = 10` para Agro; PgBouncer se CCU > 200 |
| **Servidor Redis** | Configurado em dev; ausente em produção (E11) | Ativar Redis no Compose de produção a partir do MVP 4 |
| **Storage de Mídia** | Backend local `/tmp` default (core/config.py:94) | S3 ou Cloudflare R2 com upload pré-assinado (M2/M3) |
| **Limite de Conexão** | Nginx padrão sem tuning de WebSocket | Configurar `worker_connections 2048` e buffers de streaming |

### 10.2. Blindagem do ERP Comercial
Para assegurar que a gratuidade do aplicativo Agro não degrade a operação dos clientes pagantes do DeepFarms:
1. **Pools Dedicados:** As rotas `/api/v1/community/*` e `/api/v1/agro/*` utilizarão engine de banco com conexões delimitadas, impedindo que requisições públicas esgotem o pool do ERP.
2. **Rate Limiting Restritivo no Gateway:**
   - Consultas de clima/mercado: 30 requisições/minuto por IP.
   - Buscas no diretório: 15 requisições/minuto por usuário autenticado.
   - Publicações em fórum: máximo de 3 postagens a cada 5 minutos por usuário.

---

## 11. Provedores e Licenciamento Agrícola

Confirmam-se as diretrizes vinculantes estabelecidas na auditoria 01A:

1. **Gate Comercial de Dados:** É estritamente proibido exibir cotações agrícolas sem licença formal ou provenientes de scraping e mocks.
2. **Composição do MVP 1:**
   - **Clima:** Contratação comercial inicial com Open-Meteo (plano comercial) ou ampliação do contrato OpenWeather com variáveis horárias e horizonte de 7 dias comprovado.
   - **Câmbio:** Dólar PTAX oficial obtido via API de Dados Abertos do Banco Central do Brasil (BCB), explicitamente rotulado como PTAX de fechamento/boletim oficial (não é cotação spot em tempo real).
   - **Mercado Agrícola Físico (Soja, Milho, Boi, Café):** Lançamento de cotações condicionamento à celebração de contrato de redistribuição com fonte oficial (CEPEA/Esalq ou CONAB).
3. **Modo Fallback para Calculadoras:** Sem cotação homologada, a calculadora de conversão e frete agrícola operará com a funcionalidade de "Preço Informado Manualmente pelo Produtor", entregando valor utilitário imediato sem risco jurídico de redistribuição indevida.

---

## 12. Privacidade e Moderação (LGPD)

### 12.1. Regras de Exibição Territorial no Diretório
- O produtor escolhe livremente exibir sua localização como:
  1. `Município e UF` (ex.: "Rio Verde - GO").
  2. `Apenas UF` (ex.: "Goiás").
  3. `Oculto do Diretório` (não listado em buscas).
- **Proibição Absoluta:** O sistema não capturará nem armazenará coordenadas GPS da sede, polígonos de talhões ou números de inscrição estadual/CAR para fins de comunidade.

### 12.2. Governança e Moderação de Conteúdo
- **Fase Inicial (MVP 2 e 3):** Criação de grupos restrita aos operadores da DeepFarms. Não haverá criação livre de grupos por usuários para evitar a proliferação de canais abandonados ou voltados a fraudes.
- **Painel de Moderação:** Interface administrativa em `apps/web` (Backoffice) para análise de denúncias pendentes, com ações imediatas de advertência, remoção de postagem, mutação temporária ou banimento permanente de usuários infratores.
- **Auditoria de Mensagens Denunciadas:** A denúncia gera uma cópia imutável do conteúdo para análise da moderação, mesmo que o autor tente editar ou excluir a publicação original.

---

## 13. Escopo Final dos MVPs

```text
+--------------------------------------------------------------------------------------------------+
| ESCOPO DOS QUATRO MVPS CONSOLIDADOS                                                              |
+-------------------+------------------------------------------------------------------------------+
| FASE              | FUNCIONALIDADES E ENTREGAS                                                   |
+-------------------+------------------------------------------------------------------------------+
| MVP 1             | - App PWA DeepFarms Agro (apps/agro) instalável com shell e tema Dark/Light. |
| Utilitário        | - Acesso anônimo sem login ou cadastro.                                      |
| Agrícola          | - Previsão climática horária e 7 dias com snapshots cacheados.               |
|                   | - Dólar PTAX oficial BCB e Calculadoras agrícolas com memória de cálculo.    |
|                   | - Landing institucional no apps/web com QR Code e CTAs comerciais.           |
+-------------------+------------------------------------------------------------------------------+
| MVP 2             | - Cadastro gratuito com JWT Agro (aud: deepfarms-agro, sem tenant).          |
| Identidade &      | - Perfil do produtor (UF, município, culturas, interesses e bio).            |
| Diretório         | - Configurações de privacidade (visibilidade e localização aproximada).       |
|                   | - Diretório de busca com filtros por localização e culturas.                 |
|                   | - Solicitação de contato consentida ("Troca de Cartão Digital").             |
|                   | - Ferramentas de segurança: Bloqueio unilateral e denúncia de perfis.        |
+-------------------+------------------------------------------------------------------------------+
| MVP 3             | - Grupos oficiais e regionais temáticos criados pela DeepFarms.              |
| Comunidade        | - Injeção automatizada de boletins climáticos e cotações nos grupos.         |
| (Fórum Assíncrono)| - Publicações e debates técnicos assíncronos via HTTP REST (Opção C).        |
|                   | - Notificações in-app (bell counter) para respostas e menções.               |
|                   | - Painel administrativo de moderação e tratamento de denúncias.              |
+-------------------+------------------------------------------------------------------------------+
| MVP 4             | - Chat privado 1:1 em tempo real entre conexões consentidas.                 |
| Chat & Real-Time  | - Ativação de barramento Redis Pub/Sub para instâncias Uvicorn multi-worker.  |
|                   | - Implementação real de Web Push (VAPID) no backend e Service Worker.        |
|                   | - Sincronização offline com IndexedDB (Dexie) e fila de envio local.         |
+-------------------+------------------------------------------------------------------------------+
```

---

## 14. Estratégia de Aquisição e Retenção

### 14.1. Funil de Conversão Não Invasivo (Product-Led Growth)
1. **Atração (Topo do Funil):** O produtor chega via QR Code na landing ou recomendação de colegas para consultar previsão climática de chuva ou calcular frete por saca. Nenhuma barreira de cadastro é imposta.
2. **Ativação (Meio do Funil):** Ao tentar salvar municípios favoritos, acompanhar grupos de sua região ou solicitar contato com um colega, o app solicita cadastro simplificado (Nome, E-mail, Senha e Município).
3. **Engajamento (Comunidade):** Participação nas discussões técnicas de sua cultura e acesso a alertas locais diários.
4. **Conversão Comercial (Fundo do Funil):**
   - Banners contextuais e discretos nas calculadoras e boletins: *"Gostou da calculadora? Controle seus custos completos de talhão e maquinário com o DeepFarms Gestão — Teste 14 dias grátis"*.
   - Botão no menu de configurações do perfil: *"Vincular fazenda ao DeepFarms Gestão Comercial"*.

### 14.2. Estratégia contra o Efeito "Cidade-Fantasma" (Cold Start)
- Para evitar que o produtor entre em grupos vazios:
  - **Automação de Conteúdo:** O backend injeta resumos diários de mercado e previsão agroclimática nos grupos às 06:00 e 18:00, garantindo que o canal sempre tenha dados úteis mesmo sem postagens de usuários.
  - **Curadoria Inicial:** Agrônomos e consultores parceiros da DeepFarms atuarão como embaixadores técnicos, fomentando as primeiras postagens e respondendo dúvidas de manejo.

---

## 15. Backlog Incremental Priorizado

A tabela abaixo decompõe a execução em épicos independentes, com critérios de rollback e distribuição de esforço:

| ID | Épico / Entrega | Fase | Dep. | Esforço H | Risco | Condição de Rollback |
|---|---|---|---|---|---|---|
| **EP-01** | **Fundação Apps/Agro:** Setup de workspace, shell Next 16, SW PWA e design system Agro | MVP 1 | — | 6–8 d/p | Baixo | Reverter commit do workspace; apps existentes não são tocados. |
| **EP-02** | **Dados Públicos & Calculadoras:** Snapshots de clima/PTAX, rotas públicas e fórmulas auditadas | MVP 1 | EP-01 | 7–9 d/p | Médio | Desligar cache público via feature flag; exibir modo offline. |
| **EP-03** | **Landing & Aquisição:** Atualização da landing `apps/web` com QR Code e página explicativa | MVP 1 | EP-01 | 3–4 d/p | Baixo | Reverter página estática da landing. |
| **EP-04** | **Segurança & JWT Agro:** Endpoint auth Agro, validação `aud: deepfarms-agro`, blindagem SaaS | MVP 2 | EP-01 | 5–7 d/p | **Alto** | Rejeitar tokens Agro em gateway; manter autenticação comercial. |
| **EP-05** | **Perfil & RLS de Usuário:** DDL `perfil_produtores`, `app.current_usuario_id`, CRUD perfil | MVP 2 | EP-04 | 6–8 d/p | **Alto** | Migration downgrade das tabelas de perfil; RLS comercial intacto. |
| **EP-06** | **Diretório & Solicitações:** Busca territorial, filtros, troca de cartões consentida | MVP 2 | EP-05 | 6–8 d/p | Médio | Ocultar aba de diretório no frontend `apps/agro`. |
| **EP-07** | **Grupos Oficiais & Fórum REST:** DDL `grupos_comunitarios`, `publicacoes_grupo` (Opção C) | MVP 3 | EP-06 | 7–10 d/p | Médio | Ocultar rotas de comunidade no frontend. |
| **EP-08** | **Injeção de Boletins & Moderação:** Jobs de injeção de clima/PTAX em grupos e painel de denúncia | MVP 3 | EP-07 | 5–7 d/p | Médio | Desativar workers de injeção via flag `COMMUNITY_BOTS_ENABLED=false`. |
| **EP-09** | **Infraestrutura Redis & Web Push:** Setup Redis Compose prod e implementação adapter VAPID | MVP 4 | EP-04 | 7–10 d/p | **Alto** | Manter notificações restritas a in-app polling; desligar push. |
| **EP-10** | **Chat Privado 1:1 & Real-Time:** DDL mensagens privadas, WebSocket manager e IndexedDB | MVP 4 | EP-09 | 12–16 d/p | **Alto** | Desativar rota WSS de chat; manter grupos assíncronos. |

**Esforço Total Estimado:**
- **Fase 1 (MVP 1 Utilitário):** 16–21 pessoa-dias (~3 a 4 semanas).
- **Fase 2 (MVP 2 Identidade & Diretório):** 17–23 pessoa-dias (~3 a 4 semanas).
- **Fase 3 (MVP 3 Comunidade Fórum):** 12–17 pessoa-dias (~2 a 3 semanas).
- **Fase 4 (MVP 4 Chat & Real-Time):** 19–26 pessoa-dias (~4 a 5 semanas).
- **Total Consolidado:** **64–87 pessoa-dias**.

---

## 16. Distribuição de Atribuições entre IAs

Para maximizar a eficiência de desenvolvimento e preservar cotas de execução avançada:

```text
+--------------------------------------------------------------------------------------------------+
| MATRIZ DE DISTRIBUIÇÃO OPERACIONAL ENTRE IAs                                                     |
+-------------------+------------------------------------------------------------------------------+
| AGENTE IA         | ATRIBUIÇÕES E ESCOPO DE TRABALHO                                             |
+-------------------+------------------------------------------------------------------------------+
|                   | - Análise de requisitos funcionais e validação agronômica de fórmulas.       |
| GEMINI            | - Especificação de interfaces, UX de formulários e layout PWA em apps/agro.  |
| (Arquitetura, UX, | - Redação de documentações funcionais, manuais e releases de versão.         |
| Especificação e   | - Formulação de matrizes de testes de aceitação e cenários de homologação.   |
| Governança)       | - Governança dos Termos de Uso, Política de Privacidade e Regras de Grupos.  |
|                   | - Validação editorial de boletins automáticos injetados nos fóruns.          |
+-------------------+------------------------------------------------------------------------------+
|                   | - Escrita de código-fonte backend (FastAPI, Routers, Services e Schemas).     |
| CODEX             | - Construção de migrations Alembic DDL e scripts de banco de dados.          |
| (Engenharia,      | - Implementação de políticas RLS em SQL e testes de isolamento de contexto.  |
| Implementação,    | - Desenvolvimento de código frontend TypeScript/Next.js/React e Service Worker|
| RLS, Migrations e | - Implementação criptográfica de validação JWT e filtros de segurança.       |
| Testes de Código) | - Implementação de testes automatizados unitários e de integração em pytest. |
|                   | - Otimização de performance de queries e configuração de Redis / Web Push.   |
+-------------------+------------------------------------------------------------------------------+
```

---

## 17. Plano de Testes e Homologação

1. **Testes de Isolamento e RLS (PostgreSQL Real):**
   - Validar em container de teste com roles sem superuser (`pguser`).
   - Testar SELECT/INSERT/UPDATE em `perfil_produtores` com usuário A e usuário B.
   - Confirmar que uma query em tabela tenant retorna 0 linhas quando `app.current_usuario_id` está ativo e `app.current_tenant_id` está vazio.
2. **Testes de Contrato e Audience JWT:**
   - Submissão de token Agro em todos os endpoints de `/api/v1/financeiro`, `/api/v1/agricola` e `/api/v1/pecuaria`. Todos devem retornar 401.
   - Submissão de token expirado ou com hash de sessão revogado.
3. **Testes de Concorrência e Idempotência:**
   - 10 requisições simultâneas de postagem com o mesmo `client_message_id`. Apenas uma linha deve ser persistida; as outras 9 devem retornar a mensagem existente com sucesso idempotente.
4. **Testes de PWA em Dispositivos Móveis Físicos:**
   - Instalação no Android (Chrome) e iOS 16.4+ (Safari - Adicionar à Tela de Início).
   - Teste de abertura em modo avião (verificar se o shell e o último snapshot de clima abrem com indicador claro de offline).
   - Teste de recálculo em calculadoras sem conexão com a internet.

---

## 18. Critérios de Aceite Globais

1. **Independência Operacional:** Nenhuma falha no aplicativo Agro (incluindo picos de tráfego na comunidade) pode provocar degradação superior a 5% no tempo de resposta das APIs comerciais pagas do DeepFarms.
2. **Ausência de Tenants Artificiais:** Nenhum usuário gratuito da comunidade possui registro gerado nas tabelas `tenants` ou `tenant_usuarios`.
3. **Transparência de Licenciamento:** Nenhuma cotação de produto agrícola é exibida sem indicação inequívoca da fonte, data/hora da coleta e praça de comercialização.
4. **Conformidade LGPD:** Todo usuário pode editar seus dados ou excluir sua conta comunitária a qualquer momento, resultando na anonimização de suas postagens públicas e exclusão de seu perfil.
5. **Comprovação de Entrega Offline:** O aplicativo PWA deve permitir navegação em dados cacheados e execução de cálculos mesmo sem rede.

---

## 19. Riscos e Bloqueadores

| ID | Classificação do Risco | Nível | Bloqueador para: | Ação Mitigadora Vinculante |
|---|---|---|---|---|
| **B01** | Ausência de contrato de redistribuição de dados agrícolas de mercado | **BLOQUEADOR** | Exibição de cotações físicas de soja, milho, boi e café no MVP 1 | MVP 1 lança apenas com PTAX do BCB e calculadoras de conversão com preço manual. |
| **B02** | Dependência de Web Push (VAPID) não implementado | **BLOQUEADOR** | Lançamento do Chat Privado 1:1 (MVP 4) | Chat 1:1 permanece formalmente na Fase 4; MVPs 1 a 3 utilizam notificações in-app. |
| **B03** | Vulnerabilidade de auto-resolução de tenant por vínculo de usuário | **CRÍTICO** | Lançamento do cadastro de usuários no MVP 2 | Implementar validação estrita de `aud: deepfarms-agro` e desativar auto-resolução antes de abrir cadastros. |
| **B04** | Esgotamento de conexões no PostgreSQL compartilhado | **ALTO** | Abertura de grupos comunitários no MVP 3 | Monitorar pool, dimensionar `pool_size` para 10 conexões e avaliar PgBouncer no ambiente de staging. |

---

## 20. Veredicto Final e Próxima Etapa

**VEREDICTO: GO COM RESSALVAS.**

O plano arquitetural está **tecnicamente consolidado, seguro e pronto para avanço executivo**. As inconsistências conceituais e os riscos de segurança entre as auditorias 01A e 01B foram formalmente sanados.

### Próxima Etapa Imediata:
1. **Aprovação Formal:** Submeter este plano consolidado à diretoria técnica para aprovação dos escopos dos 4 MVPs.
2. **Início da Fase 1 (MVP 1 — DeepFarms Agro Utilitário):**
   - Criação da ADR formal de Fundação do `apps/agro`.
   - Setup do workspace em `apps/agro` (Next.js 16, PWA, Tailwind, shadcn).
   - Extração do cliente OpenWeather e criação das rotas de snapshots públicos climáticos e PTAX.

---
*Relatório consolidado e registrado em `docs/implementation/reports/DEEPFARMS-AGRO-FREE-01C-CONSOLIDACAO-ARQUITETURAL-MVP.md`.*
