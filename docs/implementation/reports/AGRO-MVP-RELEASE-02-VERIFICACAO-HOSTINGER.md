# AGRO-MVP-RELEASE-02 — Verificação operacional Hostinger

**Data:** 2026-10-30  
**Escopo:** verificações DNS e HTTP públicas, somente leitura. Nenhum container, banco, configuração, arquivo de produção ou dado foi alterado.

## Veredicto

**NO-GO para avançar ao smoke test final da Hostinger.** Não foi possível identificar nem acessar o endereço da VPS Hostinger: `api.deepfarms.com.br` resolveu para `56.126.104.183`, IP documentado no repositório como o host EC2/AWS, e `agro.deepfarms.com.br` não resolveu nesta verificação. Não há evidência para afirmar que o destino HTTP observado seja a VPS KVM 4.

Além disso, embora o health check público da API responda, as rotas de clima e mercado testadas retornaram HTTP 404. Assim, a conectividade HTTP até uma API está comprovada, mas o fluxo requerido pelo Agro e as rotas necessárias do runtime não estão funcionais no endereço testado.

## Estado e topologia observados

| Verificação | Resultado |
|---|---|
| DNS `api.deepfarms.com.br` | Resolveu para `56.126.104.183`. Esse endereço coincide com o EC2 descrito em `docs/implementation/reports/OPS-CHECKOUT-01-AUDITORIA-CHECKOUT-PRODUCAO.md`; não foi associado à Hostinger. |
| DNS `agro.deepfarms.com.br` | `getent ahostsv4` não retornou endereço. O site Agro não pôde ser alcançado pelo hostname esperado. |
| Containers Agro/API, portas e redes Docker | **NÃO VERIFICADO** — sem endereço/identificação da VPS Hostinger para inspeção SSH. |
| Nginx da Hostinger e proxy `/api/v1/` | **NÃO VERIFICADO** — não se inspecionou o host AWS como substituto da VPS solicitada. |
| Build Agro e origem incorporada | **NÃO VERIFICADO no runtime Hostinger.** No código, `apps/agro/next.config.ts` só produz rewrite em produção se `AGRO_API_INTERNAL_ORIGIN` estiver definida durante o build; `src/lib/api-url.ts` usa same-origin por padrão, ou `NEXT_PUBLIC_AGRO_API_ORIGIN` quando incorporada no build. Isso descreve o código, não a imagem implantada. |

## Requisições HTTP públicas

Requisições GET sem autenticação, em 30/10/2026. Nenhuma chamada alterou estado.

| Endpoint testado | HTTP | Resultado |
|---|---:|---|
| `https://api.deepfarms.com.br/health` | **200** | JSON de health informou `status=ok` e `database=connected`. O servidor respondeu com Nginx e headers de processamento da aplicação. |
| `https://api.deepfarms.com.br/api/v1/public/clima/previsao?lat=-23.5505&lon=-46.6333` | **404** | FastAPI respondeu `{"detail":"Not Found"}`; não chegou ao código de previsão/provedor. |
| `https://api.deepfarms.com.br/api/v1/public/mercado/ibge/catalogo` | **404** | FastAPI respondeu `Not Found`; o catálogo não foi alcançado. |
| `https://api.deepfarms.com.br/api/v1/public/mercado/precos` | **404** | FastAPI respondeu `Not Found`; preços não foram alcançados. |
| `https://api.deepfarms.com.br/openapi.json` | **Sem resposta** | GET expirou após 20 s; não foi possível comparar o inventário público de rotas. |

O endpoint de saúde confirma comunicação com um processo API no endereço `api.deepfarms.com.br`, mas não confirma o caminho Agro → API no domínio Agro. O `404` com headers de processamento da aplicação diferencia o resultado de falha de DNS/TLS; a aplicação alcançada não reconheceu as rotas testadas. No checkout atual, essas rotas são registradas sob `/api/v1` (`services/api/main.py`, routers `public_clima` e `public_mercado`). Como o runtime consultado não foi identificado como Hostinger, não é possível atribuir a causa à imagem ou configuração da VPS KVM 4.

## Provedor meteorológico

| Item | Estado |
|---|---|
| Previsão pública respondendo | **FAIL** no domínio API testado: HTTP 404 antes de invocar o serviço climático. |
| Provedor ativo no runtime Hostinger | **NÃO VERIFICADO**. |
| Credencial presente/válida | **NÃO VERIFICADO**; nenhum valor ou arquivo com segredo foi lido. |
| Autorização/licença pública | **NÃO VERIFICADO**. |
| Limites/quota configurados | **NÃO VERIFICADO**. |

OpenWeather não foi confirmado como habilitado. O health check não informa provedor ou configuração. Como a rota de previsão nem foi resolvida, não há resposta real do provedor que permita testar credencial, autorização, quota ou disponibilidade externa. Não foram cadastradas credenciais.

## Classificação dos requisitos

1. **Comunicação funcional Agro PWA → API: FAIL.** O hostname Agro não resolveu e não foi possível executar chamada a partir do browser servido nesse host. O domínio API respondeu health 200, mas as rotas públicas requeridas responderam 404. Isso não satisfaz o fluxo do PWA.
2. **Provedor meteorológico habilitado e operacional: FAIL para serviço utilizável; configuração do provedor NÃO VERIFICADA.** A previsão no endpoint público retornou 404. Não se conclui que a credencial/provedor seja inválido: a requisição não alcançou o serviço climático.

## Bloqueadores comprovados e correção mínima indicada

1. **Destino Hostinger não identificado pelo domínio público:** identificar o IPv4/hostname público da KVM 4 e confirmar DNS A/AAAA dos hostnames Agro/API. O hostname Agro atualmente não resolveu, enquanto o hostname API aponta para o endereço EC2 documentado. Se a intenção é já servir a partir da Hostinger, corrigir os registros para o destino correto após confirmar o IP da VPS; não foi feita nenhuma alteração DNS.
2. **Rotas MVP ausentes no runtime consultado:** após confirmar que o endpoint pertence à Hostinger, alinhar a versão/imagem da API com o código que registra `/api/v1/public/clima/*` e `/api/v1/public/mercado/*`, e garantir que o Nginx preserve ou encaminhe o prefixo `/api/v1/`. Não reconstruir/reiniciar nada nesta verificação; primeiro precisa ficar comprovado qual host recebeu as chamadas.
3. **Provedor meteorológico:** no host confirmado, inspecionar configuração sem expor segredo e habilitar uma integração já licenciada, com credencial válida e quota definida. OpenWeather pode ser reaproveitado somente se a licença/configuração existente autorizar o uso público. Nenhuma configuração foi alterada.

## Resultado

- **Estado de containers, portas, redes, Nginx e imagem Agro na Hostinger:** NÃO VERIFICADO por falta de destino Hostinger identificável.
- **API pública no endereço DNS atual:** health PASS (HTTP 200); endpoints do MVP FAIL (HTTP 404).
- **Provedor meteorológico na Hostinger:** NÃO VERIFICADO; endpoint público de previsão FAIL no host API observado.
- **Avançar ao smoke test final:** **NO-GO** até confirmar o destino correto da VPS, corrigir/resolver DNS e disponibilizar as rotas API necessárias. Depois disso, revalidar provedor, API e o fluxo no domínio Agro.

### Limitação operacional

O repositório contém uma chave SSH local, mas não contém um hostname/IP Hostinger associado a ela. Não foi tentado SSH no endereço público atualmente apontado pelo domínio API, pois a evidência local o identifica como EC2/AWS e o escopo desta solicitação é a KVM Hostinger.
