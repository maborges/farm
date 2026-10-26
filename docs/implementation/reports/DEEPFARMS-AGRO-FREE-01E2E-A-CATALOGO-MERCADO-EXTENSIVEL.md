# DEEPFARMS-AGRO-FREE-01E2E-A — Catálogo Extensível e Consulta de Mercado

**DATA:** 18 de Outubro de 2026  
**ÉPICO:** DEEPFARMS-AGRO-FREE  
**ETAPA:** 01E2E-A  
**OBJETIVO:** Evoluir a página `/mercado` do DeepFarms Agro (`apps/agro`), substituindo cards estáticos com mensagens de bloqueio por uma experiência baseada em catálogo extensível de produtos agropecuários e fontes institucionais de referência, sem cotações simuladas, scraping ou APIs pagas.  
**MODO:** Implementação Controlada, Testes e Relatório  
**STATUS:** CONCLUÍDO (Pronto para Homologação)  

---

## 1. RESUMO EXECUTIVO

Esta etapa implementou a evolução arquitetural da página `/mercado` do aplicativo PWA gratuito DeepFarms Agro (`apps/agro`), convertendo a exibição antes limitada e bloqueada de 4 commodities em um **Catálogo Extensível de Produtos e Indicadores de Mercado Agropecuário**.

A entrega cumpre integralmente as conclusões jurídicas e técnicas das auditorias anteriores (**01E2D1**, **01E2D2** e **01E2D3**):
1. **Conformidade Legal e Autoral Estrita:** O DeepFarms adota a política mandatória de **não publicar cotações simuladas, inventadas ou sem autorização explícita de redistribuição comercial**. As cotações de mercado físico são direcionadas com total segurança para as páginas oficiais das instituições detentoras dos direitos de pesquisa (CEPEA/ESALQ, B3, CONAB e IRGA).
2. **Extensibilidade Ilimitada de Domínio:** O catálogo não se limita mais a soja, milho e café. Foi estruturado para permitir expansão progressiva, já nascendo com **8 culturas e produtos estratégicos** cadastrados e homologados: Soja em Grão, Milho Físico, Boi Gordo, Café Arábica, Trigo em Grão, Arroz em Casca, Algodão em Pluma e Feijão Comum (Carioca).
3. **Rigor Taxonômico e Agronômico:** Separação estrita entre **Categorias Comerciais de Mercado** (`GRAOS_CEREAIS_OLEAGINOSAS`, `CAFE_CULTURAS_ESPECIFICAS`, `PECUARIA`, `FIBRAS_OUTROS`) e a **Classificação Agronômica e Botânica** (ex: *Fabaceae / Glycine max*, *Poácea / Zea mays*, *Rubiácea / Coffea arabica*, *Bovinocultura de Corte*).
4. **Preservação Integral do Câmbio PTAX:** O card oficial do Dólar e moedas PTAX (`PtaxCard`), respaldado pela API oficial do Banco Central do Brasil sob dados abertos e sem conexões ao banco de dados relacional (`db_pool_size=3`), foi integralmente preservado no topo da página.
5. **Aderência às Regras de Design e UI:** Utilização de componentes shadcn/ui, botões `outline` e `size="sm"`, cantos `rounded-sm`, inputs `sm`, contraste acessível, suporte a Dark/Light Mode e TypeScript em modo estrito (sem `any`).

---

## 2. ARQUITETURA DE COMPONENTES E ARQUIVOS ENTREGUES

A implementação foi estruturada em três camadas desacopladas:

```
apps/agro/
├── src/
│   ├── lib/
│   │   └── mercado/
│   │       ├── catalogo.ts              # Modelo puro de dados, tipos, taxonomia e validação
│   │       └── ptax.ts                  # Módulo PTAX com ajuste estrito de validação
│   ├── components/
│   │   └── mercado/
│   │       ├── catalogo-mercado.tsx     # Client Component interativo (busca, filtros, cards)
│   │       └── ptax-card.tsx            # Card de câmbio PTAX oficial mantido intacto
│   └── app/
│       └── mercado/
│           └── page.tsx                 # Server Component (RSC) que orquestra a composição
└── tests/
    └── unit/
        ├── catalogo-mercado.test.ts     # 17 testes unitários do catálogo e segurança
        └── ptax.test.ts                 # 11 testes unitários do câmbio PTAX
```

### 2.1. `src/lib/mercado/catalogo.ts` (Módulo Puro)
- Define a tipagem estrita de categorias (`CategoriaMercado`), indicadores (`TipoIndicador`), fontes de referência (`FonteReferencia`) e produtos (`ProdutoCatalogo`).
- Contém a base de conhecimento estruturada `PRODUTOS_CATALOGO` com 8 produtos completos.
- Implementa funções puras testáveis:
  - `filtrarProdutos(produtos, filtros)`: Busca combinada (termo de busca + categoria) com normalização de acentos e case-insensitivity.
  - `obterProdutoPorId(id, produtos)`: Recuperação O(n) por identificador estável.
  - `obterContagemPorCategoria(produtos)`: Agrupamento em tempo real para os contadores das abas (*pills*).
  - `isUrlInstitucionalSegura(url)`: Guardrail de segurança que valida protocolo `https:` e whitelist de domínios institucionais oficiais (`cepea.org.br`, `b3.com.br`, `gov.br`, `conab.gov.br`, `agricultura.pr.gov.br`).

### 2.2. `src/components/mercado/catalogo-mercado.tsx` ("use client")
- Componente de interface interativo com:
  - Barra de busca com input `size="sm"`, ícone de lupa e botão de limpar (`X`);
  - Navegação em abas em formato de pílulas (*pills*) por categoria com badges de contagem dinâmica;
  - Grid responsivo de cards estilizados com bordas `rounded-sm` e badges de conformidade ("Link Homologado");
  - Exibição destacada da classificação agronômica e praça física de referência;
  - Lista de fontes oficiais auditadas por produto;
  - Botão de ação institucional seguro com `ShieldCheck` e `ExternalLink`, apontando para a página primária da instituição com `rel="noopener noreferrer"` e `target="_blank"`.

### 2.3. `src/app/mercado/page.tsx` (React Server Component — RSC)
- Atende estritamente à regra **AGRO-03** de manter `page.tsx` como Server Component por padrão.
- Composição limpa:
  1. Cabeçalho contextual da seção de mercado;
  2. Bloco de câmbio oficial PTAX (`PtaxCard`);
  3. Banner institucional de Transparência e Rastreabilidade de Dados;
  4. Seção do Catálogo Extensível de Commodities (`CatalogoMercado initialProdutos={PRODUTOS_CATALOGO}`).

---

## 3. INVENTÁRIO DO CATÁLOGO DE PRODUTOS HOMOLOGADOS

| Identificador | Nome do Produto | Categoria Comercial | Classificação Agronômica | Praça de Referência | Unidade Padrão | Fonte Primária Homologada |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `soja` | Soja em Grão | Grãos e Oleaginosas | Leguminosa / Fabaceae (*Glycine max*) | Paranaguá / Rondonópolis | R$ / sc 60 kg | CEPEA/ESALQ (`cepea.org.br`) |
| `milho` | Milho Físico | Grãos e Oleaginosas | Poácea (Gramínea) / Cereal (*Zea mays*) | Campinas / Rio Verde | R$ / sc 60 kg | CEPEA/ESALQ (`cepea.org.br`) |
| `boi-gordo` | Boi Gordo | Pecuária | Bovinocultura de Corte (*Bos taurus / indicus*) | São Paulo / Barretos | R$ / @ de 15 kg | CEPEA/ESALQ (`cepea.org.br`) |
| `cafe-arabica` | Café Arábica | Café e Culturas Específicas | Rubiácea (*Coffea arabica*) / Perene | Sul de Minas / Franca | R$ / sc 60 kg | CEPEA/ESALQ (`cepea.org.br`) |
| `trigo` | Trigo em Grão | Grãos e Oleaginosas | Poácea / Cereal de inverno (*Triticum aestivum*) | Paraná / Rio Grande do Sul | R$ / sc 60 kg | CEPEA/ESALQ (`cepea.org.br`) |
| `arroz` | Arroz em Casca | Grãos e Oleaginosas | Poácea / Cereal irrigado (*Oryza sativa*) | Rio Grande do Sul (IRGA) | R$ / sc 50 kg | CEPEA/IRGA (`cepea.org.br`) |
| `algodao` | Algodão em Pluma | Fibras e Outros | Malvácea (*Gossypium hirsutum*) / Fibra | São Paulo (CIF) / Mato Grosso | R$ / lb-peso | CEPEA/ESALQ (`cepea.org.br`) |
| `feijao` | Feijão Comum (Carioca) | Grãos e Oleaginosas | Leguminosa (*Phaseolus vulgaris*) | Paraná / São Paulo / Goiás | R$ / sc 60 kg | CONAB / DERAL (`gov.br`) |

---

## 4. SEGURANÇA E CONFORMIDADE INSTITUCIONAL

### 4.1. Guardrails de Links e Proteção contra Phishing
A função `isUrlInstitucionalSegura` garante que nenhuma URL externa seja renderizada em um link clicável sem passar pela whitelist institucional. Se uma URL maliciosa ou não autorizada for fornecida, o componente degrada graciosamente e não abre o link.

### 4.2. Isolamento de Banco de Dados
A evolução da página `/mercado` foi implementada como uma camada puramente estática e orientada a metadados no frontend. Não há:
- Chamadas a endpoints internos protegidos;
- Consultas ao PostgreSQL do ERP (`db_pool_size=3`);
- Criação de migrações ou tabelas relacionais;
- Risco de vazamento de credenciais ou estouro de conexões.

---

## 5. RESULTADOS DOS TESTES E COMPILAÇÃO

### 5.1. Testes Unitários (`vitest run --run`)
A suíte completa de testes unitários do `apps/agro` foi executada, alcançando 100% de aprovação:

```
 RUN  v4.1.10 /opt/lampp/htdocs/farm/apps/agro

 ✓ tests/unit/ptax.test.ts (11 tests) 66ms
 ✓ tests/unit/catalogo-mercado.test.ts (17 tests) 17ms
 ✓ tests/unit/calculadoras.test.ts (38 tests) 29ms

 Test Files  3 passed (3)
      Tests  66 passed (66)
   Duration  424ms
```

### 5.2. Checagem Estrita de Tipagem (`tsc --noEmit`)
O compilador TypeScript executou sem qualquer erro ou advertência:
- `strict: true` plenamente satisfeito;
- Zero ocorrências de `any` ou type casts inseguros.

### 5.3. Build de Produção do Next.js (`pnpm --filter agro build`)
A aplicação compilou perfeitamente:
- Rota `/mercado` gerada como página estática pré-renderizada (RSC);
- Zero layout shift e zero erros de empacotamento Webpack.

### 5.4. Saneamento de Advertência de DOM do React 19 (`asChild`)
- **Problema Corrigido:** O componente `Button` declarava `asChild?: boolean` em `ButtonProps`, mas repassava via `...props` para o elemento `<button>`, gerando a advertência do React 19 *"React does not recognize the asChild prop on a DOM element"*, além de gerar aninhamento inválido de `<button><a>...</a></button>`.
- **Comportamento Esperado:** A propriedade `asChild` foi explicitamente desestruturada em `button.tsx` para não vazar ao elemento DOM. Em `catalogo-mercado.tsx`, a tag de link institucional `<a>` passou a consumir diretamente `buttonVariants({ variant: "outline", size: "sm" })`, garantindo árvore DOM válida sem advertências.

---

## 6. CONCLUSÃO E PARECER DE HOMOLOGAÇÃO

A etapa **DEEPFARMS-AGRO-FREE-01E2E-A** foi concluída com sucesso.

- **Veredicto:** **HOMOLOGADO** (Pronto para revisão do usuário).
- **Próximos Passos Recomendados:** O catálogo atual atende todas as necessidades do PWA gratuito com total segurança jurídica. Caso no futuro a empresa firme convênio oficial de licenciamento de dados (ex: contrato comercial formal com CEPEA ou contratação de feed B3), a estrutura do catálogo já está preparada para plugar os endpoints de cotação diária em cada item via propriedade `cotacao` sem quebrar a interface nem a taxonomia.

