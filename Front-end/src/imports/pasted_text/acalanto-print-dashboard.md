🎨 DESIGN PROMPT / SPECIFICATION: ACALANTO PRINT DASHBOARD
Context: Enterprise print queue management system for "Instituto Acalanto de Ensino".
Design Style: Clean, modern, trustworthy, educational SaaS dashboard. High contrast, accessible typography, precise container padding.
Brand Palette (Institutional):

Primary: Deep Blue (#1E3A8A) - Dominant color for headers and structure.

Secondary/Accent: Vibrant Red (#DC2626) - Bottom lines, badges, critical actions.

Warning/Highlight: Warm Amber/Yellow (#FBBF24) - Pending status, role badges.

Backgrounds: Clean Slate (#F8FAFC to #FFFFFF).

🖥️ SCREEN 1: THE LOGIN GATEWAY (SESSÃO RESTRITA)
Layout: Centered card, minimalist style, split layout (left side: subtle geometric art with school initials "IA", right side: authentication form).

Components:

School Header: "Instituto Acalanto de Ensino" + Subtle subtitle "Portal de Gerenciamento de Impressão".

Main Action: Large, high-fidelity "Entrar com o Google Workspace" Button (Standard Google OAuth layout).

Secondary Action: "Entrar com Credenciais do Servidor Local" (Input Fields for Username/Password).

UX Rule: Must feel highly secure. Use light gray borders (#E2E8F0) and smooth focus transitions.

📋 SCREEN 2: MAIN DASHBOARD & SUBMISSION FORM (VIEW: COORDENADOR & T.I.)
Layout: 2-Column Responsive Layout. Top Persistent Navbar.

Top Navbar Component:

Left: Logo "IA" + Title "INSTITUTO ACALANTO DE ENSINO". Role Badge next to username ("COORDENADOR DE ÁREA" or "DEP. DE T.I.").

Center/Right: Navigation Links ("Enviar Impressão" with active state, "Fila de Impressão" with a Red counter badge for pending prints). User Profile dropdown with logout link.

Column 1: The Printing Request Form (Width: 65%):

Section Title: "Nova Solicitação de Impressão" (Subheading: "Preencha todos os campos obrigatórios").

Form Fields Stack (Vertical Grid):

Turma: Full-width Text input with placeholder "Ex: 3º Ano B — Ensino Médio".

Número de Cópias: Numeric stepper/input default value = 1.

Tipo de Cor: Segmented Control / Radio Buttons Group (Options: "P/B (Preto e Branco)" [Selected by default], "Colorida").

Modo de Página: Dropdown or Toggle (Options: "Apenas Frente", "Frente e Verso").

Acabamento: Dropdown (Options: "Normal", "Grampeada").

Anexo da Prova (The Interactive Dropzone): A large dashed-border container (border-dash, radius 12px) with an cloud icon "📤".

State A (Empty): Text "Arraste o arquivo PDF aqui ou clique para selecionar". Subtext: "Apenas arquivos PDF · Máx. 50 MB".

State B (File Attached - Animation Reference): Smooth transition to a light green/blue solid background. Display file icon "📄", filename "prova_matematica_3ano.pdf", a successful checkmark "✅", and a micro-delete button "✕".

Submit Action Button: Large, full-width primary button (#1E3A8A) with a solid red bottom border (#DC2626). Label: "🖨️ Enviar para o TI & Impressora".

Column 2: Information Sidebar (Width: 35%):

Stack of 2 Info Cards:

Card 1 (Suporte): Background white, subtle gray border. Text: "⚠️ Quaisquer dúvidas referente à plataforma, entre em contato com o Departamento de T.I (Ramal 1113)."

Card 2 (Regras de Funcionamento): Background Deep Blue (#1E3A8A), text white. Title: "⏱️ Horário de Funcionamento". Content: "Segunda a Sexta-Feira, das 07:00 às 19:00". Restrição: "É permitido apenas o envio de documentos salvos em PDF".

🪟 SCREEN 3: CONFIRMATION MODAL (POP-UP DE VALIDAÇÃO)
Layout: Overlay/Backdrop Blur (backdrop-blur-sm, bg-gray-900/50). Centered modal box with slide-in behavior.

Components:

Header: Warning icon or Print icon + "Confirmação de Impressão".

Content Body: Structured data readout (Simulating an official receipt).

Text snippet: "Você confirma o envio da impressão da matéria [Nome da Matéria] para a turma [Nome da Turma] com [X] cópias?"

Bullet list with visual tags summarizing the selected properties (e.g., [Frente e Verso] [Grampeada] [Preto e Branco]).

Footer Actions: - Cancel button: Outline gray ("Ajustar Dados").

Confirm button: High contrast solid blue button ("Confirmar Envio").

📊 SCREEN 4: THE PRINT QUEUE VIEWS (FILA DE IMPRESSÃO)
Layout: Single full-width view with metric cards at the top and a main data table below.

Top Status Metrics (3 Cards Grid):

Card 1: Pending (Amber border #FBBF24, bold number indicator).

Card 2: Printing (Blue border #1E3A8A, animated pulse dot indicator).

Card 3: Completed (Green border, success indicator).

Conditional Layout A: THE T.I. / ADMIN DASHBOARD:

Full access. Data Table Columns: ID, Remetente (Nome do Professor), Matéria / Turma, Arquivo (Link para download do PDF), Cópias, Fila, Status (Pendente/Imprimindo/Concluído).

Actions column: Buttons to change status or re-print.

Conditional Layout B: THE TEACHER PREVIEW (VISÃO RESTRITA DO DOCENTE):

Personalized access. The dashboard banner states: "Minhas Impressões".

Data Table Columns: ID, Matéria / Turma, Arquivo, Cópias, Sua Posição na Fila, Status.

UX Feature: The table only lists entries matching the logged-in teacher's username. The "Sua Posição na Fila" column features a dynamic token (e.g., "3º na fila"). Other global requests are completely hidden to preserve pedagogical privacy.

Component & Interaction Guidelines for Prototyping:
Transitions: All buttons should have hover states (opacity decrease or color shade shift).

Alerts: Use standard alert banners if a user uploads a non-PDF file (Red alert background with text "Erro: Formato inválido. Apenas PDFs são aceitos.").

Empty States: If a teacher has no active prints, show an elegant vector illustration of an idle printer with the text "Nenhuma impressão pendente na fila.".