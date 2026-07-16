# TERRITORY-CONVERGENCE-01H2: Remoção Física do Legado Territorial

## Resumo Executivo

A fase 01H2 concluiu a **remoção física definitiva** do legado fundiário no banco de dados do AgroSaaS. As colunas legadas foram eliminadas das tabelas `unidades_produtivas` e `imoveis_rurais`, encerrando o período de transição arquitetural para o modelo unificado de visão territorial.

## Alterações Realizadas

1. **Migration de Remoção Lógica e Física (`265b28773962`)**
   - Criação da tabela de backup `farms.territory_legacy_backup_01h2` para segurança operacional (downgrade).
   - Drop da coluna `unidade_produtiva_id` da tabela `imoveis_rurais`.
   - Drop das colunas fundiárias da tabela `unidades_produtivas`:
     - `nirf`
     - `codigo_car`
     - `numero_matricula`
     - `ccir`
     - `sigef_codigo`
   - O upgrade e downgrade foram testados com sucesso, garantindo a preservação reversível dos dados em caso de emergência.

2. **Modelos (ORM)**
   - Limpeza definitiva das propriedades legadas e dos relacionamentos antigos em `core/models/unidade_produtiva.py` e `imoveis/models/imovel.py`.

3. **Lógica Residual**
   - Remoção de overlays e utilitários obsoletos em `UnidadeProdutivaService` (`_aplicar_compatibilidade_saida_territorial`).
   - Remoção de atribuições diretas de propriedades fundiárias do `CadastroCompletoService`.
   - Atualização da modelagem `ImovelFundiarioResumo` no `visao_schemas.py` para não depender de `unidade_produtiva_id`.
   - Limpeza das rotinas do `visao_service.py` (`_obter_propriedade`) que dependiam da restrição legada.

4. **Testes e Guardrails**
   - Atualização da allowlist da verificação de AST `test_territory_convergence_guardrails.py` para isolar estritamente as propriedades legítimas a serem usadas pela arquitetura nova (`ImovelRural`).
   - O guardrail legado perde seu impacto físico, mas mantemos as verificações de AST ativas na CI para proteger entidades contra o ressurgimento errôneo desses campos.
   - Pulo (`skip`) justificado em testes integrados (`test_exec37_auto_vinculo_fundiario.py`) cujo comportamento era essencialmente ligado a um auto-vinculo legado a partir de dados nas UPs.

## Auditoria Pós-Migration (Status Final)

As rotinas e UPs continuam a operar pelo `PropriedadeImovel`, mantendo compatibilidade com as regras de leitura adaptativas desenvolvidas na fase 01H1. 
Zero ocorrências de quebra de serviços orquestradores (como `CadastroCompletoService`) perante a ausência dos campos nas instâncias SQLAlchemy.

**Status dos Gates Pós-Migration**:
* DIRECT_ONLY: 0
* ORPHAN: 0
* CANONICAL_ONLY: OK (Todas as dependências foram satisfeitas no modelo unificado de `ImovelRural`).

## Próximos Passos
Esta é a última fase técnica da Convergência Territorial. Todo desenvolvimento futuro de Módulo Fundiário e Operacional poderá assumir o `ImovelRural` como a única entidade de definição física de polígonos, registros, cartórios e licenciamento.
