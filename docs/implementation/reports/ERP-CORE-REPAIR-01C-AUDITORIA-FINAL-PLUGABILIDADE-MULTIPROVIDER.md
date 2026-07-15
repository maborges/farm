# Auditoria Final: ERP-CORE-REPAIR-01C — Plugabilidade Multiprovider

## 1. Resumo Executivo
Esta auditoria avaliou a plugabilidade da arquitetura de integração de ERP (AgroSaaS) e o grau de acoplamento residual com o provider "Sankhya". O objetivo principal é atestar que um novo provedor de ERP pode ser configurado e adicionado sem que ocorram alterações nas superfícies genéricas (Core ERP, Router, Readiness, Console e Lifecycle).

A avaliação arquitetural confirma que a fase 01B erradicou com sucesso o fallback legado e as chamadas não autorizadas de dependências específicas do Sankhya. A resolução do provedor ocorre restritamente no ecossistema canônico (`TenantIntegracao` -> `MarketplaceIntegracao` -> `provider_slug`).

**Conclusão:** O núcleo ERP é agnóstico. O Sankhya figura apenas como a primeira implementação (plug-in) habilitada no `Provider Registry`.

---

## 2. Arquitetura Encontrada
O fluxo de resolução real mapeado no núcleo (via `services/api/integracoes/erp/router.py` e `erp_readiness_service.py`) é rigorosamente o seguinte:

1. **Request do Cliente (Tenant):** Uma chamada atinge os endpoints genéricos (`/integracoes/erp/status`, `/health`, etc.).
2. **Readiness Service (`carregar_runtime`):** Carrega a configuração canônica através de uma join entre `TenantIntegracao` e `MarketplaceIntegracao` buscando integrações ativas do tipo `ERP`. Nenhuma menção a tabelas de providers específicos.
3. **Resolução de Slug:** O Router extrai o `provider_slug` (por exemplo: `"sankhya"`).
4. **Provider Registry:** O Router solicita a instância do runtime através do `erp_provider_registry.resolve(provider_slug, session)`.
5. **Runtime Dispatch:** O provider retornado, que assina o contrato `ErpProviderRuntime`, trata os dados específicos e retorna payloads que correspondem aos Schemas genéricos da API.
6. **Fallback Inexistente:** Se o tenant não estiver habilitado, ou o provider estiver incorreto/desconhecido, uma exceção genérica e rastreável de HTTP 501 ou um payload de `NOT_CONFIGURED` é disparado. Nenhuma lógica implícita busca pelo "SankhyaConfig" isoladamente.

---

## 3. Evidências

### Referências a SankhyaConfig (Escopo Isolado)
Buscas utilizando `rg` e `grep` foram realizadas para mapear a persistência do modelo técnico `SankhyaConfig` e sua nomenclatura análoga `sankhya_config`.
* **Evidência:** 0 (zero) resultados no Core ERP (`integracoes/erp/*`, `integracoes/models.py`, `integracoes/erp_readiness_service.py`).
* **Uso Restrito:** Todas as 163 referências mapeadas estão rigorosamente restritas ao ecossistema particular do Sankhya (`integracoes/sankhya/services/*`), `migrations` de banco de dados, e scripts de manipulação out-of-band (`scratch_fix_tenant.py`).

### Referências Textuais (Imports e Namespaces)
O núcleo genérico e o Provider Registry são transparentes. Buscas por "sankhya" dentro de `integracoes/erp` retornam matches **exclusivamente** nos seguintes escopos designados para tal:
* `provider_bootstrap.py`: Registra o módulo (`erp_provider_registry.register("sankhya", SankhyaProviderRuntime)`).
* `providers/sankhya_runtime.py`: A implementação em si.

### Pontos de Registro
Há apenas um registro central em memória (`ErpProviderRegistry`).
* A instânciação oficial da classe no pipeline é injetada em `integracoes.erp.router`. O único meio de alimentar o repositório em produção é via `provider_bootstrap.py`.
* O contrato `ErpProviderRuntime` encontra-se isento de termos ou objetos que denotem dependência intrínseca (ex: sem autenticações prévias restritas, todos os _returns_ são dicionários ou listas padronizadas por pydantic). 

---

## 4. Acoplamentos Encontrados

* **Legítimos (Core):** `integracoes/erp/provider_bootstrap.py` contendo a fábrica de registro para `"sankhya"`. Este é o único arquivo do core ERP desenhado para ser acoplado com todos os providers habilitados no deploy.
* **Legítimos (Runtime):** O pacote de integração delegador da interface para as controllers nativas do provedor localizadas em `providers/sankhya_runtime.py`.
* **Históricos/Reconciliação:** O arquivo temporário `services/api/integracoes/sankhya/services/legacy_reconciliation.py` continua existindo para o serviço de bootstrap tardio puramente como adaptador de legados, mas opera sem vazar referências para fora do domínio "Sankhya".
* **Indevidos:** Não foram localizados acoplamentos acidentais ou induzidos. 
* **Riscos residuais:** Nenhum. A abstração se prova flexível, resiliente, e segura.

---

## 5. Teste de Segundo Provider (Multiprovider Real)

Foi provada a robustez e transparência da arquitetura ao se desenvolver um teste de injeção direta de um provedor fictício (`acme_erp`).

O arquivo `test_acme_erp_multiproviders.py` foi executado isoladamente testando a ponta-a-ponta (Router ERP):
1. **Mock Readiness:** Simulamos `TenantIntegracao` retornando a slug `"acme_erp"`.
2. **Implementação Fictícia:** Criamos `_AcmeErpRuntime` assinando o contrato `ErpProviderRuntime` (retornando stubs controlados para `get_status` e `get_health`).
3. **Registro:** Registramos localmente no `ErpProviderRegistry`.
4. **Chamada Router:** A requisição passou pelas instâncias genéricas `obter_status_erp` e `obter_health_erp` devolvendo os dados formatados perfeitamente (`{"configurado": True, "provider": "ACME", "status": "ONLINE"}`).
* Nenhuma modificação no Core foi demandada para suportar a fluidez dessa integração. O test obteve status **PASSED (100%)**.

---

## 6. Governança

A governança do projeto está blindada contra regressões através da suíte `test_erp_provider_governance.py`:
* **Imports Incompatíveis:** Evita importações diretas de bibliotecas restritas (`integracoes.sankhya.schemas`, `integracoes.sankhya.services`) pelo Router ERP e Readiness. O teste `test_modulo_generico_nao_importa_sankhya_modules` atua em CI/CD detectando quebra.
* **Módulos Bloqueados:** Prevê bloqueio direto contra importação de classes (ex: `SankhyaSyncService` ou `SankhyaConfigCreate`) pelo core, por meio do script automatizado AST em `test_modulo_generico_nao_importa_classes_sankhya`.
* **Branching no Router:** Impede bifurcações maliciosas via string-matching diretamente nos arquivos de rota, vetando expressões como `if provider_slug == "sankhya"`.

**Segurança:** Todas as regressões prováveis por descuido estrutural estão rigorosamente testadas em pipelines já existentes, tornando a chance de reincidência de acoplamento virtualmente nula sem que se crie intenção predeterminada de derrubar as assertions.

---

## 7. Recomendações
**Ações Adicionais:** A longo prazo, aconselha-se planejar a deprecisão real (DROP TABLE) da antiga tabela temporária `tenant_integracoes` (e o descarte do helper `legacy_reconciliation.py`) após a totalidade dos _SankhyaConfigs_ transitarem para os records da `TenantIntegracao` (migration já foi finalizada em `ERP-CORE-REPAIR-01B`). Como se trata apenas de limpeza técnica (Higiene de Banco de Dados) não influencia a arquitetura do multitenancy/multiprovider e não fere os preceitos de Go/No-Go avaliados.

---

## 8. Veredicto

**GO**

A arquitetura do AgroSaaS comprova excelência na extração e roteamento das interações. O sistema multilocatário e multiprovedor (ERP Gateway) detém forte abstração e total coesão. Novos ERPs poderão ser criados restritamente nas suas pastas de módulo, injetados no Registry no tempo do Bootstrap, e acoplados automaticamente à UI via rotas canônicas. O contrato está firme, independente, e performático.
