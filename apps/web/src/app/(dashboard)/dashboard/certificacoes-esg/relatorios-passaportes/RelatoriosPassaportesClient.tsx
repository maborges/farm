"use client";

import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FileText, ShieldCheck, Plus, Search, Calendar, RefreshCcw, Download, QrCode } from "lucide-react";
import { useRelatoriosESG, usePassaportes, useCreateRelatorioESG, useCreatePassaporte, useUpdatePassaporteStatus } from "@/hooks/use-relatorios-passaportes";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Badge } from "@/components/ui/badge";
import { QRCodeSVG } from 'qrcode.react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogBody,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import type { PassaporteRastreabilidade, RelatorioESG } from "@/services/certificacoes-esg/service";

function downloadJson(data: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

const formatDate = (dateString: string) => {
  if (!dateString) return "-";
  return format(new Date(dateString), "dd 'de' MMMM 'de' yyyy", { locale: ptBR });
};

function StatusBadge({ status }: { status: string }) {
  const statusConfig: Record<string, { label: string; className: string }> = {
    RASCUNHO: { label: "Rascunho", className: "bg-gray-100 text-gray-800" },
    EM_REVISAO: { label: "Em Revisão", className: "bg-blue-100 text-blue-800" },
    PUBLICADO: { label: "Publicado", className: "bg-green-100 text-green-800" },
    CANCELADO: { label: "Cancelado", className: "bg-red-100 text-red-800" },
    EM_VALIDACAO: { label: "Em Validação", className: "bg-yellow-100 text-yellow-800" },
    REVOGADO: { label: "Revogado", className: "bg-red-100 text-red-800" },
  };

  const config = statusConfig[status] || { label: status, className: "bg-gray-100 text-gray-800" };

  return (
    <Badge variant="outline" className={`font-semibold ${config.className}`}>
      {config.label}
    </Badge>
  );
}

function PassaporteActionsCell({ passaporte }: { passaporte: PassaporteRastreabilidade }) {
  const updatePassaporte = useUpdatePassaporteStatus(passaporte.id);

  const handlePublicar = async () => {
    try {
      await updatePassaporte.mutateAsync({
        status: "PUBLICADO",
        publico: true,
        snapshot_json: { dados: "Snapshot de dados no momento da publicação" }
      });
      toast.success("Passaporte publicado com sucesso e link público gerado!");
    } catch (e) {
      toast.error("Erro ao publicar passaporte");
    }
  };

  return (
    <div className="flex justify-end gap-2">
        {passaporte.status === "PUBLICADO" && passaporte.public_token && (
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8 rounded-sm text-emerald-600 hover:bg-emerald-50 hover:text-emerald-700" title="Ver QR Code">
                <QrCode className="h-4 w-4" />
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle>Passaporte Público</DialogTitle>
                <DialogDescription>
                  Compartilhe este QR Code ou link para acesso público sem necessidade de login.
                </DialogDescription>
              </DialogHeader>
              <DialogBody>
                <div className="flex flex-col items-center justify-center py-2 gap-6">
                  <div className="bg-white p-4 rounded-xl shadow-sm border border-neutral-200 flex items-center justify-center">
                    <QRCodeSVG 
                      value={`${window.location.origin}/public/passaportes/${passaporte.public_token}`} 
                      size={200}
                      level="H"
                      includeMargin={true}
                    />
                  </div>
                  
                  {/* Informações de Integridade */}
                  <div className="w-full bg-neutral-50 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-lg p-4 space-y-3">
                    <div className="flex items-center gap-2 text-sm font-semibold text-neutral-700 dark:text-neutral-300">
                      <ShieldCheck className="w-4 h-4" /> Integridade do Documento
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-xs">
                      <div>
                        <span className="block text-neutral-500">Versão</span>
                        <span className="font-medium">v{passaporte.versao}.0</span>
                      </div>
                      <div>
                        <span className="block text-neutral-500">Data Pública</span>
                        <span className="font-medium">
                          {passaporte.publicado_publicamente_em ? formatDate(passaporte.publicado_publicamente_em) : "-"}
                        </span>
                      </div>
                    </div>
                    <div>
                        <span className="block text-xs text-neutral-500 mb-1">Hash SHA-256</span>
                        <span className="font-mono text-[10px] break-all bg-neutral-100 dark:bg-neutral-950 p-2 rounded block text-neutral-600 border border-neutral-200">
                          {passaporte.snapshot_hash || "Calculando..."}
                        </span>
                    </div>
                  </div>

                  <div className="w-full space-y-2">
                    <Label>Link Público</Label>
                    <div className="flex gap-2">
                      <Input readOnly value={`${window.location.origin}/public/passaportes/${passaporte.public_token}`} className="text-xs" />
                      <Button 
                        size="sm" 
                        variant="secondary"
                        onClick={() => {
                          navigator.clipboard.writeText(`${window.location.origin}/public/passaportes/${passaporte.public_token}`);
                          toast.success("Link copiado!");
                        }}
                      >
                        Copiar
                      </Button>
                    </div>
                  </div>
                </div>
              </DialogBody>
            </DialogContent>
          </Dialog>
        )}
        
        {passaporte.status !== "PUBLICADO" && (
          <Button 
            variant="outline" 
            size="sm" 
            className="h-8 rounded-sm"
            onClick={handlePublicar}
            disabled={updatePassaporte.isPending}
          >
            {updatePassaporte.isPending ? "Publicando..." : "Publicar"}
          </Button>
        )}

        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 rounded-sm"
          title="Baixar dados do passaporte"
          aria-label="Baixar dados do passaporte"
          onClick={() => downloadJson(passaporte, `passaporte-${passaporte.id}.json`)}
        >
          <Download className="h-4 w-4 text-muted-foreground" />
        </Button>
    </div>
  );
}

export function RelatoriosPassaportesClient() {
  const [activeTab, setActiveTab] = useState("relatorios");
  const [isNovoRelatorioOpen, setIsNovoRelatorioOpen] = useState(false);
  const [isNovoPassaporteOpen, setIsNovoPassaporteOpen] = useState(false);
  
  // Relatorio Form State
  const [tituloRelatorio, setTituloRelatorio] = useState("");
  
  // Passaporte Form State
  const [codigoPassaporte, setCodigoPassaporte] = useState("");
  const [descricaoPassaporte, setDescricaoPassaporte] = useState("");

  const { data: relatorios, isLoading: isLoadingRelatorios } = useRelatoriosESG();
  const { data: passaportes, isLoading: isLoadingPassaportes } = usePassaportes();
  const createRelatorio = useCreateRelatorioESG();
  const createPassaporte = useCreatePassaporte();

  const relatoriosColumns: ColumnDef<RelatorioESG>[] = [
    {
      id: "titulo",
      header: "Título",
      accessorKey: "titulo",
      sortable: true,
    },
    {
      id: "status",
      header: "Status",
      accessorKey: "status",
      cell: (val) => <StatusBadge status={val} />,
      sortable: true,
      filterable: true,
    },
    {
      id: "created_at",
      header: "Data de Criação",
      accessorFn: (row) => row.created_at,
      cell: (val) => formatDate(val),
      sortable: true,
    },
    {
      id: "acoes",
      header: "Ações",
      isActionColumn: true,
      cell: (_, row) => (
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 rounded-sm"
          title="Baixar dados do relatório"
          aria-label="Baixar dados do relatório"
          onClick={() => downloadJson(row, `relatorio-esg-${row.id}.json`)}
        >
          <Download className="h-4 w-4 text-muted-foreground" />
        </Button>
      ),
    },
  ];

  const passaportesColumns: ColumnDef<PassaporteRastreabilidade>[] = [
    {
      id: "titulo",
      header: "Identificação",
      accessorKey: "titulo",
      sortable: true,
    },
    {
      id: "status",
      header: "Status",
      accessorKey: "status",
      cell: (val) => <StatusBadge status={val} />,
      sortable: true,
      filterable: true,
    },
    {
      id: "created_at",
      header: "Data de Criação",
      accessorFn: (row) => row.created_at,
      cell: (val) => formatDate(val),
      sortable: true,
    },
    {
      id: "acoes",
      header: "Ações",
      isActionColumn: true,
      cell: (_, row) => <PassaporteActionsCell passaporte={row} />,
    },
  ];

  const handleCreateRelatorio = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createRelatorio.mutateAsync({ titulo: tituloRelatorio });
      toast.success("Relatório ESG criado com sucesso!");
      setIsNovoRelatorioOpen(false);
      setTituloRelatorio("");
    } catch (error) {
      toast.error("Erro ao criar relatório ESG");
    }
  };

  const handleCreatePassaporte = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createPassaporte.mutateAsync({ 
        titulo: descricaoPassaporte.trim()
          ? `${codigoPassaporte.trim()} — ${descricaoPassaporte.trim()}`
          : codigoPassaporte.trim(),
      });
      toast.success("Passaporte criado com sucesso!");
      setIsNovoPassaporteOpen(false);
      setCodigoPassaporte("");
      setDescricaoPassaporte("");
    } catch (error) {
      toast.error("Erro ao criar passaporte");
    }
  };

  return (
    <div className="flex flex-col space-y-6">
      <Tabs defaultValue="relatorios" className="w-full" onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-2 lg:w-[400px]">
          <TabsTrigger value="relatorios">Relatórios ESG</TabsTrigger>
          <TabsTrigger value="passaportes">Passaportes</TabsTrigger>
        </TabsList>

        <TabsContent value="relatorios" className="mt-6 space-y-4">
          <div className="flex justify-between items-center">
            <div></div>
            <Dialog open={isNovoRelatorioOpen} onOpenChange={setIsNovoRelatorioOpen}>
              <DialogTrigger asChild>
                <Button size="sm" className="rounded-sm">
                  <Plus className="mr-2 h-4 w-4" />
                  Novo Relatório
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>Novo Relatório ESG</DialogTitle>
                  <DialogDescription>
                    Crie um novo relatório para compilar indicadores ESG da sua operação.
                  </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleCreateRelatorio} className="flex flex-col flex-1 overflow-hidden">
                  <DialogBody>
                    <div className="grid gap-4 py-2">
                      <div className="grid gap-2">
                        <Label htmlFor="titulo">Título do Relatório</Label>
                        <Input 
                          id="titulo" 
                          value={tituloRelatorio} 
                          onChange={(e) => setTituloRelatorio(e.target.value)} 
                          placeholder="Ex: Relatório de Sustentabilidade 2026"
                          required
                          className="h-8 rounded-sm"
                        />
                      </div>
                    </div>
                  </DialogBody>
                  <DialogFooter>
                    <Button type="button" variant="outline" size="sm" onClick={() => setIsNovoRelatorioOpen(false)} className="rounded-sm">
                      Cancelar
                    </Button>
                    <Button type="submit" size="sm" disabled={createRelatorio.isPending} className="rounded-sm">
                      {createRelatorio.isPending ? "Criando..." : "Criar Relatório"}
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
          </div>

          <Card className="rounded-sm border-border/50 shadow-sm">
            <CardHeader className="py-4">
              <CardTitle className="text-lg">Meus Relatórios ESG</CardTitle>
              <CardDescription>Gerencie as publicações de dados ESG e certificações.</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoadingRelatorios ? (
                <div className="flex justify-center p-8"><RefreshCcw className="h-6 w-6 animate-spin text-muted-foreground" /></div>
              ) : relatorios?.length === 0 ? (
                <div className="text-center p-8 border border-dashed rounded-md">
                  <ShieldCheck className="mx-auto h-12 w-12 text-muted-foreground/50 mb-4" />
                  <h3 className="text-lg font-medium">Nenhum relatório ESG encontrado</h3>
                  <p className="text-muted-foreground mt-2 mb-4">Comece criando o seu primeiro relatório de sustentabilidade.</p>
                  <Button variant="outline" size="sm" onClick={() => setIsNovoRelatorioOpen(true)} className="rounded-sm">Criar Agora</Button>
                </div>
              ) : (
                <DataTable 
                  columns={relatoriosColumns} 
                  data={relatorios || []} 
                  className="border-0 shadow-none" 
                  searchPlaceholder="Buscar relatórios..." 
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="passaportes" className="mt-6 space-y-4">
          <div className="flex justify-between items-center">
            <div></div>
            <Dialog open={isNovoPassaporteOpen} onOpenChange={setIsNovoPassaporteOpen}>
              <DialogTrigger asChild>
                <Button size="sm" className="rounded-sm">
                  <Plus className="mr-2 h-4 w-4" />
                  Novo Passaporte
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>Novo Passaporte de Rastreabilidade</DialogTitle>
                  <DialogDescription>
                    Gere um passaporte com a rastreabilidade completa do produto.
                  </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleCreatePassaporte} className="flex flex-col flex-1 overflow-hidden">
                  <DialogBody>
                    <div className="grid gap-4 py-2">
                      <div className="grid gap-2">
                        <Label htmlFor="codigo">Código do Passaporte (SKU, Lote, etc)</Label>
                        <Input 
                          id="codigo" 
                          value={codigoPassaporte} 
                          onChange={(e) => setCodigoPassaporte(e.target.value)} 
                          placeholder="Ex: LOTE-SOJA-2026-A"
                          required
                          className="h-8 rounded-sm"
                        />
                      </div>
                      <div className="grid gap-2">
                        <Label htmlFor="descricao">Descrição (Opcional)</Label>
                        <Input 
                          id="descricao" 
                          value={descricaoPassaporte} 
                          onChange={(e) => setDescricaoPassaporte(e.target.value)} 
                          placeholder="Ex: Soja Sustentável Fazenda Boa Vista"
                          className="h-8 rounded-sm"
                        />
                      </div>
                    </div>
                  </DialogBody>
                  <DialogFooter>
                    <Button type="button" variant="outline" size="sm" onClick={() => setIsNovoPassaporteOpen(false)} className="rounded-sm">
                      Cancelar
                    </Button>
                    <Button type="submit" size="sm" disabled={createPassaporte.isPending} className="rounded-sm">
                      {createPassaporte.isPending ? "Criando..." : "Gerar Passaporte"}
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
          </div>

          <Card className="rounded-sm border-border/50 shadow-sm">
            <CardHeader className="py-4">
              <CardTitle className="text-lg">Passaportes de Rastreabilidade</CardTitle>
              <CardDescription>Certificados digitais emitidos para lotes e produtos.</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoadingPassaportes ? (
                <div className="flex justify-center p-8"><RefreshCcw className="h-6 w-6 animate-spin text-muted-foreground" /></div>
              ) : passaportes?.length === 0 ? (
                <div className="text-center p-8 border border-dashed rounded-md">
                  <FileText className="mx-auto h-12 w-12 text-muted-foreground/50 mb-4" />
                  <h3 className="text-lg font-medium">Nenhum passaporte gerado</h3>
                  <p className="text-muted-foreground mt-2 mb-4">Emita passaportes para comprovar a origem dos seus produtos.</p>
                  <Button variant="outline" size="sm" onClick={() => setIsNovoPassaporteOpen(true)} className="rounded-sm">Gerar Passaporte</Button>
                </div>
              ) : (
                <DataTable 
                  columns={passaportesColumns} 
                  data={passaportes || []} 
                  className="border-0 shadow-none" 
                  searchPlaceholder="Buscar passaportes..." 
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
