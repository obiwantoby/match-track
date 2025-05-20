# Match Report Display Fix for Service Pistol and Service Revolver

## Issue Description

The match summary page was correctly showing the 1800 (2x900) aggregate totals, but the individual match scores for 9001 (Service Pistol) and 9002 (Service Revolver) were showing as "-" despite the Excel report correctly displaying these scores.

## Root Cause

The issue stemmed from a mismatch between how caliber types are stored in the database and how they're displayed in the UI:

1. The backend was storing scores with keys like `9001_CaliberType.SERVICEPISTOL`
2. The frontend was looking for keys like `9001_Service Pistol`
3. The Excel export had special handling that correctly matched all formats, but the web UI's matching logic was more limited

## Changes Made

### 1. Enhanced Key Matching Logic

Added much more comprehensive key matching to handle both new and legacy caliber formats:

```javascript
const possibleKeys = [
  // Simple format: instance_caliber
  `${mt.instance_name}_${caliber}`,
  
  // Enum format: instance_CaliberType.ENUM
  `${mt.instance_name}_CaliberType.${caliber.replace(/[.]/g, '').toUpperCase()}`,
  
  // Special cases for specific calibers
  caliber === '.22' && `${mt.instance_name}_CaliberType.TWENTYTWO`,
  caliber === 'CF' && `${mt.instance_name}_CaliberType.CENTERFIRE`,
  caliber === '.45' && `${mt.instance_name}_CaliberType.FORTYFIVE`,
  caliber === 'Service Pistol' && `${mt.instance_name}_CaliberType.SERVICEPISTOL`,
  caliber === 'Service Revolver' && `${mt.instance_name}_CaliberType.SERVICEREVOLVER`,
  caliber === 'DR' && `${mt.instance_name}_CaliberType.DR`,
  
  // Legacy formats
  caliber === 'Service Pistol' && `${mt.instance_name}_9mm Service`,
  caliber === 'Service Pistol' && `${mt.instance_name}_45 Service`,
  caliber === 'Service Pistol' && `${mt.instance_name}_CaliberType.NINESERVICE`,
  caliber === 'Service Pistol' && `${mt.instance_name}_CaliberType.FORTYFIVESERVICE`
].filter(Boolean);
```

### 2. Improved Fallback Key Discovery

Enhanced the fallback key discovery logic to handle more formats:

```javascript
// Try one more option: see if any key contains both the instance name and caliber
if (!scoreData) {
  const relevantKeys = Object.keys(shooterData.scores).filter(key => 
    key.includes(mt.instance_name) && (
      // Direct caliber match
      key.includes(caliber) || 
      
      // Special caliber matches
      (caliber === '.22' && (
        key.includes('TWENTYTWO') || 
        key.includes('.22')
      )) ||
      (caliber === 'CF' && (
        key.includes('CENTERFIRE') || 
        key.includes('CF')
      )) ||
      (caliber === '.45' && (
        key.includes('FORTYFIVE') || 
        key.includes('.45')
      )) ||
      (caliber === 'Service Pistol' && (
        key.includes('SERVICEPISTOL') || 
        key.includes('Service Pistol') || 
        key.includes('9mm Service') || 
        key.includes('45 Service') ||
        key.includes('NINESERVICE') ||
        key.includes('FORTYFIVESERVICE')
      )) ||
      (caliber === 'Service Revolver' && (
        key.includes('SERVICEREVOLVER') || 
        key.includes('Service Revolver')
      )) ||
      (caliber === 'DR' && (
        key.includes('DR')
      ))
    )
  );
  
  if (relevantKeys.length > 0) {
    scoreData = shooterData.scores[relevantKeys[0]];
  }
}
```

### 3. Added Debugging Output

Added more console logging to help diagnose issues:

```javascript
// For debugging
console.log(`Looking for score with keys for ${mt.instance_name}_${caliber}:`, possibleKeys);
console.log("All available score keys:", Object.keys(shooterData.scores));
```

## How It Works Now

1. The match summary now shows all scores correctly:
   - Individual match scores (9001 Service Pistol, 9002 Service Revolver)
   - Aggregate scores (1800 2x900)

2. The UI handles all possible key formats for caliber types:
   - New standardized format: "Service Pistol"
   - Legacy formats: "9mm Service", "45 Service"  
   - Enum formats: "CaliberType.SERVICEPISTOL", "CaliberType.NINESERVICE"

3. Backward Compatibility:
   - The system will continue to work with both old and new formats
   - Existing match reports will display correctly
   - New match reports created with the updated caliber types will also display correctly

## Technical Note

This change only affects the display logic in the UI. The underlying data structure and storage format remain unchanged, ensuring that no data migration is needed.
