"use client";

import * as React from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import {
    ShieldAlert,
    Eye,
    Pencil,
    ArrowLeft,
    Loader2,
    CheckCircle2,
    AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";
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

export function ImpersonationBanner(): React.ReactElement | null {
    const { impersonation, switchImpersonationMode, stopImpersonation } = useAppStore();
    const router = useRouter();

    const [isSwitching, setIsSwitching] = useState(false);
    const [isStopping, setIsStopping] = useState(false);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [justificativa, setJustificativa] = useState("");

    if (!impersonation || !impersonation.active) {
        return null;
    }

    const isReadOnly = impersonation.mode === "READ_ONLY";

    const handleSwitchToReadWrite = async () => {
        if (!justificativa.trim() || justificativa.trim().length < 5) {
            toast.error("Informe uma justificativa válida com no mínimo 5 caracteres.");
            return;
        }

        setIsSwitching(true);
        try {
            await switchImpersonationMode("READ_WRITE", justificativa.trim());
            toast.success("Modo Edição ativado. Todas as alterações serão auditadas.");
            setDialogOpen(false);
            setJustificativa("");
        } catch (error: unknown) {
            const err = error as { message?: string };
            toast.error(err.message || "Erro ao alternar para modo edição.");
        } finally {
            setIsSwitching(false);
        }
    };

    const handleSwitchToReadOnly = async () => {
        setIsSwitching(true);
        try {
            await switchImpersonationMode("READ_ONLY", "Retorno voluntário ao modo somente leitura");
            toast.success("Modo Somente Leitura ativado com sucesso.");
        } catch (error: unknown) {
            const err = error as { message?: string };
            toast.error(err.message || "Erro ao alternar para somente leitura.");
        } finally {
            setIsSwitching(false);
        }
    };

    const handleReturnToBackoffice = async () => {
        setIsStopping(true);
        try {
            const returnPath = await stopImpersonation();
            toast.success("Sessão de suporte encerrada. Retornando ao Backoffice...");
            if (typeof window !== "undefined") {
                window.location.href = returnPath || "/dashboard/backoffice";
            } else {
                router.push(returnPath || "/dashboard/backoffice");
            }
        } catch (error: unknown) {
            const err = error as { message?: string };
            toast.error(err.message || "Erro ao encerrar acesso assistido.");
            setIsStopping(false);
        }
    };

    return (
        <>
            <aside
                role="region"
                aria-label="Aviso de Modo de Suporte Ativo"
                className={`w-full z-[var(--z-fixed,50)] border-b px-3 py-1.5 transition-colors ${
                    isReadOnly
                        ? "bg-amber-500/10 border-amber-500/30 text-amber-900 dark:text-amber-200"
                        : "bg-rose-500/10 border-rose-500/30 text-rose-900 dark:text-rose-200"
                }`}
            >
                <div className="flex flex-wrap items-center justify-between gap-2 max-w-7xl mx-auto">
                    {/* Metadados e Contexto */}
                    <div className="flex items-center gap-2 min-w-0">
                        <div
                            className={`p-1 rounded-sm shrink-0 ${
                                isReadOnly
                                    ? "bg-amber-500/20 text-amber-600 dark:text-amber-400"
                                    : "bg-rose-500/20 text-rose-600 dark:text-rose-400"
                            }`}
                        >
                            <ShieldAlert className="w-4 h-4" />
                        </div>

                        <div className="flex flex-wrap items-center gap-1.5 text-xs">
                            <span className="font-semibold uppercase tracking-wider text-[11px]">
                                Acesso Assistido
                            </span>
                            <span className="text-muted-foreground">•</span>
                            <span className="truncate max-w-[200px] sm:max-w-[320px]">
                                Produtor: <strong className="font-medium text-foreground">{impersonation.tenant_nome}</strong>
                            </span>
                        </div>

                        {/* Badge de Modo */}
                        <Badge
                            variant="outline"
                            className={`rounded-sm text-[11px] gap-1 px-2 py-0 border ${
                                isReadOnly
                                    ? "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300"
                                    : "border-rose-500/40 bg-rose-500/10 text-rose-700 dark:text-rose-300 font-semibold"
                            }`}
                        >
                            {isReadOnly ? (
                                <>
                                    <Eye className="w-3 h-3" />
                                    Somente Leitura
                                </>
                            ) : (
                                <>
                                    <Pencil className="w-3 h-3" />
                                    Modo Edição
                                </>
                            )}
                        </Badge>
                    </div>

                    {/* Ações Operacionais */}
                    <div className="flex items-center gap-2 shrink-0">
                        {isReadOnly ? (
                            <Button
                                variant="outline"
                                size="sm"
                                disabled={isSwitching || isStopping}
                                onClick={() => setDialogOpen(true)}
                                className="h-7 text-xs rounded-sm gap-1 border-amber-500/40 hover:bg-amber-500/10"
                            >
                                <Pencil className="w-3 h-3" />
                                Habilitar Edição
                            </Button>
                        ) : (
                            <Button
                                variant="outline"
                                size="sm"
                                disabled={isSwitching || isStopping}
                                onClick={handleSwitchToReadOnly}
                                className="h-7 text-xs rounded-sm gap-1 border-rose-500/40 hover:bg-rose-500/10"
                            >
                                {isSwitching ? (
                                    <Loader2 className="w-3 h-3 animate-spin" />
                                ) : (
                                    <Eye className="w-3 h-3" />
                                )}
                                Mudar para Somente Leitura
                            </Button>
                        )}

                        <Button
                            variant="outline"
                            size="sm"
                            disabled={isStopping || isSwitching}
                            onClick={handleReturnToBackoffice}
                            className="h-7 text-xs rounded-sm gap-1 border-border/80 bg-background/80 hover:bg-muted font-medium text-foreground"
                        >
                            {isStopping ? (
                                <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                                <ArrowLeft className="w-3 h-3 text-primary" />
                            )}
                            Voltar ao Backoffice
                        </Button>
                    </div>
                </div>
            </aside>

            {/* Modal de Confirmação para Habilitar Edição */}
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                <DialogContent className="sm:max-w-md rounded-sm">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2 text-rose-600 dark:text-rose-400">
                            <AlertTriangle className="w-5 h-5 shrink-0" />
                            Habilitar Modo Edição no Produtor
                        </DialogTitle>
                        <DialogDescription className="text-xs text-muted-foreground pt-1">
                            Você está solicitando permissão para criar, alterar ou excluir registros
                            no ambiente de <strong>{impersonation.tenant_nome}</strong>. Esta ação é auditada
                            e associada ao seu usuário institucional.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-2 py-2">
                        <Label htmlFor="motivo-edicao" className="text-xs font-medium">
                            Justificativa da Alteração <span className="text-destructive">*</span>
                        </Label>
                        <Textarea
                            id="motivo-edicao"
                            rows={3}
                            placeholder="Ex: Ajuste cadastral solicitado no chamado #482 ou correção de parcela"
                            value={justificativa}
                            onChange={(e) => setJustificativa(e.target.value)}
                            className="rounded-sm text-xs resize-none"
                        />
                        <p className="text-[11px] text-muted-foreground">
                            Mínimo de 5 caracteres. Ficará registrado permanentemente nos logs de auditoria.
                        </p>
                    </div>

                    <DialogFooter className="gap-2 sm:gap-0">
                        <Button
                            variant="outline"
                            size="sm"
                            className="rounded-sm text-xs"
                            disabled={isSwitching}
                            onClick={() => setDialogOpen(false)}
                        >
                            Cancelar
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            className="rounded-sm text-xs gap-1 border-rose-600/50 text-rose-600 hover:bg-rose-500/10"
                            disabled={isSwitching || justificativa.trim().length < 5}
                            onClick={handleSwitchToReadWrite}
                        >
                            {isSwitching ? (
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                                <CheckCircle2 className="w-3.5 h-3.5" />
                            )}
                            Confirmar Modo Edição
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}

