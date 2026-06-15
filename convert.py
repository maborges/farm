import sys

with open("apps/web/src/app/(dashboard)/suprimentos/estoque/page.tsx", "r") as f:
    content = f.read()

# Create EstoqueClient.tsx
client_content = content.replace("export default function EstoquePage() {", "export function EstoqueClient({ initialData }: { initialData: any }) {")

# Inject initialData into useQuery
client_content = client_content.replace(
    'queryFn: () => apiFetch(`/estoque/saldos${fazendaParam}`),',
    'queryFn: () => apiFetch(`/estoque/saldos${fazendaParam}`),\n    initialData: initialData.saldos,'
)
client_content = client_content.replace(
    'queryFn: () => apiFetch(`/estoque/alertas${fazendaParam}`),',
    'queryFn: () => apiFetch(`/estoque/alertas${fazendaParam}`),\n    initialData: initialData.alertas,'
)
client_content = client_content.replace(
    'queryFn: () => apiFetch("/cadastros/produtos?ativo=true&incluir_sistema=true"),',
    'queryFn: () => apiFetch("/cadastros/produtos?ativo=true&incluir_sistema=true"),\n    initialData: initialData.produtos,'
)
client_content = client_content.replace(
    'queryFn: () => apiFetch(`/estoque/depositos${fazendaParam}`),',
    'queryFn: () => apiFetch(`/estoque/depositos${fazendaParam}`),\n    initialData: initialData.depositos,'
)
client_content = client_content.replace(
    'queryFn: () => apiFetch(`/estoque/reservas?status=`),',
    'queryFn: () => apiFetch(`/estoque/reservas?status=`),\n    initialData: initialData.reservas,'
)
client_content = client_content.replace(
    'queryFn: () => apiFetch(`/estoque/movimentacoes${fazendaParam}&limit=200`),',
    'queryFn: () => apiFetch(`/estoque/movimentacoes${fazendaParam}&limit=200`),\n    initialData: initialData.movimentacoes,'
)

with open("apps/web/src/app/(dashboard)/suprimentos/estoque/EstoqueClient.tsx", "w") as f:
    f.write(client_content)

# Create page.tsx (RSC)
rsc_content = """import { EstoqueClient } from "./EstoqueClient";
import { apiFetchServer } from "@/lib/api-server";

export default async function EstoquePage() {
  const [
    saldosResult,
    alertasResult,
    produtosResult,
    depositosResult,
    reservasResult,
    movimentacoesResult,
  ] = await Promise.allSettled([
    apiFetchServer("/estoque/saldos"),
    apiFetchServer("/estoque/alertas"),
    apiFetchServer("/cadastros/produtos?ativo=true&incluir_sistema=true"),
    apiFetchServer("/estoque/depositos"),
    apiFetchServer("/estoque/reservas?status="),
    apiFetchServer("/estoque/movimentacoes?limit=200"),
  ]);

  const initialData = {
    saldos: saldosResult.status === "fulfilled" ? saldosResult.value : [],
    alertas: alertasResult.status === "fulfilled" ? alertasResult.value : [],
    produtos: produtosResult.status === "fulfilled" ? produtosResult.value : [],
    depositos: depositosResult.status === "fulfilled" ? depositosResult.value : [],
    reservas: reservasResult.status === "fulfilled" ? reservasResult.value : [],
    movimentacoes: movimentacoesResult.status === "fulfilled" ? movimentacoesResult.value : [],
  };

  return <EstoqueClient initialData={initialData} />;
}
"""

with open("apps/web/src/app/(dashboard)/suprimentos/estoque/page.tsx", "w") as f:
    f.write(rsc_content)

