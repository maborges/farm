import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { BalancoHidrico } from "@/lib/agricola/clima-api";
import { Droplets, TrendingDown, TrendingUp } from "lucide-react";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
  ComposedChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Line,
  Legend
} from "recharts";

interface Props {
  data?: BalancoHidrico[];
}

export function BalancoHidricoCard({ data }: Props) {
  const balanco: BalancoHidrico[] = data ?? [];

  if (balanco.length === 0) {
    return <Card className="rounded-sm"><CardContent className="py-10 text-center text-sm text-muted-foreground">Evapotranspiração observada indisponível para o período.</CardContent></Card>;
  }

  const chartData = balanco.map(b => ({
    ...b,
    labelData: format(parseISO(b.data), "dd/MM", { locale: ptBR })
  }));

  const totalEtc = chartData.reduce((acc, curr) => acc + (curr.etc_mm ?? 0), 0);
  const totalChuva = chartData.reduce((acc, curr) => acc + curr.chuva_efetiva_mm, 0);
  const isDeficit = totalEtc > totalChuva;

  return (
    <Card className="rounded-sm flex flex-col h-full border-border/60">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Droplets className="h-5 w-5 text-blue-500" />
          Balanço Hídrico (7 dias)
        </CardTitle>
        <CardDescription>
          Relação entre Evapotranspiração da Cultura (ETc) e Chuva Efetiva.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col flex-1">
        
        {/* Resumo */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="p-3 bg-muted/50 rounded-sm border border-border flex flex-col gap-1">
            <span className="text-xs text-muted-foreground uppercase font-semibold">ETc Acumulada</span>
            <div className="flex items-end gap-2">
              <span className="text-xl font-bold">{totalEtc.toFixed(1)}</span>
              <span className="text-xs text-muted-foreground mb-1">mm</span>
            </div>
          </div>
          <div className="p-3 bg-muted/50 rounded-sm border border-border flex flex-col gap-1">
            <span className="text-xs text-muted-foreground uppercase font-semibold">Chuva Efetiva</span>
            <div className="flex items-end gap-2">
              <span className="text-xl font-bold text-blue-600">{totalChuva.toFixed(1)}</span>
              <span className="text-xs text-muted-foreground mb-1">mm</span>
            </div>
          </div>
        </div>

        {/* Saldo Status */}
        <div className={`p-3 rounded-sm border flex items-center justify-between mb-6 ${isDeficit ? 'bg-amber-50 border-amber-200 text-amber-900' : 'bg-emerald-50 border-emerald-200 text-emerald-900'}`}>
          <div className="flex flex-col">
            <span className="text-xs font-semibold uppercase opacity-80">Saldo Semanal</span>
            <span className="font-bold">{Math.abs(totalChuva - totalEtc).toFixed(1)} mm {isDeficit ? "de déficit" : "de superávit"}</span>
          </div>
          {isDeficit ? <TrendingDown size={24} className="opacity-50" /> : <TrendingUp size={24} className="opacity-50" />}
        </div>

        {/* Chart */}
        <div className="h-[200px] w-full mt-auto">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 10, right: 10, bottom: 0, left: -25 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
              <XAxis dataKey="labelData" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} dy={5} />
              <YAxis tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip 
                contentStyle={{ borderRadius: "4px", fontSize: "12px" }}
              />
              <Legend wrapperStyle={{ fontSize: "10px", paddingTop: "10px" }} />
              <Bar dataKey="chuva_efetiva_mm" name="Chuva (mm)" fill="#3b82f6" barSize={12} radius={[2, 2, 0, 0]} />
              <Line type="monotone" dataKey="etc_mm" name="ETc (mm)" stroke="#ef4444" strokeWidth={2} dot={{ r: 3 }} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
