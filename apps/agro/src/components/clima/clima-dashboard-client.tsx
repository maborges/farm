"use client";

import * as React from "react";
import Link from "next/link";
import {
  CloudSun,
  MapPin,
  Crosshair,
  RotateCcw,
  AlertCircle,
  AlertTriangle,
  WifiOff,
  RotateCw,
  Clock,
  ShieldAlert,
  ArrowRight,
} from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useLocalidadeClima } from "@/lib/clima/localidade-store";
import {
  fetchClimaPrevisao,
  getPrevisaoCacheKey,
  readSavedPrevisao,
  savePrevisao,
  formatarHorario,
  type ClimaPrevisaoData,
} from "@/lib/clima/previsao";
import { cn } from "@/lib/utils";
import { AvisoAgronomicoCard } from "./aviso-agronomico-card";
import { ClimaDashboardSkeleton } from "./clima-dashboard-skeleton";
import { CondicoesAtuaisCard } from "./condicoes-atuais-card";
import { PrevisaoDiaria } from "./previsao-diaria";
import { PrevisaoHoraria } from "./previsao-horaria";
import { SeletorLocalidadeModal } from "./seletor-localidade-modal";

export type DashboardViewStatus =
  | "NENHUMA_LOCALIDADE"
  | "CARREGANDO"
  | "SUCESSO"
  | "DESATUALIZADO"
  | "OFFLINE_COM_CACHE"
  | "OFFLINE_SEM_CACHE"
  | "SERVICO_INDISPONIVEL_COM_CACHE"
  | "PROVEDOR_NAO_LICENCIADO"
  | "ERRO_SERVIDOR"
  | "LIMITE_EXCEDIDO";

export function ClimaDashboardClient(): React.ReactElement {
  const { localidade, isLoaded, clearLocalidade } = useLocalidadeClima();
  const [isModalOpen, setIsModalOpen] = React.useState(false);

  const [previsao, setPrevisao] = React.useState<ClimaPrevisaoData | null>(null);
  const [cacheSalvoEm, setCacheSalvoEm] = React.useState<string | undefined>(undefined);
  const [isRefreshing, setIsRefreshing] = React.useState(false);
  const [viewStatus, setViewStatus] = React.useState<DashboardViewStatus>("NENHUMA_LOCALIDADE");
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  const activeRequestIdRef = React.useRef(0);

  const carregarPrevisao = React.useCallback(
    async (lat: number, lon: number, locNome: string, forceRefresh: boolean = false) => {
      const currentRequestId = ++activeRequestIdRef.current;
      const cacheKey = getPrevisaoCacheKey(lat, lon);

      let cachedData: ClimaPrevisaoData | null = null;
      let cachedSalvoEm: string | undefined = undefined;

      if (typeof window !== "undefined") {
        const envelope = readSavedPrevisao(window.localStorage, cacheKey);
        if (envelope && envelope.dados) {
          cachedData = envelope.dados;
          cachedSalvoEm = envelope.salvoEmIso;
        }
      }

      if (cachedData && !forceRefresh) {
        setPrevisao(cachedData);
        setCacheSalvoEm(cachedSalvoEm);
        const isStale = Date.parse(cachedData.validoAteIso) < Date.now();
        setViewStatus(isStale ? "DESATUALIZADO" : "SUCESSO");
      } else if (!cachedData) {
        setViewStatus("CARREGANDO");
      }

      if (forceRefresh) {
        setIsRefreshing(true);
      }

      const controller = new AbortController();

      try {
        const resultado = await fetchClimaPrevisao(lat, lon, controller.signal);

        if (currentRequestId !== activeRequestIdRef.current) return;

        if (resultado.ok) {
          setPrevisao(resultado.dados);
          setErrorMessage(null);

          if (typeof window !== "undefined") {
            savePrevisao(window.localStorage, cacheKey, resultado.dados, locNome);
            setCacheSalvoEm(new Date().toISOString());
          }

          if (resultado.desatualizado) {
            setViewStatus("DESATUALIZADO");
          } else {
            setViewStatus("SUCESSO");
          }
        } else {
          setErrorMessage(resultado.mensagem);

          if (resultado.status === "OFFLINE") {
            if (cachedData) {
              const isStale = Date.parse(cachedData.validoAteIso) < Date.now();
              const dadosAtivos = isStale ? { ...cachedData, desatualizado: true } : cachedData;
              setPrevisao(dadosAtivos);
              setCacheSalvoEm(cachedSalvoEm);
              setViewStatus("OFFLINE_COM_CACHE");
            } else {
              setPrevisao(null);
              setViewStatus("OFFLINE_SEM_CACHE");
            }
          } else if (resultado.httpStatus === 503 && cachedData) {
            const isStale = Date.parse(cachedData.validoAteIso) < Date.now();
            const dadosAtivos = isStale ? { ...cachedData, desatualizado: true } : cachedData;
            setPrevisao(dadosAtivos);
            setCacheSalvoEm(cachedSalvoEm);
            setViewStatus("SERVICO_INDISPONIVEL_COM_CACHE");
          } else if (resultado.status === "PROVEDOR_NAO_LICENCIADO") {
            setViewStatus("PROVEDOR_NAO_LICENCIADO");
            setErrorMessage(null);
          } else if (resultado.status === "LIMITE_EXCEDIDO") {
            setViewStatus("LIMITE_EXCEDIDO");
          } else {
            setViewStatus("ERRO_SERVIDOR");
          }
        }
      } catch {
        if (currentRequestId === activeRequestIdRef.current) {
          if (cachedData) {
            const isStale = Date.parse(cachedData.validoAteIso) < Date.now();
            const dadosAtivos = isStale ? { ...cachedData, desatualizado: true } : cachedData;
            setPrevisao(dadosAtivos);
            setCacheSalvoEm(cachedSalvoEm);
            setViewStatus("OFFLINE_COM_CACHE");
          } else {
            setPrevisao(null);
            setViewStatus("OFFLINE_SEM_CACHE");
          }
          setErrorMessage("Falha de conexão com a API de clima.");
        }
      } finally {
        if (currentRequestId === activeRequestIdRef.current) {
          setIsRefreshing(false);
        }
      }
    },
    []
  );

  React.useEffect(() => {
    if (!isLoaded) return;

    if (!localidade) {
      setPrevisao(null);
      setViewStatus("NENHUMA_LOCALIDADE");
      setIsRefreshing(false);
      setErrorMessage(null);
      return;
    }

    carregarPrevisao(localidade.latitude, localidade.longitude, localidade.nome, false);
  }, [localidade, isLoaded, carregarPrevisao]);

  React.useEffect(() => {
    const handleOnline = () => {
      if (localidade && (viewStatus === "OFFLINE_COM_CACHE" || viewStatus === "OFFLINE_SEM_CACHE")) {
        carregarPrevisao(localidade.latitude, localidade.longitude, localidade.nome, true);
      }
    };

    window.addEventListener("online", handleOnline);
    return () => window.removeEventListener("online", handleOnline);
  }, [localidade, viewStatus, carregarPrevisao]);

  const handleManualRefresh = () => {
    if (!localidade) return;
    carregarPrevisao(localidade.latitude, localidade.longitude, localidade.nome, true);
  };

  return (
    <div className="flex flex-col gap-4 sm:gap-5">
      {/* Diálogo Modal de Seleção de Município */}
      <SeletorLocalidadeModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />

      {/* Cabeçalho da Seção de Clima (no mobile só aparece botão se nenhuma cidade estiver ativa) */}
      <div
        className={cn(
          "flex-col sm:flex-row sm:items-center justify-between gap-3",
          localidade ? "hidden md:flex" : "flex"
        )}
      >
        <div className="hidden md:block">
          <div className="flex items-center gap-2">
            <h1 className="text-lg sm:text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
              <CloudSun className="size-5 text-blue-600 dark:text-blue-400" />
              Previsão do Tempo
            </h1>
            <Badge variant="outline">Agrometeorologia</Badge>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            Condições atuais, horizonte horário de 24h para pulverização e tendência semanal de safra.
          </p>
        </div>

        {/* Botão de Seleção/Troca de Localidade */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsModalOpen(true)}
            id="btn-abrir-seletor-localidade"
            className="w-full sm:w-auto justify-center"
          >
            {localidade?.tipoOrigem === "GPS" ? (
              <Crosshair className="size-3.5 text-primary" />
            ) : (
              <MapPin className="size-3.5 text-primary" />
            )}
            <span>{localidade ? "Alterar Município" : "Selecionar Município"}</span>
          </Button>
        </div>
      </div>

      <Separator className="hidden md:block" />

      {/* Card da Localidade Selecionada */}
      {isLoaded && localidade && (
        <Card
          variant="muted"
          size="sm"
          id="card-localidade-ativa"
        >
          <CardContent className="flex flex-row items-center justify-between gap-2.5 sm:gap-3">
            <div className="flex flex-col gap-1 min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                {localidade.tipoOrigem === "GPS" ? (
                  <div className="flex items-center gap-1.5 font-semibold text-sm text-foreground min-w-0">
                    <Crosshair className="size-4 text-primary shrink-0" />
                    <h2 className="font-semibold text-sm text-foreground inline truncate">Localização Atual (GPS)</h2>
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5 font-semibold text-sm text-foreground min-w-0">
                    <MapPin className="size-4 text-primary shrink-0" />
                    <span className="truncate">
                      {localidade.nome}
                      {localidade.uf ? ` — ${localidade.uf}` : ""}
                    </span>
                  </div>
                )}
                <Badge variant="secondary" className="hidden sm:inline-flex">
                  {localidade.tipoOrigem === "GPS"
                    ? "Localização GPS (Consentida)"
                    : "Centroide Municipal Oficial (IBGE)"}
                </Badge>
                {localidade.codigoIbge && (
                  <span className="hidden sm:inline text-[10px] text-muted-foreground font-mono">
                    IBGE: {localidade.codigoIbge}
                  </span>
                )}
              </div>
              <p className="hidden sm:block text-[11px] text-muted-foreground font-mono">
                Coordenadas: {localidade.latitude.toFixed(4)}°, {localidade.longitude.toFixed(4)}° • Fuso: {localidade.fusoHorario}
              </p>
            </div>
            <div className="flex items-center gap-1.5 shrink-0">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsModalOpen(true)}
                id="btn-trocar-localidade-card"
              >
                Trocar
              </Button>
              <Button
                variant="ghost"
                size="icon-sm"
                className="text-muted-foreground hover:text-destructive"
                onClick={clearLocalidade}
                title="Limpar localidade salva"
                aria-label="Limpar localidade selecionada"
                id="btn-limpar-localidade"
              >
                <RotateCcw className="size-3.5" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ========================================================================= */}
      {/* GESTÃO DOS ESTADOS VISUAIS (1 a 9) */}
      {/* ========================================================================= */}

      {/* ESTADO 1: NENHUMA LOCALIDADE SELECIONADA */}
      {viewStatus === "NENHUMA_LOCALIDADE" && (
        <Alert variant="warning" id="estado-nenhuma-localidade">
          <MapPin className="size-4" />
          <AlertTitle className="text-sm">Nenhum município selecionado</AlertTitle>
          <AlertDescription className="text-xs flex flex-col gap-2">
            <span>
              Para acompanhar a temperatura, umidade e previsão de chuvas da sua lavoura, selecione uma localidade na base oficial do IBGE ou utilize as coordenadas do seu dispositivo GPS sob consentimento.
            </span>
            <div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsModalOpen(true)}
                id="btn-escolher-municipio-prompt"
              >
                Escolher município agora
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

      {/* ESTADO 2: CARREGANDO PREVISÃO (SKELETON SCREEN) */}
      {viewStatus === "CARREGANDO" && <ClimaDashboardSkeleton />}

      {/* ESTADO 5: SEM CONEXÃO COM CACHE LOCAL */}
      {viewStatus === "OFFLINE_COM_CACHE" && (
        <Alert variant="warning" id="estado-offline-com-cache" role="status">
          <WifiOff className="size-4" />
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <AlertTitle className="text-xs">Modo Offline Ativo — Exibindo Cache Local</AlertTitle>
              <AlertDescription className="text-xs">
                Você está sem conexão ou o servidor não respondeu. Exibindo os últimos dados meteorológicos salvos localmente
                {cacheSalvoEm ? ` em ${formatarHorario(cacheSalvoEm, localidade?.fusoHorario)}` : ""}.
              </AlertDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="shrink-0"
              onClick={handleManualRefresh}
              disabled={isRefreshing}
            >
              <RotateCw className={`size-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
              <span>Reconectar</span>
            </Button>
          </div>
        </Alert>
      )}

      {/* ESTADO DE CONTINGÊNCIA: SERVIÇO INDISPONÍVEL COM CACHE LOCAL */}
      {viewStatus === "SERVICO_INDISPONIVEL_COM_CACHE" && (
        <Alert variant="warning" id="estado-servico-indisponivel-com-cache" role="status">
          <AlertTriangle className="size-4" />
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <AlertTitle className="text-xs">Atualização meteorológica indisponível</AlertTitle>
              <AlertDescription className="text-xs">
                A aplicação continua operando normalmente com os últimos dados salvos
                {cacheSalvoEm ? ` em ${formatarHorario(cacheSalvoEm, localidade?.fusoHorario)}` : ""}.
              </AlertDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="shrink-0"
              onClick={handleManualRefresh}
              disabled={isRefreshing}
            >
              <RotateCw className={`size-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
              <span>Tentar novamente</span>
            </Button>
          </div>
        </Alert>
      )}

      {/* ESTADO 6: SEM CONEXÃO SEM CACHE */}
      {viewStatus === "OFFLINE_SEM_CACHE" && (
        <Alert variant="destructive" id="estado-offline-sem-cache">
          <WifiOff className="size-4" />
          <AlertTitle className="text-sm">Sem conexão com a internet</AlertTitle>
          <AlertDescription className="text-xs flex flex-col gap-2">
            <span>
              Não foi possível estabelecer contato com a API meteorológica e não há dados salvos previamente em cache para este município. Verifique sua conexão à rede para consultar a previsão.
            </span>
            <div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleManualRefresh}
                disabled={isRefreshing}
              >
                <RotateCw className={`size-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
                <span>Tentar novamente</span>
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

      {/* ESTADO 7: PROVEDOR METEOROLÓGICO EM ATUALIZAÇÃO */}
      {viewStatus === "PROVEDOR_NAO_LICENCIADO" && (
        <Alert variant="warning" id="estado-provedor-nao-licenciado">
          <ShieldAlert className="size-4" />
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center gap-2">
              <p className="font-semibold text-sm text-foreground">
                Serviço Meteorológico em Atualização
              </p>
              <Badge variant="warning">
                Em Atualização
              </Badge>
            </div>
            <p className="text-xs leading-relaxed">
              {previsao
                ? "A atualização da base meteorológica está indisponível no momento. Os últimos dados salvos continuam visíveis abaixo e os demais recursos seguem operando normalmente."
                : "Estamos atualizando a integração com a base meteorológica oficial para esta localidade. Os demais recursos do DeepFarms Agro continuam operando normalmente."}
            </p>
            <div className="pt-1 flex flex-wrap items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleManualRefresh}
                disabled={isRefreshing}
              >
                <RotateCw className={`size-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
                <span>Verificar novamente</span>
              </Button>
              <Link
                href="/"
                className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}
              >
                <span>Continuar usando a aplicação</span>
                <ArrowRight className="size-3.5" />
              </Link>
            </div>
          </div>
        </Alert>
      )}

      {/* ESTADO 8: ERRO TEMPORÁRIO DO SERVIDOR */}
      {viewStatus === "ERRO_SERVIDOR" && (
        <Alert variant="destructive" id="estado-erro-servidor">
          <AlertCircle className="size-4" />
          <AlertTitle className="text-sm">Serviço meteorológico temporariamente indisponível</AlertTitle>
          <AlertDescription className="text-xs flex flex-col gap-2">
            <span>
              {errorMessage || "Ocorreu uma falha na consulta aos dados de clima. Tente novamente em instantes."}
            </span>
            <div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleManualRefresh}
                disabled={isRefreshing}
              >
                <RotateCw className={`size-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
                <span>Tentar novamente</span>
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

      {/* ESTADO 9: LIMITE DE REQUISIÇÕES ATINGIDO */}
      {viewStatus === "LIMITE_EXCEDIDO" && (
        <Alert variant="warning" id="estado-limite-excedido">
          <AlertTriangle className="size-4" />
          <AlertTitle className="text-sm">Limite de consultas de clima atingido</AlertTitle>
          <AlertDescription className="text-xs flex flex-col gap-2">
            <span>
              Muitas requisições foram efetuadas recentemente a partir deste endereço IP. Aguarde cerca de 1 minuto antes de atualizar.
            </span>
            <div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleManualRefresh}
                disabled={isRefreshing}
              >
                <RotateCw className={`size-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
                <span>Atualizar agora</span>
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

      {/* ESTADO 4: BANNER DE DADOS DESATUALIZADOS */}
      {previsao && (viewStatus === "DESATUALIZADO" || previsao.desatualizado || (previsao.validoAteIso && Date.parse(previsao.validoAteIso) < Date.now())) && (
        <Alert variant="warning" id="banner-dados-desatualizados">
          <Clock className="size-4" />
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <AlertDescription className="text-xs">
              Previsão desatualizada. Validade regular expirou em {formatarHorario(previsao.validoAteIso, previsao.fusoHorario)}.
            </AlertDescription>
            <Button
              variant="outline"
              size="sm"
              className="shrink-0"
              onClick={handleManualRefresh}
              disabled={isRefreshing}
            >
              <RotateCw className={`size-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
              <span>Atualizar</span>
            </Button>
          </div>
        </Alert>
      )}

      {/* ========================================================================= */}
      {/* RENDERIZAÇÃO DO DASHBOARD COMPLETO (ESTADOS 3, 4 OU 5) */}
      {/* ========================================================================= */}
      {previsao && localidade && (viewStatus === "SUCESSO" || viewStatus === "DESATUALIZADO" || viewStatus === "OFFLINE_COM_CACHE" || viewStatus === "SERVICO_INDISPONIVEL_COM_CACHE" || viewStatus === "PROVEDOR_NAO_LICENCIADO") && (
        <div className="flex flex-col gap-5" id="dashboard-meteorologico-ativo">
          {/* 1. Card de Condições Atuais */}
          <CondicoesAtuaisCard
            dados={previsao}
            localidadeNome={localidade.nome}
            localidadeUf={localidade.uf}
            tipoOrigem={localidade.tipoOrigem}
            isRefreshing={isRefreshing}
            onRefresh={handleManualRefresh}
            isOffline={viewStatus === "OFFLINE_COM_CACHE"}
            isStale={viewStatus === "DESATUALIZADO" || previsao.desatualizado}
            salvoEmIso={cacheSalvoEm}
          />

          {/* 2. Previsão Horária para Pulverização (24 Horas) */}
          <PrevisaoHoraria
            itens={previsao.previsaoHoraria}
            fusoHorario={previsao.fusoHorario}
          />

          {/* 3. Previsão Semanal (7 Dias) */}
          <PrevisaoDiaria
            itens={previsao.previsaoDiaria}
            fusoHorario={previsao.fusoHorario}
          />

          {/* 4. Aviso de Governança Agronômica */}
          <AvisoAgronomicoCard />
        </div>
      )}
    </div>
  );
}
