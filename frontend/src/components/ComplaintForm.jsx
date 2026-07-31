import { useDispatch, useSelector } from 'react-redux';
import { useEffect, useRef } from 'react';
import { updateField, resetForm, submitComplaint, clearAiHighlight } from '../store/complaintSlice';
import './ComplaintForm.css';

const COMPLAINT_SOURCES = ['Email', 'Phone', 'Quality Portal', 'Letter', 'Verbal', 'Other'];
const COMPLAINT_TYPES = [
  'Packaging Defect',
  'Product Appearance / Discoloration',
  'Foreign Particle / Contamination',
  'Impurity / Assay Failure',
  'Adverse Event',
  'Labelling Error',
  'Sterility Failure',
  'Physical Defect',
  'Other',
];
const SEVERITIES = ['Critical', 'Major', 'Minor'];
const PRIORITIES = ['High', 'Medium', 'Low'];
const STATUSES = ['Pending Triage', 'Under Investigation', 'CAPA Initiated', 'Closed'];

function SectionHeader({ number, title }) {
  return (
    <div className="section-header">
      <span className="section-number">{number}</span>
      <span className="section-title">{title}</span>
    </div>
  );
}

function FieldRow({ children, cols = 2 }) {
  return (
    <div className={`field-row ${cols === 1 ? 'field-row-1' : 'field-row-2'}`}>
      {children}
    </div>
  );
}

function FormField({ label, required, children, id }) {
  return (
    <div className="form-field">
      <label className="field-label" htmlFor={id}>
        {label}
        {required && <span className="field-required">*</span>}
      </label>
      {children}
    </div>
  );
}

export default function ComplaintForm() {
  const dispatch = useDispatch();
  const form = useSelector(s => s.complaint.form);
  const aiPopulatedFields = useSelector(s => s.complaint.aiPopulatedFields);
  const saveStatus = useSelector(s => s.complaint.saveStatus);
  const savedComplaint = useSelector(s => s.complaint.savedComplaint);
  const saveError = useSelector(s => s.complaint.saveError);
  const analysisStatus = useSelector(s => s.complaint.analysis.status);
  const completeness = useSelector(s => s.complaint.analysis.completeness);
  const prevPopulated = useRef([]);

  const set = (field) => (e) => dispatch(updateField({ field, value: e.target.value }));

  // Clear AI highlight after animation completes
  useEffect(() => {
    if (aiPopulatedFields.length > 0) {
      prevPopulated.current = aiPopulatedFields;
      const t = setTimeout(() => {
        dispatch(clearAiHighlight());
        prevPopulated.current = [];
      }, 2000);
      return () => clearTimeout(t);
    }
  }, [aiPopulatedFields, dispatch]);

  const isAiField = (f) => aiPopulatedFields.includes(f) || prevPopulated.current.includes(f);

  const handleSave = () => {
    if (saveStatus === 'loading') return;
    dispatch(submitComplaint(form));
  };

  const handleReset = () => dispatch(resetForm());

  const severityColor = {
    Critical: 'severity-critical',
    Major: 'severity-major',
    Minor: 'severity-minor',
  }[form.initial_severity] || '';

  const priorityColor = {
    High: 'priority-high',
    Medium: 'priority-medium',
    Low: 'priority-low',
  }[form.priority] || '';

  return (
    <div className="complaint-form-panel">
      <div className="form-scroll">
        {/* ── Section 1: Origin ── */}
        <section className="form-section fade-in-up">
          <SectionHeader number="1" title="Origin &amp; Customer Details" />
          <FieldRow>
            <FormField label="Complaint Source" id="complaint_source">
              <select
                id="complaint_source"
                value={form.complaint_source}
                onChange={set('complaint_source')}
                className={isAiField('complaint_source') ? 'field-ai-populated' : ''}
              >
                <option value="">Select source…</option>
                {COMPLAINT_SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </FormField>
            <FormField label="Customer Name" id="customer_name">
              <input
                id="customer_name"
                type="text"
                placeholder="e.g. Apollo Pharmacy"
                value={form.customer_name}
                onChange={set('customer_name')}
                className={isAiField('customer_name') ? 'field-ai-populated' : ''}
              />
            </FormField>
          </FieldRow>
        </section>

        {/* ── Section 2: Product & Batch ── */}
        <section className="form-section fade-in-up" style={{ animationDelay: '60ms' }}>
          <SectionHeader number="2" title="Product &amp; Batch Identification" />
          <FieldRow>
            <FormField label="Product Name" id="product_name" required>
              <input
                id="product_name"
                type="text"
                placeholder="e.g. Amoxicillin Capsules"
                value={form.product_name}
                onChange={set('product_name')}
                className={isAiField('product_name') ? 'field-ai-populated' : ''}
              />
            </FormField>
            <FormField label="Product Strength / Grade" id="product_strength_grade">
              <input
                id="product_strength_grade"
                type="text"
                placeholder="e.g. 500 mg / USP Grade"
                value={form.product_strength_grade}
                onChange={set('product_strength_grade')}
                className={isAiField('product_strength_grade') ? 'field-ai-populated' : ''}
              />
            </FormField>
          </FieldRow>
          <FieldRow>
            <FormField label="Batch / Lot Number" id="batch_lot_number" required>
              <input
                id="batch_lot_number"
                type="text"
                placeholder="e.g. AMX240602"
                value={form.batch_lot_number}
                onChange={set('batch_lot_number')}
                className={isAiField('batch_lot_number') ? 'field-ai-populated' : ''}
              />
            </FormField>
            <FormField label="Affected Quantity" id="quantity_affected">
              <input
                id="quantity_affected"
                type="text"
                placeholder="e.g. 12 capsules / 50 kg"
                value={form.quantity_affected}
                onChange={set('quantity_affected')}
                className={isAiField('quantity_affected') ? 'field-ai-populated' : ''}
              />
            </FormField>
          </FieldRow>
          <FieldRow>
            <FormField label="Manufacturing Date" id="manufacturing_date">
              <input
                id="manufacturing_date"
                type="date"
                value={form.manufacturing_date}
                onChange={set('manufacturing_date')}
                className={isAiField('manufacturing_date') ? 'field-ai-populated' : ''}
              />
            </FormField>
            <FormField label="Expiry Date" id="expiry_date">
              <input
                id="expiry_date"
                type="date"
                value={form.expiry_date}
                onChange={set('expiry_date')}
                className={isAiField('expiry_date') ? 'field-ai-populated' : ''}
              />
            </FormField>
          </FieldRow>
        </section>

        {/* ── Section 3: Complaint Details ── */}
        <section className="form-section fade-in-up" style={{ animationDelay: '120ms' }}>
          <SectionHeader number="3" title="Complaint Details" />
          <FieldRow>
            <FormField label="Complaint Type" id="complaint_type">
              <select
                id="complaint_type"
                value={form.complaint_type}
                onChange={set('complaint_type')}
                className={isAiField('complaint_type') ? 'field-ai-populated' : ''}
              >
                <option value="">Select type…</option>
                {COMPLAINT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </FormField>
            <FormField label="Complaint Date" id="complaint_date">
              <input
                id="complaint_date"
                type="date"
                value={form.complaint_date}
                onChange={set('complaint_date')}
                className={isAiField('complaint_date') ? 'field-ai-populated' : ''}
              />
            </FormField>
          </FieldRow>
          <FieldRow cols={1}>
            <FormField label="Detailed Description" id="detailed_description" required>
              <textarea
                id="detailed_description"
                rows={4}
                placeholder="Describe the complaint in detail…"
                value={form.detailed_description}
                onChange={set('detailed_description')}
                className={isAiField('detailed_description') ? 'field-ai-populated' : ''}
              />
            </FormField>
          </FieldRow>
        </section>

        {/* ── Section 4: AI Risk Assessment ── */}
        <section className="form-section fade-in-up" style={{ animationDelay: '180ms' }}>
          <SectionHeader number="4" title="AI Risk Assessment" />
          <FieldRow>
            <FormField label="Initial Severity" id="initial_severity">
              <div className="severity-field-wrapper">
                <select
                  id="initial_severity"
                  value={form.initial_severity}
                  onChange={set('initial_severity')}
                  className={`severity-select ${severityColor} ${isAiField('initial_severity') ? 'field-ai-populated' : ''}`}
                >
                  <option value="">—</option>
                  {SEVERITIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
                {form.initial_severity && (
                  <span className={`severity-dot-inline ${severityColor}`} />
                )}
              </div>
            </FormField>
            <FormField label="Priority" id="priority">
              <select
                id="priority"
                value={form.priority}
                onChange={set('priority')}
                className={`${isAiField('priority') ? 'field-ai-populated' : ''}`}
              >
                <option value="">—</option>
                {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </FormField>
          </FieldRow>
          <FieldRow>
            <FormField label="Record Status" id="status">
              <select id="status" value={form.status} onChange={set('status')}>
                {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </FormField>
          </FieldRow>
          {form.ai_risk_rationale && (
            <div className="rationale-card fade-in">
              <div className="rationale-header">
                <span className="rationale-icon">✦</span>
                <span>AI Risk Rationale</span>
              </div>
              <p className="rationale-text">{form.ai_risk_rationale}</p>
            </div>
          )}
        </section>

        {/* ── Completeness ── */}
        {completeness && (
          <div className="completeness-bar-wrapper fade-in">
            <div className="completeness-bar-header">
              <span>Completeness</span>
              <span className={`completeness-score ${completeness.score >= 80 ? 'score-good' : completeness.score >= 50 ? 'score-ok' : 'score-low'}`}>
                {completeness.score}/100 — {completeness.completeness_level}
              </span>
            </div>
            <div className="completeness-track">
              <div
                className="completeness-fill"
                style={{
                  width: `${completeness.score}%`,
                  background: completeness.score >= 80
                    ? 'linear-gradient(90deg, #22c55e, #16a34a)'
                    : completeness.score >= 50
                    ? 'linear-gradient(90deg, #f59e0b, #d97706)'
                    : 'linear-gradient(90deg, #ef4444, #dc2626)',
                }}
              />
            </div>
            {completeness.missing_fields?.length > 0 && (
              <div className="completeness-missing">
                <span className="missing-label">Missing:</span>
                {completeness.missing_fields.map(m => (
                  <span key={m.field} className="missing-tag">{m.label}</span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Actions ── */}
        <div className="form-actions">
          {saveStatus === 'error' && (
            <p className="save-error">Save failed: {saveError}</p>
          )}
          {saveStatus === 'success' && savedComplaint && (
            <div className="save-success fade-in">
              <span>✓</span>
              <span>Saved as <strong>{savedComplaint.complaint_number}</strong></span>
            </div>
          )}
          <div className="action-buttons">
            <button id="reset-btn" className="btn-ghost" onClick={handleReset}>
              ↺ Reset
            </button>
            <button
              id="save-btn"
              className="btn-primary"
              onClick={handleSave}
              disabled={saveStatus === 'loading' || !form.product_name}
            >
              {saveStatus === 'loading' ? (
                <><div className="spinner" /> Saving…</>
              ) : (
                <>✦ Save Complaint</>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
