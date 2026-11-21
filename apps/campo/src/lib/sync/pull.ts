import { db, type CampoEventoOffline, type CachedItemRequisicao, type CachedRequisicao, type LocalTask, type TaskModule } from "@/lib/db";
import { useSessionStore } from "@/lib/stores/session-store";
import { cacheCampoBrandAssets } from "@/lib/campo-assets";

const API_BASE = "/api/v1";

interface SyncPullPayload {
  safras?: Array<{
    id: string;
    ano_safra: string;
    cultura?: string | null;
    cultura_id?: string | null;
    cultura_nome?: string | null;
    cultura_source?: string | null;
    status: string;
  }>;
  fazendas?: Array<{
    id: string;
    nome: string;
    municipio?: string;
    uf?: string;
    logo_url?: string | null;
  }>;
  talhoes?: Array<{
    id: string;
    nome: string;
    unidade_produtiva_id: string;
    area_ha?: number | null;
    tipo: string;
  }>;
  lotes?: Array<{
    id: string;
    identificacao: string;
    especie: string;
    quantidade_cabecas: number;
    unidade_produtiva_id: string;
    modo_gestao?: string;
    peso_medio_kg?: number;
    area_id?: string | null;
  }>;
  animais?: Array<{
    id: string;
    unidade_produtiva_id: string;
    lote_id?: string | null;
    numero_brinco?: string | null;
    numero_sisbov?: string | null;
    nome?: string | null;
    sexo?: string | null;
    categoria?: string | null;
    status?: string | null;
    especie?: string | null;
    dados_extras?: Record<string, unknown> | null;
    updated_at?: string;
  }>;
  insumos?: Array<{
    id: string;
    nome: string;
    tipo: string;
    unidade_medida?: string | null;
  }>;
  tarefas_pendentes?: Array<{
    id: string;
    client_id?: string | null;
    dispositivo_id?: string | null;
    type: string;
    module: string;
    status?: string;
    origem?: string;
    status_execucao?: string;
    titulo?: string | null;
    data_programada?: string | null;
    prioridade?: string;
    operador_id?: string | null;
    dados?: Record<string, unknown>;
    unidade_produtiva_id?: string | null;
    area_rural_id?: string | null;
    lote_id?: string | null;
    client_created_at?: string | null;
    client_updated_at?: string | null;
  }>;
  eventos_caderno_oficiais?: Array<{
    server_id: string;
    local_id?: string | null;
    device_id?: string | null;
    safra_id: string;
    talhao_id: string;
    tipo: string;
    tipo_evento?: string | null;
    descricao: string;
    data_registro: string;
    status_evento: string;
    documental_status: string;
    versao_vigente: boolean;
    retificado: boolean;
    retificador: boolean;
    invalidado: boolean;
    origem_invalidada: boolean;
    motivo_invalidacao_origem?: string | null;
    motivo_retificacao?: string | null;
    retifica_evento_id?: string | null;
    retificado_por_evento_id?: string | null;
    justificativa?: string | null;
    updated_at?: string | null;
    created_at?: string | null;
  }>;
  tombstones?: {
    talhoes?: string[];
    lotes?: string[];
    tarefas?: string[];
    insumos?: string[];
  };
  colaboradores?: Array<{
    id: string;
    nome: string;
    cpf?: string | null;
    cargo?: string | null;
  }>;
  pessoas_operacionais?: Array<{
    pessoa_id: string;
    nome_exibicao: string;
    unidade_produtiva_id: string;
    papeis: string[];
  }>;
  requisicoes_materiais?: Array<{
    id: string;
    numero?: string | null;
    tenant_id: string;
    unidade_produtiva_id: string;
    safra_id?: string | null;
    safra_tarefa_id?: string | null;
    operacao_agricola_id?: string | null;
    responsavel_pessoa_id?: string | null;
    responsavel_autorizado: boolean;
    version: number;
    status: string;
    status_efetivo: string;
    status_conciliacao?: string;
    data_solicitacao: string;
    execucoes?: Array<{ id: string; status: string; data_execucao: string }>;
    itens: Array<{
      id: string;
      produto_id: string;
      produto_nome?: string | null;
      natureza_item?: "CONSUMIVEL" | "RETORNAVEL" | null;
      unidade: string;
      quantidade_aprovada: number;
      quantidade_entregue: number;
      quantidade_recebida: number;
      quantidade_recusada: number;
      quantidade_pendente_conferencia: number;
      quantidade_em_posse: number;
      quantidade_consumida?: number;
      quantidade_devolvida?: number;
      quantidade_perdida?: number;
      quantidade_danificada?: number;
      quantidade_extraviada?: number;
      status_conferencia: string;
      status_conciliacao?: string;
      entregas: Array<{
        id: string;
        quantidade_entregue: number;
        quantidade_recebida: number;
        quantidade_recusada: number;
        quantidade_pendente_conferencia: number;
        quantidade_consumida?: number;
        quantidade_devolvida?: number;
        quantidade_perdida?: number;
        quantidade_danificada?: number;
        quantidade_extraviada?: number;
        quantidade_em_posse?: number;
        status_conciliacao?: string;
        lote_id?: string | null;
        deposito_id?: string | null;
        unidade: string;
        entregue_em: string;
      }>;
    }>;
  }>;
  recomendacoes_climaticas?: Array<{
    unidade_produtiva_id: string;
    tipo_operacao: string;
    status: string;
    severidade: string;
    motivo: string;
    dados_utilizados: Record<string, unknown>;
    data_referencia: string;
    fonte: string;
    validade_horas: number;
  }>;
  recomendacoes_operacionais?: Array<{
    id: string;
    tenant_id: string;
    unidade_produtiva_id: string | null;
    domain: string;
    status: string;
    priority: string;
    source_type: string;
    action_type: string;
    provider_name: string;
    rule_code: string;
    scope_type: string;
    scope_id: string;
    title: string;
    summary: string;
    rationale: string;
    dedupe_key: string;
    source_signal_ids: string[];
    confidence?: number | null;
    action_label?: string | null;
    action_target?: string | null;
    context?: Record<string, unknown> | null;
    created_at: string;
    updated_at: string;
    expires_at?: string | null;
    viewed_at?: string | null;
    accepted_at?: string | null;
    dismissed_at?: string | null;
    postponed_until?: string | null;
    executed_at?: string | null;
    superseded_at?: string | null;
    superseded_by_id?: string | null;
  }>;
  sync_at: string;
}

const TERMINAL_OFFICIAL_STATUSES = new Set(["APROVADO", "REJEITADO", "CONSOLIDADO", "CANCELADO"]);
const CONFLICT_MESSAGE = "Este registro possui divergência entre aparelho e servidor. Revise no sistema.";

function shouldReviewOfficialEvent(
  statusEvento: string,
  documentalStatus: string,
  origemInvalidada: boolean,
  retificado: boolean
): boolean {
  return statusEvento === "REJEITADO" || documentalStatus === "ORIGEM_INVALIDADA" || origemInvalidada || retificado;
}

function buildConflictReason(
  local: CampoEventoOffline,
  serverEvent: NonNullable<SyncPullPayload["eventos_caderno_oficiais"]>[number]
): string | null {
  if (local.server_id && local.server_id !== serverEvent.server_id) {
    return CONFLICT_MESSAGE;
  }

  if (local.server_id && TERMINAL_OFFICIAL_STATUSES.has(serverEvent.status_evento) && local.status_evento !== serverEvent.status_evento) {
    return CONFLICT_MESSAGE;
  }

  if (
    (local.sync_status === "PENDING" || local.sync_status === "SYNCING" || local.sync_status === "ERROR") &&
    TERMINAL_OFFICIAL_STATUSES.has(serverEvent.status_evento) &&
    local.server_id
  ) {
    return CONFLICT_MESSAGE;
  }

  return null;
}

export async function pullSync(): Promise<void> {
  const session = useSessionStore.getState().session;
  if (!session) throw new Error("Sessão não encontrada");

  const params = new URLSearchParams({ device_id: session.device_id });
  if (session.last_sync_at) {
    params.set("last_sync_at", session.last_sync_at);
  }

  const res = await fetch(`${API_BASE}/sync/pull?${params}`, {
    headers: { Authorization: `Bearer ${session.device_token}` },
    cache: "no-store",
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Erro ao sincronizar");
  }

  const data = (await res.json()) as SyncPullPayload;

  // Atualiza caches no IndexedDB em transação
  await db.transaction(
    "rw",
    [
      db.fazendas,
      db.talhoes,
      db.lotes,
      db.animais,
      db.insumos,
      db.safras,
      db.tasks,
      db.sync_queue,
      db.caderno_events,
      db.caderno_server_events,
      db.colaboradores,
      db.recomendacoes_climaticas,
      db.recomendacoes_operacionais,
      db.pessoas_operacionais,
      db.requisicoes,
      db.requisicao_itens,
      db.requisicao_operacoes,
    ],
    async () => {
    // Colaboradores
    if (data.colaboradores) {
      await db.colaboradores.clear();
      if (data.colaboradores.length) {
        await db.colaboradores.bulkPut(data.colaboradores);
      }
    }

    // Pessoas Operacionais (Fase 2C)
    if (data.pessoas_operacionais) {
      await db.pessoas_operacionais.clear();
      if (data.pessoas_operacionais.length) {
        const payload = data.pessoas_operacionais.map((p) => ({
          ...p,
          id: `${p.unidade_produtiva_id}:${p.pessoa_id}`,
          papeis: Array.from(new Set(p.papeis || [])),
        }));
        await db.pessoas_operacionais.bulkPut(payload);
      }
    }

    // Projeção de recebimento: é cache do estado canônico, nunca fonte de
    // verdade. Operações pendentes permanecem na fila e serão reconciliadas
    // pelo ACK/CONFLICT do push.
    if (data.requisicoes_materiais) {
      const now = new Date().toISOString();
      for (const request of data.requisicoes_materiais) {
        const cachedRequest: CachedRequisicao = {
          ...request,
          updated_at: now,
          itens: request.itens.map((item) => ({
            ...item,
            requisicao_id: request.id,
            tenant_id: request.tenant_id,
            updated_at: now,
          })),
        };
        await db.requisicoes.put(cachedRequest);
        const cachedItems: CachedItemRequisicao[] = cachedRequest.itens;
        await db.requisicao_itens.bulkPut(cachedItems);
      }
    }

    // Safras
    if (data.safras) {
      await db.safras.clear();
    }
    if (data.safras?.length) {
      await db.safras.bulkPut(
        data.safras.map((s) => ({
          id: s.id,
          ano_safra: s.ano_safra,
          cultura: s.cultura ?? undefined,
          cultura_id: s.cultura_id ?? undefined,
          cultura_nome: s.cultura_nome ?? undefined,
          cultura_source: s.cultura_source ?? undefined,
          status: s.status,
        }))
      );
    }

    // Fazendas
    if (data.fazendas) {
      await db.fazendas.clear();
    }
    if (data.fazendas?.length) {
      await db.fazendas.bulkPut(data.fazendas);
    }

    // Talhões
    if (data.talhoes) {
      await db.talhoes.clear();
    }
    if (data.talhoes?.length) {
      await db.talhoes.bulkPut(
        data.talhoes.map((t) => ({
          id: t.id,
          nome: t.nome,
          fazenda_id: t.unidade_produtiva_id,
          area_ha: t.area_ha ?? undefined,
          tipo: t.tipo,
        }))
      );
    }

    // Lotes
    if (data.lotes) {
      await db.lotes.clear();
    }
    if (data.lotes?.length) {
      await db.lotes.bulkPut(data.lotes.map((l) => ({ ...l, fazenda_id: l.unidade_produtiva_id })));
    }

    // Animais
    if (data.animais) {
      await db.animais.clear();
    }
    if (data.animais?.length) {
      await db.animais.bulkPut(data.animais);
    }

    // Insumos
    if (data.insumos) {
      await db.insumos.clear();
    }
    if (data.insumos?.length) {
      await db.insumos.bulkPut(
        data.insumos.map((i) => ({
          id: i.id,
          nome: i.nome,
          tipo: i.tipo,
          unidade_medida: i.unidade_medida ?? undefined,
        }))
      );
    }

    // Recomendações Climáticas
    await db.recomendacoes_climaticas.clear();
    if (data.recomendacoes_climaticas?.length) {
      await db.recomendacoes_climaticas.bulkPut(
        data.recomendacoes_climaticas.map((r) => ({
          id: `${r.unidade_produtiva_id}-${r.tipo_operacao}`,
          unidade_produtiva_id: r.unidade_produtiva_id,
          tipo_operacao: r.tipo_operacao,
          status: r.status,
          severidade: r.severidade,
          motivo: r.motivo,
          dados_utilizados: r.dados_utilizados,
          data_referencia: r.data_referencia,
          fonte: r.fonte,
          validade_horas: r.validade_horas,
        }))
      );
    }

    // Recomendações Operacionais
    await db.recomendacoes_operacionais.clear();
    if (data.recomendacoes_operacionais?.length) {
      await db.recomendacoes_operacionais.bulkPut(
        data.recomendacoes_operacionais.map((r) => ({
          ...r,
          source_signal_ids: r.source_signal_ids ?? [],
          confidence: r.confidence ?? null,
          action_label: r.action_label ?? null,
          action_target: r.action_target ?? null,
          context: r.context ?? null,
          expires_at: r.expires_at ?? null,
          viewed_at: r.viewed_at ?? null,
          accepted_at: r.accepted_at ?? null,
          dismissed_at: r.dismissed_at ?? null,
          postponed_until: r.postponed_until ?? null,
          executed_at: r.executed_at ?? null,
          superseded_at: r.superseded_at ?? null,
          superseded_by_id: r.superseded_by_id ?? null,
        }))
      );
    }

    // Tarefas programadas recebidas do servidor
    if (data.tarefas_pendentes?.length) {
      const now = new Date().toISOString();
      const pendingQueueItems = await db.sync_queue
        .where("status")
        .anyOf(["PENDING", "IN_FLIGHT"])
        .filter((item) => item.entity_type === "task")
        .toArray();
      const pendingTaskIds = new Set(pendingQueueItems.map((item) => item.entity_id));
      const mergedTasks: LocalTask[] = [];

      for (const t of data.tarefas_pendentes) {
        const localId = t.client_id ?? String(t.id);
        const currentTask = await db.tasks.get(localId);
        const serverTask: LocalTask = {
          id: localId,
          server_id: String(t.id),
          type: t.type,
          module: (t.module === "pecuaria" ? "pecuaria" : "agricola") as TaskModule,
          fazenda_id: t.unidade_produtiva_id ?? "",
          talhao_id: t.area_rural_id ?? undefined,
          lote_id: t.lote_id ?? undefined,
          dispositivo_id: t.dispositivo_id ?? undefined,
          operador_id: t.operador_id ?? undefined,
          status: (t.status ?? "PENDENTE") as LocalTask["status"],
          origem: (t.origem ?? "MANUAL") as LocalTask["origem"],
          status_execucao: (t.status_execucao ?? "PENDENTE") as LocalTask["status_execucao"],
          titulo: t.titulo ?? undefined,
          data_programada: t.data_programada ?? undefined,
          prioridade: (t.prioridade ?? "NORMAL") as LocalTask["prioridade"],
          dados: t.dados ?? {},
          fotos: currentTask?.fotos ?? [],
          localizacao_status: currentTask?.localizacao_status ?? ("INDISPONIVEL" as LocalTask["localizacao_status"]),
          latitude: currentTask?.latitude,
          longitude: currentTask?.longitude,
          iniciada_em: currentTask?.iniciada_em,
          concluida_em: currentTask?.concluida_em,
          created_at: t.client_created_at ?? now,
          updated_at: t.client_updated_at ?? now,
          synced: true,
          sync_conflict: undefined,
        };

        if (currentTask && pendingTaskIds.has(localId)) {
          mergedTasks.push({
            ...serverTask,
            ...currentTask,
            server_id: String(t.id),
            synced: false,
          });
          continue;
        }

        mergedTasks.push(serverTask);
      }

      await db.tasks.bulkPut(mergedTasks);
    }

    if (data.eventos_caderno_oficiais?.length) {
      await db.caderno_server_events.bulkPut(
        data.eventos_caderno_oficiais.map((evento) => ({
          ...evento,
          local_id: evento.local_id ?? undefined,
        }))
      );

      for (const evento of data.eventos_caderno_oficiais) {
        if (!evento.local_id) continue;
        const local = await db.caderno_events.get(evento.local_id);
        if (!local) continue;
        if (evento.device_id && local.device_id !== evento.device_id) continue;

        const now = evento.updated_at ?? new Date().toISOString();
        const conflictReason = buildConflictReason(local, evento);
        const reviewRequired =
          Boolean(conflictReason) ||
          shouldReviewOfficialEvent(
            evento.status_evento,
            evento.documental_status,
            evento.origem_invalidada,
            evento.retificado
          );

        if (conflictReason) {
          await db.caderno_events.update(evento.local_id, {
            status_evento: evento.status_evento as CampoEventoOffline["status_evento"],
            documental_status: evento.documental_status,
            origem_invalidada: evento.origem_invalidada,
            motivo_invalidacao_origem: evento.motivo_invalidacao_origem ?? null,
            retifica_evento_id: evento.retifica_evento_id ?? null,
            retificado_por_evento_id: evento.retificado_por_evento_id ?? null,
            oficial_justificativa: evento.justificativa ?? null,
            review_required: true,
            sync_status: "CONFLICT",
            conflict_reason: conflictReason,
            reconciled_at: now,
            updated_at: now,
          });
          continue;
        }

        await db.caderno_events.update(evento.local_id, {
          server_id: evento.server_id,
          status_evento: evento.status_evento as CampoEventoOffline["status_evento"],
          documental_status: evento.documental_status,
          origem_invalidada: evento.origem_invalidada,
          motivo_invalidacao_origem: evento.motivo_invalidacao_origem ?? null,
          retifica_evento_id: evento.retifica_evento_id ?? null,
          retificado_por_evento_id: evento.retificado_por_evento_id ?? null,
          oficial_justificativa: evento.justificativa ?? null,
          review_required: reviewRequired,
          sync_status: "SYNCED",
          conflict_reason: null,
          last_sync_error: null,
          reconciled_at: now,
          updated_at: now,
        });
      }
    }

    // Tombstones — remove entidades deletadas no servidor
    const tombstones = data.tombstones ?? {};
    if (tombstones.talhoes?.length) {
      await db.talhoes.bulkDelete(tombstones.talhoes);
    }
    if (tombstones.lotes?.length) {
      await db.lotes.bulkDelete(tombstones.lotes);
    }
    if (tombstones.insumos?.length) {
      await db.insumos.bulkDelete(tombstones.insumos);
    }
    if (tombstones.tarefas?.length) {
      // Marcar tarefas locais como canceladas
      for (const id of tombstones.tarefas) {
        const task = await db.tasks.get(id) ?? await db.tasks.where("server_id").equals(id).first();
        if (task) {
          await db.tasks.update(task.id, { status_execucao: "CANCELADA" });
        }
      }
    }
  });

  // Baixa e persiste avatar/logos em IndexedDB. Falha de uma imagem não pode
  // invalidar o sync dos dados operacionais.
  await cacheCampoBrandAssets(
    session,
    data.fazendas ?? [],
  );

  // Atualiza last_sync_at na sessão
  await useSessionStore.getState().updateLastSync(data.sync_at);
}
