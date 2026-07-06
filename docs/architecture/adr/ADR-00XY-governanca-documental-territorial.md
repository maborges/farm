# ADR-00XY - Governanca Documental Territorial

Status: Aprovado
Data: 2026-06-21
Autores: AgroSaaS Architecture / Codex

## 1. Contexto

As fases anteriores da convergencia territorial/fundiaria estabeleceram:

- `Propriedades` como dominio operacional, territorial e produtivo;
- `Imoveis Rurais` como dominio juridico, patrimonial, documental e fiscal;
- `PropriedadeImovel` como unica entidade oficial de vinculacao N:N;
- `AGRI-DOMAIN-001` e `AGRI-DOMAIN-002` como normas imutaveis.

Apesar disso, o codigo ainda possui espelhos historicos e pontos de leitura legados para documentos e identificadores fundiarios. A plataforma precisa consolidar a governanca documental sem promover nova duplicidade de fonte da verdade e sem introduzir migracao adicional neste momento.

## 2. Problema

Sem uma norma documental complementar, o AgroSaaS corre os seguintes riscos:

- tratar espelhos legados como se fossem fonte oficial;
- permitir que um mesmo documento seja representado em mais de um dominio como verdade primaria;
- abrir espaco para futuras migracoes desnecessarias;
- enfraquecer ESG, certificacoes, Due Diligence e Projeto Raizes por ambiguidade documental.

## 3. Decisao

O AgroSaaS adota oficialmente a seguinte governanca documental:

1. `Imoveis Rurais` e a fonte oficial dos documentos fundiarios e juridicos.
2. `Propriedades` e a fonte oficial das evidencias operacionais e territoriais.
3. `PropriedadeImovel` e apenas a fonte oficial do vinculo entre os dominios.
4. `PropriedadeImovel` nao armazena documentos integrais, matriculas completas, cartorios completos, CAR, CCIR, ITR, NIRF, SIGEF ou arquivos binarios.
5. Espelhos historicos em `unidades_produtivas` e `cadastros_areas_matriculas` permanecem apenas como compatibilidade temporaria e nao podem ser tratados como nova fonte oficial.
6. Nenhuma nova migracao fisica e necessaria para esta fase.

## 4. Alternativas Consideradas

### Criar um novo dominio documental

- Rejeitado.
- Duplicaria a fronteira fundiaria ja consolidada.
- Criaria confusao de ownership.

### Concentrar documentos em Propriedades

- Rejeitado.
- Viola AGRI-DOMAIN-001.
- Mistura operacao com lastro legal.

### Concentrar documentos em PropriedadeImovel

- Rejeitado.
- A entidade e de vinculacao, nao de armazenamento documental completo.

### Manter a separacao atual com governanca formal

- Aprovado.
- Preserva as fronteiras normativas.
- Mantem compatibilidade com o legado.
- Exige apenas documentacao, testes de consistencia e disciplina de ownership.

## 5. Consequencias Positivas

- Cada dado possui uma unica fonte oficial.
- A trilha documental fica mais clara para auditoria.
- ESG e certificacoes passam a ter fronteiras consistentes.
- O Projeto Raizes herda uma cadeia rastreavel sem ambiguidade.
- O legado continua funcional sem nova migracao.

## 6. Consequencias Negativas

- Os espelhos historicos permanecem no sistema ate um ciclo futuro de saneamento.
- O time precisa respeitar a distinção entre leitura de compatibilidade e escrita oficial.
- Consultas legadas podem continuar exibindo campos repetidos ate o encerramento formal do legado.

## 7. Impacto no Banco

- Nenhuma nova tabela e necessaria.
- Nenhuma nova migration e necessaria nesta fase.
- A integridade depende de disciplina de ownership e da tabela existente `propriedade_imovel`.
- O saneamento futuro dos espelhos legados deve ser tratado como projeto separado.

## 8. Impacto nas APIs

- As APIs de `Imoveis Rurais` permanecem a fonte oficial de documentos.
- As APIs de `Propriedades` continuam expondo apenas o necessario para operacao e compatibilidade.
- `PropriedadeImovel` continua sendo apenas o contrato do vinculo.
- Nao ha necessidade de novo endpoint documental nesta fase.

## 9. Impacto no Frontend

- As telas devem continuar separando:
  - operacao territorial em `Propriedades`;
  - lastro documental em `Imoveis Rurais`;
  - relacao oficial em `PropriedadeImovel`.
- Campos espelhados legados devem ser tratados como leitura ou compatibilidade, nunca como edicao primaria.

## 10. Impacto em ESG

Esta decisao fortalece ESG porque:

- preserva prova documental em um dominio unico;
- evita conflito entre lastro legal e operacao;
- facilita auditoria de APP, Reserva Legal, CAR e documentos associados;
- melhora a confianca em relatórios e certificacoes.

## 11. Impacto no Projeto Raizes

O Projeto Raizes passa a depender de uma cadeia documental previsivel:

- producao -> safra -> talhao -> propriedade -> PropriedadeImovel -> Imovel Rural -> documentacao.

Isso reduz ambiguidades sobre origem, titularidade e compliance.

## 12. Plano de Implementacao

### Fase 1 - Consolidacao documental

- publicar a governanca documental;
- apontar campos legados como compatibilidade;
- registrar a fonte oficial de cada documento.

### Fase 2 - Disciplina de escrita

- manter escrita apenas na origem oficial;
- impedir duplicidade de edicao onde houver espelho.

### Fase 3 - Saneamento futuro

- avaliar, em ADR separada, a eventual remocao dos espelhos legados;
- somente entao planejar migracao fisica.

## 13. Critérios de Aceite

Esta ADR e considerada aderente quando:

- `Imoveis Rurais` for a fonte oficial documental;
- `Propriedades` for a fonte operacional;
- `PropriedadeImovel` for apenas o vinculo;
- nao existir nova migration para esta fase;
- a rastreabilidade conseguir chegar ao Imovel Rural;
- ESG, certificacoes e Projeto Raizes tiverem base documental clara.

## 14. Critérios de Rollback

A decisao documental deve ser revista se ocorrerem:

- divergencia entre a norma e a implementacao;
- tentativa de elevar espelho legado a fonte oficial;
- surgimento de novo armazenamento documental no vinculo;
- quebra de rastreabilidade ou de auditoria.

Rollback desta ADR significa voltar a explicitar a fronteira nos documentos, nao alterar banco.

## 15. Riscos

- Persistencia de espelhos legados durante o periodo de compatibilidade.
- Leitura incorreta por consumidores antigos.
- Ambiguidade em times que ainda tratem campo espelhado como master data.
- Futuras migracoes desnecessarias se a separacao documental nao for respeitada.

## 16. Proximas Etapas

1. Validar a matriz documental consolidada com o time tecnico.
2. Consolidar a lista de campos legados como leitura compatibilidade.
3. Manter `PropriedadeImovel` apenas como vinculo.
4. Adiar qualquer saneamento fisico de espelhos para um plano futuro aprovado.
5. Reforcar os testes de consistencia documental e governanca.
