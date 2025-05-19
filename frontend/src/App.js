<file>
      <absolute_file_name>/app/frontend/src/App.js</absolute_file_name>
      <content_update>
        <find>              <Route 
                path="/admin/users" 
                element={<ProtectedRoute adminOnly={true}><UserManagement /></ProtectedRoute>} 
              /></find>
        <replace>              <Route 
                path="/admin/users" 
                element={<ProtectedRoute adminOnly={true}><UserManagement /></ProtectedRoute>} 
              />
              <Route 
                path="/change-password" 
                element={<ProtectedRoute><ChangePassword /></ProtectedRoute>} 
              /></replace>
      </content_update>
    </file>