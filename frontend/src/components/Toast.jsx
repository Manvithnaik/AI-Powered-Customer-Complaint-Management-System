import { useState, useEffect } from 'react';
import { useSelector } from 'react-redux';
import './Toast.css';

export default function ToastContainer() {
  const [toasts, setToasts] = useState([]);
  const analysisStatus = useSelector((s) => s.complaint.analysis.status);
  const analysisError = useSelector((s) => s.complaint.analysis.error);
  const duplicateCheck = useSelector((s) => s.complaint.form.ai_duplicate_check);
  const saveStatus = useSelector((s) => s.complaint.saveStatus);
  const savedComplaint = useSelector((s) => s.complaint.savedComplaint);
  const saveError = useSelector((s) => s.complaint.saveError);

  const addToast = (type, title, message) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, type, title, message }]);
    setTimeout(() => {
      removeToast(id);
    }, 4500);
  };

  const removeToast = (id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Toast trigger on AI Analysis fulfillment
  useEffect(() => {
    if (analysisStatus === 'success') {
      addToast('success', 'AI Analysis Complete', 'Extracted fields, risk score, RCA & CAPA recommendations loaded.');
      if (duplicateCheck?.duplicate_found) {
        setTimeout(() => {
          addToast('warning', 'Potential Duplicate Found', `Matching complaint ${duplicateCheck.matches[0]?.complaint_number || ''} detected (${duplicateCheck.matches[0]?.similarity_percentage || 0}% match).`);
        }, 500);
      }
    } else if (analysisStatus === 'error' && analysisError) {
      addToast('error', 'Analysis Failed', analysisError);
    }
  }, [analysisStatus]);

  // Toast trigger on Complaint Save fulfillment
  useEffect(() => {
    if (saveStatus === 'success' && savedComplaint) {
      addToast('success', 'Complaint Saved', `Record persisted successfully as ticket ${savedComplaint.complaint_number}.`);
    } else if (saveStatus === 'error' && saveError) {
      addToast('error', 'Unable to Save', saveError);
    }
  }, [saveStatus]);

  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.type} fade-in-up`}>
          <div className="toast-icon">
            {t.type === 'success' ? '✓' : t.type === 'warning' ? '⚠' : '❌'}
          </div>
          <div className="toast-content">
            <span className="toast-title">{t.title}</span>
            <span className="toast-message">{t.message}</span>
          </div>
          <button className="toast-close" onClick={() => removeToast(t.id)}>
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
