// hooks/index.ts
// Exportação centralizada de hooks customizados

export { usePermission } from "./use-permission";
export { useIsMobile as useMobile } from "./use-mobile";
export { useHasModule } from "./use-has-module";
export { useTeam } from "./use-team";
export { useRoles } from "./use-roles";
export { useAdmins } from "./use-admins";
export { useIAFeedback } from "./ia/use-ia-feedback";
export { useIATimer } from "./ia/use-ia-timer";
export { useIAUserProfile } from "./ia/use-ia-user-profile";
export { useIAExplanation } from "./ia/use-ia-explanation";
export { useIAFriction } from "./ia/use-ia-friction";
export { useIAProgresso } from "./ia/use-ia-progresso";
export { useIAGrowthCTA, useIAGrowthTrack, useIAGrowthTrackClick } from "./ia/use-ia-growth-cta";
export type { IAGrowthCTAResponse } from "./ia/use-ia-growth-cta";
export {
  useIAGrowthAssistenteComercialContexto,
  useIAGrowthAssistenteComercialMensagem,
} from "./ia/use-ia-growth-assistente-comercial";
export type {
  IAGrowthAssistenteContextoResponse,
  IAGrowthAssistenteMensagemRequest,
  IAGrowthAssistenteMensagemResponse,
} from "./ia/use-ia-growth-assistente-comercial";
export { 
  useIAGrowthExperimentos, 
  useIAGrowthExperimentoResultado, 
  useIAGrowthCriarExperimento, 
  useIAGrowthFinalizarExperimento 
} from "./ia/use-ia-growth-experimentos";
export type { 
  IAGrowthExperimento, 
  IAGrowthExperimentoVariante, 
  IAGrowthExperimentoResultado 
} from "./ia/use-ia-growth-experimentos";
export { useIAGrowthMetricas } from "./ia/use-ia-growth-metricas";
export type { IAGrowthMetricasResponse, IAGrowthMetricaContexto } from "./ia/use-ia-growth-metricas";
export { useIAGrowthConfig, useIAGrowthConfigUpdate, useIAGrowthConfigReverter } from "./ia/use-ia-growth-config";
export type { IAGrowthConfigItem } from "./ia/use-ia-growth-config";
export { useIAGrowthHistorico } from "./ia/use-ia-growth-historico";
export type { IAGrowthHistoricoItem } from "./ia/use-ia-growth-historico";
export { useIAGrowthSugestoes, useIAGrowthSugestaoAplicar, useIAGrowthSugestaoIgnorar } from "./ia/use-ia-growth-sugestoes";
export type { IAGrowthSugestao, IAGrowthSugestoesResponse } from "./ia/use-ia-growth-sugestoes";
export { useIAGrowthSugestoesDesempenho } from "./ia/use-ia-growth-desempenho";
export type { IAGrowthSugestoesDesempenhoResponse, IAGrowthSugestaoDesempenho } from "./ia/use-ia-growth-desempenho";
export { useIAGrowthPersonasPerformance } from "./ia/use-ia-growth-personas-performance";
export type { IAGrowthPersonasPerformanceResponse, IAGrowthPersonaPerformance } from "./ia/use-ia-growth-personas-performance";
export { useIAGrowthChurnPerformance } from "./ia/use-ia-growth-churn-performance";
export type { IAGrowthChurnDashboardResponse, IAGrowthChurnConversaoItem, IAGrowthChurnNivelItem } from "./ia/use-ia-growth-churn-performance";
export { useIAGrowthOportunidades } from "./ia/use-ia-growth-oportunidades";
export type { IAGrowthOportunidadeItem, IAGrowthOportunidadesResponse } from "./ia/use-ia-growth-oportunidades";
export { useIAGrowthAutopilotStatus } from "./ia/use-ia-growth-autopilot-status";
export type { IAGrowthAutopilotAcaoItem, IAGrowthAutopilotStatusResponse } from "./ia/use-ia-growth-autopilot-status";
export {
  useIAGrowthIncentivos,
  useIAGrowthIncentivoAceitar,
  useIAGrowthIncentivoRecusar,
  useIAGrowthIncentivosPendentes,
  useIAGrowthIncentivoAprovar,
  useIAGrowthIncentivoReprovar,
} from "./ia/use-ia-growth-incentivos";
export type {
  IAGrowthIncentivoItem,
  IAGrowthIncentivosResponse,
  IAGrowthIncentivoActionResponse,
  IAGrowthIncentivosAprovacaoResponse,
  IAGrowthTipoIncentivo,
  IAGrowthOrigemIncentivo,
  IAGrowthStatusIncentivo,
} from "./ia/use-ia-growth-incentivos";
export { useIAGrowthOfertasPerformance } from "./ia/use-ia-growth-ofertas-performance";
export type { IAGrowthOfertasPerformanceResponse, IAGrowthOfertaPerformanceItem } from "./ia/use-ia-growth-ofertas-performance";
export { useIAGrowthROI } from "./ia/use-ia-growth-roi";
export type { IAGrowthROIResponse, IAGrowthROIRankingItem } from "./ia/use-ia-growth-roi";
export { useIAGrowthLearningWeights, useIAGrowthLearningRecalcular } from "./ia/use-ia-growth-learning";
export type { IAGrowthLearningWeightsResponse, IAGrowthLearningWeightItem, IAGrowthLearningRecalcularResponse } from "./ia/use-ia-growth-learning";
export { useIAGrowthEngineConfig, useIAGrowthEngineConfigUpdate } from "./ia/use-ia-growth-engine-config";
export type { IAGrowthEngineConfigResponse, IAGrowthEngineConfigUpdatePayload, IAGrowthEngineFeatureItem } from "./ia/use-ia-growth-engine-config";
export {
  useIAGrowthPlanoRecomendado,
  useIAGrowthPlanoRecomendadoMetricas,
  useIAGrowthPlanoRecomendadoClique,
  useIAGrowthPlanoRecomendadoConversao,
} from "./ia/use-ia-growth-plano-recomendado";
export type {
  IAGrowthTipoOferta,
  IAGrowthPlanoRecomendadoResponse,
  IAGrowthPlanoFitItem,
  IAGrowthPlanoMetricasResponse,
  IAGrowthPlanoMetricasItem,
} from "./ia/use-ia-growth-plano-recomendado";
export { useHasTier, usePlanTier, useMaxFazendas, useMaxUsuarios } from "./use-has-tier";
export {
  useEstoqueSaldo,
  useEstoqueMovimentacoes,
  useEstoque,
  type EstoqueResumoResponse,
  type MovimentacaoSafra,
  type MovimentacaoResponse,
  type MovimentacaoFilters,
} from "./use-estoque";
export {
  useRecommendations,
  useRecommendationMetrics,
  useRecommendationLifecycleAction,
} from "./use-recommendations";
export type {
  RecommendationActionType,
  RecommendationDomain,
  RecommendationDomainMetricsItem,
  RecommendationDomainMetricsResponse,
  RecommendationLifecycleAction,
  RecommendationLifecycleActionInput,
  RecommendationLifecycleMetricsResponse,
  RecommendationListFilters,
  RecommendationListItem,
  RecommendationMetricsBundle,
  RecommendationMetricsFilters,
  RecommendationMetricsSummaryResponse,
  RecommendationPageResponse,
  RecommendationPriority,
  RecommendationRuleMetricsItem,
  RecommendationRuleMetricsResponse,
  RecommendationStatus,
} from "./use-recommendations";
