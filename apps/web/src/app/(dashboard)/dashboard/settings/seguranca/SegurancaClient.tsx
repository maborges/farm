"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { useState } from "react";
import { Shield, Lock, Clock, AlertTriangle, Save } from "lucide-react";
import { PageHeader } from "@/components/shared";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";

export interface SegurancaConfig {
    rate_limiting_ativo: boolean;
    max_tentativas: number;
    tempo_bloqueio_minutos: number;
}

export function SegurancaClient({ initialConfig }: { initialConfig: SegurancaConfig | null }) {
    const queryClient = useQueryClient();
    const [showDisableAlert, setShowDisableAlert] = useState(false);
    const [pendingValue, setPendingValue] = useState<boolean | null>(null);

    const { data: config, isLoading } = useQuery<SegurancaConfig>({
        queryKey: ["config", "seguranca"],
        queryFn: () => apiFetch("/config/seguranca"),
        initialData: initialConfig || undefined,
    });

    const updateMutation = useMutation({
        mutationFn: (data: Partial<SegurancaConfig>) =>
            apiFetch("/config/seguranca", {
                method: "PATCH",
                body: JSON.stringify(data),
            }),
        onSuccess: () => {
            toast.success("Configurações de segurança salvas!");
            queryClient.invalidateQueries({ queryKey: ["config", "seguranca"] });
        },
        onError: (err: Error) => toast.error(err.message),
    });

    const handleToggleChange = (checked: boolean) => {
        if (!checked) {
            setPendingValue(checked);
            setShowDisableAlert(true);
        } else {
            updateMutation.mutate({ rate_limiting_ativo: true });
        }
    };

    const confirmDisable = () => {
        updateMutation.mutate({ rate_limiting_ativo: false });
        setShowDisableAlert(false);
        setPendingValue(null);
    };

    if (isLoading) {
        return (
            <div className="p-8 space-y-6">
                <Skeleton className="h-10 w-64" />
                <Skeleton className="h-48 w-full rounded-sm" />
            </div>
        );
    }

    return (
        <div className="p-8 space-y-8 w-full max-w-full">
            <PageHeader
                title="Segurança"
                description="Configure o bloqueio automático por tentativas de login."
            />

            <Card className="max-w-2xl">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Shield size={20} className="text-primary" />
                        Proteção contra força bruta
                    </CardTitle>
                    <CardDescription>
                        Bloqueia temporariamente o acesso após múltiplas tentativas de login com falha.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    {/* Toggle Ativar/Desativar */}
                    <div className="flex items-center justify-between rounded-lg border p-4 bg-card">
                        <div className="space-y-0.5">
                            <Label className="text-base flex items-center gap-2">
                                <Lock size={16} className="text-muted-foreground" />
                                Bloqueio automático
                            </Label>
                            <p className="text-sm text-muted-foreground">
                                {config?.rate_limiting_ativo
                                    ? "Ativo — usuários serão bloqueados após exceder o limite de tentativas."
                                    : "Desativado — nenhuma tentativa de login será bloqueada."}
                            </p>
                        </div>
                        <Switch
                            checked={config?.rate_limiting_ativo ?? true}
                            onCheckedChange={handleToggleChange}
                            disabled={updateMutation.isPending}
                        />
                    </div>

                    {/* Quantidade de tentativas */}
                    <div className="space-y-2">
                        <Label className="flex items-center gap-2">
                            <AlertTriangle size={16} className="text-muted-foreground" />
                            Máximo de tentativas
                        </Label>
                        <p className="text-sm text-muted-foreground">
                            Número de tentativas de login com falha antes do bloqueio.
                        </p>
                        <div className="flex items-center gap-2">
                            <Input
                                type="number"
                                min={1}
                                max={20}
                                value={config?.max_tentativas ?? 5}
                                onChange={(e) => {
                                    const val = parseInt(e.target.value, 10);
                                    if (val >= 1 && val <= 20) {
                                        updateMutation.mutate({ max_tentativas: val });
                                    }
                                }}
                                onBlur={(e) => {
                                    const val = parseInt(e.target.value, 10);
                                    if (isNaN(val) || val < 1) {
                                        updateMutation.mutate({ max_tentativas: 1 });
                                    } else if (val > 20) {
                                        updateMutation.mutate({ max_tentativas: 20 });
                                    }
                                }}
                                disabled={updateMutation.isPending || !config?.rate_limiting_ativo}
                                className="w-24"
                            />
                            <span className="text-sm text-muted-foreground">tentativas</span>
                        </div>
                    </div>

                    {/* Tempo de bloqueio */}
                    <div className="space-y-2">
                        <Label className="flex items-center gap-2">
                            <Clock size={16} className="text-muted-foreground" />
                            Tempo de bloqueio
                        </Label>
                        <p className="text-sm text-muted-foreground">
                            Quanto tempo o usuário fica bloqueado após exceder o limite.
                        </p>
                        <div className="flex items-center gap-2">
                            <Input
                                type="number"
                                min={1}
                                max={1440}
                                value={config?.tempo_bloqueio_minutos ?? 15}
                                onChange={(e) => {
                                    const val = parseInt(e.target.value, 10);
                                    if (val >= 1 && val <= 1440) {
                                        updateMutation.mutate({ tempo_bloqueio_minutos: val });
                                    }
                                }}
                                onBlur={(e) => {
                                    const val = parseInt(e.target.value, 10);
                                    if (isNaN(val) || val < 1) {
                                        updateMutation.mutate({ tempo_bloqueio_minutos: 1 });
                                    } else if (val > 1440) {
                                        updateMutation.mutate({ tempo_bloqueio_minutos: 1440 });
                                    }
                                }}
                                disabled={updateMutation.isPending || !config?.rate_limiting_ativo}
                                className="w-24"
                            />
                            <span className="text-sm text-muted-foreground">minutos</span>
                        </div>
                    </div>

                    {/* Resumo visual */}
                    {config?.rate_limiting_ativo && (
                        <Alert variant="warning">
                            <AlertDescription className="font-medium">
                                🔒 Regra atual: bloquear após <strong>{config.max_tentativas}</strong> tentativas
                                falhas, com desbloqueio automático em <strong>{config.tempo_bloqueio_minutos}</strong> minutos.
                            </AlertDescription>
                        </Alert>
                    )}

                    {/* Botão salvar */}
                    <Button
                        variant="ghost"
                        size="sm"
                        className="gap-2"
                        onClick={() => queryClient.invalidateQueries({ queryKey: ["config", "seguranca"] })}
                        disabled={updateMutation.isPending}
                    >
                        <Save size={14} />
                        {updateMutation.isPending ? "Salvando..." : "Configurações salvas automaticamente"}
                    </Button>
                </CardContent>
            </Card>

            {/* Alerta de desativação */}
            <AlertDialog open={showDisableAlert} onOpenChange={setShowDisableAlert}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle className="flex items-center gap-2">
                            <AlertTriangle size={18} className="text-amber-500" />
                            Desativar proteção?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            Ao desativar o bloqueio automático, qualquer pessoa poderá tentar
                            fazer login infinitas vezes sem ser bloqueada. Isso aumenta o risco
                            de ataques de força bruta.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Manter ativado</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={confirmDisable}
                            className="bg-amber-500 hover:bg-amber-600"
                        >
                            Desativar mesmo assim
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
