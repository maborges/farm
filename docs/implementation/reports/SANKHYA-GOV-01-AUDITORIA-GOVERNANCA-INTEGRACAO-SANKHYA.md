# SANKHYA-GOV-01 — Auditoria de Governança da Integração Sankhya por Tenant e Unidade Produtiva

Data da auditoria: 2026-07-01

## 1. Resumo executivo

Esta auditoria avaliou a integração Sankhya sob a ótica de governança multi-tenant, isolamento de credenciais, localização da UI e adequação ao piloto.

Veredicto resumido:

- a integração **não está modelada como configuração global da plataforma**; o código atual aponta majoritariamente para **configuração por tenant**;
- a integração **não possui escopo por Unidade Produtiva**;
- a **UX e a navegação estão desalinhadas** com esse modelo, porque a principal vitrine de operação fica dentro do Backoffice, induzindo leitura de configuração global;
- o isolamento atual é **principalmente lógico por `tenant_id` em query**, mas **não há evidência suficiente de RLS físico ativo dentro do módulo Sankhya**, porque ele usa `get_db()` e não a dependência `get_session()` com contexto RLS;
- as credenciais **não aparentam estar criptografadas na persistência**, apesar do comentário do model indicar isso.

Conclusão objetiva:

- a integração Sankhya está **parcialmente correta** como modelagem de tenant;
- está **incorreta** como UX/navegação;
- está **parcialmente correta** em isolamento;
- está **incorreta** em governança de credenciais.

## 2. Veredicto geral

Veredicto: **PARCIALMENTE CORRETO, com desalinhamento importante de governança**.

Resposta à pergunta principal:

**A integração Sankhya não está acoplada ao Backoffice global no backend, mas a experiência atual do produto a apresenta como se fosse.**

Leitura prática:

- backend: comportamento orientado a tenant;
- frontend/navegação: posicionamento de backoffice global;
- unidade produtiva: não modelada;
- segurança de credenciais: fraca;
- piloto: viável com workaround, mas não no desenho final desejado.

## 3. Evidências encontradas

### Backend

- Configuração da integração por `tenant_id` único em [services/api/integracoes/sankhya/models/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/models/__init__.py:10).
- `SankhyaConfig.tenant_id` é `unique=True`, sugerindo uma configuração por tenant em [services/api/integracoes/sankhya/models/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/models/__init__.py:15).
- Password persistido no model `SankhyaConfig.password` em [services/api/integracoes/sankhya/models/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/models/__init__.py:20).
- Criação/atualização da configuração via `POST /api/v1/integracoes/sankhya/config` usando `tenant_id = Depends(get_current_tenant)` em [services/api/integracoes/sankhya/routers/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/routers/__init__.py:54).
- Atualização direta do password em `existing.password = config.password` em [services/api/integracoes/sankhya/routers/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/routers/__init__.py:64).
- Persistência direta do password em `criar_config(... password=password ...)` em [services/api/integracoes/sankhya/services/sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py:142).
- Recuperação de configuração por tenant em [services/api/integracoes/sankhya/services/sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py:136) e [services/api/integracoes/sankhya/services/nfe_financeiro_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/nfe_financeiro_service.py:21).
- Logs, pessoas, produtos, NFes e lançamentos financeiros carregam `tenant_id` no model em [services/api/integracoes/sankhya/models/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/models/__init__.py:40), [services/api/integracoes/sankhya/models/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/models/__init__.py:71), [services/api/integracoes/sankhya/models/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/models/__init__.py:119), [services/api/integracoes/sankhya/models/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/models/__init__.py:163), [services/api/integracoes/sankhya/models/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/models/__init__.py:217).
- Listagens filtram explicitamente por `tenant_id` em [services/api/integracoes/sankhya/routers/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/routers/__init__.py:236), [services/api/integracoes/sankhya/routers/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/routers/__init__.py:264), [services/api/integracoes/sankhya/routers/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/routers/__init__.py:290), [services/api/integracoes/sankhya/routers/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/routers/__init__.py:352), [services/api/integracoes/sankhya/routers/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/routers/__init__.py:438).
- O módulo usa `get_db()` e não `get_session()` em [services/api/integracoes/sankhya/routers/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/routers/__init__.py:8).
- `get_db()` não injeta `app.current_tenant_id` nem recebe `Request` em [services/api/core/database.py](/opt/lampp/htdocs/farm/services/api/core/database.py:69).
- `get_session()` é a dependência que ativa RLS via `SET LOCAL app.current_tenant_id` em [services/api/core/dependencies.py](/opt/lampp/htdocs/farm/services/api/core/dependencies.py:83).
- `get_current_tenant()` resolve o tenant a partir do JWT/associação do usuário em [services/api/core/dependencies.py](/opt/lampp/htdocs/farm/services/api/core/dependencies.py:275).

### Frontend

- A principal tela de visibilidade operacional da integração está em [apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx:1).
- Essa tela usa breadcrumb `Backoffice > Integrações ERP` em [apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx:58).
- Essa mesma tela chama APIs tenant-scoped `/integracoes/sankhya/status` e `/integracoes/sankhya/logs` em [apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx:47).
- A tela de configuração detalhada está fora da área `(dashboard)` em [apps/web/src/app/integracoes/sankhya/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/integracoes/sankhya/page.tsx:1).
- A tela detalhada grava `ws_url`, `username`, `password` e `sync_interval` em [apps/web/src/app/integracoes/sankhya/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/integracoes/sankhya/page.tsx:102).
- A navegação de backoffice só aparece para usuário com role de backoffice ou `is_superuser` em [apps/web/src/components/layout/app-sidebar.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/layout/app-sidebar.tsx:158).
- O grupo de configurações do tenant não possui item de integração ERP em [apps/web/src/components/layout/app-sidebar.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/layout/app-sidebar.tsx:301).
- O item de menu atual para `Integrações ERP` foi colocado no grupo de configuração do backoffice em [apps/web/src/lib/sidebar-config.ts](/opt/lampp/htdocs/farm/apps/web/src/lib/sidebar-config.ts:660).
- A permissão aplicada no menu de backoffice é `backoffice:config:view` em [apps/web/src/lib/sidebar-config.ts](/opt/lampp/htdocs/farm/apps/web/src/lib/sidebar-config.ts:663).
- O tenant já possui permissões próprias de settings em [apps/web/src/lib/permissions.ts](/opt/lampp/htdocs/farm/apps/web/src/lib/permissions.ts:105), mas não há permissão específica de integração ERP por tenant.

## 4. Estado atual da integração Sankhya

Fato encontrado:

- a integração já cobre configuração, teste de conexão, status, logs, sincronização de pessoas, sincronização de produtos, NFe e financeiro;
- a API está registrada em `/api/v1/integracoes/sankhya` em [services/api/main.py](/opt/lampp/htdocs/farm/services/api/main.py:508).

Leitura do estado atual:

- configuração: por tenant;
- execução/sync: por tenant;
- monitoramento: por tenant, mas exibido em tela de backoffice;
- unidade produtiva: ausente;
- criptografia de credencial: não evidenciada;
- RLS físico no módulo: não evidenciado.

## 5. Análise de governança multi-tenant

### Modelagem da configuração

Classificação: **CORRETO**

Motivo:

- `SankhyaConfig` possui `tenant_id` único, logo a intenção explícita é uma configuração por tenant, não global da plataforma.

### Escopo tenant

Classificação: **PARCIALMENTE CORRETO**

Motivo:

- quase toda a integração resolve a configuração e os dados por `tenant_id`;
- porém o isolamento depende de filtros lógicos nas queries do módulo;
- não há evidência de RLS físico ativado nesse módulo porque o router usa `get_db()` em vez de `get_session()`.

### Escopo unidade produtiva

Classificação: **NÃO ENCONTRADO**

Motivo:

- não há `unidade_produtiva_id` nos models, schemas, services ou rotas do Sankhya;
- não há separação entre tenant inteiro e unidade produtiva específica.

## 6. Análise tenant × unidade produtiva

Fato encontrado:

- o desenho atual assume um único `SankhyaConfig` por tenant em [services/api/integracoes/sankhya/models/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/models/__init__.py:15).

Leitura:

- isso atende um cenário em que o ERP cobre o tenant inteiro;
- isso não distingue:
  - unidade produtiva conectada ao ERP;
  - unidade produtiva sem ERP;
  - múltiplas unidades com comportamentos distintos;
  - tenants com mais de um contexto operacional.

Conclusão:

- para o modelo SaaS do AgroSaaS, a integração está hoje **tenant-scoped**, não **unit-scoped**;
- isso pode ser aceitável como v1 se o Sankhya for entendido como integração administrativa do produtor como um todo;
- não atende um cenário em que uma única organização queira governança por unidade produtiva.

Classificação:

- tenant x unidade produtiva: **AMBÍGUO**

## 7. Análise da localização atual no Backoffice

Fato encontrado:

- a principal tela de ERP fica em `dashboard/backoffice/integracoes/erp`;
- a sidebar de backoffice exige role de backoffice ou superuser;
- o tenant admin não possui item equivalente em `settings`.

Leitura:

- a tela está localizada como se a integração fosse assunto do operador interno da plataforma;
- isso entra em conflito com o comportamento do backend, que é por tenant e usa o tenant do usuário autenticado.

Conclusão:

- a localização atual no Backoffice é **arquiteturalmente incorreta** para configuração administrativa do cliente;
- ela é aceitável apenas como console interno de suporte/monitoramento, não como ponto principal de configuração do ERP do tenant.

Classificação:

- localização da tela: **INCORRETO**

## 8. Riscos de segurança e isolamento

### Credenciais

Fato encontrado:

- o model comenta `password` como “Criptografado”, mas o código grava o valor recebido diretamente, sem camada explícita de criptografia em [services/api/integracoes/sankhya/models/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/models/__init__.py:20), [services/api/integracoes/sankhya/routers/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/routers/__init__.py:66) e [services/api/integracoes/sankhya/services/sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py:150).

Classificação:

- segurança das credenciais: **INCORRETO**

### Isolamento entre tenants

Fato encontrado:

- há filtro explícito por `tenant_id` em logs, pessoas, produtos, NFes e lançamentos;
- o módulo não mostra evidência de `SET LOCAL app.current_tenant_id` via dependency de sessão.

Leitura:

- isolamento lógico existe;
- isolamento físico por RLS não foi comprovado no módulo Sankhya;
- isso aumenta o risco de regressão futura se alguma query esquecer o filtro de tenant.

Classificação:

- isolamento multi-tenant: **PARCIALMENTE CORRETO**

### Logs

Fato encontrado:

- `SankhyaSyncLog` possui `tenant_id` e a listagem filtra por tenant.

Classificação:

- logs: **CORRETO**

### Jobs/sync

Fato encontrado:

- `sync/completo` retorna mensagem de “fila” mas não evidencia orquestração robusta no módulo auditado em [services/api/integracoes/sankhya/routers/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/routers/__init__.py:202).

Classificação:

- jobs/sync: **AMBÍGUO**

## 9. Impacto no primeiro piloto

Perguntas do piloto:

### O cliente conseguiria configurar Sankhya sem acesso ao Backoffice global?

Resposta:

- hoje, pela navegação padrão, **não de forma clara**;
- existe a tela `/integracoes/sankhya`, mas ela não está posicionada como configuração do tenant.

### O administrador do tenant conseguiria operar a integração?

Resposta:

- no backend, sim, porque os endpoints são tenant-scoped;
- na UX, não está claro, porque a navegação leva o tema para backoffice.

### A configuração atual cria risco de suporte manual?

Resposta:

- sim;
- o time pode acabar operando isso como configuração interna da plataforma, quando na verdade é configuração do cliente.

### A configuração atual bloqueia o piloto?

Resposta:

- não bloqueia tecnicamente o piloto;
- mas cria fricção operacional e risco de governança.

### A configuração atual é aceitável como workaround temporário?

Resposta:

- sim, como workaround controlado para o primeiro piloto;
- não é recomendável como arquitetura definitiva.

Classificação:

- adequação ao piloto: **PARCIALMENTE CORRETO**

## 10. Classificação por área

| Área | Classificação | Leitura |
| --- | --- | --- |
| Modelagem da configuração | CORRETO | O desenho atual é por tenant. |
| Escopo tenant | PARCIALMENTE CORRETO | Há tenant_id, mas sem evidência clara de RLS físico no módulo. |
| Escopo unidade produtiva | NÃO ENCONTRADO | Não há vínculo com unidade produtiva. |
| Segurança das credenciais | INCORRETO | Password aparenta persistir sem criptografia explícita. |
| Isolamento multi-tenant | PARCIALMENTE CORRETO | Filtro lógico existe; RLS físico não está comprovado no módulo. |
| Localização da tela | INCORRETO | A UX principal posiciona a integração como backoffice global. |
| Permissões | AMBÍGUO | Backend tenant-scoped; frontend exposto em backoffice; sem permissão tenant dedicada. |
| Logs | CORRETO | Logs possuem tenant_id e filtragem por tenant. |
| Jobs/sync | AMBÍGUO | Há endpoints de sync, mas a fila/orquestração não está clara. |
| Adequação ao piloto | PARCIALMENTE CORRETO | Funciona com workaround, mas não é o desenho ideal. |

## 11. Lacunas críticas

- credenciais do Sankhya sem evidência de criptografia real;
- módulo sem evidência de RLS físico ativado na sessão;
- localização principal da integração em Backoffice, induzindo interpretação global indevida;
- ausência de permissão tenant dedicada para integração ERP.

## 12. Lacunas não críticas

- ausência de escopo por unidade produtiva;
- ausência de diferenciação clara entre console interno de suporte e console administrativo do cliente;
- sincronização completa com semântica de fila ainda pouco explícita.

## 13. Recomendação arquitetural

Recomendação objetiva:

- tratar Sankhya como **integração administrativa do tenant**, não como configuração global da plataforma;
- manter um console de suporte/backoffice apenas para observabilidade interna e diagnóstico;
- formalizar se o escopo oficial da v1 é:
  - por tenant;
  - ou por tenant com futura extensibilidade por unidade produtiva.

Leitura recomendada para a v1:

- se o objetivo do piloto é produtor/exportador com ERP administrativo centralizado, **configuração por tenant é suficiente para a v1**;
- vínculo por unidade produtiva pode esperar, desde que documentado como limitação deliberada.

## 14. Recomendação de UX/navegação

- a configuração principal do Sankhya deveria migrar para a área de **Administração do Tenant**;
- o local mais coerente seria um agrupamento de `Configurações` ou `Integrações do Tenant`;
- o Backoffice deveria ficar apenas com:
  - visão consolidada;
  - monitoramento;
  - suporte;
  - troubleshooting.

## 15. O que pode esperar

- modelagem por unidade produtiva;
- redesign mais profundo da experiência de integrações;
- console interno avançado de suporte;
- refino de fila e observabilidade de sync.

## 16. Próxima execução sugerida

Sugestão:

**SANKHYA-GOV-02 — Reorganização de Governança e Navegação da Integração Sankhya**

Escopo sugerido para a próxima execução:

- separar oficialmente console do tenant e console de backoffice;
- adicionar permissão tenant específica para integrações ERP;
- mover o ponto principal de configuração para a área administrativa do tenant;
- auditar e corrigir a persistência segura das credenciais;
- auditar a adoção de `get_session()` ou mecanismo equivalente para garantir RLS físico no módulo.
