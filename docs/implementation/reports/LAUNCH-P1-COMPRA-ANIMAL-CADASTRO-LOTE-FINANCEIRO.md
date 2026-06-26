# LAUNCH-P1 — Compra de Animal → Cadastro → Lote → Financeiro

## 1. Auditoria realizada

Foi validado no código-fonte que o domínio de Pecuária já possuía a entidade `Animal` como núcleo operacional, com suporte a `valor_aquisicao`, `lote_id`, eventos de domínio em `EventoAnimal` e integração financeira via `DespesaService`.

O fluxo, porém, não fechava de forma nativa e rastreável para:

- materialização automática de evento de compra;
- geração automática de despesa financeira de aquisição;
- persistência dos metadados comerciais da compra;
- atualização do resumo econômico do lote com custo inicial.

## 2. Integrações reaproveitadas

- `services/api/pecuaria/animal/models.py`: `Animal`, `EventoAnimal`, `LoteAnimal`.
- `services/api/financeiro/models/despesa.py`: `Despesa` com `origem_id`, `origem_tipo`, fornecedor e NF.
- `services/api/financeiro/services/despesa_service.py`: criação financeira com rateio existente.
- `services/api/agricola/alertas/service.py`: infraestrutura de alertas para despesa automática e rastreabilidade.
- `apps/web/src/app/(dashboard)/dashboard/pecuaria/animais/page.tsx`: formulário de cadastro/edição de animal.
- `apps/web/src/components/pecuaria/lote-indicadores-drawer.tsx`: visualização econômica do lote.

## 3. Lacunas encontradas

- O cadastro de animal não expunha campos de compra no frontend.
- O backend de `AnimalService` não materializava evento de compra nem despesa financeira na criação/edição.
- O lote não mostrava custo inicial agregado de aquisição.
- A resposta de indicadores do lote não carregava custo de aquisição total.

## 4. Implementações realizadas

- `services/api/pecuaria/schemas/animal_schema.py`
  - inclusão de metadados de compra em `AnimalCreate` e `AnimalUpdate`;
  - inclusão de `dados_extras` no contrato do animal.
- `services/api/pecuaria/services/animal_service.py`
  - criação de helpers para extrair e mesclar metadados de compra;
  - criação automática de `EventoAnimal` do tipo `COMPRA`;
  - criação automática de `Despesa` com `origem_tipo="COMPRA"`;
  - atualização idempotente do vínculo entre animal, evento e despesa;
  - materialização do lote após mudanças no rebanho;
  - preservação da rastreabilidade em `dados_extras.compra`.
- `services/api/pecuaria/schemas/lote_indicadores_schema.py`
  - adição de `custo_aquisicao_total`.
- `services/api/pecuaria/services/lote_indicadores_service.py`
  - cálculo do custo inicial por lote a partir de `Animal.valor_aquisicao`.
- `apps/web/src/app/(dashboard)/dashboard/pecuaria/animais/page.tsx`
  - inclusão dos campos de compra no formulário;
  - preenchimento automático a partir de `dados_extras.compra`;
  - envio dos metadados de compra para a API.
- `apps/web/src/components/pecuaria/lote-indicadores-drawer.tsx`
  - exibição do custo inicial do lote na interface.

## 5. Arquivos criados

- `services/api/tests/unit/pecuaria/test_compra_animal_service.py`
- `services/api/tests/integration/pecuaria/test_compra_animal.py`
- `docs/implementation/reports/LAUNCH-P1-COMPRA-ANIMAL-CADASTRO-LOTE-FINANCEIRO.md`

## 6. Arquivos alterados

- `services/api/pecuaria/schemas/animal_schema.py`
- `services/api/pecuaria/services/animal_service.py`
- `services/api/pecuaria/schemas/lote_indicadores_schema.py`
- `services/api/pecuaria/services/lote_indicadores_service.py`
- `apps/web/src/app/(dashboard)/dashboard/pecuaria/animais/page.tsx`
- `apps/web/src/components/pecuaria/lote-indicadores-drawer.tsx`

## 7. Testes

Executados com sucesso:

- `services/api/.venv/bin/pytest services/api/tests/unit/pecuaria/test_compra_animal_service.py services/api/tests/integration/pecuaria/test_compra_animal.py -q`
- `services/api/.venv/bin/ruff check services/api/pecuaria/schemas/animal_schema.py services/api/pecuaria/schemas/lote_indicadores_schema.py services/api/pecuaria/services/animal_service.py services/api/pecuaria/services/lote_indicadores_service.py services/api/tests/unit/pecuaria/test_compra_animal_service.py services/api/tests/integration/pecuaria/test_compra_animal.py`
- `git diff --check`

Resultado:

- 3 testes passando;
- sem falhas de lint;
- sem whitespace errors no diff.

## 8. Validações

Confirmado no código:

- o fluxo de compra gera evento de domínio e despesa financeira;
- a despesa fica rastreada por `origem_tipo` e `origem_id`;
- o lote recebe atualização automática de quantidade e peso médio;
- o frontend passa a capturar e reenviar metadados da compra;
- o resumo do lote passa a expor custo inicial;
- a integração manteve reaproveitamento dos serviços existentes.

## 9. Limitações remanescentes

- Não foi introduzido novo módulo, router ou model.
- Não há limitação funcional comprovada no escopo auditado após esta execução.
- A suíte executada aqui foi focada no fluxo alterado e não em E2E de navegador.
