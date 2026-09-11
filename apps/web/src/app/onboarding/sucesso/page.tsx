"use client";

import { CheckCircle2, BrainCircuit, Target, Zap, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";

const MODO_ESSENCIAL_ITENS = [
    {
        icon: Target,
        titulo: "O que é o Modo Essencial?",
        texto: "A IA analisa sua operação e mostra a decisão mais importante do momento — sem você precisar navegar por relatórios.",
        cls: "text-primary bg-primary/10",
    },
    {
        icon: BrainCircuit,
        titulo: "Como a IA escolhe a prioridade?",
        texto: "Ela combina dados financeiros, operacionais e histórico de decisões para determinar o que exige atenção agora.",
        cls: "text-violet-600 bg-violet-500/10",
    },
    {
        icon: Zap,
        titulo: "Como agir sobre uma sugestão?",
        texto: "Cada recomendação tem um botão de ação direto. Você confirma; a IA cuida do restante.",
        cls: "text-amber-600 bg-amber-500/10",
    },
    {
        icon: TrendingUp,
        titulo: "O que acontece com o tempo?",
        texto: "A IA aprende com seu ritmo. Quanto mais você usa, mais as sugestões se alinham ao seu perfil de decisão.",
        cls: "text-emerald-600 bg-emerald-500/10",
    },
];

export default function OnboardingSucessoPage() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-muted/30 p-4">
            <div className="w-full max-w-lg space-y-4">
                <Card className="w-full text-center">
                    <CardHeader>
                        <CheckCircle2 className="size-12 text-emerald-500 mx-auto mb-2" />
                        <CardTitle className="text-xl">Conta ativada com sucesso!</CardTitle>
                        <CardDescription>
                            Seu pagamento foi confirmado e sua conta está pronta para uso.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        <p className="text-sm text-muted-foreground">
                            Acesse a plataforma com o email e a senha que você definiu durante a ativação.
                        </p>
                        <Button asChild className="w-full">
                            <Link href="/login">Acessar a plataforma</Link>
                        </Button>
                    </CardContent>
                </Card>

                {/* Modo Essencial — Onboarding Explainer */}
                <Card className="w-full border-primary/20">
                    <CardHeader className="pb-3">
                        <div className="flex items-center gap-2">
                            <BrainCircuit className="size-5 text-primary animate-pulse" />
                            <CardTitle className="text-base">Conheça o Copiloto IA</CardTitle>
                        </div>
                        <CardDescription className="text-left leading-snug">
                            O DeepFarms mostra a decisão mais importante do dia e prepara a ação para você.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3 pt-0">
                        {MODO_ESSENCIAL_ITENS.map(({ icon: Icon, titulo, texto, cls }) => (
                            <div key={titulo} className="flex items-start gap-3">
                                <span className={`size-7 rounded-sm flex items-center justify-center shrink-0 ${cls}`}>
                                    <Icon className="size-3.5" />
                                </span>
                                <div className="space-y-0.5">
                                    <p className="text-xs font-semibold text-foreground">{titulo}</p>
                                    <p className="text-xs text-muted-foreground leading-snug">{texto}</p>
                                </div>
                            </div>
                        ))}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
