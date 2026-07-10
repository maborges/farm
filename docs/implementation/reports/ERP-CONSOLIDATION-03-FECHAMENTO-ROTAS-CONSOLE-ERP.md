# ERP-CONSOLIDATION-03 — FECHAMENTO E AUDITORIA DE ROTAS NO CONSOLE ERP DINÂMICO

## Resumo Executivo
Esta auditoria teve como foco validar se a recém-lançada interface `DynamicErpConsole` criou suposições indevidas sobre o roteamento de futuros ERPs. Foi identificada a parametrização generalista de rotas _provider-specific_, que foi corrigida de forma cirúrgica delegando essa responsabilidade para o componente _wrapper_ existente. O programa ERP-First está oficialmente pronto para encerramento e foco total no piloto controlado.

## Auditoria Localizada das Rotas

As chamadas feitas pelo frontend (antes desta correção) utilizavam a seguinte estrutura:

### ERP-Generic (Corretas e validadas)
Utilizam o path oficial de integração genérica, que se aplica igualmente a qualquer provider mapeado por `providerSlug`:
- `GET /api/v1/integracoes/erp/providers/${providerSlug}/schema` (obter o contrato)
- `GET /api/v1/integracoes/erp/status`
- `GET /api/v1/integracoes/erp/health`
- `GET /api/v1/integracoes/erp/diagnostico`
- `GET /api/v1/integracoes/erp/timeline`
- `GET /api/v1/integracoes/erp/jobs`
- `GET /api/v1/integracoes/erp/associacoes/pendentes`

### Provider-Specific (Incorretas e corrigidas)
O código assumia que rotas técnicas de provider operavam genericamente sob o namespace do `providerSlug`. Elas foram modificadas para receber seus endpoints via `props` (`endpoints` explícitos passados pelo wrapper):
- *Configuração Técnica:* `POST /api/v1/integracoes/${providerSlug}/config` → `POST /api/v1/integracoes/sankhya/config`
- *Teste de Conexão:* `POST /api/v1/integracoes/${providerSlug}/config/testar-conexao` → `POST /api/v1/integracoes/sankhya/config/testar-conexao`
- *Sync Técnico:* `POST /api/v1/integracoes/${providerSlug}/sync/${tipo}` → `POST /api/v1/integracoes/sankhya/sync/${tipo}`
- *Logs Técnicos:* `GET /api/v1/integracoes/${providerSlug}/logs` → `GET /api/v1/integracoes/sankhya/logs`

## Correção Aplicada: Compatibilidade Explícita (Opção B)
- **`DynamicErpConsole`:** Foi introduzido o objeto de configuração opcional `endpoints` nas propriedades (`DynamicErpConsoleProps`), removendo a suposição rígida sobre as URLs _provider-specific_ e deixando que a origem dite as rotas de submissão e ações técnicas.
- **`SankhyaConsole` (Wrapper):** Foi atualizado para fornecer não apenas o `providerSlug="sankhya"`, mas também a árvore `endpoints` roteando exatamente para o fluxo técnico já existente no backend (`/integracoes/sankhya/*`).

## Validações Funcionais e Testes
- Nenhuma alteração foi realizada em rotas ou serviços Python do Backend.
- O endpoint receptor oficial (`/sankhya/config`) continua realizando o `submit` original, mantendo a consistência da criação/atualização de `TenantIntegracao` e de `IntegrationCredential`.
- Os campos dinâmicos são montados respeitando metadados (como obrigatoriedade, dicas de preenchimento, placeholders) sem hardcodes atrelados ao Sankhya no lado do frontend.
- O Backoffice (`/dashboard/backoffice/integracoes/erp`) não foi alterado.
- Os testes unitários do ERP router (`pytest services/api/tests/unit/integracoes/test_erp_router.py`) executaram 100% (16 passed). O frontend foi chancelado sem erros pelo TypeScript (`tsc`).

## Veredicto e Encerramento
**VEREDICTO:** GO — Console ERP convergido e programa ERP-First encerrado.

O processo assegura a compatibilidade e a total abstração de persistência no Console Dinâmico, enquanto respeita as fronteiras técnicas atuais no Backend. O frontend está dinâmico e o backend mantém seu suporte dedicado ao único ERP real por ora. Não houve a criação de _Factories_ redundantes nem a poluição do catálogo global por falsos-providers.

**STATUS:** ERP-FIRST-CONVERGENCE CONCLUÍDO

*O programa encontra-se agora dedicado exclusivamente à consolidação do piloto inicial.*
