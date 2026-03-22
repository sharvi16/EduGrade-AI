import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth, type Role } from "@/context/AuthContext";

const EyeIcon = ({ open }: { open: boolean }) =>
    open ? (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 16, height: 16 }}>
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
            <circle cx="12" cy="12" r="3" />
        </svg>
    ) : (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 16, height: 16 }}>
            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
            <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
            <line x1="1" y1="1" x2="23" y2="23" />
        </svg>
    );

const LoginPage: React.FC = () => {
    const { login } = useAuth();
    const navigate = useNavigate();
    const [role, setRole] = useState<Role>("student");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [showPass, setShowPass] = useState(false);
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const [shake, setShake] = useState(false);

    const switchRole = (r: Role) => {
        setRole(r);
        setError("");
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError("");
        const ok = await login(email, password);
        if (ok) {
            // Wait for context update
            setTimeout(() => {
                navigate("/", { replace: true });
            }, 100);
        } else {
            setLoading(false);
            setError("Invalid email or password. Please check your credentials.");
            setShake(true);
            setTimeout(() => setShake(false), 500);
        }
    };

    return (
        <div className="login-shell">
            {/* ── Left decorative panel ─────────────────────────────── */}
            <div className="login-panel">
                <div className="login-panel-content">
                    <div className="login-brand">
                        <div className="login-brand-icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 22, height: 22 }}>
                                <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
                                <path d="M6 12v5c3 3 9 3 12 0v-5" />
                            </svg>
                        </div>
                        <span className="login-brand-name">Edu<span>Grade</span> AI</span>
                    </div>

                    <div className="login-panel-hero">
                        <h2>AI-Powered<br />Exam Grading</h2>
                        <p>Automated grading, viva proctoring, and assignment OCR — all in one platform.</p>
                    </div>

                    <div className="login-features">
                        {[
                            { icon: "🧠", label: "Vision AI grading" },
                            { icon: "👁️", label: "Live viva proctoring" },
                            { icon: "📄", label: "Handwriting OCR" },
                            { icon: "📊", label: "Detailed feedback" },
                        ].map(f => (
                            <div key={f.label} className="login-feature-item">
                                <span className="login-feature-icon">{f.icon}</span>
                                <span>{f.label}</span>
                            </div>
                        ))}
                    </div>

                    {/* floating blobs */}
                    <div className="login-blob login-blob-1" />
                    <div className="login-blob login-blob-2" />
                </div>
            </div>

            {/* ── Right form panel ──────────────────────────────────── */}
            <div className="login-form-side">
                <div className={`login-form-card${shake ? " login-shake" : ""}`}>
                    <div className="login-form-header">
                        <h1>Welcome back</h1>
                        <p>Sign in to your account to continue</p>
                    </div>

                    {/* Role toggle */}
                    <div className="role-toggle" role="group" aria-label="Select role">
                        {(["student", "teacher", "principal", "super_admin"] as Role[]).map(r => (
                            <button
                                key={r}
                                type="button"
                                className={`role-toggle-btn${role === r ? " active" : ""}`}
                                onClick={() => switchRole(r)}
                                style={{ fontSize: '12px', padding: '8px 4px' }}
                            >
                                <span className="role-icon">
                                    {r === "super_admin" ? "🛡️" : r === "principal" ? "🏫" : r === "teacher" ? "🎓" : "📚"}
                                </span>
                                {r === "super_admin" ? "Admin" : r === "principal" ? "Principal" : r === "teacher" ? "Teacher" : "Student"}
                            </button>
                        ))}
                    </div>

                    <form onSubmit={handleSubmit} className="login-form" noValidate>
                        {/* Dummy inputs to fool browser autofill */}
                        <input type="text" name="email" style={{ display: 'none' }} tabIndex={-1} />
                        <input type="password" name="password" style={{ display: 'none' }} tabIndex={-1} />

                        <div className="login-field">
                            <label htmlFor="user_login_email">Email address</label>
                            <div className="login-input-wrap">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="login-input-icon">
                                    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                                    <polyline points="22,6 12,13 2,6" />
                                </svg>
                                <input
                                    id="user_login_email"
                                    name="user_login_email"
                                    type="email"
                                    autoComplete="new-password"
                                    required
                                    readOnly
                                    onFocus={(e) => e.target.removeAttribute('readonly')}
                                    value={email}
                                    onChange={e => { setEmail(e.target.value); setError(""); }}
                                    placeholder="you@school.com"
                                    className="login-input"
                                />
                            </div>
                        </div>

                        <div className="login-field">
                            <label htmlFor="user_login_pass">Password</label>
                            <div className="login-input-wrap">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="login-input-icon">
                                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                                </svg>
                                <input
                                    id="user_login_pass"
                                    name="user_login_pass"
                                    type={showPass ? "text" : "password"}
                                    autoComplete="new-password"
                                    required
                                    readOnly
                                    onFocus={(e) => e.target.removeAttribute('readonly')}
                                    value={password}
                                    onChange={e => { setPassword(e.target.value); setError(""); }}
                                    placeholder="••••••••"
                                    className="login-input"
                                    style={{ paddingRight: 40 }}
                                />
                                <button type="button" className="login-eye-btn" onClick={() => setShowPass(p => !p)} aria-label="Toggle password visibility">
                                    <EyeIcon open={showPass} />
                                </button>
                            </div>
                        </div>

                        {error && (
                            <div className="login-error" role="alert">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 15, height: 15, flexShrink: 0 }}>
                                    <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
                                </svg>
                                {error}
                            </div>
                        )}

                        <button type="submit" disabled={loading} className="login-submit-btn">
                            {loading ? (
                                <>
                                    <span className="login-spinner" />
                                    Signing in...
                                </>
                            ) : (
                                <>
                                    Sign in as {role === "super_admin" ? "Admin" : 
                                               role === "principal" ? "Principal" :
                                               role === "teacher" ? "Teacher" : "Student"}
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 15, height: 15 }}>
                                        <line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" />
                                    </svg>
                                </>
                            )}
                        </button>
                    </form>

                </div>
            </div>
        </div>
    );
};

export default LoginPage;
