# BRAND-RENAME-01 — Auditoria AgroSaaS → DeepFarms

**Fase:** auditoria somente. Este relatório não altera código, dados, migrations, contratos ou infraestrutura.

## 1. Resumo executivo

Foram encontradas **2.070 linhas** contendo `AgroSaaS`, `AGROSAAS`, `agrosaas`,
`Agro SaaS`, `agro-saas` ou `agro_saas`, em **558 arquivos**. Algumas linhas
possuem mais de uma ocorrência: a contagem de tokens é **2.463**. A
classificação usa a unidade segura para implementação: linha/região homogênea.

| Classificação | Linhas/regiões | Leitura |
| --- | ---: | --- |
| RENOMEAR | 154 | Identidade apresentada ao usuário ou ao mercado. |
| MANTER | 859 | Histórico, identificador persistido, teste ou contrato técnico. |
| REVISAR MANUALMENTE | 1.057 | Pode ser branding, mas há risco de compatibilidade ou decisão de dono. |
| **Total** | **2.070** | |

Também foram localizadas **492 linhas** com `DeepFarms`, sobretudo na baseline
e em `docker-compose.prod.yml`, que já usa imagens/containers `deepfarms-*`.
Há **duas** referências a `DeepAgro`, ambas em relatórios históricos; não devem
ser substituídas nesta fase.

O rebranding visual/comercial pode ocorrer sem migration nem alteração do RDS.
Os riscos relevantes são URLs públicas já emitidas, chave de browser,
namespaces determinísticos, integrações e runbooks de instalações antigas.

## 2. Escopo auditado

A busca foi feita em todo o checkout textual: `services/api`, `apps/web`,
`apps/campo`, `packages`, `docs`, arquivos raiz, manifests, `package.json`,
`pyproject.toml`, `.env*`, templates, scripts e runbooks. Foram usadas buscas
case-insensitive para as variações solicitadas e para `DeepFarms`/`DeepAgro`.

Foram excluídos da contagem artefatos transitórios de dependências e build
(`node_modules`, `.next`, `__pycache__`, `.git`). O service worker rastreado em
`apps/campo/public/sw.js` foi tratado separadamente como artefato gerado. Não
foram lidos nem alterados dados do banco; `services/api/agrosaas.db` é item
protegido.

| Área | Linhas | Observação |
| --- | ---: | --- |
| `docs/` | 1.732 | Relatórios, arquitetura, runbooks e material histórico. |
| `services/api/` | 163 | API, templates, jobs, testes, scripts e migrations. |
| `apps/web/` | 116 | UI, metadata, landing, integrações e chaves de browser. |
| `apps/campo/` | 6 | Metadata, manifest, ativação e service worker. |
| `packages/` | 3 | Comentários internos. |
| raiz/scripts/configuração | 50 | README, compose local e automação. |

## 3. Inventário de ocorrências

O inventário está agrupado por arquivo/região homogênea: textos repetidos e
linhas do mesmo contrato permanecem uma decisão única. Os grupos documentais
indicam o conjunto completo de arquivos e linhas cobertos.

| Arquivo/região | Linha/região | Valor atual | Contexto | Classificação | Novo valor sugerido | Justificativa e risco |
| --- | --- | --- | --- | --- | --- | --- |
| `apps/web/src/app/layout.tsx` | 12 | `AgroSaaS \| Dashboard` | metadata | RENOMEAR | `DeepFarms \| Dashboard` | Marca de navegador; rebuild Web. |
| `apps/web/src/app/page.tsx` | 60, 305, 401, 495–1000 | nome, logo, cópia, e-mail | landing pública | RENOMEAR | `DeepFarms` | Identidade comercial. `contato@agrosaas.com.br` depende de mailbox/alias pronto. |
| `apps/web/src/app/frota/page.tsx` | 141–510 | `AgroSaaS Frota` e CTAs | landing comercial | RENOMEAR | `DeepFarms Frota` | Texto e alt visíveis. |
| `apps/web/src/components/auth/auth-layout.tsx` e `app/(auth)/register/page.tsx` | cabeçalho/rodapé | texto e `/logos/agrosaas-mark.svg` | login/cadastro | RENOMEAR | `DeepFarms` e asset novo | Troca visual coordenada; não remover asset antigo antes de validar deploy. |
| `apps/web/src/app/(auth)/**` | convite, reset, pedido | `Segurança AgroSaaS` | telas autenticáveis | RENOMEAR | `Segurança DeepFarms` | Marca apresentada ao usuário. |
| `apps/web/src/app/(dashboard)/**` | títulos, descrições e labels | `AgroSaaS` | dashboard/backoffice | RENOMEAR | `DeepFarms` | Inclui billing, IA, suporte, CRM, planos, ESG e propriedades. |
| `apps/web/src/app/public/passaportes/[token]/page.tsx`, `track/[codigo]/page.tsx` | 66–168; 159 | certificação/rodapé | páginas públicas | RENOMEAR | `DeepFarms` | Nova identidade; documentos já emitidos não são regravados. |
| `apps/web/src/components/integracoes/erp/{capability-labels,capability-center,policy-manager,sync-center-view-model}.tsx` | textos | `AgroSaaS` | UI de ERP | RENOMEAR | `DeepFarms` | Apenas cópia de UI, não enums. |
| `apps/web/src/components/integracoes/erp/{types,capability-view-model}.ts` | `ERP_TO_AGROSAAS`, `AGROSAAS_TO_ERP` | enum/direção | integração | MANTER | sem mudança | Pode estar persistido ou ser esperado por API/testes. |
| `apps/web/src/lib/stores/app-store.ts`, `lib/api.ts`, `components/auth/tenant-tab-sync-warning.tsx` | `agrosaas-auth-storage` | chave `localStorage` | sessão do browser | MANTER | sem mudança inicial | Renomear desconecta sessões locais; só com migração compatível. |
| `apps/web/src/proxy.ts` | 44–45 | `agrosaas.com` | host legado | REVISAR MANUALMENTE | manter alias ou redirecionar | Confirmar DNS/Nginx e tráfego legado antes de remover. |
| `apps/web/src/app/integracoes/contmatic/page.tsx` | 37 | `prefixo_arquivo: 'AGROSAAS'` | exportação Contmatic | REVISAR MANUALMENTE | decisão de contrato | Importador externo pode depender do prefixo. |
| `apps/web/src/app/(dashboard)/dashboard/agricola/rastreabilidade/page.tsx` e `services/api/agricola/rastreabilidade/service.py` | URLs públicas | `agrosaas.com.br`/`api.agrosaas.com` | QR/passaporte | REVISAR MANUALMENTE | novas emissões DeepFarms após validação | QR já impresso/persistido não pode deixar de resolver. |
| `apps/campo/src/app/layout.tsx`, `public/manifest.json`, `src/app/(auth)/activate/page.tsx` | metadata/ativação | `AgroSaaS Campo` | PWA | RENOMEAR | `DeepFarms Campo` | Nome instalado e login do Campo; rebuild Campo. |
| `apps/campo/public/AgroSaaS-icone.webp` | arquivo | nome/arte da marca | asset PWA | RENOMEAR | asset DeepFarms equivalente | Criar e referenciar asset novo; manter anterior durante janela de cache. |
| `apps/campo/public/sw.js` | precache | `/AgroSaaS-icone.webp` | service worker gerado | MANTER | não editar manualmente | Regenerar no build após alterar manifest/asset. |
| `services/api/main.py` | 138–139 | `AgroSaaS API` | OpenAPI | RENOMEAR | `DeepFarms API` | Metadado público; restart API; paths e operation IDs não mudam. |
| `services/api/core/templates/emails/**` | conteúdo | marca no HTML | e-mails transacionais | RENOMEAR | `DeepFarms` | Conteúdo enviado ao usuário. |
| `services/api/core/services/email_service.py`, `core/routers/backoffice.py`, `notificacoes/**`, `notifications/email_adapter.py`, `automacoes/followup_worker.py` | assunto/corpo | `AgroSaaS` | e-mail/notificação | RENOMEAR | `DeepFarms` | Cópia futura; reiniciar os processos que a renderizam. |
| `services/api/notifications/notification_config.py` | 45 | default `SMTP_FROM_NAME=AgroSaaS` | remetente | REVISAR MANUALMENTE | `DeepFarms` após confirmação | Fallback de ambiente pode divergir do SMTP global. |
| `services/api/core/utils/pdf_generator.py`, `operacional/services/frota_export_service.py` | 24; 348–359 | título/metadados | PDF/XLSX | RENOMEAR | `DeepFarms` | Saída nova ao usuário; documentos históricos não mudam. |
| `services/api/financeiro/services/nfe_xml_generator.py` | 210 | `Emissão de NFe via sistema AgroSaaS` | XML fiscal | REVISAR MANUALMENTE | decisão fiscal | `xJust` pode ser conteúdo de documento fiscal/contábil. |
| `services/api/core/config.py` | 9, 106 | `project_name`, `mail_from` | default runtime | REVISAR MANUALMENTE | marca/remetente aprovados | E-mail depende de domínio, SPF/DKIM/DMARC e mailbox. |
| `services/api/core/config.py`, `core/database.py`, `.env.example` | SQLite e `/tmp/agrosaas_uploads` | caminho/arquivo legado | dev/storage | MANTER | sem mudança | Não renomear por branding. Produção declarada usa `/opt/deepfarms/storage`. |
| `services/api/core/exceptions.py` | todas | `AgroSaaSError` | classe interna | MANTER | sem mudança | Identificador técnico importado na API. |
| `services/api/{agricola,integracoes}/**` | `agrosaas:*` | UUID namespace | IDs/deduplicação | MANTER | sem mudança | Renomear muda UUIDs e idempotência. |
| `services/api/**` | `client_system="agrosaas"` | integração TARA/Balança | protocolo externo | MANTER | sem mudança | Valor de contrato e fixture. |
| `services/api/core/services/analytics_request_cache.py` | 14–15 | `agrosaas_*` | estado interno | MANTER | sem mudança | Sem exposição comercial; evitar efeito lateral em cache. |
| `services/api/migrations/**` | campos/comentários/revisions | `*_agrosaas` | DDL/histórico | MANTER | sem mudança | Migrations e identificadores persistidos são protegidos. |
| `services/api/tests/**`, `pytest_out*.txt`, `scripts/reports/**` | fixtures/asserts/saídas | marca de teste | histórico/teste | MANTER | sem mudança nesta fase | Só ajustar asserts vinculados a texto RENOMEAR, em commit próprio. |
| `services/api/pyproject.toml`, `agrosaas_api.egg-info/**` | pacote `agrosaas-api` | empacotamento | build | REVISAR MANUALMENTE | manter inicialmente | Pode quebrar `pip`, artefatos e automações; `egg-info` é gerado. |
| `docker-compose.yml` | containers e DB `agrosaas` | ambiente local | volumes/DB | MANTER | sem mudança | Renomear pode criar banco/volume novo. |
| `docker-compose.prod.yml` | `deepfarms-*` | produção | imagens/rede | MANTER | já correto | Infraestrutura produtiva já rebrandada. |
| `docs/implementation/reports/**` | 350 linhas, 107 arquivos | fatos concluídos | relatório histórico | MANTER | sem mudança | Preservar rastreabilidade. |
| `docs/audits/**`, `docs/qwen/**`, `docs/analysis/**` | 330 linhas, 68 arquivos | auditoria/análise | histórico | MANTER | sem mudança | Alteração reescreveria estado observado. |
| `README.md`, `docs/comercial/**`, `docs/operations/notifications-email.md` | apresentação/operação | marca/exemplos | documentação atual | RENOMEAR com ressalva | `DeepFarms` | E-mail e exemplos SMTP só após provisionamento. |
| `docs/architecture/**`, `docs/pilot/**`, `docs/contexts/**`, demais `docs/**` | 1.057 linhas, 383 arquivos | norma/plano/histórico mistos | documentação | REVISAR MANUALMENTE | triagem por owner | Não há como inferir com segurança se cada documento é canônico vivo ou registro. |
| `docs/runbooks/deploy-les-svrbo-ap01.md` | 166 linhas | usuário/path/unit/DB `agrosaas` | runbook | REVISAR MANUALMENTE | runbook DeepFarms após inventário real | Mistura exemplos antigos e nota real de produção `farms`/`borgus`. |
| `docs/implementation/reports/NAVIGATION-MODE-01{A,C2}*.md` | linha 7; linha 4 | `DeepAgro` | relatório histórico | MANTER | sem mudança | Não introduzir nome não oficial nem reescrever histórico. |

## 4. Ocorrências RENOMEAR

### API

- OpenAPI em `services/api/main.py`.
- Templates em `services/api/core/templates/emails/**`.
- Assuntos/corpos em `core/services/email_service.py`, `core/routers/backoffice.py`,
  `notificacoes/**`, `notifications/email_adapter.py` e `automacoes/followup_worker.py`.
- Título do PDF e metadados de exportação em `core/utils/pdf_generator.py` e
  `operacional/services/frota_export_service.py`.

### Web

- Metadata raiz, landing principal/Frota e layouts de autenticação.
- Títulos de dashboard/backoffice, páginas públicas de passaporte e textos de
  integração ERP classificados como UI.
- Logo Web e seus consumidores, mediante asset DeepFarms novo.

### Campo

- Layout, manifest, ativação e ícone de origem. O service worker é derivado e
  deve ser gerado novamente pelo build.

### E-mails, relatórios e documentação atual

- Todos os HTML em `core/templates/emails/` e os assuntos classificados acima.
- PDF/XLSX novos; não reprocessar documentos já emitidos.
- `README.md`, `docs/comercial/**`, `docs/operations/notifications-email.md` e
  `docs/runbooks/field-pwa-local-setup.md`, após confirmar que são vigentes.

## 5. Ocorrências MANTER

- migrations, revision IDs, DDL, campos legados `*_agrosaas` e comentários de migration;
- `services/api/agrosaas.db`, nomes de banco/containers locais, volumes e paths
  históricos, incluindo `/tmp/agrosaas_uploads`;
- `client_system="agrosaas"`, contratos TARA/Balança e enums
  `ERP_TO_AGROSAAS`/`AGROSAAS_TO_ERP`;
- UUID namespaces contendo `agrosaas`, pois definem IDs determinísticos;
- `AgroSaaSError`, chaves internas de cache e a chave
  `agrosaas-auth-storage`;
- resultados de testes, fixtures de protocolo, `egg-info`, relatórios e
  auditorias históricas;
- PWA service worker gerado e os dois relatórios históricos com `DeepAgro`.

## 6. Ocorrências REVISAR

| Caso | Decisão necessária | Risco se alterado sem decisão |
| --- | --- | --- |
| URLs `agrosaas.com.br`/`api.agrosaas.com` em QR e rastreabilidade | Definir URL para emissões novas, alias/redirect e compatibilidade. | QR já emitido pode deixar de resolver; quebra de rota pública. |
| `contato@agrosaas.com.br`, `noreply@agrosaas.com.br` e defaults SMTP | Confirmar domínio, SPF/DKIM/DMARC, mailbox e aliases. | Falha de entrega/remetente inválido. |
| `agrosaas.com` no proxy Web | Confirmar se é alias legado ativo. | Pode interromper login ou roteamento de domínio antigo. |
| Prefixo `AGROSAAS` da Contmatic | Validar com cliente/importador. | Arquivo pode deixar de ser reconhecido. |
| `xJust` de NF-e | Aprovação fiscal. | Alteração de documento fiscal sem respaldo. |
| Nome do pacote em `pyproject.toml` | Decisão de build/distribuição. | Quebra de `pip`, artefatos e automações. |
| Runbook LES-SVRBO-AP01 | Comparar com serviços realmente instalados. | Paths, usuários, systemd, Nginx, DB e backup podem apontar para recursos reais. |
| Documentação de arquitetura/pilot/contexto | Owner deve distinguir documento vivo de registro histórico. | Perda de rastreabilidade ou links quebrados. |
| `DeepAgro` nos relatórios | Confirmar se o texto histórico deve continuar literal. | Revisão retroativa de material concluído. |

## 7. Impacto técnico

| Área | Impacto esperado na implementação | Banco/migration |
| --- | --- | --- |
| Web | Textos, metadata e assets; validar páginas públicas, login e dashboard. | Nenhum. |
| Campo PWA | Manifest, título e ícone; cache exige nova publicação. | Nenhum. |
| API | OpenAPI, assuntos, templates, PDF/export. | Nenhum. |
| Workers | Reinício somente se renderizam textos alterados. | Nenhum. |
| Outbox | Não mudar event type/payload. Decidir se mensagens pendentes permanecem históricas. | Nenhum. |
| RDS | Não há rename de tabela/coluna/schema/enum/constraint/índice. | **Nenhuma migration.** |
| Storage | Não migrar, mover ou renomear objetos. | Nenhum. |
| Integrações | Manter valores de contrato; alterar somente labels da UI. | Nenhum. |
| E-mail | Trocar cópia; remetente/domínio somente depois de validação operacional. | Nenhum. |
| PDF/relatórios | Documentos novos usam marca nova; históricos não mudam. | Nenhum. |

## 8. Impacto de deploy

| Item | Necessário? | Motivo |
| --- | --- | --- |
| Migration de banco | Não | Não há alteração estrutural proposta. |
| Rebuild Web | Sim | Metadata, UI e logo são empacotados pelo Next.js. |
| Rebuild Campo | Sim | Manifest, ícone e service worker/precache precisam ser regenerados. |
| Restart API | Sim, se API/e-mails/PDF mudarem | Recarregar templates, metadados e código. |
| Restart worker | Condicional | Necessário se worker/follow-up/resumo diário mudar. |
| Restart outbox | Condicional | Só se processo residente renderiza notificação alterada. |
| Nginx | Não, neste escopo | Reabrir apenas para alias/redirect de domínio legado aprovado. |
| DNS | Não | Produção já informa `deepfarms.com.br`; legado requer decisão separada. |
| SSL | Não | Nenhum host novo é proposto. |
| Storage | Não | Nenhuma alteração proposta. |

## 9. Arquivos candidatos à futura alteração

Lista fechada de alta confiança para uma primeira implementação não destrutiva.
Itens em **REVISAR** não entram sem decisão registrada.

```text
apps/web/src/app/layout.tsx
apps/web/src/app/page.tsx
apps/web/src/app/frota/page.tsx
apps/web/src/app/(auth)/register/page.tsx
apps/web/src/app/(auth)/reset-password/page.tsx
apps/web/src/app/(auth)/convite/aceitar/page.tsx
apps/web/src/app/(auth)/pedido-compra/confirmar/page.tsx
apps/web/src/app/public/passaportes/[token]/page.tsx
apps/web/src/app/track/[codigo]/page.tsx
apps/web/src/app/onboarding/sucesso/page.tsx
apps/web/src/app/(dashboard)/**              # somente textos/metadata RENOMEAR
apps/web/src/components/auth/auth-layout.tsx
apps/web/src/components/layout/{topbar,app-sidebar}.tsx
apps/web/src/components/landing/FrotaHeroContent.tsx
apps/web/src/components/agricola/soil-diagnosis-dialog.tsx
apps/web/src/components/integracoes/erp/{capability-labels,capability-center,policy-manager,sync-center-view-model}.tsx
apps/web/public/logos/agrosaas-mark.svg      # troca coordenada de asset

apps/campo/src/app/layout.tsx
apps/campo/src/app/(auth)/activate/page.tsx
apps/campo/public/manifest.json
apps/campo/public/AgroSaaS-icone.webp        # substituir por asset novo coordenado

services/api/main.py
services/api/core/templates/emails/{base,welcome,invite,password_reset,trial_notice,invoice_approved}.html
services/api/core/services/email_service.py
services/api/core/routers/backoffice.py
services/api/notificacoes/{service,email_service,resumo_diario_envio_service}.py
services/api/notifications/email_adapter.py
services/api/automacoes/followup_worker.py
services/api/core/utils/pdf_generator.py
services/api/operacional/services/frota_export_service.py

README.md
docs/comercial/**
docs/operations/notifications-email.md
docs/runbooks/field-pwa-local-setup.md
```

## 10. Arquivos e identificadores explicitamente protegidos

```text
services/api/migrations/**
services/api/agrosaas.db
services/api/core/exceptions.py: AgroSaaSError
services/api/**: UUID namespaces "agrosaas:*"
services/api/**: client_system="agrosaas"
apps/web/src/lib/stores/app-store.ts: agrosaas-auth-storage
apps/web/src/lib/api.ts e components/auth/tenant-tab-sync-warning.tsx: mesma chave
apps/web/src/components/integracoes/erp/types.ts: ERP_TO_AGROSAAS, AGROSAAS_TO_ERP
apps/campo/public/sw.js
docker-compose.yml: containers/DB locais agrosaas-*
docs/implementation/reports/**
docs/audits/**
docs/qwen/**
docs/implementation/reports/NAVIGATION-MODE-01A-AUDITORIA.md: DeepAgro
docs/implementation/reports/NAVIGATION-MODE-01C2-IMPLEMENTACAO-APP-MEGA-MENU.md: DeepAgro
```

## 11. Plano mínimo de implementação

1. Registrar decisões para URLs/redirects, mailboxes, Contmatic, NF-e, package
   name, proxy legado e runbook.
2. Criar assets DeepFarms para Web e Campo, mantendo os assets antigos durante
   a janela de cache e rollback.
3. Alterar somente textos, metadata e templates da lista de alta confiança.
4. Para novas URLs públicas, emitir DeepFarms somente após validar rota e
   preservar AgroSaaS antigo por alias/redirect.
5. Atualizar documentação atual aprovada pelo owner; não reescrever relatórios
   históricos.
6. Rebuild/deploy de Web e Campo; restart de API/worker/outbox quando os seus
   textos forem modificados.
7. Avaliar em épico futuro, se aprovado, chave local, package name, nomes de
   infraestrutura ou contratos externos.

## 12. Validação necessária após implementação

- `git diff --check`;
- testes backend afetados por e-mail, notificações, PDF/export e OpenAPI;
- frontend Web: typecheck, lint e build;
- Campo: typecheck/lint e build PWA, confirmando manifest e service worker;
- smoke API, incluindo `/docs`/OpenAPI e envio de e-mail de teste;
- smoke Web: landing, login/cadastro, dashboard, backoffice e passaportes;
- smoke Campo após limpar/revalidar cache e instalar a nova versão;
- verificação visual de logos, títulos, favicon/manifest e rodapés;
- verificação de e-mails transacionais/notificações e de PDF/XLSX novos;
- resolução de URLs AgroSaaS já emitidas e URLs DeepFarms novas.

## 13. Veredicto

**GO COM RESSALVAS** para iniciar `BRAND-RENAME-02 — Implementação`, desde que
a primeira entrega fique limitada aos candidatos de alta confiança e não toque
os itens protegidos.

Não há evidência de necessidade de migration, alteração estrutural no RDS,
mudança de storage, DNS ou SSL para o rebranding visual/comercial. A fase 02
não deve começar com alteração de QR/URLs, SMTP/remetentes, Contmatic, NF-e,
package name, `localStorage`, migrations, namespaces, integrações ou runbook
de produção sem as decisões manuais registradas acima.
