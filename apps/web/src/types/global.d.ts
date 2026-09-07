// apps/web/src/types/global.d.ts
// Tipos core simulando contratos estritos em Typescript do que vem do backend

export type ModuleId =
  | "CORE"
  | "A1_PLANEJAMENTO" | "A2_CAMPO" | "A3_DEFENSIVOS" | "A4_PRECISAO" | "A5_COLHEITA"
  | "P1_REBANHO" | "P2_GENETICA" | "P3_CONFINAMENTO" | "P4_LEITE"
  | "F1_TESOURARIA" | "F2_CUSTOS_ABC" | "F3_FISCAL" | "F4_HEDGING"
  | "O1_FROTA" | "O2_ESTOQUE" | "O3_COMPRAS" | "O4_BALANCA"
  | "IMOVEIS_CADASTRO" | "IMOVEIS_ARRENDAMENTOS" | "IMOVEIS_AVALIACAO"
  | "RH1_REMUNERACAO" | "RH2_SEGURANCA"
  | "AM1_COMPLIANCE" | "AM2_CARBONO"
  | "EXT_IA" | "EXT_IOT" | "EXT_ERP";

export type NavigationMode = "sidebar" | "mega-menu";
export type NavigationModeApi = "SIDEBAR" | "MEGA_MENU";

export type PlanTierId = "BASICO" | "PROFISSIONAL" | "ENTERPRISE" | "PREMIUM";

export type BackofficeRole = "super_admin" | "admin" | "suporte" | "financeiro" | "comercial";

export type TenantRole = "owner" | "admin" | "gerente" | "agronomo" | "veterinario" | "operador" | "financeiro" | "visualizador";

export type PermissionLevel = "write" | "read" | "none";

export interface TenantCustomPermissions {
    granted?: string[];
    permissions?: string[];
    [key: string]: PermissionLevel | string[] | undefined;
}

export interface Branding {
    primaryColor?: string;
    logoUrl?: string;
    borderRadius?: string;
}

export interface Tenant {
    id: string;
    nome: string;
    documento: string;
    slug: string | null;
    dominio_customizado: string | null;
    branding: Branding | null;
    onboarding_configuracao_completo?: boolean;
}

export interface User {
    id: string;
    name: string;
    nickname?: string;
    email: string;
    username?: string;
    cpf?: string;
    telefone?: string;
    foto_perfil_url?: string;
    foto_perfil_cache_bust?: string;
    is_superuser?: boolean;
    role?: BackofficeRole;
    tenant_role?: TenantRole;
    custom_permissions?: TenantCustomPermissions;
    grupos_auth?: string[];
    navigation_mode?: "SIDEBAR" | "MEGA_MENU";
}

export interface FazendaAccess {
    id: string;
    nome: string;
    role: "gerente_regional" | "admin" | "agronomo" | "operador";
    perfil_fazenda_id?: string | null;
    vigencia_inicio?: string | null;
    vigencia_fim?: string | null;
}

/** Contexto de tenant com módulos e fazendas permitidas. */
export interface TenantContext {
    id: string;
    nome: string;
    modules: ModuleId[];
    plan_tier: PlanTierId;
    max_fazendas: number;   // -1 = ilimitado
    max_usuarios: number;
    fazendas: Array<{ id: string; nome: string }>;
}

export type GrupoAccess = TenantContext;

/** Informações resumidas de um contexto de tenant para alternância */
export interface TenantContextInfo {
    tenant_id: string;
    tenant_nome: string;
    plano_nome: string;
    plano_tier: PlanTierId;
    status: string;
    total_fazendas: number;
    fazendas: Array<{ id: string; nome: string }>;
    modulos: ModuleId[];
    is_ativa: boolean;
}

export type AssinaturaInfo = TenantContextInfo;

/**
 * Resumo de um tenant retornado por /auth/me e /auth/my-tenants.
 * É o contrato unificado usado em auth bootstrap, switchers e store.
 */
export interface TenantSummary {
    tenant_id: string;
    nome_tenant: string;
    is_owner: boolean;
    plan_tier?: PlanTierId;
    max_fazendas?: number;
    max_usuarios?: number;
    modulos?: ModuleId[];
    perfil?: {
        nome: string;
        permissoes?: TenantCustomPermissions;
    } | null;
    fazendas: Array<{
        unidade_produtiva_id: string;
        nome: string;
    }>;
}

export interface TerritoryReadView {
    unidade_produtiva_id: string;
    exploracoes_rurais: Array<{
        id: string;
        propriedade_id: string;
    }>;
    propriedades: Array<{
        id: string;
        nome: string;
    }>;
    imovel_principal: {
        id: string;
        nome: string | null;
        nirf: string | null;
        car_numero: string | null;
        numero_matricula: string | null;
        ccir_numero?: string | null;
        sigef_codigo?: string | null;
        area_total_ha: string | null;
    } | null;
    imoveis_secundarios: Array<{
        id: string;
        nome: string | null;
        nirf: string | null;
        car_numero: string | null;
        numero_matricula: string | null;
        ccir_numero?: string | null;
        sigef_codigo?: string | null;
        area_total_ha: string | null;
    }>;
    associacoes: Array<{
        id: string;
        propriedade_id: string;
        imovel_rural_id: string;
        vinculo_principal: boolean;
        tipo_vinculo: string;
    }>;
    fonte_da_leitura: string;
    estado_de_convergencia: string;
    avisos: string[];
}

export interface UnidadeProdutiva {
    id: string;
    tenant_id: string;
    nome: string;
    tipo_propriedade: string | null;
    cpf_cnpj: string | null;
    inscricao_estadual: string | null;
    // Localização
    cep: string | null;
    logradouro: string | null;
    numero: string | null;
    complemento: string | null;
    bairro: string | null;
    municipio: string | null;
    uf: string | null;
    ibge_municipio_codigo: string | null;
    // Áreas
    area_total_ha: number | null;
    area_total_calculada_ha: number | null;
    area_app_ha: number | null;
    area_rl_ha: number | null;
    coordenadas_sede: string | null;
    geometria: Record<string, unknown> | null;
    logo_url: string | null;
    ativo: boolean;
    created_at: string;
    updated_at: string;
    territorio?: TerritoryReadView;
}

/* ─── Backoffice Admin ─── */

export interface Admin {
    id: string;
    email: string;
    nome: string;
    role: BackofficeRole;
    ativo: boolean;
    ultimo_acesso: string | null;
    timezone: string;
    locale: string;
    created_at: string;
    updated_at: string;
}

export interface AdminStats {
    total: number;
    ativos: number;
    super_admins: number;
    por_role: Record<BackofficeRole, number>;
}

/* ─── Team (Equipe do Tenant) ─── */

export interface TeamMemberProfile {
    id: string;
    nome: string;
    is_custom: boolean;
    descricao: string | null;
}

export interface FazendaComPerfilEspecifico {
    unidade_produtiva_id: string;
    fazenda_nome: string;
    perfil_id: string;
    perfil_nome: string;
}

export interface TeamMember {
    id: string;
    usuario_id: string;
    nome: string;
    email: string;
    perfil: TeamMemberProfile;
    is_owner: boolean;
    status: "ATIVO" | "INATIVO" | "PENDENTE";
    fazendas: Array<{ id: string; nome: string }>;
    fazendas_com_perfil_especifico: FazendaComPerfilEspecifico[];
    data_cadastro: string;
}

export interface TeamStats {
    total_membros: number;
    ativos: number;
    owners: number;
    convites_pendentes: number;
}

export interface TeamInvite {
    id: string;
    email_convidado: string;
    perfil: TeamMemberProfile;
    fazendas: Array<{ id: string; nome: string }>;
    status: "PENDENTE" | "ACEITO" | "EXPIRADO";
    data_expiracao: string;
    data_validade_acesso: string | null;
    created_at: string;
}

/* ─── Perfis e Permissões ─── */

export interface TenantRoleProfile {
    id: string;
    nome: string;
    is_custom: boolean;
    descricao: string | null;
    permissoes?: TenantCustomPermissions;
    em_uso?: number;
}
