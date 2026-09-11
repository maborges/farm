"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Settings2, Save, Loader2, Database, AlertCircle, CheckCircle2, CreditCard, Construction, Lock, Mail, Shield } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { useState, useEffect } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/shared/page-header";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import { StatusBadge } from "@/components/ui/status-badge";

interface SaaSConfig {
    chave: string;
    valor: any;
    descricao: string | null;
    ativo: boolean;
}

export default function SaaSConfigPage() {
    const [localConfigs, setLocalConfigs] = useState<Record<string, any>>({});
    const [mounted, setMounted] = useState(false);

    const { data: configs, isLoading, error, refetch } = useQuery<SaaSConfig[]>({
        queryKey: ["saas-configs"],
        queryFn: () => apiFetch("/config/saas"),
        retry: 1,
        retryDelay: 1000,
    });

    useEffect(() => {
        setMounted(true);
    }, []);

    const updateMutation = useMutation({
        mutationFn: ({ chave, valor }: { chave: string, valor: any }) =>
            apiFetch(`/config/saas/${chave}`, {
                method: "PUT",
                body: JSON.stringify({ valor })
            }),
        onSuccess: () => {
            toast.success("Configuração salva com sucesso!");
            refetch();
        },
        onError: (err: any) => {
            toast.error(err.message || "Erro ao salvar.");
        }
    });

    const testSmtpMutation = useMutation({
        mutationFn: () => apiFetch<{ message: string }>("/config/saas/smtp_global/test", { method: "POST" }),
        onSuccess: (result) => toast.success(result.message),
        onError: () => toast.error("Não foi possível enviar o e-mail de teste. Verifique o SMTP global salvo."),
    });

    useEffect(() => {
        if (configs) {
            const initial = configs.reduce((acc, c) => ({ ...acc, [c.chave]: c.valor }), {});
            setLocalConfigs(initial);
        }
    }, [configs]);

    const handleValueChange = (chave: string, field: string, value: any) => {
        setLocalConfigs(prev => ({
            ...prev,
            [chave]: {
                ...prev[chave],
                [field]: value
            }
        }));
    };

    if (!mounted || isLoading) {
        return (
            <div className="flex flex-col gap-6 p-6">
                <Skeleton className="h-10 w-48" />
                <div className="grid gap-6">
                    <Skeleton className="h-64" />
                    <Skeleton className="h-64" />
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col gap-6 p-6">
                <PageHeader
                    title="Parâmetros do SaaS"
                    description="Configurações globais de infraestrutura persistidas no banco de dados."
                />
                <Card className="border-destructive/30 bg-destructive/5">
                    <CardContent className="pt-6 flex items-center gap-4">
                        <AlertCircle className="size-12 text-destructive shrink-0" />
                        <div>
                            <h3 className="font-semibold text-destructive text-balance">Erro ao carregar configurações</h3>
                            <p className="text-sm text-destructive/80 mt-1 text-pretty">
                                {(error as Error)?.message || "Não foi possível carregar as configurações."}
                            </p>
                            <Button
                                variant="outline"
                                size="sm"
                                className="mt-3"
                                onClick={() => refetch()}
                            >
                                Tentar Novamente
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    // Garante que exista pelo menos o form de SMTP se o banco estiver vazio
    const hasSmtp = configs?.some(c => c.chave === "smtp_global");

    const smtpLocal = localConfigs["smtp_global"] || { host: "smtp.mailtrap.io", port: 587, user: "", from: "noreply@agrosaas.com.br" };

    const hasStripe = configs?.some(c => c.chave === "stripe");
    const stripeLocal = localConfigs["stripe"] || { secret_key: "", webhook_secret: "", frontend_url: "https://app.agrosaas.com.br" };

    const hasEmDesenvolvimento = configs?.some(c => c.chave === "em_desenvolvimento");
    const emDesenvolvimentoLocal = localConfigs["em_desenvolvimento"] || {
        titulo: "Em Desenvolvimento",
        descricao: "Esta funcionalidade está sendo construída com muito carinho e estará disponível em breve.",
        funcionalidades: [],
        previsao: "",
        voltarPara: "/dashboard"
    };

    const hasBloqueioSenha = configs?.some(c => c.chave === "bloqueio_senha");
    const bloqueioSenhaLocal = localConfigs["bloqueio_senha"] || {
        rate_limiting_ativo: true,
        max_tentativas: 5,
        tempo_bloqueio_minutos: 15
    };

    // Se não houver configs, usa valores padrão
    const configsExist = configs && configs.length > 0;

    return (
        <div className="flex flex-col gap-6 p-6">
            <PageHeader
                title="Parâmetros do SaaS"
                description="Configurações globais persistidas no banco de dados."
                icon={<Settings2 className="text-primary" size={22} />}
                actions={
                    <Badge variant="outline" className="bg-primary/5 gap-2 px-3 py-1">
                        <Database size={14} className="text-primary" /> Persistente
                    </Badge>
                }
            />

            <Tabs defaultValue="integrações">
                <div className="border-b bg-muted/5">
                    <TabsList className="bg-transparent h-10 w-full justify-start gap-4 p-0">
                        <TabsTrigger
                            value="integrações"
                            className="data-[selected]:bg-transparent data-[selected]:border-b-2 data-[selected]:border-primary rounded-none shadow-none h-full px-1 gap-1.5 text-xs"
                        >
                            <CreditCard className="size-3.5" />
                            Integrações
                        </TabsTrigger>
                        <TabsTrigger
                            value="segurança"
                            className="data-[selected]:bg-transparent data-[selected]:border-b-2 data-[selected]:border-primary rounded-none shadow-none h-full px-1 gap-1.5 text-xs"
                        >
                            <Shield className="size-3.5" />
                            Segurança
                        </TabsTrigger>
                        <TabsTrigger
                            value="ux"
                            className="data-[selected]:bg-transparent data-[selected]:border-b-2 data-[selected]:border-primary rounded-none shadow-none h-full px-1 gap-1.5 text-xs"
                        >
                            <Construction className="size-3.5" />
                            UX & Experiência
                        </TabsTrigger>
                    </TabsList>
                </div>

                {/* TAB: INTEGRAÇÕES */}
                <TabsContent value="integrações" className="mt-6">
                    <div className="grid gap-6 grid-cols-1 lg:grid-cols-2">
                        {/* SMTP GLOBAL */}
                        <Card>
                            <CardHeader className="border-b border-muted/20 bg-muted/10">
                                <div className="flex items-center justify-between">
                                    <div className="space-y-0.5">
                                        <CardTitle className="text-balance">SMTP Global</CardTitle>
                                        <CardDescription className="text-xs">E-mail para notificações</CardDescription>
                                    </div>
                                    {hasSmtp ? (
                                        <StatusBadge status="ativo" />
                                    ) : (
                                        <Badge variant="secondary" className="text-[10px]">Não configurado</Badge>
                                    )}
                                </div>
                            </CardHeader>
                            <CardContent className="pt-6 space-y-4">
                                <div className="space-y-2">
                                    <Label className="text-[11px] uppercase font-bold text-muted-foreground">Host do Servidor</Label>
                                    <Input
                                        value={smtpLocal.host}
                                        onChange={(e) => handleValueChange("smtp_global", "host", e.target.value)}
                                        placeholder="ex: smtp.sendgrid.net"
                                        className="text-sm"
                                    />
                                </div>
                                <div className="grid grid-cols-2 gap-3">
                                    <div className="space-y-2">
                                        <Label className="text-[11px] uppercase font-bold text-muted-foreground">Porta</Label>
                                        <Input
                                            type="number"
                                            value={smtpLocal.port}
                                            onChange={(e) => handleValueChange("smtp_global", "port", parseInt(e.target.value))}
                                            className="text-sm tabular-nums"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label className="text-[11px] uppercase font-bold text-muted-foreground">Remetente</Label>
                                        <Input
                                            value={smtpLocal.from}
                                            onChange={(e) => handleValueChange("smtp_global", "from", e.target.value)}
                                            placeholder="noreply@..."
                                            className="text-sm"
                                        />
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-[11px] uppercase font-bold text-muted-foreground">Usuário (Auth)</Label>
                                    <Input
                                        value={smtpLocal.user}
                                        onChange={(e) => handleValueChange("smtp_global", "user", e.target.value)}
                                        className="text-sm"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-[11px] uppercase font-bold text-muted-foreground">Senha / API Key</Label>
                                    <Input
                                        type="password"
                                        value={smtpLocal.pass || ""}
                                        onChange={(e) => handleValueChange("smtp_global", "pass", e.target.value)}
                                        placeholder="••••••••"
                                        className="text-sm"
                                    />
                                </div>
                            </CardContent>
                            <CardFooter className="flex justify-between border-t py-4 bg-muted/10">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => testSmtpMutation.mutate()}
                                    disabled={updateMutation.isPending || testSmtpMutation.isPending || !hasSmtp}
                                >
                                    {testSmtpMutation.isPending ? <Loader2 size={14} className="mr-1.5 animate-spin" /> : <Mail size={14} className="mr-1.5" />}
                                    Testar SMTP
                                </Button>
                                <Button
                                    size="sm"
                                    onClick={() => updateMutation.mutate({ chave: "smtp_global", valor: smtpLocal })}
                                    disabled={updateMutation.isPending || testSmtpMutation.isPending}
                                >
                                    {updateMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                                    Salvar
                                </Button>
                            </CardFooter>
                        </Card>

                        {/* STRIPE */}
                        <Card>
                            <CardHeader className="border-b border-muted/20 bg-muted/10">
                                <div className="flex items-center justify-between">
                                    <div className="space-y-0.5">
                                        <CardTitle className="flex items-center gap-2">
                                            <CreditCard className="size-4 text-primary" />
                                            Stripe
                                        </CardTitle>
                                        <CardDescription className="text-xs">Pagamentos & webhooks</CardDescription>
                                    </div>
                                    {hasStripe ? (
                                        <StatusBadge status="ativo" />
                                    ) : (
                                        <Badge variant="secondary" className="text-[10px]">.env</Badge>
                                    )}
                                </div>
                            </CardHeader>
                            <CardContent className="pt-6 space-y-4">
                                <div className="space-y-2">
                                    <Label className="text-[11px] uppercase font-bold text-muted-foreground">Secret Key</Label>
                                    <Input
                                        type="password"
                                        value={stripeLocal.secret_key}
                                        onChange={e => handleValueChange("stripe", "secret_key", e.target.value)}
                                        placeholder="sk_live_..."
                                        className="text-sm"
                                    />
                                    <p className="text-xs text-muted-foreground">sk_live_ para prod, sk_test_ para testes</p>
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-[11px] uppercase font-bold text-muted-foreground">Webhook Secret</Label>
                                    <Input
                                        type="password"
                                        value={stripeLocal.webhook_secret}
                                        onChange={e => handleValueChange("stripe", "webhook_secret", e.target.value)}
                                        placeholder="whsec_..."
                                        className="text-sm"
                                    />
                                    <p className="text-xs text-muted-foreground">Endpoint: <code className="bg-muted px-1 rounded text-[10px]">/api/v1/stripe/webhook</code></p>
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-[11px] uppercase font-bold text-muted-foreground">Frontend URL</Label>
                                    <Input
                                        value={stripeLocal.frontend_url}
                                        onChange={e => handleValueChange("stripe", "frontend_url", e.target.value)}
                                        placeholder="https://app.agrosaas.com.br"
                                        className="text-sm"
                                    />
                                </div>
                            </CardContent>
                            <CardFooter className="flex justify-end border-t py-4 bg-muted/10">
                                <Button
                                    size="sm"
                                    onClick={() => updateMutation.mutate({ chave: "stripe", valor: stripeLocal })}
                                    disabled={updateMutation.isPending}
                                >
                                    {updateMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                                    Salvar
                                </Button>
                            </CardFooter>
                        </Card>
                    </div>
                </TabsContent>

                {/* TAB: SEGURANÇA */}
                <TabsContent value="segurança" className="mt-6">
                    <div className="grid gap-6 grid-cols-1">
                        {/* BLOQUEIO POR TENTATIVAS DE SENHA */}
                        <Card>
                            <CardHeader className="border-b border-muted/20 bg-muted/10">
                                <div className="flex items-center justify-between">
                                    <div className="space-y-0.5">
                                        <CardTitle className="flex items-center gap-2">
                                            <Lock className="size-4 text-primary" />
                                            Proteção de Senha
                                        </CardTitle>
                                        <CardDescription className="text-xs">Bloqueio automático</CardDescription>
                                    </div>
                                    {hasBloqueioSenha ? (
                                        <StatusBadge status="ativo" />
                                    ) : (
                                        <Badge variant="secondary" className="text-[10px]">Padrão</Badge>
                                    )}
                                </div>
                            </CardHeader>
                            <CardContent className="pt-6 space-y-4">
                                <div className="flex items-center justify-between">
                                    <Label htmlFor="rate-limiting-ativo" className="text-[11px] uppercase font-bold text-muted-foreground">Ativo</Label>
                                    <Switch
                                        id="rate-limiting-ativo"
                                        checked={bloqueioSenhaLocal.rate_limiting_ativo}
                                        onCheckedChange={(checked) => handleValueChange("bloqueio_senha", "rate_limiting_ativo", checked)}
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label className="text-[11px] uppercase font-bold text-muted-foreground">Máx. Tentativas</Label>
                                    <Input
                                        type="number"
                                        min="1"
                                        max="20"
                                        value={bloqueioSenhaLocal.max_tentativas}
                                        onChange={(e) => handleValueChange("bloqueio_senha", "max_tentativas", parseInt(e.target.value) || 5)}
                                        className="text-sm tabular-nums"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label className="text-[11px] uppercase font-bold text-muted-foreground">Tempo Bloqueio (min)</Label>
                                    <Input
                                        type="number"
                                        min="1"
                                        max="1440"
                                        value={bloqueioSenhaLocal.tempo_bloqueio_minutos}
                                        onChange={(e) => handleValueChange("bloqueio_senha", "tempo_bloqueio_minutos", parseInt(e.target.value) || 15)}
                                        className="text-sm tabular-nums"
                                    />
                                </div>
                            </CardContent>
                            <CardFooter className="flex justify-end border-t py-4 bg-muted/10">
                                <Button
                                    size="sm"
                                    onClick={() => updateMutation.mutate({ chave: "bloqueio_senha", valor: bloqueioSenhaLocal })}
                                    disabled={updateMutation.isPending}
                                >
                                    {updateMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                                    Salvar
                                </Button>
                            </CardFooter>
                        </Card>
                    </div>
                </TabsContent>

                {/* TAB: UX */}
                <TabsContent value="ux" className="mt-6">
                    <div className="grid gap-6 grid-cols-1">
                        {/* INFORMAÇÕES PADRÃO DE DESENVOLVIMENTO */}
                        <Card>
                            <CardHeader className="border-b border-muted/20 bg-muted/10">
                                <div className="flex items-center justify-between">
                                    <div className="space-y-0.5">
                                        <CardTitle className="flex items-center gap-2">
                                            <Construction className="size-4 text-primary" />
                                            Tela Em Desenvolvimento
                                        </CardTitle>
                                        <CardDescription className="text-xs">Mensagens padrão</CardDescription>
                                    </div>
                                    {hasEmDesenvolvimento ? (
                                        <StatusBadge status="ativo" />
                                    ) : (
                                        <Badge variant="secondary" className="text-[10px]">Padrão</Badge>
                                    )}
                                </div>
                            </CardHeader>
                            <CardContent className="pt-6 space-y-4">
                                <div className="space-y-2">
                                    <Label className="text-[11px] uppercase font-bold text-muted-foreground">Título</Label>
                                    <Input
                                        value={emDesenvolvimentoLocal.titulo}
                                        onChange={(e) => handleValueChange("em_desenvolvimento", "titulo", e.target.value)}
                                        placeholder="Em Desenvolvimento"
                                        className="text-sm"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-[11px] uppercase font-bold text-muted-foreground">Descrição</Label>
                                    <Textarea
                                        value={emDesenvolvimentoLocal.descricao}
                                        onChange={(e) => handleValueChange("em_desenvolvimento", "descricao", e.target.value)}
                                        placeholder="Esta funcionalidade está sendo construída..."
                                        rows={2}
                                        className="text-sm"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-[11px] uppercase font-bold text-muted-foreground">Previsão (opcional)</Label>
                                    <Input
                                        value={emDesenvolvimentoLocal.previsao}
                                        onChange={(e) => handleValueChange("em_desenvolvimento", "previsao", e.target.value)}
                                        placeholder="ex: Q2 2026"
                                        className="text-sm"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-[11px] uppercase font-bold text-muted-foreground">URL de Retorno</Label>
                                    <Input
                                        value={emDesenvolvimentoLocal.voltarPara}
                                        onChange={(e) => handleValueChange("em_desenvolvimento", "voltarPara", e.target.value)}
                                        placeholder="/dashboard"
                                        className="text-sm"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-[11px] uppercase font-bold text-muted-foreground">Funcionalidades (JSON)</Label>
                                    <Textarea
                                        value={typeof emDesenvolvimentoLocal.funcionalidades === 'string' ? emDesenvolvimentoLocal.funcionalidades : JSON.stringify(emDesenvolvimentoLocal.funcionalidades || [], null, 2)}
                                        onChange={(e) => {
                                            try {
                                                const parsed = JSON.parse(e.target.value);
                                                handleValueChange("em_desenvolvimento", "funcionalidades", parsed);
                                            } catch {
                                                handleValueChange("em_desenvolvimento", "funcionalidades", e.target.value);
                                            }
                                        }}
                                        placeholder='["Feature 1", "Feature 2"]'
                                        rows={3}
                                        className="text-sm"
                                    />
                                </div>
                            </CardContent>
                            <CardFooter className="flex justify-end border-t py-4 bg-muted/10">
                                <Button
                                    size="sm"
                                    onClick={() => updateMutation.mutate({ chave: "em_desenvolvimento", valor: emDesenvolvimentoLocal })}
                                    disabled={updateMutation.isPending}
                                >
                                    {updateMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                                    Salvar
                                </Button>
                            </CardFooter>
                        </Card>

                        {/* MAINTENANCE MODE (em breve) */}
                        <Card className="opacity-50 grayscale cursor-not-allowed">
                            <CardHeader>
                                <CardTitle className="text-base text-balance">Modo de Manutenção</CardTitle>
                                <CardDescription>Bloquear acesso de todos os Tenants para manutenção programada (em breve)</CardDescription>
                            </CardHeader>
                        </Card>
                    </div>
                </TabsContent>
            </Tabs>
        </div>
    );
}
