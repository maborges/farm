# RBAC Backend Matrix

| Módulo | Endpoint | Método | Permissão Injetada | Status |
|---|---|---|---|---|
| operacional | /compras/fornecedores | GET | `operacional:compras:list` | Corrigido |
| agricola | /safras/ | POST | `agricola:safras:create` | Corrigido |
| agricola | /agricola/dashboard/ | GET | `agricola:dashboard:view` | Corrigido |
| agricola | /public/track/{codigo_lote} | GET | `PUBLICO` | Corrigido |
| agricola | /public/rastreabilidade/{token} | GET | `PUBLICO` | Corrigido |