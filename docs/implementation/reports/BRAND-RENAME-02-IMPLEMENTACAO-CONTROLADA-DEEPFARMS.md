# BRAND-RENAME-02 — Implementação Controlada AgroSaaS → DeepFarms

## 1. Resumo executivo

Foi implementado o rebranding textual de alta confiança aprovado pela auditoria BRAND-RENAME-01. As alterações estão limitadas à identidade visual/comercial apresentada ao usuário em Web, Campo, API, e-mails, notificações, PDF/XLSX e documentação viva aprovada.

Foram preservados contratos, identificadores técnicos, URLs legadas, configuração operacional de SMTP, assets antigos necessários para compatibilidade e o service worker do Campo.

## 2. Arquivos alterados

Foram alterados 67 arquivos existentes, distribuídos entre `README.md`, Web, Campo, API e documentação viva. O inventário exato pode ser obtido com `git diff --name-only`.

Também foi criado este relatório. O relatório BRAND-RENAME-01 permaneceu sem alteração.

## 3. Quantidade de ocorrências de branding alteradas

O diff contém 146 tokens legados de branding removidos/substituídos nas linhas alteradas. As substituições foram manuais e orientadas pela classificação RENOMEAR da auditoria; não foi executado search-and-replace global.

## 4. Ocorrências deliberadamente mantidas

- chaves e enums técnicos `ERP_TO_AGROSAAS` e `AGROSAAS_TO_ERP`;
- namespace/chaves de browser, incluindo `agrosaas-auth-storage`;
- package name `agrosaas-api`;
- caminhos e URLs legadas de rastreabilidade/passaporte;
- `/tmp/agrosaas_uploads` e demais referências de infraestrutura/storage;
- endereços, fallback e demais parâmetros operacionais de SMTP;
- `prefixo_arquivo = "AGROSAAS"` e conteúdo fiscal de NF-e;
- nomes históricos de migrations, relatórios e arquivos;
- os dois relatórios históricos que contêm `DeepAgro`;
- asset antigo `/logos/agrosaas-mark.svg` e `AgroSaaS-icone.webp`, pois não foi encontrado asset DeepFarms aprovado equivalente e não se deve inventar logo.

## 5. Ocorrências que continuam em REVISAR

Continuam fora do escopo as URLs antigas, host legado do proxy, configuração operacional de SMTP, domínio/endereço de e-mail, identificadores de integração, storage, nomes históricos, PDF comercial binário e referências técnicas cuja alteração possa quebrar compatibilidade.

## 6. Assets modificados/adicionados

Nenhum asset foi modificado ou adicionado. Consumidores textuais foram atualizados mantendo temporariamente os caminhos de assets antigos para cache/rollback.

## 7. Testes executados

- `git diff --check`: passou.
- `services/api/.venv/bin/python -m pytest test_password_recovery.py -q`: 1 passed.
- Campo `npm run typecheck`: passou.
- Campo `npm run lint`: passou.
- Web `npm run lint`: passou.
- Busca anti-regressão pelas variantes solicitadas e `DeepAgro`: executada; `DeepAgro` permanece somente em relatórios históricos protegidos.
- Verificação do diff contra migrations, service worker e identificadores protegidos: nenhum arquivo protegido foi alterado.

## 8. Typecheck, lint e build

O typecheck do Web foi executado, mas ficou bloqueado por dependências ausentes (`react-hook-form`) e por erro preexistente de tipagem em `propriedades-client.tsx`; o erro não foi introduzido por esta alteração. O build Web/Campo e os demais testes de integração ainda devem ser executados antes do merge/deploy.

## 9. Resultado de `git diff --check`

Passou sem erros após a correção de whitespace.

## 10. Banco e migrations

Nenhuma migration foi criada ou alterada. Nenhuma tabela, coluna, enum, constraint, índice, sequence, policy, RLS ou dado persistido foi alterado.

## 11. RDS

Nenhuma alteração no RDS.

## 12. DNS, SSL, Nginx e storage

Não houve alteração de DNS, certificados SSL, Nginx, volumes, containers, systemd ou storage.

## 13. Processos que precisarão de rebuild/restart

- rebuild Web;
- rebuild Campo, para regenerar o service worker pelo processo normal;
- restart da API, pois textos de OpenAPI/e-mail/PDF foram alterados;
- restart do worker se o processo carregar os módulos de follow-up/notificação alterados;
- restart do outbox somente se o processo residente carregar o adapter de notificações alterado.

Nenhum deploy foi executado.

## 14. Riscos ou pendências restantes

- o logo visual ainda utiliza assets legados até existir asset DeepFarms aprovado;
- URLs persistidas/legadas e endereços de e-mail continuam antigos por compatibilidade e decisão operacional;
- os builds e testes de aceitação devem ser executados no ambiente com dependências instaladas;
- documentos históricos não foram reescritos.

## 15. Veredicto

**BRAND-RENAME-02 — STATUS: GO COM RESSALVAS**

A implementação de branding textual de alta confiança está concluída sem alterações destrutivas. A fase pode seguir para validação técnica completa e análise antes de qualquer deploy em produção.
