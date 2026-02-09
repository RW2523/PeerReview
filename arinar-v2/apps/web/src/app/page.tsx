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
                <p>Describe the decision, problem, or topic you're working through</p>
              </div>
            </div>
            <div className={styles.step}>
              <div className={styles.stepNumber}>2</div>
              <div className={styles.stepContent}>
                <h3>Assemble your expert panel</h3>
                <p>Select 2-8 AI agents with diverse roles and perspectives</p>
              </div>
            </div>
            <div className={styles.step}>
              <div className={styles.stepNumber}>3</div>
              <div className={styles.stepContent}>
                <h3>Run the deliberation</h3>
                <p>Watch live as they debate, then get summary + action items</p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
