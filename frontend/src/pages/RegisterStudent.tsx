import React, { useState } from "react";
import { createUser } from "../api/client";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CheckCircle, XCircle, UserPlus, Users } from "lucide-react";
import { cn } from "@/lib/utils";

const RegisterStudent: React.FC = () => {
  const [studentName, setStudentName] = useState("");
  const [studentEmail, setStudentEmail] = useState("");
  const [studentPass, setStudentPass] = useState("");
  const [studentMsg, setStudentMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [addingStudent, setAddingStudent] = useState(false);

  const handleCreateStudent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!studentName || !studentEmail || !studentPass) return;
    setAddingStudent(true);
    setStudentMsg(null);
    try {
      await createUser({
        name: studentName,
        email: studentEmail,
        password: studentPass,
        role: "student"
      });
      setStudentMsg({ type: "success", text: `Student ${studentName} registered successfully!` });
      setStudentName(""); setStudentEmail(""); setStudentPass("");
    } catch (err: any) {
      setStudentMsg({ type: "error", text: err.response?.data?.detail || "Failed to add student" });
    } finally {
      setAddingStudent(false);
    }
  };

  return (
    <div className="space-y-10 animate-fade-up font-sans">
      <div className="page-header">
        <div className="flex items-center gap-3 mb-2">
          <div className="h-10 w-10 rounded-xl flex items-center justify-center shrink-0"
            style={{ background: "linear-gradient(135deg, #ede9fe 0%, #e0f2fe 100%)", border: "1px solid rgba(124,58,237,0.15)" }}>
            <Users className="h-5 w-5" style={{ color: "#7c3aed" }} />
          </div>
          <h1 className="text-gradient" style={{ fontSize: "1.7rem", fontWeight: 700, letterSpacing: "-0.02em" }}>Student Management</h1>
        </div>
        <p className="text-muted-foreground">Register new students and manage their access to exams</p>
      </div>

      <div className="bg-white rounded-[2rem] border border-slate-100 shadow-[0_8px_30px_rgb(0,0,0,0.04)] p-8 max-w-2xl">
        <div className="flex items-center gap-3 mb-8">
          <div className="h-9 w-9 rounded-xl flex items-center justify-center"
            style={{ background: "#f5f3ff" }}>
            <UserPlus className="h-5 w-5" style={{ color: "#7c3aed" }} />
          </div>
          <h2 className="font-bold text-lg text-slate-800">Add New Student</h2>
        </div>

        <form onSubmit={handleCreateStudent} className="space-y-6" noValidate>
          {/* Dummy inputs to fool browser autofill */}
          <input type="text" name="email" style={{ display: 'none' }} tabIndex={-1} />
          <input type="password" name="password" style={{ display: 'none' }} tabIndex={-1} />

          <div className="space-y-2">
            <Label className="text-sm font-bold text-slate-700 ml-1">Student Full Name</Label>
            <Input 
              id="student_reg_name"
              name="student_reg_name"
              value={studentName} 
              onChange={e => setStudentName(e.target.value)} 
              placeholder="e.g. Rahul Sharma" 
              required 
              autoComplete="new-password"
              readOnly
              onFocus={(e) => e.target.removeAttribute('readonly')}
              className="bg-slate-50/50 border-slate-200 rounded-2xl h-14 px-4 focus:ring-2 focus:ring-purple-500/20 focus:border-purple-400 transition-all placeholder:text-slate-400"
            />
          </div>
          <div className="space-y-2">
            <Label className="text-sm font-bold text-slate-700 ml-1">Email Address</Label>
            <Input 
              id="student_reg_email"
              name="student_reg_email"
              type="email" 
              value={studentEmail} 
              onChange={e => setStudentEmail(e.target.value)} 
              placeholder="rahul@school.com" 
              required 
              autoComplete="new-password"
              readOnly
              onFocus={(e) => e.target.removeAttribute('readonly')}
              className="bg-slate-50/50 border-slate-200 rounded-2xl h-14 px-4 focus:ring-2 focus:ring-purple-500/20 focus:border-purple-400 transition-all placeholder:text-slate-400"
            />
          </div>
          <div className="space-y-2">
            <Label className="text-sm font-bold text-slate-700 ml-1">Temporary Password</Label>
            <Input 
              id="student_reg_pass"
              name="student_reg_pass"
              type="password" 
              value={studentPass} 
              onChange={e => setStudentPass(e.target.value)} 
              placeholder="••••••••" 
              required 
              autoComplete="new-password"
              readOnly
              onFocus={(e) => e.target.removeAttribute('readonly')}
              className="bg-slate-50/50 border-slate-200 rounded-2xl h-14 px-4 focus:ring-2 focus:ring-purple-500/20 focus:border-purple-400 transition-all placeholder:text-slate-400"
            />
          </div>

          {studentMsg && (
            <div className={cn("p-4 rounded-2xl text-sm flex gap-3 animate-fade-in", 
              studentMsg.type === "success" ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200")}>
              {studentMsg.type === "success" ? <CheckCircle className="h-5 w-5 shrink-0" /> : <XCircle className="h-5 w-5 shrink-0" />}
              <span className="font-semibold">{studentMsg.text}</span>
            </div>
          )}

          <button 
            type="submit" 
            disabled={addingStudent} 
            className="w-full h-14 rounded-2xl text-white font-bold text-lg shadow-lg shadow-purple-200 hover:shadow-purple-300 hover:-translate-y-0.5 transition-all flex items-center justify-center gap-2"
            style={{ background: "linear-gradient(90deg, #7c3aed 0%, #0ea5e9 100%)" }}
          >
            {addingStudent ? (
              <span className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : "Register Student"}
          </button>
        </form>
      </div>
    </div>
  );
};

export default RegisterStudent;
