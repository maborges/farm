# 07 — Segurança e Auditoria

## Tenant e RLS

- toda entidade do módulo possui `tenant_id` obrigatório;
- toda leitura e escrita usa contexto validado pelo middleware/dependência de tenant;
- vínculos com lote, commodity, propriedade e laudo devem ser validados dentro do mesmo tenant;
- rota pública usa token opaco e snapshot explicitamente publicado, sem consulta ampla ao tenant;
- testes cross-tenant são obrigatórios.

## RBAC sugerido

| Ação | Perfil |
|---|---|
| Consultar | produtor, gestão, comprador autorizado |
| Registrar amostra | operador, classificador |
| Avaliar | classificador |
| Aprovar/reprovar | responsável técnico |
| Publicar protocolo | administrador/RT |
| Alterar política comercial | administrador financeiro |
| Publicar passaporte | gestor autorizado |
| Auditar | auditor |

## Auditoria

Registrar criação, importação, medição, avaliação, aprovação, reprovação, ajuste, bloqueio, reanálise, publicação e revogação.

O log deve conter actor, tenant, timestamp, entidade, versão anterior/nova, origem, motivo e correlation id.

## Proteção de dados

Snapshots públicos devem aplicar allowlist. Fotos só são públicas mediante marcação explícita. Laudos, documentos e dados comerciais obedecem permissões e retenção do tenant.
