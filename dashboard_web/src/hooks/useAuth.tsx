import { createContext, useContext, useState, useEffect, type ReactNode } from "react";

const ACCESS_KEY_STORAGE = "app_access_key";

type AuthContextType = {
  isAuthenticated: boolean;
  accessKey: string | null;
  login: (key: string) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [accessKey, setAccessKey] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    // Load access key from localStorage on mount
    const stored = localStorage.getItem(ACCESS_KEY_STORAGE);
    if (stored) {
      setAccessKey(stored);
      setIsAuthenticated(true);
    }
  }, []);

  const login = (key: string) => {
    localStorage.setItem(ACCESS_KEY_STORAGE, key);
    setAccessKey(key);
    setIsAuthenticated(true);
  };

  const logout = () => {
    localStorage.removeItem(ACCESS_KEY_STORAGE);
    setAccessKey(null);
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, accessKey, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
