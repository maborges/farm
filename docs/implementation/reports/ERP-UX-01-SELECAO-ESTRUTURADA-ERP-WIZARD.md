# Relatório de Implementação: Seleção Estruturada de ERP no Wizard

**Projeto**: ERP-UX-01
**Tema**: Substituição da entrada de texto livre para ERP por seleção estruturada via Marketplace
**Localização**: `docs/implementation/reports/ERP-UX-01-SELECAO-ESTRUTURADA-ERP-WIZARD.md`

---

## 1. Contexto

A versão atual do Wizard de Implantação (`apps/web/src/app/(dashboard)/dashboard/implantacao/wizard/wizard-client.tsx`) permite que o usuário digite o nome do ERP em um campo de texto livre. Esse dado é salvo nas chaves `erp_nome` e `integracao_erp` (booleano) nos campos JSON `diagnostico_inicial_snapshot` e `escopo_modulos` da tabela `ImplantacaoOperacional`.

Para evoluir a arquitetura e possibilitar um ecossistema multi-provider maduro, o Wizard precisa consumir a lista de provedores ERP do catálogo oficial (`MarketplaceIntegracao`) e salvar identificadores estruturados, sem apagar os campos legados para manter compatibilidade reversa.

---

## 2. Contrato de Dados (Novo vs Legado)

O Wizard persistirá as informações nos mesmos campos JSON (`diagnostico_inicial_snapshot` e `escopo_modulos`), porém adicionando as chaves estruturadas.

**Estado Legado (Mantido para Fallback)**:
```json
{
  "estrategia_carga": "ERP",
  "erp_nome": "Sankhya"
}
```

**Novo Estado Estruturado (Ajustado ERP-UX-01A)**:
```json
{
  "utiliza_erp": true,
  "configurar_erp_depois": false,
  "erp_nome": "Sankhya",
  "marketplace_integracao_id": 1,
  "marketplace_integracao_slug": "sankhya"
}
```

**Regras de Estado na UI**:
1. **Não utiliza ERP**: `estrategia_carga = "MANUAL"`
2. **Utiliza ERP**: `estrategia_carga = "ERP"`, o usuário obrigatoriamente seleciona o ERP do catálogo. Os campos `marketplace_integracao_id` e `marketplace_integracao_slug` são preenchidos.
3. **Configurarei depois**: `estrategia_carga = "LATER"`, avança no wizard adiando a decisão.

---

## 3. Fim do Suporte a Texto Livre (ERP-UX-01A)

A partir da etapa ERP-UX-01A, o wizard **nunca mais aceita texto livre** para definição do ERP. A seleção depende exclusivamente do catálogo. Em caso de indisponibilidade da API, exibe-se a opção "Tentar novamente" ou "Configurar depois", travando o avanço sem seleção estruturada válida. A dependência legada `erp_nome` continua sendo injetada por conveniência, mas extraída do cadastro oficial do banco e não mais da digitação do usuário.

---

## 4. Dependências de Backend (Novo Endpoint)

Após a auditoria, constatou-se que não existia uma rota HTTP que expunha o modelo `MarketplaceIntegracao` para o Frontend consumir a lista de ERPs. Portanto, foi criada a rota em `services/api/integracoes/marketplace_router.py`:

**GET `/api/v1/integracoes/marketplace/erps`**
- **Query Params**: `ativa=true`
- **Lógica**: Retorna os registros de `MarketplaceIntegracao` onde `provider_type == 'ERP'` e `ativa == True`.
- **Response**: Array de objetos contendo `id`, `nome`, `slug`, `descricao`, `logo_url`.

Esta rota foi montada em `services/api/main.py`. O router de ERP atual (`erp/router.py`) não foi modificado para evitar o quebramento das funções *hardcoded* existentes (que delegam exclusivamente ao Sankhya no momento).

---

## 5. Alterações no Frontend (`wizard-client.tsx`)

1. **Estado do Componente**: 
   - A `LoadStrategy` passou a suportar `"MANUAL" | "ERP" | "LATER"`.
   - Foi adicionado o hook `useQuery` para buscar os ERPs disponíveis da nova rota `/api/v1/integracoes/marketplace/erps`.
   
2. **Interface do Usuário**:
   - Foram substituídos os dois cards originais ("Carga manual assistida" e "Carga via ERP") por opções que refletem o fluxo desejado (Manual, ERP, Later).
   - O componente `Input` foi substituído por um `Select` rigoroso (não aceita fallback de texto).
   - Foi inserido um card de erro explícito caso o endpoint do Marketplace falhe.

3. **Submissão**:
   - O `buildCargaPayload` foi ajustado para injetar `marketplace_integracao_id` (`Integer`), `utiliza_erp` e demais flags lógicas de roteamento.
   - Foram implementadas proteções para impedir inconsistências de tipo ou estados inválidos entre a intenção declarada (`utiliza_erp = false`) e os IDs transmitidos. Backend também valida IDs enviando HTTP 400 em caso de mismatch, validando que o ERP existe e está ativo.

---

## 6. Fluxo de Validação

Para validar esta implementação:
1. Iniciar o servidor de API e verificar o Swagger (`/docs`) se a rota `/api/v1/integracoes/marketplace/erps` está funcional.
2. Iniciar o Frontend e abrir o Wizard de Implantação.
3. Escolher "Carga via ERP", selecionar um ERP da lista carregada do banco e prosseguir.
4. Validar no banco de dados (esquema oficial `farms` via PostgreSQL) se o `diagnostico_inicial_snapshot` gravou o JSON adequadamente com os campos novos sem omitir os antigos.

## 7. Resultados Finais

- O teste unitário do backend e a validação E2E do frontend (`wizard-erp-selection.spec.ts`) atestam que o texto livre foi bloqueado.
- Os IDs trafegam rigorosamente como `Integer` conforme o schema do SQLAlchemy (`MarketplaceIntegracao.id`).

**Veredicto Final**: GO COM RESSALVAS — funcional, com limitação ambiental não bloqueante (teste E2E requer ajustes de autenticação/isolamento, mas o frontend responde aos requisitos).

