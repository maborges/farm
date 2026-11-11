"use client";

import { useState } from "react";
import { toast } from "sonner";
import { KeyRound, Loader2, X, Check } from "lucide-react";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogBody,
    DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { PasswordInput } from "@/components/ui/password-input";
import { Label } from "@/components/ui/label";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

interface ChangePasswordDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export function ChangePasswordDialog({ open, onOpenChange }: ChangePasswordDialogProps) {
    const [senhaAtual, setSenhaAtual] = useState("");
    const [novaSenha, setNovaSenha] = useState("");
    const [confirmarSenha, setConfirmarSenha] = useState("");
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (novaSenha !== confirmarSenha) {
            toast.error("As senhas não coincidem.");
            return;
        }

        if (novaSenha.length < 8) {
            toast.error("A nova senha deve ter pelo menos 8 caracteres.");
            return;
        }

        setIsLoading(true);

        try {
            await apiFetch("/auth/me/change-password", {
                method: "POST",
                body: JSON.stringify({
                    senha_atual: senhaAtual,
                    nova_senha: novaSenha,
                    confirmar_senha: confirmarSenha,
                }),
            });

            toast.success("Senha alterada com sucesso!");
            setSenhaAtual("");
            setNovaSenha("");
            setConfirmarSenha("");
            onOpenChange(false);
        } catch (err: any) {
            const msg = err.message || "";
            if (msg.includes("Senha atual incorreta")) {
                toast.error("Senha atual incorreta.");
            } else if (msg.includes("coincidem")) {
                toast.error("As senhas não coincidem.");
            } else {
                toast.error(msg || "Erro ao alterar senha.");
            }
        } finally {
            setIsLoading(false);
        }
    };

    const handleOpenChange = (open: boolean) => {
        if (!isLoading) {
            setSenhaAtual("");
            setNovaSenha("");
            setConfirmarSenha("");
            onOpenChange(open);
        }
    };

    const senhasCoincidem = novaSenha === confirmarSenha && confirmarSenha.length > 0;

    return (
        <Dialog open={open} onOpenChange={handleOpenChange}>
            <DialogContent className="sm:max-w-md p-0 gap-0 overflow-hidden rounded-sm">
                <DialogHeader className="px-6 pt-6 pb-4 border-b">
                    <div className="flex items-center gap-2.5">
                        <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
                            <KeyRound className="size-4 text-primary" />
                        </div>
                        <div>
                            <DialogTitle className="text-base font-semibold">Alterar Senha</DialogTitle>
                            <DialogDescription className="text-xs text-muted-foreground">
                                Informe sua senha atual e defina uma nova senha com no mínimo 8 caracteres.
                            </DialogDescription>
                        </div>
                    </div>
                </DialogHeader>

                <form onSubmit={handleSubmit}>
                    <DialogBody className="space-y-4 px-6 py-4">
                        <div className="space-y-1.5">
                            <Label htmlFor="senha_atual" className="text-xs font-medium">Senha Atual</Label>
                            <PasswordInput
                                id="senha_atual"
                                value={senhaAtual}
                                onChange={(e) => setSenhaAtual(e.target.value)}
                                placeholder="••••••••"
                                required
                                disabled={isLoading}
                                className="h-8 text-xs rounded-sm"
                            />
                        </div>

                        <div className="space-y-1.5">
                            <Label htmlFor="nova_senha" className="text-xs font-medium">Nova Senha</Label>
                            <PasswordInput
                                id="nova_senha"
                                value={novaSenha}
                                onChange={(e) => setNovaSenha(e.target.value)}
                                placeholder="Mínimo 8 caracteres"
                                required
                                minLength={8}
                                disabled={isLoading}
                                className="h-8 text-xs rounded-sm"
                            />
                        </div>

                        <div className="space-y-1.5">
                            <Label htmlFor="confirmar_senha" className="text-xs font-medium">Confirmar Nova Senha</Label>
                            <PasswordInput
                                id="confirmar_senha"
                                value={confirmarSenha}
                                onChange={(e) => setConfirmarSenha(e.target.value)}
                                placeholder="Repita a nova senha"
                                required
                                minLength={8}
                                disabled={isLoading}
                                className={cn(
                                    "h-8 text-xs rounded-sm",
                                    !senhasCoincidem && confirmarSenha.length > 0 && "border-destructive"
                                )}
                            />
                            {!senhasCoincidem && confirmarSenha.length > 0 && (
                                <p className="text-[11px] text-destructive">As senhas não coincidem.</p>
                            )}
                        </div>
                    </DialogBody>

                    <DialogFooter className="px-6 py-3 border-t bg-muted/30">
                        <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="rounded-sm"
                            onClick={() => handleOpenChange(false)}
                            disabled={isLoading}
                        >
                            <X className="size-3.5 mr-1.5" />
                            Cancelar
                        </Button>
                        <Button
                            type="submit"
                            variant="outline"
                            size="sm"
                            className="rounded-sm border-primary/50 text-primary hover:bg-primary/10"
                            disabled={isLoading || !senhasCoincidem || novaSenha.length < 8}
                        >
                            {isLoading ? (
                                <Loader2 className="size-3.5 mr-1.5 animate-spin" />
                            ) : (
                                <Check className="size-3.5 mr-1.5" />
                            )}
                            {isLoading ? "Alterando..." : "Alterar Senha"}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
