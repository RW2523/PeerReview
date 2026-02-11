/**
 * Hook for debate setup actions (create, launch)
 * Extracted from setup/page.tsx for maintainability
 */
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import * as api from '@/lib/api';
import type { SetupParticipant, SetupMaterial } from '@/lib/api';

interface UseDebateSetupActionsOptions {
  workspaceId: string;
  title: string;
  problemStatement: string;
  agenda?: string[];
  desiredOutcomes?: string[];
  timeboxMinutes?: number;
  participants: SetupParticipant[];
  materials: SetupMaterial[];
  selectedMemorySources: string[];
}

interface UseDebateSetupActionsReturn {
  isLoading: boolean;
  createdDebateId: string | null;
  createdParticipantIds: string[];
  handleCreateDebate: () => Promise<{ debateId: string; participantIds: string[] } | null>;
  handleLaunchDebate: (debateId: string, apiKey: string | null) => Promise<void>;
}

export function useDebateSetupActions(
  options: UseDebateSetupActionsOptions
): UseDebateSetupActionsReturn {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [createdDebateId, setCreatedDebateId] = useState<string | null>(null);
  const [createdParticipantIds, setCreatedParticipantIds] = useState<string[]>([]);

  const handleCreateDebate = async () => {
    const {
      workspaceId,
      title,
      problemStatement,
      agenda,
      desiredOutcomes,
      timeboxMinutes,
      participants,
      materials,
      selectedMemorySources,
    } = options;

    if (participants.length === 0) {
      alert('At least 1 participant required');
      return null;
    }

    setIsLoading(true);
    try {
      // 1. Create debate (returns participant_ids)
      const setupResponse = await api.setupDebate({
        workspace_id: workspaceId,
        title,
        problem_statement: problemStatement,
        agenda: agenda && agenda.length > 0 ? agenda : undefined,
        desired_outcomes: desiredOutcomes && desiredOutcomes.length > 0 ? desiredOutcomes : undefined,
        timebox_minutes: timeboxMinutes || 30,
        participants,
        materials: materials && materials.length > 0 ? materials : undefined,
      });

      const { debate_id, participant_ids } = setupResponse;
      setCreatedDebateId(debate_id);
      setCreatedParticipantIds(participant_ids);

      // 2. Import memory if selected
      if (selectedMemorySources && selectedMemorySources.length > 0) {
        try {
          await api.importMemory(debate_id, {
            source_debate_ids: selectedMemorySources,
            participant_ids: participant_ids,
          });
          console.log('Memory imported successfully');
        } catch (memErr: any) {
          console.error('Memory import failed:', memErr);
          alert(`Warning: Memory import failed: ${memErr.message}. Continuing with debate creation.`);
        }
      }

      return { debateId: debate_id, participantIds: participant_ids };
    } catch (err: any) {
      alert(`Failed to create debate: ${err.message}`);
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  const handleLaunchDebate = async (debateId: string, apiKey: string | null) => {
    // Validate API key before launching
    if (!apiKey) {
      alert(
        '⚠️ OpenRouter API Key Required\n\nYou need to add your OpenRouter API key in Settings before starting the debate.\n\nThe AI agents need this key to participate in the discussion.'
      );
      return;
    }

    if (!debateId) {
      alert('No debate created yet. Please complete the setup first.');
      return;
    }

    setIsLoading(true);

    try {
      // Start the debate (pending -> running)
      await api.startDebate(debateId);

      // Trigger first agent turn immediately
      await api.triggerNextTurn(debateId, apiKey);

      // Navigate to room
      router.push(`/room?debate_id=${debateId}`);
    } catch (err: any) {
      console.error('Failed to start debate:', err);
      alert(`Failed to start debate: ${err.message || 'Unknown error'}`);
    } finally {
      setIsLoading(false);
    }
  };

  return {
    isLoading,
    createdDebateId,
    createdParticipantIds,
    handleCreateDebate,
    handleLaunchDebate,
  };
}
