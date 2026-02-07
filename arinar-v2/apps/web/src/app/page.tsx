import Link from 'next/link';
import AppNav from '@/components/layout/AppNav';
import styles from './home.module.css';

export default function HomePage() {
  return (
    <>
      <AppNav />
      <main className={styles.main}>
        {/* Hero */}
        <section className={styles.hero}>
          <div className={styles.heroContent}>
            <h1 className={styles.heroTitle}>
              Run a debate like a control room.
            </h1>
            <p className={styles.heroSubtitle}>
              Multi-agent meetings, live, with minutes and action items.
            </p>
            <div className={styles.heroCtas}>
              <Link href="/setup" className={styles.ctaPrimary}>
                Start a Meeting
              </Link>
              <Link href="/room" className={styles.ctaSecondary}>
                Open Room
              </Link>
            </div>
          </div>
        </section>

        {/* How it Works */}
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>How It Works</h2>
          <div className={styles.steps}>
            <div className={styles.step}>
              <div className={styles.stepNumber}>1</div>
              <h3>Setup</h3>
              <p>Define your meeting: problem statement, agenda, participants, and AI agents.</p>
            </div>
            <div className={styles.step}>
              <div className={styles.stepNumber}>2</div>
              <h3>Room</h3>
              <p>Watch the live debate unfold. Pause, intervene, resume, or end when ready.</p>
            </div>
            <div className={styles.step}>
              <div className={styles.stepNumber}>3</div>
              <h3>Output</h3>
              <p>Generate AI summary, minutes, and action items. Compare to intended outcome.</p>
            </div>
          </div>
        </section>

        {/* Enterprise Ready */}
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Enterprise-Ready</h2>
          <div className={styles.features}>
            <div className={styles.feature}>
              <span className={styles.featureIcon}>🔑</span>
              <h3>BYOK</h3>
              <p>Bring your own OpenRouter key. Never stored server-side.</p>
            </div>
            <div className={styles.feature}>
              <span className={styles.featureIcon}>📝</span>
              <h3>Audit Log</h3>
              <p>Every event persisted. Full debate history and timeline.</p>
            </div>
            <div className={styles.feature}>
              <span className={styles.featureIcon}>🔐</span>
              <h3>Supabase Auth</h3>
              <p>Production-ready JWT validation with workspace isolation.</p>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className={styles.footer}>
          <div className={styles.footerContent}>
            <span className={styles.version}>Arinar V2 – M3 Build</span>
            <div className={styles.footerLinks}>
              <Link href="/operator">Legacy Operator</Link>
            </div>
          </div>
        </footer>
      </main>
    </>
  );
}
