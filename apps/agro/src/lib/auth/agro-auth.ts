import { agroApiOrigin } from "@/lib/api-url";

/**
 * Cliente de autenticação e identidade integrado à Identidade Global DeepFarms.
 *
 * REGRAS CRÍTICAS:
 * 1. Não persiste tokens sensíveis em localStorage.
 * 2. Utiliza sessões com cookies HttpOnly seguros gerenciados pelo navegador (credentials: "include").
 * 3. Consome a infraestrutura central de identidade (/api/v1/auth/*).
 */

export interface AgroUsuario {
  id: string;
  email: string;
  nome: string;
  ativo: boolean;
  emailVerificado: boolean;
  createdAt: string;
}

export interface AgroAuthResponse {
  sucesso: boolean;
  mensagem: string;
  usuario: AgroUsuario;
  token?: string;
}

export interface AgroForgotPasswordResponse {
  sucesso: boolean;
  mensagem: string;
  tokenSimulado?: string;
}

export interface BrowserLocation {
  hostname: string;
  protocol: string;
}

export function getAgroAuthApiOrigin(location?: BrowserLocation): string {
  void location;
  return agroApiOrigin();
}

function normalizeAgroUsuario(raw: Record<string, unknown>): AgroUsuario {
  return {
    id: String(raw.id || ""),
    email: String(raw.email || ""),
    nome: String(raw.nome || raw.nome_completo || raw.username || "Usuário"),
    ativo: raw.ativo !== false,
    emailVerificado: Boolean(raw.emailVerificado ?? raw.email_verificado ?? true),
    createdAt: String(raw.createdAt || raw.created_at || new Date().toISOString()),
  };
}

export async function fetchCurrentAgroUser(signal?: AbortSignal): Promise<AgroUsuario | null> {
  const origin = getAgroAuthApiOrigin();
  try {
    const response = await fetch(`${origin}/api/v1/auth/me`, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      credentials: "include",
      cache: "no-store",
      signal,
    });

    if (response.status === 401 || response.status === 403) {
      return null;
    }

    if (!response.ok) {
      return null;
    }

    const data: unknown = await response.json();
    if (data && typeof data === "object" && "id" in data && "email" in data) {
      return normalizeAgroUsuario(data as Record<string, unknown>);
    }
    return null;
  } catch {
    return null;
  }
}

export async function registerAgroUser(
  dados: { nome: string; email: string; senha: string },
  signal?: AbortSignal
): Promise<AgroUsuario> {
  const origin = getAgroAuthApiOrigin();
  const response = await fetch(`${origin}/api/v1/auth/register-free`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-Agro-CSRF": "1",
    },
    credentials: "include",
    cache: "no-store",
    body: JSON.stringify(dados),
    signal,
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    let detail = typeof body.detail === "string" ? body.detail : "Falha ao criar conta gratuita.";
    if (response.status === 422 && Array.isArray(body.detail)) {
      const campos = new Set(body.detail.map((item: { loc?: unknown[] }) => item.loc?.[1]));
      const mensagens = [];
      if (campos.has("nome")) mensagens.push("Informe um nome com 2 a 150 caracteres.");
      if (campos.has("email")) mensagens.push("Informe um e-mail válido.");
      if (campos.has("senha")) mensagens.push("A senha deve ter entre 8 e 128 caracteres.");
      detail = mensagens.join(" ") || "Confira os dados informados para criar a conta.";
    }
    throw new Error(detail);
  }

  // Se o endpoint retornou o usuário diretamente
  if (body && typeof body === "object" && "usuario" in body && body.usuario) {
    return normalizeAgroUsuario(body.usuario as Record<string, unknown>);
  }

  // Realiza login automático para inicializar a sessão segura com cookie HttpOnly
  return await loginAgroUser({ email: dados.email, senha: dados.senha }, signal);
}

export async function loginAgroUser(
  dados: { email: string; senha: string },
  signal?: AbortSignal
): Promise<AgroUsuario> {
  const origin = getAgroAuthApiOrigin();
  const response = await fetch(`${origin}/api/v1/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-Agro-CSRF": "1",
    },
    credentials: "include",
    cache: "no-store",
    body: JSON.stringify(dados),
    signal,
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "Falha ao autenticar.";
    throw new Error(detail);
  }

  // Se o login retornou o usuário diretamente
  if (body && typeof body === "object" && "usuario" in body && body.usuario) {
    return normalizeAgroUsuario(body.usuario as Record<string, unknown>);
  }

  // Obtém os dados completos do usuário autenticado via cookie de sessão
  const currentUser = await fetchCurrentAgroUser(signal);
  if (currentUser) {
    return currentUser;
  }

  // Fallback seguro caso o payload do login tenha id e email
  return {
    id: String(body.id || "usr-global"),
    email: dados.email,
    nome: dados.email.split("@")[0],
    ativo: true,
    emailVerificado: true,
    createdAt: new Date().toISOString(),
  };
}

export async function logoutAgroUser(signal?: AbortSignal): Promise<boolean> {
  const origin = getAgroAuthApiOrigin();
  try {
    const response = await fetch(`${origin}/api/v1/auth/logout`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "X-Agro-CSRF": "1",
      },
      credentials: "include",
      cache: "no-store",
      signal,
    });
    return response.ok;
  } catch {
    return false;
  }
}

export async function requestAgroPasswordReset(
  email: string,
  signal?: AbortSignal
): Promise<AgroForgotPasswordResponse> {
  const origin = getAgroAuthApiOrigin();
  const response = await fetch(`${origin}/api/v1/auth/forgot-password`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    cache: "no-store",
    body: JSON.stringify({ email }),
    signal,
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "Falha ao solicitar recuperação de senha.";
    throw new Error(detail);
  }

  return {
    sucesso: body.sucesso !== false,
    mensagem: typeof body.mensagem === "string" ? body.mensagem : "Instruções de recuperação enviadas.",
    tokenSimulado: body.tokenSimulado || body.token,
  };
}

export async function resetAgroPassword(
  dados: { token: string; novaSenha: string },
  signal?: AbortSignal
): Promise<{ sucesso: boolean; mensagem: string }> {
  const origin = getAgroAuthApiOrigin();
  const response = await fetch(`${origin}/api/v1/auth/reset-password`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-Agro-CSRF": "1",
    },
    cache: "no-store",
    body: JSON.stringify({
      token: dados.token,
      nova_senha: dados.novaSenha,
      confirmar_senha: dados.novaSenha,
    }),
    signal,
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "Falha ao redefinir senha.";
    throw new Error(detail);
  }

  return {
    sucesso: body.sucesso !== false,
    mensagem: typeof body.mensagem === "string" ? body.mensagem : "Senha redefinida com sucesso.",
  };
}

export async function verifyAgroEmail(
  dados: { codigo: string },
  signal?: AbortSignal
): Promise<{ sucesso: boolean; mensagem: string }> {
  const origin = getAgroAuthApiOrigin();
  const response = await fetch(`${origin}/api/v1/auth/verify-email`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-Agro-CSRF": "1",
    },
    credentials: "include",
    cache: "no-store",
    body: JSON.stringify({ codigo: dados.codigo }),
    signal,
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "Falha ao verificar e-mail.";
    throw new Error(detail);
  }

  return {
    sucesso: body.sucesso !== false,
    mensagem: typeof body.mensagem === "string" ? body.mensagem : "E-mail verificado com sucesso.",
  };
}

export async function resendAgroVerification(
  signal?: AbortSignal
): Promise<{ sucesso: boolean; mensagem: string }> {
  const origin = getAgroAuthApiOrigin();
  const response = await fetch(`${origin}/api/v1/auth/resend-verification`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "X-Agro-CSRF": "1",
    },
    credentials: "include",
    cache: "no-store",
    signal,
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "Falha ao reenviar código.";
    throw new Error(detail);
  }

  return {
    sucesso: body.sucesso !== false,
    mensagem: typeof body.mensagem === "string" ? body.mensagem : "Código de verificação reenviado com sucesso.",
  };
}

export async function sendAgroHeartbeat(
  signal?: AbortSignal
): Promise<{ ok: boolean; throttled?: boolean }> {
  // Não envia se o navegador estiver offline
  if (typeof navigator !== "undefined" && !navigator.onLine) {
    return { ok: false };
  }

  // Não envia se a aplicação estiver em segundo plano ou em aba inativa
  if (typeof document !== "undefined" && document.visibilityState === "hidden") {
    return { ok: false };
  }

  const origin = getAgroAuthApiOrigin();
  try {
    const response = await fetch(`${origin}/api/v1/auth/heartbeat`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "X-Agro-CSRF": "1",
      },
      credentials: "include",
      cache: "no-store",
      signal,
    });

    if (response.status === 401 || response.status === 403) {
      return { ok: false };
    }

    if (!response.ok) {
      return { ok: false };
    }

    const body = (await response.json().catch(() => ({}))) as {
      ok?: boolean;
      throttled?: boolean;
    };
    return { ok: Boolean(body.ok), throttled: Boolean(body.throttled) };
  } catch {
    return { ok: false };
  }
}

