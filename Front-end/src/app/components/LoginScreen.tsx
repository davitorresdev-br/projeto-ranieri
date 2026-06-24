import { useState } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { AlertCircle, Lock, ShieldCheck } from "lucide-react";
import { Role } from "./types";
import { API_BASE_URL } from "../config";

const SESSION_KEY = "acalanto_session";
export type Session = { name: string; role: Role; method: "local"; isSuperAdmin?: boolean };
type Props = { onLogin: (session: Session) => void };

function saveSession(session: Session) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function getStoredSession(): Session | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}

export function clearSession() {
  localStorage.removeItem(SESSION_KEY);
}

export function LoginScreen({ onLogin }: Props) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState(() => localStorage.getItem("acalanto_last_user") ?? "");
  const [pass, setPass] = useState("");
  const [nome, setNome] = useState("");
  const [error, setError] = useState("");

  const trocarModo = (novo: "login" | "register") => {
    setMode(novo);
    setError("");
    setPass("");
  };

  const handleLocalLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!username.trim() || !pass) {
      setError("Por favor, preencha todos os campos.");
      return;
    }
    try {
      const response = await fetch(`${API_BASE_URL}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username.trim(), password: pass }),
      });
      const data = await response.json();
      if (response.ok && data.status === "sucesso") {
        localStorage.setItem("acalanto_last_user", username.trim());
        const session: Session = {
          name: data.name,
          role: data.role as Role,
          method: "local",
          isSuperAdmin: data.isSuperAdmin === true,
        };
        saveSession(session);
        onLogin(session);
      } else {
        setError(data.erro || "Usuário ou senha incorretos.");
      }
    } catch (err) {
      setError("Erro ao conectar com o servidor local.");
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!nome.trim() || !username.trim() || !pass) {
      setError("Preencha nome, usuário e senha.");
      return;
    }
    try {
      const response = await fetch(`${API_BASE_URL}/api/registrar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: username.trim(),
          password: pass,
          nome_completo: nome.trim(),
        }),
      });
      const data = await response.json();
      if (response.ok && data.status === "sucesso") {
        // Conta criada como Coordenador — já entra direto no sistema.
        localStorage.setItem("acalanto_last_user", username.trim().toLowerCase());
        const session: Session = {
          name: data.name,
          role: data.role as Role,
          method: "local",
          isSuperAdmin: data.isSuperAdmin === true,
        };
        saveSession(session);
        onLogin(session);
      } else {
        setError(data.erro || "Não foi possível criar a conta.");
      }
    } catch (err) {
      setError("Erro ao conectar com o servidor local.");
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-[var(--brand-slate)] p-6">
      <div className="w-full max-w-5xl grid md:grid-cols-2 rounded-2xl overflow-hidden shadow-xl border border-[var(--brand-border)] bg-white">

        {/* Painel Esquerdo Visual */}
        <div className="relative hidden md:flex flex-col justify-between p-10 bg-[var(--brand-blue)] text-white overflow-hidden">
          <div className="absolute inset-0 opacity-20">
            <svg viewBox="0 0 400 400" className="w-full h-full">
              <circle cx="80" cy="80" r="120" fill="white" />
              <circle cx="320" cy="340" r="160" fill="white" opacity="0.6" />
            </svg>
          </div>
          <div className="relative z-10">
            <div className="w-16 h-16 rounded-xl bg-white text-[var(--brand-blue)] flex items-center justify-center font-bold text-2xl">IA</div>
          </div>
          <div className="relative z-10">
            <p className="text-2xl font-semibold leading-tight">Portal de Gerenciamento de Impressão</p>
            <p className="mt-2 opacity-80">Instituto Acalanto de Ensino</p>
            <div className="mt-6 flex items-center gap-2 opacity-80">
              <ShieldCheck size={18} />
              <span className="text-sm">Acesso restrito · Rede interna do colégio</span>
            </div>
          </div>
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-[var(--brand-red)]" />
        </div>

        {/* Painel Direito (Formulário de acesso local) */}
        <div className="p-8 md:p-12 flex flex-col justify-center">
          <div className="mb-6">
            <p className="text-[var(--brand-blue)] text-xs font-bold tracking-widest">
              {mode === "login" ? "SESSÃO RESTRITA" : "NOVA CONTA"}
            </p>
            <h1 className="mt-1 text-2xl font-bold text-slate-900">Instituto Acalanto de Ensino</h1>
            <p className="text-slate-500 mt-1">
              {mode === "login"
                ? "Acesse com o seu usuário e senha do servidor local."
                : "Crie a sua conta de acesso ao portal."}
            </p>
          </div>

          <form onSubmit={mode === "login" ? handleLocalLogin : handleRegister} className="space-y-4">
            {mode === "register" && (
              <div className="space-y-2">
                <Label htmlFor="nome">Nome completo</Label>
                <Input
                  id="nome"
                  value={nome}
                  onChange={(e) => { setNome(e.target.value); setError(""); }}
                  placeholder="Ex.: Maria Souza"
                />
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="user">Usuário do servidor local</Label>
              <Input
                id="user"
                value={username}
                onChange={(e) => { setUsername(e.target.value); setError(""); }}
                placeholder="usuario.local"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="pass">Senha</Label>
              <Input
                id="pass"
                type="password"
                value={pass}
                onChange={(e) => { setPass(e.target.value); setError(""); }}
                placeholder="••••••••"
              />
            </div>

            {error && (
              <div className="flex items-start gap-2 rounded-md bg-red-50 border border-red-200 px-3 py-2.5">
                <AlertCircle size={15} className="text-[var(--brand-red)] mt-0.5 flex-shrink-0" />
                <p className="text-red-700 text-xs">{error}</p>
              </div>
            )}

            <Button type="submit" className="w-full h-11 bg-[var(--brand-blue)] hover:bg-[var(--brand-blue-hover)] text-white transition">
              <Lock size={16} className="mr-2" />
              {mode === "login" ? "Entrar" : "Criar conta e entrar"}
            </Button>
          </form>

          <p className="text-center text-sm text-slate-500 mt-5">
            {mode === "login" ? (
              <>
                Não tem conta?{" "}
                <button type="button" onClick={() => trocarModo("register")} className="text-[var(--brand-blue)] font-medium hover:underline">
                  Criar conta
                </button>
              </>
            ) : (
              <>
                Novas contas entram como{" "}
                <span className="font-medium text-slate-600">Coordenador</span>. Já tem conta?{" "}
                <button type="button" onClick={() => trocarModo("login")} className="text-[var(--brand-blue)] font-medium hover:underline">
                  Entrar
                </button>
              </>
            )}
          </p>
        </div>

      </div>
    </div>
  );
}
