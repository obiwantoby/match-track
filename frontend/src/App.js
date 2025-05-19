<file>
      <absolute_file_name>/app/frontend/src/App.js</absolute_file_name>
      <content_update>
        <find>          {user ? (
          <div className="flex items-center">
            <div className="flex space-x-4 mr-6">
              <Link to="/" className="hover:text-gray-300">Home</Link>
              <Link to="/shooters" className="hover:text-gray-300">Shooters</Link>
              <Link to="/matches" className="hover:text-gray-300">Matches</Link>
              {isAdmin() && (
                <Link to="/admin/users" className="hover:text-gray-300">Users</Link>
              )}
            </div>
            
            <div className="flex items-center">
              <span className="mr-2 text-sm bg-blue-600 px-2 py-1 rounded text-white">
                {isAdmin() ? 'Admin' : 'Reporter'}
              </span>
              <button 
                onClick={handleLogout}
                className="bg-red-600 text-white text-sm px-3 py-1 rounded hover:bg-red-700"
              >
                Logout
              </button>
            </div>
          </div>)</find>
        <replace>          {user ? (
          <div className="flex items-center">
            <div className="flex space-x-4 mr-6">
              <Link to="/" className="hover:text-gray-300">Home</Link>
              <Link to="/shooters" className="hover:text-gray-300">Shooters</Link>
              <Link to="/matches" className="hover:text-gray-300">Matches</Link>
              {isAdmin() && (
                <Link to="/admin/users" className="hover:text-gray-300">Users</Link>
              )}
              <Link to="/change-password" className="hover:text-gray-300">Change Password</Link>
            </div>
            
            <div className="flex items-center">
              <span className="mr-2 text-sm bg-blue-600 px-2 py-1 rounded text-white">
                {isAdmin() ? 'Admin' : 'Reporter'}
              </span>
              <button 
                onClick={handleLogout}
                className="bg-red-600 text-white text-sm px-3 py-1 rounded hover:bg-red-700"
              >
                Logout
              </button>
            </div>
          </div>)</replace>
      </content_update>
    </file>