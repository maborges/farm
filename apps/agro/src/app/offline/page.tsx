"use client";

import Link from "next/link";
import { WifiOff, RotateCcw, Home, CloudSun, Calculator } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function OfflinePage() {
  const handleReload = () => {
    if (typeof window !== "undefined") {
      window.location.reload();
    }
  };

  return (
    <div className="py-10 max-w-md mx-auto text-center flex flex-col gap-5">
      <div className="size-16 mx-auto rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center">
        <WifiOff className="size-8" />
      </div>

      <div className="flex flex-col gap-1.5">
        <h1 className="text-xl font-bold tracking-tight text-foreground">
          Você está sem conexão
        </h1>
        <p className="text-xs text-muted-foreground leading-relaxed">
          O DeepFarms Agro funciona mesmo com sinal de internet fraco ou inexistente na lavoura. Os recursos previamente visualizados continuam disponíveis no seu aparelho.
        </p>
      </div>

      <div className="flex items-center justify-center gap-2 pt-2">
        <Button variant="default" size="sm" onClick={handleReload}>
          <RotateCcw className="size-3.5" />
          <span>Tentar Novamente</span>
        </Button>
        <Button asChild variant="outline" size="sm">
          <Link href="/">
            <Home className="size-3.5" />
            <span>Página Inicial</span>
          </Link>
        </Button>
      </div>

      <Card className="text-left mt-2">
        <CardHeader>
          <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            Ferramentas Disponíveis Offline
          </CardTitle>
          <CardDescription className="text-xs">
            Navegue pelos módulos salvos em cache no seu dispositivo:
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-2 text-xs">
          <Link
            href="/clima"
            className="flex items-center justify-between p-2 rounded-sm hover:bg-muted transition-colors border border-border/40"
          >
            <div className="flex items-center gap-2">
              <CloudSun className="size-4 text-blue-600 dark:text-blue-400" />
              <span className="font-medium text-foreground">Previsão Climática</span>
            </div>
            <span className="text-[11px] text-muted-foreground">Último snapshot</span>
          </Link>

          <Link
            href="/calculadoras"
            className="flex items-center justify-between p-2 rounded-sm hover:bg-muted transition-colors border border-border/40"
          >
            <div className="flex items-center gap-2">
              <Calculator className="size-4 text-amber-600 dark:text-amber-400" />
              <span className="font-medium text-foreground">Calculadoras Rurais</span>
            </div>
            <span className="text-[11px] text-muted-foreground">Fórmulas locais</span>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
