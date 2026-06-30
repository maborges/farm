# PERSON-ARCH-01 — DOMINIO PESSOAS

## 1. Objetivo

Este documento define a arquitetura canônica do dominio Pessoas do AgroSaaS para a versao 1.0 e a estrategia segura de transicao a partir do modelo hibrido identificado nas auditorias:

- `RC-01-AUDITORIA-DOMINIO-PESSOAS`
- `RC-01A-AUDITORIA-IDENTIDADE-PESSOA-USUARIO`
- `RC-01B-AUDITORIA-COLABORADOR-PESSOA-RH`
- `RC-01C-AUDITORIA-FORNECEDOR-PESSOA`

Pergunta que este documento responde:

**Qual deve ser a arquitetura canônica de Pessoas para a versao 1.0 do AgroSaaS e qual sera a estrategia segura de transicao?**

## 2. Decisao arquitetural

### 2.1 Arquitetura alvo oficial

A arquitetura oficial do dominio Pessoas do AgroSaaS passa a ser:

```text
Pessoa
  ├── Usuario opcional
  ├── ColaboradorRH opcional
  ├── Fornecedor opcional
  ├── Cliente opcional
  ├── Prestador opcional
  ├── Responsavel Tecnico opcional
  ├── Parceiro opcional
  └── outros papeis via TipoRelacionamento/PessoaRelacionamento
```

### 2.2 Principio central

`Pessoa` e a identidade civil ou organizacional canônica.

Tudo o que representar um individuo ou uma organizacao do tenant deve, a longo prazo, convergir para `Pessoa` como fonte primaria de identidade.

### 2.3 Estado atual reconhecido

O sistema ainda opera em modelo hibrido.

Portanto:

- a arquitetura alvo fica definida agora;
- a consolidacao total nao e obrigatoria para a v1.0;
- a transicao deve ocorrer por compatibilidade, resolvers e migracao progressiva;
- nenhum legado deve ser removido antes de migracao segura e auditada.

## 3. Entidades centrais

### 3.1 Pessoa

Definicao oficial:

- identidade civil ou organizacional do tenant;
- base canônica para individuo ou organizacao;
- dona dos dados mestres de documento, contato, endereco, dados bancarios, PII e consentimento;
- ancora de papeis por `TipoRelacionamento` e `PessoaRelacionamento`.

Responsabilidades:

- armazenar identidade base;
- suportar LGPD e governanca de dados;
- servir de referencia para modulos novos e fluxos consolidados.

### 3.2 Usuario

Definicao oficial:

- identidade de autenticacao, acesso, sessao e RBAC;
- sujeito de login, convite, membership de tenant e escopo de unidade produtiva.

Nao e definicao oficial de `Usuario`:

- nao e a identidade civil canônica;
- nao e o cadastro mestre de pessoa;
- nao deve originar novos cadastros paralelos de dados pessoais.

Diretriz:

- `Usuario` deve evoluir para ter vinculo explicito com `Pessoa`;
- esse vinculo pode ser ausente em dados legados;
- novos fluxos devem tratar `Usuario` como identidade de acesso, nao como master data pessoal.

### 3.3 ColaboradorRH

Definicao oficial:

- vinculo trabalhista e operacional;
- recurso de custo e mao de obra;
- especializacao operacional de trabalhador usada por RH, Campo, diarias, empreitadas, SST, EPI, caderno e custos.

Diretriz:

- `ColaboradorRH` nao e a identidade civil canônica;
- ele deve convergir para especializacao de `Pessoa`, mas sem ruptura de fluxos legados;
- enquanto o legado existir, `ColaboradorRH` pode continuar com `pessoa_id` opcional e dados proprios por compatibilidade.

### 3.4 Fornecedor

Definicao oficial:

- wrapper operacional de compras e suprimentos;
- projeção de uso operacional de uma `Pessoa` com papel `FORNECEDOR`;
- portador de metadados comerciais especificos de compras.

Diretriz:

- `Fornecedor` nao e master data independente a longo prazo;
- `Pessoa` e a identidade canônica;
- `Fornecedor` pode permanecer como wrapper operacional enquanto existirem consumidores legados.

### 3.5 Cliente

Definicao oficial:

- papel comercial de uma `Pessoa`;
- representa comprador, cliente ou contraparte comercial quando o fluxo canônico estiver consolidado.

Estado atual reconhecido:

- comercializacao ja usa `comprador_id -> Pessoa`;
- financeiro ainda aceita `Receita.cliente` textual;
- portanto o dominio cliente ainda e parcialmente hibrido.

Diretriz:

- `Cliente` nao deve nascer como novo cadastro paralelo;
- deve ser modelado por `Pessoa` + papel `CLIENTE`, com compatibilidade textual quando necessario.

### 3.6 LeadCRM

Definicao oficial:

- pre-cadastro comercial e entidade pre-conversao;
- representa prospect ainda nao consolidado como `Pessoa`.

Diretriz:

- `LeadCRM` pode continuar independente enquanto estiver em estado pre-conversao;
- apos conversao comercial, a identidade operacional alvo deve ser `Pessoa`;
- nenhum novo fluxo deve tratar `LeadCRM` como substituto definitivo de `Pessoa`.

### 3.7 TipoRelacionamento

Definicao oficial:

- catalogo de papeis que uma `Pessoa` pode assumir;
- inclui papeis sistemicos e extensoes por tenant.

Exemplos:

- `FORNECEDOR`
- `CLIENTE`
- `FUNCIONARIO`
- `PRESTADOR`
- `PARCEIRO`
- `RESPONSAVEL_TECNICO`

### 3.8 PessoaRelacionamento

Definicao oficial:

- pivot entre `Pessoa` e papel;
- mecanismo oficial para afirmar que uma `Pessoa` atua como fornecedor, cliente, colaborador, prestador ou outro papel em determinado contexto.

Diretriz:

- novos papeis nao devem gerar novas entidades mestres paralelas sem passar por `PessoaRelacionamento`.

## 4. Separacao conceitual oficial

### 4.1 Pessoa

`Pessoa` = identidade civil ou organizacional.

### 4.2 Usuario

`Usuario` = autenticacao, acesso, sessao, membership e RBAC.

### 4.3 ColaboradorRH

`ColaboradorRH` = vinculo trabalhista e operacional, recurso de custo, mao de obra e trabalhador de campo.

### 4.4 Fornecedor

`Fornecedor` = papel ou wrapper operacional de compras e suprimentos.

### 4.5 Cliente / Comprador

`Cliente` = papel comercial de `Pessoa`.

`Comprador` em comercializacao deve ser tratado como manifestacao operacional desse papel.

### 4.6 LeadCRM

`LeadCRM` = identidade comercial pre-conversao, anterior ao cadastro canônico de `Pessoa`.

## 5. Compatibilidade legada

### 5.1 Usuario sem Pessoa

Suporte legado permitido:

- `Usuario` pode continuar existindo sem `Pessoa` vinculada em dados antigos;
- onboarding, convites, auth e Campo continuam funcionando sem FK obrigatoria nesta fase.

Regra:

- novos desenvolvimentos nao devem reforcar `Usuario` como fonte primaria de dados pessoais;
- quando houver resolver, ele deve ser consultado antes de criar nova duplicidade.

### 5.2 ColaboradorRH sem Pessoa

Suporte legado permitido:

- `ColaboradorRH` pode continuar existindo sem `pessoa_id`;
- RH, Campo, SST, EPI, caderno, diarias e custos continuam aceitando essa realidade enquanto durar a transicao.

Regra:

- nenhum novo fluxo deve assumir que `ColaboradorRH` e a identidade civil canônica;
- quando houver resolver, a leitura deve preferir `pessoa_id`.

### 5.3 Fornecedor com `pessoa_id` opcional

Suporte legado permitido:

- `Fornecedor` pode continuar com `pessoa_id` opcional;
- cadastro operacional continua existindo enquanto compras, estoque e financeiro ainda dependem dele.

Regra:

- novos fluxos devem preferir resolver `Pessoa`;
- o wrapper `Fornecedor` continua valido para metadados comerciais e compatibilidade.

### 5.4 `Despesa.fornecedor` textual

Suporte legado permitido:

- `Despesa.fornecedor` continua aceito como fallback textual;
- nao deve ser removido na v1.0.

Regra:

- nao deve ser usado como fonte primaria em novos fluxos quando houver `pessoa_id` resolvivel.

### 5.5 `Receita.cliente` textual

Suporte legado permitido:

- `Receita.cliente` continua aceito como fallback textual.

Regra:

- novos fluxos devem priorizar `pessoa_id`;
- o campo textual permanece apenas por compatibilidade.

### 5.6 `nome_trabalhador`

Suporte legado permitido:

- `nome_trabalhador` permanece nos fluxos de caderno e Campo PWA;
- nao deve ser removido antes da migracao completa dos consumidores offline e operacionais.

Regra:

- nao pode ser introduzido como nova fonte primaria em fluxos novos.

### 5.7 `fornecedor_nome`

Suporte legado permitido:

- `fornecedor_nome` permanece em cotacoes, pedidos e analytics de compras enquanto o fluxo ainda nao estiver consolidado.

Regra:

- deve ser tratado como fallback legado;
- nao deve originar novas modelagens paralelas.

### 5.8 LeadCRM independente

Suporte legado permitido:

- `LeadCRM` continua independente enquanto estiver em estado pre-conversao.

Regra:

- apos conversao, a identidade mestre deve ser `Pessoa`;
- nao se deve expandir `LeadCRM` para substituir a modelagem canônica de pessoas.

## 6. Resolves futuros obrigatorios

Este documento define quatro resolvers futuros como parte da estrategia segura de transicao.

Eles ainda nao sao implementados aqui. Sao definicoes arquiteturais obrigatorias.

### 6.1 PessoaIdentityResolver

Responsabilidade:

```text
Usuario -> Pessoa
```

Objetivo:

- resolver o vinculo entre identidade de acesso e identidade civil;
- permitir onboarding, convites, equipe, perfil e futuras auditorias sem duplicar dados pessoais.

Comportamento alvo:

```text
Usuario.pessoa_id explicito
fallback match controlado por documento/email
fallback usuario sem pessoa vinculada
```

### 6.2 TrabalhadorResolver

Responsabilidade:

```text
ColaboradorRH.pessoa_id
fallback ColaboradorRH
fallback nome_trabalhador
```

Objetivo:

- unificar leitura de trabalhador em RH, Campo, custos, caderno, SST e EPI;
- preservar compatibilidade com `colaborador_id`, `trabalhador_id` e campos textuais.

Comportamento alvo:

```text
1. usar ColaboradorRH.pessoa_id quando existir
2. usar ColaboradorRH como identidade operacional quando nao houver pessoa
3. usar nome_trabalhador apenas como fallback legado explicito
```

### 6.3 FornecedorResolver

Responsabilidade:

```text
Fornecedor.pessoa_id
fallback documento
fallback nome controlado
fallback texto
```

Objetivo:

- unificar fornecedor entre compras, estoque, recebimento, despesas e analytics;
- preservar compatibilidade com `fornecedor_nome`, `fornecedor` textual e `compras_fornecedores`.

Comportamento alvo:

```text
1. usar Fornecedor.pessoa_id quando existir
2. resolver por documento quando possivel
3. resolver por nome controlado quando permitido
4. manter texto apenas como fallback explicito
```

### 6.4 ClienteResolver

Responsabilidade:

```text
Pessoa com papel CLIENTE
fallback Receita.cliente textual
fallback Comercializacao.comprador_id
```

Objetivo:

- unificar cliente, comprador e contraparte comercial;
- permitir convergencia entre comercializacao, financeiro e CRM convertido.

Comportamento alvo:

```text
1. usar Pessoa com papel CLIENTE quando existir
2. aceitar comprador_id canônico de comercializacao
3. manter Receita.cliente como fallback textual legado
```

## 7. Regras obrigatorias para novos fluxos

### 7.1 Regra de identidade

Todo novo fluxo deve usar `Pessoa` como identidade canônica quando representar individuo ou organizacao do tenant.

### 7.2 Regra de papel

Todo novo papel deve ser expresso por `TipoRelacionamento` e `PessoaRelacionamento`, salvo excecao arquitetural documentada.

### 7.3 Regra de nao duplicacao

E proibido criar novo cadastro mestre paralelo para:

- pessoa
- cliente
- fornecedor
- trabalhador
- parceiro
- responsavel tecnico

sem justificativa arquitetural formal e sem compatibilidade com `Pessoa`.

### 7.4 Regra de texto livre

Campos textuais legados podem existir apenas como:

- fallback
- compatibilidade
- importacao
- preservacao historica

Nao podem ser criados como nova fonte primaria para representar identidades.

### 7.5 Regra de resolver

Enquanto houver legado, todo novo fluxo que toque dominio hibrido deve usar o resolver correspondente assim que ele existir.

## 8. Regras para a versao 1.0

### 8.1 Obrigatorio antes da v1.0

- documentacao arquitetural oficial do dominio Pessoas
- congelamento de novos cadastros paralelos de pessoa
- definicao formal de `Pessoa` como identidade canônica
- definicao formal de `Usuario` como identidade de autenticacao/acesso
- definicao formal de `ColaboradorRH` como vinculo operacional/trabalhista
- definicao formal de `Fornecedor` como wrapper operacional com ponte para `Pessoa`
- orientacao para onboarding e futuro Wizard usarem `Pessoa` como referencia canônica
- definicao arquitetural dos resolvers prioritarios:
  - `PessoaIdentityResolver`
  - `TrabalhadorResolver`
  - `FornecedorResolver`
  - `ClienteResolver`

### 8.2 Pode ficar para v1.1

- remocao de campos textuais legados
- migrations destrutivas
- obrigatoriedade plena de `Pessoa` em todos os fluxos existentes
- consolidacao completa de CRM
- remocao de wrappers legados
- eliminacao total de duplicidades historicas em `Usuario`, `ColaboradorRH` e `Fornecedor`

## 9. Estrategia segura de transicao

### Fase 1 — Congelar arquitetura

Objetivo:

- impedir novos cadastros paralelos de pessoa;
- reconhecer `Pessoa` como entidade canônica oficial;
- alinhar arquitetura sem mudar o banco ainda.

Regra:

- nenhum novo modulo pode criar master data paralelo de identidade humana ou organizacional.

### Fase 2 — Criar resolvers

Objetivo:

- introduzir leitura canônica sem quebrar compatibilidade.

Resolvers priorizados:

- `PessoaIdentityResolver`
- `TrabalhadorResolver`
- `FornecedorResolver`
- `ClienteResolver`

### Fase 3 — Migrar novos fluxos

Objetivo:

- garantir que toda funcionalidade nova use `Pessoa` como identidade primária;
- impedir crescimento adicional da divergencia estrutural.

### Fase 4 — Migrar consumidores existentes

Objetivo:

- adaptar gradualmente RH, compras, financeiro, Campo PWA e CRM;
- preservar contratos legados enquanto houver dependencia operacional.

Consumidores prioritarios:

- onboarding e equipe
- RH
- Campo PWA
- compras
- financeiro
- CRM

### Fase 5 — Remocao controlada de legado

Objetivo:

- eliminar duplicidade estrutural somente quando:
  - a migracao de dados estiver validada;
  - os testes cobrirem compatibilidade;
  - os consumidores estiverem migrados;
  - a auditoria confirmar baixo risco.

Regra:

- nenhuma remocao destrutiva ocorre antes disso.

## 10. Normas para Wizard e implantacao

### 10.1 Wizard

O futuro Assistente de Implantacao deve tratar `Pessoa` como base oficial de identidade.

Aplicacoes:

- fornecedor novo deve nascer como `Pessoa` com papel `FORNECEDOR`, ainda que um wrapper operacional seja mantido;
- cliente novo deve nascer como `Pessoa` com papel `CLIENTE`;
- colaborador novo deve, quando o fluxo estiver pronto, privilegiar `Pessoa` antes de `ColaboradorRH`;
- usuario novo deve ter estrategia explicita de vinculo com `Pessoa`.

### 10.2 Onboarding

O onboarding da v1.0 pode continuar operando com `Usuario` como identidade de acesso.

Mas a referencia arquitetural oficial passa a ser:

- `Usuario` nao substitui `Pessoa`;
- onboarding futuro deve criar ou vincular `Pessoa` por estrategia controlada.

## 11. Anti-padroes explicitamente proibidos

Ficam proibidos para novos desenvolvimentos:

- criar nova tabela mestre paralela de pessoa
- usar campo textual novo como fonte primaria de cliente, fornecedor ou trabalhador
- tratar `Usuario` como master data civil definitivo
- tratar `ColaboradorRH` como identidade civil definitiva
- criar fluxo novo que ignore `Pessoa` quando o conceito modelado for pessoa ou organizacao

## 12. Resumo normativo

### 12.1 Fonte canônica

`Pessoa` e a fonte canônica de identidade civil/organizacional.

### 12.2 Identidade de acesso

`Usuario` e a identidade de autenticacao, acesso e RBAC.

### 12.3 Especializacoes operacionais

- `ColaboradorRH` = vinculo operacional e trabalhista
- `Fornecedor` = wrapper operacional de compras
- `Cliente` = papel comercial de `Pessoa`
- `LeadCRM` = pre-conversao comercial

### 12.4 Legado

Campos textuais e estruturas legadas permanecem apenas como compatibilidade, nunca como direcao arquitetural futura.

## 13. Resposta arquitetural final

**A arquitetura canônica do dominio Pessoas para a versao 1.0 do AgroSaaS fica definida com `Pessoa` como identidade civil/organizacional canônica, `Usuario` como identidade de acesso, `ColaboradorRH` como vinculo operacional/trabalhista, `Fornecedor` como wrapper operacional de compras e `Cliente` como papel comercial de `Pessoa`, com transicao segura baseada em resolvers e compatibilidade legada, sem consolidacao destrutiva antes da migracao progressiva dos consumidores.**
