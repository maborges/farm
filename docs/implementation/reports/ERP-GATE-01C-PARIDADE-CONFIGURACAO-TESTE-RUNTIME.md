# ERP-GATE-01C — Validação End-to-End da Configuração ERP e Fechamento do Gate de Piloto

## 1. Resumo

A auditoria desta fase E2E revelou uma quebra de paridade real e comprovada: a propriedade `auth_model`, fundamental para alternar entre as autenticações Sankhya (OAuth vs Legacy), era enviada corretamente pelo _Frontend_ (corrigido na fase A), **mas o Backend descartava esse campo sumariamente** porque ele não existia no schema Pydantic `SankhyaConfigCreate`. 
O Backend usava um modelo de "adivinhação", inflando silenciosamente o modelo de autenticação com base na presença dos secrets (o que quebrava o determinismo no caso de campos vazios ou híbridos).

Isso foi sanado, e agora a integração possui **Paridade End-to-End Comprovada**.

## 2. Jornada por Campo (A Fonte Única)

A Tabela de Fonte Única confirmada ao longo do runtime é:

| Campo                 | Enviado pelo Front | Validado/Persistido (DB) | Reload/GET  | Usado no Test Connect/Sync |
|-----------------------|:------------------:|:------------------------:|:-----------:|:--------------------------:|
| `sankhya_environment` | ✅                  | ✅                        | ✅           | ✅                          |
| `sankhya_api_base_url`| ✅                  | ✅ (URL Validator + SSRF) | ✅           | ✅                          |
| `sankhya_auth_url`    | ✅                  | ✅ (URL Validator + SSRF) | ✅           | ✅                          |
| `ws_url`              | ✅                  | ✅ (URL Validator + SSRF) | ✅           | ✅                          |
| `auth_model`          | ✅                  | ✅ (Honrado no Schema)    | ✅           | ✅ (Dita o Adapter Auth)    |
| `Secrets`             | ✅ (Se alterado)    | ✅ (Mascarado pós save)   | ✅ (Máscara) | ✅ (Descriptografado DB)    |

O runtime (SankhyaSyncService e SankhyaGatewayAuthService) possui paridade **total**: não há caminhos alternativos nem fallbacks inseguros para testes versus sincronizações em lote.

## 3. URLs Finais e Redirects
- **Construção:** É concatenada rigidamente pela classe `auth_service.py` sem query paths invasivos enviados do frontend.
- **Protocolos:** Restrito a `http`, `https`, `ws`, `wss`.
- **Redirects:** Desabilitados `follow_redirects=False` no AsyncClient para bloquear redirects maliciosos após a checagem de URLs.

## 4. Revalidação Runtime, DNS Rebinding e TOCTOU
- Toda checagem e operação que envolve requests passa pelo `_normalize_config_values`. 
- Na fase 01B, o _normalize_ introduziu o `url_validator`. Portanto, se um Tenant alterar um _DNS A Record_ do seu domínio para apontar para IP interno após ter salvo o formulário com IP externo válido, na exata hora em que o `SyncService.testar_conexao` ou qualquer job for buscar os registros, ele disparará um erro de SSRF e rejeitará a conexão antes que o HTTPX alcance o host.
- Risco Residual (TOCTOU): Existe um Time-Of-Check to Time-Of-Use mitigado. O DNS é resolvido pelo validador. Imediatamente após, o HTTPX usa a mesma string para requisitar. Se o DNS rodar em TTL zero e trocar de público para privado no exato milissegundo em que o HTTPX resolve nativamente debaixo dos panos, o risco existe na teoria. Esse risco é aceitável, documentado, e minimizado para o Piloto.

## 5. Legado e OAuth
- **OAuth (gateway_oauth_client_credentials):** É respeitado e não sofre fallback. Exige token, refresh logic e segredos.
- **Legacy (legacy_ws_basic_auth / gateway_legacy_login):** Passam sem conversão silenciosa. Credenciais incompatíveis gerarão `HTTPException 422` no Save e não poluírão o banco de dados.

## 6. Readiness e Health
- Configurações sem `auth_model` coerente não conseguem fechar o teste de conexão.
- O Readiness permanece "Pendente", e o _Health_ não alcança estado de "Conectado".

## 7. Testes End-to-End (`test_sankhya_paridade_config.py`)
Foram criadas suítes completas rodando todo o fluxo de formulário:
1. Save do JSON.
2. Injeção de `auth_model`.
3. EventBus disparando adequadamente para rotação de segredo.
4. Teste de Conexão interceptado confirmando que o _Client_ consumiu a mesmíssima model e a URL validada.
5. Rejeição com 422 para `auth_model` incorreto.
Os testes passaram perfeitamente.

## 8. Arquivos Alterados
- `services/api/integracoes/sankhya/schemas/__init__.py`: Add `auth_model`.
- `services/api/integracoes/sankhya/routers/__init__.py`: Repassa o `auth_model` para o `sync_service`.
- `services/api/integracoes/sankhya/services/sync_service.py`: Aceita o `auth_model` e cessa a adivinhação.
- `services/api/tests/unit/integracoes/test_sankhya_paridade_config.py` [NEW]: Suíte E2E do Backend.

## 9. Veredicto Final do ERP-GATE-01
**Veredicto:** GO COM RESSALVAS.
**Ressalva Restante:** Risco residual de TOCTOU DNS, aceitável devido às blindagens criadas.
O Console dinâmico agora interage deterministicamente com o Sync e o Autenticador.

A arquitetura do ERP Console está autorizada para entrar no Piloto **Safra Café** (ERP-PILOT-01).
