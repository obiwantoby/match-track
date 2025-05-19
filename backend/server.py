<file>
      <absolute_file_name>/app/backend/server.py</absolute_file_name>
      <content_update>
        <find>@auth_router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user</find>
        <replace>@auth_router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

@auth_router.post("/change-password", response_model=Dict[str, bool])
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user)
):
    # Get the user from database with the hashed password
    user_in_db = await db.users.find_one({"id": current_user.id})
    if not user_in_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify current password
    user_obj = UserInDB(**user_in_db)
    if not verify_password(password_data.current_password, user_obj.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Hash new password
    hashed_password = get_password_hash(password_data.new_password)
    
    # Update password
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {"hashed_password": hashed_password}}
    )
    
    return {"success": True}</replace>
      </content_update>
    </file>