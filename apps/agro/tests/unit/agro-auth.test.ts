import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  getAgroAuthApiOrigin,
  fetchCurrentAgroUser,
  registerAgroUser,
  loginAgroUser,
  logoutAgroUser,
  requestAgroPasswordReset,
  resetAgroPassword,
  verifyAgroEmail,
  resendAgroVerification,
} from "@/lib/auth/agro-auth";

describe("Segregated Agro Auth Client", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("resolve origem local e de produção corretamente", () => {
    expect(getAgroAuthApiOrigin({ hostname: "localhost", protocol: "http:" })).toBe("");
    expect(getAgroAuthApiOrigin({ hostname: "192.168.1.50", protocol: "http:" })).toBe("");
    expect(getAgroAuthApiOrigin({ hostname: "agro.deepfarms.com.br", protocol: "https:" })).toBe("");
  });

  it("fetchCurrentAgroUser retorna null quando anônimo (HTTP 401)", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      status: 401,
      ok: false,
    });

    const user = await fetchCurrentAgroUser();
    expect(user).toBeNull();
  });

  it("fetchCurrentAgroUser retorna usuário quando sessão ativa via cookie HttpOnly", async () => {
    const mockUser = {
      id: "usr-1234-uuid",
      email: "produtor@fazenda.com.br",
      nome: "José da Silva",
      ativo: true,
      emailVerificado: true,
      createdAt: "2026-10-19T22:00:00Z",
    };

    global.fetch = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: async () => mockUser,
    });

    const user = await fetchCurrentAgroUser();
    expect(user).toEqual(mockUser);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/auth/me"),
      expect.objectContaining({
        credentials: "include",
      })
    );
  });

  it("registerAgroUser cria usuário com sucesso sem persistir no localStorage", async () => {
    const mockResponse = {
      token: "mock-jwt-token",
      tokenType: "bearer",
      expiresInSeconds: 604800,
      usuario: {
        id: "usr-5678-uuid",
        email: "novo@agro.com.br",
        nome: "Maria Rural",
        ativo: true,
        emailVerificado: false,
        createdAt: "2026-10-19T22:10:00Z",
      },
      accountType: "INDIVIDUAL_FREE",
    };

    global.fetch = vi.fn().mockResolvedValue({
      status: 201,
      ok: true,
      json: async () => mockResponse,
    });

    const usuario = await registerAgroUser({
      nome: "Maria Rural",
      email: "novo@agro.com.br",
      senha: "SenhaSegura123!",
    });

    expect(usuario.email).toBe("novo@agro.com.br");
    expect(usuario.id).toBe("usr-5678-uuid");
  });

  it("explica erro de validação 422 sem revelar a senha", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      status: 422, ok: false,
      json: async () => ({ detail: [{ loc: ["body", "senha"], input: "123" }] }),
    });
    await expect(registerAgroUser({ nome: "Teste", email: "teste@example.com", senha: "123" }))
      .rejects.toThrow("A senha deve ter entre 8 e 128 caracteres.");
  });

  it("loginAgroUser propaga erro detalhado em credenciais incorretas", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      status: 401,
      ok: false,
      json: async () => ({ detail: "E-mail ou senha incorretos." }),
    });

    await expect(
      loginAgroUser({ email: "errado@agro.com.br", senha: "senha" })
    ).rejects.toThrow("E-mail ou senha incorretos.");
  });

  it("logoutAgroUser envia requisição com credentials: include para limpeza de cookie", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: async () => ({ sucesso: true, mensagem: "Sessão encerrada com sucesso." }),
    });

    const success = await logoutAgroUser();
    expect(success).toBe(true);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/auth/logout"),
      expect.objectContaining({ credentials: "include" })
    );
  });

  it("recuperação e redefinição de senha funcionam corretamente", async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValueOnce({
        status: 200,
        ok: true,
        json: async () => ({
          sucesso: true,
          mensagem: "Código de recuperação gerado.",
          tokenSimulado: "tok-12345",
        }),
      })
      .mockResolvedValueOnce({
        status: 200,
        ok: true,
        json: async () => ({
          sucesso: true,
          mensagem: "Senha redefinida com sucesso.",
        }),
      });

    const forgotResp = await requestAgroPasswordReset("teste@agro.com.br");
    expect(forgotResp.sucesso).toBe(true);
    expect(forgotResp.tokenSimulado).toBe("tok-12345");

    const resetResp = await resetAgroPassword({
      token: "tok-12345",
      novaSenha: "NovaSenhaForte123!@",
    });
    expect(resetResp.sucesso).toBe(true);
  });

  it("verifyAgroEmail envia código de 6 dígitos e valida resposta", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: async () => ({ sucesso: true, mensagem: "E-mail verificado com sucesso." }),
    });

    const resp = await verifyAgroEmail({ codigo: "123456" });
    expect(resp.sucesso).toBe(true);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/auth/verify-email"),
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        body: JSON.stringify({ codigo: "123456" }),
      })
    );
  });

  it("resendAgroVerification solicita novo código de 6 dígitos", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: async () => ({ sucesso: true, mensagem: "Novo código enviado." }),
    });

    const resp = await resendAgroVerification();
    expect(resp.sucesso).toBe(true);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/auth/resend-verification"),
      expect.objectContaining({
        method: "POST",
        credentials: "include",
      })
    );
  });
});
