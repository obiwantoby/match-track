# 900 Match Type Scoring Changes

## Overview of Changes

We've modified how the 900 match type scoring works to allow manual entry of SFNMC, TFNMC, and RFNMC values instead of automatically calculating them. This change gives users more control and flexibility in how they score 900 matches.

## Technical Changes Made

### 1. Backend Changes

In `server.py`, we updated the match type configuration for 900 matches:

**Before:**
```python
elif match_type == BasicMatchType.NINEHUNDRED:
    # Modified to include SFNMC, TFNMC, RFNMC in entry_stages
    # When entering scores, users will still only enter SF1, SF2, TF1, TF2, RF1, RF2
    # SFNMC, TFNMC, RFNMC will be automatically calculated
    return {
        "entry_stages": ["SF1", "SF2", "TF1", "TF2", "RF1", "RF2"],
        "subtotal_stages": ["SFNMC", "TFNMC", "RFNMC"],
        "subtotal_mappings": {
            "SFNMC": ["SF1", "SF2"],
            "TFNMC": ["TF1", "TF2"],
            "RFNMC": ["RF1", "RF2"],
        },
        "max_score": 900,
    }
```

**After:**
```python
elif match_type == BasicMatchType.NINEHUNDRED:
    # Modified to include SFNMC, TFNMC, RFNMC as entry stages
    # All values will be entered manually by users (SF1, SF2, TF1, TF2, RF1, RF2, SFNMC, TFNMC, RFNMC)
    # No automatic calculation of subtotals
    return {
        "entry_stages": ["SF1", "SF2", "TF1", "TF2", "RF1", "RF2", "SFNMC", "TFNMC", "RFNMC"],
        "subtotal_stages": [],
        "subtotal_mappings": {},
        "max_score": 900,
    }
```

### 2. Frontend Changes

#### ScoreEntry.js

1. Removed the special `calculate900Total` function that automatically calculated SFNMC, TFNMC, and RFNMC values
2. Modified the total calculation to use the standard `calculateTotals` function for all match types
3. Removed the informational message about 900 match type totals

#### EditScore.js

1. Removed the special `calculate900Total` function
2. Removed the `is900` variable that identified 900 match types
3. Changed total calculation to always use standard `calculateTotals` function
4. Removed the informational message about 900 match type totals

## How This Works Now

1. When scoring a 900 match, users will see input fields for:
   - SF1
   - SF2
   - TF1
   - TF2
   - RF1
   - RF2
   - SFNMC
   - TFNMC
   - RFNMC

2. Users can directly input all values, including the SFNMC, TFNMC, and RFNMC fields

3. The total score is now simply the sum of all stage scores without any special calculation for 900 matches

## Benefits of This Change

1. **More Flexibility**: Users can enter the exact values they want for SFNMC, TFNMC, and RFNMC
2. **Manual Correction**: Users can adjust subtotals if needed without being constrained by automatic calculation
3. **Simpler Code**: Removing the special calculation logic makes the code more maintainable

## How to Get to 900

For a complete score in a 900 match:

1. Enter scores for the basic stages (SF1, SF2, TF1, TF2, RF1, RF2)
2. Enter scores for the NMC subtotals (SFNMC, TFNMC, RFNMC)
3. The total will be the sum of all entered values

For example:
- SF1: 100
- SF2: 98
- TF1: 97
- TF2: 99
- RF1: 96
- RF2: 95
- SFNMC: 198 (could be SF1 + SF2 but can be any value)
- TFNMC: 196 (could be TF1 + TF2 but can be any value)
- RFNMC: 191 (could be RF1 + RF2 but can be any value)

The total score would be the sum of all these values.