"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod/v4";
import { ArrowLeft, Loader2, LogIn, MailCheck, PlayCircle, Send, UserCheck } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ThemeToggle } from "@/components/landing/ThemeToggle";

import { apiFetch } from "@/lib/api";

const demoRequestSchema = z.object({
    nome: z.string().trim().min(2, { message: "Informe seu nome completo." }).max(150),
    email: z.string().trim().email({ message: "Insira um e-mail válido." }),
    telefone: z.string().trim().max(30).optional(),
    empresa: z.string().trim().max(200).optional(),
});

type DemoRequestFormData = z.infer<typeof demoRequestSchema>;

interface DemoRequestResponse {
    ja_cadastrado: boolean;
    ja_vinculado_demo: boolean;
    convite_reenviado: boolean;
    dias_acesso: number;
    mensagem: string;
}

export function DemoRequestForm() {
    const [result, setResult] = useState<DemoRequestResponse | null>(null);
    const [submittedEmail, setSubmittedEmail] = useState("");

    const {
        register,
        handleSubmit,
        formState: { errors, isSubmitting },
    } = useForm<DemoRequestFormData>({
        resolver: zodResolver(demoRequestSchema),
        defaultValues: {
            nome: "",
            email: "",
            telefone: "",
            empresa: "",
        },
    });

    const onSubmit = async (data: DemoRequestFormData) => {
        try {
            const response = await apiFetch<DemoRequestResponse>("/onboarding/demonstracao/solicitar", {
                method: "POST",
                body: JSON.stringify({
                    nome: data.nome,
                    email: data.email,
                    telefone: data.telefone || undefined,
                    empresa: data.empresa || undefined,
                }),
            });

            setSubmittedEmail(data.email);
            setResult(response);

            if (response.ja_cadastrado) {
                toast.info(response.mensagem);
            } else {
                toast.success("Solicitação recebida! Verifique seu e-mail para acessar a demonstração.");
            }
        } catch (error: unknown) {
            const message =
                error instanceof Error
                    ? error.message
                    : "Não foi possível enviar sua solicitação de demonstração.";
            toast.error(message);
        }
    };

    if (result) {
        const isLinked = result.ja_cadastrado && result.ja_vinculado_demo;
        const isExistingNotLinked = result.ja_cadastrado && !result.ja_vinculado_demo;

        return (
            <div className="space-y-5">
                <div className="flex items-start justify-between gap-2">
                    <Badge
                        variant="outline"
                        className="rounded-sm border-primary/30 bg-primary/10 text-primary text-[10px] font-bold uppercase tracking-wider"
                    >
                        {isLinked
                            ? "Acesso já liberado"
                            : isExistingNotLinked
                              ? "Conta já cadastrada"
                              : `Demonstração · ${result.dias_acesso} dias`}
                    </Badge>
                    <ThemeToggle />
                </div>

                <div className="flex items-start gap-3">
                    <div className="flex size-10 shrink-0 items-center justify-center rounded-sm border border-primary/25 bg-primary/10 text-primary">
                        {isLinked ? <UserCheck className="size-5" /> : <MailCheck className="size-5" />}
                    </div>
                    <div className="space-y-1">
                        <h2 className="text-xl font-semibold tracking-tight">
                            {isLinked
                                ? "Você já possui acesso à demonstração"
                                : isExistingNotLinked
                                  ? "Você já está cadastrado na plataforma"
                                  : "Confira seu e-mail"}
                        </h2>
                        <p className="text-sm leading-relaxed text-muted-foreground">
                            {result.mensagem}
                        </p>
                    </div>
                </div>

                {submittedEmail && (
                    <div className="rounded-sm border border-border/60 bg-background/60 px-3 py-2 text-xs text-muted-foreground">
                        E-mail informado: <span className="font-semibold text-foreground">{submittedEmail}</span>
                    </div>
                )}

                <div className="flex flex-wrap items-center gap-2 pt-2">
                    <Button asChild size="sm" className="rounded-sm">
                        <Link href={submittedEmail ? `/login?email=${encodeURIComponent(submittedEmail)}` : "/login"}>
                            <LogIn className="size-3.5" />
                            Ir para Entrar
                        </Link>
                    </Button>
                    <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="rounded-sm"
                        onClick={() => setResult(null)}
                    >
                        Informar outro e-mail
                    </Button>
                    <Button asChild variant="outline" size="sm" className="rounded-sm">
                        <Link href="/">
                            <ArrowLeft className="size-3.5" />
                            Voltar ao início
                        </Link>
                    </Button>
                </div>
            </div>
        );
    }

    return (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="flex items-start justify-between gap-2">
                <div className="space-y-1">
                    <Badge
                        variant="outline"
                        className="rounded-sm border-primary/30 bg-primary/10 text-primary text-[10px] font-bold uppercase tracking-wider"
                    >
                        <PlayCircle className="mr-1 size-3" />
                        Ambiente de Demonstração
                    </Badge>
                    <h2 className="text-xl font-semibold tracking-tight">
                        Solicitar acesso à demonstração
                    </h2>
                    <p className="text-xs leading-relaxed text-muted-foreground">
                        Informe seus dados para explorar o DeepFarms Gestão com dados reais em modo somente consulta.
                    </p>
                </div>
                <ThemeToggle />
            </div>

            <div className="space-y-1.5">
                <Label htmlFor="demo-nome" className="text-xs font-medium">
                    Nome completo *
                </Label>
                <Input
                    id="demo-nome"
                    placeholder="Seu nome"
                    className="h-8 rounded-sm text-sm"
                    {...register("nome")}
                />
                {errors.nome && <p className="text-xs text-destructive">{errors.nome.message}</p>}
            </div>

            <div className="space-y-1.5">
                <Label htmlFor="demo-email" className="text-xs font-medium">
                    E-mail *
                </Label>
                <Input
                    id="demo-email"
                    type="email"
                    placeholder="voce@fazenda.com.br"
                    className="h-8 rounded-sm text-sm"
                    {...register("email")}
                />
                {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                    <Label htmlFor="demo-telefone" className="text-xs font-medium">
                        Telefone / WhatsApp <span className="text-muted-foreground">(opcional)</span>
                    </Label>
                    <Input
                        id="demo-telefone"
                        placeholder="(00) 00000-0000"
                        className="h-8 rounded-sm text-sm"
                        {...register("telefone")}
                    />
                </div>
                <div className="space-y-1.5">
                    <Label htmlFor="demo-empresa" className="text-xs font-medium">
                        Fazenda / Empresa <span className="text-muted-foreground">(opcional)</span>
                    </Label>
                    <Input
                        id="demo-empresa"
                        placeholder="Ex: Fazenda Boa Vista"
                        className="h-8 rounded-sm text-sm"
                        {...register("empresa")}
                    />
                </div>
            </div>

            <Button type="submit" size="sm" disabled={isSubmitting} className="w-full rounded-sm">
                {isSubmitting ? (
                    <>
                        <Loader2 className="size-3.5 animate-spin" />
                        Enviando solicitação...
                    </>
                ) : (
                    <>
                        <Send className="size-3.5" />
                        Solicitar acesso à demonstração
                    </>
                )}
            </Button>

            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border/40 pt-3 text-xs text-muted-foreground">
                <span>Já tem conta?</span>
                <div className="flex items-center gap-2">
                    <Button asChild variant="outline" size="sm" className="rounded-sm">
                        <Link href="/login">
                            <LogIn className="size-3.5" />
                            Entrar
                        </Link>
                    </Button>
                    <Button asChild variant="outline" size="sm" className="rounded-sm">
                        <Link href="/">
                            <ArrowLeft className="size-3.5" />
                            Voltar
                        </Link>
                    </Button>
                </div>
            </div>
        </form>
    );
}
