'use client';

import { useState, useEffect } from 'react';
import styles from './AgentBehaviorsPanel.module.css';

interface Coalition {
  id: string;
  members: string[];
  formed_at: string;
  strategy?: string;
}

interface PrivateMessage {
  id: string;
  from: string;
  to: string;
  message: string;
  timestamp: string;
}

interface SubTask {
  id: string;
  agent: string;
  task: string;
  status: 'planning' | 'executing' | 'completed';
  timestamp: string;
}

interface AgentBehaviorsPanelProps {
  debateId: string;
  events: any[];
}

export default function AgentBehaviorsPanel({ debateId, events }: AgentBehaviorsPanelProps) {
  const [coalitions, setCoalitions] = useState<Coalition[]>([]);
  const [privateMessages, setPrivateMessages] = useState<PrivateMessage[]>([]);
  const [subTasks, setSubTasks] = useState<SubTask[]>([]);
  const [activeTab, setActiveTab] = useState<'coalitions' | 'messages' | 'tasks'>('coalitions');

  useEffect(() => {
    // Process events to extract agent behaviors
    const newCoalitions: Coalition[] = [];
    const newMessages: PrivateMessage[] = [];
    const newTasks: SubTask[] = [];

    events.forEach(event => {
      if (event.type === 'coalition_formed') {
        newCoalitions.push({
          id: event.event_id,
          members: event.payload?.members || [],
          formed_at: event.occurred_at,
          strategy: event.payload?.strategy
        });
      } else if (event.type === 'private_message') {
        newMessages.push({
          id: event.event_id,
          from: event.payload?.from,
          to: event.payload?.to,
          message: event.payload?.message,
          timestamp: event.occurred_at
        });
      } else if (event.type === 'agent_subtask') {
        newTasks.push({
          id: event.event_id,
          agent: event.payload?.agent,
          task: event.payload?.task,
          status: event.payload?.status,
          timestamp: event.occurred_at
        });
      }
    });

    setCoalitions(newCoalitions);
    setPrivateMessages(newMessages);
    setSubTasks(newTasks);
  }, [events]);

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h3>🎭 Agent Behaviors</h3>
        <p className={styles.subtitle}>Real-time strategic activity</p>
      </div>

      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTab === 'coalitions' ? styles.tabActive : ''}`}
          onClick={() => setActiveTab('coalitions')}
        >
          🤝 Coalitions ({coalitions.length})
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'messages' ? styles.tabActive : ''}`}
          onClick={() => setActiveTab('messages')}
        >
          💬 Private Msgs ({privateMessages.length})
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'tasks' ? styles.tabActive : ''}`}
          onClick={() => setActiveTab('tasks')}
        >
          📋 Sub-tasks ({subTasks.length})
        </button>
      </div>

      <div className={styles.content}>
        {activeTab === 'coalitions' && (
          <div className={styles.section}>
            {coalitions.length === 0 ? (
              <div className={styles.empty}>
                <span className={styles.emptyIcon}>🤝</span>
                <p>No coalitions formed yet</p>
                <p className={styles.emptyHint}>Agents will form alliances during the debate</p>
              </div>
            ) : (
              coalitions.map(coalition => (
                <div key={coalition.id} className={styles.coalitionCard}>
                  <div className={styles.coalitionHeader}>
                    <span className={styles.coalitionBadge}>Coalition</span>
                    <span className={styles.coalitionTime}>
                      {new Date(coalition.formed_at).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className={styles.coalitionMembers}>
                    {coalition.members.map((member, idx) => (
                      <span key={idx} className={styles.memberBadge}>{member}</span>
                    ))}
                  </div>
                  {coalition.strategy && (
                    <div className={styles.coalitionStrategy}>
                      <strong>Strategy:</strong> {coalition.strategy}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'messages' && (
          <div className={styles.section}>
            {privateMessages.length === 0 ? (
              <div className={styles.empty}>
                <span className={styles.emptyIcon}>💬</span>
                <p>No private messages yet</p>
                <p className={styles.emptyHint}>Agents negotiate behind the scenes</p>
              </div>
            ) : (
              privateMessages.map(msg => (
                <div key={msg.id} className={styles.messageCard}>
                  <div className={styles.messageHeader}>
                    <span className={styles.messagePath}>
                      {msg.from} → {msg.to}
                    </span>
                    <span className={styles.messageTime}>
                      {new Date(msg.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className={styles.messageContent}>{msg.message}</div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'tasks' && (
          <div className={styles.section}>
            {subTasks.length === 0 ? (
              <div className={styles.empty}>
                <span className={styles.emptyIcon}>📋</span>
                <p>No sub-tasks yet</p>
                <p className={styles.emptyHint}>Agents break down goals into steps</p>
              </div>
            ) : (
              subTasks.map(task => (
                <div key={task.id} className={styles.taskCard}>
                  <div className={styles.taskHeader}>
                    <span className={styles.taskAgent}>{task.agent}</span>
                    <span className={`${styles.taskStatus} ${styles[`status-${task.status}`]}`}>
                      {task.status === 'planning' && '🤔 Planning'}
                      {task.status === 'executing' && '⚡ Executing'}
                      {task.status === 'completed' && '✅ Complete'}
                    </span>
                  </div>
                  <div className={styles.taskContent}>{task.task}</div>
                  <div className={styles.taskTime}>
                    {new Date(task.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
