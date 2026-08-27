# 02 — Dependências e Empacotamento

## Core obrigatório

O módulo não é autônomo no sentido técnico. Requer:

- identidade, RBAC, tenant e RLS;
- propriedades, unidades produtivas e áreas rurais;
- cadastros globais e unidades de medida;
- auditoria e documentos;
- notificações;
- planos, assinatura, limites e feature flags.

## Dependências por capacidade

| Capacidade | Dependência | Obrigatória em |
|---|---|---|
| Identificar commodity e padrão | Cadastros/Commodities | MVP |
| Relacionar origem produtiva | Safra, Cultivo e Área Rural | MVP quando origem agrícola for exigida |
| Medir na colheita | Romaneio e ProdutoColhido | MVP agrícola |
| Avaliar pós-colheita | Beneficiamento | Profissional |
| Controlar saldo e bloqueio | Estoque | Profissional |
| Aplicar preço, desconto ou prêmio | Comercialização/Financeiro | Profissional |
| Emitir passaporte | Rastreabilidade | Enterprise |
| Coletar sem conexão | Campo PWA | Profissional |
| Receber medições | Integrações/IoT | Profissional/Enterprise |

## Pacotes comerciais

### Essencial

Protocolos, medições manuais, classificação, laudo e histórico.

### Profissional

Tudo do Essencial, mais amostras múltiplas, workflow técnico, importação, equipamentos, descontos, estoque e PWA.

### Enterprise

Tudo do Profissional, mais cadeia de custódia, passaporte QR, APIs de parceiros, padrões por comprador, auditoria avançada e IA assistida.

## Limites configuráveis

- commodities e protocolos ativos;
- análises e lotes por mês;
- usuários classificadores;
- propriedades e hectares;
- integrações de equipamentos;
- armazenamento de documentos;
- chamadas de IA;
- consultas públicas de passaporte.

## Regra de entitlement

Toda API, tela, job e integração deve verificar a feature flag do módulo e o limite do plano. O bloqueio comercial não pode gerar bypass de segurança nem deixar registros parcialmente gravados.
