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
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Warehouse, Plus, Beef, Salad, Layers, Activity } from "lucide-react";
import { toast } from "sonner";

type Resumo = { total_lotes: number; total_animais: number; total_racoes: number; total_cochos: number; gmd_medio: number; conversao_media: number };
type Lote = { id: number; codigo: string; total_animais?: number | null; status: string; ganho_medio_diario?: number | null; conversao_alimentar?: number | null };
type Racao = { id: number; nome: string; proteina_bruta?: number | null; custo_por_tonelada?: number | null; ativa: boolean };
type Cocho = { id: number; codigo: string; lote_id: number; consumo_kg?: number | null; data: string };

const lotesCols: ColumnDef<Lote>[] = [
  { id: "codigo", accessorKey: "codigo", header: "Código" },
  { id: "total_animais", accessorKey: "total_animais", header: "Animais", cell: ({ row }) => row.original.total_animais ?? 0 },
  { id: "ganho_medio_diario", accessorKey: "ganho_medio_diario", header: "GMD", cell: ({ row }) => row.original.ganho_medio_diario?.toFixed(2) ?? "-" },
  { id: "conversao_alimentar", accessorKey: "conversao_alimentar", header: "Conversão", cell: ({ row }) => row.original.conversao_alimentar?.toFixed(2) ?? "-" },
  { id: "status", accessorKey: "status", header: "Status", cell: ({ row }) => <Badge variant="outline">{row.original.status}</Badge> },
];

const racoesCols: ColumnDef<Racao>[] = [
  { id: "nome", accessorKey: "nome", header: "Nome" },
  { id: "proteina_bruta", accessorKey: "proteina_bruta", header: "PB%", cell: ({ row }) => row.original.proteina_bruta?.toFixed(2) ?? "-" },
  { id: "custo_por_tonelada", accessorKey: "custo_por_tonelada", header: "Custo/t", cell: ({ row }) => row.original.custo_por_tonelada?.toFixed(2) ?? "-" },
  { id: "ativa", accessorKey: "ativa", header: "Ativa", cell: ({ row }) => <Badge variant={row.original.ativa ? "default" : "outline"}>{row.original.ativa ? "Sim" : "Não"}</Badge> },
];

const cochosCols: ColumnDef<Cocho>[] = [
  { id: "codigo", accessorKey: "codigo", header: "Código" },
  { id: "lote_id", accessorKey: "lote_id", header: "Lote" },
  { id: "consumo_kg", accessorKey: "consumo_kg", header: "Consumo", cell: ({ row }) => row.original.consumo_kg?.toFixed(2) ?? "-" },
  { id: "data", accessorKey: "data", header: "Data", cell: ({ row }) => new Date(row.original.data).toLocaleDateString("pt-BR") },
];

export default function ConfinamentoClient() {
  const qc = useQueryClient();
  const hasModule = useHasModule(Modulos.PECUARIA_CONFINAMENTO);
  const [loteOpen, setLoteOpen] = React.useState(false);
  const [racaoOpen, setRacaoOpen] = React.useState(false);
  const [cochoOpen, setCochoOpen] = React.useState(false);
  const [formLote, setFormLote] = React.useState({ codigo: "", total_animais: "", peso_inicial_kg: "", data_entrada: new Date().toISOString().slice(0, 10), status: "confinado" });
  const [formRacao, setFormRacao] = React.useState({ nome: "", ingredientes: '{"milho":60,"silagem":35,"nucleo":5}', proteina_bruta: "", custo_por_tonelada: "" });
  const [formCocho, setFormCocho] = React.useState({ lote_id: "", codigo: "", consumo_kg: "", data: new Date().toISOString().slice(0, 10) });

  const { data: resumo } = useQuery<Resumo>({ queryKey: ["pecuaria", "confinamento", "dashboard"], queryFn: () => apiFetch("/pecuaria/confinamento/dashboard"), enabled: hasModule });
  const { data: lotes = [] } = useQuery<Lote[]>({ queryKey: ["pecuaria", "confinamento", "lotes"], queryFn: () => apiFetch("/pecuaria/confinamento/lotes"), enabled: hasModule, initialData: [] });
  const { data: racoes = [] } = useQuery<Racao[]>({ queryKey: ["pecuaria", "confinamento", "racoes"], queryFn: () => apiFetch("/pecuaria/confinamento/racoes"), enabled: hasModule, initialData: [] });
  const { data: cochos = [] } = useQuery<Cocho[]>({ queryKey: ["pecuaria", "confinamento", "cochos"], queryFn: () => apiFetch("/pecuaria/confinamento/cochos"), enabled: hasModule, initialData: [] });

  const createLote = useMutation({ mutationFn: (payload: Record<string, unknown>) => apiFetch("/pecuaria/confinamento/lotes", { method: "POST", body: JSON.stringify(payload) }), onSuccess: () => { qc.invalidateQueries({ queryKey: ["pecuaria", "confinamento"] }); setLoteOpen(false); toast.success("Lote criado"); } });
  const createRacao = useMutation({ mutationFn: (payload: Record<string, unknown>) => apiFetch("/pecuaria/confinamento/racoes", { method: "POST", body: JSON.stringify(payload) }), onSuccess: () => { qc.invalidateQueries({ queryKey: ["pecuaria", "confinamento"] }); setRacaoOpen(false); toast.success("Ração criada"); } });
  const createCocho = useMutation({ mutationFn: (payload: Record<string, unknown>) => apiFetch("/pecuaria/confinamento/cochos", { method: "POST", body: JSON.stringify(payload) }), onSuccess: () => { qc.invalidateQueries({ queryKey: ["pecuaria", "confinamento"] }); setCochoOpen(false); toast.success("Cocho criado"); } });

  if (!hasModule) return <div className="p-6"><Card><CardContent className="py-10 text-center text-sm text-muted-foreground">O módulo de confinamento não está contratado para este produtor.</CardContent></Card></div>;

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Confinamento"
        description="Dietas, TMR, cochos e performance do lote."
        icon={<Warehouse className="text-primary" size={22} />}
        breadcrumbs={[{ label: "Dashboard", href: "/dashboard" }, { label: "Pecuária", href: "/dashboard/pecuaria" }, { label: "Confinamento" }]}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" className="rounded-sm" onClick={() => setLoteOpen(true)}>
              <Plus className="mr-1.5 size-3.5" /> Lote
            </Button>
            <Button variant="outline" size="sm" className="rounded-sm" onClick={() => setRacaoOpen(true)}>
              <Salad className="mr-1.5 size-3.5" /> TMR
            </Button>
            <Button variant="outline" size="sm" className="rounded-sm" onClick={() => setCochoOpen(true)}>
              <Beef className="mr-1.5 size-3.5" /> Cocho
            </Button>
          </div>
        }
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-5 pb-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-2xl font-bold leading-none">{resumo?.total_lotes ?? 0}</div>
                <div className="text-xs text-muted-foreground mt-1.5 leading-tight">Lotes</div>
              </div>
              <div className="p-2 bg-muted rounded-sm text-blue-600">
                <Layers className="size-5" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5 pb-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-2xl font-bold leading-none">{resumo?.total_animais ?? 0}</div>
                <div className="text-xs text-muted-foreground mt-1.5 leading-tight">Animais</div>
              </div>
              <div className="p-2 bg-muted rounded-sm text-amber-600">
                <Beef className="size-5" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5 pb-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-2xl font-bold leading-none">{resumo?.total_racoes ?? 0}</div>
                <div className="text-xs text-muted-foreground mt-1.5 leading-tight">Dietas</div>
              </div>
              <div className="p-2 bg-muted rounded-sm text-green-600">
                <Salad className="size-5" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5 pb-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-2xl font-bold leading-none">{resumo?.total_cochos ?? 0}</div>
                <div className="text-xs text-muted-foreground mt-1.5 leading-tight">Cochos</div>
              </div>
              <div className="p-2 bg-muted rounded-sm text-orange-600">
                <Activity className="size-5" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Lotes de confinamento</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <DataTable columns={lotesCols} data={lotes} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Dietas TMR</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <DataTable columns={racoesCols} data={racoes} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Cochos</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <DataTable columns={cochosCols} data={cochos} />
          </CardContent>
        </Card>
      </div>

      <Dialog open={loteOpen} onOpenChange={setLoteOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Novo lote de confinamento</DialogTitle></DialogHeader>
          <div className="grid gap-4 md:grid-cols-2">
            <Input placeholder="Código" value={formLote.codigo} onChange={(e) => setFormLote({ ...formLote, codigo: e.target.value })} />
            <Input type="number" placeholder="Total animais" value={formLote.total_animais} onChange={(e) => setFormLote({ ...formLote, total_animais: e.target.value })} />
            <Input type="number" placeholder="Peso inicial" value={formLote.peso_inicial_kg} onChange={(e) => setFormLote({ ...formLote, peso_inicial_kg: e.target.value })} />
            <Input type="date" value={formLote.data_entrada} onChange={(e) => setFormLote({ ...formLote, data_entrada: e.target.value })} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setLoteOpen(false)}>Cancelar</Button>
            <Button onClick={() => createLote.mutate({ ...formLote, total_animais: Number(formLote.total_animais), peso_inicial_kg: formLote.peso_inicial_kg ? Number(formLote.peso_inicial_kg) : undefined, data_entrada: formLote.data_entrada })}>Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <Dialog open={racaoOpen} onOpenChange={setRacaoOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Nova dieta TMR</DialogTitle></DialogHeader>
          <div className="grid gap-4 md:grid-cols-2">
            <Input placeholder="Nome" value={formRacao.nome} onChange={(e) => setFormRacao({ ...formRacao, nome: e.target.value })} />
            <Input placeholder="PB %" value={formRacao.proteina_bruta} onChange={(e) => setFormRacao({ ...formRacao, proteina_bruta: e.target.value })} />
            <Input placeholder="Custo por tonelada" value={formRacao.custo_por_tonelada} onChange={(e) => setFormRacao({ ...formRacao, custo_por_tonelada: e.target.value })} />
            <Textarea rows={3} value={formRacao.ingredientes} onChange={(e) => setFormRacao({ ...formRacao, ingredientes: e.target.value })} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRacaoOpen(false)}>Cancelar</Button>
            <Button onClick={() => createRacao.mutate({ nome: formRacao.nome, ingredientes: JSON.parse(formRacao.ingredientes), proteina_bruta: formRacao.proteina_bruta ? Number(formRacao.proteina_bruta) : undefined, custo_por_tonelada: formRacao.custo_por_tonelada ? Number(formRacao.custo_por_tonelada) : undefined })}>Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <Dialog open={cochoOpen} onOpenChange={setCochoOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Novo cocho</DialogTitle></DialogHeader>
          <div className="grid gap-4 md:grid-cols-2">
            <Input placeholder="Lote ID" value={formCocho.lote_id} onChange={(e) => setFormCocho({ ...formCocho, lote_id: e.target.value })} />
            <Input placeholder="Código" value={formCocho.codigo} onChange={(e) => setFormCocho({ ...formCocho, codigo: e.target.value })} />
            <Input placeholder="Consumo kg" value={formCocho.consumo_kg} onChange={(e) => setFormCocho({ ...formCocho, consumo_kg: e.target.value })} />
            <Input type="date" value={formCocho.data} onChange={(e) => setFormCocho({ ...formCocho, data: e.target.value })} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCochoOpen(false)}>Cancelar</Button>
            <Button onClick={() => createCocho.mutate({ ...formCocho, lote_id: Number(formCocho.lote_id), consumo_kg: formCocho.consumo_kg ? Number(formCocho.consumo_kg) : undefined })}>Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
