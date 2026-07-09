# Relatório de Governança: Wizard como Orquestrador de Implantação (WIZARD-GOV-02)

**Data:** 2026-07-08
**Autor:** Antigravity (AI Agent)
**Status:** Concluído (Auditoria e Refinamento de Verificadores)

## 1. Diagnóstico e Arquitetura Atual
Foi realizada uma auditoria na base de código do **Wizard de Implantação Operacional** para certificar que o fluxo obedece ao princípio de Orquestrador de Implantação e não funciona como um sistema paralelo de cadastros. 

O diagnóstico revelou que a arquitetura do motor (`ChecklistEngine` em `services/api/wizard/checklist_engine.py`) e do frontend (`wizard-client.tsx`) já atuam majoritariamente de forma orquestrada, delegando os cadastros e dados reais para os módulos canônicos.
O frontend do Wizard não possui formulários de cadastro de talhões, equipamentos, finanças ou estoque em si; ele apenas exibe as etapas e itens do checklist e provê *deeplinks* (`acao_link`) diretamente para as páginas canônicas. 

## 2. Diferença: Formulário vs. Orquestrador
- **Wizard Formulário (Anti-Pattern):** Teria inputs de "Nome da Cultura", "Tamanho do Talhão" ou "Senha do ERP" salvando em tabelas próprias (ex: `wizard_culturas`, `configuracoes`).
- **Wizard Orquestrador (Padrão AgroSaaS):** Lê o plano contratado (Billing), as etapas previstas, aponta os links para `/cadastros/propriedades` e **automaticamente** reavalia a implantação checando o banco oficial (`UnidadeProdutiva`, `ProdutoCultura`, `AreaRural`, `SankhyaConfig`) para validar se a tarefa está pendente, atendida, dispensada ou falha.

## 3. Módulos Canônicos Reutilizados e Verificados
A estrutura validou e mapeou o orquestrador aos seguintes módulos e entidades da plataforma:
1. **Unidade Produtiva:** Domínio `core/cadastros/propriedades` -> Modelo `UnidadeProdutiva`.
2. **Estrutura Territorial:** Domínio `core/cadastros/propriedades` -> Modelo `AreaRural`.
3. **Agricultura (Talhão):** Domínio `core/cadastros/propriedades` -> `TipoArea.TALHAO`.
4. **Pecuária (Piquete):** Domínio `pecuaria/models/piquete.py` -> `TipoArea.PIQUETE`.
5. **Estoque (Depósito):** Domínio `operacional/estoque` -> Modelo `Deposito`.
6. **Financeiro (Plano de Contas):** Domínio `financeiro` -> Modelo `PlanoConta`.
7. **Equipamentos e Catálogo:** Domínio `core/cadastros/produtos` e `equipamentos`.
8. **Culturas/Commodities:** Domínio `core/cadastros/produtos` e `agricola/cadastros` -> `Produto` (Categoria `ProdutoCultura`/`Commodity`).
9. **Integrações (ERP):** Domínio `integracoes/sankhya`.

## 4. Passos Oficiais do Wizard e Links Canônicos
Cada etapa possui ações direcionadas à verdade do sistema (`_CHECKLIST_ACTION_TARGETS` em `router.py`):
- `CHECK_UNIDADE_PRODUTIVA` → `/cadastros/propriedades`
- `CHECK_ESTRUTURA_TERRITORIAL` → `/cadastros/propriedades/talhoes`
- `CHECK_AGRICULTURA_TALHAO` → `/cadastros/propriedades/talhoes`
- `CHECK_PECUARIA_PIQUETE` → `/dashboard/pecuaria/piquetes`
- `CHECK_ESTOQUE_DEPOSITO` → `/suprimentos/estoque`
- `CHECK_FINANCEIRO_PLANO_CONTA` → `/dashboard/financeiro/planos-conta`
- `CHECK_PRODUTO_CATALOGO` → `/cadastros/produtos`
- `CHECK_EQUIPAMENTO_CADASTRO` → `/cadastros/equipamentos`
- `CHECK_CULTURA` → `/cadastros/culturas` (Adicionado nesta execução)
- `CHECK_INTEGRACAO_ERP` → `/configuracoes/integracoes` (Adicionado nesta execução)

## 5. Duplicações Encontradas
Não foram encontradas duplicações estruturais no motor do Wizard *em si*. O Wizard estava limpo, porém carecia de verificadores que fechassem a ponte para **Culturas** e **Integrações**. O gap era reflexo direto do problema resolvido no ONBOARDING-WIZARD-GOV-01, onde o Onboarding estava roubando esses passos do orquestrador.

## 6. Correções Implementadas (Nesta Execução)
1. **Adicionado Verificador `_check_cultura`**: No `ChecklistEngine`, foi introduzida a validação de que, se o módulo agrícola está habilitado para a implantação, deve existir ao menos um `Produto` da categoria de cultura ativo no banco do Tenant, bloqueando a inicialização agrícola "falsa" e usando o domínio correto.
2. **Adicionado Verificador `_check_integracao_erp`**: Preparado verificador de obrigatoriedade de integrações caso conste no escopo.
3. **Mapeamento de Ações e Guidance (`router.py`)**: Adicionados labels descritivos, rotas canônicas e botões de `acao_link` correspondentes a Culturas e Integrações, permitindo que a interface `wizard-client.tsx` renderize os botões corretamente para o usuário.

## 7. Próxima Execução Sugerida
**Limpeza de Migrations e Dependências.** Com o fluxo reordenado para que o Onboarding faça a venda, e o Wizard orquestre usando tabelas canônicas:
- Recomenda-se remover as chamadas indevidas em `/onboarding/configurar` e retirar as colunas residuais ou restrições conflitantes (`ck_wizard_implantacao_status_requires_unidade` tratada em `WIZARD-FIX-02`) por meio de uma nova Migration de alinhamento estrutural, consolidando o fluxo.
