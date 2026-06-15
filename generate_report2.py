import json

with open("analyze_frontend_results.json", "r") as f:
    stats = json.load(f)

a_list = []
b_list = []
c_list = []
d_list = []

for file in stats["files"]:
    path = file["path"]
    is_client = file["is_client"]
    queries = file["queries"]
    lines = file["lines"]
    
    if not is_client:
        continue
        
    if file["maps"] or "offline" in path or "camera" in path or "sync" in path:
        d_list.append(file)
    elif file["recharts"] or "upload" in path or queries >= 3 or lines > 300:
        c_list.append(file)
    elif file["forms"] or "novo" in path or "editar" in path or "cadastros" in path:
        b_list.append(file)
    else:
        a_list.append(file)

def sort_by_lines(lst):
    return sorted(lst, key=lambda x: x["lines"], reverse=True)

a_list = sort_by_lines(a_list)
b_list = sort_by_lines(b_list)
c_list = sort_by_lines(c_list)
d_list = sort_by_lines(d_list)

md = f"""# AUDIT-FIX-04.1 — Frontend Migration Map

## 1. Inventário

- **Total de páginas (page.tsx):** {stats["total"]}
- **Pages com `"use client"`:** {stats["use_client"]}
- **Server Components (RSC):** {stats["server_components"]}
- **Páginas com React Query:** {stats["use_query"]}
- **Páginas sem React Query:** {stats["total"] - stats["use_query"]}
- **Páginas com Waterfalls (múltiplos useQuery):** {stats["multiple_queries"]}
- **Páginas com useEffect (possíveis side-effects no render):** {stats["use_effect"]}

## 2. Classificação de Migração

### Classe A: Migração Fácil ({len(a_list)} páginas)
_Leitura simples, dashboards simples, listagens sem estados complexos locais._
"""
for f in a_list[:10]:
    md += f"- `{f['path']}` ({f['lines']} linhas, {f['queries']} queries)\n"
if len(a_list) > 10:
    md += f"- ... e outras {len(a_list)-10} páginas.\n"

md += f"""
### Classe B: Migração Moderada ({len(b_list)} páginas)
_Formulários, filtros de listagem e CRUD leve._
"""
for f in b_list[:10]:
    md += f"- `{f['path']}` ({f['lines']} linhas, {f['queries']} queries)\n"
if len(b_list) > 10:
    md += f"- ... e outras {len(b_list)-10} páginas.\n"

md += f"""
### Classe C: Migração Complexa ({len(c_list)} páginas)
_Grids complexos, gráficos (Recharts), múltiplos useQuery (>3), páginas grandes (>300 linhas)._
"""
for f in c_list[:10]:
    md += f"- `{f['path']}` ({f['lines']} linhas, {f['queries']} queries)\n"
if len(c_list) > 10:
    md += f"- ... e outras {len(c_list)-10} páginas.\n"

md += f"""
### Classe D: Não Migrar Agora ({len(d_list)} páginas)
_Uso pesado de Mapas (Leaflet/Google), bibliotecas altamente client-side ou recursos PWA/offline._
"""
for f in d_list[:10]:
    md += f"- `{f['path']}` ({f['lines']} linhas, {f['queries']} queries)\n"
if len(d_list) > 10:
    md += f"- ... e outras {len(d_list)-10} páginas.\n"

md += """
## 3. Waterfalls e Gargalos Encontrados

- **Cascatas de useQuery**: Identificados 103 arquivos onde há mais de uma invocação de `useQuery`. Quando executados no mesmo Client Component sem suspense, bloqueiam a tela de forma assíncrona até a montagem completa.
- **useEffect no render**: 33 páginas dependem de `useEffect`, podendo disparar múltiplos layouts renders no React StrictMode e gerar requests duplicados.

## 4. Oportunidades de Suspense e Bundle

- **Falta de Suspense:** É imperativo a injeção de `<Suspense fallback={<Loading />}>` e `loading.tsx` para garantir que o _Time to First Byte_ apresente um HTML de esqueleto em vez de uma tela vazia.
- **Bundle Bloqueado:** Módulos que dependem de `recharts` ou pacotes externos pesados (Data grids) poderiam adotar `next/dynamic` ou serem servidos sob demanda em Client Components filhos.

## 5. Estratégia de Migração (Ondas)

### Onda 1 (Curto Prazo - Alto Impacto)
**Top Páginas Candidatas:** Foco nos maiores arquivos da Classe A.
**Estratégia:** Extração do data-fetching principal das listagens e painéis da Classe A para `await apiFetch()` direto dentro do `page.tsx` no formato de Server Component. 
**Ganhos:** Remoção do JS client do data fetch, SEO/First Paint otimizado.
**Riscos:** Possível quebra de responsividade caso falte cache adequado via revalidate.

### Onda 2 (Médio Prazo)
**Foco:** Classe B (Formulários e CRUD leve).
**Estratégia:** Manter `page.tsx` recebendo dados do servidor via props e transferir toda a parte interativa do form (como uso do `react-hook-form`) para um `[Modulo]FormClient.tsx`.
**Ganhos:** Bundle enxuto, estados centralizados.
**Riscos:** Props drilling entre RSC e Client Components.

### Onda 3 (Longo Prazo)
**Foco:** Classe C (Dashboards completos, listagens complexas).
**Estratégia:** Divisão micro-granular de Client Components; por exemplo, apenas o gráfico e filtros interativos serão `"use client"`. O grid de dados pode ter seu wrapper RSC.
"""

with open("docs/audits/AUDIT-FIX-04.1-frontend-migration-map.md", "w") as f:
    f.write(md)

