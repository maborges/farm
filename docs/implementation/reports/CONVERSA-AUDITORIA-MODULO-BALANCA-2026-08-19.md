# Registro da conversa — Auditoria do módulo Balança

Data: 2026-08-19

## Escopo

Foi solicitada uma auditoria do módulo Balança sem alterações no código. A auditoria revisou:

- `apps/balanca` — PWA offline-first;
- `services/api/balanca` — API, modelos, serviços e sincronização;
- `tools/balanca-bridge` — comunicação com o indicador físico;
- migrações, documentação e testes relacionados.

## Principais achados da auditoria

1. O escopo por estação/fazenda não é aplicado integralmente. O `sync pull` retorna ordens pendentes de todo o tenant, e o `push` não valida se a ordem pertence ao escopo autorizado do dispositivo.
2. As tabelas da Balança possuem `tenant_id`, mas as migrações não habilitam RLS nem criam policies PostgreSQL.
3. O sync pode criar uma ordem sombra antes de validar a etapa; um item inválido pode deixar uma ordem órfã após commit.
4. O payload de sync aceita dicionário livre e a conversão de peso inválido resulta silenciosamente em `None`.
5. O login de operador não apresenta limitação de tentativas.
6. O token do dispositivo fica armazenado no IndexedDB do navegador.
7. A ponte aceita CORS amplo e token opcional, dependendo da confiança na rede local.
8. O mapa oficial de rotas ainda não documenta as rotas da Balança.

## Verificações executadas

- TypeScript do PWA: passou.
- ESLint do PWA: passou.
- Testes da ponte: 10 passaram e 1 falhou no teste TCP por erro ao acessar `server.sockets[0]`.
- Testes de integração backend: não puderam validar o fluxo funcional porque o ambiente bloqueou a conexão/socket PostgreSQL.

## Comunicação com a balança física

O PWA não lê a porta serial diretamente pelo navegador. A arquitetura atual é:

```text
Indicador físico
  -> RS232/USB ou TCP
balanca-bridge
  -> WebSocket local (/ws/peso)
PWA no navegador
  -> IndexedDB local
Backend, quando a internet voltar
```

O `balanca-bridge` usa o driver do sistema operacional e a biblioteca `pyserial` para abrir, por exemplo, `/dev/ttyUSB0` no Linux ou `COM3` no Windows. Ele precisa ser configurado com a porta, baudrate, paridade, stop bits e formato do protocolo do indicador.

No PWA, é necessário informar a URL da ponte, por exemplo `http://127.0.0.1:8321` quando ela roda na mesma máquina, ou `http://192.168.0.50:8321` quando roda em outro computador/Raspberry Pi da rede local. O token é opcional, mas recomendado.

A leitura ao vivo não depende da internet, desde que o navegador consiga acessar a rede local e o PWA já esteja carregado/instalado. A sincronização com o backend depende da internet. Se o PWA estiver em HTTPS e a ponte em HTTP, o navegador pode bloquear a conexão por mixed content.

## Conclusão

O desenho offline e a separação entre navegador, ponte e equipamento estão adequados conceitualmente. Antes de produção, as correções prioritárias são escopo por dispositivo/fazenda, RLS, validação transacional do sync e validação de pesos.
