"use client";

import * as React from "react";
import { AlertCircle, Check, Crosshair, Loader2, MapPin, Search, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  fetchMunicipios,
  type LocalidadeClima,
  type MunicipioBuscaItem,
} from "@/lib/clima/localidade";
import { useLocalidadeClima } from "@/lib/clima/localidade-store";
import { useDeviceContext } from "@/lib/device/use-device-context";
import { cn } from "@/lib/utils";

const UFS_BRASIL = [
  "TODAS", "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
  "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ",
  "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"
] as const;

interface SeletorLocalidadeModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SeletorLocalidadeModal({
  isOpen,
  onClose,
}: SeletorLocalidadeModalProps): React.ReactElement | null {
  const { localidade, setLocalidade } = useLocalidadeClima();
  const { layoutProfile } = useDeviceContext();
  const isBottomSheet = layoutProfile.sheetPresentation === "bottom-sheet";

  const [searchTerm, setSearchTerm] = React.useState("");
  const [selectedUf, setSelectedUf] = React.useState<string>("TODAS");
  const [itens, setItens] = React.useState<MunicipioBuscaItem[]>([]);
  const [searchStatus, setSearchStatus] = React.useState<
    "INICIAL" | "CARREGANDO" | "SUCESSO" | "VAZIO" | "ERRO_CATALOGO" | "ERRO_COMUNICACAO" | "ERRO_PARAMETROS"
  >("INICIAL");
  const [statusMessage, setStatusMessage] = React.useState<string | null>(null);
  const [isGpsLoading, setIsGpsLoading] = React.useState(false);
  const [gpsError, setGpsError] = React.useState<string | null>(null);

  const inputRef = React.useRef<HTMLInputElement>(null);
  const modalRef = React.useRef<HTMLDivElement>(null);
  const activeRequestIdRef = React.useRef(0);

  // Foco inicial ao abrir
  React.useEffect(() => {
    if (isOpen) {
      setSearchTerm("");
      setItens([]);
      setSearchStatus("INICIAL");
      setStatusMessage(null);
      setGpsError(null);
      const timer = setTimeout(() => {
        inputRef.current?.focus();
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  // Tecla Escape para fechar
  React.useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Debounced search com identificador único de requisição
  React.useEffect(() => {
    if (!isOpen) return;

    const term = searchTerm.trim();
    const ufFilter = selectedUf !== "TODAS" ? selectedUf : undefined;

    if (term.length < 2 && !ufFilter) {
      setItens([]);
      setSearchStatus("INICIAL");
      setStatusMessage(null);
      return;
    }

    setSearchStatus("CARREGANDO");
    setStatusMessage(null);

    const controller = new AbortController();
    const currentRequestId = ++activeRequestIdRef.current;

    const timeout = setTimeout(async () => {
      try {
        const res = await fetchMunicipios(term, ufFilter, controller.signal);
        if (controller.signal.aborted || currentRequestId !== activeRequestIdRef.current) return;

        if (!res) {
          setItens([]);
          setSearchStatus("INICIAL");
          setStatusMessage(null);
        } else if (res.status === "SUCESSO") {
          setItens(res.itens);
          setSearchStatus("SUCESSO");
          setStatusMessage(null);
        } else if (res.status === "NENHUM_ENCONTRADO") {
          setItens([]);
          setSearchStatus("VAZIO");
          setStatusMessage(res.mensagem || "Nenhum município encontrado para os critérios informados.");
        } else if (res.status === "CATALOGO_INDISPONIVEL") {
          setItens([]);
          setSearchStatus("ERRO_CATALOGO");
          setStatusMessage(res.mensagem);
        } else if (res.status === "PARAMETROS_INVALIDOS") {
          setItens([]);
          setSearchStatus("ERRO_PARAMETROS");
          setStatusMessage(res.mensagem);
        } else {
          setItens([]);
          setSearchStatus("ERRO_COMUNICACAO");
          setStatusMessage(res.mensagem || "Falha na comunicação com o serviço.");
        }
      } catch {
        if (!controller.signal.aborted && currentRequestId === activeRequestIdRef.current) {
          setItens([]);
          setSearchStatus("ERRO_COMUNICACAO");
          setStatusMessage("Erro de rede ao consultar serviço de municípios.");
        }
      }
    }, 300);

    return () => {
      clearTimeout(timeout);
      controller.abort();
    };
  }, [searchTerm, selectedUf, isOpen]);

  // Ação de seleção de município IBGE
  const handleSelectMunicipio = (item: MunicipioBuscaItem) => {
    const loc: LocalidadeClima = {
      codigoIbge: item.codigoIbge,
      nome: item.nome,
      uf: item.uf,
      estadoNome: item.estadoNome,
      latitude: item.latitude,
      longitude: item.longitude,
      fusoHorario: item.fusoHorario,
      tipoOrigem: "CENTROIDE_IBGE",
      selecionadoEmIso: new Date().toISOString(),
    };
    setLocalidade(loc);
    onClose();
  };

  // Ação de obtenção consentida de GPS
  const handleUseGps = () => {
    if (typeof window === "undefined" || !("geolocation" in navigator)) {
      setGpsError("Geolocalização não é suportada pelo seu navegador ou dispositivo.");
      return;
    }

    setIsGpsLoading(true);
    setGpsError(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = Math.round(position.coords.latitude * 10000) / 10000;
        const lon = Math.round(position.coords.longitude * 10000) / 10000;
        const accuracy = Math.round(position.coords.accuracy);

        const loc: LocalidadeClima = {
          nome: "Localização Atual (GPS)",
          uf: "",
          latitude: lat,
          longitude: lon,
          fusoHorario: "America/Sao_Paulo",
          tipoOrigem: "GPS",
          precisaoGpsMetros: accuracy,
          selecionadoEmIso: new Date().toISOString(),
        };

        setLocalidade(loc);
        setIsGpsLoading(false);
        onClose();
      },
      (error) => {
        setIsGpsLoading(false);
        switch (error.code) {
          case 1: // PERMISSION_DENIED
            setGpsError("Permissão de localização negada. Pesquise pelo nome do município abaixo.");
            break;
          case 2: // POSITION_UNAVAILABLE
            setGpsError("Sinal GPS indisponível no momento. Tente novamente ou pesquise o município.");
            break;
          case 3: // TIMEOUT
            setGpsError("Tempo esgotado ao buscar localização. Tente novamente ou busque pelo nome.");
            break;
          default:
            setGpsError("Falha ao obter localização GPS. Você pode pesquisar o município.");
        }
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 60000,
      }
    );
  };

  if (!isOpen) return null;

  return (
    <div
      className={cn(
        "fixed inset-0 z-50 flex bg-background/80 backdrop-blur-xs",
        isBottomSheet
          ? "items-end justify-center p-0"
          : "items-center justify-center p-3 sm:p-4"
      )}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-localidade-title"
      data-presentation={layoutProfile.sheetPresentation}
      ref={modalRef}
      onClick={(e) => {
        if (e.target === modalRef.current) onClose();
      }}
    >
      <div
        className={cn(
          "relative w-full max-w-lg border border-border bg-card text-card-foreground shadow-lg flex flex-col overflow-hidden",
          isBottomSheet
            ? "rounded-t-md border-b-0 max-h-[88dvh] safe-area-pb"
            : "rounded-sm max-h-[85vh]"
        )}
      >
        {/* Indicador de Arraste Nativo (Bottom Sheet Handle) para Mobile */}
        {isBottomSheet && (
          <div className="pt-2 pb-0.5 flex justify-center" aria-hidden="true">
            <div className="w-10 h-1 rounded-full bg-muted-foreground/30" />
          </div>
        )}

        {/* Cabeçalho do Diálogo */}
        <div className="flex items-center justify-between p-3.5 border-b border-border/80">
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-primary" />
            <h2 id="modal-localidade-title" className="text-sm font-semibold">
              Selecionar Localidade
            </h2>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 rounded-sm"
            onClick={onClose}
            aria-label="Fechar diálogo de seleção"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* Conteúdo com Busca e Ações */}
        <div className="p-3.5 space-y-3 flex-1 overflow-y-auto">
          {/* Botão de Localização GPS Consentida */}
          <div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="w-full justify-center gap-2 min-h-[42px] sm:min-h-[36px] text-xs font-medium border-primary/30 hover:bg-primary/5 active:bg-primary/10"
              onClick={handleUseGps}
              disabled={isGpsLoading}
              id="btn-usar-gps"
            >
              {isGpsLoading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
                  <span>Obtendo coordenadas GPS...</span>
                </>
              ) : (
                <>
                  <Crosshair className="w-3.5 h-3.5 text-primary" />
                  <span>Usar minha localização atual (GPS)</span>
                </>
              )}
            </Button>
            <p className="text-[10px] text-muted-foreground mt-1 text-center">
              Requer consentimento explícito. Não monitora sua posição continuamente.
            </p>
          </div>

          {/* Mensagem de Erro GPS */}
          {gpsError && (
            <div
              className="p-2.5 rounded-sm border border-destructive/30 bg-destructive/5 text-destructive text-xs flex items-start gap-2"
              role="alert"
            >
              <AlertCircle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
              <span>{gpsError}</span>
            </div>
          )}

          <div className="relative flex items-center my-1">
            <div className="flex-grow border-t border-border/60" />
            <span className="flex-shrink mx-2 text-[10px] uppercase tracking-wider text-muted-foreground">
              Ou pesquise pelo município
            </span>
            <div className="flex-grow border-t border-border/60" />
          </div>

          {/* Filtros: Campo de Busca e Seletor de UF */}
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                ref={inputRef}
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Ex: Londrina, Sorriso, Ribeirão..."
                className="pl-8 text-xs h-10 sm:h-8 rounded-sm"
                aria-label="Pesquisar município"
                id="input-busca-municipio"
              />
            </div>

            <select
              value={selectedUf}
              onChange={(e) => setSelectedUf(e.target.value)}
              className="h-10 sm:h-8 rounded-sm border border-border bg-background px-2 text-xs text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              aria-label="Filtrar por estado (UF)"
              id="select-filtro-uf"
            >
              {UFS_BRASIL.map((uf) => (
                <option key={uf} value={uf}>
                  {uf === "TODAS" ? "Todas UFs" : uf}
                </option>
              ))}
            </select>
          </div>

          {/* Lista de Resultados e Estados de Busca */}
          <div className="space-y-1.5 min-h-[160px] max-h-[260px] overflow-y-auto pr-1">
            {searchStatus === "CARREGANDO" ? (
              <div
                className="flex flex-col items-center justify-center py-8 text-muted-foreground gap-2"
                id="estado-carregando"
              >
                <Loader2 className="w-5 h-5 animate-spin text-primary" />
                <span className="text-xs">Consultando catálogo oficial do IBGE...</span>
              </div>
            ) : searchStatus === "SUCESSO" && itens.length > 0 ? (
              <ul className="divide-y divide-border/40" role="listbox" id="lista-municipios">
                {itens.map((item) => {
                  const isSelected =
                    localidade?.tipoOrigem === "CENTROIDE_IBGE" &&
                    localidade.codigoIbge === item.codigoIbge;

                  return (
                    <li key={item.codigoIbge}>
                      <button
                        type="button"
                        onClick={() => handleSelectMunicipio(item)}
                        className={`w-full flex items-center justify-between p-2.5 sm:p-2 min-h-[44px] sm:min-h-0 text-left rounded-sm text-xs hover:bg-accent hover:text-accent-foreground active:bg-accent/80 transition-colors cursor-pointer ${
                          isSelected ? "bg-accent/60 font-medium" : ""
                        }`}
                        role="option"
                        aria-selected={isSelected}
                      >
                        <div className="flex items-center gap-2">
                          <MapPin className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                          <div>
                            <span className="font-medium text-foreground">{item.nome}</span>
                            <span className="text-[11px] text-muted-foreground ml-1.5">
                              {item.estadoNome} ({item.uf})
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center gap-1.5">
                          {item.capital && (
                            <Badge variant="outline" className="text-[9px] px-1 py-0">
                              Capital
                            </Badge>
                          )}
                          <Badge variant="secondary" className="text-[10px] px-1.5 py-0 font-mono">
                            {item.uf}
                          </Badge>
                          {isSelected && <Check className="w-3.5 h-3.5 text-primary" />}
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ul>
            ) : searchStatus === "VAZIO" ? (
              <div
                className="text-center py-7 px-3 text-xs text-muted-foreground space-y-1.5"
                id="estado-vazio"
              >
                <Search className="w-6 h-6 mx-auto text-muted-foreground/50 mb-1" />
                <p className="font-medium text-foreground">Nenhum município encontrado</p>
                <p className="text-[11px] text-muted-foreground">
                  {statusMessage || `Nenhum resultado corresponde à busca "${searchTerm.trim()}".`}
                </p>
                <p className="text-[10px] text-muted-foreground/80">
                  Dica: verifique a grafia do nome ou selecione outro estado no filtro de UF.
                </p>
              </div>
            ) : searchStatus === "ERRO_CATALOGO" ? (
              <div
                className="p-3 rounded-sm border border-amber-500/30 bg-amber-500/5 text-amber-950 dark:text-amber-200 text-xs space-y-1"
                id="estado-erro-catalogo"
                role="alert"
              >
                <div className="flex items-center gap-1.5 font-medium text-amber-900 dark:text-amber-100">
                  <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0" />
                  <span>Catálogo oficial temporariamente indisponível</span>
                </div>
                <p className="text-[11px] text-muted-foreground dark:text-amber-300/80">
                  A base de dados do IBGE está indisponível no servidor no momento. Você pode utilizar a sua localização GPS consentida acima.
                </p>
              </div>
            ) : searchStatus === "ERRO_COMUNICACAO" ? (
              <div
                className="p-3 rounded-sm border border-destructive/30 bg-destructive/5 text-destructive text-xs space-y-1"
                id="estado-erro-comunicacao"
                role="alert"
              >
                <div className="flex items-center gap-1.5 font-medium">
                  <AlertCircle className="w-4 h-4 text-destructive flex-shrink-0" />
                  <span>Falha na comunicação com a API</span>
                </div>
                <p className="text-[11px] text-muted-foreground">
                  {statusMessage || "Não foi possível conectar ao serviço de municípios. Tente novamente."}
                </p>
              </div>
            ) : searchStatus === "ERRO_PARAMETROS" ? (
              <div
                className="p-3 rounded-sm border border-border bg-muted/30 text-xs space-y-1"
                id="estado-erro-parametros"
                role="alert"
              >
                <div className="flex items-center gap-1.5 font-medium text-foreground">
                  <AlertCircle className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                  <span>Critérios de busca incompletos</span>
                </div>
                <p className="text-[11px] text-muted-foreground">
                  {statusMessage || "Informe ao menos 2 caracteres do município ou selecione uma UF."}
                </p>
              </div>
            ) : (
              <div className="text-center py-8 text-xs text-muted-foreground" id="estado-inicial">
                <MapPin className="w-6 h-6 mx-auto mb-1.5 text-muted-foreground/50" />
                <p className="font-medium text-foreground">Pesquise o nome da sua cidade</p>
                <p className="text-[10px] mt-0.5 text-muted-foreground/80">
                  Base territorial oficial com 5.571 municípios homologados pelo IBGE.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Rodapé Informativo */}
        <div className="p-2.5 px-3.5 border-t border-border/80 bg-muted/20 text-[10px] text-muted-foreground flex items-center justify-between">
          <span>Fonte: IBGE (Sedes Municipais / SIRGAS 2000)</span>
          <Button variant="ghost" size="sm" className="h-7 text-[11px] px-2.5" onClick={onClose}>
            Fechar
          </Button>
        </div>
      </div>
    </div>
  );
}
