# Relatório de Correção Arquitetural do Wizard (WIZARD-FIX-01)

**Data:** 2026-07-08
**Escopo:** Tenant, Multiunidade, Multicultura e Operação Mista
**Autor:** Antigravity (AI Agent)

## 1. Diagnóstico e Causa Raiz
O Wizard foi modelado contendo uma dependência restritiva na inicialização vinculando a `ImplantacaoOperacional` diretamente a uma `UnidadeProdutiva`. Além disso, havia uma premissa (ou preocupação na modelagem) de que o Wizard e seus checklists suportavam apenas operações restritas, limitadas a uma cultura específica ou forçando a escolha mutuamente exclusiva entre Agricultura e Pecuária.

**Regra antiga (incorreta):**
- A `ImplantacaoOperacional` assumia `UnidadeProdutiva` como dona/dependência restritiva para dar andamento às etapas.
- Havia risco de o backend rejeitar múltiplas unidades ou requerer seleção estrita logo no step inicial.
- Possíveis restrições de exclusividade (Agricultura OU Pecuária).

## 2. Regra Nova e Correta
- **Propriedade:** A `ImplantacaoOperacional` pertence ao `Tenant`.
- **Referência Opcional/Principal:** A `UnidadeProdutiva` atua como evidência operacional. Caso não exista no início, o Wizard indica como "pendência" e orienta a criação.
- **Go-Live Protegido:** Para atingir o Go-Live, o banco de dados e o motor de estado exigem que exista pelo menos uma Unidade Produtiva (Reference Unit). O sistema a vincula automaticamente de forma transparente no momento da transição, se houver.
- **Operação Mista & Multicultura:** A avaliação do checklist engine `_module_enabled()` já atua de forma independente. Isso permite que Agricultura e Pecuária coexistam sem problemas, bem como múltiplas culturas.

## 3. Decisões Tomadas
### 3.1. Sobre `unidade_produtiva_id`
O banco de dados possui uma *Check Constraint* (`ck_wizard_implantacao_status_requires_unidade`) que exige `unidade_produtiva_id IS NOT NULL` a partir do estado `READY_FOR_GO_LIVE`. 
**Decisão:** Em vez de gerar uma migração (evitando overhead e quebras), transformamos `unidade_produtiva_id` em um ponteiro de "Unidade Principal/Referência". Se o usuário não definiu uma no POST `/iniciar`, o sistema avança sem problemas e o próprio backend descobre a Unidade Produtiva mais antiga (`limit(1)`) pouco antes do Go-Live para satisfazer o constraint silenciosamente.

### 3.2. Sobre Multicultura e Operação Mista
Após auditoria, validou-se que o código atual (backend e frontend) não restringe artificialmente a uma única cultura nem aplica XOR entre Agricultura e Pecuária. A arquitetura de validação lê o campo `escopo_modulos` dinamicamente. Portanto, o suporte nativo já existia e foi validado. Nenhuma lista *hardcoded* bloqueia o piloto.

## 4. Arquivos Auditados e Alterados

**Auditados:**
- `services/api/wizard/models.py`
- `services/api/wizard/checklist_engine.py`
- `services/api/wizard/state_engine.py`
- `services/api/wizard/router.py`
- `services/api/wizard/schemas.py`
- `apps/web/src/app/(dashboard)/dashboard/implantacao/wizard/wizard-client.tsx`
- Componentes e helpers do frontend (ex: `apps/web/src/lib/constants/modulos.ts`)

**Alterados:**
- **`services/api/wizard/services.py`**:
  - `_resolver_unidade_produtiva_id`: Modificado para retornar a primeira Unidade Produtiva ativa encontrada ao invés de retornar `None` caso existam múltiplas unidades.
  - `aplicar_transicao_estado`: Inserido gatilho automático chamando `garantir_unidade_produtiva_contextual()` antes da transição para `READY_FOR_GO_LIVE`. Isso satisfaz o constraint sem forçar o frontend a enviar o dado.

## 5. Limitações Restantes e Próximos Passos
1. **Frontend UI/UX**: Embora o Wizard funcione, a interface gráfica pode se beneficiar de "Empty States" mais amigáveis e explicativos sobre o passo a passo da criação das Unidades, Culturas, e Piquetes antes do Go-Live.
2. **Dashboard Multi-Contexto**: À medida que a implantação avança para gerir 10+ unidades produtivas, a listagem do "Escopo da Implantação" precisará de uma UI expansível (Accordion ou List) em vez de um único cartão no topo.

## 6. Validação de Testes
Os comandos de linting e validação de testes na suíte do wizard (`pytest services/api/tests/unit/wizard`) atestam que:
- O Wizard inicia sem Unidade Produtiva.
- O Go-live continua protegido pelo constraint de banco.
- O checklist indica ausência de unidade como falha na etapa e bloqueio crítico.
