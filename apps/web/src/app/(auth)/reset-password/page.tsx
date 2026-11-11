"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod/v4";
import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
    Loader2, Lock, CheckCircle2, XCircle, ArrowLeft, Mail, KeyRound,
} from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Input, PasswordInput } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthLayout } from "@/components/auth/auth-layout";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";

// ---------------------------------------------------------------------------
// Schema de validação
// ---------------------------------------------------------------------------

const resetPasswordSchema = z
    .object({
        nova_senha: z
            .string()
            .min(6, { message: "A senha deve ter pelo menos 6 caracteres." }),
        confirmar_senha: z.string(),
    })
    .refine((data) => data.nova_senha === data.confirmar_senha, {
        message: "As senhas não coincidem.",
        path: ["confirmar_senha"],
    });

type ResetPasswordFormData = z.infer<typeof resetPasswordSchema>;

// ---------------------------------------------------------------------------
// Estado de token inválido
// ---------------------------------------------------------------------------

function TokenInvalidoState() {
    return (
        <div className="space-y-6">
            <div className="space-y-1">
                <div className="flex items-center gap-2">
                    <XCircle className="h-5 w-5 text-destructive" />
                    <h2 className="text-2xl font-black tracking-tight text-foreground">
                        Token inválido
                    </h2>
                </div>
                <p className="text-sm text-muted-foreground">
                    Este link de recuperação não é mais válido ou já foi utilizado.
                </p>
            </div>

            <div className="rounded-sm border border-destructive/20 bg-destructive/5 p-4">
                <p className="text-sm text-muted-foreground">
                    Solicite um novo link de recuperação para redefinir sua senha.
                </p>
            </div>

            <div className="space-y-2">
                <Button
                    asChild
                    variant="outline"
                    size="sm"
                    className="w-full"
                >
                    <Link href="/forgot-password">
                        <Mail className="h-4 w-4" />
                        Solicitar novo link
                    </Link>
                </Button>

                <Button
                    asChild
                    variant="ghost"
                    size="sm"
                    className="w-full rounded-sm text-muted-foreground hover:text-foreground"
                >
                    <Link href="/login">
                        <ArrowLeft className="h-4 w-4" />
                        Voltar para o login
                    </Link>
                </Button>
            </div>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Estado de sucesso
// ---------------------------------------------------------------------------

function SenhaRedefenidaState() {
    return (
        <div className="space-y-6">
            <div className="space-y-1">
                <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5 text-primary" />
                    <h2 className="text-2xl font-black tracking-tight text-foreground">
                        Senha redefinida!
                    </h2>
                </div>
                <p className="text-sm text-muted-foreground">
                    Sua senha foi atualizada com sucesso.
                </p>
            </div>

            <div className="rounded-sm border border-primary/20 bg-primary/5 p-4">
                <div className="flex items-start gap-3">
                    <div className="flex size-8 shrink-0 items-center justify-center rounded-sm bg-primary/10 border border-primary/20">
                        <CheckCircle2 className="h-4 w-4 text-primary" />
                    </div>
                    <div className="space-y-0.5">
                        <p className="text-sm font-medium text-foreground">
                            Pronto para acessar
                        </p>
                        <p className="text-xs text-muted-foreground">
                            Use sua nova senha para entrar na plataforma.
                        </p>
                    </div>
                </div>
            </div>

            <Button
                asChild
                variant="outline"
                size="sm"
                className="w-full"
            >
                <Link href="/login">
                    <ArrowLeft className="h-4 w-4" />
                    Fazer login
                </Link>
            </Button>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Formulário principal
// ---------------------------------------------------------------------------

function ResetPasswordFormContent() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const token = searchParams.get("token");

    const [isLoading, setIsLoading] = useState(false);
    const [isVerifying, setIsVerifying] = useState(true);
    const [tokenValid, setTokenValid] = useState(false);
    const [tokenInfo, setTokenInfo] = useState<{
        email: string;
        expira_em: string;
    } | null>(null);
    const [passwordReset, setPasswordReset] = useState(false);

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<ResetPasswordFormData>({
        resolver: zodResolver(resetPasswordSchema),
    });

    useEffect(() => {
        if (!token) {
            setIsVerifying(false);
            toast.error("Token de recuperação não encontrado.");
            return;
        }

        const verifyToken = async () => {
            try {
                const resultado = await apiFetch<{
                    valido: boolean;
                    email: string;
                    expira_em: string;
                    mensagem?: string;
                }>("/auth/verify-reset-token", {
                    method: "POST",
                    body: JSON.stringify({ token }),
                });

                if (resultado.valido) {
                    setTokenValid(true);
                    setTokenInfo({
                        email: resultado.email,
                        expira_em: resultado.expira_em,
                    });
                } else {
                    setTokenValid(false);
                    if (resultado.mensagem) toast.error(resultado.mensagem);
                }
            } catch (error: unknown) {
                setTokenValid(false);
                const msg =
                    error instanceof Error ? error.message : "Erro ao verificar token.";
                toast.error(msg);
            } finally {
                setIsVerifying(false);
            }
        };

        verifyToken();
    }, [token]);

    const onSubmit = async (data: ResetPasswordFormData) => {
        if (!token) {
            toast.error("Token de recuperação não encontrado.");
            return;
        }

        setIsLoading(true);

        try {
            await apiFetch("/auth/reset-password", {
                method: "POST",
                body: JSON.stringify({
                    token,
                    nova_senha: data.nova_senha,
                    confirmar_senha: data.confirmar_senha,
                }),
            });

            setPasswordReset(true);
            toast.success("Senha redefinida com sucesso!");

            setTimeout(() => router.replace("/login"), 2500);
        } catch (error: unknown) {
            const msg =
                error instanceof Error ? error.message : "Erro ao redefinir senha.";
            toast.error(msg);
        } finally {
            setIsLoading(false);
        }
    };

    // ── Carregando ────────────────────────────────────────────────
    if (isVerifying) {
        return (
            <div className="space-y-6">
                <div className="space-y-1">
                    <h2 className="text-2xl font-black tracking-tight text-foreground">
                        Verificando link...
                    </h2>
                    <p className="text-sm text-muted-foreground">
                        Estamos validando seu link de recuperação.
                    </p>
                </div>
                <div className="flex flex-col items-center justify-center py-10 gap-3">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                    <p className="text-sm text-muted-foreground">Aguarde um momento...</p>
                </div>
            </div>
        );
    }

    // ── Token inválido ────────────────────────────────────────────
    if (!tokenValid) return <TokenInvalidoState />;

    // ── Sucesso ───────────────────────────────────────────────────
    if (passwordReset) return <SenhaRedefenidaState />;

    // ── Formulário ────────────────────────────────────────────────
    return (
        <div className="space-y-6">
            {/* Cabeçalho */}
            <div className="space-y-1">
                <h2 className="text-2xl font-black tracking-tight text-foreground">
                    Redefina sua senha
                </h2>

                {tokenInfo && (
                    <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm text-muted-foreground">
                            Conta:{" "}
                            <strong className="text-foreground">{tokenInfo.email}</strong>
                        </p>
                        {tokenInfo.expira_em && (
                            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-sm bg-amber-500/10 border border-amber-500/20 text-amber-600 dark:text-amber-400">
                                Expira em {tokenInfo.expira_em}
                            </span>
                        )}
                    </div>
                )}
            </div>

            {/* Formulário */}
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">

                {/* Nova senha */}
                <div className="space-y-1.5">
                    <Label
                        htmlFor="nova_senha"
                        className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider"
                    >
                        Nova senha
                    </Label>
                    <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-primary/70 pointer-events-none z-10" />
                        <PasswordInput
                            id="nova_senha"
                            {...register("nova_senha")}
                            placeholder="Digite sua nova senha"
                            autoComplete="new-password"
                            disabled={isLoading}
                            className="pl-9"
                        />
                    </div>
                    {errors.nova_senha && (
                        <p className="text-[10px] font-bold text-destructive animate-in slide-in-from-top-1 px-1">
                            {errors.nova_senha.message}
                        </p>
                    )}
                </div>

                {/* Confirmar senha */}
                <div className="space-y-1.5">
                    <Label
                        htmlFor="confirmar_senha"
                        className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider"
                    >
                        Confirmar senha
                    </Label>
                    <div className="relative">
                        <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-primary/70 pointer-events-none z-10" />
                        <PasswordInput
                            id="confirmar_senha"
                            {...register("confirmar_senha")}
                            placeholder="Confirme sua nova senha"
                            autoComplete="new-password"
                            disabled={isLoading}
                            className="pl-9"
                        />
                    </div>
                    {errors.confirmar_senha && (
                        <p className="text-[10px] font-bold text-destructive animate-in slide-in-from-top-1 px-1">
                            {errors.confirmar_senha.message}
                        </p>
                    )}
                </div>

                {/* Submit */}
                <Button
                    type="submit"
                    variant="default"
                    size="sm"
                    disabled={isLoading}
                    className="w-full mt-2 group"
                >
                    {isLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                        <span className="flex items-center gap-2 uppercase tracking-widest text-[10px] font-black">
                            Redefinir senha
                        </span>
                    )}
                </Button>
            </form>

            {/* Voltar */}
            <Button
                asChild
                variant="ghost"
                size="sm"
                className="w-full rounded-sm text-muted-foreground hover:text-foreground"
            >
                <Link href="/login">
                    <ArrowLeft className="h-4 w-4" />
                    Voltar para o login
                </Link>
            </Button>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Page export
// ---------------------------------------------------------------------------

export default function ResetPasswordPage() {
    return (
        <AuthLayout
            badgeLabel="Redefinição de Senha"
            title="Redefina sua senha com segurança."
            description="Crie uma nova senha forte para proteger sua conta na plataforma DeepFarms."
        >
            <Suspense
                fallback={
                    <div className="flex flex-col items-center justify-center py-10 gap-3">
                        <Loader2 className="h-8 w-8 animate-spin text-primary" />
                        <p className="text-sm text-muted-foreground">Carregando...</p>
                    </div>
                }
            >
                <ResetPasswordFormContent />
            </Suspense>
        </AuthLayout>
    );
}
