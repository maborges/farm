import { apiFetchServer } from "@/lib/api-server";
import { RegistrosClient } from "./RegistrosClient";
import { HedgeRegistro, ContratoFuturo } from "../types";

export default async function RegistrosPage() {
    let initialRegistros: HedgeRegistro[] = [];
    let contratos: ContratoFuturo[] = [];

    try {
        const [registrosRes, contratosRes] = await Promise.allSettled([
            apiFetchServer<HedgeRegistro[]>("/financeiro/hedge/registros"),
            apiFetchServer<ContratoFuturo[]>("/financeiro/hedge/contratos")
        ]);

        if (registrosRes.status === "fulfilled") initialRegistros = registrosRes.value;
        if (contratosRes.status === "fulfilled") contratos = contratosRes.value;
    } catch (e) {
        // Ignora e deixa o Client component resolver
    }

    return (
        <RegistrosClient 
            initialRegistros={initialRegistros}
            contratos={contratos}
        />
    );
}
