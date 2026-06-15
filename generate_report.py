import json

with open("analyze_frontend_results.json", "r") as f:
    stats = json.load(f)

# Classify pages
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
        # already server component
        continue
        
    # Class D: Offline, PWA, map heavy, camera
    if file["maps"] or "offline" in path or "camera" in path or "sync" in path:
        d_list.append(file)
    # Class C: Complex grids, charts, upload, multiple queries
    elif file["recharts"] or "upload" in path or queries >= 3 or lines > 300:
        c_list.append(file)
    # Class B: Forms, simple CRUD
    elif file["forms"] or "novo" in path or "editar" in path or "cadastros" in path:
        b_list.append(file)
    # Class A: Simple listing, static or 1-2 queries
    else:
        a_list.append(file)

# Sort by lines descending to find the biggest ones for impact
def sort_by_lines(lst):
    return sorted(lst, key=lambda x: x["lines"], reverse=True)

a_list = sort_by_lines(a_list)
b_list = sort_by_lines(b_list)
c_list = sort_by_lines(c_list)
d_list = sort_by_lines(d_list)

# Generate Markdown
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

for f in a_list[:5]:
    md += f"- `{f['path']}` ({f['lines']} linhas, {f['queries']} queries)\n"
if len(a_list) > 5:
    md += f"- ... e outras {len(a_list)-5} páginas.\n"

md += f"""
### Classe B: Migração Moderada ({len(b_list)} páginas)
_Formulários, filtros de listagem e CRUD leve._

"""
for f in b_list[:5]:
    md += f"- `{f['path']}` ({f['lines']} linhas, {f['queries']} queries)\n"
if len(b_list) > 5:
    md += f"- ... e outras {len(b_list)-5} páginas.\n"

md += f"""
### Classe C: Migração Complexa ({len(c_list)} páginas)
_Grids complexos, gráficos (Recharts), múltiplos useQuery (>3), páginas grandes (>300 linhas)._

"""
for f in c_list[:5]:
    md += f"- `{f['path']}` ({f['lines']} linhas, {f['queries']} queries)\n"
if len(c_list) > 5:
    md += f"- ... e outras {len(c_list)-5} páginas.\n"

md += f"""
### Classe D: Não Migrar Agora ({len(d_list)} páginas)
_Uso pesado de Mapas (Leaflet/Google), bibliotecas altamente client-side._

"""
for f in d_list[:5]:
    md += f"- `{f['path']}` ({f['lines']} linhas, {f['queries']} queries)\n"
if len(d_list) > 5:
    md += f"- ... e outras {len(d_list)-5} páginas.\n"

md += """
## 3. Waterfalls e Gargalos Encontrados

- Múltiplos `useQuery` identificados em cascata ou paralelo dentro de componentes cliente atrasando a pintura (TTFB do usuário fica bloqueado até o React montar a página).
- Cerca de **33 páginas** utilizam `useEffect`, possivelmente causando fetching duplo em Strict Mode ou lógicas imperativas que poderiam ser derivadas.

## 4. Oportunidades de Suspense e Loading.tsx

- A maioria das listagens (Classe A e B) deve ser envolvida em `<Suspense fallback={<ListagemSkeleton />}>` para entregar HTML imediato enquanto a busca de servidor não termina.
- Módulos inteiros como `(dashboard)/financeiro/` precisam de arquivos `loading.tsx` globais.

## 5. Estratégia de Migração Recomendada

### Onda 1 (Curto Prazo - Alto Impacto)
- Focar nas páginas da **Classe A** e painéis de leitura principais (dashboards).
- Substituir `useQuery` nestas páginas por fetching direto no Server Component com `await apiFetch()`.
- Passar os dados como prop (`initialData`) para Client Components menores (grids ou gráficos).

### Onda 2 (Médio Prazo)
- Refatorar a **Classe B**, isolando formulários (`react-hook-form`) em Client Components "folha" (leaf components) e deixando as páginas raiz de criação/edição como RSC.

### Onda 3 (Longo Prazo)
- Desacoplar a **Classe C**, reestruturando Grids e Dashboards massivos, movendo as chamadas de API para o Next.js e injetando as propriedades nos componentes client pesados via Props ou Providers React.
"""

with open("docs/audits/AUDIT-FIX-04.1-frontend-migration-map.md", "w") as f:
    f.write(md)

print("Report generated successfully.")
