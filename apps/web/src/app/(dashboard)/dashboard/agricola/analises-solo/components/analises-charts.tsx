"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { BarChart2, Beaker } from "lucide-react";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartTooltip,
    ResponsiveContainer, ReferenceLine, Cell,
} from "recharts";

interface ChartDataPoint {
    nome: string;
    v_pct: number | null;
    ph: number | null;
}

interface AnalisesChartsProps {
    data: ChartDataPoint[];
}

export function AnalisesCharts({ data = [] }: AnalisesChartsProps) {
    const vPctData = data.filter(d => d.v_pct !== null);
    const phData = data.filter(d => d.ph !== null);

    if (vPctData.length === 0 && phData.length === 0) return null;

    return (
        <div className="space-y-3 animate-in fade-in slide-in-from-bottom-5 duration-500 delay-150">
            <div className="px-1 py-2 bg-blue-50 dark:bg-blue-950/20 rounded-sm border border-blue-200 dark:border-blue-800">
                <p className="text-xs text-blue-700 dark:text-blue-300">
                    <strong>ℹ️ Dados baseados na última análise realizada para cada talhão</strong>
                </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* V% por Talhão */}
            {vPctData.length > 0 && (
                <Card className="border-border/40 shadow-sm rounded-sm">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-bold text-muted-foreground flex items-center gap-2">
                            <BarChart2 size={14} className="text-primary" /> Saturação de Bases V%
                        </CardTitle>
                        <CardDescription className="text-[10px] uppercase tracking-wider">Meta: ≥ 60% — Necessidade de Calagem</CardDescription>
                    </CardHeader>
                    <CardContent className="pt-0">
                        <div className="h-[220px]">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={vPctData} layout="vertical" margin={{ left: 4, right: 24, top: 4, bottom: 4 }}>
                                    <CartesianGrid strokeDasharray="3 3" horizontal={false} opacity={0.1} />
                                    <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10 }}
                                        tickFormatter={v => `${v}%`} axisLine={false} tickLine={false} />
                                    <YAxis type="category" dataKey="nome" width={80}
                                        tick={{ fontSize: 10, fontWeight: 500 }} axisLine={false} tickLine={false} />
                                    <RechartTooltip
                                        cursor={{ fill: 'transparent' }}
                                        formatter={(v: number) => [`${v.toFixed(1)}%`, "V%"]}
                                        contentStyle={{ fontSize: 12, borderRadius: 4, border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                                    />
                                    <ReferenceLine x={60} stroke="#ef4444" strokeDasharray="4 2" strokeWidth={1}
                                        label={{ value: "60%", position: "top", fontSize: 10, fill: "#ef4444", fontWeight: 700 }} />
                                    <Bar dataKey="v_pct" radius={[0, 4, 4, 0]} maxBarSize={16}>
                                        {vPctData.map((d, i) => (
                                            <Cell key={i} fill={(d.v_pct ?? 0) >= 60 ? "#10b981" : "#ef4444"} fillOpacity={0.8} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* pH por Talhão */}
            {phData.length > 0 && (
                <Card className="border-border/40 shadow-sm rounded-sm">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-bold text-muted-foreground flex items-center gap-2">
                            <Beaker size={14} className="text-primary" /> pH (H₂O) por Talhão
                        </CardTitle>
                        <CardDescription className="text-[10px] uppercase tracking-wider">Faixa ideal: 5.5 – 6.5</CardDescription>
                    </CardHeader>
                    <CardContent className="pt-0">
                        <div className="h-[220px]">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={phData} layout="vertical" margin={{ left: 4, right: 24, top: 4, bottom: 4 }}>
                                    <CartesianGrid strokeDasharray="3 3" horizontal={false} opacity={0.1} />
                                    <XAxis type="number" domain={[0, 8]} tick={{ fontSize: 10 }}
                                        axisLine={false} tickLine={false} />
                                    <YAxis type="category" dataKey="nome" width={80}
                                        tick={{ fontSize: 10, fontWeight: 500 }} axisLine={false} tickLine={false} />
                                    <RechartTooltip
                                        cursor={{ fill: 'transparent' }}
                                        formatter={(v: number) => [v.toFixed(2), "pH"]}
                                        contentStyle={{ fontSize: 12, borderRadius: 4, border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                                    />
                                    <ReferenceLine x={5.5} stroke="#f59e0b" strokeDasharray="4 2"
                                        label={{ value: "5.5", position: "top", fontSize: 9, fill: "#f59e0b", fontWeight: 700 }} />
                                    <ReferenceLine x={6.5} stroke="#10b981" strokeDasharray="4 2"
                                        label={{ value: "6.5", position: "top", fontSize: 9, fill: "#10b981", fontWeight: 700 }} />
                                    <Bar dataKey="ph" radius={[0, 4, 4, 0]} maxBarSize={16}>
                                        {phData.map((d, i) => (
                                            <Cell key={i} fill={
                                                (d.ph ?? 0) < 5.5 ? "#ef4444"
                                                : (d.ph ?? 0) <= 6.5 ? "#10b981"
                                                : "#3b82f6"
                                            } fillOpacity={0.8} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </CardContent>
                </Card>
            )}
            </div>
        </div>
    );
}
