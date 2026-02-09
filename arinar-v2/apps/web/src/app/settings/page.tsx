'use client';

import { useState, useEffect } from 'react';
import AppNav from '@/components/layout/AppNav';
import { useOpenRouterKey } from '@/hooks/useOpenRouterKey';
import { KeyPersistence } from '@/lib/openrouterKeyStore';
import * as api from '@/lib/api';
import styles from './settings.module.css';

export default function SettingsPage() {
  const { apiKey, persistence, saveKey, clearKey } = useOpenRouterKey();
  const [keyInput, setKeyInput] = useState('');
  const [selectedPersistence, setSelectedPersistence] = useState<KeyPersistence>('memory');
  const [accountInfo, setAccountInfo] = useState<api.OpenRouterAccountResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    if (apiKey) {
      setKeyInput('');
      fetchAccountInfo();
    } else {
      setAccountInfo(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiKey]);

  useEffect(() => {
    if (persistence) {
      setSelectedPersistence(persistence);
    }
  }, [persistence]);

  const fetchAccountInfo = async () => {
    if (!apiKey) return;

    setLoading(true);
    setError(null);

    try {
      const data = await api.getOpenRouterAccount(apiKey);
      setAccountInfo(data);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch account info');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveKey = () => {
    if (!keyInput.trim()) return;
    saveKey(keyInput, selectedPersistence);
    setKeyInput('');
  };

  const handleClearKey = () => {
    clearKey();
    setAccountInfo(null);
    setLastUpdated(null);
  };

  return (
    <>
      <AppNav />
      <div className={styles.container}>
        <div className={styles.content}>
          <h1>Settings</h1>
          <p className={styles.subtitle}>Enter your OpenRouter API key to enable AI features</p>

          {/* API Key Card */}
          <section className={styles.card}>
            <h2>OpenRouter API Key</h2>
            <p className={styles.cardDesc}>
              Enter your OpenRouter key to use AI features. Your key is never stored on our servers.
            </p>

            {apiKey ? (
              <div className={styles.keyStatus}>
                <div className={styles.keyStatusHeader}>
                  <span className={styles.keyIcon}>🔑</span>
                  <div>
                    <strong>Key Saved</strong>
                    <p>
                      Stored: <span className={styles.persistenceBadge}>{persistence}</span>
                    </p>
                  </div>
                </div>
                <button onClick={handleClearKey} className={styles.btnDanger}>
                  Clear Key
                </button>
              </div>
            ) : (
              <>
                <div className={styles.form}>
                  <label>
                    API Key
                    <input
                      type="password"
                      value={keyInput}
                      onChange={(e) => setKeyInput(e.target.value)}
                      placeholder="sk-or-..."
                    />
                  </label>

                  <div className={styles.persistenceOptions}>
                    <label className={styles.radio}>
                      <input
                        type="radio"
                        name="persistence"
                        value="memory"
                        checked={selectedPersistence === 'memory'}
                        onChange={(e) => setSelectedPersistence(e.target.value as KeyPersistence)}
                      />
                      <div>
                        <strong>Do not save (memory only)</strong>
                        <p>Key lost when page reloads</p>
                      </div>
                    </label>

                    <label className={styles.radio}>
                      <input
                        type="radio"
                        name="persistence"
                        value="session"
                        checked={selectedPersistence === 'session'}
                        onChange={(e) => setSelectedPersistence(e.target.value as KeyPersistence)}
                      />
                      <div>
                        <strong>Save for this session</strong>
                        <p>Cleared when browser closes</p>
                      </div>
                    </label>

                    <label className={styles.radio}>
                      <input
                        type="radio"
                        name="persistence"
                        value="local"
                        checked={selectedPersistence === 'local'}
                        onChange={(e) => setSelectedPersistence(e.target.value as KeyPersistence)}
                      />
                      <div>
                        <strong>Save on this device</strong>
                        <p className={styles.warning}>⚠ Key stored in browser localStorage</p>
                      </div>
                    </label>
                  </div>

                  <button
                    onClick={handleSaveKey}
                    disabled={!keyInput.trim()}
                    className={styles.btnPrimary}
                  >
                    Save Key
                  </button>
                </div>

                <div className={styles.securityNote}>
                  <span>🔒</span>
                  <div>
                    <strong>Security Promise</strong>
                    <p>Your API key is never sent to our database. It stays in your browser only.</p>
                  </div>
                </div>
              </>
            )}
          </section>

          {/* Account Info Card */}
          {apiKey && (
            <section className={styles.card}>
              <div className={styles.cardHeader}>
                <h2>Account Info</h2>
                <button
                  onClick={fetchAccountInfo}
                  disabled={loading}
                  className={styles.btnSecondary}
                >
                  {loading ? 'Refreshing...' : 'Refresh'}
                </button>
              </div>

              {error && (
                <div className={styles.error}>
                  <span>⚠</span>
                  <span>{error}</span>
                </div>
              )}

              {loading && !accountInfo ? (
                <div className={styles.loading}>Loading account info...</div>
              ) : accountInfo ? (
                <>
                  {accountInfo.credits ? (
                    <div className={styles.metric}>
                      <h3>Credits Balance</h3>
                      <div className={styles.metricValue}>
                        ${accountInfo.credits.balance?.toFixed(2) || '0.00'}
                      </div>
                      <div className={styles.metricDetails}>
                        <span>Total: ${accountInfo.credits.total_credits?.toFixed(2)}</span>
                        <span>Used: ${accountInfo.credits.total_usage?.toFixed(2)}</span>
                      </div>
                    </div>
                  ) : accountInfo.key ? (
                    <div className={styles.metric}>
                      <h3>Usage & Limits</h3>
                      <div className={styles.metricValue}>
                        ${accountInfo.key.usage?.toFixed(2) || '0.00'}
                        {accountInfo.key.limit ? ` / $${accountInfo.key.limit.toFixed(2)}` : ' (Unlimited)'}
                      </div>
                      {accountInfo.key.rate_limit && (
                        <div className={styles.metricDetails}>
                          <span>
                            Rate: {accountInfo.key.rate_limit.requests} req / {accountInfo.key.rate_limit.interval}
                          </span>
                        </div>
                      )}
                    </div>
                  ) : null}

                  {accountInfo.note && (
                    <div className={styles.note}>
                      <span>ℹ️</span>
                      <span>{accountInfo.note}</span>
                    </div>
                  )}

                  {lastUpdated && (
                    <div className={styles.timestamp}>
                      Last updated: {lastUpdated.toLocaleTimeString()}
                    </div>
                  )}
                </>
              ) : null}
            </section>
          )}
        </div>
      </div>
    </>
  );
}
