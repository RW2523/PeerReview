/**
 * Supabase client for authentication
 */
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

if (!supabaseUrl || !supabaseAnonKey) {
  console.warn('Supabase credentials not configured. Auth will not work.');
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

/**
 * Get current session access token
 * Returns null if no active session
 * 
 * In development mode (NEXT_PUBLIC_AUTH_MODE=development), uses test token from env
 */
export async function getAccessToken(): Promise<string | null> {
  // Development mode: use test token for local testing without Supabase
  const authMode = process.env.NEXT_PUBLIC_AUTH_MODE;
  if (authMode === 'development') {
    const testToken = process.env.NEXT_PUBLIC_TEST_TOKEN;
    if (testToken) {
      return testToken;
    }
  }
  
  // Production mode: use Supabase session
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token || null;
}

/**
 * Sign in with email and password
 */
export async function signInWithPassword(email: string, password: string) {
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });
  
  if (error) throw error;
  return data;
}

/**
 * Sign in with magic link
 */
export async function signInWithMagicLink(email: string) {
  const { data, error } = await supabase.auth.signInWithOtp({
    email,
    options: {
      emailRedirectTo: `${window.location.origin}/operator`,
    },
  });
  
  if (error) throw error;
  return data;
}

/**
 * Sign out
 */
export async function signOut() {
  const { error } = await supabase.auth.signOut();
  if (error) throw error;
}

/**
 * Get current user
 */
export async function getCurrentUser() {
  const { data: { user } } = await supabase.auth.getUser();
  return user;
}
