import { useState } from 'react';
import styles from './SetupSteps.module.css';

interface BasicInfoStepProps {
  title: string;
  problemStatement: string;
  agenda: string[];
  desiredOutcomes: string[];
  timeboxMinutes?: number;
  onTitleChange: (value: string) => void;
  onProblemChange: (value: string) => void;
  onAgendaChange: (value: string[]) => void;
  onDesiredOutcomesChange: (value: string[]) => void;
  onTimeboxChange: (value: number | undefined) => void;
  isLoading: boolean;
}

export function BasicInfoStep({
  title,
  problemStatement,
  agenda,
  desiredOutcomes,
  timeboxMinutes,
  onTitleChange,
  onProblemChange,
  onAgendaChange,
  onDesiredOutcomesChange,
  onTimeboxChange,
  isLoading,
}: BasicInfoStepProps) {
  const [agendaInput, setAgendaInput] = useState('');
  const [outcomeInput, setOutcomeInput] = useState('');

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

      <label>Problem Statement *</label>
      <textarea
        value={problemStatement}
        onChange={(e) => onProblemChange(e.target.value)}
        placeholder="What question or problem should the group discuss?"
        rows={3}
        disabled={isLoading}
      />

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

      <label>Meeting Duration (minutes, optional)</label>
      <input
        type="number"
        value={timeboxMinutes || ''}
        onChange={(e) => onTimeboxChange(e.target.value ? parseInt(e.target.value) : undefined)}
        placeholder="30"
        disabled={isLoading}
        min="5"
        max="240"
      />
    </div>
  );
}
