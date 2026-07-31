import { describe, it, expect } from 'vitest';
import reducer from './src/store/complaintSlice';

const pendingAction = { type: 'complaint/analyzeText/pending' };
const fulfilledAction = (payload) => ({
  type: 'complaint/analyzeText/fulfilled',
  payload,
});

describe('Complaint Redux Slice State Resets & Clear Logic', () => {
  it('should correctly clear previous complaint state on pending analysis', () => {
    // Start with a state containing Atorvastatin data
    const existingState = {
      form: {
        product_name: 'Atorvastatin Tablets',
        manufacturing_date: '2026-03-01',
        initial_severity: 'Critical',
      },
      analysis: {
        status: 'success',
        completeness: { score: 90 },
        validation_warnings: ['some warning'],
      },
      saveStatus: 'success',
      savedComplaint: { complaint_number: 'CMP-2026-0001' },
      aiPopulatedFields: ['product_name', 'manufacturing_date'],
    };

    // Transition to pending (user starts second analysis)
    const nextState = reducer(existingState, pendingAction);

    // Assert that the draft and analysis/save states are reset
    expect(nextState.form.product_name).toBe('');
    expect(nextState.form.manufacturing_date).toBe('');
    expect(nextState.form.initial_severity).toBe('');
    expect(nextState.analysis.completeness).toBeNull();
    expect(nextState.analysis.validation_warnings).toEqual([]);
    expect(nextState.saveStatus).toBe('idle');
    expect(nextState.savedComplaint).toBeNull();
    expect(nextState.aiPopulatedFields).toEqual([]);
    expect(nextState.analysis.status).toBe('loading');
  });

  it('should overwrite old values with empty/null fields from new extraction on fulfilled', () => {
    const existingState = {
      form: {
        product_name: 'Atorvastatin Tablets',
        manufacturing_date: '2026-03-01', // Pre-existing stale date
      },
      analysis: {
        status: 'loading',
      },
      chat: [],
    };

    const newExtraction = {
      product_name: 'Amoxicillin Capsules',
      manufacturing_date: null, // Absent in new complaint
      expiry_date: null,
      initial_severity: 'Minor',
    };

    const nextState = reducer(existingState, fulfilledAction(newExtraction));

    // Assert that Amoxicillin is written, but Atorvastatin's manufacturing date is cleared (overwritten)
    expect(nextState.form.product_name).toBe('Amoxicillin Capsules');
    expect(nextState.form.manufacturing_date).toBe(''); // Overwritten from '2026-03-01' -> ''
    expect(nextState.form.expiry_date).toBe('');
    expect(nextState.form.initial_severity).toBe('Minor');
  });
});
