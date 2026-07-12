# ERP-OPS-01 — Auditoria Operacional de Configuração, APIs, Estoque e De-Para ERP

**Status:** Concluído
**Data da Auditoria:** 12 de Julho de 2026

Este documento contém o relatório técnico resultante da auditoria operacional da implementação das integrações ERP no AgroSaaS, validando a arquitetura ERP-First materializada no runtime atual, com foco especial na integração Sankhya.

## 1. Configuração de Credenciais e Dados Técnicos do ERP

**Onde o cliente configura as credenciais e os dados técnicos do ERP?**

- **Console do Tenant:** O cliente utiliza a página de configurações no painel web (`apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx`), que invoca o componente dinâmico `DynamicErpConsole` (`apps/web/src/components/integracoes/erp-console.tsx`).
- **Endpoints de API:** O frontend consome os endpoints do ERP Router Canônico (`/api/v1/integracoes/erp/*`) e do Sankhya Router (`/api/v1/integracoes/sankhya/config`). A configuração é recebida no formato `SankhyaConfigCreate`.
- **Persistência Segura:** As credenciais e secrets (ex: `client_secret`, `x_token`, senhas) são persistidas no banco utilizando o pacote `cryptography.fernet` através dos utilitários em `services/api/integracoes/security.py` (`encrypt_integration_secret` e `decrypt_integration_secret`). O frontend recebe apenas máscaras.
- **Armazenamento de Estado:** As chaves ativas do tenant residem na entidade `TenantIntegracao` e os dados específicos do Sankhya ficam em `SankhyaConfig` (em `services/api/integracoes/sankhya/models/__init__.py`).

## 2. Configuração de APIs, Rotas e Operações do Provedor

**Onde são configuradas as APIs, rotas ou operações específicas de cada provedor?**

- **Catálogo de Features e Adapter:** A taxonomia das integrações e as *capabilities* são definidas no nível do *Canonical Adapter* (`SankhyaCanonicalAdapter` em `services/api/integracoes/sankhya/services/canonical_adapter.py`). Lá encontramos as chaves para `pessoas`, `produtos`, `financeiro`, `nfe`, entre outras.
- **Auth Gateway / WS Client:** O cliente HTTP que define as URLs e as operações fica em `SankhyaWSClient` (`services/api/integracoes/sankhya/services/sync_service.py`) e `SankhyaGatewayAuthService` (`services/api/integracoes/sankhya/services/auth_service.py`), que gerenciam a autenticação OAUTH ou legado dependendo das propriedades salvas no `SankhyaConfig`.
- **Exposição HTTP Interna:** O arquivo `services/api/integracoes/sankhya/routers/__init__.py` expõe os endpoints específicos da integração Sankhya. O `services/api/main.py` registra esse router em `/api/v1/integracoes`.

## 3. Sincronização de Estoque e Comportamento

**Quando o AgroSaaS sincroniza estoque, qual endpoint externo é chamado? Qual endpoint interno inicia a sincronização?**

- **Constatação Operacional:** Atualmente, a funcionalidade de Sincronização de Estoque agrícola está listada como uma **feature futura e não operacional**.
- No `SankhyaCanonicalAdapter` (`services/api/integracoes/sankhya/services/canonical_adapter.py`), a feature `estoque` é declarada com `"habilitada": False`, modo `"EVENTO"` e transporte `"OUTBOX"`. A restrição definida textualmente afirma: `"não cobre estoque operacional agrícola do AgroSaaS"`.
- Não existe um endpoint interno `/api/v1/integracoes/sankhya/sync/estoque` nos routers. As únicas rotas de sync ativas (em `services/api/integracoes/sankhya/routers/__init__.py`) são para `pessoas`, `produtos`, `financeiro`, `nfe` e `completo`. 

## 4. Services, Adapters e Capabilities de Estoque

**Qual service, adapter e capability executam essa chamada?**

- **Capability Code:** O código mapeado no modelo é `erp.estoque.administrativo.sincronizar`.
- **Adapter:** `SankhyaCanonicalAdapter`.
- **Serviço Helper (De-Para):** Existe, de forma latente, uma estrutura de vinculação de local de estoque (De-Para) preparada em `SankhyaExternalAssociationHelper.sync_deposito` (`services/api/integracoes/sankhya/services/external_association_helper.py`). Ela resolve o `CODLOCAL` e `NOMELOCAL` do ERP mapeando para a entidade `Deposito` do AgroSaaS. No entanto, não há um Sync Service ativo orquestrando e efetuando a chamada externa via HTTP (WS) neste escopo, indicando que o estoque aguarda implementação em fases seguintes (P2).

## 5. Dados de Estoque no AgroSaaS

**Quais dados de estoque entram no AgroSaaS?**

- Visto que a rota de sync ainda não opera, no modelo do helper, a perspectiva de integração foca nos *Locais de Estoque/Depósitos*, validando:
  - `CODLOCAL`
  - `NOMELOCAL` / `DESCRLOCAL` / `LOCAL`
  - `TIPOLOCAL`
  - `CODFILIAL` (Empresa / Filial atrelada)
A movimentação de quantidades de estoque físico agrícola em si parece isolada do tráfego administrativo atual que foca em Cadastros (Produto/Pessoa) e Notas/Financeiro.

## 6. Governança, De-Para e Observabilidade (Backoffice vs Console)

- O sistema adere estritamente à separação de poderes.
- **De-Para (Associação Externa):** Toda associação de registros entre AgroSaaS e ERP (como Pessoas ou Produtos) é efetuada no `ExternalRecordAssociationService`. Quando o *confidence* da associação é baixo (ex: o sistema não tem certeza se um `LocalEstoque` externo já é o `Deposito` local), um registro é deixado no status `PENDENTE`. 
- **Console do Tenant:** A reconciliação pode ser feita pelo tenant no console usando o endpoint canônico `/integracoes/erp/associacoes/{association_id}/reconciliar`.
- **Backoffice (Suporte):** O painel do backoffice (`dashboard/backoffice/integracoes/erp/page.tsx`) visualiza o Health, Logs (`SankhyaSyncLog`), diagnósticos cruzados da *readiness* e Jobs falhos. O Backoffice atua como apoio investigativo (sem ver texto puro de senha) observando as tabelas e o `IntegrationHealth`, porém a reconfiguração da *connection* é delegada à autoridade do Console do Tenant.
- **Schedules Automáticos:** Uma busca nos jobs orquestrados de background em `background_jobs.py` revela a ausência de um loop de Polling para integrações. Os processos ou são ativados via webhook/evento assíncrono futuro (Outbox) ou via demanda manual (`/sync/*`), de acordo com o `runtime_sync_modes` do adapter de integração ERP.

---
**Conclusão da Auditoria:**
A arquitetura ERP-First (Sankhya) está solidamente materializada em rotas, ownership de tenants e serviços de governança (Associação Externa / Readiness). As políticas de separação Console/Backoffice estão integradas. No aspecto técnico focado em Estoque, a auditoria constatou que o sync ativo ainda é uma promessa futura (registrada no adapter P2 para transporte assíncrono), havendo apenas mapeamentos de associação preexistentes de "Locais de Estoque". A plataforma bloqueia falhas de governança (máscara obrigatória de credenciais) e usa OAUTH2 + Fallbacks legados adequadamente na persistência e na comunicação externa.
