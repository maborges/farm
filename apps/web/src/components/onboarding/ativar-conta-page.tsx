"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Card, CardContent, CardDescription, CardHeader, CardTitle,
} from "@/components/ui/card";
import {
    CheckCircle2, Tractor, Package, AlertTriangle, Loader2,
} from "lucide-react";

interface ContaInfo {
    nome_tenant: string;
    email: string;
    nome_completo: string;
    telefone: string | null;
    fazendas: string[];
    plano_nome: string;
    ciclo_pagamento: string;
}

export function AtivarContaClientPage() {
    const searchParams = useSearchParams();
    const token = searchParams.get("token") ?? "";

    const [info, setInfo] = useState<ContaInfo | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [nomeCompleto, setNomeCompleto] = useState("");
    const [telefone, setTelefone] = useState("");
    const [senha, setSenha] = useState("");
    const [confirmarSenha, setConfirmarSenha] = useState("");
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        if (!token) {
            setError("Token de ativação não encontrado na URL.");
            setLoading(false);
            return;
        }
        apiFetch(`/onboarding/ativar/${token}`)
            .then((data: ContaInfo) => {
                setInfo(data);
                setNomeCompleto(data.nome_completo);
                setTelefone(data.telefone ?? "");
            })
            .catch((err) => setError(err.message || "Token inválido ou expirado."))
            .finally(() => setLoading(false));
    }, [token]);

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        if (senha !== confirmarSenha) {
            toast.error("As senhas não coincidem.");
            return;
        }
        if (senha.length < 6) {
            toast.error("Senha deve ter pelo menos 6 caracteres.");
            return;
        }
        setSubmitting(true);
        try {
            const res = await apiFetch(`/onboarding/ativar/${token}`, {
                method: "POST",
                body: {
                    nome_completo: nomeCompleto,
                    telefone: telefone || undefined,
                    senha,
                },
            }) as { checkout_url: string };
            window.location.href = res.checkout_url;
        } catch (err: any) {
            toast.error(err.message || "Erro ao confirmar ativação.");
        } finally {
            setSubmitting(false);
        }
    }

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-muted/30 p-4">
                <div className="w-full max-w-lg space-y-4">
                    <Skeleton className="h-8 w-48 mx-auto" />
                    <Skeleton className="h-64 w-full rounded-lg" />
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-muted/30 p-4">
                <Card className="w-full max-w-md text-center">
                    <CardHeader>
                        <AlertTriangle className="size-10 text-destructive mx-auto mb-2" />
                        <CardTitle>Link inválido</CardTitle>
                        <CardDescription>{error}</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <p className="text-sm text-muted-foreground">
                            Entre em contato com o suporte para solicitar um novo link de ativação.
                        </p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-muted/30 flex items-start justify-center p-4 pt-12">
            <div className="w-full max-w-2xl space-y-6">
                <div className="text-center space-y-1">
                    <h1 className="text-2xl font-bold">Bem-vindo ao DeepFarms</h1>
                    <p className="text-muted-foreground">
                        Confirme seus dados e defina sua senha para ativar a conta
                    </p>
                </div>

                <div className="grid md:grid-cols-5 gap-4">
                    <Card className="md:col-span-2">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm font-semibold uppercase text-muted-foreground">
                                Sua assinatura
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4 text-sm">
                            <div>
                                <p className="text-muted-foreground text-xs">Empresa</p>
                                <p className="font-medium">{info!.nome_tenant}</p>
                            </div>
                            <div className="flex items-center gap-2">
                                <Package className="size-4 text-primary" />
                                <div>
                                    <p className="font-medium">{info!.plano_nome}</p>
                                    <p className="text-xs text-muted-foreground">
                                        {info!.ciclo_pagamento === "ANUAL" ? "Cobrança anual" : "Cobrança mensal"}
                                    </p>
                                </div>
                            </div>
                            <div>
                                <p className="text-muted-foreground text-xs mb-1.5 flex items-center gap-1">
                                    <Tractor className="size-3" /> Fazendas
                                </p>
                                <div className="space-y-1">
                                    {info!.fazendas.map((f, i) => (
                                        <Badge key={i} variant="secondary" className="text-xs mr-1">{f}</Badge>
                                    ))}
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="md:col-span-3">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm font-semibold uppercase text-muted-foreground">
                                Confirme seus dados
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <form onSubmit={handleSubmit} className="space-y-4">
                                <div className="space-y-1.5">
                                    <Label>Email de acesso</Label>
                                    <Input value={info!.email} disabled className="bg-muted/50" />
                                </div>
                                <div className="space-y-1.5">
                                    <Label>Nome completo *</Label>
                                    <Input
                                        value={nomeCompleto}
                                        onChange={(e) => setNomeCompleto(e.target.value)}
                                        placeholder="Seu nome completo"
                                        required
                                    />
                                </div>
                                <div className="space-y-1.5">
                                    <Label>Telefone</Label>
                                    <Input
                                        value={telefone}
                                        onChange={(e) => setTelefone(e.target.value)}
                                        placeholder="(00) 00000-0000"
                                    />
                                </div>
                                <div className="grid grid-cols-2 gap-3">
                                    <div className="space-y-1.5">
                                        <Label>Senha *</Label>
                                        <Input
                                            type="password"
                                            value={senha}
                                            onChange={(e) => setSenha(e.target.value)}
                                            placeholder="Mínimo 6 caracteres"
                                            required
                                        />
                                    </div>
                                    <div className="space-y-1.5">
                                        <Label>Confirmar senha *</Label>
                                        <Input
                                            type="password"
                                            value={confirmarSenha}
                                            onChange={(e) => setConfirmarSenha(e.target.value)}
                                            placeholder="Repita a senha"
                                            required
                                        />
                                    </div>
                                </div>

                                <Button type="submit" className="w-full gap-2" disabled={submitting}>
                                    {submitting ? (
                                        <><Loader2 className="size-4 animate-spin" /> Aguarde...</>
                                    ) : (
                                        <><CheckCircle2 className="size-4" /> Confirmar e ir para pagamento</>
                                    )}
                                </Button>

                                <p className="text-xs text-center text-muted-foreground">
                                    Você será redirecionado para o pagamento seguro via Stripe.
                                    Sua conta será ativada automaticamente após a confirmação.
                                </p>
                            </form>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}
