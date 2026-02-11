'use client';

import * as api from '@/lib/api';
import styles from './AccountInfoCard.module.css';

interface AccountInfoCardProps {
  apiKey: string | null;
  accountInfo: api.OpenRouterAccountResponse | null;
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
  onRefresh: () => void;
}

export function AccountInfoCard({
  apiKey,
  accountInfo,
  loading,
  error,
  lastUpdated,
  onRefresh
}: AccountInfoCardProps) {
  if (!apiKey) return null;

  return (
    <section className={styles.card}>
      <div className={styles.cardHeader}>
        <h2>Account Info</h2>
        <button
          onClick={onRefresh}
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
          {/* Show key validation status */}
          <div className={styles.metric}>
            <h3>API Key Status</h3>
            <div className={styles.metricValue} style={{ color: 'var(--success)' }}>
              ✓ Valid
            </div>
            <div className={styles.metricDetails}>
              {accountInfo.models_available && (
                <span>{accountInfo.models_available} models available</span>
              )}
              {accountInfo.key?.label && (
                <span>Label: {accountInfo.key.label}</span>
              )}
            </div>
          </div>

          {/* Show credits if available (management keys only) */}
          {accountInfo.credits && accountInfo.credits.balance !== null ? (
            <div className={styles.metric}>
              <h3>Credits Balance</h3>
              <div className={styles.metricValue} style={{ color: 'var(--success)', fontSize: '2rem' }}>
                ${accountInfo.credits.balance.toFixed(2)}
              </div>
              <div className={styles.metricDetails}>
                {accountInfo.credits.total_credits !== null && (
                  <span>Total Purchased: ${accountInfo.credits.total_credits.toFixed(2)}</span>
                )}
                {accountInfo.credits.total_usage !== null && (
                  <span>Total Used: ${accountInfo.credits.total_usage.toFixed(2)}</span>
                )}
              </div>
            </div>
          ) : accountInfo.key?.usage !== undefined ? (
            <div className={styles.metric}>
              <h3>Usage & Limits</h3>
              <div className={styles.metricValue}>
                ${accountInfo.key.usage.toFixed(2)}
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

          {/* Show note about credits availability */}
          {accountInfo.note && (
            <div className={styles.note}>
              <span>ℹ️</span>
              <span>{accountInfo.note}</span>
            </div>
          )}
          
          {/* Show if management key is working */}
          {accountInfo.has_management_key && accountInfo.credits?.balance !== null && (
            <div className={styles.note} style={{ backgroundColor: '#e8f5e9', borderColor: '#4caf50' }}>
              <span>✅</span>
              <span>Management key verified - showing live credit balance</span>
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
  );
}
