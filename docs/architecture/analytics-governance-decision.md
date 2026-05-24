# Decisão de Governança Analítica

## Contexto

O ciclo de infraestrutura analítica do AgroSaaS evoluiu em etapas sucessivas:

- Step 38: memoização request-scoped para a cadeia analítica.
- Step 39 e Step 39.2: otimização estrutural da DRE agrícola v1.
- Step 40 e Step 40.2: registry canônico de severidade, códigos e taxonomia analítica.
- Step 41: medição objetiva do fan-out residual da cadeia.

A cadeia oficial permanece:

`DRE -> KPIs -> Rentabilidade -> Eficiência -> Benchmark -> Diagnóstico -> Recomendações -> Prioridades`

## Medição Observada

A instrumentação request-scoped mostrou que:

- a recomputação redundante dentro da mesma request foi mitigada;
- a DRE direta apresenta hit/miss coerente;
- a Central de Prioridades reutiliza cache em chamadas repetidas;
- ainda existe fan-out residual na primeira execução da cadeia;
- o custo remanescente está concentrado na primeira execução, não em recomputações evitáveis.

## Decisão

O próximo passo arquitetural **não** é criar read-model, snapshot persistido ou projeção materializada.

A decisão vigente é:

- manter a arquitetura atual;
- monitorar o comportamento real em produção;
- adiar read-model/projeção leve até haver evidência operacional suficiente.

## Motivo

A otimização request-scoped já atacou o principal problema estrutural observado até aqui: recomputação redundante na mesma request.

O custo residual identificado no Step 41 está concentrado na primeira execução da cadeia analítica. Isso caracteriza um custo inerente ao caminho atual, mas ainda não justifica, por si só, a introdução de uma camada persistida de leitura.

## Gatilhos Para Reavaliar Read-Model

Reavaliar a criação de um read-model ou projeção leve apenas se houver evidência consistente de um ou mais dos cenários abaixo:

- latência real elevada em produção;
- tenants com alto volume e recorrência de consultas;
- múltiplas chamadas analíticas repetidas por request ou por sessão;
- dashboards executivos com agregações pesadas;
- necessidade de histórico comparativo persistido;
- crescimento de fan-out acima do que a memoização request-scoped e a DRE otimizada conseguem absorver.

## O Que Não Fazer Agora

- Não criar Redis.
- Não criar snapshot persistido.
- Não criar CQRS.
- Não criar event sourcing.
- Não criar read-model sem métrica real.
- Não fazer micro-otimizações sem evidência operacional.

## Diretriz

Para o próximo ciclo, a postura padrão é:

1. observar métricas reais de uso;
2. preservar contratos públicos e a semântica econômica;
3. só então decidir se a evolução correta é read-model, projeção leve ou apenas monitoramento contínuo.
