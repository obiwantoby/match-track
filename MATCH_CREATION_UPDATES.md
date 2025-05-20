# Match Creation Updates

## Changes Implemented

### 1. Updated Caliber Options

The caliber options in the match creation form have been updated to include only the following options:
- .22
- CF
- .45
- Service Pistol (simplified from 9mm Service and 45 Service)
- Service Revolver
- DR

### 2. Manual Sub-Match Naming

Added the ability to manually rename sub-matches during match creation:
- The auto-generation of names still works as before (e.g., "NMC1", "6001", etc.)
- A new text input field has been added to allow custom naming of each sub-match
- The default value of this field is the auto-generated name
- Users can change it to any custom name they prefer

## Implementation Details

### Updated Caliber Types in Backend

```python
# Caliber Type enumeration
class CaliberType(str, Enum):
    TWENTYTWO = ".22"
    CENTERFIRE = "CF"
    FORTYFIVE = ".45"
    SERVICEPISTOL = "Service Pistol"
    SERVICEREVOLVER = "Service Revolver"
    DR = "DR"
```

### Updated Frontend Match Creation Form

1. **Updated Caliber Buttons**
```javascript
{[".22", "CF", ".45", "Service Pistol", "Service Revolver", "DR"].map((caliber) => (
  <button
    key={caliber}
    type="button"
    onClick={() => toggleCaliber(index, caliber)}
    className={`px-2 py-1 rounded text-sm ${
      matchType.calibers.includes(caliber)
        ? "bg-blue-600 text-white"
        : "bg-gray-200 text-gray-700 hover:bg-gray-300"
    }`}
  >
    {caliber}
  </button>
))}
```

2. **Added Manual Sub-Match Naming**
```jsx
<div className="flex flex-col md:flex-row md:items-center gap-2">
  <div className="font-medium">{matchType.type}</div>
  <div className="flex items-center">
    <span className="text-gray-500 mr-2">Name:</span>
    <input
      type="text"
      value={matchType.instance_name}
      onChange={(e) => {
        const updatedTypes = [...newMatch.match_types];
        updatedTypes[index].instance_name = e.target.value;
        setNewMatch({
          ...newMatch,
          match_types: updatedTypes
        });
      }}
      className="border px-2 py-1 rounded text-sm"
      placeholder={`${matchType.type}${instanceCounter}`}
    />
  </div>
</div>
```

## Using the New Features

### Adding Match Types with Custom Names

1. Click the "+ [Match Type]" button to add a match type
2. The match type will be added with an auto-generated name (e.g., "NMC1")
3. You can now edit the name directly in the "Name:" text field
4. The custom name will be saved with the match

### Selecting Calibers

The caliber options have been updated. You can select:
- .22
- CF
- .45
- Service Pistol (which replaces both "9mm Service" and "45 Service")
- Service Revolver
- DR

## Notes on Backward Compatibility

- Existing matches with the old caliber types ("9mm Service" and "45 Service") will still display correctly in reports
- The backend enumeration has been updated to support the new caliber types
- The score display logic in match reports has been updated to handle both old and new caliber naming formats
