export type Role = "COORDENADOR" | "TI";

export type JobStatus = "Pendente" | "Imprimindo" | "Concluído" | "Erro";
export type ColorMode = "PB" | "Colorida";
export type PageMode = "Frente" | "FrenteVerso";
export type Finishing = "Normal" | "Grampeada";

export type PrintJob = {
  id: string;
  sender: string;
  subject: string;
  turma: string;
  fileName: string;
  copies: number;
  color: ColorMode;
  pageMode: PageMode;
  finishing: Finishing;
  status: JobStatus;
  submittedAt: number;
  // Carimbos vindos do backend (ISO 8601, horário de Brasília). Opcionais
  // porque pedidos antigos, anteriores ao registro de data/hora, podem não
  // tê-los. São o que responde "quando exatamente isso foi enviado/impresso".
  submittedAtIso?: string | null;
  printedAtIso?: string | null;
  errorAtIso?: string | null;
};

export type LocalUser = {
  username: string;
  password: string;
  name: string;
  role: Role;
};

export const LOCAL_USERS: LocalUser[] = [
  { username: "coordenador", password: "acalanto2024", name: "Juliana Ferreira", role: "COORDENADOR" },
  { username: "ti.carlos", password: "acalanto2024", name: "Carlos Mendes", role: "TI" },
  { username: "ana.paula", password: "acalanto2024", name: "Ana Paula Rocha", role: "COORDENADOR" },
];

export const ROLE_LABELS: Record<Role, string> = {
  COORDENADOR: "COORDENADOR DE ÁREA",
  TI: "DEP. DE T.I.",
};

export const COLOR_LABELS: Record<ColorMode, string> = {
  PB: "P/B (Preto e Branco)",
  Colorida: "Colorida",
};

export const PAGE_MODE_LABELS: Record<PageMode, string> = {
  Frente: "Apenas Frente",
  FrenteVerso: "Frente e Verso",
};

export const SEED_JOBS: PrintJob[] = [
  { id: "IMP-0421", sender: "Prof. Marina Costa", subject: "Matemática", turma: "3º Ano B — EM", fileName: "prova_matematica_3ano.pdf", copies: 32, color: "PB", pageMode: "FrenteVerso", finishing: "Grampeada", status: "Pendente", submittedAt: Date.now() - 1000 * 60 * 8 },
  { id: "IMP-0420", sender: "Prof. Ricardo Lima", subject: "História", turma: "2º Ano A — EM", fileName: "lista_revisao_historia.pdf", copies: 28, color: "PB", pageMode: "Frente", finishing: "Normal", status: "Pendente", submittedAt: Date.now() - 1000 * 60 * 22 },
  { id: "IMP-0419", sender: "Prof. Silva", subject: "Português", turma: "1º Ano C — EM", fileName: "redacao_tema_dissertativo.pdf", copies: 30, color: "PB", pageMode: "Frente", finishing: "Normal", status: "Pendente", submittedAt: Date.now() - 1000 * 60 * 40 },
  { id: "IMP-0418", sender: "Prof. Ana Beatriz", subject: "Biologia", turma: "3º Ano A — EM", fileName: "atividade_genetica.pdf", copies: 25, color: "Colorida", pageMode: "FrenteVerso", finishing: "Grampeada", status: "Imprimindo", submittedAt: Date.now() - 1000 * 60 * 55 },
  { id: "IMP-0417", sender: "Prof. Silva", subject: "Português", turma: "2º Ano B — EM", fileName: "interpretacao_texto_modernismo.pdf", copies: 30, color: "PB", pageMode: "FrenteVerso", finishing: "Grampeada", status: "Imprimindo", submittedAt: Date.now() - 1000 * 60 * 70 },
  { id: "IMP-0416", sender: "Prof. Helena Souza", subject: "Geografia", turma: "1º Ano A — EM", fileName: "mapa_brasil_regioes.pdf", copies: 33, color: "Colorida", pageMode: "Frente", finishing: "Normal", status: "Concluído", submittedAt: Date.now() - 1000 * 60 * 120 },
  { id: "IMP-0415", sender: "Prof. Silva", subject: "Português", turma: "3º Ano C — EM", fileName: "gabarito_simulado.pdf", copies: 35, color: "PB", pageMode: "Frente", finishing: "Normal", status: "Concluído", submittedAt: Date.now() - 1000 * 60 * 180 },
  { id: "IMP-0414", sender: "Prof. Eduardo Pinto", subject: "Química", turma: "2º Ano C — EM", fileName: "tabela_periodica_exercicios.pdf", copies: 29, color: "PB", pageMode: "FrenteVerso", finishing: "Grampeada", status: "Concluído", submittedAt: Date.now() - 1000 * 60 * 240 },
];
