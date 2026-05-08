"use client";

import { Component, type ReactNode } from "react";
import { logger } from "@/lib/logger";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    logger.error("ErrorBoundary", error.message, {
      stack: error.stack,
      component: info.componentStack,
    });
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="flex flex-col items-center justify-center gap-4 min-h-dvh p-6 text-center">
            <div className="text-5xl">⚠️</div>
            <div>
              <h2 className="text-lg font-bold">Algo deu errado</h2>
              <p className="text-sm text-neutral-400 mt-1">
                {this.state.error?.message ?? "Erro desconhecido"}
              </p>
            </div>
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              className="bg-green-600 rounded-2xl px-6 py-3 font-semibold text-sm"
            >
              Tentar novamente
            </button>
            <button
              onClick={() => (window.location.href = "/home")}
              className="text-neutral-400 text-sm underline"
            >
              Voltar ao início
            </button>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
