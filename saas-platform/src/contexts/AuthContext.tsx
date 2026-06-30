import React, { createContext, useContext, useState, useCallback } from 'react';
import type { User } from '@/types';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string, company: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const stored = localStorage.getItem('quantmatrix_user');
    return stored ? JSON.parse(stored) : null;
  });

  const login = useCallback(async (email: string, _password: string) => {
    const mockUser: User = {
      id: '1', email, name: email.split('@')[0],
      company: '演示公司', plan: 'pro', avatar: undefined,
    };
    setUser(mockUser);
    localStorage.setItem('quantmatrix_user', JSON.stringify(mockUser));
  }, []);

  const register = useCallback(async (name: string, email: string, _password: string, company: string) => {
    const mockUser: User = {
      id: '1', email, name, company, plan: 'free',
    };
    setUser(mockUser);
    localStorage.setItem('quantmatrix_user', JSON.stringify(mockUser));
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    localStorage.removeItem('quantmatrix_user');
  }, []);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
