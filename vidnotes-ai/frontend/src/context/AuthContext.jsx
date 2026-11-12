import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import {
  configureAuth,
  getPreferences,
  getProfile,
  getPublicConfig,
  updatePreferences as savePreferences,
} from '../services/api.js';

const AuthContext = createContext(null);

// theme is null until loaded, so the device's own theme is kept until then.
const DEFAULT_PREFERENCES = { theme: null, default_language: 'en', default_quiz_count: 10 };
const NEXT_PATH_KEY = 'vidnotes-after-sign-in';

const FRIENDLY_ERRORS = [
  [/invalid login credentials/i, 'Wrong email or password.'],
  [/email not confirmed/i, 'Please confirm your email first. Check your inbox for the link.'],
  [/already registered|already been registered/i, 'An account with this email already exists. Try logging in.'],
  [/rate limit|too many/i, 'Too many attempts. Please wait a minute and try again.'],
  [/provider is not enabled/i, 'Google sign-in is not set up yet. Use email and password for now.'],
  [/code verifier|auth code/i, 'This link must be opened in the same browser you requested it from.'],
  [/fetch|network/i, 'Cannot reach the sign-in service. Check your internet connection.'],
];

function friendly(error) {
  const message = error?.message ?? String(error);
  const match = FRIENDLY_ERRORS.find(([pattern]) => pattern.test(message));
  return new Error(match ? match[1] : message);
}

// Remembers where to return after an OAuth or email redirect.
export function rememberNextPath(path) {
  try {
    sessionStorage.setItem(NEXT_PATH_KEY, path);
  } catch {
    // Without storage the user simply lands on My Notes.
  }
}

export function takeNextPath(fallback = '/notes') {
  try {
    const path = sessionStorage.getItem(NEXT_PATH_KEY);
    sessionStorage.removeItem(NEXT_PATH_KEY);
    return path?.startsWith('/') ? path : fallback;
  } catch {
    return fallback;
  }
}

export function AuthProvider({ children }) {
  // status: loading | signedIn | signedOut | error.  mode: local | cloud
  const [auth, setAuth] = useState({ status: 'loading', mode: null, session: null, cloudSync: false, error: '' });
  const [profile, setProfile] = useState(null);
  const [preferences, setPreferences] = useState(DEFAULT_PREFERENCES);
  const preferencesRef = useRef(preferences);
  preferencesRef.current = preferences;
  const clientRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    let unsubscribe = () => {};

    async function start() {
      try {
        const config = await getPublicConfig();
        if (cancelled) return;
        if (!config.auth_enabled) {
          setAuth({ status: 'signedIn', mode: 'local', session: null, cloudSync: false, error: '' });
          return;
        }

        // Loaded only when accounts are on, so local mode stays lightweight.
        const { createClient } = await import('@supabase/supabase-js');
        if (cancelled) return;
        const client = createClient(config.supabase_url, config.supabase_publishable_key, {
          auth: { flowType: 'pkce', persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
        });
        clientRef.current = client;
        configureAuth({
          // getSession refreshes an expired token before returning it.
          tokenProvider: async () => (await client.auth.getSession()).data.session?.access_token ?? null,
          unauthorizedHandler: () => client.auth.signOut({ scope: 'local' }),
        });

        const { data } = await client.auth.getSession();
        console.log('SUPABASE SESSION:', data.session);
        if (cancelled) return;
        setAuth({
          status: data.session ? 'signedIn' : 'signedOut',
          mode: 'cloud',
          session: data.session,
          cloudSync: config.cloud_sync,
          error: '',
        });
        const { data: listener } = client.auth.onAuthStateChange((_event, session) => {
          setAuth((current) => ({ ...current, status: session ? 'signedIn' : 'signedOut', session }));
        });
        unsubscribe = () => listener.subscription.unsubscribe();
      } catch (error) {
        if (!cancelled) setAuth((current) => ({ ...current, status: 'error', error: error.message }));
      }
    }

    start();
    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, []);

  const userId = auth.mode === 'local' ? 'local' : auth.session?.user?.id;

  // Profile and preferences come from the backend, so they follow the user
  // to every device.
  useEffect(() => {
    if (auth.status !== 'signedIn') {
      setProfile(null);
      setPreferences(DEFAULT_PREFERENCES);
      return undefined;
    }
    let cancelled = false;
    Promise.all([getProfile(), getPreferences()])
      .then(([loadedProfile, loadedPreferences]) => {
        if (cancelled) return;
        setProfile(loadedProfile);
        setPreferences(loadedPreferences);
      })
      .catch(() => {
        // The pages show their own errors; defaults keep the app usable.
      });
    return () => {
      cancelled = true;
    };
  }, [auth.status, userId]);

  const client = () => {
    if (!clientRef.current) throw new Error('Accounts are not configured on this server.');
    return clientRef.current;
  };

  const signInWithGoogle = useCallback(async (nextPath) => {
    rememberNextPath(nextPath);
    const { error } = await client().auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
    if (error) throw friendly(error);
  }, []);

  const signInWithPassword = useCallback(async (email, password) => {
    const { error } = await client().auth.signInWithPassword({ email, password });
    if (error) throw friendly(error);
  }, []);

  const signUp = useCallback(async (fullName, email, password) => {
    const { data, error } = await client().auth.signUp({
      email,
      password,
      options: { data: { full_name: fullName }, emailRedirectTo: `${window.location.origin}/auth/callback` },
    });
    if (error) throw friendly(error);
    return { needsConfirmation: !data.session };
  }, []);

  const sendPasswordReset = useCallback(async (email) => {
    const { error } = await client().auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    });
    if (error) throw friendly(error);
  }, []);

  const updatePassword = useCallback(async (password) => {
    const { error } = await client().auth.updateUser({ password });
    if (error) throw friendly(error);
  }, []);

  const signOut = useCallback(async () => {
    if (clientRef.current) await clientRef.current.auth.signOut();
  }, []);

  // Optimistic: the change shows at once and is rolled back if saving fails.
  const updatePreferences = useCallback(async (changes) => {
    const previous = preferencesRef.current;
    setPreferences({ ...previous, ...changes });
    try {
      setPreferences(await savePreferences(changes));
    } catch (error) {
      setPreferences(previous);
      throw error;
    }
  }, []);

  const value = useMemo(
    () => ({
      ...auth,
      user: auth.session?.user ?? null,
      profile,
      setProfile,
      preferences,
      updatePreferences,
      signInWithGoogle,
      signInWithPassword,
      signUp,
      sendPasswordReset,
      updatePassword,
      signOut,
    }),
    [auth, profile, preferences, updatePreferences, signInWithGoogle, signInWithPassword, signUp,
      sendPasswordReset, updatePassword, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>.');
  return context;
}
