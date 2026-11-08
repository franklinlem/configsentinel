import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import {
  BrowserRouter,
  NavLink,
  Routes,
  Route,
  useNavigate,
} from "react-router-dom";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  ShieldCheck,
  LayoutDashboard,
  Activity,
  Server,
  FolderKanban,
  KeyRound,
  ScrollText,
  Users,
  LogOut,
  Sun,
  Moon,
  ArrowUpRight,
  Check,
  Search,
  RefreshCw,
  Radio,
  FileCheck2,
  AlertTriangle,
  ChevronRight,
  X,
  Plus,
  Copy,
} from "lucide-react";
import {
  api,
  ApiError,
  date,
  labels,
  getCsrf,
  setCsrf,
  clearCsrf,
  type Row,
  type Listing,
} from "./api";
import "./styles.css";
const client = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchInterval: 30000 } },
});
const useList = (key: string, path: string, enabled = true) =>
  useQuery({
    queryKey: [key, path],
    queryFn: () => api<Listing>(path),
    enabled,
  });
function ErrorNote({ error }: { error: unknown }) {
  return error ? (
    <div className="notice error" role="alert">
      {error instanceof Error ? error.message : String(error)}
    </div>
  ) : null;
}
function Empty({
  text = "Nenhum registro por aqui ainda.",
}: {
  text?: string;
}) {
  return (
    <div className="empty">
      <FileCheck2 size={30} />
      <strong>{text}</strong>
      <span>Os registros aparecerão após a primeira coleta autorizada.</span>
    </div>
  );
}
function Status({ value }: { value: string }) {
  return (
    <span className={"badge " + value}>
      <i />
      {labels[value] || value}
    </span>
  );
}
function App() {
  const [logged, setLogged] = useState(false);
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    try {
      const saved = localStorage.getItem("cs_theme");
      if (saved === "dark" || saved === "light") return saved;
    } catch {}
    return "dark";
  });

  React.useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("cs_theme", theme);
    } catch {}
  }, [theme]);

  const toggleTheme = () =>
    setTheme((t) => (t === "dark" ? "light" : "dark"));

  const me = useQuery({
    queryKey: ["me", logged],
    queryFn: () => api("/me"),
    retry: false,
    refetchInterval: false,
  });
  if (me.isPending)
    return (
      <div className="loading" role="status">
        Carregando ConfigSentinel…
      </div>
    );
  if (me.isError && !(me.error instanceof ApiError && me.error.status === 401))
    return (
      <main className="loading">
        <div role="alert">
          Não foi possível verificar sua sessão. Verifique a conexão e tente
          novamente.
        </div>
        <button className="primary" onClick={() => me.refetch()}>
          Tentar novamente
        </button>
      </main>
    );
  if (!me.data)
    return (
      <Login
        theme={theme}
        toggleTheme={toggleTheme}
        done={() => {
          setLogged(true);
          me.refetch();
        }}
      />
    );
  return (
    <Shell
      email={me.data.email}
      theme={theme}
      toggleTheme={toggleTheme}
      logout={() => {
        setLogged(false);
        client.setQueryData(["me", logged], null);
        client.clear();
        window.location.href = "/";
      }}
    />
  );
}
const loginSchema = z.object({
  email: z.email("Informe um e-mail válido"),
  password: z.string().min(1, "Informe sua senha"),
});
function Login({
  done,
  theme,
  toggleTheme,
}: {
  done: () => void;
  theme: "dark" | "light";
  toggleTheme: () => void;
}) {
  const [error, setError] = useState<unknown>();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(loginSchema) });
  return (
    <main className="login">
      <div style={{ position: "absolute", top: 18, right: 22, zIndex: 10 }}>
        <button
          type="button"
          className="icon-button"
          aria-label={
            theme === "dark"
              ? "Mudar para visual claro"
              : "Mudar para visual escuro"
          }
          title={theme === "dark" ? "Visual claro" : "Visual escuro"}
          onClick={toggleTheme}
        >
          {theme === "dark" ? <Sun size={20} /> : <Moon size={20} />}
        </button>
      </div>
      <section className="login-story">
        <div className="brand">
          <ShieldCheck />
          <span>ConfigSentinel</span>
        </div>
        <div>
          <span className="eyebrow">VISIBILIDADE SEM EXPOSIÇÃO</span>
          <h1>
            Suas configurações.
            <br />
            Cada mudança
            <br />
            <em>sob observação.</em>
          </h1>
          <p>
            Um histórico de integridade para sua infraestrutura.
            <br />
            Somente hashes e metadados, desde a origem.
          </p>
        </div>
        <small>SELF-HOSTED · HASH-ONLY · SOMENTE LEITURA</small>
      </section>
      <section className="login-form">
        <form
          onSubmit={handleSubmit(async (v) => {
            try {
              setError(undefined);
              const data = await api("/auth/login", "POST", v);
              setCsrf(data.csrf_token);
              done();
            } catch (e) {
              setError(e);
            }
          })}
        >
          <ShieldCheck className="login-icon" size={36} />
          <h2>Acesse seu observatório</h2>
          <p>Entre com sua conta administrativa.</p>
          <label>
            E-mail
            <input
              type="email"
              autoComplete="username"
              {...register("email")}
            />
          </label>
          {errors.email && <small role="alert">{errors.email.message}</small>}
          <label>
            Senha
            <input
              type="password"
              autoComplete="current-password"
              {...register("password")}
            />
          </label>
          {errors.password && (
            <small role="alert">{errors.password.message}</small>
          )}
          <ErrorNote error={error} />
          <button className="primary" disabled={isSubmitting}>
            {isSubmitting ? "Entrando…" : "Entrar no ConfigSentinel"}
            <ArrowUpRight size={18} />
          </button>
          <small className="hint">
            Acesso restrito. Para recuperar sua conta, consulte o administrador
            da instalação.
          </small>
        </form>
      </section>
    </main>
  );
}
const nav = [
  ["/", "Visão geral", LayoutDashboard],
  ["/events", "Eventos", Activity],
  ["/servers", "Servidores", Server],
  ["/projects", "Projetos e ambientes", FolderKanban],
  ["/credentials", "Credenciais", KeyRound],
  ["/members", "Membros", Users],
  ["/audit", "Auditoria", ScrollText],
] as const;
function getEnvironment() {
  const host = typeof window !== "undefined" ? window.location.hostname.toLowerCase() : "";
  if (host === "configsentinel.franklem.uk" || host === "configsentinel.com" || (!host.includes("dev") && !host.includes("homolog") && !host.includes("localhost") && !host.includes("127.0.0.1") && host.length > 0)) {
    return { name: "PRODUÇÃO", className: "prod" };
  }
  if (host.includes("dev") || host.includes("homolog")) {
    return { name: "HOMOLOGAÇÃO", className: "homolog" };
  }
  return { name: "DEV LOCAL", className: "dev" };
}
function Shell({
  email,
  logout,
  theme,
  toggleTheme,
}: {
  email: string;
  logout: () => void;
  theme: "dark" | "light";
  toggleTheme: () => void;
}) {
  const [error, setError] = useState<unknown>();
  const endSession = async () => {
    try {
      await api("/auth/logout", "POST");
    } catch (e) {
      setError(e);
    } finally {
      clearCsrf();
      logout();
    }
  };
  return (
    <div className="layout">
      <a className="skip" href="#main">
        Pular para o conteúdo
      </a>
      <aside className="sidebar">
        <div className="brand">
          <ShieldCheck size={29} />
          <span>
            ConfigSentinel<small>CONFIGURATION OBSERVABILITY</small>
          </span>
        </div>
        <div className="workspace">
          <span className="avatar">F</span>
          <div>
            Workspace<small>Infraestrutura privada</small>
          </div>
          <ChevronRight size={16} />
        </div>
        <span className="nav-caption">OBSERVATÓRIO</span>
        <nav aria-label="Navegação principal">
          {nav.map(([to, label, Icon]) => (
            <NavLink key={to} to={to} end={to === "/"}>
              <Icon size={19} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="privacy">
            <ShieldCheck size={20} />
            <div>
              Privacidade por padrão<small>Sem conteúdo. Sem comandos.</small>
            </div>
          </div>
          <div className="profile">
            <span className="avatar small">F</span>
            <span title={email}>
              {email}
              <small>Sessão administrativa</small>
            </span>
            <button
              type="button"
              className="icon-button"
              aria-label="Sair da sessão"
              title="Sair da sessão"
              onClick={endSession}
            >
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </aside>
      <div className="main-wrap">
        <header className="topbar">
          <span>
            Workspace <ChevronRight size={13} /> Observatório
          </span>
          <div>
            <span className={`env-pill ${getEnvironment().className}`}>
              {getEnvironment().name}
            </span>
            <span className="version">v0.1.0</span>
            <button
              type="button"
              className="icon-button"
              aria-label={
                theme === "dark"
                  ? "Mudar para visual claro"
                  : "Mudar para visual escuro"
              }
              title={theme === "dark" ? "Visual claro" : "Visual escuro"}
              onClick={toggleTheme}
            >
              {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
            </button>
            <button
              type="button"
              className="icon-button"
              aria-label="Sair da sessão"
              title="Sair da sessão"
              onClick={endSession}
            >
              <LogOut size={17} />
            </button>
          </div>
        </header>
        <main id="main" tabIndex={-1}>
          <ErrorNote error={error} />
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/events" element={<Events />} />
            <Route path="/servers" element={<Servers />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/credentials" element={<Credentials />} />
            <Route path="/members" element={<Members />} />
            <Route path="/audit" element={<Audit />} />
            <Route path="*" element={<Empty text="Página não encontrada" />} />
          </Routes>
          <footer>
            <ShieldCheck size={14} /> Integridade observada. Conteúdo
            preservado.<span>ConfigSentinel © 2026</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
function Heading({
  title,
  sub,
  action,
}: {
  title: string;
  sub: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="heading">
      <div>
        <span className="eyebrow">CONFIGSENTINEL / OBSERVATÓRIO</span>
        <h1>{title}</h1>
        <p>{sub}</p>
      </div>
      {action}
    </div>
  );
}
function Refresh() {
  const qc = useQueryClient();
  const [refreshing, setRefreshing] = useState(false);
  const [done, setDone] = useState(false);

  const handleRefresh = async () => {
    if (refreshing) return;
    setRefreshing(true);
    setDone(false);
    try {
      await Promise.all([
        qc.invalidateQueries({ refetchType: "active" }),
        new Promise((resolve) => setTimeout(resolve, 500)),
      ]);
      setDone(true);
      setTimeout(() => setDone(false), 2000);
    } catch {
      //
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <button
      type="button"
      className="secondary refresh-button"
      onClick={handleRefresh}
      disabled={refreshing}
      aria-busy={refreshing}
      aria-live="polite"
      title={
        refreshing
          ? "Atualizando dados…"
          : done
          ? "Dados atualizados com sucesso!"
          : "Atualizar dados agora"
      }
    >
      {done ? (
        <Check size={15} className="success-icon" />
      ) : (
        <RefreshCw size={15} className={refreshing ? "spin-icon" : ""} />
      )}
      <span>{refreshing ? "Atualizando…" : done ? "Atualizado!" : "Atualizar"}</span>
    </button>
  );
}
function Overview() {
  const servers = useList("servers", "/servers");
  const events = useList("events", "/events?limit=6");
  const alerts = useList("alerts", "/alerts");
  const rows = servers.data?.items || [];
  const online = rows.filter((s) => s.status === "online").length;
  const pending = alerts.data?.items.length || 0;
  return (
    <>
      <Heading
        title="Visão geral"
        sub="Acompanhe a integridade das suas configurações em um só lugar."
        action={<Refresh />}
      />
      <ErrorNote error={servers.error || events.error || alerts.error} />
      <section className="summary-banner">
        <div className="radar">
          <Radio size={30} />
        </div>
        <div>
          <span className="eyebrow">SEU AMBIENTE, SOB OBSERVAÇÃO</span>
          <h2>
            {pending
              ? "Há sinais que precisam de atenção"
              : rows.length
                ? "Coleta de integridade em acompanhamento"
                : "Tudo começa com uma coleta autorizada"}
          </h2>
          <p>
            {rows.length
              ? `${online} de ${rows.length} servidores com comunicação e coleta recentes.`
              : "Cadastre um servidor e instale o agente para criar a primeira baseline."}
          </p>
        </div>
        <span className="hash-pill">
          <ShieldCheck size={15} />
          HASH-ONLY
        </span>
      </section>
      <section className="stats" aria-label="Indicadores">
        <Stat
          title="Servidores monitorados"
          value={rows.length}
          icon={<Server />}
          sub={`${online} online agora`}
        />
        <Stat
          title="Agentes sem comunicação"
          value={rows.filter((s) => s.status === "offline").length}
          icon={<Radio />}
          sub="Limite inicial de 5 minutos"
        />
        <Stat
          title="Sinais em aberto"
          value={pending}
          icon={<AlertTriangle />}
          sub="Eventos e saúde da coleta"
        />
        <Stat
          title="Eventos na fila local"
          value={rows.reduce((a, s) => a + (s.queue_depth || 0), 0)}
          icon={<Activity />}
          sub="Último heartbeat recebido"
        />
      </section>
      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>Atividade recente</h2>
            <p>As últimas observações da sua infraestrutura.</p>
          </div>
          <NavLink to="/events" className="text-link">
            Todos os eventos <ArrowUpRight size={16} />
          </NavLink>
        </div>
        <EventTable
          rows={events.data?.items || []}
          loading={events.isPending}
        />
      </section>
      <div className="two-column">
        <section className="panel">
          <div className="panel-head">
            <h2>Saúde dos agentes</h2>
            <NavLink to="/servers" className="text-link">
              Ver servidores <ArrowUpRight size={15} />
            </NavLink>
          </div>
          {rows.length ? (
            rows.slice(0, 5).map((s) => (
              <div className="server-line" key={s.id}>
                <span className="server-icon">
                  <Server size={19} />
                </span>
                <div>
                  <strong>{s.display_name}</strong>
                  <small>
                    {s.project} / {s.environment}
                  </small>
                </div>
                <Status value={s.status} />
              </div>
            ))
          ) : (
            <Empty text="Nenhum servidor cadastrado" />
          )}
        </section>
        <section className="panel principle">
          <ShieldCheck size={28} />
          <span className="eyebrow">DESENHADO PARA PRESERVAR</span>
          <h2>
            Você observa a mudança.
            <br />
            Os arquivos ficam onde estão.
          </h2>
          <p>
            O agente transmite somente hashes SHA-256 e metadados permitidos. A
            allowlist é definida no servidor, sob seu controle.
          </p>
          <div>
            <Check size={16} /> Sem conteúdo ou diff textual
          </div>
          <div>
            <Check size={16} /> Sem execução remota
          </div>
          <div>
            <Check size={16} /> Histórico com reconhecimento auditável
          </div>
        </section>
      </div>
    </>
  );
}
function Stat({
  title,
  value,
  icon,
  sub,
}: {
  title: string;
  value: number;
  icon: React.ReactNode;
  sub: string;
}) {
  return (
    <article className="stat">
      <span>{title}</span>
      <div>
        <strong>{value.toString().padStart(2, "0")}</strong>
        <span className="stat-icon">{icon}</span>
      </div>
      <small>{sub}</small>
    </article>
  );
}
function EventTable({
  rows,
  loading = false,
}: {
  rows: Row[];
  loading?: boolean;
}) {
  const [selected, setSelected] = useState<string>();
  if (loading)
    return (
      <p className="loading" role="status">
        Carregando eventos…
      </p>
    );
  return (
    <>
      {rows.length ? (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Arquivo / evento</th>
                <th>Servidor</th>
                <th>Ambiente</th>
                <th>Recebido em</th>
                <th>Estado</th>
                <th>
                  <span className="sr-only">Detalhes</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((e) => (
                <tr key={e.id}>
                  <td>
                    <button
                      className="event-button"
                      onClick={() => setSelected(e.id)}
                    >
                      <span className={"event-icon " + e.severity}>
                        <FileCheck2 size={18} />
                      </span>
                      <span>
                        <strong>{e.file_alias}</strong>
                        <small>{labels[e.kind] || e.kind}</small>
                      </span>
                    </button>
                  </td>
                  <td>{e.server_name}</td>
                  <td>
                    <span className="muted-pill">{e.environment}</span>
                  </td>
                  <td className="timestamp">{date(e.received_at)}</td>
                  <td>
                    <span
                      className={"badge " + (e.acknowledged ? "ack" : "info")}
                    >
                      {e.acknowledged
                        ? "Reconhecido"
                        : e.kind === "baseline"
                          ? "Baseline"
                          : "Novo"}
                    </span>
                  </td>
                  <td>
                    <button
                      className="icon-button"
                      aria-label={"Detalhes de " + e.file_alias}
                      onClick={() => setSelected(e.id)}
                    >
                      <ChevronRight size={17} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <Empty text="Nenhum evento registrado" />
      )}
      {selected && (
        <EventDetail id={selected} close={() => setSelected(undefined)} />
      )}
    </>
  );
}
function Modal({
  title,
  close,
  children,
}: {
  title: string;
  close: () => void;
  children: React.ReactNode;
}) {
  const ref = React.useRef<HTMLDialogElement>(null);
  React.useEffect(() => {
    ref.current?.showModal();
  }, []);
  return (
    <dialog
      ref={ref}
      onCancel={close}
      onClick={(e) => {
        if (e.target === e.currentTarget) close();
      }}
      aria-label={title}
    >
      <div className="modal-head">
        <h2>{title}</h2>
        <button className="icon-button" aria-label="Fechar" onClick={close}>
          <X />
        </button>
      </div>
      {children}
    </dialog>
  );
}
function EventDetail({ id, close }: { id: string; close: () => void }) {
  const q = useList("detail", "/events/" + id);
  const event = q.data?.items[0];
  const [error, setError] = useState<unknown>();
  const qc = useQueryClient();
  return (
    <Modal title="Detalhe do evento" close={close}>
      <ErrorNote error={q.error || error} />
      {event && (
        <>
          <Status value={event.kind} />
          <h3>{event.file_alias}</h3>
          <dl>
            <dt>Observado no agente</dt>
            <dd>{date(event.observed_at)}</dd>
            <dt>Recebido na central</dt>
            <dd>{date(event.received_at)}</dd>
            <dt>Sequência</dt>
            <dd>{event.sequence}</dd>
            <dt>SHA-256 anterior</dt>
            <dd>
              <code>{event.old_sha256 || "Não disponível"}</code>
            </dd>
            <dt>SHA-256 atual</dt>
            <dd>
              <code>{event.new_sha256 || "Não disponível"}</code>
            </dd>
          </dl>
          <h3>Reconhecimentos</h3>
          {event.acknowledgements?.length ? (
            event.acknowledgements.map((a: Row) => (
              <div className="acknowledgement" key={a.id}>
                <p>{a.comment}</p>
                <small>
                  {a.actor} · {date(a.created_at)}
                </small>
              </div>
            ))
          ) : (
            <p className="hint">Este evento ainda não foi reconhecido.</p>
          )}
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const f = e.currentTarget;
              try {
                await api("/events/" + id + "/acknowledgements", "POST", {
                  comment: new FormData(f).get("comment"),
                });
                f.reset();
                qc.invalidateQueries();
              } catch (e) {
                setError(e);
              }
            }}
          >
            <label>
              Comentário de investigação
              <textarea
                name="comment"
                minLength={3}
                maxLength={2000}
                required
                placeholder="Registre o contexto desta observação."
              />
            </label>
            <p className="hint">
              Reconhecer registra a investigação. Não equivale a aprovar a
              alteração.
            </p>
            <button className="primary">
              Reconhecer evento
              <Check size={16} />
            </button>
          </form>
        </>
      )}
    </Modal>
  );
}
function Events() {
  const [kind, setKind] = useState("");
  const [search, setSearch] = useState("");
  const [server, setServer] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [cursor, setCursor] = useState("");
  const servers = useList("servers", "/servers");
  const params = new URLSearchParams({
    limit: "30",
    kind,
    q: search,
    cursor,
    server_id: server,
  });
  if (from) params.set("from", new Date(from).toISOString());
  if (to) params.set("to", new Date(to).toISOString());
  const q = useList("events", "/events?" + params);
  return (
    <>
      <Heading
        title="Histórico de eventos"
        sub="Cada observação tem origem, instante e evidência de integridade."
        action={<Refresh />}
      />
      <section className="panel">
        <div className="filters">
          <label className="search">
            <Search size={17} />
            <input
              aria-label="Buscar alias"
              value={search}
              placeholder="Buscar por alias do arquivo"
              onChange={(e) => {
                setSearch(e.target.value);
                setCursor("");
              }}
            />
          </label>
          <select
            aria-label="Filtrar tipo de evento"
            value={kind}
            onChange={(e) => {
              setKind(e.target.value);
              setCursor("");
            }}
          >
            <option value="">Todos os tipos</option>
            {Object.entries(labels)
              .slice(0, 11)
              .map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
          </select>
          <select
            aria-label="Filtrar servidor"
            value={server}
            onChange={(e) => {
              setServer(e.target.value);
              setCursor("");
            }}
          >
            <option value="">Todos os servidores</option>
            {servers.data?.items.map((s) => (
              <option key={s.id} value={s.id}>
                {s.display_name}
              </option>
            ))}
          </select>
          <label>
            De
            <input
              type="datetime-local"
              value={from}
              onChange={(e) => {
                setFrom(e.target.value);
                setCursor("");
              }}
            />
          </label>
          <label>
            Até
            <input
              type="datetime-local"
              value={to}
              onChange={(e) => {
                setTo(e.target.value);
                setCursor("");
              }}
            />
          </label>
        </div>
        <ErrorNote error={q.error} />
        <EventTable rows={q.data?.items || []} loading={q.isPending} />
        <div className="pagination">
          <button
            className="secondary"
            disabled={!cursor}
            onClick={() => setCursor("")}
          >
            Mais recentes
          </button>
          <button
            className="secondary"
            disabled={!q.data?.next_cursor}
            onClick={() => setCursor(q.data?.next_cursor || "")}
          >
            Próxima página
            <ChevronRight size={15} />
          </button>
        </div>
      </section>
    </>
  );
}
function Servers() {
  const q = useList("servers", "/servers");
  const [selected, setSelected] = useState<Row>();
  return (
    <>
      <Heading
        title="Servidores"
        sub="Comunicação e coleta são acompanhadas separadamente."
        action={
          <NavLink className="primary" to="/projects">
            <Plus size={16} />
            Cadastrar servidor
          </NavLink>
        }
      />
      <ErrorNote error={q.error} />
      <div className="server-grid">
        {q.data?.items.map((s) => (
          <button
            className="panel server-card"
            key={s.id}
            onClick={() => setSelected(s)}
          >
            <div>
              <span className="server-icon">
                <Server />
              </span>
              <Status value={s.status} />
            </div>
            <h2>{s.display_name}</h2>
            <p>
              {s.project} / {s.environment}
            </p>
            <dl>
              <dt>Última comunicação</dt>
              <dd>{date(s.last_seen_at)}</dd>
              <dt>Última coleta</dt>
              <dd>{date(s.last_observed_at)}</dd>
              <dt>Agente / fila</dt>
              <dd>
                {s.agent_version || "Não instalado"} · {s.queue_depth || 0}
                {s.queue_capacity ? ` / ${s.queue_capacity}` : ""} pendentes
              </dd>
            </dl>
            <span className="text-link">
              Inspecionar arquivos <ArrowUpRight size={15} />
            </span>
          </button>
        ))}
      </div>
      {q.data?.items.length === 0 && (
        <Empty text="Cadastre seu primeiro servidor" />
      )}
      {selected && (
        <Observations server={selected} close={() => setSelected(undefined)} />
      )}
    </>
  );
}
function Observations({ server, close }: { server: Row; close: () => void }) {
  const q = useList("observations", "/servers/" + server.id + "/observations");
  return (
    <Modal title={server.display_name + " · arquivos"} close={close}>
      <ErrorNote error={q.error} />
      {q.data?.items.length ? (
        q.data.items.map((f) => (
          <div key={f.agent_id + f.file_alias} className="observation">
            <strong>{f.file_alias}</strong>
            <Status value={f.state} />
            <code>{f.sha256 || "Hash não disponível"}</code>
            <small>
              {date(f.observed_at)} · {f.file_size} bytes
            </small>
          </div>
        ))
      ) : (
        <Empty text="Aguardando a primeira observação" />
      )}
    </Modal>
  );
}
function useScope() {
  const orgs = useList("organizations", "/organizations");
  const [chosenOrg, setOrg] = useState("");
  const org = chosenOrg || orgs.data?.items[0]?.id || "";
  const projects = useList(
    "projects",
    "/organizations/" + org + "/projects",
    !!org,
  );
  const [chosenProject, setProject] = useState("");
  const project =
    projects.data?.items.find((p) => p.id === chosenProject)?.id ||
    projects.data?.items[0]?.id ||
    "";
  const envs = useList(
    "environments",
    "/projects/" + project + "/environments",
    !!project,
  );
  const [chosenEnv, setEnv] = useState("");
  const env =
    envs.data?.items.find((e) => e.id === chosenEnv)?.id ||
    envs.data?.items[0]?.id ||
    "";
  return {
    orgs,
    org,
    setOrg,
    projects,
    project,
    setProject,
    envs,
    env,
    setEnv,
  };
}
function Options({ items }: { items?: Row[] }) {
  return (
    <>
      {items?.map((i) => (
        <option value={i.id} key={i.id}>
          {i.name || i.display_name}
        </option>
      ))}
    </>
  );
}
function Projects() {
  const s = useScope();
  const [error, setError] = useState<unknown>();
  const qc = useQueryClient();
  const create = async (
    e: React.FormEvent<HTMLFormElement>,
    path: string,
    server = false,
  ) => {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    try {
      await api(
        path,
        "POST",
        server
          ? { display_name: f.get("name") }
          : { name: f.get("name"), slug: f.get("slug") },
      );
      form.reset();
      qc.invalidateQueries();
      setError(undefined);
    } catch (e) {
      setError(e);
    }
  };
  return (
    <>
      <Heading
        title="Projetos e ambientes"
        sub="Organize servidores por contexto e mantenha os ambientes identificados."
      />
      <ErrorNote
        error={error || s.orgs.error || s.projects.error || s.envs.error}
      />
      <div className="scope-bar">
        <label>
          Organização
          <select value={s.org} onChange={(e) => s.setOrg(e.target.value)}>
            <Options items={s.orgs.data?.items} />
          </select>
        </label>
        <label>
          Projeto
          <select
            value={s.project}
            onChange={(e) => s.setProject(e.target.value)}
          >
            <Options items={s.projects.data?.items} />
          </select>
        </label>
        <label>
          Ambiente
          <select value={s.env} onChange={(e) => s.setEnv(e.target.value)}>
            <Options items={s.envs.data?.items} />
          </select>
        </label>
      </div>
      <div className="server-grid">
        {[
          ["Organização", "/organizations", true],
          ["Projeto", "/organizations/" + s.org + "/projects", !!s.org],
          ["Ambiente", "/projects/" + s.project + "/environments", !!s.project],
          ["Servidor", "/environments/" + s.env + "/servers", !!s.env],
        ].map(([title, path, enabled]) => (
          <form
            key={String(title)}
            className="panel form-panel"
            onSubmit={(e) => create(e, String(path), title === "Servidor")}
          >
            <h2>Novo {String(title).toLowerCase()}</h2>
            <label>
              {title === "Servidor" ? "Nome lógico (sem espaços)" : "Nome"}
              <input
                name="name"
                maxLength={title === "Servidor" ? 80 : 120}
                required
                pattern={
                  title === "Servidor"
                    ? "[A-Za-z0-9][A-Za-z0-9_.-]*"
                    : undefined
                }
              />
            </label>
            {title !== "Servidor" && (
              <label>
                Slug
                <input
                  name="slug"
                  pattern="[a-z0-9][a-z0-9-]*"
                  maxLength={63}
                  required
                />
              </label>
            )}
            <button disabled={!enabled} className="primary">
              <Plus size={16} />
              Criar {String(title).toLowerCase()}
            </button>
          </form>
        ))}
      </div>
    </>
  );
}
function Credentials() {
  const servers = useList("servers", "/servers");
  const [chosen, setChosen] = useState("");
  const server: Row =
    servers.data?.items.find((s) => s.id === chosen) ||
    servers.data?.items[0] ||
    {};
  const tokens = useList(
    "tokens",
    "/agents/" + server?.agent_id + "/tokens",
    !!server?.agent_id,
  );
  const [issued, setIssued] = useState<Row>();
  const [error, setError] = useState<unknown>();
  const qc = useQueryClient();
  return (
    <>
      <Heading
        title="Credenciais de agentes"
        sub="Emissão restrita ao servidor, expiração em 90 dias e revogação auditada."
      />
      <ErrorNote error={error || servers.error || tokens.error} />
      <section className="panel form-panel">
        <label>
          Servidor
          <select
            value={server?.id || ""}
            onChange={(e) => setChosen(e.target.value)}
          >
            <Options items={servers.data?.items} />
          </select>
        </label>
        <div className="button-row">
          <button
            disabled={!server.id}
            className="primary"
            onClick={async () => {
              try {
                setIssued(
                  await api("/servers/" + server.id + "/agents", "POST"),
                );
                qc.invalidateQueries();
              } catch (e) {
                setError(e);
              }
            }}
          >
            <Plus size={16} />
            Provisionar nova instalação
          </button>
          <button
            disabled={!server?.agent_id}
            className="secondary"
            onClick={async () => {
              try {
                setIssued(
                  await api("/agents/" + server.agent_id + "/tokens", "POST"),
                );
                qc.invalidateQueries();
              } catch (e) {
                setError(e);
              }
            }}
          >
            Emitir token de rotação
          </button>
        </div>
        <p className="hint">
          Rotação: instale o token novo no host, confirme o heartbeat e revogue
          o anterior. Provisionar cria outra identidade de instalação.
        </p>
      </section>
      <section className="panel">
        <div className="panel-head">
          <h2>Tokens da instalação</h2>
        </div>
        {tokens.data?.items.map((t) => (
          <div className="token-line" key={t.id}>
            <code>{t.prefix}…</code>
            <span>Expira {date(t.expires_at)}</span>
            {t.revoked_at ? (
              <Status value="Revogado" />
            ) : (
              <button
                className="danger-button"
                onClick={async () => {
                  try {
                    await api(
                      "/agents/" + server.agent_id + "/tokens/" + t.id,
                      "DELETE",
                    );
                    qc.invalidateQueries();
                  } catch (e) {
                    setError(e);
                  }
                }}
              >
                Revogar token
              </button>
            )}
          </div>
        ))}
        {!tokens.data?.items.length && (
          <Empty text="Nenhuma credencial disponível" />
        )}
      </section>
      {issued && (
        <Modal
          title="Credencial emitida · exibição única"
          close={() => setIssued(undefined)}
        >
          <p>
            Guarde o token em um arquivo com permissão 0600 no host do agente.
          </p>
          <label>
            Identificador do agente
            <input readOnly value={issued.agent_id} />
          </label>
          <label>
            Token
            <input readOnly value={issued.token} />
          </label>
          <button
            className="secondary"
            onClick={() => navigator.clipboard.writeText(issued.token)}
          >
            <Copy size={16} />
            Copiar token
          </button>
          <p className="notice">
            Este token não será exibido novamente. A allowlist permanece na
            configuração local.
          </p>
          <button className="primary" onClick={() => setIssued(undefined)}>
            Credencial guardada
            <Check size={16} />
          </button>
        </Modal>
      )}
    </>
  );
}
function Members() {
  const s = useScope();
  const [role, setRole] = useState("viewer");
  const [error, setError] = useState<unknown>();
  const q = useList("members", "/organizations/" + s.org + "/members", !!s.org);
  const qc = useQueryClient();
  return (
    <>
      <Heading
        title="Membros e permissões"
        sub="Owner gerencia a organização; admin recebe acesso a um projeto específico."
      />
      <label className="scope-select">
        Organização
        <select value={s.org} onChange={(e) => s.setOrg(e.target.value)}>
          <Options items={s.orgs.data?.items} />
        </select>
      </label>
      <ErrorNote error={error || q.error} />
      <div className="two-column">
        <form
          className="panel form-panel"
          onSubmit={async (e) => {
            e.preventDefault();
            const form = e.currentTarget;
            const f = new FormData(form);
            try {
              await api("/organizations/" + s.org + "/members", "POST", {
                email: f.get("email"),
                password: f.get("password"),
                role,
                project_id: role === "admin" ? s.project : null,
              });
              form.reset();
              qc.invalidateQueries();
              setError(undefined);
            } catch (e) {
              setError(e);
            }
          }}
        >
          <h2>Adicionar membro</h2>
          <label>
            E-mail
            <input name="email" type="email" required />
          </label>
          <label>
            Senha inicial (conta nova)
            <input
              name="password"
              type="password"
              minLength={16}
              maxLength={1024}
              required
              autoComplete="new-password"
            />
          </label>
          <label>
            Perfil
            <select value={role} onChange={(e) => setRole(e.target.value)}>
              {["viewer", "analyst", "admin", "owner"].map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </label>
          {role === "admin" && (
            <label>
              Projeto
              <select
                value={s.project}
                onChange={(e) => s.setProject(e.target.value)}
              >
                <Options items={s.projects.data?.items} />
              </select>
            </label>
          )}
          <p className="hint">
            Para contas existentes, a senha permanece inalterada.
          </p>
          <button className="primary">
            Adicionar membro
            <Plus size={16} />
          </button>
        </form>
        <section className="panel">
          <div className="panel-head">
            <h2>Membros da organização</h2>
          </div>
          {q.data?.items.map((m) => (
            <div className="server-line" key={m.id}>
              <Users size={20} />
              <div>
                <strong>{m.email}</strong>
                <small>
                  {m.project_id
                    ? s.projects.data?.items.find((p) => p.id === m.project_id)
                        ?.name
                    : "Todos os projetos"}
                </small>
              </div>
              <span className="badge">{m.role}</span>
            </div>
          ))}
        </section>
      </div>
    </>
  );
}
function Audit() {
  const s = useScope();
  const q = useList(
    "audit",
    "/organizations/" + s.org + "/audit-logs",
    !!s.org,
  );
  return (
    <>
      <Heading
        title="Trilha de auditoria"
        sub="Ações administrativas preservadas, sem registrar credenciais."
      />
      <label className="scope-select">
        Organização
        <select value={s.org} onChange={(e) => s.setOrg(e.target.value)}>
          <Options items={s.orgs.data?.items} />
        </select>
      </label>
      <ErrorNote error={q.error} />
      <section className="panel">
        {q.data?.items.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Ação</th>
                  <th>Ator</th>
                  <th>Recurso</th>
                  <th>Instante</th>
                </tr>
              </thead>
              <tbody>
                {q.data.items.map((a) => (
                  <tr key={a.id}>
                    <td>
                      <strong>{a.operation}</strong>
                    </td>
                    <td>{a.actor || "Agente"}</td>
                    <td>
                      <small>{a.target_type}</small>
                      <code>{a.target_id}</code>
                    </td>
                    <td>{date(a.timestamp)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty text="Nenhuma ação administrativa registrada" />
        )}
      </section>
    </>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={client}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
