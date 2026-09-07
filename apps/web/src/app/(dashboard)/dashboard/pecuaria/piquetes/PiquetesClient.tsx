"use client";

import { useMemo, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Layers, Loader2, MapPin, Maximize2, Plus, Scale } from "lucide-react";
import { toast } from "sonner";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { cn } from "@/lib/utils";

export interface PiqueteCreate {
  unidade_produtiva_id: string;
  parent_id: string;
  tipo: string;
  nome: string;
  area_hectares: number;
  dados_extras?: Record<string, unknown>;
}

export interface PiqueteArea {
  id: string;
  nome: string;
  tipo: string;
  area_hectares: number | null;
  ativo: boolean;
  dados_extras?: {
    capacidade_suporte_ua?: number | null;
  } | null;
}

export interface AreaRuralOption {
  id: string;
  nome: string;
  tipo: string;
}

const INPUT_CLASSNAME = "h-8 rounded-sm text-xs";
const EMPTY_OPTION_VALUE = "__empty__";
const FRIENDLY_AREA_MESSAGE =
  "Selecione uma Área Operacional antes de criar o piquete. Caso ainda não exista, cadastre primeiro a área física da fazenda.";

function FormField({
  label,
  children,
  required = false,
}: {
  label: string;
  children: ReactNode;
  required?: boolean;
}) {
  return (
    <label className="space-y-1.5">
      <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
        {label}
        {required ? <span className="text-destructive"> *</span> : null}
      </div>
      {children}
    </label>
  );
}

function getFriendlyPiqueteError(error: Error) {
  const message = error.message.toLowerCase();

  if (
    message.includes("parent_id") ||
    message.includes("area_id") ||
    message.includes("área operacional") ||
    message.includes("area operacional") ||
    message.includes("campo inválido") ||
    message.includes("campo invalido")
  ) {
    return FRIENDLY_AREA_MESSAGE;
  }

  return error.message || "Erro ao criar piquete.";
}

function NovoPiqueteDialog({
  fazendaId,
  parentOptions,
  open,
  onOpenChange,
}: {
  fazendaId: string;
  parentOptions: AreaRuralOption[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ nome: "", area_ha: "", capacidade_suporte_ua: "", parent_id: "" });

  const mutation = useMutation({
    mutationFn: (payload: PiqueteCreate) =>
      apiFetch("/cadastros/areas-rurais/", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => {
      toast.success("Piquete criado com sucesso.");
      queryClient.invalidateQueries({ queryKey: ["piquetes"] });
      queryClient.invalidateQueries({ queryKey: ["areas-rurais", fazendaId] });
      setForm({ nome: "", area_ha: "", capacidade_suporte_ua: "", parent_id: "" });
      onOpenChange(false);
    },
    onError: (err: Error) => toast.error(getFriendlyPiqueteError(err)),
  });

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();

    if (!form.parent_id) {
      toast.error(FRIENDLY_AREA_MESSAGE);
      return;
    }

    const payload: PiqueteCreate = {
      unidade_produtiva_id: fazendaId,
      tipo: "PIQUETE",
      parent_id: form.parent_id,
      nome: form.nome.trim(),
      area_hectares: Number(form.area_ha),
      dados_extras: form.capacidade_suporte_ua
        ? { capacidade_suporte_ua: Number(form.capacidade_suporte_ua) }
        : undefined,
    };

    mutation.mutate(payload);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg rounded-sm border border-border-subtle bg-surface shadow-2xl gap-0 ring-0">
        <DialogHeader className="border-b border-border-subtle px-6 py-5">
          <DialogTitle className="text-base font-bold text-primary">Novo piquete</DialogTitle>
          <p className="text-xs text-muted-foreground">
            Cadastre uma subdivisão de pastejo vinculada à base física da fazenda.
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 px-6 py-5">
          <FormField label="Nome do piquete" required>
            <Input
              required
              className={INPUT_CLASSNAME}
              placeholder="Ex: Piquete 01 - Braquiária"
              value={form.nome}
              onChange={(event) => setForm((current) => ({ ...current, nome: event.target.value }))}
            />
          </FormField>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-1.5 md:col-span-2">
              <FormField label="Área Operacional da Pecuária" required>
                <Select
                  value={form.parent_id || EMPTY_OPTION_VALUE}
                  onValueChange={(value) =>
                    setForm((current) => ({
                      ...current,
                      parent_id: value === EMPTY_OPTION_VALUE ? "" : value,
                    }))
                  }
                >
                  <SelectTrigger className={INPUT_CLASSNAME}>
                    <SelectValue placeholder="Selecione" />
                  </SelectTrigger>
                  <SelectContent className="rounded-sm text-xs">
                    {parentOptions.map((item) => (
                      <SelectItem key={item.id} value={item.id}>
                        {item.nome} • Base física
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>
              <p className="text-[11px] leading-4 text-muted-foreground">
                Use este campo para vincular o piquete ou pastagem à área física da fazenda. Em propriedades pecuárias, esta área pode representar um pasto, setor, retiro, curral ou zona de manejo.
              </p>
            </div>

            <FormField label="Área (ha)" required>
              <Input
                required
                type="number"
                min="0.1"
                step="0.1"
                className={INPUT_CLASSNAME}
                placeholder="Ex: 15.5"
                value={form.area_ha}
                onChange={(event) => setForm((current) => ({ ...current, area_ha: event.target.value }))}
              />
            </FormField>

            <FormField label="Capacidade suporte (UA)">
              <Input
                type="number"
                min="0"
                step="0.1"
                className={INPUT_CLASSNAME}
                placeholder="Ex: 30"
                value={form.capacidade_suporte_ua}
                onChange={(event) =>
                  setForm((current) => ({ ...current, capacidade_suporte_ua: event.target.value }))
                }
              />
            </FormField>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
              disabled={mutation.isPending}
            >
              Cancelar
            </Button>
            <Button type="submit" size="sm" disabled={mutation.isPending}>
              {mutation.isPending ? <Loader2 className="size-4 animate-spin" /> : <Plus className="size-4" />}
              {mutation.isPending ? "Salvando..." : "Criar piquete"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ResumoCard({
  title,
  value,
  description,
  icon: Icon,
  tone = "default",
}: {
  title: string;
  value: string | number;
  description: string;
  icon: typeof MapPin;
  tone?: "default" | "success" | "warning";
}) {
  return (
    <Card className="rounded-sm shadow-sm">
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{title}</div>
            <div className="text-2xl font-semibold leading-none">{value}</div>
            <div className="text-xs text-muted-foreground">{description}</div>
          </div>
          <div
            className={cn(
              "flex size-10 items-center justify-center rounded-sm border",
              tone === "success" && "border-emerald-200 bg-emerald-50 text-emerald-700",
              tone === "warning" && "border-amber-200 bg-amber-50 text-amber-700",
              tone === "default" && "border-primary/20 bg-primary/5 text-primary"
            )}
          >
            <Icon className="size-4" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function PiqueteSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: 6 }).map((_, index) => (
        <Card key={index} className="rounded-sm shadow-sm">
          <CardContent className="space-y-4 p-5">
            <div className="flex items-start justify-between">
              <Skeleton className="size-10 rounded-sm" />
              <Skeleton className="h-6 w-16 rounded-sm" />
            </div>
            <div className="space-y-2">
              <Skeleton className="h-5 w-2/3 rounded-sm" />
              <Skeleton className="h-4 w-1/2 rounded-sm" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Skeleton className="h-16 rounded-sm" />
              <Skeleton className="h-16 rounded-sm" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: value % 1 === 0 ? 0 : 1,
    maximumFractionDigits: 1,
  }).format(value);
}

export function PiquetesClient({
  initialData = [],
  initialAreas = [],
  initialActiveFazendaId,
}: {
  initialData?: PiqueteArea[];
  initialAreas?: AreaRuralOption[];
  initialActiveFazendaId?: string;
}) {
  const { activeFazendaId } = useAppStore();
  const router = useRouter();
  const [showDialog, setShowDialog] = useState(false);

  const { data: areas = [] } = useQuery<AreaRuralOption[]>({
    queryKey: ["areas-rurais", activeFazendaId],
    queryFn: () =>
      apiFetch<AreaRuralOption[]>(`/cadastros/areas-rurais/?unidade_produtiva_id=${activeFazendaId}`),
    enabled: Boolean(activeFazendaId),
    initialData: activeFazendaId === initialActiveFazendaId ? initialAreas : undefined,
  });

  const { data: piquetes = [], isLoading } = useQuery<PiqueteArea[]>({
    queryKey: ["piquetes", activeFazendaId],
    queryFn: () => apiFetch<PiqueteArea[]>(`/cadastros/areas-rurais/?tipo=PIQUETE&unidade_produtiva_id=${activeFazendaId}`),
    enabled: Boolean(activeFazendaId),
    initialData: activeFazendaId === initialActiveFazendaId ? initialData : undefined,
  });

  const parentOptions = useMemo(
    () => areas.filter((item) => item.tipo === "AREA_OPERACIONAL"),
    [areas]
  );

  const resumo = useMemo(() => {
    const ativos = piquetes.filter((item) => item.ativo);
    const areaTotal = ativos.reduce((sum, item) => sum + Number(item.area_hectares || 0), 0);
    const capacidadeTotal = ativos.reduce(
      (sum, item) => sum + Number(item.dados_extras?.capacidade_suporte_ua || 0),
      0
    );

    return {
      total: piquetes.length,
      ativos: ativos.length,
      areaTotal,
      capacidadeTotal,
    };
  }, [piquetes]);

  const columns = useMemo<ColumnDef<PiqueteArea>[]>(() => [
    {
      id: "nome",
      header: "Nome",
      accessorKey: "nome",
      cell: (value) => (
        <div className="flex items-center gap-3">
          <div className="size-8 rounded-sm bg-emerald-50 text-emerald-700 flex items-center justify-center shrink-0 ring-1 ring-emerald-200">
            <MapPin className="size-4" />
          </div>
          <span className="font-medium">{value as string}</span>
        </div>
      ),
    },
    {
      id: "area_hectares",
      header: "Área (ha)",
      accessorKey: "area_hectares",
      cell: (value) => (value ? `${formatNumber(Number(value))} ha` : "—"),
    },
    {
      id: "capacidade",
      header: "Capacidade (UA)",
      accessorFn: (row) => row.dados_extras?.capacidade_suporte_ua,
      cell: (value) => (value ? `${formatNumber(Number(value))} UA` : "—"),
    },
    {
      id: "ativo",
      header: "Status",
      accessorKey: "ativo",
      cell: (value) => (
        <Badge
          variant="outline"
          className={cn(
            value
              ? "border-emerald-200 bg-emerald-50 text-emerald-700 rounded-sm"
              : "border-rose-200 bg-rose-50 text-rose-700 rounded-sm"
          )}
        >
          {value ? "Ativo" : "Inativo"}
        </Badge>
      ),
    },
    {
      id: "acoes",
      header: "",
      exportable: false,
      sortable: false,
      filterable: false,
      cell: () => (
          <div className="flex items-center gap-0 justify-end">
          </div>
      )
    }
  ], []);

  const hasAreaOperacional = parentOptions.length > 0;

  const handleOpenDialog = () => {
    if (!activeFazendaId) {
      toast.error("Selecione uma fazenda para cadastrar piquetes.");
      return;
    }
    if (!hasAreaOperacional) {
      toast.error(FRIENDLY_AREA_MESSAGE);
      return;
    }
    setShowDialog(true);
  };

  const estruturaHref = activeFazendaId
    ? `/dashboard/settings/propriedades/${activeFazendaId}/estrutura`
    : undefined;

  const handleCadastrarAreaOperacional = () => {
    if (estruturaHref) {
      router.push(estruturaHref);
    }
  };

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Piquetes & Pastagens"
        description="Gestão das subdivisões de pastejo e da base física da pecuária."
        icon={<MapPin className="text-primary" size={22} />}
        breadcrumbs={[
          { label: "Pecuária", href: "/dashboard/pecuaria" },
          { label: "Piquetes" },
        ]}
        actions={
          activeFazendaId ? (
            hasAreaOperacional ? (
              <Button size="sm" variant="outline" className="rounded-sm" onClick={handleOpenDialog}>
                <Plus className="size-3.5 mr-1.5" />
                Novo piquete
              </Button>
            ) : (
              <Button size="sm" variant="outline" className="rounded-sm" onClick={handleCadastrarAreaOperacional} disabled={!estruturaHref}>
                <Plus className="size-3.5 mr-1.5" />
                Cadastrar Área Operacional
              </Button>
            )
          ) : null
        }
      />

      {!activeFazendaId ? (
        <Card className="rounded-sm shadow-sm">
          <CardContent className="p-6">
            <EmptyState
              icon={<MapPin />}
              title="Selecione uma fazenda para visualizar os piquetes"
              description="A listagem e o cadastro dependem do contexto da unidade produtiva ativa."
            />
          </CardContent>
        </Card>
      ) : null}

      {activeFazendaId ? (
        <>
          {parentOptions.length === 0 ? (
            <Card className="rounded-sm shadow-sm">
              <CardContent className="p-6">
                <EmptyState
                  icon={<MapPin />}
                  title="Antes de cadastrar um piquete ou pastagem, cadastre uma Área Operacional da fazenda."
                  description="Na Pecuária, a Área Operacional representa a base física onde ficam pastos, piquetes, currais ou zonas de manejo."
                  action={
                    estruturaHref
                      ? {
                          label: "Cadastrar Área Operacional",
                          onClick: handleCadastrarAreaOperacional,
                        }
                      : undefined
                  }
                />
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="grid gap-4 md:grid-cols-3">
                <ResumoCard
                  title="Piquetes ativos"
                  value={resumo.ativos}
                  description={`${resumo.total} cadastrado(s) no total`}
                  icon={Layers}
                />
                <ResumoCard
                  title="Área total"
                  value={`${formatNumber(resumo.areaTotal)} ha`}
                  description="Soma das áreas ativas"
                  icon={Maximize2}
                  tone="success"
                />
                <ResumoCard
                  title="Capacidade suporte"
                  value={formatNumber(resumo.capacidadeTotal)}
                  description="UA estimada em piquetes ativos"
                  icon={Scale}
                  tone="warning"
                />
              </div>

              <Card className="shadow-sm">
                <CardHeader className="border-b">
                  <CardTitle>Lista de Piquetes</CardTitle>
                  <CardDescription>
                    Consulte os piquetes e pastagens cadastrados nesta Área Operacional.
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-4">
                  <DataTable
                    columns={columns}
                    data={piquetes}
                    isLoading={isLoading}
                    searchable={true}
                    searchPlaceholder="Buscar piquete..."
                    exportable={true}
                    exportFileName="piquetes_export"
                    emptyMessage="Nenhum piquete cadastrado ou encontrado."
                  />
                </CardContent>
              </Card>
            </>
          )}
        </>
      ) : null}

      {activeFazendaId ? (
        <NovoPiqueteDialog
          fazendaId={activeFazendaId}
          parentOptions={parentOptions}
          open={showDialog}
          onOpenChange={setShowDialog}
        />
      ) : null}
    </div>
  );
}
