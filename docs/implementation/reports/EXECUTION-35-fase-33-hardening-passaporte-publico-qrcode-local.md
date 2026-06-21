# Relatório de Execução - Fase 33: Hardening do Passaporte Público e QR Code Local

**Tarefa**: EXECUTION-35
**Objetivo**: Remover dependência externa de geração de QR Code e endurecer a segurança e privacidade do passaporte público de rastreabilidade.

## Resumo da Implementação

### 1. Frontend - Geração Local de QR Code
- **Remoção de Requisições Externas**: A URL direta para a API externa `api.qrserver.com` que renderizava as imagens de QR Code foi eliminada, prevenindo o vazamento potencial da URL pública para infraestruturas de terceiros.
- **Implementação com `qrcode.react`**: Foi adicionada a dependência `qrcode.react` no `apps/web`. A geração passou a utilizar o componente genérico `<QRCodeSVG />` injetado puramente via DOM. 
- A URL do QR Code não é enviada na rede em nenhum momento do ciclo de renderização.

### 2. Backend - Hardening de Payload (`snapshot_json`)
- **Sanitização Dinâmica**: Foi implementado o método `sanitize_snapshot` no schema `PassaportePublicoResponse` no backend (`services/api/certificacoes_esg/schemas.py`).
- O schema agora itera ativamente sobre o conteúdo do `snapshot_json` antes da serialização para o front e expurga ativamente chaves que remetam a dados confidenciais de propriedade ou tenant.
- **Dados Bloqueados**: O algoritmo bloqueia explicitamente as chaves contendo substrings como `tenant_id`, `user_id`, `created_by`, `responsavel_pessoa_id`, `car`, `ccir`, `itr`, `nirf`, `sigef` e `matricula`.
- **Dados Públicos Expostos**: Ficam restritos apenas os IDs do passaporte (`public_token`), o título, o status, versão, data de publicação e dados genéricos seguros provenientes do lote/volume que o produtor optou por publicar publicamente.

### 3. Testes
- **Backend**: Foi adicionado o teste unitário `test_get_passaporte_publico_sanitized_snapshot` para a rota pública com mock garantindo o bloqueio do payload.
- **Frontend / E2E**: O `certificacoes-esg-relatorios-passaportes.spec.ts` foi atualizado para atestar que não há requisições para URLs externas e para garantir que o contêiner final contendo a tag `<svg>` é perfeitamente visível na interface do dashboard para cópia do link público.

## Status das Restrições
- ✅ **Não criar migration**: Não foi necessária criação de nova migration, já que tratou-se exclusivamente de bloqueio lógico de vazamento via schema de Response e client UI.
- ✅ **Não alterar Propriedade, Imóvel Rural ou PropriedadeImovel**: Estruturas mantidas inalteradas.
- ✅ **Não expor dados sensíveis**: `snapshot_json` está formalmente seguro com barreira impeditiva.
- ✅ **Não exigir login na página pública**: A página no Next.js continuou como SSR não autenticada.

## Conclusão
A remoção de dependências externas de terceiros para manipulação do link de passaportes fortalece o tenant isolation e garante total aderência a privacidade solicitada. O QR code é nativamente renderizado e a API sanitizada. O Passaporte Público atinge padrão de segurança robusto para produção.
