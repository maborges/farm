# Step 35 - Normalização de Tier Enterprise

## Decisão

- `ENTERPRISE` passa a ser o nome oficial do tier topo.
- `PREMIUM` permanece apenas como alias legado de leitura.

## Escopo aplicado

- Backend: `PlanTier.ENTERPRISE` adicionado e `PlanTier("PREMIUM")` continua aceito.
- Frontend: o store normaliza valores antigos para `ENTERPRISE`.
- Gates novos e mensagens de UI foram migrados para `ENTERPRISE`.

## Regra de manutenção

- Novos gates, textos e documentação devem usar `ENTERPRISE`.
- `PREMIUM` só deve aparecer em camadas de compatibilidade ou migração.
