# ERP-DATA-HYGIENE-01D — Desacoplamento do Runtime Sankhya do ORM Legado

## 1. Resumo Executivo
Esta fase do programa cumpriu o objetivo arquitetural de isolar os componentes operacionais do provider Sankhya da estrutura de persistência ORM `SankhyaConfig`. O desacoplamento permitiu libertar o `SankhyaGatewayAuthService`, o `SankhyaWSClient`, os serviços financeiros e fiscais, e as suítes de testes associadas, substituindo a injeção do modelo de banco de dados por uma nova `dataclass` puramente em memória (`SankhyaConnectionData`). Nenhuma nova tabela ou migração foi adicionada, e a fonte da verdade operacional segue sendo, temporariamente, a camada legada, até a ativação dos provedores canônicos na fase 01E.

## 2. Dependências Encontradas
Durante a varredura, `SankhyaConfig` era injetado diretamente em:
- `SankhyaGatewayAuthService` (no seu construtor `__init__`)
- `SankhyaWSClient` (no seu construtor `__init__`)
- `SankhyaConfigSerializer` (usado na geração das respostas para o frontend)
- Construtores de instâncias `SankhyaWSClient` em `nfe_financeiro_service.py`
- Toda a suíte de testes unitários do `auth_service` (`test_sankhya_gateway_auth_service.py`), instanciando mocks do SQLAlchemy Model.

## 3. Arquivos Alterados
- `services/api/integracoes/sankhya/services/auth_service.py`
- `services/api/integracoes/sankhya/services/sync_service.py`
- `services/api/integracoes/sankhya/services/nfe_financeiro_service.py`
- `services/api/tests/unit/integracoes/test_sankhya_gateway_auth_service.py`
- `services/api/tests/unit/integracoes/test_sankhya_architecture.py` (Novo arquivo de teste/guardrail)

## 4. Desenho Anterior
```text
SankhyaConfig ORM
        ↓
SankhyaGatewayAuthService (recebia o ORM)
SankhyaWSClient (recebia o ORM)
SankhyaNFeFinanceiroService (injetava o ORM no WSClient)
```

## 5. Desenho Implementado
```text
SankhyaConfig ORM (leitura atual no BD)
        ↓
build_sankhya_connection_data (fronteira de conversão dentro do sync_service.py)
        ↓
SankhyaConnectionData (dataclass simples e imutável)
        ↓
SankhyaGatewayAuthService
SankhyaWSClient
```

## 6. Ponto de Fronteira com o ORM
A leitura do modelo legado ficou estritamente concentrada na montagem dos payloads do `sync_service.py`. A função converte os campos do `SankhyaConfig` para a estrutura desacoplada.

## 7. Consumidores Desacoplados
- `SankhyaGatewayAuthService`
- `SankhyaWSClient`
- `SankhyaNFeService`
- `SankhyaFinanceiroService`
- Os testes unitários associados.

## 8. Consumidores Ainda Temporariamente Acoplados
- `SankhyaSyncService`: o serviço responsável por ler do banco, validar o status atual, lidar com regras the legacy gateway, e construir a fronteira. Seu acoplamento temporário é inevitável para orquestrar a carga de `SankhyaConfig`.

## 9. Estruturas Internas Utilizadas
- `@dataclass(frozen=True) class SankhyaConnectionData:` que atua como barreira impenetrável sem qualquer relação com a sessão SQLAlchemy ou estado persistente.

## 10. Justificativa para Cada Estrutura Criada
- `SankhyaConnectionData`: a dataclass foi criada por prover garantias explícitas de imutabilidade (frozen), e permite transitar credenciais decriptadas ou encriptadas pela aplicação, reduzindo o trânsito do SQLAlchemy state. Os nomes dos campos foram mantidos de maneira idêntica às propriedades de interesse do config para não quebrar acesso via namespace.

## 11. Comportamento Preservado
- Fluxos OAuth
- Fluxos Legacy Login/WS Basic Auth
- URL handling (intercept base url/env/auth)
- Nenhuma alteração foi feita nas rotas do Router ERP, Console ERP, `TenantIntegracao` ou Sincronização. As chamadas aos testes passaram integralmente. 

## 12. Testes
- Adição da injeção nativa de `SankhyaConnectionData` nos testes do `auth_service`, verificando a resiliência das validações de secrets, sem acoplamento.

## 13. Guardrail
- `test_sankhya_architecture.py` foi implantado com parsing AST (`ast.parse`) e análise de importações. Ele falhará compulsoriamente (CI Failure) se algum módulo desacoplado (como `auth_service.py` ou `nfe_financeiro_service.py`) reimportar `from integracoes.sankhya.models import SankhyaConfig`.

## 14. Riscos Remanescentes
- A leitura no banco por `SankhyaSyncService` ainda invoca `SankhyaConfig`. É o elo principal a ser migrado nas fases subsequentes (01E, 01F) para injetar as credenciais canônicas nesta fronteira recém-criada, em substituição. 

## 15. Preparação para a Próxima Fase
O runtime do Provider Sankhya está, agora, inteiramente pronto para transitar para as estruturas canônicas do Core ERP, pois seu núcleo (WS Client, Auth Service) depende apenas de `SankhyaConnectionData`. A próxima fase apenas substituirá a extração dos valores que preenchem essa estrutura.

## 16. Veredicto Final
**GO PARA ERP-DATA-HYGIENE-01E**
