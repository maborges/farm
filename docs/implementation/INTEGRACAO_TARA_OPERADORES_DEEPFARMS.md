# Integração TARA — Operadores e estações no DeepFarms

## Escopo

Este documento descreve somente a integração do DeepFarms com os contratos
públicos da TARA. Não há implementação da aplicação da estação, pacote offline,
IndexedDB, instalação, atualização ou rollback neste escopo.

O DeepFarms mantém seus próprios operadores e envia à TARA apenas uma projeção
necessária para a operação da Balança. A TARA continua independente e não deve
interpretar o domínio interno do DeepFarms.

## Rotas do DeepFarms

As rotas ficam sob `/api/v1/integracoes/tara` e exigem tenant/RBAC do
DeepFarms:

- `POST /config/testar-conexao`: valida a configuração salva usando uma consulta leve à TARA;
- `POST /operators`: envia a projeção de um operador;
- `GET /operators`: consulta operadores disponíveis na TARA;
- `POST /operators/{operator_id}/revoke`: solicita revogação;
- `POST /stations/activate`: solicita ativação de estação.

O botão **Testar conexão**, na tela de configuração, chama essa rota e retorna
`CONNECTED` quando URL, contexto e credenciais são aceitos. O segredo nunca é
retornado ou exibido; a consulta usa `limit=1` e não altera pesagens.

## Telas do painel

O painel Web expõe as telas:

- `/dashboard/operacional/balanca`: visão geral e configuração da conexão;
- `/dashboard/operacional/balanca/operadores`: projeção e revogação de operadores;
- `/dashboard/operacional/balanca/estacoes`: solicitação de ativação pela API;
- `/dashboard/operacional/balanca/pesagens`: consulta das pesagens retornadas pela TARA.

O módulo comercial é identificado por `O4_BALANCA`, aparece no catálogo de
módulos do backoffice e está incluído nos pacotes Profissional e Enterprise.

O DeepFarms não envia senha, PIN, hash de senha, segredo de recuperação ou
station token por essas rotas.

## Identidade

O identificador do operador é opaco e estável. A idempotência usa
`external_id`. A identidade local do operador permanece no DeepFarms e não é
substituída pelo identificador retornado pela TARA.

O cliente HTTP envia somente as credenciais públicas configuradas no tenant:

- `X-Balanca-Client-ID`;
- `X-Balanca-Client-Secret`.

O `X-Tenant-ID` não é enviado. A TARA resolve a Conta a partir da credencial,
e o DeepFarms não tenta trocar tenant após respostas `401` ou `403`.

A configuração também identifica explicitamente o Cliente cadastrado na TARA:

- `client_system`: sistema cliente estável, por exemplo `deepfarms`;
- `client_tenant_id`: identificador textual e opaco do cliente, por exemplo
  `fazenda-123`;
- `tara_client_id`: referência retornada pela TARA após o cadastro idempotente.

O botão **Testar conexão** valida essa associação por `POST
/config/testar-conexao`, que executa o cadastro idempotente em
`POST /v1/clients`. A API Key da Conta não é considerada automaticamente
autorizada para qualquer Cliente.

Conta TARA, tenant TARA e tenant DeepFarms são conceitos distintos e devem ser
associados na configuração da integração.

## Responsabilidades

O DeepFarms é responsável por:

- cadastro e status do operador local;
- escolha dos operadores autorizados;
- associação do operador ao contexto de negócio;
- envio idempotente da projeção;
- aplicação de revogação local;
- auditoria local da integração.

A TARA é responsável por:

- cadastro técnico do operador na Conta;
- estações e equipamentos;
- credenciais próprias da estação;
- operação de pesagem;
- eventos e status técnicos.

## Observação de contrato

Os endpoints de operadores utilizados pelo adapter são contratos públicos
esperados (`/v1/operators`, `/v1/operators/{id}/revoke`). Os nomes finais dos
campos de resposta, associação operador-estação e escopos devem ser confirmados
na documentação oficial da TARA antes da homologação.

Até essa confirmação, o DeepFarms não deve inferir regras internas da TARA nem
enviar credenciais de operador.
