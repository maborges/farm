import { CalendarClock, CloudRain, ShieldAlert, ThermometerSun } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ChuvaPrevista, EstressePrevisto, JanelaManejo, PrevisaoIth } from "@/lib/pecuaria/clima-api";

interface PrevisaoPecuariaCardsProps {
    previsao: PrevisaoIth[];
    estresse: EstressePrevisto;
    chuva: ChuvaPrevista;
    janela: JanelaManejo;
}

function riscoLabel(risco: PrevisaoIth["risco"]): string {
    return risco === "INDETERMINADO" ? "Indeterminado" : risco;
}

function formatarHorario(horario: string | null): string {
    if (!horario) return "Nenhuma janela segura identificada";
    return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }).format(new Date(horario));
}

export function PrevisaoPecuariaCards({ previsao, estresse, chuva, janela }: PrevisaoPecuariaCardsProps) {
    return (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Card className="rounded-sm border-border/40">
                <CardHeader className="pb-3"><CardTitle className="flex items-center gap-2 text-sm"><ThermometerSun className="size-4 text-orange-500" />ITH previsto</CardTitle></CardHeader>
                <CardContent className="space-y-3">
                    {previsao.length === 0 ? <p className="text-sm text-muted-foreground">Sem previsão climática disponível.</p> : previsao.map((item) => (
                        <div key={item.data} className="flex items-center justify-between rounded-sm border border-border/40 px-3 py-2 text-sm">
                            <span>{item.horizonte_horas}h</span>
                            <span className="font-medium">{item.ith_max === null ? "Indeterminado" : item.ith_max.toFixed(1)}</span>
                            <span className="text-muted-foreground">{riscoLabel(item.risco)}</span>
                        </div>
                    ))}
                </CardContent>
            </Card>

            <Card className="rounded-sm border-border/40">
                <CardHeader className="pb-3"><CardTitle className="flex items-center gap-2 text-sm"><ShieldAlert className="size-4 text-red-500" />Estresse nas próximas 72h</CardTitle></CardHeader>
                <CardContent>
                    <p className="text-2xl font-bold">{estresse.duracao_horas === null ? "Indeterminado" : `${estresse.duracao_horas}h`}</p>
                    <p className="mt-1 text-sm text-muted-foreground">Intensidade prevista: {riscoLabel(estresse.intensidade)}</p>
                </CardContent>
            </Card>

            <Card className="rounded-sm border-border/40">
                <CardHeader className="pb-3"><CardTitle className="flex items-center gap-2 text-sm"><CloudRain className="size-4 text-blue-500" />Chuva prevista em 72h</CardTitle></CardHeader>
                <CardContent>
                    <p className="text-2xl font-bold">{chuva.volume_mm_72h === null ? "Indeterminado" : `${chuva.volume_mm_72h.toFixed(1)} mm`}</p>
                    <p className="mt-1 text-sm text-muted-foreground">Probabilidade máxima: {chuva.probabilidade_max_pct === null ? "Indeterminada" : `${chuva.probabilidade_max_pct.toFixed(0)}%`}</p>
                </CardContent>
            </Card>

            <Card className="rounded-sm border-border/40">
                <CardHeader className="pb-3"><CardTitle className="flex items-center gap-2 text-sm"><CalendarClock className="size-4 text-emerald-600" />Janela segura de manejo</CardTitle></CardHeader>
                <CardContent>
                    <p className="text-lg font-bold">{janela.status === "RECOMENDADA" ? formatarHorario(janela.horario) : "Não identificada"}</p>
                    <p className="mt-1 text-sm text-muted-foreground">{janela.ith === null ? "Temperatura e umidade insuficientes para recomendar horário." : `ITH estimado: ${janela.ith.toFixed(1)}`}</p>
                </CardContent>
            </Card>
        </div>
    );
}
