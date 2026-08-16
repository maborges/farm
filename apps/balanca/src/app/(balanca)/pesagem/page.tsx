"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useLiveQuery } from "dexie-react-hooks";
import { db, getSession, clearSession, type OrdemPendenteLocal } from "@/lib/db";
import { enqueuePesagem } from "@/lib/sync/push";
import { startSyncLoop, runSyncCycle } from "@/lib/sync/trigger";

function gerarNumeroTicketLocal(): string {
  const hoje = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  return `BAL-${hoje}-${crypto.randomUUID().slice(0, 6).toUpperCase()}`;
}

export default function PesagemPage() {
  const router = useRouter();

  // Mesmo gate de mount usado em "/": evita ler Dexie antes de hidratar.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const session = useLiveQuery(getSession);
  const ordens = useLiveQuery(
    () => db.ordens.where("status").anyOf(["PENDENTE", "EM_PESAGEM"]).toArray(),
    [],
  );

  useEffect(() => {
    if (!mounted || session === undefined) return;
    if (!session) router.replace("/");
  }, [mounted, session, router]);

  useEffect(() => {
    const stop = startSyncLoop();
    return stop;
  }, []);

  const [ordemSelecionadaId, setOrdemSelecionadaId] = useState<string | null>(null);
  const ordemSelecionada = useMemo(
    () => ordens?.find((o) => o.id === ordemSelecionadaId) ?? null,
    [ordens, ordemSelecionadaId],
  );

  const pesagensDaOrdem = useLiveQuery(
    () => (ordemSelecionadaId ? db.pesagens.where("ordem_id").equals(ordemSelecionadaId).toArray() : []),
    [ordemSelecionadaId],
  );

  const [peso, setPeso] = useState("");
  const [placa, setPlaca] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [mensagem, setMensagem] = useState<string | null>(null);

  if (!mounted || !session || ordens === undefined) return null;

  const pesagemAberta = pesagensDaOrdem?.find((p) => p.peso_liquido_kg === null) ?? null;
  const ehSegundaPesagem = ordemSelecionada?.tipo_pesagem === "DUPLA" && !!pesagemAberta;

  async function handleRegistrarPeso(e: React.FormEvent) {
    e.preventDefault();
    if (!ordemSelecionada) return;
    setSalvando(true);
    setMensagem(null);
    const agora = new Date().toISOString();
    const pesoNum = Number(peso.replace(",", "."));

    try {
      if (ehSegundaPesagem && pesagemAberta) {
        const bruto = Number(pesagemAberta.peso_bruto_kg ?? 0);
        const liquido = Math.abs(bruto - pesoNum).toFixed(3);
        await db.pesagens.update(pesagemAberta.local_id, {
          peso_tara_kg: pesoNum.toFixed(3),
          peso_liquido_kg: liquido,
          data_saida: agora,
          client_updated_at: agora,
        });
        // Só entra na fila se já tiver sido sincronizada (tem server_id); senão a
        // primeira entrada na fila (CREATE) ainda carrega o payload completo.
        if (pesagemAberta.server_id) {
          await db.sync_queue.add({
            local_id: pesagemAberta.local_id,
            entity_type: "pesagem",
            operation: "UPDATE",
            server_id: pesagemAberta.server_id,
            status: "PENDING",
            attempts: 0,
            created_at: agora,
          });
        }
      } else {
        const localId = crypto.randomUUID();
        const ehDupla = ordemSelecionada.tipo_pesagem === "DUPLA";
        await db.pesagens.add({
          local_id: localId,
          ordem_id: ordemSelecionada.id,
          server_id: null,
          numero_ticket: gerarNumeroTicketLocal(),
          peso_bruto_kg: pesoNum.toFixed(3),
          peso_tara_kg: ehDupla ? null : "0.000",
          peso_liquido_kg: ehDupla ? null : pesoNum.toFixed(3),
          captured_via: "MANUAL",
          leitura_bruta: null,
          placa: placa || null,
          motorista: null,
          animal_id: null,
          pessoa_id: null,
          data_entrada: agora,
          data_saida: null,
          client_created_at: agora,
          client_updated_at: agora,
          synced: 0,
        });
        await enqueuePesagem(localId);
      }

      await db.ordens.update(ordemSelecionada.id, {
        status: ordemSelecionada.tipo_pesagem === "DUPLA" && !ehSegundaPesagem ? "EM_PESAGEM" : "CONCLUIDA",
      });

      setPeso("");
      setPlaca("");
      setOrdemSelecionadaId(null);
      setMensagem("Pesagem registrada. Sincronizando quando houver conexão.");
      void runSyncCycle();
    } finally {
      setSalvando(false);
    }
  }

  return (
    <main className="min-h-screen p-4">
      <header className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">{session.nome}</h1>
          <p className="text-xs text-gray-500">
            Última sincronização: {session.last_sync_at ? new Date(session.last_sync_at).toLocaleString("pt-BR") : "nunca"}
          </p>
        </div>
        <button
          className="text-xs text-gray-400 underline"
          onClick={async () => {
            await clearSession();
            router.replace("/");
          }}
        >
          Desativar estação
        </button>
      </header>

      {mensagem && <p className="mb-4 rounded bg-green-50 p-2 text-sm text-green-700">{mensagem}</p>}

      {!ordemSelecionada ? (
        <section>
          <h2 className="mb-2 text-sm font-medium text-gray-600">Ordens de pesagem pendentes</h2>
          {ordens.length === 0 && <p className="text-sm text-gray-400">Nenhuma ordem pendente no momento.</p>}
          <ul className="space-y-2">
            {ordens.map((ordem: OrdemPendenteLocal) => (
              <li key={ordem.id}>
                <button
                  className="w-full rounded border border-gray-200 bg-white p-3 text-left shadow-sm"
                  onClick={() => setOrdemSelecionadaId(ordem.id)}
                >
                  <div className="flex justify-between text-sm font-medium">
                    <span>{ordem.origem_tipo}</span>
                    <span className="text-gray-400">{ordem.subject_type}</span>
                  </div>
                  <div className="text-xs text-gray-500">
                    {ordem.tipo_pesagem === "DUPLA" ? "Pesagem dupla (entrada/saída)" : "Pesagem única"} · {ordem.status}
                  </div>
                  {typeof ordem.contexto?.placa === "string" && (
                    <div className="text-xs text-gray-400">Placa: {ordem.contexto.placa}</div>
                  )}
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <form onSubmit={handleRegistrarPeso} className="space-y-4 rounded border border-gray-200 bg-white p-4 shadow-sm">
          <button type="button" className="text-xs text-gray-400 underline" onClick={() => setOrdemSelecionadaId(null)}>
            ← Voltar
          </button>
          <h2 className="text-base font-semibold">
            {ehSegundaPesagem ? "Pesagem de saída" : "Pesagem de entrada"} — {ordemSelecionada.origem_tipo}
          </h2>

          <div className="space-y-1">
            <label className="text-sm font-medium">Peso (kg)</label>
            <input
              type="text"
              inputMode="decimal"
              className="w-full rounded border border-gray-300 px-3 py-3 text-2xl"
              value={peso}
              onChange={(e) => setPeso(e.target.value)}
              placeholder="0,000"
              required
              autoFocus
            />
            <p className="text-xs text-gray-400">Digitação manual — captura eletrônica prevista para fase posterior.</p>
          </div>

          {ordemSelecionada.subject_type === "VEICULO" && !ehSegundaPesagem && (
            <div className="space-y-1">
              <label className="text-sm font-medium">Placa</label>
              <input
                className="w-full rounded border border-gray-300 px-3 py-2 uppercase"
                value={placa}
                onChange={(e) => setPlaca(e.target.value)}
              />
            </div>
          )}

          <button
            type="submit"
            disabled={salvando}
            className="w-full rounded bg-orange-600 py-3 text-lg font-medium text-white disabled:opacity-50"
          >
            {salvando ? "Salvando..." : "Confirmar pesagem"}
          </button>
        </form>
      )}
    </main>
  );
}
