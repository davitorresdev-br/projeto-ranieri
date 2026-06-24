import { useEffect, useState } from "react";
import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { Role } from "./types";
import { API_BASE_URL } from "../config";
import { toast } from "sonner";
import { ShieldCheck, GraduationCap, ArrowUpCircle, ArrowDownCircle, Trash2, Users } from "lucide-react";

type Props = {
  // Nome de quem está gerenciando. O backend confere, por esse nome, se a
  // pessoa é mesmo do Departamento de T.I. antes de devolver/alterar nada.
  currentUser: string;
};

type Conta = {
  username: string;
  name: string;
  role: Role;
  isSuperAdmin: boolean;
};

const ROLE_LABEL: Record<string, string> = {
  TI: "Dep. de T.I.",
  COORDENADOR: "Coordenador",
};

export function UserManagementPanel({ currentUser }: Props) {
  const [contas, setContas] = useState<Conta[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [ocupado, setOcupado] = useState<string | null>(null);

  const carregar = async () => {
    if (!currentUser) return;
    setCarregando(true);
    try {
      const url = `${API_BASE_URL}/api/usuarios?user_name=${encodeURIComponent(currentUser)}`;
      const resposta = await fetch(url, { method: "GET" });
      const json = await resposta.json();
      if (resposta.ok) {
        setContas(json.usuarios ?? []);
      } else {
        toast.error(json.erro || "Não foi possível carregar as contas.");
      }
    } catch {
      toast.error("Erro ao comunicar com o servidor.");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentUser]);

  const alterarCargo = async (conta: Conta, novoRole: Role) => {
    setOcupado(conta.username);
    try {
      const resposta = await fetch(`${API_BASE_URL}/api/usuarios/cargo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_name: currentUser, username: conta.username, role: novoRole }),
      });
      const json = await resposta.json();
      if (resposta.ok && json.status === "sucesso") {
        toast.success(
          novoRole === "TI"
            ? `${conta.name} agora é do Departamento de T.I.`
            : `${conta.name} voltou a ser Coordenador.`
        );
        await carregar();
      } else {
        toast.error(json.erro || "Não foi possível alterar o cargo.");
      }
    } catch {
      toast.error("Erro ao comunicar com o servidor.");
    } finally {
      setOcupado(null);
    }
  };

  const remover = async (conta: Conta) => {
    if (!confirm(`Remover a conta de ${conta.name} (${conta.username})? Esta ação não pode ser desfeita.`)) {
      return;
    }
    setOcupado(conta.username);
    try {
      const resposta = await fetch(`${API_BASE_URL}/api/usuarios/remover`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_name: currentUser, username: conta.username }),
      });
      const json = await resposta.json();
      if (resposta.ok && json.status === "sucesso") {
        toast.success(`Conta de ${conta.name} removida.`);
        await carregar();
      } else {
        toast.error(json.erro || "Não foi possível remover a conta.");
      }
    } catch {
      toast.error("Erro ao comunicar com o servidor.");
    } finally {
      setOcupado(null);
    }
  };

  return (
    <Card className="border-[var(--brand-border)] overflow-hidden">
      <div className="px-6 py-4 border-b border-[var(--brand-border)] flex items-center gap-2">
        <div className="w-9 h-9 rounded-lg bg-slate-100 text-[var(--brand-blue)] flex items-center justify-center">
          <Users size={18} />
        </div>
        <div>
          <p style={{ fontWeight: 600, color: "#0f172a" }}>Gestão de Contas Locais</p>
          <p className="text-slate-500" style={{ fontSize: "0.8rem" }}>
            Promova um coordenador a T.I., rebaixe ou remova contas. A conta de administrador é protegida.
          </p>
        </div>
      </div>

      {carregando ? (
        <div className="px-6 py-8 text-center text-slate-400">Carregando…</div>
      ) : contas.length === 0 ? (
        <div className="px-6 py-8 text-center text-slate-500">Nenhuma conta local cadastrada.</div>
      ) : (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="bg-slate-50">
                <TableHead>Nome</TableHead>
                <TableHead>Usuário</TableHead>
                <TableHead>Cargo</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {contas.map((conta) => {
                const isTi = conta.role === "TI";
                const protegido = conta.isSuperAdmin;
                const linhaOcupada = ocupado === conta.username;
                return (
                  <TableRow key={conta.username} className="hover:bg-slate-50/50">
                    <TableCell style={{ fontWeight: 500, color: "#0f172a" }}>
                      <span className="flex items-center gap-2">
                        {conta.name}
                        {protegido && (
                          <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">Admin</Badge>
                        )}
                      </span>
                    </TableCell>
                    <TableCell className="text-slate-500" style={{ fontFamily: "ui-monospace, monospace", fontSize: "0.8rem" }}>
                      {conta.username}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={isTi ? "bg-blue-50 text-blue-700 border-blue-200" : "bg-slate-50 text-slate-700 border-slate-200"}
                      >
                        {isTi ? <ShieldCheck size={13} className="mr-1" /> : <GraduationCap size={13} className="mr-1" />}
                        {ROLE_LABEL[conta.role] ?? conta.role}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      {protegido ? (
                        <span className="text-slate-400" style={{ fontSize: "0.8rem" }}>Conta protegida</span>
                      ) : (
                        <div className="flex justify-end gap-2">
                          {isTi ? (
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={linhaOcupada}
                              onClick={() => alterarCargo(conta, "COORDENADOR")}
                              className="gap-1"
                            >
                              <ArrowDownCircle size={14} /> Rebaixar
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={linhaOcupada}
                              onClick={() => alterarCargo(conta, "TI")}
                              className="gap-1"
                            >
                              <ArrowUpCircle size={14} /> Promover a T.I.
                            </Button>
                          )}
                          <Button
                            size="sm"
                            variant="ghost"
                            disabled={linhaOcupada}
                            onClick={() => remover(conta)}
                            className="gap-1 text-[var(--brand-red)] hover:text-[var(--brand-red)]"
                          >
                            <Trash2 size={14} /> Remover
                          </Button>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </Card>
  );
}
