# Padrão Arquitetural React Server Components (RSC) no AgroSaaS

Este documento consolida o padrão oficial de implementação e migração de páginas do AgroSaaS para a arquitetura **React Server Components (RSC) Shell** no Next.js 15.

---

## 1. Quando usar vs. Quando NÃO usar RSC

### Quando usar RSC (Recomendado)
- **Visualização de Dados e Relatórios**: Telas como dashboards executivos, relatórios de custos ou indicadores que se beneficiam do pré-carregamento no servidor.
- **Listagens e Tabelas**: Páginas com tabelas densas (como `DataTable` ou `AG Grid`) que usam busca, ordenação ou exportação e podem receber os dados iniciais do servidor.
- **Leitura Simples e Painéis de Configurações**: Páginas que consultam poucas APIs de parametrização e não possuem estados locais complexos.

### Quando NÃO usar RSC (Manter ou Usar Client-Only)
- **Telas Altamente Interativas com Mapas**: Páginas que utilizam WebGL, Mapbox, Leaflet ou Google Maps para desenho e manipulação de polígonos/talhões.
- **Editores e Agendadores Visuais**: Calendários interativos complexos (ex: Gantt de planejamento) que dependem de arrastar-e-soltar (drag-and-drop) constante e sincronização imediata de estados do navegador.
- **Aplicações com Funcionalidades PWA/Offline**: Páginas de coleta de dados em campo que exigem sincronização offline baseada em Service Workers e IndexedDB local.

---

## 2. Estrutura Padrão de Componentes

Toda rota migrada para o padrão RSC deve ser dividida em dois arquivos complementares no mesmo diretório:
1. `page.tsx` (Server Component)
2. `[Modulo]Client.tsx` (Client Component)

---

## 3. Padrão `page.tsx` (Server Component)

O arquivo `page.tsx` atua como a "casca" ou shell da página. Ele é responsável exclusivamente por extrair parâmetros de rota, prefetch de dados e repassar os dados de hidratação.

### Regras do `page.tsx`
- **Não utilizar `"use client"`**.
- Tratar argumentos `params` e `searchParams` como assíncronos (Promises) de acordo com o padrão do Next.js 15.
- Realizar requisições utilizando a biblioteca de servidor `apiFetchServer`.
- **Prevenção de Crash (Anti-500)**: Envolver os data-fetchings em um bloco `try/catch` para que falhas de backend (como erros 402 ou 500) não quebrem a renderização da página inteira.
- **Concorrência Otimizada**: Usar `Promise.allSettled` caso a página precise carregar dados de múltiplas origens em paralelo, evitando cascatas (waterfalls) no servidor.

### Exemplo de Código do `page.tsx`
```tsx
import { apiFetchServer } from "@/lib/api-server";
import { MeuModuloClient } from "./MeuModuloClient";
import { MeuModuloData } from "./_components/types";

export default async function MeuModuloPage(props: {
  searchParams: Promise<{ [key: string]: string | undefined }>;
}) {
  const searchParams = await props.searchParams;
  const serverFazendaId = searchParams?.unidade_produtiva_id || "";

  let initialData: MeuModuloData | null = null;

  try {
    const queryParam = serverFazendaId ? `?unidade_produtiva_id=${serverFazendaId}` : "";
    // Pré-carrega de forma segura
    initialData = await apiFetchServer<MeuModuloData>(`/modulo/dashboard${queryParam}`);
  } catch (error) {
    // Registra falha de prefetch sem causar crash 500 na página
    console.error("Failed to prefetch MeuModulo data on server:", error);
  }

  return (
    <MeuModuloClient
      initialData={initialData}
      serverFazendaId={serverFazendaId}
    />
  );
}
```

---

## 4. Padrão `Client.tsx` (Client Component)

O arquivo Client Component (ex: `MeuModuloClient.tsx`) concentra toda a interatividade, gerenciamento de estados locais (filtros, abas), chamadas de modificação (mutations) e a lógica de consulta/sincronização do React Query.

### Regras do Client Component
- **Utilizar `"use client"`** na primeira linha.
- Definir chaves de query e usar `initialData` de forma condicional: apenas usar o `initialData` do servidor se o estado de filtros atual (ex: fazenda ativa) for idêntico ao carregado pelo servidor.
- Centralizar mutations de formulários usando React Hook Form e validações Zod.
- Exibir placeholders e estados amigáveis (`EmptyState` ou `Skeleton`) caso `initialData` falhe ou os dados ainda estejam carregando.

### Exemplo de Hidratação do React Query
```tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { MeuModuloData } from "./_components/types";

interface MeuModuloClientProps {
  initialData: MeuModuloData | null;
  serverFazendaId: string;
}

export function MeuModuloClient({ initialData, serverFazendaId }: MeuModuloClientProps) {
  const { activeFazendaId } = useAppStore();

  // Verifica se o estado do cliente coincide com o pré-carregado no servidor
  const isServerDataMatching = (!activeFazendaId && !serverFazendaId) || (activeFazendaId === serverFazendaId);

  const { data, isLoading, isError, error } = useQuery<MeuModuloData>({
    queryKey: ["modulo", "dashboard", activeFazendaId],
    queryFn: () =>
      apiFetch("/modulo/dashboard", {
        params: activeFazendaId ? { unidade_produtiva_id: activeFazendaId } : undefined,
      }),
    // O initialData só é injetado se os filtros forem compatíveis
    initialData: isServerDataMatching ? (initialData ?? undefined) : undefined,
  });

  // Renderização do layout com tratamentos de erro e carregamento...
}
```

---

## 5. Padrão para Concorrência com Múltiplas Consultas (`Promise.allSettled`)

Se uma página exigir dados de múltiplos endpoints para hidratar o cliente, o servidor deve fazer as chamadas paralelamente utilizando `Promise.allSettled` ao invés de awaits sequenciais.

```tsx
const [saldosRes, alertasRes, produtosRes] = await Promise.allSettled([
  apiFetchServer(`/estoque/saldos${fazendaParam}`),
  apiFetchServer(`/estoque/alertas${fazendaParam}`),
  apiFetchServer("/cadastros/produtos"),
]);

const initialData = {
  saldos: saldosRes.status === "fulfilled" ? saldosRes.value : [],
  alertas: alertasRes.status === "fulfilled" ? alertasRes.value : [],
  produtos: produtosRes.status === "fulfilled" ? produtosRes.value : [],
};
```
> [!IMPORTANT]
> Nunca utilize `Promise.all` simples sem captura de erro individual no servidor. Se uma única API secundária falhar por instabilidade ou timeout, o `Promise.all` rejeita toda a requisição, derrubando o carregamento completo do dashboard.

---

## 6. Padrão de Restrição de Planos (Tier-Based Loading)

Páginas ou abas que dependem de planos Professional ou Enterprise requerem verificação de planos segura.

1. **No Servidor (`page.tsx`)**: Se o endpoint do backend exigir plano e retornar erro de pagamento (`402 Payment Required`), capture-o no `try/catch` definindo o dado correspondente como `null`.
2. **No Cliente (`Client.tsx`)**:
   - Utilize o hook `useHasTier("PROFISSIONAL")` ou `useHasTier("ENTERPRISE")` para habilitar ou desabilitar as consultas adicionais via flag `enabled`.
   - Se o plano for insuficiente, apresente o card padrão de upgrade (`TierUpgradeCard`) no lugar da interface operacional daquele plano.

---

## 7. Padrão de Testes E2E (Playwright)

Toda rota migrada para RSC deve conter um teste E2E correspondente em `tests/e2e/[modulo]-rsc-migration.spec.ts` validando a interface.

- **Mock de Autenticação**:
  - Injetar no `localStorage` o objeto `"agrosaas-auth-storage"` serializado contendo o estado da sessão com permissões adequadas.
  - Inserir cookies de autenticação (`token`, `tenant_id`, `unidade_produtiva_id`) no contexto do navegador.
- **Intercepção de API**: Mockar rotas `/api/v1/...` por meio de `page.route` para fornecer payloads previsíveis.
- **Asserções de Visibilidade**: Validar se os KPI Cards, cabeçalhos (`h1`) e tabelas estão visíveis e se comportam de forma responsiva às interações locais (filtros, abas).
- **Asserção de Fallback**: Validar que, se uma rota de detalhe carregar um ID inválido, a tela apresente uma mensagem de erro e não quebre em tela branca.
