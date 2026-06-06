'use client';

/**
 * VoiceDefenseRoom
 * ─────────────────────────────────────────────────────────────────────────
 * Full voice-powered mock academic defense:
 *  • TTS   — each committee persona speaks their question aloud.
 *  • STT   — the student answers by speaking; transcript shown live.
 *  • Flow  — analyze → committee → questions → answer → evaluate →
 *            follow-up (if weak) → next question → readiness report.
 * Uses only the browser's built-in Web Speech API — zero extra deps.
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import styles from './VoiceDefenseRoom.module.css';
import { useSpeechSynthesis, roleToVoiceId } from '@/hooks/useSpeechSynthesis';
import { useSpeechRecognition } from '@/hooks/useSpeechRecognition';
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

// ── Types ────────────────────────────────────────────────────────────────

type Phase =
  | 'setup'
  | 'loading'       // analyze + generate
  | 'ready'         // show committee + questions list
  | 'speaking'      // TTS reading question
  | 'listening'     // student speaking
  | 'confirming'    // review transcript before submit
  | 'evaluating'    // waiting for AI evaluation
  | 'result'        // show evaluation
  | 'follow_up'     // TTS reading follow-up, then go to listening
  | 'reporting'     // generating final report
  | 'report'        // show readiness report
  | 'error';

interface LoadingStep { label: string; done: boolean; }

// ── Persona emoji lookup ──────────────────────────────────────────────────

const PERSONA_EMOJI: Record<string, string> = {
  advisor:     '🎓',
  methodology: '📐',
  domain:      '🔬',
  skeptical:   '🧐',
  friendly:    '😊',
  examiner:    '⚖️',
};

function personaEmoji(role: string): string {
  const r = role.toLowerCase();
  if (r.includes('advisor'))   return PERSONA_EMOJI.advisor;
  if (r.includes('method'))    return PERSONA_EMOJI.methodology;
  if (r.includes('domain') || r.includes('expert')) return PERSONA_EMOJI.domain;
  if (r.includes('skeptic'))   return PERSONA_EMOJI.skeptical;
  if (r.includes('friendly'))  return PERSONA_EMOJI.friendly;
  if (r.includes('examiner') || r.includes('external')) return PERSONA_EMOJI.examiner;
  return '👤';
}

const DIFF_COLOR: Record<string, string> = {
  beginner:       '#4d9fff',
  moderate:       '#f5a623',
  advanced:       '#ff6b6b',
  'strict committee': '#ff3333',
};

// ── Score Bar (static component outside render) ──────────────────────────

function ScoreBar({ label, value }: { label: string; value: number }) {
  const pct   = (value / 10) * 100;
  const color = value >= 7 ? '#4ade80' : value >= 5 ? '#f5a623' : '#ff6b6b';
  return (
    <div className={styles.scoreRow}>
      <span className={styles.scoreLabel}>{label}</span>
      <div className={styles.scoreBarTrack}>
        <div className={styles.scoreBarFill} style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className={styles.scoreVal} style={{ color }}>{value}</span>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────

interface Props {
  debateId:      string;
  openrouterKey: string;
}

export default function VoiceDefenseRoom({ debateId, openrouterKey }: Props) {
  const tts = useSpeechSynthesis();
  const stt = useSpeechRecognition();

  const [mode,           setMode]           = useState<ReasoningMode>('light');
  const [phase,          setPhase]          = useState<Phase>('setup');
  const [error,          setError]          = useState('');
  const [loadingSteps,   setLoadingSteps]   = useState<LoadingStep[]>([]);

  const [profile,   setProfile]   = useState<ResearchProfile | null>(null);
  const [personas,  setPersonas]  = useState<SuggestedPersona[]>([]);
  const [questions, setQuestions] = useState<DefenseQuestion[]>([]);
  const [qIndex,    setQIndex]    = useState(0);

  const [evaluation,    setEvaluation]    = useState<AnswerEvaluation | null>(null);
  const [report,        setReport]        = useState<ReadinessReport | null>(null);
  const [answeredCount, setAnsweredCount] = useState(0);

  // editable transcript (user can correct STT mistakes)
  const [editText,   setEditText]   = useState('');
  const [isMuted,    setIsMuted]    = useState(false);
  const [autoSubmit, setAutoSubmit] = useState(true);

  const hasAutoSubmittedRef = useRef(false);

  // ── Restore existing session ──────────────────────────────────────────

  useEffect(() => {
    (async () => {
      try {
        const p = await getResearchProfile(debateId);
        if (p?.status === 'complete') {
          setProfile(p);
          const qRes = await getDefenseQuestions(debateId);
          if (qRes.count > 0) {
            setQuestions(qRes.questions);
            try {
              const r = await getReadinessReport(debateId);
              setReport(r);
              setPhase('report');
            } catch {
              setPhase('ready');
            }
          }
        }
      } catch {
        // no prior data — stay on setup
      }
    })();
  }, [debateId]);

  // ── Auto-submit when STT goes silent ─────────────────────────────────

  useEffect(() => {
    if (
      phase === 'listening' &&
      autoSubmit &&
      !stt.isListening &&
      stt.finalTranscript.trim().length >= 15 &&
      !hasAutoSubmittedRef.current
    ) {
      hasAutoSubmittedRef.current = true;
      setEditText(stt.finalTranscript.trim());
      setPhase('confirming');
    }
  }, [phase, stt.isListening, stt.finalTranscript, autoSubmit]);

  // ── Helpers ───────────────────────────────────────────────────────────

  const currentQuestion = questions[qIndex] ?? null;

  const speakQuestion = useCallback((q: DefenseQuestion) => {
    if (isMuted || !tts.isSupported) return;
    const voiceId = roleToVoiceId(q.persona);
    // Prefix with persona name for clarity
    const intro = `${q.persona} asks: ${q.question_text}`;
    tts.speak(intro, voiceId);
  }, [isMuted, tts]);

  // ── Flow handlers ─────────────────────────────────────────────────────

  const handleStart = useCallback(async () => {
    if (!openrouterKey) {
      setError('OpenRouter API key is required. Add it in Settings.');
      setPhase('error');
      return;
    }
    setError('');
    setPhase('loading');

    const steps: LoadingStep[] = [
      { label: 'Analysing research materials…', done: false },
      { label: 'Generating committee personas…', done: false },
      { label: 'Generating defense questions…', done: false },
    ];
    setLoadingSteps([...steps]);

    try {
      // Step 1: analyze
      const aRes = await analyzeResearch(debateId, openrouterKey, mode);
      setProfile(aRes.profile);
      steps[0].done = true;
      setLoadingSteps([...steps]);

      // Step 2: personas
      const pRes = await suggestPersonas(debateId, openrouterKey, mode);
      setPersonas(pRes.personas);
      steps[1].done = true;
      setLoadingSteps([...steps]);

      // Step 3: questions
      const qRes = await generateDefenseQuestions(debateId, openrouterKey, 10, mode);
      setQuestions(qRes.questions);
      steps[2].done = true;
      setLoadingSteps([...steps]);

      setPhase('ready');
    } catch (e: any) {
      setError(e.message || 'Preparation failed');
      setPhase('error');
    }
  }, [debateId, openrouterKey, mode]);

  const handleBeginDefense = useCallback(() => {
    setQIndex(0);
    setAnsweredCount(0);
    setPhase('speaking');
    if (questions[0]) speakQuestion(questions[0]);
  }, [questions, speakQuestion]);

  const handleStartListening = useCallback(() => {
    tts.cancel();
    hasAutoSubmittedRef.current = false;
    stt.resetTranscript();
    setEditText('');
    setPhase('listening');
    stt.startListening();
  }, [tts, stt]);

  const handleStopListening = useCallback(() => {
    stt.stopListening();
    setEditText(stt.finalTranscript.trim() || stt.interimTranscript.trim());
    setPhase('confirming');
  }, [stt]);

  const handleSubmitAnswer = useCallback(async () => {
    const text = editText.trim();
    if (text.length < 10 || !currentQuestion) return;

    setPhase('evaluating');
    try {
      const ev = await submitAnswer(debateId, currentQuestion.question_id, text, openrouterKey, mode);
      setEvaluation(ev);
      setAnsweredCount(c => c + 1);
      setPhase('result');

      // TTS reads the strength/feedback (brief version)
      if (!isMuted && tts.isSupported && ev.strength) {
        setTimeout(() => {
          tts.speak(`Score: ${Math.round(ev.overall_score)} out of 10. ${ev.strength}`, 'advisor');
        }, 600);
      }
    } catch (e: any) {
      setError(e.message || 'Evaluation failed');
      setPhase('error');
    }
  }, [editText, currentQuestion, debateId, openrouterKey, mode, isMuted, tts]);

  const handleFollowUp = useCallback(() => {
    if (!evaluation?.follow_up_question) return;
    setPhase('follow_up');
    if (!isMuted && tts.isSupported) {
      const voiceId = currentQuestion ? roleToVoiceId(currentQuestion.persona) : 'default';
      tts.speak(`Follow-up: ${evaluation.follow_up_question}`, voiceId);
    }
    // After a brief pause, move to listening
    setTimeout(() => {
      hasAutoSubmittedRef.current = false;
      stt.resetTranscript();
      setEditText('');
      setPhase('listening');
      stt.startListening();
    }, 3500);
  }, [evaluation, currentQuestion, isMuted, tts, stt]);

  const handleNextQuestion = useCallback(() => {
    tts.cancel();
    stt.resetTranscript();
    setEvaluation(null);
    setEditText('');
    const next = qIndex + 1;
    if (next >= questions.length) {
      setPhase('ready'); // back to overview — can generate report
    } else {
      setQIndex(next);
      setPhase('speaking');
      if (questions[next]) speakQuestion(questions[next]);
    }
  }, [qIndex, questions, tts, stt, speakQuestion]);

  const handleGenerateReport = useCallback(async () => {
    setPhase('reporting');
    try {
      const r = await generateReadinessReport(debateId, openrouterKey, mode);
      setReport(r);
      setPhase('report');
      if (!isMuted && tts.isSupported) {
        const score = Math.round(r.overall_readiness ?? 0);
        tts.speak(
          `Your defense readiness report is ready. Overall score: ${score} percent. ${
            score >= 70 ? 'You appear ready for your defense.' : 'You have some areas to improve before the defense.'
          }`,
          'advisor'
        );
      }
    } catch (e: any) {
      setError(e.message || 'Report generation failed');
      setPhase('error');
    }
  }, [debateId, openrouterKey, mode, isMuted, tts]);

  // ── Phase renders ─────────────────────────────────────────────────────

  /* SETUP */
  if (phase === 'setup') {
    const hasPriorData = questions.length > 0;
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <h2 className={styles.title}>🎤 Voice Defense Room</h2>
          <p className={styles.subtitle}>
            Speak your answers aloud. AI committee members ask questions via voice, evaluate your responses, and generate a readiness report.
          </p>
        </div>

        {!openrouterKey && (
          <div className={styles.keyWarning}>
            <span>🔑</span>
            <div>
              <strong>API Key Required</strong>
              <p>Add your OpenRouter key in <a href="/settings">Settings</a> first.</p>
            </div>
          </div>
        )}

        {!stt.isSupported && (
          <div className={styles.warning}>
            <span>⚠️</span>
            <p>Your browser doesn't support speech recognition. Use Chrome or Edge for voice input. You can still type your answers.</p>
          </div>
        )}

        {!tts.isSupported && (
          <div className={styles.warning}>
            <span>⚠️</span>
            <p>Text-to-speech is not available in this browser. Questions will appear as text only.</p>
          </div>
        )}

        <div className={styles.modeRow}>
          {(['light', 'medium', 'heavy'] as ReasoningMode[]).map(m => (
            <button
              key={m}
              className={`${styles.modeBtn} ${mode === m ? styles.modeBtnActive : ''}`}
              onClick={() => setMode(m)}
            >
              <span className={styles.modeBtnLabel}>{m.charAt(0).toUpperCase() + m.slice(1)}</span>
              <span className={styles.modeBtnCost}>
                {m === 'light' ? '~$0.01–0.05' : m === 'medium' ? '~$0.10–0.40' : '~$1–5'}
              </span>
            </button>
          ))}
        </div>

        <div className={styles.optionRow}>
          <label className={styles.optionLabel}>
            <input
              type="checkbox"
              checked={isMuted}
              onChange={e => setIsMuted(e.target.checked)}
            />
            Mute AI voice (text only)
          </label>
          <label className={styles.optionLabel}>
            <input
              type="checkbox"
              checked={autoSubmit}
              onChange={e => setAutoSubmit(e.target.checked)}
            />
            Auto-submit after silence
          </label>
        </div>

        <div className={styles.actionRow}>
          {hasPriorData ? (
            <>
              <button
                className={styles.primaryBtn}
                onClick={handleBeginDefense}
                disabled={!openrouterKey}
              >
                Resume Defense ({questions.length} questions)
              </button>
              <button className={styles.secondaryBtn} onClick={handleStart} disabled={!openrouterKey}>
                Re-analyse Research
              </button>
            </>
          ) : (
            <button
              className={styles.primaryBtn}
              onClick={handleStart}
              disabled={!openrouterKey}
              style={{ fontSize: '1rem', padding: '12px 28px' }}
            >
              Analyse & Start Voice Defense
            </button>
          )}
        </div>
      </div>
    );
  }

  /* LOADING */
  if (phase === 'loading') {
    return (
      <div className={styles.container}>
        <div className={styles.loadingBox}>
          <div className={styles.spinner} />
          <h3 className={styles.loadingTitle}>Preparing your defense committee…</h3>
          <div className={styles.loadingSteps}>
            {loadingSteps.map((s, i) => (
              <div key={i} className={`${styles.loadingStep} ${s.done ? styles.stepDone : ''}`}>
                <span className={styles.stepIcon}>{s.done ? '✅' : '⏳'}</span>
                <span>{s.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  /* REPORTING */
  if (phase === 'reporting') {
    return (
      <div className={styles.container}>
        <div className={styles.loadingBox}>
          <div className={styles.spinner} />
          <h3 className={styles.loadingTitle}>Generating your readiness report…</h3>
          <p className={styles.loadingHint}>Analysing all your answers across 5 dimensions.</p>
        </div>
      </div>
    );
  }

  /* EVALUATING */
  if (phase === 'evaluating') {
    return (
      <div className={styles.container}>
        <div className={styles.loadingBox}>
          <div className={styles.spinner} />
          <h3 className={styles.loadingTitle}>Evaluating your answer…</h3>
          <p className={styles.loadingHint}>Scoring across 6 dimensions.</p>
        </div>
      </div>
    );
  }

  /* ERROR */
  if (phase === 'error') {
    return (
      <div className={styles.container}>
        <div className={styles.errorBox}>
          <h3>Something went wrong</h3>
          <p>{error}</p>
          {error.toLowerCase().includes('key') && (
            <a href="/settings" className={styles.settingsLink}>🔑 Go to Settings</a>
          )}
          <button className={styles.secondaryBtn} onClick={() => { setError(''); setPhase('setup'); }}>
            Back to Setup
          </button>
        </div>
      </div>
    );
  }

  /* READY — overview with committee + questions */
  if (phase === 'ready') {
    const overall = report?.overall_readiness;
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <div className={styles.headerRow}>
            <h2 className={styles.title}>🎓 Defense Committee Ready</h2>
            {answeredCount > 0 && (
              <span className={styles.progressBadge}>{answeredCount} / {questions.length} answered</span>
            )}
          </div>
        </div>

        {/* Committee row */}
        {personas.length > 0 && (
          <div className={styles.committeeRow}>
            {personas.map((p, i) => (
              <div key={i} className={styles.committeeCard}>
                <div className={styles.committeeEmoji}>{personaEmoji(p.role)}</div>
                <div className={styles.committeeName}>{p.name}</div>
                <div className={styles.committeeRole}>{p.role}</div>
              </div>
            ))}
          </div>
        )}

        {/* Question list */}
        <div className={styles.qList}>
          {questions.map((q, i) => (
            <button
              key={q.question_id}
              className={styles.qListRow}
              onClick={() => { setQIndex(i); setEvaluation(null); setPhase('speaking'); if (q) speakQuestion(q); }}
            >
              <span className={styles.qNum}>Q{i + 1}</span>
              <span className={styles.qPersona}>{personaEmoji(q.persona)}</span>
              <span className={styles.qRowText}>{q.question_text}</span>
              <span
                className={styles.qDiff}
                style={{ color: DIFF_COLOR[q.difficulty?.toLowerCase()] ?? '#aaa' }}
              >
                {q.difficulty}
              </span>
            </button>
          ))}
        </div>

        <div className={styles.actionRow}>
          <button className={styles.primaryBtn} onClick={handleBeginDefense}>
            Start Voice Defense
          </button>
          {answeredCount > 0 && (
            <button className={styles.reportBtn} onClick={handleGenerateReport}>
              Generate Readiness Report
            </button>
          )}
        </div>
      </div>
    );
  }

  /* SPEAKING — committee member speaking question via TTS */
  if (phase === 'speaking' && currentQuestion) {
    const emoji = personaEmoji(currentQuestion.persona);
    return (
      <div className={styles.container}>
        <div className={styles.qCounterRow}>
          <span>Question {qIndex + 1} of {questions.length}</span>
          <button className={styles.muteBtn} onClick={() => setIsMuted(m => !m)} title="Toggle mute">
            {isMuted ? '🔇' : '🔊'}
          </button>
        </div>

        <div className={styles.speakingCard}>
          <div className={`${styles.personaBubble} ${tts.isSpeaking ? styles.pulsing : ''}`}>
            <span className={styles.bigEmoji}>{emoji}</span>
          </div>
          {tts.isSpeaking && (
            <div className={styles.soundBars}>
              {[0,1,2,3,4].map(i => (
                <div key={i} className={styles.bar} style={{ animationDelay: `${i * 0.12}s` }} />
              ))}
            </div>
          )}
          <div className={styles.speakingRole}>{currentQuestion.persona}</div>
          <p className={styles.questionText}>{currentQuestion.question_text}</p>
          <div className={styles.qMeta}>
            <span className={styles.qCat}>{currentQuestion.category}</span>
            <span
              className={styles.qDiff}
              style={{ color: DIFF_COLOR[currentQuestion.difficulty?.toLowerCase()] ?? '#aaa' }}
            >
              {currentQuestion.difficulty}
            </span>
          </div>
        </div>

        <div className={styles.actionRow}>
          <button
            className={styles.listenBtn}
            onClick={handleStartListening}
          >
            🎙 Speak my Answer
          </button>
          <button className={styles.secondaryBtn} onClick={() => setPhase('ready')}>
            Back to Overview
          </button>
        </div>
      </div>
    );
  }

  /* LISTENING — student speaking */
  if (phase === 'listening') {
    const hasText = (stt.finalTranscript + stt.interimTranscript).trim().length > 0;
    return (
      <div className={styles.container}>
        <div className={styles.qCounterRow}>
          <span>Your Answer — Q{qIndex + 1}</span>
          <button className={styles.muteBtn} onClick={() => setIsMuted(m => !m)}>{isMuted ? '🔇' : '🔊'}</button>
        </div>

        {currentQuestion && (
          <div className={styles.questionBanner}>
            <span className={styles.questionBannerLabel}>{personaEmoji(currentQuestion.persona)} {currentQuestion.persona}:</span>
            <p>{currentQuestion.question_text}</p>
          </div>
        )}

        <div className={styles.listeningBox}>
          <div className={`${styles.micCircle} ${stt.isListening ? styles.micActive : ''}`}>
            <span className={styles.micIcon}>🎙</span>
          </div>
          {stt.isListening && (
            <div className={styles.micBars}>
              {[0,1,2,3,4,5,6].map(i => (
                <div key={i} className={styles.micBar} style={{ animationDelay: `${i * 0.1}s` }} />
              ))}
            </div>
          )}
          <p className={styles.listenLabel}>
            {stt.isListening ? 'Listening… speak your answer' : 'Click the microphone to start'}
          </p>
        </div>

        {/* Live transcript */}
        {hasText && (
          <div className={styles.transcriptBox}>
            <span className={styles.transcriptFinal}>{stt.finalTranscript}</span>
            <span className={styles.transcriptInterim}> {stt.interimTranscript}</span>
          </div>
        )}

        {stt.error && <div className={styles.sttError}>{stt.error}</div>}

        <div className={styles.actionRow}>
          {stt.isListening ? (
            <button className={styles.stopBtn} onClick={handleStopListening}>
              ⏹ Stop & Review
            </button>
          ) : (
            <button className={styles.listenBtn} onClick={handleStartListening}>
              🎙 Start Speaking
            </button>
          )}
          {hasText && !stt.isListening && (
            <button
              className={styles.primaryBtn}
              onClick={() => { setEditText((stt.finalTranscript + ' ' + stt.interimTranscript).trim()); setPhase('confirming'); }}
            >
              Review Answer →
            </button>
          )}
          <button className={styles.secondaryBtn} onClick={() => { stt.stopListening(); setPhase('speaking'); }}>
            Re-read Question
          </button>
        </div>
      </div>
    );
  }

  /* CONFIRMING — review transcript, allow edits */
  if (phase === 'confirming') {
    return (
      <div className={styles.container}>
        <div className={styles.qCounterRow}>
          <span>Review Your Answer — Q{qIndex + 1}</span>
        </div>

        {currentQuestion && (
          <div className={styles.questionBanner}>
            <span className={styles.questionBannerLabel}>{personaEmoji(currentQuestion.persona)} {currentQuestion.persona}:</span>
            <p>{currentQuestion.question_text}</p>
          </div>
        )}

        <div className={styles.confirmBox}>
          <label className={styles.confirmLabel}>
            Your answer (edit if needed):
          </label>
          <textarea
            className={styles.confirmTextarea}
            value={editText}
            onChange={e => setEditText(e.target.value)}
            rows={6}
          />
          <div className={styles.wordCount}>
            {editText.trim().split(/\s+/).filter(Boolean).length} words
          </div>
        </div>

        <div className={styles.actionRow}>
          <button
            className={styles.primaryBtn}
            onClick={handleSubmitAnswer}
            disabled={editText.trim().length < 10}
          >
            Submit for Evaluation
          </button>
          <button className={styles.secondaryBtn} onClick={handleStartListening}>
            🎙 Re-record
          </button>
          <button className={styles.secondaryBtn} onClick={() => setPhase('speaking')}>
            Re-read Question
          </button>
        </div>
      </div>
    );
  }

  /* RESULT — show evaluation */
  if (phase === 'result' && evaluation && currentQuestion) {
    const score      = Math.round(evaluation.overall_score * 10) / 10;
    const scoreColor = score >= 7 ? '#4ade80' : score >= 5 ? '#f5a623' : '#ff6b6b';
    const hasFollowUp = evaluation.follow_up_needed && !!evaluation.follow_up_question;
    const isLast     = qIndex + 1 >= questions.length;

    return (
      <div className={styles.container}>
        <div className={styles.evalCard}>
          <div className={styles.evalHeader}>
            <div className={styles.bigScore} style={{ color: scoreColor }}>
              {score}<small>/10</small>
            </div>
            <div>
              <div className={styles.evalTitle}>Answer Evaluation</div>
              <div className={styles.evalQuestion}>{currentQuestion.question_text}</div>
            </div>
          </div>

          <div className={styles.scoresGrid}>
            <ScoreBar label="Relevance"         value={(evaluation as any).score_relevance         ?? 0} />
            <ScoreBar label="Evidence Support"  value={(evaluation as any).score_evidence           ?? 0} />
            <ScoreBar label="Clarity"           value={(evaluation as any).score_clarity            ?? 0} />
            <ScoreBar label="Completeness"      value={(evaluation as any).score_completeness       ?? 0} />
            <ScoreBar label="Methodology"       value={(evaluation as any).score_methodology        ?? 0} />
            <ScoreBar label="Critical Thinking" value={(evaluation as any).score_critical_thinking  ?? 0} />
          </div>

          <div className={styles.feedbackGrid}>
            <div className={styles.strengthCard}>
              <h4>💪 Strength</h4>
              <p>{evaluation.strength}</p>
            </div>
            <div className={styles.weaknessCard}>
              <h4>⚠️ Weakness</h4>
              <p>{evaluation.weakness}</p>
            </div>
          </div>

          {evaluation.suggested_improvement && (
            <div className={styles.improvementBox}>
              <h4>💡 Suggested Improvement</h4>
              <p>{evaluation.suggested_improvement}</p>
            </div>
          )}

          {hasFollowUp && (
            <div className={styles.followUpBox}>
              <h4>🔄 Follow-up Question</h4>
              <p>{evaluation.follow_up_question}</p>
            </div>
          )}
        </div>

        <div className={styles.actionRow}>
          {hasFollowUp && (
            <button className={styles.followUpBtn} onClick={handleFollowUp}>
              🎙 Answer Follow-up
            </button>
          )}
          {!isLast ? (
            <button className={styles.primaryBtn} onClick={handleNextQuestion}>
              Next Question →
            </button>
          ) : (
            <button className={styles.reportBtn} onClick={handleGenerateReport}>
              📊 Generate Readiness Report
            </button>
          )}
          <button className={styles.secondaryBtn} onClick={() => setPhase('ready')}>
            Back to Overview
          </button>
        </div>
      </div>
    );
  }

  /* FOLLOW_UP speaking */
  if (phase === 'follow_up') {
    return (
      <div className={styles.container}>
        <div className={styles.loadingBox}>
          <div className={`${styles.personaBubble} ${styles.pulsing}`} style={{ marginBottom: 16 }}>
            <span className={styles.bigEmoji}>{currentQuestion ? personaEmoji(currentQuestion.persona) : '🎓'}</span>
          </div>
          <div className={styles.soundBars}>
            {[0,1,2,3,4].map(i => (
              <div key={i} className={styles.bar} style={{ animationDelay: `${i * 0.12}s` }} />
            ))}
          </div>
          <p className={styles.loadingHint}>Asking follow-up question…</p>
          {evaluation?.follow_up_question && (
            <p className={styles.followUpText}>{evaluation.follow_up_question}</p>
          )}
        </div>
      </div>
    );
  }

  /* REPORT */
  if (phase === 'report' && report) {
    const overall   = report.overall_readiness ?? 0;
    const color     = overall >= 70 ? '#4ade80' : overall >= 50 ? '#f5a623' : '#ff6b6b';
    const label     = overall >= 70 ? 'Ready for Defense' : overall >= 50 ? 'More Practice Recommended' : 'Significant Gaps Found';

    return (
      <div className={styles.container}>
        <div className={styles.reportHeader}>
          <div className={styles.reportBigScore} style={{ color }}>
            {Math.round(overall)}%
          </div>
          <div>
            <h2 className={styles.reportTitle}>Defense Readiness Report</h2>
            <p className={styles.readinessLabel} style={{ color }}>{label}</p>
          </div>
        </div>

        <div className={styles.dimGrid}>
          {[
            ['Research Clarity', report.research_clarity],
            ['Methodology',      report.methodology_score],
            ['Evidence',         report.evidence_score],
            ['Critical Thinking',report.critical_thinking],
            ['Communication',    report.communication],
          ].map(([lbl, val]) => {
            const v = (val as number) ?? 0;
            const c = v >= 70 ? '#4ade80' : v >= 50 ? '#f5a623' : '#ff6b6b';
            return (
              <div key={lbl as string} className={styles.dimCard}>
                <div className={styles.dimScore} style={{ color: c }}>{Math.round(v)}%</div>
                <div className={styles.dimLabel}>{lbl as string}</div>
                <div className={styles.dimBarTrack}>
                  <div style={{ width: `${v}%`, background: c, height: '100%', borderRadius: 2 }} />
                </div>
              </div>
            );
          })}
        </div>

        {(report.improvement_plan?.length ?? 0) > 0 && (
          <div className={styles.section}>
            <div className={styles.sectionTitle}>Improvement Plan</div>
            <ol className={styles.planList}>
              {(report.improvement_plan ?? []).map((item: any, i: number) => (
                <li key={i}>{typeof item === 'string' ? item : JSON.stringify(item)}</li>
              ))}
            </ol>
          </div>
        )}

        {(report.likely_questions?.length ?? 0) > 0 && (
          <div className={styles.section}>
            <div className={styles.sectionTitle}>Likely Committee Questions</div>
            <ul className={styles.likelyList}>
              {(report.likely_questions ?? []).map((q: string, i: number) => (
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
          <button className={styles.primaryBtn} onClick={() => { setPhase('ready'); tts.cancel(); }}>
            Practice Again
          </button>
          <button className={styles.secondaryBtn} onClick={() => { setPhase('setup'); setQuestions([]); setPersonas([]); setReport(null); setAnsweredCount(0); tts.cancel(); }}>
            New Session
          </button>
        </div>
      </div>
    );
  }

  return null;
}
