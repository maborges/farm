"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { Monitor, Smartphone, Globe, LogOut, ShieldAlert, Users } from "lucide-react";
import { PageHeader } from "@/components/shared";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
    AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";

export interface Sessao {
    id: string;
    ip_address: string | null;
    user_agent: string | null;
    inicio: string;
    ultimo_heartbeat: string;
    expira_em: string;
    status: string;
    is_current: boolean;
    usuario_id?: string;
    usuario_apelido?: string | null;
}

function parseDevice(userAgent: string | null): { icon: React.ReactNode; label: string } {
    if (!userAgent) return { icon: <Globe size={16} />, label: "Desconhecido" };
    const ua = userAgent.toLowerCase();
    if (ua.includes("mobile") || ua.includes("android") || ua.includes("iphone")) {
        return { icon: <Smartphone size={16} />, label: "Dispositivo Móvel" };
    }
    return { icon: <Monitor size={16} />, label: "Computador" };
}

function formatRelative(dateStr: string): string {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "agora mesmo";
    if (mins < 60) return `há ${mins} min`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `há ${hours}h`;
    return `há ${Math.floor(hours / 24)}d`;
}

function SessaoRow({
    sessao,
    onRevoke,
    isPending,
    showUser,
}: {
    sessao: Sessao;
    onRevoke: (id: string) => void;
    isPending: boolean;
    showUser?: boolean;
}) {
    const device = parseDevice(sessao.user_agent);
    return (
        <TableRow>
            {showUser && (
                <TableCell>
                    <div className="font-medium text-sm">{sessao.usuario_apelido || "Usuário"}</div>
                </TableCell>
            )}
            <TableCell>
                <div className="flex items-center gap-2 text-sm">
                    {device.icon}
                    <div>
                        <p className="font-medium">{device.label}</p>
                        <p className="text-xs text-muted-foreground truncate max-w-xs">
                            {sessao.user_agent ?? "—"}
                        </p>
                    </div>
                </div>
            </TableCell>
            <TableCell className="text-sm text-muted-foreground">
                {sessao.ip_address ?? "—"}
            </TableCell>
            <TableCell className="text-sm text-muted-foreground">
                {formatRelative(sessao.ultimo_heartbeat)}
            </TableCell>
            <TableCell>
                {sessao.is_current ? (
                    <Badge variant="default">Sessão atual</Badge>
                ) : (
                    <Badge variant="outline">Ativa</Badge>
                )}
            </TableCell>
            <TableCell className="text-right">
                {!sessao.is_current && (
                    <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive hover:text-destructive gap-0"
                        onClick={() => onRevoke(sessao.id)}
                        disabled={isPending}
                        title="Encerrar"
                    >
                        <LogOut size={14} />
                    </Button>
                )}
            </TableCell>
        </TableRow>
    );
}

export function SessoesClient({ initialSessoes, initialTeam }: { initialSessoes: Sessao[], initialTeam?: Sessao[] }) {
    const queryClient = useQueryClient();

    const { data: minhasSessoes, isLoading } = useQuery<Sessao[]>({
        queryKey: ["sessoes", "me"],
        queryFn: () => apiFetch("/auth/sessions/me"),
        initialData: initialSessoes,
    });

    const { data: sessoesMembros, isLoading: isLoadingTeam } = useQuery<Sessao[]>({
        queryKey: ["sessoes", "team"],
        queryFn: () => apiFetch("/auth/sessions/team"),
        // Silencia erro 403 se o usuário não tem permissão de owner/admin
        retry: false,
        initialData: initialTeam,
    });

    const revogarMutation = useMutation({
        mutationFn: (id: string) =>
            apiFetch(`/auth/sessions/me/${id}`, { method: "DELETE" }),
        onSuccess: () => {
            toast.success("Sessão encerrada.");
            queryClient.invalidateQueries({ queryKey: ["sessoes"] });
        },
        onError: (err: Error) => toast.error(err.message),
    });

    const revogarMembroMutation = useMutation({
        mutationFn: (id: string) =>
            apiFetch(`/auth/sessions/team/${id}`, { method: "DELETE" }),
        onSuccess: () => {
            toast.success("Sessão do membro encerrada.");
            queryClient.invalidateQueries({ queryKey: ["sessoes"] });
        },
        onError: (err: Error) => toast.error(err.message),
    });

    const revogarTodasMutation = useMutation({
        mutationFn: () => apiFetch("/auth/sessions/me", { method: "DELETE" }),
        onSuccess: () => {
            toast.success("Todas as outras sessões foram encerradas.");
            queryClient.invalidateQueries({ queryKey: ["sessoes"] });
        },
        onError: (err: Error) => toast.error(err.message),
    });

    const outrosSessoes = minhasSessoes?.filter((s) => !s.is_current) ?? [];

    return (
        <div className="p-8 space-y-8 w-full max-w-full">
            <PageHeader
                title="Sessões Ativas"
                description="Veja e gerencie os dispositivos conectados à sua conta."
            />

            {/* Minhas sessões */}
            <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                        <CardTitle className="flex items-center gap-2">
                            <Monitor size={18} className="text-primary" />
                            Meus dispositivos
                        </CardTitle>
                        <CardDescription>
                            Dispositivos com sessão ativa na sua conta.
                        </CardDescription>
                    </div>
                    {outrosSessoes.length > 1 && (
                        <AlertDialog>
                            <AlertDialogTrigger asChild>
                                <Button variant="outline" size="sm" className="gap-2 text-destructive border-destructive/30 hover:bg-destructive/10">
                                    <ShieldAlert size={14} />
                                    Encerrar outros ({outrosSessoes.length})
                                </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                                <AlertDialogHeader>
                                    <AlertDialogTitle>Encerrar todas as outras sessões?</AlertDialogTitle>
                                    <AlertDialogDescription>
                                        Todos os outros dispositivos serão desconectados. Sua sessão atual permanece ativa.
                                    </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                    <AlertDialogCancel>Cancelar</AlertDialogCancel>
                                    <AlertDialogAction
                                        className="bg-destructive hover:bg-destructive/90"
                                        onClick={() => revogarTodasMutation.mutate()}
                                    >
                                        Encerrar tudo
                                    </AlertDialogAction>
                                </AlertDialogFooter>
                            </AlertDialogContent>
                        </AlertDialog>
                    )}
                </CardHeader>
                <CardContent>
                    {isLoading ? (
                        <div className="space-y-3">
                            {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
                        </div>
                    ) : !minhasSessoes?.length ? (
                        <p className="text-sm text-muted-foreground py-4 text-center">
                            Nenhuma sessão ativa encontrada.
                        </p>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-muted/5 hover:bg-transparent">
                                    <TableHead className="font-bold text-[10px] uppercase tracking-wider">Dispositivo</TableHead>
                                    <TableHead className="font-bold text-[10px] uppercase tracking-wider">IP</TableHead>
                                    <TableHead className="font-bold text-[10px] uppercase tracking-wider">Último acesso</TableHead>
                                    <TableHead className="font-bold text-[10px] uppercase tracking-wider">Status</TableHead>
                                    <TableHead className="text-right font-bold text-[10px] uppercase tracking-wider" />
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {minhasSessoes.map((s) => (
                                    <SessaoRow
                                        key={s.id}
                                        sessao={s}
                                        onRevoke={(id) => revogarMutation.mutate(id)}
                                        isPending={revogarMutation.isPending}
                                    />
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>

            {/* Sessões da equipe — visível apenas para owner/admin */}
            {sessoesMembros && sessoesMembros.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Users size={18} className="text-primary" />
                            Sessões da equipe
                        </CardTitle>
                        <CardDescription>
                            Sessões ativas de membros da sua organização.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {isLoadingTeam ? (
                            <div className="space-y-3">
                                {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
                            </div>
                        ) : (
                            <Table>
                                <TableHeader>
                                    <TableRow className="bg-muted/5 hover:bg-transparent">
                                        <TableHead className="font-bold text-[10px] uppercase tracking-wider">Membro</TableHead>
                                        <TableHead className="font-bold text-[10px] uppercase tracking-wider">Dispositivo</TableHead>
                                        <TableHead className="font-bold text-[10px] uppercase tracking-wider">IP</TableHead>
                                        <TableHead className="font-bold text-[10px] uppercase tracking-wider">Último acesso</TableHead>
                                        <TableHead className="font-bold text-[10px] uppercase tracking-wider">Status</TableHead>
                                        <TableHead className="text-right font-bold text-[10px] uppercase tracking-wider" />
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {sessoesMembros.map((s) => (
                                        <SessaoRow
                                            key={s.id}
                                            sessao={s}
                                            onRevoke={(id) => revogarMembroMutation.mutate(id)}
                                            isPending={revogarMembroMutation.isPending}
                                            showUser={true}
                                        />
                                    ))}
                                </TableBody>
                            </Table>
                        )}
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
