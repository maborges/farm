"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Search, Building2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface FornecedorComboboxItem {
  id: string;
  nome_fantasia: string;
  cnpj_cpf: string | null;
  condicoes_pagamento?: string | null;
  prazo_entrega_dias?: number | null;
}

export function FornecedorCombobox({ value, onChange, onSelectFornecedor, className }: {
  value: string;
  onChange: (fornecedorId: string) => void;
  onSelectFornecedor?: (fornecedor: FornecedorComboboxItem) => void;
  className?: string;
}) {
  const [aberto, setAberto] = useState(false);
  const [termo, setTermo] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  const { data: fornecedores = [], isFetching } = useQuery<FornecedorComboboxItem[]>({
    queryKey: ["fornecedores-busca", termo],
    queryFn: () => apiFetch(`/compras/fornecedores?q=${encodeURIComponent(termo)}`),
    enabled: aberto,
    staleTime: 30_000,
  });

  const selecionado = fornecedores.find(f => f.id === value);

  useEffect(() => {
    function handleClickFora(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setAberto(false);
      }
    }
    document.addEventListener("mousedown", handleClickFora);
    return () => document.removeEventListener("mousedown", handleClickFora);
  }, []);

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      <div className="relative">
        <Search className="absolute left-2 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
        <Input
          placeholder="Buscar fornecedor por nome ou CNPJ/CPF"
          className="h-8 rounded-sm text-xs pl-7"
          value={aberto ? termo : (selecionado?.nome_fantasia ?? "")}
          onFocus={() => { setAberto(true); setTermo(""); }}
          onChange={e => setTermo(e.target.value)}
        />
      </div>
      {aberto && (
        <div className="absolute z-50 mt-1 w-full rounded-sm border bg-popover shadow-md">
          <ScrollArea className="max-h-48">
            {isFetching && (
              <p className="px-3 py-2 text-xs text-muted-foreground">Buscando...</p>
            )}
            {!isFetching && fornecedores.length === 0 && (
              <p className="px-3 py-2 text-xs text-muted-foreground">
                Nenhum fornecedor encontrado.
              </p>
            )}
            {fornecedores.map(f => (
              <button
                key={f.id}
                type="button"
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs hover:bg-accent"
                onClick={() => { onChange(f.id); onSelectFornecedor?.(f); setAberto(false); }}
              >
                <Building2 className="size-3.5 text-muted-foreground shrink-0" />
                <span className="truncate">{f.nome_fantasia}</span>
                {f.cnpj_cpf && (
                  <span className="ml-auto text-muted-foreground shrink-0">{f.cnpj_cpf}</span>
                )}
              </button>
            ))}
          </ScrollArea>
        </div>
      )}
    </div>
  );
}
