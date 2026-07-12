# PERSON-PILOT-01B — Dry Run Operacional Completo da Jornada do Executor

**Status**: ✅ APROVADO
**Data da Execução**: 12 de Julho de 2026

## 1. Objetivo da Auditoria e Dry Run

Validar ponta a ponta a jornada operacional do executor no domínio `Pessoas` antes do início do piloto. O foco da validação foi o comportamento do `CadernoCampoService` ao receber e processar apontamentos (Web e PWA Offline) que contêm o novo campo estruturado `executado_por_pessoa_id`.

A validação foi feita simulando os exatos 7 cenários operacionais exigidos, utilizando o banco de dados oficial (schemas reais), integrando todas as validações de unidade produtiva (`PessoaRelacionamento`), e testando a carga offline pelo PWA.

## 2. Cenários e Veredictos

| Cenário | Descrição | Resultado |
|---------|-----------|-----------|
| **Cenário 1: Fluxo Feliz** | Seleção de executor (João) devidamente vinculado e com papel ativo na unidade produtiva correta (UP1) na data do apontamento. O serviço processa sem erros e armazena os IDs separados de `usuario_id` e `executado_por_pessoa_id`. | ✅ PASS |
| **Cenário 2: Pessoa de Outra UP** | Tentativa de registrar um apontamento usando um executor (Maria) cujo único relacionamento ativo pertence exclusivamente a uma Unidade Produtiva (UP2) diferente da UP do apontamento (UP1). O serviço bloqueia corretamente lançando `BusinessRuleError`. | ✅ PASS |
| **Cenário 3: Alocação Temporária** | Operador temporariamente emprestado para outra UP, sem mudar sua lotação de origem. É necessário um novo relacionamento em `PessoaRelacionamento` explícito para a UP destino na data do evento. Testado o bloqueio (quando ausente) e a liberação (quando presente). | ✅ PASS |
| **Cenário 4: Executor Sem Login** | O apontamento foi feito por um apontador/supervisor logado, registrando a execução para um prestador de serviço (Zezinho) que não possui usuário no sistema. O sistema aceita normalmente, validando apenas `PessoaRelacionamento` sem exigir `TenantUsuario`. | ✅ PASS |
| **Cenário 5: User != Pessoa** | O apontador (Usuário Logado) registra e a pessoa física em campo executa. Validou-se que a camada de persistência mantém perfeitamente isolado: `CadernoCampoEntrada.usuario_id` ≠ `CadernoCampoEntrada.executado_por_pessoa_id`. | ✅ PASS |
| **Cenário 6: Offline PWA** | Carga de sincronização offline (JSON payload). O serviço validou a associação do dispositivo à UP, hidratou corretamente os eventos, resolveu a rastreabilidade do executor e inseriu os apontamentos através da rotina `sincronizar_eventos_offline`. | ✅ PASS |
| **Cenário 7: Legado (Sem Executor)** | Para garantir retrocompatibilidade com aplicações antigas, fluxos legados que ainda não enviam o executor físico foram processados corretamente sem lançar erro de validação de Pessoa (`executado_por_pessoa_id` persistido como Nulo). | ✅ PASS |

## 3. Conclusão da Auditoria

**O domínio Pessoa está operacionalmente pronto para o piloto com as regras definidas pela Fase 1.**

- A separação entre identidade de acesso (IAM) e identidade operacional (Pessoa) funcionou com sucesso.
- O campo `executado_por_pessoa_id` está devidamente isolado de `usuario_id` em todos os fluxos e é transportado corretamente desde a requisição HTTP (Web e PWA Sync) até o banco de dados.
- O contrato estrito de que um executor deve pertencer explicitamente à UP do evento (`PessoaRelacionamento`) protege os dados multi-fazenda e atende à legislação trabalhista e de apropriação de custos.
- A sincronização offline do PWA está compatível com as mudanças arquiteturais.

A execução do piloto para a Fase 1 da Rastreabilidade do Executor pode prosseguir.
