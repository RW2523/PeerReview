'use client';

import AppNav from '@/components/layout/AppNav';
import DebateHistory from '@/components/dashboard/DebateHistory';
import styles from './history.module.css';

const DEFAULT_WORKSPACE_ID = '00000000-0000-0000-0000-000000000001';

export default function HistoryPage() {
  return (
    <>
      <AppNav />
      <main className={styles.main}>
        <div className={styles.container}>
          <header className={styles.header}>
            <h1>Debate History</h1>
            <p className={styles.subtitle}>View and continue your past debates</p>
          </header>

          <DebateHistory
            workspaceId={DEFAULT_WORKSPACE_ID}
            refreshTrigger={0}
          />
        </div>
      </main>
    </>
  );
}
