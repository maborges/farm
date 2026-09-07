import { Phone, Mail, Users, FileText, CheckCircle2, MessageSquare } from "lucide-react";

export type Severidade = "warning" | "danger";
export type Periodo = "30" | "90" | "180" | "all";

export interface Estagio {
    id: string;
    nome: string;
    cor: string;
    ordem: number;
    ativo: boolean;
    total_leads: number;
    created_at: string;
}

export interface Atividade {
    id: string;
    lead_id: string;
    tipo: string;
    descricao: string;
    data_agendada: string | null;
    concluida: boolean;
    admin_user_id: string | null;
    admin_email: string | null;
    created_at: string;
}

export interface Lead {
    id: string;
    nome: string;
    email: string | null;
    telefone: string | null;
    empresa: string | null;
    documento: string | null;
    estagio_id: string;
    origem: string;
    valor_estimado: number | null;
    plano_interesse: string | null;
    qtd_fazendas: number | null;
    qtd_usuarios: number | null;
    responsavel_id: string | null;
    status: string;
    motivo_perda: string | null;
    data_conversao: string | null;
    tenant_convertido_id: string | null;
    notas: string | null;
    tags: Record<string, unknown> | null;
    created_at: string;
    updated_at: string;
    estagio: Estagio | null;
    atividades: Atividade[];
}

export interface KanbanData {
    estagios: Estagio[];
    leads_por_estagio: Record<string, Lead[]>;
    totais: Record<string, number>;
}

export interface PlanoComercial {
    id: string;
    nome: string;
    slug: string;
    descricao: string | null;
    tipo_oferta: string;
    modulos_inclusos: string[];
    preco_mensal_padrao: number | null;
    preco_anual_padrao: number | null;
    ativo: boolean;
}

export interface ModuloOferta {
    id: string;
    nome: string;
    slug: string;
    descricao: string | null;
    categoria: string;
    ativo: boolean;
    icone: string | null;
}

export interface CRMStats {
    total_leads: number;
    leads_ativos: number;
    leads_convertidos: number;
    leads_perdidos: number;
    valor_pipeline: number;
    por_origem: Record<string, number>;
    por_estagio: Record<string, number>;
    conversoes_mes: number;
}

export interface LeadListData {
    items: Lead[];
    total: number;
    page: number;
    page_size: number;
}

export const ORIGENS: Record<string, { label: string; color: string }> = {
    manual: { label: "Manual", color: "bg-zinc-500/10 text-zinc-700 border-zinc-200 dark:bg-zinc-500/20 dark:text-zinc-100 dark:border-zinc-700" },
    site: { label: "Site", color: "bg-blue-500/10 text-blue-700 border-blue-200 dark:bg-blue-500/20 dark:text-blue-100 dark:border-blue-400/30" },
    indicacao: { label: "Indicação", color: "bg-emerald-500/10 text-emerald-700 border-emerald-200 dark:bg-emerald-500/20 dark:text-emerald-100 dark:border-emerald-400/30" },
    evento: { label: "Evento", color: "bg-violet-500/10 text-violet-700 border-violet-200 dark:bg-violet-500/20 dark:text-violet-100 dark:border-violet-400/30" },
    social: { label: "Social", color: "bg-pink-500/10 text-pink-700 border-pink-200 dark:bg-pink-500/20 dark:text-pink-100 dark:border-pink-400/30" },
    parceiro: { label: "Parceiro", color: "bg-amber-500/10 text-amber-700 border-amber-200 dark:bg-amber-500/20 dark:text-amber-100 dark:border-amber-400/30" },
};

export const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
    ativo: { label: "Ativo", color: "bg-emerald-500/10 text-emerald-700 border-emerald-200 dark:bg-emerald-500/20 dark:text-emerald-100 dark:border-emerald-400/30" },
    aprovado: { label: "Aprovado", color: "bg-amber-500/10 text-amber-700 border-amber-200 dark:bg-amber-500/20 dark:text-amber-100 dark:border-amber-400/30" },
    convertido: { label: "Convertido", color: "bg-blue-500/10 text-blue-700 border-blue-200 dark:bg-blue-500/20 dark:text-blue-100 dark:border-blue-400/30" },
    perdido: { label: "Perdido", color: "bg-red-500/10 text-red-700 border-red-200 dark:bg-red-500/20 dark:text-red-100 dark:border-red-400/30" },
};

export const ATIVIDADE_TIPOS: Record<string, { label: string; icon: typeof Phone }> = {
    ligacao: { label: "Ligação", icon: Phone },
    email: { label: "Email", icon: Mail },
    reuniao: { label: "Reunião", icon: Users },
    nota: { label: "Nota", icon: FileText },
    tarefa: { label: "Tarefa", icon: CheckCircle2 },
    whatsapp: { label: "WhatsApp", icon: MessageSquare },
};
