"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod/v4";
import { useState } from "react";
import { Loader2, Mail, ArrowLeft, CheckCircle2, ArrowRight } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import { AuthLayout } from "@/components/auth/auth-layout";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";

const schema = z.object({
    email: z.string().email({ message: "Insira um e-mail válido." }),
});

export type FormData = z.infer<typeof schema>;

export function ForgotPasswordClient() {
    const [isLoading, setIsLoading] = useState(false);
    const [emailSent, setEmailSent] = useState(false);
    const [sentTo, setSentTo] = useState("");

    const form = useForm<FormData>({
        resolver: zodResolver(schema),
        defaultValues: { email: "" },
    });

    const onSubmit = async (data: FormData) => {
        setIsLoading(true);
        try {
            await apiFetch("/auth/forgot-password", {
                method: "POST",
                body: { email: data.email },
            });
            setSentTo(data.email);
            setEmailSent(true);
            toast.success("E-mail de recuperação enviado!");
        } catch (error: any) {
            toast.error(error.message || "Erro ao solicitar recuperação de senha.");
        } finally {
            setIsLoading(false);
        }
    };

    if (emailSent) {
        return (
            <AuthLayout
                badgeLabel="Verifique seu e-mail"
                title="Instruções enviadas."
                description="Acesse o link no seu e-mail para definir uma nova senha. O link expira em 1 hora."
            >
                <div className="space-y-6">
                    <div className="space-y-2">
                        <h2 className="text-2xl font-light tracking-tight text-foreground">
                            E-mail enviado
                        </h2>
                        <p className="text-sm text-muted-foreground">
                            Enviamos as instruções para{" "}
                            <strong className="text-foreground">{sentTo}</strong>.
                        </p>
                    </div>

                    <Alert>
                        <CheckCircle2 className="size-4" />
                        <AlertTitle>Próximos passos</AlertTitle>
                        <AlertDescription className="space-y-1 mt-1">
                            <p>1. Abra seu e-mail e clique no link de recuperação.</p>
                            <p>2. Crie uma nova senha segura.</p>
                        </AlertDescription>
                    </Alert>

                    <Link href="/login" className="block">
                        <Button
                            variant="outline"
                            size="sm"
                            className="w-full h-9 rounded-sm border-primary/40 text-primary hover:bg-primary hover:text-primary-foreground shadow-lg shadow-primary/10 transition-all duration-300 group"
                        >
                            <span className="flex items-center gap-2 uppercase tracking-widest text-[10px] font-semibold">
                                <ArrowLeft className="h-4 w-4" />
                                Voltar para o login
                            </span>
                        </Button>
                    </Link>

                    <div className="relative">
                        <div className="absolute inset-0 flex items-center">
                            <Separator className="w-full" />
                        </div>
                        <div className="relative flex justify-center text-xs uppercase">
                            <span className="bg-background px-2 text-muted-foreground/50">ou</span>
                        </div>
                    </div>

                    <p className="text-center text-sm text-muted-foreground/60">
                        Não recebeu?{" "}
                        <button
                            onClick={() => setEmailSent(false)}
                            className="text-primary font-semibold hover:underline transition-all"
                        >
                            Tentar novamente
                        </button>
                    </p>
                </div>
            </AuthLayout>
        );
    }

    return (
        <AuthLayout
            badgeLabel="Segurança da Conta"
            title="Recupere o acesso à sua conta."
            description="Informe o e-mail cadastrado e enviaremos um link para criar uma nova senha."
        >
            <div className="space-y-6">
                <div className="space-y-2">
                    <h2 className="text-2xl font-light tracking-tight text-foreground">
                        Recuperar senha
                    </h2>
                    <p className="text-sm text-muted-foreground">
                        Enviaremos um link de recuperação para o seu e-mail cadastrado.
                    </p>
                </div>

                <Form {...form}>
                    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                        <FormField
                            control={form.control}
                            name="email"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                                        E-mail de cadastro
                                    </FormLabel>
                                    <FormControl>
                                        <div className="relative">
                                            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-primary/70 pointer-events-none" />
                                            <Input
                                                type="email"
                                                autoComplete="email"
                                                placeholder="seu@email.com.br"
                                                className="pl-9"
                                                {...field}
                                            />
                                        </div>
                                    </FormControl>
                                    <FormMessage className="text-[10px] font-bold px-1" />
                                </FormItem>
                            )}
                        />

                        <Button
                            type="submit"
                            variant="outline"
                            size="sm"
                            disabled={isLoading}
                            className="w-full h-9 rounded-sm mt-2 border-primary/40 text-primary hover:bg-primary hover:text-primary-foreground shadow-lg shadow-primary/10 transition-all duration-300 group"
                        >
                            {isLoading ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                <span className="flex items-center gap-2 uppercase tracking-widest text-[10px] font-semibold">
                                    Enviar link de recuperação
                                    <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                                </span>
                            )}
                        </Button>
                    </form>
                </Form>

                <div className="relative">
                    <div className="absolute inset-0 flex items-center">
                        <Separator className="w-full" />
                    </div>
                    <div className="relative flex justify-center text-xs uppercase">
                        <span className="bg-background px-2 text-muted-foreground/50">ou</span>
                    </div>
                </div>

                <p className="text-center text-sm text-muted-foreground/60">
                    Lembrou a senha?{" "}
                    <Link
                        href="/login"
                        className="text-primary font-semibold hover:underline transition-all"
                    >
                        Voltar para o login
                    </Link>
                </p>
            </div>
        </AuthLayout>
    );
}
