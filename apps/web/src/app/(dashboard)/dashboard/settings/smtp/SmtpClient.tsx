"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Mail, ShieldCheck, Server, Key, Send, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod/v4";
import { useEffect } from "react";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/shared/page-header";

const smtpSchema = z.object({
    host: z.string().min(1, "O host do servidor é obrigatório."),
    port: z.number().int().positive("Porta inválida."),
    user: z.string().optional(),
    pass: z.string().optional(),
    from: z.string().email("E-mail do remetente inválido."),
});

export type SMTPFormData = z.infer<typeof smtpSchema>;

export function SmtpClient({ initialData }: { initialData?: SMTPFormData | null }) {
    const {
        register,
        handleSubmit,
        reset,
        formState: { errors, isDirty }
    } = useForm<SMTPFormData>({
        resolver: zodResolver(smtpSchema),
        defaultValues: {
            port: 587
        }
    });

    const { data: smtpConfig, isLoading, refetch } = useQuery<SMTPFormData>({
        queryKey: ["my-smtp-config"],
        queryFn: () => apiFetch("/config/my-smtp"),
        initialData: initialData || undefined
    });

    const updateMutation = useMutation({
        mutationFn: (data: SMTPFormData) =>
            apiFetch("/config/my-smtp", {
                method: "PUT",
                body: JSON.stringify(data)
            }),
        onSuccess: () => {
            toast.success("Configurações SMTP atualizadas com sucesso!");
            refetch();
        },
        onError: (err: any) => {
            toast.error(err.message || "Erro ao salvar configurações.");
        }
    });

    useEffect(() => {
        if (smtpConfig) {
            reset(smtpConfig);
        }
    }, [smtpConfig, reset]);

    const onSubmit = (data: SMTPFormData) => {
        updateMutation.mutate(data);
    };

    if (isLoading) {
        return (
            <div className="p-8 flex items-center justify-center min-h-[400px]">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    return (
        <div className="p-8 space-y-8 w-full max-w-full">
            <PageHeader
                title="Comunicação por E-mail"
                description="Configure seu próprio servidor SMTP para enviar e-mails personalizados com sua marca (White-label)."
                breadcrumbs={[{ label: "Configurações" }, { label: "SMTP" }]}
            />

            <div className="grid gap-6 lg:grid-cols-3">
                <div className="lg:col-span-2">
                    <form onSubmit={handleSubmit(onSubmit)}>
                        <Card className="border-l-[3px] border-l-primary">
                            <CardHeader className="bg-muted/30">
                                <CardTitle className="text-lg flex items-center gap-2">
                                    <Server size={18} className="text-primary" /> Parâmetros do Servidor
                                </CardTitle>
                                <CardDescription>Consulte seu provedor de e-mail para obter as credenciais corretas.</CardDescription>
                            </CardHeader>
                            <CardContent className="pt-6 space-y-4">
                                <div className="grid grid-cols-4 gap-4">
                                    <div className="col-span-3 space-y-2">
                                        <Label htmlFor="host">Host / Servidor SMTP</Label>
                                        <Input
                                            id="host"
                                            placeholder="smtp.exemplo.com.br"
                                            {...register("host")}
                                            className={cn(errors.host && "border-destructive")}
                                        />
                                        {errors.host && <p className="text-xs text-destructive font-medium">{errors.host.message}</p>}
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="port">Porta</Label>
                                        <Input
                                            id="port"
                                            type="number"
                                            placeholder="587"
                                            {...register("port", { valueAsNumber: true })}
                                            className={cn(errors.port && "border-destructive")}
                                        />
                                        {errors.port && <p className="text-xs text-destructive font-medium">{errors.port.message}</p>}
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="from">E-mail de Remetente (Exibido ao cliente)</Label>
                                    <Input
                                        id="from"
                                        placeholder="notificacoes@fazendaouro.com.br"
                                        {...register("from")}
                                        className={cn(errors.from && "border-destructive")}
                                    />
                                    {errors.from && <p className="text-xs text-destructive font-medium">{errors.from.message}</p>}
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="user">Usuário / Login</Label>
                                        <Input id="user" placeholder="usuario@provedor.com" {...register("user")} />
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="pass">Chave de App / Senha</Label>
                                        <div className="relative">
                                            <Input id="pass" type="password" placeholder="••••••••" {...register("pass")} className="pr-10" />
                                            <Key className="absolute right-3 top-2.5 text-muted-foreground" size={14} />
                                        </div>
                                    </div>
                                </div>
                            </CardContent>
                            <CardFooter className="flex justify-between items-center border-t py-4 bg-muted/10">
                                <p className="text-[10px] text-muted-foreground italic flex items-center gap-1">
                                    <ShieldCheck size={12} className="text-emerald-500" /> Suas credenciais são criptografadas em repouso.
                                </p>
                                <Button
                                    type="submit"
                                    size="sm"
                                    className="gap-2"
                                    disabled={!isDirty || updateMutation.isPending}
                                >
                                    {updateMutation.isPending ? <Loader2 className="size-4 animate-spin" /> : <Send size={14} />}
                                    Salvar Alterações
                                </Button>
                            </CardFooter>
                        </Card>
                    </form>
                </div>

                <Card className="bg-emerald-500/5 border-emerald-500/10 shadow-none h-fit">
                    <CardHeader>
                        <CardTitle className="text-sm font-bold uppercase tracking-widest text-emerald-700">Por que configurar?</CardTitle>
                    </CardHeader>
                    <CardContent className="text-xs space-y-4 text-emerald-900/70 leading-relaxed">
                        <p>
                            Ao utilizar o seu próprio servidor de e-mail, você aumenta a confiança dos seus produtores e parceiros.
                        </p>
                        <ul className="list-disc pl-4 space-y-2">
                            <li>Emails enviados de @suafazenda.com.br</li>
                            <li>Menor risco de cair na caixa de Spam</li>
                            <li>Centralização de logs no seu provedor</li>
                        </ul>
                        <div className="p-3 bg-white/50 rounded-sm border border-emerald-200">
                            <p className="font-bold text-emerald-800 flex items-center gap-2">
                                <Info size={14} /> Recomendação
                            </p>
                            <p className="mt-1">Recomendamos usar porta 587 (STARTTLS) ou 465 (TLS) para segurança.</p>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}

function Info({ size }: { size: number }) {
    return (
        <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-info"><circle cx="12" cy="12" r="10" /><path d="M12 16v-4" /><path d="M12 8h.01" /></svg>
    );
}
