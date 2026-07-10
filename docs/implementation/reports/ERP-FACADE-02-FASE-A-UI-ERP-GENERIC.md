# ERP-FACADE-02 - Fase A: Desacoplamento Inicial da UI ERP do Provider Sankhya

Status: CONCLUIDA  
Data: 2026-07-09  
Escopo: refatoracao de fronteira de UI, sem alteracao de backend ou runtime

## Resumo executivo

Esta execucao concluiu a Fase A de baixo risco com sucesso.

A UI ERP do tenant e do backoffice passou a consumir uma superficie conceitualmente ERP-generic:

- `ErpConsole`
- `ErpTimeline`
- tipos `Erp*` nas telas ERP

O comportamento funcional foi preservado. Nenhum endpoint foi trocado. Toda a compatibilidade com o provider atual Sankhya foi mantida internamente por meio de aliases e do uso continuo de `/integracoes/sankhya/*`.

Conclusao desta fase:

- o acoplamento visual e conceitual das telas ERP ao nome Sankhya foi reduzido;
- o acoplamento tecnico de compatibilidade foi mantido de forma deliberada;
- backend, adapter, runtime e contratos canonicos permaneceram intactos.

## Auditorias executadas

### 1. Auditoria de reutilizacao

Arquivos auditados para reaproveitamento:

- [apps/web/src/components/integracoes/sankhya-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/sankhya-console.tsx)
- [apps/web/src/components/integracoes/sankhya-timeline.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/sankhya-timeline.tsx)
- [apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx)
- [apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx)

Conclusao:

- o comportamento existente de console e timeline era integralmente reaproveitavel;
- nao houve necessidade de duplicar logica;
- a mudanca adequada para esta fase era expor uma nova superficie de consumo `Erp*` sobre a implementacao atual.

### 2. Auditoria arquitetural

Mapeamento confirmado antes da alteracao:

- import direto de `SankhyaConsole` na tela ERP do tenant;
- import direto de `SankhyaTimeline` na tela ERP do backoffice;
- tipos `SankhyaStatus`, `SankhyaHealth`, `SankhyaJob`, `SankhyaLog`, `SankhyaDiagnosis` na tela de backoffice;
- nomes provider-first nos componentes compartilhados;
- textos de UI com `ERP atual: Sankhya`;
- uso de `/integracoes/sankhya/*` nas telas e componentes.

Conclusao:

- o maior acoplamento estava mesmo na borda consumidora;
- o comportamento interno ja era em boa parte generico, mas exposto por nomes Sankhya.

### 3. Auditoria do provider atual

Confirmacao registrada nesta fase:

- Sankhya continua sendo o provider atual;
- endpoints `/integracoes/sankhya/*` permanecem em uso;
- adapter, autenticacao, gateway, staging, sync tecnico e backend nao foram alterados.

### 4. Auditoria de extensibilidade

Conclusao:

- a troca de `SankhyaConsole`/`SankhyaTimeline` por `ErpConsole`/`ErpTimeline` reduz o acoplamento visual e conceitual;
- essa mudanca nao impede novos providers como SAP, TOTVS, Omie e Senior;
- a fase prepara uma futura Fachada ERP sem introduzir nova arquitetura.

## Arquivos alterados

- [apps/web/src/components/integracoes/sankhya-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/sankhya-console.tsx)
- [apps/web/src/components/integracoes/sankhya-timeline.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/sankhya-timeline.tsx)
- [apps/web/src/components/integracoes/erp-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp-console.tsx)
- [apps/web/src/components/integracoes/erp-timeline.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp-timeline.tsx)
- [apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx)
- [apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx)

## Arquivos apenas analisados

- [docs/implementation/reports/ERP-FACADE-01-AUDITORIA-ARQUITETURAL.md](/opt/lampp/htdocs/farm/docs/implementation/reports/ERP-FACADE-01-AUDITORIA-ARQUITETURAL.md)
- [docs/architecture/agrosaas-engineering-playbook.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-engineering-playbook.md)

Observacao:

- a skill de frontend referenciou `docs/03-frontend-web.md`, mas esse arquivo nao foi localizado no workspace durante a execucao.

## Acoplamentos removidos

### Tela ERP do tenant

- remocao do import direto de `SankhyaConsole`;
- substituicao por `ErpConsole`.

### Tela ERP do backoffice

- remocao do import direto de `SankhyaTimeline`;
- substituicao por `ErpTimeline`;
- renomeacao dos tipos locais de `Sankhya*` para `Erp*`.

### Superficie compartilhada

- exposicao de `ErpConsole` como superficie de consumo;
- exposicao de `ErpTimeline` e `ErpTimelineItem` como superficie de consumo;
- texto do console tenant ajustado para tratar Sankhya como ERP atual conectado, nao como nome da superficie.

## Acoplamentos mantidos por compatibilidade

Mantidos deliberadamente nesta fase:

- uso interno dos endpoints `/integracoes/sankhya/*`;
- tipos internos `Sankhya*` no componente de implementacao atual;
- arquivos fisicos `sankhya-console.tsx` e `sankhya-timeline.tsx`;
- aliases `SankhyaConsole` e `SankhyaTimeline` exportados para nao quebrar consumidores remanescentes.

Justificativa:

- a fase foi definida como refatoracao segura de fronteira;
- trocar endpoints ou reestruturar backend violaria o escopo aprovado;
- preservar aliases torna a mudanca incremental e reversivel.

## Justificativa para nao alterar backend

O backend nao foi alterado porque isso violaria explicitamente o escopo da Fase A.

Razoes tecnicas:

- o objetivo desta fase era desacoplamento visual e conceitual da UI;
- os endpoints Sankhya ainda sao a camada oficial de compatibilidade;
- o runtime ERP oficial ja existe e nao precisava de extensao nesta etapa;
- qualquer mudanca em adapter, readiness, auth, gateway, rotas ou contratos deslocaria a execucao para Fase B ou C.

## Riscos remanescentes

### 1. Compatibilidade ainda provider-first internamente

Mesmo com a superficie `Erp*`, a implementacao ainda consome `/integracoes/sankhya/*`.

### 2. Nomes fisicos de arquivo ainda expostos no repositorio

Os arquivos-base continuam com prefixo `sankhya-`, o que e aceitavel nesta fase, mas ainda denuncia o provider atual na camada interna.

### 3. Tipos internos do console ainda sao Sankhya-specific

Isso foi mantido para evitar refatoracao mais profunda e risco funcional desnecessario nesta etapa.

### 4. Textos de provider atual ainda aparecem como dado fixo em pontos de backoffice

O backoffice continua informando Sankhya como provider atual conectado, o que e compativel com o escopo, mas ainda nao e uma leitura dinamica e plenamente provider-agnostic.

## Proximos passos recomendados para Fase B

- mover os contratos de consumo da UI para tipos ERP-generic compartilhados;
- reduzir a dependencia dos componentes internos em nomes `Sankhya*`;
- avaliar uma superficie HTTP ERP-generic apenas na borda consumidora, reaproveitando o runtime oficial;
- manter rotas Sankhya como compatibilidade enquanto a UI e eventuais hooks migram;
- revisar textos e dados de provider para leitura mais dinamica do `provider_definition`.

## Comandos executados

```bash
sed -n '1,260p' /home/borgus/.codex/skills/agrosaas-frontend-web/SKILL.md
sed -n '1,260p' docs/architecture/agrosaas-engineering-playbook.md
rg -n "SankhyaConsole|SankhyaTimeline|type Sankhya|ERP atual: Sankhya|/integracoes/sankhya" apps/web/src/components/integracoes apps/web/src/app/'(dashboard)'/dashboard/settings/integracoes/erp apps/web/src/app/'(dashboard)'/dashboard/backoffice/integracoes/erp
sed -n '330,760p' apps/web/src/components/integracoes/sankhya-console.tsx
sed -n '1,420p' 'apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx'
npm run typecheck
git diff --check
```

## Validacoes realizadas

- `npm run typecheck` executado com sucesso em `apps/web`;
- `git diff --check` executado com sucesso;
- nenhuma alteracao de backend foi realizada;
- nenhum endpoint foi trocado;
- o comportamento funcional da UI foi preservado.
