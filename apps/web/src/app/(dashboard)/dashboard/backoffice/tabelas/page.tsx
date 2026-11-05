"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Plus, Pencil, Trash2, ChevronRight, Tag, Box, Layers } from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";
import { PageHeader } from "@/components/shared/page-header";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface Marca { id: string; nome: string; nome_fantasia?: string; pais_origem?: string; website?: string; ativo: boolean; }
interface Modelo { id: string; nome: string; referencia?: string; marca_id: string; marca_nome?: string; tipo_produto?: string; ativo: boolean; }
interface Categoria { id: string; nome: string; descricao?: string; parent_id?: string; cor?: string; icone?: string; ordem: number; ativo: boolean; }

// ---------------------------------------------------------------------------
// Marcas Tab
// ---------------------------------------------------------------------------
function MarcasTab() {
  const qc = useQueryClient();
  const [dialog, setDialog] = useState<{ open: boolean; marca?: Marca }>({ open: false });
  const [form, setForm] = useState<Partial<Marca>>({});
  const set = (p: Partial<Marca>) => setForm((f) => ({ ...f, ...p }));

  const { data: marcas = [] } = useQuery<Marca[]>({
    queryKey: ["bo-marcas"],
    queryFn: () => apiFetch("/backoffice/tabelas/marcas"),
  });

  const save = useMutation({
    mutationFn: (f: Partial<Marca>) =>
      dialog.marca
        ? apiFetch(`/backoffice/tabelas/marcas/${dialog.marca.id}`, { method: "PATCH", body: JSON.stringify(f) })
        : apiFetch("/backoffice/tabelas/marcas", { method: "POST", body: JSON.stringify(f) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["bo-marcas"] }); setDialog({ open: false }); },
  });

  const remove = useMutation({
    mutationFn: (id: string) => apiFetch(`/backoffice/tabelas/marcas/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bo-marcas"] }),
  });

  function openNew() { setForm({ nome: "", pais_origem: "Brasil", ativo: true }); setDialog({ open: true }); }
  function openEdit(m: Marca) { setForm(m); setDialog({ open: true, marca: m }); }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <p className="text-sm text-muted-foreground">{marcas.length} marcas cadastradas</p>
        <Button size="sm" variant="outline" onClick={openNew}><Plus className="size-4 mr-1" />Nova Marca</Button>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Nome</TableHead>
            <TableHead>Nome Fantasia</TableHead>
            <TableHead>País</TableHead>
            <TableHead>Website</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="w-20" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {marcas.length === 0 && <TableRow><TableCell colSpan={6} className="text-center text-muted-foreground py-8">Nenhuma marca</TableCell></TableRow>}
          {marcas.map((m) => (
            <TableRow key={m.id}>
              <TableCell className="font-medium">{m.nome}</TableCell>
              <TableCell>{m.nome_fantasia ?? "—"}</TableCell>
              <TableCell>{m.pais_origem ?? "—"}</TableCell>
              <TableCell>{m.website ? <a href={m.website} target="_blank" rel="noreferrer" className="text-primary hover:underline">{m.website}</a> : "—"}</TableCell>
              <TableCell><StatusBadge status={m.ativo ? "ativo" : "inativo"} /></TableCell>
              <TableCell>
                <div className="flex items-center gap-1 justify-end">
                  <Button size="icon" variant="ghost" className="size-7 text-primary hover:text-primary" onClick={() => openEdit(m)}><Pencil className="size-3.5" /></Button>
                  <Button size="icon" variant="ghost" className="size-7 text-destructive hover:text-destructive" onClick={() => remove.mutate(m.id)}><Trash2 className="size-3.5" /></Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <Dialog open={dialog.open} onOpenChange={(o) => setDialog({ open: o })}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle>{dialog.marca ? "Editar Marca" : "Nova Marca"}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5"><Label>Nome *</Label><Input value={form.nome ?? ""} onChange={(e) => set({ nome: e.target.value })} /></div>
            <div className="space-y-1.5"><Label>Nome Fantasia</Label><Input value={form.nome_fantasia ?? ""} onChange={(e) => set({ nome_fantasia: e.target.value })} /></div>
            <div className="space-y-1.5"><Label>País de Origem</Label><Input value={form.pais_origem ?? ""} onChange={(e) => set({ pais_origem: e.target.value })} /></div>
            <div className="space-y-1.5"><Label>Website</Label><Input placeholder="https://..." value={form.website ?? ""} onChange={(e) => set({ website: e.target.value })} /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog({ open: false })}>Cancelar</Button>
            <Button variant="outline" onClick={() => save.mutate(form)} disabled={!form.nome || save.isPending}>{save.isPending ? "Salvando…" : "Salvar"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Modelos Tab
// ---------------------------------------------------------------------------
function ModelosTab() {
  const qc = useQueryClient();
  const [dialog, setDialog] = useState<{ open: boolean; modelo?: Modelo }>({ open: false });
  const [form, setForm] = useState<Partial<Modelo>>({});
  const [filterMarca, setFilterMarca] = useState("all");
  const set = (p: Partial<Modelo>) => setForm((f) => ({ ...f, ...p }));

  const { data: marcas = [] } = useQuery<Marca[]>({
    queryKey: ["bo-marcas"],
    queryFn: () => apiFetch("/backoffice/tabelas/marcas"),
  });

  const { data: modelos = [] } = useQuery<Modelo[]>({
    queryKey: ["bo-modelos", filterMarca],
    queryFn: () => apiFetch(`/backoffice/tabelas/modelos${filterMarca !== "all" ? `?marca_id=${filterMarca}` : ""}`),
  });

  const save = useMutation({
    mutationFn: (f: Partial<Modelo>) =>
      dialog.modelo
        ? apiFetch(`/backoffice/tabelas/modelos/${dialog.modelo.id}`, { method: "PATCH", body: JSON.stringify(f) })
        : apiFetch("/backoffice/tabelas/modelos", { method: "POST", body: JSON.stringify(f) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["bo-modelos"] }); setDialog({ open: false }); },
  });

  const remove = useMutation({
    mutationFn: (id: string) => apiFetch(`/backoffice/tabelas/modelos/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bo-modelos"] }),
  });

  function openNew() { setForm({ nome: "", ativo: true }); setDialog({ open: true }); }
  function openEdit(m: Modelo) { setForm(m); setDialog({ open: true, modelo: m }); }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center gap-3">
        <div className="flex items-center gap-3">
          <Label className="text-sm shrink-0">Filtrar por marca:</Label>
          <Select value={filterMarca} onValueChange={setFilterMarca}>
            <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todas</SelectItem>
              {marcas.map((m) => <SelectItem key={m.id} value={m.id}>{m.nome}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <Button size="sm" variant="outline" onClick={openNew}><Plus className="size-4 mr-1" />Novo Modelo</Button>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Modelo</TableHead>
            <TableHead>Marca</TableHead>
            <TableHead>Referência</TableHead>
            <TableHead>Tipo Produto</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="w-20" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {modelos.length === 0 && <TableRow><TableCell colSpan={6} className="text-center text-muted-foreground py-8">Nenhum modelo</TableCell></TableRow>}
          {modelos.map((m) => (
            <TableRow key={m.id}>
              <TableCell className="font-medium">{m.nome}</TableCell>
              <TableCell>{marcas.find(mk => mk.id === m.marca_id)?.nome ?? "—"}</TableCell>
              <TableCell>{m.referencia ?? "—"}</TableCell>
              <TableCell>{m.tipo_produto ?? "—"}</TableCell>
              <TableCell><StatusBadge status={m.ativo ? "ativo" : "inativo"} /></TableCell>
              <TableCell>
                <div className="flex items-center gap-1 justify-end">
                  <Button size="icon" variant="ghost" className="size-7 text-primary hover:text-primary" onClick={() => openEdit(m)}><Pencil className="size-3.5" /></Button>
                  <Button size="icon" variant="ghost" className="size-7 text-destructive hover:text-destructive" onClick={() => remove.mutate(m.id)}><Trash2 className="size-3.5" /></Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <Dialog open={dialog.open} onOpenChange={(o) => setDialog({ open: o })}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle>{dialog.modelo ? "Editar Modelo" : "Novo Modelo"}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label>Marca *</Label>
              <Select value={form.marca_id ?? "none"} onValueChange={(v: string) => set({ marca_id: v === "none" ? undefined : v })}>
                <SelectTrigger>
                  <SelectValue placeholder={form.marca_id ? (marcas.find(m => m.id === form.marca_id)?.nome ?? form.marca_nome ?? "Selecionar…") : "Selecionar…"} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">— Selecionar —</SelectItem>
                  {marcas.map((m) => <SelectItem key={m.id} value={m.id}>{m.nome}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5"><Label>Nome *</Label><Input value={form.nome ?? ""} onChange={(e) => set({ nome: e.target.value })} /></div>
            <div className="space-y-1.5"><Label>Referência</Label><Input placeholder="Part number / código" value={form.referencia ?? ""} onChange={(e) => set({ referencia: e.target.value })} /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog({ open: false })}>Cancelar</Button>
            <Button variant="outline" onClick={() => save.mutate(form)} disabled={!form.nome || !form.marca_id || save.isPending}>{save.isPending ? "Salvando…" : "Salvar"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Categorias Tab
// ---------------------------------------------------------------------------
function CategoriasTab() {
  const qc = useQueryClient();
  const [dialog, setDialog] = useState<{ open: boolean; cat?: Categoria }>({ open: false });
  const [form, setForm] = useState<Partial<Categoria>>({});
  const set = (p: Partial<Categoria>) => setForm((f) => ({ ...f, ...p }));

  const { data: categorias = [] } = useQuery<Categoria[]>({
    queryKey: ["bo-categorias"],
    queryFn: () => apiFetch("/backoffice/tabelas/categorias-produto"),
  });

  const save = useMutation({
    mutationFn: (f: Partial<Categoria>) =>
      dialog.cat
        ? apiFetch(`/backoffice/tabelas/categorias-produto/${dialog.cat.id}`, { method: "PATCH", body: JSON.stringify(f) })
        : apiFetch("/backoffice/tabelas/categorias-produto", { method: "POST", body: JSON.stringify(f) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["bo-categorias"] }); setDialog({ open: false }); },
  });

  const remove = useMutation({
    mutationFn: (id: string) => apiFetch(`/backoffice/tabelas/categorias-produto/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bo-categorias"] }),
  });

  function openNew() { setForm({ nome: "", cor: "#6366f1", ordem: 0, ativo: true }); setDialog({ open: true }); }
  function openEdit(c: Categoria) { setForm(c); setDialog({ open: true, cat: c }); }

  const raizes = categorias.filter((c) => !c.parent_id);
  const filhos = (pid: string) => categorias.filter((c) => c.parent_id === pid);
  const netos = (pid: string) => categorias.filter((c) => {
    const parent = categorias.find(x => x.id === c.parent_id);
    return parent?.parent_id === pid;
  });

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <p className="text-sm text-muted-foreground">{categorias.length} categorias cadastradas</p>
        <Button size="sm" variant="outline" onClick={openNew}><Plus className="size-4 mr-1" />Nova Categoria</Button>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Nome</TableHead>
            <TableHead>Cor</TableHead>
            <TableHead>Ordem</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="w-20" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {categorias.length === 0 && <TableRow><TableCell colSpan={5} className="text-center text-muted-foreground py-8">Nenhuma categoria</TableCell></TableRow>}
          {raizes.map((cat) => (
            <>
              <TableRow key={cat.id} className="font-medium">
                <TableCell>{cat.nome}</TableCell>
                <TableCell>{cat.cor ? <span className="inline-flex items-center gap-1.5"><span className="size-3 rounded-full border" style={{ background: cat.cor }} />{cat.cor}</span> : "—"}</TableCell>
                <TableCell>{cat.ordem}</TableCell>
                <TableCell><StatusBadge status={cat.ativo ? "ativo" : "inativo"} /></TableCell>
                <TableCell><div className="flex gap-1 justify-end"><Button size="icon" variant="outline" className="size-7" onClick={() => openEdit(cat)}><Pencil className="size-3.5" /></Button><Button size="icon" variant="outline" className="size-7 text-destructive hover:bg-destructive/10" onClick={() => remove.mutate(cat.id)}><Trash2 className="size-3.5" /></Button></div></TableCell>
              </TableRow>
              {filhos(cat.id).map((filho) => (
                <>
                  <TableRow key={filho.id} className="bg-muted/20">
                    <TableCell className="pl-8 text-sm"><span className="flex items-center gap-1 text-muted-foreground"><ChevronRight className="size-3" />{filho.nome}</span></TableCell>
                    <TableCell>{filho.cor ? <span className="inline-flex items-center gap-1.5"><span className="size-3 rounded-full border" style={{ background: filho.cor }} />{filho.cor}</span> : "—"}</TableCell>
                    <TableCell>{filho.ordem}</TableCell>
                    <TableCell><StatusBadge status={filho.ativo ? "ativo" : "inativo"} /></TableCell>
                    <TableCell><div className="flex gap-1 justify-end"><Button size="icon" variant="outline" className="size-7" onClick={() => openEdit(filho)}><Pencil className="size-3.5" /></Button><Button size="icon" variant="outline" className="size-7 text-destructive hover:bg-destructive/10" onClick={() => remove.mutate(filho.id)}><Trash2 className="size-3.5" /></Button></div></TableCell>
                  </TableRow>
                  {categorias.filter(c => c.parent_id === filho.id).map((neto) => (
                    <TableRow key={neto.id} className="bg-muted/10">
                      <TableCell className="pl-14 text-sm"><span className="flex items-center gap-1 text-muted-foreground"><ChevronRight className="size-3" />{neto.nome}</span></TableCell>
                      <TableCell>{neto.cor ? <span className="inline-flex items-center gap-1.5"><span className="size-3 rounded-full border" style={{ background: neto.cor }} />{neto.cor}</span> : "—"}</TableCell>
                      <TableCell>{neto.ordem}</TableCell>
                      <TableCell><StatusBadge status={neto.ativo ? "ativo" : "inativo"} /></TableCell>
                      <TableCell><div className="flex items-center gap-1 justify-end"><Button size="icon" variant="ghost" className="size-7 text-primary hover:text-primary" onClick={() => openEdit(neto)}><Pencil className="size-3.5" /></Button><Button size="icon" variant="ghost" className="size-7 text-destructive hover:text-destructive" onClick={() => remove.mutate(neto.id)}><Trash2 className="size-3.5" /></Button></div></TableCell>
                    </TableRow>
                  ))}
                </>
              ))}
            </>
          ))}
        </TableBody>
      </Table>

      <Dialog open={dialog.open} onOpenChange={(o) => setDialog({ open: o })}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle>{dialog.cat ? "Editar Categoria" : "Nova Categoria"}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5"><Label>Nome *</Label><Input value={form.nome ?? ""} onChange={(e) => set({ nome: e.target.value })} /></div>
            <div className="space-y-1.5">
              <Label>Categoria Pai</Label>
              <Select value={form.parent_id ?? "none"} onValueChange={(v: string) => set({ parent_id: v === "none" ? undefined : v })}>
                <SelectTrigger><SelectValue placeholder="Nenhuma (raiz)" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">— Nenhuma (raiz) —</SelectItem>
                  {categorias.filter(c => c.id !== dialog.cat?.id).map((c) => (
                    <SelectItem key={c.id} value={c.id}>{"  ".repeat(c.parent_id ? (categorias.find(x => x.id === c.parent_id)?.parent_id ? 2 : 1) : 0)}{c.nome}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5"><Label>Descrição</Label><Input value={form.descricao ?? ""} onChange={(e) => set({ descricao: e.target.value })} /></div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Cor</Label>
                <div className="flex gap-2 items-center">
                  <input type="color" value={form.cor ?? "#6366f1"} onChange={(e) => set({ cor: e.target.value })} className="size-9 rounded border cursor-pointer bg-transparent" />
                  <Input value={form.cor ?? ""} onChange={(e) => set({ cor: e.target.value })} className="font-mono text-sm" />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label>Ordem</Label>
                <Input type="number" min={0} value={form.ordem ?? 0} onChange={(e) => set({ ordem: parseInt(e.target.value) || 0 })} />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog({ open: false })}>Cancelar</Button>
            <Button variant="outline" onClick={() => save.mutate(form)} disabled={!form.nome || save.isPending}>{save.isPending ? "Salvando…" : "Salvar"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function TabelasPadraoPage() {
  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Tabelas Padrão do Sistema"
        description="Registros padrão disponibilizados para todos os tenants. Tenants podem visualizar estes registros e criar os seus próprios adicionais."
        icon={<Layers size={22} className="text-primary" />}
        breadcrumbs={[
          { label: "Backoffice", href: "/dashboard/backoffice/dashboard" },
          { label: "Tabelas Padrão" },
        ]}
      />

      <Tabs defaultValue="marcas">
        <div className="border-b bg-muted/5">
          <TabsList className="w-full justify-start h-10 gap-1 bg-transparent p-0 rounded-none">
          <TabsTrigger
            value="marcas"
            className="rounded-t-sm border-b-2 border-transparent data-[selected]:border-primary data-[selected]:bg-accent transition-all hover:bg-accent gap-1.5 px-3 py-2"
          >
            <Tag className="size-3.5" /> Marcas
          </TabsTrigger>
          <TabsTrigger
            value="modelos"
            className="rounded-t-sm border-b-2 border-transparent data-[selected]:border-primary data-[selected]:bg-accent transition-all hover:bg-accent gap-1.5 px-3 py-2"
          >
            <Box className="size-3.5" /> Modelos
          </TabsTrigger>
          <TabsTrigger
            value="categorias"
            className="rounded-t-sm border-b-2 border-transparent data-[selected]:border-primary data-[selected]:bg-accent transition-all hover:bg-accent gap-1.5 px-3 py-2"
          >
            <Layers className="size-3.5" /> Categorias de Produto
          </TabsTrigger>
          </TabsList>
        </div>
        <TabsContent value="marcas" className="pt-4">
          <MarcasTab />
        </TabsContent>
        <TabsContent value="modelos" className="pt-4">
          <ModelosTab />
        </TabsContent>
        <TabsContent value="categorias" className="pt-4">
          <CategoriasTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
