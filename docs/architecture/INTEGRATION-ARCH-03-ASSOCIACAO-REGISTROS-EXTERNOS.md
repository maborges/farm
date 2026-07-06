# INTEGRATION-ARCH-03 - Modelo Oficial de Associacao entre Registros do AgroSaaS e Sistemas Externos

Data: 2026-07-06

## 1. Objetivo

Definir o modelo oficial do AgroSaaS para associar registros locais a registros equivalentes em sistemas externos.

Esta decisao nasce no contexto da integracao Sankhya, mas nao deve ser tratada como uma solucao exclusiva do Sankhya. O modelo precisa servir para ERPs, bancos, fiscal, plataformas de cobranca, sistemas de BI e qualquer integracao futura que exija reconhecer que dois registros representam a mesma informacao de negocio.

Este documento nao implementa tabelas, migrations, endpoints ou contratos. Ele registra a decisao arquitetural recomendada para uma etapa posterior de implementacao.

## 2. Documentos revisados

- `docs/implementation/reports/SANKHYA-SYNC-04-AUDITORIA-VINCULO-REGISTROS-AGROSAAS-SANKHYA.md`
- `docs/implementation/reports/INTEGRATION-DOMAIN-01-AUDITORIA-ENTIDADES-INTEGRACAO.md`
- `docs/implementation/reports/SANKHYA-SYNC-01-ESCOPO-PILOTO-CAFE.md`
- `docs/implementation/reports/SANKHYA-SYNC-02-MAPEAMENTO-CANONICO.md`
- `docs/implementation/reports/SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md`
- `docs/implementation/reports/SANKHYA-AUTH-03-VALIDACAO-ESPECIFICACAO-TECNICA.md`
- `docs/implementation/reports/integracao_sankhya_especificacao_tecnica.md`
- `docs/architecture/INTEGRATIONS-ARCH-01.md`
- `docs/architecture/INTEGRATIONS-ARCH-02.md`
- `docs/implementation/reports/INTEGRATIONS-DOMAIN-02-ESPECIFICACAO-MATERIALIZACAO.md`
- `services/api/integracoes/models.py`
- `services/api/integracoes/sankhya/models/__init__.py`
- `services/api/integracoes/sankhya/services/sync_service.py`
- `services/api/integracoes/sankhya/services/nfe_financeiro_service.py`
- `services/api/integracoes/sankhya/services/canonical_adapter.py`

## 3. Problema atual

O AgroSaaS ja possui um dominio de integracoes com configuracao, credenciais, jobs, health, features, policies, logs, adapter Sankhya e autenticacao Gateway-first.

O Sankhya tambem possui tabelas de staging ou espelho para pessoas, produtos, NFe, lancamentos financeiros e tabelas auxiliares. Essas tabelas armazenam identificadores externos como `CODPARC`, `CODPROD`, `DESDOB`, `CHAVEACESSO` e outros codigos do ERP.

A lacuna arquitetural e outra: ainda nao existe um modelo oficial e reutilizavel para declarar que um registro de negocio do AgroSaaS corresponde a um registro existente em um sistema externo.

Exemplo:

- `sankhya_pessoas.sankhya_id = CODPARC` existe.
- `cadastros_pessoas.id` existe.
- Mas o vinculo oficial `cadastros_pessoas.id <-> CODPARC`, escopado por tenant, provider, ambiente, empresa e filial, nao esta padronizado.

O mesmo ocorre para produto, deposito, natureza financeira, centro de custo, conta corrente, documentos fiscais, contas a pagar, contas a receber, empresa e filial.

## 4. Decisao arquitetural recomendada

O AgroSaaS deve adotar o conceito de **Associacao Oficial com Sistema Externo** como parte do dominio de Integracoes.

Definicao:

> Este registro do AgroSaaS corresponde a este registro no sistema externo X, neste ambiente, para este tenant, empresa e filial.

Essa associacao deve ser uma capacidade de plataforma, nao um campo especifico do Sankhya espalhado em cada entidade de negocio.

Recomendacao principal:

- criar, em etapa futura, uma estrutura unica e transversal de associacoes externas, ligada ao dominio de Integracoes;
- manter staging provider-specific, como `sankhya_pessoas` e `sankhya_produtos`, apenas como espelho tecnico do provider;
- usar a associacao oficial para responder qual registro local corresponde ao registro externo;
- usar historico de associacao para auditoria, conflitos, mudanca de codigo externo e reprocessamento.

## 5. Informacoes minimas da associacao

Qualquer associacao oficial com sistema externo deve conter, conceitualmente:

| Informacao | Finalidade |
| --- | --- |
| Tenant | Garantir isolamento entre clientes. |
| Sistema externo/provider | Identificar Sankhya, TOTVS, SAP, Omie, banco, fiscal ou outro sistema. |
| Configuracao da integracao | Amarrar a associacao a uma conexao real do tenant. |
| Ambiente | Separar producao, homologacao e sandbox. |
| Escopo | Indicar se a associacao vale para tenant ou estabelecimento. |
| Empresa externa | Registrar codigos como `CODEMP`, quando aplicavel. |
| Filial externa | Registrar codigos como `CODFILIAL`, quando aplicavel. |
| Entidade local | Ex.: Pessoa, Produto, Deposito, Nota Fiscal, Despesa. |
| ID local | Identificador do registro no AgroSaaS. |
| Entidade externa | Ex.: Parceiro, Produto, Local de Estoque, Documento, Natureza. |
| Identificador externo | Ex.: `CODPARC`, `CODPROD`, `CODLOCAL`, `NUNOTA`, `DESDOB`. |
| Identificadores secundarios | Documento, chave de acesso, numero, serie, SKU, codigo de barras, CNPJ, CPF. |
| Status da associacao | Ativa, pendente de validacao, em conflito, inativa, substituida. |
| Origem da criacao | Importacao, conciliacao manual, criacao via AgroSaaS, migracao, rotina de sync. |
| Confianca da associacao | Alta, media, baixa, manualmente confirmada. |
| Ultima sincronizacao | Quando a associacao foi usada ou validada pela ultima vez. |
| Ultimo job | Qual execucao de integracao tocou a associacao. |
| Observacoes | Justificativas de excecao ou conciliacao. |
| Historico | Alteracoes de identificador, status, conflito, usuario e rotina. |

## 6. Escopo por entidade

### 6.1 P0 - Antes do piloto

| Entidade AgroSaaS | Entidade externa esperada | Identificador externo comum | Motivo |
| --- | --- | --- | --- |
| Pessoa | Parceiro | `CODPARC` | Base para cliente, fornecedor, transportadora e representante. |
| Produto/Insumo | Produto | `CODPROD` | Base para financeiro, fiscal, estoque e itens de documento. |
| Plano de Contas/Natureza | Natureza Financeira | `CODNAT` ou equivalente | Necessario para classificar financeiro quando o ERP exigir natureza. |
| Conta a Pagar | Titulo financeiro | `DESDOB`, `NUMDOC`, identificador nativo se houver | Evitar duplicidade financeira e permitir reprocesso. |
| Conta a Receber | Titulo financeiro | `DESDOB`, `NUMDOC`, identificador nativo se houver | Evitar duplicidade financeira e permitir reprocesso. |
| NFe/Documento Fiscal | Nota/documento fiscal | `CHAVEACESSO`, `NUNOTA`, `NUMNOTA`, `SERIE` | A chave de acesso mitiga duplicidade, mas nao substitui o vinculo com o registro local. |
| Empresa/Filial | Empresa/Filial | `CODEMP`, `CODFILIAL` | P0 se o cliente nao for monoempresa/monofilial. |
| Unidade de Medida | Unidade | codigo/sigla do ERP | Necessaria para produtos, conversoes e documentos. |

### 6.2 P1 - Logo apos o piloto ou conforme necessidade

| Entidade AgroSaaS | Entidade externa esperada | Identificador externo comum | Motivo |
| --- | --- | --- | --- |
| Deposito | Local de Estoque | `CODLOCAL` | Necessario para saldos, lotes e movimentacoes. |
| Conta Corrente | Conta Corrente | codigo de conta no ERP | Necessaria para baixas, conciliacao e fluxo financeiro. |
| Centro de Resultado | Centro de Resultado | codigo do ERP | Necessario para demonstrativos gerenciais e rateios. |
| Centro de Custo | Centro de Custo | `CODCENCUS` ou equivalente | Necessario quando o ERP exige centro nos titulos/documentos. |
| Tipo de Operacao | Tipo de Operacao | `CODTIPOPER` ou equivalente | Regra de roteamento fiscal/operacional, nao apenas cadastro simples. |
| Banco | Banco | codigo bancario/ERP | Apoia contas correntes e remessas. |
| Agencia | Agencia | codigo da agencia/ERP | Apoia contas correntes e conciliacao. |
| Carteira | Carteira | codigo da carteira/ERP | Apoia cobranca e recebiveis. |

### 6.3 P2 - Futuro

| Entidade AgroSaaS | Entidade externa esperada | Motivo |
| --- | --- | --- |
| Pedido | Pedido/documento comercial | Fluxos comerciais bidirecionais. |
| Contrato | Contrato/documento | Comercializacao, compra, venda e faturamento. |
| Comercializacao | Documento ou contrato comercial | Evolucao do modulo comercial. |
| Barter | Contrato/operacao composta | Operacoes com troca e liquidacao futura. |
| Equipamento | Bem/maquina | Manutencao, custos e frota. |
| Colaborador | Funcionario/prestador | RH, apontamentos e custos. |
| RH | Equipe, OS, apontamento | Evolucao operacional integrada. |
| Frota | Veiculo/equipamento | Abastecimento, manutencao e telemetria. |

## 7. Empresas, filiais e estabelecimentos

O Sankhya pode usar `CODEMP` e, conforme a configuracao, um codigo de filial ou estrutura equivalente. Esses codigos nao devem ser confundidos automaticamente com `Tenant` nem com `UnidadeProdutiva`.

Regras arquiteturais:

- se o ERP representa toda a organizacao do cliente, a integracao pode ser escopada por `TENANT`;
- se matriz, filial, CNPJ ou inscricao fiscal mudam dentro do mesmo tenant, a integracao deve usar o conceito de `ESTABELECIMENTO`;
- `UnidadeProdutiva` representa operacao rural e nao deve ser tratada como filial fiscal;
- uma Unidade Produtiva pode pertencer a um estabelecimento, e o estabelecimento pode estar associado a `CODEMP`/`CODFILIAL`;
- financeiro, fiscal, estoque e documentos devem herdar empresa/filial pela configuracao correta, nao por inferencia livre a partir da fazenda.

Antes do piloto, deve existir uma confirmacao operacional:

- se o cliente for monoempresa e monofilial, esse pressuposto deve ser registrado;
- se houver mais de uma empresa ou filial relevante, a associacao `Estabelecimento/Tenant <-> CODEMP/CODFILIAL` vira requisito P0.

## 8. Tipo de operacao

Tipo de operacao nao deve ser tratado apenas como um cadastro externo simples.

Ele pode depender de:

- empresa;
- filial;
- produto;
- unidade produtiva;
- natureza da operacao;
- compra;
- venda;
- transferencia;
- consumo interno;
- devolucao;
- regras fiscais.

Decisao recomendada:

- a associacao externa pode guardar o identificador do tipo de operacao quando houver um registro equivalente;
- a escolha do tipo de operacao deve ser modelada como regra de roteamento por cenario;
- para o piloto de leitura, nao e bloqueador se nao houver escrita de documentos;
- para criacao, confirmacao, cancelamento ou faturamento de documentos no ERP, tipo de operacao vira requisito obrigatorio.

## 9. Centro de resultado, centro de custo e rateio

Esses conceitos nao devem ser misturados.

| Conceito | Interpretacao recomendada |
| --- | --- |
| Centro de Resultado | Dimensao gerencial para medir resultado de uma unidade, atividade ou area de negocio. |
| Centro de Custo | Dimensao de responsabilidade por custos ou despesas. |
| Rateio | Regra de distribuicao de valor entre centros, safras, talhoes, unidades ou atividades. |
| Safra | Ciclo agricola; pode influenciar rateio, mas nao e centro de custo por si so. |
| Talhao | Area operacional; pode ser dimensao de apontamento ou rateio. |
| Unidade Produtiva | Unidade operacional da fazenda; pode mapear para estabelecimento apenas quando houver regra administrativa clara. |

Para integracao com ERP:

- centro de resultado e centro de custo precisam de associacao externa propria quando o ERP exigir codigos;
- safra, talhao e unidade produtiva podem alimentar rateios, mas nao devem ser convertidos automaticamente em `CODCENCUS`;
- se o Sankhya exigir `CODCENCUS` em titulo ou documento, a ausencia dessa associacao deve ser tratada como risco P0/P1 conforme o fluxo do piloto.

## 10. Conta corrente, banco, agencia e carteira

Essas entidades entram principalmente em:

- contas a pagar;
- contas a receber;
- baixas;
- remessas;
- conciliacao bancaria;
- fluxo financeiro;
- cobranca;
- integracao futura com bancos.

Recomendacao:

- banco e agencia podem usar codigos oficiais e codigos internos do ERP;
- conta corrente deve ter associacao externa propria quando houver baixa, remessa ou conciliacao;
- carteira deve ser tratada como configuracao financeira por conta/cobranca, nao apenas como texto em titulo;
- no piloto de leitura financeira, podem ser P1 se nao forem necessarias para gravacao ou baixa;
- em fluxos de escrita, baixa ou conciliacao, passam a ser obrigatorias.

## 11. Protecao contra duplicidade

A associacao oficial deve impedir duplicidade por cinco caminhos.

| Risco | Regra recomendada |
| --- | --- |
| Pessoas duplicadas | Usar `tenant + sistema externo + ambiente + entidade externa + CODPARC`, com documento normalizado e papel como validacao secundaria. |
| Produtos duplicados | Usar `tenant + sistema externo + ambiente + entidade externa + CODPROD`, com SKU, codigo interno, codigo de barras, unidade e descricao como validacao secundaria. |
| Documentos duplicados | Usar `CHAVEACESSO` para NF-e, somada a empresa/filial e identificador nativo do ERP quando existir. |
| Financeiro duplicado | Nao usar `DESDOB` isolado; usar identificador nativo ou chave composta validada com `CODPARC`, `NUMDOC`, vencimento, valor, empresa e filial. |
| Codigo externo alterado | Registrar historico, marcar associacao anterior como substituida e reconciliar antes de criar novo registro local. |
| Tenants diferentes | Nenhum identificador externo pode ser global sem `tenant_id`, provider, ambiente e configuracao. |

Codigos como `CODPARC`, `CODPROD`, `DESDOB`, `CODLOCAL`, `CODNAT` e `CODCENCUS` nao devem ser tratados como unicos globalmente.

## 12. Historico e auditoria

O modelo deve permitir responder:

- quando a associacao foi criada;
- quem criou ou confirmou;
- por qual sincronizacao ou job foi criada;
- quando foi atualizada;
- qual era o identificador externo anterior;
- se houve conflito de associacao;
- se uma associacao foi substituida por outra;
- se uma associacao foi desativada;
- qual rotina usou a associacao pela ultima vez;
- qual era a configuracao da integracao naquele momento.

Historico e auditoria sao parte do requisito de integracao, nao apenas detalhe operacional. Sem isso, reprocessamento e migracao futura ficam dependentes de analise manual.

## 13. Ambientes

Ambiente faz parte da identidade da associacao.

Regras:

- uma associacao criada em sandbox nao deve ser reutilizada automaticamente em producao;
- troca de credenciais nao deve apagar associacoes, mas deve registrar nova versao/configuracao operacional;
- troca de ambiente deve exigir nova validacao;
- troca de empresa ou filial deve exigir reconciliacao;
- importacoes de homologacao podem servir como ensaio, mas nao como prova de vinculo produtivo;
- se o mesmo tenant usar mais de um ERP ou mais de uma base do mesmo ERP, a associacao deve apontar para a configuracao correta.

## 14. Estrategias de implementacao futura avaliadas

| Alternativa | Vantagens | Riscos |
| --- | --- | --- |
| Campos especificos por entidade | Simples para poucos casos; facil de consultar diretamente. | Acopla entidades ao Sankhya; nao escala para multiplos ERPs; multiplica campos e regras; dificulta historico. |
| Tabela unica de associacao externa | Modelo transversal; suporta multiplos ERPs; facilita auditoria e rastreabilidade; evita poluir entidades de negocio. | Precisa de governanca de tipos de entidade e validacoes por dominio. |
| Tabela por dominio | Permite regras fortes por dominio; consultas mais especificas. | Pode fragmentar a arquitetura e repetir conceitos de ambiente, provider, status e historico. |
| Extensao do dominio de Integracoes | Reusa provider, configuracao, ambiente, jobs, health e credenciais existentes. | Exige cuidado para nao misturar staging tecnico com vinculo de negocio. |
| Abordagem hibrida | Usa uma associacao transversal e permite validacoes auxiliares por dominio quando necessario. | Requer disciplina para nao virar duplicacao de modelos. |

## 15. Recomendacao final

A abordagem preferencial e **hibrida com nucleo transversal no dominio de Integracoes**.

Na pratica, isso significa:

- uma associacao oficial unica e reutilizavel para ligar registros locais a registros externos;
- referencia ao provider e a configuracao de integracao ja existentes;
- isolamento por tenant e ambiente como regra obrigatoria;
- empresa e filial externas como parte do contexto quando aplicavel;
- historico separado para alteracoes, conflitos e substituicoes;
- validacoes especificas por dominio apenas quando agregarem regra real de negocio;
- staging provider-specific mantido como espelho tecnico, nao como associacao oficial.

Essa escolha evita uma solucao exclusiva para o Sankhya e preserva evolucao para TOTVS, SAP, Omie, bancos e outros sistemas.

## 16. Impacto no piloto Sankhya

### Precisa estar resolvido antes do piloto

- Confirmar se o piloto e monoempresa/monofilial.
- Registrar explicitamente o pressuposto operacional de empresa/filial, ou tratar `CODEMP`/`CODFILIAL` como requisito P0.
- Definir a regra de associacao para pessoas/parceiros.
- Definir a regra de associacao para produtos/insumos.
- Definir como contas a pagar e contas a receber serao reconhecidas sem duplicidade.
- Usar `CHAVEACESSO` como protecao primaria para NF-e.
- Validar se natureza financeira e unidade de medida sao exigidas nos fluxos reais do piloto.

### Pode ficar para depois do piloto

- Deposito/local de estoque, se estoque nao entrar no piloto operacional.
- Conta corrente, banco, agencia e carteira, se nao houver baixa, remessa ou conciliacao.
- Centro de resultado e centro de custo, se nao forem exigidos nos titulos importados.
- Tipo de operacao, se nao houver escrita, confirmacao, cancelamento ou faturamento de documentos.
- Pedido, contrato, barter, equipamentos, RH e frota.

### Bloqueadores

- Piloto multiempresa ou multifilial sem associacao `CODEMP`/`CODFILIAL`.
- Criacao ou atualizacao de documentos no ERP sem regra de tipo de operacao.
- Importacao financeira sem chave confiavel para reconhecer titulo ja importado.
- Criacao de pessoas ou produtos locais sem reconciliacao com `CODPARC` e `CODPROD`.

### Melhorias futuras

- Interface operacional de conciliacao de associacoes pendentes.
- Historico visual de alteracoes de identificador externo.
- Relatorio de conflitos por tenant, provider, entidade e ambiente.
- Reprocessamento por entidade usando a associacao oficial.

## 17. Conclusao

O modelo atual do AgroSaaS esta preparado para configurar, autenticar, executar, monitorar e registrar sincronizacoes de integracao. Ele tambem possui staging Sankhya suficiente para o primeiro piloto em leitura controlada.

O que ainda falta e uma associacao oficial, persistente, rastreavel e reutilizavel entre registros de negocio do AgroSaaS e registros equivalentes em sistemas externos.

A decisao recomendada e evoluir o dominio de Integracoes com uma capacidade transversal de Associacao Oficial com Sistema Externo, usando o Sankhya como primeiro caso de uso, mas sem acoplar o modelo ao Sankhya.

Para o primeiro piloto, o AgroSaaS pode seguir se o escopo permanecer controlado, preferencialmente monoempresa/monofilial, leitura primeiro e com deduplicacao validada para pessoas, produtos, financeiro e NFe. Para evolucao completa da integracao e para Go-Live com escrita, multiempresa, estoque, baixas ou documentos, a associacao oficial passa a ser requisito arquitetural.
