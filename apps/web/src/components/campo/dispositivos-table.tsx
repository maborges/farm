"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ShieldOff, Wifi, WifiOff, Smartphone } from "lucide-react";
import { toast } from "sonner";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";
import { DataTable, ColumnDef } from "@/components/ui/data-table";
import { cn } from "@/lib/utils";
import { Copy, CheckCheck } from "lucide-react";

interface Dispositivo {
  id: string;
  nome: string;
  status: string;
  modulos: string[];
  last_seen_at: string | null;
  last_sync_at: string | null;
  expires_at: string;
  created_at: string;
}

interface ReactivateResult {
  id: string;
  nome: string;
  activation_code: string;
  activation_code_expires_at: string;
  expires_at: string;
  status: string;
}

const STATUS_CONFIG: Record<string, { label: string }> = {
  PENDENTE: { label: "Aguardando ativação" },
  ATIVO:    { label: "Ativo" },
  REVOGADO: { label: "Revogado" },
  EXPIRADO: { label: "Expirado" },
};

const getBadgeClass = (status: string) => {
  if (status === "ATIVO")    return "bg-emerald-500/10 text-emerald-600 border-emerald-500/20";
  if (status === "PENDENTE") return "bg-amber-500/10 text-amber-600 border-amber-500/20";
  if (status === "REVOGADO") return "bg-red-500/10 text-red-600 border-red-500/20";
  return "";
};

export function DispositivosTable() {
  const queryClient = useQueryClient();
  const [revogarId, setRevogarId] = useState<string | null>(null);
  const [reativarResult, setReativarResult] = useState<ReactivateResult | null>(null);
  const [copied, setCopied] = useState(false);

  const { data: dispositivos = [], isLoading } = useQuery<Dispositivo[]>({
    queryKey: ["campo-dispositivos"],
    queryFn: () => apiFetch("/campo/devices"),
  });

  const revogar = useMutation({
    mutationFn: (id: string) =>
      apiFetch("/campo/devices/revoke", {
        method: "POST",
        body: JSON.stringify({ device_id: id }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campo-dispositivos"] });
      toast.success("Dispositivo revogado com sucesso.");
      setRevogarId(null);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const reativar = useMutation({
    mutationFn: (id: string) =>
      apiFetch("/campo/devices/reactivate", {
        method: "POST",
        body: JSON.stringify({ device_id: id, expires_days: 30 }),
      }),
    onSuccess: (data: ReactivateResult) => {
      queryClient.invalidateQueries({ queryKey: ["campo-dispositivos"] });
      setReativarResult(data);
      toast.success("Código de reativação gerado.");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  async function copiarCodigo() {
    if (!reativarResult) return;
    await navigator.clipboard.writeText(reativarResult.activation_code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast.success("Código copiado para a área de transferência.");
  }

  const columns: ColumnDef<Dispositivo>[] = [
    {
      id: "dispositivo",
      header: "Dispositivo",
      accessorKey: "nome",
      cell: (value, row) => {
        const isOnline = row.last_seen_at
          ? Date.now() - new Date(row.last_seen_at).getTime() < 5 * 60 * 1000
          : false;
        
        return (
          <div className="flex items-center gap-3">
            <div className="relative shrink-0 p-2 bg-muted/50 rounded-sm">
              <Smartphone className="size-4 text-muted-foreground" />
              {row.status === "ATIVO" && (
                <span className="absolute -top-1 -right-1 flex size-3 items-center justify-center rounded-full bg-background">
                  {isOnline
                    ? <Wifi className="size-2.5 text-emerald-500" />
                    : <WifiOff className="size-2.5 text-muted-foreground/50" />}
                </span>
              )}
            </div>
            <div className="flex flex-col">
              <span className="font-medium text-sm">{value}</span>
              <span className="text-[10px] text-muted-foreground font-mono uppercase">
                ID: {row.id.slice(0, 8)}
              </span>
            </div>
          </div>
        );
      }
    },
    {
      id: "status",
      header: "Status",
      accessorKey: "status",
      cell: (value) => (
        <Badge
          variant="outline"
          className={cn("rounded-sm font-medium", getBadgeClass(value))}
        >
          {STATUS_CONFIG[value]?.label ?? value}
        </Badge>
      )
    },
    {
      id: "last_sync",
      header: "Última Sincronização",
      accessorKey: "last_sync_at",
      cell: (value) => value 
        ? formatDistanceToNow(new Date(value), { locale: ptBR, addSuffix: true })
        : <span className="text-muted-foreground">—</span>
    },
    {
      id: "expires",
      header: "Expira em",
      accessorKey: "expires_at",
      cell: (value) => formatDistanceToNow(new Date(value), { locale: ptBR, addSuffix: true })
    },
    {
      id: "acoes",
      header: "",
      exportable: false,
      sortable: false,
      filterable: false,
      cell: (_, row) => (
        <div className="flex items-center justify-end">
          {(row.status === "ATIVO" || row.status === "PENDENTE") && (
            <Button
              size="icon"
              variant="ghost"
              className="size-8 rounded-sm text-muted-foreground hover:text-destructive transition-colors"
              title="Revogar Acesso"
              onClick={() => setRevogarId(row.id)}
              >
                <ShieldOff className="size-4" />
              </Button>
            )}
          {(row.status === "REVOGADO" || row.status === "EXPIRADO") && (
            <Button
              size="sm"
              variant="outline"
              className="h-8 rounded-sm text-xs"
              onClick={() => reativar.mutate(row.id)}
              disabled={reativar.isPending}
            >
              Reativar
            </Button>
          )}
        </div>
      )
    }
  ];

  return (
    <>
      <div className="bg-card border border-border rounded-sm shadow-sm">
        <DataTable
          data={dispositivos}
          columns={columns}
          isLoading={isLoading}
          exportFileName="dispositivos-campo"
          searchPlaceholder="Buscar dispositivo..."
        />
      </div>

      <AlertDialog open={!!revogarId} onOpenChange={(open) => !open && setRevogarId(null)}>
        <AlertDialogContent className="rounded-sm">
          <AlertDialogHeader>
            <AlertDialogTitle>Revogar dispositivo?</AlertDialogTitle>
            <AlertDialogDescription>
              O dispositivo perderá acesso imediatamente a todas as informações e recursos de campo. 
              Esta ação é irreversível e exigirá uma nova ativação.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="rounded-sm">Cancelar</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-white hover:bg-destructive/90 rounded-sm"
              onClick={() => revogarId && revogar.mutate(revogarId)}
            >
              Revogar Acesso
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={!!reativarResult} onOpenChange={(open) => !open && setReativarResult(null)}>
        <DialogContent className="sm:max-w-md rounded-sm">
          <DialogHeader>
            <DialogTitle>Dispositivo reativado</DialogTitle>
            <DialogDescription>
              Repasse o novo código ao operador para que o mesmo aparelho recupere acesso e sincronize os dados pendentes.
            </DialogDescription>
          </DialogHeader>

          {reativarResult && (
            <div className="space-y-5">
              <div className="flex flex-col items-center gap-3 rounded-sm border bg-muted/30 p-6 text-center">
                <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground">
                  Novo código
                </span>
                <span className="font-mono text-3xl font-black tracking-[0.28em] text-primary select-all">
                  {reativarResult.activation_code}
                </span>
                <Button variant="outline" size="sm" onClick={copiarCodigo} className="mt-1 gap-1.5 rounded-sm">
                  {copied ? <CheckCheck className="size-3.5 text-emerald-500" /> : <Copy className="size-3.5" />}
                  {copied ? "Copiado!" : "Copiar código"}
                </Button>
              </div>
              <div className="rounded-sm border bg-background text-xs">
                <div className="flex justify-between border-b px-4 py-2.5">
                  <span className="text-muted-foreground">Dispositivo</span>
                  <span className="font-semibold">{reativarResult.nome}</span>
                </div>
                <div className="flex justify-between px-4 py-2.5">
                  <span className="text-muted-foreground">Expira em</span>
                  <span className="font-semibold text-orange-600">
                    {new Date(reativarResult.activation_code_expires_at).toLocaleString("pt-BR")}
                  </span>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" className="w-full rounded-sm" onClick={() => setReativarResult(null)}>
                  Concluído
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
