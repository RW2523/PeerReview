'use client';

import AppNav from '@/components/layout/AppNav';
import CreateDebateCard from '@/components/dashboard/CreateDebateCard';
import styles from './home.module.css';

const DEFAULT_WORKSPACE_ID = 'ws_demo_001';

export default function HomePage() {
  const handleDebateCreated = () => {
    // Debate created successfully
  };

  return (
    <>
      <AppNav />
      <main className={styles.main}>
        <div className={styles.container}>
          <header className={styles.header}>
            <div className={styles.badge}>New Session</div>
            <h1>Bring your challenge.</h1>
            <h1 className={styles.gradient}>Get expert perspective.</h1>
            <p className={styles.subtitle}>
              Whether you're facing a strategic decision, exploring research directions, or need diverse viewpoints—assemble your panel of AI experts and let them deliberate.
            </p>
          </header>

          <CreateDebateCard
            workspaceId={DEFAULT_WORKSPACE_ID}
            onDebateCreated={handleDebateCreated}
          />
          
          <div className={styles.howItWorks}>
            <div className={styles.step}>
              <div className={styles.stepNumber}>1</div>
              <div className={styles.stepContent}>
                <h3>Frame your challenge</h3>
                <p>Share the problem, decision, or topic you need help with</p>
              </div>
            </div>
            <div className={styles.step}>
              <div className={styles.stepNumber}>2</div>
              <div className={styles.stepContent}>
                <h3>Assemble your panel</h3>
                <p>Choose AI experts with diverse perspectives and expertise</p>
              </div>
            </div>
            <div className={styles.step}>
              <div className={styles.stepNumber}>3</div>
              <div className={styles.stepContent}>
                <h3>Watch them deliberate</h3>
                <p>Follow the live discussion and get actionable insights</p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
