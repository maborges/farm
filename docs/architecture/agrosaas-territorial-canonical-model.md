# AgroSaaS Territorial Canonical Model

Data de referência: 2026-06-20

## Objetivo

Estabelecer o modelo canônico oficial do AgroSaaS para território, fundiário, rastreabilidade, ESG e certificações.

Este documento é a referência normativa para:
- Arquitetura
- Backend
- Frontend
- Banco
- ESG
- Certificações
- Rastreabilidade
- Projeto Raízes
- Integrações futuras

## Base Arquitetural

Este modelo respeita os documentos oficiais:
- [agrosaas-master-context.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-master-context.md)
- [agrosaas-domain-map.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-domain-map.md)
- [agrosaas-data-model.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-data-model.md)
- [agrosaas-routing-map.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-routing-map.md)
- [agrosaas-ai-rules.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-ai-rules.md)
- [propriedades-auditoria-arquitetural.md](/opt/lampp/htdocs/farm/docs/analysis/propriedades-auditoria-arquitetural.md)
- [arch-domain-01-consolidacao-propriedades-imoveis.md](/opt/lampp/htdocs/farm/docs/analysis/arch-domain-01-consolidacao-propriedades-imoveis.md)

## Princípios Canônicos

1. Não existe um terceiro módulo entre `Propriedades` e `Imóveis Rurais`.
2. `Propriedades` é o domínio operacional, territorial e produtivo.
3. `Imóveis Rurais` é o domínio legal, patrimonial, documental e fiscal.
4. Cada informação possui uma única fonte oficial.
5. Dados espelhados são leitura derivada, nunca fonte concorrente.
6. Rastreamento operacional deve chegar até o imóvel legal.
7. Nenhum conceito jurídico pode ser tratado como detalhe implícito do cadastro operacional.

## Etapa 1 - Mapa Conceitual

### 1. Tenant
- Definição: raiz de isolamento multi-tenant do AgroSaaS.
- Responsabilidade: isolar dados, permissões, rotas e contexto de execução.
- Ownership: infraestrutura de plataforma.
- Módulo responsável: Core / Admin SaaS.

### 2. Imóvel Rural
- Definição: unidade legal, patrimonial, documental e fiscal do território.
- Responsabilidade: titularidade, matrícula, cartório, CAR, CCIR, ITR, NIRF, SIGEF, contratos e avaliações.
- Ownership: domínio fundiário/legal.
- Módulo responsável: Imóveis Rurais.

### 3. Propriedade
- Definição: unidade operacional e territorial da fazenda, usada no dia a dia agrícola e pecuário.
- Responsabilidade: organizar glebas, talhões, pastagens, infraestrutura, áreas ambientais e safra operacional.
- Ownership: domínio operacional.
- Módulo responsável: Propriedades.

### 4. Gleba
- Definição: subconjunto territorial da propriedade com identidade geoespacial própria.
- Responsabilidade: subdividir o território operacional e servir de base para talhões e áreas ambientais.
- Ownership: Propriedades.
- Módulo responsável: Propriedades.

### 5. Talhão
- Definição: unidade operacional de manejo e produção.
- Responsabilidade: concentrar plantio, operação, monitoramento e rastreabilidade agrícola.
- Ownership: Propriedades.
- Módulo responsável: Agrícola / Propriedades.

### 6. Pastagem
- Definição: unidade de uso pecuário do território.
- Responsabilidade: organizar lotação, manejo de rebanho, rotação e uso operacional da área.
- Ownership: Propriedades.
- Módulo responsável: Pecuária / Propriedades.

### 7. Infraestrutura
- Definição: benfeitorias e estruturas físicas de suporte à operação.
- Responsabilidade: sede, armazém, curral, acessos e outras estruturas.
- Ownership: Propriedades.
- Módulo responsável: Propriedades.

### 8. Safra
- Definição: ciclo operacional temporário de planejamento e execução.
- Responsabilidade: agrupar planejamento, execução, monitoramento, custos e indicadores.
- Ownership: domínio operacional.
- Módulo responsável: Agrícola.

### 9. Produção
- Definição: resultado material da execução operacional.
- Responsabilidade: registrar volume, qualidade, origem, destino e evidência de produção.
- Ownership: domínio operacional.
- Módulo responsável: Agrícola / Comercialização.

### 10. Proprietário
- Definição: pessoa física ou jurídica com titularidade legal sobre o imóvel.
- Responsabilidade: representar a titularidade e a cadeia de domínio legal.
- Ownership: Imóveis Rurais.
- Módulo responsável: Imóveis Rurais.

### 11. Condômino
- Definição: coproprietário de um imóvel rural.
- Responsabilidade: representar estrutura compartilhada de titularidade.
- Ownership: Imóveis Rurais.
- Módulo responsável: Imóveis Rurais.

### 12. Representante Legal
- Definição: pessoa habilitada a agir em nome do titular.
- Responsabilidade: autorizar, assinar e responder juridicamente.
- Ownership: Imóveis Rurais.
- Módulo responsável: Imóveis Rurais.

### 13. Procurador
- Definição: mandatário formal com poderes específicos.
- Responsabilidade: operar atos delegados.
- Ownership: Imóveis Rurais.
- Módulo responsável: Imóveis Rurais.

### 14. Contrato
- Definição: instrumento jurídico que regula uso, exploração, cessão ou parceria.
- Responsabilidade: formalizar arrendamento, parceria, comodato ou instrumentos correlatos.
- Ownership: Imóveis Rurais.
- Módulo responsável: Imóveis Rurais.

### 15. Documento
- Definição: evidência documental associada ao imóvel ou à operação.
- Responsabilidade: guardar versão, validade, origem e status de prova.
- Ownership: compartilhado, com origem canônica no domínio fundiário para documentos legais.
- Módulo responsável: Imóveis Rurais e Ambiental, conforme o tipo.

### 16. Avaliação
- Definição: mensuração patrimonial ou operacional de valor.
- Responsabilidade: suportar valor econômico, garantia, histórico e decisão.
- Ownership: Imóveis Rurais para avaliação patrimonial; Propriedades para análises operacionais.
- Módulo responsável: Imóveis Rurais e Analytics/Financeiro, conforme finalidade.

## Etapa 2 - Cardinalidades Oficiais

### Tenant ↔ Imóvel Rural
- Cardinalidade: `1:N`
- Justificativa: um tenant pode possuir vários imóveis rurais; um imóvel pertence a um único tenant.

### Tenant ↔ Propriedade
- Cardinalidade: `1:N`
- Justificativa: um tenant pode operar várias propriedades; uma propriedade pertence a um único tenant.

### Imóvel Rural ↔ Propriedade
- Cardinalidade: `1:N`
- Justificativa: uma propriedade operacional pode ser suportada por mais de um imóvel legal; cada imóvel legal referencia uma única propriedade operacional principal.
- Observação: o vínculo é de sobreposição legal sobre a unidade operacional, não de substituição.

### Imóvel Rural ↔ Proprietário
- Cardinalidade: `N:N`
- Justificativa: um imóvel pode ter múltiplos proprietários e um proprietário pode deter vários imóveis.

### Imóvel Rural ↔ Matrícula
- Cardinalidade: `1:N`
- Justificativa: um imóvel legal pode consolidar várias matrículas/documentos registrais; cada matrícula pertence a um imóvel principal.

### Imóvel Rural ↔ Contrato
- Cardinalidade: `1:N`
- Justificativa: um imóvel pode ter vários contratos ao longo do tempo; cada contrato pertence a um imóvel.

### Propriedade ↔ Gleba
- Cardinalidade: `1:N`
- Justificativa: uma propriedade contém várias glebas; uma gleba pertence a uma propriedade.

### Propriedade ↔ Talhão
- Cardinalidade: `1:N`
- Justificativa: uma propriedade contém vários talhões; um talhão pertence a uma propriedade.

### Propriedade ↔ Pastagem
- Cardinalidade: `1:N`
- Justificativa: uma propriedade pode conter várias áreas de pastagem; cada pastagem é atribuída a uma unidade operacional da propriedade.

### Propriedade ↔ Safra
- Cardinalidade: `N:N`
- Justificativa: uma safra é um ciclo operacional do tenant e pode envolver várias propriedades; uma propriedade participa de várias safras ao longo do tempo.
- Observação: a relação precisa existir por vínculo operacional, não por ownership estrutural.

### Propriedade ↔ Produção
- Cardinalidade: `1:N`
- Justificativa: a produção é registrada por unidade operacional e pode ser consolidada por propriedade; uma propriedade produz múltiplos eventos/entradas de produção.

## Etapa 3 - Hierarquia Territorial Oficial

### Modelo oficial

```text
Tenant
└── Propriedade
    ├── Gleba
    │   ├── Talhão
    │   │   └── Área Operacional
    │   │       ├── Piquete
    │   │       ├── Zona de Manejo
    │   │       └── Subtalhão
    │   ├── Área Ambiental
    │   │   ├── APP
    │   │   ├── Reserva Legal
    │   │   └── Nascentes
    │   └── Pastagem
    ├── Infraestrutura
    │   ├── Sede
    │   ├── Armazém
    │   ├── Curral
    │   └── Outros
    └── Estrada / Acesso
```

### Validação

O modelo-base está correto, mas com dois ajustes canônicos:
- `Pastagem` deve ser tratada como unidade operacional pecuária, não como raiz separada.
- `Estrada` deve ser tratada como infraestrutura/acesso, não como entidade fundiária autônoma.

### Leitura normativa

O que o backend já implementa como `AREA_RURAL`, `GLEBA`, `TALHAO`, `AREA_OPERACIONAL`, `AREA_AMBIENTAL` e `INFRAESTRUTURA` é consistente com a hierarquia oficial. `Pastagem` e `Estrada` são extensões canônicas do mesmo tronco operacional.

## Etapa 4 - Hierarquia Fundiária Oficial

### Modelo oficial

```text
Tenant
└── Imóvel Rural
    ├── Proprietários
    ├── Condôminos
    ├── Representantes Legais
    ├── Procuradores
    ├── Matrículas
    ├── Cartórios
    ├── CAR
    ├── CCIR
    ├── ITR
    ├── NIRF
    ├── SIGEF
    ├── Contratos
    ├── Documentos
    └── Avaliações
```

### Validação

O modelo está correto como árvore fundiária oficial, com uma melhoria importante:
- `Documentos` deve ser entendido como camada transversal de prova e não como simples anexo.
- `CAR`, `CCIR`, `ITR`, `NIRF` e `SIGEF` são atributos/documentos oficiais do imóvel, não da propriedade operacional.

## Etapa 5 - Fonte da Verdade

### Tabela definitiva

| Campo | Fonte Oficial | Domínio | Pode ser replicado? | Pode ser editado fora da origem? |
|---|---|---|---|---|
| Nome da propriedade | Propriedades | Territorial / Operacional | Sim | Não |
| Código interno da área | Propriedades | Territorial / Operacional | Sim | Não |
| Geometria territorial | Propriedades | Territorial | Sim | Não |
| Coordenadas da sede | Propriedades | Territorial / Operacional | Sim | Não |
| Gleba | Propriedades | Territorial | Sim | Não |
| Talhão | Propriedades | Territorial / Operacional | Sim | Não |
| Pastagem | Propriedades | Territorial / Pecuária | Sim | Não |
| Infraestrutura | Propriedades | Territorial / Operacional | Sim | Não |
| Safra | Operacional / Agrícola | Produtivo | Sim | Não |
| Produção | Operacional / Agrícola | Produtivo | Sim | Não |
| Área total legal | Imóveis Rurais | Fundiário / Fiscal | Sim | Não |
| Área APP legal | Imóveis Rurais | Ambiental / Fundiário | Sim | Não |
| Área Reserva Legal legal | Imóveis Rurais | Ambiental / Fundiário | Sim | Não |
| CAR | Imóveis Rurais | Fundiário / Ambiental | Sim | Não |
| CCIR | Imóveis Rurais | Fundiário | Sim | Não |
| ITR | Imóveis Rurais | Fiscal | Sim | Não |
| NIRF | Imóveis Rurais | Fiscal | Sim | Não |
| SIGEF | Imóveis Rurais | Fundiário / Geoespacial | Sim | Não |
| Matrículas | Imóveis Rurais | Fundiário | Sim | Não |
| Cartórios | Imóveis Rurais | Fundiário | Sim | Não |
| Proprietários | Imóveis Rurais | Fundiário / Jurídico | Sim | Não |
| Condôminos | Imóveis Rurais | Fundiário / Jurídico | Sim | Não |
| Representantes legais | Imóveis Rurais | Jurídico | Sim | Não |
| Procuradores | Imóveis Rurais | Jurídico | Sim | Não |
| Contratos | Imóveis Rurais | Jurídico | Sim | Não |
| Avaliações patrimoniais | Imóveis Rurais | Patrimonial | Sim | Não |
| Licenças ambientais | Compartilhado | Ambiental / Compliance | Sim | Não |
| Certificações | Compartilhado | ESG / Compliance | Sim | Não |
| Carbono | Compartilhado | ESG / Ambiental | Sim | Não |
| Recuperação ambiental | Compartilhado | Ambiental / Operacional | Sim | Não |

### Regras gerais

- A origem canônica é única.
- Replicação é permitida somente para leitura, cache, visualização ou consolidação operacional.
- Edição fora da origem é proibida.
- Campos derivados devem ser explicitamente marcados como derivados.

## Etapa 6 - Regras de Sincronização

### Quando um dado pode ser espelhado

Um dado pode ser espelhado quando:
- a UI precisa exibi-lo em outro contexto;
- o espelho não altera a informação canônica;
- a origem permanece única.

Exemplos:
- CAR exibido na propriedade operacional como leitura.
- NIRF exibido na tela operacional para contexto do usuário.
- Nome do imóvel exibido em dashboards de produção.

### Quando um dado pode ser replicado

Um dado pode ser replicado quando:
- o espelho é necessário para ergonomia do fluxo;
- a fonte oficial continua sendo a mesma;
- o espelho é marcado como leitura derivada.

Exemplos:
- Nome da propriedade espelhado no imóvel legal.
- Área legal espelhada na visão produtiva.
- Município e UF espelhados entre domínio territorial e fundiário.

### Quando um dado pode ser derivado

Um dado pode ser derivado quando:
- a fórmula é explícita;
- a origem dos insumos é conhecida;
- não existe necessidade de edição manual.

Exemplos:
- Área útil = área total - APP - Reserva Legal.
- Indicadores de produtividade por talhão.
- Percentual de área ambiental sobre o total.

### Quando um dado não pode ser duplicado

Um dado não pode ser duplicado quando:
- ele é jurídico, registral ou fiscal;
- a duplicação criaria duas verdades concorrentes;
- a edição em dois pontos pode gerar divergência.

Exemplos:
- matrícula;
- cartório;
- CAR;
- CCIR;
- ITR;
- NIRF;
- titularidade;
- poderes de representação;
- contratos.

## Etapa 7 - Rastreabilidade

### Cadeia oficial

```text
Produção
↓
Safra
↓
Talhão
↓
Gleba
↓
Propriedade
↓
Imóvel Rural
↓
Documentação
↓
Proprietários / Condôminos / Representantes
```

### Validação

O modelo suporta rastreabilidade completa porque:
- a produção é ancorada na safra e no talhão;
- o talhão pertence à propriedade operacional;
- a propriedade é sobreposta por um ou mais imóveis rurais;
- o imóvel rural contém a base documental e jurídica;
- a cadeia documental leva aos titulares e representantes.

### Melhoria recomendada

Para Projeto Raízes e exportações, a rastreabilidade deve carregar sempre:
- identificação da produção;
- identificação da safra;
- origem territorial;
- origem fundiária;
- documentação de suporte;
- evidência de compliance.

## Etapa 8 - ESG e Certificações

### Classificação oficial

| Conceito | Classificação | Justificativa |
|---|---|---|
| APP | Compartilhado | É território operacional e também obrigação legal. |
| Reserva Legal | Compartilhado | É território operacional e também obrigação legal. |
| Nascentes | Compartilhado | Podem ser operacionais, ambientais e de compliance. |
| Licenças | Compartilhado | São evidências de compliance, mas afetam operação e imóvel. |
| Certificações | Compartilhado | São transversais à produção, compliance e mercado. |
| ESG | Compartilhado | É uma camada analítica e regulatória transversal. |
| Carbono | Compartilhado | Depende de território, manejo e evidência documental. |
| Recuperação Ambiental | Compartilhado | Une execução operacional e comprovação legal/ambiental. |

### Regra de posicionamento

- `Imóveis Rurais` deve ser a fonte legal da conformidade ambiental quando existir documento formal.
- `Propriedades` deve ser a fonte operacional da execução ambiental.
- A camada ESG deve consolidar as duas visões sem duplicar a verdade.

## Etapa 9 - Projeto Raízes

### Resposta

**SIM**, o modelo suporta o Projeto Raízes.

### Justificativa

O Projeto Raízes depende de:
- rastreabilidade até a origem;
- vínculo entre produção e território;
- vínculo entre território e imóvel legal;
- evidência documental e ambiental;
- integridade da cadeia de custódia.

O modelo canônico proposto entrega essa cadeia porque:
- produção e safra ficam no domínio operacional;
- território e infraestrutura ficam no domínio de propriedades;
- titularidade e documentação ficam no domínio de imóveis rurais;
- ESG e certificações funcionam como camada compartilhada de evidência.

## Etapa 10 - Regras Arquiteturais Definitivas

## Regras definitivas

1. CAR pertence ao domínio `Imóveis Rurais`.
2. CCIR pertence ao domínio `Imóveis Rurais`.
3. ITR pertence ao domínio `Imóveis Rurais`.
4. NIRF pertence ao domínio `Imóveis Rurais`.
5. SIGEF pertence ao domínio `Imóveis Rurais`.
6. Matrículas pertencem ao domínio `Imóveis Rurais`.
7. Cartórios pertencem ao domínio `Imóveis Rurais`.
8. Proprietários, condôminos, representantes legais e procuradores pertencem ao domínio `Imóveis Rurais`.
9. Contratos de arrendamento, parceria e instrumentos correlatos pertencem ao domínio `Imóveis Rurais`.
10. Talhões pertencem ao domínio `Propriedades`.
11. Glebas pertencem ao domínio `Propriedades`.
12. Pastagens pertencem ao domínio `Propriedades`.
13. Infraestrutura operacional pertence ao domínio `Propriedades`.
14. Estradas e acessos pertencem ao domínio `Propriedades`.
15. Safras pertencem ao domínio operacional.
16. Produção pertence ao domínio operacional.
17. Nenhum campo pode ter duas fontes oficiais.
18. Dados espelhados não podem ser editados fora da origem.
19. Dados derivados devem ser explicitamente rotulados como derivados.
20. Toda rastreabilidade deve chegar até o Imóvel Rural.
21. Toda rastreabilidade deve preservar o vínculo com Propriedade e Talhão.
22. O domínio ambiental é compartilhado, mas a prova documental formal deve residir no eixo fundiário quando existir documento legal.
23. ESG, certificações e carbono são camadas transversais e não podem criar uma verdade paralela.
24. Propriedade não substitui Imóvel Rural.
25. Imóvel Rural não substitui Propriedade.
26. Um tenant pode ter múltiplas propriedades e múltiplos imóveis rurais.
27. Uma propriedade pode ser suportada por múltiplos imóveis rurais.
28. Um imóvel rural pertence a uma única propriedade operacional principal.
29. Um imóvel rural pode possuir múltiplos proprietários.
30. Um imóvel rural pode possuir múltiplas matrículas e múltiplos contratos.

## Respostas Objetivas

### 1. Qual é o modelo territorial oficial?

O modelo territorial oficial é:

```text
Tenant
└── Propriedade
    ├── Gleba
    ├── Talhão
    ├── Pastagem
    ├── Infraestrutura
    ├── Estrada / Acesso
    └── Área Ambiental
```

com hierarquias internas para área operacional, ambiental e infraestrutura.

### 2. Qual é o modelo fundiário oficial?

O modelo fundiário oficial é:

```text
Tenant
└── Imóvel Rural
    ├── Proprietários
    ├── Condôminos
    ├── Representantes Legais
    ├── Procuradores
    ├── Matrículas
    ├── Cartórios
    ├── CAR
    ├── CCIR
    ├── ITR
    ├── NIRF
    ├── SIGEF
    ├── Contratos
    ├── Documentos
    └── Avaliações
```

### 3. Qual a cardinalidade entre Propriedades e Imóveis Rurais?

**1:N**, com `Propriedade` como unidade operacional principal e `Imóvel Rural` como camada legal/patrimonial sobreposta.

### 4. Qual a fonte da verdade para cada domínio?

- `Propriedades`: território, operação, manejo, produção, infraestrutura, talhões, glebas, pastagens e rastreabilidade operacional.
- `Imóveis Rurais`: titularidade, registro, matrícula, cartório, CAR, CCIR, ITR, NIRF, SIGEF, contratos e avaliações.
- `Compartilhado`: ESG, certificações, carbono, recuperação ambiental e licenças, sempre sem multiplicar a fonte oficial.

### 5. Como a rastreabilidade deve funcionar?

Ela deve sair da produção e subir até o imóvel legal:

```text
Produção -> Safra -> Talhão -> Gleba -> Propriedade -> Imóvel Rural -> Documentação -> Titulares
```

### 6. O modelo suporta ESG?

**SIM.**

Ele suporta ESG porque combina:
- origem territorial;
- prova fundiária;
- evidência ambiental;
- rastreabilidade produtiva;
- camada compartilhada de certificações e carbono.

### 7. O modelo suporta o Projeto Raízes?

**SIM.**

O Projeto Raízes depende exatamente da cadeia de origem que este modelo formaliza.

### 8. Quais regras devem ser consideradas imutáveis daqui para frente?

- CAR, CCIR, ITR, NIRF, SIGEF, matrícula, cartório, titularidade e contratos são do domínio Imóveis Rurais.
- Talhões, glebas, pastagens, estradas, infraestrutura e safra operacional são do domínio Propriedades.
- Nenhum dado pode possuir duas fontes oficiais.
- Dados espelhados são somente leitura.
- Dados derivados devem ser explícitos.
- Toda rastreabilidade precisa alcançar o Imóvel Rural.
- ESG e certificações são transversais, não um terceiro domínio concorrente.
- Propriedade e Imóvel Rural coexistem, mas não se substituem.

## Conclusão

Este é o modelo canônico oficial de território, fundiário, rastreabilidade e ESG do AgroSaaS.

Ele resolve a fronteira entre `Propriedades` e `Imóveis Rurais`, preserva a operação agrícola, mantém a cadeia legal, e estabelece a base para certificações, exportação, Projeto Raízes e integrações futuras.
