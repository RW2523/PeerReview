import * as api from '@/lib/api';
import styles from './SetupSteps.module.css';

interface MaterialsStepProps {
  materials: api.SetupMaterial[];
  onAdd: (kind: 'text' | 'link' | 'file_placeholder') => void;
  onUpdate: (idx: number, updates: Partial<api.SetupMaterial>) => void;
  onRemove: (idx: number) => void;
}

export function MaterialsStep({ materials, onAdd, onUpdate, onRemove }: MaterialsStepProps) {
  return (
    <div className={styles.section}>
      <h2>Materials</h2>
      <p className={styles.hint}>Add context, documents, or links for participants</p>

      <div className={styles.buttonGroup}>
        <button onClick={() => onAdd('text')} className={styles.btnAdd}>
          <span>📝</span> Add Text
        </button>
        <button onClick={() => onAdd('link')} className={styles.btnAdd}>
          <span>🔗</span> Add Link
        </button>
        <button onClick={() => onAdd('file_placeholder')} disabled className={styles.btnAdd}>
          <span>📎</span> Upload File
          <span className={styles.comingSoon}>Soon</span>
        </button>
      </div>

      <div className={styles.list}>
        {materials.map((material, idx) => (
          <div key={idx} className={styles.materialCard}>
            <div className={styles.cardHeader}>
              <span className={styles.badge}>{material.kind}</span>
              <button onClick={() => onRemove(idx)} className={styles.btnRemove}>×</button>
            </div>
            
            <input
              type="text"
              value={material.title || ''}
              onChange={(e) => onUpdate(idx, { title: e.target.value })}
              placeholder="Title"
            />
            
            {material.kind === 'text' && (
              <textarea
                value={material.body_text || ''}
                onChange={(e) => onUpdate(idx, { body_text: e.target.value })}
                placeholder="Paste text content here"
                rows={3}
              />
            )}
            
            {(material.kind === 'link' || material.kind === 'file_placeholder') && (
              <input
                type="text"
                value={material.url || ''}
                onChange={(e) => onUpdate(idx, { url: e.target.value })}
                placeholder="https://..."
              />
            )}
          </div>
        ))}
        
        {materials.length === 0 && (
          <p className={styles.empty}>No materials added yet (optional)</p>
        )}
      </div>
    </div>
  );
}
