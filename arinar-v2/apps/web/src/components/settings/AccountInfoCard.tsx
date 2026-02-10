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
  );
}
