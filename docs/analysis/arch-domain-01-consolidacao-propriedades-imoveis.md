# ARCH-DOMAIN-01 - Consolidação dos Domínios Propriedades e Imóveis Rurais

Data da análise: 2026-06-20

Escopo:
- Apenas análise arquitetural e plano de evolução.
- Sem código, migrations, banco, APIs ou frontend.

Fontes obrigatórias lidas:
- [agrosaas-master-context.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-master-context.md)
- [agrosaas-domain-map.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-domain-map.md)
- [agrosaas-data-model.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-data-model.md)
- [agrosaas-routing-map.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-routing-map.md)
- [agrosaas-ai-rules.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-ai-rules.md)
- [propriedades-auditoria-arquitetural.md](/opt/lampp/htdocs/farm/docs/analysis/propriedades-auditoria-arquitetural.md)

## Diretriz Executiva

O AgroSaaS já opera com dois domínios distintos:

- `Propriedades` como unidade operacional, territorial e produtiva.
- `Imóveis Rurais` como unidade legal, patrimonial e documental.

O problema atual não é ausência de módulo. O problema é **sobreposição parcial de atributos e fronteiras semânticas insuficientemente explicitadas**.

Conclusão executiva:
- `Propriedades` não deve virar um módulo legal paralelo.
- `Imóveis Rurais` não deve absorver a operação agrícola.
- A consolidação correta é manter os dois domínios e formalizar a fonte de verdade de cada campo.

## Etapa 1 - Análise de Responsabilidades

### Tabela de responsabilidades

| Campo | Responsável Atual | Responsável Futuro | Justificativa |
|---|---|---|---|
| Nome | Propriedades | Propriedades | É o nome operacional da fazenda/unidade produtiva. |
| Código | Propriedades | Propriedades | É identificador interno de área, talhão, gleba ou estrutura territorial. |
| Município | Propriedades e Imóveis Rurais | Imóveis Rurais como oficial; Propriedades como espelho operacional | Município faz parte do cadastro legal e também ajuda a contextualizar a operação. |
| Estado | Propriedades e Imóveis Rurais | Imóveis Rurais como oficial; Propriedades como espelho operacional | UF é atributo cadastral/territorial e documental. |
| Coordenadas | Propriedades | Propriedades | Coordenadas da sede, centroides e geometria são dados territoriais e operacionais. |
| Área Total | Propriedades e Imóveis Rurais | Imóveis Rurais como oficial para a dimensão legal; Propriedades para a dimensão operacional | A área legal deve ser auditável no domínio fundiário; a área operacional é consumida pela produção. |
| Área APP | Propriedades e Imóveis Rurais | Imóveis Rurais como oficial; Propriedades como estrutura territorial | APP é atributo ambiental/legal, mas também é usado na operação. |
| Área Reserva Legal | Propriedades e Imóveis Rurais | Imóveis Rurais como oficial; Propriedades como estrutura territorial | Reserva Legal pertence à dimensão ambiental/jurídica. |
| CAR | Imóveis Rurais | Imóveis Rurais | CAR é cadastro ambiental rural e pertence ao imóvel legal. |
| CCIR | Imóveis Rurais | Imóveis Rurais | CCIR é documento fundiário/legal. |
| ITR | Imóveis Rurais | Imóveis Rurais | ITR pertence ao ciclo fiscal do imóvel. |
| NIRF | Imóveis Rurais | Imóveis Rurais | NIRF é identificador fiscal do imóvel. |
| SIGEF | Imóveis Rurais | Imóveis Rurais | SIGEF é georreferenciamento fundiário. |
| Matrículas | Imóveis Rurais | Imóveis Rurais | Matricula é registro legal do imóvel. |
| Cartórios | Imóveis Rurais | Imóveis Rurais | O cartório é parte da custódia documental/legal. |
| Proprietários | Inexistente / fragmentado | Imóveis Rurais | O proprietário deve residir no domínio jurídico-patrimonial. |
| Condôminos | Inexistente | Imóveis Rurais | Condomínio é relação civil/fundiária. |
| Arrendamentos | Imóveis Rurais | Imóveis Rurais | Contratos de arrendamento e parceria são jurídicos e patrimoniais. |
| Parcerias | Imóveis Rurais | Imóveis Rurais | Mesma lógica de arrendamento. |
| Benfeitorias | Imóveis Rurais e Propriedades | Imóveis Rurais como oficial; Propriedades como operacional-territorial | A benfeitoria existe fisicamente, mas sua leitura patrimonial pertence ao imóvel. |
| Talhões | Propriedades | Propriedades | Talhão é unidade operacional de manejo. |
| Glebas | Propriedades | Propriedades | Gleba é subdivisão territorial/operacional da fazenda. |
| Pastagens | Propriedades | Propriedades | Pastagem é unidade de uso operacional e pecuário. |
| Estradas | Propriedades | Propriedades | Estradas são infraestrutura territorial de acesso e operação. |
| Infraestrutura | Propriedades | Propriedades | Sede, armazém, curral e estruturas operacionais pertencem ao domínio da propriedade. |

### Leitura técnica

- O eixo `Propriedades` deve representar o que a operação usa diariamente.
- O eixo `Imóveis Rurais` deve representar o que exige prova, registro, documento e custódia legal.
- Campos como CAR, CCIR, NIRF e matrícula podem ser espelhados na experiência operacional, mas não devem mudar de ownership canônico.

## Etapa 2 - Modelo Canônico

### Modelo oficial proposto

**Imóvel Rural**
- Documentação
- Matrículas
- Proprietários
- Cartórios
- CAR
- CCIR
- ITR
- NIRF
- SIGEF
- Contratos
- Avaliações

**Propriedade**
- Talhões
- Glebas
- Pastagens
- Estradas
- Infraestrutura
- Safras
- Operações
- Produção
- Custos
- Indicadores

### Observação

Esse modelo canônico está consistente com o material já existente:
- o `data model` trata `Propriedades / Áreas Rurais` como entidade central multi-domínio;
- o módulo `imoveis` já assume o papel patrimonial/legal;
- o `routing map` e o `permission catalog` já separam os caminhos operacionais e legais.

## Etapa 3 - Relacionamento Entre Domínios

### Relação oficial

**D) Outro**

### Forma exata do relacionamento

`Imóvel Rural` é a camada legal/patrimonial da `Propriedade`.

### Justificativa técnica

- `Propriedade` é a unidade usada pelo fluxo operacional.
- `Imóvel Rural` é a unidade usada pela prova documental e fundiária.
- Não há evidência de relação N:N como regra de negócio principal.
- Também não é correto tratar `Propriedade` como filha exclusiva de `Imóvel Rural`, porque o domínio operacional pode existir mesmo quando a formalização fundiária estiver incompleta ou em trânsito.

### Interpretação prática

- Uma `Propriedade` pode operar com um `Imóvel Rural` principal.
- O `Imóvel Rural` deve servir como referência legal do território operacional.
- A vinculação deve ser tratada como "camada legal sobreposta à unidade operacional", e não como substituição de um pelo outro.

## Etapa 4 - Fonte da Verdade

### Regra geral

- `Propriedades` é a fonte da verdade para o que é operacional, territorial e produtivo.
- `Imóveis Rurais` é a fonte da verdade para o que é jurídico, documental, cartorial e fiscal.

### Tabela de fonte da verdade

| Campo | Fonte Oficial | Pode ser replicado? | Pode ser derivado? |
|---|---|---|---|
| Nome | Propriedades | Sim, para leitura no Imóvel Rural | Não |
| Código | Propriedades | Sim | Não |
| Município | Imóveis Rurais | Sim, para visualização operacional | Não |
| Estado | Imóveis Rurais | Sim, para visualização operacional | Não |
| Coordenadas | Propriedades | Sim, para leitura no Imóvel Rural se necessário | Não |
| Área Total | Imóveis Rurais | Sim, para uso operacional | Não |
| Área APP | Imóveis Rurais | Sim | Não |
| Área Reserva Legal | Imóveis Rurais | Sim | Não |
| CAR | Imóveis Rurais | Sim | Não |
| CCIR | Imóveis Rurais | Sim | Não |
| ITR | Imóveis Rurais | Sim | Não |
| NIRF | Imóveis Rurais | Sim | Não |
| SIGEF | Imóveis Rurais | Sim | Não |
| Matrículas | Imóveis Rurais | Sim | Não |
| Cartórios | Imóveis Rurais | Sim | Não |
| Proprietários | Imóveis Rurais | Sim, para exibição em propriedade | Não |
| Condôminos | Imóveis Rurais | Sim | Não |
| Arrendamentos | Imóveis Rurais | Sim, para leitura em propriedade | Não |
| Parcerias | Imóveis Rurais | Sim, para leitura em propriedade | Não |
| Benfeitorias | Propriedades | Sim, para visão patrimonial | Não |
| Talhões | Propriedades | Sim, para leitura no imóvel | Não |
| Glebas | Propriedades | Sim, para leitura no imóvel | Não |
| Pastagens | Propriedades | Sim | Não |
| Estradas | Propriedades | Sim | Não |
| Infraestrutura | Propriedades | Sim | Não |
| Safra | Propriedades | Não | Não, é entidade própria do domínio operacional |

### Regra de replicação

Replicar é permitido quando:
- a informação precisa aparecer em outra tela por conveniência;
- a réplica é explicitamente derivada ou espelhada;
- a escrita continua concentrada na fonte oficial.

Replicar é proibido quando:
- o espelho vira fonte concorrente;
- a UI passa a editar dois lugares;
- o campo replicado começa a divergir por atualização assíncrona.

## Etapa 5 - Lacunas de Domínio

### Classificação das ausências

| Lacuna | Classificação | Motivo |
|---|---|---|
| Proprietários | CRÍTICO | Sem essa entidade, o domínio fundiário não fecha com segurança jurídica. |
| Condôminos | IMPORTANTE | Necessário para copropriedade e situações compartilhadas. |
| Representantes legais | CRÍTICO | Essencial para autorização e governança documental. |
| Procuradores | IMPORTANTE | Relevante para operações com mandato e representação. |
| Posse | IMPORTANTE | Já há sinais parciais, mas sem entidade/fluxo canônico consolidado. |
| Usufruto | FUTURO | Relevante juridicamente, mas não bloqueia o núcleo atual. |
| Comodato | FUTURO | Acordo de uso, útil mas não central no curto prazo. |
| Hipoteca | FUTURO | Importante para garantias reais, mas fora do núcleo operacional imediato. |
| Garantias reais | FUTURO | Complementa o patrimônio e crédito, mas pode entrar em fase posterior. |

### Observação

As lacunas mais críticas não são técnicas; são de **modelagem jurídica de titularidade e representação**.

## Etapa 6 - Impacto no AgroSaaS

| Módulo | Impacto da consolidação | Observação |
|---|---|---|
| Agrícola | Alto | Depende da propriedade como unidade de planejamento, talhão e safra. |
| Pecuária | Alto | Usa piquetes, pastagens e infraestrutura territorial. |
| Financeiro | Alto | Pode consumir o imóvel legal para apropriação, captação e custeio. |
| Compras | Médio | Usa contexto operacional da propriedade. |
| Estoque | Médio | Consome a lógica da unidade produtiva. |
| Frota | Médio | Usa a propriedade como contexto de localização e operação. |
| RH | Baixo/Médio | Impacto indireto em alocação e estrutura de equipe. |
| Ambiental | Alto | Depende da leitura de APP, RL, licenças e restrições. |
| Comercialização | Médio | Pode usar imóvel e propriedade para rastreabilidade e contratos. |
| Hedge | Médio | O ativo legal pode ser base de garantias e análise. |
| Certificações | Alto | Precisa da trilha documental correta. |
| Projeto Raízes | Alto | Pode exigir rastreabilidade de origem territorial e legal. |

## Etapa 7 - Roadmap de Consolidação

### Fase 1 - Correções imediatas

- Definir oficialmente a fronteira entre `Propriedades` e `Imóveis Rurais`.
- Remover ambiguidade em nomenclatura e telas duplicadas.
- Declarar qual entidade é a fonte oficial de cada campo.
- Padronizar a narrativa de produto para o usuário final.

### Fase 2 - Consolidação de domínio

- Consolidar `Propriedades` como unidade operacional.
- Consolidar `Imóveis Rurais` como unidade legal/patrimonial.
- Reduzir duplicidade de campos cadastrais.
- Separar claramente leitura, edição e espelhamento de dados.

### Fase 3 - Expansão fundiária

- Introduzir domínio mais forte para proprietários, representantes e condôminos.
- Estruturar posse, usufruto, comodato, hipoteca e garantias reais.
- Aprofundar cartórios, matrículas e documentos.

### Fase 4 - Expansão ambiental

- Estruturar nascentes, restrições e áreas sensíveis.
- Organizar licenças e registros ambientais canônicos.
- Melhorar leitura ambiental por imóvel e por propriedade.

### Fase 5 - Integração ESG e rastreabilidade

- Consolidar certificações.
- Estruturar ESG como camadas de evidência.
- Integrar rastreabilidade territorial, fundiária e produtiva.

## Respostas Objetivas

### 1. Qual deve ser a fronteira definitiva entre Propriedades e Imóveis Rurais?

`Propriedades` deve ser o domínio da operação rural e da estrutura territorial.

`Imóveis Rurais` deve ser o domínio da titularidade legal, documentação, matrícula, cartório, CAR, CCIR, ITR, NIRF e contratos.

### 2. Qual é o relacionamento oficial entre eles?

O relacionamento oficial deve ser:

**Imóvel Rural sobreposto à Propriedade como camada legal/patrimonial da unidade operacional.**

Em termos práticos:
- a propriedade opera;
- o imóvel rural legitima e documenta.

### 3. Qual deve ser a fonte da verdade para cada informação?

- Operação, talhões, glebas, pastagens, estradas, infraestrutura e georreferenciamento operacional: `Propriedades`.
- Titularidade, matrícula, cartório, CAR, CCIR, ITR, NIRF, SIGEF e contratos: `Imóveis Rurais`.
- Dados espelhados devem ser apenas leitura derivada, não fonte concorrente.

### 4. Quais lacunas precisam ser corrigidas?

- Titularidade formal: proprietários, condôminos, representantes e procuradores.
- Regimes jurídicos: posse, usufruto, comodato, hipoteca e garantias reais.
- Explicitação de fronteiras entre o legal e o operacional.
- Diminuição de duplicidade cadastral.
- Consolidação de camadas ambientais e ESG.

### 5. Qual o roadmap recomendado para os próximos ciclos?

1. Fixar fronteiras e fontes oficiais.
2. Consolidar `Propriedades` e `Imóveis Rurais` como domínios complementares.
3. Expandir o eixo fundiário.
4. Expandir o eixo ambiental.
5. Integrar ESG, certificações e rastreabilidade.

## Recomendação Final

O AgroSaaS deve tratar a consolidação como um problema de **governança de domínio**, não como criação de novo módulo.

Diretriz final:
- manter `Propriedades` como núcleo operacional;
- manter `Imóveis Rurais` como núcleo legal/patrimonial;
- remover duplicidade sem fundir os domínios;
- evoluir com a fonte da verdade bem definida para cada dado.
