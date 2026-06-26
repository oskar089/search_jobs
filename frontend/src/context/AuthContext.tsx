import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { getMe, loginUser, registerUser, logoutUser } from "../lib/auth";
import type { UserResponse } from "../types";

interface AuthContextType {
  user: UserResponse | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // On mount, try to get the current user via cookie-based auth.
    // Cookies are auto-sent by the browser; no localStorage token needed.
    getMe()
      .then(setUser)
      .catch(() => {
        /* 401 — not authenticated, that's OK */
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = async (email: string, password: string) => {
    await loginUser({ email, password });
    // Cookies are auto-set by the backend login endpoint
    const userData = await getMe();
    setUser(userData);
  };

  const register = async (name: string, email: string, password: string) => {
    await registerUser({ email, password, name });
    // Cookies are auto-set by the backend register endpoint
    const userData = await getMe();
    setUser(userData);
  };

  const logout = useCallback(async () => {
    try {
      await logoutUser();
    } catch {
      // Even if the API call fails, clear local state
    }
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
