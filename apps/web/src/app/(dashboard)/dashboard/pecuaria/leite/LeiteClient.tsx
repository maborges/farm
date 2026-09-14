"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useHasModule } from "@/hooks/use-has-module";
import { Modulos } from "@/lib/constants/modulos";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Milk, Plus, LineChart, Activity, Droplets } from "lucide-react";
import { toast } from "sonner";

type Resumo = { total_registros: number; volume_total_litros: number; media_volume_litros: number; media_gordura_pct: number; media_proteina_pct: number };
type Producao = { id: string; data: string; turno: string; volume_litros: number; gordura_pct?: number | null; proteina_pct?: number | null; destino?: string | null; preco_litro?: number | null; valor_total?: number | null };

const cols: ColumnDef<Producao>[] = [
  { id: "data", accessorKey: "data", header: "Data", cell: ({ row }) => new Date(row.original.data).toLocaleDateString("pt-BR") },
  { id: "turno", accessorKey: "turno", header: "Turno" },
  { id: "volume_litros", accessorKey: "volume_litros", header: "Volume", cell: ({ row }) => `${row.original.volume_litros.toFixed(2)} L` },
  { id: "gordura_pct", accessorKey: "gordura_pct", header: "Gordura", cell: ({ row }) => row.original.gordura_pct?.toFixed(2) ?? "-" },
  { id: "proteina_pct", accessorKey: "proteina_pct", header: "Proteína", cell: ({ row }) => row.original.proteina_pct?.toFixed(2) ?? "-" },
  { id: "destino", accessorKey: "destino", header: "Destino", cell: ({ row }) => <Badge variant="outline">{row.original.destino ?? "-"}</Badge> },
];

export default function LeiteClient() {
  const qc = useQueryClient();
  const hasModule = useHasModule(Modulos.PECUARIA_LEITE);
  const [open, setOpen] = React.useState(false);
  const [form, setForm] = React.useState({ unidade_produtiva_id: "", animal_id: "", lote_id: "", data: new Date().toISOString().slice(0, 10), turno: "MANHA", volume_litros: "", gordura_pct: "", proteina_pct: "", destino: "LATICINIO", preco_litro: "", valor_total: "" });

  const { data: resumo } = useQuery<Resumo>({ queryKey: ["pecuaria", "leite", "dashboard"], queryFn: () => apiFetch("/pecuaria/leite/dashboard"), enabled: hasModule });
  const { data: registros = [] } = useQuery<Producao[]>({ queryKey: ["pecuaria", "leite", "producao"], queryFn: () => apiFetch("/pecuaria/leite/producao"), enabled: hasModule, initialData: [] });

  const createMutation = useMutation({ mutationFn: (payload: Record<string, unknown>) => apiFetch("/pecuaria/leite/producao", { method: "POST", body: JSON.stringify(payload) }), onSuccess: () => { qc.invalidateQueries({ queryKey: ["pecuaria", "leite"] }); setOpen(false); toast.success("Produção registrada"); } });

  if (!hasModule) return <div className="p-6"><Card><CardContent className="py-10 text-center text-sm text-muted-foreground">O módulo de leite não está contratado para este produtor.</CardContent></Card></div>;

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Pecuária Leiteira"
        description="Produção, qualidade e destino do leite."
        icon={<Milk className="text-primary" size={22} />}
        breadcrumbs={[{ label: "Dashboard", href: "/dashboard" }, { label: "Pecuária", href: "/dashboard/pecuaria" }, { label: "Leite" }]}
        actions={
          <Button variant="outline" size="sm" className="rounded-sm" onClick={() => setOpen(true)}>
            <Plus className="mr-1.5 size-3.5" /> Registrar produção
          </Button>
        }
      />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-5 pb-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-2xl font-bold leading-none">{resumo?.total_registros ?? 0}</div>
                <div className="text-xs text-muted-foreground mt-1.5 leading-tight">Registros</div>
              </div>
              <div className="p-2 bg-muted rounded-sm text-blue-600">
                <Activity className="size-5" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5 pb-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-2xl font-bold leading-none">{(resumo?.volume_total_litros ?? 0).toFixed(2)}</div>
                <div className="text-xs text-muted-foreground mt-1.5 leading-tight">Volume total (L)</div>
              </div>
              <div className="p-2 bg-muted rounded-sm text-blue-400">
                <Milk className="size-5" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5 pb-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-2xl font-bold leading-none">{(resumo?.media_gordura_pct ?? 0).toFixed(2)}%</div>
                <div className="text-xs text-muted-foreground mt-1.5 leading-tight">Gordura média</div>
              </div>
              <div className="p-2 bg-muted rounded-sm text-amber-500">
                <Droplets className="size-5" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5 pb-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-2xl font-bold leading-none">{(resumo?.media_proteina_pct ?? 0).toFixed(2)}%</div>
                <div className="text-xs text-muted-foreground mt-1.5 leading-tight">Proteína média</div>
              </div>
              <div className="p-2 bg-muted rounded-sm text-green-600">
                <LineChart className="size-5" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Produção diária</CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <DataTable columns={cols} data={registros} />
        </CardContent>
      </Card>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nova produção de leite</DialogTitle>
            <DialogDescription>Registre volume, turno e qualidade.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 md:grid-cols-2">
            <Input placeholder="Unidade produtiva ID" value={form.unidade_produtiva_id} onChange={(e) => setForm({ ...form, unidade_produtiva_id: e.target.value })} />
            <Input placeholder="Animal ID" value={form.animal_id} onChange={(e) => setForm({ ...form, animal_id: e.target.value })} />
            <Input placeholder="Lote ID" value={form.lote_id} onChange={(e) => setForm({ ...form, lote_id: e.target.value })} />
            <Input type="date" value={form.data} onChange={(e) => setForm({ ...form, data: e.target.value })} />
            <Select value={form.turno} onValueChange={(v) => setForm({ ...form, turno: v })}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="MANHA">Manhã</SelectItem>
                <SelectItem value="TARDE">Tarde</SelectItem>
                <SelectItem value="NOITE">Noite</SelectItem>
                <SelectItem value="UNICA">Única</SelectItem>
              </SelectContent>
            </Select>
            <Input placeholder="Volume litros" value={form.volume_litros} onChange={(e) => setForm({ ...form, volume_litros: e.target.value })} />
            <Input placeholder="Gordura %" value={form.gordura_pct} onChange={(e) => setForm({ ...form, gordura_pct: e.target.value })} />
            <Input placeholder="Proteína %" value={form.proteina_pct} onChange={(e) => setForm({ ...form, proteina_pct: e.target.value })} />
            <Input placeholder="Preço/L" value={form.preco_litro} onChange={(e) => setForm({ ...form, preco_litro: e.target.value })} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button>
            <Button onClick={() => createMutation.mutate({ unidade_produtiva_id: Number(form.unidade_produtiva_id), animal_id: form.animal_id ? Number(form.animal_id) : undefined, lote_id: form.lote_id ? Number(form.lote_id) : undefined, data: form.data, turno: form.turno, volume_litros: Number(form.volume_litros), gordura_pct: form.gordura_pct ? Number(form.gordura_pct) : undefined, proteina_pct: form.proteina_pct ? Number(form.proteina_pct) : undefined, preco_litro: form.preco_litro ? Number(form.preco_litro) : undefined, destino: "LATICINIO" })}>Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
