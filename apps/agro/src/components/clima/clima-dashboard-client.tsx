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
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useLocalidadeClima } from "@/lib/clima/localidade-store";
import {
  fetchClimaPrevisao,
  getPrevisaoCacheKey,
  readSavedPrevisao,
  savePrevisao,
  formatarHorario,
  type ClimaPrevisaoData,
} from "@/lib/clima/previsao";
import { SeletorLocalidadeModal } from "./seletor-localidade-modal";
import { CondicoesAtuaisCard } from "./condicoes-atuais-card";
import { PrevisaoHoraria } from "./previsao-horaria";
import { PrevisaoDiaria } from "./previsao-diaria";
import { AvisoAgronomicoCard } from "./aviso-agronomico-card";
import { ClimaDashboardSkeleton } from "./clima-dashboard-skeleton";

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

  // Estados de dados meteorológicos
  const [previsao, setPrevisao] = React.useState<ClimaPrevisaoData | null>(null);
  const [cacheSalvoEm, setCacheSalvoEm] = React.useState<string | undefined>(undefined);
  const [isRefreshing, setIsRefreshing] = React.useState(false);
  const [viewStatus, setViewStatus] = React.useState<DashboardViewStatus>("NENHUMA_LOCALIDADE");
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  const activeRequestIdRef = React.useRef(0);

  // Função principal de carregamento de previsão
  const carregarPrevisao = React.useCallback(
    async (lat: number, lon: number, locNome: string, forceRefresh: boolean = false) => {
      const currentRequestId = ++activeRequestIdRef.current;
      const cacheKey = getPrevisaoCacheKey(lat, lon);

      // 1. Tenta recuperar cache local imediatamente
      let cachedData: ClimaPrevisaoData | null = null;
      let cachedSalvoEm: string | undefined = undefined;

      if (typeof window !== "undefined") {
        const envelope = readSavedPrevisao(window.localStorage, cacheKey);
        if (envelope && envelope.dados) {
          cachedData = envelope.dados;
          cachedSalvoEm = envelope.salvoEmIso;
        }
      }

      // Se temos cache local e não é refresh forçado, renderiza otimisticamente
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

      // 2. Consulta a API remota via AbortController
      const controller = new AbortController();

      try {
        const resultado = await fetchClimaPrevisao(lat, lon, controller.signal);

        // Se uma nova localidade foi selecionada enquanto a requisição estava em voo, descarta
        if (currentRequestId !== activeRequestIdRef.current) return;

        if (resultado.ok) {
          setPrevisao(resultado.dados);
          setErrorMessage(null);

          // Salva no cache local
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
            console.info(
              "[Clima] Provedor meteorológico upstream requer licença ou chave ativa:",
              resultado.detalhe || resultado.mensagem
            );
            setViewStatus("PROVEDOR_NAO_LICENCIADO");
            setErrorMessage(null);
          } else if (resultado.status === "LIMITE_EXCEDIDO") {
            console.warn("[Clima] Limite de requisições excedido:", resultado.mensagem);
            setViewStatus("LIMITE_EXCEDIDO");
          } else {
            console.error("[Clima] Erro no serviço de clima:", resultado.mensagem);
            setViewStatus("ERRO_SERVIDOR");
          }
        }
      } catch (err: unknown) {
        console.error("[Clima] Exceção inesperada ao consultar previsão:", err);
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

  // Dispara busca quando localidade ativa mudar
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

  // Listener de reconexão online
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
    <div className="space-y-5">
      {/* Diálogo Modal de Seleção de Município */}
      <SeletorLocalidadeModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />

      {/* Cabeçalho da Seção de Clima */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg sm:text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
              <CloudSun className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              Previsão do Tempo
            </h1>
            <Badge variant="outline" className="text-[10px]">Agrometeorologia</Badge>
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
            className="text-xs gap-1.5 cursor-pointer rounded-sm"
            onClick={() => setIsModalOpen(true)}
            id="btn-abrir-seletor-localidade"
          >
            {localidade?.tipoOrigem === "GPS" ? (
              <Crosshair className="w-3.5 h-3.5 text-primary" />
            ) : (
              <MapPin className="w-3.5 h-3.5 text-primary" />
            )}
            <span>{localidade ? "Alterar Município" : "Selecionar Município"}</span>
          </Button>

          {localidade && (
            <Button
              variant="ghost"
              size="sm"
              className="text-xs text-muted-foreground hover:text-destructive h-8 px-2 rounded-sm"
              onClick={clearLocalidade}
              title="Limpar localidade salva"
              aria-label="Limpar localidade selecionada"
              id="btn-limpar-localidade"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </Button>
          )}
        </div>
      </div>

      {/* Card da Localidade Selecionada */}
      {isLoaded && localidade && (
        <div
          className="p-3.5 rounded-sm border border-primary/20 bg-primary/5 text-xs text-foreground flex flex-col sm:flex-row sm:items-center justify-between gap-3"
          id="card-localidade-ativa"
        >
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              {localidade.tipoOrigem === "GPS" ? (
                <div className="flex items-center gap-1.5 font-semibold text-sm text-foreground">
                  <Crosshair className="w-4 h-4 text-primary shrink-0" />
                  <h2 className="font-semibold text-sm text-foreground inline">Localização Atual (GPS)</h2>
                </div>
              ) : (
                <div className="flex items-center gap-1.5 font-semibold text-sm text-foreground">
                  <MapPin className="w-4 h-4 text-primary shrink-0" />
                  <span>
                    {localidade.nome}
                    {localidade.uf ? ` — ${localidade.uf}` : ""}
                  </span>
                </div>
              )}
              <Badge variant="secondary" className="text-[10px] px-1.5 font-normal">
                {localidade.tipoOrigem === "GPS"
                  ? "Localização GPS (Consentida)"
                  : "Centroide Municipal Oficial (IBGE)"}
              </Badge>
              {localidade.codigoIbge && (
                <span className="text-[10px] text-muted-foreground font-mono">
                  IBGE: {localidade.codigoIbge}
                </span>
              )}
            </div>
            <p className="text-[11px] text-muted-foreground font-mono">
              Coordenadas: {localidade.latitude.toFixed(4)}°, {localidade.longitude.toFixed(4)}° • Fuso: {localidade.fusoHorario}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs bg-background cursor-pointer"
              onClick={() => setIsModalOpen(true)}
              id="btn-trocar-localidade-card"
            >
              Trocar
            </Button>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* GESTÃO DOS ESTADOS VISUAIS (1 a 9) */}
      {/* ========================================================================= */}

      {/* ESTADO 1: NENHUMA LOCALIDADE SELECIONADA */}
      {viewStatus === "NENHUMA_LOCALIDADE" && (
        <div
          className="p-4 rounded-sm border border-amber-500/30 bg-amber-500/5 text-xs text-amber-950 dark:text-amber-200 flex items-start gap-3"
          id="estado-nenhuma-localidade"
        >
          <MapPin className="w-5 h-5 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
          <div className="space-y-1.5 flex-1">
            <p className="font-semibold text-sm text-foreground">Nenhum município selecionado</p>
            <p className="text-xs text-muted-foreground dark:text-amber-300/80">
              Para acompanhar a temperatura, umidade e previsão de chuvas da sua lavoura, selecione uma localidade na base oficial do IBGE ou utilize as coordenadas do seu dispositivo GPS sob consentimento.
            </p>
            <div className="pt-1">
              <Button
                variant="outline"
                size="sm"
                className="h-8 text-xs bg-background cursor-pointer"
                onClick={() => setIsModalOpen(true)}
                id="btn-escolher-municipio-prompt"
              >
                Escolher município agora
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ESTADO 2: CARREGANDO PREVISÃO (SKELETON SCREEN) */}
      {viewStatus === "CARREGANDO" && <ClimaDashboardSkeleton />}

      {/* ESTADO 5: SEM CONEXÃO COM CACHE LOCAL */}
      {viewStatus === "OFFLINE_COM_CACHE" && (
        <div
          className="p-3.5 rounded-sm border border-amber-500/40 bg-amber-500/10 text-xs text-amber-950 dark:text-amber-200 flex items-start justify-between gap-3"
          id="estado-offline-com-cache"
          role="status"
        >
          <div className="flex items-start gap-2.5">
            <WifiOff className="w-4 h-4 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold text-xs">Modo Offline Ativo — Exibindo Cache Local</p>
              <p className="text-[11px] text-muted-foreground dark:text-amber-300/80">
                Você está sem conexão ou o servidor não respondeu. Exibindo os últimos dados meteorológicos salvos localmente
                {cacheSalvoEm ? ` em ${formatarHorario(cacheSalvoEm, localidade?.fusoHorario)}` : ""}.
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs bg-background shrink-0"
            onClick={handleManualRefresh}
            disabled={isRefreshing}
          >
            <RotateCw className={`w-3 h-3 mr-1 ${isRefreshing ? "animate-spin" : ""}`} />
            Reconectar
          </Button>
        </div>
      )}

      {/* ESTADO DE CONTINGÊNCIA: SERVIÇO INDISPONÍVEL COM CACHE LOCAL */}
      {viewStatus === "SERVICO_INDISPONIVEL_COM_CACHE" && (
        <div
          className="p-3.5 rounded-sm border border-amber-500/40 bg-amber-500/10 text-xs text-amber-950 dark:text-amber-200 flex items-start justify-between gap-3"
          id="estado-servico-indisponivel-com-cache"
          role="status"
        >
          <div className="flex items-start gap-2.5">
            <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold text-xs">Atualização meteorológica indisponível</p>
              <p className="text-[11px] text-muted-foreground dark:text-amber-300/80">
                A aplicação continua operando normalmente com os últimos dados salvos
                {cacheSalvoEm ? ` em ${formatarHorario(cacheSalvoEm, localidade?.fusoHorario)}` : ""}.
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs bg-background shrink-0"
            onClick={handleManualRefresh}
            disabled={isRefreshing}
          >
            <RotateCw className={`w-3 h-3 mr-1 ${isRefreshing ? "animate-spin" : ""}`} />
            Tentar novamente
          </Button>
        </div>
      )}

      {/* ESTADO 6: SEM CONEXÃO SEM CACHE */}
      {viewStatus === "OFFLINE_SEM_CACHE" && (
        <div
          className="p-4 rounded-sm border border-destructive/30 bg-destructive/5 text-xs text-destructive flex items-start gap-3"
          id="estado-offline-sem-cache"
          role="alert"
        >
          <WifiOff className="w-5 h-5 text-destructive mt-0.5 shrink-0" />
          <div className="space-y-1.5 flex-1">
            <p className="font-semibold text-sm">Sem conexão com a internet</p>
            <p className="text-xs text-muted-foreground">
              Não foi possível estabelecer contato com a API meteorológica e não há dados salvos previamente em cache para este município. Verifique sua conexão à rede para consultar a previsão.
            </p>
            <div className="pt-1">
              <Button
                variant="outline"
                size="sm"
                className="h-8 text-xs bg-background cursor-pointer"
                onClick={handleManualRefresh}
                disabled={isRefreshing}
              >
                <RotateCw className={`w-3.5 h-3.5 mr-1.5 ${isRefreshing ? "animate-spin" : ""}`} />
                Tentar novamente
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ESTADO 7: PROVEDOR METEOROLÓGICO EM ATUALIZAÇÃO */}
      {viewStatus === "PROVEDOR_NAO_LICENCIADO" && (
        <div
          className="p-4 rounded-sm border border-amber-500/40 bg-amber-500/10 text-xs text-amber-950 dark:text-amber-100 flex items-start gap-3"
          id="estado-provedor-nao-licenciado"
          role="alert"
        >
          <ShieldAlert className="w-5 h-5 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
          <div className="space-y-1.5 flex-1">
            <div className="flex items-center gap-2">
              <p className="font-semibold text-sm text-foreground">
                Serviço Meteorológico em Atualização
              </p>
              <Badge variant="outline" className="text-[9px] border-amber-600 text-amber-700 dark:text-amber-300">
                Em Atualização
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground dark:text-amber-300/80 leading-relaxed">
              {previsao
                ? "A atualização da base meteorológica está indisponível no momento. Os últimos dados salvos continuam visíveis abaixo e os demais recursos seguem operando normalmente."
                : "Estamos atualizando a integração com a base meteorológica oficial para esta localidade. Os demais recursos do DeepFarms Agro continuam operando normalmente."}
            </p>
            <div className="pt-1 flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="h-8 text-xs bg-background cursor-pointer"
                onClick={handleManualRefresh}
                disabled={isRefreshing}
              >
                <RotateCw className={`w-3.5 h-3.5 mr-1.5 ${isRefreshing ? "animate-spin" : ""}`} />
                Verificar novamente
              </Button>
              <Link
                href="/"
                className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "h-8 text-xs")}
              >
                Continuar usando a aplicação
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* ESTADO 8: ERRO TEMPORÁRIO DO SERVIDOR */}
      {viewStatus === "ERRO_SERVIDOR" && (
        <div
          className="p-4 rounded-sm border border-destructive/30 bg-destructive/5 text-xs text-destructive flex items-start gap-3"
          id="estado-erro-servidor"
          role="alert"
        >
          <AlertCircle className="w-5 h-5 text-destructive mt-0.5 shrink-0" />
          <div className="space-y-1.5 flex-1">
            <p className="font-semibold text-sm">Serviço meteorológico temporariamente indisponível</p>
            <p className="text-xs text-muted-foreground">
              {errorMessage || "Ocorreu uma falha na consulta aos dados de clima. Tente novamente em instantes."}
            </p>
            <div className="pt-1">
              <Button
                variant="outline"
                size="sm"
                className="h-8 text-xs bg-background cursor-pointer"
                onClick={handleManualRefresh}
                disabled={isRefreshing}
              >
                <RotateCw className={`w-3.5 h-3.5 mr-1.5 ${isRefreshing ? "animate-spin" : ""}`} />
                Tentar novamente
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ESTADO 9: LIMITE DE REQUISIÇÕES ATINGIDO */}
      {viewStatus === "LIMITE_EXCEDIDO" && (
        <div
          className="p-4 rounded-sm border border-amber-500/30 bg-amber-500/5 text-xs text-amber-950 dark:text-amber-200 flex items-start gap-3"
          id="estado-limite-excedido"
          role="alert"
        >
          <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
          <div className="space-y-1.5 flex-1">
            <p className="font-semibold text-sm text-foreground">Limite de consultas de clima atingido</p>
            <p className="text-xs text-muted-foreground">
              Muitas requisições foram efetuadas recentemente a partir deste endereço IP. Aguarde cerca de 1 minuto antes de atualizar.
            </p>
            <div className="pt-1">
              <Button
                variant="outline"
                size="sm"
                className="h-8 text-xs bg-background cursor-pointer"
                onClick={handleManualRefresh}
                disabled={isRefreshing}
              >
                <RotateCw className={`w-3.5 h-3.5 mr-1.5 ${isRefreshing ? "animate-spin" : ""}`} />
                Atualizar agora
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ESTADO 4: BANNER DE DADOS DESATUALIZADOS (QUANDO DADOS EXISTEM E ESTÃO EXPIRADOS OU MARCADOS) */}
      {previsao && (viewStatus === "DESATUALIZADO" || previsao.desatualizado || (previsao.validoAteIso && Date.parse(previsao.validoAteIso) < Date.now())) && (
        <div
          className="p-3 rounded-sm border border-amber-500/40 bg-amber-500/10 text-xs text-amber-950 dark:text-amber-200 flex items-center justify-between gap-3"
          id="banner-dados-desatualizados"
        >
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
            <span>
              Previsão desatualizada. Validade regular expirou em {formatarHorario(previsao.validoAteIso, previsao.fusoHorario)}.
            </span>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs bg-background shrink-0"
            onClick={handleManualRefresh}
            disabled={isRefreshing}
          >
            <RotateCw className={`w-3 h-3 mr-1 ${isRefreshing ? "animate-spin" : ""}`} />
            Atualizar
          </Button>
        </div>
      )}

      {/* ========================================================================= */}
      {/* RENDERIZAÇÃO DO DASHBOARD COMPLETO (ESTADOS 3, 4 OU 5) */}
      {/* ========================================================================= */}
      {previsao && localidade && (viewStatus === "SUCESSO" || viewStatus === "DESATUALIZADO" || viewStatus === "OFFLINE_COM_CACHE" || viewStatus === "SERVICO_INDISPONIVEL_COM_CACHE" || viewStatus === "PROVEDOR_NAO_LICENCIADO") && (
        <div className="space-y-5" id="dashboard-meteorologico-ativo">
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
