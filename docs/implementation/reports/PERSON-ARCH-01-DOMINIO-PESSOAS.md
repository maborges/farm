# PERSON-ARCH-01 — RELATORIO DE CONSOLIDACAO DO DOMINIO PESSOAS

## 1. Objetivo

Este relatorio registra a consolidacao documental da arquitetura oficial do dominio Pessoas com base exclusiva nas auditorias:

- `RC-01`
- `RC-01A`
- `RC-01B`
- `RC-01C`

Entregavel principal criado nesta execucao:

- [PERSON-ARCH-01-DOMINIO-PESSOAS.md](/opt/lampp/htdocs/farm/docs/architecture/PERSON-ARCH-01-DOMINIO-PESSOAS.md)

## 2. Decisao consolidada

A arquitetura alvo oficial do AgroSaaS passa a ser:

```text
Pessoa
  ├── Usuario opcional
  ├── ColaboradorRH opcional
  ├── Fornecedor opcional
  ├── Cliente opcional
  ├── Prestador opcional
  ├── Responsavel Tecnico opcional
  └── outros papeis
```

Decisoes normativas consolidadas:

- `Pessoa` = identidade civil/organizacional oficial
- `Usuario` = autenticacao, acesso e RBAC
- `ColaboradorRH` = vinculo operacional/trabalhista
- `Fornecedor` = wrapper operacional de compras com ponte para `Pessoa`
- `Cliente` = papel comercial de `Pessoa`
- `LeadCRM` = pre-conversao comercial

## 3. Compatibilidade definida

O documento arquitetural oficializa a convivencia segura com:

- `Usuario` sem `Pessoa`
- `ColaboradorRH` sem `Pessoa`
- `Fornecedor` com `pessoa_id` opcional
- `Despesa.fornecedor` textual
- `Receita.cliente` textual
- `nome_trabalhador`
- `fornecedor_nome`
- `LeadCRM` independente

Diretriz central:

- nenhum desses legados e reconhecido como direcao arquitetural futura;
- todos passam a ser tratados como compatibilidade, fallback ou transicao.

## 4. Resolvers futuros definidos

Foram definidos como obrigatorios para a estrategia de transicao:

- `PessoaIdentityResolver`
- `TrabalhadorResolver`
- `FornecedorResolver`
- `ClienteResolver`

## 5. Recorte v1.0 x v1.1

### Obrigatorio antes da v1.0

- arquitetura oficial documentada
- `Pessoa` definida como fonte oficial
- congelamento de novos cadastros paralelos
- regras para novos fluxos
- definicao formal dos resolvers futuros

### Pode ficar para v1.1

- remocao de campos textuais
- migrations destrutivas
- consolidacao total dos consumidores legados
- obrigatoriedade plena de `Pessoa` em todos os fluxos antigos

## 6. Estrategia de transicao consolidada

Fases definidas:

1. congelar arquitetura
2. criar resolvers
3. migrar novos fluxos
4. migrar consumidores existentes
5. remover legado de forma controlada

## 7. Confirmacoes de aceite

- A arquitetura alvo de Pessoas foi definida.
- `Pessoa` foi definida como identidade oficial.
- `Usuario` foi definido como identidade de autenticacao/acesso.
- `ColaboradorRH` foi definido como vinculo operacional/trabalhista.
- `Fornecedor` foi definido como wrapper/papel operacional.
- A estrategia de compatibilidade com legado foi definida.
- Os resolvers futuros foram definidos.
- O que entra na v1.0 e o que fica para v1.1 foi separado.
- Nenhuma alteracao operacional foi feita.

## 8. Resposta final obrigatoria

**Apos esta execucao, qualquer novo desenvolvimento no AgroSaaS passa a ter uma referencia arquitetural clara para representar Pessoas, Usuarios, Colaboradores, Fornecedores, Clientes e papeis relacionados, sem criar novos cadastros paralelos ou duplicidades estruturais.**
