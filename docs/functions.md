# Application Functions

This document provides a map of the key functions in the Match Score Tracker application, organized by component and purpose.

## Core Business Logic Functions (`core.py`)

### Match Configuration Functions
- `get_stages_for_match_type(match_type)`: Returns stage names and subtotal structure for NMC, 600, 900, Presidents matches
- `get_match_type_max_score(match_type)`: Returns maximum possible score for each match type

### Calculation Functions
- `calculate_aggregates(scores, match)`: Calculates 1800 and 2700 aggregate scores based on match configuration
- `calculate_shooter_averages_by_caliber(scores)`: Computes shooter performance averages grouped by caliber
- `calculate_score_subtotals(score_obj, stages_config)`: Calculates subtotals for multi-stage matches (like 900-yard)

### Aggregate Helper Functions
- `_get_aggregate_components(aggregate_type)`: Returns base match type and required sub-fields for aggregates
- `_get_ordered_calibers_for_aggregate(match_obj, base_match_type)`: Gets calibers in proper order for aggregate reporting

## Authentication Functions (`auth.py`)

### User Management
- `get_password_hash(password)`: Hashes passwords using bcrypt
- `verify_password(plain_password, hashed_password)`: Verifies password against hash
- `create_access_token(data, expires_delta)`: Generates JWT tokens with expiration
- `get_current_user(token)`: Validates JWT and returns user information
- `get_current_active_user(current_user)`: Ensures user account is active
- `get_admin_user(current_user)`: Verifies admin role permissions

### API Authentication Endpoints
- `POST /api/auth/token`: Login endpoint returning JWT token
- `POST /api/auth/register`: User registration with role assignment
- `GET /api/auth/me`: Current user profile information
- `POST /api/auth/change-password`: Password update functionality

## Database Functions (`database.py`)

### Connection Management
- `connect_to_mongo()`: Establishes MongoDB connection using Motor async client
- `close_mongo_connection()`: Properly closes database connections
- `get_database()`: Returns configured database instance

## Excel Export Functions (`server.py`)

### Dynamic Header Builders

#### `_build_dynamic_aggregate_header_and_calibers(match_obj)`
**Purpose**: Creates dual-row headers for aggregate match reports with proper caliber grouping
**Header Structure for Aggregates**:
- **Row 1 (Caliber Row)**: `["Shooter", "Agg Total", ".22", "", "", "CF", "", "", ...]`
  - Column A: "Shooter" 
  - Column B: "Agg Total"
  - Column C+: Caliber names with empty cells for sub-fields
- **Row 2 (Fields Row)**: `["", "", "SF", "TF", "900", "SF", "TF", "900", ...]`
  - Column A-B: Empty (under "Shooter" and "Agg Total")
  - Column C+: Sub-field names repeating per caliber

**Cell Merging Logic**:
- Caliber names are merged across their sub-field columns
- Example: ".22" merges from Column C to E (3 sub-fields: SF, TF, 900)
- Merge calculations: `start_col + len(agg_sub_fields) - 1`

#### `_build_dynamic_non_aggregate_header(match_obj)`
**Purpose**: Creates single-row headers for individual match reports maintaining score entry order
**Header Structure**: `["Shooter", "Average", "NMC1 (CF)", "NMC2 (CF)", ...]`
- Preserves exact match creation order (no sorting)
- Uses `match_obj.match_types` and `mt.calibers` in original sequence
- Format: `{instance_name} ({caliber_value})`

### Row Building Functions

#### `build_aggregate_row_grouped(shooter, shooter_data, report_data, ordered_calibers, agg_sub_fields, base_match_type)`
**Purpose**: Builds Excel rows for aggregate matches with subtotals and totals
**Row Structure**: `[shooter_name, agg_total, sf_score_22, tf_score_22, total_900_22, sf_score_cf, ...]`
**Column Mapping Logic**:
- Column 1: Shooter name
- Column 2: Aggregate total score
- Column 3+: Scores organized by caliber, then by sub-field
- **Sub-field Pattern**: For each caliber: [SF, TF, Total] repeating
- **Indexing**: Uses `STANDARD_CALIBER_ORDER_MAP` for consistent caliber sequence

#### `build_non_aggregate_row(shooter, shooter_data, match_obj)`
**Purpose**: Builds Excel rows for individual matches preserving match type instance order
**Row Structure**: `[shooter_name, average, score1, score2, ...]`
**Column Mapping**:
- Column 1: Shooter name
- Column 2: Calculated average across all scored entries
- Column 3+: Scores in match type instance creation order
- **Score Format**: `"Score (XCount)X"` or `"-"` for not shot
- **Null Handling**: Uses `"-"` for missing scores, DNS, or DNF

### Excel Export Endpoint: `GET /api/match-report/{match_id}/excel`

#### **Workbook Structure**
- **Main Sheet**: Summary report with all shooters
- **Detail Sheets**: Individual breakdown per shooter per match type instance

#### **Main Sheet Formatting Logic**

**Title Section** (Rows 1-6):
- Row 1: Match title (merged A1:G1, bold, 16pt, center-aligned)
- Rows 3-6: Match metadata (name, date, location, aggregate type)

**Header Section Indexing**:
- **Aggregate Matches** (2-row headers):
  - `header_offset = 2`
  - `current_header_start_row = 8` (after title section + empty row)
  - **Row 8**: Caliber names with merging
  - **Row 9**: Sub-field names (SF, TF, 900)
- **Non-Aggregate Matches** (1-row header):
  - `header_offset = 1`
  - `current_header_start_row = 8`
  - **Row 8**: Match type instance names

**Data Section**:
- `data_start_excel_row = current_header_start_row + header_offset`
- Aggregate: Data starts at Row 10
- Non-aggregate: Data starts at Row 9

#### **Cell Styling Application**

**Header Styling Logic**:
```python
# For aggregate dual headers:
if r_idx_offset == 0:  # Caliber row (Row 8)
    if col_idx_excel in caliber_start_cols_excel:
        # Style caliber name cells: bold, left-aligned, bordered
    elif col_idx_excel <= 2:
        # No border for "Shooter"/"Agg Total" in caliber row
    else:
        # Border only for blank cells under merged caliber names
else:  # Fields row (Row 9)
    # All cells: bold, bordered, center-aligned
```

**Column Width Auto-Adjustment**:
- Column A (Shooter): 25 characters
- Column B (Aggregate/Average): 18 characters  
- Columns C+ (Scores): 12 characters default

**Border Application**:
- Headers: `thin_border` on all styled cells
- Data: `thin_border` applied to all data cells
- Alignment: Score columns center-aligned, shooter names left-aligned

#### **Cell Merging for Aggregate Headers**
**Merge Range Calculation**:
```python
# For each caliber in ordered_calibers_for_agg:
start_col_merge = 3  # Column C
for caliber in ordered_calibers_for_agg:
    if len(agg_sub_fields) > 1:  # Only merge if multiple sub-fields
        end_col_merge = start_col_merge + len(agg_sub_fields) - 1
        # Merge caliber name across its sub-field columns
        ws.merge_cells(start_row=8, start_column=start_col_merge, 
                      end_row=8, end_column=end_col_merge)
    start_col_merge += len(agg_sub_fields)  # Move to next caliber
```

#### **Total Column Bolding Logic**
**Identification of Total Columns**:
- For aggregates: Find columns containing total field name (e.g., "900", "600")
- **Algorithm**: Search `header_row_for_styling_and_cols` for `agg_sub_fields[-1]`
- **Application**: Bold font applied to data cells in identified total columns

#### **Detail Sheet Generation**
**Sheet Creation Logic**:
- One sheet per shooter per match type instance with scores
- **Sheet Naming**: `{shooter_name}_{instance_name}_{caliber}`
- **Content**: Stage-by-stage breakdown with totals
- **Formatting**: Headers bold, score columns center-aligned, borders on all cells

#### **Data Population Indexing**
**Row Building Process**:
1. **Header Row Addition**: `ws.append(header_content)`
2. **Data Row Iteration**: Loop through `sorted_shooters_in_report`
3. **Row Content Building**: Call appropriate row builder function
4. **Cell Value Assignment**: `ws.cell(row=data_start_excel_row + idx, column=col_idx, value=value)`
5. **Post-Processing**: Apply styling, borders, and column bolding

**Error Handling in Excel Generation**:
- Missing scores: Display as `"-"`
- Null values: Converted to `"-"` for display
- Invalid data: Graceful degradation with placeholder values

## API Endpoint Functions (`server.py`)

### Shooter Management
- `POST /api/shooters`: Create new shooter with validation
- `GET /api/shooters`: Retrieve all shooters
- `GET /api/shooters/{shooter_id}`: Get individual shooter details

### Match Management  
- `POST /api/matches`: Create match with match type instances and calibers
- `GET /api/matches`: Retrieve all matches with optional filtering
- `GET /api/matches/{match_id}`: Get detailed match information
- `GET /api/match-types`: Return available BasicMatchType enum values
- `GET /api/match-config/{match_id}`: Get match configuration for score entry

### Score Management
- `POST /api/scores`: Create new score with stage breakdown
- `PUT /api/scores/{score_id}`: Update existing score records
- `GET /api/scores`: Get scores filtered by match_id and/or shooter_id
- `GET /api/scores/{score_id}`: Retrieve specific score details

### Report Generation
- `GET /api/match-report/{match_id}`: Generate comprehensive match report with:
  - Individual shooter scores
  - Aggregate calculations
  - Winner determinations
  - Average calculations
- `GET /api/shooter-report/{shooter_id}`: Individual shooter performance across matches
- `GET /api/shooter-averages/{shooter_id}`: Shooter statistics by caliber and match type

### System Management (Admin Only)
- `GET /api/users`: List all system users
- `PUT /api/users/{user_id}`: Update user information and roles
- `DELETE /api/users/{user_id}`: Remove user accounts
- `POST /api/reset-database`: Clear all data (development/testing)

## Data Validation Functions

### Pydantic Models
- `ShooterBase`, `Shooter`: Shooter data validation with rating enums
- `MatchBase`, `Match`: Match configuration validation
- `MatchTypeInstance`: Match type instance with caliber validation
- `ScoreBase`, `Score`: Score entry validation with stage structure
- `UserBase`, `User`: User account validation

### Score Processing
- Automatic total calculation from stage scores
- X-count aggregation across stages
- "Not shot" flag handling for DNS/DNF scenarios
- Stage-by-stage score validation

## Frontend Helper Functions (React Components)

### Score Entry Management
- Stage-by-stage score input with real-time totals
- Match type instance navigation
- Caliber selection and validation
- "Not Shot" toggle functionality

### Report Display Functions
- Dynamic table generation based on match type
- Score formatting with X-count display
- Average calculation display
- Winner highlighting and sorting

### Excel Export Utilities
- Download trigger with proper MIME types
- Filename generation with match names and dates
- Error handling for export failures

## Utility Functions

### Data Formatting
- Score display: "Score (XCount)" format
- Date formatting for displays and filenames
- Caliber name standardization
- Match type display names

### Constants and Enums
- `STANDARD_CALIBER_ORDER_MAP`: Defines caliber sorting order for consistent display
- Enum definitions for match types, calibers, ratings, and user roles
- Maximum score definitions per match type

### Error Handling
- HTTP exception handling with proper status codes
- Database connection error management
- Authentication failure responses
- Validation error formatting

## Performance Optimization Functions

### Database Operations
- Compound indexing strategies for efficient queries
- Aggregation pipeline optimization for reports
- Async database operations using Motor

### Caching and Efficiency
- JWT token validation caching
- Match configuration caching for score entry
- Efficient score aggregation algorithms
