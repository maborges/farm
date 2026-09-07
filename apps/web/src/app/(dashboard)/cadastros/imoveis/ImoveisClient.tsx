"use client";
import * as React from "react";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { useHasModule } from "@/hooks/use-has-module";
import { Modulos } from "@/lib/constants/modulos";
import { toast } from "sonner";
import {
  Home, FileText, Plus, Search, MapPin, Ruler, AlertTriangle, Eye,
  CheckCircle2, XCircle, Clock, Upload, Download, Pencil, Trash2, TrendingUp
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
  DialogDescription, DialogBody
} from "@/components/ui/dialog";
import { Save } from "lucide-react";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ArrendamentosClient } from "./ArrendamentosClient";
import { PermissionGuard } from "@/components/auth/permission-guard";
import { parseLocaleNumber } from "@/lib/utils";

export interface ImovelRural {
  id: string;
  tenant_id: string;
  unidade_produtiva_id: string | null;
  nome: string;
  nirf?: string;
  car_numero?: string;
  ccir_numero?: string;
  sigef_codigo?: string;
  area_total_ha: number;
  area_aproveitavel_ha?: number;
  area_app_ha?: number;
  area_rl_ha?: number;
  numero_matricula?: string;
  municipio?: string;
  uf?: string;
  situacao: string;
  proprietario_nome?: string;
  propriedades_vinculadas_count?: number;
  vinculo_status?: string;
  propriedade_id?: string | null;
  propriedade_nome?: string | null;
  tipo_vinculo?: string | null;
}

export interface UnidadeProdutiva {
  id: string;
  nome: string;
  area_total_ha: number;
  municipio?: string | null;
  uf?: string | null;
}

interface PropriedadeOption {
  id: string;
  nome: string;
  ativo?: boolean;
}

const SITUACAO_BADGE: Record<string, string> = {
  regular: "bg-green-100 text-green-700 border-green-300",
  pendente: "bg-yellow-100 text-yellow-700 border-yellow-300",
  irregular: "bg-red-100 text-red-700 border-red-300",
};

const SITUACAO_ICON: Record<string, React.ReactNode> = {
  regular: <CheckCircle2 className="h-4 w-4" />,
  pendente: <Clock className="h-4 w-4" />,
  irregular: <XCircle className="h-4 w-4" />,
};

const TIPO_IMOVEL_OPTIONS = [
  { value: "rural", label: "Rural" },
  { value: "particular", label: "Particular" },
  { value: "devoluta", label: "Devoluta" },
  { value: "posse", label: "Posse" },
];

function formatAreaHa(value: number | string | null | undefined) {
  const numericValue = typeof value === "string" ? Number(value) : value;
  return Number.isFinite(numericValue ?? NaN) ? Number(numericValue).toFixed(2) : "-";
}

function formatCountLabel(count: number) {
  if (count === 0) return "Não vinculado";
  return count === 1 ? "1 propriedade vinculada" : `${count} propriedades vinculadas`;
}

function getTipoImovelLabel(tipo?: string | null) {
  return TIPO_IMOVEL_OPTIONS.find((option) => option.value === tipo)?.label ?? "Selecione";
}

export function ImoveisClient({ 
  initialImoveis, initialFazendas, initialActiveFazendaId 
}: { 
  initialImoveis: ImovelRural[], initialFazendas: UnidadeProdutiva[], initialActiveFazendaId?: string 
}) {
  const { activeFazendaId, tenant, unidadesProdutivasAutorizadas } = useAppStore();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [situacaoFilter, setSituacaoFilter] = useState("all");
  const [open, setOpen] = useState(false);
  const [selectedImovel, setSelectedImovel] = useState<ImovelRural | null>(null);
  const [form, setForm] = useState({
    nome: "",
    unidade_produtiva_id: "",
    nirf: "",
    car_numero: "",
    ccir_numero: "",
    sigef_codigo: "",
    area_total_ha: "",
    area_aproveitavel_ha: "",
    area_app_ha: "",
    area_rl_ha: "",
    motivo_alteracao_area: "",
    numero_matricula: "",
    propriedade_id: "",
    tipo_vinculo: "PROPRIEDADE_PRINCIPAL",
    municipio: "",
    uf: "",
    situacao: "PROPRIO",
    proprietario_nome: "",
    tipo: "rural" as any,
    observacao: "",
  });

  const hasImoveisModule = useHasModule(Modulos.IMOVEIS_CADASTRO);

  // Usa as fazendas autorizadas do store (já populado no login/refresh)
  const fazendas = unidadesProdutivasAutorizadas.length > 0 ? unidadesProdutivasAutorizadas : initialFazendas;

  const { data: propriedades = [] } = useQuery<PropriedadeOption[]>({
    queryKey: ["propriedades-imoveis-select"],
    queryFn: async () => apiFetch("/cadastros/propriedades?ativo=true"),
    enabled: hasImoveisModule,
  });

  const getFazendaById = React.useCallback(
    (id?: string | null) => {
      if (!id) return null;
      return fazendas.find((fazenda) => fazenda.id === id) ?? null;
    },
    [fazendas]
  );

  const getFazendaLabel = React.useCallback(
    (id?: string | null) => {
      if (!id) return "Selecione";
      return getFazendaById(id)?.nome ?? "Selecione";
    },
    [getFazendaById]
  );

  const getPropriedadeLabel = React.useCallback(
    (id?: string | null) => {
      if (!id) return "Não vincular";
      return propriedades.find((propriedade) => propriedade.id === id)?.nome ?? "Não vincular";
    },
    [propriedades]
  );

  const buildImovelPayload = (data: typeof form) => ({
    ...data,
    area_total_ha: parseLocaleNumber(data.area_total_ha, 0),
    area_aproveitavel_ha: data.area_aproveitavel_ha ? parseLocaleNumber(data.area_aproveitavel_ha) : undefined,
    area_app_ha: data.area_app_ha ? parseLocaleNumber(data.area_app_ha) : undefined,
    area_rl_ha: data.area_rl_ha ? parseLocaleNumber(data.area_rl_ha) : undefined,
    motivo_alteracao_area: data.motivo_alteracao_area || undefined,
    propriedade_id: data.propriedade_id || undefined,
    tipo_vinculo: data.propriedade_id ? data.tipo_vinculo || "PROPRIEDADE_PRINCIPAL" : undefined,
  });


  // Busca imóveis
  const { data: imoveis = [], isLoading } = useQuery<ImovelRural[]>({
    queryKey: ["imoveis-rurais", situacaoFilter],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (situacaoFilter !== "all") params.set("situacao", situacaoFilter);
      const queryString = params.toString();
      return apiFetch(`imoveis/${queryString ? `?${queryString}` : ""}`);
    },
    enabled: hasImoveisModule,
    placeholderData: situacaoFilter === "all" ? initialImoveis : undefined,
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: typeof form) =>
      apiFetch("imoveis/", {
        method: "POST",
        body: JSON.stringify(buildImovelPayload(data)),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["imoveis-rurais"] });
      setOpen(false);
      resetForm();
      toast.success("Imóvel rural criado com sucesso");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Erro ao criar imóvel");
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<typeof form> }) =>
      apiFetch(`imoveis/${id}`, {
        method: "PATCH",
        body: JSON.stringify(buildImovelPayload(data as typeof form)),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["imoveis-rurais"] });
      setOpen(false);
      setSelectedImovel(null);
      resetForm();
      toast.success("Imóvel atualizado com sucesso");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Erro ao atualizar imóvel");
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`imoveis/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["imoveis-rurais"] });
      setOpen(false);
      setSelectedImovel(null);
      toast.success("Imóvel excluído com sucesso");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Erro ao excluir imóvel");
    },
  });

  const resetForm = () => {
    setForm({
      nome: "",
      unidade_produtiva_id: "",
      nirf: "",
      car_numero: "",
      ccir_numero: "",
      sigef_codigo: "",
      area_total_ha: "",
      area_aproveitavel_ha: "",
      area_app_ha: "",
      area_rl_ha: "",
      motivo_alteracao_area: "",
      numero_matricula: "",
      propriedade_id: "",
      tipo_vinculo: "PROPRIEDADE_PRINCIPAL",
      situacao: "PROPRIO",
      proprietario_nome: "",
      municipio: "",
      uf: "",
      tipo: "rural",
      observacao: "",
    });
  };

  const handleOpenCreate = () => {
    resetForm();
    setSelectedImovel(null);
    if (activeFazendaId) {
      const fazendaAtiva = getFazendaById(activeFazendaId);
      setForm((prev) => ({
        ...prev,
        unidade_produtiva_id: activeFazendaId,
        municipio: fazendaAtiva?.municipio ?? prev.municipio,
        uf: fazendaAtiva?.uf ?? prev.uf,
      }));
    }
    setOpen(true);
  };

  const handleOpenEdit = (imovel: ImovelRural) => {
    const fazendaOrigem = getFazendaById(imovel.unidade_produtiva_id);
    setForm({
      nome: imovel.nome,
      unidade_produtiva_id: imovel.unidade_produtiva_id,
      numero_matricula: imovel.numero_matricula || "",
      situacao: imovel.situacao || "PROPRIO",
      proprietario_nome: imovel.proprietario_nome || "",
      nirf: imovel.nirf || "",
      car_numero: imovel.car_numero || "",
      ccir_numero: imovel.ccir_numero || "",
      sigef_codigo: imovel.sigef_codigo || "",
      area_total_ha: String(imovel.area_total_ha),
      area_aproveitavel_ha: String(imovel.area_aproveitavel_ha || "") || "",
      area_app_ha: String(imovel.area_app_ha || "") || "",
      area_rl_ha: String(imovel.area_rl_ha || "") || "",
      motivo_alteracao_area: "",
      propriedade_id: imovel.propriedade_id || "",
      tipo_vinculo: imovel.tipo_vinculo || "PROPRIEDADE_PRINCIPAL",
      municipio: imovel.municipio || fazendaOrigem?.municipio || "",
      uf: imovel.uf || fazendaOrigem?.uf || "",
      tipo: (imovel as any).tipo,
      observacao: (imovel as any).observacao || "",
    });
    setSelectedImovel(imovel);
    setOpen(true);
  };

  React.useEffect(() => {
    if (!open || !form.unidade_produtiva_id) return;
    const fazendaOrigem = getFazendaById(form.unidade_produtiva_id);
    if (!fazendaOrigem) return;

    setForm((prev) => {
      const nextMunicipio = prev.municipio || fazendaOrigem.municipio || "";
      const nextUf = prev.uf || fazendaOrigem.uf || "";

      if (nextMunicipio === prev.municipio && nextUf === prev.uf) {
        return prev;
      }

      return {
        ...prev,
        municipio: nextMunicipio,
        uf: nextUf,
      };
    });
  }, [open, form.unidade_produtiva_id, getFazendaById]);

  const handleSubmit = () => {
    if (!form.nome || !form.unidade_produtiva_id || !form.municipio || !form.uf) {
      toast.error("Preencha os campos obrigatórios");
      return;
    }

    const areaAtual = Number(form.area_total_ha || 0);
    const areaOriginal = Number(selectedImovel?.area_total_ha || 0);
    const areaAlterada = Boolean(selectedImovel) && Number.isFinite(areaAtual) && areaAtual > 0 && areaAtual !== areaOriginal;

    if (areaAlterada && !form.motivo_alteracao_area.trim()) {
      toast.error("Informe a justificativa da alteração de área.");
      return;
    }

    if (selectedImovel) {
      updateMutation.mutate({
        id: selectedImovel.id,
        data: form,
      });
    } else {
      createMutation.mutate(form);
    }
  };

  const handleDelete = () => {
    if (selectedImovel) {
      deleteMutation.mutate(selectedImovel.id);
    }
  };

  // Filtra imóveis
  const filteredImoveis = (imoveis || []).filter((imovel) => {
    const matchSearch = imovel.nome.toLowerCase().includes(search.toLowerCase()) ||
      imovel.municipio.toLowerCase().includes(search.toLowerCase());
    const matchSituacao = situacaoFilter === "all" || imovel.situacao === situacaoFilter;
    return matchSearch && matchSituacao;
  });

  if (!hasImoveisModule) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Home className="h-16 w-16 mx-auto mb-4 text-gray-400" />
          <h2 className="text-xl font-semibold mb-2">Módulo Imóveis Rurais não contratado</h2>
          <p className="text-gray-600">
            Entre em contato com o administrador para habilitar o módulo de gestão de imóveis rurais.
          </p>
        </div>
      </div>
    );
  }

  const areaAtualEdicao = Number(form.area_total_ha || 0);
  const areaOriginalEdicao = Number(selectedImovel?.area_total_ha || 0);
  const areaAlteradaEmEdicao =
    Boolean(selectedImovel) &&
    Number.isFinite(areaAtualEdicao) &&
    areaAtualEdicao > 0 &&
    areaAtualEdicao !== areaOriginalEdicao;

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Imóveis Rurais"
        description="Gestão de propriedades rurais, NIRF, CAR, CCIR e documentação legal"
        icon={<Home className="text-primary" size={22} />}
        breadcrumbs={[
            { label: "Cadastros", href: "/cadastros" },
            { label: "Imóveis Rurais" },
        ]}
        actions={
          <div className="flex items-center gap-2">
            <Button asChild size="sm" className="rounded-sm outline-none border-primary/50 text-primary hover:bg-primary/5" variant="outline">
              <Link href="/cadastros/imoveis/avaliacoes">
                <TrendingUp className="size-3.5 mr-1.5" />
                Avaliações
              </Link>
            </Button>
            <PermissionGuard permission="tenant:imoveis:create">
              <Button onClick={handleOpenCreate} size="sm" className="rounded-sm outline-none border-primary/50 text-primary hover:bg-primary/5" variant="outline">
                <Plus className="size-3.5 mr-1.5" />
                Novo Imóvel
              </Button>
            </PermissionGuard>
          </div>
        }
      />

      {/* Filtros */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Buscar por nome ou município..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <Select value={situacaoFilter} onValueChange={setSituacaoFilter}>
              <SelectTrigger className="w-[200px] h-8 rounded-sm text-xs">
                <SelectValue placeholder="Situação" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas</SelectItem>
                <SelectItem value="regular">Regular</SelectItem>
                <SelectItem value="pendente">Pendente</SelectItem>
                <SelectItem value="irregular">Irregular</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Lista de Imóveis */}
      <Card>
        <CardHeader>
          <CardTitle>Imóveis Cadastrados</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-gray-500">Carregando...</div>
          ) : filteredImoveis.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Home className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>Nenhum imóvel encontrado</p>
            </div>
          ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nome</TableHead>
                    <TableHead>Município/UF</TableHead>
                    <TableHead>Área Total (ha)</TableHead>
                    <TableHead>NIRF</TableHead>
                    <TableHead>CAR</TableHead>
                    <TableHead>Matrícula</TableHead>
                    <TableHead>SIGEF</TableHead>
                    <TableHead>Vínculo</TableHead>
                    <TableHead>Situação</TableHead>
                    <TableHead className="text-right">Ações</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                {filteredImoveis.map((imovel) => (
                  <TableRow key={imovel.id} className="hover:bg-muted/30">
                    <TableCell className="font-medium">{imovel.nome}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1 text-xs">
                        <MapPin className="h-3 w-3 text-gray-400" />
                        {imovel.municipio}/{imovel.uf}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1 text-xs">
                        <Ruler className="h-3 w-3 text-gray-400" />
                        {formatAreaHa(imovel.area_total_ha)}
                      </div>
                    </TableCell>
                    <TableCell className="text-xs">{imovel.nirf || "-"}</TableCell>
                    <TableCell className="text-xs">{imovel.car_numero || "-"}</TableCell>
                    <TableCell className="text-xs">{imovel.numero_matricula || "-"}</TableCell>
                    <TableCell className="text-xs">{imovel.sigef_codigo || "-"}</TableCell>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        <Badge
                          variant={imovel.vinculo_status === "VINCULADO" ? "secondary" : "outline"}
                          className="rounded-sm text-[10px] uppercase font-bold px-1.5 py-0"
                        >
                          {imovel.vinculo_status || "Não vinculado"}
                        </Badge>
                        <span className="text-[10px] text-foreground">{imovel.propriedade_nome || "-"}</span>
                        <span className="text-[10px] text-muted-foreground">{formatCountLabel(imovel.propriedades_vinculadas_count || 0)}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={`rounded-sm text-[10px] uppercase font-bold px-1.5 py-0 ${SITUACAO_BADGE[imovel.situacao]}`}>
                        <span className="flex items-center gap-1">
                          {SITUACAO_ICON[imovel.situacao]}
                          {imovel.situacao}
                        </span>
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0 rounded-sm hover:bg-primary/10 hover:text-primary"
                          asChild
                        >
                          <Link href={`/cadastros/imoveis/${imovel.id}/visao-fundiaria`}>
                            <Eye className="h-3.5 w-3.5" />
                          </Link>
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0 rounded-sm hover:bg-primary/10 hover:text-primary"
                          onClick={() => handleOpenEdit(imovel)}
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0 rounded-sm hover:bg-destructive/10 hover:text-destructive"
                          onClick={() => {
                            setSelectedImovel(imovel);
                            handleDelete();
                          }}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <ArrendamentosClient
        imoveis={imoveis}
        fazendas={fazendas}
        activeFazendaId={activeFazendaId}
      />

      {/* Dialog de Create/Edit */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-xl p-0">
          <DialogHeader>
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                <Home className="size-4 text-primary" />
              </div>
              <div className="flex flex-col">
                <DialogTitle>
                  {selectedImovel ? "Editar Imóvel Rural" : "Novo Imóvel Rural"}
                </DialogTitle>
                <DialogDescription className="text-[11px] leading-none mt-1">
                  Cadastre as informações legais do imóvel rural (NIRF, CAR, CCIR, matrícula)
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          <DialogBody>

          <Tabs defaultValue="dados" className="mt-4">
            <TabsList>
              <TabsTrigger value="dados">Dados Principais</TabsTrigger>
              <TabsTrigger value="documentos">Documentos</TabsTrigger>
              <TabsTrigger value="areas">Áreas</TabsTrigger>
            </TabsList>

            <TabsContent value="dados" className="space-y-4 mt-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="imovel-nome" className="text-sm font-medium mb-1 block">Nome *</label>
                  <Input
                    id="imovel-nome"
                    value={form.nome}
                    onChange={(e) => setForm({ ...form, nome: e.target.value })}
                    placeholder="Ex: Fazenda São João"
                  />
                </div>
              <div>
                <label className="text-sm font-medium mb-1 block">Fazenda *</label>
                <Select
                  value={form.unidade_produtiva_id || undefined}
                  onValueChange={(value: string) => setForm({ ...form, unidade_produtiva_id: value })}
                >
                    <SelectTrigger aria-label="Fazenda">
                      {getFazendaLabel(form.unidade_produtiva_id)}
                    </SelectTrigger>
                    <SelectContent>
                      {fazendas.map((fazenda) => (
                        <SelectItem key={fazenda.id} value={fazenda.id}>
                          {fazenda.nome}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="imovel-municipio" className="text-sm font-medium mb-1 block">Município *</label>
                  <Input
                    id="imovel-municipio"
                    value={form.municipio}
                    onChange={(e) => setForm({ ...form, municipio: e.target.value })}
                  />
                </div>
              <div>
                <label className="text-sm font-medium mb-1 block">UF *</label>
                <Select
                  value={form.uf || undefined}
                  onValueChange={(value: string) => setForm({ ...form, uf: value })}
                >
                    <SelectTrigger aria-label="UF">
                      {form.uf || "Selecione"}
                    </SelectTrigger>
                    <SelectContent>
                      {["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
                        "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
                        "RS", "RO", "RR", "SC", "SP", "SE", "TO"].map((uf) => (
                        <SelectItem key={uf} value={uf}>{uf}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div>
                <label className="text-sm font-medium mb-1 block">Tipo</label>
                <Select
                  value={form.tipo}
                  onValueChange={(value: typeof form.tipo) => setForm({ ...form, tipo: value })}
                >
                  <SelectTrigger aria-label="Tipo">
                    {getTipoImovelLabel(form.tipo)}
                  </SelectTrigger>
                  <SelectContent>
                    {TIPO_IMOVEL_OPTIONS.map((tipo) => (
                      <SelectItem key={tipo.value} value={tipo.value}>
                        {tipo.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="text-sm font-medium mb-1 block">Observações</label>
                <Textarea
                  value={form.observacao}
                  onChange={(e) => setForm({ ...form, observacao: e.target.value })}
                  rows={3}
                />
              </div>
            </TabsContent>

            <TabsContent value="documentos" className="space-y-4 mt-4">
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  Os documentos legais (CCIR, ITR, CAR) podem ser gerenciados na aba Documentos Legais
                </AlertDescription>
              </Alert>

              <div className="space-y-2 rounded-sm border border-dashed p-4">
                <div>
                  <label className="text-sm font-medium mb-1 block">
                    Vincular este imóvel rural a uma propriedade existente
                  </label>
                  <p className="text-xs text-muted-foreground">
                    Opcional. Selecione uma Propriedade para criar o vínculo oficial sem duplicar o imóvel rural.
                  </p>
                </div>
                <Select
                  value={form.propriedade_id || "__none__"}
                  onValueChange={(value: string) =>
                    setForm({
                      ...form,
                      propriedade_id: value === "__none__" ? "" : value,
                      tipo_vinculo: "PROPRIEDADE_PRINCIPAL",
                    })
                  }
                >
                  <SelectTrigger aria-label="Vincular este imóvel rural a uma propriedade existente">
                    {getPropriedadeLabel(form.propriedade_id)}
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">
                      Não vincular
                    </SelectItem>
                    {propriedades.map((propriedade) => (
                      <SelectItem key={propriedade.id} value={propriedade.id}>
                        {propriedade.nome}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="imovel-nirf" className="text-sm font-medium mb-1 block">NIRF</label>
                  <Input
                    id="imovel-nirf"
                    value={form.nirf}
                    onChange={(e) => setForm({ ...form, nirf: e.target.value })}
                    placeholder="000.000.000-0"
                  />
                </div>
                <div>
                  <label htmlFor="imovel-car" className="text-sm font-medium mb-1 block">CAR</label>
                  <Input
                    id="imovel-car"
                    value={form.car_numero}
                    onChange={(e) => setForm({ ...form, car_numero: e.target.value })}
                    placeholder="UF000000000000"
                  />
                </div>
              </div>

              {areaAlteradaEmEdicao && (
                <div>
                  <label htmlFor="imovel-motivo-alteracao-area" className="text-sm font-medium mb-1 block">
                    Justificativa da alteração de área *
                  </label>
                  <Textarea
                    id="imovel-motivo-alteracao-area"
                    value={form.motivo_alteracao_area}
                    onChange={(e) => setForm({ ...form, motivo_alteracao_area: e.target.value })}
                    placeholder="Ex: Retificação de área conforme nova medição georreferenciada."
                    rows={3}
                  />
                  <p className="mt-1 text-xs text-muted-foreground">
                    Área anterior: {areaOriginalEdicao.toLocaleString("pt-BR", { minimumFractionDigits: 0, maximumFractionDigits: 4 })} ha
                  </p>
                </div>
              )}

              <div>
                <label htmlFor="imovel-ccir" className="text-sm font-medium mb-1 block">CCIR</label>
                <Input
                  id="imovel-ccir"
                  value={form.ccir_numero}
                  onChange={(e) => setForm({ ...form, ccir_numero: e.target.value })}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="imovel-matricula" className="text-sm font-medium mb-1 block">Matrícula</label>
                  <Input
                    id="imovel-matricula"
                    value={form.numero_matricula}
                    onChange={(e) => setForm({ ...form, numero_matricula: e.target.value })}
                  />
                </div>
                <div>
                  <label htmlFor="imovel-sigef" className="text-sm font-medium mb-1 block">SIGEF</label>
                  <Input
                    id="imovel-sigef"
                    value={form.sigef_codigo}
                    onChange={(e) => setForm({ ...form, sigef_codigo: e.target.value })}
                  />
                </div>
              </div>
            </TabsContent>

            <TabsContent value="areas" className="space-y-4 mt-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="imovel-area-total" className="text-sm font-medium mb-1 block">Área Total (ha) *</label>
                  <Input
                    id="imovel-area-total"
                    type="number"
                    step="0.0001"
                    value={form.area_total_ha}
                    onChange={(e) => setForm({ ...form, area_total_ha: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium mb-1 block">Área Aproveitável (ha)</label>
                  <Input
                    type="number"
                    step="0.0001"
                    value={form.area_aproveitavel_ha}
                    onChange={(e) => setForm({ ...form, area_aproveitavel_ha: e.target.value })}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium mb-1 block">Área APP (ha)</label>
                  <Input
                    type="number"
                    step="0.0001"
                    value={form.area_app_ha}
                    onChange={(e) => setForm({ ...form, area_app_ha: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium mb-1 block">Área Reserva Legal (ha)</label>
                  <Input
                    type="number"
                    step="0.0001"
                    value={form.area_rl_ha}
                    onChange={(e) => setForm({ ...form, area_rl_ha: e.target.value })}
                  />
                </div>
              </div>
            </TabsContent>
          </Tabs>
          </DialogBody>

          <DialogFooter>
            <Button variant="outline" size="sm" className="rounded-sm" onClick={() => setOpen(false)}>
              <XCircle className="size-3.5 mr-1.5" />
              Cancelar
            </Button>
            <Button 
              variant="outline"
              size="sm"
              className="rounded-sm border-primary/50 text-primary hover:bg-primary/5"
              onClick={handleSubmit} 
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              <Save className="size-3.5 mr-1.5" />
              {selectedImovel ? "Salvar Alterações" : "Criar Imóvel"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
