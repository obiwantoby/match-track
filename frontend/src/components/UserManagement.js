<file>
      <absolute_file_name>/app/frontend/src/components/UserManagement.js</absolute_file_name>
      <content_update>
        <find>      {error && (
        <div className="bg-red-100 text-red-700 p-3 rounded mb-4">
          {error}
        </div>
      )}</find>
        <replace>      {error && (
        <div className="bg-red-100 text-red-700 p-3 rounded mb-4">
          {error}
        </div>
      )}
      
      {success && (
        <div className="bg-green-100 text-green-700 p-3 rounded mb-4">
          {success}
        </div>
      )}</replace>
      </content_update>
    </file>