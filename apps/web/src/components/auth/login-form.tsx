"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod/v4";
import { useAppStore } from "@/lib/stores/app-store";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Loader2, Mail, Lock, ArrowRight } from "lucide-react";
import Link from "next/link";
import { ThemeToggle } from "@/components/landing/ThemeToggle";

import { Button } from "@/components/ui/button";
import { Input, PasswordInput } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { Separator } from "@/components/ui/separator";
import { setAuthCookies, setContextCookies } from "@/app/actions/auth";
import { extractTenantContextsFromToken } from "@/lib/jwt";
import type { TenantRole, TenantSummary } from "@/types/global";
import { isStaleServerActionError } from "@/lib/server-action-errors";

const loginSchema = z.object({
    email: z.string().email({ message: "Insira um e-mail válido." }),
    password: z.string().min(6, { message: "A senha deve ter pelo menos 6 caracteres." }),
});

type LoginFormData = z.infer<typeof loginSchema>;

interface AuthProfileResponse {
    id: string;
    nome_completo: string;
    apelido?: string | null;
    email: string;
    username: string;
    cpf?: string | null;
    telefone?: string | null;
    foto_perfil_url?: string | null;
    is_superuser: boolean;
    tenants: TenantSummary[];
}

interface OnboardingStatusResponse {
    completo: boolean;
}

interface AuthTenantSummary extends TenantSummary {
    ativo?: boolean;
    activation_pending?: boolean;
}

interface ReenviarAtivacaoResponse {
    sucesso: boolean;
    mensagem: string;
}

type AuthProfileWithActivation = Omit<AuthProfileResponse, "tenants"> & {
    tenants: AuthTenantSummary[];
};

type TenantFazenda = AuthTenantSummary["fazendas"][number];

export function LoginForm() {
    const [isLoading, setIsLoading] = useState(false);
    const [isResendingActivation, setIsResendingActivation] = useState(false);
    const [pendingActivationEmail, setPendingActivationEmail] = useState<string | null>(null);
    const [submitError, setSubmitError] = useState<string | null>(null);
    const { setSession } = useAppStore();
    const router = useRouter();

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<LoginFormData>({
        resolver: zodResolver(loginSchema),
    });

    const onSubmit = async (data: LoginFormData) => {
        setIsLoading(true);
        setSubmitError(null);
        setPendingActivationEmail(null);

        const payload = {
            email: data.email.trim().toLowerCase(),
            senha: data.password,
        };

        try {
            const { access_token } = await apiFetch<{ access_token: string }>("/auth/login", {
                method: "POST",
                body: payload,
            });

            useAppStore.setState({ token: access_token });

            const profile = await apiFetch<AuthProfileWithActivation>("/auth/me");

            const isSuper = profile.is_superuser === true;
            const hasSingleTenant = !isSuper && profile.tenants.length === 1;
            const defaultTenant = hasSingleTenant ? profile.tenants[0] : null;

            if (!isSuper && defaultTenant?.activation_pending) {
                useAppStore.setState({ token: null });
                const friendlyMessage = "Seu cadastro ainda não foi confirmado. Reenvie o e-mail de confirmação e conclua a validação antes de entrar.";
                setPendingActivationEmail(payload.email);
                setSubmitError(friendlyMessage);
                toast.error("Confirmação pendente", {
                    description: friendlyMessage,
                    duration: 8000,
                });
                return;
            }

            await setAuthCookies(access_token);

            await setAuthCookies(
                access_token,
                defaultTenant?.tenant_id,
                defaultTenant?.fazendas?.[0]?.unidade_produtiva_id
            );

            const grupos = extractTenantContextsFromToken(access_token);

            setSession(
                access_token,
                defaultTenant ? {
                    id: defaultTenant.tenant_id,
                    nome: defaultTenant.nome_tenant,
                    documento: "",
                    slug: "",
                    dominio_customizado: null,
                    branding: { primaryColor: "154 100% 21%" }
                } : null,
                {
                    id: profile.id,
                    name: profile.nome_completo,
                    nickname: profile.apelido ?? undefined,
                    email: profile.email,
                    username: profile.username,
                    cpf: profile.cpf,
                    telefone: profile.telefone,
                    foto_perfil_url: profile.foto_perfil_url,
                    is_superuser: profile.is_superuser,
                    tenant_role: defaultTenant?.is_owner
                        ? "owner"
                        : ((defaultTenant?.perfil?.nome?.toLowerCase() as TenantRole | undefined) ?? undefined),
                    custom_permissions: defaultTenant?.perfil?.permissoes ?? undefined,
                },
                grupos,
                defaultTenant ? defaultTenant.fazendas.map((f: TenantFazenda) => ({
                    id: f.unidade_produtiva_id,
                    nome: f.nome,
                    tenant_id: defaultTenant.tenant_id,
                    tipo_propriedade: null,
                    cpf_cnpj: null,
                    inscricao_estadual: null,
                    codigo_car: null,
                    nirf: null,
                    ccir: null,
                    sigef_codigo: null,
                    cep: null,
                    logradouro: null,
                    numero: null,
                    complemento: null,
                    bairro: null,
                    municipio: null,
                    uf: null,
                    ibge_municipio_codigo: null,
                    area_total_ha: null,
                    area_app_ha: null,
                    area_rl_ha: null,
                    coordenadas_sede: null,
                    geometria: null,
                    logo_url: null,
                    ativo: true,
                    numero_matricula: null,
                    area_total_calculada_ha: null,
                    created_at: "",
                    updated_at: "",
                    role: defaultTenant.perfil?.nome ?? "operador"
                })) : [],
                profile.tenants,
            );

            // Uma nova autenticação não deve herdar o tempo ocioso da sessão anterior.
            localStorage.setItem("agrosaas-last-activity", String(Date.now()));

            if (!isSuper && profile.tenants.length > 1) {
                await setContextCookies(undefined, null);
                router.replace("/selecionar-tenant");
                return;
            }

            let nextRoute = "/dashboard";

            if (!profile.is_superuser && defaultTenant) {
                try {
                    const onboardingStatus = await apiFetch<OnboardingStatusResponse>("/onboarding/status", {
                        suppressErrorLog: true,
                    });

                    if (!onboardingStatus.completo) {
                        nextRoute = "/dashboard/implantacao/wizard";
                    } else {
                        try {
                            await apiFetch("/wizard/status", {
                                suppressErrorLog: true,
                            });
                        } catch (wizardError: unknown) {
                            const wizardMessage = wizardError instanceof Error ? wizardError.message : "";
                            if (
                                wizardMessage.includes("Implantacao ativa nao encontrada para o tenant.") ||
                                wizardMessage.includes("Implantação ativa não encontrada para o tenant.")
                            ) {
                                nextRoute = "/dashboard/implantacao/wizard";
                            }
                        }
                    }
                } catch {
                    // Se a consulta falhar, o guard do dashboard ainda protege o fluxo.
                }
            }

            router.replace(nextRoute);
            router.refresh();

        } catch (error: unknown) {
            console.error("Erro no login:", error);

            if (isStaleServerActionError(error)) {
                const friendlyMessage = "A página foi atualizada. Clique em ‘Atualizar página’ para continuar.";
                setSubmitError(friendlyMessage);
                toast.error("A página precisa ser atualizada", {
                    description: "O sistema foi atualizado enquanto esta página estava aberta.",
                    action: {
                        label: "Atualizar página",
                        onClick: () => window.location.reload(),
                    },
                    duration: Infinity,
                });
                return;
            }

            const msg: string = error instanceof Error ? error.message : "Erro inesperado ao autenticar.";
            const lowerMsg = msg.toLowerCase();

            if (lowerMsg.includes("bloqueada") || lowerMsg.includes("bloqueado") || msg.includes("423") || lowerMsg.includes("tente novamente")) {
                const friendlyMessage = msg.includes("minuto")
                    ? msg
                    : "Muitas tentativas incorretas. Aguarde 15 minutos antes de tentar novamente.";
                setSubmitError(friendlyMessage);
                toast.error("🔒 Acesso Temporariamente Bloqueado", {
                    description: friendlyMessage,
                    duration: 12000,
                });
            } else if (lowerMsg.includes("inativo") || lowerMsg.includes("suspenso")) {
                const friendlyMessage = "Seu cadastro ainda não foi confirmado. Reenvie o e-mail de confirmação e conclua a validação antes de entrar.";
                setPendingActivationEmail(payload.email);
                setSubmitError(friendlyMessage);
                toast.error("Confirmação pendente", {
                    description: friendlyMessage,
                    duration: 8000,
                });
            } else if (
                lowerMsg.includes("email ou senha incorretos") ||
                lowerMsg.includes("credenciais inválidas") ||
                lowerMsg.includes("unauthorized") ||
                lowerMsg.includes("401")
            ) {
                const friendlyMessage = "E-mail ou senha incorretos. Verifique seus dados e tente novamente.";
                setSubmitError(friendlyMessage);
                toast.error("Credenciais inválidas", {
                    description: friendlyMessage,
                    duration: 5000,
                });
            } else if (lowerMsg.includes("internal server error") || msg.includes("500")) {
                const friendlyMessage = "Ocorreu um erro interno no servidor. Nossa equipe já foi notificada. Por favor, tente novamente em instantes.";
                setSubmitError(friendlyMessage);
                // O toast global do apiFetch já exibirá a notificação de erro 500
            } else {
                setSubmitError(msg);
                toast.error("Falha ao entrar", {
                    description: msg,
                    duration: 7000,
                });
            }
        } finally {
            setIsLoading(false);
        }
    };

    const handleResendActivation = async () => {
        if (!pendingActivationEmail) {
            return;
        }

        setIsResendingActivation(true);
        try {
            const response = await apiFetch<ReenviarAtivacaoResponse>("/onboarding/ativacao/reenviar", {
                method: "POST",
                body: { email: pendingActivationEmail },
            });
            toast.success(response.mensagem);
        } catch (error: unknown) {
            const message = error instanceof Error ? error.message : "Não foi possível reenviar o e-mail de confirmação.";
            toast.error(message);
        } finally {
            setIsResendingActivation(false);
        }
    };

    return (
        <div className="space-y-5 relative">
            {/* Cabeçalho */}
            <div className="flex items-start justify-between gap-4">
                <div className="space-y-1">
                    <h2 className="text-2xl font-light tracking-tight text-foreground">
                        Bem-vindo de volta
                    </h2>
                    <p className="text-sm text-muted-foreground font-medium">
                        Entre com suas credenciais para acessar a plataforma.
                    </p>
                </div>
                <div className="shrink-0 mt-1">
                    <ThemeToggle />
                </div>
            </div>

            {/* Formulário */}
            <form method="post" onSubmit={handleSubmit(onSubmit)} className="space-y-4" data-testid="login-form">
                {submitError && (
                    <div className="space-y-2 rounded-sm border border-destructive/20 bg-destructive/8 px-3 py-2 text-xs font-medium text-destructive">
                        <div>{submitError}</div>
                        {pendingActivationEmail ? (
                            <Button
                                type="button"
                                variant="destructive"
                                size="sm"
                                disabled={isResendingActivation}
                                onClick={handleResendActivation}
                                className="h-8"
                            >
                                {isResendingActivation ? (
                                    <span className="flex items-center gap-2">
                                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                        Reenviando...
                                    </span>
                                ) : (
                                    "Reenviar e-mail de confirmação"
                                )}
                            </Button>
                        ) : null}
                    </div>
                )}

                {/* E-mail */}
                <div className="space-y-1.5">
                    <Label htmlFor="email" className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                        E-mail de Acesso
                    </Label>
                    <div className="relative">
                        <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-primary/70 pointer-events-none" />
                        <Input
                            id="email"
                            {...register("email")}
                            type="email"
                            placeholder="seu@email.com.br"
                            autoComplete="email"
                            disabled={isLoading}
                            data-testid="email-input"
                            className="pl-9"
                        />
                    </div>
                    {errors.email && (
                        <p className="text-[10px] font-bold text-destructive animate-in slide-in-from-top-1 px-1">
                            {errors.email.message}
                        </p>
                    )}
                </div>

                {/* Senha */}
                <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                        <Label htmlFor="password" className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                            Senha
                        </Label>
                        <Link href="/forgot-password" hidden={isLoading} className="text-[10px] font-bold text-primary/70 hover:text-primary transition-colors">
                            Esqueceu a senha?
                        </Link>
                    </div>
                    <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-primary/70 pointer-events-none z-10" />
                        <PasswordInput
                            id="password"
                            {...register("password")}
                            placeholder="••••••••"
                            autoComplete="current-password"
                            disabled={isLoading}
                            data-testid="password-input"
                            className="pl-9"
                        />
                    </div>
                    {errors.password && (
                        <p className="text-[10px] font-bold text-destructive animate-in slide-in-from-top-1 px-1">
                            {errors.password.message}
                        </p>
                    )}
                </div>

                {/* Botão de envio */}
                <Button
                    type="submit"
                    variant="default"
                    size="sm"
                    disabled={isLoading}
                    data-testid="login-button"
                    className="w-full mt-2 group"
                >
                    {isLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                        <span className="flex items-center gap-2 uppercase tracking-widest text-[10px] font-semibold">
                            Entrar na plataforma
                            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                        </span>
                    )}
                </Button>
            </form>

            {/* Divisor */}
            <div className="relative">
                <div className="absolute inset-0 flex items-center">
                    <Separator className="w-full" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-background px-2 text-muted-foreground/50">
                        ou continuar com
                    </span>
                </div>
            </div>

            {/* Rodapé */}
            <p className="text-center text-sm text-muted-foreground/60">
                Não tem uma conta?{" "}
                <Link
                    href="/register"
                    className="text-primary font-semibold hover:underline transition-all"
                >
                    Solicitar acesso
                </Link>
            </p>
        </div>
    );
}
