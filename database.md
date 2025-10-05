### Shooters
- Stores information about individual shooters
- Includes identification and organization membership details

```json
{
  "_id": ObjectId,
  "id": String,  // UUID string
  "name": String,
  "nra_number": String (optional),
  "cmp_number": String (optional),
  "rating": String (optional, enum: "HM", "MA", "EX", "SS", "MK", "UNC"),
  "created_at": DateTime
}
```

### Matches
- Contains match configuration and structure information
- Defines the types of competitions and eligible calibers

```json
{
  "_id": ObjectId,
  "id": String,  // UUID string
  "name": String,
  "date": DateTime,
  "location": String,
  "match_types": [
    {
      "type": String (enum: "NMC", "600", "900", "Presidents"),
      "instance_name": String,  // e.g., "NMC1", "600_1"
      "calibers": [String]  // enum: ".22", "CF", ".45", "Service Pistol", "Service Revolver", "DR"
    }
  ],
  "aggregate_type": String (enum: "None", "1800 (2x900)", "1800 (3x600)", "2700 (3x900)"),
  "created_at": DateTime
}
```

### Scores
- Records individual scores by shooter, match, match type instance, and caliber
- Includes stage-by-stage breakdown of points and X counts

```json
{
  "_id": ObjectId,
  "id": String,  // UUID string
  "shooter_id": String,  // UUID reference
  "match_id": String,   // UUID reference
  "match_type_instance": String,  // e.g., "NMC1", "600_1"
  "caliber": String,    // enum value
  "stages": [
    {
      "name": String,   // e.g., "SF", "TF1", "RF2"
      "score": Number (optional),
      "x_count": Number (optional)
    }
  ],
  "total_score": Number (optional),
  "total_x_count": Number (optional),
  "not_shot": Boolean (default: false),
  "created_at": DateTime
}
```

## Enums and Constants

### BasicMatchType
- `"NMC"`: National Match Course
- `"600"`: 600 yard match
- `"900"`: 900 yard match  
- `"Presidents"`: Presidents match

### CaliberType
- `".22"`: .22 caliber
- `"CF"`: Centerfire
- `".45"`: .45 caliber
- `"Service Pistol"`: Service Pistol
- `"Service Revolver"`: Service Revolver
- `"DR"`: Distinguished Revolver

### AggregateType
- `"None"`: No aggregate scoring
- `"1800 (2x900)"`: 1800 point aggregate from two 900s
- `"1800 (3x600)"`: 1800 point aggregate from three 600s
- `"2700 (3x900)"`: 2700 point aggregate from three 900s

### Rating
- `"HM"`: High Master
- `"MA"`: Master
- `"EX"`: Expert
- `"SS"`: Sharpshooter
- `"MK"`: Marksman
- `"UNC"`: Unclassified

### UserRole
- `"admin"`: Full system access
- `"reporter"`: Read-only access

## Relationships

- **Users to Operations**: Users with "admin" role can create/edit all data; "reporter" role has read-only access
- **Shooters to Scores**: Each score belongs to exactly one shooter (via shooter_id UUID)
- **Matches to Scores**: Scores are grouped by match (via match_id UUID)
- **Match Type Instances to Scores**: Scores are recorded for specific match type instances within a match
- **UUID References**: All relationships use UUID strings rather than MongoDB ObjectIds for cross-collection references

## Indexing Strategy

Recommended indexes for optimal query performance:

- **scores collection**:
  - Compound index: `{match_id: 1, shooter_id: 1}`
  - Index: `{match_type_instance: 1, caliber: 1}`
- **matches collection**: 
  - Index: `{date: 1}`
  - Index: `{aggregate_type: 1}`
- **shooters collection**: 
  - Index: `{name: 1}` for search functionality
- **users collection**: 
  - Unique index: `{email: 1}`
  - Index: `{username: 1}`
```