import { useRef, useState } from 'react';
import * as api from '@/lib/api';
import styles from './SetupSteps.module.css';

interface MaterialsStepProps {
  debateId?: string;
  materials: api.SetupMaterial[];
  onAdd: (kind: 'text' | 'link' | 'file_placeholder') => void;
  onUpdate: (idx: number, updates: Partial<api.SetupMaterial>) => void;
  onRemove: (idx: number) => void;
  uploadedFiles?: api.MaterialStatus[];
  onFilesUploaded?: (files: api.MaterialStatus[]) => void;
}

export function MaterialsStep({ 
  debateId, 
  materials, 
  onAdd, 
  onUpdate, 
  onRemove,
  uploadedFiles = [],
  onFilesUploaded
}: MaterialsStepProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0 || !debateId) return;

    setUploading(true);
    setUploadError(null);

    try {
      const fileArray = Array.from(files);
      await api.uploadMaterials(debateId, fileArray);
      
      // Fetch updated status
      const status = await api.getMaterialsStatus(debateId);
      if (onFilesUploaded) {
        onFilesUploaded(status.materials);
      }
    } catch (error) {
      console.error('Upload failed:', error);
      setUploadError(error instanceof Error ? error.message : 'Upload failed');
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const getStatusBadge = (status: string) => {
    const badges: Record<string, string> = {
      'pending': '⏳ Pending',
      'processing': '⚙️ Processing',
      'complete': '✅ Ready',
      'failed': '❌ Failed',
      'needs_ocr': '👁️ Needs OCR'
    };
    return badges[status] || status;
  };

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
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.txt,.md"
          style={{ display: 'none' }}
          onChange={handleFileUpload}
          disabled={!debateId || uploading}
        />
        <button 
          onClick={() => fileInputRef.current?.click()} 
          className={styles.btnAdd}
          disabled={!debateId || uploading}
          title={!debateId ? 'Debate being created...' : 'Upload PDF, DOCX, TXT, or MD files'}
        >
          <span>📎</span> {uploading ? 'Uploading...' : 'Upload Files'}
        </button>
      </div>

      {uploadError && (
        <div className={styles.error}>{uploadError}</div>
      )}

      <div className={styles.list}>
        {/* Show uploaded files with status */}
        {uploadedFiles.map((file) => (
          <div key={file.material_id} className={styles.materialCard}>
            <div className={styles.cardHeader}>
              <span className={styles.badge}>{file.kind}</span>
              <span className={styles.statusBadge}>{getStatusBadge(file.processed_status)}</span>
            </div>
            
            <div className={styles.materialInfo}>
              <strong>{file.title}</strong>
              {file.file_size_bytes && (
                <span className={styles.fileSize}>
                  {(file.file_size_bytes / 1024).toFixed(1)} KB
                </span>
              )}
              {file.processing_metadata.word_count && (
                <span className={styles.wordCount}>
                  {file.processing_metadata.word_count} words
                </span>
              )}
              {file.processing_metadata.chunk_count && (
                <span className={styles.chunkCount}>
                  {file.processing_metadata.chunk_count} chunks
                </span>
              )}
            </div>

            {file.processed_status === 'failed' && (
              <div className={styles.errorMessage}>
                {file.processing_metadata.error || 'Processing failed'}
              </div>
            )}
          </div>
        ))}

        {/* Show manual materials */}
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
        
        {materials.length === 0 && uploadedFiles.length === 0 && (
          <p className={styles.empty}>No materials added yet (optional)</p>
        )}
      </div>
    </div>
  );
}
