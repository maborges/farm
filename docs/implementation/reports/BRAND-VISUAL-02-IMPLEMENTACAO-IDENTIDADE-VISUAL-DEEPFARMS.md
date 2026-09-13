# BRAND-VISUAL-02 — Implementação Controlada da Identidade Visual DeepFarms

## 1. Objetivo

Aplicar a identidade gráfica DeepFarms aprovada nos consumidores visuais ativos mapeados pela BRAND-VISUAL-01, sem alterar domínio, banco, API, infraestrutura ou contratos técnicos. Não foi realizado deploy.

## 2. Baseline

- Pacote fonte autorizado: `DeepFarms-IDENTIDADE-VISUAL-DEFINITIVA.zip`.
- Master imutável: `deepfarms-mark-master.svg`.
- Legados preservados: `apps/web/public/logos/agrosaas-mark.svg`, `apps/campo/public/AgroSaaS-icone.webp`, ícones Campo anteriores e `apps/campo/public/sw.js` antes da regeneração.
- Não houve remoção, migration, alteração de API, SMTP, banco, RDS, DNS, SSL, Nginx ou storage.

## 3. Assets recebidos e verificação

O pacote contém todos os arquivos obrigatórios, incluindo marks/logos positivo e negativo, favicon, ícones PWA, hero e ativação Campo. README e `manifest.json` foram lidos; hashes, tamanhos e dimensões conferiram integralmente.

| Asset instalado | SHA-256 validado | Consumidor |
| --- | --- | --- |
| `deepfarms-mark.svg` | `4b0d75447ffed7e656c823a1aa098f08126cd1eb549c9fbf9ef882f7946be005` | Landing, auth claro, favicon SVG Next |
| `deepfarms-mark-negative.svg` | `45a11434874adc8ed1c24aa5954647d19a7b734235ab1f60abddaaa6ff73d2ef` | Auth/registro em painel escuro |
| `deepfarms-logo.svg` | `5b1fa7d6f40b7e588f0278fa912e3dffb387abbd7f116cf7e8d312036245db3d` | Disponível para consumidor futuro aprovado |
| `deepfarms-logo-negative.svg` | `a55d9ff7f4a1162fa574843ba162f316d2286c1e360b126f30e0fb11bbeb4404` | Disponível para consumidor futuro aprovado |
| `deepfarms-hero.webp` (1774×887) | `39668903ad52480cb4556fa2302d071e3d4900701e6a6cd9d39b20d2181a0720` | Hero da landing |
| `deepfarms-campo-activation.webp` (1080×1920) | `de3520238c28affabb7ae429b4cc9335ff1d487b07608acffac36120a7c5c5a1` | Fundo da ativação Campo |
| `deepfarms-icon-192.webp` (192×192) | `98b91a2d09271e4ab1e73e4e6518fbe75a52d32ab3f4ca2ed54d042d898e8cbd` | Manifest/ativação Campo |
| `deepfarms-icon-512.webp` (512×512) | `b4f7015ff1b0b24acbd4cbe3e955a634bdd2e5420d5bdb4f3e1f7a6a72fe24a4` | Manifest Campo |
| `favicon.ico` | `0bbc789c16e45bada5174c990cdd9f7db45b8c8469c272cc0f029e265f04d15f` | Web e Campo |

## 4. Matriz consumidor → asset

| Consumidor | Asset anterior | Asset novo | Ação |
| --- | --- | --- | --- |
| Landing Web | `agrosaas-mark.svg`; painel ilustrativo | mark e `deepfarms-hero.webp` | Migrado |
| Login/auth Web | `agrosaas-mark.svg` | marks positivo/negativo | Migrado por contraste |
| Cadastro Web | `agrosaas-mark.svg` | marks positivo/negativo | Migrado por contraste |
| Ícone Web | `src/app/icon.svg` histórico | mark DeepFarms e favicon aprovado | Migrado pelo mecanismo nativo Next |
| Ativação Campo | `AgroSaaS-icone.webp` | activation e icon-192 DeepFarms | Migrado |
| Manifest Campo | WebP declarado como PNG | DeepFarms WebP com `image/webp` | Migrado e MIME corrigido |
| Favicon Campo | favicon histórico implícito | favicon aprovado via metadata | Migrado |

## 5. Arquivos adicionados

- `apps/web/public/logos/deepfarms-{mark,mark-negative,logo,logo-negative}.svg`
- `apps/web/public/images/deepfarms-hero.webp`
- `apps/web/src/app/favicon.ico`
- `apps/campo/public/deepfarms-campo-activation.webp`
- `apps/campo/public/deepfarms-{icon-192,icon-512}.webp`
- `apps/campo/public/deepfarms-favicon.ico`

## 6. Arquivos modificados

- Landing, layout de autenticação e cadastro Web: referências dos marks e hero aprovado.
- `apps/web/src/app/icon.svg`: substituído pelo mark oficial, sem alteração de geometria.
- Layout/manifest/ativação Campo: novos assets, título Apple Web App, cor institucional `#006B3D` e MIME WebP correto.
- `apps/campo/public/sw.js`: regenerado exclusivamente pelo `next-pwa` durante o build.

## 7. Legados preservados

Os seguintes permanecem físicos e não receberam novos consumidores:

- `apps/web/public/logos/agrosaas-mark.svg`
- `apps/campo/public/AgroSaaS-icone.webp`
- `apps/campo/public/icon-192.webp`
- `apps/campo/public/icon-512.webp`
- `apps/campo/public/favicon.ico`

O service worker regenerado mantém `AgroSaaS-icone.webp` no precache e também passa a precachear os novos assets DeepFarms. Isso preserva compatibilidade de cache e rollback de PWAs instaladas.

## 8. Validações

| Verificação | Resultado |
| --- | --- |
| Integridade dos assets instalados | PASSOU — hashes idênticos ao manifesto do pacote |
| `pnpm --filter web typecheck` | PASSOU |
| `pnpm --filter web lint` | PASSOU |
| `NODE_OPTIONS=--max-old-space-size=1536 pnpm --filter web build` | PASSOU |
| `pnpm --filter @agro/campo typecheck` | PASSOU |
| `pnpm --filter @agro/campo lint` | PASSOU |
| `pnpm --filter @agro/campo build` | PASSOU; `next-pwa` regenerou `public/sw.js` |
| JSON do manifest Campo | PASSOU |
| `git diff --check` | PASSOU |

O build Campo apresentou apenas o aviso não bloqueante de dados Browserslist desatualizados. Nenhum asset foi alterado durante a cópia: folha, bovino, circuitos, três nós e proporções são os do pacote aprovado.

## 9. Evidência visual

- `deepfarms-hero.webp` foi inspecionado no formato e proporção aprovados e é exibido no painel visual responsivo da landing, mantendo menu, headline e CTAs em HTML/React.
- `deepfarms-campo-activation.webp` foi inspecionado no formato vertical aprovado e aplicado como fundo da ativação; o ícone 192 é usado no cabeçalho.
- As variantes positiva (`#006B3D`) e negativa (`#FFFFFF`) são usadas, respectivamente, nos fundos claro e escuro dos consumidores Web.
- A validação de página completa em navegador local ficou pendente porque a porta 3000 já estava ocupada por processo externo, que foi preservado. Não houve falha de aplicação; build Web e Campo passaram.

## 10. Guardrails e escopo

- Nenhuma migration ou Alembic.
- Nenhuma mudança em banco, RDS, DNS, SSL, Nginx, storage ou systemd.
- Nenhuma alteração de API, workers, outbox, SMTP, PDF/XLSX ou regras de negócio.
- Nenhum identificador técnico protegido foi alterado.
- Não foi criado nem editado manualmente o service worker.
- Não foi feito deploy.

## 11. Riscos e recomendação

O único ponto remanescente é a checagem manual pós-deploy de landing desktop/mobile, login/cadastro, favicon e instalação PWA em dispositivo/navegador real, especialmente por causa de cache de service worker. É uma validação operacional visual, não um bloqueio de build ou integridade.

Recomendação para deploy futuro: rebuild Web e Campo; publicar os novos artefatos; validar cache/PWA. Não requer restart de API, worker, outbox, Nginx, DNS, SSL, banco ou migration.

## 12. Veredicto

**BRAND-VISUAL-02 — STATUS: GO COM RESSALVAS**

Implementação controlada concluída com todos os gates técnicos verdes. A ressalva é exclusivamente a inspeção manual das telas reais após publicação, que não foi executada nesta fase sem deploy.
