import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import {
  bookingSchema,
  containerSchema,
  transhipmentLegSchema,
  transhipmentLegsSchema,
} from './schema';

// Helper: generate a valid date as a timestamp (ms since epoch) within a reasonable range
const dateArb = fc.integer({
  min: new Date('2020-01-01').getTime(),
  max: new Date('2029-12-31').getTime(),
});

// Feature: react-frontend, Property 6: Booking Date Ordering Validation
// **Validates: Requirements 4.8**

describe('Property 6: Booking Date Ordering Validation', () => {
  // Helper to build a valid base booking object (satisfying all non-date constraints)
  function makeBaseBooking(
    bookingDate: Date,
    validityDate: Date,
    fwStart: Date,
    fwEnd: Date,
  ) {
    return {
      booking_date: bookingDate.toISOString(),
      booking_validity_date: validityDate.toISOString(),
      forwarding_window_start: fwStart.toISOString(),
      forwarding_window_end: fwEnd.toISOString(),
      shipping_line: 1,
      pol: 1,
      pod: 1,
      client: 1,
      commodity: 1,
      cargo_type: 'FCL' as const,
      shipment_type: 'Export',
      stuffing_type: 'Factory',
      is_haz: false,
    };
  }

  it('produces error on booking_validity_date when booking_date > booking_validity_date', () => {
    fc.assert(
      fc.property(
        dateArb,
        fc.integer({ min: 1, max: 365 }),
        (validityTs, dayOffset) => {
          const validityDate = new Date(validityTs);
          const bookingDate = new Date(validityTs + dayOffset * 86400000);

          // Use valid forwarding window dates to isolate the booking date validation
          const fwStart = new Date('2025-01-01');
          const fwEnd = new Date('2025-01-31');

          const input = makeBaseBooking(bookingDate, validityDate, fwStart, fwEnd);
          const result = bookingSchema.safeParse(input);

          expect(result.success).toBe(false);
          if (!result.success) {
            const paths = result.error.issues.map((i) => i.path.join('.'));
            expect(paths).toContain('booking_validity_date');
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it('produces error on forwarding_window_end when start > end', () => {
    fc.assert(
      fc.property(
        dateArb,
        fc.integer({ min: 1, max: 365 }),
        (fwEndTs, dayOffset) => {
          const fwEnd = new Date(fwEndTs);
          const fwStart = new Date(fwEndTs + dayOffset * 86400000);

          // Use valid booking dates to isolate the forwarding window validation
          const bookingDate = new Date('2025-01-01');
          const validityDate = new Date('2025-01-31');

          const input = makeBaseBooking(bookingDate, validityDate, fwStart, fwEnd);
          const result = bookingSchema.safeParse(input);

          expect(result.success).toBe(false);
          if (!result.success) {
            const paths = result.error.issues.map((i) => i.path.join('.'));
            expect(paths).toContain('forwarding_window_end');
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it('produces no date-ordering error when both constraints are satisfied', () => {
    fc.assert(
      fc.property(
        dateArb,
        fc.nat({ max: 365 }),
        dateArb,
        fc.nat({ max: 365 }),
        (bookingTs, validityOffset, fwStartTs, fwEndOffset) => {
          // Ensure booking_date <= booking_validity_date
          const bookingDate = new Date(bookingTs);
          const validityDate = new Date(bookingTs + validityOffset * 86400000);
          // Ensure forwarding_window_start <= forwarding_window_end
          const fwStart = new Date(fwStartTs);
          const fwEnd = new Date(fwStartTs + fwEndOffset * 86400000);

          const input = makeBaseBooking(bookingDate, validityDate, fwStart, fwEnd);
          const result = bookingSchema.safeParse(input);

          // If result fails, it should NOT be due to date ordering
          if (!result.success) {
            const paths = result.error.issues.map((i) => i.path.join('.'));
            expect(paths).not.toContain('booking_validity_date');
            expect(paths).not.toContain('forwarding_window_end');
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});

// Feature: react-frontend, Property 7: Container Entry Schema Validation
// **Validates: Requirements 5.2, 5.3**

describe('Property 7: Container Entry Schema Validation', () => {
  const validSizes = ['20FT', '40FT', '40FT_HC', '45FT'] as const;

  it('rejects container entries with invalid size', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 10 }).filter(
          (s) => !validSizes.includes(s as (typeof validSizes)[number]),
        ),
        (invalidSize) => {
          const input = {
            container_type: 1,
            container_size: invalidSize,
            container_count: 1,
          };
          const result = containerSchema.safeParse(input);
          expect(result.success).toBe(false);
        },
      ),
      { numRuns: 100 },
    );
  });

  it('rejects container entries with count < 1', () => {
    fc.assert(
      fc.property(
        fc.integer({ max: 0 }),
        fc.constantFrom(...validSizes),
        (count, size) => {
          const input = {
            container_type: 1,
            container_size: size,
            container_count: count,
          };
          const result = containerSchema.safeParse(input);
          expect(result.success).toBe(false);
        },
      ),
      { numRuns: 100 },
    );
  });

  it('rejects container entries with container_no string > 20 chars', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 21, maxLength: 50 }),
        fc.constantFrom(...validSizes),
        (containerNo, size) => {
          const input = {
            container_type: 1,
            container_size: size,
            container_count: 1,
            container_no: containerNo,
          };
          const result = containerSchema.safeParse(input);
          expect(result.success).toBe(false);
        },
      ),
      { numRuns: 100 },
    );
  });

  it('rejects container entries with seal_no string > 20 chars', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 21, maxLength: 50 }),
        fc.constantFrom(...validSizes),
        (sealNo, size) => {
          const input = {
            container_type: 1,
            container_size: size,
            container_count: 1,
            seal_no: sealNo,
          };
          const result = containerSchema.safeParse(input);
          expect(result.success).toBe(false);
        },
      ),
      { numRuns: 100 },
    );
  });

  it('accepts valid container entries', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 1000 }),
        fc.constantFrom(...validSizes),
        fc.integer({ min: 1, max: 100 }),
        fc.string({ minLength: 0, maxLength: 20 }),
        fc.string({ minLength: 0, maxLength: 20 }),
        (containerType, size, count, containerNo, sealNo) => {
          const input = {
            container_type: containerType,
            container_size: size,
            container_count: count,
            container_no: containerNo || undefined,
            seal_no: sealNo || undefined,
          };
          const result = containerSchema.safeParse(input);
          expect(result.success).toBe(true);
        },
      ),
      { numRuns: 100 },
    );
  });
});

// Feature: react-frontend, Property 8: Transhipment Leg Chronological Validation
// **Validates: Requirements 6.3**

describe('Property 8: Transhipment Leg Chronological Validation', () => {
  function makeLeg(eta: Date, etd: Date) {
    return {
      port: 1,
      eta: eta.toISOString(),
      connecting_vessel_voyage: 'VESSEL-001',
      etd: etd.toISOString(),
    };
  }

  it('fails when etd <= eta for a single leg', () => {
    fc.assert(
      fc.property(
        dateArb,
        fc.integer({ min: 0, max: 86400000 * 30 }),
        (etaTs, offsetMs) => {
          const eta = new Date(etaTs);
          // etd <= eta: subtract offset from eta
          const etd = new Date(etaTs - offsetMs);
          const leg = makeLeg(eta, etd);
          const result = transhipmentLegSchema.safeParse(leg);
          expect(result.success).toBe(false);
        },
      ),
      { numRuns: 100 },
    );
  });

  it('fails when chronological order is violated between consecutive legs', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 2, max: 4 }),
        dateArb,
        (numLegs, baseTs) => {
          // Build legs in proper individual order (etd > eta) but violate inter-leg ordering
          const legs = [];
          let currentTime = baseTs;

          for (let i = 0; i < numLegs; i++) {
            const eta = new Date(currentTime);
            const etd = new Date(currentTime + 86400000); // etd = eta + 1 day
            legs.push(makeLeg(eta, etd));
            currentTime += 86400000 * 2;
          }

          // Violate chronological order: swap first and last legs
          if (legs.length >= 2) {
            const temp = legs[0]!;
            legs[0] = legs[legs.length - 1]!;
            legs[legs.length - 1] = temp;
          }

          const result = transhipmentLegsSchema.safeParse(legs);
          expect(result.success).toBe(false);
        },
      ),
      { numRuns: 100 },
    );
  });

  it('passes when all legs have etd > eta and chronological order is maintained', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 4 }),
        dateArb,
        fc.array(fc.integer({ min: 1, max: 30 }), { minLength: 4, maxLength: 4 }),
        fc.array(fc.integer({ min: 0, max: 30 }), { minLength: 4, maxLength: 4 }),
        (numLegs, baseTs, stayDays, gapDays) => {
          // Build legs sequentially ensuring:
          // 1. etd > eta (within each leg)
          // 2. legs[i].eta >= legs[i-1].etd (chronological order)
          const legs = [];
          let currentTime = baseTs;

          for (let i = 0; i < numLegs; i++) {
            const eta = new Date(currentTime);
            const etd = new Date(currentTime + stayDays[i]! * 86400000);
            legs.push(makeLeg(eta, etd));
            // Next leg's eta is at or after current leg's etd
            currentTime = etd.getTime() + gapDays[i]! * 86400000;
          }

          const result = transhipmentLegsSchema.safeParse(legs);
          expect(result.success).toBe(true);
        },
      ),
      { numRuns: 100 },
    );
  });
});
