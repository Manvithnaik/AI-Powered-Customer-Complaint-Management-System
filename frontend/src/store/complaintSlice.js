import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { analyzeComplaintText, analyzeComplaintFile, saveComplaint } from '../services/api';

// ─── Async Thunks ───────────────────────────────────────────────
export const analyzeText = createAsyncThunk(
  'complaint/analyzeText',
  async (text, { rejectWithValue, getState }) => {
    try {
      // Send the current form state so the backend can detect follow-up intent
      const currentForm = getState().complaint.form;
      // Only send if there is at least a product name (draft is active)
      const currentState = currentForm.product_name ? currentForm : null;
      return await analyzeComplaintText(text, currentState);
    } catch (err) {
      return rejectWithValue(err.message);
    }
  }
);

export const analyzeFile = createAsyncThunk(
  'complaint/analyzeFile',
  async (file, { rejectWithValue }) => {
    try {
      return await analyzeComplaintFile(file);
    } catch (err) {
      return rejectWithValue(err.message);
    }
  }
);

export const submitComplaint = createAsyncThunk(
  'complaint/submitComplaint',
  async (formData, { rejectWithValue }) => {
    try {
      return await saveComplaint(formData);
    } catch (err) {
      return rejectWithValue(err.message);
    }
  }
);

// ─── Initial State ──────────────────────────────────────────────
const emptyForm = {
  complaint_source: '',
  customer_name: '',
  product_name: '',
  product_strength_grade: '',
  batch_lot_number: '',
  manufacturing_date: '',
  expiry_date: '',
  quantity_affected: '',
  complaint_type: '',
  complaint_date: '',
  detailed_description: '',
  initial_severity: '',
  priority: '',
  ai_risk_rationale: '',
  ai_complaint_summary: '',
  ai_capa_rca: null,
  ai_capa_recommendation: null,
  status: 'Pending Triage',
};

const initialState = {
  form: { ...emptyForm },
  // AI analysis results
  analysis: {
    status: 'idle',  // idle | loading | success | error
    error: null,
    completeness: null,
    validation_warnings: [],
    validation_passed: true,
  },
  // Chat thread
  chat: [
    {
      id: 1,
      role: 'assistant',
      content: 'Ready to process new complaints. Paste the raw email from the customer, or upload a PDF of the complaint report. I will extract the data and run the initial risk assessment.',
      timestamp: Date.now(),
    }
  ],
  // Which fields were just AI-populated (drives flash animation)
  aiPopulatedFields: [],
  // Save state
  saveStatus: 'idle',  // idle | loading | success | error
  saveError: null,
  savedComplaint: null,
};

// ─── Slice ──────────────────────────────────────────────────────
const complaintSlice = createSlice({
  name: 'complaint',
  initialState,
  reducers: {
    updateField(state, action) {
      const { field, value } = action.payload;
      state.form[field] = value;
    },
    resetForm(state) {
      state.form = { ...emptyForm };
      state.analysis = { ...initialState.analysis };
      state.aiPopulatedFields = [];
      state.saveStatus = 'idle';
      state.savedComplaint = null;
      state.chat = [initialState.chat[0]];
    },
    addUserMessage(state, action) {
      state.chat.push({
        id: Date.now(),
        role: 'user',
        content: action.payload,
        timestamp: Date.now(),
      });
    },
    clearAiHighlight(state) {
      state.aiPopulatedFields = [];
    },
  },
  extraReducers: (builder) => {
    // ── Analyze Text / File (shared logic) ───────────────────────
    const onAnalysisPending = (state, action) => {
      state.analysis.status = 'loading';
      state.analysis.error = null;
      // NOTE: We do NOT reset form fields here.
      // The backend detects whether this is a new complaint or a follow-up.
      // On fulfilled, the response always contains the correct merged/fresh state.
      // If we blanked the form now, follow-up analyses would flash empty fields
      // during the loading phase, and the form would lose the original description.
      state.aiPopulatedFields = [];
    };

    const onAnalysisFulfilled = (state, action) => {
      const data = action.payload;
      state.analysis.status = 'success';
      state.analysis.completeness = data.ai_completeness_check;
      state.analysis.validation_warnings = data.validation_warnings || [];
      state.analysis.validation_passed = data.validation_passed;

      // Track which fields are AI-populated for animation
      const populated = [];
      const fieldMap = {
        complaint_source: data.complaint_source,
        customer_name: data.customer_name,
        product_name: data.product_name,
        product_strength_grade: data.product_strength_grade,
        batch_lot_number: data.batch_lot_number,
        manufacturing_date: data.manufacturing_date,
        expiry_date: data.expiry_date,
        quantity_affected: data.quantity_affected,
        complaint_type: data.complaint_type,
        complaint_date: data.complaint_date,
        detailed_description: data.detailed_description,
        initial_severity: data.initial_severity,
        priority: data.priority,
        ai_risk_rationale: data.ai_risk_rationale,
      };
      Object.entries(fieldMap).forEach(([key, val]) => {
        // Explicitly write value, falling back to empty string to overwrite old values
        state.form[key] = val || '';
        if (val) {
          populated.push(key);
        }
      });
      // Write object/non-string AI outputs directly (not through string coercion)
      state.form.ai_complaint_summary = data.ai_complaint_summary || '';
      state.form.ai_capa_rca = data.ai_capa_rca ?? null;
      state.form.ai_capa_recommendation = data.ai_capa_recommendation ?? null;
      state.aiPopulatedFields = populated;

      // Build assistant response message — detect if this was a follow-up
      const severity = data.initial_severity || 'Unknown';
      const score = data.ai_completeness_check?.score || 0;
      const level = data.ai_completeness_check?.completeness_level || '';
      const missing = data.ai_completeness_check?.missing_fields || [];
      const missingStr = missing.length > 0
        ? ` Missing: ${missing.slice(0, 3).map(m => m.label).join(', ')}.`
        : ' All key fields captured.';
      // Determine if this was an update vs new by checking if description was preserved
      const isUpdate = !!(data.product_name && populated.length > 0 && populated.length < 8);
      const intro = isUpdate
        ? `Complaint updated successfully. I've merged the new information into the existing draft.`
        : `Complaint parsed successfully. I've extracted the product details and mapped the batch information.`;

      state.chat.push({
        id: Date.now(),
        role: 'assistant',
        content: `${intro}\n\n**Risk Assessment:** ${severity} severity — ${data.priority} priority.\n**Completeness:** ${score}/100 (${level}).${missingStr}\n\n${data.ai_risk_rationale || ''}`,
        timestamp: Date.now(),
        isAnalysis: true,
        severity,
        score,
      });
    };

    const onAnalysisRejected = (state, action) => {
      state.analysis.status = 'error';
      state.analysis.error = action.payload;
      state.chat.push({
        id: Date.now(),
        role: 'assistant',
        content: `Analysis failed: ${action.payload}. Please check your connection and try again.`,
        timestamp: Date.now(),
        isError: true,
      });
    };

    builder
      .addCase(analyzeText.pending, onAnalysisPending)
      .addCase(analyzeText.fulfilled, onAnalysisFulfilled)
      .addCase(analyzeText.rejected, onAnalysisRejected)
      .addCase(analyzeFile.pending, onAnalysisPending)
      .addCase(analyzeFile.fulfilled, onAnalysisFulfilled)
      .addCase(analyzeFile.rejected, onAnalysisRejected)
      // ── Submit Complaint ────────────────────────────────────────
      .addCase(submitComplaint.pending, (state) => {
        state.saveStatus = 'loading';
        state.saveError = null;
      })
      .addCase(submitComplaint.fulfilled, (state, action) => {
        state.saveStatus = 'success';
        state.savedComplaint = action.payload;
        state.chat.push({
          id: Date.now(),
          role: 'assistant',
          content: `Complaint saved successfully as **${action.payload.complaint_number}**. Status: ${action.payload.status}.`,
          timestamp: Date.now(),
          isSave: true,
        });
      })
      .addCase(submitComplaint.rejected, (state, action) => {
        state.saveStatus = 'error';
        state.saveError = action.payload;
      });
  },
});

export const { updateField, resetForm, addUserMessage, clearAiHighlight } = complaintSlice.actions;
export default complaintSlice.reducer;
