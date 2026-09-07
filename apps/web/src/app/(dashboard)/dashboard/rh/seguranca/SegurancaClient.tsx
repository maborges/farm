"use client";

import * as React from "react";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useHasModule } from "@/hooks/use-has-module";
import { Modulos } from "@/lib/constants/modulos";
import { toast } from "sonner";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { Download, ShieldCheck, FileText, Plus, Users } from "lucide-react";

interface Colaborador {
  id: string;
  nome: string;
}

interface ItemSeguranca {
  id: string;
  nome: string;
  tipo: "EPI" | "EPC";
  ca_numero?: string | null;
  validade_dias?: number | null;
  fornecedor?: string | null;
  observacoes?: string | null;
  ativo: boolean;
}

interface EntregaSeguranca {
  id: string;
  colaborador_id: string;
  item_id: string;
  data_entrega: string;
  data_validade?: string | null;
  quantidade: number;
  status: string;
}

interface DocumentoSST {
  id: string;
  colaborador_id?: string | null;
  tipo: string;
  numero?: string | null;
  data_emissao: string;
  data_vencimento?: string | null;
  status: string;
  observacoes?: string | null;
}

interface Resumo {
  total_itens_ativos: number;
  total_entregas_ativas: number;
  total_documentos_ativos: number;
  documentos_vencendo_30d: number;
  documentos_vencidos: number;
}

interface Props {
  initialColaboradores: Colaborador[];
}

const TIPOS_ITEM = [
  { value: "EPI", label: "EPI" },
  { value: "EPC", label: "EPC" },
];

const TIPOS_DOC = ["PPP", "PCMSO", "LTCAT", "NR31", "ASO", "TREINAMENTO"];

export function SegurancaClient({ initialColaboradores }: Props) {
  const queryClient = useQueryClient();
  const hasModule = useHasModule(Modulos.RH_SEGURANCA);
  const [itemOpen, setItemOpen] = useState(false);
  const [entregaOpen, setEntregaOpen] = useState(false);
  const [docOpen, setDocOpen] = useState(false);
  const [formItem, setFormItem] = useState({
    nome: "",
    tipo: "EPI",
    ca_numero: "",
    validade_dias: "",
    fornecedor: "",
    observacoes: "",
  });
  const [formEntrega, setFormEntrega] = useState({
    colaborador_id: initialColaboradores[0]?.id || "",
    item_id: "",
    data_entrega: new Date().toISOString().split("T")[0],
    data_validade: "",
    quantidade: "1",
    termo_assinado_url: "",
    observacoes: "",
  });
  const [formDoc, setFormDoc] = useState({
    colaborador_id: "",
    tipo: "PPP",
    numero: "",
    data_emissao: new Date().toISOString().split("T")[0],
    data_vencimento: "",
    arquivo_url: "",
    observacoes: "",
  });

  const { data: resumo } = useQuery<Resumo>({
    queryKey: ["rh-seguranca-resumo"],
    queryFn: () => apiFetch("/rh/seguranca/resumo"),
    enabled: hasModule,
  });

  const { data: itens = [] } = useQuery<ItemSeguranca[]>({
    queryKey: ["rh-seguranca-itens"],
    queryFn: () => apiFetch("/rh/seguranca/itens"),
    enabled: hasModule,
    initialData: [],
  });

  const { data: entregas = [] } = useQuery<EntregaSeguranca[]>({
    queryKey: ["rh-seguranca-entregas"],
    queryFn: () => apiFetch("/rh/seguranca/entregas"),
    enabled: hasModule,
    initialData: [],
  });

  const { data: documentos = [] } = useQuery<DocumentoSST[]>({
    queryKey: ["rh-seguranca-documentos"],
    queryFn: () => apiFetch("/rh/seguranca/documentos"),
    enabled: hasModule,
    initialData: [],
  });

  const itemMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => apiFetch("/rh/seguranca/itens", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rh-seguranca-itens"] });
      queryClient.invalidateQueries({ queryKey: ["rh-seguranca-resumo"] });
      setItemOpen(false);
      toast.success("Item cadastrado");
    },
    onError: (error: Error) => toast.error(error.message || "Erro ao cadastrar item"),
  });

  const entregaMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => apiFetch("/rh/seguranca/entregas", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rh-seguranca-entregas"] });
      queryClient.invalidateQueries({ queryKey: ["rh-seguranca-resumo"] });
      setEntregaOpen(false);
      toast.success("Entrega registrada");
    },
    onError: (error: Error) => toast.error(error.message || "Erro ao registrar entrega"),
  });

  const docMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => apiFetch("/rh/seguranca/documentos", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rh-seguranca-documentos"] });
      queryClient.invalidateQueries({ queryKey: ["rh-seguranca-resumo"] });
      setDocOpen(false);
      toast.success("Documento registrado");
    },
    onError: (error: Error) => toast.error(error.message || "Erro ao registrar documento"),
  });

  if (!hasModule) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-muted-foreground">
          O módulo de segurança do trabalho não está contratado para este tenant.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Segurança do Trabalho"
        description="Controle de EPI, EPC, documentos SST e relatórios NR-31"
        icon={<ShieldCheck className="text-primary" size={22} />}
        breadcrumbs={[
            { label: "Pessoas & RH", href: "/dashboard/rh" },
            { label: "Segurança" }
        ]}
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => setItemOpen(true)} className="rounded-sm border-primary text-primary hover:bg-primary/5 font-bold">
              <Plus className="mr-1.5 size-4" />
              Novo item
            </Button>
            <Button variant="outline" size="sm" onClick={() => setEntregaOpen(true)} className="rounded-sm border-primary text-primary hover:bg-primary/5 font-bold">
              <Users className="mr-1.5 size-4" />
              Nova entrega
            </Button>
            <Button variant="outline" size="sm" onClick={() => setDocOpen(true)} className="rounded-sm border-primary text-primary hover:bg-primary/5 font-bold">
              <FileText className="mr-1.5 size-4" />
              Novo documento
            </Button>
            <Button size="sm" variant="outline" onClick={() => window.open("/rh/seguranca/export/nr31.pdf", "_blank")} className="rounded-sm border-primary text-primary hover:bg-primary/5 font-bold">
              <Download className="mr-1.5 size-4" />
              Relatório NR-31
            </Button>
          </div>
        }
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
            { label: "Itens Ativos", value: resumo?.total_itens_ativos ?? 0, color: "text-foreground", border: "border-l-primary/60" },
            { label: "Entregas Ativas", value: resumo?.total_entregas_ativas ?? 0, color: "text-foreground", border: "border-l-primary/60" },
            { label: "Docs Vencendo (30d)", value: resumo?.documentos_vencendo_30d ?? 0, color: (resumo?.documentos_vencendo_30d ?? 0) > 0 ? "text-yellow-600" : "text-foreground", border: (resumo?.documentos_vencendo_30d ?? 0) > 0 ? "border-l-yellow-500/60" : "border-l-primary/60" },
            { label: "Docs Vencidos", value: resumo?.documentos_vencidos ?? 0, color: (resumo?.documentos_vencidos ?? 0) > 0 ? "text-red-600" : "text-foreground", border: (resumo?.documentos_vencidos ?? 0) > 0 ? "border-l-red-500/60" : "border-l-primary/60" },
        ].map((k, i) => (
            <Card key={i} className={`rounded-sm border-l-[3px] ${k.border} shadow-sm transition-all hover:shadow-md`}>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-[10px] text-muted-foreground uppercase tracking-wider font-bold">{k.label}</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className={`text-2xl font-black tabular-nums ${k.color}`}>
                        {k.value}
                    </div>
                </CardContent>
            </Card>
        ))}
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Itens de segurança</CardTitle>
        </CardHeader>
        <CardContent>
          {itens.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 px-4 text-center bg-muted/10 rounded-lg border border-dashed">
                <div className="size-10 rounded-full bg-primary/10 flex items-center justify-center mb-3">
                    <ShieldCheck className="size-5 text-primary" />
                </div>
                <h3 className="text-sm font-semibold mb-1">Nenhum item cadastrado</h3>
                <p className="text-xs text-muted-foreground max-w-sm mb-4">Cadastre equipamentos (EPI/EPC) para gerenciar as entregas.</p>
                <Button size="sm" variant="outline" onClick={() => setItemOpen(true)} className="rounded-sm"><Plus className="size-3.5 mr-1.5" /> Novo item</Button>
            </div>
          ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead>CA</TableHead>
                <TableHead>Validade</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {itens.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-medium">{item.nome}</TableCell>
                  <TableCell>{item.tipo}</TableCell>
                  <TableCell>{item.ca_numero || "-"}</TableCell>
                  <TableCell>{item.validade_dias ? `${item.validade_dias} dias` : "-"}</TableCell>
                  <TableCell><Badge variant="outline">{item.ativo ? "ATIVO" : "INATIVO"}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Entregas</CardTitle>
        </CardHeader>
        <CardContent>
          {entregas.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 px-4 text-center bg-muted/10 rounded-lg border border-dashed">
                <div className="size-10 rounded-full bg-primary/10 flex items-center justify-center mb-3">
                    <Users className="size-5 text-primary" />
                </div>
                <h3 className="text-sm font-semibold mb-1">Nenhuma entrega registrada</h3>
                <p className="text-xs text-muted-foreground max-w-sm mb-4">Registre as entregas de equipamentos aos colaboradores.</p>
                <Button size="sm" variant="outline" onClick={() => setEntregaOpen(true)} className="rounded-sm"><Plus className="size-3.5 mr-1.5" /> Nova entrega</Button>
            </div>
          ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Data</TableHead>
                <TableHead>Colaborador</TableHead>
                <TableHead>Item</TableHead>
                <TableHead>Validade</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {entregas.map((entrega) => (
                <TableRow key={entrega.id}>
                  <TableCell>{new Date(entrega.data_entrega).toLocaleDateString("pt-BR")}</TableCell>
                  <TableCell>{entrega.colaborador_id}</TableCell>
                  <TableCell>{entrega.item_id}</TableCell>
                  <TableCell>{entrega.data_validade ? new Date(entrega.data_validade).toLocaleDateString("pt-BR") : "-"}</TableCell>
                  <TableCell><Badge variant="outline">{entrega.status}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Documentos SST</CardTitle>
        </CardHeader>
        <CardContent>
          {documentos.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 px-4 text-center bg-muted/10 rounded-lg border border-dashed">
                <div className="size-10 rounded-full bg-primary/10 flex items-center justify-center mb-3">
                    <FileText className="size-5 text-primary" />
                </div>
                <h3 className="text-sm font-semibold mb-1">Nenhum documento cadastrado</h3>
                <p className="text-xs text-muted-foreground max-w-sm mb-4">Gerencie PCMSO, PPP, e laudos técnicos.</p>
                <Button size="sm" variant="outline" onClick={() => setDocOpen(true)} className="rounded-sm"><Plus className="size-3.5 mr-1.5" /> Novo documento</Button>
            </div>
          ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Tipo</TableHead>
                <TableHead>Emissão</TableHead>
                <TableHead>Vencimento</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {documentos.map((doc) => (
                <TableRow key={doc.id}>
                  <TableCell>{doc.tipo}</TableCell>
                  <TableCell>{new Date(doc.data_emissao).toLocaleDateString("pt-BR")}</TableCell>
                  <TableCell>{doc.data_vencimento ? new Date(doc.data_vencimento).toLocaleDateString("pt-BR") : "-"}</TableCell>
                  <TableCell><Badge variant="outline">{doc.status}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={itemOpen} onOpenChange={setItemOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Novo item de segurança</DialogTitle>
            <DialogDescription>Cadastre EPI ou EPC com CA e validade.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 md:grid-cols-2">
            <div><label className="mb-1 block text-sm font-medium">Nome</label><Input value={formItem.nome} onChange={(e) => setFormItem({ ...formItem, nome: e.target.value })} /></div>
            <div><label className="mb-1 block text-sm font-medium">Tipo</label><Select value={formItem.tipo} onValueChange={(v) => setFormItem({ ...formItem, tipo: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{TIPOS_ITEM.map((item) => <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>)}</SelectContent></Select></div>
            <div><label className="mb-1 block text-sm font-medium">CA</label><Input value={formItem.ca_numero} onChange={(e) => setFormItem({ ...formItem, ca_numero: e.target.value })} /></div>
            <div><label className="mb-1 block text-sm font-medium">Validade (dias)</label><Input type="number" value={formItem.validade_dias} onChange={(e) => setFormItem({ ...formItem, validade_dias: e.target.value })} /></div>
            <div><label className="mb-1 block text-sm font-medium">Fornecedor</label><Input value={formItem.fornecedor} onChange={(e) => setFormItem({ ...formItem, fornecedor: e.target.value })} /></div>
            <div className="md:col-span-2"><label className="mb-1 block text-sm font-medium">Observações</label><Textarea rows={3} value={formItem.observacoes} onChange={(e) => setFormItem({ ...formItem, observacoes: e.target.value })} /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setItemOpen(false)}>Cancelar</Button>
            <Button onClick={() => itemMutation.mutate({ ...formItem, validade_dias: formItem.validade_dias ? Number(formItem.validade_dias) : undefined })}>Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={entregaOpen} onOpenChange={setEntregaOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Nova entrega</DialogTitle>
            <DialogDescription>Registre a entrega por colaborador.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 md:grid-cols-2">
            <div><label className="mb-1 block text-sm font-medium">Colaborador</label><Select value={formEntrega.colaborador_id || "__none__"} onValueChange={(v) => setFormEntrega({ ...formEntrega, colaborador_id: v === "__none__" ? "" : v })}><SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger><SelectContent><SelectItem value="__none__">Selecione</SelectItem>{initialColaboradores.map((c) => <SelectItem key={c.id} value={c.id}>{c.nome}</SelectItem>)}</SelectContent></Select></div>
            <div><label className="mb-1 block text-sm font-medium">Item</label><Select value={formEntrega.item_id} onValueChange={(v) => setFormEntrega({ ...formEntrega, item_id: v })}><SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger><SelectContent>{itens.map((item) => <SelectItem key={item.id} value={item.id}>{item.nome}</SelectItem>)}</SelectContent></Select></div>
            <div><label className="mb-1 block text-sm font-medium">Data de entrega</label><Input type="date" value={formEntrega.data_entrega} onChange={(e) => setFormEntrega({ ...formEntrega, data_entrega: e.target.value })} /></div>
            <div><label className="mb-1 block text-sm font-medium">Data de validade</label><Input type="date" value={formEntrega.data_validade} onChange={(e) => setFormEntrega({ ...formEntrega, data_validade: e.target.value })} /></div>
            <div><label className="mb-1 block text-sm font-medium">Quantidade</label><Input type="number" step="0.1" value={formEntrega.quantidade} onChange={(e) => setFormEntrega({ ...formEntrega, quantidade: e.target.value })} /></div>
            <div><label className="mb-1 block text-sm font-medium">Termo assinado URL</label><Input value={formEntrega.termo_assinado_url} onChange={(e) => setFormEntrega({ ...formEntrega, termo_assinado_url: e.target.value })} /></div>
            <div className="md:col-span-2"><label className="mb-1 block text-sm font-medium">Observações</label><Textarea rows={3} value={formEntrega.observacoes} onChange={(e) => setFormEntrega({ ...formEntrega, observacoes: e.target.value })} /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEntregaOpen(false)}>Cancelar</Button>
            <Button onClick={() => entregaMutation.mutate({
              ...formEntrega,
              quantidade: Number(formEntrega.quantidade || 1),
              data_validade: formEntrega.data_validade || undefined,
              termo_assinado_url: formEntrega.termo_assinado_url || undefined,
              observacoes: formEntrega.observacoes || undefined,
            })}>Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={docOpen} onOpenChange={setDocOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Novo documento SST</DialogTitle>
            <DialogDescription>Registre PPP, PCMSO, NR-31 e documentos correlatos.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 md:grid-cols-2">
            <div><label className="mb-1 block text-sm font-medium">Colaborador</label><Select value={formDoc.colaborador_id || "__none__"} onValueChange={(v) => setFormDoc({ ...formDoc, colaborador_id: v === "__none__" ? "" : v })}><SelectTrigger><SelectValue placeholder="Opcional" /></SelectTrigger><SelectContent><SelectItem value="__none__">Nenhum</SelectItem>{initialColaboradores.map((c) => <SelectItem key={c.id} value={c.id}>{c.nome}</SelectItem>)}</SelectContent></Select></div>
            <div><label className="mb-1 block text-sm font-medium">Tipo</label><Select value={formDoc.tipo} onValueChange={(v) => setFormDoc({ ...formDoc, tipo: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{TIPOS_DOC.map((tipo) => <SelectItem key={tipo} value={tipo}>{tipo}</SelectItem>)}</SelectContent></Select></div>
            <div><label className="mb-1 block text-sm font-medium">Número</label><Input value={formDoc.numero} onChange={(e) => setFormDoc({ ...formDoc, numero: e.target.value })} /></div>
            <div><label className="mb-1 block text-sm font-medium">Emissão</label><Input type="date" value={formDoc.data_emissao} onChange={(e) => setFormDoc({ ...formDoc, data_emissao: e.target.value })} /></div>
            <div><label className="mb-1 block text-sm font-medium">Vencimento</label><Input type="date" value={formDoc.data_vencimento} onChange={(e) => setFormDoc({ ...formDoc, data_vencimento: e.target.value })} /></div>
            <div><label className="mb-1 block text-sm font-medium">Arquivo URL</label><Input value={formDoc.arquivo_url} onChange={(e) => setFormDoc({ ...formDoc, arquivo_url: e.target.value })} /></div>
            <div className="md:col-span-2"><label className="mb-1 block text-sm font-medium">Observações</label><Textarea rows={3} value={formDoc.observacoes} onChange={(e) => setFormDoc({ ...formDoc, observacoes: e.target.value })} /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDocOpen(false)}>Cancelar</Button>
            <Button onClick={() => docMutation.mutate({
              ...formDoc,
              colaborador_id: formDoc.colaborador_id || undefined,
              numero: formDoc.numero || undefined,
              data_vencimento: formDoc.data_vencimento || undefined,
              arquivo_url: formDoc.arquivo_url || undefined,
              observacoes: formDoc.observacoes || undefined,
            })}>Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
