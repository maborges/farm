# AGRI-DOMAIN-001

## Norma Oficial do Domínio Territorial e Fundiário do AgroSaaS

**Status:** APROVADA

**Categoria:** Arquitetura de Domínio

**Tipo:** Regra Arquitetural Imutável

**Origem:** ARCH-DOMAIN-01, ARCH-DOMAIN-02 e ARCH-DOMAIN-03

**Última Revisão:** 2026-06-20

---

# 1. Objetivo

Definir oficialmente:

* Os limites de responsabilidade entre os domínios Propriedades e Imóveis Rurais.
* A cardinalidade oficial entre ambos.
* A fonte da verdade para cada informação.
* As regras de rastreabilidade territorial e fundiária.
* As diretrizes obrigatórias para ESG, Certificações e Projeto Raízes.

Esta norma deve ser considerada a autoridade máxima sobre o domínio territorial e fundiário do AgroSaaS.

---

# 2. Domínio Propriedades

O módulo Propriedades representa o domínio:

* Operacional
* Territorial
* Produtivo

É responsável por:

* Propriedades
* Glebas
* Talhões
* Subtalhões
* Pastagens
* Estradas
* Infraestrutura
* Áreas Operacionais
* Safras
* Produção
* Manejo
* Custos Operacionais
* Indicadores Produtivos

## Fonte Oficial

Todos os dados relacionados à operação rural possuem como fonte oficial o domínio Propriedades.

---

# 3. Domínio Imóveis Rurais

O módulo Imóveis Rurais representa o domínio:

* Jurídico
* Patrimonial
* Documental
* Fiscal

É responsável por:

* Proprietários
* Condôminos
* Representantes Legais
* Procuradores
* Matrículas
* Cartórios
* CAR
* CCIR
* ITR
* NIRF
* SIGEF
* Contratos
* Avaliações
* Documentação Fundiária

## Fonte Oficial

Todos os dados relacionados à titularidade e comprovação legal do território possuem como fonte oficial o domínio Imóveis Rurais.

---

# 4. Cardinalidade Oficial

A cardinalidade oficial entre Propriedades e Imóveis Rurais é:

```text
Propriedade
      N
      │
      │
      N
Imóvel Rural
```

Implementação conceitual:

```text
Propriedade
      │
      ▼
PropriedadeImovel
      ▲
      │
Imóvel Rural
```

A entidade de vínculo é obrigatória.

---

# 5. Entidade PropriedadeImovel

A entidade PropriedadeImovel é responsável por:

* Tipo de vínculo
* Área vinculada
* Percentual vinculado
* Vigência
* Origem documental
* Vínculo principal
* Vínculo secundário
* Arrendamento
* Parceria
* Compartilhamento

Não deve armazenar dados operacionais nem fundiários.

Sua responsabilidade é exclusivamente representar o relacionamento entre os domínios.

---

# 6. Fonte da Verdade

## Propriedades

Responsável por:

* Talhões
* Glebas
* Pastagens
* Estradas
* Infraestrutura
* Produção
* Safras
* Operações
* Manejo

## Imóveis Rurais

Responsável por:

* Proprietários
* Condôminos
* Matrículas
* Cartórios
* CAR
* CCIR
* ITR
* NIRF
* SIGEF
* Contratos
* Avaliações

## Compartilhado

Podem atravessar ambos os domínios:

* ESG
* Certificações
* Carbono
* Recuperação Ambiental
* Licenciamento Ambiental

Sem criação de fonte duplicada.

---

# 7. Rastreabilidade Oficial

Toda cadeia de rastreabilidade do AgroSaaS deve seguir:

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
PropriedadeImovel
 ↓
Imóvel Rural
 ↓
Documentação
 ↓
Titularidade
```

Nenhum fluxo de rastreabilidade poderá terminar antes do domínio Imóveis Rurais.

---

# 8. Compatibilidade com ESG

O modelo deve permitir:

* Origem territorial comprovada
* Origem fundiária comprovada
* Cadeia de custódia
* Certificações
* Auditorias
* Indicadores ESG
* Carbono
* Recuperação ambiental

---

# 9. Compatibilidade com Projeto Raízes

O modelo deve suportar:

* Origem da produção
* Cadeia de custódia
* Certificações
* ESG
* Exportação
* Auditoria documental

Toda produção deve ser rastreável até o imóvel legal correspondente.

---

# 10. Regras Imutáveis

É proibido:

* Criar um terceiro domínio concorrente.
* Duplicar CAR em Propriedades.
* Duplicar CCIR em Propriedades.
* Duplicar ITR em Propriedades.
* Duplicar NIRF em Propriedades.
* Duplicar SIGEF em Propriedades.
* Duplicar Talhões em Imóveis Rurais.
* Duplicar Glebas em Imóveis Rurais.
* Duplicar Safras em Imóveis Rurais.
* Criar duas fontes oficiais para o mesmo dado.

É obrigatório:

* Utilizar cardinalidade N:N.
* Utilizar a entidade PropriedadeImovel.
* Garantir rastreabilidade completa.
* Garantir compatibilidade com ESG.
* Garantir compatibilidade com Certificações.
* Garantir compatibilidade com Projeto Raízes.

---

# 11. Vigência

Esta norma entra em vigor imediatamente.

Toda evolução futura deverá respeitar este documento.

Em caso de conflito:

1. AGRI-DOMAIN-001
2. Domain Map
3. Data Model
4. Routing Map
5. Engineering Playbook

Nesta ordem.
