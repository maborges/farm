# 09 — Roadmap de Implementação

## Fase 0 — Discovery e consolidação

**Objetivo:** fechar decisões antes de modelar.

- inventariar entidades `operacional_qualidade_*`;
- definir ownership canônico;
- escolher commodity-piloto;
- obter protocolo oficial e política comercial;
- definir dicionário de dados e unidades;
- confirmar runtime e endpoints existentes;
- criar fixtures de qualidade reais anonimizadas.

**Gate:** protocolo aprovado, entidades sem duplicidade e dados de teste disponíveis.

## Fase 1 — MVP de classificação

- protocolos e critérios versionados;
- amostras, medições e laudos;
- motor determinístico;
- classificação explicável;
- aprovação/reprovação;
- telas Web;
- auditoria e testes.

**Gate:** classificar uma commodity de ponta a ponta sem integração financeira.

## Fase 2 — Lote e operação

- integração com romaneio, ProdutoColhido e beneficiamento;
- múltiplas amostras;
- reanálise;
- perdas e rendimento;
- bloqueio de lote;
- importação de laudos;
- relatórios por safra, talhão e lote.

**Gate:** lote aprovado/reprovado com histórico e saldo físico preservado.

## Fase 3 — Comercial e estoque

- descontos e bonificações parametrizados;
- valuation por lote;
- integração com estoque;
- integração com comercialização/financeiro;
- regras de mistura e expedição.

**Gate:** impacto econômico reproduzível e aprovado pelo cliente-piloto.

## Fase 4 — PWA e equipamentos

- coleta offline;
- sincronização e conflitos;
- balança/medidor/laboratório;
- calibração e validade;
- evidência original da medição.

**Gate:** operação em rede rural intermitente e dispositivo real.

## Fase 5 — Enterprise e IA

- cadeia de custódia;
- padrões por comprador;
- passaporte QR;
- API de parceiros;
- detecção de anomalias;
- classificação assistida por IA;
- BI multi-propriedade.

**Gate:** validação estatística, técnica e contratual antes de qualquer claim de acurácia.

## Ordem de prioridade

`Fase 0 → Fase 1 → Fase 2 → Fase 3 → Fase 4 → Fase 5`.

O módulo pode ser lançado comercialmente ao final da Fase 1, desde que seu posicionamento seja “classificação por protocolos e regras”, não “IA autônoma”.
