"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { AlertTriangle, CheckCircle2, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiFetch } from "@/lib/api";

export function ConfirmarCadastroClient() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [loading, setLoading] = useState(Boolean(token));
  const [error, setError] = useState<string | null>(token ? null : "Token de confirmação não encontrado.");

  useEffect(() => {
    if (!token) {
      return;
    }

    apiFetch(`/onboarding/confirmar-cadastro/${token}`, {
      method: "POST",
      body: {},
    })
      .catch((err: Error) => {
        setError(err.message || "Não foi possível confirmar o cadastro.");
      })
      .finally(() => setLoading(false));
  }, [token]);

  return (
    <Card className="w-full max-w-md text-center">
      <CardHeader>
        {loading ? (
          <Loader2 className="mx-auto mb-3 h-12 w-12 animate-spin text-primary" />
        ) : error ? (
          <AlertTriangle className="mx-auto mb-3 h-12 w-12 text-destructive" />
        ) : (
          <CheckCircle2 className="mx-auto mb-3 h-12 w-12 text-emerald-600" />
        )}
        <CardTitle>
          {loading ? "Confirmando cadastro" : error ? "Não foi possível confirmar" : "Cadastro confirmado"}
        </CardTitle>
        <CardDescription>
          {loading
            ? "Estamos validando seu link de confirmação."
            : error
              ? error
              : "Seu cadastro foi confirmado. Agora você já pode fazer login e continuar seu fluxo normalmente."}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {!loading ? (
          <Button asChild className="w-full">
            <Link href="/login">Ir para o login</Link>
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}
