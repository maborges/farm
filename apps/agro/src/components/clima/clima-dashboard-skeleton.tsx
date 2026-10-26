"use client";

import * as React from "react";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Loader2 } from "lucide-react";

export function ClimaDashboardSkeleton(): React.ReactElement {
  return (
    <div className="space-y-4 animate-pulse" id="skeleton-dashboard">
      {/* Banner de Carregamento Ativo */}
      <div className="flex items-center justify-center gap-2 p-3 rounded-sm border border-border/60 bg-muted/30 text-xs text-muted-foreground">
        <Loader2 className="w-4 h-4 animate-spin text-primary shrink-0" />
        <span>Consultando projeção meteorológica para a localidade...</span>
      </div>

      {/* Skeleton Condições Atuais */}
      <Card className="rounded-sm border-border">
        <CardHeader className="pb-3 border-b border-border/60">
          <div className="flex items-center justify-between">
            <div className="h-5 w-48 bg-muted rounded-sm" />
            <div className="h-4 w-24 bg-muted rounded-sm" />
          </div>
          <div className="h-3 w-64 bg-muted/60 rounded-sm mt-1" />
        </CardHeader>
        <CardContent className="pt-4 space-y-4">
          <div className="p-4 rounded-sm bg-muted/20 border border-border/50 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-muted rounded-sm" />
              <div className="space-y-1.5">
                <div className="h-8 w-20 bg-muted rounded-sm" />
                <div className="h-4 w-32 bg-muted/70 rounded-sm" />
              </div>
            </div>
            <div className="space-y-1">
              <div className="h-3 w-28 bg-muted/60 rounded-sm" />
              <div className="h-3 w-20 bg-muted/40 rounded-sm" />
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="p-3 rounded-sm bg-muted/20 border border-border/50 space-y-2">
                <div className="h-3 w-16 bg-muted/60 rounded-sm" />
                <div className="h-6 w-12 bg-muted rounded-sm" />
                <div className="h-2 w-20 bg-muted/40 rounded-sm" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Skeleton Horária */}
      <Card className="rounded-sm border-border">
        <CardHeader className="pb-3 border-b border-border/60">
          <div className="h-4 w-40 bg-muted rounded-sm" />
        </CardHeader>
        <CardContent className="pt-4">
          <div className="flex gap-2.5 overflow-hidden">
            {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => (
              <div key={i} className="flex-shrink-0 w-24 p-3 rounded-sm bg-muted/20 border border-border/50 flex flex-col items-center gap-2">
                <div className="h-3 w-10 bg-muted rounded-sm" />
                <div className="w-6 h-6 bg-muted/60 rounded-sm" />
                <div className="h-4 w-8 bg-muted rounded-sm" />
                <div className="h-2 w-12 bg-muted/40 rounded-sm" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Skeleton Diária */}
      <Card className="rounded-sm border-border">
        <CardHeader className="pb-3 border-b border-border/60">
          <div className="h-4 w-48 bg-muted rounded-sm" />
        </CardHeader>
        <CardContent className="pt-2 divide-y divide-border/40">
          {[0, 1, 2, 3, 4].map((i) => (
            <div key={i} className="py-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-6 h-6 bg-muted/60 rounded-sm" />
                <div className="space-y-1">
                  <div className="h-3 w-20 bg-muted rounded-sm" />
                  <div className="h-2 w-12 bg-muted/40 rounded-sm" />
                </div>
              </div>
              <div className="h-3 w-28 bg-muted/50 rounded-sm" />
              <div className="h-4 w-16 bg-muted rounded-sm" />
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
