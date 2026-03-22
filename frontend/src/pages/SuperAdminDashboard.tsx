import React, { useEffect, useState } from 'react';
import { listSchools, createSchool, createUser } from '../api/client';
import { Building2, Shield, Plus, UserPlus, X, Landmark, XCircle } from 'lucide-react';

const AddPrincipalModal: React.FC<{ 
    school: { id: string, name: string } | null, 
    onClose: () => void, 
    onSuccess: () => void 
}> = ({ school, onClose, onSuccess }) => {
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    if (!school) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSubmitting(true);
        setError(null);
        try {
            await createUser({ name, email, password, role: 'principal', school_id: school.id });
            onSuccess();
            onClose();
        } catch (err: any) {
            setError(err.response?.data?.detail || "Failed to add principal");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
            <div className="bg-white rounded-[2rem] w-full max-w-md shadow-2xl border border-slate-100 p-8 animate-scale-up">
                <div className="flex items-center justify-between mb-8">
                    <div className="flex items-center gap-3">
                        <div className="h-9 w-9 rounded-xl flex items-center justify-center" style={{ background: "#f5f3ff" }}>
                            <UserPlus className="h-5 w-5" style={{ color: "#7c3aed" }} />
                        </div>
                        <h2 className="font-bold text-lg text-slate-800">Add Principal</h2>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-lg transition-colors">
                        <X className="h-5 w-5 text-slate-400" />
                    </button>
                </div>

                <div className="mb-6 p-4 bg-purple-50 rounded-2xl border border-purple-100 flex items-center gap-3">
                    <Landmark className="h-5 w-5 text-purple-500" />
                    <div>
                        <p className="text-[10px] uppercase font-bold text-purple-400 tracking-wider">Target School</p>
                        <p className="font-bold text-purple-900 text-sm">{school.name}</p>
                    </div>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="space-y-1.5">
                        <label className="text-sm font-bold text-slate-700 ml-1">Principal Name</label>
                        <input 
                            className="bg-slate-50/50 border border-slate-200 rounded-2xl p-4 w-full outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-400 transition-all text-sm font-medium" 
                            placeholder="Full Name"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            required
                        />
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-sm font-bold text-slate-700 ml-1">Email Address</label>
                        <input 
                            type="email"
                            className="bg-slate-50/50 border border-slate-200 rounded-2xl p-4 w-full outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-400 transition-all text-sm font-medium" 
                            placeholder="principal@school.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                        />
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-sm font-bold text-slate-700 ml-1">Password</label>
                        <input 
                            type="password"
                            className="bg-slate-50/50 border border-slate-200 rounded-2xl p-4 w-full outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-400 transition-all text-sm font-medium" 
                            placeholder="••••••••"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>

                    {error && (
                        <div className="p-4 bg-red-50 border border-red-100 text-red-700 rounded-2xl text-xs font-bold animate-shake flex gap-2">
                            <XCircle className="h-4 w-4 shrink-0" /> {error}
                        </div>
                    )}

                    <button 
                        type="submit"
                        disabled={submitting}
                        className="w-full h-14 rounded-2xl text-white font-bold text-lg shadow-lg shadow-purple-200 hover:shadow-purple-300 hover:-translate-y-0.5 transition-all flex items-center justify-center gap-2 mt-4"
                        style={{ background: "linear-gradient(90deg, #7c3aed 0%, #0ea5e9 100%)" }}
                    >
                        {submitting ? <span className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : "Save Principal"}
                    </button>
                </form>
            </div>
        </div>
    );
};

const SuperAdminDashboard: React.FC = () => {
    const [schools, setSchools] = useState<any[]>([]);
    const [newSchoolName, setNewSchoolName] = useState('');
    const [loading, setLoading] = useState(true);
    const [activeSchool, setActiveSchool] = useState<{ id: string, name: string } | null>(null);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const data = await listSchools();
            setSchools(data);
        } catch (err) {
            console.error('Failed to load schools', err);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateSchool = async () => {
        if (!newSchoolName) return;
        try {
            await createSchool(newSchoolName);
            setNewSchoolName('');
            loadData();
        } catch (err) {
            alert('Failed to create school');
        }
    };

    if (loading) return (
        <div className="h-[80vh] flex flex-col items-center justify-center gap-4">
            <div className="h-12 w-12 border-4 border-purple-100 border-t-purple-600 rounded-full animate-spin" />
            <p className="text-slate-400 font-bold animate-pulse">Initializing Platform Management...</p>
        </div>
    );

    return (
        <div className="max-w-7xl mx-auto p-8 space-y-12 animate-fade-up font-sans">
            <div className="page-header">
                <div className="flex items-center gap-3 mb-2">
                    <div className="h-10 w-10 rounded-xl flex items-center justify-center shrink-0"
                        style={{ background: "linear-gradient(135deg, #ede9fe 0%, #e0f2fe 100%)", border: "1px solid rgba(124,58,237,0.15)" }}>
                        <Shield className="h-5 w-5" style={{ color: "#7c3aed" }} />
                    </div>
                    <h1 className="text-gradient" style={{ fontSize: "1.8rem", fontWeight: 800, letterSpacing: "-0.02em" }}>Super Admin Hub</h1>
                </div>
                <p className="text-muted-foreground">Orchestrate global school infrastructure and administration</p>
            </div>
            
            <section className="bg-white rounded-[2.5rem] border border-slate-100 shadow-[0_8px_30px_rgb(0,0,0,0.04)] p-10">
                <div className="flex items-center gap-3 mb-8">
                    <div className="h-9 w-9 rounded-xl flex items-center justify-center" style={{ background: "#f0f9ff" }}>
                        <Building2 className="h-5 w-5" style={{ color: "#0ea5e9" }} />
                    </div>
                    <h2 className="font-bold text-xl text-slate-800">Register New School</h2>
                </div>
                <div className="flex flex-col md:flex-row gap-5">
                    <input 
                        className="bg-slate-50/50 border border-slate-200 rounded-2xl p-5 flex-1 text-slate-900 outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-400 transition-all font-medium placeholder:text-slate-400" 
                        placeholder="e.g. Greenwood International High School"
                        value={newSchoolName}
                        onChange={(e) => setNewSchoolName(e.target.value)}
                    />
                    <button 
                        onClick={handleCreateSchool}
                        className="h-[60px] px-8 rounded-2xl text-white font-bold text-lg shadow-lg shadow-sky-100 hover:shadow-sky-200 hover:-translate-y-0.5 transition-all flex items-center justify-center gap-2 whitespace-nowrap"
                        style={{ background: "linear-gradient(90deg, #0ea5e9 0%, #2dd4bf 100%)" }}
                    >
                        <Plus className="h-6 w-6" /> Add New School
                    </button>
                </div>
            </section>

            <section className="space-y-8">
                <div className="flex items-center gap-3 ml-2">
                    <div className="h-9 w-9 rounded-xl flex items-center justify-center" style={{ background: "#f5f3ff" }}>
                        <Landmark className="h-5 w-5" style={{ color: "#7c3aed" }} />
                    </div>
                    <h2 className="font-extrabold text-xl text-slate-800">Operational Networks</h2>
                    <span className="badge-purple px-3 py-1 font-bold ml-1">{schools.length} total</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
                    {schools.map(school => (
                        <div key={school.id} className="bg-white p-8 rounded-[2rem] border border-slate-100 shadow-[0_4px_20px_rgb(0,0,0,0.03)] hover:shadow-xl hover:border-purple-100 transition-all group relative overflow-hidden">
                            <div className="absolute top-0 right-0 w-32 h-32 bg-purple-50 rounded-full -mr-16 -mt-16 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                            <h3 className="text-xl font-bold text-slate-900 mb-2 relative">{school.name}</h3>
                            <div className="flex items-center gap-2 text-slate-400 text-xs font-bold tracking-wider mb-6 relative">
                                <Landmark className="h-3 w-3" /> NETWORK ID: {school.id}
                            </div>
                            <button 
                                onClick={() => setActiveSchool(school)}
                                className="w-full h-12 rounded-xl bg-slate-50 text-purple-600 font-bold text-sm hover:bg-purple-600 hover:text-white transition-all duration-300 flex items-center justify-center gap-2 border border-slate-100 group-hover:border-transparent"
                            >
                                <UserPlus className="h-4 w-4" /> Deploy Principal
                            </button>
                        </div>
                    ))}
                </div>
            </section>

            <AddPrincipalModal 
                school={activeSchool} 
                onClose={() => setActiveSchool(null)} 
                onSuccess={() => {
                    alert('Command node successfully established: Principal registered.');
                    loadData();
                }} 
            />
        </div>
    );
};

export default SuperAdminDashboard;
