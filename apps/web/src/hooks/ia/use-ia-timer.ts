"use client";

import React from "react";

/**
 * Hook para gerenciar o tempo de decisão.
 * Útil para telemetria de UX.
 */
export function useIATimer() {
    const startTime = React.useRef<number | null>(null);

    React.useEffect(() => {
        startTime.current = Date.now();
    }, []);

    const getElapsedTime = React.useCallback(() => {
        if (startTime.current === null) {
            return 0;
        }

        return Math.max(0, Math.round(Date.now() - startTime.current));
    }, []);

    return { getElapsedTime };
}
