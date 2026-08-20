import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { AuthUser } from "./types";
import {
  getCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
} from "../services/authService";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  authenticated: boolean;
  isOwner: boolean;
  isAdmin: boolean;
  hasPermission: (permission: string) => boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void (async () => {
      try {
        setUser(await getCurrentUser());
      } catch {
        setUser(null);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    setUser(await loginRequest(username, password));
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutRequest();
    } finally {
      setUser(null);
    }
  }, []);

  const hasPermission = useCallback(
    (permission: string) => {
      if (!user) return false;
      if (user.role === "OWNER") return true;
      return user.permissions.includes(permission);
    },
    [user],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      authenticated: user !== null,
      isOwner: user?.role === "OWNER",
      isAdmin: hasPermission("user.view") || hasPermission("role.view"),
      hasPermission,
      login,
      logout,
    }),
    [user, loading, hasPermission, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return context;
}
