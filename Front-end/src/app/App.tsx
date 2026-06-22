import { useEffect, useState } from "react";
import { Toaster } from "./components/ui/sonner";
import { toast } from "sonner";
import { LoginScreen, getStoredSession, clearSession, Session } from "./components/LoginScreen";
import { TopNavbar } from "./components/TopNavbar";
import { SubmissionForm, SubmissionDraft } from "./components/SubmissionForm";
import { InfoSidebar } from "./components/InfoSidebar";
import { ConfirmationModal } from "./components/ConfirmationModal";
import { QueueMetricsCards } from "./components/QueueMetricsCards";
import { PrintQueueTable } from "./components/PrintQueueTable";
import { JobStatus, PrintJob, Role } from "./components/types";
import { API_BASE_URL } from "./config";

type View = "login" | "dashboard" | "queue";

export default function App() {
  const [view, setView] = useState<View>("login");
  const [role, setRole] = useState<Role>("COORDENADOR");
  const [isSuperAdmin, setIsSuperAdmin] = useState(false);
  const [currentUser, setCurrentUser] = useState("");
  const [jobs, setJobs] = useState<PrintJob[]>([]);
  const [draft, setDraft] = useState<SubmissionDraft | null>(null);
  const [formResetKey, setFormResetKey] = useState(0);

  // 1. VERIFICA SESSÃO
  useEffect(() => {
    const session = getStoredSession();
    if (session) {
      setCurrentUser(session.name);
      setRole(session.role);
      setIsSuperAdmin(session.isSuperAdmin === true);
      setView("dashboard");
      carregarFila(session.role);
    }
  }, []);

  // 2. BUSCAR FILA REAL NO BACKEND
  const carregarFila = async (roleOverride?: Role) => {
    try {
      const session = getStoredSession();
      const nomeParaBusca = session ? session.name : currentUser;
      const roleParaBusca = roleOverride ?? (session ? session.role : role);

      if (!nomeParaBusca) return;

      // Passamos os dados de forma transparente na URL, eliminando erros de cookie cross-origin
      const url = `${API_BASE_URL}/api/fila?user_name=${encodeURIComponent(nomeParaBusca)}&user_role=${encodeURIComponent(roleParaBusca)}`;

      const response = await fetch(url, { method: "GET" });

      if (response.ok) {
        const data = await response.json();

        const filaFormatada: PrintJob[] = data.pedidos.map((p: any) => ({
          id: p.id.toString(),
          sender: p.remetente,
          subject: p.materia_turma.split(' — ')[0] || "Geral",
          turma: p.materia_turma.split(' — ')[1] || "-",
          fileName: p.arquivo,
          copies: p.copias,
          color: "Preto e Branco", 
          pageMode: "Apenas Frente",
          finishing: "Nenhum",
          status: p.status as JobStatus,
          submittedAt: Date.now(), 
        }));

        setJobs(filaFormatada);
      }
    } catch (error) {
      console.error("Erro ao carregar a fila:", error);
    }
  };

  // 3. ENVIAR DADOS REAIS PARA O BACKEND
  const handleConfirm = async () => {
    if (!draft) return;
    
    const session = getStoredSession();
    const nomeRemetente = session ? session.name : currentUser;

    const formData = new FormData();
    formData.append("user_name", nomeRemetente); // <--- ENVIA O NOME REAL LOGADO PELO GOOGLE OU LOCAL!
    formData.append("materia", draft.subject);
    formData.append("turma", draft.turma); 
    formData.append("copias", draft.copies.toString());
    formData.append("cor", draft.color);
    formData.append("frente_verso", draft.pageMode); 
    formData.append("acabamento", draft.finishing);
    
    if (draft.file) {
      formData.append("arquivo", draft.file);
    } else {
      toast.error("É obrigatório anexar um ficheiro PDF.");
      return; // Interrompe o envio se não houver ficheiro
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/enviar`, {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (response.ok && result.status === "sucesso") {
        toast.success("Documento enviado para a fila de impressão com sucesso!");
        setDraft(null);
        setFormResetKey((k) => k + 1);
        setView("queue");
        carregarFila();
      } else {
        toast.error(result.erro || "Ocorreu um erro ao enviar o documento.");
      }
    } catch (error) {
      console.error("Erro de rede:", error);
      toast.error("Erro ao comunicar com o servidor da impressora.");
    }
  };

  const handleLogin = (session: Session) => {
    setCurrentUser(session.name);
    setRole(session.role);
    setIsSuperAdmin(session.isSuperAdmin === true);
    setView("dashboard");
    carregarFila(session.role);
  };

  const handleLogout = () => {
    clearSession();
    setCurrentUser("");
    setRole("COORDENADOR");
    setIsSuperAdmin(false);
    setJobs([]);
    setView("login");
  };

  // Alterna o modo de visualização (Professor / Dep. de T.I.).
  // Só o usuário Admin (isSuperAdmin) pode usar isso a qualquer momento —
  // qualquer outra pessoa é apenas avisada; o papel real dela continua
  // sendo exatamente o que está cadastrado no banco de dados.
  const handleSetRole = (novoRole: Role) => {
    if (!isSuperAdmin) {
      toast.error("Apenas o Administrador pode alternar entre os modos.");
      return;
    }
    setRole(novoRole);
    carregarFila(novoRole);
  };

  // Funções temporárias da UI
  const cycleStatus = (id: string) => {
    toast.info("A atualização de status será feita pela impressora física.");
  };

  const reprint = (id: string) => {
    toast.info("Reimpressão em desenvolvimento.");
  };

  const isAdmin = role === "TI";
  const visibleMetricJobs = jobs; // O backend já filtrou adequadamente por escopo!
  const pendingCount = jobs.filter((j) => j.status === "Pendente").length;

  return (
    <div className="min-h-screen bg-[var(--brand-slate)]">
      {view !== "login" && (
        <TopNavbar
          view={view}
          setView={setView}
          role={role}
          setRole={handleSetRole}
          isSuperAdmin={isSuperAdmin}
          currentUser={`${currentUser} (${isAdmin ? "Dep. de TI" : "Professor"})`}
          pendingCount={pendingCount}
          onLogout={handleLogout}
        />
      )}

      <main className={`max-w-7xl mx-auto px-6 ${view === "login" ? "py-0" : "py-8"}`}>
        {view === "login" && <LoginScreen onLogin={handleLogin} />}

        {view === "dashboard" && (
          <>
            <div className="mb-6">
              <h1 style={{ fontSize: "1.75rem", fontWeight: 700, color: "#0f172a" }}>
                Painel de Solicitações
              </h1>
              <p className="text-slate-500 mt-1">
                Envie documentos para impressão e acompanhe sua fila em tempo real.
              </p>
            </div>

            <div className="grid lg:grid-cols-[1fr_400px] gap-6">
              <SubmissionForm key={formResetKey} onReview={setDraft} />
              <InfoSidebar />
            </div>
          </>
        )}

        {view === "queue" && (
          <div className="space-y-6">
            <div>
              <h1 style={{ fontSize: "1.75rem", fontWeight: 700, color: "#0f172a" }}>
                {isAdmin ? "Fila de Impressão" : "Minhas Impressões"}
              </h1>
              <p className="text-slate-500 mt-1">
                {isAdmin
                  ? "Visão completa de todos os documentos enviados à impressora central."
                  : "Acompanhe o status dos documentos que você enviou."}
              </p>
            </div>
            
            <QueueMetricsCards jobs={visibleMetricJobs} />
            
            <PrintQueueTable
              jobs={jobs} // Passamos a lista direta sem filtros adicionais de front
              role={role}
              currentUser={currentUser}
              onCycleStatus={cycleStatus}
              onReprint={reprint}
            />
          </div>
        )}
      </main>

      <ConfirmationModal
        draft={draft}
        onCancel={() => setDraft(null)}
        onConfirm={handleConfirm}
      />

      <Toaster position="top-right" richColors />
    </div>
  );
}
