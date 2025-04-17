"use client";

import React, { createContext, useContext, useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { authApi } from './api/api-service';
import { User } from './api/types';

type AuthContextType = {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // Check if user is already logged in
    const loadUser = async () => {
      setIsLoading(true);
      try {
        if (authApi.isAuthenticated()) {
          const userData = localStorage.getItem('user');
          if (userData) {
            setUser(JSON.parse(userData));
          }
        }
      } catch (error) {
        console.error('Error loading user:', error);
        // Clear any invalid auth data
        authApi.logout();
      } finally {
        setIsLoading(false);
      }
    };
    
    loadUser();
  }, []);

  // Redirect logic
  useEffect(() => {
    if (!isLoading) {
      const isAuthRoute = pathname === '/login' || pathname === '/register';
      
      if (!authApi.isAuthenticated() && pathname.startsWith('/dashboard')) {
        router.push('/login');
      } else if (authApi.isAuthenticated() && isAuthRoute) {
        router.push('/dashboard');
      }
    }
  }, [isLoading, pathname, router]);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await authApi.login({ email, password });
      if (response.user) {
        setUser(response.user);
        router.push('/dashboard');
      }
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  // Register function
  const register = async (username: string, email: string, password: string) => {
    setIsLoading(true);
    try {
      await authApi.register({ username, email, password });
      // After registration, the user will be redirected to login
    } catch (error) {
      console.error('Registration error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    authApi.logout();
    setUser(null);
    router.push('/login');
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}; 