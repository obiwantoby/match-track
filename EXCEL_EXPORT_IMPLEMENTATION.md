# Excel Export Implementation for Match Reports

## Overview

This feature adds the ability to export match reports as Excel files with comprehensive formatting and detailed score breakdowns.

## Implementation Details

### 1. Backend Changes

#### 1.1 Added Dependencies
```python
import io
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
from fastapi.responses import StreamingResponse
```

#### 1.2 New API Endpoint
Created a new endpoint that leverages the existing match-report data structure:

```python
@api_router.get("/match-report/{match_id}/excel")
async def get_match_report_excel(
    match_id: str,
    current_user: User = Depends(get_current_active_user)
):
    # Get the match report data from the existing endpoint
    report_data = await get_match_report(match_id, current_user)
    match_obj = report_data["match"]
    shooters_data = report_data["shooters"]
    
    # Create Excel workbook with formatting
    # ...
    
    # Return as a streaming download
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
```

### 2. Excel Report Structure

The Excel report is organized with multiple sheets:

#### 2.1 Summary Sheet
- Match information (name, date, location, aggregate type)
- Summary table with all shooters and their scores for each match type/caliber
- Aggregate scores column if applicable

#### 2.2 Individual Score Sheets
- One sheet per shooter containing their detailed scores
- Shooter information (name, NRA/CMP numbers if available)
- Detailed breakdown of scores by match type and caliber
- Stage-by-stage scores with totals

### 3. Frontend Changes

Added a "Download Excel Report" button on the match report page:

```jsx
<a 
  href={`${API}/match-report/${matchId}/excel`}
  className="bg-green-600 hover:bg-green-700 text-white py-2 px-4 rounded flex items-center justify-center"
  download
>
  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
  </svg>
  Download Excel Report
</a>
```

## Excel Report Features

### Formatting

- **Headers**: Bold white text on blue background
- **Borders**: All cells in tables have thin borders
- **Alignment**: Center alignment for numeric values
- **Merged Cells**: Used for section headers
- **Column Widths**: Auto-adjusted for better readability

### Data Handling

- Support for all caliber types including the new ones (.22, CF, .45, Service Pistol, Service Revolver, DR)
- Legacy format compatibility for old caliber types (9mm Service, 45 Service)
- Proper calculation of aggregate scores
- Detailed score breakdown by stage

### File Naming

The Excel file is named dynamically based on the match:
```
match_report_[Match Name]_[Date].xlsx
```

## Usage

1. Navigate to any match report
2. Click the "Download Excel Report" button
3. The browser will download the Excel file automatically
4. Open in any spreadsheet program (Microsoft Excel, Google Sheets, LibreOffice Calc)

## Benefits

- Professional-quality reports that can be printed or shared
- Comprehensive view of all match data in a single file
- Individual score sheets for each shooter
- Consistent formatting matching the web interface
