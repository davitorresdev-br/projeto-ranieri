# Acalanto Print Dashboard — Implementation Plan

## Context
The user attached a detailed spec (`src/imports/pasted_text/acalanto-print-dashboard.md`) for an enterprise print queue management system for "Instituto Acalanto de Ensino". Build it as a React + Tailwind app in this Figma Make project. The spec covers 4 screens: Login, Main Dashboard with submission form, Confirmation Modal, and Print Queue views (admin + teacher variants).

This is a pure frontend build (no Supabase needed) — all data is local/mock state. Role switching (Coordenador / T.I. / Docente) is simulated client-side.

## Approach

Single-page app with view-state routing inside `App.tsx` (no `react-router` needed — keeps it lean). Existing shadcn UI primitives in `src/app/components/ui/` are reused throughout.

### Design tokens
Extend `src/styles/theme.css` with brand CSS vars:
- `--brand-blue: #1E3A8A`, `--brand-red: #DC2626`, `--brand-amber: #FBBF24`, `--brand-slate: #F8FAFC`, `--brand-border: #E2E8F0`.
Use via Tailwind arbitrary values (`bg-[var(--brand-blue)]`) — no Tailwind config since v4.

### Components to create (`src/app/components/`)
- `LoginScreen.tsx` — split layout, "IA" geometric art panel left, auth form right (Google OAuth button + local credentials). Uses `Button`, `Input`, `Card`.
- `TopNavbar.tsx` — logo + title, role badge, nav links with active state + red counter badge for "Fila de Impressão", user dropdown with role switcher (dev affordance to switch between Coordenador/T.I./Docente) + logout.
- `SubmissionForm.tsx` — Column 1. Uses `Input`, `RadioGroup` (segmented for color), `Select` (page mode + finishing), numeric stepper for copies, and a custom dropzone.
- `FileDropzone.tsx` — dashed border container with two states (empty / attached). PDF-only validation; non-PDF triggers `sonner` red toast "Erro: Formato inválido. Apenas PDFs são aceitos." File state is local; uses `useRef` + drag handlers.
- `InfoSidebar.tsx` — Column 2. Two stacked cards (white support card + deep-blue hours card).
- `ConfirmationModal.tsx` — `Dialog` from shadcn. Receipt-style summary with `Badge` tags for selected properties; "Ajustar Dados" (outline) + "Confirmar Envio" (solid blue) actions.
- `QueueMetricsCards.tsx` — 3 status cards (Pending/Printing/Completed) with colored borders and the animated pulse dot on "Printing".
- `PrintQueueTable.tsx` — accepts `role` prop; renders admin columns (ID, Remetente, Matéria/Turma, Arquivo, Cópias, Fila, Status, Ações) or teacher-restricted columns (ID, Matéria/Turma, Arquivo, Cópias, Sua Posição na Fila, Status) filtered to current user. Empty state shows idle-printer illustration + "Nenhuma impressão pendente na fila."
- `IdlePrinterIllustration.tsx` — inline SVG.

### State (in `App.tsx`)
- `view`: `'login' | 'dashboard' | 'queue'`
- `role`: `'COORDENADOR' | 'TI' | 'DOCENTE'` (switchable from navbar dropdown for demo)
- `currentUser`: string (e.g., "Prof. Silva")
- `printJobs`: array of mock jobs with `{ id, sender, subject, turma, file, copies, color, pageMode, finishing, status, queuePosition }`
- `pendingSubmission`: holds form draft when confirmation modal is open

Seed `printJobs` with ~8 realistic Portuguese-language entries spanning all three statuses.

### Behavior
- Login: either button transitions to `dashboard` (no real auth).
- Submit: validates required fields → opens `ConfirmationModal` → confirm appends a `Pendente` job to `printJobs`, shows sonner success toast, resets form.
- Pending counter badge in navbar reflects `printJobs.filter(j => j.status === 'Pendente').length`.
- T.I./Admin sees full table with status-change action buttons (Pendente → Imprimindo → Concluído cycle); Docente sees only their own jobs with position-in-queue.
- Hover transitions on buttons via Tailwind `transition` + `hover:opacity-90`.

### Files to modify
- `src/app/App.tsx` — main composition, view + role state, role-conditioned routing
- `src/styles/theme.css` — append brand color CSS vars
- New files under `src/app/components/` listed above

### Reuse from existing codebase
- `src/app/components/ui/{button,input,card,dialog,select,radio-group,badge,table,dropdown-menu,label,separator,sonner}.tsx` — shadcn primitives, all present.
- `src/app/components/figma/ImageWithFallback.tsx` — not needed (no raster images required; everything is vector/CSS).

## Verification
1. Reload the preview surface — confirm Login screen renders centered with split layout.
2. Click "Entrar com Google Workspace" → arrives at dashboard with 2-column layout, navbar with "COORDENADOR" badge + red pending counter.
3. Fill the form, attach a sample PDF (verify dropzone state B transition); attach a non-PDF and confirm red error toast.
4. Submit → confirmation modal shows receipt-style summary with badge tags → Confirmar Envio → toast + form reset + counter increments.
5. Navigate to "Fila de Impressão" → 3 metric cards visible; admin table shows all jobs with action buttons; cycle a job's status and confirm metric counts update.
6. Switch role to "DOCENTE" via navbar dropdown → table reduces to that teacher's jobs only and shows "Sua Posição na Fila" column; banner reads "Minhas Impressões".
7. Empty queue (filter to a teacher with no jobs) → idle-printer illustration + empty-state copy.
