export interface UnitOption {
  value: string;
  label: string;
}

export const UNIT_OPTIONS: UnitOption[] = [
  { value: 'units', label: 'Units' },
  { value: 'kg', label: 'Kilograms (kg)' },
  { value: 'bags', label: 'Bags' },
  { value: 'tonnes', label: 'Tonnes' },
  { value: 'litres', label: 'Litres' },
  { value: 'meters', label: 'Meters' },
  { value: 'pieces', label: 'Pieces' },
  { value: 'boxes', label: 'Boxes' },
  { value: 'cartons', label: 'Cartons' },
  { value: 'pallets', label: 'Pallets' },
];
