'use client';

import Link from 'next/link';
import AppNav from '@/components/layout/AppNav';
import styles from './home.module.css';

export default function HomePage() {
  return (
    <>
      <AppNav />
      <main className={styles.main}>

        {/* ── Hero ─────────────────────────────────────────────────── */}
        <section className={styles.hero}>
          <div className={styles.heroInner}>
            <div className={styles.badge}>Academic Defense Readiness Platform</div>
            <h1 className={styles.heroHeadline}>
              Prepare for your thesis defense
              <br />
              <span className={styles.gradient}>with AI-powered academic questioning.</span>
            </h1>
            <p className={styles.heroSub}>
              Upload your research, discover weak areas, practice with AI committee members,
              and get a readiness report before your real defense.
            </p>
            <div className={styles.heroCtas}>
              <Link href="/setup" className={styles.btnPrimary}>
                Start Defense Practice
              </Link>
              <a href="#how-it-works" className={styles.btnGhost}>
                See how it works
              </a>
            </div>
            <p className={styles.heroDisclaimer}>
              PeerForge prepares you to defend your own work — it does not write it for you.
            </p>
          </div>
        </section>

        {/* ── Problem ──────────────────────────────────────────────── */}
        <section className={styles.section}>
          <div className={styles.sectionInner}>
            <div className={styles.sectionBadge}>The Problem</div>
            <h2 className={styles.sectionHeadline}>
              Most students walk into their defense without adequate practice.
            </h2>
            <div className={styles.problemGrid}>
              <div className={styles.problemCard}>
                <div className={styles.problemIcon}>⚠️</div>
                <h3>No realistic rehearsal</h3>
                <p>Mocking a committee with friends or advisors rarely captures the pressure and depth of real committee questioning.</p>
              </div>
              <div className={styles.problemCard}>
                <div className={styles.problemIcon}>🔍</div>
                <h3>Unknown weak areas</h3>
                <p>Students can't see their own methodology gaps, unsupported novelty claims, or missing evidence until a committee flags them — live.</p>
              </div>
              <div className={styles.problemCard}>
                <div className={styles.problemIcon}>📋</div>
                <h3>No structured feedback loop</h3>
                <p>Generic advisor notes don't tell you which questions to practice, which answers were weak, or whether you improved between sessions.</p>
              </div>
            </div>
          </div>
        </section>

        {/* ── How It Works ─────────────────────────────────────────── */}
        <section id="how-it-works" className={`${styles.section} ${styles.sectionAlt}`}>
          <div className={styles.sectionInner}>
            <div className={styles.sectionBadge}>How It Works</div>
            <h2 className={styles.sectionHeadline}>
              From uploaded research to defense readiness in one structured loop.
            </h2>
            <div className={styles.stepsGrid}>
              {STEPS.map((s, i) => (
                <div key={i} className={styles.stepCard}>
                  <div className={styles.stepNum}>{i + 1}</div>
                  <div>
                    <h3 className={styles.stepTitle}>{s.title}</h3>
                    <p className={styles.stepDesc}>{s.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Core Features ─────────────────────────────────────────── */}
        <section className={styles.section}>
          <div className={styles.sectionInner}>
            <div className={styles.sectionBadge}>Core Features</div>
            <h2 className={styles.sectionHeadline}>
              Every tool a student needs to walk in ready.
            </h2>
            <div className={styles.featureGrid}>
              {FEATURES.map((f, i) => (
                <div key={i} className={styles.featureCard}>
                  <span className={styles.featureIcon}>{f.icon}</span>
                  <h3>{f.title}</h3>
                  <p>{f.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Mock Defense Preview ──────────────────────────────────── */}
        <section className={`${styles.section} ${styles.sectionAlt}`}>
          <div className={styles.sectionInner}>
            <div className={styles.sectionBadge}>Mock Defense Room</div>
            <h2 className={styles.sectionHeadline}>
              Face AI committee members that question every weak point.
            </h2>
            <p className={styles.sectionSub}>
              Each AI examiner plays a distinct academic role — from a skeptical reviewer
              who challenges unsupported claims, to a methodology professor who drills your research design.
            </p>
            <div className={styles.previewCard}>
              <div className={styles.previewHeader}>
                <span className={styles.previewTitle}>Mock Defense Session</span>
                <span className={styles.previewBadge}>LIVE</span>
              </div>
              <div className={styles.chatLines}>
                {PREVIEW_CHAT.map((line, i) => (
                  <div key={i} className={`${styles.chatLine} ${line.role === 'student' ? styles.chatStudent : styles.chatCommittee}`}>
                    <span className={styles.chatSender}>{line.sender}</span>
                    <span className={styles.chatMsg}>{line.msg}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ── Readiness Report Preview ──────────────────────────────── */}
        <section className={styles.section}>
          <div className={styles.sectionInner}>
            <div className={styles.sectionBadge}>Readiness Report</div>
            <h2 className={styles.sectionHeadline}>
              A scored report that tells you exactly what to practice next.
            </h2>
            <p className={styles.sectionSub}>
              After each mock defense session, PeerForge generates a structured report
              with dimension scores, weak answer analysis, and a prioritised improvement plan.
            </p>
            <div className={styles.reportPreview}>
              <div className={styles.reportHeader}>
                <span className={styles.reportTitle}>Defense Readiness Report</span>
                <span className={styles.reportScore}>Score: 68 / 100</span>
              </div>
              <div className={styles.scoreGrid}>
                {REPORT_SCORES.map((s, i) => (
                  <div key={i} className={styles.scoreRow}>
                    <span className={styles.scoreLabel}>{s.label}</span>
                    <div className={styles.scoreBar}>
                      <div
                        className={styles.scoreBarFill}
                        style={{ width: `${s.score}%`, background: s.score >= 70 ? 'var(--accent)' : s.score >= 50 ? 'var(--warning)' : '#e00' }}
                      />
                    </div>
                    <span className={styles.scoreValue}>{s.score}</span>
                  </div>
                ))}
              </div>
              <div className={styles.reportNext}>
                <span className={styles.reportNextLabel}>Next recommended action:</span>
                <span className={styles.reportNextText}>
                  Your methodology score is weak. Practice 5 methodology questions with the Methodology Professor persona.
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* ── University Value ─────────────────────────────────────── */}
        <section className={`${styles.section} ${styles.sectionAlt}`}>
          <div className={styles.sectionInner}>
            <div className={styles.sectionBadge}>For Universities</div>
            <h2 className={styles.sectionHeadline}>
              A responsible academic preparation tool universities can trust.
            </h2>
            <div className={styles.pillars}>
              {PILLARS.map((p, i) => (
                <div key={i} className={styles.pillar}>
                  <span className={styles.pillarIcon}>{p.icon}</span>
                  <h3>{p.title}</h3>
                  <p>{p.desc}</p>
                </div>
              ))}
            </div>
            <div className={styles.integrityBox}>
              <strong>Academic Integrity First.</strong> PeerForge never writes your thesis, generates your results, or invents citations.
              It only helps you defend your own work — more clearly, more completely, and with confidence.
            </div>
          </div>
        </section>

        {/* ── Pricing / Waitlist ───────────────────────────────────── */}
        <section className={styles.section} id="waitlist">
          <div className={styles.sectionInner}>
            <div className={styles.sectionBadge}>Early Access</div>
            <h2 className={styles.sectionHeadline}>
              Currently in early access for research institutions.
            </h2>
            <p className={styles.sectionSub}>
              PeerForge is being piloted with graduate programs. Institutional and individual plans
              will be announced soon. Start practicing now with your own OpenRouter API key.
            </p>
            <div className={styles.pricingCards}>
              <div className={styles.pricingCard}>
                <h3>Student</h3>
                <div className={styles.pricingPrice}>Free Beta</div>
                <ul className={styles.pricingList}>
                  <li>1 research workspace</li>
                  <li>Research analysis</li>
                  <li>Question bank</li>
                  <li>Mock defense sessions</li>
                  <li>Readiness reports</li>
                  <li>Bring your own OpenRouter key</li>
                </ul>
                <Link href="/setup" className={styles.btnPrimary}>
                  Start Free
                </Link>
              </div>
              <div className={`${styles.pricingCard} ${styles.pricingCardFeatured}`}>
                <div className={styles.pricingFeaturedBadge}>Coming Soon</div>
                <h3>Institution</h3>
                <div className={styles.pricingPrice}>Contact Us</div>
                <ul className={styles.pricingList}>
                  <li>Unlimited student seats</li>
                  <li>Advisor review mode</li>
                  <li>Department rubric integration</li>
                  <li>Cohort-level analytics</li>
                  <li>Audit logs &amp; compliance controls</li>
                  <li>SSO &amp; LMS integration</li>
                </ul>
                <button className={styles.btnOutline} disabled>
                  Join Waitlist
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* ── Final CTA ───────────────────────────────────────────── */}
        <section className={`${styles.section} ${styles.ctaSection}`}>
          <div className={styles.sectionInner}>
            <h2 className={styles.ctaHeadline}>
              Your defense date is approaching. Start practicing now.
            </h2>
            <p className={styles.ctaSub}>
              Upload your thesis or research paper and get your first AI committee session in minutes.
            </p>
            <Link href="/setup" className={styles.btnPrimaryLg}>
              Start Defense Practice
            </Link>
          </div>
        </section>

        {/* ── Footer ──────────────────────────────────────────────── */}
        <footer className={styles.footer}>
          <p>PeerForge — AI Academic Defense &amp; Research Readiness Platform</p>
          <p className={styles.footerSub}>
            A responsible tool for academic preparation. PeerForge does not write thesis content, generate results, or invent citations.
          </p>
        </footer>

      </main>
    </>
  );
}

// ── Static data ───────────────────────────────────────────────────────────

const STEPS = [
  {
    title: 'Create your research workspace',
    desc: 'Enter your thesis title, research domain, project type (thesis, dissertation, proposal), and research stage.',
  },
  {
    title: 'Upload your research materials',
    desc: 'Upload your thesis draft, proposal, slides, advisor notes, rubrics, and related papers. PeerForge extracts, chunks, and indexes everything.',
  },
  {
    title: 'Analyze your research',
    desc: 'The AI identifies your research problem, methodology, contribution, evidence, limitations, and weak areas — all grounded in your uploaded documents.',
  },
  {
    title: 'Generate your defense question bank',
    desc: 'Source-grounded questions are generated across 10 categories: problem statement, methodology, novelty, evidence, limitations, results, and more.',
  },
  {
    title: 'Run a mock defense session',
    desc: 'AI committee members from different roles — Methodology Professor, Skeptical Reviewer, Domain Expert, External Examiner — take turns questioning you.',
  },
  {
    title: 'Receive your readiness report',
    desc: 'Each answer is scored on 6 axes. Your report shows strong areas, weak areas, repeated issues, and a prioritised improvement plan.',
  },
];

const FEATURES = [
  {
    icon: '🔬',
    title: 'Research Analysis Engine',
    desc: 'Extracts your research problem, gap, methodology, contribution, and weak areas from uploaded documents.',
  },
  {
    icon: '❓',
    title: 'Defense Question Bank',
    desc: 'Generates grounded questions across 10 categories with source citations, difficulty levels, and follow-up rules.',
  },
  {
    icon: '🎭',
    title: 'AI Committee Personas',
    desc: '10 distinct roles including Advisor, Methodology Professor, Skeptical Reviewer, External Examiner, and Ethics Reviewer.',
  },
  {
    icon: '📊',
    title: '6-Axis Answer Evaluation',
    desc: 'Every answer is scored on Relevance, Evidence Support, Clarity, Completeness, Methodology Understanding, and Critical Thinking.',
  },
  {
    icon: '🔄',
    title: 'Follow-Up Question Engine',
    desc: 'Weak answers trigger targeted follow-ups: ask for evidence, demand baseline comparison, or require limitation explanation.',
  },
  {
    icon: '📋',
    title: 'Readiness Report',
    desc: 'Aggregated report with overall score, dimension breakdown, weak answer analysis, and a prioritised improvement plan.',
  },
  {
    icon: '📈',
    title: 'Progress Tracking',
    desc: 'Track readiness scores over multiple sessions, identify repeated weak areas, and measure improvement after practice.',
  },
  {
    icon: '🛡️',
    title: 'Grounded Evidence Only',
    desc: 'Every AI question and critique is tied to your uploaded materials. No invented citations, no fabricated results.',
  },
];

const PREVIEW_CHAT = [
  {
    role: 'committee',
    sender: 'Methodology Professor',
    msg: 'Your paper states you used a mixed-methods approach, but Section 3.2 only describes the quantitative instrument. How did the qualitative component contribute to your findings?',
  },
  {
    role: 'student',
    sender: 'You',
    msg: 'The interviews in Chapter 4 were used to triangulate the survey results and explain unexpected patterns in the quantitative data.',
  },
  {
    role: 'committee',
    sender: 'Methodology Professor',
    msg: 'Your answer mentions triangulation, but does not specify how conflicts between the qualitative and quantitative data were resolved. Can you explain your reconciliation process?',
  },
];

const REPORT_SCORES = [
  { label: 'Research Clarity', score: 78 },
  { label: 'Methodology', score: 52 },
  { label: 'Evidence Support', score: 65 },
  { label: 'Critical Thinking', score: 70 },
  { label: 'Communication', score: 74 },
];

const PILLARS = [
  {
    icon: '🏛️',
    title: 'Academically responsible',
    desc: 'PeerForge is a preparation tool, not a writing tool. It supports students in defending their own work, not producing it.',
  },
  {
    icon: '🔒',
    title: 'Private and secure',
    desc: 'Student research materials are kept private. Data access is controlled, and audit logs are maintained for institutional compliance.',
  },
  {
    icon: '📐',
    title: 'Rubric and guideline aware',
    desc: 'Upload your department\'s defense rubric or dissertation evaluation criteria and the AI will align all questioning and feedback to those standards.',
  },
  {
    icon: '📊',
    title: 'Department-level insights',
    desc: 'Aggregate, privacy-safe analytics show common weak areas across your cohort so department programs can improve their preparation approach.',
  },
];
