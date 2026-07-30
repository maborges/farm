# NAVIGATION-ARCH-02B — Jornada da Agricultura e contexto da Safra

**Data:** 2026-07-29  
**Status:** GO COM RESSALVAS

## Resultado

O módulo Agricultura passou a expor a sequência operacional da safra sem
alterar qualquer contrato funcional. A navegação lateral agora apresenta:

```text
Painel Agrícola
Safras e Painel da Safra
  → Planejamento
  → Diagnóstico
  → Execução
  → Produção
  → Resultados
  → Suporte
```

`Safras e Painel da Safra` é a porta explícita para listar, criar e selecionar
uma safra. Depois da seleção, a rota já existente `/agricola/safras/[id]` é o
hub contextual da operação.

## Auditoria do contexto de Safra

| Item auditado | Evidência | Conclusão |
| --- | --- | --- |
| Painel Agrícola | `/agricola` | É o painel agregado do módulo; não substitui o contexto de uma safra específica. |
| Lista e criação de Safras | `/agricola/safras` | Lista as safras, oferece `Nova Safra` e encaminha a seleção para `/agricola/safras/[id]`; também resolve os redirects seletivos de orçamento e planejamento. |
| Painel da Safra | `/agricola/safras/[id]` | Já concentra cultura, área, fase/status, progresso, tarefas, timeline, checklist e acessos de continuidade. Pode assumir o papel de hub sem nova página. |
| Dashboard da Safra | `/agricola/safras/[id]/dashboard` | Complementa o hub com KPIs, riscos e cenários no plano Profissional; não substitui o painel operacional principal. |
| Navegação contextual | `components/agricola/safra-subnav.tsx` e `safras/[id]/layout.tsx` | Já oferece os destinos por safra para resumo, planejamento, execução, monitoramento, colheita e gestão. |
| Breadcrumbs | `PageHeader` e páginas em `safras/[id]` | Já seguem `Agrícola > Safras > [nome da safra] > [destino]`, sem mudar roteamento. |

### Existe uma Safra ativa oficial?

Não. Não há `SafraContext`, provider, store Zustand nem parâmetro global que
persista uma safra ativa. As telas fora de `/safras/[id]` selecionam uma safra
localmente — em geral a primeira não encerrada — ou permitem a escolha no
próprio formulário. Isso é deliberadamente mantido nesta fase: introduzir um
contexto global violaria o escopo.

As rotas com `[id]` já carregam o contexto explícito na URL e são a experiência
mais coerente para trabalhar em uma safra específica.

## Reorganização aplicada ao sidebar

| Ordem | Seção | Conteúdo |
| --- | --- | --- |
| Entrada | Safras e Contexto | Painel Agrícola; Safras e Painel da Safra |
| 1 | Planejamento | Planejamento Operacional; Orçamento; Culturas e Variedades; Receitas de Aplicação; Custeio |
| 2 | Diagnóstico | Análises de Solo; Dados Climáticos; Pragas e Doenças; Fitossanitário; Fenologia; NDVI; Mapa de Prescrições |
| 3 | Execução | Operações Consolidadas; Caderno de Campo; Timeline Operacional |
| 4 | Produção | Romaneios de Colheita; Beneficiamento |
| 5 | Resultados | Rentabilidade; DRE; Relatórios; Central de Inteligência |
| 6 | Suporte | Central de Ajuda |

Não foi adicionada uma entrada global para Tarefas: ela já existe no contexto
de safra em `/agricola/safras/[id]/tarefas`. Criar ou alterar um `href` global
estaria fora da permissão desta fase. Campo PWA permanece inalterado.

## Contratos preservados

- Nenhuma rota foi criada, removida ou alterada.
- Nenhuma permissão/RBAC foi alterada.
- Nenhum `moduleId`, `ModuleGate`, tier ou plano foi alterado.
- Não houve mudança em APIs, backend, banco, modelo territorial, modelo
  econômico, Campo PWA, store ou provider.
- Ícones dos itens e das seções foram preservados.

O guardrail `test:sidebar` passou a proteger a ordem da jornada e o manifesto
dos `href`, permissões, tiers e gate da Agricultura.

## Arquivos alterados

- `apps/web/src/lib/sidebar-config.ts`
- `apps/web/scripts/check-sidebar-guardrails.mjs`
- `docs/implementation/reports/NAVIGATION-ARCH-02B-JORNADA-AGRICULTURA.md`

## Validação

| Comando | Resultado |
| --- | --- |
| `cd apps/web && npm run test:sidebar` | aprovado — 134 `hrefs`, 12 gates |
| `cd apps/web && npm run typecheck` | aprovado |
| `cd apps/web && npm run lint` | aprovado (script oficial) |
| `cd apps/web && npm run build` | aprovado |
| `git diff --check` | aprovado |

## Respostas ao aceite

1. **O Painel da Safra já pode ser o hub operacional?** Sim. A rota
   `/agricola/safras/[id]` já possui o resumo e as continuidades necessárias;
   o dashboard de safra permanece complementar.
2. **Existe conceito de Safra ativa?** Não globalmente. Há contexto por rota
   `[id]` e seleções locais independentes.
3. **A sequência ficou clara?** Sim, no sidebar e na subnavegação já existente
   da safra selecionada.
4. **Houve alteração de rotas?** Não.
5. **Houve alteração de permissões?** Não.
6. **Houve alteração de ModuleGate?** Não.
7. **Quais arquivos foram alterados?** Os três listados acima.
8. **Quais riscos permanecem?** Telas globais ainda escolhem safra de modo
   local; a continuidade contextual plena fora de `/safras/[id]` exigiria uma
   fase futura de contexto global, explicitamente fora deste escopo.
9. **O piloto fica mais intuitivo?** Sim. O menu agora explica a ordem do
   trabalho e torna a seleção da safra a transição visível para o hub já
   existente, sem surpresa de navegação ou mudança de acesso.
10. **Veredicto:** **GO COM RESSALVAS** — a jornada é clara e compatível com o
    piloto; a única ressalva é a inexistência intencional de uma Safra ativa
    global.
