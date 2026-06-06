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
  | 'setup'
  | 'analyzing'
  | 'suggesting'
  | 'questions'
  | 'defense'
  | 'evaluated'
  | 'report'
  | 'error';

interface ModeOption {
  id: ReasoningMode;
  label: string;
  description: string;
  costHint: string;
}

const MODE_OPTIONS: ModeOption[] = [
  {
    id: 'light',
    label: 'Light',
    description: 'Single fast model for all tasks. Ideal for practice and iteration.',
    costHint: '~$0.01–0.05 / session',
  },
  {
    id: 'medium',
    label: 'Medium',
    description: 'Different models per role. Balanced quality and cost.',
    costHint: '~$0.10–0.40 / session',
  },
  {
    id: 'heavy',
    label: 'Heavy',
    description: 'Frontier models for every activity. Production-grade depth.',
    costHint: '~$1–5 / session',
  },
];

const SCORE_LABELS: Record<string, string> = {
  score_relevance:         'Relevance',
  score_evidence:          'Evidence Support',
  score_clarity:           'Clarity',
  score_completeness:      'Completeness',
  score_methodology:       'Methodology',
  score_critical_thinking: 'Critical Thinking',
};

// ── Component ──────────────────────────────────────────────────────────────

interface Props {
  debateId: string;
  openrouterKey: string;
}

export default function MockDefenseRoom({ debateId, openrouterKey }: Props) {
  const [mode, setMode]       = useState<ReasoningMode>('medium');
  const [phase, setPhase]     = useState<Phase>('setup');
  const [error, setError]     = useState('');

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

  // Restore existing session data on mount
  useEffect(() => {
    (async () => {
      try {
        const p = await getResearchProfile(debateId);
        setProfile(p);
        if (p.status === 'complete') {
          const qRes = await getDefenseQuestions(debateId);
          if (qRes.count > 0) {
            setQuestions(qRes.questions);
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
        // no profile yet — remain on setup
      }
    })();
  }, [debateId]);

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleAnalyzeAndSuggest = useCallback(async () => {
    if (!openrouterKey) {
      setError('OpenRouter API key is required. Add it in Settings.');
      setPhase('error');
      return;
    }
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
      setPhase('questions');
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

  // ── Shared values ──────────────────────────────────────────────────────────

  const currentQuestion = questions[qIndex] ?? null;
  const answeredCount   = answeredIds.size;
  const modeInfo        = MODE_OPTIONS.find(m => m.id === mode)!;

  // ── Setup ──────────────────────────────────────────────────────────────────

  if (phase === 'setup') {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <h2 className={styles.title}>Mock Defense</h2>
          <p className={styles.subtitle}>
            Select a reasoning mode, then analyse your uploaded research to generate a
            tailored committee and defense questions.
          </p>
        </div>

        {!openrouterKey && (
          <div style={{
            background: '#fff8e1',
            border: '1px solid #f5a623',
            borderRadius: '10px',
            padding: '16px 20px',
            marginBottom: '24px',
            display: 'flex',
            alignItems: 'center',
            gap: '14px',
          }}>
            <span style={{ fontSize: '1.6rem' }}>🔑</span>
            <div>
              <strong style={{ color: '#92400e', fontSize: '0.95rem' }}>API Key Required</strong>
              <p style={{ margin: '4px 0 0', color: '#92400e', fontSize: '0.875rem' }}>
                Add your OpenRouter API key in{' '}
                <a href="/settings" style={{ fontWeight: 700, textDecoration: 'underline' }}>Settings</a>
                {' '}to run the AI mock defense.
              </p>
            </div>
          </div>
        )}

        <div className={styles.section}>
          <div className={styles.sectionTitle}>Reasoning Mode</div>
          <div className={styles.modeGrid}>
            {MODE_OPTIONS.map(opt => (
              <button
                key={opt.id}
                className={`${styles.modeCard} ${mode === opt.id ? styles.modeCardActive : ''}`}
                onClick={() => setMode(opt.id)}
              >
                <div className={styles.modeLabel}>{opt.label}</div>
                <div className={styles.modeDesc}>{opt.description}</div>
                <div className={styles.modeCost}>{opt.costHint}</div>
              </button>
            ))}
          </div>
        </div>

        <div className={styles.section}>
          <div className={styles.sectionTitle}>AI Committee Roles</div>
          <p className={styles.hint}>
            After analysis, the system generates 6 committee members tailored to your
            research domain. Each member stays within their assigned role.
          </p>
          <div className={styles.personaPreviewGrid}>
            {[
              { role: 'Advisor',               desc: 'Alignment with research goals' },
              { role: 'Methodology Professor', desc: 'Methods, baselines, validity' },
              { role: 'Domain Expert',         desc: 'Domain correctness, contribution' },
              { role: 'Skeptical Reviewer',    desc: 'Weak claims, unsupported assumptions' },
              { role: 'Friendly Professor',    desc: 'Clarity and confidence-building' },
              { role: 'External Examiner',     desc: 'Defense-level challenge' },
            ].map(p => (
              <div key={p.role} className={styles.personaPreviewCard}>
                <div className={styles.personaRole}>{p.role}</div>
                <div className={styles.personaDesc}>{p.desc}</div>
              </div>
            ))}
          </div>
        </div>

        <button
          className={styles.primaryBtn}
          onClick={handleAnalyzeAndSuggest}
          disabled={!openrouterKey}
          style={{ opacity: openrouterKey ? 1 : 0.45, cursor: openrouterKey ? 'pointer' : 'not-allowed' }}
        >
          Analyse Research and Generate Committee
        </button>
      </div>
    );
  }

  // ── Loading ────────────────────────────────────────────────────────────────

  if (phase === 'analyzing' || phase === 'suggesting') {
    const steps = [
      { key: 'analyzing', label: 'Analysing research materials…', detail: 'Extracting research problem, methodology, contributions, and weak areas.' },
      { key: 'suggesting', label: 'Generating committee personas…', detail: 'Tailoring 6 AI committee members to your research domain and methodology.' },
    ];
    const current = steps.find(s => s.key === phase) || steps[0];
    return (
      <div className={styles.container}>
        <div className={styles.loadingBox}>
          <div className={styles.spinner} />
          <p className={styles.loadingText}>{current.label}</p>
          <p className={styles.loadingHint}>{modeInfo.label} mode · {current.detail}</p>
          <div style={{ display: 'flex', gap: '8px', marginTop: '20px', justifyContent: 'center' }}>
            {steps.map((s, i) => (
              <div key={s.key} style={{
                width: 10, height: 10, borderRadius: '50%',
                background: s.key === phase ? 'var(--accent, #4f46e5)' : 'var(--border, #ccc)',
                transition: 'background 0.3s',
              }} />
            ))}
          </div>
        </div>
      </div>
    );
  }

  // ── Error ──────────────────────────────────────────────────────────────────

  if (phase === 'error') {
    return (
      <div className={styles.container}>
        <div className={styles.errorBox}>
          <h3>Something went wrong</h3>
          <p style={{ color: 'var(--text-2)', fontSize: '0.9rem', marginBottom: '16px' }}>{error}</p>
          {error.toLowerCase().includes('key') || error.toLowerCase().includes('unauthorized') ? (
            <a href="/settings" style={{
              display: 'inline-block', marginBottom: '12px',
              padding: '10px 20px', background: '#f5a623', color: '#fff',
              borderRadius: '8px', fontWeight: 600, textDecoration: 'none'
            }}>
              🔑 Go to Settings
            </a>
          ) : null}
          <button className={styles.secondaryBtn} onClick={() => { setError(''); setPhase('setup'); }}>
            Back to Setup
          </button>
        </div>
      </div>
    );
  }

  // ── Questions overview ─────────────────────────────────────────────────────

  if (phase === 'questions') {
    return (
      <div className={styles.container}>
        <div className={styles.modeBadgeRow}>
          <span className={styles.modeBadge}>{modeInfo.label}</span>
          {answeredCount > 0 && (
            <span className={styles.progressBadge}>
              {answeredCount} / {questions.length} answered
            </span>
          )}
        </div>

        {/* Suggested committee */}
        {personas.length > 0 && (
          <div className={styles.section}>
            <div className={styles.sectionTitle}>AI Committee</div>
            <div className={styles.personaGrid}>
              {personas.map((p, i) => (
                <div key={i} className={styles.personaCard}>
                  <div className={styles.personaCardRole}>{p.role}</div>
                  <div className={styles.personaCardName}>{p.name}</div>
                  <div className={styles.personaCardExpertise}>{p.expertise}</div>
                  <div className={styles.personaCardFocus}>{p.focus_area}</div>
                  <div className={styles.personaModel}>
                    <code>{p.model_id}</code>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Research profile */}
        {profile && (
          <div className={styles.section}>
            <button
              className={styles.toggleBtn}
              onClick={() => setShowProfile(v => !v)}
            >
              {showProfile ? 'Hide' : 'Show'} Research Profile
            </button>
            {showProfile && (
              <div className={styles.profileGrid}>
                {[
                  ['Research Problem', profile.research_problem],
                  ['Main Claim',       profile.main_claim],
                  ['Methodology',      profile.methodology],
                  ['Contribution',     profile.contribution],
                  ['Limitations',      profile.limitations],
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
            <div className={styles.sectionTitle}>
              Defense Questions &mdash; {questions.length} total
            </div>
            <div className={styles.questionList}>
              {questions.map((q, i) => (
                <div
                  key={q.question_id}
                  className={`${styles.questionListItem} ${answeredIds.has(q.question_id) ? styles.answered : ''}`}
                >
                  <div className={styles.qNum}>Q{i + 1}</div>
                  <div className={styles.qMeta}>
                    <span className={styles.qPersona}>{q.persona}</span>
                    <span className={`${styles.qDiff} ${styles[q.difficulty]}`}>{q.difficulty}</span>
                    <span className={styles.qCat}>{q.category}</span>
                    {answeredIds.has(q.question_id) && (
                      <span className={styles.answeredBadge}>Answered</span>
                    )}
                  </div>
                  <div className={styles.qText}>{q.question_text}</div>
                </div>
              ))}
            </div>

            <div className={styles.actionRow}>
              <button className={styles.primaryBtn} onClick={() => { setQIndex(0); setPhase('defense'); }}>
                Start Defense
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
            <p className={styles.hint}>No questions generated yet.</p>
            <button className={styles.primaryBtn} onClick={handleGenerateQuestions}>
              Generate Defense Questions
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
          <span className={styles.modeBadge}>{modeInfo.label}</span>
          <span className={styles.qCounter}>
            Question {qIndex + 1} of {questions.length}
          </span>
        </div>

        <div className={styles.questionCard}>
          <div className={styles.personaHeader}>
            <div>
              <div className={styles.activePersonaRole}>{currentQuestion.persona}</div>
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
              {currentQuestion.source_excerpt}
            </blockquote>
          )}
        </div>

        <div className={styles.answerSection}>
          <label className={styles.answerLabel}>Your Answer</label>
          <textarea
            className={styles.answerTextarea}
            value={answerText}
            onChange={e => setAnswerText(e.target.value)}
            placeholder="Type your answer here. Reference your methodology, evidence, and document sources where applicable."
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
            Back to Questions
          </button>
          <button
            className={styles.primaryBtn}
            onClick={handleSubmitAnswer}
            disabled={submitting || answerText.trim().length < 10}
          >
            {submitting ? 'Evaluating…' : 'Submit Answer'}
          </button>
        </div>
      </div>
    );
  }

  // ── Evaluation result ──────────────────────────────────────────────────────

  if (phase === 'evaluated' && evaluation && currentQuestion) {
    const score      = Math.round(evaluation.overall_score * 10) / 10;
    const scoreColor = score >= 7 ? 'var(--accent)' : score >= 5 ? 'var(--warning, #f5a623)' : 'var(--danger, #e00)';
    const followUp   = evaluation.follow_up_needed && evaluation.follow_up_question;

    return (
      <div className={styles.container}>
        <div className={styles.modeBadgeRow}>
          <span className={styles.modeBadge}>{modeInfo.label}</span>
        </div>

        <div className={styles.evalCard}>
          <div className={styles.evalHeader}>
            <div className={styles.overallScore} style={{ color: scoreColor }}>
              {score}<span style={{ fontSize: '1rem', color: 'var(--text-3)' }}>/10</span>
            </div>
            <div>
              <div className={styles.evalTitle}>Answer Evaluation</div>
              <div className={styles.evalQuestion}>{currentQuestion.question_text}</div>
            </div>
          </div>

          <div className={styles.scoreGrid}>
            {Object.entries(SCORE_LABELS).map(([key, label]) => {
              const val = (evaluation as any)[key] ?? 0;
              const pct = (val / 10) * 100;
              const barColor = val >= 7
                ? 'var(--accent)'
                : val >= 5 ? 'var(--warning, #f5a623)' : 'var(--danger, #e00)';
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

          <div className={styles.feedbackGrid}>
            <div className={`${styles.feedbackCard} ${styles.strength}`}>
              <h4>Strength</h4>
              <p>{evaluation.strength}</p>
            </div>
            <div className={`${styles.feedbackCard} ${styles.weakness}`}>
              <h4>Weakness</h4>
              <p>{evaluation.weakness}</p>
            </div>
          </div>

          {evaluation.missing_evidence && (
            <div className={styles.missingEvidence}>
              <h4>Missing Evidence</h4>
              <p>{evaluation.missing_evidence}</p>
            </div>
          )}

          {evaluation.suggested_improvement && (
            <div className={styles.improvement}>
              <h4>Suggested Improvement</h4>
              <p>{evaluation.suggested_improvement}</p>
            </div>
          )}

          {followUp && (
            <div className={styles.followUp}>
              <h4>Follow-up Question</h4>
              <p>{evaluation.follow_up_question}</p>
            </div>
          )}
        </div>

        <div className={styles.actionRow}>
          {qIndex + 1 < questions.length ? (
            <button className={styles.primaryBtn} onClick={handleNextQuestion}>
              Next Question
            </button>
          ) : (
            <button className={styles.reportBtn} onClick={handleGenerateReport}>
              Generate Readiness Report
            </button>
          )}
          <button className={styles.secondaryBtn} onClick={() => setPhase('questions')}>
            Back to Overview
          </button>
        </div>
      </div>
    );
  }

  // ── Readiness report ───────────────────────────────────────────────────────

  if (phase === 'report' && report) {
    const overall = report.overall_readiness ?? 0;
    const color   = overall >= 70 ? 'var(--accent)' : overall >= 50 ? 'var(--warning, #f5a623)' : 'var(--danger, #e00)';
    const label   = overall >= 70
      ? 'Ready for Defense'
      : overall >= 50 ? 'Additional Preparation Recommended'
      : 'Significant Gaps Identified';

    return (
      <div className={styles.container}>
        <div className={styles.modeBadgeRow}>
          <span className={styles.modeBadge}>{modeInfo.label}</span>
        </div>

        <div className={styles.reportHeader}>
          <div className={styles.bigScore} style={{ color }}>
            {Math.round(overall)}%
          </div>
          <div>
            <h2 className={styles.reportTitle}>Defense Readiness Report</h2>
            <div className={styles.readinessLabel}>{label}</div>
          </div>
        </div>

        <div className={styles.section}>
          <div className={styles.sectionTitle}>Dimension Scores</div>
          <div className={styles.dimGrid}>
            {[
              ['Research Clarity',  report.research_clarity],
              ['Methodology',       report.methodology_score],
              ['Evidence',          report.evidence_score],
              ['Critical Thinking', report.critical_thinking],
              ['Communication',     report.communication],
            ].map(([lbl, val]) => {
              const v = (val as number) ?? 0;
              const c = v >= 70 ? 'var(--accent)' : v >= 50 ? 'var(--warning, #f5a623)' : 'var(--danger, #e00)';
              return (
                <div key={lbl as string} className={styles.dimCard}>
                  <div className={styles.dimScore} style={{ color: c }}>{Math.round(v)}%</div>
                  <div className={styles.dimLabel}>{lbl as string}</div>
                  <div className={styles.dimBar}>
                    <div style={{ width: `${v}%`, background: c, height: '100%', borderRadius: '2px' }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className={styles.swGrid}>
          {report.strong_answers && report.strong_answers.length > 0 && (
            <div className={styles.section}>
              <div className={styles.sectionTitle}>Strong Answers</div>
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
              <div className={styles.sectionTitle}>Weak Answers</div>
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

        {report.improvement_plan && report.improvement_plan.length > 0 && (
          <div className={styles.section}>
            <div className={styles.sectionTitle}>Improvement Plan</div>
            <ol className={styles.planList}>
              {report.improvement_plan.map((item: any, i: number) => (
                <li key={i} className={styles.planItem}>
                  {typeof item === 'string' ? item : JSON.stringify(item)}
                </li>
              ))}
            </ol>
          </div>
        )}

        {report.likely_questions && report.likely_questions.length > 0 && (
          <div className={styles.section}>
            <div className={styles.sectionTitle}>Likely Committee Questions</div>
            <ul className={styles.likelyList}>
              {report.likely_questions.map((q: string, i: number) => (
                <li key={i}>{q}</li>
              ))}
            </ul>
          </div>
        )}

        {report.next_recommendation && (
          <div className={styles.nextRec}>
            <h4>Next Practice Recommendation</h4>
            <p>{report.next_recommendation}</p>
          </div>
        )}

        <div className={styles.actionRow}>
          <button className={styles.secondaryBtn} onClick={() => setPhase('questions')}>
            Back to Questions
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
