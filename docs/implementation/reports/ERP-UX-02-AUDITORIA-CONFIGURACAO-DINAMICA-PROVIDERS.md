# Relatório de Auditoria: Configuração Dinâmica de Providers ERP (ERP-UX-02)

**Projeto**: ERP-UX-02
**Tema**: Auditoria da Configuração Dinâmica de Providers ERP
**Data da Auditoria**: 2026-07-10

---

## 1. Resumo Executivo
Esta auditoria avaliou a infraestrutura ERP-First atual do AgroSaaS para determinar se possui os componentes necessários para gerar e gerenciar formulários de configuração de qualquer ERP de forma dinâmica. A conclusão principal é que **a infraestrutura do banco de dados (modelos e relações) é robusta, dinâmica e perfeitamente reutilizável sem alterações estruturais**, porém as interfaces de frontend (`sankhya-console.tsx`) e os endpoints de teste e persistência de credenciais ainda estão fortemente acoplados à lógica do "Sankhya".

Não serão necessárias novas tabelas, modelos ou serviços, garantindo aderência absoluta à diretriz de não-duplicação. A transição demandará a implementação de um contrato JSON Schema padrão para renderização do frontend e abstração das chamadas de conexão.

## 2. Auditoria do Marketplace (`MarketplaceIntegracao`)
No modelo `MarketplaceIntegracao` (`services/api/integracoes/models.py`), as propriedades base do provider (`nome`, `slug`, `descricao`, `logo_url`, `versao`, `provider_type`, `ativa`) já estão definidas explicitamente em colunas tipadas. 
**Esquema de Credenciais**:
Existe o campo `credential_schema` (coluna JSON) junto com `connection_schema`. Atualmente, eles são injetados pelo `canonical_adapter.py` do Sankhya e possuem o seguinte formato básico:
```json
{
  "required": ["sankhya_client_id"],
  "optional": ["sankhya_client_secret", "sankhya_x_token", "password"]
}
```
*Gaps*: O formato atual especifica apenas os nomes das chaves, faltando propriedades de apresentação (tipos, placeholders, hints, campos sensíveis) para possibilitar a renderização visual dinâmica no frontend.

## 3. Auditoria das Credenciais (`IntegrationCredential`)
As credenciais já são independentes e genéricas. O modelo `IntegrationCredential` (`services/api/integracoes/models.py`) não possui colunas com nomes específicos para o Sankhya.
- A persistência é feita de forma agnóstica na coluna de texto `segredo_criptografado`, armazenando os valores JSON cifrados pelo backend.
- O campo `mask_metadata` (JSON) mantém as máscaras parciais para devolução visual (ex: `***-***-1234`) no frontend sem expor o segredo em plain text.
- O isolamento multi-tenant (`tenant_id`, `scope_type`) é cumprido por design.

## 4. Auditoria do Provider Contract e Adapters
Hoje o Provider Contract (`ProviderDefinition` / `Adapter`) é quem popula os metadados do `MarketplaceIntegracao` (via método `_ensure_provider` do `canonical_adapter.py`).
*Gaps*: Não há um mecanismo padronizado rico declarativo (como JSON Schema). O provider lista apenas as strings obrigatórias/opcionais, porém não expõe metadados de UI para cada campo, forçando o frontend a deduzir ou hardcodar a interface.

## 5. Auditoria do Teste de Conexão
Atualmente a ação "Testar Conexão" aciona a rota HTTP `/config/testar-conexao` no pacote `sankhya/routers/__init__.py`. 
- **Quem executa**: O `SankhyaSyncService` invocando o método `.test_connection()` do `SankhyaAuthService`.
- **Quem grava/atualiza**: Os status refletem em `IntegrationHealth` e `ErpReadinessService` após o teste. 
*Gaps*: O endpoint é acoplado ao path do Sankhya. Para ser dinâmico, o router HTTP deve ser genérico (ex: `/api/v1/integracoes/erp/testar-conexao`) resolvendo o adapter correto baseado no `slug` do provider ativo via *Provider Factory*.

## 6. Auditoria do Frontend (Console ERP)
O arquivo `apps/web/src/components/integracoes/sankhya-console.tsx` está fixo para campos do Sankhya (`sankhya_client_id`, `sankhya_api_base_url`, etc), renderizados por tags hardcoded de UI (`Input`, `Label`).
- A interface `SankhyaConfig` tem até colunas literais booleanas para indicar configurações salvas. 
*Vantagem*: Os componentes do *shadcn/ui* subjacentes são excelentes. Será simples iterar um `DynamicErpConsole` que leia um array de objetos de schema e imprima iterativamente `<Input type="password" />`, reusando a estética já homologada.

## 7. Mapeamento de Tipos de Campos
O `credential_schema` deve evoluir para especificar:
- **string**: Input text normal.
- **password/secret**: Input do tipo *password* (bolinhas) no preenchimento e estado mascarado na leitura (exibido como texto com botão alterar).
- **url**: Input text com validação HTTP/HTTPS.
- **integer**: Input number.
- **boolean**: Switch/Checkbox.

## 8. Auditoria de Extensibilidade e Duplicidades
Fica atestado que **nenhuma entidade nova** deve ser modelada. Reutiliza-se:
- `MarketplaceIntegracao` para o catálogo e portador dos JSON schemas.
- `IntegrationCredential` para criptografia genérica dos campos sensíveis.
- `TenantIntegracao` para associação lógica com o ambiente e campos descritivos abertos em `connection_payload` ou `configuracoes`.
- `IntegrationHealth` para o histórico e status do "Testar Conexão".

## 9. Fluxo Ideal Dinâmico
1. **Frontend**: Solicita metadados do ERP ativo (`MarketplaceIntegracao.credential_schema` enriquecido).
2. **Frontend**: Itera iterativamente sobre os metadados gerando a tela de configuração (Formulário Dinâmico).
3. **Usuário**: Preenche e salva.
4. **Backend genérico**: Recebe o payload, cifra os sensíveis, aloca em `IntegrationCredential`. Salva os abertos em `TenantIntegracao`.
5. **Teste de Conexão**: O frontend chama `/api/v1/erp/testar-conexao`. O backend resolve dinamicamente o Adapter do provider e dispara `.test_connection()`. Atualiza Readiness e Health.

## 10. Roadmap Incremental (ERP-UX-02)

Para implementar a arquitetura dinâmica e segura sem quebrar retrocompatibilidade:

* **ERP-UX-02A**: Enriquecimento do Contrato do Provider. Transformar o `credential_schema` e `connection_schema` atuais (arrays de string) em um JSON Schema válido ou metadata struct com tipos visuais (type, label, is_secret).
* **ERP-UX-02B**: Abstração dos Endpoints Genéricos. Criar endpoints `/erp/config` para receber submissões e persistir as credenciais em `IntegrationCredential` sem acoplamento ao router hardcoded do Sankhya.
* **ERP-UX-02C**: Renderização Dinâmica. Criar o componente frontend genérico `<DynamicErpConsole />` que interpreta o JSON Schema e gera a tela agnóstica substituindo a amarra nativa.
* **ERP-UX-02D**: Delegação do Teste de Conexão. Centralizar `/erp/testar-conexao` com Factory pattern delegando o ping ao respectivo Adapter do Provider.
* **ERP-UX-02E**: Encerramento de Fallbacks Legados.

---

**Veredicto Final**: GO. 
A arquitetura base (modelos e isolamento de segurança) está completamente apta para a virada de chave para providers dinâmicos. Nenhum risco estrutural encontrado, apenas ajustes de contratos JSON e desacoplamento de routers (HTTP) que já eram esperados na escalada do *multi-provider*.
