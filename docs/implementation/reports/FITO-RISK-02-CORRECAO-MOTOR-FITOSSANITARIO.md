# FITO-RISK-02 — Correção de segurança e consistência do motor fitossanitário

**Data:** 2026-10-30  
**Escopo:** correções técnicas para deixar o motor pronto para futura validação agronômica. Nenhuma regra epidemiológica foi criada ou homologada.

## Resumo e veredicto

O motor convertia dados inteiramente ausentes em zeros, permitia que uma regra de tenant ocultasse todas as regras globais da cultura, e expunha um score heurístico sob o nome de probabilidade de doença. Também não distinguia os motivos pelos quais não havia resultado e aceitava configurações JSON sem validação suficiente.

Esses pontos foram corrigidos preservando os campos públicos antigos como aliases depreciados e adicionando campos/estado explícitos. A interface passou a chamar o valor de favorabilidade climática e informa que ele não é probabilidade nem diagnóstico.

**Veredicto: GO COM RESSALVAS para avançar à validação agronômica.** Os testes técnicos passaram, mas as regras, variáveis epidemiológicas e limiares ainda precisam de fundamentação e aprovação agronômica. O recurso não está homologado para orientar diagnóstico ou aplicação de defensivos.

## Diagnóstico confirmado

- `_calcular_stats_climaticas()` inicializava cada variável em zero e calculava estatísticas sem exigir amostras válidas. Assim, campo ausente podia parecer condição climática observada.
- `_calcular_risco_doencas()` escolhia regras do tenant como conjunto preferencial da cultura. Uma regra específica podia, portanto, suprimir regras globais de outras doenças. As consultas também precisavam explicitar o tenant para garantir isolamento.
- O score é a soma ponderada das condições satisfeitas, normalizada pelo total dos pesos. Não é uma probabilidade epidemiológica calibrada. A API e a interface apresentavam `probabilidade_pct` como tal.
- Resultados vazios não identificavam se faltava cultura, modelo aplicável ou histórico climático. A lista vazia podia ser interpretada visualmente como baixo risco.
- `regras_risco` não validava suficientemente variáveis, operadores, finitude e coerência dos intervalos, pesos e limiares.

## Correções aplicadas

### Dados climáticos

As estatísticas agora preservam `None` quando não há observações válidas e mantêm zero quando zero foi medido. Valores não finitos ou fora de limites físicos amplos são classificados como inválidos. A avaliação de uma regra não produz score se alguma variável exigida estiver indisponível. Também se exige janela mínima de sete datas distintas, correspondente à janela técnica já usada pelo serviço; isso não constitui limiar epidemiológico validado.

### Precedência e isolamento

Regras agora são resolvidas pela chave `(cultura, doença)`: a regra do tenant substitui apenas a regra global da mesma combinação, mantendo regras globais das demais doenças. Consultas de tenant são explicitamente limitadas ao tenant atual, e regras globais a `tenant_id IS NULL`.

### Resultado e contrato

O score é representado como `favorabilidade_pct`, com `nivel_favorabilidade`. Foram adicionados estados explícitos para ausência de cultura, ausência de modelo, dados insuficientes ou inválidos, configuração inválida, resultado parcial e cálculo concluído. Os campos antigos `probabilidade_pct` e `nivel` permanecem como aliases depreciados para compatibilidade, documentados como score/nível heurístico e não como probabilidade ou severidade da doença. O frontend usa os novos campos e não recomenda defensivos.

O estado é aditivo no contrato da resposta; consumidores antigos podem continuar usando os aliases durante a transição. A remoção futura desses aliases exigirá decisão de versionamento. Recomenda-se publicar API e frontend em conjunto para que a interface utilize a semântica nova.

### Validação de regras

Os schemas validam variáveis e operadores permitidos, condições não vazias, valores numéricos finitos, intervalos ordenados, limites físicos básicos, pesos positivos e thresholds percentuais coerentes e ordenados. A mesma validação é aplicada defensivamente ao avaliar/copiar configuração persistida. Os limites de temperatura implementados são apenas validações físicas de entrada; não são parâmetros de doença. Os thresholds de classificação existentes foram preservados, sem atribuir-lhes validade agronômica.

## Arquivos alterados

- `services/api/agricola/climatico/service.py` — preservação de ausências, validação defensiva, precedência por cultura/doença, isolamento, estados e representação do score.
- `services/api/agricola/climatico/schemas.py` — validação de JSON e extensão compatível dos schemas de resposta.
- `services/api/tests/unit/agricola/test_clima_fitossanitario_contract.py` — novos testes direcionados de contrato e regressão.
- `services/api/tests/unit/agricola/test_clima_inteligencia_rules.py` — adequação dos testes existentes à distinção de variável ausente e peso inválido.
- `apps/web/src/lib/agricola/clima-api.ts` — tipos dos novos campos/estados e documentação dos aliases antigos.
- `apps/web/src/components/clima/inteligencia/agricultura/risco-doencas.tsx` — apresentação de favorabilidade e estados sem cálculo.
- `apps/web/src/app/(dashboard)/dashboard/agricola/clima/inteligencia/inteligencia-dashboard-client.tsx` — propagação do estado nos caminhos com e sem dados.

## Verificações executadas

- Testes direcionados (`test_clima_fitossanitario_contract.py`, `test_clima_inteligencia_rules.py`, `test_climatico_service.py`): **29 passed**.
- Ruff nos arquivos Python alterados, ignorando apenas `E501`, `W291` e `W293`: **All checks passed**.
- Compilação dos arquivos Python alterados com `compileall`: **passou**.
- `npm run typecheck` no frontend: **passou**.
- `git diff --check`: **passou**.

O Ruff sem filtros ainda aponta 29 ocorrências dessas três categorias no serviço. A comparação com a versão HEAD anterior à alteração apontou 37 ocorrências da mesma natureza; são problemas preexistentes de comprimento de linha e whitespace, fora do escopo desta correção. Não foram feitas alterações para limpar esses avisos não relacionados.

## Pendências e riscos remanescentes

- Não há regras fitossanitárias aprovadas nesta etapa. Cada combinação cultura/doença e seus dados precisam de fonte técnica identificável e validação por profissional habilitado.
- A janela de sete datas é uma proteção de suficiência técnica, não uma recomendação agronômica.
- O score permanece heurístico e não estima incidência, severidade ou probabilidade de doença. Não deve motivar aplicação de defensivos.
- Os aliases públicos antigos permanecem por compatibilidade; consumidores devem migrar para `favorabilidade_pct`, `nivel_favorabilidade` e o estado explícito antes de eventual remoção.
- Não foram acessados bancos, executados seeds, criadas migrations ou realizados deploy, commit ou push.

## Próximo passo

Avançar à validação agronômica com combinações cultura/doença sustentadas por fontes técnicas e critérios de teste independentes. Somente regras aprovadas nessa validação devem ser configuradas futuramente. A aprovação técnica desta etapa não equivale à homologação agronômica do recurso.
