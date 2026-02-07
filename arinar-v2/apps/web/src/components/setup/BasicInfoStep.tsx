import styles from './SetupSteps.module.css';

interface BasicInfoStepProps {
  title: string;
  problemStatement: string;
  timeboxMinutes?: number;
  onTitleChange: (value: string) => void;
  onProblemChange: (value: string) => void;
  onTimeboxChange: (value: number | undefined) => void;
  isLoading: boolean;
}

export function BasicInfoStep({
  title,
  problemStatement,
  timeboxMinutes,
  onTitleChange,
  onProblemChange,
  onTimeboxChange,
  isLoading,
}: BasicInfoStepProps) {
  return (
    <div className={styles.section}>
      <h2>Basic Information</h2>
      
      <label>Meeting Title</label>
      <input
        type="text"
        value={title}
        onChange={(e) => onTitleChange(e.target.value)}
        placeholder="e.g., Q1 Feature Planning"
        disabled={isLoading}
      />

      <label>Problem Statement</label>
      <textarea
        value={problemStatement}
        onChange={(e) => onProblemChange(e.target.value)}
        placeholder="What question or problem should the group discuss?"
        rows={4}
        disabled={isLoading}
      />

      <label>Timebox (minutes, optional)</label>
      <input
        type="number"
        value={timeboxMinutes || ''}
        onChange={(e) => onTimeboxChange(e.target.value ? parseInt(e.target.value) : undefined)}
        placeholder="30"
        disabled={isLoading}
      />
    </div>
  );
}
