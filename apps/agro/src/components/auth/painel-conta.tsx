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
import { SessionHeartbeat } from "@/components/auth/session-heartbeat";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
        <div className="size-8 border-2 border-primary border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-xs text-muted-foreground">Verificando sessão individual...</p>
      </div>
    );
  }

  // --- SE ESTIVER AUTENTICADO ---
  if (user) {
    return (
      <div className="flex flex-col gap-6">
        <SessionHeartbeat />
        {/* Banner de Mensagem */}
        {message && (
          <Alert
            variant={
              message.type === "success"
                ? "success"
                : message.type === "error"
                ? "destructive"
                : "info"
            }
          >
            {message.type === "success" ? (
              <CheckCircle2 className="size-4" />
            ) : (
              <AlertCircle className="size-4" />
            )}
            <AlertDescription className="text-xs">{message.text}</AlertDescription>
          </Alert>
        )}

        {/* Card do Perfil Individual Segregado */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2.5">
              <div className="size-9 rounded-sm bg-primary/10 text-primary flex items-center justify-center">
                <User className="size-4" />
              </div>
              <div>
                <CardTitle className="text-sm font-semibold text-foreground">{user.nome}</CardTitle>
                <CardDescription className="text-xs text-muted-foreground">{user.email}</CardDescription>
              </div>
            </div>
            <CardAction>
              <Badge variant="success">
                INDIVIDUAL FREE
              </Badge>
            </CardAction>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
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
                  <ShieldCheck className="size-3.5 text-emerald-500" />
                  Sessão HttpOnly Segregada
                </span>
              </div>
              <div className="p-2.5 rounded-sm bg-muted/40 border border-border flex flex-col gap-1">
                <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Status de E-mail</span>
                <span className="text-[11px] text-foreground flex items-center gap-1.5">
                  {user.emailVerificado ? (
                    <>
                      <CheckCircle2 className="size-3.5 text-emerald-500" />
                      Verificado
                    </>
                  ) : (
                    <>
                      <Clock className="size-3.5 text-amber-500" />
                      Pendente de confirmação
                    </>
                  )}
                </span>
              </div>
              <div className="p-2.5 rounded-sm bg-muted/40 border border-border flex flex-col gap-1">
                <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Isolamento do SaaS</span>
                <span className="text-[11px] text-foreground flex items-center gap-1.5">
                  <Database className="size-3.5 text-primary" />
                  Zero Tenant / Zero Postgres Pool
                </span>
              </div>
            </div>

            {/* Caixa de Confirmação de E-mail Pendente */}
            {!user.emailVerificado && (
              <Alert variant="warning">
                <Clock className="size-4" />
                <AlertTitle className="text-xs">Confirmação de E-mail Pendente</AlertTitle>
                <AlertDescription className="text-xs flex flex-col gap-2">
                  <span>
                    Insira o código numérico de 6 dígitos enviado para seu e-mail para validar sua conta.
                  </span>
                  <form onSubmit={handleVerifyEmail} className="flex flex-wrap items-center gap-2 pt-1">
                    <div className="flex-1 min-w-[140px] max-w-[200px]">
                      <Input
                        id="input-codigo-verificacao"
                        type="text"
                        maxLength={6}
                        placeholder="000000"
                        value={codigoVerificacaoInput}
                        onChange={(e) => setCodigoVerificacaoInput(e.target.value.replace(/\D/g, ""))}
                        className="text-center font-mono tracking-widest text-xs"
                        required
                      />
                    </div>
                    <Button
                      type="submit"
                      variant="outline"
                      size="sm"
                      disabled={submitting || codigoVerificacaoInput.length !== 6}
                    >
                      <CheckCircle2 className="size-3.5" />
                      <span>Confirmar Código</span>
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={handleResendVerification}
                      disabled={submitting}
                    >
                      Reenviar
                    </Button>
                  </form>
                </AlertDescription>
              </Alert>
            )}

            <Alert variant="default">
              <Info className="size-4 text-primary" />
              <AlertTitle className="text-xs">Fundação de Identidade Segregada Ativa</AlertTitle>
              <AlertDescription className="text-xs">
                Sua conta individual opera exclusivamente no repositório segregado de identidades do DeepFarms Agro.
                Ela não cria empresas artificiais (tenants), não consome o pool de conexões do SaaS comercial e não gera qualquer cobrança.
              </AlertDescription>
            </Alert>
          </CardContent>
          <CardFooter className="flex justify-between items-center">
            <span className="text-[10px] text-muted-foreground">
              Membro desde: {new Date(user.createdAt).toLocaleDateString("pt-BR")}
            </span>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleLogout}
              disabled={submitting}
            >
              <LogOut className="size-3.5" />
              <span>Sair da conta</span>
            </Button>
          </CardFooter>
        </Card>

        {/* Seção Informativa do Futuro Cofre Segregado (BYOK) */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <div className="size-7 rounded-sm bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center">
                <KeyRound className="size-3.5" />
              </div>
              <div>
                <CardTitle className="text-xs font-semibold uppercase tracking-wider">Cofre de Credenciais Segregado (BYOK)</CardTitle>
                <CardDescription className="text-[11px]">Arquitetura e contratos de criptografia para provedores de mercado</CardDescription>
              </div>
            </div>
            <CardAction>
              <Badge variant="warning">
                FASE C2 — ESPECIFICAÇÃO
              </Badge>
            </CardAction>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <div className="p-3 rounded-sm bg-muted/40 border border-border flex flex-col gap-2 text-xs">
              <div className="flex items-center gap-2 font-medium text-foreground text-[11px]">
                <Layers className="size-3.5 text-primary" />
                <span>Garantias Arquiteturais da Fase C2</span>
              </div>
              <ul className="flex flex-col gap-1.5 text-[10px] text-muted-foreground">
                <li className="flex items-start gap-1.5">
                  <CheckCircle2 className="size-3 text-emerald-500 shrink-0 mt-0.5" />
                  <span><strong>Envelope Encryption AES-256-GCM:</strong> chaves de dados (DEK) locais cifradas sob Master Key no KMS com AAD vinculado ao ID do usuário individual.</span>
                </li>
                <li className="flex items-start gap-1.5">
                  <CheckCircle2 className="size-3 text-emerald-500 shrink-0 mt-0.5" />
                  <span><strong>Zero Armazenamento no Navegador:</strong> credenciais jamais trafegam ou repousam em localStorage ou cookies do frontend.</span>
                </li>
                <li className="flex items-start gap-1.5">
                  <CheckCircle2 className="size-3 text-emerald-500 shrink-0 mt-0.5" />
                  <span><strong>Isolamento Criptográfico Estrito:</strong> impossibilidade de descriptografia cruzada entre usuários ou vazamento para o SaaS comercial.</span>
                </li>
              </ul>
            </div>

            <div className="p-3 rounded-sm border border-dashed border-border bg-background text-center flex flex-col gap-1">
              <p className="text-[11px] font-medium text-foreground">Conexão com Provedores Externos Bloqueada</p>
              <p className="text-[10px] text-muted-foreground">
                Nesta fase (C2), o registro de chaves reais de fornecedores (Twelve Data, Polygon, IBKR) está estritamente desabilitado por conformidade com as restrições da tarefa.
              </p>
            </div>
          </CardContent>
          <CardFooter>
            <Button asChild variant="outline" size="sm" className="w-full">
              <Link href="/mercado">
                <span>Acessar Cotações Públicas do Mercado</span>
                <ArrowRight className="size-3.5" />
              </Link>
            </Button>
          </CardFooter>
        </Card>
      </div>
    );
  }

  // --- SE ESTIVER ANÔNIMO (VISITANTE) ---
  return (
    <div className="flex flex-col gap-6">
      {/* Banner de Mensagem */}
      {message && (
        <Alert
          variant={
            message.type === "success"
              ? "success"
              : message.type === "error"
              ? "destructive"
              : "info"
          }
        >
          {message.type === "success" ? (
            <CheckCircle2 className="size-4" />
          ) : (
            <AlertCircle className="size-4" />
          )}
          <AlertDescription className="text-xs">{message.text}</AlertDescription>
        </Alert>
      )}

      {/* Destaque da Independência Anônima */}
      <Alert variant="success">
        <ShieldCheck className="size-4" />
        <AlertTitle className="text-xs">Acesso Público 100% Gratuito e Anônimo</AlertTitle>
        <AlertDescription className="text-xs flex flex-col gap-2">
          <span>
            O DeepFarms Agro não exige login para uso diário. As cotações da PTAX oficial, os indicadores econômicos do BCB, as estatísticas do IBGE/SIDRA e as calculadoras rurais continuam abertos e livres de cadastro para todos os produtores.
          </span>
          <div className="flex flex-wrap gap-2 pt-1">
            <Button asChild variant="outline" size="sm">
              <Link href="/mercado">
                <span>Ver Mercado Público</span>
                <ArrowRight className="size-3" />
              </Link>
            </Button>
            <Button asChild variant="outline" size="sm">
              <Link href="/calculadoras">
                <span>Calculadoras Rurais</span>
                <ArrowRight className="size-3" />
              </Link>
            </Button>
          </div>
        </AlertDescription>
      </Alert>

      {/* Card de Autenticação Opcional */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold">Conta Individual DeepFarms Agro</CardTitle>
          <CardAction>
            <Tabs
              value={tab === "forgot" ? "login" : tab}
              onValueChange={(next) => {
                if (next === "login" || next === "register") {
                  setTab(next);
                  setMessage(null);
                }
              }}
            >
              <TabsList className="h-8 p-0.5">
                <TabsTrigger value="login" className="h-7 px-2.5 text-xs">
                  Entrar
                </TabsTrigger>
                <TabsTrigger value="register" className="h-7 px-2.5 text-xs">
                  Cadastrar
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </CardAction>
          <CardDescription className="text-xs">
            {tab === "login"
              ? "Acesse sua identidade individual segregada para futuras integrações BYOK."
              : tab === "register"
              ? "Crie sua conta individual gratuita sem criar empresas comerciais."
              : "Recupere o acesso à sua conta individual com código seguro."}
          </CardDescription>
        </CardHeader>

        <CardContent className="flex flex-col gap-4">
          {tab === "login" && (
            <form onSubmit={handleLogin} className="flex flex-col gap-3">
              <div className="flex flex-col gap-1">
                <Label htmlFor="login-email" className="text-xs">E-mail</Label>
                <Input
                  id="login-email"
                  type="email"
                  required
                  placeholder="produtor@fazenda.com.br"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="text-xs"
                />
              </div>
              <div className="flex flex-col gap-1">
                <div className="flex justify-between items-center">
                  <Label htmlFor="login-senha" className="text-xs">Senha</Label>
                  <Button
                    type="button"
                    variant="link"
                    size="xs"
                    onClick={() => { setTab("forgot"); setMessage(null); }}
                    className="h-auto p-0 text-[10px]"
                  >
                    Esqueceu a senha?
                  </Button>
                </div>
                <Input
                  id="login-senha"
                  type="password"
                  required
                  placeholder="••••••••••••"
                  value={senha}
                  onChange={(e) => setSenha(e.target.value)}
                  className="text-xs"
                />
              </div>
              <Button type="submit" variant="default" size="sm" className="w-full" disabled={submitting}>
                <Lock className="size-3.5" />
                <span>{submitting ? "Entrando..." : "Entrar na Conta Individual"}</span>
              </Button>
            </form>
          )}

          {tab === "register" && (
            <form onSubmit={handleRegister} className="flex flex-col gap-3">
              <div className="flex flex-col gap-1">
                <Label htmlFor="reg-nome" className="text-xs">Nome Completo</Label>
                <Input
                  id="reg-nome"
                  type="text"
                  required
                  placeholder="José da Silva"
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  className="text-xs"
                />
              </div>
              <div className="flex flex-col gap-1">
                <Label htmlFor="reg-email" className="text-xs">E-mail</Label>
                <Input
                  id="reg-email"
                  type="email"
                  required
                  placeholder="produtor@fazenda.com.br"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="text-xs"
                />
              </div>
              <div className="flex flex-col gap-1">
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
                  className="text-xs"
                />
              </div>
              <Button type="submit" variant="default" size="sm" className="w-full" disabled={submitting}>
                <ShieldCheck className="size-3.5" />
                <span>{submitting ? "Criando Conta..." : "Criar Conta Individual Gratuita"}</span>
              </Button>
            </form>
          )}

          {tab === "forgot" && (
            <div className="flex flex-col gap-3">
              {stepReset === "request" ? (
                <form onSubmit={handleForgotPassword} className="flex flex-col gap-3">
                  <div className="flex flex-col gap-1">
                    <Label htmlFor="forgot-email" className="text-xs">E-mail cadastrado</Label>
                    <Input
                      id="forgot-email"
                      type="email"
                      required
                      placeholder="seu-email@dominio.com.br"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="text-xs"
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
                <form onSubmit={handleConfirmReset} className="flex flex-col gap-3">
                  <div className="flex flex-col gap-1">
                    <Label htmlFor="reset-token" className="text-xs">Código de Recuperação</Label>
                    <Input
                      id="reset-token"
                      type="text"
                      required
                      placeholder="Cole aqui o token recebido"
                      value={resetToken}
                      onChange={(e) => setResetToken(e.target.value)}
                      className="text-xs font-mono"
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <Label htmlFor="reset-nova-senha" className="text-xs">Nova Senha</Label>
                    <Input
                      id="reset-nova-senha"
                      type="password"
                      required
                      placeholder="Mínimo 8 caracteres"
                      value={novaSenha}
                      onChange={(e) => setNovaSenha(e.target.value)}
                      className="text-xs"
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

        <CardFooter className="justify-center">
          <div className="w-full text-center text-[10px] text-muted-foreground flex items-center justify-center gap-1.5">
            <Lock className="size-3 text-emerald-500" />
            <span>Sessões HttpOnly SameSite protegidas contra XSS e CSRF. Zero dados em localStorage.</span>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}
