# TERRITORY-CONVERGENCE-01E1-AUDITORIA-FECHAMENTO

## 1. Resumo Executivo
Esta auditoria de fechamento atesta a higidez, performance e segurança da fase **01E** (Conversão de Leituras). A implementação comprovou isolar o legado, sem perda de acessibilidade aos dados atuais. Todos os requisitos de delegação, telemetria estruturada e resiliência foram cumpridos. A fase **01F (Drops)** está liberada para execução, com ressalvas apenas no âmbito dos registros físicos não-convergidos que requerem backfill posterior.

## 2. Auditoria do `TerritoryReadService`
- **Métodos e Sessão:** Operacional com sessão transacional controlada pelo caller. Consulta isolada por `tenant_id`.
- **Validação Soft Delete:** Respeitada em `ImovelRural.deleted_at.is_(None)`.
- **Múltiplos Cenários:** Comporta UPs com múltiplas propriedades e imóveis. `vinculo_principal` elege o principal; os demais são secundários.
- **Consultas sem Arbitrariedades:** Não utiliza `.first()` ou `.limit(1)` arbitrariamente para a fonte canônica. Efetua agregação real do relacionamento N:N e identifica adequadamente ambiguidades.

## 3. Ordem Real de Resolução
Os testes automatizados (`test_territory_read_service.py`) validaram:
- **Caso A (Associação Oficial):** Retorna `CANONICAL_PROPERTY_ASSOCIATION`.
- **Caso B (Legado Direto):** Retorna `LEGACY_DIRECT_LINK`.
- **Caso C (Campos UP):** Retorna `LEGACY_UP_FIELDS` / `PARTIALLY_CONVERTED`.
- **Caso D (Múltiplos / Ambiguidade):** Reporta nos campos de `avisos` e define `estado_de_convergencia = AMBIGUOUS` / `CONFLICT`.

## 4. Auditoria do Overlay (`UnidadeProdutivaService`)
- O método `_aplicar_overlay_territorial` atua puramente como **ADAPTADOR_DE_COMPATIBILIDADE**.
- Substitui atributos unicamente em memória para os DTOs atuais, sem executar IO destrutivo.
- Instancia o `TerritoryReadView` e mapeia seu imovel principal sobre `codigo_car`, `nirf` etc.

## 5. Auditoria do Sincronizador Legado
- O método `_sincronizar_vinculo_fundiario` possui `NOOP_CANONICAL_LINK_EXISTS` caso o U.P. já esteja no modelo novo.
- Possui bypass (`NOOP_OFFICIAL_FLOW`) para o `CadastroCompletoService`.
- **Callers Residuais (UnidadeProdutivaService):**
  - `criar_unidade_produtiva` e `atualizar_unidade_produtiva` (LEGACY_REQUIRED)

## 6. Inventário da Allowlist (AST Guardrails)
| Arquivo | Símbolo | Acesso legado permitido | Motivo atual | Pode sair na 01F? |
| ------- | ------- | ----------------------- | ------------ | ----------------- |
| `core/services/unidade_produtiva_service.py` | `UnidadeProdutivaService` | `*` | Hospeda o sincronizador e o overlay. | Sim (Após limpeza) |
| `core/services/territory_read_service.py` | `*` | `*` | Serviço oficial autorizado a realizar fallbacks. | Não (O fallback será aposentado via script) |
| `imoveis/services/imovel_service.py` | `ImovelService` | `unidade_produtiva_id` | Utilizado pelo sincronizador para UPs que ainda nascem pelo modo antigo. | Sim |
| `alert_engine/generators/...` | `*` | `unidade_produtiva_id` | Lê o fallback legado. | Sim |

## 7. Diagnóstico Físico do Banco (`agrosaas.db` - Base Local)
*Comparativo (Estado isolado desta suíte de testes vs 01C)*
- **Imóveis totais:** 125
- **Associação Oficial (`CANONICAL_ONLY` / `BOTH_CONSISTENT`):** 0
- **Apenas Vínculo Direto (`DIRECT_ONLY`):** 125
- **U.P. com Apenas Campos Fundiários (`LEGACY_FIELDS_ONLY`):** 21
- **U.P. sem `ExploracaoRural`:** 2183
- **Conflitos Principais / Secundários:** 0
- **Cross-tenant:** 0

*Nota:* O ambiente local atual apresenta 100% de `DIRECT_ONLY` nos seus 125 imóveis. A migração total do backfill dependerá da geração de `ExploracaoRural` em produção.

## 8. Evidências de Telemetria
Os logs estruturados incluem `[TerritoryRead] source=... state=... up_id=... tenant_id=...`. Não persistem CPF, CNPJ, NIRF, CAR ou Matrícula, assegurando total aderência a boas práticas (Zero PII e Zero Secrets no log).

## 9. Performance e N+1
- **Detalhe de U.P.:** Leitura pontual por `obter_visao_territorial_da_unidade`.
- **Listagem de U.P.:** Utiliza o `obter_visoes_territoriais_em_lote(unidade_ids)` carregando dados antecipadamente (`where id.in_()`), agrupando referências via dicionários de forma eficiente (O(N)), sem subqueries de N+1 no banco de dados.

## 10. Contratos de API
- Os DTOs de `UnidadeProdutivaResponse` agregam `territorio` como estrutura isolada e auto-contida.
- IDs oficiais (UUIDs de Imovel, Propriedade e Associacoes) foram corretamente expostos, dispensando dedução via documentos no client.

## 11. Frontend
- Os componentes `propriedades-client.tsx` e `propriedade-detalhe-client.tsx` extraem os identificadores do nó `.territorio.imovel_principal`.
- Foram introduzidos marcadores visuais de alertas de ambiguidade (status do ícone), painéis dedicados a **Imóveis Secundários**, e mensagens temporárias para propriedades não-migradas.

## 12. Testes Executados
- `pytest tests/unit/test_territory_convergence_guardrails.py` (Pass - 100%)
- `pytest tests/unit/core/test_territory_read_service.py` (Pass - 100%)
- `npm run typecheck && npm run lint` no workspace Web (Corrigidos os tipos restritos para o MapLibre).

## 13. Veredicto Final

**GO COM RESSALVAS**

A fase `TERRITORY-CONVERGENCE-01E` cumpriu integralmente os objetivos arquitetônicos de modernizar as leituras fundiárias de forma compatível e sem geração residual.
As ressalvas apontam unicamente à realidade física do banco: como as estruturas ainda dependem vastamente da `unidade_produtiva_id` (`DIRECT_ONLY`: 125), a remoção física destas colunas no banco (drops físicos) durante a fase 01F não poderá acontecer de imediato sem que o backfill residual converta massivamente estes 125 casos e as UPs órfãs de `ExploracaoRural`.

**Próxima Fase:**
`TERRITORY-CONVERGENCE-01F — Regularização residual e remoção controlada do legado`
- **DROPS_AUTORIZÁVEIS:** Camadas lógicas (Sincronizador Legado pós-backfill), rotas legadas e uso de fallback na API.
- **DROPS_BLOQUEADOS:** `unidade_produtiva_id` de `ImovelRural` e campos da `UnidadeProdutiva` na camada de banco de dados (Aguardam regularização).
- **REGULARIZAÇÕES_OBRIGATÓRIAS:** Injeção sistêmica de `ExploracaoRural` para UPs que atualmente não a possuem.
