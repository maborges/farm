"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { isApiError } from "@/lib/api-error";
import { useAppStore } from "@/lib/stores/app-store";
import { Loader2, CheckCircle2, XCircle, Sprout, ArrowRight, UserPlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input, PasswordInput } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { AuthLayout } from "@/components/auth/auth-layout";

interface InviteDetails {
    tenant_nome: string;
    perfil_nome: string;
    email_convidado: string;
    expira_em: string;
    fazendas: string[];
    usuario_existe: boolean;
    is_demo?: boolean;
}

function AcceptInviteContent() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const queryClient = useQueryClient();
    const currentUser = useAppStore((state) => state.user);
    
    const [status, setStatus] = useState<"loading" | "details" | "register" | "success" | "error">("loading");
    const [invite, setInvite] = useState<InviteDetails | null>(null);
    const [message, setMessage] = useState("");
    const [isProcessing, setIsProcessing] = useState(false);

    // Register form state
    const [nome, setNome] = useState("");
    const [telefone, setTelefone] = useState("");
    const [empresa, setEmpresa] = useState("");
    const [senha, setSenha] = useState("");
    const [senhaConfirm, setSenhaConfirm] = useState("");
    const inviteToken = searchParams.get("token");
    const currentUserMatchesInvite = Boolean(
        currentUser?.email && invite?.email_convidado &&
        currentUser.email.trim().toLowerCase() === invite.email_convidado.trim().toLowerCase()
    );

    // 1. Buscar detalhes do convite ao carregar
    useEffect(() => {
        if (!inviteToken) {
            setStatus("error");
            setMessage("O link de convite é inválido ou está corrompido.");
            return;
        }

        const fetchDetails = async () => {
            try {
                const data = await apiFetch<InviteDetails>(`/onboarding/convites/${inviteToken}`);
                setInvite(data);
                // A existência da conta do e-mail convidado é a referência; um token
                // de outra conta neste navegador não deve pular o cadastro.
                if (!data.usuario_existe) {
                    setStatus("register");
                } else {
                    setStatus("details");
                }
            } catch (error: any) {
                setStatus("error");
                setMessage(error.message || "Este convite expirou ou não é mais válido.");
            }
        };

        fetchDetails();
    }, [inviteToken]);

    const handleAccept = async () => {
        setIsProcessing(true);
        try {
            await apiFetch<any>(`/onboarding/convites/aceitar?token=${inviteToken}`, {
                method: "POST"
            });
            // O convite libera um novo tenant para a conta convidada — invalida o cache
            // do switcher (staleTime de 2min) para refletir sem precisar de reload manual
            // caso o usuário já esteja logado com essa conta em outra aba.
            queryClient.invalidateQueries({ queryKey: ["my-tenants"] });
            queryClient.invalidateQueries({ queryKey: ["auth-me-tenants"] });
            setStatus("success");
            setMessage("Convite aceito! Faça login para acessar.");
            toast.success("Convite aceito com sucesso!");
        } catch (error: any) {
            if (
                isApiError(error) &&
                error.status === 404 &&
                error.detail === "Nenhuma conta encontrada para este e-mail. Cadastre-se primeiro."
            ) {
                setStatus("register");
                toast.info("Crie sua conta para concluir o convite.");
                return;
            }
            toast.error(error.message || "Erro ao aceitar convite.");
            setStatus("error");
            setMessage(error.message || "Não foi possível aceitar este convite.");
        } finally {
            setIsProcessing(false);
        }
    };

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        if (senha !== senhaConfirm) {
            toast.error("As senhas não coincidem.");
            return;
        }
        if (senha.length < 8) {
            toast.error("A senha deve ter pelo menos 8 caracteres.");
            return;
        }

        setIsProcessing(true);
        try {
            await apiFetch<{ access_token: string }>("/onboarding/convites/registrar", {
                method: "POST",
                body: JSON.stringify({
                    token: inviteToken,
                    senha,
                    nome_completo: nome || undefined,
                    telefone: telefone.trim() || undefined,
                    empresa: empresa.trim() || undefined,
                }),
            });

            setStatus("success");
            setMessage("Conta criada com sucesso! Faça login para entrar.");
            toast.success("Conta criada! Redirecionando para o login...");
            setTimeout(() => router.push(`/login?email=${encodeURIComponent(invite!.email_convidado)}`), 1800);
        } catch (error: unknown) {
            if (isApiError(error) && error.status === 429) {
                setStatus("success");
                setMessage(error.message);
                toast.warning("Conta criada com aviso de acesso simultâneo", {
                    description: error.message,
                    duration: 9000,
                });
                return;
            }
            const errMsg = error instanceof Error ? error.message : "Erro ao criar conta.";
            toast.error(errMsg);
        } finally {
            setIsProcessing(false);
        }
    };

    // Renderização baseada no status
    return (
        <div className="w-full max-w-[420px] animate-in fade-in zoom-in duration-500">
            {/* Cabeçalho de Logo */}
                <div className="flex flex-col items-center mb-8 gap-3">
                    <div className="flex size-11 items-center justify-center rounded-sm bg-primary border border-primary/20 shadow-lg shadow-primary/20 transition-all duration-300">
                        <Sprout className="size-6 text-primary-foreground" />
                    </div>
                </div>

                <Card className="rounded-sm border-border bg-card/75 backdrop-blur-md shadow-premium p-8 relative overflow-hidden group">
                    {/* Linha de acento no topo */}
                    <div className="absolute top-0 left-0 w-full h-[1.5px] bg-gradient-to-r from-transparent via-primary/40 to-transparent" />
                    
                    {status === "loading" && (
                        <div className="flex flex-col items-center py-8 gap-4 text-center">
                            <Loader2 className="size-10 animate-spin text-primary" />
                            <p className="text-sm text-muted-foreground font-medium animate-pulse">Autenticando convite no sistema...</p>
                        </div>
                    )}

                    {status === "details" && invite && (
                        <div className="space-y-6">
                            <div className="space-y-2 text-center">
                                <Badge variant="outline" className="bg-primary/5 border-primary/20 text-primary text-[10px] uppercase font-black tracking-widest px-2 py-0.5">
                                    Acesso Autorizado
                                </Badge>
                                <h3 className="text-2xl font-black text-foreground leading-tight tracking-tight">
                                    Convite Recebido
                                </h3>
                                <p className="text-sm text-muted-foreground">
                                    Você foi convidado para integrar a equipe.
                                </p>
                            </div>

                            <div className="space-y-4 py-4 border-y border-border/10">
                                <div className="flex justify-between items-center text-sm">
                                    <span className="text-muted-foreground font-medium">Organização</span>
                                    <span className="text-foreground font-bold">{invite.tenant_nome}</span>
                                </div>
                                <div className="flex justify-between items-center text-sm">
                                    <span className="text-muted-foreground font-medium">Perfil de Acesso</span>
                                    <Badge variant="secondary" className="bg-secondary text-secondary-foreground font-bold border-border">
                                        {invite.perfil_nome}
                                    </Badge>
                                </div>
                                {invite.fazendas.length > 0 && (
                                    <div className="space-y-2">
                                        <span className="text-[10px] text-muted-foreground uppercase font-black tracking-widest">Unidades de Produção</span>
                                        <div className="flex flex-wrap gap-1.5">
                                            {invite.fazendas.map((f) => (
                                                <Badge key={f} variant="ghost" className="bg-primary/5 text-primary text-[10px] font-bold border-primary/10">
                                                    {f}
                                                </Badge>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div className="space-y-4 pt-2">
                                <p className="text-xs text-muted-foreground text-center leading-relaxed">
                                    O acesso será vinculado à conta de <span className="font-semibold text-foreground">{invite.email_convidado}</span>. Você poderá entrar com essa conta em seguida.
                                </p>
                                <Button
                                    disabled={isProcessing}
                                    className="w-full h-10 bg-primary hover:bg-primary/90 text-primary-foreground font-black uppercase tracking-widest text-xs border-0 shadow-lg shadow-primary/20 group"
                                    onClick={handleAccept}
                                >
                                    {isProcessing ? (
                                        <Loader2 className="animate-spin size-4" />
                                    ) : (
                                        <>
                                            Aceitar Convite
                                            <ArrowRight size={16} className="ml-2 group-hover:translate-x-1 transition-transform" />
                                        </>
                                    )}
                                </Button>
                            </div>
                        </div>
                    )}

                    {status === "register" && invite && (
                        <form onSubmit={handleRegister} className="space-y-5">
                            <div className="space-y-2 text-center">
                                <div className="flex flex-wrap items-center justify-center gap-1.5">
                                    <Badge variant="outline" className="bg-primary/5 border-primary/20 text-primary text-[10px] uppercase font-black tracking-widest px-2 py-0.5">
                                        Concluir Onboarding
                                    </Badge>
                                    {invite.is_demo && (
                                        <Badge variant="outline" className="bg-amber-500/10 border-amber-500/30 text-amber-700 dark:text-amber-300 text-[10px] uppercase font-black tracking-widest px-2 py-0.5">
                                            Demonstração · 15 dias
                                        </Badge>
                                    )}
                                </div>
                                <h3 className="text-2xl font-black text-foreground leading-tight tracking-tight">
                                    Criar sua conta
                                </h3>
                                <p className="text-xs text-muted-foreground leading-relaxed">
                                    Registre-se em <span className="text-foreground font-semibold">{invite.tenant_nome}</span> para começar.
                                </p>
                            </div>

                            <div className="space-y-1.5">
                                <Label htmlFor="reg-email" className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">E-mail Corporativo</Label>
                                <Input id="reg-email" value={invite.email_convidado} disabled className="opacity-60 grayscale cursor-not-allowed" />
                            </div>

                            <div className="space-y-1.5">
                                <Label htmlFor="reg-nome" className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider text-primary">Nome Completo</Label>
                                <Input
                                    id="reg-nome"
                                    placeholder="Como quer ser chamado?"
                                    value={nome}
                                    onChange={(e) => setNome(e.target.value)}
                                />
                            </div>

                            {invite.is_demo && (
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div className="space-y-1.5">
                                        <Label htmlFor="reg-telefone" className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                                            Telefone / WhatsApp <span className="font-normal normal-case">(opcional)</span>
                                        </Label>
                                        <Input
                                            id="reg-telefone"
                                            placeholder="(00) 00000-0000"
                                            value={telefone}
                                            onChange={(e) => setTelefone(e.target.value)}
                                        />
                                    </div>
                                    <div className="space-y-1.5">
                                        <Label htmlFor="reg-empresa" className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                                            Fazenda / Empresa <span className="font-normal normal-case">(opcional)</span>
                                        </Label>
                                        <Input
                                            id="reg-empresa"
                                            placeholder="Ex: Fazenda Boa Vista"
                                            value={empresa}
                                            onChange={(e) => setEmpresa(e.target.value)}
                                        />
                                    </div>
                                </div>
                            )}

                            <div className="grid grid-cols-2 gap-3">
                                <div className="space-y-1.5">
                                    <Label htmlFor="reg-senha" className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Senha</Label>
                                    <PasswordInput
                                        id="reg-senha"
                                        placeholder="Sua senha"
                                        value={senha}
                                        onChange={(e) => setSenha(e.target.value)}
                                        required
                                    />
                                </div>

                                <div className="space-y-1.5">
                                    <Label htmlFor="reg-confirm" className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Repetir Senha</Label>
                                    <PasswordInput
                                        id="reg-confirm"
                                        placeholder="Confirme"
                                        value={senhaConfirm}
                                        onChange={(e) => setSenhaConfirm(e.target.value)}
                                        required
                                    />
                                </div>
                            </div>

                            <Button
                                type="submit"
                                disabled={isProcessing}
                                className="w-full h-10 bg-primary hover:bg-primary/90 text-primary-foreground font-black uppercase tracking-widest text-xs border-0 shadow-lg shadow-primary/20 group"
                            >
                                {isProcessing ? (
                                    <Loader2 className="animate-spin size-4" />
                                ) : (
                                    <>
                                        <UserPlus size={14} className="mr-2" />
                                        Confirmar Registro
                                        <ArrowRight size={14} className="ml-2 group-hover:translate-x-1 transition-transform" />
                                    </>
                                )}
                            </Button>

                            <p className="text-center text-[11px] text-muted-foreground">
                                Você poderá adicionar uma foto de perfil depois de entrar.
                            </p>

                            <p className="text-center text-[11px] text-muted-foreground">
                                Já possui conta?{" "}
                                <button type="button" className="text-primary font-bold hover:underline" onClick={() => router.push(`/login?redirect=/convite/aceitar?token=${inviteToken}`)}>
                                    Realizar Login
                                </button>
                            </p>
                        </form>
                    )}

                    {status === "success" && (
                        <div className="flex flex-col items-center text-center py-6 space-y-6">
                            <div className="size-20 rounded-full bg-primary/10 flex items-center justify-center border border-primary/20">
                                <CheckCircle2 className="size-10 text-primary shadow-sm" />
                            </div>
                            <div className="space-y-2">
                                 <h3 className="text-2xl font-black text-foreground tracking-tight">Sucesso Total!</h3>
                                 <p className="text-sm text-muted-foreground leading-relaxed max-w-[280px]">
                                    {message} Seu perfil foi atualizado com as novas permissões.
                                 </p>
                            </div>
                            <Button
                                className="w-full h-10 bg-primary text-primary-foreground font-black uppercase tracking-widest text-xs hover:bg-primary/90 shadow-primary/20 shadow-xl transition-all"
                                onClick={() => router.push(currentUserMatchesInvite ? "/dashboard" : `/login?email=${encodeURIComponent(invite?.email_convidado ?? "")}`)}
                            >
                                {currentUserMatchesInvite ? "Ir para o Painel Inicial" : "Fazer Login"}
                            </Button>
                        </div>
                    )}

                    {status === "error" && (
                        <div className="flex flex-col items-center text-center py-6 space-y-6">
                             <div className="size-20 rounded-full bg-destructive/10 flex items-center justify-center border border-destructive/20">
                                <XCircle className="size-10 text-destructive" />
                            </div>
                            <div className="space-y-2">
                                 <h3 className="text-2xl font-black text-foreground">Link Indisponível</h3>
                                 <p className="text-sm text-muted-foreground leading-relaxed">
                                    {message}
                                 </p>
                            </div>
                            <Button 
                                variant="outline"
                                size="sm"
                                className="w-full h-10 border-border text-foreground font-bold hover:bg-accent"
                                onClick={() => router.push("/login")}
                            >
                                Voltar para o Início
                            </Button>
                        </div>
                    )}
                </Card>

                <p className="text-center text-[10px] text-muted-foreground/30 mt-8 font-bold uppercase tracking-widest">
                    Segurança DeepFarms · 2026
                </p>
            </div>
    );
}

export default function AcceptInvitePage() {
    return (
        <AuthLayout badgeLabel="Convite Oficial">
            <Suspense fallback={
                <div className="flex flex-col items-center gap-4">
                    <Loader2 className="animate-spin text-primary size-12" />
                    <p className="text-white/20 text-xs font-bold uppercase tracking-widest">Carregando...</p>
                </div>
            }>
                <AcceptInviteContent />
            </Suspense>
        </AuthLayout>
    );
}
