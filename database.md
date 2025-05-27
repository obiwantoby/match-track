# Database Structure

## Overview

The application uses MongoDB, a NoSQL database, for data storage. This allows for a flexible schema that can adapt to evolving requirements. Below is a detailed description of the data structure.

## Collections

### Users
- Manages authentication and authorization
- Stores user credentials and role information

```json
{
  "_id": ObjectId,
  "email": String,
  "username": String,
  "password": String (hashed),
  "role": String (enum: "admin", "reporter"),
  "created_at": DateTime
}
```

### Shooters
- Stores information about individual shooters
- Includes identification and organization membership details

```json
{
  "_id": ObjectId,
  "name": String,
  "nra_number": String (optional),
  "cmp_number": String (optional),
  "additional_info": String (optional),
  "created_at": DateTime
}
```

### Matches
- Contains match configuration and structure information
- Defines the types of competitions and eligible calibers

```json
{
  "_id": ObjectId,
  "name": String,
  "date": Date,
  "location": String,
  "match_types": [
    {
      "instance_name": String,
      "type": String (enum: "NMC", "900", "Presidents", etc.),
      "calibers": [String],
      "stages": [
        {
          "name": String,
          "max_score": Number,
          "max_x_count": Number
        }
      ]
    }
  ],
  "aggregate_type": String (optional),
  "year": Number,
  "created_at": DateTime
}
```

### Scores
- Records individual scores by shooter, match, match type, and caliber
- Includes stage-by-stage breakdown of points and X counts

```json
{
  "_id": ObjectId,
  "match_id": ObjectId,
  "shooter_id": ObjectId,
  "match_type": String,
  "caliber": String,
  "total_score": Number,
  "total_x_count": Number,
  "stages": [
    {
      "name": String,
      "score": Number,
      "x_count": Number
    }
  ],
  "created_at": DateTime,
  "updated_at": DateTime
}
```

## Relationships

- **Users to Scores**: Users with the "admin" role can create and edit scores
- **Shooters to Scores**: Each score is associated with exactly one shooter
- **Matches to Scores**: Scores are grouped by match
- **Match Types to Scores**: Scores are recorded for specific match types within a match

## Indexing Strategy

To optimize query performance, the database uses the following indexes:

- `scores`: Compound index on `match_id` and `shooter_id`
- `matches`: Index on `date` and `year`
- `shooters`: Index on `name` for quick search

## Aggregation Pipelines

The application uses MongoDB's aggregation framework for complex operations:

1. **Match Reports**: Aggregates scores by match, grouping by shooter
2. **Shooter Reports**: Aggregates scores by shooter, grouping by match
3. **Average Statistics**: Calculates averages using the `$avg` operator grouped by caliber and match type
