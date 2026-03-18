import { BrowserRouter, NavLink, Navigate, Route, Routes } from "react-router-dom";
import StudentGrader from "./pages/StudentGrader";
import TeacherPortal from "./pages/TeacherPortal";
import LoginPage from "./pages/LoginPage";
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider, useAuth } from "./context/AuthContext";

// ── Nav items ────────────────────────────────────────────────────
const ALL_NAV = [
  {
    to: "/teacher",
    label: "Teacher Portal",
    role: "teacher" as const,
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
        <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
      </svg>
    ),
  },
  {
    to: "/grade",
    label: "Student Grader",
    role: "student" as const,
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="8" r="6" />
        <path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11" />
      </svg>
    ),
  },
];

// ── Sidebar (auth-aware) ─────────────────────────────────────────
function Sidebar() {
  const { user, logout } = useAuth();
  const nav = ALL_NAV.filter(n => n.role === user?.role);
  const initials = user?.name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase() ?? "?";

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5"
            strokeLinecap="round" strokeLinejoin="round" style={{ width: 16, height: 16 }}>
            <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
            <path d="M6 12v5c3 3 9 3 12 0v-5" />
          </svg>
        </div>
        <span className="sidebar-logo-text">
          Edu<span>Grade</span> AI
        </span>
      </div>

      {/* Nav */}
      <nav className="sidebar-nav">
        <p className="sidebar-section-label">Navigation</p>
        {nav.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}
          >
            {icon}
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User profile + Logout */}
      <div className="sidebar-footer">
        {user && (
          <div className="sidebar-user">
            <div className="sidebar-user-avatar">{initials}</div>
            <div className="sidebar-user-info">
              <p className="sidebar-user-name">{user.name}</p>
              <span className={`sidebar-role-badge sidebar-role-badge--${user.role}`}>
                {user.role === "teacher" ? "🎓 Teacher" : "📚 Student"}
              </span>
            </div>
          </div>
        )}
        <button className="sidebar-logout-btn" onClick={logout}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 15, height: 15 }}>
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
          Sign out
        </button>
      </div>
    </aside>
  );
}

// ── Authenticated shell ──────────────────────────────────────────
function AppShell() {
  const { user } = useAuth();

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <Routes>
          {/* Teacher routes */}
          <Route path="/teacher" element={<ProtectedRoute allowedRoles={["teacher"]}><TeacherPortal /></ProtectedRoute>} />

          {/* Student routes */}
          <Route path="/grade" element={<ProtectedRoute allowedRoles={["student"]}><StudentGrader /></ProtectedRoute>} />

          {/* Default redirect based on auth status and role */}
          <Route path="/" element={<Navigate to={user ? (user.role === "teacher" ? "/teacher" : "/grade") : "/login"} replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

// ── Root ─────────────────────────────────────────────────────────
function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/*" element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          } />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
