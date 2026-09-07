import { notFound } from "next/navigation";
import { getApiBaseUrl } from "@/lib/runtime-config";
import { CheckCircle2, Leaf, MapPin, Award, Calendar, Package, ShieldCheck, Camera, FileText } from "lucide-react";
import Image from "next/image";
import { Badge } from "@/components/ui/badge";
import MapaWrapper from "./mapa-wrapper";

interface TimelineEvent {
  id: string;
  tipo: string;
  tipo_evento: string;
  descricao: string;
  data_registro: string;
  fotos?: {
    url: string;
    latitude?: number | null;
    longitude?: number | null;
    data_captura?: string | null;
  }[];
}

interface Certificacao {
  nome: string;
  extensao?: string | null;
  numero_registro?: string | null;
  data_validade: string;
  orgao_certificador?: string | null;
}

interface FotoPublica {
  url: string;
  latitude?: number | null;
  longitude?: number | null;
  data_captura?: string | null;
}

interface PassportSnapshot {
  lote_codigo: string;
  produto: string;
  variedade?: string | null;
  peso_liquido_kg: number;
  quantidade_volumes: number;
  safra: string;
  fazenda: string;
  municipio?: string | null;
  uf?: string | null;
  talhoes: string[];
  geometria?: any;
  centroide_lat?: number | null;
  centroide_lng?: number | null;
  talhao_area_ha?: number | null;
  datas_principais: {
    criado_em: string;
    data_entrada_origem: string;
  };
  timeline: TimelineEvent[];
  certificacoes: Certificacao[];
  fotos: FotoPublica[];
  protocolo: string;
  hash?: string;
}

interface PageProps {
  params: Promise<{ token: string }>;
}

async function getPassportData(token: string): Promise<PassportSnapshot | null> {
  const apiBase = getApiBaseUrl();
  try {
    const res = await fetch(`${apiBase}/public/rastreabilidade/${token}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.error("Erro ao carregar dados do passaporte:", err);
    return null;
  }
}

function fmtDate(dStr: string | null): string {
  if (!dStr) return "—";
  try {
    const d = new Date(dStr.includes("T") ? dStr : `${dStr}T00:00:00`);
    return d.toLocaleDateString("pt-BR", { timeZone: "UTC" });
  } catch {
    return dStr;
  }
}

export default async function PassaporteRastreabilidadePage({ params }: PageProps) {
  const { token } = await params;
  const data = await getPassportData(token);

  if (!data) {
    notFound();
  }

  return (
    <div className="min-h-screen bg-stone-50/50 text-stone-800 pb-16 font-sans">
      {/* Premium Cover Banner */}
      <div className="relative h-72 w-full overflow-hidden bg-emerald-950">
        <Image
          src="/images/coffee_farm_cover.png"
          alt="Coffee Farm Sunrise"
          fill
          priority
          sizes="100vw"
          className="object-cover opacity-60 pointer-events-none"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-emerald-950 via-emerald-950/40 to-transparent" />
        
        {/* Floating Glassmorphism Title Card */}
        <div className="absolute bottom-6 left-6 right-6 max-w-4xl mx-auto">
          <div className="bg-emerald-950/80 backdrop-blur-md border border-emerald-700/50 p-6 rounded-sm text-white shadow-xl">
            <div className="flex items-center gap-2 text-emerald-400 mb-2">
              <Leaf className="size-5" />
              <span className="text-xs font-bold uppercase tracking-wider">Passaporte de Rastreabilidade Comercial</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight mb-1">{data.produto}</h1>
            {data.variedade && (
              <p className="text-stone-300 text-sm mb-3 font-medium">Variedade / Cultivo: {data.variedade}</p>
            )}
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-stone-300">
              <span className="bg-emerald-800/80 px-2 py-0.5 rounded-sm font-semibold border border-emerald-600/30">
                Lote: {data.lote_codigo}
              </span>
              <span>•</span>
              <span>Safra: {data.safra}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid Content */}
      <div className="max-w-4xl mx-auto px-6 mt-8 grid grid-cols-1 md:grid-cols-3 gap-8">
        
        {/* Left Column: Product & Origin Details */}
        <div className="md:col-span-1 space-y-6">
          {/* Card 1: Informações Físicas */}
          <div className="bg-white border border-stone-200/80 p-5 rounded-sm shadow-sm space-y-4">
            <h2 className="text-xs font-bold uppercase tracking-wider text-emerald-800 flex items-center gap-2">
              <Package className="size-4" /> Informações do Lote
            </h2>
            <div className="space-y-3 pt-2 text-sm border-t border-stone-100">
              <div className="flex justify-between">
                <span className="text-stone-500">Volume</span>
                <span className="font-semibold">{data.quantidade_volumes} SC</span>
              </div>
              <div className="flex justify-between">
                <span className="text-stone-500">Peso Líquido</span>
                <span className="font-semibold">{data.peso_liquido_kg.toLocaleString("pt-BR")} kg</span>
              </div>
              <div className="flex justify-between">
                <span className="text-stone-500">Expedição/Saída</span>
                <span className="font-semibold">{fmtDate(data.datas_principais.data_entrada_origem)}</span>
              </div>
            </div>
          </div>

          {/* Card 2: Origem Territorial */}
          <div className="bg-white border border-stone-200/80 p-5 rounded-sm shadow-sm space-y-4">
            <h2 className="text-xs font-bold uppercase tracking-wider text-emerald-800 flex items-center gap-2">
              <MapPin className="size-4" /> Origem Produtiva
            </h2>
            <div className="space-y-3 pt-2 text-sm border-t border-stone-100">
              <div>
                <span className="text-stone-500 block text-xs">Propriedade / Fazenda</span>
                <span className="font-semibold">{data.fazenda}</span>
              </div>
              {data.municipio && (
                <div>
                  <span className="text-stone-500 block text-xs">Localização</span>
                  <span className="font-semibold">{data.municipio} - {data.uf}</span>
                </div>
              )}
              {data.talhoes && data.talhoes.length > 0 && (
                <div>
                  <span className="text-stone-500 block text-xs">Talões de Origem</span>
                  <span className="font-semibold text-emerald-800">{data.talhoes.join(", ")}</span>
                </div>
              )}
            </div>
          </div>

          {/* Mapeamento Geoespacial Card */}
          {(data.geometria || (data.centroide_lat && data.centroide_lng)) ? (
            <div className="bg-white border border-stone-200/80 p-5 rounded-sm shadow-sm space-y-4">
              <h2 className="text-xs font-bold uppercase tracking-wider text-emerald-800 flex items-center gap-2">
                <MapPin className="size-4" /> Georreferenciamento
              </h2>
              <div className="pt-2 border-t border-stone-100 space-y-3">
                <MapaWrapper
                  geometria={data.geometria}
                  centroide_lat={data.centroide_lat}
                  centroide_lng={data.centroide_lng}
                  talhao_nome={data.talhoes?.[0]}
                  fazenda_nome={data.fazenda}
                />
                
                <div className="text-xs space-y-1.5 text-stone-500 pt-1">
                  {data.talhao_area_ha && data.talhao_area_ha > 0 ? (
                    <div className="flex justify-between">
                      <span>Área Calculada:</span>
                      <span className="font-semibold text-stone-700">{data.talhao_area_ha.toFixed(2)} ha</span>
                    </div>
                  ) : null}
                  {data.centroide_lat && data.centroide_lng ? (
                    <div className="flex justify-between">
                      <span>Coordenadas:</span>
                      <span className="font-mono text-stone-600">
                        {data.centroide_lat.toFixed(5)}, {data.centroide_lng.toFixed(5)}
                      </span>
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          ) : null}

          {/* Card 3: Certificações Ativas */}
          {data.certificacoes && data.certificacoes.length > 0 && (
            <div className="bg-white border border-stone-200/80 p-5 rounded-sm shadow-sm space-y-4">
              <h2 className="text-xs font-bold uppercase tracking-wider text-emerald-800 flex items-center gap-2">
                <Award className="size-4" /> Certificações Ativas
              </h2>
              <div className="space-y-4 pt-2 border-t border-stone-100">
                {data.certificacoes.map((c, idx) => (
                  <div key={idx} className="bg-emerald-50/50 border border-emerald-100 p-3 rounded-sm space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-sm text-emerald-950">{c.nome}</span>
                      <Badge variant="outline" className="text-[10px] bg-emerald-100/30 text-emerald-800 border-emerald-200/50 rounded-sm">
                        Ativa
                      </Badge>
                    </div>
                    {c.numero_registro && (
                      <span className="text-stone-500 text-xs block">Registro: {c.numero_registro}</span>
                    )}
                    <span className="text-[10px] text-stone-400 block">
                      Validade: {fmtDate(c.data_validade)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Compliance Timeline */}
        <div className="md:col-span-2 space-y-6">
          <div className="bg-white border border-stone-200/80 p-6 rounded-sm shadow-sm">
            <h2 className="text-xs font-bold uppercase tracking-wider text-emerald-800 flex items-center gap-2 mb-6">
              <Calendar className="size-4" /> Linha do Tempo de Conformidade
            </h2>
            
            {/* Timeline wrapper */}
            {data.timeline && data.timeline.length > 0 ? (
              <div className="relative pl-6 border-l border-stone-200 space-y-8 ml-3">
                {data.timeline.map((event, idx) => (
                  <div key={idx} className="relative group">
                    {/* Timeline bullet dot */}
                    <div className="absolute -left-[31px] top-1.5 size-4 rounded-full border-2 border-emerald-700 bg-white transition-colors group-hover:bg-emerald-700" />
                    
                    <div className="space-y-1">
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-semibold text-stone-400">
                          {fmtDate(event.data_registro)}
                        </span>
                        <Badge variant="outline" className="text-[10px] bg-stone-50 text-stone-600 rounded-sm border-stone-200 uppercase px-1 py-0 font-medium">
                          {event.tipo.toLowerCase()}
                        </Badge>
                      </div>
                      <h3 className="font-bold text-base text-stone-900 leading-tight">
                        {event.tipo_evento}
                      </h3>
                      <p className="text-sm text-stone-600 leading-relaxed max-w-xl">
                        {event.descricao}
                      </p>

                      {/* Display Photos directly below timeline item if present */}
                      {event.fotos && event.fotos.length > 0 && (
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-3">
                          {event.fotos.map((f, fIdx) => (
                            <div key={fIdx} className="relative aspect-video rounded-sm overflow-hidden border border-stone-200 bg-stone-50">
                              <Image
                                src={f.url}
                                alt={`Evidência ${event.tipo_evento}`}
                                fill
                                sizes="(max-width: 768px) 50vw, 33vw"
                                className="object-cover hover:scale-105 transition-transform duration-200"
                              />
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-stone-500 italic py-4">
                Nenhum evento público registrado na timeline deste lote.
              </p>
            )}
          </div>
        </div>

      </div>

      {/* Global Public Media Gallery */}
      {data.fotos && data.fotos.length > 0 && (
        <div className="max-w-4xl mx-auto px-6 mt-8">
          <div className="bg-white border border-stone-200/80 p-6 rounded-sm shadow-sm space-y-4">
            <h2 className="text-xs font-bold uppercase tracking-wider text-emerald-800 flex items-center gap-2">
              <Camera className="size-4" /> Galeria de Evidências Fotográficas do Campo
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 pt-2 border-t border-stone-100">
              {data.fotos.map((foto, idx) => (
                <div key={idx} className="group border border-stone-100 rounded-sm overflow-hidden shadow-sm bg-stone-50">
                  <div className="relative aspect-square w-full">
                    <Image
                      src={foto.url}
                      alt={`Foto Rastreabilidade ${idx + 1}`}
                      fill
                      sizes="(max-width: 768px) 50vw, 25vw"
                      className="object-cover transition-transform duration-300 group-hover:scale-105"
                    />
                  </div>
                  {(foto.latitude || foto.data_captura) && (
                    <div className="p-2 bg-stone-50 text-[10px] text-stone-500 space-y-0.5">
                      {foto.latitude && foto.longitude && (
                        <div className="flex items-center gap-1">
                          <MapPin className="size-3 text-emerald-700" />
                          <span>GPS: {foto.latitude.toFixed(4)}, {foto.longitude.toFixed(4)}</span>
                        </div>
                      )}
                      {foto.data_captura && (
                        <div className="flex items-center gap-1">
                          <Calendar className="size-3 text-stone-400" />
                          <span>{fmtDate(foto.data_captura)}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Authenticity Verification Card */}
      <div className="max-w-4xl mx-auto px-6 mt-8">
        <div className="bg-emerald-900 border border-emerald-800/80 p-6 rounded-sm text-emerald-50 shadow-md">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <ShieldCheck className="size-6 text-emerald-400 shrink-0" />
                <h2 className="font-extrabold text-lg tracking-tight">Passaporte Autenticado</h2>
              </div>
              <p className="text-emerald-200/90 text-sm leading-relaxed max-w-xl">
                Este lote comercial possui registro digital imutável e foi assinado eletronicamente pelo Responsável Técnico da propriedade agrícola. Os dados operacionais de conformidade e as fotos foram consolidados de forma segura e descentralizada.
              </p>
            </div>
            
            <div className="bg-emerald-950/70 border border-emerald-800 p-4 rounded-sm text-center shrink-0 w-full sm:w-auto">
              <div className="text-emerald-400 text-xs font-bold uppercase tracking-wider mb-1">
                Status Rastreabilidade
              </div>
              <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-950 rounded-sm text-emerald-400 font-bold border border-emerald-600/20 text-sm">
                <span className="size-2 rounded-full bg-emerald-400 animate-pulse" />
                ATIVO / VERIFICADO
              </div>
            </div>
          </div>

          <div className="mt-6 pt-5 border-t border-emerald-800/50 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-emerald-200/70">
            <div className="space-y-1">
              <div className="flex items-center gap-1 font-semibold text-emerald-200">
                <FileText className="size-3.5" /> Protocolo de Rastreamento
              </div>
              <p className="font-mono text-emerald-100">{data.protocolo}</p>
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-1 font-semibold text-emerald-200">
                <ShieldCheck className="size-3.5" /> Assinatura Digital (SHA-256 Hash)
              </div>
              <p className="font-mono text-emerald-100 break-all text-[11px] select-all">{data.hash || "—"}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
