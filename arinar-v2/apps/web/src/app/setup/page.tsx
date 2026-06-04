'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import AppNav from '@/components/layout/AppNav';
import * as api from '@/lib/api';
import { BasicInfoStep } from '@/components/setup/BasicInfoStep';
import { MaterialsStep } from '@/components/setup/MaterialsStep';
import { ParticipantsStep } from '@/components/setup/ParticipantsStep';
import { MemoryImportStep } from '@/components/setup/MemoryImportStep';
import { PreflightStep } from '@/components/setup/PreflightStep';
import { LiteratureStep } from '@/components/setup/LiteratureStep';
import { ReviewStep } from '@/components/setup/ReviewStep';
import { SetupStepper } from '@/components/setup/SetupStepper';
import { useMemoryImport } from '@/hooks/useMemoryImport';
import { useSetupValidation } from '@/hooks/useSetupValidation';
import { useParticipants } from '@/hooks/useParticipants';
import { useMaterials } from '@/hooks/useMaterials';
import { useOpenRouterKey } from '@/hooks/useOpenRouterKey';
import { useDebateSetupActions } from '@/hooks/useDebateSetupActions';
import styles from './setup.module.css';

export default function SetupPage() {
  const router = useRouter();
  const { apiKey } = useOpenRouterKey();
  const [step, setStep] = useState(1);
  const [canEnterRoom, setCanEnterRoom] = useState(false);
  const [participantIds, setParticipantIds] = useState<string[]>([]);
  
  // Step 1: Basic Info
  const [title, setTitle] = useState('');
  const [problemStatement, setProblemStatement] = useState('');
  const [agenda, setAgenda] = useState<string[]>([]);
  const [desiredOutcomes, setDesiredOutcomes] = useState<string[]>([]);
  const [timeboxMinutes, setTimeboxMinutes] = useState<number | undefined>(30);
  const [maxRounds, setMaxRounds] = useState<number | undefined>(undefined);
  
  // YOLO Mode Configuration
  const [yoloMode, setYoloMode] = useState(false);
  const [autoTurnDelay, setAutoTurnDelay] = useState(10);
  
  // Reasoning Mode
  const [reasoningMode, setReasoningMode] = useState<api.ReasoningMode>('medium');

  // Host Configuration
  const [enableHost, setEnableHost] = useState(false);
  const [hostModelId, setHostModelId] = useState('openai/gpt-4o-mini');
  
  // Document Configuration
  const [enableDocuments, setEnableDocuments] = useState(false);
  const [documentTemplateId, setDocumentTemplateId] = useState('meeting-summary');
  const [documentTitle, setDocumentTitle] = useState('');

  // Pre-fill from draft if coming from home page
  useEffect(() => {
    const draft = sessionStorage.getItem('debate_draft');
    if (draft) {
      try {
        const data = JSON.parse(draft);
        setTitle(data.title || '');
        setProblemStatement(data.problemStatement || '');
        sessionStorage.removeItem('debate_draft');
      } catch (e) {
        console.error('Failed to parse debate draft:', e);
      }
    }
  }, []);
  
  // Step 2: Materials
  const {
    materials,
    handleAdd: handleAddMaterial,
    handleUpdate: handleUpdateMaterial,
    handleRemove: handleRemoveMaterial,
  } = useMaterials();
  const [uploadedFiles, setUploadedFiles] = useState<api.MaterialStatus[]>([]);
  
  // Step 3: Participants
  const {
    participants,
    setParticipants,
    handleAddFromTemplate: handleAddParticipantFromTemplate,
    handleAddExisting: handleAddExistingAgent,
    handleUpdate: handleUpdateParticipant,
    handleRemove: handleRemoveParticipant,
    handleReorder: handleReorderParticipant,
  } = useParticipants();
  const [templates, setTemplates] = useState<api.AgentTemplate[]>([]);
  const [agents, setAgents] = useState<api.Agent[]>([]);
  
  // Step 4: Memory Import
  const { memoryImport, setMemoryImport, validateMemoryImport, createMemoryGrants } = useMemoryImport();
  
  // Validation
  const { canGoNext: validateStep } = useSetupValidation();
  
  const workspaceId = '00000000-0000-0000-0000-000000000101';

  // Debate setup actions (create, launch)
  const {
    isLoading,
    createdDebateId,
    createdParticipantIds,
    setCreatedParticipantIds,
    handleCreateDebate: createDebate,
    handleLaunchDebate,
  } = useDebateSetupActions({
    workspaceId,
    title,
    problemStatement,
    enableDocuments,
    documentTemplateId,
    documentTitle,
    agenda,
    desiredOutcomes,
    timeboxMinutes,
    maxRounds,
    enableHost,
    hostModelId,
    yoloMode,
    autoTurnDelay,
    participants,
    materials,
    selectedMemorySources: memoryImport.source_debate_ids,
    reasoningMode,
  });
  const steps = [
    { id: 1, label: 'Idea & Scope' },
    { id: 2, label: 'Documents' },
    { id: 3, label: 'Reviewers' },
    { id: 4, label: 'Prior Memory' },
    { id: 5, label: 'Literature' },
    { id: 6, label: 'Review & Launch' },
  ];

  useEffect(() => {
    const loadData = async () => {
      try {
        console.log('Loading templates and agents...');
        const [templatesData, agentsData] = await Promise.all([
          api.listAgentTemplates(),
          api.listAgents(workspaceId),
        ]);
        console.log('Templates loaded:', templatesData.length);
        console.log('Agents loaded:', agentsData.length);
        setTemplates(templatesData);
        setAgents(agentsData);
      } catch (err: any) {
        console.error('Failed to load templates/agents:', err);
        alert(`Failed to load templates/agents: ${err.message}`);
      }
    };
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Create debate early (after step 1) to enable file uploads
  const handleCreateDebateEarly = async () => {
    if (createdDebateId) {
      // Debate already exists — reload its materials then proceed
      try {
        const status = await api.getMaterialsStatus(createdDebateId);
        setUploadedFiles(status.materials);
      } catch { /* ignore */ }
      setStep(2);
      return;
    }
    
    const result = await createDebate();
    if (result) {
      setStep(2);
    }
  };

  const handleCreateDebate = async () => {
    // Validate participants exist
    if (participants.length === 0) {
      alert('Please add at least one participant before continuing');
      return;
    }
    
    // Validate memory import
    const memoryError = validateMemoryImport(participants);
    if (memoryError) {
      alert(memoryError);
      return;
    }

    let result;
    
    // If debate already exists (from step 2 file uploads), just add participants
    if (createdDebateId && participantIds.length === 0) {
      try {
        const addResult = await api.addParticipantsToDebate(createdDebateId, participants);
        setParticipantIds(addResult.participant_ids);
        setCreatedParticipantIds(addResult.participant_ids); // Update hook state
        result = { debateId: createdDebateId, participantIds: addResult.participant_ids };
      } catch (err: any) {
        alert(`Failed to add participants: ${err.message}`);
        return;
      }
    } else {
      // Otherwise create debate with participants (or recreate if participants changed)
      result = await createDebate();
      if (result) {
        setParticipantIds(result.participantIds);
      }
    }
    if (result) {
      // Create memory grants if enabled, then advance to Literature step
      const shouldContinue = await createMemoryGrants(result.debateId, result.participantIds);
      if (shouldContinue) {
        setStep(5); // Literature step
      }
    }
  };

  const handleLaunchAfterPreflight = () => {
    if (createdDebateId) {
      handleLaunchDebate(createdDebateId, apiKey);
    }
  };

  const canGoNext = () => validateStep(step, title, problemStatement, participants);

  return (
    <>
      <AppNav />
      <div className={styles.container}>
      <header className={styles.header}>
        <h1>New Review Session</h1>
        <p className={styles.subtitle}>Configure your AI-powered peer review</p>
      </header>

      {!apiKey && (
        <div style={{
          backgroundColor: '#fff3cd',
          border: '1px solid #ffc107',
          borderRadius: '8px',
          padding: '16px 20px',
          marginBottom: '24px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}>
          <span style={{ fontSize: '24px' }}>⚠️</span>
          <div>
            <strong style={{ color: '#856404' }}>OpenRouter API Key Required</strong>
            <p style={{ margin: '4px 0 0 0', color: '#856404', fontSize: '14px' }}>
              Add your OpenRouter API key in <a href="/settings" style={{ color: '#0066cc', textDecoration: 'underline' }}>Settings</a> before launching the review. AI reviewers need this key to participate.
            </p>
          </div>
        </div>
      )}

      <div className={styles.wizard}>
        <SetupStepper steps={steps} currentStep={step} />

        <div className={styles.content}>
          {step === 1 && (
            <BasicInfoStep
              title={title}
              problemStatement={problemStatement}
              agenda={agenda}
              desiredOutcomes={desiredOutcomes}
              timeboxMinutes={timeboxMinutes}
              maxRounds={maxRounds}
              yoloMode={yoloMode}
              autoTurnDelay={autoTurnDelay}
              onTitleChange={setTitle}
              onProblemChange={setProblemStatement}
              onAgendaChange={setAgenda}
              onDesiredOutcomesChange={setDesiredOutcomes}
              onTimeboxChange={setTimeboxMinutes}
              onMaxRoundsChange={setMaxRounds}
              onYoloModeChange={setYoloMode}
              onAutoTurnDelayChange={setAutoTurnDelay}
              isLoading={isLoading}
            />
          )}

          {step === 2 && (
            <MaterialsStep
              debateId={createdDebateId || undefined}
              materials={materials}
              onAdd={handleAddMaterial}
              onUpdate={handleUpdateMaterial}
              onRemove={handleRemoveMaterial}
              uploadedFiles={uploadedFiles}
              onFilesUploaded={(files) => setUploadedFiles(files)}
            />
          )}

          {step === 3 && (
          <>
            <ReasoningModeSelector mode={reasoningMode} onChange={setReasoningMode} />
            <ParticipantsStep
              participants={participants}
              templates={templates}
              agents={agents}
              enableHost={enableHost}
              hostModelId={hostModelId}
              enableDocuments={enableDocuments}
              documentTemplateId={documentTemplateId}
              documentTitle={documentTitle}
              onEnableHostChange={setEnableHost}
              onHostModelChange={setHostModelId}
              onEnableDocumentsChange={setEnableDocuments}
              onDocumentTemplateChange={setDocumentTemplateId}
              onDocumentTitleChange={setDocumentTitle}
              onAddFromTemplate={handleAddParticipantFromTemplate}
              onAddExisting={handleAddExistingAgent}
              onUpdate={handleUpdateParticipant}
              onRemove={handleRemoveParticipant}
              onReorder={handleReorderParticipant}
            />
          </>
          )}

          {step === 4 && (
            <MemoryImportStep
              workspaceId={workspaceId}
              participants={participants}
              memoryImport={memoryImport}
              onUpdate={setMemoryImport}
            />
          )}

          {step === 5 && (
            <LiteratureStep
              debateId={createdDebateId}
              researchQuestion={problemStatement}
              onCanContinueChange={setCanEnterRoom}
            />
          )}

          {step === 6 && (
            <>
              <PreflightStep
                debateId={createdDebateId}
                participants={participants}
                participantIds={createdParticipantIds}
                onCanContinueChange={setCanEnterRoom}
                meetingTitle={title}
                meetingPurpose={problemStatement}
                meetingAgenda={agenda}
                desiredOutcomes={desiredOutcomes}
              />
              <ReviewStep
                title={title}
                problemStatement={problemStatement}
                timeboxMinutes={timeboxMinutes}
                yoloMode={yoloMode}
                autoTurnDelay={autoTurnDelay}
                materials={materials}
                participants={participants}
                workspaceId={workspaceId}
              />
            </>
          )}
        </div>

        <div className={styles.navigation}>
          {step > 1 && (
            <button 
              onClick={() => {
                if (step === 6) {
                  setStep(5); // Back to Literature from Prepare & Launch
                } else {
                  setStep(step - 1);
                }
              }} 
              disabled={isLoading}
              className={styles.btnPrevious}
            >
              <span className={styles.btnIcon}>←</span>
              <span>Previous</span>
            </button>
          )}
          
          <div style={{ flex: 1 }} />
          
          {step === 1 && (
            <button
              onClick={handleCreateDebateEarly}
              disabled={!canGoNext() || isLoading}
              className={styles.btnNext}
            >
              <span>{isLoading ? 'Creating...' : 'Next'}</span>
              <span className={styles.btnIcon}>→</span>
            </button>
          )}
          
          {step > 1 && step < 4 && (
            <button
              onClick={() => setStep(step + 1)}
              disabled={!canGoNext() || isLoading}
              className={styles.btnNext}
            >
              <span>Next</span>
              <span className={styles.btnIcon}>→</span>
            </button>
          )}
          
          {step === 4 && (
            <button
              onClick={handleCreateDebate}
              disabled={!canGoNext() || isLoading}
              className={styles.btnNext}
            >
              <span>{isLoading ? 'Creating...' : 'Continue to Literature Search'}</span>
              <span className={styles.btnIcon}>→</span>
            </button>
          )}

          {step === 5 && (
            <button
              onClick={() => setStep(6)}
              disabled={isLoading}
              className={styles.btnNext}
            >
              <span>Continue to Prepare &amp; Launch</span>
              <span className={styles.btnIcon}>→</span>
            </button>
          )}
          
          {step === 6 && (
            <button
              onClick={handleLaunchAfterPreflight}
              disabled={isLoading || !canEnterRoom || !apiKey}
              className={styles.btnLaunch}
              title={!apiKey ? 'Add OpenRouter API key in Settings first' : !canEnterRoom ? 'Complete reviewer preparation first' : ''}
            >
              <span className={styles.launchIcon}>🚀</span>
              <span>
                {isLoading ? 'Loading...' : !apiKey ? 'API Key Required' : 'Launch Review'}
              </span>
            </button>
          )}
        </div>
      </div>
      </div>
    </>
  );
}

// ── Reasoning Mode Selector (inline) ──────────────────────────────────────

const MODE_OPTS = [
  { id: 'light'  as api.ReasoningMode, emoji: '⚡', label: 'Light',  hint: 'Fast, low-cost single model', color: '#16a34a' },
  { id: 'medium' as api.ReasoningMode, emoji: '⚖️', label: 'Medium', hint: 'Role-aware balanced models',  color: '#d97706' },
  { id: 'heavy'  as api.ReasoningMode, emoji: '🔥', label: 'Heavy',  hint: 'Frontier models for all',    color: '#dc2626' },
];

function ReasoningModeSelector({
  mode,
  onChange,
}: {
  mode: api.ReasoningMode;
  onChange: (m: api.ReasoningMode) => void;
}) {
  return (
    <div style={{ marginBottom: 24, padding: 16, border: '1px solid #e2e8f0', borderRadius: 12, background: '#fff' }}>
      <h3 style={{ margin: '0 0 6px', fontSize: '0.95rem', fontWeight: 700, color: '#1e293b' }}>
        ⚡ Reasoning Mode
      </h3>
      <p style={{ margin: '0 0 12px', fontSize: '0.8rem', color: '#64748b' }}>
        Controls which AI models power every activity — analysis, agent turns, evaluations, and reports.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
        {MODE_OPTS.map(opt => (
          <button
            key={opt.id}
            onClick={() => onChange(opt.id)}
            style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
              padding: '12px 8px',
              border: `2px solid ${mode === opt.id ? opt.color : '#e2e8f0'}`,
              borderRadius: 10,
              background: mode === opt.id ? `${opt.color}15` : '#f8fafc',
              cursor: 'pointer',
            }}
          >
            <span style={{ fontSize: '1.3rem' }}>{opt.emoji}</span>
            <span style={{ fontWeight: 700, fontSize: '0.85rem', color: '#0f172a' }}>{opt.label}</span>
            <span style={{ fontSize: '0.7rem', color: opt.color }}>{opt.hint}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
