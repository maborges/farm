"use client";

import { useState } from "react";
import { toast } from "sonner";
import { KeyRound, Loader2 } from "lucide-react";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch } from "@/lib/api";

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
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <KeyRound className="size-4" />
                        Alterar Senha
                    </DialogTitle>
                    <DialogDescription>
                        Informe sua senha atual e defina uma nova senha com no mínimo 8 caracteres.
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={handleSubmit}>
                    <div className="space-y-4 py-2">
                        <div className="space-y-1.5">
                            <Label htmlFor="senha_atual">Senha Atual</Label>
                            <Input
                                id="senha_atual"
                                type="password"
                                value={senhaAtual}
                                onChange={(e) => setSenhaAtual(e.target.value)}
                                placeholder="••••••••"
                                required
                                disabled={isLoading}
                            />
                        </div>

                        <div className="space-y-1.5">
                            <Label htmlFor="nova_senha">Nova Senha</Label>
                            <Input
                                id="nova_senha"
                                type="password"
                                value={novaSenha}
                                onChange={(e) => setNovaSenha(e.target.value)}
                                placeholder="Mínimo 8 caracteres"
                                required
                                minLength={8}
                                disabled={isLoading}
                            />
                        </div>

                        <div className="space-y-1.5">
                            <Label htmlFor="confirmar_senha">Confirmar Nova Senha</Label>
                            <Input
                                id="confirmar_senha"
                                type="password"
                                value={confirmarSenha}
                                onChange={(e) => setConfirmarSenha(e.target.value)}
                                placeholder="Repita a nova senha"
                                required
                                minLength={8}
                                disabled={isLoading}
                                className={!senhasCoincidem && confirmarSenha.length > 0 ? "border-destructive" : ""}
                            />
                            {!senhasCoincidem && confirmarSenha.length > 0 && (
                                <p className="text-xs text-destructive">As senhas não coincidem.</p>
                            )}
                        </div>
                    </div>

                    <div className="flex gap-2 justify-end pt-4 border-t">
                        <Button
                            type="button"
                            variant="ghost"
                            onClick={() => handleOpenChange(false)}
                            disabled={isLoading}
                        >
                            Cancelar
                        </Button>
                        <Button
                            type="submit"
                            disabled={isLoading || !senhasCoincidem || novaSenha.length < 8}
                        >
                            {isLoading && <Loader2 className="mr-2 size-4 animate-spin" />}
                            {isLoading ? "Alterando..." : "Alterar Senha"}
                        </Button>
                    </div>
                </form>
            </DialogContent>
        </Dialog>
    );
}
