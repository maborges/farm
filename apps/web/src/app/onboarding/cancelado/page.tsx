"use client";

import { XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useRouter } from "next/navigation";

export default function OnboardingCanceladoPage() {
    const router = useRouter();

    return (
        <div className="min-h-screen flex items-center justify-center bg-muted/30 p-4">
            <Card className="w-full max-w-md text-center">
                <CardHeader>
                    <XCircle className="size-12 text-muted-foreground mx-auto mb-2" />
                    <CardTitle className="text-xl">Pagamento não concluído</CardTitle>
                    <CardDescription>
                        Você cancelou o pagamento. Sua conta ainda não foi ativada.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                    <p className="text-sm text-muted-foreground">
                        Você pode tentar novamente usando o link de ativação enviado por email.
                        Se precisar de ajuda, entre em contato com nosso suporte.
                    </p>
                    <Button variant="outline" className="w-full" onClick={() => router.back()}>
                        Tentar novamente
                    </Button>
                </CardContent>
            </Card>
        </div>
    );
}
