"use client";

import React, { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  FlaskConical,
  Globe,
  PauseCircle,
  Pencil,
  Play,
  Plus,
  ShieldAlert,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { apiFetch } from "@/lib/api";

import type {
  AutoPublishPolicyType,
  CollectorDryRunResponse,
  CollectorRunSummary,
  CollectorSourceItem,
  DomainType,
  EstrategiaColetaType,
  TipoLicencaType,
} from "./types";

interface CollectorSourcesTabProps {
  sources: CollectorSourceItem[];
  isLoading: boolean;
  canUpdate: boolean;
}

interface SourceFormState {
  domain: DomainType;
  slug: string;
  nome: string;
  sigla: string;
  tipo_licenca: TipoLicencaType;
  termo_autorizacao_ref: string;
  atribuicao_obrigatoria: string;
  uf_padrao: string;
  praca_padrao: string;
  dominios_whitelist: string;
  url_principal: string;
  url_indice: string;
  estrategia_coleta: EstrategiaColetaType;
  auto_publish_policy: AutoPublishPolicyType;
  max_variacao_pct: string;
  max_defasagem_dias: string;
  cron_ou_intervalo_seg: string;
  config_extrator_json: string;
  ativo: boolean;
}

const EMPTY_FORM: SourceFormState = {
  domain: "MERCADO",
  slug: "",
  nome: "",
  sigla: "",
  tipo_licenca: "PARCEIRO_AUTORIZADO",
  termo_autorizacao_ref: "",
  atribuicao_obrigatoria: "",
  uf_padrao: "MT",
  praca_padrao: "",
  dominios_whitelist: "",
  url_principal: "https://",
  url_indice: "",
  estrategia_coleta: "GENERICO_PARCEIRO",
  auto_publish_policy: "SEMPRE_REVISAO_HUMANA",
  max_variacao_pct: "12.00",
  max_defasagem_dias: "14",
  cron_ou_intervalo_seg: "86400",
  config_extrator_json: '{\n  "formato": "csv"\n}',
  ativo: true,
};

function toFormState(src: CollectorSourceItem): SourceFormState {
  return {
    domain: src.domain,
    slug: src.slug,
    nome: src.nome,
    sigla: src.sigla,
    tipo_licenca: src.tipo_licenca,
    termo_autorizacao_ref: src.termo_autorizacao_ref ?? "",
    atribuicao_obrigatoria: src.atribuicao_obrigatoria ?? "",
    uf_padrao: src.uf_padrao,
    praca_padrao: src.praca_padrao ?? "",
    dominios_whitelist: (src.dominios_whitelist ?? []).join(", "),
    url_principal: src.url_principal,
    url_indice: src.url_indice ?? "",
    estrategia_coleta: src.estrategia_coleta,
    auto_publish_policy: src.auto_publish_policy,
    max_variacao_pct: String(src.max_variacao_pct),
    max_defasagem_dias: String(src.max_defasagem_dias),
    cron_ou_intervalo_seg: String(src.cron_ou_intervalo_seg),
    config_extrator_json: JSON.stringify(src.config_extrator ?? {}, null, 2),
    ativo: src.ativo,
  };
}

export function CollectorSourcesTab({ sources, isLoading, canUpdate }: CollectorSourcesTabProps) {
  const queryClient = useQueryClient();
  const [licencaFilter, setLicencaFilter] = useState<string>("TODAS");
  const [ufFilter, setUfFilter] = useState<string>("TODAS");
  const [editingSource, setEditingSource] = useState<CollectorSourceItem | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formState, setFormState] = useState<SourceFormState>(EMPTY_FORM);
  const [dryRunResult, setDryRunResult] = useState<CollectorDryRunResponse | null>(null);

  const ufsDisponiveis = useMemo(
    () => Array.from(new Set(sources.map((s) => s.uf_padrao))).sort(),
    [sources]
  );

  const filteredSources = useMemo(() => {
    return sources.filter((s) => {
      if (licencaFilter !== "TODAS" && s.tipo_licenca !== licencaFilter) return false;
      if (ufFilter !== "TODAS" && s.uf_padrao !== ufFilter) return false;
      return true;
    });
  }, [sources, licencaFilter, ufFilter]);

  const invalidateCollectorQueries = () => {
    queryClient.invalidateQueries({ queryKey: ["backoffice-collector-sources"] });
    queryClient.invalidateQueries({ queryKey: ["backoffice-collector-runs"] });
    queryClient.invalidateQueries({ queryKey: ["backoffice-collector-staging"] });
  };

  const saveMutation = useMutation({
    mutationFn: async (state: SourceFormState) => {
      let parsedConfig: Record<string, unknown> = {};
      if (state.config_extrator_json.trim()) {
        const rawParsed: unknown = JSON.parse(state.config_extrator_json);
        if (typeof rawParsed !== "object" || rawParsed === null || Array.isArray(rawParsed)) {
          throw new Error("config_extrator precisa ser um objeto JSON válido.");
        }
        parsedConfig = rawParsed as Record<string, unknown>;
      }
      const whitelist = state.dominios_whitelist
        .split(",")
        .map((d) => d.trim())
        .filter(Boolean);

      if (editingSource) {
        return apiFetch<CollectorSourceItem>(
          `/api/v1/backoffice/agro/mercado/collector/sources/${editingSource.id}`,
          {
            method: "PUT",
            body: {
              nome: state.nome,
              sigla: state.sigla,
              tipo_licenca: state.tipo_licenca,
              termo_autorizacao_ref: state.termo_autorizacao_ref || null,
              atribuicao_obrigatoria: state.atribuicao_obrigatoria || null,
              uf_padrao: state.uf_padrao.toUpperCase(),
              praca_padrao: state.praca_padrao || null,
              dominios_whitelist: whitelist,
              url_principal: state.url_principal,
              url_indice: state.url_indice || null,
              estrategia_coleta: state.estrategia_coleta,
              config_extrator: parsedConfig,
              cron_ou_intervalo_seg: Number(state.cron_ou_intervalo_seg),
              auto_publish_policy: state.auto_publish_policy,
              max_variacao_pct: Number(state.max_variacao_pct),
              max_defasagem_dias: Number(state.max_defasagem_dias),
              ativo: state.ativo,
            },
          }
        );
      }
      return apiFetch<CollectorSourceItem>("/api/v1/backoffice/agro/mercado/collector/sources", {
        method: "POST",
        body: {
          domain: state.domain,
          slug: state.slug.trim(),
          nome: state.nome.trim(),
          sigla: state.sigla.trim(),
          tipo_licenca: state.tipo_licenca,
          termo_autorizacao_ref: state.termo_autorizacao_ref || null,
          atribuicao_obrigatoria: state.atribuicao_obrigatoria || null,
          uf_padrao: state.uf_padrao.toUpperCase(),
          praca_padrao: state.praca_padrao || null,
          dominios_whitelist: whitelist,
          url_principal: state.url_principal.trim(),
          url_indice: state.url_indice.trim() || null,
          estrategia_coleta: state.estrategia_coleta,
          config_extrator: parsedConfig,
          cron_ou_intervalo_seg: Number(state.cron_ou_intervalo_seg),
          auto_publish_policy: state.auto_publish_policy,
          max_variacao_pct: Number(state.max_variacao_pct),
          max_defasagem_dias: Number(state.max_defasagem_dias),
          ativo: state.ativo,
        },
      });
    },
    onSuccess: (item) => {
      toast.success(`Fonte '${item.sigla}' salva com sucesso.`);
      setIsModalOpen(false);
      setEditingSource(null);
      invalidateCollectorQueries();
    },
    onError: (err: Error) => {
      toast.error(`Erro ao salvar fonte: ${err.message}`);
    },
  });

  const dryRunMutation = useMutation({
    mutationFn: (sourceId: string) =>
      apiFetch<CollectorDryRunResponse>(
        `/api/v1/backoffice/agro/mercado/collector/sources/${sourceId}/test-dry-run`,
        { method: "POST" }
      ),
    onSuccess: (res) => {
      setDryRunResult(res);
      toast.success(`Dry-Run concluído: ${res.total_extraidos} itens pré-extraídos.`);
    },
    onError: (err: Error) => {
      toast.error(`Falha no Dry-Run: ${err.message}`);
    },
  });

  const runMutation = useMutation({
    mutationFn: (sourceId: string) =>
      apiFetch<CollectorRunSummary>(
        `/api/v1/backoffice/agro/mercado/collector/sources/${sourceId}/run`,
        { method: "POST" }
      ),
    onSuccess: (res) => {
      toast.success(
        `Coleta '${res.source_slug}' (${res.status}): ${res.total_publicados} publicados, ${res.total_quarentena} em revisão.`
      );
      invalidateCollectorQueries();
    },
    onError: (err: Error) => {
      toast.error(`Erro ao executar coleta: ${err.message}`);
    },
  });

  const columns: ColumnDef<CollectorSourceItem>[] = [
    {
      id: "fonte",
      header: "Fonte / Sigla",
      accessorFn: (row) => `${row.sigla} ${row.nome} ${row.slug}`,
      sortable: true,
      cell: (_val, row) => (
        <div className="space-y-0.5">
          <div className="font-medium text-foreground text-xs">{row.sigla}</div>
          <div className="text-[11px] text-muted-foreground truncate max-w-[230px]" title={row.nome}>
            {row.nome}
          </div>
          <div className="font-mono text-[10px] text-muted-foreground">{row.slug}</div>
        </div>
      ),
    },
    {
      id: "licenca",
      header: "Licença & Estratégia",
      accessorKey: "tipo_licenca",
      sortable: true,
      cell: (_val, row) => (
        <div className="space-y-1">
          <Badge
            variant="outline"
            className={`rounded-sm text-[10px] ${
              row.tipo_licenca === "DADO_PUBLICO_GOV"
                ? "border-emerald-600/30 text-emerald-700 bg-emerald-50 dark:text-emerald-400 dark:bg-emerald-950/30"
                : row.tipo_licenca === "PARCEIRO_AUTORIZADO"
                ? "border-sky-600/30 text-sky-700 bg-sky-50 dark:text-sky-400 dark:bg-sky-950/30"
                : "border-zinc-400/40 text-muted-foreground"
            }`}
          >
            {row.tipo_licenca}
          </Badge>
          <div className="text-[10px] font-mono text-muted-foreground">{row.estrategia_coleta}</div>
        </div>
      ),
    },
    {
      id: "uf",
      header: "UF / Praça",
      accessorKey: "uf_padrao",
      sortable: true,
      cell: (_val, row) => (
        <div className="text-xs">
          <Badge variant="outline" className="rounded-sm font-mono text-[10px] mr-1.5">
            {row.uf_padrao}
          </Badge>
          <span className="text-[11px] text-muted-foreground">{row.praca_padrao || "Estado"}</span>
        </div>
      ),
    },
    {
      id: "status",
      header: "Saúde & Revisão",
      accessorFn: (row) => `${row.ativo ? "ATIVO" : "INATIVO"} ${row.falhas_consecutivas}`,
      cell: (_val, row) => (
        <div className="flex flex-col gap-1 text-[11px]">
          <div className="flex items-center gap-1.5">
            {row.ativo ? (
              <span className="inline-flex items-center gap-1 text-emerald-700 dark:text-emerald-400 font-medium">
                <CheckCircle2 className="h-3.5 w-3.5" /> Ativa
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-muted-foreground">
                <PauseCircle className="h-3.5 w-3.5" /> Pausada
              </span>
            )}
            {row.falhas_consecutivas > 0 && (
              <Badge variant="outline" className="rounded-sm text-[10px] border-red-500/40 text-red-600">
                {row.falhas_consecutivas} falhas
              </Badge>
            )}
          </div>
          {row.pendentes_revisao > 0 && (
            <Badge variant="outline" className="w-fit rounded-sm text-[10px] border-amber-500/40 text-amber-700 dark:text-amber-400">
              {row.pendentes_revisao} em revisão
            </Badge>
          )}
        </div>
      ),
    },
    {
      id: "actions",
      header: "",
      isActionColumn: true,
      exportable: false,
      cell: (_val, row) => {
        const isLinkOnly = row.tipo_licenca === "LINK_HOMOLOGADO_APENAS";
        return (
          <div className="flex items-center justify-end gap-0">
            {canUpdate && !isLinkOnly && (
              <>
                <Button
                  type="button"
                  size="icon"
                  variant="ghost"
                  className="size-7 border-0 text-sky-600 hover:text-sky-700 dark:text-sky-400"
                  title="Testar Coleta (Dry-Run)"
                  aria-label={`Testar Dry-Run de ${row.sigla}`}
                  disabled={dryRunMutation.isPending}
                  onClick={() => dryRunMutation.mutate(row.id)}
                >
                  <FlaskConical className="h-3.5 w-3.5" />
                </Button>
                <Button
                  type="button"
                  size="icon"
                  variant="ghost"
                  className="size-7 border-0 text-emerald-600 hover:text-emerald-700 dark:text-emerald-400"
                  title="Executar Coleta Agora"
                  aria-label={`Executar coleta de ${row.sigla}`}
                  disabled={runMutation.isPending}
                  onClick={() => runMutation.mutate(row.id)}
                >
                  <Play className="h-3.5 w-3.5" />
                </Button>
              </>
            )}
            {canUpdate && (
              <Button
                type="button"
                size="icon"
                variant="ghost"
                className="size-7 border-0 text-muted-foreground hover:text-foreground"
                title="Editar Fonte / Whitelist"
                aria-label={`Editar fonte ${row.sigla}`}
                onClick={() => {
                  setEditingSource(row);
                  setFormState(toFormState(row));
                  setIsModalOpen(true);
                }}
              >
                <Pencil className="h-3.5 w-3.5" />
              </Button>
            )}
          </div>
        );
      },
    },
  ];

  return (
    <div className="space-y-4">
      <Card className="rounded-sm">
        <CardHeader className="pb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle className="text-base font-medium flex items-center gap-2">
              <Globe className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Fontes Oficiais &amp; Parceiros Autorizados
            </CardTitle>
            <CardDescription className="text-xs">
              Gerencie órgãos públicos estaduais, cooperativas parceiras com termo de autorização e whitelists HTTPS anti-SSRF.
            </CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Select value={licencaFilter} onValueChange={setLicencaFilter}>
              <SelectTrigger className="h-8 w-44 rounded-sm text-xs">
                <SelectValue placeholder="Licença" />
              </SelectTrigger>
              <SelectContent className="rounded-sm">
                <SelectItem value="TODAS">Todas as licenças</SelectItem>
                <SelectItem value="DADO_PUBLICO_GOV">DADO_PUBLICO_GOV</SelectItem>
                <SelectItem value="PARCEIRO_AUTORIZADO">PARCEIRO_AUTORIZADO</SelectItem>
                <SelectItem value="LINK_HOMOLOGADO_APENAS">LINK_HOMOLOGADO_APENAS</SelectItem>
              </SelectContent>
            </Select>

            <Select value={ufFilter} onValueChange={setUfFilter}>
              <SelectTrigger className="h-8 w-28 rounded-sm text-xs">
                <SelectValue placeholder="UF" />
              </SelectTrigger>
              <SelectContent className="rounded-sm">
                <SelectItem value="TODAS">Todas UFs</SelectItem>
                {ufsDisponiveis.map((uf) => (
                  <SelectItem key={uf} value={uf}>
                    {uf}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {canUpdate && (
              <Button
                variant="outline"
                size="sm"
                className="rounded-sm"
                onClick={() => {
                  setEditingSource(null);
                  setFormState(EMPTY_FORM);
                  setIsModalOpen(true);
                }}
              >
                <Plus className="h-3.5 w-3.5 mr-1.5" />
                Nova Fonte / Parceiro
              </Button>
            )}
          </div>
        </CardHeader>

        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-9 w-full rounded-sm" />
              <Skeleton className="h-12 w-full rounded-sm" />
            </div>
          ) : (
            <DataTable
              data={filteredSources}
              columns={columns}
              searchable
              searchPlaceholder="Buscar por sigla, slug ou nome..."
              exportable
              exportFileName="fontes-coletor-agro"
              emptyMessage="Nenhuma fonte cadastrada para os filtros atuais."
            />
          )}
        </CardContent>
      </Card>

      {/* Modal Criar / Editar Fonte ou Parceiro */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-base">
              {editingSource ? `Editar Fonte: ${editingSource.sigla}` : "Cadastrar Fonte / Parceiro Autorizado"}
            </DialogTitle>
            <DialogDescription className="text-xs">
              Somente URLs HTTPS dentro dos domínios autorizados são aceitas pelo fetcher anti-SSRF.
            </DialogDescription>
          </DialogHeader>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs py-2">
            <div>
              <Label className="text-xs">Slug único</Label>
              <Input
                value={formState.slug}
                disabled={Boolean(editingSource)}
                onChange={(e) => setFormState((p) => ({ ...p, slug: e.target.value }))}
                placeholder="ex: coop_sorriso_mt"
                className="h-8 rounded-sm mt-1 font-mono"
              />
            </div>
            <div>
              <Label className="text-xs">Sigla exibida</Label>
              <Input
                value={formState.sigla}
                onChange={(e) => setFormState((p) => ({ ...p, sigla: e.target.value }))}
                placeholder="ex: COOP-SORRISO/MT"
                className="h-8 rounded-sm mt-1"
              />
            </div>
            <div className="sm:col-span-2">
              <Label className="text-xs">Nome institucional completo</Label>
              <Input
                value={formState.nome}
                onChange={(e) => setFormState((p) => ({ ...p, nome: e.target.value }))}
                className="h-8 rounded-sm mt-1"
              />
            </div>

            <div>
              <Label className="text-xs">Tipo de Licença</Label>
              <Select
                value={formState.tipo_licenca}
                onValueChange={(v) => setFormState((p) => ({ ...p, tipo_licenca: v as TipoLicencaType }))}
              >
                <SelectTrigger className="h-8 rounded-sm mt-1 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="rounded-sm">
                  <SelectItem value="DADO_PUBLICO_GOV">DADO_PUBLICO_GOV</SelectItem>
                  <SelectItem value="PARCEIRO_AUTORIZADO">PARCEIRO_AUTORIZADO</SelectItem>
                  <SelectItem value="LINK_HOMOLOGADO_APENAS">LINK_HOMOLOGADO_APENAS</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label className="text-xs">Estratégia de Coleta</Label>
              <Select
                value={formState.estrategia_coleta}
                onValueChange={(v) =>
                  setFormState((p) => ({ ...p, estrategia_coleta: v as EstrategiaColetaType }))
                }
              >
                <SelectTrigger className="h-8 rounded-sm mt-1 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="rounded-sm">
                  <SelectItem value="NIVEL1_DETERMINISTICO">NIVEL1_DETERMINISTICO</SelectItem>
                  <SelectItem value="NIVEL2_IA_PDF_HTML">NIVEL2_IA_PDF_HTML</SelectItem>
                  <SelectItem value="GENERICO_PARCEIRO">GENERICO_PARCEIRO</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label className="text-xs">UF Padrão</Label>
              <Input
                maxLength={2}
                value={formState.uf_padrao}
                onChange={(e) => setFormState((p) => ({ ...p, uf_padrao: e.target.value.toUpperCase() }))}
                className="h-8 rounded-sm mt-1 uppercase"
              />
            </div>
            <div>
              <Label className="text-xs">Política de Publicação</Label>
              <Select
                value={formState.auto_publish_policy}
                onValueChange={(v) =>
                  setFormState((p) => ({ ...p, auto_publish_policy: v as AutoPublishPolicyType }))
                }
              >
                <SelectTrigger className="h-8 rounded-sm mt-1 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="rounded-sm">
                  <SelectItem value="SEMPRE_REVISAO_HUMANA">SEMPRE_REVISAO_HUMANA</SelectItem>
                  <SelectItem value="AUTO_SE_GUARDRAILS_OK">AUTO_SE_GUARDRAILS_OK</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="sm:col-span-2">
              <Label className="text-xs">URL Principal (HTTPS)</Label>
              <Input
                value={formState.url_principal}
                onChange={(e) => setFormState((p) => ({ ...p, url_principal: e.target.value }))}
                className="h-8 rounded-sm mt-1 font-mono"
              />
            </div>

            <div className="sm:col-span-2">
              <Label className="text-xs">URL Índice (para Sentinela, opcional)</Label>
              <Input
                value={formState.url_indice}
                onChange={(e) => setFormState((p) => ({ ...p, url_indice: e.target.value }))}
                className="h-8 rounded-sm mt-1 font-mono"
              />
            </div>

            <div className="sm:col-span-2">
              <Label className="text-xs">Domínios na Whitelist (separados por vírgula)</Label>
              <Input
                value={formState.dominios_whitelist}
                onChange={(e) => setFormState((p) => ({ ...p, dominios_whitelist: e.target.value }))}
                placeholder="ex: dados.coopsorriso.com.br, coopsorriso.com.br"
                className="h-8 rounded-sm mt-1 font-mono"
              />
            </div>

            {formState.tipo_licenca === "PARCEIRO_AUTORIZADO" && (
              <div className="sm:col-span-2">
                <Label className="text-xs">Referência do Termo de Autorização (Obrigatório)</Label>
                <Input
                  value={formState.termo_autorizacao_ref}
                  onChange={(e) =>
                    setFormState((p) => ({ ...p, termo_autorizacao_ref: e.target.value }))
                  }
                  placeholder="ex: Termo Cooperativa 2026/001 assinado em 10/11/2026"
                  className="h-8 rounded-sm mt-1"
                />
              </div>
            )}

            <div className="sm:col-span-2">
              <Label className="text-xs">Atribuição Obrigatória Exibida ao Produtor</Label>
              <Input
                value={formState.atribuicao_obrigatoria}
                onChange={(e) =>
                  setFormState((p) => ({ ...p, atribuicao_obrigatoria: e.target.value }))
                }
                className="h-8 rounded-sm mt-1"
              />
            </div>

            <div>
              <Label className="text-xs">Banda Máxima de Variação (%)</Label>
              <Input
                type="number"
                step="0.5"
                value={formState.max_variacao_pct}
                onChange={(e) => setFormState((p) => ({ ...p, max_variacao_pct: e.target.value }))}
                className="h-8 rounded-sm mt-1"
              />
            </div>
            <div className="flex items-end gap-2 pb-1">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formState.ativo}
                  onChange={(e) => setFormState((p) => ({ ...p, ativo: e.target.checked }))}
                />
                <span>Fonte Ativa para Agendamento</span>
              </label>
            </div>

            <div className="sm:col-span-2">
              <Label className="text-xs">Configuração do Extrator (JSON — CSV/Prompt/Emails)</Label>
              <Textarea
                rows={4}
                value={formState.config_extrator_json}
                onChange={(e) =>
                  setFormState((p) => ({ ...p, config_extrator_json: e.target.value }))
                }
                className="rounded-sm mt-1 font-mono text-[11px]"
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              className="rounded-sm"
              onClick={() => setIsModalOpen(false)}
            >
              Cancelar
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="rounded-sm border-emerald-600 text-emerald-700 dark:text-emerald-400"
              disabled={saveMutation.isPending}
              onClick={() => saveMutation.mutate(formState)}
            >
              Salvar Fonte
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal de Prévia do Dry-Run */}
      <Dialog open={Boolean(dryRunResult)} onOpenChange={() => setDryRunResult(null)}>
        <DialogContent className="rounded-sm max-w-3xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-base flex items-center gap-2">
              <FlaskConical className="h-4 w-4 text-sky-600" />
              Resultado Dry-Run — {dryRunResult?.source_slug}
            </DialogTitle>
            <DialogDescription className="text-xs font-mono break-all">
              {dryRunResult?.url_efetiva} · SHA-256: {dryRunResult?.sha256_bruto}
            </DialogDescription>
          </DialogHeader>

          {dryRunResult && (
            <div className="space-y-3 text-xs">
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline" className="rounded-sm">
                  {dryRunResult.total_extraidos} observações extraídas
                </Badge>
                {dryRunResult.modelo_ia && (
                  <Badge variant="outline" className="rounded-sm font-mono">
                    IA: {dryRunResult.modelo_ia} ({dryRunResult.tokens_entrada}+{dryRunResult.tokens_saida} tok · US$ {dryRunResult.custo_estimado_usd})
                  </Badge>
                )}
              </div>

              <div className="max-h-80 overflow-auto border rounded-sm divide-y">
                {dryRunResult.itens.map((item, idx) => (
                  <div key={`${item.commodity_id}-${item.praca}-${idx}`} className="p-2.5 space-y-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold">
                        {item.commodity_id} · {item.praca} ({item.uf}) — {item.data_referencia}
                      </span>
                      <span className="font-mono font-semibold text-emerald-700 dark:text-emerald-400">
                        R$ {item.valor_normalizado} / {item.unidade_normalizada}
                      </span>
                    </div>
                    <p className="text-[11px] font-mono bg-muted/50 p-1.5 rounded-sm break-all">
                      {item.trecho_evidencia}
                    </p>
                    {item.flags_anomalia.length > 0 && (
                      <div className="flex items-center gap-1 text-amber-700 dark:text-amber-400 text-[10px]">
                        <ShieldAlert className="h-3 w-3" />
                        Flags: {item.flags_anomalia.join(", ")}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              className="rounded-sm"
              onClick={() => setDryRunResult(null)}
            >
              Fechar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
