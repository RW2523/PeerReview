'use client';

import { useState, useEffect, useCallback } from 'react';
import * as api from '@/lib/api';
import type {
  ResearchProfile, DefenseQuestion, AnswerEvaluation, ReadinessReport
} from '@/lib/api';
import { keyStore } from '@/lib/openrouterKeyStore';
import styles from './MockDefenseRoom.module.css';

interface Props {
  debateId: string;
}

type Phase = 'setup' | 'analyzing' | 'questions' | 'defense' | 'report';

const CATEGORY_LABELS: Record<string, string> = {
  problem_statement:  'Problem Statement',
  research_gap:       'Research Gap',
  methodology:        'Methodology',
  novelty:            'Novelty',
  evidence:           'Evidence',
  limitations:        'Limitations',
  results:            'Results',
  future_work:        'Future Work',
  practical_impact:   'Practical Impact',
  committee_challenge:'Committee Challenge',
};

const DIFFICULTY_COLOR: Record<string, string> = {
  easy:   '#22c55e',
  medium: '#f59e0b',
  hard:   '#ef4444',
};

const PERSONA_EMOJI: Record<string, string> = {
  'Advisor':               '🎓',
  'Methodology Professor': '🔬',
  'Domain Expert':         '📚',
  'Skeptical Reviewer':    '🧐',
  'Friendly Professor':    '😊',
  'External Examiner':     '⚖️',
};

export default function MockDefenseRoom({ debateId }: Props) {
  const [phase, setPhase] = useState<Phase>('setup');
  const [profile, setProfile] = useState<ResearchProfile | null>(null);
  const [questions, setQuestions] = useState<DefenseQuestion[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [answer, setAnswer] = useState('');
  const [evaluation, setEvaluation] = useState<AnswerEvaluation | null>(null);
  const [allEvaluations, setAllEvaluations] = useState<AnswerEvaluation[]>([]);
  const [report, setReport] = useState<ReadinessReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nQuestions, setNQuestions] = useState(10);

  const apiKey = keyStore.getKey() || '';

  // ── Load existing data on mount ──────────────────────────────────────────
  useEffect(() => {
    (async () => {
      try {
        const p = await api.getResearchProfile(debateId);
        setProfile(p);
        if (p.status === 'complete') {
          const qs = await api.getDefenseQuestions(debateId);
          if (qs.questions.length > 0) {
            setQuestions(qs.questions);
            const ans = await api.getAnswers(debateId);
            setAllEvaluations(ans.answers as AnswerEvaluation[]);
            // Find first unanswered
            const firstUnanswered = qs.questions.findIndex(q => !q.asked);
            setCurrentIdx(firstUnanswered >= 0 ? firstUnanswered : 0);
            setPhase('defense');
          } else {
            setPhase('questions');
          }
        } else {
          setPhase('setup');
        }
        // Check for existing report
        try {
          const r = await api.getReadinessReport(debateId);
          setReport(r);
          if (r.status === 'complete') setPhase('report');
        } catch {}
      } catch {
        setPhase('setup');
      }
    })();
  }, [debateId]);

  // ── Step 1: Analyze research ─────────────────────────────────────────────
  const handleAnalyze = useCallback(async () => {
    if (!apiKey) { setError('Enter your OpenRouter API key first (Key Vault button)'); return; }
    setError(null);
    setLoading(true);
    setPhase('analyzing');
    try {
      const result = await api.analyzeResearch(debateId, apiKey);
      setProfile(result.profile);
      setPhase('questions');
    } catch (e: any) {
      setError(e.message);
      setPhase('setup');
    } finally {
      setLoading(false);
    }
  }, [debateId, apiKey]);

  // ── Step 2: Generate questions ───────────────────────────────────────────
  const handleGenerateQuestions = useCallback(async () => {
    if (!apiKey) { setError('Enter your OpenRouter API key first'); return; }
    setError(null);
    setLoading(true);
    try {
      const result = await api.generateDefenseQuestions(debateId, apiKey, nQuestions);
      setQuestions(result.questions);
      setCurrentIdx(0);
      setPhase('defense');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [debateId, apiKey, nQuestions]);

  // ── Step 3: Submit answer ────────────────────────────────────────────────
  const handleSubmitAnswer = useCallback(async () => {
    if (!apiKey) { setError('Enter your OpenRouter API key first'); return; }
    if (!answer.trim()) { setError('Please type your answer before submitting'); return; }
    const q = questions[currentIdx];
    if (!q) return;
    setError(null);
    setLoading(true);
    setEvaluation(null);
    try {
      const ev = await api.submitAnswer(debateId, q.question_id, answer.trim(), apiKey);
      setEvaluation(ev);
      setAllEvaluations(prev => [...prev, ev]);
      // Mark question as answered locally
      setQuestions(prev => prev.map((pq, i) => i === currentIdx ? { ...pq, asked: true } : pq));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [debateId, apiKey, answer, questions, currentIdx]);

  const handleNextQuestion = useCallback(() => {
    setAnswer('');
    setEvaluation(null);
    setError(null);
    const nextIdx = currentIdx + 1;
    if (nextIdx < questions.length) {
      setCurrentIdx(nextIdx);
    } else {
      setPhase('report');
    }
  }, [currentIdx, questions.length]);

  // ── Step 4: Generate report ──────────────────────────────────────────────
  const handleGenerateReport = useCallback(async () => {
    if (!apiKey) { setError('Enter your OpenRouter API key first'); return; }
    setError(null);
    setLoading(true);
    try {
      const r = await api.generateReadinessReport(debateId, apiKey);
      setReport(r);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [debateId, apiKey]);

  // ── Render ───────────────────────────────────────────────────────────────
  const currentQ = questions[currentIdx];
  const answeredCount = questions.filter(q => q.asked).length;
  const progress = questions.length > 0 ? Math.round((answeredCount / questions.length) * 100) : 0;

  return (
    <div className={styles.defenseRoom}>
      {/* Header */}
      <div className={styles.header}>
        <h2>🎓 Mock Defense Room</h2>
        <div className={styles.headerMeta}>
          {phase === 'defense' && (
            <span className={styles.progress}>
              {answeredCount} / {questions.length} questions answered
            </span>
          )}
          <span className={`${styles.phaseBadge} ${styles[`phase_${phase}`]}`}>
            {phase === 'setup' && '📋 Setup'}
            {phase === 'analyzing' && '🔬 Analyzing…'}
            {phase === 'questions' && '🗂 Generating Questions'}
            {phase === 'defense' && '⚔️ Defense In Progress'}
            {phase === 'report' && '📊 Report Ready'}
          </span>
        </div>
      </div>

      {error && (
        <div className={styles.errorBanner}>⚠️ {error}</div>
      )}

      {/* ── Phase: Setup ── */}
      {phase === 'setup' && (
        <div className={styles.setupCard}>
          <p className={styles.setupIntro}>
            Upload your research documents (in the Materials step), then analyze them to
            build your research profile and generate personalized committee questions.
          </p>
          <button
            className={styles.btnPrimary}
            onClick={handleAnalyze}
            disabled={loading || !apiKey}
          >
            🔬 Analyze Research Materials
          </button>
          {!apiKey && (
            <p className={styles.keyHint}>⚠️ Click "API Key" in the toolbar to enter your OpenRouter key.</p>
          )}
        </div>
      )}

      {/* ── Phase: Analyzing ── */}
      {phase === 'analyzing' && (
        <div className={styles.loadingCard}>
          <div className={styles.spinner} />
          <p>Analyzing your research materials…<br /><small>This may take 30-60 seconds</small></p>
        </div>
      )}

      {/* ── Phase: Questions (profile ready, no questions yet) ── */}
      {phase === 'questions' && profile && (
        <div className={styles.profileCard}>
          <h3>✅ Research Profile Ready</h3>
          <div className={styles.profileGrid}>
            <ProfileField label="Research Problem"  value={profile.research_problem} />
            <ProfileField label="Main Claim"        value={profile.main_claim} />
            <ProfileField label="Methodology"       value={profile.methodology} />
            <ProfileField label="Limitations"       value={profile.limitations} />
          </div>
          {profile.weak_areas && profile.weak_areas.length > 0 && (
            <div className={styles.weakAreas}>
              <strong>⚠️ Potential Weak Areas:</strong>
              <ul>
                {profile.weak_areas.map((w, i) => (
                  <li key={i}><b>{w.area}:</b> {w.reason}</li>
                ))}
              </ul>
            </div>
          )}
          <div className={styles.questionConfig}>
            <label>Number of questions:
              <input
                type="number" min={5} max={30} value={nQuestions}
                onChange={e => setNQuestions(Number(e.target.value))}
                className={styles.numInput}
              />
            </label>
          </div>
          <button
            className={styles.btnPrimary}
            onClick={handleGenerateQuestions}
            disabled={loading}
          >
            {loading ? '⏳ Generating…' : '🗂 Generate Defense Questions'}
          </button>
        </div>
      )}

      {/* ── Phase: Defense ── */}
      {phase === 'defense' && currentQ && !evaluation && (
        <div className={styles.defenseCard}>
          {/* Progress bar */}
          <div className={styles.progressBar}>
            <div className={styles.progressFill} style={{ width: `${progress}%` }} />
          </div>

          {/* Question card */}
          <div className={styles.questionCard}>
            <div className={styles.questionMeta}>
              <span className={styles.personaBadge}>
                {PERSONA_EMOJI[currentQ.persona] || '🎓'} {currentQ.persona}
              </span>
              <span className={styles.categoryBadge}>
                {CATEGORY_LABELS[currentQ.category] || currentQ.category}
              </span>
              <span
                className={styles.difficultyBadge}
                style={{ background: DIFFICULTY_COLOR[currentQ.difficulty] }}
              >
                {currentQ.difficulty}
              </span>
            </div>

            <p className={styles.questionText}>{currentQ.question_text}</p>

            {currentQ.source_excerpt && (
              <blockquote className={styles.sourceExcerpt}>
                📄 {currentQ.source_excerpt}
              </blockquote>
            )}
          </div>

          {/* Answer box */}
          <div className={styles.answerBox}>
            <label className={styles.answerLabel}>Your Answer:</label>
            <textarea
              className={styles.answerTextarea}
              placeholder="Type your answer here. Be specific — reference your methodology, data, and evidence."
              value={answer}
              onChange={e => setAnswer(e.target.value)}
              rows={6}
              disabled={loading}
            />
            <div className={styles.answerActions}>
              <span className={styles.wordCount}>{answer.trim().split(/\s+/).filter(Boolean).length} words</span>
              <button
                className={styles.btnPrimary}
                onClick={handleSubmitAnswer}
                disabled={loading || !answer.trim()}
              >
                {loading ? '⏳ Evaluating…' : '✅ Submit Answer'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Evaluation result ── */}
      {phase === 'defense' && evaluation && (
        <div className={styles.evalCard}>
          <h3>📊 Answer Evaluation</h3>
          <div className={styles.overallScore}>
            <span className={styles.scoreNumber}>{evaluation.overall_score.toFixed(1)}</span>
            <span className={styles.scoreLabel}>/ 10 overall</span>
          </div>

          <div className={styles.scoreGrid}>
            <ScoreBar label="Relevance"              score={evaluation.score_relevance} />
            <ScoreBar label="Evidence Support"       score={evaluation.score_evidence} />
            <ScoreBar label="Clarity"                score={evaluation.score_clarity} />
            <ScoreBar label="Completeness"           score={evaluation.score_completeness} />
            <ScoreBar label="Methodology"            score={evaluation.score_methodology} />
            <ScoreBar label="Critical Thinking"      score={evaluation.score_critical_thinking} />
          </div>

          <div className={styles.feedbackGrid}>
            <FeedbackBlock emoji="✅" label="Strength"            text={evaluation.strength} />
            <FeedbackBlock emoji="⚠️" label="Weakness"           text={evaluation.weakness} />
            <FeedbackBlock emoji="🔍" label="Missing Evidence"   text={evaluation.missing_evidence} />
            <FeedbackBlock emoji="💡" label="Suggested Improvement" text={evaluation.suggested_improvement} />
          </div>

          {evaluation.follow_up_needed && evaluation.follow_up_question && (
            <div className={styles.followUp}>
              <strong>🔁 Follow-up Question:</strong>
              <p>{evaluation.follow_up_question}</p>
            </div>
          )}

          <div className={styles.evalActions}>
            {currentIdx < questions.length - 1 ? (
              <button className={styles.btnPrimary} onClick={handleNextQuestion}>
                ➡️ Next Question
              </button>
            ) : (
              <button className={styles.btnPrimary} onClick={() => setPhase('report')}>
                📊 Generate Readiness Report
              </button>
            )}
            <button className={styles.btnSecondary} onClick={handleNextQuestion}>
              Skip
            </button>
          </div>
        </div>
      )}

      {/* ── Phase: Report ── */}
      {phase === 'report' && (
        <div className={styles.reportPhase}>
          {!report ? (
            <div className={styles.reportGenerate}>
              <h3>🎉 Mock Defense Complete!</h3>
              <p>You answered {answeredCount} out of {questions.length} questions.</p>
              <button
                className={styles.btnPrimary}
                onClick={handleGenerateReport}
                disabled={loading}
              >
                {loading ? '⏳ Generating Report…' : '📊 Generate Readiness Report'}
              </button>
            </div>
          ) : (
            <ReadinessReportView report={report} onRestart={() => {
              setPhase('questions');
              setEvaluation(null);
              setAnswer('');
              setCurrentIdx(0);
            }} />
          )}
        </div>
      )}
    </div>
  );
}

// ── Sub-components ──────────────────────────────────────────────────────────

function ProfileField({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <div className={styles.profileField}>
      <span className={styles.fieldLabel}>{label}</span>
      <span className={styles.fieldValue}>{value}</span>
    </div>
  );
}

function ScoreBar({ label, score }: { label: string; score: number }) {
  const pct = Math.min(100, Math.max(0, (score / 10) * 100));
  const color = score >= 7 ? '#22c55e' : score >= 5 ? '#f59e0b' : '#ef4444';
  return (
    <div className={styles.scoreBarRow}>
      <span className={styles.scoreBarLabel}>{label}</span>
      <div className={styles.scoreBarTrack}>
        <div className={styles.scoreBarFill} style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className={styles.scoreBarValue}>{score.toFixed(1)}</span>
    </div>
  );
}

function FeedbackBlock({ emoji, label, text }: { emoji: string; label: string; text?: string | null }) {
  if (!text) return null;
  return (
    <div className={styles.feedbackBlock}>
      <div className={styles.feedbackLabel}>{emoji} {label}</div>
      <p className={styles.feedbackText}>{text}</p>
    </div>
  );
}

function ReadinessReportView({ report, onRestart }: { report: ReadinessReport; onRestart: () => void }) {
  const score = report.overall_readiness ?? 0;
  const color = score >= 70 ? '#22c55e' : score >= 50 ? '#f59e0b' : '#ef4444';
  const label = score >= 70 ? 'Defense Ready ✅' : score >= 50 ? 'Needs More Preparation ⚠️' : 'Significant Gaps Found 🔴';

  return (
    <div className={styles.reportView}>
      <div className={styles.reportHeader}>
        <div className={styles.overallCircle} style={{ borderColor: color }}>
          <span className={styles.circleScore} style={{ color }}>{score.toFixed(0)}</span>
          <span className={styles.circleLabel}>/ 100</span>
        </div>
        <div>
          <h3 className={styles.readinessLabel} style={{ color }}>{label}</h3>
          <p className={styles.recommendation}>{report.next_recommendation}</p>
        </div>
      </div>

      {/* Dimension scores */}
      <div className={styles.dimGrid}>
        {[
          { label: 'Research Clarity',   val: report.research_clarity },
          { label: 'Methodology',         val: report.methodology_score },
          { label: 'Evidence',            val: report.evidence_score },
          { label: 'Critical Thinking',   val: report.critical_thinking },
          { label: 'Communication',       val: report.communication },
        ].filter(d => d.val != null).map(d => (
          <div key={d.label} className={styles.dimCard}>
            <span className={styles.dimLabel}>{d.label}</span>
            <span className={styles.dimScore}>{d.val!.toFixed(0)}</span>
          </div>
        ))}
      </div>

      {/* Improvement plan */}
      {report.improvement_plan && report.improvement_plan.length > 0 && (
        <section className={styles.reportSection}>
          <h4>📋 Improvement Plan</h4>
          <div className={styles.planList}>
            {report.improvement_plan.map((item: any, i: number) => (
              <div key={i} className={`${styles.planItem} ${styles[`priority_${item.priority}`]}`}>
                <span className={styles.planPriority}>{item.priority}</span>
                <div>
                  <strong>{item.area}</strong>
                  <p>{item.action}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Likely questions */}
      {report.likely_questions && report.likely_questions.length > 0 && (
        <section className={styles.reportSection}>
          <h4>🔮 Likely Committee Questions in Real Defense</h4>
          <ul className={styles.likelyList}>
            {report.likely_questions.map((q, i) => <li key={i}>{q}</li>)}
          </ul>
        </section>
      )}

      {/* Weak answers */}
      {report.weak_answers && report.weak_answers.length > 0 && (
        <section className={styles.reportSection}>
          <h4>⚠️ Answers That Need Work</h4>
          {report.weak_answers.map((a: any, i: number) => (
            <div key={i} className={styles.weakItem}>
              <span className={styles.weakScore}>{Number(a.score).toFixed(1)}/10</span>
              <div>
                <p className={styles.weakQ}>{a.question}</p>
                <p className={styles.weakSummary}>{a.summary}</p>
              </div>
            </div>
          ))}
        </section>
      )}

      <button className={styles.btnSecondary} onClick={onRestart}>
        🔄 Practice Again
      </button>
    </div>
  );
}
