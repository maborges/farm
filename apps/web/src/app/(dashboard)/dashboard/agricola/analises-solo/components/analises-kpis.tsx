"use client";

import { FlaskConical, AlertTriangle, CheckCircle2, Beaker } from "lucide-react";
import { StatCard } from "@/components/shared/stat-card";

interface AnaliseSolo {
    nome?: string;
    v_pct: number | null;
    ph: number | null;
}

interface AnalisesKPIsProps {
    data: AnaliseSolo[];
}

export function AnalisesKPIs({ data = [] }: AnalisesKPIsProps) {
    const totalTalhoes = data.length;
    const precisamCalagem = data.filter(a => (a.v_pct ?? 0) < 60 && (a.v_pct ?? 0) > 0).length;
    const vPctAdequado = data.filter(a => (a.v_pct ?? 0) >= 60).length;
    const phAcido = data.filter(a => (a.ph ?? 7) < 5.5).length;

    return (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <StatCard
                label="Talhões Analisados"
                value={totalTalhoes}
                icon={FlaskConical}
                color="agro"
            />
            <StatCard
                label="Precisam Calagem"
                value={precisamCalagem}
                icon={AlertTriangle}
                color="destructive"
            />
            <StatCard
                label="V% Adequado"
                value={vPctAdequado}
                icon={CheckCircle2}
                color="success"
            />
            <StatCard
                label="pH Ácido"
                value={phAcido}
                icon={Beaker}
                color="warning"
            />
        </div>
    );
}
