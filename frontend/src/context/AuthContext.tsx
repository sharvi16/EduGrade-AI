import React, { createContext, useCallback, useContext, useEffect, useState } from "react";

export type Role = "teacher" | "student";

export interface AuthUser {
  name: string;
  email: string;
  role: Role;
}

interface AuthContextValue {
  user: AuthUser | null;
  login: (email: string, password: string, role: Role) => boolean;
  logout: () => void;
}

// Demo credentials
const CREDENTIALS: Record<string, { password: string; name: string; role: Role }> = {
  // Teachers
  "teacher@school.com": { password: "teach123", name: "Prof. Sharma", role: "teacher" },
  "teacher2@school.com": { password: "teach123", name: "Dr. Gupta", role: "teacher" },

  // Students
  "student@school.com": { password: "study123", name: "Rahul Mehta", role: "student" },
  "student2@school.com": { password: "study123", name: "Priya Singh", role: "student" },
  "student3@school.com": { password: "study123", name: "Amit Kumar", role: "student" },

  // You can add Hackathon judges here if you want to use their names!
  "judge@school.com": { password: "judge123", name: "Hackathon Judge", role: "teacher" },
};

const LS_KEY = "edugrade_user";

const AuthContext = createContext<AuthContextValue>({
  user: null,
  login: () => false,
  logout: () => { },
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(() => {
    try {
      const raw = localStorage.getItem(LS_KEY);
      return raw ? (JSON.parse(raw) as AuthUser) : null;
    } catch {
      return null;
    }
  });

  useEffect(() => {
    if (user) localStorage.setItem(LS_KEY, JSON.stringify(user));
    else localStorage.removeItem(LS_KEY);
  }, [user]);

  const login = useCallback((email: string, password: string, role: Role): boolean => {
    const cred = CREDENTIALS[email.toLowerCase().trim()];
    if (!cred || cred.password !== password || cred.role !== role) return false;
    setUser({ name: cred.name, email: email.toLowerCase().trim(), role: cred.role });
    return true;
  }, []);

  const logout = useCallback(() => setUser(null), []);

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => useContext(AuthContext);
