"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useHasModule } from "@/hooks/use-has-module";
import { useAppStore } from "@/lib/stores/app-store";
import { Modulos } from "@/lib/constants/modulos";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/shared/page-header";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogBody } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { DataTable, ColumnDef } from "@/components/ui/data-table";
import { PermissionGuard } from "@/components/auth/permission-guard";
import { Leaf, Plus, FileText, TrendingUp, Download, Pencil, Archive } from "lucide-react";

interface Dashboard {
  total_emissoes: number;
  total_creditos: number;
  saldo_liquido: number;
  total_emissoes_registradas: number;
  total_projetos: number;
  total_relatorios: number;
  emissoes_escopo_1: number;
  emissoes_escopo_2: number;
  emissoes_escopo_3: number;
}

interface Emissao {
  id: number;
  unidade_produtiva_id?: string | null;
  unidade_nome?: string | null;
  categoria: string;
  escopo: number;
  fonte?: string | null;
  atividade?: string | null;
  quantidade: number;
  unidade: string;
  total_co2e?: number | null;
  fator_emissao?: number | null;
  fator_emissao_referencia?: string | null;
  data_referencia: string;
  observacoes?: string | null;
}

interface Projeto {
  id: number;
  unidade_produtiva_id?: string | null;
  unidade_nome?: string | null;
  nome: string;
  tipo: string;
  area_ha: number;
  status: string;
  creditos_estimados?: number | null;
  creditos_verificados?: number | null;
  creditos_vendidos?: number | null;
  descricao?: string | null;
  metodologia?: string | null;
  data_inicio?: string | null;
  certificador?: string | null;
  numero_registro?: string | null;
  padrao?: string | null;
}

interface Relatorio {
  id: number;
  periodo_inicio: string;
  periodo_fim: string;
  total_geral?: number | null;
  creditos_gerados?: number | null;
  saldo_liquido?: number | null;
  status?: string | null;
}

const ESCOPOS = [
  { value: 1, label: "Escopo 1" },
  { value: 2, label: "Escopo 2" },
  { value: 3, label: "Escopo 3" },
];

export function CarbonoClient() {
  const queryClient = useQueryClient();
  const hasModule = useHasModule(Modulos.AMBIENTAL_CARBONO);
  const activeFazendaId = useAppStore((state) => state.activeFazendaId);
  const unidadesAutorizadas = useAppStore((state) => state.unidadesProdutivasAutorizadas);
  const unidadeSelecionada = unidadesAutorizadas.find((unidade) => unidade.id === activeFazendaId);
  const [emissaoOpen, setEmissaoOpen] = React.useState(false);
  const [projetoOpen, setProjetoOpen] = React.useState(false);
  const [relatorioOpen, setRelatorioOpen] = React.useState(false);
  const [editandoEmissao, setEditandoEmissao] = React.useState<Emissao | null>(null);
  const [editandoProjeto, setEditandoProjeto] = React.useState<Projeto | null>(null);

  const [formEmissao, setFormEmissao] = React.useState({
    escopo: 1,
    categoria: "diesel",
    fonte: "",
    atividade: "",
    quantidade: "",
    unidade: "L",
    fator_emissao: "",
    fator_emissao_referencia: "",
    data_referencia: new Date().toISOString().slice(0, 16),
    observacoes: "",
  });
  const [formProjeto, setFormProjeto] = React.useState({
    nome: "",
    descricao: "",
    tipo: "reflorestamento",
    metodologia: "",
    area_ha: "",
    creditos_estimados: "",
    creditos_verificados: "",
    creditos_vendidos: "",
    status: "planejamento",
    data_inicio: new Date().toISOString().slice(0, 10),
    certificador: "",
    numero_registro: "",
    padrao: "",
  });
  const [formRelatorio, setFormRelatorio] = React.useState({
    periodo_inicio: new Date().toISOString().slice(0, 10),
    periodo_fim: new Date().toISOString().slice(0, 10),
  });

  const { data: dashboard } = useQuery<Dashboard>({
    queryKey: ["ambiental", "carbono", "dashboard"],
    queryFn: () => apiFetch("/ambiental/carbono/dashboard"),
    enabled: hasModule,
  });
  const { data: emissoes = [] } = useQuery<Emissao[]>({
    queryKey: ["ambiental", "carbono", "emissoes"],
    queryFn: () => apiFetch("/ambiental/carbono/emissoes"),
    enabled: hasModule,
    initialData: [],
  });
  const { data: projetos = [] } = useQuery<Projeto[]>({
    queryKey: ["ambiental", "carbono", "projetos"],
    queryFn: () => apiFetch("/ambiental/carbono/projetos"),
    enabled: hasModule,
    initialData: [],
  });
  const { data: relatorios = [] } = useQuery<Relatorio[]>({
    queryKey: ["ambiental", "carbono", "relatorios"],
    queryFn: () => apiFetch("/ambiental/carbono/relatorios"),
    enabled: hasModule,
    initialData: [],
  });

  const formatNumber = (value?: number | null) => (value ?? 0).toFixed(2);

  const emitirMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      apiFetch("/ambiental/carbono/emissoes", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ambiental", "carbono"] });
      setEmissaoOpen(false);
      toast.success("Emissão registrada");
    },
    onError: (error: Error) => toast.error(error.message || "Erro ao registrar emissão"),
  });

  const projetoMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      apiFetch("/ambiental/carbono/projetos", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ambiental", "carbono"] });
      setProjetoOpen(false);
      toast.success("Projeto criado");
    },
    onError: (error: Error) => toast.error(error.message || "Erro ao criar projeto"),
  });

  const editarEmissaoMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Record<string, unknown> }) =>
      apiFetch(`/ambiental/carbono/emissoes/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["ambiental", "carbono"] }); setEditandoEmissao(null); setEmissaoOpen(false); toast.success("Emissão atualizada"); },
    onError: (error: Error) => toast.error(error.message || "Erro ao atualizar emissão"),
  });

  const editarProjetoMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Record<string, unknown> }) =>
      apiFetch(`/ambiental/carbono/projetos/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["ambiental", "carbono"] }); setEditandoProjeto(null); setProjetoOpen(false); toast.success("Projeto atualizado"); },
    onError: (error: Error) => toast.error(error.message || "Erro ao atualizar projeto"),
  });

  const relatorioMutation = useMutation({
    mutationFn: ({ periodo_inicio, periodo_fim }: { periodo_inicio: string; periodo_fim: string }) =>
      apiFetch(`/ambiental/carbono/relatorios?periodo_inicio=${periodo_inicio}&periodo_fim=${periodo_fim}`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ambiental", "carbono"] });
      setRelatorioOpen(false);
      toast.success("Relatório gerado");
    },
    onError: (error: Error) => toast.error(error.message || "Erro ao gerar relatório"),
  });

  const exigirUnidade = (abrir: () => void) => {
    if (!activeFazendaId) {
      toast.error("Selecione uma unidade produtiva no topbar antes de cadastrar dados de carbono.");
      return;
    }
    abrir();
  };

  const abrirEdicaoEmissao = (emissao: Emissao) => {
    setEditandoEmissao(emissao);
    setFormEmissao({
      escopo: emissao.escopo,
      categoria: emissao.categoria,
      fonte: emissao.fonte ?? "",
      atividade: emissao.atividade ?? "",
      quantidade: String(emissao.quantidade),
      unidade: emissao.unidade,
      fator_emissao: emissao.fator_emissao == null ? "" : String(emissao.fator_emissao),
      fator_emissao_referencia: emissao.fator_emissao_referencia ?? "",
      data_referencia: emissao.data_referencia.slice(0, 16),
      observacoes: emissao.observacoes ?? "",
    });
    setEmissaoOpen(true);
  };

  const abrirEdicaoProjeto = (projeto: Projeto) => {
    setEditandoProjeto(projeto);
    setFormProjeto({
      nome: projeto.nome, descricao: projeto.descricao ?? "", tipo: projeto.tipo, metodologia: projeto.metodologia ?? "", area_ha: String(projeto.area_ha),
      creditos_estimados: projeto.creditos_estimados == null ? "" : String(projeto.creditos_estimados),
      creditos_verificados: projeto.creditos_verificados == null ? "" : String(projeto.creditos_verificados),
      creditos_vendidos: projeto.creditos_vendidos == null ? "" : String(projeto.creditos_vendidos),
      status: projeto.status, data_inicio: projeto.data_inicio ?? "", certificador: projeto.certificador ?? "", numero_registro: projeto.numero_registro ?? "", padrao: projeto.padrao ?? "",
    });
    setProjetoOpen(true);
  };

  const inativarEmissao = (emissao: Emissao) => {
    if (window.confirm("Inativar esta emissão?")) editarEmissaoMutation.mutate({ id: emissao.id, payload: { ativo: false } });
  };

  const inativarProjeto = (projeto: Projeto) => {
    if (window.confirm("Inativar este projeto?")) editarProjetoMutation.mutate({ id: projeto.id, payload: { ativo: false } });
  };

  const emissoesColumns: ColumnDef<Emissao>[] = [
    { id: "unidade", header: "Unidade produtiva", accessorFn: (row) => row.unidade_nome ?? "Não informada" },
    { id: "data", header: "Data", accessorFn: (row) => new Date(row.data_referencia).toLocaleDateString("pt-BR") },
    { id: "escopo", header: "Escopo", cell: (val, row) => <Badge variant="outline">S{row.escopo}</Badge> },
    { id: "categoria", header: "Categoria", accessorKey: "categoria" },
    { id: "quantidade", header: "Quantidade", accessorFn: (row) => `${row.quantidade} ${row.unidade}` },
    { id: "total", header: "Total kgCO2e", accessorFn: (row) => row.total_co2e?.toFixed(2) ?? "-" },
    { id: "acoes", header: "", isActionColumn: true, cell: (_, row) => <PermissionGuard permission="ambiental:carbono:edit"><div className="flex"><Button variant="ghost" size="icon" title="Editar emissão" onClick={() => abrirEdicaoEmissao(row)}><Pencil className="h-4 w-4" /></Button><Button variant="ghost" size="icon" title="Inativar emissão" onClick={() => inativarEmissao(row)}><Archive className="h-4 w-4" /></Button></div></PermissionGuard> },
  ];

  const projetosColumns: ColumnDef<Projeto>[] = [
    { id: "unidade", header: "Unidade produtiva", accessorFn: (row) => row.unidade_nome ?? "Não informada" },
    { id: "nome", header: "Nome", accessorKey: "nome" },
    { id: "tipo", header: "Tipo", accessorKey: "tipo" },
    { id: "area", header: "Área", accessorFn: (row) => `${row.area_ha.toFixed(2)} ha` },
    { id: "creditos", header: "Créditos verificados", accessorFn: (row) => row.creditos_verificados?.toFixed(2) ?? "-" },
    { id: "status", header: "Status", cell: (val, row) => <Badge variant="outline">{row.status}</Badge> },
    { id: "acoes", header: "", isActionColumn: true, cell: (_, row) => <PermissionGuard permission="ambiental:carbono:edit"><div className="flex"><Button variant="ghost" size="icon" title="Editar projeto" onClick={() => abrirEdicaoProjeto(row)}><Pencil className="h-4 w-4" /></Button><Button variant="ghost" size="icon" title="Inativar projeto" onClick={() => inativarProjeto(row)}><Archive className="h-4 w-4" /></Button></div></PermissionGuard> },
  ];

  const relatoriosColumns: ColumnDef<Relatorio>[] = [
    { id: "periodo", header: "Período", accessorFn: (row) => `${new Date(row.periodo_inicio).toLocaleDateString("pt-BR")} - ${new Date(row.periodo_fim).toLocaleDateString("pt-BR")}` },
    { id: "total", header: "Total", accessorFn: (row) => row.total_geral?.toFixed(2) ?? "-" },
    { id: "creditos", header: "Créditos", accessorFn: (row) => row.creditos_gerados?.toFixed(2) ?? "-" },
    { id: "saldo", header: "Saldo", accessorFn: (row) => row.saldo_liquido?.toFixed(2) ?? "-" },
    {
      id: "acoes",
      header: "",
      isActionColumn: true,
      cell: (val, row) => (
        <PermissionGuard permission="ambiental:carbono:export">
          <Button
            variant="ghost"
            size="icon"
            className="text-primary hover:text-primary/80 gap-0"
            onClick={() => window.open(`/api/v1/ambiental/carbono/relatorios/${row.id}/pdf`, "_blank")}
          >
            <Download className="h-4 w-4" />
          </Button>
        </PermissionGuard>
      ),
    },
  ];

  if (!hasModule) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-muted-foreground">
          O módulo de gestão de carbono não está contratado para este tenant.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Gestão de Carbono"
        description="MRV, pegada de carbono, créditos e relatórios de sustentabilidade"
        icon={<Leaf size={22} />}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Ambiental" },
          { label: "Carbono" },
        ]}
        actions={
          <div className="flex flex-wrap gap-2">
            <PermissionGuard permission="ambiental:carbono:create">
              <Button variant="outline" size="sm" onClick={() => exigirUnidade(() => { setEditandoEmissao(null); setEmissaoOpen(true); })}>
                <Plus className="mr-2 h-3.5 w-3.5" />
                Nova emissão
              </Button>
            </PermissionGuard>
            <PermissionGuard permission="ambiental:carbono:create">
              <Button variant="outline" size="sm" onClick={() => exigirUnidade(() => { setEditandoProjeto(null); setProjetoOpen(true); })}>
                <TrendingUp className="mr-2 h-3.5 w-3.5" />
                Novo projeto
              </Button>
            </PermissionGuard>
            <PermissionGuard permission="ambiental:carbono:create">
              <Button variant="outline" size="sm" onClick={() => setRelatorioOpen(true)}>
                <FileText className="mr-2 h-3.5 w-3.5" />
                Gerar relatório
              </Button>
            </PermissionGuard>
          </div>
        }
      />

      <div role="status" className="rounded-sm border border-violet-500/20 bg-violet-500/10 px-3 py-2 text-sm text-violet-800 dark:text-violet-200">
        <strong>Visão consolidada:</strong> emissões, projetos e relatórios exibidos pertencem ao produtor. Novas emissões e projetos serão vinculados à unidade produtiva selecionada no topbar.
        {!unidadeSelecionada && <span className="ml-1 text-destructive">Selecione uma unidade para cadastrar.</span>}
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card><CardHeader className="pb-2"><CardDescription>Total emissões</CardDescription><CardTitle>{formatNumber(dashboard?.total_emissoes)}</CardTitle></CardHeader></Card>
        <Card><CardHeader className="pb-2"><CardDescription>Créditos</CardDescription><CardTitle>{formatNumber(dashboard?.total_creditos)}</CardTitle></CardHeader></Card>
        <Card><CardHeader className="pb-2"><CardDescription>Saldo líquido</CardDescription><CardTitle>{formatNumber(dashboard?.saldo_liquido)}</CardTitle></CardHeader></Card>
        <Card><CardHeader className="pb-2"><CardDescription>Relatórios</CardDescription><CardTitle>{dashboard?.total_relatorios ?? 0}</CardTitle></CardHeader></Card>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Emissões registradas</CardTitle>
        </CardHeader>
        <CardContent className="p-0 sm:p-6 sm:pt-0">
          <DataTable data={emissoes} columns={emissoesColumns} searchPlaceholder="Buscar emissões..." className="border-0 sm:border" />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Projetos de carbono</CardTitle>
        </CardHeader>
        <CardContent className="p-0 sm:p-6 sm:pt-0">
          <DataTable data={projetos} columns={projetosColumns} searchPlaceholder="Buscar projetos..." className="border-0 sm:border" />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Relatórios gerados</CardTitle>
        </CardHeader>
        <CardContent className="p-0 sm:p-6 sm:pt-0">
          <DataTable data={relatorios} columns={relatoriosColumns} searchPlaceholder="Buscar relatórios..." className="border-0 sm:border" />
        </CardContent>
      </Card>

      <Dialog open={emissaoOpen} onOpenChange={(open) => { setEmissaoOpen(open); if (!open) setEditandoEmissao(null); }}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>{editandoEmissao ? "Editar emissão" : "Nova emissão"}</DialogTitle>
            <DialogDescription>Registre consumo, energia, combustíveis ou outras fontes emissoras.</DialogDescription>
          </DialogHeader>
          <DialogBody>
            <div className="grid gap-4 md:grid-cols-2">
              <div><label className="mb-1 block text-sm font-medium">Escopo</label><Select value={String(formEmissao.escopo)} onValueChange={(v) => setFormEmissao({ ...formEmissao, escopo: Number(v) })}><SelectTrigger className="h-8"><SelectValue /></SelectTrigger><SelectContent>{ESCOPOS.map((item) => <SelectItem key={item.value} value={String(item.value)}>{item.label}</SelectItem>)}</SelectContent></Select></div>
              <div><label className="mb-1 block text-sm font-medium">Categoria</label><Input className="h-8" value={formEmissao.categoria} onChange={(e) => setFormEmissao({ ...formEmissao, categoria: e.target.value })} /></div>
              <div><label className="mb-1 block text-sm font-medium">Fonte</label><Input className="h-8" value={formEmissao.fonte} onChange={(e) => setFormEmissao({ ...formEmissao, fonte: e.target.value })} /></div>
              <div><label className="mb-1 block text-sm font-medium">Atividade</label><Input className="h-8" value={formEmissao.atividade} onChange={(e) => setFormEmissao({ ...formEmissao, atividade: e.target.value })} /></div>
              <div><label className="mb-1 block text-sm font-medium">Quantidade</label><Input className="h-8" type="number" step="0.01" value={formEmissao.quantidade} onChange={(e) => setFormEmissao({ ...formEmissao, quantidade: e.target.value })} /></div>
              <div><label className="mb-1 block text-sm font-medium">Unidade</label><Input className="h-8" value={formEmissao.unidade} onChange={(e) => setFormEmissao({ ...formEmissao, unidade: e.target.value })} /></div>
              <div><label className="mb-1 block text-sm font-medium">Fator emissão</label><Input className="h-8" type="number" step="0.0001" value={formEmissao.fator_emissao} onChange={(e) => setFormEmissao({ ...formEmissao, fator_emissao: e.target.value })} /></div>
              <div><label className="mb-1 block text-sm font-medium">Data referência</label><Input className="h-8" type="datetime-local" value={formEmissao.data_referencia} onChange={(e) => setFormEmissao({ ...formEmissao, data_referencia: e.target.value })} /></div>
              <div className="md:col-span-2"><label className="mb-1 block text-sm font-medium">Observações</label><Textarea className="min-h-[80px] resize-none text-sm" rows={3} value={formEmissao.observacoes} onChange={(e) => setFormEmissao({ ...formEmissao, observacoes: e.target.value })} /></div>
            </div>
          </DialogBody>
          <DialogFooter>
            <Button size="sm" variant="outline" onClick={() => setEmissaoOpen(false)}>Cancelar</Button>
            <Button size="sm" onClick={() => {
              const payload = {
                ...formEmissao,
                quantidade: Number(formEmissao.quantidade || 0),
                fator_emissao: formEmissao.fator_emissao ? Number(formEmissao.fator_emissao) : undefined,
                data_referencia: formEmissao.data_referencia,
                observacoes: formEmissao.observacoes || undefined,
                fonte: formEmissao.fonte || undefined,
                atividade: formEmissao.atividade || undefined,
              };
              if (editandoEmissao) editarEmissaoMutation.mutate({ id: editandoEmissao.id, payload });
              else emitirMutation.mutate({ unidade_produtiva_id: activeFazendaId, ...payload });
            }}>Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={projetoOpen} onOpenChange={(open) => { setProjetoOpen(open); if (!open) setEditandoProjeto(null); }}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>{editandoProjeto ? "Editar projeto" : "Novo projeto"}</DialogTitle>
            <DialogDescription>Crie um projeto de carbono ou MRV para acompanhamento.</DialogDescription>
          </DialogHeader>
          <DialogBody>
            <div className="grid gap-4 md:grid-cols-2">
              <div><label className="mb-1 block text-sm font-medium">Nome</label><Input className="h-8" value={formProjeto.nome} onChange={(e) => setFormProjeto({ ...formProjeto, nome: e.target.value })} /></div>
              <div><label className="mb-1 block text-sm font-medium">Tipo</label><Input className="h-8" value={formProjeto.tipo} onChange={(e) => setFormProjeto({ ...formProjeto, tipo: e.target.value })} /></div>
              <div><label className="mb-1 block text-sm font-medium">Área (ha)</label><Input className="h-8" type="number" step="0.01" value={formProjeto.area_ha} onChange={(e) => setFormProjeto({ ...formProjeto, area_ha: e.target.value })} /></div>
              <div><label className="mb-1 block text-sm font-medium">Metodologia</label><Input className="h-8" value={formProjeto.metodologia} onChange={(e) => setFormProjeto({ ...formProjeto, metodologia: e.target.value })} /></div>
              <div><label className="mb-1 block text-sm font-medium">Status</label><Input className="h-8" value={formProjeto.status} onChange={(e) => setFormProjeto({ ...formProjeto, status: e.target.value })} /></div>
              <div><label className="mb-1 block text-sm font-medium">Data início</label><Input className="h-8" type="date" value={formProjeto.data_inicio} onChange={(e) => setFormProjeto({ ...formProjeto, data_inicio: e.target.value })} /></div>
              <div><label className="mb-1 block text-sm font-medium">Créditos estimados</label><Input className="h-8" type="number" step="0.01" value={formProjeto.creditos_estimados} onChange={(e) => setFormProjeto({ ...formProjeto, creditos_estimados: e.target.value })} /></div>
              <div><label className="mb-1 block text-sm font-medium">Créditos verificados</label><Input className="h-8" type="number" step="0.01" value={formProjeto.creditos_verificados} onChange={(e) => setFormProjeto({ ...formProjeto, creditos_verificados: e.target.value })} /></div>
              <div className="md:col-span-2"><label className="mb-1 block text-sm font-medium">Descrição</label><Textarea className="min-h-[80px] resize-none text-sm" rows={3} value={formProjeto.descricao} onChange={(e) => setFormProjeto({ ...formProjeto, descricao: e.target.value })} /></div>
            </div>
          </DialogBody>
          <DialogFooter>
            <Button size="sm" variant="outline" onClick={() => setProjetoOpen(false)}>Cancelar</Button>
            <Button size="sm" onClick={() => {
              const payload = {
                ...formProjeto,
                area_ha: Number(formProjeto.area_ha || 0),
                creditos_estimados: formProjeto.creditos_estimados ? Number(formProjeto.creditos_estimados) : undefined,
                creditos_verificados: formProjeto.creditos_verificados ? Number(formProjeto.creditos_verificados) : undefined,
                creditos_vendidos: formProjeto.creditos_vendidos ? Number(formProjeto.creditos_vendidos) : undefined,
                data_inicio: formProjeto.data_inicio || undefined,
                metodologia: formProjeto.metodologia || undefined,
                certificador: formProjeto.certificador || undefined,
                numero_registro: formProjeto.numero_registro || undefined,
                padrao: formProjeto.padrao || undefined,
              };
              if (editandoProjeto) editarProjetoMutation.mutate({ id: editandoProjeto.id, payload });
              else projetoMutation.mutate({ unidade_produtiva_id: activeFazendaId, ...payload });
            }}>Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={relatorioOpen} onOpenChange={setRelatorioOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Gerar relatório</DialogTitle>
            <DialogDescription>Cria o relatório MRV do período informado.</DialogDescription>
          </DialogHeader>
          <DialogBody>
            <div className="grid gap-4 md:grid-cols-2">
              <div><label className="mb-1 block text-sm font-medium">Início</label><Input className="h-8" type="date" value={formRelatorio.periodo_inicio} onChange={(e) => setFormRelatorio({ ...formRelatorio, periodo_inicio: e.target.value })} /></div>
              <div><label className="mb-1 block text-sm font-medium">Fim</label><Input className="h-8" type="date" value={formRelatorio.periodo_fim} onChange={(e) => setFormRelatorio({ ...formRelatorio, periodo_fim: e.target.value })} /></div>
            </div>
          </DialogBody>
          <DialogFooter>
            <Button size="sm" variant="outline" onClick={() => setRelatorioOpen(false)}>Cancelar</Button>
            <Button size="sm" onClick={() => relatorioMutation.mutate(formRelatorio)}>Gerar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
