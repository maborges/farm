"use client";

import { useState, useRef, useCallback } from "react";
import { useAppStore } from "@/lib/stores/app-store";
import { toast } from "sonner";
import { UserCircle, Lock, Loader2, Camera } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ChangePasswordDialog } from "@/components/layout/change-password-dialog";
import { apiFetch } from "@/lib/api";
import { resolveAssetUrl } from "@/lib/runtime-config";
import {
    Avatar,
    AvatarFallback,
    AvatarImage,
} from "@/components/ui/avatar";

/* ─── Máscaras ─── */

function formatCpf(value: string): string {
    const digits = value.replace(/\D/g, "").slice(0, 11);
    if (digits.length <= 3) return digits;
    if (digits.length <= 6) return `${digits.slice(0, 3)}.${digits.slice(3)}`;
    if (digits.length <= 9) return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6)}`;
    return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6, 9)}-${digits.slice(9)}`;
}

function formatPhone(value: string): string {
    const digits = value.replace(/\D/g, "").slice(0, 11);
    if (digits.length <= 2) return digits;
    if (digits.length <= 7) return `(${digits.slice(0, 2)}) ${digits.slice(2)}`;
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
}

function parseCpf(value: string): string {
    return value.replace(/\D/g, "");
}

function parsePhone(value: string): string {
    return value.replace(/\D/g, "");
}

/** Resolve URL relativa do backend para absoluta (para carregamento de imagens no browser). */
function resolveAvatarUrl(url: string | undefined): string | undefined {
    return resolveAssetUrl(url);
}

function buildAvatarSrc(url: string | undefined, cacheBust?: string): string | undefined {
    const resolved = resolveAvatarUrl(url);
    if (!resolved) {
        return undefined;
    }
    if (!cacheBust) {
        return resolved;
    }
    const base = resolved.split("?")[0];
    return `${base}?v=${encodeURIComponent(cacheBust)}`;
}

export default function AccountSettingsPage() {
    const { user, setSession, token, tenant, grupos, unidadesProdutivasAutorizadas, availableTenants } = useAppStore();
    const fileInputRef = useRef<HTMLInputElement>(null);

    const [nome, setNome] = useState(user?.name ?? "");
    const [apelido, setApelido] = useState(user?.nickname ?? "");
    const [cpf, setCpf] = useState(user?.cpf ? formatCpf(user.cpf) : "");
    const [telefone, setTelefone] = useState(user?.telefone ? formatPhone(user.telefone) : "");
    const [fotoUrl, setFotoUrl] = useState(resolveAvatarUrl(user?.foto_perfil_url) ?? "");
    const [isSaving, setIsSaving] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [showChangePassword, setShowChangePassword] = useState(false);

    const userInitial = (user?.name ?? "U").charAt(0).toUpperCase();
    const avatarSrc = buildAvatarSrc(fotoUrl || user?.foto_perfil_url, user?.foto_perfil_cache_bust);

    const handleAvatarUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        if (!file.type.startsWith("image/")) {
            toast.error("Selecione um arquivo de imagem.");
            return;
        }

        if (file.size > 5 * 1024 * 1024) {
            toast.error("A imagem deve ter no máximo 5MB.");
            return;
        }

        setIsUploading(true);
        try {
            const formData = new FormData();
            formData.append("file", file);

            const result = await apiFetch<{ url: string }>("/auth/me/avatar", {
                method: "POST",
                body: formData,
            });

            const fullUrl = resolveAvatarUrl(result.url) ?? result.url;
            const cacheBust = Date.now().toString();
            setFotoUrl(fullUrl);

            if (user) {
                useAppStore.setState((state) => ({
                    ...state,
                    user: {
                        ...state.user!,
                        foto_perfil_url: fullUrl || undefined,
                        foto_perfil_cache_bust: cacheBust,
                    },
                }));
            }

            toast.success("Foto atualizada com sucesso!");
        } catch (err: any) {
            toast.error(err.message || "Erro ao enviar foto.");
        } finally {
            setIsUploading(false);
            if (fileInputRef.current) {
                fileInputRef.current.value = "";
            }
        }
    }, []);

    const handleSave = async () => {
        if (!nome.trim()) {
            toast.error("O nome não pode estar vazio.");
            return;
        }
        if (!apelido.trim()) {
            toast.error("O apelido é obrigatório.");
            return;
        }

        setIsSaving(true);
        try {
            await apiFetch("/auth/me", {
                method: "PUT",
                body: JSON.stringify({
                    nome_completo: nome.trim(),
                    apelido: apelido.trim(),
                    telefone: parsePhone(telefone) || null,
                    foto_perfil_url: fotoUrl || null,
                }),
            });

            const updatedUser = user ? {
                ...user,
                name: nome.trim(),
                nickname: apelido.trim(),
                telefone: parsePhone(telefone) || undefined,
                foto_perfil_url: fotoUrl || undefined,
                foto_perfil_cache_bust: user.foto_perfil_cache_bust,
            } : null;

            setSession(
                token!,
                tenant,
                updatedUser,
                grupos,
                unidadesProdutivasAutorizadas,
                availableTenants
            );

            toast.success("Perfil atualizado com sucesso!");
        } catch (err: any) {
            toast.error(err.message || "Erro ao atualizar perfil.");
        } finally {
            setIsSaving(false);
        }
    };

    const hasChanges =
        nome.trim() !== (user?.name ?? "") ||
        apelido.trim() !== (user?.nickname ?? "") ||
        parsePhone(telefone) !== (user?.telefone ?? "") ||
        fotoUrl !== resolveAvatarUrl(user?.foto_perfil_url);

    return (
        <div className="p-8 space-y-8 w-full max-w-full">
            <PageHeader
                title="Meu Perfil"
                description="Gerencie os dados da sua conta de usuário."
            />

            <div className="max-w-2xl space-y-6">
                {/* Foto de Perfil */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <UserCircle className="size-5 text-primary" />
                            Foto de Perfil
                        </CardTitle>
                        <CardDescription>Sua imagem de identificação na plataforma.</CardDescription>
                    </CardHeader>
                    <CardContent className="flex items-center gap-6">
                        <div className="relative">
                            <Avatar className="size-20 border-2 border-border">
                                <AvatarImage
                                    src={avatarSrc}
                                    alt={userInitial}
                                    onError={(e) => {
                                        (e.target as HTMLImageElement).style.display = "none";
                                    }}
                                />
                                <AvatarFallback className="bg-primary/10 text-primary text-2xl font-bold">
                                    {userInitial}
                                </AvatarFallback>
                            </Avatar>
                            <button
                                type="button"
                                onClick={() => fileInputRef.current?.click()}
                                disabled={isUploading}
                                className="absolute bottom-0 right-0 size-6 rounded-full bg-background/90 backdrop-blur-sm ring-1 ring-border shadow-sm flex items-center justify-center hover:bg-accent transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                aria-label="Alterar foto de perfil"
                            >
                                {isUploading ? (
                                    <Loader2 className="size-3 animate-spin" />
                                ) : (
                                    <Camera className="size-3" />
                                )}
                            </button>
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept="image/jpeg,image/png,image/webp"
                                onChange={handleAvatarUpload}
                                className="hidden"
                            />
                        </div>
                        <div className="flex-1">
                            <p className="text-sm font-medium">Foto atual</p>
                            <p className="text-xs text-muted-foreground mt-1">
                                Clique no ícone de câmera para enviar uma nova imagem.
                                Formatos aceitos: JPG, PNG, WebP (máx. 5MB).
                            </p>
                        </div>
                    </CardContent>
                </Card>

                {/* Dados Pessoais */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <UserCircle className="size-5 text-primary" />
                            Dados Pessoais
                        </CardTitle>
                        <CardDescription>Informações básicas de sua conta.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-1.5">
                            <Label htmlFor="nome">Nome Completo</Label>
                            <Input
                                id="nome"
                                value={nome}
                                onChange={(e) => setNome(e.target.value)}
                                placeholder="Seu nome completo"
                            />
                        </div>

                        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                            <div className="space-y-1.5">
                                <Label htmlFor="username">ID do Usuário</Label>
                                <Input id="username" value={user?.username ?? ""} disabled />
                                <p className="text-xs text-muted-foreground">O ID do usuário não pode ser alterado.</p>
                            </div>
                            <div className="space-y-1.5">
                                <Label htmlFor="apelido">Apelido <span className="text-destructive">*</span></Label>
                                <Input
                                    id="apelido"
                                    value={apelido}
                                    onChange={(e) => setApelido(e.target.value.slice(0, 20))}
                                    placeholder="Como quer ser chamado"
                                    maxLength={20}
                                />
                            </div>
                        </div>

                        <div className="space-y-1.5">
                            <Label htmlFor="email">E-mail</Label>
                            <Input id="email" value={user?.email ?? ""} disabled />
                            <p className="text-xs text-muted-foreground">O e-mail não pode ser alterado por segurança.</p>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-1.5">
                                <Label htmlFor="cpf">CPF</Label>
                                <Input
                                    id="cpf"
                                    value={cpf}
                                    onChange={(e) => setCpf(formatCpf(e.target.value))}
                                    placeholder="000.000.000-00"
                                    disabled
                                />
                            </div>
                            <div className="space-y-1.5">
                                <Label htmlFor="telefone">Telefone</Label>
                                <Input
                                    id="telefone"
                                    value={telefone}
                                    onChange={(e) => setTelefone(formatPhone(e.target.value))}
                                    placeholder="(00) 00000-0000"
                                />
                            </div>
                        </div>

                        <div className="flex gap-2 justify-end pt-4 border-t">
                            <Button
                                onClick={handleSave}
                                disabled={isSaving || !hasChanges}
                            >
                                {isSaving && <Loader2 className="mr-2 size-4 animate-spin" />}
                                {isSaving ? "Salvando..." : "Salvar"}
                            </Button>
                        </div>
                    </CardContent>
                </Card>

                {/* Segurança */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Lock className="size-5 text-primary" />
                            Segurança
                        </CardTitle>
                        <CardDescription>Gerencie a segurança da sua conta.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        <button
                            type="button"
                            className="flex w-full items-center justify-between p-3 rounded-lg border bg-muted/50 transition-colors hover:bg-muted text-left"
                            onClick={() => setShowChangePassword(true)}
                        >
                            <div>
                                <p className="text-sm font-medium">Alterar Senha</p>
                                <p className="text-xs text-muted-foreground">Atualize sua senha regularmente para maior segurança.</p>
                            </div>
                            <span className="inline-flex items-center rounded-md border border-transparent px-3 py-1.5 text-sm font-medium text-primary hover:bg-background/60">
                                Alterar
                            </span>
                        </button>
                    </CardContent>
                </Card>
            </div>

            <ChangePasswordDialog open={showChangePassword} onOpenChange={setShowChangePassword} />
        </div>
    );
}
