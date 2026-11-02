# DeepFarms Agro — PWA Gratuito para Produtores Rurais

Aplicativo web progressivo (PWA) gratuito do DeepFarms, voltado ao produtor rural brasileiro. Oferece ferramentas operacionais autônomas, informações agropecuárias e funcionamento 100% offline.

## Features

### Calculadoras Agrícolas e Homologação PWA (DEEPFARMS-AGRO-FREE-01E1)

**Descrição:**  
Conjunto de 5 ferramentas matemáticas essenciais para a rotina no campo: conversão de sacas/kg/t, conversor de áreas rurais e alqueires regionais, estimativa de frete agrícola, análise de custo por hectare com ponto de equilíbrio (break-even) e conversor geral de grandezas do Sistema Internacional com proteção dimensional.

**Fluxo de Funcionamento:**
1. **Acesso e Pré-Cache:** Ao acessar a rota `/calculadoras` pelo navegador ou PWA instalado, o Service Worker ativa o cache local de todos os scripts e do App Shell.
2. **Seleção de Ferramenta:** O produtor escolhe na barra superior a calculadora desejada:
   - **Sacas, Kg e Toneladas:** Permite definir a massa por saca (padrão 60 kg para soja/milho, 50 kg para café/feijão) e converter instantaneamente quantidades de sacas, quilogramas ou toneladas.
   - **Áreas Rurais:** Converte qualquer medida entre Hectares (10.000 m²), Metros Quadrados (m²), Alqueire Paulista (24.200 m²), Alqueire Mineiro/Goiano (48.400 m²) e Alqueire do Norte (27.225 m²), alertando sobre variações regionais.
   - **Estimativa de Frete:** Informa carga e tarifa negociada (R$/tonelada ou R$/saca) somada a despesas extras (pedágios/seguros), gerando custo total estimado e custos efetivos unitários.
   - **Custo por Hectare e Ponto de Equilíbrio:** A partir de área, custos totais, produtividade e preço de venda informado manualmente, projeta o custo por hectare, resultado operacional e as metas mínimas de preço e produtividade de equilíbrio (Break-Even).
   - **Conversor Geral:** Converte grandezas de Massa, Área, Volume e Comprimento, bloqueando dimensionalmente conversões incompatíveis.
3. **Cálculo Determinístico:** O motor matemático opera de forma puramente local e síncrona. Nenhum dado é enviado para a nuvem.
4. **Resiliência Offline:** O produtor pode utilizar as ferramentas mesmo sem sinal de celular ou em modo avião, com recarregamento garantido via CacheStorage.

### Catálogo Extensível e Consulta de Mercado (DEEPFARMS-AGRO-FREE-01E2E-A)

**Descrição:**  
Painel de consulta de commodities agropecuárias (grãos, café, pecuária, fibras) com filtros por categoria comercial, busca textual por produto/praça e links institucionais certificados para fontes primárias oficiais (CEPEA/ESALQ, B3, CONAB e IRGA), operando em conjunto com o card oficial de câmbio PTAX do Banco Central do Brasil.

**Fluxo de Funcionamento:**
1. **Acesso ao Painel:** O produtor acessa a rota `/mercado`, onde o Server Component (RSC) renderiza o catálogo completo com zero latência de banco de dados e preserva a política estrita de não exibir cotações simuladas ou desautorizadas.
2. **Câmbio PTAX em Tempo Real:** No topo, o componente `PtaxCard` exibe a cotação oficial do Banco Central, histórico intradiário de boletins e suporte a moedas estrangeiras (USD, EUR, etc.), com cache local offline.
3. **Filtros e Busca de Commodities:** O produtor filtra os produtos pelas abas de categorias (*Grãos e Oleaginosas*, *Café e Culturas Específicas*, *Pecuária*, *Fibras e Outros*) ou digita no campo de busca para localizar por nome, praça de referência (ex: Paranaguá, Campinas, Barretos) ou classificação científica botânica (*Glycine max*, *Zea mays*, *Coffea arabica*).
4. **Consulta Segura na Fonte Primária:** Cada card apresenta os metadados auditados e um botão de ação com validação estrita de segurança (`ShieldCheck`), que abre a página oficial da instituição de pesquisa em nova aba (`rel="noopener noreferrer" target="_blank"`), garantindo informação fidedigna com total segurança jurídica autoral.

### UI/UX Adaptativa Multi-Dispositivo (Mobile, Tablet e Desktop)

**Descrição:**  
Motor de detecção determinística de ambiente (`mobile`, `tablet`, `desktop`, modo `standalone` PWA vs navegador e sistema operacional `ios`/`android`/`other`) acoplado ao App Shell adaptativo, conferindo experiência nativa de aplicativo móvel em celulares e tablets sem perder a produtividade em telas desktop.

**Fluxo de Funcionamento:**
1. **Identificação do Ambiente em Tempo de Execução:** O módulo `device-detection` avalia dimensões de viewport, capacidade de toque (`maxTouchPoints` / `pointer: coarse`), assinatura de tablets (incluindo iPadOS sob `MacIntel`) e `display-mode: standalone`.
2. **Adaptação no Celular (`mobile`):**
   - Ativa a **Bottom Navigation Dock** nativa com 5 abas principais (*Início*, *Clima*, *Mercado*, *Calculadoras* e *Conta*), indicador superior de aba ativa e suporte a `safe-area-inset-bottom`.
   - Transforma o cabeçalho superior em uma **App Bar Contextual** com botão nativo de retorno em subpáginas, título do módulo ativo e atalho rápido para o município selecionado.
   - Exibe grade rápida estilo **App Launcher** na tela inicial, seletores horizontais deslizantes (`snap-x`) nas calculadoras e atalhos rápidos de seção no painel de mercado.
   - Converte modais (como o seletor de município) em **Bottom Sheets** nativos com alça de arraste.
3. **Adaptação no Tablet (`tablet`):**
   - Oculta a barra inferior e ativa uma **Navigation Rail** lateral retrátil à esquerda com alvos de toque ampliados, preservando a área útil vertical e horizontal.
4. **Adaptação no Desktop (`desktop`):**
   - Exibe **Sidebar Retrátil** expandida por módulos contratados/operacionais (*Ferramentas de Campo* e *Comunidade & Conta*) combinada com barra de navegação superior e diagnóstico do modo de execução.

## Como Executar

```bash
# Desenvolvimento local
pnpm --filter agro dev

# Testes unitários (Vitest)
pnpm --filter agro test

# Testes de navegador e homologação PWA (Playwright)
pnpm --filter agro test:e2e

# Verificações de qualidade
pnpm --filter agro typecheck
pnpm --filter agro lint
pnpm --filter agro build
```
