# Relatório de Governança: Responsabilidades Onboarding, Billing e Wizard (ONBOARDING-WIZARD-GOV-01)

**Data:** 2026-07-08
**Autor:** Antigravity (AI Agent)
**Status:** Concluído (Auditoria e Diagnóstico)

## 1. Resumo Executivo
Foi identificada uma grande sobreposição e confusão de papéis no fluxo inicial do AgroSaaS. O Onboarding atual está antecipando decisões operacionais e de negócio que pertencem ao Wizard de Implantação e ao Domínio de Integrações. Além disso, a coleta de dados de módulos no onboarding entra em conflito direto com as regras de Billing (Planos), e a escolha de culturas ignora as bases canônicas robustas já existentes no sistema.

## 2. Diagnóstico do Onboarding Atual
**Evidências:**
- **Frontend (`apps/web/src/app/onboarding/configurar/page.tsx`)**: O fluxo faz 3 perguntas restritivas:
  1. *Cultura* ("O que você produz?" com opções hardcoded: CAFE, SOJA, MILHO, PECUARIA, CANA, OUTRO).
  2. *Gestão* ("Como você trabalha hoje?" listando SANKHYA, TOTVS, SAP, etc).
  3. *Módulos* ("O que você deseja controlar?" listando CUSTOS, ESTOQUE, FINANCEIRO, etc).
- **Backend (`services/api/core/routers/configuration.py`)**: A rota `/onboarding/configurar` persiste as seleções de Cultura, ERP e Módulos como strings genéricas (`cultura_principal`, `erp_principal`, `modulos_selecionados`) na tabela genérica de `configuracoes`. Pior ainda, ao detectar `erp == "SANKHYA"`, o backend imediatamente dispara o evento de sincronização `IntegrationSyncRequested` (Fase 05B) antes mesmo de qualquer configuração de credenciais ser estabelecida.

## 3. Diagnóstico do Wizard Atual
**Evidências:**
- O Wizard (`ImplantacaoOperacional`) já possui infraestrutura (etapas de `AGRICULTURA`, `PECUARIA`, `FINANCEIRO`, `ESTOQUE`, etc., conforme visualizado em `wizard-client.tsx`) para fazer o real mapeamento da fazenda.
- O campo `escopo_modulos` no modelo do Wizard duplica a intenção do usuário colhida no Onboarding (`modulos_selecionados`).

## 4. Diagnóstico do Billing / Planos / Features
**Evidências:**
- **Backend (`services/api/core/models/billing.py`)**: A entidade `PlanoAssinatura` define explicitamente os `modulos_inclusos` (JSON de pacotes como "CORE", "A1", etc), bem como `limite_hectares`, `max_fazendas` e o `plan_tier`.
- **Conflito:** Perguntar no Onboarding "Quais módulos você quer controlar" não faz sentido quando o usuário já selecionou um Plano no step 2 (`register-form.tsx`) que dita matematicamente a quais módulos ele tem direito comercialmente.

## 5. Diagnóstico de Commodities / Culturas
**Evidências:**
- As tabelas canônicas existem e são robustas: `Commodity`, `ProdutoCultura`, `ProdutoAgricola` (`cadastros/commodities` e `cadastros/produtos`), bem como `Cultura`, `Safra` e `Cultivo` no domínio `agricola`.
- O Onboarding ignora isso, definindo a fazenda inteira com uma string genérica de cultura única ("CAFE"), ignorando o fato de que a fazenda pode ser mista (ex: Café e Milho consorciados).

## 6. Diagnóstico de Pecuária
**Evidências:**
- O domínio existe com os modelos: `CategoriaAnimal`, `LoteAnimal`, `Animal`, `Piquete`, `Pastagem` (`pecuaria/animal/models.py`).
- O Onboarding resume tudo a um botão genérico "Pecuária", perdendo toda a granularidade (Corte, Leite, Recria, Confinamento) necessária para a correta implantação operacional.

## 7. Diagnóstico de ERP / Sankhya
**Evidências:**
- Sankhya possui um domínio denso de configurações (`SankhyaConfigCreate`, rotas, adapters).
- O gatilho de sincronização inicial (`sankhya_initial_sync`) em `configuration.py` é um risco arquitetural grave, pois é acionado no Onboarding antes da inserção da URL, Auth ou Mapeamento do Tenant.

---

## 8. Mapa de Responsabilidades Correto

### 8.1. PERTENCE AO ONBOARDING
- **Cadastro Mínimo Legal e Acesso:** Nome, E-mail, Senha, Telefone.
- **Cadastro do Produtor/Tenant:** Nome da Fazenda (ou Razão Social), CPF/CNPJ.
- **Conclusão:** O Onboarding termina na conversão do Lead em Assinante.

### 8.2. PERTENCE AO BILLING
- **Definição de Limites Módulos:** Baseado no plano selecionado (Tier).
- Módulos ativos comercialmente (o sistema libera apenas o que está no pacote).
- Número máximo de usuários e fazendas (Unidades Produtivas).

### 8.3. PERTENCE AO WIZARD (Implantação)
- **Quais módulos contrados serão implantados AGORA:** (O usuário pode ter direito a 10, mas quer iniciar só pelo Financeiro).
- **Ativação das Culturas:** Relacionamento da operação com as tabelas canônicas de `Commodity`/`Cultura`.
- **Ativação da Pecuária:** Definição da modalidade pecuária daquela unidade (Corte, Leite, etc).
- **Configuração Inicial de Ambiente:** Qual Unidade Produtiva (se houver mais de uma).

### 8.4. PERTENCE AO DOMÍNIO DE INTEGRAÇÕES (ERP)
- Escolha e Autenticação do ERP.
- A decisão de usar Sankhya deve ocorrer na Central de Integrações ou em um step dedicado do Wizard de Implantação de Backoffice, mediante payload de credenciais válidas.

---

## 9. Sumário de Correções Recomendadas

**A. Dados que devem SAIR do Onboarding:**
- Formulário "O que você produz?".
- Formulário "Como você trabalha hoje?" (Escolha de ERP).
- Formulário "O que você deseja controlar?" (Módulos).
- Desativar e remover o endpoint `/onboarding/configurar` (frontend e backend). O usuário, ao pagar/assinar, deve ir direto para o Wizard (Dashboard).

**B. Dados que devem IR para o Wizard:**
- Step de "Atividades Produtivas", onde o cliente seleciona a Cultura buscando de `ProdutoCultura`/`Commodity` e a Pecuária com os tipos corretos.
- Step de "Escopo de Implantação", onde o usuário escolhe quais módulos ativar agora (filtrados pelos `modulos_inclusos` do seu Plano no Billing).

**C. Riscos Arquiteturais Identificados:**
- Eventos de sincronismo complexos (`IntegrationSyncRequested`) engatilhados sem validação de credenciais de ERP na rota de configuração inicial do onboarding.

## 10. Próxima Execução Sugerida
**Remover Tela Intermediária de Configuração do Onboarding (`apps/web/src/app/onboarding/configurar/page.tsx`).**
Isso garantirá que, após o cadastro no `register-form.tsx`, o usuário pouse diretamente na tela do Wizard, e todo o backoffice comercial (Billing) assuma a verdade sobre os módulos liberados, estancando a duplicação no gatilho do ERP e os modelos de cultura.
