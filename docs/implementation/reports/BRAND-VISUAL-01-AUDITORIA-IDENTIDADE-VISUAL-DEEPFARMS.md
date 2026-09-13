# BRAND-VISUAL-01 — Auditoria e Plano de Identidade Visual DeepFarms

## 1. Resumo executivo

A plataforma já publica a marca textual DeepFarms, mas ainda combina texto novo com assets gráficos históricos AgroSaaS. Não foi encontrado no repositório um pacote de identidade DeepFarms nomeado, completo e com evidência de aprovação formal.

O cenário é **C — NÃO**: não existe hoje identidade visual DeepFarms suficientemente completa e claramente aprovada para implantação. A próxima fase deve receber assets aprovados; não deve redesenhá-los nem inferir aprovação pelo uso de um SVG existente.

## 2. Inventário de assets

| Asset | Tipo / dimensões | Marca/origem aparente | Consumidores | Situação |
|---|---|---|---|---|
| `apps/web/public/logos/agrosaas-mark.svg` | SVG, `viewBox 100x100` | AgroSaaS pelo nome; mark geométrico sem texto | landing, cadastro e layout de autenticação | SUBSTITUIR após asset aprovado; MANTER TEMPORARIAMENTE até cache/rollback |
| `apps/web/src/app/icon.svg` | SVG, `viewBox 100x100` | Sem nome de marca; hash idêntico ao mark AgroSaaS | ícone metadata padrão do Next/Web | REVISAR |
| `apps/campo/public/icon.svg` | SVG, `viewBox 100x100` | Sem nome de marca; hash idêntico ao mark AgroSaaS | asset público potencial; não consta no manifest atual | REVISAR |
| `apps/campo/public/AgroSaaS-icone.webp` | WebP, 5.470 bytes | AgroSaaS pelo nome | tela de ativação Campo; precache do SW gerado | SUBSTITUIR após asset aprovado; MANTER TEMPORARIAMENTE |
| `apps/campo/public/icon-192.webp` | WebP, declarado 192x192 | origem visual não comprovada | manifest PWA | REVISAR |
| `apps/campo/public/icon-512.webp` | WebP, declarado 512x512 | origem visual não comprovada | manifest PWA | REVISAR |
| `apps/campo/public/icon-192.png` | PNG, 192x192 | origem visual não comprovada | precache; não é ícone declarado no manifest | REVISAR |
| `apps/campo/public/icon-512.png` | PNG, 512x512 | origem visual não comprovada | precache; não é ícone declarado no manifest | REVISAR |
| `apps/campo/public/favicon.ico` | ICO, 30x32 | origem visual não comprovada | favicon Campo; precache | REVISAR |
| `apps/web/public/images/login-bg.png` | JPEG nomeado `.png`, 1024x1024 | imagem de ambientação, não logo | layouts de autenticação/cadastro | MANTER TEMPORARIAMENTE; não há marca textual identificada no código |
| `apps/web/public/images/coffee_farm_cover.png` | JPEG nomeado `.png`, 1024x1024 | imagem de rastreabilidade, não logo | página pública `/p/rastreabilidade/[token]` | MANTER |
| `apps/web/public/icons/field-grid.svg` | SVG, `viewBox 64x64` | ícone funcional sem marca textual | asset público, sem consumidor encontrado por referência literal | REVISAR |

Arquivos `.xcf` no Campo são fontes de edição históricas dos ícones e não são consumidos diretamente pela aplicação; classificam-se como **HISTÓRICO/REVISAR**, sem remoção nesta fase.

## 3. Mapa asset → consumidor

| Asset | Consumidor | Contexto |
|---|---|---|
| `agrosaas-mark.svg` | `apps/web/src/app/page.tsx` | landing, com texto DeepFarms |
| `agrosaas-mark.svg` | `apps/web/src/app/(auth)/register/page.tsx` | cadastro, logo e watermark |
| `agrosaas-mark.svg` | `apps/web/src/components/auth/auth-layout.tsx` | login/autenticação, desktop, mobile e watermark |
| `AgroSaaS-icone.webp` | `apps/campo/src/app/(auth)/activate/page.tsx` | ativação de dispositivo Campo |
| `icon-192.webp`, `icon-512.webp` | `apps/campo/public/manifest.json` | PWA instalável Campo |
| `icon-*.png`, `icon.svg`, favicon, `AgroSaaS-icone.webp` | `apps/campo/public/sw.js` gerado | precache PWA; não editar manualmente |
| `apps/web/src/app/icon.svg` | convenção `app/icon.svg` do Next | favicon/ícone Web gerado pelo framework |
| `login-bg.png` | cadastro e `AuthLayout` | fundo visual da autenticação |
| `coffee_farm_cover.png` | página pública de rastreabilidade | capa ilustrativa |

Não foram encontradas referências a imagens externas, imagens inline de logo, nem URLs de logo nos templates de e-mail.

## 4. Assets AgroSaaS ainda visíveis

1. O mark em `agrosaas-mark.svg` aparece ao lado do texto DeepFarms na landing, cadastro e autenticação, criando a combinação visual inconsistente “logo antigo + texto novo”.
2. `AgroSaaS-icone.webp` aparece na ativação Campo, embora o texto alternativo já seja DeepFarms Campo.
3. O service worker precacheia o ícone de ativação antigo por ser gerado a partir dos assets públicos.
4. O endereço operacional `contato@agrosaas.com.br` permanece no rodapé da landing; é configuração/compatibilidade operacional, fora do escopo visual desta auditoria.

## 5. Assets DeepFarms existentes

Não há arquivo visual com nome DeepFarms. O SVG `apps/web/src/app/icon.svg` e `apps/campo/public/icon.svg` é byte a byte idêntico a `apps/web/public/logos/agrosaas-mark.svg`. Isso demonstra reaproveitamento técnico do mesmo mark, mas não comprova que ele seja o logo DeepFarms aprovado.

Os textos DeepFarms em metadata, manifest, autenticação, landing e e-mails estão corretos, mas são identidade textual, não um pacote gráfico aprovado.

## 6. Logo principal

O logo gráfico principal de fato é o `agrosaas-mark.svg`, usado em superfícies públicas e de autenticação. Dashboard/sidebar/topbar usam principalmente nome do tenant ou texto/fallback DeepFarms; não há outro logo gráfico principal localizado nesses componentes.

O futuro asset de mark deve substituir o consumidor atual por caminho novo, preservando o arquivo antigo na primeira implantação para cache, rollback e versões PWA instaladas.

## 7. Favicon e metadata

Web possui `apps/web/src/app/icon.svg`, automaticamente usado pela convenção Next, mas ele é o mesmo mark histórico e precisa de revisão visual. A metadata Web contém título/descrição DeepFarms, porém não declara `icons`, `openGraph`, `twitter` ou `og:image` explícitos.

Campo possui metadata e manifest textual DeepFarms Campo. O manifest declara somente `icon-192.webp` e `icon-512.webp`, com `type: image/png` apesar de os arquivos serem WebP: inconsistência a revisar na futura fase visual. Não há `apple-touch-icon`, screenshots ou atalhos PWA configurados.

## 8. Campo / PWA

- Nome do manifest: `DeepFarms Campo` — **JÁ DEEPFARMS**.
- Título do layout: `DeepFarms Campo` — **JÁ DEEPFARMS**.
- Ícone da ativação: `AgroSaaS-icone.webp` — **SUBSTITUIR** futuramente.
- Ícones do manifest/favicons: origem e aprovação visual não comprovadas — **REVISAR**.
- `apps/campo/public/sw.js`: artefato gerado, contém URLs de todos os ícones no precache — **MANTER TEMPORARIAMENTE**, regenerar apenas pelo build após alterar fontes.

## 9. E-mail

Os templates são textuais/HTML/CSS. Não possuem `<img>`, logo externo ou imagem inline. O cabeçalho e rodapé de `base.html`, templates de fluxo e assuntos já usam DeepFarms. O fallback `SMTP_FROM_NAME` continua operacional/protegido e não será alterado por uma fase visual.

## 10. PDF / XLSX / documentos

`core/utils/pdf_generator.py` apresenta título textual DeepFarms, sem asset gráfico. `operacional/services/frota_export_service.py` grava DeepFarms nos metadados XLSX, sem imagem. O DANFE usa dados do emitente e não incorpora logo gráfico de plataforma. O exportador de caderno importa `ReportLab Image`, mas não há chamada `RLImage(...)` encontrada; não há logo de plataforma incorporado.

Documentos novos não exigem asset visual nesta fase; documentos históricos permanecem intocados.

## 11. Open Graph / compartilhamento

Não foram encontradas declarações de `openGraph`, `og:image`, `twitter:image` ou imagem social em Web/Campo/API. Não há social preview de marca a substituir atualmente. Caso seja introduzido em fase futura, requer uma imagem aprovada separada.

## 12. Classificação consolidada

| Classificação | Itens |
|---|---|
| SUBSTITUIR | `agrosaas-mark.svg` em seus consumidores; `AgroSaaS-icone.webp` na ativação Campo |
| MANTER TEMPORARIAMENTE | assets AgroSaaS atuais e URLs no precache durante a primeira janela de cache/rollback |
| REMOVER FUTURAMENTE | somente os assets AgroSaaS após confirmação de ausência de consumidores e expiração da janela de cache PWA |
| JÁ DEEPFARMS | textos Web/API/e-mail/PDF/XLSX; nome/metadata Campo |
| REVISAR | `icon.svg`, `icon-192.*`, `icon-512.*`, `favicon.ico`, `field-grid.svg`, fontes `.xcf`, correção MIME do manifest |
| HISTÓRICO | fontes `.xcf`, documentos e relatórios históricos; não reescrever |

## 13. Identidade existente

**Classificação: C — NÃO.**

Não há evidência de um pacote visual DeepFarms oficial, aprovado e completo. O mark geométrico existente pode ser uma base histórica, mas não é suficiente para inferir autorização de uso como nova identidade.

## 14. Pacote mínimo de assets necessário

Somente após aprovação de design, o pacote mínimo efetivamente demandado pelo código é:

| Asset solicitado | Formato/finalidade | Consumidor futuro |
|---|---|---|
| `deepfarms-mark.svg` | SVG vetorial, transparente, versão do símbolo | landing, login, cadastro, favicon Web e watermark |
| `deepfarms-campo-activation.webp` | WebP quadrado, transparência/fundo conforme design aprovado | ativação Campo |
| `icon-192.webp` e `icon-512.webp` aprovados | WebP 192x192 e 512x512 | manifest Campo/PWA |
| `favicon.ico` aprovado | ICO multi-resolução | Campo/browser legado |

Se o mark aprovado não for adequado para favicon/PWA, incluir também versões raster PNG 192x192 e 512x512 e um favicon ICO derivados pelo design. Não é necessário solicitar logo horizontal, Apple touch icon ou social-preview enquanto o código não os consome; estes só devem ser adicionados mediante decisão de produto.

## 15. Estratégia mínima de implementação futura

1. Receber e registrar aprovação formal dos assets DeepFarms.
2. Adicionar novos arquivos com nomes novos; não substituir bytes de assets AgroSaaS existentes.
3. Alterar somente os consumidores mapeados para os novos caminhos.
4. Ajustar manifest para tipo MIME coerente com o formato aprovado.
5. Manter assets antigos e não editar `sw.js` manualmente.
6. Rebuild Web e Campo; o build Campo deve regenerar o SW/precache.
7. Validar cache de PWA, favicon, landing, autenticação e ativação Campo.
8. Em fase posterior, após janela de cache/rollback, auditar consumidores novamente antes de remover assets antigos.

## 16. Testes necessários para implementação

- Web: typecheck, lint, build; landing, login, cadastro, dashboard/sidebar/topbar, favicon e páginas públicas.
- Campo: typecheck, lint, build; manifest, ativação, ícones, instalação PWA e SW gerado normalmente.
- Visual: conferir contraste, transparência, tamanhos e ausência de “logo antigo + texto novo”.
- Regressão: busca residual por caminhos de assets AgroSaaS; confirmar que identificadores técnicos protegidos não foram alterados.

## 17. Impacto de deploy futuro

| Componente | Impacto |
|---|---|
| Web rebuild/restart | SIM |
| Campo rebuild/restart | SIM |
| API restart | NÃO, salvo se forem introduzidos assets servidos pela API (não previsto) |
| Worker / Outbox | NÃO |
| Banco / migration | NÃO |
| DNS / SSL / Nginx / storage | NÃO |

## 18. Riscos

- trocar ou remover o asset antigo imediatamente pode quebrar cache de PWA e rollback;
- substituir arquivos no mesmo caminho sem versionamento explícito dificulta invalidação de cache;
- usar o SVG existente como “DeepFarms” sem aprovação pode perpetuar uma identidade não oficial;
- o MIME WebP declarado como PNG no manifest deve ser resolvido com cuidado e validado por instalação real de PWA.

## 19. Veredicto

**BRAND-VISUAL-01 — STATUS: GO COM RESSALVAS**

Há um plano mínimo, não destrutivo e consumidores claramente mapeados. A implementação visual pode começar somente após o fornecimento/aprovação explícita dos assets DeepFarms. Nenhum asset foi criado, alterado, renomeado ou removido nesta fase.
