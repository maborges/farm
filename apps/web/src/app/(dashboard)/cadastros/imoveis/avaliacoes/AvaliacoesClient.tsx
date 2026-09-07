"use client";

import * as React from "react";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useHasModule } from "@/hooks/use-has-module";
import { Modulos } from "@/lib/constants/modulos";
import { toast } from "sonner";
import {
  Badge,
} from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { Download, FileText, Plus, TrendingUp, DollarSign } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import type { ImovelRural } from "../ImoveisClient";

interface Avaliacao {
  id: string;
  imovel_id: string;
  data_avaliacao: string;
  metodo: "MERCADO" | "CUSTO" | "RENDA" | "DECLARADO" | "LAUDO";
  valor_total: string | number;
  valor_por_hectare?: string | number | null;
  valor_terra_nua?: string | number | null;
  valor_benfeitorias?: string | number | null;
  valor_lavoura_perene?: string | number | null;
  moeda: string;
  responsavel?: string | null;
  numero_laudo?: string | null;
  observacoes?: string | null;
  anexos?: Array<Record<string, unknown>> | null;
}

interface AvaliacaoResumo {
  total_avaliacoes: number;
  valor_total_atual?: string | number | null;
  valor_por_hectare_atual?: string | number | null;
  variacao_percentual?: number | null;
  area_total_ha?: string | number | null;
}

interface AvaliacoesClientProps {
  initialImoveis: ImovelRural[];
}

const METODOS = [
  { value: "LAUDO", label: "Laudo técnico" },
  { value: "MERCADO", label: "Mercado comparativo" },
  { value: "CUSTO", label: "Custo de reposição" },
  { value: "RENDA", label: "Capitalização da renda" },
  { value: "DECLARADO", label: "Valor declarado" },
];

function formatCurrency(value: string | number | null | undefined, currency = "BRL") {
  const amount = Number(value || 0);
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency }).format(amount);
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("pt-BR").format(new Date(value));
}

export function AvaliacoesClient({ initialImoveis }: AvaliacoesClientProps) {
  const queryClient = useQueryClient();
  const hasModule = useHasModule(Modulos.IMOVEIS_AVALIACAO);
  const [open, setOpen] = useState(false);
  const [imovelId, setImovelId] = useState<string>(initialImoveis[0]?.id || "");
  const [form, setForm] = useState({
    data_avaliacao: new Date().toISOString().split("T")[0],
    metodo: "LAUDO",
    valor_total: "",
    valor_por_hectare: "",
    valor_terra_nua: "",
    valor_benfeitorias: "",
    valor_lavoura_perene: "",
    moeda: "BRL",
    responsavel: "",
    numero_laudo: "",
    observacoes: "",
  });

  const { data: imoveis = initialImoveis, isLoading: isLoadingImoveis } = useQuery<ImovelRural[]>({
    queryKey: ["imoveis-rurais-avaliacoes"],
    queryFn: async () => apiFetch("imoveis/?situacao=all"),
    enabled: hasModule,
    initialData: initialImoveis.length > 0 ? initialImoveis : undefined,
  });

  const selectedImovel = useMemo(
    () => imoveis.find((item) => item.id === imovelId),
    [imoveis, imovelId]
  );

  const { data: avaliacoes = [], isLoading } = useQuery<Avaliacao[]>({
    queryKey: ["imoveis-avaliacoes", imovelId],
    queryFn: async () => {
      if (!imovelId) return [];
      return apiFetch(`imoveis/avaliacoes?imovel_id=${imovelId}`);
    },
    enabled: hasModule && Boolean(imovelId),
    initialData: [],
  });

  const { data: resumo } = useQuery<AvaliacaoResumo>({
    queryKey: ["imoveis-avaliacoes-resumo", imovelId],
    queryFn: async () => apiFetch(`imoveis/avaliacoes/${imovelId}/resumo`),
    enabled: hasModule && Boolean(imovelId),
  });

  const createMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      apiFetch("imoveis/avaliacoes", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["imoveis-avaliacoes"] });
      queryClient.invalidateQueries({ queryKey: ["imoveis-avaliacoes-resumo"] });
      setOpen(false);
      toast.success("Avaliação patrimonial registrada");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Erro ao registrar avaliação");
    },
  });

  const handleSubmit = () => {
    if (!imovelId || !form.data_avaliacao) {
      toast.error("Selecione um imóvel e informe a data da avaliação");
      return;
    }

    createMutation.mutate({
      imovel_id: imovelId,
      data_avaliacao: form.data_avaliacao,
      metodo: form.metodo,
      valor_total: form.valor_total ? Number(form.valor_total) : undefined,
      valor_por_hectare: form.valor_por_hectare ? Number(form.valor_por_hectare) : undefined,
      valor_terra_nua: form.valor_terra_nua ? Number(form.valor_terra_nua) : undefined,
      valor_benfeitorias: form.valor_benfeitorias ? Number(form.valor_benfeitorias) : undefined,
      valor_lavoura_perene: form.valor_lavoura_perene ? Number(form.valor_lavoura_perene) : undefined,
      moeda: form.moeda || "BRL",
      responsavel: form.responsavel || undefined,
      numero_laudo: form.numero_laudo || undefined,
      observacoes: form.observacoes || undefined,
      anexos: [],
    });
  };

  if (!hasModule) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-muted-foreground">
          O módulo de avaliação patrimonial não está contratado para este tenant.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Avaliação Patrimonial"
        description="Laudos, histórico de valorização e indicadores por hectare"
        icon={<DollarSign className="text-primary" size={22} />}
        breadcrumbs={[
            { label: "Cadastros", href: "/cadastros" },
            { label: "Imóveis Rurais", href: "/cadastros/imoveis" },
            { label: "Avaliações Patrimoniais" },
        ]}
      />

      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <CardTitle className="text-base">Painel de Avaliação</CardTitle>
            <div className="flex flex-wrap items-center gap-2">
              <Select value={imovelId || undefined} onValueChange={setImovelId}>
                <SelectTrigger className="min-w-[280px]" aria-label="Selecione um imóvel">
                  <SelectValue placeholder="Selecione um imóvel" />
                </SelectTrigger>
                <SelectContent>
                  {isLoadingImoveis && imoveis.length === 0 ? (
                    <SelectItem value="__loading__" disabled>Carregando imóveis...</SelectItem>
                  ) : imoveis.length === 0 ? (
                    <SelectItem value="__empty__" disabled>Nenhum imóvel encontrado</SelectItem>
                  ) : (
                    imoveis.map((imovel) => (
                      <SelectItem key={imovel.id} value={imovel.id}>
                        {imovel.nome} - {imovel.municipio}/{imovel.uf}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
              <Button variant="outline" size="sm" className="rounded-sm" onClick={() => setOpen(true)}>
                <Plus className="h-3.5 w-3.5 mr-2" />
                Nova avaliação
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="rounded-sm"
                disabled={!imovelId}
                onClick={() => window.open(`/api/v1/imoveis/avaliacoes/${imovelId}/export/pdf`, "_blank")}
              >
                <Download className="h-3.5 w-3.5 mr-2" />
                Exportar PDF
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Valor patrimonial atual</CardDescription>
            <CardTitle>{formatCurrency(resumo?.valor_total_atual)}</CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            {selectedImovel ? `${selectedImovel.nome}` : "Selecione um imóvel"}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Valor por hectare</CardDescription>
            <CardTitle>{formatCurrency(resumo?.valor_por_hectare_atual)}</CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            Área total: {Number(resumo?.area_total_ha || 0).toFixed(4)} ha
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Variação histórica</CardDescription>
            <CardTitle>{resumo?.variacao_percentual != null ? `${resumo.variacao_percentual.toFixed(2)}%` : "—"}</CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            {resumo?.total_avaliacoes ? `${resumo.total_avaliacoes} avaliações registradas` : "Sem histórico ainda"}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Histórico de avaliações</CardTitle>
          <CardDescription>Últimas avaliações patrimoniais do imóvel selecionado</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="py-8 text-center text-sm text-muted-foreground">Carregando avaliações...</div>
          ) : avaliacoes.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              Nenhuma avaliação encontrada.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Data</TableHead>
                  <TableHead>Método</TableHead>
                  <TableHead>Valor total</TableHead>
                  <TableHead>Valor/ha</TableHead>
                  <TableHead>Laudo</TableHead>
                  <TableHead>Responsável</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {avaliacoes.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="text-xs">{formatDate(item.data_avaliacao)}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="rounded-sm text-[10px] uppercase font-bold">
                        {item.metodo}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-medium">{formatCurrency(item.valor_total, item.moeda)}</TableCell>
                    <TableCell>{formatCurrency(item.valor_por_hectare || 0, item.moeda)}</TableCell>
                    <TableCell className="text-xs">{item.numero_laudo || "-"}</TableCell>
                    <TableCell className="text-xs">{item.responsavel || "-"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-xl p-0">
          <DialogHeader className="px-6 pt-6 pb-2 border-b">
            <DialogTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary" />
              Nova avaliação patrimonial
            </DialogTitle>
            <DialogDescription>
              Registre o laudo com valor total, valor por hectare e observações.
              {selectedImovel && (
                <span className="block mt-2 px-3 py-2 bg-muted/40 border rounded-md text-foreground font-medium flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-primary" />
                  Imóvel alvo: {selectedImovel.nome} <span className="text-muted-foreground font-normal ml-1">({selectedImovel.municipio}/{selectedImovel.uf})</span>
                </span>
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="px-6 py-4 space-y-6 max-h-[70vh] overflow-y-auto">
            {/* Informações Básicas */}
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Informações Básicas</h4>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="av-data" className="mb-1.5 block text-sm font-medium">Data *</label>
                  <Input
                    id="av-data"
                    type="date"
                    value={form.data_avaliacao}
                    onChange={(e) => setForm({ ...form, data_avaliacao: e.target.value })}
                  />
                </div>
                <div>
                  <label htmlFor="av-metodo" className="mb-1.5 block text-sm font-medium">Método *</label>
                  <Select value={form.metodo} onValueChange={(value) => setForm({ ...form, metodo: value })}>
                    <SelectTrigger id="av-metodo" aria-label="Método">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {METODOS.map((metodo) => (
                        <SelectItem key={metodo.value} value={metodo.value}>
                          {metodo.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label htmlFor="av-responsavel" className="mb-1.5 block text-sm font-medium">Responsável Técnico</label>
                  <Input
                    id="av-responsavel"
                    placeholder="Nome do avaliador"
                    value={form.responsavel}
                    onChange={(e) => setForm({ ...form, responsavel: e.target.value })}
                  />
                </div>
                <div>
                  <label htmlFor="av-laudo" className="mb-1.5 block text-sm font-medium">Número do Laudo</label>
                  <Input
                    id="av-laudo"
                    placeholder="Ex: LAUDO-2026-001"
                    value={form.numero_laudo}
                    onChange={(e) => setForm({ ...form, numero_laudo: e.target.value })}
                  />
                </div>
              </div>
            </div>

            {/* Composição de Valores */}
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Composição de Valores</h4>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="sm:col-span-2 grid gap-4 sm:grid-cols-2 p-3 bg-muted/30 rounded-md border border-dashed">
                  <div>
                    <label htmlFor="av-moeda" className="mb-1.5 block text-sm font-medium">Moeda</label>
                    <Select value={form.moeda} onValueChange={(value) => setForm({ ...form, moeda: value })}>
                      <SelectTrigger id="av-moeda" aria-label="Moeda">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="BRL">Real (R$)</SelectItem>
                        <SelectItem value="USD">Dólar (US$)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <label htmlFor="av-total" className="mb-1.5 block text-sm font-medium">Valor Total Estimado</label>
                    <Input
                      id="av-total"
                      type="number"
                      step="0.01"
                      placeholder="0.00"
                      value={form.valor_total}
                      onChange={(e) => setForm({ ...form, valor_total: e.target.value })}
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="av-ha" className="mb-1.5 block text-sm font-medium text-muted-foreground">Valor por Hectare</label>
                  <Input
                    id="av-ha"
                    type="number"
                    step="0.01"
                    placeholder="0.00"
                    value={form.valor_por_hectare}
                    onChange={(e) => setForm({ ...form, valor_por_hectare: e.target.value })}
                  />
                </div>
                <div>
                  <label htmlFor="av-terra" className="mb-1.5 block text-sm font-medium text-muted-foreground">Terra Nua</label>
                  <Input
                    id="av-terra"
                    type="number"
                    step="0.01"
                    placeholder="0.00"
                    value={form.valor_terra_nua}
                    onChange={(e) => setForm({ ...form, valor_terra_nua: e.target.value })}
                  />
                </div>
                <div>
                  <label htmlFor="av-benf" className="mb-1.5 block text-sm font-medium text-muted-foreground">Benfeitorias</label>
                  <Input
                    id="av-benf"
                    type="number"
                    step="0.01"
                    placeholder="0.00"
                    value={form.valor_benfeitorias}
                    onChange={(e) => setForm({ ...form, valor_benfeitorias: e.target.value })}
                  />
                </div>
                <div>
                  <label htmlFor="av-perene" className="mb-1.5 block text-sm font-medium text-muted-foreground">Lavoura Perene / Pastagem</label>
                  <Input
                    id="av-perene"
                    type="number"
                    step="0.01"
                    placeholder="0.00"
                    value={form.valor_lavoura_perene}
                    onChange={(e) => setForm({ ...form, valor_lavoura_perene: e.target.value })}
                  />
                </div>
              </div>
            </div>

            {/* Observações */}
            <div>
              <label htmlFor="av-obs" className="mb-1.5 block text-sm font-medium">Observações adicionais</label>
              <Textarea
                id="av-obs"
                rows={3}
                placeholder="Detalhes metodológicos, premissas adotadas, ressalvas do laudo..."
                value={form.observacoes}
                onChange={(e) => setForm({ ...form, observacoes: e.target.value })}
              />
            </div>
          </div>

          <DialogFooter className="px-6 py-4 border-t bg-muted/20">
            <Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button>
            <Button onClick={handleSubmit}>Salvar avaliação</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
