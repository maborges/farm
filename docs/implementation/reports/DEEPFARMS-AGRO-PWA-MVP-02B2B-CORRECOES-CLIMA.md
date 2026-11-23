# DEEPFARMS Agro PWA MVP-02B2B — Correções controladas da integração climática

Data: 26/10/2026  
Escopo: alterações locais e testes sem serviços, credenciais ou chamadas a provedores.

## Resultado

As correções de segurança de ativação, cache, configuração sem banco e apresentação foram implementadas. WeatherAPI continua desativada por padrão e não foi ativada nesta fase.

**Veredicto: GO COM RESSALVAS para preparação técnica; NO-GO para ativação pública da WeatherAPI.** Ainda são necessários aceite dos termos vigentes, configuração autorizada de credencial somente no backend e smoke limitado em fase separada.

## Alterações

- `services/api/public_clima/adapters.py`: WeatherAPI só é autorizado quando `WEATHERAPI_ENABLED=true` e existe credencial. A presença de credencial isolada não habilita o provedor.
- `services/api/public_clima/dynamic_orchestrator.py`: adapter dinâmico aplica a mesma flag. `CLIMA_CONFIG_SOURCE=environment` agora seleciona configuração estática do processo e retorna antes de criar sessão SQLAlchemy; o padrão `database` preserva o modo dinâmico atual. Valor desconhecido é recusado.
- `services/api/core/config.py`: adicionada a configuração `clima_config_source`, default `database` (variável `CLIMA_CONFIG_SOURCE`). Neste checkout o arquivo de configurações já continha outras alterações anteriores; nenhuma delas foi reformatada ou removida.
- `services/api/public_clima/cache.py` e `service.py`: TTL fresh é limitado a 3.600 segundos. O Redis stale e o fallback em memória têm retenção máxima de uma hora, verificam a idade do envelope e descartam entradas expiradas; entradas Redis antigas são removidas quando consultadas. Respostas stale são revalidadas imediatamente antes de serem servidas.
- `services/api/public_clima/router.py`: cabeçalho HTTP não permite stale adicional e a descrição da rota informa previsão diária de até três dias.
- `services/api/public_clima/service.py`: a API pública limita a lista diária recebida a três itens, sem criar dias ausentes.
- `services/api/public_clima/contracts.py`, `apps/agro/src/app/page.tsx` e `apps/agro/src/components/clima/previsao-diaria.tsx`: documentação e interface do MVP anunciam até três dias.
- `apps/agro/src/lib/clima/previsao.ts`: cache offline usa o menor prazo entre a validade recebida e 60 minutos após o salvamento; item expirado é removido e não volta ao dashboard offline. Calculadoras e página offline estática não usam esse envelope e permanecem disponíveis.
- `apps/agro/src/components/clima/condicoes-atuais-card.tsx`: mostra a fonte do provedor retornado; WeatherAPI continua creditada por link nominal.
- `apps/agro/src/components/clima/aviso-agronomico-card.tsx`: explica caráter informativo/probabilístico, imprecisão de localização/horário, não exclusividade em decisões críticas e consulta a serviços meteorológicos oficiais.
- `services/api/tests/unit/test_weatherapi_mvp_controls.py` e `apps/agro/tests/unit/clima-previsao.test.ts`: testes direcionados de flag, caminho sem banco e expiração do cache local.

## Configuração climática estática

Para optar pelo caminho sem PostgreSQL, o processo da API deve receber `CLIMA_CONFIG_SOURCE=environment`. Nesse modo, o orquestrador usa as configurações climáticas carregadas pelo `Settings` e não chama `async_session_maker`. O modo padrão continua sendo `database`, preservando o funcionamento dinâmico já usado pelo DeepFarms principal. O modo estático restringe a cadeia de contingência ao provedor ativo declarado no ambiente, evitando selecionar silenciosamente provedores por configuração persistida.

WeatherAPI ainda exige `WEATHERAPI_ENABLED=true` e uma chave no backend; o default do código continua falso. A configuração efetiva do host não foi inspecionada. Este trabalho não alterou credenciais, não exibiu valores de chave e não enviou credenciais ao navegador ou a provedores.

## Testes e verificações

- Backend isolado: `PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest --confcutdir=tests/unit tests/unit/test_weatherapi_mvp_controls.py -q` — **PASS, 3 testes**. O conjunto simula falha de banco por mock e não conecta a PostgreSQL, Redis ou provedores.
- Ruff do novo módulo de teste: **PASS**.
- Vitest `clima-previsao.test.ts` e `clima-localidade.test.ts`: **PASS, 2 arquivos, 29 testes**.
- `npm run typecheck` em `apps/agro`: **PASS**.
- `npm run lint` em `apps/agro`: **PASS**.
- `npm run build` em `apps/agro`: **PASS**, páginas estáticas geradas.
- Ruff dos módulos backend completos: **não passou**; apontou 59 ocorrências distribuídas nos módulos auditados (ordenação/imports, linhas longas, regras de compatibilidade e avisos de segurança já presentes nesses arquivos). Não foi feita refatoração ampla para limpar débitos fora do ajuste funcional. O teste backend novo, isoladamente, passa no Ruff.
- `git diff --check`: **não passou por uma linha em branco no fim de `services/api/core/routers/backoffice_sessions.py`**, arquivo fora deste escopo e já modificado previamente. Não foi alterado.

O pytest global de `services/api/tests` não foi executado. `services/api/tests/conftest.py` define fallback de teste para `postgresql+asyncpg://...@192.168.0.2/farms`, executa `metadata.create_all` e inserts de fixtures. Esse caminho é incompatível com a restrição de não acessar bancos comerciais/compartilhados e explica por que a suite anterior não era segura para execução indiscriminada. O teste novo foi executado com `--confcutdir=tests/unit` e plugin autoload desabilitado para evitar esse conftest.

## Limites e riscos remanescentes

- Não foram feitas chamadas reais, contratação, ativação ou consultas a banco/Redis. Arquivos de ambiente não foram inspecionados manualmente; os testes substituíram as configurações de clima por valores sintéticos.
- A retenção de uma hora segue a decisão técnica conservadora baseada na auditoria 02B2A; os termos e limites comerciais devem ser reconfirmados no momento da ativação. Builds e testes não comprovam disponibilidade, quota ou licenciamento do provedor.
- O modo estático de clima evita a consulta PostgreSQL no refresh do orquestrador. O uso de outros módulos da API pode continuar dependendo do backend principal; esta mudança não torna toda a aplicação FastAPI independente de banco.
- O Redis não foi alterado. Em múltiplos workers, a operação de quota/rate limit precisa manter o Redis compartilhado conforme a arquitetura existente.
- A suite backend geral permanece sem resultado e requer isolamento próprio antes de ser executada.

## Próximas condições

Antes de qualquer ativação, reconfirmar termos/atribuição e autorizar separadamente a credencial. Após autorização, executar smoke limitado em ambiente não comercial e verificar a atribuição, horizonte real, expiracão online/offline, limites e comportamento de indisponibilidade. Nenhuma ativação foi iniciada automaticamente.
