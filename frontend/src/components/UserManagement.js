import { useState, useEffect, useCallback, useRef } from "react";
import axios from "axios";
import { useAuth } from "../App";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = BACKEND_URL?.endsWith("/api") ? BACKEND_URL : `${BACKEND_URL}/api`;

const EMPTY_USER_FORM = {
  username: "",
  email: "",
  password: "",
  role: "reporter",
};

const SAMPLE_CSV = `username,email,password,role
jdoe,jdoe@example.com,changeme123,reporter
asmith,asmith@example.com,changeme123,admin
`;

function getAuthConfig(extraHeaders = {}) {
  const token = localStorage.getItem("token");
  if (!token) {
    return null;
  }
  return {
    headers: {
      Authorization: `Bearer ${token}`,
      ...extraHeaders,
    },
  };
}

const UserManagement = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState("");
  const [importResult, setImportResult] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newUser, setNewUser] = useState(EMPTY_USER_FORM);
  const fileInputRef = useRef(null);
  const { user: currentUser } = useAuth();

  const clearMessages = () => {
    setError(null);
    setSuccess("");
  };

  const showSuccess = (message) => {
    setSuccess(message);
    setTimeout(() => setSuccess(""), 4000);
  };

  const fetchUsers = useCallback(async () => {
    const config = getAuthConfig();
    if (!config) {
      setError("Authentication required. Please log in again.");
      setLoading(false);
      return;
    }

    try {
      const response = await axios.get(`${API}/users`, config);
      setUsers(response.data);
      setError(null);
    } catch (err) {
      console.error("Error fetching users:", err);
      setError(
        err.response?.data?.detail || "Failed to load users. Please try again."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleDeleteUser = async (userId) => {
    if (userId === currentUser.id) {
      setError("You cannot delete your own account");
      return;
    }

    if (!window.confirm("Are you sure you want to delete this user?")) {
      return;
    }

    const config = getAuthConfig();
    if (!config) {
      setError("Authentication required. Please log in again.");
      return;
    }

    try {
      clearMessages();
      await axios.delete(`${API}/users/${userId}`, config);
      setUsers((prev) => prev.filter((user) => user.id !== userId));
      showSuccess("User deleted successfully");
    } catch (err) {
      console.error("Error deleting user:", err);
      setError(
        err.response?.data?.detail || "Failed to delete user. Please try again."
      );
    }
  };

  const handleChangeRole = async (user) => {
    if (user.id === currentUser.id) {
      setError("You cannot change your own role");
      return;
    }

    const newRole = user.role === "admin" ? "reporter" : "admin";
    const config = getAuthConfig();
    if (!config) {
      setError("Authentication required. Please log in again.");
      return;
    }

    try {
      clearMessages();
      await axios.put(
        `${API}/users/${user.id}`,
        {
          email: user.email,
          username: user.username,
          role: newRole,
        },
        config
      );

      setUsers((prev) =>
        prev.map((u) => (u.id === user.id ? { ...u, role: newRole } : u))
      );
      showSuccess(`User role changed to ${newRole} successfully`);
    } catch (err) {
      console.error("Error updating user role:", err);
      setError(
        err.response?.data?.detail ||
          "Failed to update user role. Please try again."
      );
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    const config = getAuthConfig();
    if (!config) {
      setError("Authentication required. Please log in again.");
      return;
    }

    if (!newUser.username || !newUser.email || !newUser.password) {
      setError("Username, email, and password are required");
      return;
    }

    setCreating(true);
    clearMessages();
    setImportResult(null);

    try {
      const response = await axios.post(`${API}/users`, newUser, config);
      setUsers((prev) => [...prev, response.data]);
      setNewUser(EMPTY_USER_FORM);
      showSuccess(`User ${response.data.email} created successfully`);
    } catch (err) {
      console.error("Error creating user:", err);
      setError(
        err.response?.data?.detail || "Failed to create user. Please try again."
      );
    } finally {
      setCreating(false);
    }
  };

  const handleCsvUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) {
      return;
    }

    // Do not set Content-Type manually — the browser must add the multipart boundary.
    const config = getAuthConfig();
    if (!config) {
      setError("Authentication required. Please log in again.");
      e.target.value = "";
      return;
    }

    if (!file.name.toLowerCase().endsWith(".csv")) {
      setError("Please select a .csv file");
      e.target.value = "";
      return;
    }

    setUploading(true);
    clearMessages();
    setImportResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post(`${API}/users/bulk-csv`, formData, config);
      setImportResult(response.data);
      const { created, skipped, errors } = response.data;
      showSuccess(
        `CSV import finished: ${created} created, ${skipped} skipped, ${errors} errors`
      );
      if (created > 0) {
        await fetchUsers();
      }
    } catch (err) {
      console.error("Error uploading CSV:", err);
      setError(
        err.response?.data?.detail ||
          "Failed to import users from CSV. Please check the file format."
      );
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const downloadSampleCsv = () => {
    const blob = new Blob([SAMPLE_CSV], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "users_template.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleDatabaseReset = async () => {
    if (
      !window.confirm(
        "Are you sure you want to reset the database? This will delete all matches, scores, and shooters."
      )
    ) {
      return;
    }

    const config = getAuthConfig();
    if (!config) {
      setError("Authentication required. Please log in again.");
      return;
    }

    try {
      clearMessages();
      await axios.post(`${API}/reset-database`, {}, config);
      showSuccess("Database reset successfully!");
      setTimeout(() => {
        window.location.reload();
      }, 2000);
    } catch (err) {
      console.error("Error resetting database:", err);
      setError(
        err.response?.data?.detail ||
          "Failed to reset database. Please try again."
      );
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
        <div className="bg-red-100 text-red-700 p-3 rounded mb-4" role="alert">
          {typeof error === "string" ? error : JSON.stringify(error)}
        </div>
      )}

      {success && (
        <div className="bg-green-100 text-green-700 p-3 rounded mb-4" role="status">
          {success}
        </div>
      )}

      {/* Create single user */}
      <div className="bg-white p-6 rounded-lg shadow mb-6">
        <h2 className="text-xl font-semibold mb-4">Create User</h2>
        <form onSubmit={handleCreateUser} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label
                htmlFor="new-username"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Username
              </label>
              <input
                id="new-username"
                type="text"
                value={newUser.username}
                onChange={(e) =>
                  setNewUser((prev) => ({ ...prev, username: e.target.value }))
                }
                className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label
                htmlFor="new-email"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Email
              </label>
              <input
                id="new-email"
                type="email"
                value={newUser.email}
                onChange={(e) =>
                  setNewUser((prev) => ({ ...prev, email: e.target.value }))
                }
                className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label
                htmlFor="new-password"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Password
              </label>
              <input
                id="new-password"
                type="password"
                value={newUser.password}
                onChange={(e) =>
                  setNewUser((prev) => ({ ...prev, password: e.target.value }))
                }
                className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
                minLength={6}
              />
            </div>
            <div>
              <label
                htmlFor="new-role"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Role
              </label>
              <select
                id="new-role"
                value={newUser.role}
                onChange={(e) =>
                  setNewUser((prev) => ({ ...prev, role: e.target.value }))
                }
                className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="reporter">Reporter</option>
                <option value="admin">Admin</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={creating}
              className={`bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 ${
                creating ? "opacity-70 cursor-not-allowed" : ""
              }`}
            >
              {creating ? "Creating..." : "Create User"}
            </button>
          </div>
        </form>
      </div>

      {/* CSV bulk upload */}
      <div className="bg-white p-6 rounded-lg shadow mb-6">
        <h2 className="text-xl font-semibold mb-2">Bulk Import from CSV</h2>
        <p className="text-sm text-gray-600 mb-4">
          Upload a CSV with columns{" "}
          <code className="bg-gray-100 px-1 rounded">username</code>,{" "}
          <code className="bg-gray-100 px-1 rounded">email</code>,{" "}
          <code className="bg-gray-100 px-1 rounded">password</code>, and optional{" "}
          <code className="bg-gray-100 px-1 rounded">role</code> (
          <code className="bg-gray-100 px-1 rounded">admin</code> or{" "}
          <code className="bg-gray-100 px-1 rounded">reporter</code>). Existing
          emails are skipped.
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,text/csv"
            onChange={handleCsvUpload}
            className="hidden"
            id="user-csv-upload"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className={`bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 ${
              uploading ? "opacity-70 cursor-not-allowed" : ""
            }`}
          >
            {uploading ? "Uploading..." : "Upload CSV"}
          </button>
          <button
            type="button"
            onClick={downloadSampleCsv}
            className="bg-gray-200 text-gray-800 px-4 py-2 rounded hover:bg-gray-300"
          >
            Download Template
          </button>
        </div>

        {importResult && (
          <div className="mt-4 border rounded overflow-hidden">
            <div className="bg-gray-50 px-4 py-2 text-sm font-medium text-gray-700">
              Import results — {importResult.created} created,{" "}
              {importResult.skipped} skipped, {importResult.errors} errors
            </div>
            <div className="max-h-64 overflow-y-auto">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-white sticky top-0">
                  <tr>
                    <th className="px-4 py-2 text-left">Row</th>
                    <th className="px-4 py-2 text-left">Email</th>
                    <th className="px-4 py-2 text-left">Username</th>
                    <th className="px-4 py-2 text-left">Status</th>
                    <th className="px-4 py-2 text-left">Detail</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {importResult.results.map((row) => (
                    <tr key={`${row.row}-${row.email || ""}`}>
                      <td className="px-4 py-2">{row.row}</td>
                      <td className="px-4 py-2">{row.email || "—"}</td>
                      <td className="px-4 py-2">{row.username || "—"}</td>
                      <td className="px-4 py-2">
                        <span
                          className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                            row.status === "created"
                              ? "bg-green-100 text-green-800"
                              : row.status === "skipped"
                              ? "bg-yellow-100 text-yellow-800"
                              : "bg-red-100 text-red-800"
                          }`}
                        >
                          {row.status}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-gray-600">{row.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* User list */}
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
                  <tr
                    key={user.id}
                    className={user.id === currentUser.id ? "bg-blue-50" : ""}
                  >
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
                      <span
                        className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                          user.role === "admin"
                            ? "bg-green-100 text-green-800"
                            : "bg-blue-100 text-blue-800"
                        }`}
                      >
                        {user.role}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-4">
                      <button
                        onClick={() => handleChangeRole(user)}
                        disabled={user.id === currentUser.id}
                        className={`text-blue-600 hover:text-blue-900 ${
                          user.id === currentUser.id
                            ? "opacity-50 cursor-not-allowed"
                            : ""
                        }`}
                      >
                        {user.role === "admin" ? "Make Reporter" : "Make Admin"}
                      </button>
                      <button
                        onClick={() => handleDeleteUser(user.id)}
                        disabled={user.id === currentUser.id}
                        className={`text-red-600 hover:text-red-900 ${
                          user.id === currentUser.id
                            ? "opacity-50 cursor-not-allowed"
                            : ""
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
