import { notFound } from "next/navigation";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Leaf, ShieldCheck, FileText, CheckCircle2 } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

interface PassaportePublico {
  public_token: string;
  titulo: string;
  status: string;
  versao: number;
  snapshot_hash: string | null;
  publicado_publicamente_em: string | null;
  created_at: string;
}

interface IntegridadeResponse {
  integridade: "VALIDA" | "INVALIDA";
  algoritmo?: string;
  hash?: string;
  versao?: number;
  publicado_em?: string;
}

interface PageProps {
  params: Promise<{ token: string }>;
}

async function getPassaportePublico(token: string): Promise<PassaportePublico> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const res = await fetch(`${apiUrl}/api/v1/public/passaportes/${token}`, {
    next: { revalidate: 60 },
  });

  if (!res.ok) {
    if (res.status === 404) {
      notFound();
    }
    throw new Error("Falha ao buscar dados públicos do passaporte");
  }

  return res.json();
}

async function verifyPassaporteIntegridade(token: string): Promise<IntegridadeResponse> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const res = await fetch(`${apiUrl}/api/v1/public/passaportes/${token}/verify`, {
    next: { revalidate: 60 },
  });

  if (!res.ok) {
    return { integridade: "INVALIDA" };
  }

  return res.json();
}

export default async function PassaportePublicoPage({ params }: PageProps) {
  const { token } = await params;
  const passaporte = await getPassaportePublico(token);
  const integridade = await verifyPassaporteIntegridade(token);

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-900 text-neutral-900 dark:text-neutral-50 flex flex-col items-center">
      {/* Header Público com Identidade Visual AgroSaaS */}
      <header className="w-full max-w-4xl py-6 px-4 flex items-center justify-between border-b border-neutral-200 dark:border-neutral-800">
        <div className="flex items-center gap-2">
          <div className="bg-emerald-600 p-2 rounded-md">
            <Leaf className="w-6 h-6 text-white" />
          </div>
          <span className="text-xl font-bold tracking-tight text-emerald-800 dark:text-emerald-400">AgroSaaS</span>
        </div>
        <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-500 font-medium">
          <ShieldCheck className="w-5 h-5" />
          <span className="hidden sm:inline">Verificado Oficialmente</span>
        </div>
      </header>

      <main className="w-full max-w-4xl flex-1 px-4 py-12 flex flex-col gap-8">
        {/* Banner de Verificação */}
        <div className="bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/50 rounded-xl p-6 flex flex-col md:flex-row items-start md:items-center gap-4 shadow-sm">
          <div className="bg-emerald-100 dark:bg-emerald-900/50 p-3 rounded-full flex-shrink-0">
            <CheckCircle2 className="w-8 h-8 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-emerald-900 dark:text-emerald-300">
              Passaporte de Rastreabilidade Válido
            </h1>
            <p className="text-emerald-700 dark:text-emerald-400 mt-1">
              Este documento foi certificado e emitido na plataforma AgroSaaS. Os dados abaixo são de origem garantida e inalterável desde a sua emissão.
            </p>
          </div>
        </div>

        {/* Informações Principais */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-xl p-6 shadow-sm">
            <h2 className="text-lg font-semibold flex items-center gap-2 border-b border-neutral-100 dark:border-neutral-700 pb-3 mb-4">
              <FileText className="w-5 h-5 text-neutral-500" /> Detalhes do Documento
            </h2>
            <div className="space-y-4">
              <div>
                <span className="text-sm text-neutral-500 dark:text-neutral-400 block mb-1">Título</span>
                <span className="font-medium text-lg">{passaporte.titulo}</span>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-sm text-neutral-500 dark:text-neutral-400 block mb-1">Status</span>
                  <span className="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300">
                    {passaporte.status}
                  </span>
                </div>
                <div>
                  <span className="text-sm text-neutral-500 dark:text-neutral-400 block mb-1">Versão</span>
                  <span className="font-medium">v{passaporte.versao}.0</span>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-xl p-6 shadow-sm">
            <h2 className="text-lg font-semibold flex items-center gap-2 border-b border-neutral-100 dark:border-neutral-700 pb-3 mb-4">
              <ShieldCheck className="w-5 h-5 text-neutral-500" /> Integridade e Segurança
            </h2>
            <div className="space-y-4">
              <div className="flex items-center gap-3 bg-neutral-50 dark:bg-neutral-900 p-3 rounded-lg border border-neutral-200 dark:border-neutral-800">
                {integridade.integridade === "VALIDA" ? (
                  <>
                    <CheckCircle2 className="w-6 h-6 text-emerald-500" />
                    <div>
                      <span className="font-semibold text-emerald-700 dark:text-emerald-400 block">✓ Documento íntegro</span>
                      <span className="text-xs text-neutral-500 dark:text-neutral-400">Verificado matematicamente</span>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="w-6 h-6 flex items-center justify-center rounded-full bg-red-100 text-red-600 font-bold">!</div>
                    <div>
                      <span className="font-semibold text-red-700 dark:text-red-400 block">⚠ Integridade inválida</span>
                      <span className="text-xs text-neutral-500 dark:text-neutral-400">O documento pode ter sido alterado</span>
                    </div>
                  </>
                )}
              </div>
              <div>
                <span className="text-sm text-neutral-500 dark:text-neutral-400 block mb-1">Assinatura Digital ({integridade.algoritmo || "Hash"})</span>
                <span className="font-mono text-xs break-all bg-neutral-100 dark:bg-neutral-900 px-2 py-1.5 rounded text-neutral-600 dark:text-neutral-300 block border border-neutral-200 dark:border-neutral-800">
                  {integridade.hash || passaporte.snapshot_hash || "Não disponível"}
                </span>
              </div>
              <div>
                <span className="text-sm text-neutral-500 dark:text-neutral-400 block mb-1">Data de Emissão Pública</span>
                <span className="font-medium">
                  {passaporte.publicado_publicamente_em
                    ? format(new Date(passaporte.publicado_publicamente_em), "dd 'de' MMMM 'de' yyyy, 'às' HH:mm", { locale: ptBR })
                    : "Data não registrada"}
                </span>
              </div>
            </div>
          </div>
        </div>

      </main>

      {/* Footer Público */}
      <footer className="w-full text-center py-8 text-neutral-500 dark:text-neutral-400 text-sm border-t border-neutral-200 dark:border-neutral-800">
        <p>Desenvolvido com tecnologia <strong>AgroSaaS</strong></p>
        <p className="mt-1">Garantindo transparência e conformidade ESG na cadeia produtiva.</p>
      </footer>
    </div>
  );
}
