import { Suspense } from "react";
import { AnalisesClient } from "./components/analises-client";
import Loading from "./loading";

export const metadata = {
    title: "Análise de Solo | DeepFarms",
    description: "Gestão técnica de fertilidade e recomendações de correção de solo.",
};

/**
 * Análise de Solo - Server Component
 * 
 * Esta página segue o padrão RSC (React Server Components).
 * A interatividade e o estado do cliente são gerenciados pelo componente AnalisesClient.
 */
export default async function AnaliseSoloPage() {
    return (
        <Suspense fallback={<Loading />}>
            <AnalisesClient />
        </Suspense>
    );
}
