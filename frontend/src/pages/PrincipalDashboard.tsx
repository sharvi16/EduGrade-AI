import React, { useState, useEffect, useCallback } from 'react';
import { createUser, listUsers } from '../api/client';
import { Users, Mail, UserPlus, Shield, CheckCircle, XCircle } from 'lucide-react';
import { cn } from "@/lib/utils";

const PrincipalDashboard: React.FC = () => {
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [teachers, setTeachers] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [msg, setMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
    const [submitting, setSubmitting] = useState(false);

    const fetchTeachers = useCallback(async () => {
        setLoading(true);
        try {
            const data = await listUsers();
            setTeachers(data.filter(u => u.role === 'teacher'));
        } catch (err) {
            console.error("Failed to fetch teachers", err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchTeachers();
    }, [fetchTeachers]);

    const handleAddTeacher = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!name || !email || !password) return;
        
        setSubmitting(true);
        setMsg(null);
        try {
            await createUser({ name, email, password, role: 'teacher' });
            setMsg({ type: "success", text: `Teacher ${name} registered successfully!` });
            setName(''); setEmail(''); setPassword('');
            fetchTeachers();
        } catch (err: any) {
            setMsg({ type: "error", text: err.response?.data?.detail || "Failed to add teacher" });
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="max-w-6xl mx-auto p-8 space-y-10 animate-fade-up font-sans">
            <div className="page-header">
                <div className="flex items-center gap-3 mb-2">
                    <div className="h-10 w-10 rounded-xl flex items-center justify-center shrink-0"
                        style={{ background: "linear-gradient(135deg, #ede9fe 0%, #e0f2fe 100%)", border: "1px solid rgba(124,58,237,0.15)" }}>
                        <Shield className="h-5 w-5" style={{ color: "#7c3aed" }} />
                    </div>
                    <h1 className="text-gradient" style={{ fontSize: "1.7rem", fontWeight: 700, letterSpacing: "-0.02em" }}>Principal Dashboard</h1>
                </div>
                <p className="text-muted-foreground">Manage your school's faculty and academic structure</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
                {/* Registration Form */}
                <section className="bg-white rounded-[2rem] border border-slate-100 shadow-[0_8px_30px_rgb(0,0,0,0.04)] p-8">
                    <div className="flex items-center gap-3 mb-8">
                        <div className="h-9 w-9 rounded-xl flex items-center justify-center"
                            style={{ background: "#f5f3ff" }}>
                            <UserPlus className="h-5 w-5" style={{ color: "#7c3aed" }} />
                        </div>
                        <h2 className="font-bold text-lg text-slate-800">Register New Teacher</h2>
                    </div>

                    <form onSubmit={handleAddTeacher} className="space-y-6" noValidate>
                        <input type="text" name="email" style={{ display: 'none' }} tabIndex={-1} />
                        <input type="password" name="password" style={{ display: 'none' }} tabIndex={-1} />
                        
                        <div className="space-y-2">
                            <label className="text-sm font-bold text-slate-700 ml-1">Teacher Name</label>
                            <input 
                                id="teacher_reg_name"
                                name="teacher_reg_name"
                                className="w-full bg-slate-50/50 border border-slate-200 rounded-2xl p-4 text-slate-900 focus:ring-2 focus:ring-purple-500/20 focus:border-purple-400 outline-none transition-all placeholder:text-slate-400" 
                                value={name} 
                                onChange={e => setName(e.target.value)} 
                                placeholder="e.g. Prof. Arvind Kumar"
                                required
                                autoComplete="new-password"
                                readOnly
                                onFocus={(e) => e.target.removeAttribute('readonly')}
                            />
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-bold text-slate-700 ml-1">Email Address</label>
                            <input 
                                id="teacher_reg_email"
                                name="teacher_reg_email"
                                type="email"
                                className="w-full bg-slate-50/50 border border-slate-200 rounded-2xl p-4 text-slate-900 focus:ring-2 focus:ring-purple-500/20 focus:border-purple-400 outline-none transition-all placeholder:text-slate-400" 
                                value={email} 
                                onChange={e => setEmail(e.target.value)} 
                                placeholder="teacher@school.com"
                                required
                                autoComplete="new-password"
                                readOnly
                                onFocus={(e) => e.target.removeAttribute('readonly')}
                            />
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-bold text-slate-700 ml-1">Temporary Password</label>
                            <input 
                                id="teacher_reg_pass"
                                name="teacher_reg_pass"
                                type="password"
                                className="w-full bg-slate-50/50 border border-slate-200 rounded-2xl p-4 text-slate-900 focus:ring-2 focus:ring-purple-500/20 focus:border-purple-400 outline-none transition-all placeholder:text-slate-400" 
                                value={password} 
                                onChange={e => setPassword(e.target.value)} 
                                placeholder="••••••••"
                                required
                                autoComplete="new-password"
                                readOnly
                                onFocus={(e) => e.target.removeAttribute('readonly')}
                            />
                        </div>

                        {msg && (
                            <div className={cn("p-4 rounded-2xl text-sm flex gap-3 animate-fade-in", 
                                msg.type === "success" ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200")}>
                                {msg.type === "success" ? <CheckCircle className="h-5 w-5 shrink-0" /> : <XCircle className="h-5 w-5 shrink-0" />}
                                <span className="font-semibold">{msg.text}</span>
                            </div>
                        )}

                        <button 
                            type="submit"
                            disabled={submitting}
                            className="w-full h-14 rounded-2xl text-white font-bold text-lg shadow-lg shadow-purple-200 hover:shadow-purple-300 hover:-translate-y-0.5 transition-all flex items-center justify-center gap-2"
                            style={{ background: "linear-gradient(90deg, #7c3aed 0%, #0ea5e9 100%)" }}
                        >
                            {submitting ? (
                                <span className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            ) : "Register Teacher"}
                        </button>
                    </form>
                </section>

                {/* Teachers List */}
                <section className="bg-white rounded-[2rem] border border-slate-100 shadow-[0_8px_30px_rgb(0,0,0,0.04)] p-8">
                    <div className="flex items-center justify-between mb-8">
                        <div className="flex items-center gap-3">
                            <div className="h-9 w-9 rounded-xl flex items-center justify-center"
                                style={{ background: "#ede9fe" }}>
                                <Users className="h-5 w-5" style={{ color: "#7c3aed" }} />
                            </div>
                            <h2 className="font-bold text-lg text-slate-800">Faculty Members</h2>
                        </div>
                        <span className="badge-purple px-3 py-1 font-bold">{teachers.length} Active</span>
                    </div>

                    {loading ? (
                        <div className="space-y-4">
                            {[1, 2, 3, 4].map(i => (
                                <div key={i} className="h-16 bg-slate-50 animate-pulse rounded-2xl border border-slate-100" />
                            ))}
                        </div>
                    ) : teachers.length === 0 ? (
                        <div className="text-center py-16 bg-slate-50/50 rounded-3xl border border-dashed border-slate-200">
                            <Users className="h-10 w-10 text-slate-300 mx-auto mb-3" />
                            <p className="text-slate-500 font-bold">No teachers registered yet</p>
                            <p className="text-xs text-slate-400 mt-1">Add your first faculty member using the form</p>
                        </div>
                    ) : (
                        <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
                            {teachers.map((t) => (
                                <div key={t.id} className="p-4 bg-white rounded-2xl border border-slate-100 flex items-center justify-between shadow-sm hover:shadow-md hover:border-purple-100 transition-all group px-5">
                                    <div className="flex items-center gap-4">
                                        <div className="h-12 w-12 rounded-2xl bg-gradient-to-br from-purple-50 to-blue-50 flex items-center justify-center font-black text-purple-600 group-hover:from-purple-600 group-hover:to-indigo-600 group-hover:text-white transition-all duration-300 shadow-inner">
                                            {t.name.charAt(0).toUpperCase()}
                                        </div>
                                        <div>
                                            <p className="font-extrabold text-slate-900 text-sm leading-tight">{t.name}</p>
                                            <div className="flex items-center gap-1.5 mt-1">
                                                <Mail className="h-3 w-3 text-slate-400" />
                                                <p className="text-[11px] text-slate-500 font-medium">{t.email}</p>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="h-2 w-2 rounded-full bg-green-400 shadow-[0_0_8px_rgba(74,222,128,0.5)] animate-pulse" />
                                </div>
                            ))}
                        </div>
                    )}
                </section>
            </div>
        </div>
    );
};

export default PrincipalDashboard;
