import { apiFetchServer } from "@/lib/api-server";
import { PedidosClient } from "./PedidosClient";
import type { ComponentProps } from "react";

type PedidosClientProps = ComponentProps<typeof PedidosClient>;

export const metadata = {
  title: "Pedidos de Compra | AGRO",
  description: "Acompanhe a oficialização e o recebimento das compras da fazenda.",
};

export default async function ComprasPage() {
  let initialData: PedidosClientProps["initialData"] = [];
  try {
    initialData = await apiFetchServer<PedidosClientProps["initialData"]>("/compras/pedidos");
  } catch (error) {
    console.error("Erro ao carregar pedidos iniciais:", error);
  }

  return <PedidosClient initialData={initialData} />;
}
