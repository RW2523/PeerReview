'use client';

import AppNav from '@/components/layout/AppNav';
import CreateDebateCard from '@/components/dashboard/CreateDebateCard';
import styles from './home.module.css';

const DEFAULT_WORKSPACE_ID = '00000000-0000-0000-0000-000000000101';

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
            <div className={styles.badge}>AI Peer Review</div>
            <h1>Submit your research.</h1>
            <h1 className={styles.gradient}>Get rigorous feedback.</h1>
            <p className={styles.subtitle}>
              Upload your paper, proposal, or idea and let an AI panel of domain experts, methodologists, statisticians, and critical reviewers evaluate it with literature-grounded depth.
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
                <h3>Define your research question</h3>
                <p>State your research topic, scope, and what kind of review you need</p>
              </div>
            </div>
            <div className={styles.step}>
              <div className={styles.stepNumber}>2</div>
              <div className={styles.stepContent}>
                <h3>Search the literature</h3>
                <p>Find relevant papers from arXiv, Semantic Scholar, PubMed, and Crossref</p>
              </div>
            </div>
            <div className={styles.step}>
              <div className={styles.stepNumber}>3</div>
              <div className={styles.stepContent}>
                <h3>Get your peer-review report</h3>
                <p>AI reviewers debate your work and produce a structured report with recommendations</p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
