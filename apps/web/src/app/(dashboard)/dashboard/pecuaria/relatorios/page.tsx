"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
    FileText, Download, TrendingUp,
    BarChart3, PieChart as PieChartIcon,
    Calendar, Filter, Printer,
    Activity, Beef, MapPin, Syringe
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, Cell,
    PieChart, Pie, Legend, LineChart, Line
} from 'recharts';
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

interface PecuariaReport {
    rebanho: {
        total_cabecas: number;
        ua_total: number;
        gmd_medio: number;
        lotes_ativos: number;
    };
    composicao_categorias: Array<{ categoria: string, quantidade: number }>;
    sanitario_pendente: number;
    estoque_pastagem: {
        disponivel_massa: number;
        carga_animal: number;
    };
}

const ChartTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-background/95 backdrop-blur-md border border-border p-3 rounded-sm shadow-2xl">
                <p className="text-[10px] font-bold text-muted-foreground uppercase mb-2 tracking-wider">{label}</p>
                {payload.map((entry: any, index: number) => (
                    <div key={index} className="flex items-center gap-3 py-1">
                        <div className="h-2 w-2 rounded-full" style={{ backgroundColor: entry.color || entry.fill }} />
                        <span className="text-xs font-medium text-foreground">{entry.name}:</span>
                        <span className="text-xs font-black ml-auto">
                            {entry.value.toLocaleString()}
                            {entry.unit ? ` ${entry.unit}` : ""}
                        </span>
                    </div>
                ))}
            </div>
        );
    }
    return null;
};

export default function PecuariaReportsPage() {
    const { data: report, isLoading } = useQuery<PecuariaReport>({
        queryKey: ["pecuaria", "reports", "summary"],
        queryFn: () => apiFetch("/reports/pecuaria/summary")
    });

    if (isLoading) {
        return <div className="p-8 space-y-8"><Skeleton className="h-64 w-full" /><Skeleton className="h-96 w-full" /></div>;
    }

    const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6'];

    return (
        <div className="p-8 space-y-8 w-full max-w-7xl mx-auto">
            <svg style={{ height: 0, width: 0, position: 'absolute' }}>
                <defs>
                    <linearGradient id="barPasture" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#10b981" stopOpacity={0.8} />
                        <stop offset="100%" stopColor="#059669" stopOpacity={0.4} />
                    </linearGradient>
                </defs>
            </svg>
            <PageHeader
                title="Relatórios Zootécnicos"
                description="Indicadores de desempenho do rebanho e manejo de pastagem."
                icon={<Beef className="h-8 w-8 text-primary" />}
                actions={
                    <div className="flex gap-2">
                        <Badge variant="outline" className="text-primary border-primary">Pecuária</Badge>
                        <Button variant="outline" size="sm" className="gap-2">
                            <Calendar size={14} /> Ciclo Atual
                        </Button>
                        <Button size="sm" className="gap-2">
                            <Download size={14} /> Exportar Inventário
                        </Button>
                    </div>
                }
            />

            {/* Zootecnia Hero Stats */}
            <div className="grid gap-6 md:grid-cols-4">
                <Card className="bg-surface shadow-md border-b-4 border-b-green-500">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-[10px] font-black uppercase text-muted-foreground">Total de Animais</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-black">{report?.rebanho.total_cabecas.toLocaleString()}</div>
                        <p className="text-[10px] text-muted-foreground mt-1">{report?.rebanho.ua_total} Unidades Animal (UA)</p>
                    </CardContent>
                </Card>

                <Card className="bg-surface shadow-md border-b-4 border-b-blue-500">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-[10px] font-black uppercase text-muted-foreground">GMD Médio</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-black text-blue-600">{report?.rebanho.gmd_medio} kg</div>
                        <p className="text-[10px] text-muted-foreground mt-1">Ganho Médio Diário</p>
                    </CardContent>
                </Card>

                <Card className="bg-surface shadow-md border-b-4 border-b-amber-500">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-[10px] font-black uppercase text-muted-foreground">Lotes em Manejo</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-black text-amber-600">{report?.rebanho.lotes_ativos}</div>
                        <p className="text-[10px] text-muted-foreground mt-1">Lotes ativos na fazenda</p>
                    </CardContent>
                </Card>

                <Card className="bg-surface shadow-md border-b-4 border-b-red-500">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-[10px] font-black uppercase text-muted-foreground">Saúde / Sanidade</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-black text-red-600">{report?.sanitario_pendente}</div>
                        <p className="text-[10px] text-muted-foreground mt-1">Pendências sanitárias detectadas</p>
                    </CardContent>
                </Card>
            </div>

            <div className="grid gap-8 md:grid-cols-12">
                {/* Categories Table/Chart */}
                <Card className="md:col-span-4 bg-surface shadow-lg">
                    <CardHeader>
                        <CardTitle className="text-base flex items-center gap-2">
                            <Beef className="size-4 text-primary" /> Inventário por Categoria
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            {report?.composicao_categorias.map((item, i) => (
                                <div key={i} className="space-y-1">
                                    <div className="flex justify-between text-sm">
                                        <span className="font-medium">{item.categoria}</span>
                                        <span className="font-bold">{item.quantidade}</span>
                                    </div>
                                    <Progress value={(item.quantidade / (report?.rebanho.total_cabecas || 1)) * 100} className="h-1.5" />
                                </div>
                            ))}
                        </div>
                        <div className="mt-8 h-[200px]">
                            <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                    <Pie
                                        data={report?.composicao_categorias}
                                        innerRadius={50}
                                        outerRadius={70}
                                        paddingAngle={5}
                                        dataKey="quantidade"
                                        nameKey="categoria"
                                    >
                                        {report?.composicao_categorias.map((_, index) => (
                                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                        ))}
                                    </Pie>
                                    <Tooltip content={<ChartTooltip />} />
                                    <Legend iconType="circle" />
                                </PieChart>
                            </ResponsiveContainer>
                        </div>
                    </CardContent>
                </Card>

                {/* Pasture Management */}
                <Card className="md:col-span-8 bg-surface shadow-lg">
                    <CardHeader>
                        <CardTitle className="text-base flex items-center gap-2">
                            <MapPin className="size-4 text-green-600" /> Manejo de Pastagens & Forragem
                        </CardTitle>
                        <CardDescription>Carga animal vs Disponibilidade de biomassa.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-2 gap-8 mb-8">
                            <div className="p-4 bg-green-500/5 rounded-sm border border-green-200">
                                <p className="text-[10px] font-black uppercase text-green-700">Carga Média</p>
                                <p className="text-2xl font-black text-green-600">{report?.estoque_pastagem.carga_animal} UA/ha</p>
                                <p className="text-[10px] text-green-600/70">Status: Dentro do limite ideal</p>
                            </div>
                            <div className="p-4 bg-blue-500/5 rounded-sm border border-blue-200">
                                <p className="text-[10px] font-black uppercase text-blue-700">Massa de Forragem</p>
                                <p className="text-2xl font-black text-blue-600">{report?.estoque_pastagem.disponivel_massa} kg/ha</p>
                                <p className="text-[10px] text-blue-600/70">Média em matéria seca (MS)</p>
                            </div>
                        </div>

                        <div className="h-[250px] w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={([
                                    { mes: 'Out', carga: 1.2, massa: 2200 },
                                    { mes: 'Nov', carga: 1.4, massa: 2500 },
                                    { mes: 'Dez', carga: 1.8, massa: 2800 },
                                    { mes: 'Jan', carga: 1.6, massa: 2400 },
                                    { mes: 'Fev', carga: 1.5, massa: 2100 },
                                    { mes: 'Mar', carga: 1.3, massa: 1900 },
                                ])}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.1} />
                                    <XAxis dataKey="mes" axisLine={false} tickLine={false} tick={{ fontSize: 12 }} />
                                    <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10 }} />
                                    <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(0,0,0,0.05)' }} />
                                    <Legend iconType="circle" />
                                    <Bar dataKey="massa" fill="url(#barPasture)" radius={[4, 4, 0, 0]} name="Massa (kg/ha)" barSize={32} />
                                    <Line type="monotone" dataKey="carga" stroke="#3b82f6" strokeWidth={3} dot={{ r: 4 }} name="Carga (UA/ha)" />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Sanitary Calendar Warning */}
            <Card className="bg-surface shadow-md overflow-hidden ring-1 ring-red-100">
                <div className="flex items-center gap-4 p-4 bg-red-600 text-white">
                    <Syringe size={24} className="animate-bounce" />
                    <div>
                        <h4 className="font-bold">Ciclo de Vacinação Aftosa - Alerta de Pendência</h4>
                        <p className="text-sm opacity-90">145 animais cadastrados ainda não receberam a dose do ciclo atual.</p>
                    </div>
                    <Button size="sm" variant="secondary" className="ml-auto font-bold">Ver Lista de Animais</Button>
                </div>
            </Card>
        </div>
    );
}
