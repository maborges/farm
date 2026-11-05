"use client";

import * as React from "react";
import { useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import {
    ShieldCheck,
    Eye,
    Pencil,
    Loader2,
    LogIn,
    Building2,
    CheckCircle2,
    Info,
    FileText,
    Tag,
} from "lucide-react";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import { startImpersonationCookies } from "@/app/actions/auth";
import { useAppStore } from "@/lib/stores/app-store";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { extractTenantContextsFromToken } from "@/lib/jwt";
import type { ImpersonationInfo, ModuleId } from "@/types/global";

interface ImpersonateTenantDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    tenant: {
        id: string;
        nome: string;
        documento?: string | null;
    } | null;
}

interface ImpersonationStartResponse {
    access_token: string;
    token_type: string;
    impersonation_id: string;
    modo: "READ_ONLY" | "READ_WRITE";
    tenant: {
        id: string;
        nome: string;
        documento?: string;
        plan_tier?: string;
        modulos?: string[];
    };
    fazendas: Array<{ id: string; nome: string }>;
    expira_em: string;
}

export function ImpersonateTenantDialog({
    open,
    onOpenChange,
    tenant,
}: ImpersonateTenantDialogProps): React.ReactElement {
    const router = useRouter();
    const pathname = usePathname();
    const { setImpersonation } = useAppStore();

    const [modo, setModo] = useState<"READ_ONLY" | "READ_WRITE">("READ_ONLY");
    const [categoria, setCategoria] = useState("SUPORTE_TECNICO");
    const [motivo, setMotivo] = useState("");
    const [loading, setLoading] = useState(false);

    const isMotivoValid = motivo.trim().length >= 5;

    const handleStart = async () => {
        if (!tenant) return;

        if (!isMotivoValid) {
            toast.error("Informe uma justificativa com pelo menos 5 caracteres.");
            return;
        }

        setLoading(true);
        try {
            const data = await apiFetch<ImpersonationStartResponse>("/backoffice/impersonate/start", {
                method: "POST",
                body: JSON.stringify({
                    tenant_id: tenant.id,
                    modo,
                    motivo: motivo.trim(),
                    categoria,
                }),
            });

            // Salva cookies com suporte a retorno ao Backoffice
            await startImpersonationCookies(
                data.access_token,
                tenant.id,
                data.fazendas?.[0]?.id,
                pathname
            );

            // Atualiza store Zustand
            const impInfo: ImpersonationInfo = {
                active: true,
                mode: data.modo,
                impersonation_id: data.impersonation_id,
                tenant_id: tenant.id,
                tenant_nome: tenant.nome,
            };

            const grupos = extractTenantContextsFromToken(data.access_token);

            // Atualiza imediatamente o Zustand store com o novo token e contexto do tenant
            useAppStore.setState({
                token: data.access_token,
                tenant: {
                    id: tenant.id,
                    nome: tenant.nome,
                    documento: tenant.documento || "",
                    slug: "",
                    dominio_customizado: null,
                    branding: { primaryColor: "154 100% 21%" },
                },
                activeGrupoId: tenant.id,
                activeFazendaId: data.fazendas?.[0]?.id || null,
                impersonation: impInfo,
                grupos,
            });

            toast.success(`Acesso assistido iniciado para ${tenant.nome}`);
            onOpenChange(false);

            // Redireciona para o painel principal do tenant
            if (typeof window !== "undefined") {
                window.location.href = "/dashboard";
            } else {
                router.push("/dashboard");
            }
        } catch (error: unknown) {
            const err = error as { message?: string };
            toast.error(err.message || "Não foi possível iniciar o acesso assistido.");
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[580px] max-h-[90vh] overflow-hidden p-0 flex flex-col rounded-sm">
                {/* Cabeçalho */}
                <DialogHeader className="border-b p-5 pb-4 bg-muted/20 shrink-0">
                    <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-sm bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
                            <ShieldCheck className="w-5 h-5" />
                        </div>
                        <div className="min-w-0 flex-1">
                            <DialogTitle className="text-base font-semibold leading-tight">
                                Acessar como Assinante
                            </DialogTitle>
                            <DialogDescription className="text-xs text-muted-foreground mt-0.5">
                                Sessão assistida de suporte técnico com isolamento de contexto e auditoria integral.
                            </DialogDescription>
                        </div>
                    </div>
                </DialogHeader>

                {/* Conteúdo com rolagem */}
                <div className="flex-1 overflow-y-auto p-5 space-y-4">
                    {/* Cartão de Identificação do Assinante */}
                    {tenant && (
                        <div className="rounded-sm border border-l-[3px] border-l-emerald-600 bg-muted/30 p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                            <div className="flex items-center gap-3 min-w-0">
                                <div className="h-8 w-8 rounded-sm bg-background border flex items-center justify-center text-muted-foreground shrink-0">
                                    <Building2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                                </div>
                                <div className="min-w-0">
                                    <div className="flex items-center gap-2">
                                        <span className="font-semibold text-sm text-foreground truncate max-w-[220px] sm:max-w-[280px]">
                                            {tenant.nome}
                                        </span>
                                    </div>
                                    <span className="text-[11px] text-muted-foreground block truncate">
                                        {tenant.documento ? `Documento: ${tenant.documento}` : "Sem documento cadastrado"}
                                    </span>
                                </div>
                            </div>
                            <div className="flex sm:flex-col items-start sm:items-end justify-between sm:justify-center gap-1 shrink-0 pt-1 sm:pt-0 border-t sm:border-t-0 border-border/50">
                                <Badge variant="secondary" className="text-[10px] py-0 px-2 font-medium bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20">
                                    Sessão Isolada
                                </Badge>
                                <span className="text-[10px] text-muted-foreground">
                                    Não consome vaga
                                </span>
                            </div>
                        </div>
                    )}

                    {/* Seletor de Modo Operacional */}
                    <div className="space-y-2">
                        <Label className="text-xs font-semibold flex items-center gap-1.5">
                            <Eye className="w-3.5 h-3.5 text-primary" />
                            Modo Operacional Inicial
                        </Label>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                            {/* Card Somente Leitura */}
                            <div
                                role="button"
                                tabIndex={0}
                                onClick={() => setModo("READ_ONLY")}
                                onKeyDown={(e) => {
                                    if (e.key === "Enter" || e.key === " ") {
                                        e.preventDefault();
                                        setModo("READ_ONLY");
                                    }
                                }}
                                className={`relative flex flex-col p-3 rounded-sm border cursor-pointer select-none transition-all ${
                                    modo === "READ_ONLY"
                                        ? "border-emerald-600 bg-emerald-500/5 ring-1 ring-emerald-600/30"
                                        : "border-border/70 hover:border-border hover:bg-muted/40"
                                }`}
                            >
                                <div className="flex items-center justify-between gap-1 mb-1.5">
                                    <div className="flex items-center gap-1.5 font-semibold text-xs text-foreground">
                                        <Eye className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                                        <span>Somente Leitura</span>
                                    </div>
                                    {modo === "READ_ONLY" ? (
                                        <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                                    ) : (
                                        <span className="text-[10px] px-1.5 py-0.2 rounded-sm bg-muted text-muted-foreground font-medium">
                                            Padrão
                                        </span>
                                    )}
                                </div>
                                <p className="text-[11px] text-muted-foreground leading-snug">
                                    Ideal para diagnóstico e visualização. Bloqueia qualquer inserção, edição ou exclusão.
                                </p>
                            </div>

                            {/* Card Modo Edição */}
                            <div
                                role="button"
                                tabIndex={0}
                                onClick={() => setModo("READ_WRITE")}
                                onKeyDown={(e) => {
                                    if (e.key === "Enter" || e.key === " ") {
                                        e.preventDefault();
                                        setModo("READ_WRITE");
                                    }
                                }}
                                className={`relative flex flex-col p-3 rounded-sm border cursor-pointer select-none transition-all ${
                                    modo === "READ_WRITE"
                                        ? "border-amber-600 bg-amber-500/5 ring-1 ring-amber-600/30"
                                        : "border-border/70 hover:border-border hover:bg-muted/40"
                                }`}
                            >
                                <div className="flex items-center justify-between gap-1 mb-1.5">
                                    <div className="flex items-center gap-1.5 font-semibold text-xs text-foreground">
                                        <Pencil className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                                        <span>Modo Edição</span>
                                    </div>
                                    {modo === "READ_WRITE" ? (
                                        <CheckCircle2 className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
                                    ) : (
                                        <span className="text-[10px] px-1.5 py-0.2 rounded-sm bg-muted text-muted-foreground font-medium">
                                            Sob demanda
                                        </span>
                                    )}
                                </div>
                                <p className="text-[11px] text-muted-foreground leading-snug">
                                    Permite salvar cadastros e configurações. Cada mutação é gravada na auditoria.
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Categoria do Atendimento */}
                    <div className="space-y-1.5">
                        <Label htmlFor="categoria-select" className="text-xs font-semibold flex items-center gap-1.5">
                            <Tag className="w-3.5 h-3.5 text-primary" />
                            Categoria do Atendimento
                        </Label>
                        <Select value={categoria} onValueChange={setCategoria}>
                            <SelectTrigger id="categoria-select" className="rounded-sm h-8 text-xs bg-background">
                                <SelectValue placeholder="Selecione a categoria" />
                            </SelectTrigger>
                            <SelectContent className="rounded-sm text-xs">
                                <SelectItem value="SUPORTE_TECNICO">Suporte Técnico / Chamado de Usuário</SelectItem>
                                <SelectItem value="CONFIGURACAO_CONTA">Auxílio na Configuração de Módulos</SelectItem>
                                <SelectItem value="INVESTIGACAO_INCIDENTE">Investigação de Bug ou Inconsistência</SelectItem>
                                <SelectItem value="TREINAMENTO_CLIENTE">Treinamento e Demonstração Assistida</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    {/* Justificativa / Motivo */}
                    <div className="space-y-1.5">
                        <div className="flex items-center justify-between">
                            <Label htmlFor="motivo-input" className="text-xs font-semibold flex items-center gap-1.5">
                                <FileText className="w-3.5 h-3.5 text-primary" />
                                Justificativa / Número do Chamado <span className="text-destructive">*</span>
                            </Label>
                            <span className={`text-[10px] font-medium ${isMotivoValid ? "text-muted-foreground" : "text-destructive"}`}>
                                {motivo.trim().length}/5 mín.
                            </span>
                        </div>
                        <Textarea
                            id="motivo-input"
                            rows={3}
                            placeholder="Ex: Atendimento ao chamado #1042 referente a conferência de lote de animais ou safra..."
                            value={motivo}
                            onChange={(e) => setMotivo(e.target.value)}
                            className="rounded-sm text-xs resize-none bg-background focus-visible:ring-1"
                        />
                        <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground pt-0.5">
                            <Info className="w-3.5 h-3.5 text-primary/70 shrink-0" />
                            <span>A justificativa é arquivada nos logs de auditoria e associada ao seu usuário institucional.</span>
                        </div>
                    </div>
                </div>

                {/* Rodapé com botões de ação */}
                <DialogFooter className="border-t p-4 px-5 bg-muted/10 shrink-0 flex items-center justify-between sm:justify-between gap-2">
                    <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={loading}
                        onClick={() => onOpenChange(false)}
                        className="rounded-sm text-xs h-8 px-3"
                    >
                        Cancelar
                    </Button>
                    <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={loading || !isMotivoValid}
                        onClick={handleStart}
                        className="rounded-sm text-xs h-8 px-3 gap-1.5 border-emerald-600/60 bg-emerald-600 text-white hover:bg-emerald-700 hover:text-white dark:bg-emerald-600 dark:text-white dark:hover:bg-emerald-700 font-medium transition-all"
                    >
                        {loading ? (
                            <>
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                Conectando...
                            </>
                        ) : (
                            <>
                                <LogIn className="w-3.5 h-3.5" />
                                Entrar como Assinante
                            </>
                        )}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
