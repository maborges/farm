# AUDIT-01: Auditoria Arquitetural do AgroSaaS

## 1. Resumo executivo
A auditoria técnica AUDIT-01 foi realizada para avaliar a separação de camadas, violações de domínio, bypass de regras oficiais, e riscos de evolução do AgroSaaS. Foram identificados pontos de acoplamento indevido, principalmente entre routers acessando a base de dados diretamente e cruzamento de fronteiras entre domínios (Estoque e Financeiro). A estrutura base do projeto é sólida, mas pequenas correções incrementais são necessárias para garantir escalabilidade e manutenção da saúde do sistema multi-tenant.

## 2. Escopo auditado
A auditoria cobriu os seguintes diretórios no backend (FastAPI/Python):
- `services/api/financeiro/*`
- `services/api/operacional/*`
- `services/api/core/*`
- `services/api/agricola/*`
- `services/api/campo/*`

*Front-end e outras pastas foram analisadas superficialmente devido à concentração de violações severas encontradas logo na camada de backend.*

## 3. Mapa arquitetural observado
- Padrão arquitetural pretendido: Arquitetura em Camadas com Domain-Driven Design (DDD) modular.
- Camada de Routers (Controllers): Responsável por expor endpoints REST.
- Camada de Services: Concentra regras de negócio e intermediação com banco de dados.
- Camada de Models: Mapeamento ORM (SQLAlchemy) das entidades.
- Integração entre módulos percebida: Módulos como Operacional e Financeiro ocasionalmente interagem de forma direta, burlando os limites modulares desejados.

## 4. Pontos positivos encontrados
- Uso consistente de `tenant_id` garantindo multi-tenant na maioria dos services e schemas.
- Validação de contexto operacional (`validate_deposito_context`, `validate_lote_context`) nas operações de estoque.
- Implementação assistida de estoque (`SALDO_INICIAL` com origem `IMPLANTACAO`) corretamente implementada através do ledger (`registrar_ledger_estoque`).

## 5. Achados classificados por severidade
- **P0 Crítico**: 0
- **P1 Alto**: 2
- **P2 Médio**: 2
- **P3 Baixo**: 0

## 6. Detalhamento dos Achados

### Achado #1: Routers acessando banco diretamente e vazamento de regra de negócio
- **ID**: ARQ-001
- **Severidade**: P1 Alto
- **Arquivo**: `services/api/financeiro/routers/receitas.py` e `despesas.py` (linhas 136-138)
- **Descrição**: O endpoint `baixar_receita` altera diretamente os atributos do modelo `receita` (ex: `receita.status = "RECEBIDO"`) e realiza `db.commit()` e `db.refresh()`. O mesmo ocorre para despesas e exclusões.
- **Impacto**: Quebra da separação de camadas (Service Layer bypass). Regra de negócio financeira vaza para o controller, dificultando testes unitários e reuso de lógica.
- **Recomendação**: Mover a lógica de "baixar receita" e "baixar despesa" (incluindo o save/commit) para o `ReceitaService` e `DespesaService` e delegar no router.
- **Risco de corrigir**: Baixo. Alteração encapsulada apenas nos routers e services de Receitas/Despesas.
- **Prioridade sugerida**: Alta (AUDIT-FIX-01).

### Achado #2: Violação de Domínio - Estoque manipulando Financeiro diretamente
- **ID**: ARQ-002
- **Severidade**: P1 Alto
- **Arquivo**: `services/api/operacional/services/estoque_service.py` (linha ~688)
- **Descrição**: O método `_criar_lancamento_insumo` importa o modelo `LancamentoFinanceiro` (`from financeiro.models.lancamento import LancamentoFinanceiro`) e instancializa/persiste diretamente um lançamento (`self.session.add(lancamento)`).
- **Impacto**: Acoplamento forte entre domínios. Alterações na estrutura do módulo Financeiro irão quebrar o módulo Estoque/Operacional.
- **Recomendação**: O Estoque deve interagir com Financeiro via interface de serviço (`FinanceiroService`) ou, idealmente, disparando um evento de domínio (`InsumoConsumidoEvent`).
- **Risco de corrigir**: Médio. Requer validação cuidadosa de dependências cíclicas entre services.
- **Prioridade sugerida**: Alta (AUDIT-FIX-02).

### Achado #3: Soft Delete realizado manualmente no Controller
- **ID**: ARQ-003
- **Severidade**: P2 Médio
- **Arquivo**: `services/api/financeiro/routers/receitas.py` e `despesas.py` (endpoint DELETE, linha ~110)
- **Descrição**: A lógica de soft-delete (`receita.ativo = False` -> `db.add` -> `db.commit`) é feita manualmente no nível do Router, sem passar por uma regra validada no `ReceitaService` ou `DespesaService`.
- **Impacto**: Duplicação potencial se outro fluxo precisar excluir. Contorna possíveis verificações de negócio (ex: "não excluir se já recebida").
- **Recomendação**: Transferir o soft-delete para um método `excluir` ou `desativar` no respectivo service.
- **Risco de corrigir**: Baixo.
- **Prioridade sugerida**: Média (Pode ser parte da AUDIT-FIX-01).

### Achado #4: Duplicação implícita de conceitos entre Operacional e Financeiro
- **ID**: ARQ-004
- **Severidade**: P2 Médio
- **Arquivo**: `services/api/operacional/services/abastecimento_service.py` e `frota_service.py`
- **Descrição**: Estes services importam `Despesa` e `PlanoConta` diretamente de `financeiro.models`, sugerindo criação direta de obrigações financeiras a partir do módulo operacional.
- **Impacto**: Como no ARQ-002, eleva o acoplamento sistêmico.
- **Recomendação**: Usar uma fachada (`FinanceiroFacade`) ou os services financeiros (`DespesaService`) para criar as despesas de abastecimento e frota.
- **Risco de corrigir**: Médio. Envolve refatoração de fluxos críticos (frota/abastecimento).
- **Prioridade sugerida**: Média (AUDIT-FIX-03).

## 7. Sinais de dívida técnica
- **Vazamento de Commits:** Alta prevalência de `await session.commit()` na camada de routers, o que impossibilita compor transações atômicas entre múltiplos services de forma limpa.
- **Acoplamento Interserviços Pobre:** A comunicação entre `operacional` e `financeiro` se dá instanciando entidades um do outro, ignorando o princípio de Service Boundary.

## 8. Riscos para multi-tenant
Nesta avaliação, os riscos multi-tenant aparentam estar mitigados na raiz, dado o uso constante do parâmetro `tenant_id` e utilitários como `validate_deposito_context(tenant_id=self.tenant_id)`. Não foram encontrados `selects` não qualificados com tenant na amostra de core logic.

## 9. Riscos para evolução modular
O acoplamento direto via `imports` de modelos entre pastas de domínio (`operacional` -> `financeiro`) impossibilita que esses módulos virem microserviços futuramente, ou até pacotes isolados, sem quebrar o sistema. Monetizar o módulo "Operacional" sem vender o "Financeiro" (ou vice-versa) será desafiador devido a estas interdependências de ORM.

## 10. Riscos para auditoria/compliance
Mudar `status = RECEBIDO` direto no router inviabiliza rastrear corretamente a auditoria do *quem* e *quando* alterou o registro (caso exista um listener de ORM ou um event logger injetado nos services).

## 11. O que NÃO deve ser alterado agora
- **`estoque_service.py` -> `registrar_ledger_estoque`**: O fluxo de Implantação e Ledger de Estoque está bem desenhado e centralizado (Uso de Ledger). Não refatorar.
- **Design de Contextos (Unidade Produtiva vs Tenant)**: A validação existente funciona e protege vazamentos de dados.

## 12. Plano de correção incremental sugerido

1. **AUDIT-FIX-01: Remoção de DB e Regra de Negócio dos Routers (Financeiro)**
   - Mover os handlers de `baixar_receita`, `baixar_despesa` e `excluir_*` para `ReceitaService` e `DespesaService`.
   - Limpar chamadas explícitas de `commit` e `db.add` dos routers.
   - Esforço: Baixo. Impacto: Alto.

2. **AUDIT-FIX-02: Desacoplamento Financeiro/Estoque**
   - Refatorar `_criar_lancamento_insumo` no `EstoqueService` para utilizar uma Interface de `Financeiro` (ex: invocando `LancamentoFinanceiroService.criar_lancamento()`), removendo o `import` de model inter-domínio.
   - Esforço: Médio. Impacto: Alto.

3. **AUDIT-FIX-03: Desacoplamento Frota/Abastecimento**
   - Assim como no Estoque, o apontamento de abastecimento que gera Despesa deve chamar um Service do financeiro e não o ORM `Despesa` e `PlanoConta`.
   - Esforço: Médio. Impacto: Médio.

## 13. Próxima auditoria recomendada
**AUDIT-02 — Performance e Identificação de Consultas N+1**, a ser realizada após a conclusão das melhorias estruturais da AUDIT-01. A auditoria focará em rastrear carregamentos Lazy de SQLAlchemy que podem degradar a performance de relatórios nas APIs e Front-End.
