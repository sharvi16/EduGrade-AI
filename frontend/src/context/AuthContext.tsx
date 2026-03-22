import React, { createContext, useCallback, useContext, useEffect, useState } from "react";

export type Role = "super_admin" | "principal" | "teacher" | "student";

export interface AuthUser {
  name: string;
  email: string;
  role: Role;
  token: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => void;
}

const LS_KEY = "edugrade_user";

const AuthContext = createContext<AuthContextValue>({
  user: null,
  login: async () => false,
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

  const login = useCallback(async (email: string, password: string): Promise<boolean> => {
    try {
      const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
      console.log(`Attempting login at: ${baseUrl}/auth/login`);
      
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 15000); // 15s timeout
      
      const response = await fetch(`${baseUrl}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        console.error(`Login failed with status: ${response.status}`);
        return false;
      }
      
      const data = await response.json();
      console.log("Login successful, updating user state.");
      
      setUser({
        name: data.user.name,
        email: data.user.email,
        role: data.user.role as Role,
        token: data.access_token,
      });
      return true;
    } catch (err: any) {
      console.error("Login request error:", err.name === 'AbortError' ? 'Request timed out' : err);
      return false;
    }
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
