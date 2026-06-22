# Requirements Document

## Introduction

This feature converts the "Unit" field on the "New Stock Item" form from a free-text input into a dropdown select with predefined unit options. The current implementation allows users to type arbitrary text (with placeholder "e.g., units, kg, bags"), which leads to inconsistent data entry. A dropdown select ensures consistency and reduces user input errors.

## Glossary

- **Stock_Form**: The React form component (`StockFormPage.tsx`) used to create or edit stock items in the inventory management system.
- **Unit_Dropdown**: A `<select>` dropdown UI element replacing the current free-text input for the unit field.
- **Unit_Options**: The predefined list of valid unit values that users can select from.
- **StockItem_API**: The Django REST Framework endpoint (`/api/stock-items/`) that handles CRUD operations for stock items.
- **StockItem_Model**: The Django model (`inventory.models.StockItem`) storing inventory data including the unit field.

## Requirements

### Requirement 1: Predefined Unit Options List

**User Story:** As an inventory manager, I want a predefined list of unit options, so that all stock items use consistent unit values across the system.

#### Acceptance Criteria

1. THE Unit_Options SHALL include the following values in this display order: "units", "kg", "bags", "tonnes", "litres", "meters", "pieces", "boxes", "cartons", "pallets"
2. WHEN creating a new stock item, THE Unit_Dropdown SHALL use "units" as the default selected value
3. THE Unit_Options SHALL display the following human-readable labels alongside their values: "Units" for "units", "Kilograms (kg)" for "kg", "Bags" for "bags", "Tonnes" for "tonnes", "Litres" for "litres", "Meters" for "meters", "Pieces" for "pieces", "Boxes" for "boxes", "Cartons" for "cartons", "Pallets" for "pallets"

### Requirement 2: Frontend Dropdown Component

**User Story:** As an inventory manager, I want the Unit field to be a dropdown select instead of a free-text input, so that I can quickly select the correct unit without typing.

#### Acceptance Criteria

1. WHEN the Stock_Form renders, THE Unit_Dropdown SHALL display a Material UI select element populated with the following Unit_Options in this order: "units", "kg", "bags", "tonnes", "litres", "meters", "pieces", "boxes", "cartons", "pallets"
2. WHEN a user selects a value from the Unit_Dropdown, THE Stock_Form SHALL update the unit field state with the selected value
3. WHEN the Stock_Form renders for a new stock item, THE Unit_Dropdown SHALL pre-select "units" as the default value
4. WHEN editing an existing stock item, THE Unit_Dropdown SHALL pre-select the current unit value of that stock item
5. IF the existing stock item's unit value does not match any value in Unit_Options, THEN THE Unit_Dropdown SHALL display the existing value as a selected option appended to the list so that no data is lost
6. THE Unit_Dropdown SHALL maintain the same grid position and layout as the current text input (Grid size xs=12, sm=6, md=3)

### Requirement 3: Backend Validation

**User Story:** As a system administrator, I want the backend to validate unit values against the predefined list, so that invalid unit values cannot be persisted to the database.

#### Acceptance Criteria

1. WHEN a stock item creation or update request is received, THE StockItem_API SHALL validate the unit field value against the predefined Unit_Options list using a case-sensitive exact match
2. IF an invalid unit value is submitted, THEN THE StockItem_API SHALL return a 400 response with an error message indicating which values are accepted from the Unit_Options list
3. IF the unit field is omitted or submitted as an empty string in a creation request, THEN THE StockItem_API SHALL apply the default value "units"
4. THE StockItem_Model SHALL define unit choices as a set of constrained values matching the Unit_Options list, enforced at the Django model validation layer
5. WHEN a stock item with a legacy unit value (not in Unit_Options) is updated without changing the unit field, THE StockItem_API SHALL accept the request and preserve the existing unit value

### Requirement 4: Backward Compatibility with Existing Data

**User Story:** As a system administrator, I want existing stock items with non-standard unit values to remain accessible, so that no data is lost during the migration.

#### Acceptance Criteria

1. WHEN an existing stock item has a unit value not in the Unit_Options list, THE Unit_Dropdown SHALL display the existing legacy value as an additional selectable option appended to the Unit_Options list, visually distinguishable from standard options (e.g., suffixed with a label indicating it is a legacy value)
2. THE StockItem_Model migration SHALL NOT alter existing unit field values in the database and SHALL NOT add a database-level constraint that would invalidate existing rows
3. WHEN editing a stock item with a legacy unit value, THE Stock_Form SHALL pre-select the legacy value and allow the user to either keep the existing value or select a new value from Unit_Options
4. IF a stock item update request contains a legacy unit value that was already stored for that specific stock item, THEN THE StockItem_API SHALL accept the value without validation failure, bypassing the Unit_Options constraint for that item's pre-existing value
5. WHEN a user replaces a legacy unit value with a standard Unit_Options value and saves successfully, THE Stock_Form SHALL no longer display the previous legacy value as a selectable option for that stock item on subsequent edits
