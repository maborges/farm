import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { AlertTriangle, Info, ThermometerSun, ShieldCheck } from "lucide-react";
import { InteligenciaPecuariaResponse } from "@/lib/pecuaria/clima-api";
import { cn } from "@/lib/utils";

interface RiscoTermicoCardProps {
    data: InteligenciaPecuariaResponse;
}

export function RiscoTermicoCard({ data }: RiscoTermicoCardProps) {
    const { risco_atual, valor_referencia, detalhes, tipo_risco, especie } = data;

    let colorClass = "from-muted/50 to-muted/20 text-muted-foreground border-border/50";
    let Icon = Info;
    let titleColor = "text-foreground";
    let description = "Sem risco significativo detectado.";
    let shadowClass = "shadow-sm";

    if (risco_atual === "BAIXO") {
         colorClass = "from-green-500/20 to-green-500/5 border-green-500/20 text-green-700 dark:text-green-400";
         titleColor = "text-green-700 dark:text-green-400";
         Icon = ShieldCheck;
         description = "Condições favoráveis para o bem-estar animal.";
         shadowClass = "shadow-green-500/10";
    } else if (risco_atual === "MEDIO") {
         colorClass = "from-yellow-500/20 to-yellow-500/5 border-yellow-500/20 text-yellow-700 dark:text-yellow-400";
         titleColor = "text-yellow-700 dark:text-yellow-400";
         Icon = ThermometerSun;
         description = "Atenção necessária. Estresse térmico moderado.";
         shadowClass = "shadow-yellow-500/10";
    } else if (risco_atual === "ALTO") {
         colorClass = "from-orange-500/20 to-orange-500/5 border-orange-500/20 text-orange-700 dark:text-orange-400";
         titleColor = "text-orange-700 dark:text-orange-400";
         Icon = AlertTriangle;
         description = "Perigo! Estresse térmico alto. Aplique medidas de mitigação imediatamente.";
         shadowClass = "shadow-orange-500/10";
    } else if (risco_atual === "CRITICO") {
         colorClass = "from-red-600/30 to-red-600/10 border-red-600/30 text-red-700 dark:text-red-400";
         titleColor = "text-red-700 dark:text-red-400";
         Icon = AlertTriangle;
         description = "Emergência Zoossanitária! Risco de mortalidade iminente. Intervenção urgente necessária.";
         shadowClass = "shadow-red-600/20";
    }

    // Extracting the border color from colorClass
    const borderTopColor = colorClass.split(' ').find(c => c.startsWith('border-'))?.replace('border-', 'bg-') || 'bg-muted';

    return (
        <Card className={cn("overflow-hidden border border-border/40 transition-all duration-300 hover:scale-[1.01] hover:shadow-lg rounded-sm bg-background/60 backdrop-blur-sm", shadowClass)}>
            <div className={cn("h-1.5 w-full", borderTopColor)} />
            <CardHeader className="pb-3 pt-5 px-6">
                <div className="flex justify-between items-start">
                    <div>
                        <CardTitle className="text-xl flex items-center gap-2 font-bold tracking-tight">
                            <ThermometerSun className="size-5 text-muted-foreground/60" />
                            {tipo_risco}
                        </CardTitle>
                        <CardDescription className="mt-1.5">
                            Análise zoossanitária para <span className="font-medium text-foreground/80">{especie}</span>
                        </CardDescription>
                    </div>
                    {valor_referencia !== null && (
                        <div className="flex flex-col items-end">
                            <span className="text-4xl font-black tracking-tighter bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/60">
                                {valor_referencia.toFixed(1)}
                            </span>
                            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mt-1">
                                Índice ITH
                            </span>
                        </div>
                    )}
                </div>
            </CardHeader>
            <CardContent className="space-y-6 px-6 pb-6">
                <div className={cn("flex items-center gap-4 rounded-sm p-5 border bg-gradient-to-br", colorClass)}>
                    <div className="p-2.5 bg-background/50 rounded-full shadow-sm">
                        <Icon className="size-7 flex-shrink-0" />
                    </div>
                    <div>
                        <h4 className={cn("font-bold text-lg leading-tight", titleColor)}>
                            Risco {risco_atual}
                        </h4>
                        <p className="text-sm font-medium opacity-90 leading-relaxed mt-1">
                            {description}
                        </p>
                    </div>
                </div>

                {detalhes.length > 0 && (
                    <div className="space-y-3">
                        <h5 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                            Alertas e Recomendações
                        </h5>
                        <ul className="space-y-2">
                            {detalhes.map((detalhe, index) => (
                                <li key={index} className="flex items-start gap-2 text-sm">
                                    <div className="mt-1.5 size-1.5 rounded-full bg-primary/60 flex-shrink-0" />
                                    <span className="leading-relaxed">{detalhe}</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
