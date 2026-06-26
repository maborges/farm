"use client";

import { useMemo, useState } from "react";
import { Search, CheckCircle2 } from "lucide-react";

import type { CachedAnimal, CachedLote } from "@/lib/db";
import { CampoPill, CampoSurface } from "./ui";

type AnimalPickerMode = "MATRIZ" | "DIAGNOSTICO" | "PARTO" | "DESMAMA" | "GERAL";

interface AnimalPickerProps {
  label: string;
  animals: CachedAnimal[];
  lotes: CachedLote[];
  value: string;
  onChange: (id: string) => void;
  mode: AnimalPickerMode;
  loteId?: string;
  placeholder?: string;
  emptyMessage?: string;
}

const REPRODUCAO_FIELDS = (animal: CachedAnimal): Record<string, unknown> => {
  const extras = animal.dados_extras as Record<string, unknown> | undefined;
  const repro = extras?.reproducao;
  return (repro && typeof repro === "object" ? (repro as Record<string, unknown>) : {}) as Record<string, unknown>;
};

export function AnimalPicker({
  label,
  animals,
  lotes,
  value,
  onChange,
  mode,
  loteId,
  placeholder = "Pesquisar por identificação, brinco, nome ou lote",
  emptyMessage = "Nenhum animal encontrado para os filtros atuais.",
}: AnimalPickerProps) {
  const [search, setSearch] = useState("");

  const lotesMap = useMemo(() => new Map(lotes.map((lote) => [lote.id, lote])), [lotes]);

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    return animals
      .filter((animal) => {
        if (loteId && animal.lote_id && animal.lote_id !== loteId) return false;
        if (mode === "MATRIZ") {
          if ((animal.sexo ?? "").toUpperCase() !== "FEMEA") return false;
          if ((animal.status ?? "").toUpperCase() !== "ATIVO") return false;
        }
        if (mode === "DIAGNOSTICO") {
          const repro = REPRODUCAO_FIELDS(animal);
          if ((animal.sexo ?? "").toUpperCase() !== "FEMEA") return false;
          if ((animal.status ?? "").toUpperCase() !== "ATIVO") return false;
          if (!["COBERTURA", "INSEMINACAO"].includes(String(repro.ultimo_evento ?? "").toUpperCase())) return false;
        }
        if (mode === "PARTO") {
          const repro = REPRODUCAO_FIELDS(animal);
          const diagnostico = repro.diagnostico as Record<string, unknown> | undefined;
          if ((animal.sexo ?? "").toUpperCase() !== "FEMEA") return false;
          if (String(repro.diagnostico_resultado ?? diagnostico?.resultado ?? "").toUpperCase() !== "PRENHE") return false;
        }
        if (mode === "DESMAMA") {
          if (!["BEZERRO", "BEZERRA"].includes((animal.categoria ?? "").toUpperCase())) return false;
        }

        if (!query) return true;
        const lote = animal.lote_id ? lotesMap.get(animal.lote_id) : undefined;
        const haystack = [
          animal.numero_brinco,
          animal.numero_sisbov,
          animal.nome,
          animal.id,
          animal.categoria,
          animal.sexo,
          lote?.identificacao,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return haystack.includes(query);
      })
      .sort((a, b) => {
        if (a.id === value) return -1;
        if (b.id === value) return 1;
        return (a.numero_brinco ?? a.nome ?? a.id).localeCompare(b.numero_brinco ?? b.nome ?? b.id);
      });
  }, [animals, loteId, lotesMap, mode, search, value]);

  const selected = animals.find((animal) => animal.id === value);

  return (
    <CampoSurface className="flex flex-col gap-3 p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-foreground">{label}</p>
          <p className="text-xs text-muted-foreground">{placeholder}</p>
        </div>
        <CampoPill>{filtered.length} encontrados</CampoPill>
      </div>

      <label className="flex items-center gap-2 rounded-sm border border-border bg-card px-3 py-2.5">
        <Search className="size-4 text-muted-foreground" />
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="w-full bg-transparent text-sm outline-none"
          placeholder={placeholder}
          autoComplete="off"
          inputMode="search"
        />
      </label>

      {selected && (
        <div className="rounded-sm border border-primary/20 bg-primary/5 px-3 py-2 text-sm">
          <p className="font-semibold text-foreground">Selecionado</p>
          <p className="mt-1 text-muted-foreground">
            {selected.numero_brinco ?? selected.id}
            {selected.nome ? ` · ${selected.nome}` : ""}
            {selected.lote_id ? ` · ${lotesMap.get(selected.lote_id)?.identificacao ?? selected.lote_id}` : ""}
          </p>
        </div>
      )}

      <div className="max-h-72 overflow-auto rounded-sm border border-border">
        {filtered.length === 0 ? (
          <div className="px-3 py-4 text-sm text-muted-foreground">{emptyMessage}</div>
        ) : (
          <div className="divide-y divide-border">
            {filtered.map((animal) => {
              const lot = animal.lote_id ? lotesMap.get(animal.lote_id) : undefined;
              const active = animal.id === value;
              return (
                <button
                  key={animal.id}
                  type="button"
                  onClick={() => onChange(animal.id)}
                  className={`flex w-full flex-col gap-1 px-3 py-3 text-left transition-colors ${
                    active ? "bg-primary/5" : "bg-card hover:bg-muted/60"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-foreground">
                        {animal.numero_brinco ?? "Sem brinco"}
                        {animal.nome ? ` · ${animal.nome}` : ""}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {lot?.identificacao ?? "Sem lote"}
                        {animal.categoria ? ` · ${animal.categoria}` : ""}
                        {animal.sexo ? ` · ${animal.sexo}` : ""}
                        {animal.status ? ` · ${animal.status}` : ""}
                      </p>
                    </div>
                    {active && <CheckCircle2 className="size-4 shrink-0 text-primary" />}
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </CampoSurface>
  );
}
