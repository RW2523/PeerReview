import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useOpenRouterKey } from '@/hooks/useOpenRouterKey';
import * as api from '@/lib/api';
import styles from './SetupSteps.module.css';

interface BasicInfoStepProps {
  title: string;
  problemStatement: string;
  agenda: string[];
  desiredOutcomes: string[];
  timeboxMinutes?: number;
  maxRounds?: number;
  onTitleChange: (value: string) => void;
  onProblemChange: (value: string) => void;
  onAgendaChange: (value: string[]) => void;
  onDesiredOutcomesChange: (value: string[]) => void;
  onTimeboxChange: (value: number | undefined) => void;
  onMaxRoundsChange: (value: number | undefined) => void;
  isLoading: boolean;
}

export function BasicInfoStep({
  title,
  problemStatement,
  agenda,
  desiredOutcomes,
  timeboxMinutes,
  maxRounds,
  onTitleChange,
  onProblemChange,
  onAgendaChange,
  onDesiredOutcomesChange,
  onTimeboxChange,
  onMaxRoundsChange,
  isLoading,
}: BasicInfoStepProps) {
  const router = useRouter();
  const { apiKey } = useOpenRouterKey();
  const [agendaInput, setAgendaInput] = useState('');
  const [outcomeInput, setOutcomeInput] = useState('');
  const [meetingType, setMeetingType] = useState<'rounds' | 'time'>(maxRounds ? 'rounds' : 'time');
  const [isGenerating, setIsGenerating] = useState(false);
  const [showKeyPoints, setShowKeyPoints] = useState(false);
  const [keyPoints, setKeyPoints] = useState<string[]>([]);

  const handleAddAgendaItem = () => {
    if (agendaInput.trim()) {
      onAgendaChange([...agenda, agendaInput.trim()]);
      setAgendaInput('');
    }
  };

  const handleRemoveAgendaItem = (index: number) => {
    onAgendaChange(agenda.filter((_, i) => i !== index));
  };

  const handleAddOutcome = () => {
    if (outcomeInput.trim()) {
      onDesiredOutcomesChange([...desiredOutcomes, outcomeInput.trim()]);
      setOutcomeInput('');
    }
  };

  const handleRemoveOutcome = (index: number) => {
    onDesiredOutcomesChange(desiredOutcomes.filter((_, i) => i !== index));
  };

  const handleImproveProblemStatement = async () => {
    if (!apiKey) {
      router.push('/settings');
      return;
    }

    if (!problemStatement || problemStatement.trim().length < 10) {
      alert('Please enter at least a brief problem statement (10+ characters) to improve');
      return;
    }

    setIsGenerating(true);
    try {
      const result = await api.improveProblemStatement(problemStatement, apiKey);
      
      // Update problem statement
      onProblemChange(result.improved_text);
      
      // Update key points
      setKeyPoints(result.key_points);
      if (result.key_points.length > 0) {
        setShowKeyPoints(true);
      }
      
      // Update agenda items if provided
      if (result.agenda_items && result.agenda_items.length > 0) {
        onAgendaChange(result.agenda_items);
      }
      
      // Update desired outcomes if provided
      if (result.desired_outcomes && result.desired_outcomes.length > 0) {
        onDesiredOutcomesChange(result.desired_outcomes);
      }
      
    } catch (err) {
      console.error('Failed to improve problem statement:', err);
      const errorMsg = err instanceof Error ? err.message : 'Failed to improve problem statement';
      alert(errorMsg);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className={styles.section}>
      <h2>Meeting Details</h2>
      
      <label>Meeting Title *</label>
      <input
        type="text"
        value={title}
        onChange={(e) => onTitleChange(e.target.value)}
        placeholder="e.g., Q1 Feature Planning"
        disabled={isLoading}
      />

      <label>
        Problem Statement *
        <button
          type="button"
          onClick={handleImproveProblemStatement}
          disabled={isLoading || isGenerating || !problemStatement.trim()}
          className={styles.generateButton}
          title="Use AI to improve this problem statement"
        >
          {isGenerating ? '⏳' : '✨'} {isGenerating ? 'Generating...' : 'Improve with AI'}
        </button>
      </label>
      <textarea
        value={problemStatement}
        onChange={(e) => onProblemChange(e.target.value)}
        placeholder="What question or problem should the group discuss?"
        rows={4}
        disabled={isLoading || isGenerating}
      />
      {showKeyPoints && keyPoints.length > 0 && (
        <div className={styles.keyPoints}>
          <div className={styles.keyPointsHeader}>
            <strong>📌 Key Discussion Points:</strong>
            <button
              type="button"
              onClick={() => setShowKeyPoints(false)}
              className={styles.closeButton}
            >
              ✕
            </button>
          </div>
          <ul>
            {keyPoints.map((point, idx) => (
              <li key={idx}>{point}</li>
            ))}
          </ul>
        </div>
      )}

      <label>Meeting Agenda (optional)</label>
      <div className={styles.listInput}>
        <input
          type="text"
          value={agendaInput}
          onChange={(e) => setAgendaInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              handleAddAgendaItem();
            }
          }}
          placeholder="Add agenda item and press Enter"
          disabled={isLoading}
        />
        <button 
          type="button" 
          onClick={handleAddAgendaItem}
          disabled={!agendaInput.trim() || isLoading}
          className={styles.addButton}
        >
          + Add
        </button>
      </div>
      {agenda.length > 0 && (
        <ul className={styles.itemList}>
          {agenda.map((item, index) => (
            <li key={index}>
              <span>{item}</span>
              <button 
                type="button"
                onClick={() => handleRemoveAgendaItem(index)}
                className={styles.removeButton}
                disabled={isLoading}
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}

      <label>Desired Outcomes (optional)</label>
      <div className={styles.listInput}>
        <input
          type="text"
          value={outcomeInput}
          onChange={(e) => setOutcomeInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              handleAddOutcome();
            }
          }}
          placeholder="Add desired outcome and press Enter"
          disabled={isLoading}
        />
        <button 
          type="button" 
          onClick={handleAddOutcome}
          disabled={!outcomeInput.trim() || isLoading}
          className={styles.addButton}
        >
          + Add
        </button>
      </div>
      {desiredOutcomes.length > 0 && (
        <ul className={styles.itemList}>
          {desiredOutcomes.map((item, index) => (
            <li key={index}>
              <span>{item}</span>
              <button 
                type="button"
                onClick={() => handleRemoveOutcome(index)}
                className={styles.removeButton}
                disabled={isLoading}
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}

      <label>Meeting Limit</label>
      <div className={styles.radioGroup}>
        <label className={styles.radioLabel}>
          <input
            type="radio"
            checked={meetingType === 'rounds'}
            onChange={() => {
              setMeetingType('rounds');
              onTimeboxChange(undefined);
              onMaxRoundsChange(3); // default to 3 rounds
            }}
            disabled={isLoading}
          />
          <span>Rounds-based (each participant speaks once per round)</span>
        </label>
        <label className={styles.radioLabel}>
          <input
            type="radio"
            checked={meetingType === 'time'}
            onChange={() => {
              setMeetingType('time');
              onMaxRoundsChange(undefined);
              onTimeboxChange(30); // default to 30 minutes
            }}
            disabled={isLoading}
          />
          <span>Time-based (unlimited rounds within time limit)</span>
        </label>
      </div>

      {meetingType === 'rounds' && (
        <>
          <label>Number of Rounds *</label>
          <input
            type="number"
            value={maxRounds || ''}
            onChange={(e) => onMaxRoundsChange(e.target.value ? parseInt(e.target.value) : undefined)}
            placeholder="3"
            disabled={isLoading}
            min="1"
            max="10"
          />
          <p className={styles.helpText}>
            Example: With 5 agents and 3 rounds, each agent will speak 3 times (15 total turns)
          </p>
        </>
      )}

      {meetingType === 'time' && (
        <>
          <label>Meeting Duration (minutes) *</label>
          <input
            type="number"
            value={timeboxMinutes || ''}
            onChange={(e) => onTimeboxChange(e.target.value ? parseInt(e.target.value) : undefined)}
            placeholder="30"
            disabled={isLoading}
            min="5"
            max="240"
          />
        </>
      )}
    </div>
  );
}
