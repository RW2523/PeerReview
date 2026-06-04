'use client';

import React, { useState, useEffect, useCallback } from 'react';
import styles from './MockDefenseRoom.module.css';
import {
  analyzeResearch,
  generateDefenseQuestions,
  suggestPersonas,
  submitAnswer,
  generateReadinessReport,
  getResearchProfile,
  getDefenseQuestions,
  getReadinessReport,
  type ResearchProfile,
  type DefenseQuestion,
  type AnswerEvaluation,
  type ReadinessReport,
  type ReasoningMode,
  type SuggestedPersona,
} from '@/lib/api';

// ── Types ──────────────────────────────────────────────────────────────────

type Phase =
  | 'setup'        // choose mode, see persona previews
  | 'analyzing'    // analyzing research materials
  | 'suggesting'   // fetching AI persona suggestions
  | 'questions'    // reviewing/selecting questions
  | 'defense'      // active Q&A loop
  | 'evaluated'    // last answer was evaluated
  | 'report'       // readiness report rendered
  | 'error';

interface ModeOption {
  id: ReasoningMode;
  label: string;
  emoji: string;
  description: string;
  costHint: string;
  badgeColor: string;
}

const MODE_OPTIONS: ModeOption[] = [
  {
    id: 'light',
    label: 'Light',
    emoji: '⚡',
    description: 'Single fast model for all tasks. Great for practice and iteration.',
    costHint: '~$0.01–0.05 / session',
    badgeColor: '#16a34a',
  },
  {
    id: 'medium',
    label: 'Medium',
    emoji: '⚖️',
    description: 'Different smarter models per role. Balanced quality vs. cost.',
    costHint: '~$0.10–0.40 / session',
    badgeColor: '#d97706',
  },
  {
    id: 'heavy',
    label: 'Heavy',
    emoji: '🔥',
    description: 'Frontier models for every activity. Production-grade depth.',
    costHint: '~$1–5 / session',
    badgeColor: '#dc2626',
  },
];

const SCORE_LABELS: Record<string, string> = {
  score_relevance:          'Relevance',
  score_evidence:           'Evidence Support',
  score_clarity:            'Clarity',
  score_completeness:       'Completeness',
  score_methodology:        'Methodology',
  score_critical_thinking:  'Critical Thinking',
};

// ── Component ──────────────────────────────────────────────────────────────

interface Props {
  debateId: string;
  openrouterKey: string;
}

export default function MockDefenseRoom({ debateId, openrouterKey }: Props) {
  // mode & phase
  const [mode, setMode]       = useState<ReasoningMode>('medium');
  const [phase, setPhase]     = useState<Phase>('setup');
  const [error, setError]     = useState('');

  // data
  const [profile, setProfile]         = useState<ResearchProfile | null>(null);
  const [personas, setPersonas]       = useState<SuggestedPersona[]>([]);
  const [questions, setQuestions]     = useState<DefenseQuestion[]>([]);
  const [qIndex, setQIndex]           = useState(0);
  const [evaluation, setEvaluation]   = useState<AnswerEvaluation | null>(null);
  const [report, setReport]           = useState<ReadinessReport | null>(null);
  const [answerText, setAnswerText]   = useState('');
  const [submitting, setSubmitting]   = useState(false);
  const [answeredIds, setAnsweredIds] = useState<Set<string>>(new Set());
  const [showProfile, setShowProfile] = useState(false);

  // Load existing data if any
  useEffect(() => {
    (async () => {
      try {
        const p = await getResearchProfile(debateId);
        setProfile(p);
        if (p.status === 'complete') {
          const qRes = await getDefenseQuestions(debateId);
          if (qRes.count > 0) {
            setQuestions(qRes.questions);
            // check report
            try {
              const r = await getReadinessReport(debateId);
              setReport(r);
              setPhase('report');
            } catch {
              setPhase('questions');
            }
          } else {
            setPhase('setup');
          }
        }
      } catch {
        // no profile yet – stay on setup
      }
    })();
  }, [debateId]);

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleAnalyzeAndSuggest = useCallback(async () => {
    setError('');
    setPhase('analyzing');
    try {
      const res = await analyzeResearch(debateId, openrouterKey, mode);
      setProfile(res.profile);

      setPhase('suggesting');
      const pRes = await suggestPersonas(debateId, openrouterKey, mode);
      setPersonas(pRes.personas);

      setPhase('questions');
    } catch (e: any) {
      setError(e.message || 'Analysis failed');
      setPhase('error');
    }
  }, [debateId, openrouterKey, mode]);

  const handleGenerateQuestions = useCallback(async () => {
    setError('');
    setPhase('analyzing');
    try {
      const res = await generateDefenseQuestions(debateId, openrouterKey, 15, mode);
      setQuestions(res.questions);
      setQIndex(0);
      setPhase('defense');
    } catch (e: any) {
      setError(e.message || 'Question generation failed');
      setPhase('error');
    }
  }, [debateId, openrouterKey, mode]);

  const handleSubmitAnswer = useCallback(async () => {
    if (!answerText.trim() || submitting) return;
    const q = questions[qIndex];
    if (!q) return;
    setSubmitting(true);
    setError('');
    try {
      const ev = await submitAnswer(debateId, q.question_id, answerText, openrouterKey, mode);
      setEvaluation(ev);
      setAnsweredIds(prev => new Set(prev).add(q.question_id));
      setPhase('evaluated');
    } catch (e: any) {
      setError(e.message || 'Evaluation failed');
    } finally {
      setSubmitting(false);
    }
  }, [answerText, debateId, openrouterKey, mode, questions, qIndex, submitting]);

  const handleNextQuestion = useCallback(() => {
    setAnswerText('');
    setEvaluation(null);
    const next = qIndex + 1;
    if (next >= questions.length) {
      setPhase('questions'); // all done — let them generate report
    } else {
      setQIndex(next);
      setPhase('defense');
    }
  }, [qIndex, questions.length]);

  const handleGenerateReport = useCallback(async () => {
    setError('');
    setPhase('analyzing');
    try {
      const r = await generateReadinessReport(debateId, openrouterKey, mode);
      setReport(r);
      setPhase('report');
    } catch (e: any) {
      setError(e.message || 'Report generation failed');
      setPhase('error');
    }
  }, [debateId, openrouterKey, mode]);

  // ── Render helpers ─────────────────────────────────────────────────────────

  const currentQuestion = questions[qIndex] ?? null;
  const answeredCount   = answeredIds.size;
  const modeInfo        = MODE_OPTIONS.find(m => m.id === mode)!;

  // ── Setup phase ────────────────────────────────────────────────────────────

  if (phase === 'setup') {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <h2 className={styles.title}>🎓 Mock Defense Setup</h2>
          <p className={styles.subtitle}>
            Choose your reasoning mode, then analyse your research to generate a
            tailored committee and defense questions.
          </p>
        </div>

        {/* Mode selector */}
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>Reasoning Mode</h3>
          <div className={styles.modeGrid}>
            {MODE_OPTIONS.map(opt => (
              <button
                key={opt.id}
                className={`${styles.modeCard} ${mode === opt.id ? styles.modeCardActive : ''}`}
                onClick={() => setMode(opt.id)}
                style={mode === opt.id ? { borderColor: opt.badgeColor } : undefined}
              >
                <div className={styles.modeEmoji}>{opt.emoji}</div>
                <div className={styles.modeLabel}>{opt.label}</div>
                <div className={styles.modeDesc}>{opt.description}</div>
                <div
                  className={styles.modeCost}
                  style={{ color: opt.badgeColor }}
                >
                  {opt.costHint}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Persona preview */}
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>AI Committee Personas</h3>
          <p className={styles.hint}>
            After analysis, the AI will suggest 6 committee members tailored
            to your specific research domain and methodology.
          </p>
          <div className={styles.personaPreviewGrid}>
            {[
              { role: 'Advisor', icon: '🧑‍🏫', desc: 'Alignment with research goals' },
              { role: 'Methodology Professor', icon: '🔬', desc: 'Methods, baselines, validity' },
              { role: 'Domain Expert', icon: '📚', desc: 'Domain correctness, contribution' },
              { role: 'Skeptical Reviewer', icon: '🤨', desc: 'Weak claims, unsupported assumptions' },
              { role: 'Friendly Professor', icon: '😊', desc: 'Clarity and confidence-building' },
              { role: 'External Examiner', icon: '🎓', desc: 'Defense-level challenge' },
            ].map(p => (
              <div key={p.role} className={styles.personaPreviewCard}>
                <span className={styles.personaIcon}>{p.icon}</span>
                <div className={styles.personaRole}>{p.role}</div>
                <div className={styles.personaDesc}>{p.desc}</div>
              </div>
            ))}
          </div>
        </div>

        <button className={styles.primaryBtn} onClick={handleAnalyzeAndSuggest}>
          Analyse Research &amp; Suggest Committee →
        </button>
      </div>
    );
  }

  // ── Loading states ─────────────────────────────────────────────────────────

  if (phase === 'analyzing' || phase === 'suggesting') {
    const msg = phase === 'suggesting'
      ? 'Generating tailored committee personas…'
      : 'Analysing your research materials…';
    return (
      <div className={styles.container}>
        <div className={styles.loadingBox}>
          <div className={styles.spinner} />
          <p className={styles.loadingText}>{msg}</p>
          <p className={styles.loadingHint}>
            Using <strong>{modeInfo.emoji} {modeInfo.label}</strong> mode — this may take a moment
          </p>
        </div>
      </div>
    );
  }

  // ── Error state ────────────────────────────────────────────────────────────

  if (phase === 'error') {
    return (
      <div className={styles.container}>
        <div className={styles.errorBox}>
          <h3>Something went wrong</h3>
          <p>{error}</p>
          <button className={styles.secondaryBtn} onClick={() => setPhase('setup')}>
            ← Back to Setup
          </button>
        </div>
      </div>
    );
  }

  // ── Questions / pre-defense ────────────────────────────────────────────────

  if (phase === 'questions') {
    return (
      <div className={styles.container}>
        {/* Mode badge */}
        <div className={styles.modeBadgeRow}>
          <span
            className={styles.modeBadge}
            style={{ background: modeInfo.badgeColor }}
          >
            {modeInfo.emoji} {modeInfo.label} Mode
          </span>
          {answeredCount > 0 && (
            <span className={styles.progressBadge}>
              {answeredCount}/{questions.length} answered
            </span>
          )}
        </div>

        {/* Suggested personas */}
        {personas.length > 0 && (
          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>Your AI Committee</h3>
            <div className={styles.personaGrid}>
              {personas.map((p, i) => (
                <div key={i} className={styles.personaCard}>
                  <div className={styles.personaCardRole}>{p.role}</div>
                  <div className={styles.personaCardName}>{p.name}</div>
                  <div className={styles.personaCardExpertise}>{p.expertise}</div>
                  <div className={styles.personaCardFocus}>
                    🎯 {p.focus_area}
                  </div>
                  <div className={styles.personaModel}>
                    Model: <code>{p.model_id}</code>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Research profile summary */}
        {profile && (
          <div className={styles.section}>
            <button
              className={styles.toggleBtn}
              onClick={() => setShowProfile(v => !v)}
            >
              {showProfile ? '▲ Hide' : '▼ Show'} Research Profile
            </button>
            {showProfile && (
              <div className={styles.profileGrid}>
                {[
                  ['Research Problem', profile.research_problem],
                  ['Main Claim',        profile.main_claim],
                  ['Methodology',       profile.methodology],
                  ['Contribution',      profile.contribution],
                  ['Limitations',       profile.limitations],
                ].map(([label, val]) => val ? (
                  <div key={label as string} className={styles.profileItem}>
                    <div className={styles.profileLabel}>{label}</div>
                    <div className={styles.profileValue}>{val as string}</div>
                  </div>
                ) : null)}
              </div>
            )}
          </div>
        )}

        {/* Question list */}
        {questions.length > 0 ? (
          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>
              Defense Questions ({questions.length})
            </h3>
            <div className={styles.questionList}>
              {questions.map((q, i) => (
                <div
                  key={q.question_id}
                  className={`${styles.questionListItem} ${answeredIds.has(q.question_id) ? styles.answered : ''}`}
                >
                  <span className={styles.qNum}>{i + 1}</span>
                  <div className={styles.qMeta}>
                    <span className={styles.qPersona}>{q.persona}</span>
                    <span className={`${styles.qDiff} ${styles[q.difficulty]}`}>{q.difficulty}</span>
                    <span className={styles.qCat}>{q.category}</span>
                  </div>
                  <div className={styles.qText}>{q.question_text}</div>
                  {answeredIds.has(q.question_id) && (
                    <span className={styles.answeredBadge}>✓ Answered</span>
                  )}
                </div>
              ))}
            </div>

            <div className={styles.actionRow}>
              <button className={styles.primaryBtn} onClick={() => { setQIndex(0); setPhase('defense'); }}>
                Start Defense →
              </button>
              {answeredCount > 0 && (
                <button className={styles.reportBtn} onClick={handleGenerateReport}>
                  Generate Readiness Report
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className={styles.section}>
            <p className={styles.hint}>No questions yet. Generate them to begin.</p>
            <button className={styles.primaryBtn} onClick={handleGenerateQuestions}>
              Generate Defense Questions →
            </button>
          </div>
        )}
      </div>
    );
  }

  // ── Active defense ─────────────────────────────────────────────────────────

  if (phase === 'defense' && currentQuestion) {
    return (
      <div className={styles.container}>
        <div className={styles.modeBadgeRow}>
          <span className={styles.modeBadge} style={{ background: modeInfo.badgeColor }}>
            {modeInfo.emoji} {modeInfo.label}
          </span>
          <span className={styles.qCounter}>
            Question {qIndex + 1} of {questions.length}
          </span>
        </div>

        {/* Persona + question card */}
        <div className={styles.questionCard}>
          <div className={styles.personaHeader}>
            <div className={styles.personaAvatar}>
              {getPersonaEmoji(currentQuestion.persona)}
            </div>
            <div>
              <div className={styles.activePersonaRole}>{currentQuestion.persona}</div>
              {/* Show suggested persona name if available */}
              {personas.find(p => p.role === currentQuestion.persona) && (
                <div className={styles.activePersonaName}>
                  {personas.find(p => p.role === currentQuestion.persona)!.name}
                </div>
              )}
            </div>
            <div className={styles.questionMeta}>
              <span className={`${styles.diffBadge} ${styles[currentQuestion.difficulty]}`}>
                {currentQuestion.difficulty}
              </span>
              <span className={styles.catBadge}>{currentQuestion.category}</span>
            </div>
          </div>

          <p className={styles.questionText}>{currentQuestion.question_text}</p>

          {currentQuestion.source_excerpt && (
            <blockquote className={styles.sourceExcerpt}>
              📄 {currentQuestion.source_excerpt}
            </blockquote>
          )}
        </div>

        {/* Answer box */}
        <div className={styles.answerSection}>
          <label className={styles.answerLabel}>Your Answer</label>
          <textarea
            className={styles.answerTextarea}
            value={answerText}
            onChange={e => setAnswerText(e.target.value)}
            placeholder="Type your answer here. Be specific — reference your methodology, evidence, and document sources."
            rows={7}
            disabled={submitting}
          />
          <div className={styles.wordCount}>
            {answerText.trim().split(/\s+/).filter(Boolean).length} words
          </div>
        </div>

        {error && <div className={styles.inlineError}>{error}</div>}

        <div className={styles.actionRow}>
          <button
            className={styles.secondaryBtn}
            onClick={() => setPhase('questions')}
            disabled={submitting}
          >
            ← Back to Questions
          </button>
          <button
            className={styles.primaryBtn}
            onClick={handleSubmitAnswer}
            disabled={submitting || answerText.trim().length < 10}
          >
            {submitting ? 'Evaluating…' : 'Submit Answer →'}
          </button>
        </div>
      </div>
    );
  }

  // ── Evaluation result ──────────────────────────────────────────────────────

  if (phase === 'evaluated' && evaluation && currentQuestion) {
    const score = Math.round(evaluation.overall_score * 10) / 10;
    const scoreColor = score >= 7 ? '#16a34a' : score >= 5 ? '#d97706' : '#dc2626';
    const followUp = evaluation.follow_up_needed && evaluation.follow_up_question;

    return (
      <div className={styles.container}>
        <div className={styles.modeBadgeRow}>
          <span className={styles.modeBadge} style={{ background: modeInfo.badgeColor }}>
            {modeInfo.emoji} {modeInfo.label}
          </span>
        </div>

        <div className={styles.evalCard}>
          <div className={styles.evalHeader}>
            <div className={styles.overallScore} style={{ color: scoreColor }}>
              {score}/10
            </div>
            <div>
              <div className={styles.evalTitle}>Answer Evaluation</div>
              <div className={styles.evalQuestion}>{currentQuestion.question_text}</div>
            </div>
          </div>

          {/* 6-axis scores */}
          <div className={styles.scoreGrid}>
            {Object.entries(SCORE_LABELS).map(([key, label]) => {
              const val = (evaluation as any)[key] ?? 0;
              const pct = (val / 10) * 100;
              const barColor = val >= 7 ? '#16a34a' : val >= 5 ? '#d97706' : '#dc2626';
              return (
                <div key={key} className={styles.scoreRow}>
                  <span className={styles.scoreLabel}>{label}</span>
                  <div className={styles.scoreBar}>
                    <div
                      className={styles.scoreBarFill}
                      style={{ width: `${pct}%`, background: barColor }}
                    />
                  </div>
                  <span className={styles.scoreVal}>{val}</span>
                </div>
              );
            })}
          </div>

          {/* Feedback */}
          <div className={styles.feedbackGrid}>
            <div className={`${styles.feedbackCard} ${styles.strength}`}>
              <h4>✅ Strength</h4>
              <p>{evaluation.strength}</p>
            </div>
            <div className={`${styles.feedbackCard} ${styles.weakness}`}>
              <h4>⚠️ Weakness</h4>
              <p>{evaluation.weakness}</p>
            </div>
          </div>

          {evaluation.missing_evidence && (
            <div className={styles.missingEvidence}>
              <h4>📄 Missing Evidence</h4>
              <p>{evaluation.missing_evidence}</p>
            </div>
          )}

          {evaluation.suggested_improvement && (
            <div className={styles.improvement}>
              <h4>💡 Suggested Improvement</h4>
              <p>{evaluation.suggested_improvement}</p>
            </div>
          )}

          {followUp && (
            <div className={styles.followUp}>
              <h4>🔄 Follow-up Question</h4>
              <p>{evaluation.follow_up_question}</p>
            </div>
          )}
        </div>

        <div className={styles.actionRow}>
          {qIndex + 1 < questions.length ? (
            <button className={styles.primaryBtn} onClick={handleNextQuestion}>
              Next Question →
            </button>
          ) : (
            <button className={styles.reportBtn} onClick={handleGenerateReport}>
              All Done — Generate Readiness Report 📊
            </button>
          )}
          <button className={styles.secondaryBtn} onClick={() => setPhase('questions')}>
            ← Back to Overview
          </button>
        </div>
      </div>
    );
  }

  // ── Readiness report ───────────────────────────────────────────────────────

  if (phase === 'report' && report) {
    const overall = report.overall_readiness ?? 0;
    const color = overall >= 70 ? '#16a34a' : overall >= 50 ? '#d97706' : '#dc2626';
    const label = overall >= 70 ? 'Ready for Defense' : overall >= 50 ? 'Needs More Preparation' : 'Significant Work Required';

    return (
      <div className={styles.container}>
        <div className={styles.modeBadgeRow}>
          <span className={styles.modeBadge} style={{ background: modeInfo.badgeColor }}>
            {modeInfo.emoji} {modeInfo.label}
          </span>
        </div>

        <div className={styles.reportHeader}>
          <div className={styles.bigScore} style={{ color }}>
            {Math.round(overall)}%
          </div>
          <div>
            <h2 className={styles.reportTitle}>Defense Readiness Report</h2>
            <div className={styles.readinessLabel} style={{ color }}>{label}</div>
          </div>
        </div>

        {/* Dimension scores */}
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>Dimension Scores</h3>
          <div className={styles.dimGrid}>
            {[
              ['Research Clarity',  report.research_clarity],
              ['Methodology',       report.methodology_score],
              ['Evidence',          report.evidence_score],
              ['Critical Thinking', report.critical_thinking],
              ['Communication',     report.communication],
            ].map(([label, val]) => {
              const v = (val as number) ?? 0;
              const c = v >= 70 ? '#16a34a' : v >= 50 ? '#d97706' : '#dc2626';
              return (
                <div key={label as string} className={styles.dimCard}>
                  <div className={styles.dimScore} style={{ color: c }}>{Math.round(v)}%</div>
                  <div className={styles.dimLabel}>{label as string}</div>
                  <div className={styles.dimBar}>
                    <div style={{ width: `${v}%`, background: c, height: '100%', borderRadius: '4px' }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Strong / Weak */}
        <div className={styles.swGrid}>
          {report.strong_answers && report.strong_answers.length > 0 && (
            <div className={styles.section}>
              <h3 className={styles.sectionTitle}>💪 Strong Answers</h3>
              {report.strong_answers.map((a: any, i: number) => (
                <div key={i} className={styles.swItem}>
                  <span className={styles.swScore}>
                    {typeof a.overall_score === 'number' ? `${a.overall_score}/10` : ''}
                  </span>
                  <span>{a.question_text || a.question || JSON.stringify(a)}</span>
                </div>
              ))}
            </div>
          )}
          {report.weak_answers && report.weak_answers.length > 0 && (
            <div className={styles.section}>
              <h3 className={styles.sectionTitle}>⚠️ Weak Answers</h3>
              {report.weak_answers.map((a: any, i: number) => (
                <div key={i} className={styles.swItemWeak}>
                  <span className={styles.swScore}>
                    {typeof a.overall_score === 'number' ? `${a.overall_score}/10` : ''}
                  </span>
                  <span>{a.question_text || a.question || JSON.stringify(a)}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Improvement plan */}
        {report.improvement_plan && report.improvement_plan.length > 0 && (
          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>📋 Improvement Plan</h3>
            <ol className={styles.planList}>
              {report.improvement_plan.map((item: any, i: number) => (
                <li key={i} className={styles.planItem}>
                  {typeof item === 'string' ? item : JSON.stringify(item)}
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* Likely questions */}
        {report.likely_questions && report.likely_questions.length > 0 && (
          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>🔮 Likely Committee Questions</h3>
            <ul className={styles.likelyList}>
              {report.likely_questions.map((q: string, i: number) => (
                <li key={i}>{q}</li>
              ))}
            </ul>
          </div>
        )}

        {report.next_recommendation && (
          <div className={styles.nextRec}>
            <h4>🚀 Next Practice Recommendation</h4>
            <p>{report.next_recommendation}</p>
          </div>
        )}

        <div className={styles.actionRow}>
          <button className={styles.secondaryBtn} onClick={() => setPhase('questions')}>
            ← Back to Questions
          </button>
          <button
            className={styles.primaryBtn}
            onClick={() => {
              setAnsweredIds(new Set());
              setEvaluation(null);
              setPhase('setup');
            }}
          >
            Start New Session
          </button>
        </div>
      </div>
    );
  }

  return null;
}

// ── Helpers ────────────────────────────────────────────────────────────────

function getPersonaEmoji(role: string): string {
  const map: Record<string, string> = {
    'Advisor':                 '🧑‍🏫',
    'Methodology Professor':   '🔬',
    'Domain Expert':           '📚',
    'Skeptical Reviewer':      '🤨',
    'Friendly Professor':      '😊',
    'External Examiner':       '🎓',
  };
  return map[role] ?? '👤';
}
