"use client";

import { useEffect } from "react";

import { initPwaUpdateListeners } from "@/lib/stores/pwa-update-store";

/**
 * Componente silencioso montado no root layout para monitorar atualizações do Service Worker.
 *
 * Args:
 *   Nenhum argumento.
 *
 * Return:
 *   null: Não renderiza elementos visuais próprios.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
export function PwaUpdateLifecycle() {
  useEffect(() => initPwaUpdateListeners(), []);
  return null;
}
