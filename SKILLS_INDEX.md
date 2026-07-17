# AgroSaaS - Índice de Skills Especializadas

Acesso rápido às skills especializadas por módulo. Use quando a tarefa for claramente ligada a um módulo de negócio.
Para contexto geral, siga `docs/architecture/ai-bootstrap.md` primeiro (não repetido aqui).

## 📚 Skills Disponíveis

| Skill | Especialidade | Use quando |
|---|---|---|
| [Core Module Expert](.claude/skills/CORE_MODULE_EXPERT.md) | Auth, RBAC, Multi-tenancy, Billing — **fonte única destes temas no projeto** | Auth, billing, multi-tenancy |
| [Agricola Module Expert](.claude/skills/AGRICOLA_MODULE_EXPERT.md) | Safras, talhões, NDVI, romaneios, prescrições | Culturas, campo, precisão, colheita |
| [Pecuaria Module Expert](.claude/skills/PECUARIA_MODULE_EXPERT.md) | Lotes, piquetes, IATF, confinamento, leite | Gado, pastagens, reprodução, leite |
| [Financeiro Module Expert](.claude/skills/FINANCEIRO_MODULE_EXPERT.md) | Plano de contas, rateio, DRE, hedge, fiscal | Financeiro, custos, compliance fiscal |
| [Operacional Module Expert](.claude/skills/OPERACIONAL_MODULE_EXPERT.md) | Frota, estoque, manutenção, compras | Equipamentos, peças, estoque, compras |
| [Backoffice/Admin Expert](.claude/skills/BACKOFFICE_ADMIN_EXPERT.md) | Admin SaaS, tenants, suporte, analytics | Backoffice, admin, analytics |

## 🎯 Quando Usar Cada Skill

| Tarefa | Skill Primária | Skills Secundárias |
|--------|---------------|-------------------|
| Implementar login/signup | Core | - |
| Criar safra | Agricola | Financeiro (custos) |
| Registrar pesagem de gado | Pecuaria | - |
| Lançar despesa | Financeiro | Agricola/Pecuaria (rateio) |
| Criar ordem de serviço (campo) | Agricola | Operacional (equipamento) |
| Manutenção de trator | Operacional | Financeiro (custos) |
| Processar billing | Backoffice | Core (subscription) |
| Criar ticket suporte | Backoffice | Core (impersonation) |

## Integrações Entre Módulos

```
CORE (Base)
  └─ Autenticação, Multi-tenancy, Billing
      ├─ AGRICOLA ──┬──> OPERACIONAL (equipamentos, insumos)
      │             └──> FINANCEIRO (custos/receitas safra)
      ├─ PECUARIA ──┬──> OPERACIONAL (ração, medicamentos)
      │             ├──> AGRICOLA (pastagens compartilhadas)
      │             └──> FINANCEIRO (custos gado, venda leite)
      ├─ FINANCEIRO ←─── TODOS (recebe custos e receitas)
      └─ OPERACIONAL ──> TODOS (fornece estoque e equipamentos)
BACKOFFICE ── gerencia todos os módulos
```

## Guia de Uso

- **Desenvolvimento**: identifique o módulo, leia a skill correspondente, siga "Common Workflows" e "Key Business Rules".
- **Code Review**: valide contra "Business Rules" e "Integration Points" da skill; confirme isolamento de tenant via [CORE_MODULE_EXPERT.md](.claude/skills/CORE_MODULE_EXPERT.md).
- **Onboarding**: dia 1-2 → `ai-bootstrap.md` + Core Module Expert; dia 3-5 → skills dos módulos designados.
- **Troubleshooting**: cada skill tem sua própria seção "Troubleshooting".

## Checklist de Implementação de Feature

- [ ] Consultei a skill do módulo correspondente
- [ ] Segui os padrões de Business Rules
- [ ] Implementei isolamento de tenant via `BaseService`
- [ ] Adicionei verificação de permissões e módulo contratado
- [ ] Criei testes conforme Testing Guidelines
- [ ] Documentei integrações com outros módulos

## Documentação Adicional

- [README.md](README.md) — visão geral do projeto
- [CLAUDE.md](CLAUDE.md) — guia de arquitetura e padrões de código
- [CONTEXTO.md](CONTEXTO.md) — mapa operacional ativo
- [docs/architecture/ai-bootstrap.md](docs/architecture/ai-bootstrap.md) — ordem oficial de leitura
- [API_REFERENCE_RBAC.md](API_REFERENCE_RBAC.md) — endpoints de RBAC (verificar cópia duplicada — ver `CONTEXTO.md` § Sinais de Atenção)

> `IMPLEMENTACAO_RBAC_MULTI_SUB.md` e `FRONTEND_MAINTENANCE_GUIDE.md` são históricos de execução de fases já
> concluídas — não fazem parte da leitura padrão de nenhuma skill.