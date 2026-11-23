"use client";

import React, { useState, useMemo, useEffect, useRef } from "react";
import { usePessoasOperacionais } from "@/lib/hooks/use-pessoas";
import { useSessionStore } from "@/lib/stores/session-store";
import { Search, X, Check, ChevronDown } from "lucide-react";
import { CampoButton } from "./ui";

interface Props {
  unidadeProdutivaId?: string | null;
  value?: string | null;
  onChange: (pessoaId: string | null) => void;
  disabled?: boolean;
}

export function PessoaSelect({ unidadeProdutivaId, value, onChange, disabled }: Props) {
  const pessoas = usePessoasOperacionais(unidadeProdutivaId || undefined);
  const session = useSessionStore((state) => state.session);
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  // Limpeza de executor inválido ao trocar de UP
  useEffect(() => {
    if (unidadeProdutivaId && pessoas && value) {
      const isEligible = pessoas.some((p) => p.pessoa_id === value);
      if (!isEligible) {
        onChange(null);
      }
    }
  }, [unidadeProdutivaId, pessoas, value, onChange]);

  // Click outside para fechar
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const selectedPerson = useMemo(() => {
    if (!pessoas || !value) return null;
    return pessoas.find((p) => p.pessoa_id === value) || null;
  }, [pessoas, value]);

  const filteredPessoas = useMemo(() => {
    if (!pessoas) return [];
    if (!search) return pessoas;

    // Helper para remover acentos para a busca
    const removeAccents = (str: string) => str.normalize("NFD").replace(/[\u0300-\u036f]/g, "");

    const searchLower = removeAccents(search.toLowerCase());
    return pessoas.filter((p) =>
      removeAccents(p.nome_exibicao.toLowerCase()).includes(searchLower)
    );
  }, [pessoas, search]);

  const buttonLabel = selectedPerson
    ? selectedPerson.nome_exibicao
    : "Não informado (Sistêmico / Titular)";

  const isDisabled = disabled || !unidadeProdutivaId;

  // Estados de texto para placeholder do dropdown ou botões
  let statusText = null;
  if (!unidadeProdutivaId) {
    statusText = "Selecione primeiro a Unidade Produtiva.";
  } else if (!pessoas) {
    statusText = "Carregando executores...";
  } else if (pessoas.length === 0) {
    if (session?.last_sync_at === null) {
      statusText = "Catálogo de pessoas ainda não sincronizado. Conecte-se à internet e atualize os dados.";
    } else {
      statusText = "Nenhuma pessoa disponível para esta Unidade Produtiva.";
    }
  } else if (filteredPessoas.length === 0) {
    statusText = "Nenhuma pessoa encontrada com esse nome.";
  }

  return (
    <div className="relative flex flex-col gap-1.5" ref={containerRef}>
      <button
        data-testid="pessoa-select-trigger"
        type="button"
        disabled={isDisabled}
        onClick={() => setIsOpen((prev) => !prev)}
        className={`flex items-center justify-between w-full h-11 px-3.5 rounded-lg md:rounded-sm border transition-all
          ${isDisabled
            ? "border-input bg-background/50 text-muted-foreground opacity-60 cursor-not-allowed"
            : "border-border bg-card text-foreground hover:bg-muted focus:border-ring focus:ring-1 focus:ring-ring"
          }
        `}
      >
        <span className="truncate text-sm font-medium">
          {buttonLabel}
        </span>
        {value && !isDisabled ? (
          <X
            className="w-4 h-4 opacity-50 hover:opacity-100"
            onClick={(e) => {
              e.stopPropagation();
              onChange(null);
            }}
          />
        ) : (
          <ChevronDown className="w-4 h-4 opacity-50" />
        )}
      </button>

      {/* Helper text nativo se disabled */}
      {!unidadeProdutivaId && (
        <p className="text-[11px] text-amber-600 font-medium">
          ⚠️ Selecione primeiro a Unidade Produtiva.
        </p>
      )}

      {/* Overlay Dropdown Inline */}
      {isOpen && !isDisabled && (
        <div className="absolute top-full mt-1 left-0 right-0 z-50 rounded-xl md:rounded-sm border border-border bg-card shadow-lg max-h-[300px] flex flex-col overflow-hidden">
          {/* Search Input */}
          <div className="p-2 border-b border-border bg-muted/30">
            <div className="relative">
              <Search className="absolute left-3 md:left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                autoFocus
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar por nome..."
                className="w-full h-11 md:h-9 pl-9 pr-3 rounded-lg md:rounded-sm border border-input bg-background text-base md:text-sm outline-none focus:border-primary"
              />
            </div>
          </div>

          {/* List or Status */}
          <div className="overflow-y-auto flex-1 p-1">
            {statusText ? (
              <div className="p-4 text-center text-sm text-muted-foreground">
                {statusText}
              </div>
            ) : (
              <ul className="flex flex-col gap-0.5">
                {/* Opção None explícita no dropdown também para facilidade */}
                <li>
                  <button
                    type="button"
                    onClick={() => {
                      onChange(null);
                      setIsOpen(false);
                    }}
                    className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg md:rounded-sm text-left transition-colors hover:bg-muted ${!value ? 'bg-primary/10' : ''}`}
                  >
                    <span className={`text-sm ${!value ? 'font-semibold text-primary' : 'font-medium'}`}>Não informado (Sistêmico / Titular)</span>
                    {!value && <Check className="w-4 h-4 text-primary" />}
                  </button>
                </li>

                {filteredPessoas.map((p) => {
                  const isSelected = p.pessoa_id === value;
                  return (
                    <li key={p.id}>
                      <button
                        type="button"
                        onClick={() => {
                          onChange(p.pessoa_id);
                          setIsOpen(false);
                        }}
                        className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg md:rounded-sm text-left transition-colors hover:bg-muted ${isSelected ? 'bg-primary/10' : ''}`}
                      >
                        <div className="flex flex-col gap-0.5 min-w-0 pr-2">
                          <span className={`text-sm truncate ${isSelected ? 'font-semibold text-primary' : 'font-medium text-foreground'}`}>
                            {p.nome_exibicao}
                          </span>
                          {p.papeis && p.papeis.length > 0 && (
                            <span className="text-[11px] text-muted-foreground truncate">
                              {p.papeis.join(" · ")}
                            </span>
                          )}
                        </div>
                        {isSelected && <Check className="w-4 h-4 text-primary shrink-0" />}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
