"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useHasModule } from "@/hooks/use-has-module";
import { Modulos } from "@/lib/constants/modulos";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Textarea } from "@/components/ui/textarea";
import { Dna, Plus, WandSparkles } from "lucide-react";
import { toast } from "sonner";

type Resumo = {
  total_registros: number;
  total_matrizes: number;
  total_reprodutores: number;
  total_sugestoes: number;
  total_coberturas: number;
  total_diagnosticos_prenhez: number;
  total_partos: number;
  total_nascimentos: number;
  total_desmamas: number;
  taxa_prenhez_pct: number;
  taxa_natalidade_pct: number;
  taxa_desmama_pct: number;
  intervalo_medio_partos_dias: number;
  peso_nascimento_medio_kg: number;
  peso_desmama_medio_kg: number;
  idade_media_desmama_dias: number;
  crias_por_matriz: number;
  perdas_reprodutivas: number;
};

type Genetica = {
  id: number;
  brinco?: string | null;
  animal_id: number;
  dep_ganho_peso?: number | null;
  dep_area_olho_lombo?: number | null;
  dep_gordura_subcutanea?: number | null;
  dep_maciez?: number | null;
  matriz: boolean;
  reprodutor: boolean;
};

type Sugestao = {
  id: number;
  matriz_id: number;
  reprodutor_id: number;
  score_complementaridade?: number | null;
  realizado: boolean;
  data_acasalamento?: string | null;
};

export default function GeneticaClient() {
  const queryClient = useQueryClient();
  const hasModule = useHasModule(Modulos.PECUARIA_GENETICA);
  const [open, setOpen] = React.useState(false);
  const [sugestaoOpen, setSugestaoOpen] = React.useState(false);
  const [form, setForm] = React.useState({ animal_id: "", brinco: "", dep_ganho_peso: "", dep_area_olho_lombo: "", dep_gordura_subcutanea: "", dep_maciez: "", matriz: true, reprodutor: false });
  const [sugForm, setSugForm] = React.useState({ matriz_id: "", reprodutor_id: "", score_complementaridade: "", realizado: false });

  const { data: resumo } = useQuery<Resumo>({
    queryKey: ["pecuaria", "genetica", "dashboard"],
    queryFn: () => apiFetch("/pecuaria/genetica/dashboard"),
    enabled: hasModule,
  });
  const { data: registros = [] } = useQuery<Genetica[]>({
    queryKey: ["pecuaria", "genetica", "animais"],
    queryFn: () => apiFetch("/pecuaria/genetica/animais"),
    enabled: hasModule,
    initialData: [],
  });
  const { data: sugestoes = [] } = useQuery<Sugestao[]>({
    queryKey: ["pecuaria", "genetica", "sugestoes"],
    queryFn: () => apiFetch("/pecuaria/genetica/acasalamentos"),
    enabled: hasModule,
    initialData: [],
  });

  const createMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => apiFetch("/pecuaria/genetica/animais", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["pecuaria", "genetica"] }); setOpen(false); toast.success("Registro genético criado"); },
  });
  const sugestaoMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => apiFetch("/pecuaria/genetica/acasalamentos", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["pecuaria", "genetica"] }); setSugestaoOpen(false); toast.success("Sugestão criada"); },
  });

  if (!hasModule) {
    return <Card><CardContent className="py-10 text-center text-sm text-muted-foreground">O módulo de genética não está contratado para este produtor.</CardContent></Card>;
  }

  const pct = (value?: number | null) => `${Number(value ?? 0).toFixed(1)}%`;

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Genética Reprodutiva"
        description="Pedigree, DEPs e planejamento de acasalamento."
        icon={<Dna className="text-primary" size={22} />}
        breadcrumbs={[{ label: "Pecuária", href: "/dashboard/pecuaria" }, { label: "Genética" }]}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" className="rounded-sm" onClick={() => setOpen(true)}>
              <Plus className="size-3.5 mr-1.5" />
              Novo registro
            </Button>
            <Button variant="outline" size="sm" className="rounded-sm" onClick={() => setSugestaoOpen(true)}>
              <WandSparkles className="size-3.5 mr-1.5" />
              Acasalamento
            </Button>
          </div>
        }
      />
      <div className="grid gap-4 md:grid-cols-4">
        <Card><CardHeader className="pb-2"><CardDescription>Registros</CardDescription><CardTitle>{resumo?.total_registros ?? 0}</CardTitle></CardHeader></Card>
        <Card><CardHeader className="pb-2"><CardDescription>Matrizes</CardDescription><CardTitle>{resumo?.total_matrizes ?? 0}</CardTitle></CardHeader></Card>
        <Card><CardHeader className="pb-2"><CardDescription>Reprodutores</CardDescription><CardTitle>{resumo?.total_reprodutores ?? 0}</CardTitle></CardHeader></Card>
        <Card><CardHeader className="pb-2"><CardDescription>Sugestões</CardDescription><CardTitle>{resumo?.total_sugestoes ?? 0}</CardTitle></CardHeader></Card>
        <Card><CardHeader className="pb-2"><CardDescription>Coberturas</CardDescription><CardTitle>{resumo?.total_coberturas ?? 0}</CardTitle></CardHeader></Card>
        <Card><CardHeader className="pb-2"><CardDescription>Diagnósticos</CardDescription><CardTitle>{resumo?.total_diagnosticos_prenhez ?? 0}</CardTitle></CardHeader></Card>
        <Card><CardHeader className="pb-2"><CardDescription>Partos</CardDescription><CardTitle>{resumo?.total_partos ?? 0}</CardTitle></CardHeader></Card>
        <Card><CardHeader className="pb-2"><CardDescription>Desmamas</CardDescription><CardTitle>{resumo?.total_desmamas ?? 0}</CardTitle></CardHeader></Card>
        <Card><CardHeader className="pb-2"><CardDescription>Taxa prenhez</CardDescription><CardTitle>{pct(resumo?.taxa_prenhez_pct)}</CardTitle></CardHeader></Card>
        <Card><CardHeader className="pb-2"><CardDescription>Taxa natalidade</CardDescription><CardTitle>{pct(resumo?.taxa_natalidade_pct)}</CardTitle></CardHeader></Card>
        <Card><CardHeader className="pb-2"><CardDescription>Taxa desmama</CardDescription><CardTitle>{pct(resumo?.taxa_desmama_pct)}</CardTitle></CardHeader></Card>
        <Card><CardHeader className="pb-2"><CardDescription>Perdas reprodutivas</CardDescription><CardTitle>{resumo?.perdas_reprodutivas ?? 0}</CardTitle></CardHeader></Card>
      </div>
      <Card>
        <CardHeader><CardTitle className="text-base">Indicadores reprodutivos</CardTitle></CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          <SummaryItem label="Intervalo médio entre partos" value={`${Number(resumo?.intervalo_medio_partos_dias ?? 0).toFixed(1)} dias`} />
          <SummaryItem label="Peso médio ao nascer" value={`${Number(resumo?.peso_nascimento_medio_kg ?? 0).toFixed(1)} kg`} />
          <SummaryItem label="Peso médio à desmama" value={`${Number(resumo?.peso_desmama_medio_kg ?? 0).toFixed(1)} kg`} />
          <SummaryItem label="Idade média à desmama" value={`${Number(resumo?.idade_media_desmama_dias ?? 0).toFixed(1)} dias`} />
          <SummaryItem label="Crias por matriz" value={Number(resumo?.crias_por_matriz ?? 0).toFixed(2)} />
          <SummaryItem label="Nascimentos" value={String(resumo?.total_nascimentos ?? 0)} />
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Animais com genética</CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          <DataTable
            data={registros}
            columns={React.useMemo<ColumnDef<Genetica>[]>(() => [
              { id: "brinco", header: "Brinco", accessorKey: "brinco", cell: (value) => value ?? "-" },
              { id: "animal", header: "Animal", accessorKey: "animal_id" },
              { id: "ganho", header: "DEP ganho", accessorKey: "dep_ganho_peso", cell: (value) => value?.toFixed(2) ?? "-" },
              { id: "lombo", header: "DEP lombo", accessorKey: "dep_area_olho_lombo", cell: (value) => value?.toFixed(2) ?? "-" },
              { id: "matriz", header: "Matriz", accessorKey: "matriz", cell: (value) => <Badge variant={value ? "default" : "outline"}>{value ? "Sim" : "Não"}</Badge> },
              { id: "reprodutor", header: "Reprodutor", accessorKey: "reprodutor", cell: (value) => <Badge variant={value ? "default" : "outline"}>{value ? "Sim" : "Não"}</Badge> }
            ], [])}
            searchable
            searchPlaceholder="Buscar por brinco..."
            exportable
            exportFileName="genetica-animais"
            emptyMessage="Nenhum registro genético encontrado."
          />
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Sugestões de acasalamento</CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          <DataTable
            data={sugestoes}
            columns={React.useMemo<ColumnDef<Sugestao>[]>(() => [
              { id: "matriz", header: "Matriz", accessorKey: "matriz_id" },
              { id: "reprodutor", header: "Reprodutor", accessorKey: "reprodutor_id" },
              { id: "score", header: "Score", accessorKey: "score_complementaridade", cell: (value) => value?.toFixed(2) ?? "-" },
              { id: "realizado", header: "Realizado", accessorKey: "realizado", cell: (value) => <Badge variant={value ? "default" : "outline"}>{value ? "Sim" : "Não"}</Badge> }
            ], [])}
            searchable={false}
            exportable
            exportFileName="genetica-sugestoes"
            emptyMessage="Nenhuma sugestão de acasalamento encontrada."
          />
        </CardContent>
      </Card>
      <Dialog open={open} onOpenChange={setOpen}><DialogContent><DialogHeader><DialogTitle>Novo registro genético</DialogTitle><DialogDescription>Cadastre DEPs e classificação reprodutiva.</DialogDescription></DialogHeader><div className="grid gap-4 md:grid-cols-2"><Input placeholder="Animal ID" value={form.animal_id} onChange={(e) => setForm({ ...form, animal_id: e.target.value })} /><Input placeholder="Brinco" value={form.brinco} onChange={(e) => setForm({ ...form, brinco: e.target.value })} /><Input placeholder="DEP ganho" value={form.dep_ganho_peso} onChange={(e) => setForm({ ...form, dep_ganho_peso: e.target.value })} /><Input placeholder="DEP lombo" value={form.dep_area_olho_lombo} onChange={(e) => setForm({ ...form, dep_area_olho_lombo: e.target.value })} /><Input placeholder="DEP gordura" value={form.dep_gordura_subcutanea} onChange={(e) => setForm({ ...form, dep_gordura_subcutanea: e.target.value })} /><Input placeholder="DEP maciez" value={form.dep_maciez} onChange={(e) => setForm({ ...form, dep_maciez: e.target.value })} /></div><DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button><Button onClick={() => createMutation.mutate({ ...form, animal_id: Number(form.animal_id), brinco: form.brinco || undefined, dep_ganho_peso: form.dep_ganho_peso ? Number(form.dep_ganho_peso) : undefined, dep_area_olho_lombo: form.dep_area_olho_lombo ? Number(form.dep_area_olho_lombo) : undefined, dep_gordura_subcutanea: form.dep_gordura_subcutanea ? Number(form.dep_gordura_subcutanea) : undefined, dep_maciez: form.dep_maciez ? Number(form.dep_maciez) : undefined })}>Salvar</Button></DialogFooter></DialogContent></Dialog>
      <Dialog open={sugestaoOpen} onOpenChange={setSugestaoOpen}><DialogContent><DialogHeader><DialogTitle>Nova sugestão de acasalamento</DialogTitle></DialogHeader><div className="grid gap-4 md:grid-cols-2"><Input placeholder="Matriz ID" value={sugForm.matriz_id} onChange={(e) => setSugForm({ ...sugForm, matriz_id: e.target.value })} /><Input placeholder="Reprodutor ID" value={sugForm.reprodutor_id} onChange={(e) => setSugForm({ ...sugForm, reprodutor_id: e.target.value })} /><Input placeholder="Score" value={sugForm.score_complementaridade} onChange={(e) => setSugForm({ ...sugForm, score_complementaridade: e.target.value })} /><Textarea placeholder="Dep esperado (JSON)" rows={3} onChange={(e) => setSugForm({ ...sugForm, score_complementaridade: sugForm.score_complementaridade, realizado: sugForm.realizado })} /></div><DialogFooter><Button variant="outline" onClick={() => setSugestaoOpen(false)}>Cancelar</Button><Button onClick={() => sugestaoMutation.mutate({ matriz_id: Number(sugForm.matriz_id), reprodutor_id: Number(sugForm.reprodutor_id), score_complementaridade: sugForm.score_complementaridade ? Number(sugForm.score_complementaridade) : 0, realizado: sugForm.realizado })}>Salvar</Button></DialogFooter></DialogContent></Dialog>
    </div>
  );
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-sm border border-border-subtle bg-muted/20 px-3 py-2">
      <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold text-foreground">{value}</p>
    </div>
  )
}
