# Implementation Plan: Unit Dropdown

## Overview

Convert the "Unit" free-text input on the Stock Item form into a Material UI Select dropdown with predefined options. Implementation spans frontend (React/MUI Select component + constants file) and backend (Django model choices, serializer validation with legacy bypass, and migration). Backward compatibility is preserved for existing stock items with non-standard unit values.

## Tasks

- [x] 1. Backend: Add UNIT_CHOICES and update model
  - [x] 1.1 Add UNIT_CHOICES constant and update StockItem model field
    - Add `UNIT_CHOICES` list to `inventory/models.py` with the 10 predefined unit tuples
    - Update the `unit` field to include `choices=UNIT_CHOICES` parameter
    - Ensure `default='units'` and `max_length=50` are preserved
    - _Requirements: 1.1, 3.4_

  - [x] 1.2 Generate Django migration for the updated unit field
    - Run `makemigrations` to create an AlterField migration
    - Verify the migration only updates field metadata (choices) and does NOT add a database-level CHECK constraint
    - _Requirements: 4.2_

- [x] 2. Backend: Implement serializer validation
  - [x] 2.1 Add validate_unit method to StockItemSerializer
    - Import `UNIT_CHOICES` from models
    - Implement `validate_unit` that accepts values in the choices list
    - Default to `'units'` if value is empty or omitted on create
    - On update, allow the current persisted value (legacy bypass) by checking `self.instance`
    - Return a 400 error with accepted values listed for invalid submissions
    - _Requirements: 3.1, 3.2, 3.3, 3.5, 4.4_

  - [ ]* 2.2 Write property test: Backend validation accepts exactly valid units and rejects invalid ones
    - **Property 2: Backend validation accepts exactly valid units and rejects invalid ones**
    - **Validates: Requirements 3.1, 3.2, 3.3**
    - Use hypothesis to generate random strings and verify: valid values accepted, invalid values rejected with 400

  - [ ]* 2.3 Write property test: Legacy values preserved on update
    - **Property 3: Legacy values preserved on update**
    - **Validates: Requirements 3.5, 4.4**
    - Use hypothesis to generate non-standard unit strings, create a stock item with that value, then submit an update preserving it and assert success

  - [ ]* 2.4 Write unit tests for serializer validation
    - Test UNIT_CHOICES contains exactly the expected values in order
    - Test serializer defaults unit to "units" when omitted or empty on create
    - Test serializer rejects invalid unit on create
    - Test serializer accepts legacy value on update when unchanged
    - Test serializer rejects invalid value on create
    - _Requirements: 3.1, 3.2, 3.3, 3.5_

- [x] 3. Checkpoint - Backend complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Frontend: Create unit options constant
  - [x] 4.1 Create unitOptions.ts with UNIT_OPTIONS constant
    - Create new file `frontend/src/features/inventory/unitOptions.ts`
    - Export `UnitOption` interface with `value` and `label` fields
    - Export `UNIT_OPTIONS` array with the 10 predefined options matching backend UNIT_CHOICES
    - _Requirements: 1.1, 1.3_

- [x] 5. Frontend: Replace TextField with Select dropdown
  - [x] 5.1 Update StockFormPage.tsx to use MUI Select for the unit field
    - Import `Select`, `MenuItem`, `InputLabel`, `FormControl` from `@mui/material`
    - Import `UNIT_OPTIONS` from `./unitOptions`
    - Replace the Unit `<TextField>` with a `<FormControl>` + `<InputLabel>` + `<Select>` rendering `<MenuItem>` for each option
    - Keep the same Grid size props (xs=12, sm=6, md=3)
    - Preserve the existing `unit` state and `setUnit` handler
    - _Requirements: 2.1, 2.2, 2.3, 2.6_

  - [x] 5.2 Handle legacy unit values in edit mode
    - After loading stock item data, check if the unit value exists in `UNIT_OPTIONS`
    - If not found, append it as an additional `<MenuItem>` with a "(legacy)" suffix label
    - After a successful save that changes to a standard value, the legacy option disappears on re-render (driven by fresh API data)
    - _Requirements: 2.4, 2.5, 4.1, 4.3, 4.5_

  - [ ]* 5.3 Write property test: Edit form correctly displays any unit value
    - **Property 1: Edit form correctly displays any unit value**
    - **Validates: Requirements 2.4, 2.5, 4.1, 4.3**
    - Use fast-check to generate random unit strings, render the edit form, assert value is shown and legacy items get "(legacy)" label

  - [ ]* 5.4 Write property test: Legacy value removed after replacement
    - **Property 4: Legacy value removed after replacement**
    - **Validates: Requirements 4.5**
    - Use fast-check to generate legacy unit strings, simulate saving a standard value, re-render and assert legacy option is gone

  - [ ]* 5.5 Write unit tests for the dropdown component
    - Test UNIT_OPTIONS constant contains correct values and labels
    - Test form renders a Select component (not TextField) for unit field
    - Test default selection is "units" in create mode
    - Test grid layout props are preserved (xs=12, sm=6, md=3)
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.3, 2.6_

- [x] 6. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The migration is metadata-only (no data transformation, no DB constraint) ensuring zero-risk deployment
- Frontend and backend unit option lists must stay in sync (same values, same order)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "4.1"] },
    { "id": 1, "tasks": ["1.2", "2.1", "5.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "2.4", "5.2"] },
    { "id": 3, "tasks": ["5.3", "5.4", "5.5"] }
  ]
}
```
