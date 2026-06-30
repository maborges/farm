# TERRITORY-GOV-01 — Guardrails do Domínio Territorial e Operacional

## Resumo

Esta execução adiciona guardrails mínimos de governança para proteger a arquitetura oficial definida em `TERRITORY-ARCH-01`, sem remover legado, sem migrar dados e sem alterar contratos públicos.

## Guardrails criados

- Teste estático `services/api/tests/unit/test_territory_governance_guardrails.py` cobrindo:
  - `AreaRural` como árvore territorial oficial.
  - `Talhão` como `AreaRural.tipo = TALHAO`.
  - `Piquete` como `AreaRural.tipo = PIQUETE`.
  - `AreaOperacional` como tipo de `AreaRural`, não model próprio.
  - `PropriedadeImovel` como ponte canônica entre `Propriedade` e `ImovelRural`.
  - `ProductionUnit` como unidade agrícola oficial de safra/cultivo/área.
  - `UnidadeProdutiva` como unidade operacional, com campos fundiários apenas por compatibilidade.
- Comentários inline de compatibilidade legada em:
  - `services/api/core/models/unidade_produtiva.py`
  - `services/api/pecuaria/models/piquete.py`
  - `services/api/pecuaria/services/piquete_service.py`
  - `services/api/agricola/services/talhao_service.py`

## Arquivos tocados

- `services/api/core/models/unidade_produtiva.py`
- `services/api/pecuaria/models/piquete.py`
- `services/api/pecuaria/services/piquete_service.py`
- `services/api/agricola/services/talhao_service.py`
- `services/api/tests/unit/test_territory_governance_guardrails.py`
- `docs/implementation/reports/TERRITORY-GOV-01-GUARDRAILS-DOMINIO-TERRITORIAL.md`

## Legado explicitamente preservado

- `pec_piquetes` permanece como compatibilidade histórica.
- Campos fundiários legados em `UnidadeProdutiva` permanecem preservados.
- Alias histórico `Fazenda = UnidadeProdutiva` permanece preservado.
- Linguagem histórica de `fazenda` em payloads e UI continua fora de escopo nesta execução.

## Proibido para novos fluxos

- Criar model/tabela nova para `Talhão`.
- Criar model/tabela nova para `Piquete`.
- Transformar `AreaOperacional` em model/tabela própria.
- Criar vínculo direto novo entre `Propriedade` e `ImovelRural` fora de `PropriedadeImovel`.
- Usar `UnidadeProdutiva` como entidade fundiária/documental.
- Criar unidade agrícola analítica paralela fora de `ProductionUnit`.

## Validações executadas

- `pytest services/api/tests/unit/test_territory_governance_guardrails.py -q`
- `ruff check services/api/tests/unit/test_territory_governance_guardrails.py services/api/core/models/unidade_produtiva.py services/api/pecuaria/models/piquete.py services/api/pecuaria/services/piquete_service.py services/api/agricola/services/talhao_service.py` foi tentado, mas o binário `ruff` não está disponível neste ambiente.
- `git diff --check`

## Limitações

- Os guardrails são mínimos e majoritariamente estáticos; eles reduzem regressão estrutural, mas não substituem revisão arquitetural para novos fluxos maiores.
- Legados documentados continuam ativos por compatibilidade e ainda exigem disciplina para não serem ampliados.
