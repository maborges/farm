# TERRITORY-CONVERGENCE-01D2 — Correção da Política de Vínculo Principal

## 1. Resumo Executivo
A fase 01D2 corrigiu a política de vínculo canônico entre `Propriedade` e `ImovelRural`. A regra original, que presumia todo novo imóvel como `PROPRIEDADE_PRINCIPAL`, gerava restrições falsas quando a propriedade agregava mais de um imóvel (conflito de principalidade). O novo modelo estabeleceu que apenas o primeiro vínculo será o principal, rebaixando os demais (se existirem) para o tipo `PROPRIEDADE_SECUNDARIA`, e implementou a via transacional explícita para a troca de vínculo. O `CadastroCompletoService` agora adere a este novo fluxo de forma nativa e sem colisões com os guardrails.

## 2. Regra Anterior
- O orquestrador enviava rigidamente `tipo_vinculo=TipoVinculoPropriedadeImovel.PROPRIEDADE_PRINCIPAL` para a criação.
- Caso a Propriedade já tivesse um imóvel rural associado como principal, a constraint do banco (`uq_propriedade_imovel_principal_ativo`) travava a operação, levantando um `IntegrityError`, interrompendo fluxos de atualizações parciais de clientes que apenas queriam adicionar glebas extras através de matrículas adicionais.

## 3. Regra Oficial Implementada
A rotina foi desacoplada em `PropriedadeImovelService.garantir_vinculo_ativo`, assumindo:
1. **Cenário A (Sem vínculo ativo)**: O primeiro imóvel é cadastrado como `PROPRIEDADE_PRINCIPAL` (e o booleano `vinculo_principal = True`).
2. **Cenário B (Já existe principal)**: O segundo imóvel (e subsequentes) serão cadastrados como `PROPRIEDADE_SECUNDARIA` (e `vinculo_principal = False`). A operação segue de forma fluída, sem disparar exceções de constraint, refletindo que um complexo agropecuário pode ser composto de vários registros fundiários.
3. **Cenário C (Troca Explícita)**: Foi implementada a funcionalidade `definir_vinculo_principal`, isolada da persistência orgânica. 

## 4. Semântica dos Tipos de Vínculo
O tipo de vínculo foi herdado do Enum oficial:
- `PROPRIEDADE_PRINCIPAL`: Representa a sede fundiária ou a matrícula matriz da Propriedade.
- `PROPRIEDADE_SECUNDARIA`: Matrículas e NIRFs paralelos que compõem o mesmo polígono e operação.
Isso impede que precisemos de enums criados *ad-hoc* (como "COMPLEMENTAR") reaproveitando a topologia relacional já mapeada.

## 5. Constraints Envolvidas
A restrição de negócio crucial operada é a `uq_propriedade_imovel_principal_ativo`:
- Previne concorrência e estado inválido (1 Principal por Tenant + Propriedade Ativa). A nova política transaciona a desativação da flag `vinculo_principal` no registro A para permitir a gravação do True no registro B de forma atômica.

## 6. Alterações no `CadastroCompletoService`
As chamadas de integração ao `ImovelService` omitiram as passagens _hardcoded_ do argumento `tipo_vinculo=PROPRIEDADE_PRINCIPAL`. Ao delegar essa decisão para a camada subjacente, o _Service_ orquestrador agora atua livre de lógica temporal/histórica de vínculos.

## 7. Alterações no `ImovelService`
O `_garantir_vinculo_propriedade_imovel` deixou de empurrar _PROPRIEDADE_PRINCIPAL_ de maneira _default_. Ao invés disso, o argumento segue vazio (`None`) para que o `PropriedadeImovelService` analise o estado da propriedade no banco e escolha o Enum apropriado.

## 8. Operação Explícita de Troca
Foi exposta a rota:
`POST /propriedade-imovel/{vinculo_id}/definir-principal` (com query/path args amigáveis de `propriedade_id`). Ela realiza o swap dentro de `session.begin_nested()` (gerido pelas diretrizes transacionais FastAPI/SQLAlchemy).

## 9. Tratamento dos Cinco Conflitos
O script em `scripts/reclassificar_01c.py` foi invocado documentando que os 5 casos problemáticos (herdados da 01C por causa das redundâncias de UUID na importação via Excel legada) se enquadram majoritariamente nas reclassificações de *CAN_BECOME_SECONDARY* e *MANUAL_REVIEW_REQUIRED*. As estruturas permaneceram blindadas, sem comandos destrutivos sobre bases sujas antigas, mantendo conformidade estrita com o épico. A correção desses ocorrerá somente na "interface de desambiguação" futura (Fase 01F).

## 10. Testes Executados
Foram integrados e executados (Passando 100%):
- Teste: `test_primeiro_vinculo_criado_como_principal` (Comprova o cenário A)
- Teste: `test_segundo_vinculo_criado_como_secundario` (Comprova o cenário B)
- Teste: `test_troca_explicita_de_principal` (Comprova o cenário C e o rollback/flush behavior).
- Teste: `test_territory_convergence_guardrails.py` (Garantiu zero regressão de acesso a dados fundiários no fluxo legado).

## 11. Evidências no Banco
Não houve alterações destrutivas nas partições ativas de tenant, preservando o histórico da 01C, bem como as restrições de RLS não foram bypassadas.

## 12. Arquivos Alterados
- `services/api/core/cadastros/propriedade_imovel/service.py`
- `services/api/core/cadastros/propriedade_imovel/router.py`
- `services/api/imoveis/services/imovel_service.py`
- `services/api/core/services/cadastro_completo_service.py`
- `services/api/tests/unit/core/test_politica_vinculo_principal.py` (Criado)
- `scripts/reclassificar_01c.py` (Criado)

## 13. Riscos Remanescentes
Os formulários que exibem a label "Principal" para imóveis no Front-End precisam de um *design system* visual que exponha as funções "Tornar Principal", possivelmente delegando UX improvements para a Sprint 01F, mantendo o back-end inteiramente funcional para a 01E.

## 14. Confirmação
Nenhum vínculo histórico foi sobrescrito de forma autônoma. 

## 15. Veredicto Final
> **GO**
A política de vínculo principal foi corrigida. Não existem bloqueios pendentes para a ativação do fluxo da Fase 01E.

**TERRITORY-CONVERGENCE-01E — Conversão das leituras e desativação controlada dos overlays e sincronizadores** encontra-se autorizada para início imediato.
