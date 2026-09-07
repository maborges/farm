import { Suspense } from "react";

import { Loader2 } from "lucide-react";

import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

import { ConfirmarCadastroClient } from "./confirmar-cadastro-client";

export default function ConfirmarCadastroPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
      <Suspense
        fallback={
          <Card className="w-full max-w-md text-center">
            <CardHeader>
              <Loader2 className="mx-auto mb-3 h-12 w-12 animate-spin text-primary" />
              <CardTitle>Confirmando cadastro</CardTitle>
              <CardDescription>Estamos validando seu link de confirmação.</CardDescription>
            </CardHeader>
          </Card>
        }
      >
        <ConfirmarCadastroClient />
      </Suspense>
    </div>
  );
}
