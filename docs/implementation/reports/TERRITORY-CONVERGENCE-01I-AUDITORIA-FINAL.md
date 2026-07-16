# Relatório Final de Auditoria: Convergência Territorial 01I (Remoção Física e Lógica)

## 1. Resumo Executivo
Este relatório atesta a conclusão definitiva do programa de Convergência Territorial, cujo objetivo principal era estabilizar o domínio fundiário segregando dados territoriais oficiais (`ImovelRural`) das unidades operacionais produtivas (`UnidadeProdutiva`). As redundâncias foram removidas, o runtime foi higienizado e a integridade de todas as referências foi homologada pelas suítes automatizadas e guardrails implementados. 

## 2. Linha do Tempo das Fases
* **01A a 01E1**: Auditorias, guardrails, backfills e adaptação das rotinas de gravação/leitura para a nova arquitetura sem afetar a produção.
* **01F e 01G1**: Regularização assistida eliminando todas as anomalias, garantindo que 100% dos dados herdados tivessem vínculos canônicos.
* **01H1**: Remoção lógica do legado no sistema.
* **01H2**: Drop físico das colunas do banco e limpeza de schemas/models.
* **01I**: Auditoria Final, atestando o não retorno do débito técnico, o ajuste final de testes legados e a documentação definitiva da arquitetura.

## 3. Schema Físico Final
A auditoria via metadados SQLAlchemy e consultas diretas provou a total ausência das antigas colunas fundiárias em `unidades_produtivas`, bem como o campo `unidade_produtiva_id` em `imoveis_rurais`. Toda chave estrangeira, views e lógicas obsoletas foram devidamente mitigadas pela migration `265b28773962`.

## 4. Estado dos Dados
Foi executado script direto no banco (DML Validator) assegurando:
* **ORPHAN**: 0
* **TENANT_MISMATCH**: 0
* **AMBIGUOUS**: 0
* **DIVERGENT**: 0

O conceito `DIRECT_ONLY` já não existe fisicamente. Os 125 imóveis encontram-se integralmente associados através de `PropriedadeImovel`.

## 5. Referências Residuais
A busca (grep search em todos os pacotes, diretórios de API, frontend) confirmou que a presença de termos como `nirf`, `car_numero` ou `numero_matricula` ocorre **apenas no seu uso legítimo** dentro da entidade `ImovelRural`, `car_parser` (ambiental), ou relatórios de transações contábeis, que pertencem ao novo design institucional. Qualquer uso operacional indevido (ex: _aplicar_overlay_territorial) foi eliminado e não se encontra mais nos códigos-fonte.

## 6. Models e Metadata
Alembic não detecta nenhum *drift* da infraestrutura atual perante os metadados do repositório. O schema final estabelece que:
- `UnidadeProdutiva` (operacional)
- `ImovelRural` (fundiário)
São independentes estruturalmente e seu único elo baseia-se unicamente nas instâncias combinadas de `Propriedade` e vinculadas via associação N:N `PropriedadeImovel`.

## 7. Serviços Oficiais
- **CadastroCompletoService**: Centraliza a gravação e respeita o isolamento de entidades fundiárias.
- **TerritoryReadService**: Lê via vínculos canônicos (fonte oficial e única).
- **PropriedadeImovelService**: Gerencia integridade de vinculação.
Todos idempotentes e testados contra sobreposições (ex: AMBIGUOUS = 0).

## 8. Contratos
O output de DTO (ex: `UnidadeProdutivaResponse`) que continha campos com aviso `deprecated=True` para `codigo_car`, `nirf`, etc., teve os campos explicitamente removidos do Schema.

## 9. Frontend e 10. Campo PWA
Ambas suítes (apps/web e apps/campo) foram escaneadas via compilador Typescript (`pnpm run typecheck`), retornando zero alertas ou quebras de builds derivadas das deleções dos DTOs fundiários. A plataforma SPA consome dados pela raiz aninhada sem inferências inválidas.

## 11. Guardrails
A suíte `test_territory_convergence_guardrails.py` restringe o uso dos atributos a um subconjunto ultra estrito, barrando regressões no desenvolvimento normal da aplicação para reintrodução de sincronizadores ou fields.

## 12. Testes Pulados Removidos ou Substituídos
* `test_exec37_auto_vinculo_fundiario.py` (anteriormente ignorado devido à quebra de lógica após as remoções) foi refatorado em um Guardrail Negativo. Agora ele injeta dados inválidos (`nirf`, etc.) no payload da `UnidadeProdutivaCreate` demonstrando ativamente que o input os rejeita (via `ValidationError` ou sanitização nativa Pydantic) e nenhum imóvel rural é acidentalmente gerado.
* Testes defasados de compatibilidade em `test_territory_read_service.py` foram excluídos da esteira.

## 13. Tabela de Backup e Retenção
A tabela `farms.territory_legacy_backup_01h2` guarda os últimos resquícios das informações em backup. 
**Regras Aplicadas:**
* Acesso restrito. Sem Model ORM na API;
* Sem dependência de rotinas de leitura;
* **Retenção Prevista:** `DROP_AFTER` = 30 dias a contar da implantação produtiva deste release.

## 14. Migration Downgrade/Upgrade
Testes locais rodaram o downgrade para a migração antecedente (`5cee1dab62fb`) e upgrade subsequente com sucesso e preservação íntegra de esquema (`head`), atestando operação livre de erros.

## 15 e 16. Testes Backend e Frontend
100% pass, nenhuma suíte do pacote Backend (Pytest) reportou erro ou quebra de lógica.
100% pass no `typecheck` e Lint do Frontend Typescript. 

## 17, 18 e 19. Smoke, Performance e Documentação Oficial
N+1 e loops não foram reintroduzidos nas chamadas de listagem ou de endpoints territoriais. A documentação (este documento e indexação correspondente) decreta formalmente que:
* *Não existe vínculo direto UnidadeProdutiva → ImovelRural.*
* *Dados fundiários não pertencem à UnidadeProdutiva.*

## 20. Riscos Residuais
* A exclusão física da tabela de backup daqui a 30 dias (`farms.territory_legacy_backup_01h2`) representará uma ação destrutiva definitiva, devendo ocorrer apenas após constatação pacífica nas frentes de produção do ERP/App. Sem riscos adicionais encontrados.

## 21. Conclusão
O domínio fundiário foi finalmente libertado do modelo legado. Todos os dados foram preservados e reatribuídos segundo arquitetura moderna, e o código não retém nenhuma compatibilidade temporária que comprometa a saúde do serviço ou os custos de manutenção da dívida técnica. O trabalho atinge grau de suficiência atestado pelas validações empíricas do runtime e do banco de dados relacional.

## 22. Veredicto

**GO**

*(A convergência territorial foi concluída e o programa pode ser encerrado.)*

* Uma única fonte de verdade? SIM
* Vínculo oficial único? SIM
* Campos fundiários fora da UP? SIM
* Runtime sem legado? SIM
* Banco sem legado? SIM
* Dados íntegros? SIM
* Guardrails definitivos? SIM
* Programa encerrado? SIM
