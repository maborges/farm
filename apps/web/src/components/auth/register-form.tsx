"use client";

import { useEffect, useState, useRef, useTransition } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import {
    ArrowLeft, ArrowRight, Check, ChevronRight,
    Loader2, Star, Shield, Mail, User, Building2, CreditCard,
    Camera,
} from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
    Avatar,
    AvatarFallback,
    AvatarImage,
} from "@/components/ui/avatar";
import { toast } from "sonner";

interface Plano {
    id: string;
    nome: string;
    descricao: string | null;
    preco_mensal: number;
    preco_anual: number;
    plan_tier: string;
    is_free: boolean;
    tem_trial: boolean;
    dias_trial: number;
    destaque: boolean;
    modulos_inclusos: string[];
    descricao_marketing: string | null;
}

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

export function RegisterForm() {
    const router = useRouter();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [step, setStep] = useState(1);
    const [isLoading, setIsLoading] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [isPending, startTransition] = useTransition();
    const [planosTimeout, setPlanosTimeout] = useState(false);

    // Step 1 — Dados do Usuário
    const [nomeCompleto, setNomeCompleto] = useState("");
    const [apelido, setApelido] = useState("");
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [cpf, setCpf] = useState("");
    const [telefone, setTelefone] = useState("");
    const [senha, setSenha] = useState("");
    const [confirmarSenha, setConfirmarSenha] = useState("");
    const [fotoUrl, setFotoUrl] = useState("");
    const [fotoFile, setFotoFile] = useState<File | null>(null);

    // Step 2 — Dados do Produtor + Plano
    const [nomeProdutor, setNomeProdutor] = useState("");
    const [cnpjCpf, setCnpjCpf] = useState("");
    const [planoSelecionado, setPlanoSelecionado] = useState<Plano | null>(null);
    const [ciclo, setCiclo] = useState<"MENSAL" | "ANUAL">("MENSAL");

    const { data: planos = [], isLoading: loadingPlanos, isError: erroPlanos, error: errorPlanos, refetch: refetchPlanos } = useQuery<Plano[]>({
        queryKey: ["billing-plans"],
        queryFn: async ({ signal }) => {
            return await apiFetch("/billing/plans", {
                signal,
                suppressErrorLog: true,
            });
        },
        enabled: step === 2,
        staleTime: 300_000,
        retry: false,
    });

    useEffect(() => {
        if (step !== 2) {
            setPlanosTimeout(false);
            return;
        }

        if (!loadingPlanos) {
            setPlanosTimeout(false);
            return;
        }

        const timeoutId = window.setTimeout(() => {
            setPlanosTimeout(true);
        }, 5000);

        return () => window.clearTimeout(timeoutId);
    }, [loadingPlanos, step]);

    const precoExibido = (plano: Plano) =>
        ciclo === "ANUAL" ? plano.preco_anual / 12 : plano.preco_mensal;

    const step1Valido = nomeCompleto.trim().length >= 3
        && username.trim().length >= 3
        && email.includes("@")
        && senha.length >= 6
        && senha === confirmarSenha;

    const step2Valido = nomeProdutor.trim().length >= 2 && !!planoSelecionado;

    const irParaEtapa2 = () => {
        if (!step1Valido) {
            toast.error("Preencha os dados de acesso corretamente antes de continuar.");
            return;
        }

        startTransition(() => setStep(2));
    };

    const irParaEtapa3 = () => {
        if (!step2Valido) {
            toast.error("Selecione um plano para continuar.");
            return;
        }

        startTransition(() => setStep(3));
    };

    const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
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

        setFotoFile(file);
        setFotoUrl(URL.createObjectURL(file));
        if (fileInputRef.current) fileInputRef.current.value = "";
    };

    const handleSubmit = async () => {
        setIsLoading(true);
        try {
            // Verificar documento se informado
            if (cnpjCpf.trim()) {
                const check = await apiFetch<{ disponivel: boolean; mensagem: string | null }>(
                    `/onboarding/verificar-documento/${encodeURIComponent(cnpjCpf.trim())}`
                );
                if (!check.disponivel) {
                    toast.error(check.mensagem || "CPF ou CNPJ já cadastrado.");
                    setIsLoading(false);
                    return;
                }
            }

            await apiFetch<{ access_token: string }>("/onboarding/assinante", {
                method: "POST",
                body: {
                    email,
                    username,
                    nome_completo: nomeCompleto,
                    apelido: apelido.trim(),
                    senha,
                    cpf: cpf.replace(/\D/g, "") || undefined,
                    telefone: telefone.replace(/\D/g, "") || undefined,
                    nome_produtor: nomeProdutor,
                    cnpj_tenant: cnpjCpf || undefined,
                    plano_id: planoSelecionado!.id,
                    ciclo,
                },
            });

            toast.success("Conta criada com sucesso. Enviamos um e-mail para confirmar seu cadastro.");
            router.push("/login");
        } catch (error: unknown) {
            toast.error(error instanceof Error ? error.message : "Erro ao criar conta. Tente novamente.");
        } finally {
            setIsLoading(false);
        }
    };

    const userInitial = nomeCompleto.trim().charAt(0).toUpperCase() || "U";

    return (
        <div className="space-y-5">
            {/* Cabeçalho */}
            <div className="space-y-2 text-center">
                <div className="inline-flex items-center justify-center size-11 rounded-sm bg-primary border border-primary/20 shadow-lg shadow-primary/20 transition-all duration-300 mb-2">
                    <Shield className="size-6 text-primary-foreground" />
                </div>
                <div className="space-y-1">
                    <h2 className="text-2xl font-light tracking-tight text-foreground uppercase italic leading-none">
                        Nova Conta Rural
                    </h2>
                    <p className="text-xs text-muted-foreground uppercase tracking-widest font-medium opacity-30">
                        Inicie sua gestão inteligente agora mesmo.
                    </p>
                </div>
            </div>

            {/* Stepper */}
            <Card className="border-border bg-card/60 backdrop-blur-md shadow-premium">
                <CardContent className="p-3">
                    <div className="flex items-center justify-between">
                        {[
                            { num: 1, icon: User, label: "Acesso" },
                            { num: 2, icon: Building2, label: "Produtor" },
                            { num: 3, icon: Check, label: "Confirmar" },
                        ].map((s, idx) => (
                            <div key={s.num} className="flex items-center flex-1">
                                <div className="flex items-center gap-2 flex-1 justify-center">
                                    <div className={`size-7 rounded-sm flex items-center justify-center text-[10px] font-semibold transition-all ${s.num < step
                                            ? "bg-primary text-primary-foreground shadow-md shadow-primary/20"
                                            : s.num === step
                                                ? "bg-primary/10 text-primary border border-primary/30"
                                                : "bg-muted/30 text-muted-foreground/40 border border-border/50"
                                        }`}>
                                        {s.num < step ? <Check size={12} /> : <s.icon size={12} />}
                                    </div>
                                    <span className={`text-[11px] font-semibold uppercase tracking-widest hidden sm:block ${s.num === step ? "text-primary" : "text-muted-foreground/30"
                                        }`}>
                                        {s.label}
                                    </span>
                                </div>
                                {idx < 2 && (
                                    <div className={`h-[1px] w-full max-w-[40px] ${s.num < step ? "bg-primary/50" : "bg-border/30"
                                        }`} />
                                )}
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* ── Step 1: Dados do Usuário ── */}
            {step === 1 && (
                <div className="space-y-3">
                    <div className="flex items-center gap-2 mb-1 px-1">
                        <User className="size-3.5 text-primary" />
                        <h3 className="text-[11px] font-semibold text-foreground uppercase tracking-wider">Credenciais de Acesso</h3>
                    </div>

                    {/* Avatar */}
                    <div className="flex items-center gap-4 p-3 rounded-sm bg-muted/20 border border-border/50">
                        <div className="relative group shrink-0">
                            <Avatar className="size-12 border border-border/50 shadow-inner">
                                <AvatarImage src={fotoUrl || undefined} alt={userInitial} />
                                <AvatarFallback className="bg-primary/5 text-primary text-lg font-semibold italic">
                                    {userInitial}
                                </AvatarFallback>
                            </Avatar>
                            <button
                                type="button"
                                onClick={() => fileInputRef.current?.click()}
                                disabled={isUploading}
                                className="absolute -bottom-1 -right-1 size-5 rounded-sm bg-primary text-white flex items-center justify-center transition-all shadow-lg hover:bg-primary/90 disabled:opacity-50"
                                aria-label="Enviar foto"
                            >
                                {isUploading ? (
                                    <Loader2 className="size-2.5 animate-spin" />
                                ) : (
                                    <Camera className="size-2.5" />
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
                        <div className="flex-1 min-w-0">
                            <p className="text-[11px] font-semibold text-foreground uppercase tracking-tight">Identidade Visual</p>
                            <p className="text-[9px] text-muted-foreground font-medium">Recomendado para personalização do sistema.</p>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                        <Field
                            label="Nome completo"
                            placeholder="Seu nome"
                            value={nomeCompleto}
                            onChange={setNomeCompleto}
                            icon={User}
                        />
                        <Field
                            label="Apelido"
                            placeholder="Como quer ser chamado"
                            value={apelido}
                            onChange={(value) => setApelido(value.slice(0, 20))}
                            icon={User}
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                        <Field
                            label="Usuário"
                            placeholder="login"
                            value={username}
                            onChange={setUsername}
                            icon={User}
                        />
                    </div>

                    <Field
                        label="E-mail"
                        type="email"
                        placeholder="contato@empresa.com"
                        value={email}
                        onChange={setEmail}
                        icon={Mail}
                    />

                    <div className="grid grid-cols-2 gap-2">
                        <Field
                            label="CPF"
                            placeholder="000.000.000-00"
                            value={cpf}
                            onChange={(v) => setCpf(formatCpf(v))}
                        />
                        <Field
                            label="Telefone"
                            placeholder="(00) 00000-0000"
                            value={telefone}
                            onChange={(v) => setTelefone(formatPhone(v))}
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                        <Field
                            label="Senha"
                            type="password"
                            placeholder="••••••••"
                            value={senha}
                            onChange={setSenha}
                        />
                        <Field
                            label="Confirmar senha"
                            type="password"
                            placeholder="••••••••"
                            value={confirmarSenha}
                            onChange={setConfirmarSenha}
                        />
                    </div>

                    {confirmarSenha && senha !== confirmarSenha && (
                        <div className="flex items-center gap-2 p-2 rounded bg-destructive/10 border border-destructive/20">
                            <p className="text-xs text-destructive">As senhas não coincidem.</p>
                        </div>
                    )}

                    {senha.length >= 6 && senha === confirmarSenha && (
                        <div className="flex items-center gap-2 p-2 rounded bg-primary/10 border border-primary/20">
                            <Check size={12} className="text-primary" />
                            <p className="text-xs text-primary">Senha válida</p>
                        </div>
                    )}

                    <Separator className="bg-border/40" />

                    <div className="flex justify-end pt-2">
                        <Button
                            onClick={irParaEtapa2}
                            disabled={!step1Valido || isPending}
                            size="sm"
                            className="bg-primary hover:bg-primary/90 text-white"
                        >
                            Próximo <ChevronRight size={14} className="ml-1" />
                        </Button>
                    </div>
                </div>
            )}

            {/* ── Step 2: Dados do Produtor + Plano ── */}
            {step === 2 && (
                <div className="space-y-3">
                    <div className="flex items-center gap-2 mb-2">
                        <Building2 className="size-4 text-primary" />
                        <h3 className="text-sm font-semibold text-foreground">Dados do Produtor</h3>
                    </div>

                    <div className="space-y-3">
                        <Field
                            label="Nome do Produtor / Empresa *"
                            placeholder="Ex: João da Silva ou Fazenda São José Ltda"
                            value={nomeProdutor}
                            onChange={setNomeProdutor}
                            icon={Building2}
                        />
                        <div className="space-y-1">
                            <Field
                                label="CNPJ / CPF"
                                placeholder="000.000.000-00 ou 00.000.000/0000-00"
                                value={cnpjCpf}
                                onChange={setCnpjCpf}
                            />
                            <p className="text-[10px] text-muted-foreground">Opcional — pode ser preenchido depois em Configurações</p>
                        </div>
                    </div>

                    <Separator className="bg-border/40" />

                    {/* Plano */}
                    <div>
                        <div className="flex items-center gap-2 mb-3">
                            <CreditCard className="size-4 text-primary" />
                            <p className="text-sm font-semibold text-foreground">Escolha seu Plano</p>
                        </div>

                        {/* Toggle Mensal/Anual */}
                        <div className="flex items-center gap-2 p-1 bg-muted/40 rounded-sm w-fit mb-3 border border-border">
                            {(["MENSAL", "ANUAL"] as const).map((c) => (
                                <button
                                    key={c}
                                    type="button"
                                    onClick={() => setCiclo(c)}
                                    className={`px-3 py-1.5 text-xs rounded-sm transition-colors ${ciclo === c
                                            ? "bg-primary/20 text-primary font-semibold border border-primary/30"
                                            : "text-muted-foreground hover:text-foreground"
                                        }`}
                                >
                                    {c === "MENSAL" ? "Mensal" : "Anual −20%"}
                                </button>
                            ))}
                        </div>

                        {loadingPlanos && !planosTimeout ? (
                            <div className="flex justify-center py-8">
                                <Loader2 className="animate-spin text-primary/50" size={24} />
                            </div>
                        ) : erroPlanos || planosTimeout ? (
                            <div className="space-y-3 rounded-sm border border-destructive/20 bg-destructive/5 p-3">
                                <p className="text-sm font-semibold text-foreground">
                                    Não foi possível carregar os planos.
                                </p>
                                <p className="text-xs text-muted-foreground">
                                    {planosTimeout
                                        ? "A resposta demorou demais. Verifique a conexão ou tente novamente."
                                        : (errorPlanos instanceof Error ? errorPlanos.message : "Tente novamente em instantes.")}
                                </p>
                                <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    onClick={() => {
                                        setPlanosTimeout(false);
                                        void refetchPlanos();
                                    }}
                                >
                                    Tentar novamente
                                </Button>
                            </div>
                        ) : planos.length === 0 ? (
                            <div className="space-y-2 rounded-sm border border-border bg-muted/20 p-3">
                                <p className="text-sm font-semibold text-foreground">Nenhum plano disponível no momento.</p>
                                <p className="text-xs text-muted-foreground">
                                    Volte mais tarde ou fale com o suporte para liberar os planos de assinatura.
                                </p>
                            </div>
                        ) : (
                            <div className="space-y-2 max-h-52 overflow-y-auto pr-1 scrollbar-thin">
                                {planos.map((plano) => (
                                    <button
                                        key={plano.id}
                                        onClick={() => setPlanoSelecionado(plano)}
                                        className={`w-full text-left p-3 rounded-sm border transition-all ${planoSelecionado?.id === plano.id
                                                ? "border-primary bg-primary/10 shadow-lg shadow-primary/10"
                                                : "border-border hover:border-primary/50 bg-card/50"
                                            }`}
                                    >
                                        <div className="flex items-start justify-between gap-2">
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-1.5 flex-wrap">
                                                    <span className="font-semibold text-sm text-foreground">{plano.nome}</span>
                                                    {plano.destaque && <Star size={12} className="text-amber-400 fill-amber-400" />}
                                                    {plano.is_free && <Badge variant="secondary" className="text-[10px]">Grátis</Badge>}
                                                    {!plano.is_free && plano.tem_trial && (
                                                        <Badge className="text-[10px] bg-primary text-white">{plano.dias_trial}d grátis</Badge>
                                                    )}
                                                </div>
                                                {plano.descricao_marketing && (
                                                    <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-2">{plano.descricao_marketing}</p>
                                                )}
                                            </div>
                                            <div className="text-right shrink-0">
                                                {plano.is_free ? (
                                                    <span className="text-sm font-bold text-primary">R$ 0</span>
                                                ) : (
                                                    <div>
                                                        <span className="text-sm font-bold text-foreground">
                                                            R$ {precoExibido(plano).toFixed(2).replace(".", ",")}
                                                        </span>
                                                        <span className="text-[10px] text-muted-foreground">/mês</span>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                        {planoSelecionado?.id === plano.id && (
                                            <div className="flex items-center gap-1 mt-2 pt-2 border-t border-primary/20">
                                                <Check size={12} className="text-primary" />
                                                <span className="text-[10px] text-primary font-semibold">Selecionado</span>
                                            </div>
                                        )}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    <Separator className="bg-border/40" />

                    <div className="flex justify-between pt-2">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => startTransition(() => setStep(1))}
                            className="text-muted-foreground hover:text-foreground"
                        >
                            <ArrowLeft size={14} className="mr-1" /> Voltar
                        </Button>
                        <Button
                            onClick={irParaEtapa3}
                            disabled={!step2Valido || isPending}
                            size="sm"
                            className="bg-primary hover:bg-primary/90 text-white"
                        >
                            Próximo <ChevronRight size={14} className="ml-1" />
                        </Button>
                    </div>
                </div>
            )}

            {/* ── Step 3: Confirmação ── */}
            {step === 3 && planoSelecionado && (
                <div className="space-y-3">
                    <div className="flex items-center gap-2 mb-2">
                        <Check className="size-4 text-primary" />
                        <h3 className="text-sm font-semibold text-foreground">Confirme seus Dados</h3>
                    </div>

                    <Card className="border-border bg-card/50">
                        <CardContent className="p-4 space-y-3">
                            <SummaryRow label="Nome" value={nomeCompleto} icon={User} />
                            <SummaryRow label="E-mail" value={email} icon={Mail} />
                            {cpf && <SummaryRow label="CPF" value={cpf} />}
                            {telefone && <SummaryRow label="Telefone" value={telefone} />}
                            <SummaryRow label="Produtor" value={nomeProdutor} icon={Building2} />
                            {cnpjCpf && <SummaryRow label="CNPJ/CPF" value={cnpjCpf} />}

                            <Separator className="bg-border/40" />

                            <div className="flex items-center gap-2 p-3 rounded-sm bg-primary/10 border border-primary/20">
                                <CreditCard className="size-4 text-primary" />
                                <div className="flex-1">
                                    <p className="text-[10px] text-muted-foreground uppercase font-semibold">Plano Selecionado</p>
                                    <p className="text-sm font-semibold text-foreground">{planoSelecionado.nome}</p>
                                </div>
                                <div className="text-right">
                                    {planoSelecionado.is_free ? (
                                        <span className="text-lg font-bold text-primary">Grátis</span>
                                    ) : (
                                        <div>
                                            <span className="text-lg font-bold text-foreground">
                                                R$ {precoExibido(planoSelecionado).toFixed(2).replace(".", ",")}
                                            </span>
                                            <span className="text-[10px] text-muted-foreground">/mês</span>
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div className="flex items-center justify-between text-sm pt-2 border-t border-border">
                                <span className="text-muted-foreground">Ciclo de pagamento</span>
                                <span className="font-semibold text-foreground">
                                    {ciclo === "MENSAL" ? "Mensal" : "Anual (20% desconto)"}
                                </span>
                            </div>

                            {planoSelecionado.tem_trial && planoSelecionado.dias_trial > 0 && (
                                <div className="flex items-center gap-2 p-2 rounded bg-primary/10 border border-primary/20">
                                    <Star size={12} className="text-primary" />
                                    <p className="text-xs text-primary font-medium">
                                        {planoSelecionado.dias_trial} dias grátis para testar
                                    </p>
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    <div className="flex justify-between pt-2">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => startTransition(() => setStep(2))}
                            className="text-muted-foreground hover:text-foreground"
                        >
                            <ArrowLeft size={14} className="mr-1" /> Voltar
                        </Button>
                        <Button
                            onClick={handleSubmit}
                            disabled={isLoading}
                            size="lg"
                            className="bg-primary hover:bg-primary/90 text-primary-foreground font-semibold uppercase tracking-widest text-xs border-0 shadow-lg shadow-primary/20 transition-all min-w-[180px]"
                        >
                            {isLoading
                                ? <><Loader2 size={14} className="mr-2 animate-spin" />Finalizando...</>
                                : <>Criar minha conta <ArrowRight size={14} className="ml-2" /></>}
                        </Button>
                    </div>
                </div>
            )}

            {/* Rodapé */}
            <div className="text-center space-y-4">
                <div className="relative">
                    <div className="absolute inset-0 flex items-center">
                        <Separator className="w-full" />
                    </div>
                    <div className="relative flex justify-center text-xs uppercase">
                        <span className="bg-background px-2 text-muted-foreground/50">
                            Já é membro?
                        </span>
                    </div>
                </div>

                <p className="text-center">
                    <Link
                        href="/login"
                        className="text-primary font-semibold uppercase text-sm hover:underline transition-all"
                    >
                        Fazer Login Agora
                    </Link>
                </p>
                <div className="flex items-center justify-center gap-1.5 text-[10px] text-muted-foreground/50">
                    <Shield size={10} />
                    <span>Protegido por criptografia end-to-end · SOC 2 Type II</span>
                </div>
            </div>
        </div>
    );
}

// ── Helpers ───────────────────────────────────────────────
function Field({ label, placeholder, value, onChange, type = "text", icon: Icon }: {
    label: string; placeholder: string; value: string;
    onChange: (v: string) => void; type?: string;
    icon?: React.ComponentType<{ size?: number; className?: string }>;
}) {
    return (
        <div className="space-y-1">
            <Label className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">{label}</Label>
            <div className="relative">
                {Icon && (
                    <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none">
                        <Icon size={14} className="text-primary/70" />
                    </div>
                )}
                <Input
                    type={type}
                    placeholder={placeholder}
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    className={Icon ? "pl-9" : ""}
                />
            </div>
        </div>
    );
}

function SummaryRow({ label, value, icon: Icon }: { label: string; value: string; icon?: React.ComponentType<{ size?: number; className?: string }> }) {
    return (
        <div className="flex items-center justify-between text-[11px] font-medium py-0.5">
            <div className="flex items-center gap-2">
                {Icon && <Icon size={12} className="text-primary/60" />}
                <span className="text-muted-foreground uppercase tracking-wider">{label}</span>
            </div>
            <span className="font-semibold text-foreground">{value}</span>
        </div>
    );
}
