import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { isValidSearchQuery } from './useBookingSearch';

// Feature: react-frontend, Property 9: Search Query Length Gating
// **Validates: Requirements 7.1**

describe('Property 9: Search Query Length Gating', () => {
  it('rejects empty strings (length 0)', () => {
    expect(isValidSearchQuery('')).toBe(false);
  });

  it('rejects strings with length > 100', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 101, maxLength: 150 }),
        (query) => {
          expect(isValidSearchQuery(query)).toBe(false);
        },
      ),
      { numRuns: 100 },
    );
  });

  it('accepts strings with length between 1 and 100 (inclusive)', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 100 }),
        (query) => {
          expect(isValidSearchQuery(query)).toBe(true);
        },
      ),
      { numRuns: 100 },
    );
  });

  it('correctly gates based on length for arbitrary strings 0–150', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 0, maxLength: 150 }),
        (query) => {
          const result = isValidSearchQuery(query);
          const expectedValid = query.length >= 1 && query.length <= 100;
          expect(result).toBe(expectedValid);
        },
      ),
      { numRuns: 100 },
    );
  });
});
