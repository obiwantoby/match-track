import { useState, useEffect } from "react";
import axios from "axios";
import { useAuth } from "../App";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
// Check if BACKEND_URL already contains /api to avoid duplication
const API = BACKEND_URL.endsWith('/api') ? BACKEND_URL : `${BACKEND_URL}/api`;

const UserManagement = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState("");
  const { user: currentUser } = useAuth();

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        // Get the token from localStorage
        const token = localStorage.getItem('token');
        if (!token) {
          setError("Authentication required. Please log in again.");
          setLoading(false);
          return;
        }

        // Set authorization header
        const config = {
          headers: { Authorization: `Bearer ${token}` }
        };

        const response = await axios.get(`${API}/users`, config);
        setUsers(response.data);
        setLoading(false);
      } catch (err) {
        console.error("Error fetching users:", err);
        setError("Failed to load users. Please try again.");
        setLoading(false);
      }
    };

    fetchUsers();
  }, []);

  const handleDeleteUser = async (userId) => {
    // Don't allow deleting the current user
    if (userId === currentUser.id) {
      setError("You cannot delete your own account");
      return;
    }
    
    if (window.confirm("Are you sure you want to delete this user?")) {
      try {
        await axios.delete(`${API}/users/${userId}`);
        setUsers(users.filter(user => user.id !== userId));
        setSuccess("User deleted successfully");
        setTimeout(() => setSuccess(""), 3000);
      } catch (err) {
        console.error("Error deleting user:", err);
        setError("Failed to delete user. Please try again.");
      }
    }
  };

  const handleChangeRole = async (user) => {
    // Don't allow changing your own role
    if (user.id === currentUser.id) {
      setError("You cannot change your own role");
      return;
    }
    
    const newRole = user.role === "admin" ? "reporter" : "admin";
    
    try {
      const response = await axios.put(`${API}/users/${user.id}`, {
        ...user,
        role: newRole
      });
      
      // Update the user in the state
      setUsers(users.map(u => 
        u.id === user.id ? { ...u, role: newRole } : u
      ));
      
      setSuccess(`User role changed to ${newRole} successfully`);
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      console.error("Error updating user role:", err);
      setError("Failed to update user role. Please try again.");
    }
  };

  // Function to reset the database
  const handleDatabaseReset = async () => {
    if (window.confirm("Are you sure you want to reset the database? This will delete all matches, scores, and shooters.")) {
      try {
        await axios.post(`${API}/reset-database`);
        setSuccess("Database reset successfully!");
        setTimeout(() => {
          setSuccess("");
          // Refresh the page
          window.location.reload();
        }, 3000);
      } catch (err) {
        console.error("Error resetting database:", err);
        setError("Failed to reset database. Please try again.");
      }
    }
  };

  return (
    <div className="container mx-auto p-4">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">User Management</h1>
        <button 
          onClick={handleDatabaseReset}
          className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
        >
          Reset Database
        </button>
      </div>
      
      {error && (
        <div className="bg-red-100 text-red-700 p-3 rounded mb-4">
          {error}
        </div>
      )}
      
      {success && (
        <div className="bg-green-100 text-green-700 p-3 rounded mb-4">
          {success}
        </div>
      )}
      
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4">User List</h2>
        
        {loading ? (
          <p className="text-center text-gray-500">Loading users...</p>
        ) : users.length === 0 ? (
          <p className="text-center text-gray-500">No users found</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Username
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Email
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Role
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {users.map((user) => (
                  <tr key={user.id} className={user.id === currentUser.id ? "bg-blue-50" : ""}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {user.username}
                        {user.id === currentUser.id && (
                          <span className="ml-2 text-xs text-blue-600">(You)</span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-500">{user.email}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        user.role === "admin" ? "bg-green-100 text-green-800" : "bg-blue-100 text-blue-800"
                      }`}>
                        {user.role}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-4">
                      <button
                        onClick={() => handleChangeRole(user)}
                        disabled={user.id === currentUser.id}
                        className={`text-blue-600 hover:text-blue-900 ${
                          user.id === currentUser.id ? "opacity-50 cursor-not-allowed" : ""
                        }`}
                      >
                        {user.role === "admin" ? "Make Reporter" : "Make Admin"}
                      </button>
                      <button
                        onClick={() => handleDeleteUser(user.id)}
                        disabled={user.id === currentUser.id}
                        className={`text-red-600 hover:text-red-900 ${
                          user.id === currentUser.id ? "opacity-50 cursor-not-allowed" : ""
                        }`}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default UserManagement;