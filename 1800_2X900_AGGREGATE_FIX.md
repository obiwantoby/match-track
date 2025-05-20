# 1800 (2x900) Aggregate Display Fix

## Issue Description

The 1800 (2x900) aggregate scores were not displaying correctly in two places:

1. **Match Summary Page**: The 1800 (2x900) column was showing empty/blank values ("-") in the aggregate column.
2. **Excel Export**: The Excel report showed individual match scores but the 1800 (2x900) aggregate column was blank.

## Root Cause

The issue was that while the backend code had logic to calculate aggregates for 1800 (2x900) matches, the display components (both in the web UI and Excel export) were only checking for "1800 (3x600)" match types, but not for "1800 (2x900)" match types.

## Changes Made

### 1. Match Report Component (frontend/src/components/MatchReport.js)

**Before:**
```javascript
// For 1800 (3x600) match, we want to show the sum of all calibers
if (match.aggregate_type === "1800 (3x600)") {
  // Calculate grand total across all calibers
  let totalScore = 0;
  let totalXCount = 0;
  // ... calculation logic ...
}
```

**After:**
```javascript
// For 1800 (3x600) or 1800 (2x900) match, we want to show the sum of all calibers
if (match.aggregate_type === "1800 (3x600)" || match.aggregate_type === "1800 (2x900)") {
  // Calculate grand total across all calibers
  let totalScore = 0;
  let totalXCount = 0;
  // ... calculation logic ...
}
```

Also updated the same condition in the Aggregates tab to include the 1800 (2x900) type.

### 2. Excel Export (backend/server.py)

**Before:**
```python
# Add aggregate score if applicable
if match_obj.aggregate_type != "None":
    if match_obj.aggregate_type == "1800 (3x600)":
        # Calculate total across all calibers
        total_score = 0
        total_x_count = 0
        # ... calculation logic ...
```

**After:**
```python
# Add aggregate score if applicable
if match_obj.aggregate_type != "None":
    if match_obj.aggregate_type == "1800 (3x600)" or match_obj.aggregate_type == "1800 (2x900)":
        # Calculate total across all calibers
        total_score = 0
        total_x_count = 0
        # ... calculation logic ...
```

## How It Works Now

1. The Match Summary page now calculates and displays the total score for both 1800 (3x600) and 1800 (2x900) aggregates.
2. The Excel export now properly shows the 1800 (2x900) aggregate value in the aggregate column.

## Calculation Method

For both 1800 (3x600) and 1800 (2x900) aggregates, the total score is calculated as:
- The sum of all individual scores in the match
- The sum of X-counts from all individual scores

For example:
- 9001 (Service Pistol): 808 (28X)
- 9002 (Service Revolver): 772 (34X)
- 1800 (2x900) aggregate: 1580 (62X)

## Testing

You can verify the fix by:
1. Viewing a match with the 1800 (2x900) aggregate type in the web UI
2. Downloading the Excel report for the same match

Both should now display the correct aggregate score instead of showing a dash ("-").
