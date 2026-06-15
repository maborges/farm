import os
import glob
import re
import json

app_dir = "apps/web/src/app"
pages = glob.glob(f"{app_dir}/**/page.tsx", recursive=True)

stats = {
    "total": len(pages),
    "use_client": 0,
    "server_components": 0,
    "use_query": 0,
    "use_effect": 0,
    "multiple_queries": 0,
    "recharts": 0,
    "forms": 0,
    "maps": 0,
    "files": []
}

for page in pages:
    with open(page, 'r', encoding='utf-8') as f:
        content = f.read()
    
    is_client = '"use client"' in content or "'use client'" in content
    if is_client:
        stats["use_client"] += 1
    else:
        stats["server_components"] += 1
        
    uses_query = "useQuery(" in content or "useQuery<" in content
    if uses_query:
        stats["use_query"] += 1
        
    uses_effect = "useEffect(" in content
    if uses_effect:
        stats["use_effect"] += 1
        
    query_matches = re.findall(r'useQuery[\(<]', content)
    if len(query_matches) > 1:
        stats["multiple_queries"] += 1
        
    has_recharts = "recharts" in content
    if has_recharts:
        stats["recharts"] += 1
        
    has_forms = "react-hook-form" in content or "useForm" in content
    if has_forms:
        stats["forms"] += 1
        
    has_maps = "leaflet" in content or "Map" in content or "google-maps" in content
    if has_maps:
        stats["maps"] += 1
        
    stats["files"].append({
        "path": page,
        "is_client": is_client,
        "queries": len(query_matches),
        "effect": uses_effect,
        "recharts": has_recharts,
        "forms": has_forms,
        "maps": has_maps,
        "lines": len(content.splitlines())
    })

with open("analyze_frontend_results.json", "w") as f:
    json.dump(stats, f, indent=2)

print(f"Done analyzing {len(pages)} pages.")
