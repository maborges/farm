# RC-01A — Auditoria de Identidade: Pessoa × Usuário

## 1. Resumo executivo

Esta auditoria encontrou que o AgroSaaS opera hoje com um **modelo híbrido de identidade**.

Existem dois eixos centrais distintos:

- `Pessoa`, em `services/api/core/cadastros/pessoas/`, como cadastro mestre civil/organizacional do tenant;
- `Usuario`, em `services/api/core/models/auth.py`, como identidade de autenticação e acesso.

O problema é que `Usuario` não ficou restrito a autenticação. Ele também armazena dados pessoais próprios:

- `email`
- `nome_completo`
- `cpf`
- `telefone`
- `apelido`
- `foto_perfil_url`

Ao mesmo tempo:

- `Pessoa` já possui infraestrutura própria para PII, documentos, contatos, endereços, LGPD e papéis;
- não existe FK `usuario -> pessoa`;
- onboarding, convite, login, troca de tenant, equipe e Campo PWA operam em torno de `Usuario`, `TenantUsuario` e `UnidadeProdutivaUsuario`;
- o fluxo de criação de conta e convite **não cria Pessoa**.

Conclusão objetiva:

- `Usuario` **não é apenas credencial** hoje;
- `Usuario` **também não substitui corretamente `Pessoa`**;
- a arquitetura atual caracteriza **duplicação de identidade pessoal** entre autenticação e cadastro mestre;
- para a v1.0, a arquitetura deve evoluir para um **vínculo explícito entre `Usuario` e `Pessoa`**, com compatibilidade legada.

Classificação final:

- **Arquitetura encontrada: Modelo C**
- **Decisão: Opção C**

---

## 2. Escopo auditado

### Backend

- `services/api/core/models/auth.py`
- `services/api/core/routers/auth.py`
- `services/api/core/routers/onboarding.py`
- `services/api/core/routers/configuration.py`
- `services/api/core/routers/team.py`
- `services/api/core/services/auth_service.py`
- `services/api/core/services/onboarding_service.py`
- `services/api/core/dependencies.py`
- `services/api/core/cadastros/pessoas/`
- `services/api/tests/`

### Frontend Web

- login
- cadastro
- convite
- equipe
- seleção de tenant
- onboarding
- configurações de conta/time

Em:

- `apps/web/`

### Campo PWA

Em:

- `apps/campo/`

### Arquivos solicitados e não encontrados

Não foram encontrados:

- `services/api/core/routers/users.py`
- `services/api/core/routers/usuarios.py`

Na codebase atual, a gestão de identidade e acesso está distribuída principalmente em:

- `core/routers/auth.py`
- `core/routers/team.py`
- `core/routers/onboarding.py`

---

## 3. Inventário obrigatório

| Conceito | Model/Tabela | Owner | Dados pessoais? | FK para Pessoa? | Uso | Risco |
| --- | --- | --- | ---: | ---: | --- | --- |
| Usuario | `Usuario` / `usuarios` | Core / Auth | Sim | Não | Login, perfil, sessão, onboarding, convites, equipe, Campo | Alto |
| TenantUsuario | `TenantUsuario` / `tenant_usuarios` | Core / Auth | Não | Não | Vínculo usuário-tenant, owner, status, RBAC de tenant | Médio |
| UnidadeProdutivaUsuario | `UnidadeProdutivaUsuario` / `unidade_produtiva_usuarios` | Core / Auth | Não | Não | Escopo por unidade produtiva/fazenda | Médio |
| PerfilAcesso | `PerfilAcesso` / `perfis_acesso` | Core / Auth | Não | Não | Perfis, permissões e overrides | Baixo |
| ConviteAcesso | `ConviteAcesso` / `convites_acesso` | Core / Auth / Onboarding | Sim, parcial | Não | Convite por e-mail para equipe | Médio |
| TokenRecuperacaoSenha | `TokenRecuperacaoSenha` / `tokens_recuperacao_senha` | Core / Auth | Não | Não | Recuperação de senha | Baixo |
| TentativaLogin | `TentativaLogin` / `login_tentativas` | Core / Auth | Sim, parcial | Não | Rate limit, bloqueio e segurança | Médio |
| Pessoa | `Pessoa` / `cadastros_pessoas` | Core / Cadastros | Sim, indireto | N/A | Identidade civil/organizacional do tenant | Médio |
| PessoaDocumento | `PessoaDocumento` / `cadastros_pessoas_documentos` | Core / Cadastros | Sim | N/A | CPF/CNPJ/RG/IE | Alto |
| PessoaContato | `PessoaContato` / `cadastros_pessoas_contatos` | Core / Cadastros | Sim | N/A | Telefone, e-mail, WhatsApp | Médio |
| PessoaEndereco | `PessoaEndereco` / `cadastros_pessoas_enderecos` | Core / Cadastros | Sim | N/A | Endereço | Médio |
| PessoaPII | `PessoaPII` / `cadastros_pessoas_pii` | Core / Cadastros | Sim | N/A | PII segregado com trilha LGPD | Alto |
| ColaboradorRH | `ColaboradorRH` / `rh_colaboradores` | RH | Sim | Sim, opcional | Colaborador operacional, SST, Campo | Alto |
| SessaoAtiva | `SessaoAtiva` / tabela de sessão ativa | Core / Sessões | Não | Não | Validação de sessão JWT ativa | Médio |
| LocalSession Campo | `LocalSession` / IndexedDB | Campo PWA | Sim, parcial | Não | Sessão local offline (`user_id`, `user_name`) | Alto |

---

## 4. O que é `Usuario` hoje?

### Resposta objetiva

`Usuario` hoje é **tudo misturado**:

- credencial global;
- perfil humano de acesso;
- membro de tenant;
- sujeito de RBAC;
- identidade usada em onboarding;
- identidade usada em convites;
- identidade usada pelo Campo PWA;
- portador de dados pessoais próprios.

### Evidências

Em `services/api/core/models/auth.py`, `Usuario` contém:

- `email`
- `username`
- `cpf`
- `telefone`
- `nome_completo`
- `apelido`
- `foto_perfil_url`
- `senha_hash`
- `is_superuser`
- `ativo`

Isso significa que `Usuario` não é apenas credencial técnica.

Ao mesmo tempo, em `auth.py` e `dependencies.py`, toda a autenticação e autorização parte de:

- `sub` do JWT
- `TenantUsuario`
- `UnidadeProdutivaUsuario`
- `PerfilAcesso`

Portanto `Usuario` também é o sujeito de acesso principal da plataforma.

---

## 5. `Usuario` possui dados que já existem em `Pessoa`?

### Sim

Há sobreposição direta.

### Mapa

| Dado | Em `Usuario` | Em `Pessoa` / agregados |
| --- | --- | --- |
| Nome | `nome_completo`, `apelido` | `Pessoa.nome_exibicao`, `PessoaPII.nome_completo`, `PessoaDocumento.nome_completo` |
| CPF | `Usuario.cpf` | `PessoaPII.cpf`, `PessoaDocumento.numero` tipo `CPF` |
| Telefone | `Usuario.telefone` | `PessoaPII.telefone`, `PessoaPII.celular`, `PessoaContato.valor` |
| E-mail | `Usuario.email` | `PessoaPII.email`, `PessoaContato.valor` tipo `EMAIL` |
| Foto | `Usuario.foto_perfil_url` | Não existe equivalente canônico explícito em `Pessoa` |
| Documento civil | Parcial (`cpf`) | Completo em `PessoaDocumento` |
| Contatos múltiplos | Não | Sim, em `PessoaContato` |

### Leitura arquitetural

`Usuario` armazena uma versão simplificada e operacional dos dados pessoais, enquanto `Pessoa` possui a modelagem mestre e rica.

Isso cria sobreposição estrutural, não apenas redundância acidental.

---

## 6. Existe relação `Usuario -> Pessoa`?

### Resposta objetiva

**Não existe vínculo estrutural explícito na modelagem atual.**

### O que foi verificado

- FK direta: **não encontrada**
- campo `pessoa_id` em `Usuario`: **não encontrado**
- associação por e-mail: **não implementada como regra estrutural**
- associação por CPF: **não implementada como regra estrutural**
- associação indireta em produção: **não encontrada**
- associação apenas em testes: **sim, por convenção em alguns fixtures**

### Evidências

Em `services/api/core/models/auth.py`:

- `Usuario` não possui `pessoa_id`

Em `services/api/core/cadastros/pessoas/`:

- `Pessoa` e agregados não referenciam `usuario_id`

Em `services/api/tests/conftest.py` da auditoria anterior, há fixture que insere `usuarios` e `cadastros_pessoas` com o mesmo UUID por convenção, mas sem vínculo modelado. Isso é evidência de workaround de testes, não de arquitetura oficial.

### Conclusão

Hoje a relação `Usuario ↔ Pessoa` é:

- **inexistente no banco**
- **inexistente nos services**
- **inexistente nos routers**
- **inexistente como regra de negócio**

---

## 7. O onboarding cria `Pessoa`?

### Resposta objetiva

**Não.**

### Fluxo real encontrado

Em `services/api/core/services/onboarding_service.py`, `register_new_tenant` faz:

1. cria `Usuario`
2. cria `Tenant`
3. cria `TenantUsuario`
4. cria assinatura/fatura
5. envia e-mail

Não foi encontrada criação de:

- `Pessoa`
- `PessoaContato`
- `PessoaDocumento`
- `PessoaRelacionamento`

### Payload de onboarding

`AssinanteRegisterRequest` recebe:

- `email`
- `username`
- `nome_completo`
- `apelido`
- `senha`
- `cpf`
- `telefone`
- `nome_produtor`
- `cnpj_tenant`

Esses dados são distribuídos entre:

- `Usuario`
- `Tenant`

Não entre:

- `Pessoa`

### Conclusão

O onboarding inicial da plataforma hoje é um fluxo de:

`Usuario -> Tenant -> TenantUsuario`

e não:

`Pessoa -> Usuario -> Tenant`

---

## 8. Convites criam `Pessoa`?

### Resposta objetiva

**Não.**

### Fluxo real encontrado

Em `services/api/core/services/onboarding_service.py`:

- `enviar_convite` cria `ConviteAcesso`
- `registrar_via_convite` cria `Usuario`
- `aceitar_convite` cria:
  - `TenantUsuario`
  - `UnidadeProdutivaUsuario`

Não cria:

- `Pessoa`
- `PessoaContato`
- `PessoaDocumento`

### Observação importante

O convite é todo baseado em:

- `email_convidado`
- `perfil_id`
- `unidades_produtivas_ids`

Ou seja, o onboarding de equipe é modelado em torno de acesso, não de identidade civil.

### Conclusão

Convite hoje significa:

`ConviteAcesso -> Usuario -> TenantUsuario -> UnidadeProdutivaUsuario`

Sem qualquer camada de `Pessoa`.

---

## 9. RBAC depende de `Pessoa`?

### Resposta objetiva

**Não.**

### O que o RBAC usa de fato

Em `services/api/core/dependencies.py`, `require_tenant_permission()` resolve permissão a partir de:

- `get_current_user() -> Usuario`
- `get_tenant_id()`
- `TenantUsuario`
- `PerfilAcesso`
- `UnidadeProdutivaUsuario`
- `perfil_fazenda_id`

### Não encontrado no RBAC

- `pessoa_id`
- `Pessoa`
- `PessoaRelacionamento`

### Conclusão

O RBAC atual é totalmente baseado em:

`Usuario -> TenantUsuario -> PerfilAcesso -> UnidadeProdutivaUsuario`

`Pessoa` não participa do modelo de autorização.

---

## 10. Campo PWA depende de `Usuario` ou `Pessoa`?

### Resposta objetiva

**Depende de `Usuario` para autenticação/sessão e de `ColaboradorRH` para trabalhador operacional. Não depende de `Pessoa` como identidade principal.**

### Evidências

Em `apps/campo/src/lib/db.ts`, `LocalSession` armazena:

- `user_id`
- `tenant_id`
- `device_id`
- `device_token`
- `user_name`
- `fazenda_ids`

Em `apps/campo/src/app/(auth)/activate/page.tsx`, a ativação persiste:

- `payload.user_id`
- `payload.user_name`
- `payload.device_token`

Em `apps/campo/src/lib/task-factory.ts` e `caderno-offline.ts`:

- `operador_id` e `usuario_id` usam `session.user_id`

Já o pull de sincronização em `apps/campo/src/lib/sync/pull.ts` baixa:

- `colaboradores[]`

e o Campo usa `db.colaboradores` como catálogo operacional.

### Conclusão

No Campo PWA:

- autenticação/sessão = `Usuario`
- trabalhador/colaborador = `ColaboradorRH`
- identidade civil canônica `Pessoa` = **não é o eixo principal**

---

## 11. Models

### Identidade e acesso

Arquivo:

- `services/api/core/models/auth.py`

Models:

- `Usuario`
- `PerfilAcesso`
- `TenantUsuario`
- `UnidadeProdutivaUsuario`
- `ConviteAcesso`
- `TokenRecuperacaoSenha`
- `TentativaLogin`

### Identidade civil/cadastral

Arquivo:

- `services/api/core/cadastros/pessoas/models.py`

Models:

- `Pessoa`
- `PessoaDocumento`
- `PessoaContato`
- `PessoaEndereco`
- `PessoaBancario`
- `PessoaPII`
- `TipoRelacionamento`
- `PessoaRelacionamento`
- `PessoaConsentimento`
- `PessoaAcessoLog`

### Identidade operacional relacionada

Arquivo:

- `services/api/rh/models.py`

Model:

- `ColaboradorRH`

Ele aparece nos fluxos de usuário do Campo como entidade operacional de trabalhador.

---

## 12. Tabelas

### Tabelas de auth/acesso

- `usuarios`
- `tenant_usuarios`
- `unidade_produtiva_usuarios`
- `perfis_acesso`
- `convites_acesso`
- `tokens_recuperacao_senha`
- `login_tentativas`

### Tabelas de pessoa

- `cadastros_pessoas`
- `cadastros_pessoas_documentos`
- `cadastros_pessoas_contatos`
- `cadastros_pessoas_enderecos`
- `cadastros_pessoas_bancario`
- `cadastros_pessoas_pii`
- `cadastros_tipos_relacionamento`
- `cadastros_pessoa_relacionamentos`
- `cadastros_pessoas_consentimentos`
- `cadastros_pessoas_acesso_log`

### Tabela operacional correlata

- `rh_colaboradores`

---

## 13. Rotas

### Auth

Em `services/api/core/routers/auth.py`:

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `GET /auth/my-tenants`
- `PUT /auth/me`
- `POST /auth/me/avatar`
- `POST /auth/switch-tenant`

### Onboarding

Em `services/api/core/routers/onboarding.py`:

- `POST /onboarding/assinante`
- `POST /onboarding/convites`
- `GET /onboarding/status`
- rotas de ativação de conta
- rotas de detalhe/registro/aceite de convites

### Team / gestão de equipe

Em `services/api/core/routers/team.py`:

- `GET /team/users`
- `POST /team/invite`
- `PATCH /team/users/{id}/role`
- `PATCH /team/users/{id}/fazendas`
- `DELETE /team/users/{id}`
- `GET /team/invites`
- `POST /team/invites/{id}/resend`
- `DELETE /team/invites/{id}`
- `GET/POST/PATCH/DELETE /team/roles`

### Pessoas

Em `services/api/core/cadastros/pessoas/router.py`:

- CRUD de `/cadastros/pessoas`
- subrotas de contatos, endereços, PII, bancário, relacionamentos

### Leitura estrutural

As rotas de auth/onboarding/team não passam por `Pessoa`.

---

## 14. Frontend

### Login

Em `apps/web/src/components/auth/login-form.tsx`:

- login usa `/auth/login`
- perfil usa `/auth/me`
- sessão no store recebe:
  - `id`
  - `name`
  - `email`
  - `username`
  - `cpf`
  - `telefone`
  - `foto_perfil_url`

Ou seja, o frontend trata `UsuarioMeResponse` como perfil pessoal do usuário.

### Cadastro

Em `apps/web/src/components/auth/register-form.tsx`:

o formulário de criação de conta coleta diretamente para onboarding:

- `nomeCompleto`
- `apelido`
- `username`
- `email`
- `cpf`
- `telefone`
- `senha`

e envia tudo para `/onboarding/assinante`.

Isso confirma que a identidade do usuário nasce antes de qualquer `Pessoa`.

### Convite

Em `apps/web/src/app/(auth)/convite/aceitar/page.tsx`:

- detalhe do convite consulta `/onboarding/convites/{token}`
- aceite usa `/onboarding/convites/aceitar`
- registro via convite usa `/onboarding/convites/registrar`

Também há um detalhe relevante:

- upload de avatar tenta usar `/users/me/avatar`

mas o router principal encontrado para avatar está em:

- `/auth/me/avatar`

Isso indica assimetria de frontend em torno da identidade do usuário.

### Tenant switcher

Em `apps/web/src/components/layout/tenant-switcher.tsx`:

- troca de contexto é feita por `/auth/switch-tenant`
- o store e os cookies são reconstruídos a partir de `/auth/me`

O contexto de navegação é baseado em `Usuario + TenantUsuario`, não em `Pessoa`.

### Equipe

Em `apps/web/src/app/(dashboard)/dashboard/settings/team/TeamClient.tsx`:

- lista membros por `nome`, `email`, `perfil`, `status`, `fazendas`
- toda a UX de equipe opera sobre usuário e convite

Não há acoplamento com `Pessoa`.

### Perfil da conta

Em `apps/web/src/app/(dashboard)/dashboard/settings/account/page.tsx`:

- atualização de perfil usa `/auth/me`
- avatar usa `/auth/me/avatar`

Novamente, o perfil pessoal da UI é o `Usuario`.

---

## 15. Campo PWA

### Sessão

Em `apps/campo/src/lib/stores/session-store.ts`:

- a sessão local depende de `user_id` e `device_token`
- a validação consulta `/campo/devices/me`

### Ativação

Em `apps/campo/src/app/(auth)/activate/page.tsx`:

- a ativação persiste `payload.user_id` e `payload.user_name`

### Operação

Em `apps/campo/src/lib/caderno-offline.ts` e `task-factory.ts`:

- `usuario_id` e `operador_id` usam a sessão do usuário

### Trabalhador

Em `apps/campo/src/lib/sync/pull.ts`:

- colaboradores são sincronizados separadamente como catálogo operacional

### Conclusão

O Campo PWA separa:

- `Usuario` para autenticação/sessão do dispositivo
- `ColaboradorRH` para trabalhador operacional

Não usa `Pessoa` como eixo principal de identidade local.

---

## 16. Testes

### Padrão dominante encontrado

Nos testes de auth, onboarding, multi-tenant e Campo, o setup dominante cria:

- `Usuario`
- `TenantUsuario`
- às vezes `UnidadeProdutivaUsuario`

Sem criação correspondente de `Pessoa`.

### Exemplos de cobertura observados

- `services/api/tests/integration/core/test_auth_api.py`
- `services/api/tests/integration/test_seguranca.py`
- `services/api/tests/test_create_subscription.py`
- `services/api/tests/test_multi_up_hardening_step01.py`
- `services/api/tests/unit/agricola/test_field_pwa01_offline_sync.py`
- `services/api/tests/unit/agricola/test_epi_offline_sync.py`
- `services/api/tests/integration/campo/test_sync_pecuaria_integration.py`

### Leitura dos testes

Os testes reforçam a arquitetura atual:

- identidade de acesso = `Usuario`
- vínculo organizacional = `TenantUsuario`
- escopo de fazenda = `UnidadeProdutivaUsuario`

Não foi encontrada exigência de:

- `Usuario` ter `Pessoa`
- convite criar `Pessoa`
- onboarding criar `Pessoa`

---

## 17. Fluxos reais

### Login

`Usuario`

↓

`JWT (sub=user.id)`

↓

`SessaoAtiva`

↓

`TenantUsuario`

↓

`PerfilAcesso`

↓

`UnidadeProdutivaUsuario`

↓

`Permissões`

### Convite de equipe

`ConviteAcesso`

↓

`Usuario` novo ou existente

↓

`TenantUsuario`

↓

`UnidadeProdutivaUsuario`

↓

`PerfilAcesso`

### Onboarding

`Usuario`

↓

`Tenant`

↓

`TenantUsuario`

↓

`Assinatura`

↓

`Onboarding status`

### Cadastro de pessoa

`Pessoa`

↓

`PessoaContato / PessoaDocumento / PessoaEndereco / PessoaPII`

↓

`PessoaRelacionamento`

↓

`Uso operacional`

### Perfil do usuário

`Usuario`

↓

`PUT /auth/me`

↓

`nome_completo / telefone / foto`

### Conclusão dos fluxos

Hoje existem **dois pipelines paralelos de identidade**:

1. `Usuario` para acesso
2. `Pessoa` para cadastro mestre

Sem ponte explícita entre ambos.

---

## 18. Arquitetura encontrada

### Classificação final

**Modelo C**

### Justificativa

`Usuario` autentica e autoriza, mas também carrega dados pessoais duplicados.

`Pessoa` já existe como identidade civil/organizacional canônica, mas não participa dos fluxos de login, convite, onboarding ou RBAC.

Isso é exatamente um modelo híbrido.

Não é:

- Modelo A, porque `Usuario` não é credencial pura;
- Modelo B, porque `Pessoa` não está restrita a terceiros externos e já é fonte canônica para pessoas do domínio;
- Modelo D, porque a evidência encontrada é suficiente para enquadrar o modelo atual.

---

## 19. Perguntas obrigatórias consolidadas

### 1. O que é `Usuario` hoje?

**Credencial + perfil humano + membro de tenant + sujeito de RBAC + portador de dados pessoais próprios.**

### 2. `Usuario` possui dados que já existem em `Pessoa`?

**Sim.**

Nome, CPF, telefone e e-mail estão duplicados estruturalmente.

### 3. Existe relação `Usuario -> Pessoa`?

**Não.**

Não foi encontrada FK, campo opcional ou regra formal de associação.

### 4. O onboarding cria `Pessoa`?

**Não.**

Cria `Usuario`, `Tenant` e `TenantUsuario`.

### 5. Convites criam `Pessoa`?

**Não.**

Criam `Usuario`, `TenantUsuario` e `UnidadeProdutivaUsuario`.

### 6. RBAC depende de `Pessoa`?

**Não.**

Depende de `Usuario`, `TenantUsuario`, `PerfilAcesso` e `UnidadeProdutivaUsuario`.

### 7. Campo PWA depende de `Usuario` ou `Pessoa`?

**Depende de `Usuario` para sessão e de `ColaboradorRH` para trabalhador.**

### 8. Existe risco LGPD/PII?

**Sim.**

Há duplicidade de CPF, telefone, e-mail e nome entre `Usuario` e a estrutura de `Pessoa`.

---

## 20. Riscos

### Risco 1: duplicidade de dados pessoais

O mesmo indivíduo pode existir com dados divergentes em:

- `usuarios`
- `cadastros_pessoas`
- `cadastros_pessoas_pii`
- `cadastros_pessoas_documentos`
- `cadastros_pessoas_contatos`

### Risco 2: usuário sem pessoa correspondente

Esse é o comportamento padrão atual.

### Risco 3: pessoa sem usuário correspondente

Também é comportamento normal do sistema.

### Risco 4: divergência de CPF

`Usuario.cpf` pode divergir de:

- `PessoaPII.cpf`
- `PessoaDocumento.numero` tipo `CPF`

### Risco 5: divergência de telefone/e-mail

`Usuario.telefone` e `Usuario.email` podem divergir de:

- `PessoaPII.telefone`
- `PessoaPII.email`
- `PessoaContato`

### Risco 6: conflito LGPD

`Pessoa` já possui modelagem de:

- base legal
- anonimização
- consentimento
- log de acesso a PII

`Usuario` mantém dados pessoais fora dessa malha canônica.

### Risco 7: onboarding e convite fora da base mestre

Novos usuários entram no produto sem `Pessoa`, o que perpetua o desacoplamento.

### Risco 8: Campo PWA reforça separação

O Campo autentica por usuário, mas trabalha com colaboradores separadamente, sem ponte oficial com `Pessoa`.

### Risco 9: assimetria de frontend

A tela de convite usa `/users/me/avatar`, mas o router principal encontrado é `/auth/me/avatar`. Isso sugere inconsistência em torno do ownership da identidade do usuário.

---

## 21. Decisão

### Opção escolhida

**Opção C — Criar futuramente vínculo obrigatório `Usuario ↔ Pessoa` para novos usuários, com compatibilidade legada.**

### Justificativa

`Usuario` não pode continuar como entidade totalmente independente se o objetivo é consolidar `Pessoa` como master data do domínio humano/civil da plataforma.

Ao mesmo tempo, não é seguro inferir que todos os fluxos legados possam ser convertidos imediatamente.

Portanto, a decisão segura e coerente com a codebase é:

- manter compatibilidade para usuários legados;
- introduzir vínculo explícito obrigatório para novos usuários e novos fluxos.

---

## 22. Plano recomendado

### Objetivo

Separar formalmente:

- identidade de autenticação/acesso
- identidade civil/organizacional

### Direção recomendada

1. `Usuario` deve ser tratado arquiteturalmente como identidade de acesso.
2. `Pessoa` deve permanecer como identidade civil/organizacional canônica.
3. Deve existir vínculo explícito entre ambos.
4. Para novos usuários, esse vínculo deve nascer no onboarding e no convite.
5. O RBAC pode continuar baseado em `Usuario`, `TenantUsuario` e `PerfilAcesso`.
6. O perfil pessoal exibido na UI deve ser reconciliado com a base canônica.
7. Fluxos de LGPD devem apontar para uma governança única dos dados pessoais.

### O que este relatório não recomenda fazer agora

- alterar auth;
- alterar onboarding;
- mudar JWT;
- mexer em RBAC;
- remover campos legados;
- assumir fusão imediata entre `Usuario` e `Pessoa`.

---

## 23. Confirmação de escopo

- Nenhum arquivo operacional foi alterado.
- Nenhuma migration foi criada.
- Nenhum model foi alterado.
- Nenhuma rota foi alterada.
- Nenhuma regra de autenticação, RBAC, onboarding ou usuários foi modificada.
- Apenas documentação foi criada.

---

## 24. Pergunta final obrigatória

**Para a versão 1.0 do AgroSaaS, `Usuario` não deveria continuar totalmente independente de `Pessoa`. A codebase mostra que `Usuario` hoje mistura autenticação, vínculo organizacional e dados pessoais duplicados, enquanto `Pessoa` já existe como base canônica civil. Portanto, a arquitetura deve evoluir para um vínculo explícito entre `Usuario` e `Pessoa` antes do lançamento, preferencialmente obrigatório para novos usuários e compatível com o legado existente.**
