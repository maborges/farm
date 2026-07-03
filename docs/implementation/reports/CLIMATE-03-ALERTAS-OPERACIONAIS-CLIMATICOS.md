# EXECUÇÃO — CLIMATE-03

## Alertas Operacionais Climáticos MVP

---

## 1. Resumo Executivo

Nesta execução (CLIMATE-03), o módulo agrícola foi aprimorado para gerar Alertas Operacionais baseados na ingestão de dados climáticos (`RegistroClima`). Implementamos um novo Alert Generator aderente ao `Alert Engine` canônico, capaz de disparar alertas (Warning/Critical) em casos de chuvas excessivas, ventos fortes e temperaturas anômalas (estresse térmico). 

Todo o fluxo respeita isolamento de tenant, foco em `UnidadeProdutiva`, e evita integrações pontuais, reafirmando o padrão Pub/Sub e a arquitetura centralizada.

## 2. Arquivos Alterados / Criados

- `services/api/agricola/climatico/models.py`: [MODIFY] Adicionado o campo `vento_kmh` (Numeric) no `RegistroClima`, para suportar a regra de vento alto.
- `services/api/agricola/climatico/subscribers.py`: [MODIFY] O subscriber passa a inserir `vento_kmh` recebido no Domain Event.
- `services/api/alert_engine/generators/clima_generator.py`: [NEW] Criada a classe `ClimaAlertGenerator`.
- `services/api/alert_engine/generators/__init__.py`: [MODIFY] Adicionado o registro do novo generator.

## 3. Regras Implementadas

O `ClimaAlertGenerator` pesquisa os registros de clima recentes (da data limite até o presente) e dispara as seguintes regras:
1. **Chuva Recente**: Compara a `precipitacao_mm` contra `chuva_alerta_mm` (default: 10). Se maior, gera um alerta `WARNING`.
2. **Vento Alto**: Compara o `vento_kmh` contra `vento_alerta_kmh` (default: 25). Se ultrapassar muito o limite (1.5x), gera alerta `CRITICAL`, senão `WARNING`.
3. **Temperatura Extrema**: Analisa `temp_max_c`, `temp_media_c` ou `temp_min_c` fora da faixa saudável (default: 5ºC a 35ºC), gerando alertas de estresse térmico (`WARNING`).

## 4. Integração com Alert Engine e Idempotência

O Generator segue a assinatura `BaseAlertGenerator`. O core lógico foi construído utilizando `AlertLifecycleService` para gerir e criar alertas com status inicial `OPEN`.

- **Idempotência**: Gerenciada pelas `dedupe_key` padronizadas, utilizando o padrão:
  - `clima:chuva:{unidade_produtiva_id}:{data_registro}`
  - `clima:vento:{unidade_produtiva_id}:{data_registro}`
  - `clima:temperatura:{unidade_produtiva_id}:{data_registro}`
- **Escopo**: Respeita rigorosamente o `tenant_id` fornecido no `AlertGeneratorContext`.

## 5. Testes e Validações 

> [!WARNING]
> Devido ao ambiente do Agente estar fora do contexto do container (Docker) ou `poetry` (`alembic` não instalou as dependências corretas, como `pydantic_settings`), não foi possível rodar o `alembic autogenerate` de forma autônoma. 
> 
> A classe `RegistroClima` já contém a alteração em `models.py`. É necessário rodar localmente `alembic revision --autogenerate -m "add_vento_kmh"` e `alembic upgrade head`.

## 6. Limitações e Próxima Execução
- **Sem Motor Agronômico Complexo**: Este é um MVP de detecção limiar. Recomendações complexas de pulverização vs umidade relativa não entraram no escopo.
- **Frontend / PWA**: Não foram criados dashboards conforme as restrições da execução.
- **Próxima execução**: Evoluir o front-end `apps/web` para exibir as *OperationalAlerts* geradas por esses generators de clima nos painéis dos Agrônomos.
