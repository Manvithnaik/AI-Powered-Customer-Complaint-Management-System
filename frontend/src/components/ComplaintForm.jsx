import { useDispatch, useSelector } from 'react-redux';
import { useState, useEffect, useRef } from 'react';
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

  // Default mode is Read-Only to protect AI-populated data
  const [isEditing, setIsEditing] = useState(false);

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

  const handleReset = () => {
    dispatch(resetForm());
    setIsEditing(false);
  };

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
      {/* ── Form Top Action Bar (Mode Indicator & Edit Toggle) ── */}
      <div className="form-header-bar">
        <div className="form-mode-container">
          {isEditing ? (
            <span className="mode-badge mode-editing">
              <span className="mode-dot editing-dot" /> Manual Editing
            </span>
          ) : (
            <span className="mode-badge mode-readonly">
              <span className="mode-dot readonly-dot" /> AI Generated
            </span>
          )}
        </div>
        <button
          type="button"
          className={`btn-toggle-edit ${isEditing ? 'is-editing' : ''}`}
          onClick={() => setIsEditing(!isEditing)}
        >
          {isEditing ? '✓ Save Changes' : '✏ Edit Complaint'}
        </button>
      </div>

      <div className="form-scroll">
        {/* ── Edit Mode Informational Banner ── */}
        {isEditing && (
          <div className="edit-mode-banner fade-in">
            <span className="banner-icon">💡</span>
            <span>
              You are now editing AI-generated data. Your manual changes will override the AI extraction.
            </span>
          </div>
        )}

        {/* ── Section 1: Origin ── */}
        <section className="form-section fade-in-up">
          <SectionHeader number="1" title="Origin &amp; Customer Details" />
          <FieldRow>
            <FormField label="Complaint Source" id="complaint_source">
              <select
                id="complaint_source"
                value={form.complaint_source}
                onChange={set('complaint_source')}
                disabled={!isEditing}
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
                disabled={!isEditing}
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
                disabled={!isEditing}
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
                disabled={!isEditing}
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
                disabled={!isEditing}
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
                disabled={!isEditing}
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
                disabled={!isEditing}
                className={isAiField('manufacturing_date') ? 'field-ai-populated' : ''}
              />
            </FormField>
            <FormField label="Expiry Date" id="expiry_date">
              <input
                id="expiry_date"
                type="date"
                value={form.expiry_date}
                onChange={set('expiry_date')}
                disabled={!isEditing}
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
                disabled={!isEditing}
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
                disabled={!isEditing}
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
                disabled={!isEditing}
                className={isAiField('detailed_description') ? 'field-ai-populated' : ''}
              />
            </FormField>
          </FieldRow>
        </section>

        {/* ── Section 4: AI Risk Assessment ── */}
        <section className="form-section fade-in-up" style={{ animationDelay: '180ms' }}>
          <SectionHeader number="4" title="AI Risk Assessment" />
          <FieldRow>
            <FormField label="Initial Severity (AI Output)" id="initial_severity">
              <div className="severity-field-wrapper">
                <select
                  id="initial_severity"
                  value={form.initial_severity}
                  onChange={set('initial_severity')}
                  disabled={true}
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
            <FormField label="Priority (AI Output)" id="priority">
              <select
                id="priority"
                value={form.priority}
                onChange={set('priority')}
                disabled={true}
                className={`${isAiField('priority') ? 'field-ai-populated' : ''}`}
              >
                <option value="">—</option>
                {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </FormField>
          </FieldRow>
          <FieldRow>
            <FormField label="Record Status" id="status">
              <select id="status" value={form.status} onChange={set('status')} disabled={!isEditing}>
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

          {/* ── AI Complaint Summary (Bonus Feature #1) ── */}
          {form.ai_complaint_summary && (
            <div className="summary-card fade-in">
              <div className="summary-header">
                <span className="summary-icon">✦</span>
                <span>AI Complaint Summary</span>
              </div>
              <p className="summary-text">{form.ai_complaint_summary}</p>
            </div>
          )}

          {/* ── AI Root Cause Recommendation (Bonus Feature #2) ── */}
          {form.ai_capa_rca && (
            <div className="rca-card fade-in">
              <div className="rca-header">
                <span className="rca-icon">✦</span>
                <span>AI Root Cause Recommendation</span>
                <span className={`rca-confidence-badge confidence-${(form.ai_capa_rca.confidence || 'low').toLowerCase()}`}>
                  {form.ai_capa_rca.confidence || 'Low'} Confidence
                </span>
              </div>

              {form.ai_capa_rca.possible_root_causes?.length > 0 ? (
                <ul className="rca-list">
                  {form.ai_capa_rca.possible_root_causes.map((item, idx) => (
                    <li key={idx} className="rca-item">
                      <span className="rca-cause">{item.cause}</span>
                      <span className="rca-reason">{item.reason}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="rca-insufficient">
                  {form.ai_capa_rca.disclaimer || 'Insufficient data to generate root cause recommendations.'}
                </p>
              )}

              {form.ai_capa_rca.possible_root_causes?.length > 0 && (
                <p className="rca-disclaimer">⚠ {form.ai_capa_rca.disclaimer}</p>
              )}
            </div>
          )}

          {/* ── AI CAPA Recommendation (Bonus Feature #3) ── */}
          {form.ai_capa_recommendation && (
            <div className="capa-card fade-in">
              <div className="capa-header">
                <span className="capa-icon">✦</span>
                <span>AI CAPA Recommendation</span>
                <span className={`capa-confidence-badge confidence-${(form.ai_capa_recommendation.confidence || 'low').toLowerCase()}`}>
                  {form.ai_capa_recommendation.confidence || 'Low'} Confidence
                </span>
              </div>

              <div className="capa-sections">
                {/* Corrective Actions */}
                <div className="capa-group">
                  <h4 className="capa-subtitle">Corrective Actions (Immediate Response)</h4>
                  {form.ai_capa_recommendation.corrective_actions?.length > 0 ? (
                    <ul className="capa-list">
                      {form.ai_capa_recommendation.corrective_actions.map((act, idx) => (
                        <li key={idx} className="capa-item item-corrective">
                          <span className="capa-bullet">•</span>
                          <span className="capa-text">{act}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="capa-empty-text">No immediate corrective actions identified.</p>
                  )}
                </div>

                {/* Preventive Actions */}
                <div className="capa-group">
                  <h4 className="capa-subtitle">Preventive Actions (Avoid Recurrence)</h4>
                  {form.ai_capa_recommendation.preventive_actions?.length > 0 ? (
                    <ul className="capa-list">
                      {form.ai_capa_recommendation.preventive_actions.map((act, idx) => (
                        <li key={idx} className="capa-item item-preventive">
                          <span className="capa-bullet">•</span>
                          <span className="capa-text">{act}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="capa-empty-text">No preventive actions identified.</p>
                  )}
                </div>
              </div>

              <p className="capa-disclaimer">⚠ {form.ai_capa_recommendation.disclaimer}</p>
            </div>
          )}

          {/* ── AI Duplicate Complaint Detection (Bonus Feature #4) ── */}
          {form.ai_duplicate_check && (
            <div className={`duplicate-card fade-in ${form.ai_duplicate_check.duplicate_found ? 'has-duplicates' : 'no-duplicates'}`}>
              <div className="duplicate-header">
                <span className="duplicate-icon">✦</span>
                <span>AI Duplicate Complaint Detection</span>
                <span className={`duplicate-confidence-badge confidence-${(form.ai_duplicate_check.confidence || 'high').toLowerCase()}`}>
                  {form.ai_duplicate_check.confidence || 'High'} Confidence
                </span>
              </div>

              {form.ai_duplicate_check.duplicate_found && form.ai_duplicate_check.matches?.length > 0 ? (
                <div className="duplicate-body">
                  <div className="duplicate-alert-banner">
                    <span className="alert-icon">⚠</span>
                    <span>Potential Duplicate(s) Identified in Database</span>
                  </div>

                  <div className="duplicate-matches-list">
                    {form.ai_duplicate_check.matches.map((m, idx) => (
                      <div key={idx} className="duplicate-match-item">
                        <div className="match-top-row">
                          <span className="match-complaint-number">{m.complaint_number}</span>
                          <span className="match-similarity-pill">{m.similarity}% Similarity</span>
                        </div>
                        {m.reasons?.length > 0 && (
                          <div className="match-reasons">
                            {m.reasons.map((r, rIdx) => (
                              <span key={rIdx} className="reason-tag">✓ {r}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  <p className="duplicate-recommendation">
                    <strong>Recommendation:</strong> {form.ai_duplicate_check.recommendation}
                  </p>
                </div>
              ) : (
                <div className="duplicate-clear-banner">
                  <span className="clear-icon">✓</span>
                  <span>No Similar Historical Complaints Found</span>
                </div>
              )}
            </div>
          )}
        </section>

        {/* ── Completeness ── */}
        {completeness && (
          <div className="completeness-bar-wrapper fade-in">
            <div className="completeness-bar-header">
              <span>Completeness</span>
              {completeness.score != null ? (
                <span className={`completeness-score ${completeness.score >= 80 ? 'score-good' : completeness.score >= 50 ? 'score-ok' : 'score-low'}`}>
                  {completeness.score}/100 — {completeness.completeness_level}
                </span>
              ) : (
                <span className="completeness-score score-na">
                  {completeness.completeness_level || 'Not Available'}
                </span>
              )}
            </div>
            <div className="completeness-track">
              <div
                className="completeness-fill"
                style={{
                  width: completeness.score != null ? `${completeness.score}%` : '0%',
                  background: completeness.score == null
                    ? 'linear-gradient(90deg, #6b7280, #4b5563)'
                    : completeness.score >= 80
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
            <button
              id="reset-btn"
              className="btn-danger-ghost"
              onClick={handleReset}
              disabled={analysisStatus === 'loading' || saveStatus === 'loading'}
            >
              ↺ Reset
            </button>
            <button
              id="save-btn"
              className="btn-primary"
              onClick={handleSave}
              disabled={saveStatus === 'loading' || analysisStatus === 'loading' || !form.product_name}
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
