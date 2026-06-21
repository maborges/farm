# ARCH-DOMAIN-03 - Validação Definitiva de Cardinalidade entre Propriedades e Imóveis Rurais

Data da análise: 2026-06-20

Escopo:
- Apenas análise arquitetural.
- Sem código, migrations, banco, APIs ou frontend.

Fontes lidas:
- [agrosaas-master-context.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-master-context.md)
- [agrosaas-domain-map.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-domain-map.md)
- [agrosaas-data-model.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-data-model.md)
- [agrosaas-routing-map.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-routing-map.md)
- [agrosaas-ai-rules.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-ai-rules.md)
- [propriedades-auditoria-arquitetural.md](/opt/lampp/htdocs/farm/docs/analysis/propriedades-auditoria-arquitetural.md)
- [arch-domain-01-consolidacao-propriedades-imoveis.md](/opt/lampp/htdocs/farm/docs/analysis/arch-domain-01-consolidacao-propriedades-imoveis.md)
- [agrosaas-territorial-canonical-model.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-territorial-canonical-model.md)

## Conclusão Executiva

A cardinalidade oficial do AgroSaaS entre `Propriedade` e `Imóvel Rural` deve ser **N:N**.

Motivo central:
- uma propriedade operacional pode ser suportada por múltiplos imóveis rurais;
- um imóvel rural pode sustentar múltiplas operações ou múltiplas propriedades funcionais;
- cenários reais de arrendamento parcial, grupos empresariais, uso misto e certificações exigem uma relação não redutível a um simples 1:N.

Essa cardinalidade deve ser implementada conceitualmente por uma entidade de ligação canônica, aqui tratada como `PropriedadeImovel`.

## Etapa 1 - Cenários Reais do Agronegócio

### Cenário 1 - Uma fazenda operacional formada por Matrícula A, B e C

Avaliação:
- O caso real é um único contexto operacional suportado por vários títulos legais.
- `1:N` até ajuda parcialmente se a relação for vista como "uma propriedade com vários imóveis".
- Porém, a cardinalidade precisa também cobrir o inverso quando um mesmo imóvel é compartilhado por mais de uma operação.

Conclusão:
- `N:N` cobre o cenário sem limitar cenários futuros.

### Cenário 2 - Um único imóvel rural utilizado por agricultura, pecuária e reflorestamento

Avaliação:
- Um mesmo imóvel legal pode hospedar múltiplas unidades operacionais ou linhas de negócio.
- Se o AgroSaaS modelar cada unidade como uma propriedade operacional distinta, um mesmo imóvel precisa se conectar a várias propriedades.

Conclusão:
- `N:N` é a única forma que preserva a realidade de uso misto sem forçar duplicação de imóvel.

### Cenário 3 - Arrendamento parcial

Avaliação:
- Parte da área pode ser própria.
- Parte pode ser arrendada.
- A relação precisa carregar percentual, área, vigência e tipo de vínculo.

Conclusão:
- `N:N` é necessário para representar coexistência de títulos, uso e contratos.

### Cenário 4 - Grupo empresarial

Avaliação:
- Um mesmo imóvel pode servir a diferentes operações, veículos societários ou centros operacionais.
- A operação não se confunde com a titularidade.

Conclusão:
- `N:N` permite separar propriedade legal de uso operacional.

### Cenário 5 - Projeto Raízes

Avaliação:
- A rastreabilidade precisa seguir da produção até a origem fundiária exata.
- Em cadeias complexas, a origem pode envolver mais de um imóvel e mais de uma operação.

Conclusão:
- `N:N` oferece aderência superior para rastreabilidade e cadeia de custódia.

## Etapa 2 - Análise de Cardinalidade

### Tabela comparativa

| Cardinalidade | Simplicidade | Flexibilidade | Escalabilidade | ESG | Certificações | Rastreabilidade | Complexidade de implementação | Complexidade de manutenção |
|---|---|---|---|---|---|---|---|---|
| `1:1` | Alta | Muito baixa | Baixa | Fraca | Fraca | Fraca | Baixa | Baixa |
| `1:N` | Alta | Média | Média | Parcial | Parcial | Parcial | Baixa/Média | Média |
| `N:1` | Alta | Média | Média | Parcial | Parcial | Parcial | Baixa/Média | Média |
| `N:N` | Média | Alta | Alta | Forte | Forte | Forte | Média/Alta | Média/Alta |

### Leitura objetiva

- `1:1` é simples, mas artificial para o agronegócio real.
- `1:N` resolve o caso de várias matrículas em uma fazenda, mas falha quando um imóvel participa de várias operações.
- `N:1` é apenas a inversão semântica de `1:N` e tem a mesma limitação estrutural.
- `N:N` é o único modelo que suporta o conjunto completo de cenários reais.

## Etapa 3 - Impacto no Data Model

### Banco de dados

Impacto:
- exige entidade de associação canônica;
- evita que um lado carregue múltiplos significados em uma FK simples;
- permite registrar vigência, área, percentual, papel e origem documental.

### SQLAlchemy

Impacto:
- relacionamento deixa de ser puramente unidirecional;
- a associação passa a ser entidade de primeira classe;
- consultas precisam navegar pela tabela de vínculo.

### APIs

Impacto:
- endpoints precisam expor o vínculo entre imóvel e propriedade;
- filtros passam a considerar vínculo principal, vínculo parcial e vigência;
- a API não pode inferir sozinho o papel do vínculo apenas pela presença da FK.

### Frontend

Impacto:
- a UI precisa exibir o vínculo e não apenas a referência simples;
- telas de propriedade e imóvel devem indicar "imóvel principal", "imóvel parcial", "vínculo temporário" e "fonte documental";
- relatórios ficam mais fiéis ao contexto real.

### RLS

Impacto:
- o `tenant_id` continua sendo a fronteira de isolamento;
- a associação não altera o princípio de isolamento, mas aumenta a necessidade de consistência entre entidades dentro do mesmo tenant.

### Relatórios

Impacto:
- melhora consolidação de área por imóvel, por propriedade e por operação;
- evita contagem dupla de área;
- permite relatórios legais e operacionais separados.

### Dashboards

Impacto:
- dashboards operacionais continuam ancorados na propriedade;
- dashboards legais e patrimoniais continuam ancorados no imóvel;
- dashboards consolidados podem atravessar a associação sem perder rastreabilidade.

### Rastreabilidade

Impacto:
- fortalece a trilha da produção até a origem fundiária;
- permite provar que uma produção passou por um imóvel específico em uma janela temporal específica;
- reduz ambiguidade em auditorias e certificações.

## Etapa 4 - Impacto no Projeto Raízes

### Origem da produção

- `N:N` é o modelo que melhor preserva a origem real quando há mistura de títulos, parcelas e operações.

### Cadeia de custódia

- a cadeia de custódia fica mais precisa porque cada produção pode ser ligada ao conjunto exato de propriedades e imóveis que a sustentam.

### Certificações

- certificações tendem a exigir prova fundiária e operacional simultaneamente;
- `N:N` evita simplificações indevidas em propriedades com múltiplos títulos.

### ESG

- ESG exige contexto territorial, titularidade e manejo;
- `N:N` melhora a prova semântica e documental da relação entre uso e origem.

### Exportação

- exportação e mercados regulados se beneficiam de rastreabilidade granular;
- a origem legal não pode ser perdida em uma modelagem simplificada.

## Etapa 5 - Recomendação Final

### Cardinalidade oficial do AgroSaaS

**N:N**

### Justificativa técnica

`N:N` é a única cardinalidade que:
- suporta múltiplos imóveis compondo uma única operação;
- suporta um mesmo imóvel servindo a múltiplas operações;
- representa arrendamento parcial, uso misto e grupos empresariais;
- mantém aderência para ESG, certificações e Projeto Raízes;
- preserva a separação entre domínio operacional e domínio legal.

### Observação importante

Adotar `N:N` não significa que o sistema deve perder simplicidade.
Significa que a simplicidade deve ficar na experiência do usuário, enquanto o modelo interno mantém a precisão necessária.

## Etapa 6 - Modelo Canônico para N:N

### Estrutura conceitual

```text
Propriedade
└── PropriedadeImovel
    └── Imóvel Rural
```

### Ownership

- `Propriedade` é dona da dimensão operacional.
- `Imóvel Rural` é dono da dimensão legal/fundiária.
- `PropriedadeImovel` é dona do vínculo e da semântica de associação.

### Responsabilidades

#### Propriedade
- organizar talhões, glebas, pastagens, infraestrutura, safra e produção;
- representar a operação real no campo.

#### Imóvel Rural
- organizar titularidade, matrícula, cartório, documentos, contratos, avaliações e atributos legais;
- representar a prova jurídica do território.

#### PropriedadeImovel
- registrar o relacionamento entre os dois domínios;
- armazenar papel do vínculo;
- indicar se é vínculo principal, parcial, temporário, arrendado, parceiro ou de compartilhamento;
- registrar área vinculada, percentuais, vigência e origem documental.

### Regras de negócio

1. Um vínculo deve sempre apontar para um tenant único.
2. Um vínculo não altera a titularidade do imóvel.
3. Um vínculo não altera a natureza operacional da propriedade.
4. O vínculo deve permitir múltiplos papéis por imóvel e por propriedade.
5. Vínculos temporários devem carregar vigência.
6. Vínculos parciais devem carregar área ou percentual.
7. O vínculo principal deve ser explicitamente marcado.
8. Toda rastreabilidade deve usar o vínculo para provar origem fundiária.

### Rastreabilidade no modelo N:N

```text
Produção
↓
Safra
↓
Talhão
↓
Propriedade
↓
PropriedadeImovel
↓
Imóvel Rural
↓
Documentação
↓
Titularidade
```

## Cenários que o N:N resolve

- fazenda com várias matrículas;
- um imóvel com uso agrícola, pecuário e florestal;
- arrendamento parcial;
- parceria rural parcial;
- grupos empresariais com operação compartilhada;
- certificações com prova de origem mais granular;
- Project Raízes com cadeia de custódia precisa.

## Cenários que o N:N não resolve sozinho

- titularidade jurídica detalhada sem modelo próprio de proprietário/condômino;
- usufruto e garantias reais sem expansão fundiária;
- regras tributárias específicas sem camada fiscal dedicada;
- conflitos de sobreposição territorial sem motor geoespacial mais robusto.

## Impacto para ESG

`N:N` melhora o ESG porque:
- permite relacionar a operação ao imóvel legal correto;
- evita perda de origem em cadeias complexas;
- mantém a prova documental associada ao vínculo certo;
- facilita auditoria ambiental e certificação.

## Impacto para o Projeto Raízes

`N:N` é a melhor cardinalidade para o Projeto Raízes porque:
- a origem precisa ser auditável;
- a cadeia pode atravessar mais de um imóvel e mais de uma operação;
- a prova de custódia precisa ser histórica e não apenas instantânea;
- a associação permite revelar o contexto exato da produção.

## Imutabilidade da Decisão

### Deve ser considerada imutável?

**Sim, como regra de arquitetura de domínio.**

### Condição

Ela só deve ser revista se o AgroSaaS abandonar a exigência de rastreabilidade fundiária e de suporte a cenários reais de arrendamento, uso misto e múltiplas matrículas. Isso não é compatível com a direção atual do produto.

## Respostas Objetivas

### 1. Qual cardinalidade deve ser adotada?

**N:N**

### 2. Quais cenários ela resolve?

- múltiplas matrículas em uma fazenda;
- um imóvel com múltiplas operações;
- arrendamento parcial;
- parceria rural;
- grupos empresariais;
- certificações;
- ESG;
- Projeto Raízes;
- rastreabilidade de cadeia de custódia.

### 3. Quais cenários ela não resolve?

- detalhamento jurídico de titularidade sem entidades adicionais;
- usufruto, hipoteca e garantias reais sem expansão fundiária;
- conflitos geoespaciais sem camada territorial mais robusta.

### 4. Qual o impacto para ESG?

Positivo e alto.
O `N:N` permite manter a prova da origem territorial, documental e operacional sem simplificações indevidas.

### 5. Qual o impacto para o Projeto Raízes?

Positivo e alto.
O modelo suporta origem, custódia, documentação e vínculo legal com granularidade suficiente.

### 6. Essa decisão deve ser considerada imutável para o AgroSaaS?

**Sim, como regra normativa do domínio.**

## Recomendação Final

O AgroSaaS deve congelar a cardinalidade oficial entre `Propriedade` e `Imóvel Rural` como **N:N**, implementada conceitualmente por uma entidade de vínculo canônica.

Isso elimina a limitação de um `1:N` simplificado e garante aderência ao agronegócio real, à rastreabilidade, ao ESG, às certificações e ao Projeto Raízes.
