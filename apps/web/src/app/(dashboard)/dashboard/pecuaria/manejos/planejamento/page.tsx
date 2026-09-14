"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
  CalendarDays,
  CheckSquare,
  CircleSlash2,
  ClipboardList,
  Eye,
  Loader2,
  MapPin,
  Package,
  Plus,
  Scale,
  Syringe,
} from "lucide-react";
import { toast } from "sonner";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";

const EMPTY_VALUE = "__empty__";
const TIPO_PESAGEM = "PESAGEM" as const;
const TIPO_VACINACAO = "VACINACAO" as const;
const TIPOS_MANEJO = [TIPO_PESAGEM, TIPO_VACINACAO] as const;
const UNIDADES_MEDIDA_VACINA = ["ML", "UN", "DOSE"] as const;
const VIAS_APLICACAO = ["SUBCUTANEA", "INTRAMUSCULAR", "INTRAVENOSA", "ORAL", "TOPICA"] as const;

type TipoManejo = (typeof TIPOS_MANEJO)[number];

interface LoteOption {
  id: string;
  identificacao: string;
  categoria?: string | null;
  raca?: string | null;
  ativo?: boolean;
  area_id?: string | null;
  piquete_id?: string | null;
}

interface AreaOption {
  id: string;
  nome: string;
  tipo: string;
  ativo: boolean;
}

interface AnimalOption {
  id: string;
  numero_brinco?: string | null;
  nome?: string | null;
  status: string;
  lote_id?: string | null;
}

interface AnimalListResponse {
  items: AnimalOption[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

interface PessoaOption {
  id: string;
  nome_exibicao: string;
  ativo: boolean;
}

interface ProdutoOption {
  id: string;
  nome: string;
  tipo: string;
  unidade_medida: string;
  ativo: boolean;
}

interface ManejoPlanejamentoAnimalItem {
  animal_id: string;
  numero_brinco?: string | null;
  peso_kg?: number | null;
  observacao?: string | null;
}

interface ManejoPlanejamentoLoteResumo {
  id: string;
  identificacao: string;
}

interface ManejoPlanejamentoOperadorResumo {
  id: string;
  nome_exibicao: string;
}

interface ManejoPlanejamentoResponse {
  tarefa_campo_id: string;
  tipo: TipoManejo;
  lote: ManejoPlanejamentoLoteResumo;
  area_id?: string | null;
  operador?: ManejoPlanejamentoOperadorResumo | null;
  status: string;
  origem: string;
  data_programada: string;
  quantidade_animais: number;
  observacoes?: string | null;
  animais: ManejoPlanejamentoAnimalItem[];
}

interface ManejoPlanejamentoListResponse {
  items: ManejoPlanejamentoResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

interface ManejoPlanejamentoFormPayload {
  tipo: TipoManejo;
  lote_id: string;
  animais_ids: string[];
  data_programada: string;
  operador_id?: string;
  observacoes?: string;
  produto_id?: string;
  dose?: number;
  unidade_medida?: string;
  via_aplicacao?: string;
}

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  const parsed = new Date(`${value}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? value : format(parsed, "dd/MM/yyyy", { locale: ptBR });
}

function statusBadgeClass(status: string) {
  switch (status) {
    case "PENDENTE":
      return "border-amber-200 bg-amber-50 text-amber-700";
    case "EM_EXECUCAO":
      return "border-blue-200 bg-blue-50 text-blue-700";
    case "CONCLUIDA":
      return "border-emerald-200 bg-emerald-50 text-emerald-700";
    case "CANCELADA":
      return "border-rose-200 bg-rose-50 text-rose-700";
    default:
      return "border-border-subtle bg-muted text-muted-foreground";
  }
}

function tipoBadgeClass(tipo: TipoManejo) {
  return tipo === TIPO_VACINACAO
    ? "border-rose-200 bg-rose-50 text-rose-700"
    : "border-sky-200 bg-sky-50 text-sky-700";
}

function tipoLabel(tipo: TipoManejo) {
  return tipo === TIPO_VACINACAO ? "VACINAÇÃO" : "PESAGEM";
}

export default function PlanejamentoManejosPage() {
  const queryClient = useQueryClient();
  const { activeFazendaId } = useAppStore();

  const [tipoManejo, setTipoManejo] = useState<TipoManejo>(TIPO_PESAGEM);
  const [loteId, setLoteId] = useState("");
  const [selectAllAnimals, setSelectAllAnimals] = useState(true);
  const [selectedAnimalIds, setSelectedAnimalIds] = useState<string[]>([]);
  const [dataProgramada, setDataProgramada] = useState(() => new Date().toISOString().slice(0, 10));
  const [operadorId, setOperadorId] = useState("");
  const [observacoes, setObservacoes] = useState("");
  const [produtoId, setProdutoId] = useState("");
  const [dose, setDose] = useState("");
  const [unidadeMedida, setUnidadeMedida] = useState("ML");
  const [viaAplicacao, setViaAplicacao] = useState("");
  const [detail, setDetail] = useState<ManejoPlanejamentoResponse | null>(null);

  const { data: lotes = [], isLoading: lotesLoading } = useQuery<LoteOption[]>({
    queryKey: ["pecuaria", "lotes", activeFazendaId],
    queryFn: () => apiFetch<LoteOption[]>(`/pecuaria/lotes/?unidade_produtiva_id=${activeFazendaId}`),
    enabled: Boolean(activeFazendaId),
  });

  const { data: areas = [] } = useQuery<AreaOption[]>({
    queryKey: ["cadastros", "areas-rurais", activeFazendaId],
    queryFn: () => apiFetch<AreaOption[]>(`/cadastros/areas-rurais/?unidade_produtiva_id=${activeFazendaId}`),
    enabled: Boolean(activeFazendaId),
  });

  const { data: operadores = [] } = useQuery<PessoaOption[]>({
    queryKey: ["cadastros", "pessoas", "operadores"],
    queryFn: () => apiFetch<PessoaOption[]>("/cadastros/pessoas?ativo=true"),
  });

  const { data: produtos = [] } = useQuery<ProdutoOption[]>({
    queryKey: ["cadastros", "produtos", "vacinas", activeFazendaId],
    queryFn: () => apiFetch<ProdutoOption[]>("/cadastros/produtos?ativo=true&tipo=VACINA"),
    enabled: Boolean(activeFazendaId),
  });

  const animaisQuery = useQuery<AnimalListResponse>({
    queryKey: ["pecuaria", "animais", activeFazendaId, loteId],
    queryFn: () =>
      apiFetch<AnimalListResponse>(
        `/pecuaria/animais/?unidade_produtiva_id=${activeFazendaId}&lote_id=${loteId}&page=1&page_size=200`
      ),
    enabled: Boolean(activeFazendaId && loteId),
  });

  const planejadosQuery = useQuery<ManejoPlanejamentoListResponse>({
    queryKey: ["pecuaria", "manejos-planejados", activeFazendaId],
    queryFn: () =>
      apiFetch<ManejoPlanejamentoListResponse>("/pecuaria/manejos/planejados", {
        params: {
          unidade_produtiva_id: activeFazendaId ?? undefined,
          page: 1,
          page_size: 10,
        },
      }),
    enabled: Boolean(activeFazendaId),
  });

  const lotesAtivos = useMemo(() => lotes.filter((item) => item.ativo !== false), [lotes]);
  const loteSelecionado = useMemo(
    () => lotesAtivos.find((item) => item.id === loteId) ?? null,
    [lotesAtivos, loteId]
  );
  const areaSelecionadaId = loteSelecionado?.area_id ?? loteSelecionado?.piquete_id ?? null;
  const areaSelecionada = useMemo(
    () => areas.find((item) => item.id === areaSelecionadaId) ?? null,
    [areas, areaSelecionadaId]
  );

  const animaisAtivos = useMemo(
    () => animaisQuery.data?.items.filter((item) => item.status === "ATIVO") ?? [],
    [animaisQuery.data]
  );
  const manualSelectedAnimalIds = useMemo(
    () => selectedAnimalIds.filter((animalId) => animaisAtivos.some((animal) => animal.id === animalId)),
    [animaisAtivos, selectedAnimalIds]
  );

  const produtoSelecionado = useMemo(
    () => produtos.find((produto) => produto.id === produtoId) ?? null,
    [produtoId, produtos]
  );

  const planejamentoMutation = useMutation({
    mutationFn: (payload: ManejoPlanejamentoFormPayload) =>
      apiFetch<ManejoPlanejamentoResponse>("/pecuaria/manejos/planejar", {
        method: "POST",
        body: payload,
      }),
    onSuccess: async () => {
      toast.success("Tarefa de campo gerada com sucesso.");
      setObservacoes("");
      setOperadorId("");
      setSelectAllAnimals(true);
      setSelectedAnimalIds([]);
      setProdutoId("");
      setDose("");
      setUnidadeMedida("ML");
      setViaAplicacao("");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["pecuaria", "manejos-planejados", activeFazendaId] }),
        queryClient.invalidateQueries({ queryKey: ["pecuaria", "animais", activeFazendaId, loteId] }),
      ]);
    },
    onError: (error: Error) => {
      toast.error(error.message || "Erro ao gerar tarefa de campo.");
    },
  });

  const handleTipoChange = (value: TipoManejo) => {
    setTipoManejo(value);
    if (value === TIPO_PESAGEM) {
      setProdutoId("");
      setDose("");
      setUnidadeMedida("ML");
      setViaAplicacao("");
    }
  };

  const handleLoteChange = (value: string) => {
    setLoteId(value);
    setSelectAllAnimals(true);
    setSelectedAnimalIds([]);
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();

    if (!activeFazendaId) {
      toast.error("Selecione uma fazenda para planejar o manejo.");
      return;
    }
    if (!loteId) {
      toast.error("Selecione um lote.");
      return;
    }
    if (!dataProgramada) {
      toast.error("Informe a data programada.");
      return;
    }
    if (!selectAllAnimals && manualSelectedAnimalIds.length === 0) {
      toast.error("Selecione ao menos um animal ou marque a opção de selecionar todos.");
      return;
    }
    if (tipoManejo === TIPO_VACINACAO) {
      if (!produtoId) {
        toast.error("Selecione um produto para vacinação.");
        return;
      }
      const doseNumeric = Number(dose);
      if (!doseNumeric || doseNumeric <= 0) {
        toast.error("Informe uma dose válida maior que zero.");
        return;
      }
      if (!unidadeMedida) {
        toast.error("Selecione a unidade de medida.");
        return;
      }
    }

    const payload: ManejoPlanejamentoFormPayload = {
      tipo: tipoManejo,
      lote_id: loteId,
      animais_ids: selectAllAnimals ? [] : manualSelectedAnimalIds,
      data_programada: dataProgramada,
      observacoes: observacoes.trim() || undefined,
      operador_id: operadorId || undefined,
      ...(tipoManejo === TIPO_VACINACAO
        ? {
            produto_id: produtoId,
            dose: Number(dose),
            unidade_medida: unidadeMedida,
            via_aplicacao: viaAplicacao || undefined,
          }
        : {}),
    };

    planejamentoMutation.mutate(payload);
  };

  const quantidadeSelecionada = selectAllAnimals ? animaisAtivos.length : manualSelectedAnimalIds.length;
  const podeGerar =
    Boolean(activeFazendaId && loteId && dataProgramada && animaisAtivos.length > 0) &&
    (tipoManejo === TIPO_PESAGEM ||
      (tipoManejo === TIPO_VACINACAO &&
        produtoId &&
        Number(dose) > 0 &&
        unidadeMedida &&
        (!selectAllAnimals || manualSelectedAnimalIds.length > 0)));

  return (
    <div className="space-y-6 p-6 animate-in fade-in duration-500">
      <PageHeader
        title="Planejamento de Manejos"
        description="Planeje pesagens e vacinações no Backoffice e gere tarefas para execução no Campo."
        icon={<Scale className="text-primary" size={22} />}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Pecuária", href: "/dashboard/pecuaria" },
          { label: "Planejamento de Manejos" },
        ]}
      />

      {!activeFazendaId ? (
        <Card className="rounded-sm shadow-sm">
          <CardContent className="p-6">
            <EmptyState
              icon={<MapPin />}
              title="Selecione uma fazenda para planejar manejos"
              description="O planejamento depende do contexto da unidade produtiva ativa."
            />
          </CardContent>
        </Card>
      ) : null}

      {activeFazendaId ? (
        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <Card className="rounded-sm shadow-sm">
            <CardHeader className="space-y-1 border-b border-border-subtle">
              <CardTitle className="text-base">Novo planejamento</CardTitle>
              <CardDescription>Selecione o lote, os animais e complete os campos conforme o manejo.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6 pt-6">
              <form className="space-y-6" onSubmit={handleSubmit}>
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="space-y-1.5">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      Tipo de manejo
                    </div>
                    <Select value={tipoManejo} onValueChange={(value) => handleTipoChange(value as TipoManejo)}>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecione o tipo" />
                      </SelectTrigger>
                      <SelectContent>
                        {TIPOS_MANEJO.map((tipo) => (
                          <SelectItem key={tipo} value={tipo}>
                            {tipoLabel(tipo)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </label>

                  <label className="space-y-1.5">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      Lote <span className="text-destructive">*</span>
                    </div>
                    <Select
                      value={loteId}
                      onValueChange={handleLoteChange}
                      disabled={lotesLoading || lotesAtivos.length === 0}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Selecione um lote" />
                      </SelectTrigger>
                      <SelectContent>
                        {lotesAtivos.map((item) => (
                          <SelectItem key={item.id} value={item.id}>
                            {item.identificacao}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </label>
                </div>

                {tipoManejo === TIPO_VACINACAO ? (
                  <div className="grid gap-4 md:grid-cols-2">
                    <label className="space-y-1.5">
                      <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                        Produto <span className="text-destructive">*</span>
                      </div>
                      <Select value={produtoId} onValueChange={setProdutoId} disabled={produtos.length === 0}>
                        <SelectTrigger>
                          <SelectValue placeholder="Selecione o produto" />
                        </SelectTrigger>
                        <SelectContent>
                          {produtos.map((produto) => (
                            <SelectItem key={produto.id} value={produto.id}>
                              {produto.nome}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      {produtos.length === 0 ? (
                        <p className="text-xs text-muted-foreground">
                          Nenhum produto de vacina disponível no catálogo da fazenda.
                        </p>
                      ) : null}
                    </label>

                    <label className="space-y-1.5">
                      <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                        Dose <span className="text-destructive">*</span>
                      </div>
                      <Input
                        type="number"
                        min="0"
                        step="0.01"
                        className="h-8"
                        placeholder="Ex.: 2,00"
                        value={dose}
                        onChange={(event) => setDose(event.target.value)}
                      />
                    </label>

                    <label className="space-y-1.5">
                      <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                        Unidade de medida <span className="text-destructive">*</span>
                      </div>
                      <Select value={unidadeMedida} onValueChange={setUnidadeMedida}>
                        <SelectTrigger>
                          <SelectValue placeholder="Selecione a unidade" />
                        </SelectTrigger>
                        <SelectContent>
                          {UNIDADES_MEDIDA_VACINA.map((unidade) => (
                            <SelectItem key={unidade} value={unidade}>
                              {unidade}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </label>

                    <label className="space-y-1.5">
                      <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                        Via de aplicação
                      </div>
                      <Select value={viaAplicacao || EMPTY_VALUE} onValueChange={(value) => setViaAplicacao(value === EMPTY_VALUE ? "" : value)}>
                        <SelectTrigger>
                          <SelectValue placeholder="Opcional" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value={EMPTY_VALUE}>Sem via definida</SelectItem>
                          {VIAS_APLICACAO.map((via) => (
                            <SelectItem key={via} value={via}>
                              {via}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </label>
                  </div>
                ) : null}

                {loteSelecionado ? (
                  <div className="grid gap-3 md:grid-cols-3">
                    <div className="rounded-sm border border-border-subtle bg-muted/20 p-3">
                      <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Lote</div>
                      <div className="mt-1 text-sm font-semibold">{loteSelecionado.identificacao}</div>
                    </div>
                    <div className="rounded-sm border border-border-subtle bg-muted/20 p-3">
                      <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Área/Piquete</div>
                      <div className="mt-1 text-sm font-semibold">
                        {areaSelecionada?.nome ?? "Sem área vinculada"}
                      </div>
                      {areaSelecionada ? (
                        <div className="mt-2">
                          <Badge variant="outline" className="text-[10px]">
                            {areaSelecionada.tipo}
                          </Badge>
                        </div>
                      ) : null}
                    </div>
                    <div className="rounded-sm border border-border-subtle bg-muted/20 p-3">
                      <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Animais ativos</div>
                      <div className="mt-1 text-sm font-semibold">{animaisAtivos.length}</div>
                    </div>
                  </div>
                ) : null}

                <div className="grid gap-4 md:grid-cols-2">
                  <label className="space-y-1.5">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      Data programada <span className="text-destructive">*</span>
                    </div>
                    <div className="relative">
                      <CalendarDays className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        type="date"
                        className="h-8 pl-9"
                        value={dataProgramada}
                        onChange={(event) => setDataProgramada(event.target.value)}
                      />
                    </div>
                  </label>

                  <label className="space-y-1.5">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Operador</div>
                    <Select value={operadorId || EMPTY_VALUE} onValueChange={(value) => setOperadorId(value === EMPTY_VALUE ? "" : value)}>
                      <SelectTrigger>
                        <SelectValue placeholder="Sem operador" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value={EMPTY_VALUE}>Sem operador</SelectItem>
                        {operadores.map((item) => (
                          <SelectItem key={item.id} value={item.id}>
                            {item.nome_exibicao}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </label>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center gap-3 rounded-sm border border-border-subtle bg-muted/20 px-3 py-2">
                    <Checkbox
                      checked={selectAllAnimals}
                      onCheckedChange={(checked) => {
                        const nextChecked = Boolean(checked);
                        setSelectAllAnimals(nextChecked);
                        setSelectedAnimalIds([]);
                      }}
                    />
                    <div className="min-w-0">
                      <div className="text-sm font-medium">Selecionar todos os animais ativos</div>
                      <div className="text-xs text-muted-foreground">
                        {selectAllAnimals
                          ? "O sistema enviará todos os animais ativos do lote para o planejamento."
                          : "Desmarque para selecionar manualmente apenas alguns animais."}
                      </div>
                    </div>
                  </div>

                  {!selectAllAnimals ? (
                    <div className="rounded-sm border border-border-subtle">
                      <div className="flex items-center justify-between border-b border-border-subtle px-4 py-3">
                        <div>
                          <div className="text-sm font-semibold">Seleção manual</div>
                          <div className="text-xs text-muted-foreground">
                            {manualSelectedAnimalIds.length} selecionado(s) de {animaisAtivos.length}
                          </div>
                        </div>
                        <Badge variant="outline">{quantidadeSelecionada} selecionado(s)</Badge>
                      </div>
                      <div className="max-h-72 overflow-auto">
                        {animaisAtivos.length === 0 ? (
                          <EmptyState
                            icon={<CircleSlash2 />}
                            title="Nenhum animal ativo disponível"
                            description="Somente animais ativos do lote podem entrar no planejamento."
                            className="py-10"
                          />
                        ) : (
                          <div className="divide-y divide-border-subtle">
                            {animaisAtivos.map((animal) => {
                              const checked = manualSelectedAnimalIds.includes(animal.id);
                              return (
                                <label
                                  key={animal.id}
                                  className="flex cursor-pointer items-center gap-3 px-4 py-3 hover:bg-muted/30"
                                >
                                  <Checkbox
                                    checked={checked}
                                    onCheckedChange={(nextChecked) => {
                                      setSelectedAnimalIds((current) =>
                                        nextChecked
                                          ? current.includes(animal.id)
                                            ? current
                                            : [...current, animal.id]
                                          : current.filter((item) => item !== animal.id)
                                      );
                                    }}
                                  />
                                  <div className="min-w-0 flex-1">
                                    <div className="text-sm font-medium">
                                      {animal.numero_brinco || animal.nome || animal.id.slice(0, 8)}
                                    </div>
                                    <div className="text-xs text-muted-foreground">
                                      ID {animal.id.slice(0, 8)} • {animal.status}
                                    </div>
                                  </div>
                                </label>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    </div>
                  ) : null}
                </div>

                <label className="space-y-1.5">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Observações</div>
                  <Textarea
                    rows={3}
                    placeholder={
                      tipoManejo === TIPO_VACINACAO
                        ? "Vacinação contra clostridiose, lote com reforço..."
                        : "Pesagem de desmame, preparo para venda, acompanhamento sanitário..."
                    }
                    value={observacoes}
                    onChange={(event) => setObservacoes(event.target.value)}
                  />
                </label>

                <div className="flex items-center justify-between gap-3 rounded-sm border border-dashed border-border-subtle bg-muted/10 px-4 py-3">
                  <div className="space-y-0.5">
                    <div className="text-sm font-medium">Resumo do planejamento</div>
                    <div className="text-xs text-muted-foreground">
                      {quantidadeSelecionada} animal(is) • {formatDate(dataProgramada)} • {loteSelecionado?.identificacao || "Sem lote"}
                    </div>
                    {tipoManejo === TIPO_VACINACAO ? (
                      <div className="text-xs text-muted-foreground">
                        {produtoSelecionado?.nome ?? "Sem produto"} • {dose || "0"} {unidadeMedida || "—"}
                      </div>
                    ) : null}
                  </div>
                  <Button type="submit" size="sm" disabled={planejamentoMutation.isPending || !podeGerar}>
                    {planejamentoMutation.isPending ? (
                      <Loader2 className="mr-2 size-4 animate-spin" />
                    ) : (
                      <Plus className="mr-2 size-4" />
                    )}
                    Gerar tarefa de campo
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          <div className="space-y-6">
            <Card className="rounded-sm shadow-sm">
              <CardHeader className="space-y-1 border-b border-border-subtle">
                <CardTitle className="text-base">Indicadores do planejamento</CardTitle>
                <CardDescription>Resumo rápido da seleção atual.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-3 pt-6 md:grid-cols-2 xl:grid-cols-1">
                <div className="rounded-sm border border-border-subtle bg-muted/20 p-4">
                  <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                    <CheckSquare className="size-3.5" /> Animais selecionados
                  </div>
                  <div className="mt-2 text-2xl font-semibold">{quantidadeSelecionada}</div>
                  <div className="text-xs text-muted-foreground">
                    {selectAllAnimals ? "Todos os animais ativos" : "Seleção manual"}
                  </div>
                </div>
                <div className="rounded-sm border border-border-subtle bg-muted/20 p-4">
                  <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                    {tipoManejo === TIPO_VACINACAO ? <Syringe className="size-3.5" /> : <Scale className="size-3.5" />} Tipo
                  </div>
                  <div className="mt-2 text-2xl font-semibold">{tipoLabel(tipoManejo)}</div>
                  <div className="text-xs text-muted-foreground">
                    {tipoManejo === TIPO_VACINACAO ? "Campos de vacinação ativos" : "Campos de pesagem ativos"}
                  </div>
                </div>
                <div className="rounded-sm border border-border-subtle bg-muted/20 p-4">
                  <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                    <MapPin className="size-3.5" /> Área principal
                  </div>
                  <div className="mt-2 text-2xl font-semibold">{areaSelecionada?.nome || "—"}</div>
                  <div className="text-xs text-muted-foreground">
                    {areaSelecionada ? areaSelecionada.tipo : "O lote ainda não possui área vinculada"}
                  </div>
                </div>
                {tipoManejo === TIPO_VACINACAO ? (
                  <div className="rounded-sm border border-border-subtle bg-muted/20 p-4">
                    <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      <Package className="size-3.5" /> Produto
                    </div>
                    <div className="mt-2 text-2xl font-semibold">{produtoSelecionado?.nome || "—"}</div>
                    <div className="text-xs text-muted-foreground">
                      {produtoSelecionado ? produtoSelecionado.unidade_medida : "Selecione uma vacina"}
                    </div>
                  </div>
                ) : null}
              </CardContent>
            </Card>

            <Card className="rounded-sm shadow-sm">
              <CardHeader className="space-y-1 border-b border-border-subtle">
                <CardTitle className="text-base">Planejamentos recentes</CardTitle>
                <CardDescription>Últimas tarefas programadas do produtor na fazenda ativa.</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                {planejadosQuery.isLoading ? (
                  <div className="p-6 text-center text-sm text-muted-foreground">Carregando planejamentos...</div>
                ) : (planejadosQuery.data?.items ?? []).length === 0 ? (
                  <div className="p-6">
                    <EmptyState
                      icon={<ClipboardList />}
                      title="Nenhum planejamento encontrado"
                      description="A primeira tarefa programada aparecerá aqui após a criação."
                    />
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Data</TableHead>
                        <TableHead>Tipo</TableHead>
                        <TableHead>Lote</TableHead>
                        <TableHead>Área/Piquete</TableHead>
                        <TableHead>Animais</TableHead>
                        <TableHead>Operador</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Origem</TableHead>
                        <TableHead className="text-right">Ações</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {(planejadosQuery.data?.items ?? []).map((item) => {
                        const area = areas.find((entry) => entry.id === item.area_id);
                        return (
                          <TableRow key={item.tarefa_campo_id}>
                            <TableCell>{formatDate(item.data_programada)}</TableCell>
                            <TableCell>
                              <Badge variant="outline" className={tipoBadgeClass(item.tipo)}>
                                {tipoLabel(item.tipo)}
                              </Badge>
                            </TableCell>
                            <TableCell>{item.lote.identificacao}</TableCell>
                            <TableCell>{area?.nome || "—"}</TableCell>
                            <TableCell>{item.quantidade_animais}</TableCell>
                            <TableCell>{item.operador?.nome_exibicao || "—"}</TableCell>
                            <TableCell>
                              <Badge variant="outline" className={statusBadgeClass(item.status)}>
                                {item.status}
                              </Badge>
                            </TableCell>
                            <TableCell>{item.origem}</TableCell>
                            <TableCell className="text-right">
                              <Button variant="ghost" size="sm" onClick={() => setDetail(item)}>
                                <Eye className="mr-2 size-4" />
                                Ver detalhes
                              </Button>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      ) : null}

      <Dialog open={Boolean(detail)} onOpenChange={(open) => !open && setDetail(null)}>
        <DialogContent className="max-w-3xl rounded-sm border border-border-subtle bg-surface shadow-2xl">
          <DialogHeader className="border-b border-border-subtle px-6 py-5">
            <DialogTitle className="text-base font-bold">Detalhes do planejamento</DialogTitle>
          </DialogHeader>
          {detail ? (
            <div className="space-y-5 px-6 py-5">
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-sm border border-border-subtle bg-muted/20 p-4">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Tipo</div>
                  <div className="mt-2">
                    <Badge variant="outline" className={tipoBadgeClass(detail.tipo)}>
                      {tipoLabel(detail.tipo)}
                    </Badge>
                  </div>
                </div>
                <div className="rounded-sm border border-border-subtle bg-muted/20 p-4">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Lote</div>
                  <div className="mt-1 text-sm font-semibold">{detail.lote.identificacao}</div>
                </div>
                <div className="rounded-sm border border-border-subtle bg-muted/20 p-4">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Área/Piquete</div>
                  <div className="mt-1 text-sm font-semibold">
                    {areas.find((entry) => entry.id === detail.area_id)?.nome || "—"}
                  </div>
                </div>
                <div className="rounded-sm border border-border-subtle bg-muted/20 p-4">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Data programada</div>
                  <div className="mt-1 text-sm font-semibold">{formatDate(detail.data_programada)}</div>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <div className="rounded-sm border border-border-subtle bg-muted/20 p-4">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Status</div>
                  <div className="mt-2">
                    <Badge variant="outline" className={statusBadgeClass(detail.status)}>
                      {detail.status}
                    </Badge>
                  </div>
                </div>
                <div className="rounded-sm border border-border-subtle bg-muted/20 p-4">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Origem</div>
                  <div className="mt-1 text-sm font-semibold">{detail.origem}</div>
                </div>
                <div className="rounded-sm border border-border-subtle bg-muted/20 p-4">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Animais</div>
                  <div className="mt-1 text-sm font-semibold">{detail.quantidade_animais}</div>
                </div>
              </div>

              <div className="space-y-3">
                <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Operador</div>
                <div className="rounded-sm border border-border-subtle bg-muted/20 p-4 text-sm">
                  {detail.operador?.nome_exibicao || "—"}
                </div>
              </div>

              <div className="space-y-3">
                <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Observações</div>
                <div className="rounded-sm border border-border-subtle bg-muted/20 p-4 text-sm">
                  {detail.observacoes || "—"}
                </div>
              </div>

              <Separator />

              <div className="space-y-3">
                <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Animais planejados</div>
                <div className="rounded-sm border border-border-subtle">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Brinco</TableHead>
                        <TableHead>Peso</TableHead>
                        <TableHead>Observação</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {detail.animais.map((animal) => (
                        <TableRow key={animal.animal_id}>
                          <TableCell>{animal.numero_brinco || animal.animal_id.slice(0, 8)}</TableCell>
                          <TableCell>{animal.peso_kg ?? "null"}</TableCell>
                          <TableCell>{animal.observacao || "—"}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}
