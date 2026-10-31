# AGRO-MVP-RELEASE-01 — Verificação de publicação

**Data:** 2026-10-30  
**Escopo:** `apps/agro` e as dependências de API/configuração usadas pelo Agro PWA. Não houve acesso a banco de produção, execução de seeds ou deploy.

## Veredicto

**GO COM RESSALVAS.** A revisão estática, testes unitários, lint, typecheck e build passaram. Antes da publicação, precisam ser confirmados no ambiente Hostinger dois requisitos de configuração que não podem ser validados localmente: uma rota efetiva do PWA à API e um provedor meteorológico autorizado e habilitado. Sem eles, a tela de clima não tem garantia de fornecer dados em produção. O E2E não forneceu uma homologação confiável: 16 passaram, 12 falharam e 1 foi interrompido, em sua maioria por timeout de `networkidle` mesmo após `load`.

## Funcionalidades verificadas

| Área | Evidência e resultado | Classificação |
|---|---|---|
| Clima atual e previsão | `apps/agro/src/lib/clima/previsao.ts` consome `/api/v1/public/clima/previsao`, trata cache, validade, falhas e dados ausentes. A tela apresenta condições atuais e previsões horária/diária. A API limita a previsão diária a até 3 dias (`services/api/public_clima/service.py`), compatível com a indicação da interface. Os componentes não exibem risco de doença nem alerta fitossanitário não homologado; `probabilidadeChuvaPct` se refere à chuva. | NÃO BLOQUEADOR no código; configuração meteorológica é condição de publicação. |
| Provedores meteorológicos | O orquestrador usa configuração dinâmica do banco e credenciais armazenadas com fallback para configuração da aplicação. O caminho padrão habilita WeatherAPI, mas `weatherapi_enabled=False` e chave vazia por padrão (`services/api/core/config.py`). WeatherAPI exige habilitação e chave; OpenWeather/Open-Meteo também passam por verificações de credenciais/licença e limites. Os caminhos de quota/fallback estão implementados. Não inspecionamos as configurações da Hostinger nem confirmamos contrato/licença/limites efetivos lá. | **BLOQUEADOR CONDICIONAL:** confirmar pelo menos um provedor autorizado, habilitado e dentro da quota antes de anunciar clima funcional. |
| Mercado e cotações | `apps/agro/src/app/mercado/page.tsx` separa indicadores e preços. Fontes e data/unidade são informadas; cotações dinâmicas ausentes são indicadas como indisponíveis, com fontes oficiais para consulta. Fluxo possui estados de carregamento, indisponibilidade e atualização parcial. Não foram consultadas fontes reais durante esta revisão. | NÃO BLOQUEADOR; falha de fonte é comunicada sem inventar cotação. |
| Calculadoras | Cinco calculadoras estão disponíveis na tela `/calculadoras`; lógica e interface cobertas pelos testes Vitest. | NÃO BLOQUEADOR. |
| PWA | `src/app/manifest.ts` gera manifesto standalone e ícones existentes; `public/sw.js` define app shell, fallback offline e não intercepta `/api/`; layout registra o service worker. Requer HTTPS em produção para instalação/Service Worker. | NÃO BLOQUEADOR no artefato; HTTPS é condição normal da publicação PWA. |
| Comunicação com API | URLs são produzidas por `apps/agro/src/lib/api-url.ts` com `NEXT_PUBLIC_AGRO_API_ORIGIN`, vazio por padrão, usando caminho same-origin. `apps/agro/next.config.ts` cria rewrite apenas quando `AGRO_API_INTERNAL_ORIGIN` está definido (em dev há fallback para localhost). O build desta verificação, sem variável de produção, gerou manifest de rotas sem rewrites. Portanto, produção precisa configurar a origem pública no build ou oferecer proxy same-origin; se usar rewrite Next, definir a origem interna no build e garantir que o container Next consiga alcançá-la. | **BLOQUEADOR CONDICIONAL:** validar uma rota API funcional no domínio publicado. |

### Segurança fitossanitária

Busca no código do Agro PWA não encontrou consumidor de risco de doenças ou favorabilidade fitossanitária. Os cartões do clima exibem meteorologia e aviso de uso informativo; a probabilidade apresentada é de chuva. A ausência de regras homologadas no backend não se transforma em alerta operacional no Agro PWA.

## Verificações executadas

Executadas no diretório `apps/agro`:

- `pnpm test` — **PASS**, 12 arquivos, 161 testes.
- `pnpm typecheck` — **PASS**.
- `pnpm lint` — **PASS**.
- `pnpm build` — **PASS**, rotas principais, manifesto e páginas estáticas geradas.
- Playwright direcionado a clima, mercado/PTAX e PWA/calculadoras — **inconclusivo**, 16 passaram, 12 falharam e 1 foi interrompido. Os erros recorrentes expiraram em `page.waitForLoadState("networkidle")`; os logs registram `commit`, `domcontentloaded` e `load`. Uma falha adicional no fixture de mercado decorre do próprio fixture abortar a requisição de recuperação que o teste espera concluir. Como o E2E completo não passou, PWA/fluxos de browser não ficam homologados por esta rodada. Isso não foi tratado como falha funcional comprovada do produto.

O build foi gerado sem `AGRO_API_INTERNAL_ORIGIN` ou `NEXT_PUBLIC_AGRO_API_ORIGIN` de produção. A ausência de rewrite nesse build é observável em `.next/routes-manifest.json`; não significa que o proxy externo da Hostinger esteja ausente, pois essa configuração não foi inspecionada.

## Bloqueadores reais e correções indispensáveis

Não foi identificado defeito de código que justifique alteração nesta etapa. Há dois **bloqueadores condicionais de publicação**, dependentes de configuração que não está no repositório:

1. **API:** assegurar que o navegador consiga acessar os endpoints `/api/v1/...` no domínio Agro — por proxy same-origin, ou por `NEXT_PUBLIC_AGRO_API_ORIGIN`; se a aplicação Next encaminhar internamente, configurar `AGRO_API_INTERNAL_ORIGIN` no build. Validar clima e mercado após a configuração.
2. **Clima:** habilitar e validar ao menos um provedor autorizado, com credenciais, licença aplicável e limites/quota configurados. O padrão local não fornece uma chave WeatherAPI e a integração pode recusar provedores sem autorização pública. Sem essa condição, previsão pode resultar indisponível (inclusive HTTP 503).

Não alterar código ou infraestrutura nesta revisão. Mercado degrada para indisponibilidade explícita e, portanto, não é bloqueador por si só. A falta de resposta positiva no E2E recomenda smoke de browser pós-configuração; os timeouts atuais não demonstram falha funcional, mas também não substituem essa verificação.

## Resultado e ressalvas

- Nenhum arquivo de aplicação foi alterado. Este relatório é o único arquivo novo da tarefa.
- Não houve conexão a bancos, alteração de configuração Hostinger, integração meteorológica, seed ou deploy.
- **Publicação:** GO COM RESSALVAS, condicionada à confirmação da rota API e do provedor meteorológico autorizado no ambiente Hostinger, seguida de smoke de clima, mercado, calculadoras e instalação PWA em HTTPS.
- **Reconstrução da imagem:** não é necessária por esta auditoria, já que não houve mudança no código. Caso sejam alteradas variáveis `NEXT_PUBLIC_*` ou `AGRO_API_INTERNAL_ORIGIN`, reconstruir a imagem Next, pois esses valores são incorporados ao build.
