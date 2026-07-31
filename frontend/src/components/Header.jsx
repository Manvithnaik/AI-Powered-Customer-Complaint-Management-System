import { useSelector } from 'react-redux';
import './Header.css';

export default function Header() {
  const saveStatus = useSelector(s => s.complaint.saveStatus);
  const savedComplaint = useSelector(s => s.complaint.savedComplaint);
  const analysisStatus = useSelector(s => s.complaint.analysis.status);

  const getStatusBadge = () => {
    if (saveStatus === 'success' && savedComplaint) {
      return { label: `Saved — ${savedComplaint.complaint_number}`, cls: 'status-saved' };
    }
    if (saveStatus === 'loading') {
      return { label: 'Saving…', cls: 'status-saving' };
    }
    if (analysisStatus === 'loading') {
      return { label: 'Analyzing…', cls: 'status-analyzing' };
    }
    if (analysisStatus === 'success') {
      return { label: 'Ready to Commit', cls: 'status-ready' };
    }
    return { label: 'Awaiting Input', cls: 'status-idle' };
  };

  const { label, cls } = getStatusBadge();

  return (
    <header className="app-header">
      <div className="header-left">
        <div className="header-logo">
          <span className="logo-icon">⬡</span>
          <div>
            <span className="logo-title">AIVOA</span>
            <span className="logo-sub">QMS Platform</span>
          </div>
        </div>
        <div className="header-divider" />
        <span className="header-module">API &amp; FDF Quality Assurance Module</span>
      </div>
      <div className="header-right">
        <div className={`status-badge ${cls}`}>
          <span className="status-dot" />
          {label}
        </div>
      </div>
    </header>
  );
}
