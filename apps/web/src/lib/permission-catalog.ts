/**
 * Catálogo de permissões granulares — derivado dos 42 routers da API.
 * Formato: modulo:recurso:acao
 *
 * Ações disponíveis:
 *   view   — visualizar / detalhar registro
 *   list   — listar registros
 *   create — criar novo registro
 *   edit   — editar registro existente
 *   delete — excluir registro
 *   export — exportar / gerar relatório
 *   approve — aprovar / validar (fluxos de aprovação)
 */

export type PermAction = "view" | "list" | "create" | "edit" | "delete" | "export" | "approve";

export interface PermResource {
    key: string;          // Ex: "agricola:operacoes"
    label: string;        // Ex: "Operações de Campo"
    actions: PermAction[];
}

export interface PermModule {
    key: string;          // Ex: "agricola"
    label: string;
    icon: string;
    resources: PermResource[];
}

const A: PermAction[] = ["view", "list", "create", "edit", "delete", "export"];
const AR: PermAction[] = ["view", "list", "create", "edit", "delete", "export", "approve"];
const RO: PermAction[] = ["view", "list", "export"];

export const PERMISSION_CATALOG: PermModule[] = [
    // ─── CONTA / TENANT ───────────────────────────────────────────────────────
    {
        key: "tenant",
        label: "Gestão da Conta",
        icon: "🏢",
        resources: [
            { key: "tenant:fazendas", label: "Fazendas", actions: ["view", "list", "create", "edit", "delete"] },
            { key: "tenant:groups", label: "Grupos de Fazendas", actions: ["view", "list", "create", "edit", "delete"] },
            { key: "tenant:users", label: "Membros da Equipe", actions: ["view", "list", "create", "edit", "delete"] },
            { key: "tenant:invites", label: "Convites", actions: ["view", "list", "create", "delete"] },
            { key: "tenant:permissions", label: "Perfis e Permissões", actions: ["view", "list", "create", "edit", "delete"] },
            { key: "tenant:settings", label: "Configurações da Conta", actions: ["view", "edit"] },
            { key: "tenant:billing", label: "Plano e Faturamento", actions: ["view"] },
            { key: "tenant:audit", label: "Auditoria e Logs", actions: ["view", "list", "export"] },
        ],
    },

    // ─── MÓDULO AGRÍCOLA ──────────────────────────────────────────────────────
    {
        key: "agricola",
        label: "Módulo Agrícola",
        icon: "🌱",
        resources: [
            { key: "agricola:safras", label: "Safras", actions: A },
            { key: "agricola:talhoes", label: "Talhões e Glebas", actions: A },
            { key: "agricola:cadastros", label: "Cadastros (Culturas, Insumos)", actions: A },
            { key: "agricola:planejamento", label: "Planejamento / Orçamento", actions: AR },
            { key: "agricola:operacoes", label: "Operações do Campo", actions: AR },
            { key: "agricola:custos", label: "Custos de Produção", actions: [...A, "approve"] },
            { key: "agricola:colheita", label: "Colheita / Romaneios", actions: AR },
            { key: "agricola:beneficiamento", label: "Beneficiamento / Secagem", actions: A },
            { key: "agricola:analises_solo", label: "Análises de Solo", actions: A },
            { key: "agricola:monitoramento", label: "Monitoramento (Pragas/Doenças)", actions: A },
            { key: "agricola:ndvi", label: "Índices de Vegetação (NDVI)", actions: RO },
            { key: "agricola:climatico", label: "Dados Climáticos", actions: RO },
            { key: "agricola:fenologia", label: "Fenologia", actions: A },
            { key: "agricola:irrigacao", label: "Irrigação", actions: A },
            { key: "agricola:prescricoes", label: "Prescrições e VRT", actions: A },
            { key: "agricola:rastreabilidade", label: "Rastreabilidade de Campo", actions: [...RO, "create"] },
            { key: "agricola:checklist", label: "Checklists Agrícolas", actions: A },
            { key: "agricola:alertas", label: "Alertas Agronômicos", actions: ["view", "list", "delete"] },
            { key: "agricola:agronomo", label: "Laudos e RAT (Agrônomo)", actions: [...A, "approve"] },
            { key: "agricola:relatorios", label: "Relatórios Agrícolas", actions: ["view", "list", "export"] },
            { key: "agricola:dashboard", label: "Dashboard Agrícola", actions: ["view"] },
        ],
    },

    // ─── MÓDULO PECUÁRIO ──────────────────────────────────────────────────────
    {
        key: "pecuaria",
        label: "Módulo Pecuário",
        icon: "🐄",
        resources: [
            { key: "pecuaria:dashboard", label: "Dashboard Pecuário", actions: RO },
            { key: "pecuaria:sync_campo", label: "Sincronização de Campo", actions: RO },
            { key: "pecuaria:nutricao", label: "Nutrição / Alimentação", actions: A },
            { key: "pecuaria:confinamento", label: "Confinamento (TMR/Cochos)", actions: A },
            { key: "pecuaria:leite", label: "Produção de Leite", actions: A },
            { key: "pecuaria:lotes", label: "Lotes e Rebanho", actions: A },
            { key: "pecuaria:animais", label: "Animais (individual)", actions: A },
            { key: "pecuaria:manejos", label: "Manejos Sanitários", actions: A },
            { key: "pecuaria:pesagens", label: "Pesagens e GMD", actions: A },
            { key: "pecuaria:reproducao", label: "Reprodução", actions: A },
            { key: "pecuaria:piquetes", label: "Piquetes / Pastagens", actions: A },
            { key: "pecuaria:climatico", label: "Dados Climáticos Pecuários", actions: RO },
            { key: "pecuaria:inteligencia", label: "Inteligência e Zoossanitário", actions: A },
            { key: "pecuaria:custos", label: "Custos Pecuários", actions: [...A, "approve"] },
            { key: "pecuaria:abates", label: "Abates e Comercialização", actions: [...A, "approve"] },
            { key: "pecuaria:alertas", label: "Alertas Zootécnicos", actions: ["view", "list", "delete"] },
            { key: "pecuaria:relatorios", label: "Relatórios Pecuários", actions: ["view", "list", "export"] },
        ],
    },

    // ─── MÓDULO FINANCEIRO ────────────────────────────────────────────────────
    {
        key: "financeiro",
        label: "Módulo Financeiro",
        icon: "💰",
        resources: [
            { key: "financeiro:dashboard", label: "Dashboard Financeiro", actions: RO },
            { key: "financeiro:hedge", label: "Hedging & Futuros", actions: A },
            { key: "financeiro:fiscal", label: "Fiscal & Obrigações (NF-e/LCDPR/eSocial)", actions: A },
            { key: "financeiro:despesas", label: "Despesas", actions: AR },
            { key: "financeiro:receitas", label: "Receitas", actions: AR },
            { key: "financeiro:lancamentos", label: "Lançamentos Gerais", actions: AR },
            { key: "financeiro:categorias", label: "Categorias Financeiras", actions: A },
            { key: "financeiro:centro_custo", label: "Centros de Custo", actions: A },
            { key: "financeiro:contas", label: "Contas Bancárias / Caixa", actions: A },
            { key: "financeiro:dre", label: "DRE / Resultado", actions: RO },
            { key: "financeiro:fluxo_caixa", label: "Fluxo de Caixa", actions: RO },
            { key: "financeiro:relatorios", label: "Relatórios Financeiros", actions: RO },
        ],
    },

    // ─── MÓDULO OPERACIONAL ───────────────────────────────────────────────────
    {
        key: "operacional",
        label: "Módulo Operacional",
        icon: "⚙️",
        resources: [
            { key: "operacional:frota", label: "Frota (Máquinas/Veículos)", actions: A },
            { key: "operacional:abastecimento", label: "Abastecimento", actions: A },
            { key: "operacional:oficina", label: "Oficina / Manutenção", actions: AR },
            { key: "operacional:checklist", label: "Checklist de Equipamentos", actions: A },
            { key: "operacional:apontamento", label: "Apontamentos Operacionais", actions: A },
            { key: "operacional:compras", label: "Compras / Pedidos", actions: AR },
            { key: "operacional:inteligencia", label: "Inteligência de Frota", actions: RO },
            { key: "operacional:relatorios", label: "Relatórios Operacionais", actions: RO },
        ],
    },

    // ─── MÓDULO ESTOQUE ───────────────────────────────────────────────────────
    {
        key: "estoque",
        label: "Estoque",
        icon: "📦",
        resources: [
            { key: "estoque:saldo", label: "Saldos de Estoque", actions: ["view", "list", "export"] },
            { key: "estoque:movimentacoes", label: "Movimentações (Entrada/Saída)", actions: A },
            { key: "estoque:lotes", label: "Lotes de Produtos", actions: A },
            { key: "estoque:recepcao", label: "Recepção / Notas de Entrada", actions: AR },
            { key: "estoque:devolucao", label: "Devoluções", actions: AR },
            { key: "estoque:implantacao_assistida", label: "Implantação Assistida de Estoque", actions: ["view", "list", "create", "edit", "approve", "delete"] },
            { key: "estoque:fornecedores", label: "Fornecedores", actions: A },
            { key: "estoque:relatorios", label: "Relatórios de Estoque", actions: RO },
        ],
    },

    // ─── MÓDULO PESSOAS / RH ─────────────────────────────────────────────────
    {
        key: "pessoas",
        label: "Pessoas / RH",
        icon: "👥",
        resources: [
            { key: "pessoas:colaboradores", label: "Colaboradores", actions: A },
            { key: "pessoas:contratos", label: "Contratos de Trabalho", actions: A },
            { key: "pessoas:folha", label: "Folha de Pagamento", actions: [...A, "approve"] },
            { key: "pessoas:ponto", label: "Controle de Ponto", actions: A },
            { key: "pessoas:esocial", label: "eSocial", actions: A },
            { key: "pessoas:relatorios", label: "Relatórios de RH", actions: RO },
        ],
    },

    // ─── IMÓVEIS RURAIS ───────────────────────────────────────────────────────
    {
        key: "imoveis",
        label: "Imóveis Rurais",
        icon: "🗺️",
        resources: [
            { key: "imoveis:propriedades", label: "Propriedades (CAR/ITR)", actions: A },
            { key: "imoveis:documentos", label: "Documentos e Certidões", actions: A },
            { key: "imoveis:areas", label: "Áreas Rurais e Glebas", actions: A },
            { key: "imoveis:avaliacoes", label: "Avaliação Patrimonial", actions: A },
        ],
    },

    // ─── CADASTROS COMPARTILHADOS ─────────────────────────────────────────────
    {
        key: "cadastros",
        label: "Cadastros Compartilhados",
        icon: "🗂️",
        resources: [
            { key: "cadastros:commodities", label: "Commodities", actions: A },
            { key: "cadastros:produtos", label: "Catálogo de Produtos", actions: A },
            { key: "cadastros:pessoas", label: "Pessoas & Parceiros", actions: A },
            { key: "cadastros:marcas", label: "Marcas", actions: A },
            { key: "cadastros:modelos", label: "Modelos", actions: A },
            { key: "cadastros:categorias_produto", label: "Categorias de Produto", actions: A },
        ],
    },

    // ─── RH — SEGURANÇA DO TRABALHO ───────────────────────────────────────────
    {
        key: "sst",
        label: "Segurança do Trabalho",
        icon: "🦺",
        resources: [
            { key: "sst:seguranca", label: "EPI/EPC, Documentos e Relatórios SST", actions: A },
        ],
    },

    // ─── MÓDULO AMBIENTAL ─────────────────────────────────────────────────────
    {
        key: "ambiental",
        label: "Módulo Ambiental",
        icon: "🌳",
        resources: [
            { key: "ambiental:dashboard", label: "Dashboard Ambiental", actions: RO },
            { key: "ambiental:car", label: "CAR & Áreas", actions: A },
            { key: "ambiental:outorgas", label: "Outorgas Hídricas", actions: A },
            { key: "ambiental:carbono", label: "Gestão de Carbono", actions: A },
            { key: "ambiental:certificacoes", label: "Certificações & ESG", actions: A },
            { key: "ambiental:monitoramento", label: "Monitoramento de Desmatamento", actions: RO },
        ],
    },

    // ─── COPILOTO IA ──────────────────────────────────────────────────────────
    {
        key: "ia",
        label: "Copiloto IA",
        icon: "🧠",
        resources: [
            { key: "ia:dashboard", label: "Dashboard de IA", actions: RO },
            { key: "ia:recomendacoes", label: "Recomendações Operacionais", actions: RO },
            { key: "ia:performance", label: "Performance & Eficiência", actions: RO },
            { key: "ia:plano", label: "Plano de Ação e Resumo de Safra", actions: A },
        ],
    },

    // ─── CAMPO PWA ────────────────────────────────────────────────────────────
    {
        key: "campo",
        label: "Campo PWA",
        icon: "📱",
        resources: [
            { key: "campo:dispositivos", label: "Dispositivos", actions: A },
            { key: "campo:tarefas", label: "Tarefas de Campo", actions: A },
        ],
    },

    // ─── BALANÇA ──────────────────────────────────────────────────────────────
    {
        key: "balanca",
        label: "Balança",
        icon: "⚖️",
        resources: [
            { key: "balanca:dispositivo", label: "Estações de Balança", actions: A },
            { key: "balanca:operador", label: "Operadores de Balança", actions: A },
            { key: "balanca:pesagem", label: "Ordens de Pesagem", actions: A },
        ],
    },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Converte lista de strings granted → Set para lookup O(1) */
export function buildGrantedSet(granted: string[]): Set<string> {
    return new Set(granted);
}

/** Verifica se uma permissão está no granted set (suporta wildcards) */
export function isGranted(grantedSet: Set<string>, permission: string): boolean {
    if (grantedSet.has("*") || grantedSet.has(permission)) return true;
    const parts = permission.split(":");
    for (let i = 1; i <= parts.length; i++) {
        if (grantedSet.has(parts.slice(0, i).join(":") + ":*")) return true;
    }
    return false;
}

/** Toggle de uma permissão específica na lista */
export function togglePermission(granted: string[], permission: string): string[] {
    if (granted.includes(permission)) return granted.filter((p) => p !== permission);
    return [...granted, permission];
}

/**
 * Remove uma permissão do conjunto concedido, mesmo quando ela só está coberta
 * por um wildcard herdado (ex: "agricola:*" ou "agricola:operacoes:*") em vez de
 * uma entrada exata. "Abre" o wildcard nas permissões concretas que ele cobre e
 * remove apenas a solicitada — sem isso, desmarcar um item herdado de um perfil
 * clonado não tinha efeito (a entrada exata nunca existia para ser removida).
 */
export function revokeGranted(granted: string[], permission: string): string[] {
    if (granted.includes(permission)) {
        return granted.filter((p) => p !== permission);
    }

    const parts = permission.split(":");
    const mod = PERMISSION_CATALOG.find((m) => m.key === parts[0]);
    if (!mod) return granted;

    for (let i = 1; i < parts.length; i++) {
        const prefix = parts.slice(0, i).join(":");
        const wildcard = `${prefix}:*`;
        if (!granted.includes(wildcard)) continue;

        const coveredResources = prefix === mod.key
            ? mod.resources
            : mod.resources.filter((r) => r.key === prefix);

        const expanded = coveredResources
            .flatMap((r) => r.actions.map((a) => `${r.key}:${a}`))
            .filter((p) => p !== permission);

        return [...granted.filter((p) => p !== wildcard), ...expanded];
    }

    return granted;
}

/** Labels para ações */
export const ACTION_LABELS: Record<PermAction, string> = {
    view: "Ver",
    list: "Listar",
    create: "Criar",
    edit: "Editar",
    delete: "Excluir",
    export: "Exportar",
    approve: "Aprovar",
};

/** Cores por ação */
export const ACTION_COLORS: Record<PermAction, string> = {
    view: "text-blue-600",
    list: "text-sky-600",
    create: "text-green-600",
    edit: "text-amber-600",
    delete: "text-red-500",
    export: "text-purple-600",
    approve: "text-emerald-600",
};
