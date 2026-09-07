"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";

const MESES = [
  { value: 1, label: "Janeiro" },
  { value: 2, label: "Fevereiro" },
  { value: 3, label: "Março" },
  { value: 4, label: "Abril" },
  { value: 5, label: "Maio" },
  { value: 6, label: "Junho" },
  { value: 7, label: "Julho" },
  { value: 8, label: "Agosto" },
  { value: 9, label: "Setembro" },
  { value: 10, label: "Outubro" },
  { value: 11, label: "Novembro" },
  { value: 12, label: "Dezembro" },
];

const UNIDADES_AREA = [
  { value: "HA", label: "Hectare (ha)" },
  { value: "ALQUEIRE_PAULISTA", label: "Alqueire Paulista (2,42 ha)" },
  { value: "ALQUEIRE_MINEIRO", label: "Alqueire Mineiro (4,84 ha)" },
  { value: "ALQUEIRE_NORTE", label: "Alqueire do Norte (2,7225 ha)" },
  { value: "ACRE", label: "Acre (0,4047 ha)" },
];

const FUSOS = [
  { value: "America/Sao_Paulo", label: "São Paulo / Brasília (UTC-3)" },
  { value: "America/Cuiaba", label: "Cuiabá / MT (UTC-4)" },
  { value: "America/Manaus", label: "Manaus / AM (UTC-4)" },
  { value: "America/Boa_Vista", label: "Boa Vista / RR (UTC-4)" },
  { value: "America/Porto_Velho", label: "Porto Velho / RO (UTC-4)" },
  { value: "America/Recife", label: "Recife / PE (UTC-3)" },
  { value: "America/Fortaleza", label: "Fortaleza / CE (UTC-3)" },
  { value: "America/Belem", label: "Belém / PA (UTC-3)" },
  { value: "America/Noronha", label: "Fernando de Noronha (UTC-2)" },
];

interface ConfigGeral {
  ano_agricola: { mes_inicio: number; mes_fim: number };
  unidade_area: string;
  moeda: string;
  fuso_horario: string;
  idioma: string;
}

export function ConfiguracoesGeraisForm({ initialData }: { initialData?: ConfigGeral | null } = {}) {
  const queryClient = useQueryClient();

  const { data: config, isLoading } = useQuery<ConfigGeral>({
    queryKey: ["config-geral"],
    queryFn: () => apiFetch("config/geral"),
    initialData: initialData ?? undefined,
  });

  const [form, setForm] = useState<Partial<{
    ano_agricola_inicio: number;
    ano_agricola_fim: number;
    unidade_area: string;
    fuso_horario: string;
  }>>({});

  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      apiFetch("config/geral", { method: "PATCH", body: JSON.stringify(data) }),
    onSuccess: () => {
      toast.success("Configurações salvas com sucesso");
      queryClient.invalidateQueries({ queryKey: ["config-geral"] });
    },
    onError: () => toast.error("Erro ao salvar configurações"),
  });

  if (isLoading) {
    return <div className="animate-pulse h-64 bg-muted rounded-sm" />;
  }

  const current = { ...config, ...form };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Ano Agrícola */}
        <div className="space-y-3 p-4 border rounded-sm">
          <h3 className="font-medium text-sm">Ano Agrícola</h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Início</Label>
              <Select
                value={String(current.ano_agricola?.mes_inicio ?? 7)}
                onValueChange={(v) => setForm((f) => ({ ...f, ano_agricola_inicio: Number(v) }))}
              >
                <SelectTrigger className="h-8 rounded-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {MESES.map((m) => (
                    <SelectItem key={m.value} value={String(m.value)}>
                      {m.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Fim</Label>
              <Select
                value={String(current.ano_agricola?.mes_fim ?? 6)}
                onValueChange={(v) => setForm((f) => ({ ...f, ano_agricola_fim: Number(v) }))}
              >
                <SelectTrigger className="h-8 rounded-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {MESES.map((m) => (
                    <SelectItem key={m.value} value={String(m.value)}>
                      {m.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        {/* Unidade de Área */}
        <div className="space-y-3 p-4 border rounded-sm">
          <h3 className="font-medium text-sm">Unidade de Área</h3>
          <Select
            value={current.unidade_area ?? "HA"}
            onValueChange={(v) => setForm((f) => ({ ...f, unidade_area: v }))}
          >
            <SelectTrigger className="h-8 rounded-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {UNIDADES_AREA.map((u) => (
                <SelectItem key={u.value} value={u.value}>
                  {u.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            Dados são armazenados em hectares internamente. A exibição é convertida automaticamente.
          </p>
        </div>

        {/* Fuso Horário */}
        <div className="space-y-3 p-4 border rounded-sm">
          <h3 className="font-medium text-sm">Fuso Horário</h3>
          <Select
            value={current.fuso_horario ?? "America/Sao_Paulo"}
            onValueChange={(v) => setForm((f) => ({ ...f, fuso_horario: v }))}
          >
            <SelectTrigger className="h-8 rounded-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {FUSOS.map((f) => (
                <SelectItem key={f.value} value={f.value}>
                  {f.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Moeda */}
        <div className="space-y-3 p-4 border rounded-sm">
          <h3 className="font-medium text-sm">Moeda</h3>
          <Select value={current.moeda ?? "BRL"} disabled>
            <SelectTrigger className="h-8 rounded-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="BRL">Real Brasileiro (BRL)</SelectItem>
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            Suporte a USD/EUR disponível em relatórios.
          </p>
        </div>
      </div>

      <div className="flex justify-end">
        <Button
          size="sm"
          variant="outline"
          onClick={() => mutation.mutate(form)}
          disabled={mutation.isPending || Object.keys(form).length === 0}
        >
          {mutation.isPending ? "Salvando..." : "Salvar Configurações"}
        </Button>
      </div>
    </div>
  );
}
