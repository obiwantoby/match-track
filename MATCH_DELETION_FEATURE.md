# Match Deletion Feature Documentation

## Overview

A new feature has been added to allow administrators to delete matches and all their associated data. This feature helps maintain data cleanliness by allowing the removal of unwanted or test matches while ensuring all related records are properly cleaned up.

## Implementation Details

### Backend Changes

A new DELETE endpoint has been added to the API:

```python
@api_router.delete("/matches/{match_id}")
async def delete_match(
    match_id: str,
    current_user: User = Depends(get_current_active_user)
):
    # Only admins can delete matches
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete matches")
    
    # Find the match to ensure it exists
    match = await db.matches.find_one({"id": match_id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Delete all scores associated with this match
    delete_scores_result = await db.scores.delete_many({"match_id": match_id})
    
    # Delete match configuration
    await db.match_configs.delete_many({"match_id": match_id})
    
    # Delete the match itself
    delete_match_result = await db.matches.delete_one({"id": match_id})
    
    if delete_match_result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Failed to delete match")
    
    return {
        "success": True,
        "message": f"Match deleted successfully along with {delete_scores_result.deleted_count} related scores"
    }
```

### Frontend Changes

Added a Delete button in the match list for administrators only:

```jsx
<button
  onClick={() => {
    if (window.confirm(`Are you sure you want to delete the match "${match.name}"? This will also delete all scores associated with this match and cannot be undone.`)) {
      axios.delete(`${API}/matches/${match.id}`)
        .then(() => {
          setMatches(matches.filter(m => m.id !== match.id));
          alert(`Match "${match.name}" deleted successfully`);
        })
        .catch(err => {
          console.error("Error deleting match:", err);
          alert("Failed to delete match. Please try again.");
        });
    }
  }}
  className="text-red-600 hover:text-red-900"
>
  Delete
</button>
```

## Data Management Considerations

When a match is deleted, the following associated data is also deleted:

1. **Scores**: All score records linked to the match
2. **Match Configuration**: The match configuration document

This cascading deletion ensures that no orphaned records remain in the database.

## Security Considerations

The match deletion feature is secured in several ways:

1. **Admin-Only Access**: Only users with the admin role can delete matches
2. **Confirmation Dialog**: Users must confirm deletion to prevent accidental data loss
3. **Descriptive Warning**: The confirmation message clearly explains what data will be deleted
4. **Server-Side Validation**: The backend verifies admin status again before performing the deletion

## User Experience

When an administrator views the matches list, they will see a red "Delete" button next to each match. Clicking this button:

1. Shows a confirmation dialog with details about what will be deleted
2. If confirmed, removes the match from the database and updates the UI
3. Shows a success message when deletion is complete

## Error Handling

The feature includes error handling at multiple levels:

1. **Backend**:
   - 403 error if a non-admin attempts to delete a match
   - 404 error if the match doesn't exist
   - 500 error if the deletion operation fails

2. **Frontend**:
   - Error messaging for failed API calls
   - Console logging for debugging purposes
   - User-friendly alerts

## Testing

To test this feature:

1. Log in as an admin user
2. Navigate to the Matches list
3. Locate a test match you want to delete
4. Click the Delete button
5. Confirm the deletion in the popup dialog
6. Verify the match is removed from the list
7. Verify that attempting to access the deleted match results in a "not found" error
