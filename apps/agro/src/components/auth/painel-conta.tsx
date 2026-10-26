"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import {
  ShieldCheck,
  KeyRound,
  Lock,
  User,
  LogOut,
  CheckCircle2,
  AlertCircle,
  Clock,
  Database,
  ArrowRight,
  Info,
  Layers,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SessionHeartbeat } from "@/components/auth/session-heartbeat";
import {
  AgroUsuario,
  fetchCurrentAgroUser,
  loginAgroUser,
  logoutAgroUser,
  registerAgroUser,
  requestAgroPasswordReset,
  resendAgroVerification,
  resetAgroPassword,
  verifyAgroEmail,
} from "@/lib/auth/agro-auth";

type AuthTab = "login" | "register" | "forgot";

export function PainelConta() {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<AgroUsuario | null>(null);
  const [tab, setTab] = useState<AuthTab>("login");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error" | "info"; text: string } | null>(null);

  // Form states
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [nome, setNome] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [novaSenha, setNovaSenha] = useState("");
  const [stepReset, setStepReset] = useState<"request" | "confirm">("request");
  const [codigoVerificacaoInput, setCodigoVerificacaoInput] = useState("");

  useEffect(() => {
    let mounted = true;
    fetchCurrentAgroUser()
      .then((currentUser) => {
        if (mounted) {
          setUser(currentUser);
          setLoading(false);
        }
      })
      .catch(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setMessage(null);
    try {
      const usuario = await loginAgroUser({ email, senha });
      setUser(usuario);
      setMessage({ type: "success", text: `Bem-vindo(a), ${usuario.nome}!` });
      setSenha("");
    } catch (err: unknown) {
      const errMessage = err instanceof Error ? err.message : "Erro ao efetuar login.";
      setMessage({ type: "error", text: errMessage });
    } finally {
      setSubmitting(false);
    }
  };

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setMessage(null);
    try {
      const usuario = await registerAgroUser({ nome, email, senha });
      setUser(usuario);
      setMessage({
        type: "success",
        text: "Conta individual criada com sucesso! Sessão segura iniciada.",
      });
      setSenha("");
    } catch (err: unknown) {
      const errMessage = err instanceof Error ? err.message : "Erro ao criar conta.";
      setMessage({ type: "error", text: errMessage });
    } finally {
      setSubmitting(false);
    }
  };

  const handleLogout = async () => {
    setSubmitting(true);
    setMessage(null);
    try {
      await logoutAgroUser();
      setUser(null);
      setMessage({ type: "info", text: "Sessão encerrada com sucesso." });
    } catch {
      setMessage({ type: "error", text: "Falha ao encerrar sessão." });
    } finally {
      setSubmitting(false);
    }
  };

  const handleForgotPassword = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setMessage(null);
    try {
      const resp = await requestAgroPasswordReset(email);
      setMessage({
        type: "success",
        text: resp.mensagem,
      });
      if (resp.tokenSimulado) {
        setResetToken(resp.tokenSimulado);
      }
      setStepReset("confirm");
    } catch (err: unknown) {
      const errMessage = err instanceof Error ? err.message : "Falha na solicitação.";
      setMessage({ type: "error", text: errMessage });
    } finally {
      setSubmitting(false);
    }
  };

  const handleConfirmReset = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setMessage(null);
    try {
      const resp = await resetAgroPassword({ token: resetToken, novaSenha });
      setMessage({ type: "success", text: `${resp.mensagem} Você já pode fazer login com a nova senha.` });
      setTab("login");
      setStepReset("request");
      setNovaSenha("");
      setResetToken("");
    } catch (err: unknown) {
      const errMessage = err instanceof Error ? err.message : "Falha ao redefinir senha.";
      setMessage({ type: "error", text: errMessage });
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerifyEmail = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setMessage(null);
    try {
      const resp = await verifyAgroEmail({ codigo: codigoVerificacaoInput });
      if (user) {
        setUser({ ...user, emailVerificado: true });
      }
      setMessage({ type: "success", text: resp.mensagem || "E-mail verificado com sucesso!" });
      setCodigoVerificacaoInput("");
    } catch (err: unknown) {
      const errMessage = err instanceof Error ? err.message : "Falha ao verificar código.";
      setMessage({ type: "error", text: errMessage });
    } finally {
      setSubmitting(false);
    }
  };

  const handleResendVerification = async () => {
    setSubmitting(true);
    setMessage(null);
    try {
      const resp = await resendAgroVerification();
      setMessage({ type: "info", text: resp.mensagem || "Novo código de verificação enviado para seu e-mail." });
    } catch (err: unknown) {
      const errMessage = err instanceof Error ? err.message : "Falha ao reenviar código.";
      setMessage({ type: "error", text: errMessage });
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-xs text-muted-foreground">Verificando sessão individual...</p>
      </div>
    );
  }

  // --- SE ESTIVER AUTENTICADO ---
  if (user) {
    return (
      <div className="space-y-6">
        <SessionHeartbeat />
        {/* Banner de Mensagem */}
        {message && (
          <div
            className={`p-3 rounded-sm text-xs flex items-center gap-2 border ${
              message.type === "success"
                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20"
                : message.type === "error"
                ? "bg-destructive/10 text-destructive border-destructive/20"
                : "bg-muted text-foreground border-border"
            }`}
          >
            {message.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
            )}
            <span>{message.text}</span>
          </div>
        )}

        {/* Card do Perfil Individual Segregado */}
        <Card className="rounded-sm border-border bg-card">
          <CardHeader className="pb-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-sm bg-primary/10 text-primary flex items-center justify-center">
                  <User className="w-4 h-4" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold text-foreground">{user.nome}</CardTitle>
                  <CardDescription className="text-xs text-muted-foreground">{user.email}</CardDescription>
                </div>
              </div>
              <Badge variant="outline" className="text-[10px] border-emerald-500/30 text-emerald-600 dark:text-emerald-400 bg-emerald-500/5">
                INDIVIDUAL FREE
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 pt-0">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
              <div className="p-2.5 rounded-sm bg-muted/40 border border-border flex flex-col gap-1">
                <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Identificador Global</span>
                <span className="font-mono text-[11px] text-foreground truncate" title={user.id}>
                  {user.id}
                </span>
              </div>
              <div className="p-2.5 rounded-sm bg-muted/40 border border-border flex flex-col gap-1">
                <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Tipo de Autenticação</span>
                <span className="text-[11px] text-foreground flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
                  Sessão HttpOnly Segregada
                </span>
              </div>
              <div className="p-2.5 rounded-sm bg-muted/40 border border-border flex flex-col gap-1">
                <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Status de E-mail</span>
                <span className="text-[11px] text-foreground flex items-center gap-1.5">
                  {user.emailVerificado ? (
                    <>
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                      Verificado
                    </>
                  ) : (
                    <>
                      <Clock className="w-3.5 h-3.5 text-amber-500" />
                      Pendente de confirmação
                    </>
                  )}
                </span>
              </div>
              <div className="p-2.5 rounded-sm bg-muted/40 border border-border flex flex-col gap-1">
                <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Isolamento do SaaS</span>
                <span className="text-[11px] text-foreground flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5 text-primary" />
                  Zero Tenant / Zero Postgres Pool
                </span>
              </div>
            </div>

            {/* Caixa de Confirmação de E-mail Pendente */}
            {!user.emailVerificado && (
              <div className="p-3 rounded-sm bg-amber-500/10 border border-amber-500/20 text-xs text-foreground space-y-2.5">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-amber-500 flex-shrink-0" />
                  <span className="font-semibold text-xs text-foreground">Confirmação de E-mail Pendente</span>
                </div>
                <p className="text-[11px] text-muted-foreground">
                  Insira o código numérico de 6 dígitos enviado para seu e-mail para validar sua conta.
                </p>
                <form onSubmit={handleVerifyEmail} className="flex flex-wrap items-center gap-2 pt-1">
                  <div className="flex-1 min-w-[140px] max-w-[200px]">
                    <Input
                      id="input-codigo-verificacao"
                      type="text"
                      maxLength={6}
                      placeholder="000000"
                      value={codigoVerificacaoInput}
                      onChange={(e) => setCodigoVerificacaoInput(e.target.value.replace(/\D/g, ""))}
                      className="h-8 text-center font-mono tracking-widest text-xs rounded-sm"
                      required
                    />
                  </div>
                  <Button
                    type="submit"
                    variant="outline"
                    size="sm"
                    disabled={submitting || codigoVerificacaoInput.length !== 6}
                    className="h-8 text-xs border-emerald-500/30 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/10"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                    Confirmar Código
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={handleResendVerification}
                    disabled={submitting}
                    className="h-8 text-xs text-muted-foreground hover:text-foreground"
                  >
                    Reenviar
                  </Button>
                </form>
              </div>
            )}

            <div className="p-3 rounded-sm bg-primary/5 border border-primary/20 text-xs text-foreground/90 flex gap-2.5 items-start">
              <Info className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-medium text-[11px]">Fundação de Identidade Segregada Ativa</p>
                <p className="text-[10px] text-muted-foreground leading-relaxed">
                  Sua conta individual opera exclusivamente no repositório segregado de identidades do DeepFarms Agro.
                  Ela não cria empresas artificiais (tenants), não consome o pool de conexões do SaaS comercial e não gera qualquer cobrança.
                </p>
              </div>
            </div>
          </CardContent>
          <CardFooter className="flex justify-between items-center border-t border-border pt-3">
            <span className="text-[10px] text-muted-foreground">
              Membro desde: {new Date(user.createdAt).toLocaleDateString("pt-BR")}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={handleLogout}
              disabled={submitting}
              className="gap-1.5 text-destructive hover:bg-destructive/10 hover:text-destructive border-destructive/30"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Sair da conta</span>
            </Button>
          </CardFooter>
        </Card>

        {/* Seção Informativa do Futuro Cofre Segregado (BYOK) */}
        <Card className="rounded-sm border-border bg-card">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-sm bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center">
                  <KeyRound className="w-3.5 h-3.5" />
                </div>
                <div>
                  <CardTitle className="text-xs font-semibold uppercase tracking-wider">Cofre de Credenciais Segregado (BYOK)</CardTitle>
                  <CardDescription className="text-[11px]">Arquitetura e contratos de criptografia para provedores de mercado</CardDescription>
                </div>
              </div>
              <Badge variant="outline" className="text-[9px] border-amber-500/30 text-amber-600 dark:text-amber-400 bg-amber-500/5">
                FASE C2 — ESPECIFICAÇÃO
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 pt-0">
            <div className="p-3 rounded-sm bg-muted/40 border border-border space-y-2 text-xs">
              <div className="flex items-center gap-2 font-medium text-foreground text-[11px]">
                <Layers className="w-3.5 h-3.5 text-primary" />
                <span>Garantias Arquiteturais da Fase C2</span>
              </div>
              <ul className="space-y-1.5 text-[10px] text-muted-foreground">
                <li className="flex items-start gap-1.5">
                  <CheckCircle2 className="w-3 h-3 text-emerald-500 flex-shrink-0 mt-0.5" />
                  <span><strong>Envelope Encryption AES-256-GCM:</strong> chaves de dados (DEK) locais cifradas sob Master Key no KMS com AAD vinculado ao ID do usuário individual.</span>
                </li>
                <li className="flex items-start gap-1.5">
                  <CheckCircle2 className="w-3 h-3 text-emerald-500 flex-shrink-0 mt-0.5" />
                  <span><strong>Zero Armazenamento no Navegador:</strong> credenciais jamais trafegam ou repousam em localStorage ou cookies do frontend.</span>
                </li>
                <li className="flex items-start gap-1.5">
                  <CheckCircle2 className="w-3 h-3 text-emerald-500 flex-shrink-0 mt-0.5" />
                  <span><strong>Isolamento Criptográfico Estrito:</strong> impossibilidade de descriptografia cruzada entre usuários ou vazamento para o SaaS comercial.</span>
                </li>
              </ul>
            </div>

            <div className="p-3 rounded-sm border border-dashed border-border bg-background text-center space-y-1">
              <p className="text-[11px] font-medium text-foreground">Conexão com Provedores Externos Bloqueada</p>
              <p className="text-[10px] text-muted-foreground">
                Nesta fase (C2), o registro de chaves reais de fornecedores (Twelve Data, Polygon, IBKR) está estritamente desabilitado por conformidade com as restrições da tarefa.
              </p>
            </div>
          </CardContent>
          <CardFooter className="pt-0">
            <Link href="/mercado" className="w-full">
              <Button variant="outline" size="sm" className="w-full gap-1.5">
                <span>Acessar Cotações Públicas do Mercado</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Button>
            </Link>
          </CardFooter>
        </Card>
      </div>
    );
  }

  // --- SE ESTIVER ANÔNIMO (VISITANTE) ---
  return (
    <div className="space-y-6">
      {/* Banner de Mensagem */}
      {message && (
        <div
          className={`p-3 rounded-sm text-xs flex items-center gap-2 border ${
            message.type === "success"
              ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20"
              : message.type === "error"
              ? "bg-destructive/10 text-destructive border-destructive/20"
              : "bg-muted text-foreground border-border"
          }`}
        >
          {message.type === "success" ? (
            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
          )}
          <span>{message.text}</span>
        </div>
      )}

      {/* Destaque da Independência Anônima */}
      <div className="p-4 rounded-sm border border-emerald-500/20 bg-emerald-500/5 space-y-2">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          <h3 className="text-xs font-semibold text-foreground">Acesso Público 100% Gratuito e Anônimo</h3>
        </div>
        <p className="text-[11px] text-muted-foreground leading-relaxed">
          O DeepFarms Agro não exige login para uso diário. As cotações da PTAX oficial, os indicadores econômicos do BCB, as estatísticas do IBGE/SIDRA e as calculadoras rurais continuam abertos e livres de cadastro para todos os produtores.
        </p>
        <div className="flex flex-wrap gap-2 pt-1">
          <Link href="/mercado">
            <Button variant="outline" size="sm" className="h-7 text-[11px] gap-1">
              Ver Mercado Público
              <ArrowRight className="w-3 h-3" />
            </Button>
          </Link>
          <Link href="/calculadoras">
            <Button variant="outline" size="sm" className="h-7 text-[11px] gap-1">
              Calculadoras Rurais
              <ArrowRight className="w-3 h-3" />
            </Button>
          </Link>
        </div>
      </div>

      {/* Card de Autenticação Opcional */}
      <Card className="rounded-sm border-border bg-card">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-semibold">Conta Individual DeepFarms Agro</CardTitle>
            <div className="flex items-center gap-1 bg-muted p-0.5 rounded-sm">
              <button
                type="button"
                onClick={() => { setTab("login"); setMessage(null); }}
                className={`px-2.5 py-1 text-xs rounded-sm transition-colors ${
                  tab === "login"
                    ? "bg-background text-foreground font-medium shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Entrar
              </button>
              <button
                type="button"
                onClick={() => { setTab("register"); setMessage(null); }}
                className={`px-2.5 py-1 text-xs rounded-sm transition-colors ${
                  tab === "register"
                    ? "bg-background text-foreground font-medium shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Cadastrar
              </button>
            </div>
          </div>
          <CardDescription className="text-xs">
            {tab === "login"
              ? "Acesse sua identidade individual segregada para futuras integrações BYOK."
              : tab === "register"
              ? "Crie sua conta individual gratuita sem criar empresas comerciais."
              : "Recupere o acesso à sua conta individual com código seguro."}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4 pt-1">
          {tab === "login" && (
            <form onSubmit={handleLogin} className="space-y-3">
              <div className="space-y-1">
                <Label htmlFor="login-email" className="text-xs">E-mail</Label>
                <Input
                  id="login-email"
                  type="email"
                  required
                  placeholder="produtor@fazenda.com.br"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="h-8 text-xs rounded-sm"
                />
              </div>
              <div className="space-y-1">
                <div className="flex justify-between items-center">
                  <Label htmlFor="login-senha" className="text-xs">Senha</Label>
                  <button
                    type="button"
                    onClick={() => { setTab("forgot"); setMessage(null); }}
                    className="text-[10px] text-primary hover:underline"
                  >
                    Esqueceu a senha?
                  </button>
                </div>
                <Input
                  id="login-senha"
                  type="password"
                  required
                  placeholder="••••••••••••"
                  value={senha}
                  onChange={(e) => setSenha(e.target.value)}
                  className="h-8 text-xs rounded-sm"
                />
              </div>
              <Button type="submit" variant="default" size="sm" className="w-full gap-1.5" disabled={submitting}>
                <Lock className="w-3.5 h-3.5" />
                <span>{submitting ? "Entrando..." : "Entrar na Conta Individual"}</span>
              </Button>
            </form>
          )}

          {tab === "register" && (
            <form onSubmit={handleRegister} className="space-y-3">
              <div className="space-y-1">
                <Label htmlFor="reg-nome" className="text-xs">Nome Completo</Label>
                <Input
                  id="reg-nome"
                  type="text"
                  required
                  placeholder="José da Silva"
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  className="h-8 text-xs rounded-sm"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="reg-email" className="text-xs">E-mail</Label>
                <Input
                  id="reg-email"
                  type="email"
                  required
                  placeholder="produtor@fazenda.com.br"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="h-8 text-xs rounded-sm"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="reg-senha" className="text-xs">Senha Forte (mínimo 8 caracteres)</Label>
                <Input
                  id="reg-senha"
                  type="password"
                  required
                  minLength={8}
                  maxLength={128}
                  placeholder="Mínimo 8 caracteres"
                  value={senha}
                  onChange={(e) => setSenha(e.target.value)}
                  className="h-8 text-xs rounded-sm"
                />
              </div>
              <Button type="submit" variant="default" size="sm" className="w-full gap-1.5" disabled={submitting}>
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>{submitting ? "Criando Conta..." : "Criar Conta Individual Gratuita"}</span>
              </Button>
            </form>
          )}

          {tab === "forgot" && (
            <div className="space-y-3">
              {stepReset === "request" ? (
                <form onSubmit={handleForgotPassword} className="space-y-3">
                  <div className="space-y-1">
                    <Label htmlFor="forgot-email" className="text-xs">E-mail cadastrado</Label>
                    <Input
                      id="forgot-email"
                      type="email"
                      required
                      placeholder="seu-email@dominio.com.br"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="h-8 text-xs rounded-sm"
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setTab("login")}
                      disabled={submitting}
                      className="w-1/3"
                    >
                      Voltar
                    </Button>
                    <Button type="submit" variant="default" size="sm" className="w-2/3" disabled={submitting}>
                      {submitting ? "Enviando..." : "Solicitar Código"}
                    </Button>
                  </div>
                </form>
              ) : (
                <form onSubmit={handleConfirmReset} className="space-y-3">
                  <div className="space-y-1">
                    <Label htmlFor="reset-token" className="text-xs">Código de Recuperação</Label>
                    <Input
                      id="reset-token"
                      type="text"
                      required
                      placeholder="Cole aqui o token recebido"
                      value={resetToken}
                      onChange={(e) => setResetToken(e.target.value)}
                      className="h-8 text-xs font-mono rounded-sm"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="reset-nova-senha" className="text-xs">Nova Senha</Label>
                    <Input
                      id="reset-nova-senha"
                      type="password"
                      required
                      placeholder="Mínimo 8 caracteres"
                      value={novaSenha}
                      onChange={(e) => setNovaSenha(e.target.value)}
                      className="h-8 text-xs rounded-sm"
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setStepReset("request")}
                      disabled={submitting}
                      className="w-1/3"
                    >
                      Voltar
                    </Button>
                    <Button type="submit" variant="default" size="sm" className="w-2/3" disabled={submitting}>
                      {submitting ? "Redefinindo..." : "Salvar Nova Senha"}
                    </Button>
                  </div>
                </form>
              )}
            </div>
          )}
        </CardContent>

        <CardFooter className="flex flex-col gap-2 pt-0 border-t border-border mt-2">
          <div className="w-full text-center text-[10px] text-muted-foreground pt-3 flex items-center justify-center gap-1.5">
            <Lock className="w-3 h-3 text-emerald-500" />
            <span>Sessões HttpOnly SameSite protegidas contra XSS e CSRF. Zero dados em localStorage.</span>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}
