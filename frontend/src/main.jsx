import React, { useState, useEffect, createContext, useContext } from "react";
import { createRoot } from "react-dom/client";
import {
  BrowserRouter,
  Routes,
  Route,
  NavLink,
  Link,
  useNavigate,
  useLocation,
  Navigate,
} from "react-router-dom";
import {
  Shield,
  LayoutDashboard,
  ScanLine,
  Link2,
  MessageSquare,
  IndianRupee,
  Mail,
  History,
  Flag,
  BookOpen,
  Settings,
  ArrowUpRight,
  ArrowRight,
  ChevronRight,
  Search,
  Plus,
  Check,
  CheckCheck,
  LockKeyhole,
  ShieldCheck,
  TriangleAlert,
  Activity,
  Download,
  Trash2,
  LogOut,
  Eye,
  EyeOff,
  Menu,
  X,
  ExternalLink,
  LifeBuoy,
  Globe,
  FileText,
  LoaderCircle,
  ChevronDown,
  Info,
  Code2,
  Camera,
  AudioLines,
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Family, Verification } from "./pages/Family";
import { GitHubScanner } from "./pages/GitHubScanner";
import {
  UploadScanner,
  Assistant,
  Learning,
  Notifications,
  Admin,
  Shopkeeper,
} from "./pages/Advanced";
import { api, errorText, download } from "./api";
import "./styles.css";
import{useLocale,setLocale,getLocale,tr}from"./i18n/core";
import{LanguagePicker}from"./i18n/LanguagePicker";
const Auth = createContext();
const icons = {
  url: Link2,
  message: MessageSquare,
  upi: IndianRupee,
  email: Mail,
};
const names = {
  url: "Website & URL",
  message: "Message",
  upi: "UPI payment",
  email: "Email phishing",
};
function Icon({ type, ...props }) {
  const I = icons[type] || Shield;
  return <I {...props} />;
}
function App() {
  const locale=useLocale();
  useEffect(()=>{document.documentElement.lang=locale},[locale]);
  const [user, setUser] = useState(null),
    [loading, setLoading] = useState(true);
  useEffect(() => {
    if (sessionStorage.getItem("token"))
      api
        .get("/auth/me")
        .then((r) => setUser(r.data))
        .catch(() => sessionStorage.removeItem("token"))
        .finally(() => setLoading(false));
    else setLoading(false);
  }, []);
  useEffect(()=>{if(user)api.get("/profile/preferences").then(r=>{if(["en","hi","mr"].includes(r.data.language))setLocale(r.data.language)}).catch(()=>{})},[user?.id]);
  return (
    <Auth.Provider value={{ user, setUser, loading }}>
      <LanguagePicker />
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<AuthPage />} />
          <Route path="/register" element={<AuthPage register />} />
          <Route path="/forgot-password" element={<Recovery />} />
          <Route path="/reset-password" element={<Recovery reset />} />
          <Route path="/*" element={<Shell />} />
        </Routes>
      </BrowserRouter>
    </Auth.Provider>
  );
}
function Brand() {
  return (
    <Link to="/" className="brand">
      <span className="brand-icon">
        <Shield size={24} />
      </span>
      <span>
        ScamShield <b>AI</b>
        <small>YOUR DIGITAL GUARDIAN</small>
      </span>
    </Link>
  );
}
function Shell() {
  const { user, setUser, loading } = useContext(Auth),
    [open, setOpen] = useState(false),
    [apiOnline, setApiOnline] = useState(null);
  useEffect(() => {
    const check = () =>
      api
        .get("/health")
        .then(() => setApiOnline(true))
        .catch(() => setApiOnline(false));
    check();
    const timer = setInterval(check, 60000);
    return () => clearInterval(timer);
  }, []);
  const location = useLocation();
  useEffect(() => setOpen(false), [location.pathname]);
  const logout = async () => {
    try {
      await api.post("/auth/logout");
      sessionStorage.removeItem("token");
      setUser(null);
    } catch (e) {
      alert(errorText(e));
    }
  };
  return (
    <div className="app">
      <aside className={open ? "sidebar open" : "sidebar"}>
        <Brand />
        <div className="workspace">
          <span className="workspace-icon">
            <ShieldCheck size={18} />
          </span>
          <span>
            Personal workspace<small>Your security command center</small>
          </span>
          <ChevronDown size={14} />
        </div>
        <div className="nav-caption">WORKSPACE</div>
        <nav>
          {[
            [LayoutDashboard, "Overview", "/"],
            [ScanLine, "Security scanner", "/scan"],
            [History, "Scan history", "/history"],
            [Flag, "Threat reports", "/reports"],
              [ShieldCheck, "Family safety", "/family"],
            [Camera, "Screenshot scanner", "/image"],
            [ScanLine, "QR scanner", "/qr"],
            [Mail, "Email file scanner", "/email-file"],
            [AudioLines, "Voice analyzer", "/voice"],
            [MessageSquare, "AI assistant", "/assistant"],
            [Code2, "Developer security", "/code"],
            [Code2, "GitHub scanner", "/github"],
            [IndianRupee, "Shopkeeper mode", "/shopkeeper"],
          ].map(([I, n, p]) => (
            <NavLink key={p} to={p} end={p === "/"}>
              <I size={18} />
              {n}
              {p === "/scan" && <span className="nav-new">NEW</span>}
            </NavLink>
          ))}
        </nav>
        <div className="nav-caption resources">RESOURCES</div>
        <nav>
          <NavLink to="/awareness">
            <BookOpen size={18} />
            Safety center
          </NavLink>
          <NavLink to="/emergency">
            <LifeBuoy size={18} />
            Emergency help
            <span className="small-dot" />
          </NavLink>
          <NavLink to="/learning">
            <BookOpen size={18} />
            Safety quizzes
          </NavLink>
          <NavLink to="/notifications">
            <Shield size={18} />
            Notifications
          </NavLink>
          <NavLink to="/settings">
            <Settings size={18} />
            Settings
          </NavLink>
          {user?.role === "admin" && (
            <NavLink to="/admin">
              <Settings size={18} />
              Administration
            </NavLink>
          )}
        </nav>
        <div className="sidebar-bottom">
          <div className="privacy-card">
            <span className="privacy-icon">
              <LockKeyhole size={18} />
            </span>
            <strong>Private by design</strong>
            <p>
              Your scans stay in your account.
              <br />
              Your safety comes first.
            </p>
            <Link to="/awareness">
              Explore safety tips <ArrowUpRight size={13} />
            </Link>
          </div>
          {user ? (
            <button
              className="user-row"
              onClick={logout}
              title="Sign out of all sessions"
            >
              <span className="avatar">
                {user.name.slice(0, 2).toUpperCase()}
              </span>
              <span>
                {user.name}
                <small>Personal account</small>
              </span>
              <LogOut size={17} />
            </button>
          ) : (
            <Link className="user-row" to="/login">
              <span className="avatar">
                <Shield size={19} />
              </span>
              <span>
                Guest workspace<small>Sign in to save your scans</small>
              </span>
              <ArrowRight size={17} />
            </Link>
          )}
        </div>
      </aside>
      <div className="main-wrap">
        <header className="topbar">
          <button
            className="mobile-menu"
            onClick={() => setOpen(!open)}
            aria-label="Toggle menu"
          >
            <Menu />
          </button>
          <div className="breadcrumb">
            Workspace <ChevronRight size={13} />{" "}
            <span>
              {location.pathname === "/"
                ? "Overview"
                : location.pathname.startsWith("/scan")
                  ? "Security scanner"
                  : location.pathname.slice(1).replaceAll("-", " ")}
            </span>
          </div>
          <div className="top-right">
            <span className="operational">
              <i />{" "}
              {apiOnline === null
                ? "Checking API…"
                : apiOnline
                  ? "API online"
                  : "API unavailable"}
            </span>
            <Link
              to="/awareness"
              className="help-icon"
              aria-label="Safety help"
            >
              <LifeBuoy size={19} />
            </Link>
            {user ? (
              <Link to="/settings" className="avatar top-avatar">
                {user.name.slice(0, 2).toUpperCase()}
              </Link>
            ) : (
              <Link to="/login" className="top-signin">
                Sign in <ArrowUpRight size={14} />
              </Link>
            )}
          </div>
        </header>
        <main>
          {loading ? (
            <Loading />
          ) : (
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/scan" element={<Scanner />} />
              <Route path="/verify-email" element={<Verification />} />
              <Route path="/family" element={<Private><Family /></Private>} />
              {["image", "qr", "voice", "code", "email-file"].map((kind) => (
                <Route
                  key={kind}
                  path={"/" + kind}
                  element={
                    <Private>
                      <UploadScanner kind={kind} Result={Result} />
                    </Private>
                  }
                />
              ))}
              <Route
                path="/github"
                element={
                  <Private>
                    <GitHubScanner Result={Result} />
                  </Private>
                }
              />
              <Route
                path="/assistant"
                element={
                  <Private>
                    <Assistant />
                  </Private>
                }
              />
              <Route
                path="/learning"
                element={
                  <Private>
                    <Learning />
                  </Private>
                }
              />
              <Route
                path="/notifications"
                element={
                  <Private>
                    <Notifications />
                  </Private>
                }
              />
              <Route path="/shopkeeper" element={<Shopkeeper />} />
              <Route
                path="/admin"
                element={
                  <Private>
                    <Admin />
                  </Private>
                }
              />
              <Route
                path="/history"
                element={
                  <Private>
                    <HistoryPage />
                  </Private>
                }
              />
              <Route
                path="/scans/:id"
                element={
                  <Private>
                    <Detail />
                  </Private>
                }
              />
              <Route
                path="/reports"
                element={
                  <Private>
                    <Reports />
                  </Private>
                }
              />
              <Route
                path="/settings"
                element={
                  <Private>
                    <SettingsPage />
                  </Private>
                }
              />
              <Route path="/awareness" element={<Awareness />} />
              <Route path="/emergency" element={<Emergency />} />
              <Route
                path="*"
                element={
                  <div className="panel">
                    <h2>Page not found</h2>
                    <Link to="/">Return to overview</Link>
                  </div>
                }
              />
            </Routes>
          )}
        </main>
        <footer>
          <span>
            <Shield size={13} /> ScamShield AI{" "}
            <span className="muted"> / </span> Built for a safer digital India
          </span>
          <span>Risk estimates. Never a guarantee of safety.</span>
        </footer>
      </div>
    </div>
  );
}
function Private({ children }) {
  const { user } = useContext(Auth);
  return user ? (
    children
  ) : (
    <div className="panel gate">
      <LockKeyhole size={34} />
      <h2>Your security, in one private space.</h2>
      <p>Sign in to save scans, view your history and manage your account.</p>
      <Link className="btn primary" to="/login">
        Sign in securely <ArrowRight size={16} />
      </Link>
      <Link className="text-link" to="/register">
        Create an account
      </Link>
    </div>
  );
}
function Loading() {
  return (
    <div className="loading">
      <LoaderCircle className="spin" /> Loading your workspace…
    </div>
  );
}
function ErrorBox({ error }) {
  return (
    error && (
      <div role="alert" className="error-box">
        <TriangleAlert size={17} />
        {error}
      </div>
    )
  );
}
function PageTitle({ eyebrow, title, description, children }) {
  return (
    <div className="page-title">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {children}
    </div>
  );
}
function Dashboard() {
  const { user } = useContext(Auth);
  const [data, setData] = useState(null),
    [error, setError] = useState("");
  useEffect(() => {
    if (user)
      api
        .get("/dashboard/overview")
        .then((r) => setData(r.data))
        .catch((e) => setError(errorText(e)));
  }, [user]);
  const empty = {
    total: 0,
    low: 0,
    moderate: 0,
    dangerous: 0,
    recent: [],
    activity: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((day) => ({
      day,
      scans: 0,
    })),
    categories: [],
  };
  const d = data || empty;
  return (
    <>
      <PageTitle
        eyebrow="YOUR SECURITY AT A GLANCE"
        title={
          user
            ? `Welcome back, ${user.name.split(" ")[0]}`
            : "Your digital safety starts here."
        }
        description="A little awareness. A powerful shield. Stay one step ahead of scams."
      >
        <Link to="/scan" className="btn primary">
          <Plus size={17} /> New scan
        </Link>
      </PageTitle>
      <ErrorBox error={error} />
      <section className="hero-banner">
        <div className="hero-copy">
          <span className="hero-tag">
            <span className="tiny-pulse" /> THINK BEFORE YOU CLICK
          </span>
          <h2>
            Scams are evolving.
            <br />
            Your protection should too.
          </h2>
          <p>
            Check suspicious links, messages and payment requests.
            <br className="desktop" /> Get clear answers before you take the
            next step.
          </p>
          <Link className="btn light" to="/scan">
            Scan something suspicious <ArrowRight size={16} />
          </Link>
          <span className="hero-note">
            <LockKeyhole size={12} /> Private scans. Clear explanations. Real
            peace of mind.
          </span>
        </div>
        <div className="shield-art" aria-hidden="true">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="orbit orbit-three" />
          <div className="art-grid" />
          <div className="floating-tag tag-top">
            <Link2 size={15} />
            <span>
              Suspicious link?<b>Check before you click</b>
            </span>
            <span className="float-check">
              <Check size={12} />
            </span>
          </div>
          <div className="giant-shield">
            <Shield size={125} strokeWidth={1} />
            <Check className="shield-check" size={48} strokeWidth={3} />
          </div>
          <div className="floating-tag tag-bottom">
            <LockKeyhole size={16} />
            <span>
              You're in control<b>Verify. Don't assume.</b>
            </span>
          </div>
          <span className="spark s1" />
          <span className="spark s2" />
          <span className="spark s3" />
        </div>
      </section>
      <div className="stat-grid">
        {[
          [
            ScanLine,
            "Total scans",
            d.total,
            "All your security checks",
            "blue",
          ],
          [
            ShieldCheck,
            "Low risk",
            d.low,
            "No strong indicators found",
            "green",
          ],
          [
            TriangleAlert,
            "Suspicious",
            d.moderate,
            "Worth a closer look",
            "yellow",
          ],
          [
            Shield,
            "High / critical risk",
            d.dangerous,
            "Take action with care",
            "red",
          ],
        ].map(([I, n, v, sub, c]) => (
          <div className="stat-card" key={n}>
            <div className="stat-head">
              <span>{n}</span>
              <span className={`stat-icon ${c}`}>
                <I size={18} />
              </span>
            </div>
            <strong>{v.toLocaleString()}</strong>
            <span className="stat-caption">
              <i className={c} />
              {sub}
            </span>
          </div>
        ))}
      </div>
      <section className="section">
        <div className="section-heading">
          <div>
            <h2>What would you like to check?</h2>
            <p>One simple check can prevent a costly mistake.</p>
          </div>
          <span className="subtle-label">
            <LockKeyhole size={13} /> Secure analysis
          </span>
        </div>
        <div className="quick-grid">
          {Object.entries(names).map(([type, name]) => (
            <Link key={type} to={"/scan?type=" + type} className="quick-card">
              <span className={`quick-icon ${type}`}>
                <Icon type={type} size={22} />
              </span>
              <ArrowUpRight className="quick-arrow" size={16} />
              <h3>
                {name}
                {type === "url"
                  ? " scanner"
                  : type === "upi"
                    ? " check"
                    : " scanner"}
              </h3>
              <p>
                {
                  {
                    url: "Spot phishing links and deceptive domains.",
                    message: "Uncover scams hiding in everyday texts.",
                    upi: "Check before you pay. Protect your money.",
                    email: "Look beyond the inbox. Detect phishing.",
                  }[type]
                }
              </p>
              <span className="quick-cta">
                Start scan <ArrowRight size={13} />
              </span>
            </Link>
          ))}
        </div>
      </section>
      <div className="analytics-grid">
        <section className="panel activity-panel">
          <div className="panel-heading">
            <div>
              <h2>Scan activity</h2>
              <p>Your checks over the last 7 days</p>
            </div>
            <span className="chart-period">Last 7 days</span>
          </div>
          <div className="chart-legend">
            <i /> Scans <b>{d.total}</b>
            <span>all time</span>
          </div>
          <div className="activity-chart">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={d.activity}
                margin={{ top: 10, right: 10, left: -25, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3785ff" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#3785ff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  stroke="#213044"
                  strokeDasharray="3 5"
                  vertical={false}
                />
                <XAxis
                  dataKey="day"
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: "#738399", fontSize: 11 }}
                  dy={10}
                />
                <YAxis
                  allowDecimals={false}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: "#738399", fontSize: 10 }}
                  domain={[0, "auto"]}
                />
                <Tooltip
                  contentStyle={{
                    background: "#132134",
                    border: "1px solid #293a52",
                    borderRadius: 8,
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="scans"
                  stroke="#438bff"
                  strokeWidth={2.5}
                  fill="url(#area)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          {!user && (
            <div className="chart-footnote">
              Sign in to start building your security activity.
            </div>
          )}
        </section>
        <section className="panel distribution">
          <div className="panel-heading">
            <div>
              <h2>Scan breakdown</h2>
              <p>Know what you're checking</p>
            </div>
            <Activity size={17} className="muted" />
          </div>
          <div className="donut">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={
                    d.total
                      ? d.categories.filter((x) => x.value)
                      : [{ name: "No scans", value: 1 }]
                  }
                  dataKey="value"
                  innerRadius={61}
                  outerRadius={77}
                  stroke="none"
                  paddingAngle={d.total ? 5 : 0}
                >
                  {(d.total ? d.categories.filter((x) => x.value) : [{}]).map(
                    (_, i) => (
                      <Cell
                        key={i}
                        fill={
                          d.total
                            ? [
                                "#4d89ff",
                                "#32c8be",
                                "#a18afa",
                                "#efb754",
                                "#4cc6e9",
                                "#9fbb7f",
                                "#f09bac",
                                "#b2a0f8",
                              ][i]
                            : "#233248"
                        }
                      />
                    ),
                  )}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: "#132134",
                    border: "1px solid #293a52",
                    borderRadius: 8,
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="donut-center">
              <strong>{d.total}</strong>
              <span>Total scans</span>
            </div>
          </div>
          <div className="distribution-legend">
            {[
              "URL",
              "Message",
              "UPI",
              "Email",
              "Image",
              "QR",
              "Voice",
              "Code",
            ].map((n, i) => (
              <span key={n}>
                <i
                  style={{
                    background: [
                      "#4d89ff",
                      "#32c8be",
                      "#a18afa",
                      "#efb754",
                      "#4cc6e9",
                      "#9fbb7f",
                      "#f09bac",
                      "#b2a0f8",
                    ][i],
                  }}
                />
                {n}
                <b>{d.categories[i]?.value || 0}</b>
              </span>
            ))}
          </div>
        </section>
      </div>
      <section className="panel recent-panel">
        <div className="panel-heading">
          <div>
            <h2>Recent scans</h2>
            <p>Your latest security checks, all in one place.</p>
          </div>
          <Link className="text-link" to="/history">
            View all history <ArrowRight size={14} />
          </Link>
        </div>
        <ScanTable items={d.recent} />
      </section>
      <div className="bottom-grid">
        <section className="tip-card">
          <span className="tip-icon">
            <BookOpen size={22} />
          </span>
          <div>
            <span className="eyebrow">SMALL TIP. BIG PROTECTION.</span>
            <h3>Receiving money? You don't need a UPI PIN.</h3>
            <p>
              A PIN authorizes a payment from your account. Never enter it to
              claim a refund or receive money.
            </p>
            <Link to="/awareness">
              Build your scam instincts <ArrowRight size={14} />
            </Link>
          </div>
        </section>
        <Link className="emergency-card" to="/emergency">
          <LifeBuoy size={25} />
          <div>
            <h3>Think you've been scammed?</h3>
            <p>
              Act quickly. Call <b>1930</b>.
            </p>
            <span>
              Get emergency guidance <ArrowUpRight size={13} />
            </span>
          </div>
        </Link>
      </div>
      <div className="disclaimer">
        <Info size={13} /> ScamShield provides evidence-based risk estimates,
        not guarantees. Always verify important requests independently.
      </div>
    </>
  );
}
function ScanTable({ items, onDelete }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>SCANNED CONTENT</th>
            <th>TYPE</th>
            <th>RISK LEVEL</th>
            <th>DATE</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {items.map((s) => (
            <tr key={s.id}>
              <td>
                <Link to={"/scans/" + s.id} className="scan-content">
                  <span className="table-icon">
                    <Icon type={s.kind} size={16} />
                  </span>
                  <span>
                    {s.content.slice(0, 65)}
                    {s.content.length > 65 ? "…" : ""}
                  </span>
                </Link>
              </td>
              <td className="capitalize">{s.kind}</td>
              <td>
                <Risk level={s.result.level} />
              </td>
              <td>
                {new Date(
                  /Z$|[+-]\d\d:\d\d$/.test(s.created_at)
                    ? s.created_at
                    : s.created_at + "Z",
                ).toLocaleDateString(({en:"en-IN",hi:"hi-IN",mr:"mr-IN"})[getLocale()], {
                  day: "numeric",
                  month: "short",
                })}
              </td>
              <td>
                {onDelete ? (
                  <button
                    title="Delete scan"
                    className="icon-btn"
                    onClick={() => onDelete(s.id)}
                  >
                    <Trash2 size={16} />
                  </button>
                ) : (
                  <Link aria-label="View analysis" to={"/scans/" + s.id}>
                    <ChevronRight size={16} />
                  </Link>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!items.length && (
        <div className="empty-state">
          <span>
            <ScanLine size={24} />
          </span>
          <h3>Your next safer decision starts with a scan.</h3>
          <p>
            No scans yet. Check a suspicious link or message to see your results
            here.
          </p>
          <Link to="/scan" className="text-link">
            Run your first scan <ArrowRight size={14} />
          </Link>
        </div>
      )}
    </div>
  );
}
function Risk({ level }) {
  return (
    <span className={"risk " + level}>
      <i />
      {level === "low"
        ? "Low risk"
        : level === "moderate"
          ? "Suspicious"
          : level === "high"
            ? "High risk"
            : "Critical risk"}
    </span>
  );
}
function Scanner() {
  const { user } = useContext(Auth);
  const location = useLocation();
  const [type, setType] = useState(
      new URLSearchParams(location.search).get("type") || "url",
    ),
    [content, setContent] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [result, setResult] = useState(null),
    [external, setExternal] = useState(false),
    [ai, setAI] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setResult(null);
    if (!user) {
      setError(
        "Please sign in to analyze content and save your private result.",
      );
      return;
    }
    setBusy(true);
    try {
      const r = await api.post(
        "/scans/" + type,
        {
          content,
          ...(external ? { use_external: true } : {}),
          ...(ai ? { use_ai: true } : {}),
          ...(getLocale()!=="en"?{language:{en:"English",hi:"Hindi",mr:"Marathi"}[getLocale()]}:{}),
        },
        { timeout: 120000 },
      );
      setResult(r.data);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <PageTitle
        eyebrow="PAUSE. CHECK. PROTECT."
        title="Security scanner"
        description="Turn uncertainty into a more informed decision."
      />
      <div className="scanner-layout">
        <section className="panel scanner-panel">
          <div className="scan-tabs">
            {Object.entries(names).map(([k, n]) => (
              <button
                key={k}
                className={type === k ? "active" : ""}
                onClick={() => {
                  setType(k);
                  setResult(null);
                  setError("");
                }}
              >
                <Icon type={k} size={17} />
                {k === "url"
                  ? "URL"
                  : k === "message"
                    ? "Message"
                    : k === "upi"
                      ? "UPI"
                      : "Email"}
              </button>
            ))}
          </div>
          <div className="scan-body">
            <span className="large-scan-icon">
              <Icon type={type} size={30} />
            </span>
            <h2>{names[type] || "URL"} analysis</h2>
            <p>
              {type === "url"
                ? "Check a destination without opening it. We analyze its structure for signs of deception."
                : "Paste the complete suspicious content. More context makes the local rule-based analysis more useful."}
            </p>
            <form onSubmit={submit}>
              <label htmlFor="content">
                {type === "url" ? "Website address" : "Content to analyze"}
              </label>
              {type === "url" ? (
                <input
                  id="content"
                  type="url"
                  placeholder="https://example.com/suspicious-link"
                  required
                  maxLength={12000}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                />
              ) : (
                <textarea
                  id="content"
                  placeholder={
                    type === "email"
                      ? "From: sender@example.com\nSubject: Important update\n\nPaste the full email or raw headers and body…"
                      : "Paste your message here. Never submit real passwords, OTPs or UPI PINs."
                  }
                  rows={8}
                  minLength={3}
                  maxLength={12000}
                  required
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                />
              )}
              <label className="consent">
                <input
                  type="checkbox"
                  checked={external}
                  onChange={(e) => setExternal(e.target.checked)}
                />
                Send extracted URLs to configured reputation providers
              </label>
              <label className="consent">
                <input
                  type="checkbox"
                  checked={ai}
                  onChange={(e) => setAI(e.target.checked)}
                />
                Send content to Gemini for an AI explanation (not independent
                verification)
              </label>
              <ErrorBox error={error} />
              <div className="form-actions">
                <span>
                  <LockKeyhole size={13} /> Saved privately to your account
                </span>
                <button disabled={busy} className="btn primary">
                  {busy ? (
                    <LoaderCircle className="spin" size={17} />
                  ) : (
                    <ScanLine size={17} />
                  )}{" "}
                  {busy
                    ? "Analyzing…"
                    : "Analyze " + (type === "url" ? "URL" : "content")}
                </button>
              </div>
            </form>
            {!user && (
              <p className="signin-note">
                <Link to="/login">Sign in</Link> or{" "}
                <Link to="/register">create an account</Link> to run your first
                scan.
              </p>
            )}
          </div>
        </section>
        <aside className="scan-explainer panel">
          <ShieldCheck size={27} />
          <h3>Know what a scan can tell you</h3>
          <p>
            Every finding comes with a reason. No magic scores. No promises of
            perfect safety.
          </p>
          <ul>
            <li>
              <Check size={15} /> Transparent, weighted indicators
            </li>
            <li>
              <Check size={15} /> Private, downloadable reports
            </li>
            <li>
              <Check size={15} /> Practical next steps
            </li>
          </ul>
          <div className="notice">
            <Info size={16} />
            <p>
              Local rules are always active. External reputation checks and AI
              explanations are opt-in and require backend configuration. No bank
              transaction is verified.
            </p>
          </div>
          <p className="muted">
            Do not submit secrets or financial credentials. You can delete saved
            scans from your history.
          </p>
        </aside>
      </div>
      {result && <Result scan={result} />}
      <div className="panel roadmap-note">
        <Camera size={19} />
        <div>
          <h3>Looking for image, QR, voice or code analysis?</h3>
          <p>
            Open the screenshot, QR, voice or developer modules from the
            sidebar. Some local software or model files may need installation.
          </p>
        </div>
      </div>
    </>
  );
}
function Result({ scan }) {
  const [error, setError] = useState("");
  const r = scan.result;
  return (
    <section className="panel result-panel">
      <div className="result-header">
        <div>
          <div className="eyebrow">ANALYSIS COMPLETE · SCAN #{scan.id}</div>
          <h2>Your security assessment</h2>
          <Risk level={r.level} />
        </div>
        <div className={"score " + r.level}>
          <strong>
            {r.score}
            <small>/100</small>
          </strong>
          <span>Estimated risk</span>
        </div>
      </div>
      <p>{r.summary}</p>
      <ErrorBox error={error} />
      <div className="result-columns">
        <div>
          <h3>Why this score?</h3>
          {r.indicators.length ? (
            r.indicators.map((i) => (
              <div className="indicator" key={i.code}>
                <TriangleAlert size={16} />
                <p>{i.reason}</p>
                <b>
                  {i.weight
                    ? "+" + i.weight
                    : i.code === "known_threat_match"
                      ? "≥90"
                      : "Review"}
                </b>
              </div>
            ))
          ) : (
            <div className="notice">
              <Info size={17} />
              <p>
                No local rule matched. Sophisticated or unfamiliar scams may
                still be missed.
              </p>
            </div>
          )}
          <h3>Provider coverage</h3>
          <div className="notice">
            <Globe size={17} />
            <p>
              {r.provider.status} · {r.provider.reason}
            </p>
          </div>
          {r.details.sender && (
            <div className="email-metadata">
              <p>
                Supplied sender: <code>{r.details.sender}</code>
              </p>
              <p>Subject: {r.details.subject}</p>
              <p>{r.details.header_note}</p>
            </div>
          )}
          {r.details.domain && (
            <p className="data-line">
              Domain: <code>{r.details.domain}</code> ·{" "}
              {r.details.https ? "HTTPS in URL" : "HTTP in URL"} (certificate
              not verified)
            </p>
          )}
          {r.urls.length > 0 && (
            <>
              <h3>Extracted destinations — not clickable</h3>
              {r.urls.map((u) => (
                <code className="extracted" key={u}>
                  {u}
                </code>
              ))}
            </>
          )}
        </div>
        <div>
          <h3>What to do next</h3>
          {r.actions.map((a, i) => (
            <div className="action-item" key={a}>
              <span>{i + 1}</span>
              <p>{a}</p>
            </div>
          ))}
          <div className="notice warning">
            <Info size={17} />
            <p>
              Screenshots and messages cannot verify a payment. Check your own
              bank or payment app transaction history.
            </p>
          </div>
        </div>
      </div>
      <p>Technical findings and submitted evidence remain in their original language.</p><EnrichedResult result={r} />
      <div className="limitations">
        {r.limitations.map((l) => (
          <p key={l}>• {l}</p>
        ))}
      </div>
      <button
        className="btn primary"
        onClick={() =>
          download(
            "/history/" + scan.id + "/report.pdf",
            `scan-${scan.id}.pdf`,
          ).catch((e) => setError(errorText(e)))
        }
      >
        <Download size={16} /> Download PDF report
      </button>
    </section>
  );
}
function EnrichedResult({ result: r }) {
  return (
    <div className="enriched-result">
      {r.providers?.map((p, i) => (
        <div className="notice" key={i}>
          <Globe size={15} />
          <p>
            <b>
              {p.provider}: {p.status}
            </b>{" "}
            — {p.category} {p.reason}
          </p>
        </div>
      ))}
      {r.ml && (
        <div className="notice">
          <Activity size={16} />
          <p>
            ML baseline · {r.ml.status} {r.ml.label && <b> · {r.ml.label}</b>}
            <br />
            {r.ml.reason || r.ml.limitations}
          </p>
        </div>
      )}
      {r.ai && (
        <div className="notice">
          <MessageSquare size={16} />
          <p>
            AI explanation · {r.ai.status}
            <br />
            {r.ai.explanation || r.ai.reason || "AI not requested."}
            <br />
            {r.ai.uncertainty}
          </p>
        </div>
      )}
      {["extracted_text", "qr_payload", "transcript"].map(
        (k) =>
          r.details[k] && (
            <div key={k}>
              <h3>{k.replaceAll("_", " ")}</h3>
              <pre className="extracted">{r.details[k]}</pre>
            </div>
          ),
      )}
      {r.details.payment_intent && (
        <div className="notice warning">
          <IndianRupee size={16} />
          <p>
            {r.details.payment_intent.action}
            <br />
            Payee: {r.details.payment_intent.payee}
            <br />
            Amount: {r.details.payment_intent.amount}
            <br />A QR payload is not proof of ownership or legitimacy.
          </p>
        </div>
      )}
      {r.details.payment_action && (
        <div className="notice warning">
          <IndianRupee size={16} />
          <p>{r.details.payment_action}</p>
        </div>
      )}
      {r.details.deepfake_detection && <p>{r.details.deepfake_detection}</p>}
      {r.details.osv?.map((o, i) => (
        <div className="notice" key={i}>
          <Code2 size={16} />
          <p>
            OSV · {o.package}@{o.version}: {o.status} ·{" "}
            {o.ids.length
              ? o.ids.join(", ")
              : "No vulnerabilities reported by this lookup (not a guarantee)."}
          </p>
        </div>
      ))}
    </div>
  );
}

function Detail() {
  const id = useLocation().pathname.split("/").pop();
  const [data, setData] = useState(null),
    [error, setError] = useState("");
  useEffect(() => {
    api
      .get("/history/" + id)
      .then((r) => setData(r.data))
      .catch((e) => setError(errorText(e)));
  }, [id]);
  return (
    <>
      <PageTitle
        eyebrow="YOUR PRIVATE RECORD"
        title="Scan details"
        description="Review the evidence behind your risk estimate."
      />
      <ErrorBox error={error} />
      {data ? <Result scan={data} /> : !error && <Loading />}
    </>
  );
}
function HistoryPage() {
  const [data, setData] = useState({ items: [], total: 0 }),
    [q, setQ] = useState(""),
    [kind, setKind] = useState(""),
    [level, setLevel] = useState(""),
    [page, setPage] = useState(1),
    [error, setError] = useState("");
  const load = () =>
    api
      .get("/history", { params: { q, kind, level, page } })
      .then((r) => setData(r.data))
      .catch((e) => setError(errorText(e)));
  useEffect(() => {
    const t = setTimeout(load, 200);
    return () => clearTimeout(t);
  }, [q, kind, level, page]);
  const remove = async (id) => {
    if (!confirm(tr("Permanently delete this scan?"))) return;
    try {
      await api.delete("/history/" + id);
      load();
    } catch (e) {
      setError(errorText(e));
    }
  };
  return (
    <>
      <PageTitle
        eyebrow="YOUR SECURITY JOURNEY"
        title="Scan history"
        description="Every check. Every finding. Always yours."
      >
        <button
          className="btn secondary"
          onClick={() =>
            download("/history/export.csv", "scamshield-history.csv").catch(
              (e) => setError(errorText(e)),
            )
          }
        >
          <Download size={16} /> Export CSV
        </button>
      </PageTitle>
      <ErrorBox error={error} />
      <div className="panel">
        <div className="filters">
          <div className="search-input">
            <Search size={17} />
            <input
              aria-label="Search history"
              placeholder="Search scanned content…"
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setPage(1);
              }}
            />
          </div>
          <select
            aria-label="Scan type"
            value={kind}
            onChange={(e) => {
              setKind(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All scan types</option>
            {Object.keys(names).map((k) => (
              <option key={k}>{k}</option>
            ))}
          </select>
          <select
            aria-label="Risk level"
            value={level}
            onChange={(e) => {
              setLevel(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All risk levels</option>
            {["low", "moderate", "high", "critical"].map((k) => (
              <option key={k}>{k}</option>
            ))}
          </select>
        </div>
        <ScanTable items={data.items} onDelete={remove} />
        <div className="pagination">
          <span>
            {data.total} records · Page {page}
          </span>
          <button disabled={page === 1} onClick={() => setPage(page - 1)}>
            Previous
          </button>
          <button
            disabled={page * 20 >= data.total}
            onClick={() => setPage(page + 1)}
          >
            Next
          </button>
        </div>
      </div>
    </>
  );
}
function Reports() {
  const [items, setItems] = useState([]),
    [error, setError] = useState(""),
    [success, setSuccess] = useState(""),
    [busy, setBusy] = useState(false);
  const load = () =>
    api
      .get("/reports")
      .then((r) => setItems(r.data))
      .catch((e) => setError(errorText(e)));
  useEffect(() => {
    load();
  }, []);
  async function submit(e) {
    e.preventDefault();
    const form = e.currentTarget;
    setBusy(true);
    setError("");
    try {
      const f = new FormData(form);
      await api.post("/reports", {
        category: f.get("category"),
        description: f.get("description"),
      });
      setSuccess("Report submitted for review. It is not a verified threat.");
      form.reset();
      load();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageTitle
        eyebrow="SEE SOMETHING? SAY SOMETHING."
        title="Threat reports"
        description="Help document suspicious activity. Reports are not official police complaints."
      />
      <div className="scanner-layout">
        <section className="panel padded">
          <h2>Submit a report</h2>
          <form onSubmit={submit}>
            <label>
              Category
              <select name="category">
                {["URL", "Message", "UPI", "Email", "Phone", "Other"].map(
                  (c) => (
                    <option key={c}>{c}</option>
                  ),
                )}
              </select>
            </label>
            <label>
              What happened?
              <textarea
                name="description"
                minLength={10}
                maxLength={4000}
                rows={7}
                required
                placeholder="Describe the suspicious content. Do not include secrets or OTPs."
              />
            </label>
            <ErrorBox error={error} />
            {success && <p className="success-text">{success}</p>}
            <button className="btn primary" disabled={busy}>
              <Flag size={16} /> {busy ? "Submitting…" : "Submit report"}
            </button>
          </form>
        </section>
        <section className="panel padded">
          <h2>Your reports</h2>
          {items.length ? (
            items.map((r) => (
              <div className="report-item" key={r.id}>
                <span className="eyebrow">
                  #{r.id} · {r.category}
                </span>
                <p>{r.description}</p>
                <span className="report-status">{r.status}</span>
              </div>
            ))
          ) : (
            <p className="muted">No reports submitted yet.</p>
          )}
        </section>
      </div>
    </>
  );
}
function SettingsPage() {
  const { user, setUser } = useContext(Auth),
    [error, setError] = useState(""),
    [message, setMessage] = useState("");
  async function profile(e) {
    e.preventDefault();
    try {
      const r = await api.put("/profile", {
        name: new FormData(e.currentTarget).get("name"),
      });
      setUser(r.data);
      setMessage("Profile saved.");
    } catch (e) {
      setError(errorText(e));
    }
  }
  async function change(e) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    try {
      await api.put("/profile/password", {
        current_password: f.get("current"),
        new_password: f.get("new"),
      });
      sessionStorage.removeItem("token");
      setUser(null);
    } catch (e) {
      setError(errorText(e));
    }
  }
  return (
    <>
      <PageTitle
        eyebrow="YOUR ACCOUNT"
        title="Profile & security"
        description="Keep your details up to date and your account protected."
      />
      <ErrorBox error={error} />
      {message && <p className="success-text">{message}</p>}
      <div className="scanner-layout">
        <section className="panel padded">
          <h2>Personal details</h2>
          <form onSubmit={profile}>
            <label>
              Name
              <input
                name="name"
                defaultValue={user.name}
                minLength={2}
                maxLength={80}
                required
              />
            </label>
            <label>
              Email
              <input value={user.email} disabled />
            </label>
            <p className="muted">
              Email verification protects your family invitations.
            </p><Link className="text-link" to="/verify-email">{user.email_verified ? "Email verified" : "Verify email"}</Link>
            <button className="btn primary">Save changes</button>
          </form>
        </section>
        <section className="panel padded">
          <h2>Change password</h2>
          <form onSubmit={change}>
            <label>
              Current password
              <input
                name="current"
                type="password"
                autoComplete="current-password"
                required
              />
            </label>
            <label>
              New password
              <input
                name="new"
                type="password"
                autoComplete="new-password"
                minLength={12}
                maxLength={128}
                required
              />
            </label>
            <p className="muted">
              Use at least 12 characters. Changing your password signs out all
              sessions.
            </p>
            <button className="btn secondary">Update password</button>
          </form>
        </section>
      </div>
    </>
  );
}
const authSchema = z.object({
  email: z.string().email("Enter a valid email address."),
  password: z.string().min(1, "Enter your password."),
});
function AuthPage({ register = false }) {
  const { setUser } = useContext(Auth),
    navigate = useNavigate(),
    [error, setError] = useState(""),
    [visible, setVisible] = useState(false);
  const schema = register
    ? authSchema.extend({
        name: z.string().trim().min(2, "Enter at least two characters."),
        password: z.string().min(12, "Use at least 12 characters.").max(128),
      })
    : authSchema;
  const {
    register: field,
    handleSubmit,
    formState: { errors, isSubmitting },
    watch,
  } = useForm({ resolver: zodResolver(schema) });
  const pass = watch("password", "");
  const submit = async (values) => {
    try {
      const r = await api.post(
        register ? "/auth/register" : "/auth/login",
        values,
      );
      sessionStorage.setItem("token", r.data.token);
      setUser(r.data.user);
      navigate("/");
    } catch (e) {
      setError(errorText(e));
    }
  };
  return (
    <div className="auth-page">
      <div className="auth-brand">
        <Brand />
      </div>
      <div className="auth-decoration">
        <span className="hero-tag">
          <ShieldCheck size={14} /> A SAFER DIGITAL EVERYDAY
        </span>
        <h1>
          One step ahead
          <br />
          of the next scam.
        </h1>
        <p>
          Your messages. Your money. Your peace of mind.
          <br />
          Protect what matters with clear, practical security checks.
        </p>
        <div className="auth-shield">
          <ShieldCheck size={160} strokeWidth={0.8} />
        </div>
        <div className="auth-values">
          <span>
            <Check size={15} /> Private scan history
          </span>
          <span>
            <Check size={15} /> Transparent analysis
          </span>
        </div>
      </div>
      <section className="auth-card panel">
        <span className="large-scan-icon">
          <LockKeyhole size={25} />
        </span>
        <h2>
          {register ? "Create your safe space." : "Good to have you back."}
        </h2>
        <p>
          {register
            ? "Start making safer digital decisions."
            : "Sign in to your personal security workspace."}
        </p>
        <ErrorBox error={error} />
        <form onSubmit={handleSubmit(submit)}>
          {register && (
            <label>
              Full name
              <input {...field("name")} autoComplete="name" />
              {errors.name && (
                <small className="field-error">{errors.name.message}</small>
              )}
            </label>
          )}
          <label>
            Email address
            <input
              {...field("email")}
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
            />
            {errors.email && (
              <small className="field-error">{errors.email.message}</small>
            )}
          </label>
          <label>
            Password
            <div className="password-input">
              <input
                {...field("password")}
                type={visible ? "text" : "password"}
                autoComplete={register ? "new-password" : "current-password"}
                placeholder={
                  register ? "At least 12 characters" : "Your password"
                }
              />
              <button
                type="button"
                aria-label={visible ? "Hide password" : "Show password"}
                onClick={() => setVisible(!visible)}
              >
                {visible ? <EyeOff size={17} /> : <Eye size={17} />}
              </button>
            </div>
            {errors.password && (
              <small className="field-error">{errors.password.message}</small>
            )}
          </label>
          {register && (
            <div className="strength">
              <div
                style={{
                  width: `${Math.min(100, (pass.length / 16) * 100)}%`,
                  background: pass.length >= 12 ? "#31caa0" : "#e5ae47",
                }}
              />
              <span>
                {pass.length >= 12
                  ? "Length requirement met"
                  : "Use at least 12 characters; a unique passphrase is best."}
              </span>
            </div>
          )}
          {!register && (
            <Link className="forgot" to="/forgot-password">
              Forgot password?
            </Link>
          )}
          <button className="btn primary auth-submit" disabled={isSubmitting}>
            {isSubmitting ? <LoaderCircle size={17} className="spin" /> : null}
            {register ? "Create account" : "Sign in securely"}
            <ArrowRight size={17} />
          </button>
        </form>
        <p className="auth-switch">
          {register ? "Already have an account?" : "New to ScamShield?"}{" "}
          <Link to={register ? "/login" : "/register"}>
            {register ? "Sign in" : "Create account"}
          </Link>
        </p>
        <div className="auth-foot">
          <LockKeyhole size={12} /> Passwords are securely hashed. Never share
          your OTP or PIN.
        </div>
        <Link to="/" className="text-link">
          ← Back to overview
        </Link>
      </section>
    </div>
  );
}
function Recovery({ reset = false }) {
  const [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const f = new FormData(e.currentTarget);
    try {
      const r = await api.post(
        reset ? "/auth/reset-password" : "/auth/forgot-password",
        reset
          ? {
              token: new URLSearchParams(location.search).get("token") || "",
              password: f.get("password"),
            }
          : { email: f.get("email") },
      );
      setMessage(r.data.message);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="recovery">
      <Brand />
      <section className="panel auth-card">
        <h2>{reset ? "Choose a new password" : "Forgot your password?"}</h2>
        <p>
          {reset
            ? "Your reset link is single-use and expires in 20 minutes."
            : "We’ll email a secure reset link if your account exists."}
        </p>
        <ErrorBox error={error} />
        {message ? (
          <p className="success-text">{message}</p>
        ) : (
          <form onSubmit={submit}>
            <label>
              {reset ? "New password" : "Email address"}
              <input
                name={reset ? "password" : "email"}
                type={reset ? "password" : "email"}
                minLength={reset ? 12 : undefined}
                maxLength={128}
                required
              />
            </label>
            <button className="btn primary" disabled={busy}>
              {busy
                ? "Please wait…"
                : reset
                  ? "Reset password"
                  : "Send reset link"}
            </button>
          </form>
        )}
        <Link className="text-link" to="/login">
          Back to sign in
        </Link>
      </section>
    </div>
  );
}
function Awareness() {
  const [answer, setAnswer] = useState(null);
  return (
    <>
      <PageTitle
        eyebrow="AWARENESS IS YOUR FIRST DEFENSE"
        title="Build your scam instincts."
        description="Simple habits. Safer choices. Share these tips with someone you care about."
      />
      <div className="quick-grid safety-grid">
        {[
          [
            IndianRupee,
            "UPI safety",
            "A UPI PIN authorizes an outgoing payment. You never need to share it to receive money. Verify payment in your own app, never from a screenshot.",
          ],
          [
            Link2,
            "Look at the real domain",
            "Read the full hostname. bank.example.com belongs to example.com. HTTPS encrypts traffic but does not mean a site is trustworthy.",
          ],
          [
            LockKeyhole,
            "Keep your secrets secret",
            "Never share an OTP, recovery code, password or PIN. Use unique passwords and turn on two-factor authentication.",
          ],
          [
            MessageSquare,
            "Pause under pressure",
            "Urgent account blocks, guaranteed jobs and advance fees are red flags. Call the organization using a number you find independently.",
          ],
          [
            Globe,
            "Browse with care",
            "Keep your browser updated. Avoid unknown extensions, unexpected downloads and granting notification permissions to unfamiliar websites.",
          ],
          [
            Mail,
            "Question the sender",
            "A familiar display name can hide an unrelated email address. Verify unexpected attachments and payment-detail changes through a separate channel.",
          ],
        ].map(([I, t, p]) => (
          <section className="panel padded" key={t}>
            <I className="cyan" size={27} />
            <h3>{t}</h3>
            <p>{p}</p>
          </section>
        ))}
      </div>
      <section className="panel padded quiz">
        <span className="eyebrow">A 10-SECOND SAFETY CHECK</span>
        <h2>
          Someone wants to send you a refund. They ask you to enter your UPI
          PIN. What do you do?
        </h2>
        {[
          "Enter the PIN to receive the money",
          "Decline and verify through the official app",
        ].map((a, i) => (
          <button
            className={"quiz-option " + (answer === i ? "selected" : "")}
            key={a}
            onClick={() => setAnswer(i)}
          >
            {a}
            <ChevronRight size={17} />
          </button>
        ))}
        {answer !== null && (
          <div className={answer === 1 ? "success-text" : "field-error"}>
            {answer === 1 ? "Exactly right." : "Not quite."} A UPI PIN
            authorizes an outgoing payment. Never enter it just to receive
            money. Quiz answers are not persisted in this release.
          </div>
        )}
      </section>
    </>
  );
}
function Emergency() {
  return (
    <>
      <PageTitle
        eyebrow="ACT QUICKLY. YOU ARE NOT ALONE."
        title="Think you've been scammed?"
        description="A fast response may limit the damage. Recovery cannot be guaranteed."
      />
      <section className="emergency-hero panel">
        <LifeBuoy size={40} />
        <div>
          <h2>Financial cyber fraud? Call 1930.</h2>
          <p>
            Contact your bank or payment provider immediately using its official
            app or published number.
          </p>
          <a className="btn primary" href="tel:1930">
            Call 1930 <ArrowUpRight size={16} />
          </a>
          <a
            className="btn secondary"
            href="https://cybercrime.gov.in/"
            target="_blank"
            rel="noopener noreferrer"
          >
            National Cyber Crime Reporting Portal <ExternalLink size={15} />
          </a>
        </div>
      </section>
      <div className="scanner-layout">
        {[
          [
            "1",
            "Stop contact and secure your money",
            "Do not send further money, even if someone promises to recover your loss for a fee. Ask your bank or payment provider to block compromised accounts or cards and dispute the transaction.",
          ],
          [
            "2",
            "Secure affected accounts",
            "From a trusted device, change exposed passwords, revoke active sessions and enable two-factor authentication. If you installed remote-access software, disconnect the device and seek trusted technical help.",
          ],
          [
            "3",
            "Preserve your evidence",
            "Save transaction IDs, dates, messages, phone numbers, email headers and screenshots. Do not alter or delete the original evidence.",
          ],
          [
            "4",
            "Report through official channels",
            "Call 1930 promptly for financial cyber fraud and file a complaint at cybercrime.gov.in. A ScamShield threat report is not a police complaint.",
          ],
        ].map(([n, t, p]) => (
          <section className="panel padded" key={n}>
            <span className="step-number">{n}</span>
            <h3>{t}</h3>
            <p>{p}</p>
          </section>
        ))}
      </div>
    </>
  );
}
export { App, AuthPage, Auth, Scanner, Risk, Recovery };
if (document.getElementById("root"))
  createRoot(document.getElementById("root")).render(<App />);
