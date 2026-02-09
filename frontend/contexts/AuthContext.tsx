import React, { createContext, useContext, ReactNode, useState, useEffect } from 'react';
import { useRouter } from 'next/router';

interface User {
  id: string;
  email: string;
  name?: string;
  image?: string;
}

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [session, setSession] = useState<any>(null);
  const [status, setStatus] = useState<'loading' | 'authenticated' | 'unauthenticated'>('loading');
  const [authFunctions, setAuthFunctions] = useState<{
    signIn: any;
    signOut: any;
  } | null>(null);
  
  const router = useRouter();

  // Initialize next-auth functions when component mounts in browser
  useEffect(() => {
    if (typeof window !== 'undefined') {
      try {
        const { signIn, signOut, useSession } = require('next-auth/react');
        setAuthFunctions({ signIn, signOut });
        
        // Get initial session
        const [initialSession, initialStatus] = useSession();
        setSession(initialSession);
        setStatus(initialStatus as 'loading' | 'authenticated' | 'unauthenticated');
      } catch (error) {
        console.warn('next-auth not available:', error);
        setStatus('unauthenticated');
      }
    } else {
      // For SSR, start with loading state
      setStatus('loading');
    }
  }, []);

  const login = async (email: string, password: string) => {
    if (!authFunctions) {
      throw new Error('Authentication functions not initialized');
    }
    
    const result = await authFunctions.signIn('credentials', {
      email,
      password,
      redirect: false,
    });

    if (result?.error) {
      throw new Error(result.error);
    }

    if (result?.ok) {
      router.push('/dashboard'); // ✅ Login redirects to dashboard
    }
  };

  const signup = async (email: string, password: string) => {
    if (!authFunctions) {
      throw new Error('Authentication functions not initialized');
    }
    
    try {
      // Create the user account via backend API
      const BACKEND_API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
      const response = await fetch(`${BACKEND_API_URL}/api/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Signup failed');
      }

      // After successful signup, log them in
      const result = await authFunctions.signIn('credentials', {
        email,
        password,
        redirect: false,
      });

      if (result?.error) {
        throw new Error('Account created but login failed. Please try logging in.');
      }

      if (result?.ok) {
        router.push('/dashboard'); // ✅ Signup also redirects to dashboard
      }
    } catch (error) {
      console.error('Signup error:', error);
      throw error;
    }
  };

  const loginWithGoogle = async () => {
    if (!authFunctions) {
      throw new Error('Authentication functions not initialized');
    }
    
    await authFunctions.signIn('google', { callbackUrl: '/dashboard' }); // ✅ Google login also goes to dashboard
  };

  const logout = async () => {
    if (!authFunctions) {
      throw new Error('Authentication functions not initialized');
    }
    
    await authFunctions.signOut({ callbackUrl: '/login' });
  };

  const value = {
    user: session?.user ? {
      id: session.user.id as string,
      email: session.user.email!,
      name: session.user.name || undefined,
      image: session.user.image || undefined,
    } : null,
    login,
    signup,
    loginWithGoogle,
    logout,
    isAuthenticated: !!session?.user,
    isLoading: status === 'loading',
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};