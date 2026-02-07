import { useState, useEffect } from 'react';
import { keyStore, KeyPersistence } from '@/lib/openrouterKeyStore';

export function useOpenRouterKey() {
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [persistence, setPersistence] = useState<KeyPersistence | null>(null);

  useEffect(() => {
    // Load key on mount
    const key = keyStore.getKey();
    const persist = keyStore.getPersistence();
    setApiKey(key);
    setPersistence(persist);
  }, []);

  const saveKey = (key: string, persist: KeyPersistence = 'memory') => {
    keyStore.setKey(key, persist);
    setApiKey(key);
    setPersistence(persist);
  };

  const clearKey = () => {
    keyStore.clearKey();
    setApiKey(null);
    setPersistence(null);
  };

  const hasKey = keyStore.hasKey();

  return {
    apiKey,
    persistence,
    hasKey,
    saveKey,
    clearKey,
  };
}
