# 08 — Testes e Critérios de Aceite

## Testes unitários

- limites inclusivos e exclusivos;
- unidade e conversão;
- critério obrigatório ausente;
- enum inválido;
- regra conflitante;
- arredondamento;
- desconto que excede peso;
- protocolo inativo ou versão antiga;
- idempotência da avaliação;
- reanálise sem sobrescrever histórico.

## Integração

- laudo vinculado somente a lote do mesmo tenant;
- romaneio → produto colhido → qualidade;
- beneficiamento com entrada/saída e perdas;
- bloqueio de lote reprovado;
- desconto sem alterar ledger físico;
- publicação de evento/outbox;
- importação parcial com relatório de erros;
- RLS real no PostgreSQL.

## E2E

1. cadastrar protocolo;
2. receber lote;
3. coletar amostra;
4. registrar medições;
5. avaliar automaticamente;
6. revisar/aprovar;
7. calcular ajuste;
8. consultar lote no estoque/comercialização;
9. gerar passaporte, se contratado;
10. auditar toda a cadeia.

## Definition of Done

- migrations revisadas e reversíveis;
- schemas, services e routers canônicos;
- cobertura de regras críticas;
- testes cross-tenant;
- sem `any` ou `ts-ignore` no frontend;
- PWA offline validado quando incluído;
- documentação e routing map atualizados;
- telemetria e logs disponíveis;
- nenhum ajuste financeiro sem justificativa;
- revisão técnica e aceite de produto concluídos.
