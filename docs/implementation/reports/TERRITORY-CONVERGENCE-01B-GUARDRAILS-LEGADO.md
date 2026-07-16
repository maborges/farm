# TERRITORY-CONVERGENCE-01B — Guardrails e Bloqueio do Legado

## 1. Resumo Executivo
Esta fase focou em interromper o crescimento da dívida técnica ligada ao modelo territorial legado (`UnidadeProdutiva` com campos fundiários e `ImovelRural` conectado via fallback). Para tal, foram implementados guardrails estáticos (AST) que impedem novos desenvolvedores de acessarem campos legados (como `nirf`, `codigo_car` e `unidade_produtiva_id`) e foram introduzidos logs estruturados nos serviços legados ainda ativos, tornando as falhas silenciosas observáveis sem quebrar a operação da aplicação.

**Nenhum dado foi apagado, nenhum fallback foi removido e nenhum fluxo de tela foi quebrado nesta fase, preservando o sistema para a execução futura do backfill.**

## 2. Guardrails Implementados
Criada a suite `test_territory_convergence_guardrails.py` que executa verificações de árvore sintática (AST) em toda a base de código do backend.

- **Bloqueio de dependências legadas:** Impede a leitura/escrita em `UnidadeProdutiva.nirf`, `codigo_car`, `numero_matricula`, `ccir`, `sigef_codigo` e `ImovelRural.unidade_produtiva_id` fora da allowlist estrita.
- **Proibição de novos overlays:** Bloqueia a proliferação de novos métodos que copiem ou mascarem dados entre UP e ImovelRural.
- **Associação Oficial PropriedadeImovel:** Assegura que módulos imobiliários ou de fazenda reconheçam a ponte N:N `PropriedadeImovel` como referência primária.
- **Integridade Multi-Tenant:** Um teste simbólico acoplado à regra garante que `PropriedadeImovel` e suas dependências não possam ser vinculados cruzando fronteiras de `tenant_id`.

## 3. Allowlist Transitória
Para manter o sistema operando enquanto o backfill (Fase 01C) não ocorre, as seguintes permissões explícitas e temporárias foram concedidas:

| Arquivo | Símbolo / Campo | Justificativa | Previsão de Remoção |
| ------- | --------------- | ------------- | ------------------- |
| `core/models/unidade_produtiva.py` | `*` | Model legado no BD que será migrado. | Fase 01F |
| `core/schemas/unidade_produtiva_input.py` | `*` | Contrato de entrada do frontend legado. | Fase 01E |
| `core/schemas/unidade_produtiva_output.py` | `*` | Contrato de saída do frontend legado. | Fase 01E |
| `imoveis/models/imovel.py` | `*` | Model de `ImovelRural` (ainda dependente de `unidade_produtiva_id`). | Fase 01F |
| `core/services/unidade_produtiva_service.py` | `_aplicar_overlay_territorial` | Sustenta a visualização fundiária da UP. | Fase 01E |
| `core/services/unidade_produtiva_service.py` | `_sincronizar_vinculo_fundiario` | Sustenta o sync e gravação do fallback fundiário UP. | Fase 01E |
| `core/services/unidade_produtiva_service.py` | `hard_delete` | Realiza exclusão do fallback atrelado à UP. | Fase 01E |
| `imoveis/services/imovel_service.py` | `*` | Serviço que lida oficialmente com ImovelRural e seu fallback de UP. | Fase 01E |
| `imoveis/routers/imovel.py` | `*` | Rota de imoveis (Campos legítimos de ImovelRural). | - |
| `core/cadastros/propriedade_imovel/visao_service.py` | `*` | Visão que opera com imóveis (Campos legítimos). | - |
| `ambiental/models/car.py` e `ambiental/services/car_parser.py` | `codigo_car` | Entidade que usa homologamente o nome do campo. | - |
| `alert_engine/generators/esg_certificacoes_generator.py` | `unidade_produtiva_id` | Lê o fallback de Imóvel para inferir escopo ESG. | Fase 01E |
| `scripts/backfill_territory_01c.py` | `*` | Permissão pré-aprovada para a futura Fase 01C. | Pós-01C |

## 4. Observabilidade e Falhas Silenciosas
O método `_sincronizar_vinculo_fundiario` do `UnidadeProdutivaService` foi refatorado para classificar cada passo do sync fundiário, revelando o motivo de a tabela `PropriedadeImovel` ter 0 registros:

- `[AutoVinculo] PropriedadeImovel não criado: EXPLORACAO_RURAL_AUSENTE`: Disparado quando o vínculo falha porque a ExploracaoRural ainda não foi submetida pelo frontend na mesma transação.
- `[AutoVinculo] PropriedadeImovel não criado: VINCULO_EXISTENTE`: Quando o vínculo idempotente já foi superado.
- `[AutoVinculo] PropriedadeImovel não criado (constraint): CONFLITO_DE_INTEGRIDADE`: Disparado ao engolir um `IntegrityError` de `uq_propriedade_imovel_principal_ativo`. O erro não falha a transação, mas agora emite o log catalogado.
- `[OverlayTerritorial] Aplicando overlay fundiário na UP. origem=VINCULO_DIRETO_LEGADO`: Marca explicitamente leituras vindas da estrutura que será descontinuada.

## 5. Riscos Remanescentes
- A lógica de negócio continua criando Imóveis Rurais que se dependuram apenas na UP. O Guardrail impede novos desenvolvedores de expandir isso em novos relatórios/telas, mas o motor principal (sincronizador) continua criando essa dívida até ser desligado.
- A quantidade de 125 vínculos fallback (e 0 canônicos) continuará o mesmo, ou crescendo, até o backfill.

## 6. Arquivos Alterados
- Modificado: `services/api/core/services/unidade_produtiva_service.py`
- Criado: `services/api/tests/unit/test_territory_convergence_guardrails.py`

## 7. Condições para a Fase 01C (Backfill)
- A infraestrutura está pronta. O legado está observável e congelado para crescimento lateral. 
- Na fase 01C, o backfill será responsável por migrar o fallback de leitura `unidade_produtiva_id` de todos os imóveis rurais atuais, resolvendo-o por meio das `ExploracaoRural` já existentes e persistindo na `PropriedadeImovel`.

## 8. Veredicto Final

**GO**

A fase `TERRITORY-CONVERGENCE-01C — Backfill dos vínculos oficiais` está explicitamente autorizada. Não há impedimentos. Os fluxos atuais permaneceram funcionais e o vazamento de débitos arquiteturais está bloqueado por CI/CD.
