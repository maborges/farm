# TERRITORY-CONVERGENCE-01A — Auditoria de Fechamento da Convergência Territorial

## 1. Resumo Executivo
Esta auditoria avaliou a transição da arquitetura territorial do AgroSaaS, que visava separar o conceito de `UnidadeProdutiva` (operacional) do conceito de `ImovelRural` (fundiário/legal) utilizando `Propriedade` e `PropriedadeImovel` como pontes canônicas. 
O resultado revela que a convergência **está incompleta**. A tabela oficial de vínculos `propriedade_imovel` encontra-se totalmente vazia. Em vez disso, o sistema continua operando sobre mecanismos legados e de compatibilidade temporária (overlays e fallbacks em `imoveis_rurais.unidade_produtiva_id`), mantendo vivos campos fundiários dentro da `UnidadeProdutiva`.

## 2. Arquitetura Encontrada vs Documentada
### Arquitetura Oficialmente Documentada
```text
Tenant
├── UnidadeProdutiva (contexto operacional, acesso e organização)
├── Propriedade (contexto territorial e produtivo)
├── PropriedadeImovel (associação N:N canônica)
└── ImovelRural (contexto legal, fundiário, documental e fiscal)
```

### Arquitetura Encontrada (Física e Lógica)
```text
Tenant
├── UnidadeProdutiva (ainda hospeda CAR, NIRF, Matrícula na sua estrutura e formulários)
│   ├── (vínculo direto legado) -> ImovelRural (125 registros dependem exclusivamente disso)
│   └── (vínculo N:1 via) -> ExploracaoRural (3015 registros)
│                            └── Propriedade
├── PropriedadeImovel (0 registros - o vínculo canônico não está sendo formado)
```
Diferenças principais: A associação canônica `PropriedadeImovel` não está sendo consolidada. `ExploracaoRural` se tornou o eixo central de ligação para propriedades, enquanto `ImovelRural` permanece amarrado ao legado `unidade_produtiva_id`.

## 3. Inventário de Models, Tabelas e Relacionamentos
- **UnidadeProdutiva** (`unidades_produtivas`): Preserva campos legados (`nirf`, `codigo_car`, `numero_matricula`, `ccir`, `sigef_codigo`). Atua como origem operacional.
- **Propriedade** (`cadastros_propriedades`): Representa a dimensão produtiva.
- **ImovelRural** (`imoveis_rurais`): Detém os dados legais. Apresenta o campo `unidade_produtiva_id` (fallback legado) que hoje é sua principal amarração.
- **PropriedadeImovel** (`propriedade_imovel`): Tabela vazia.
- **ExploracaoRural** (`cadastros_exploracoes_rurais`): Liga UnidadeProdutiva a Propriedade (3015 vínculos).

## 4. Inventário de Consumidores
- **Formulários e Telas Web:** 
  - `apps/web/src/components/propriedade/propriedade-dialog.tsx` -> Coleta ativamente `codigo_car` e `numero_matricula`. (Frontend) [LEGADO_ATIVO]
  - `packages/zod-schemas/src/fazenda-schemas.ts` -> Valida dados fundiários na entidade operacional. (Schema) [LEGADO_ATIVO]
- **Backend (Python):**
  - `UnidadeProdutivaService._aplicar_overlay_territorial`: Método de compatibilidade que busca dados em `ImovelRural` e sobrepõe em `UnidadeProdutiva` na leitura. (Service) [COMPATIBILIDADE_TEMPORARIA]
  - `UnidadeProdutivaService._sincronizar_vinculo_fundiario`: Sincronizador de gravação. Tenta criar `ImovelRural` e `PropriedadeImovel`. (Service) [LEGADO_TOLERADO]

## 5. Mapas de Leitura e Gravação
### Mapa Completo de Leituras
1. **GET UnidadeProdutiva:** Lê a tabela `unidades_produtivas`, e em seguida aciona `_aplicar_overlay_territorial`.
2. O **Overlay** faz um SELECT direto em `ImovelRural` por `unidade_produtiva_id`. Se não achar, faz JOIN com `ExploracaoRural` -> `PropriedadeImovel`.
3. Resultado: Frontend sempre recebe a entidade UnidadeProdutiva com os dados "mascarados" do ImovelRural.

### Mapa Completo de Gravações
1. **POST/PUT UnidadeProdutiva:** Usuário preenche `codigo_car` / `numero_matricula` via `propriedade-dialog.tsx`.
2. A API salva a `UnidadeProdutiva` com os campos fundiários.
3. Aciona o `_sincronizar_vinculo_fundiario`.
4. O sincronizador cria ou atualiza um `ImovelRural` vinculando via `unidade_produtiva_id`.
5. O sincronizador tenta criar `PropriedadeImovel`, mas **falha silenciosamente** pois a `ExploracaoRural` (ponte UP-Prop) geralmente ainda não foi criada na transação de criação da UP. A exceção é engolida ou a lógica ignora.

## 6. Diagnóstico do Banco Físico
Foram executadas consultas estritamente de leitura, garantindo isolamento de RLS (`tenant_id`), com os seguintes resultados físicos no momento da auditoria:
- **CONSISTENTE (UPs associadas via ExploracaoRural):** 3015
- **SOMENTE_VINCULO_DIRETO (ImovelRural dependendo 100% de unidade_produtiva_id):** 125 (Nenhum destes possui PropriedadeImovel)
- **SOMENTE_VINCULO_PROPRIEDADE_IMOVEL:** 0 (A tabela canônica `propriedade_imovel` tem 0 registros em todo o banco).
- **Vínculos Órfãos (ImovelRural sem UP e sem PropriedadeImovel):** 0
- **DIVERGENTE (NIRF conflitante entre UP e ImovelRural Direto):** 1
- **AMBIGUO (UPs com múltiplos ImovelRural diretos vinculados):** 1
- **LEGADO_ATIVO:** Existem 114 registros na tabela `unidades_produtivas` com campos fundiários ativamente preenchidos.

## 7. Matriz de Fonte de Verdade

| Conceito ou campo   | Fonte utilizada atualmente | Fonte oficial proposta | Legado identificado | Consumidores | Risco |
| ------------------- | -------------------------- | ---------------------- | ------------------- | ------------ | ----- |
| Nome operacional    | `UnidadeProdutiva` | `UnidadeProdutiva` | N/A | Front, Relatórios | Baixo |
| CPF/CNPJ            | `UnidadeProdutiva` | `UnidadeProdutiva` | N/A | Notas Fiscais | Baixo |
| NIRF/CIB            | `UnidadeProdutiva` + Overlay | `ImovelRural` | Campos em UP | `propriedade-dialog` | Alto |
| CAR                 | `UnidadeProdutiva` + Overlay | `ImovelRural` | Campos em UP | `propriedade-dialog` | Alto |
| Matrícula           | `UnidadeProdutiva` + Overlay | `ImovelRural` | Campos em UP | `propriedade-dialog` | Alto |
| Vínculo operacional | `ExploracaoRural` | `ExploracaoRural` | N/A | Produção, Custos | Médio |
| Vínculo fundiário   | `ImovelRural.unidade_produtiva_id` | `PropriedadeImovel` | Vínculo Direto ImovelRural-UP | `_sincronizar_vinculo_fundiario` | Alto |

## 8. Análise de `ExploracaoRural`
A entidade `ExploracaoRural` atua atualmente como uma ponte técnica entre `UnidadeProdutiva` (operação) e `Propriedade` (produtivo).
- **Conceito de negócio:** Sim. Representa a natureza do vínculo (posse, arrendamento, parceria).
- **Justificativa de manutenção:** Totalmente necessária, possuindo 3015 registros vitais para as amarrações do sistema produtivo. Não deve ser removida.

## 9. Classificação dos Elementos Legados
- `unidades_produtivas.codigo_car`: LEGADO_ATIVO
- `unidades_produtivas.nirf`: LEGADO_ATIVO
- `unidades_produtivas.numero_matricula`: LEGADO_ATIVO
- `imoveis_rurais.unidade_produtiva_id`: COMPATIBILIDADE_TEMPORARIA (Atualmente a única coisa que mantém os 125 imóveis amarrados)
- `PropriedadeImovel`: OFICIAL (Mas não utilizado, 0 records)
- `_aplicar_overlay_territorial`: COMPATIBILIDADE_TEMPORARIA
- `_sincronizar_vinculo_fundiario`: LEGADO_ATIVO (gera o link direto, mas falha no link N:N)

## 10. Riscos Operacionais e de Dados
- **Falso positivo de migração:** Os desenvolvedores podem acreditar que `PropriedadeImovel` já funciona por existirem "125 Imóveis", quando na verdade a associação N:N oficial é inexistente no banco físico.
- **Perda de dados em exclusão:** Se `unidade_produtiva_id` for apagada prematuramente, os 125 `ImovelRural` se tornarão órfãos irremediáveis.
- **Falhas transacionais silenciosas:** O método `_sincronizar_vinculo_fundiario` silencia ConstraintExceptions/IntegrityErrors ao tentar fazer o vínculo canônico.

## 11. Plano de Convergência Esperado
- **TERRITORY-CONVERGENCE-01B (Guardrails e Bloqueio):** Implementar testes AST proibindo leitura e escrita direta dos campos legados (nirf, car) em UnidadeProdutiva fora dos sincronizadores, prevenindo o crescimento do débito técnico.
- **TERRITORY-CONVERGENCE-01C (Backfill do Link Canônico):** Criar script idempotente para ler todos os `ImovelRural` que possuem `unidade_produtiva_id`, encontrar a `Propriedade` via `ExploracaoRural` (daquela UP) e persistir o vínculo formal em `PropriedadeImovel`.
- **TERRITORY-CONVERGENCE-01D (Atualização do Formulário Frontend):** Refatorar `propriedade-dialog.tsx` e dependentes para gravar os campos fundiários em endpoints próprios de Imóvel, em vez de atrelar a UP.
- **TERRITORY-CONVERGENCE-01E (Limpeza Backend):** Apagar `_aplicar_overlay_territorial` e `_sincronizar_vinculo_fundiario`. Remover os campos do Zod Schema.
- **TERRITORY-CONVERGENCE-01F (Drops de Colunas - Opcional, pós-verificação):** Dropar `unidade_produtiva_id` de `imoveis_rurais` e os campos fundiários de `unidades_produtivas`.

## 12. Lista de Arquivos Potencialmente Afetados Futuramente
- `apps/web/src/components/propriedade/propriedade-dialog.tsx`
- `packages/zod-schemas/src/fazenda-schemas.ts`
- `services/api/core/services/unidade_produtiva_service.py`
- `services/api/core/models/unidade_produtiva.py`
- `services/api/imoveis/models/imovel.py`

## 13. Veredicto Final

**GO COM RESSALVAS**

A convergência está perfeitamente mapeada e as causas do problema estão evidentes (a falha silenciosa ao criar PropriedadeImovel pela ausência de ExploracaoRural na mesma transação de criação da UP). A fase de guardrails (TERRITORY-CONVERGENCE-01B) está expressamente AUTORIZADA para iniciar, desde que nenhum script apague dados ainda, visto que 100% dos imóveis existentes dependem do vínculo legado direto.
