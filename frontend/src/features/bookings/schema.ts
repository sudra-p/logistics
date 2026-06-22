import { z } from 'zod/v4';

/** Validates a YYYY-MM-DD date string. */
const dateString = z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Date must be YYYY-MM-DD format');

export const bookingSchema = z
  .object({
    booking_date: dateString,
    booking_validity_date: dateString,
    forwarding_window_start: dateString,
    forwarding_window_end: dateString,
    shipping_line: z.number().positive(),
    pol: z.number().positive(),
    pod: z.number().positive(),
    client: z.number().positive(),
    commodity: z.number().positive(),
    cargo_type: z.enum(['FCL', 'LCL']),
    shipment_type: z.string().min(1),
    stuffing_type: z.string().min(1),
    is_haz: z.boolean().default(false),
    haz_class: z.string().optional(),
    haz_uin: z.string().optional(),
    haz_group: z.string().optional(),
  })
  .refine((data) => data.booking_date <= data.booking_validity_date, {
    message: 'Booking date must be on or before validity date',
    path: ['booking_validity_date'],
  })
  .refine(
    (data) => data.forwarding_window_start <= data.forwarding_window_end,
    {
      message: 'Forwarding window start must be on or before end',
      path: ['forwarding_window_end'],
    },
  )
  .refine(
    (data) =>
      !data.is_haz || (!!data.haz_class && !!data.haz_uin && !!data.haz_group),
    {
      message: 'HAZ fields are required when is_haz is true',
      path: ['haz_class'],
    },
  );

export type BookingFormValues = z.infer<typeof bookingSchema>;

export const containerSchema = z.object({
  container_type: z.number().positive(),
  container_size: z.enum(['20FT', '40FT', '40FT_HC', '45FT']),
  container_count: z.number().int().min(1),
  container_no: z.string().max(20).optional(),
  seal_no: z.string().max(20).optional(),
});

export type ContainerFormValues = z.infer<typeof containerSchema>;

export const transhipmentLegSchema = z
  .object({
    port: z.number().positive(),
    eta: z.string().pipe(z.coerce.date()),
    connecting_vessel_voyage: z.string().min(1).max(200),
    etd: z.string().pipe(z.coerce.date()),
  })
  .refine((data) => data.etd > data.eta, {
    message: 'ETD must be after ETA',
    path: ['etd'],
  });

export type TranshipmentLegFormValues = z.infer<typeof transhipmentLegSchema>;

export const transhipmentLegsSchema = z
  .array(transhipmentLegSchema)
  .max(4)
  .refine(
    (legs) => {
      for (let i = 1; i < legs.length; i++) {
        const current = legs[i];
        const previous = legs[i - 1];
        if (current && previous && current.eta < previous.etd) return false;
      }
      return true;
    },
    { message: 'Legs must be in chronological order' },
  );

export type TranshipmentLegsFormValues = z.infer<typeof transhipmentLegsSchema>;
