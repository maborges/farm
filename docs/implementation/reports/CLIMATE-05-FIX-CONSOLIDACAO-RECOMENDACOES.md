# CLIMATE-05-FIX: Consolidação do Motor de Recomendações

Este relatório documenta a execução de padronização (CLIMATE-05-FIX), eliminando duplicações e unificando o comportamento do módulo de clima.

## 1. Auditoria dos Thresholds
Ao inspecionar o `ClimaAlertGenerator` e o `ClimaRecommendationService`, foi constatado que os *thresholds* lógicos utilizados eram idênticos na prática, porém estavam definidos de forma separada (*hardcoded* / números mágicos).
- **Vento**: 25.0 km/h (Ambos os motores usavam esse limite para alertar/bloquear operações).
- **Chuva**: 10.0 mm (Ambos usavam 10 mm como limite base).
- **Temperatura**: Mínima de 5.0 °C e máxima de 35.0 °C. O *Alert Engine* tinha os números diretos, enquanto o *Recommendation Service* apenas reagia à presença do alerta de Temperatura Extrema.

**Veredito:** Eram numericamente iguais, mas a separação gerava risco de divergência futura caso um fosse atualizado e o outro não.

## 2. Padronização e Refatoração (Thresholds)
Foi criado o arquivo de configuração oficial focado nas regras de negócio climáticas.

**Arquivo criado**: `services/api/agricola/climatico/config.py`
```python
class ClimaThresholds:
    CHUVA_ALERTA_MM = 10.0
    VENTO_ALERTA_KMH = 25.0
    TEMPERATURA_MIN_C = 5.0
    TEMPERATURA_MAX_C = 35.0
```

Tanto o *Recommendation Engine* quanto o *Alert Engine* foram refatorados para importar e depender diretamente do `ClimaThresholds`, garantindo 100% de consistência na plataforma. Se houver uma alteração de limite de vento no futuro (ex: para 30 km/h), os alertas e recomendações responderão no mesmo instante.

## 3. Fixtures RLS (Row-Level Security)
Anteriormente, os testes de *Recommendation Engine* precisavam executar manualmente `SET app.current_tenant_id = ...` para que a inserção na tabela `operational_alerts` não fosse bloqueada pelo banco de dados (que exige o tenant_id ativo na sessão para operações seguras).

**Solução:**
1. Criada a fixture compartilhada `tenant_session` em `services/api/tests/fixtures/tenant_context.py`. Ela intercepta o `session` do SQLAlchemy e define o contexto RLS apropriado na injeção.
2. Registramos a rota do plugin no `conftest.py` principal: `pytest_plugins = ["tests.fixtures.tenant_context"]`.
3. Os arquivos `test_recommendation_service.py` e `test_climatico_service.py` foram totalmente migrados para consumir `tenant_session` diretamente, eliminando mais de 5 blocos de SQL cru duplicados.

## 4. Testes e Validação
Foi executada a bateria de testes (`pytest services/api/tests/unit/agricola`, `pytest services/api/tests/unit/alert_engine`) e checagem estática com `ruff`.
- Foi verificado que os testes do `alert_engine` funcionaram mantendo a mesma semântica após utilizar a constante (embora os testes originais do alert_engine possuam alguns problemas de *test-pollution* preexistentes em função de usarem `.commit()` explicitamente, não relacionados a esta alteração).
- O `ClimaRecommendationService` passou integralmente após a migração para as novas fixtures e constantes.
- O isolamento Multi-Tenant original do SQLAlchemy permaneceu intacto.

## 5. Próximos Passos
Esta consolidação deixa a base climática segura para a importação para os fluxos Mobile (`apps/campo`), pois não há mais limites vazando entre os serviços ou dependências manuais inconsistentes.
