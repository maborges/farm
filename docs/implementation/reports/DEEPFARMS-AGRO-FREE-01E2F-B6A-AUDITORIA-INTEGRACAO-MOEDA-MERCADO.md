# Relatório de Auditoria Técnica: Integração dos Preços do Mercado com a Seleção de Moeda

**Identificador:** `DEEPFARMS-AGRO-FREE-01E2F-B6A`  
**Título:** Auditoria de Arquitetura Cambial e Planejamento da Dupla Cotação no Módulo Mercado  
**Data da Auditoria:** 21/10/2026  
**Modelo de Execução:** GPT-5.6 Codex — Sol  
**Nível de Raciocínio:** High  
**Modalidade:** Auditoria técnica somente leitura (sem alteração de código nesta fase)  
**Veredicto:** **GO COM RESSALVAS**  

---

## 1. Sumário Executivo

A presente auditoria técnica e arquitetural foi executada no âmbito da plataforma **DeepFarms Agro** com o propósito de examinar a infraestrutura cambial existente, o seletor de moedas já implementado no aplicativo e planejar a integração harmoniosa, transparente e reativa dos preços públicos de commodities agropecuárias (entregues na fase B5B) com a preferência monetária do produtor rural.

### Conclusões Centrais da Auditoria:
1. **Seletor de Moeda Existente e Mapeamento:** O seletor de moedas já se encontra em produção no frontend (`apps/agro/src/components/mercado/ptax-card.tsx`), suportando **11 moedas internacionais** cotadas oficialmente contra o Real brasileiro pelo Banco Central do Brasil (BCB): USD, EUR, GBP, JPY, CAD, CHF, AUD, CNY, ARS, CLP e ZAR.
2. **Armazenamento e Isolamento Atual de Estado (Lacuna Crítica):** A preferência do usuário é persistida no `localStorage` sob a chave `deepfarms_agro_mercado_moeda_v1`. Contudo, o estado reativo é mantido estritamente em um `useState` local no interior do componente `PtaxCard`. Não existe atualmente barramento de eventos, contexto ou store compartilhado que notifique componentes irmãos (como `CatalogoMercado`) quando o usuário troca a moeda no topo da página.
3. **Inexistência Prévia de Serviço de Conversão Cambial:** A aplicação possui conversores para unidades agronômicas físicas (sacas, kg, toneladas, alqueires, hectares em `apps/agro/src/lib/calculadoras/core.ts`), mas **nenhum serviço ou função de conversão cambial** para produtos agrícolas. Os cards de commodities formatam os valores unicamente em Reais (`BRL`) via `formatarPrecoPublico(valor, moeda)`.
4. **Fonte Oficial Exclusiva:** As taxas de câmbio provêm exclusivamente do **Banco Central do Brasil (BCB)** através da PTAX oficial de fechamento. Para o Dólar (USD), há consumo primário via endpoint local com fallback para a API Olinda do BCB; para as demais 10 moedas, o cliente web consulta diretamente os endpoints OData do BCB (`CotacaoMoedaPeriodo`), com validação rigorosa de integridade e descarte de dados corrompidos.
5. **Diretriz de Dupla Cotação:** O preço oficial em BRL com sua unidade comercial original brasileira (ex: `R$ 123,03 / sc 60 kg`) deve permanecer inalterado como preço primário obrigatório, garantindo a proveniência DERAL/SEAB-PR. A conversão cambial deve ser apresentada como valor equivalente secundário (ex: `≈ US$ 21,82 / sc 60 kg`), calculada estritamente pela PTAX Venda oficial do dia de referência, sem alterar as unidades de medida físicas.
6. **Reatividade Instantânea sem Recarregar Página:** A transição de moeda deve atualizar os 22 cards de commodities em tempo real (0ms para moedas com cotação em cache), sem desmontar a página, sem perda do estado de busca e sem recarregamento de tela (`no page reload`).

---

## 2. Inventário da Implementação Existente de Moeda

### 2.1. Localização do Seletor Existente
O seletor de moeda do DeepFarms Agro está localizado no componente cliente:
- **Arquivo:** `apps/agro/src/components/mercado/ptax-card.tsx` (linhas 151 a 175).
- **Elemento HTML:**
  ```tsx
  <select
    id="ptax-currency"
    aria-label="Moeda para consultar"
    className="min-h-8 rounded-sm border border-border bg-background px-2 py-1 text-xs text-foreground"
    value={currency}
    onChange={(event) => {
      const selected = CURRENCIES.find((item) => item.code === event.target.value)?.code;
      if (!selected) return;
      saveSelectedCurrency(window.localStorage, selected);
      const saved = readSavedCurrencyQuote(window.localStorage, selected);
      setQuote(saved);
      setIntraday([]);
      setState(navigator.onLine ? saved?.estadoDisponibilidade ?? "INDISPONIVEL" : saved ? "OFFLINE" : "INDISPONIVEL");
      setLoading(true);
      setCurrency(selected);
    }}
  >
    <optgroup label="Moedas padrão">
      {CURRENCIES.slice(0, 2).map((item) => <option key={item.code} value={item.code}>{item.name} ({item.code})</option>)}
    </optgroup>
    <optgroup label="Outras moedas">
      {CURRENCIES.slice(2).map((item) => <option key={item.code} value={item.code}>{item.name} ({item.code})</option>)}
    </optgroup>
  </select>
  ```
- **Conformidade com Restrições:** Conforme estabelecido nas restrições da B6A, este é o **único seletor de moeda legítimo** da aplicação no Mercado. É terminantemente proibido criar outro seletor no catálogo de produtos.

### 2.2. Catálogo de Moedas Suportadas
As moedas aceitas pelo sistema estão tipadas e enumeradas na constante `CURRENCIES` em `apps/agro/src/lib/mercado/ptax.ts` (linhas 39 a 53):

| Código ISO | Nome Oficial da Moeda | Símbolo Oficial | Categoria no Seletor | Fonte Oficial de Câmbio |
| :---: | :--- | :---: | :---: | :--- |
| `USD` | Dólar americano | `US$` | Moedas padrão | BCB PTAX Fechamento (API Local / Olinda) |
| `EUR` | Euro | `€` | Moedas padrão | BCB Olinda PTAX / SGS Série 21619 |
| `GBP` | Libra esterlina | `£` | Outras moedas | BCB Olinda OData (`CotacaoMoedaPeriodo`) |
| `JPY` | Iene japonês | `¥` | Outras moedas | BCB Olinda OData (`CotacaoMoedaPeriodo`) |
| `CAD` | Dólar canadense | `CA$` | Outras moedas | BCB Olinda OData (`CotacaoMoedaPeriodo`) |
| `CHF` | Franco suíço | `CHF` | Outras moedas | BCB Olinda OData (`CotacaoMoedaPeriodo`) |
| `AUD` | Dólar australiano | `A$` | Outras moedas | BCB Olinda OData (`CotacaoMoedaPeriodo`) |
| `CNY` | Yuan chinês | `¥` | Outras moedas | BCB Olinda OData (`CotacaoMoedaPeriodo`) |
| `ARS` | Peso argentino | `AR$` | Outras moedas | BCB Olinda OData (`CotacaoMoedaPeriodo`) |
| `CLP` | Peso chileno | `CLP$` | Outras moedas | BCB Olinda OData (`CotacaoMoedaPeriodo`) |
| `ZAR` | Rand sul-africano | `R` | Outras moedas | BCB Olinda OData (`CotacaoMoedaPeriodo`) |

*Nota sobre BRL:* O Real brasileiro é a moeda de referência base (`moedaReferencia: "BRL"`). Os preços de commodities são coletados nativamente em BRL.

### 2.3. Mecanismo de Armazenamento e Compartilhamento Atual
1. **Chaves no `localStorage`:**
   - Preferência da Moeda Ativa: `deepfarms_agro_mercado_moeda_v1` (gerenciada por `readSavedCurrency` e `saveSelectedCurrency`).
   - Cotação em Cache por Moeda: `deepfarms_agro_mercado_cotacao_v1:<currency>` (gerenciada por `readSavedCurrencyQuote` e `saveCurrencyQuote`).
   - Envelope Legado USD: `deepfarms_agro_mercado_ptax_v1` (mantido por compatibilidade).
2. **Como o estado é compartilhado hoje:**
   - **Diagnóstico:** O estado `currency` é mantido exclusivamente no hook `useState<CurrencyCode>("USD")` do componente `PtaxCard`.
   - Quando o usuário altera a seleção no dropdown, `saveSelectedCurrency` atualiza o `localStorage`. Contudo, a API nativa de `localStorage` **não despacha eventos `'storage'` na própria aba/janela** em que a modificação ocorreu.
   - Como resultado, o componente irmão `CatalogoMercado` (`apps/agro/src/components/mercado/catalogo-mercado.tsx`) não é notificado e não re-renderiza seus cards.
   - **Solução Arquitetural Necessária para B6B:** Implementar mecanismo de sincronização via `CustomEvent` ou micro-store reativa (ex: `useSyncExternalStore` ou listener de eventos da janela) para que a alteração no `PtaxCard` reflita instantaneamente no catálogo sem recarregar a página.

---

## 3. Auditoria do Serviço de Conversão Cambial e Fontes de Dados

### 3.1. Estado Atual da Conversão de Valores
- **Ausência de Conversão:** A plataforma atualmente não realiza nenhuma conversão monetária sobre os preços agrícolas. O arquivo `apps/agro/src/lib/mercado/precos.ts` contém apenas:
  ```ts
  export function formatarPrecoPublico(valor: number, moeda = "BRL"): string {
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: moeda,
    }).format(valor);
  }
  ```
  Como todos os 21 preços DERAL possuem `moeda: "BRL"`, a exibição é fixa em Reais.

### 3.2. Provedores de Taxas e Mecânica de Obtenção
1. **Dólar Americano (`USD`):**
   - Rota primária: Requisição HTTP interna a `/api/v1/public/mercado/ptax` (FastAPI + Redis/fallback).
   - Rota de contingência: Requisição direta do navegador para a API de Dados Abertos do BCB (`https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo...`).
2. **Demais Moedas (`EUR`, `GBP`, `JPY`, etc.):**
   - Requisição direta do navegador à API Olinda do BCB (`https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoMoedaPeriodo...`).
   - Todos os dados recebem validação estrita via `parseBcbCurrency()`.

### 3.3. Modelo Matemático da Conversão Cambial
No mercado financeiro internacional e na precificação de exportação agropecuária brasileira:
- A cotação PTAX expressa a quantidade de Reais necessária para comprar ou vender 1 unidade da moeda estrangeira:
  $$\text{Taxa PTAX} = \frac{\text{BRL}}{\text{Moeda}}$$
- Portanto, o preço de uma commodity cotada em Reais equivale a:
  $$\text{Preço na Moeda} = \frac{\text{Preço em BRL}}{\text{Taxa PTAX (Venda)}}$$
- **Convenção de Taxa (Venda vs Compra):** Adota-se a cotação de **Venda** (`cotacaoVenda`) da PTAX de fechamento do BCB, pois é a taxa de referência contábil e contratual estipulada para liquidação e precificação de balanços e paridade de exportação no Brasil.
- **Precisão Numérica:** Arredondamento conforme as diretrizes cambiais padrão (2 casas decimais para moedas ocidentais; 0 casas decimais para JPY e CLP, respeitando a convenção de mercado internacional de câmbio).

---

## 4. Tratamento de Taxas Indisponíveis, Cache e Modo Offline

### 4.1. Ciclo de Resiliência Existente
O subsistema PTAX implementa 4 estados formais de disponibilidade (`EstadoDisponibilidadePtax`):
1. `NORMAL`: Taxa obtida online com sucesso e dentro do período de validade.
2. `OFFLINE`: Navegador desconectado da rede (`!navigator.onLine`). O sistema recupera a cotação salva do `localStorage` e sinaliza o badge *"Modo offline — dado salvo"*.
3. `FONTE_INDISPONIVEL`: Falha de resposta da API do BCB (HTTP 5xx, timeout ou instabilidade de rede). O sistema apresenta a última cotação conhecida válida em cache com a legenda *"Último fechamento conhecido — fonte indisponível"*.
4. `INDISPONIVEL`: Ausência total de dados (primeiro acesso sem rede ou cache vazio/corrompido).

### 4.2. Diretrizes Regulamentares Anti-Alucinação de Preços
Para a integração com os preços de commodities na B6B, devem vigorar as seguintes salvaguardas inegociáveis:
- **Proibição de Taxas Fictícias:** Jamais arbitrar taxas cambiais estáticas ou estimativas inventadas (ex: assumir dólar a R$ 5,00).
- **Tratamento de Indisponibilidade Cambial:** Caso a taxa da moeda selecionada esteja no estado `INDISPONIVEL`:
  - O preço oficial em BRL continua plenamente visível e inalterado.
  - O espaço reservado para a cotação convertida deve apresentar uma indicação discreta e elegante: `(Câmbio indisponível)` ou omitir a cotação convertida até que a taxa seja obtida.
- **Tratamento de Defasagem Temporal:** Quando a cotação utilizada for histórica (proveniente de cache offline ou fim de semana), uma anotação em tooltip ou subtítulo deve deixar explícita a data da taxa utilizada (ex: `Base: PTAX 16/10`).

---

## 5. Auditoria dos Componentes do Módulo Mercado

### 5.1. Topologia da Página `/mercado`
A rota `apps/agro/src/app/mercado/page.tsx` é um Server Component (RSC) estruturado da seguinte forma:
```
apps/agro/src/app/mercado/page.tsx (RSC)
├── <PtaxCard /> (Client Component) -> Contém o seletor <select id="ptax-currency">
├── <IndicadoresMacroCard /> (Client Component)
├── <IbgeProducaoCard /> (Client Component)
└── <CatalogoMercado initialProdutos={produtos} /> (Client Component) -> 22 cards de commodities
```

### 5.2. Ponto de Integração Recomendado
A integração deve ocorrer na fronteira entre `ptax.ts` (mecanismo de dados e persistência) e `catalogo-mercado.tsx` (exibição dos cards):
1. **Emissor (`PtaxCard` / `ptax.ts`):**  
   Ao salvar a moeda e a cotação atualizada, despachar um evento customizado leve:
   ```ts
   window.dispatchEvent(new CustomEvent("deepfarms:moeda-alterada", {
     detail: { currency: selected, quote: savedQuote }
   }));
   ```
2. **Receptor (`CatalogoMercado`):**  
   No `CatalogoMercado`, subscrever ao evento no `useEffect` de inicialização e ler a moeda e cotação já salvas no `localStorage`. Armazenar em estado local `moedaAtiva: CurrencyCode` e `cotacaoAtiva: PtaxPublicaV1 | null`.
3. **Card da Commodity (`catalogo-mercado.tsx`):**  
   Substituir a renderização unicamente em Reais pela **Apresentação Simultânea**.

---

## 6. Desenho da Apresentação Simultânea (Dupla Cotação)

### 6.1. Especificação Visual do Bloco de Preço
Para cada commodity com preço real homologado (21 itens do DERAL), o card deve exibir com hierarquia visual clara:

```
+-----------------------------------------------------------------------+
|  Relógio  Semana 42-2026 (16/10)                 [ DERAL/SEAB-PR ]   |
|                                                                       |
|  R$ 123,03 / saca de 60 kg                 Ref.: 16/10/2026           |
|  ≈ US$ 21,82 / saca de 60 kg (câmbio PTAX)                            |
|                                                                       |
|  Origem: Célula X24 · DERAL/SEAB-PR          SHA: 0f3c5553...         |
+-----------------------------------------------------------------------+
```

### 6.2. Regras de Exibição:
1. **Preço Primário Oficial (Inalterado):**
   - Renderização: `formatarPrecoPublico(precoReal.valor, "BRL")` + ` / ${precoReal.unidade}`.
   - Tipografia: `text-lg font-bold tracking-tight text-foreground`.
   - Propósito: Representa o dado auditado e juridicamente rastreável da fonte primária (DERAL).
2. **Preço Secundário Equivalente (Convertido):**
   - Visibilidade: Exibido sempre que a moeda selecionada for diferente de `BRL` e a taxa estiver disponível.
   - Renderização: `≈ ${formatarPrecoMoeda(precoConvertido, moedaAtiva)} / ${precoReal.unidade}`.
   - Tipografia: `text-xs font-semibold text-emerald-700 dark:text-emerald-400 font-mono`.
   - Se a moeda selecionada for `BRL`: A linha secundária não é exibida, evitando redundância.
   - Se a cotação estiver carregando ou indisponível: Exibir indicador suave `≈ Consultando câmbio...` ou `(Câmbio indisponível)`.
3. **Preservação Irrevogável da Unidade Física:**
   - A unidade permanece estritamente a do levantamento original (`saca de 60 kg`, `arroba de 15 kg`, `kg vivo`, `litro`, `tonelada`).
   - É **proibida** a conversão de unidades agronômicas (ex: converter sacas para bushels de Chicago ou arroba para libras-peso), pois tais conversões introduzem variações de densidade e umidade estranhas ao dado oficial.

---

## 7. Reatividade e Performance sem Recarregar Página

Para cumprir o requisito de atualização reativa sem reload:
1. **Tempo de Resposta 0ms (Cache Hit):**  
   Quando o usuário troca de USD para EUR e a cotação do Euro já foi gravada previamente no `localStorage`, o evento é processado instantaneamente, recalculando todos os 22 cards no mesmo tick do React.
2. **Preservação do Estado de Navegação:**  
   O usuário pode estar com o filtro de busca preenchido (ex: `"soja"`) e navegando em uma categoria específica (ex: `"Grãos e Cereais"`). A troca de moeda não redefine nem altera esses filtros.
3. **Zero Layout Shift (CLS):**  
   O container de preços no card do catálogo deve possuir altura mínima reservada (`min-h-[76px]`) para acomodar a linha secundária de conversão sem saltos visuais na página.

---

## 8. Avaliação de Impactos nos Testes, Acessibilidade e Responsividade

### 8.1. Impactos na Suíte de Testes
- **Testes Unitários (Vitest - `apps/agro/tests/unit/`):**
  - Criação de nova suíte unitária `conversao-cambial.test.ts` (ou acréscimo em `precos.test.ts`):
    - Teste de cálculo exato de conversão BRL -> Moeda Estrangeira utilizando taxa de venda.
    - Teste de arredondamento e formatação para as 11 moedas (incluindo JPY sem decimais e USD com 2 decimais).
    - Teste de tratamento de divisões por zero, taxas negativas, valores NaN ou nulos.
    - Teste de preservação da unidade física.
- **Testes E2E (Playwright - `apps/agro/tests/e2e/mercado-ptax.spec.ts`):**
  - Adição de caso de teste E2E:
    1. Acessar `/mercado`.
    2. Verificar valor em BRL no card de Soja (`R$ 123,03`).
    3. Selecionar `EUR` no dropdown `#ptax-currency`.
    4. Validar que o card de Soja exibe imediatamente `≈ €` sem reload da página.
    5. Validar que a unidade `/ saca de 60 kg` permaneceu idêntica.

### 8.2. Acessibilidade (WCAG 2.1 AA)
- Os valores convertidos devem possuir rótulos semânticos completos para leitores de tela:
  `aria-label="Preço oficial: 123 reais e 3 centavos por saca de 60 quilos. Equivalente aproximado em dólar americano: 21 dólares e 82 centavos por saca de 60 quilos"`
- Contraste cromático mínimo de 4.5:1 mantido tanto no Light Mode quanto no Dark Mode.

### 8.3. Responsividade Mobile (375px)
- Em telas compactas (iPhone SE / 375px), a linha secundária de conversão cambial ajusta-se naturalmente em fluxo vertical logo abaixo do valor em Reais, sem causar overflow horizontal na grade nem colidir com a badge da fonte.

---

## 9. Matriz de Lacunas e Riscos (Gaps & Mitigation)

| ID | Lacuna Identificada | Risco Associado | Mitigação Arquitetural Proposta |
| :---: | :--- | :--- | :--- |
| **GAP-01** | `PtaxCard` isola a moeda em `useState` local sem emitir evento na mesma aba. | Catálogo não reage à troca de moeda pelo usuário. | Disparar `CustomEvent` de janela em `saveSelectedCurrency` e escutar no `CatalogoMercado`. |
| **GAP-02** | Inexistência de função utilitária para cálculo cambial de commodities. | Lógica de cálculo espalhada ou duplicação de regras. | Criar função pura `calcularEquivalenteMoeda(valorBrl, taxaVenda, moeda)` em `apps/agro/src/lib/mercado/precos.ts`. |
| **GAP-03** | Moeda selecionada sem cotação em cache enquanto a rede busca a taxa. | Card exibir NaN ou travar a renderização. | Retornar `null` na função de conversão quando a taxa for inexistente e exibir fallback informativo. |
| **GAP-04** | Risco de conversão indevida de unidades físicas (ex: saca para bushel). | Deturpar o dado oficial DERAL e induzir o produtor a erro. | Travar o sufixo da unidade física estritamente no valor do contrato original (`precoReal.unidade`). |

---

## 10. Plano Mínimo de Implementação (Fase B6B)

A implementação subsequente da fase **DEEPFARMS-AGRO-FREE-01E2F-B6B** deverá executar os seguintes passos atômicos:

1. **Etapa 1 — Funções Utilitárias Cambiais (`apps/agro/src/lib/mercado/precos.ts`):**
   - Implementar `calcularEquivalenteMoeda(valorBrl: number, cotacaoVenda: number | null | undefined): number | null`.
   - Implementar `formatarPrecoMoeda(valor: number, moeda: CurrencyCode): string` com `Intl.NumberFormat`.
2. **Etapa 2 — Barramento Leve de Moeda (`apps/agro/src/lib/mercado/ptax.ts`):**
   - Adicionar emissão de evento de janela `deepfarms:moeda-alterada` em `saveSelectedCurrency` e `saveCurrencyQuote`.
   - Exportar helper de leitura e subscrição reativa `subscribeCurrencyChange()`.
3. **Etapa 3 — Integração do Catálogo (`apps/agro/src/components/mercado/catalogo-mercado.tsx`):**
   - Conectar o hook de escuta da moeda ativa e da respectiva cotação PTAX.
   - Renderizar a dupla cotação nos cards de commodities homologadas.
   - Manter altura fixa/mínima para evitar layout shifts.
4. **Etapa 4 — Cobertura de Testes e Homologação:**
   - Adicionar testes unitários em Vitest para os conversores cambiais.
   - Adicionar teste E2E em Playwright validando a sincronização reativa e não-regressão.

---

## 11. Veredicto Arquitetural Final

### **GO COM RESSALVAS**

**Fundamentação Técnica:**
A integração é perfeitamente viável, limpa e alinhada com as diretrizes de código livre de dependências pagas do DeepFarms Agro. O seletor existente no `PtaxCard` e o ecossistema de dados abertos do Banco Central do Brasil oferecem todas as bases necessárias.

**Ressalvas a Serem Rigorosamente Cumpridas na Fase B6B:**
1. **Ressalva 1 (Seletor Único):** Não criar nenhum outro seletor de moedas no catálogo. O seletor do `PtaxCard` deve permanecer a fonte exclusiva de preferência.
2. **Ressalva 2 (Integridade Física):** Não alterar a unidade de comercialização oficial (manter saca de 60 kg, arroba, etc.).
3. **Ressalva 3 (Tolerância a Falhas):** Se a cotação cambial falhar ou estiver em carregamento, o preço em Reais deve continuar plenamente acessível, sem bloqueios de tela nem valores simulados.
