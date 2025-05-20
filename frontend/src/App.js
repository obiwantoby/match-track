import { useState, useEffect, createContext, useContext } from "react";
import { BrowserRouter, Routes, Route, Link, useNavigate, useParams, Navigate } from "react-router-dom";
import axios from "axios";
import "./App.css";
import UserManagement from "./components/UserManagement";
import ShooterDetail from "./components/ShooterDetail";
import MatchReport from "./components/MatchReport";
import ScoreEntry from "./components/ScoreEntry";
import EditScore from "./components/EditScore";
import ChangePassword from "./components/ChangePassword";

// Get Backend URL from environment variable
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// Check if BACKEND_URL already contains /api to avoid duplication
const API = BACKEND_URL.endsWith('/api') ? BACKEND_URL : `${BACKEND_URL}/api`;
const AUTH_API = `${API}/auth`;

// Create Auth Context
const AuthContext = createContext(null);

// Auth Provider Component
const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadUser = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          // Set default auth header
          axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
          
          // Fetch user data
          const response = await axios.get(`${AUTH_API}/me`);
          setUser({
            ...response.data,
            token
          });
        } catch (error) {
          console.error("Auth error:", error);
          localStorage.removeItem('token');
          delete axios.defaults.headers.common['Authorization'];
        }
      }
      setLoading(false);
    };

    loadUser();
  }, []);

  const login = async (email, password) => {
    try {
      console.log("Attempting login for:", email);
      
      // Create form data for token request
      const formData = new FormData();
      formData.append('username', email);  // Note: API expects email in the username field
      formData.append('password', password);
      
      // Get token
      const response = await axios.post(`${AUTH_API}/token`, formData);
      console.log("Login successful, token received");
      
      // Store token in localStorage
      localStorage.setItem('token', response.data.access_token);
      
      // Set default auth header
      axios.defaults.headers.common['Authorization'] = `Bearer ${response.data.access_token}`;
      
      // Save user data
      setUser({
        id: response.data.user_id,
        role: response.data.role,
        token: response.data.access_token
      });
      
      console.log("User authenticated with role:", response.data.role);
      return true;
    } catch (error) {
      console.error("Login error:", error);
      if (error.response && error.response.data) {
        console.error("Login error details:", error.response.data);
      }
      return false;
    }
  };

  const logout = () => {
    // Remove token from localStorage
    localStorage.removeItem('token');
    
    // Remove auth header
    delete axios.defaults.headers.common['Authorization'];
    
    // Clear user data
    setUser(null);
  };

  const register = async (username, email, password) => {
    try {
      console.log("Registering user:", email);
      const response = await axios.post(`${AUTH_API}/register`, {
        username,
        email,
        password,
        role: "reporter"  // Default role for new users
      });
      
      console.log("Registration successful, response:", response.data);
      
      // Auto login after registration
      return await login(email, password);
    } catch (error) {
      console.error("Registration error:", error);
      if (error.response && error.response.data) {
        console.error("Registration error details:", error.response.data);
      }
      return false;
    }
  };

  const isAdmin = () => {
    return user && user.role === "admin";
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, register, isAdmin, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

// Custom hook to use the auth context
export const useAuth = () => {
  return useContext(AuthContext);
};

// Protected Route Component
const ProtectedRoute = ({ children, adminOnly = false }) => {
  const { user, loading, isAdmin } = useAuth();
  const navigate = useNavigate();
  
  useEffect(() => {
    // If not loading and not authenticated, redirect to login
    if (!loading && !user) {
      navigate('/login');
    }
    
    // If authenticated but not admin and route requires admin, redirect to unauthorized
    if (!loading && user && adminOnly && !isAdmin()) {
      navigate('/unauthorized');
    }
  }, [user, loading, adminOnly, isAdmin, navigate]);
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <svg className="animate-spin h-10 w-10 text-blue-600 mx-auto mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }
  
  if (!user) {
    return null; // Will be redirected by the useEffect
  }
  
  if (adminOnly && !isAdmin()) {
    return null; // Will be redirected by the useEffect
  }
  
  return children;
};

// Unauthorized Page
const Unauthorized = () => {
  return (
    <div className="container mx-auto p-4 text-center">
      <div className="bg-red-100 text-red-700 p-6 rounded-lg shadow-md">
        <h1 className="text-2xl font-bold mb-3">Unauthorized Access</h1>
        <p className="mb-4">You do not have permission to access this resource.</p>
        <Link to="/" className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700">
          Go to Home
        </Link>
      </div>
    </div>
  );
};

// Navbar Component
const Navbar = () => {
  const { user, isAdmin } = useAuth();
  const navigate = useNavigate();
  
  const handleLogout = () => {
    // Get the logout function from the context
    const auth = useAuth();
    // Call the logout function directly
    auth.logout();
    // Navigate to login page
    navigate('/login');
  };

  return (
    <nav className="bg-gray-800 text-white p-4">
      <div className="container mx-auto flex justify-between items-center">
        <div>
          <Link to="/" className="text-xl font-bold">Match Score Tracker</Link>
        </div>
        
        {user ? (
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
          </div>
        ) : (
          <div className="space-x-4">
            <Link to="/login" className="hover:text-gray-300">Login</Link>
            <Link to="/register" className="hover:text-gray-300">Register</Link>
          </div>
        )}
      </div>
    </nav>
  );
};

// Login Page
const Login = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const { login, user } = useAuth();
  const navigate = useNavigate();

  // If user is already logged in, redirect to home
  useEffect(() => {
    if (user) {
      navigate('/');
    }
  }, [user, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setIsLoggingIn(true);
    
    try {
      console.log("Attempting login with email:", email);
      const success = await login(email, password);
      
      if (success) {
        console.log("Login successful, navigating to home");
        navigate('/');
      } else {
        console.error("Login failed in component");
        
        // Check if token was set anyway
        const token = localStorage.getItem('token');
        if (token) {
          console.log("Token found after login, proceeding to home");
          navigate('/');
          return;
        }
        
        setError("Invalid email or password. Please verify your credentials and try again.");
      }
    } catch (err) {
      console.error("Login error in component:", err);
      setError(`Login error: ${err.message || "Server communication error"}`);
    } finally {
      setIsLoggingIn(false);
    }
  };

  return (
    <div className="container mx-auto p-4 max-w-md">
      <div className="bg-white p-8 rounded-lg shadow-md">
        <h1 className="text-2xl font-bold mb-6 text-center">Log in to your account</h1>
        
        {error && (
          <div className="bg-red-100 text-red-700 p-3 rounded mb-4">
            {error}
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          
          <button
            type="submit"
            disabled={isLoggingIn}
            className={`w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 ${
              isLoggingIn ? "opacity-70 cursor-not-allowed" : ""
            }`}
          >
            {isLoggingIn ? "Logging in..." : "Log in"}
          </button>
        </form>
        
        <div className="mt-6 text-center">
          <p className="text-gray-600">
            Don't have an account?{" "}
            <Link to="/register" className="text-blue-600 hover:underline">
              Register here
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

// Register Page
const Register = () => {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [isRegistering, setIsRegistering] = useState(false);
  const { register, user } = useAuth();
  const navigate = useNavigate();

  // If user is already logged in, redirect to home
  useEffect(() => {
    if (user) {
      navigate('/');
    }
  }, [user, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    
    setIsRegistering(true);
    
    try {
      console.log("Submitting registration for:", email);
      const success = await register(username, email, password);
      
      if (success) {
        console.log("Registration and auto-login successful");
        navigate('/');
      } else {
        console.error("Registration failed in component");
        // Check local storage to see if we have a token anyway
        const token = localStorage.getItem('token');
        if (token) {
          console.log("Token found after registration, proceeding to home");
          navigate('/');
          return;
        }
        
        setError("Registration failed. The email may already be in use or there was a server error.");
      }
    } catch (err) {
      console.error("Registration exception:", err);
      setError(`Registration error: ${err.message || "Unknown error"}`);
    } finally {
      setIsRegistering(false);
    }
  };

  return (
    <div className="container mx-auto p-4 max-w-md">
      <div className="bg-white p-8 rounded-lg shadow-md">
        <h1 className="text-2xl font-bold mb-6 text-center">Create an account</h1>
        
        {error && (
          <div className="bg-red-100 text-red-700 p-3 rounded mb-4">
            {error}
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
              Username
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          
          <div>
            <label htmlFor="register-email" className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              id="register-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          
          <div>
            <label htmlFor="register-password" className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              id="register-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          
          <div>
            <label htmlFor="confirm-password" className="block text-sm font-medium text-gray-700 mb-1">
              Confirm Password
            </label>
            <input
              id="confirm-password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          
          <button
            type="submit"
            disabled={isRegistering}
            className={`w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 ${
              isRegistering ? "opacity-70 cursor-not-allowed" : ""
            }`}
          >
            {isRegistering ? "Registering..." : "Register"}
          </button>
        </form>
        
        <div className="mt-6 text-center">
          <p className="text-gray-600">
            Already have an account?{" "}
            <Link to="/login" className="text-blue-600 hover:underline">
              Log in here
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

// Home Page
const Home = () => {
  return (
    <div className="container mx-auto p-4">
      <div className="bg-white p-6 rounded-lg shadow-md mb-8">
        <h1 className="text-3xl font-bold mb-4">Match Score Tracker</h1>
        <p className="text-gray-600 mb-2">
          Welcome to the Match Score Tracker application. This application helps you manage shooters, 
          matches, and scores for pistol shooting competitions.
        </p>
        <p className="text-gray-600">
          Use the navigation menu above to access different sections of the application.
        </p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-lg shadow hover:shadow-md transition-shadow">
          <h2 className="text-xl font-semibold mb-3">Shooters</h2>
          <p className="text-gray-600 mb-4">
            Manage shooter profiles, including NRA and CMP numbers. View shooter performance history.
          </p>
          <Link 
            to="/shooters" 
            className="inline-block bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            View Shooters
          </Link>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow hover:shadow-md transition-shadow">
          <h2 className="text-xl font-semibold mb-3">Matches</h2>
          <p className="text-gray-600 mb-4">
            Create and manage shooting matches. Define match structure, date, and location.
          </p>
          <Link 
            to="/matches" 
            className="inline-block bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            View Matches
          </Link>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow hover:shadow-md transition-shadow">
          <h2 className="text-xl font-semibold mb-3">Score Reports</h2>
          <p className="text-gray-600 mb-4">
            View match reports and shooter performance statistics across multiple matches.
          </p>
          <Link 
            to="/matches" 
            className="inline-block bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            View Reports
          </Link>
        </div>
      </div>
    </div>
  );
};

// Shooters List with Year Filter
const ShootersList = () => {
  const [shooters, setShooters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newShooter, setNewShooter] = useState({ name: "", nra_number: "", cmp_number: "" });
  const { isAdmin } = useAuth();

  useEffect(() => {
    const fetchShooters = async () => {
      try {
        const response = await axios.get(`${API}/shooters`);
        setShooters(response.data);
        setLoading(false);
      } catch (err) {
        console.error("Error fetching shooters:", err);
        setError("Failed to load shooters. Please try again.");
        setLoading(false);
      }
    };

    fetchShooters();
  }, []);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setNewShooter({
      ...newShooter,
      [name]: value
    });
  };

  const handleAddShooter = async (e) => {
    e.preventDefault();
    
    if (!newShooter.name) {
      setError("Shooter name is required");
      return;
    }
    
    try {
      const response = await axios.post(`${API}/shooters`, newShooter);
      setShooters([...shooters, response.data]);
      setNewShooter({ name: "", nra_number: "", cmp_number: "" });
    } catch (err) {
      console.error("Error adding shooter:", err);
      setError("Failed to add shooter. Please try again.");
    }
  };

  if (loading) return <div className="container mx-auto p-4 text-center">Loading shooters...</div>;
  if (error) return <div className="container mx-auto p-4 text-center text-red-500">{error}</div>;

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6">Shooters</h1>
      
      {/* Add Shooter Form - only visible to admins */}
      {isAdmin() && (
        <div className="mb-8 bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Add New Shooter</h2>
          <form onSubmit={handleAddShooter} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                  Shooter Name
                </label>
                <input
                  id="name"
                  name="name"
                  type="text"
                  value={newShooter.name}
                  onChange={handleInputChange}
                  placeholder="Enter shooter name"
                  className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label htmlFor="nra_number" className="block text-sm font-medium text-gray-700 mb-1">
                  NRA Number (Optional)
                </label>
                <input
                  id="nra_number"
                  name="nra_number"
                  type="text"
                  value={newShooter.nra_number}
                  onChange={handleInputChange}
                  placeholder="Enter NRA number"
                  className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label htmlFor="cmp_number" className="block text-sm font-medium text-gray-700 mb-1">
                  CMP Number (Optional)
                </label>
                <input
                  id="cmp_number"
                  name="cmp_number"
                  type="text"
                  value={newShooter.cmp_number}
                  onChange={handleInputChange}
                  placeholder="Enter CMP number"
                  className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div className="flex justify-end">
              <button 
                type="submit" 
                className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
              >
                Add Shooter
              </button>
            </div>
          </form>
        </div>
      )}
      
      {/* Shooters List */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                NRA Number
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                CMP Number
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {shooters.length === 0 ? (
              <tr>
                <td colSpan="4" className="px-6 py-4 text-center text-gray-500">
                  No shooters found
                </td>
              </tr>
            ) : (
              shooters.map((shooter) => (
                <tr key={shooter.id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{shooter.name}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-500">{shooter.nra_number || "-"}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-500">{shooter.cmp_number || "-"}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <Link 
                      to={`/shooters/${shooter.id}`} 
                      className="text-blue-600 hover:text-blue-900"
                    >
                      View Details
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// Matches List with Year Filter
const MatchesList = () => {
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newMatch, setNewMatch] = useState({ 
    name: "", 
    date: new Date().toISOString().split('T')[0],
    location: "",
    match_types: [],
    aggregate_type: "None"
  });
  const [showForm, setShowForm] = useState(false);
  const [formStep, setFormStep] = useState(1);
  const [matchTypes, setMatchTypes] = useState(null);
  const [instanceCounter, setInstanceCounter] = useState(1);
  const [selectedYear, setSelectedYear] = useState("all");
  const [availableYears, setAvailableYears] = useState([]);
  const handleDeleteMatch = async (matchId, matchName) => {
    if (window.confirm(`Are you sure you want to delete the match "${matchName}"? This will also delete all scores associated with this match and cannot be undone.`)) {
      try {
        await axios.delete(`${API}/matches/${matchId}`);
        setMatches(matches.filter(match => match.id !== matchId));
        toast.success(`Match "${matchName}" deleted successfully`);
      } catch (err) {
        console.error("Error deleting match:", err);
        toast.error("Failed to delete match. Please try again.");
      }
    }
  };

  const { isAdmin } = useAuth();

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch matches
        const matchesResponse = await axios.get(`${API}/matches`);
        const matchesData = matchesResponse.data;
        setMatches(matchesData);
        
        // Extract unique years from match dates
        const years = [...new Set(matchesData.map(match => 
          new Date(match.date).getFullYear()
        ))].sort((a, b) => b - a); // Sort years in descending order
        
        setAvailableYears(years);
        
        // Set selected year to the most recent year if available
        if (years.length > 0) {
          setSelectedYear(years[0].toString());
        }
        
        // Fetch match types for the form
        if (isAdmin()) {
          const typesResponse = await axios.get(`${API}/match-types`);
          setMatchTypes(typesResponse.data);
        }
        
        setLoading(false);
      } catch (err) {
        console.error("Error fetching data:", err);
        setError("Failed to load data. Please try again.");
        setLoading(false);
      }
    };

    fetchData();
  }, [isAdmin]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setNewMatch({
      ...newMatch,
      [name]: value
    });
  };

  const handleYearChange = (e) => {
    setSelectedYear(e.target.value);
  };

  const addMatchType = (type) => {
    const instanceName = `${type}${instanceCounter}`;
    setInstanceCounter(instanceCounter + 1);
    
    setNewMatch({
      ...newMatch,
      match_types: [
        ...newMatch.match_types,
        {
          type,
          instance_name: instanceName,
          calibers: []
        }
      ]
    });
  };

  const removeMatchType = (index) => {
    const updatedTypes = [...newMatch.match_types];
    updatedTypes.splice(index, 1);
    
    setNewMatch({
      ...newMatch,
      match_types: updatedTypes
    });
  };

  const toggleCaliber = (matchTypeIndex, caliber) => {
    const updatedTypes = [...newMatch.match_types];
    const currentCaliberIndex = updatedTypes[matchTypeIndex].calibers.indexOf(caliber);
    
    if (currentCaliberIndex === -1) {
      // Add caliber
      updatedTypes[matchTypeIndex].calibers.push(caliber);
    } else {
      // Remove caliber
      updatedTypes[matchTypeIndex].calibers.splice(currentCaliberIndex, 1);
    }
    
    setNewMatch({
      ...newMatch,
      match_types: updatedTypes
    });
  };

  const handleAddMatch = async (e) => {
    e.preventDefault();
    
    if (!newMatch.name || !newMatch.date || !newMatch.location || newMatch.match_types.length === 0) {
      setError("Please fill out all required fields and add at least one match type");
      return;
    }
    
    // Check that each match type has at least one caliber
    for (const matchType of newMatch.match_types) {
      if (matchType.calibers.length === 0) {
        setError(`Please select at least one caliber for ${matchType.instance_name}`);
        return;
      }
    }

    try {
      const response = await axios.post(`${API}/matches`, {
        name: newMatch.name,
        date: new Date(newMatch.date).toISOString(),
        location: newMatch.location,
        match_types: newMatch.match_types,
        aggregate_type: newMatch.aggregate_type
      });
      
      setMatches([response.data, ...matches]);
      
      // Update available years if a new year is encountered
      const newMatchYear = new Date(response.data.date).getFullYear();
      if (!availableYears.includes(newMatchYear)) {
        setAvailableYears([...availableYears, newMatchYear].sort((a, b) => b - a));
      }
      
      setNewMatch({ 
        name: "", 
        date: new Date().toISOString().split('T')[0],
        location: "",
        match_types: [],
        aggregate_type: "None"
      });
    } catch (err) {
      console.error("Error adding match:", err);
      setError("Failed to add match. Please try again.");
    }
  };

  // Filter matches by selected year
  const filteredMatches = selectedYear === "all" 
    ? matches 
    : matches.filter(match => {
        const matchYear = new Date(match.date).getFullYear().toString();
        return matchYear === selectedYear;
      });

  if (loading) return <div className="container mx-auto p-4 text-center">Loading matches...</div>;
  if (error) return <div className="container mx-auto p-4 text-center text-red-500">{error}</div>;

  return (
    <div className="container mx-auto p-4">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Matches</h1>
        
        {/* Year Filter */}
        <div className="flex items-center">
          <label htmlFor="year-filter" className="mr-2 text-gray-700">
            Year:
          </label>
          <select
            id="year-filter"
            value={selectedYear}
            onChange={handleYearChange}
            className="px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Years</option>
            {availableYears.map(year => (
              <option key={year} value={year.toString()}>
                {year}
              </option>
            ))}
          </select>
        </div>
      </div>
      
      {/* Add Match Form - only visible to admins */}
      {isAdmin() && (
        <div className="mb-8 bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Add New Match</h2>
          <form onSubmit={handleAddMatch} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                  Match Name
                </label>
                <input
                  id="name"
                  name="name"
                  type="text"
                  value={newMatch.name}
                  onChange={handleInputChange}
                  placeholder="Enter match name"
                  className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label htmlFor="date" className="block text-sm font-medium text-gray-700 mb-1">
                  Match Date
                </label>
                <input
                  id="date"
                  name="date"
                  type="date"
                  value={newMatch.date}
                  onChange={handleInputChange}
                  className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label htmlFor="location" className="block text-sm font-medium text-gray-700 mb-1">
                  Location
                </label>
                <input
                  id="location"
                  name="location"
                  type="text"
                  value={newMatch.location}
                  onChange={handleInputChange}
                  placeholder="Enter match location"
                  className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
            </div>
            
            <div>
              <label htmlFor="aggregate_type" className="block text-sm font-medium text-gray-700 mb-1">
                Aggregate Type
              </label>
              <select
                id="aggregate_type"
                name="aggregate_type"
                value={newMatch.aggregate_type}
                onChange={handleInputChange}
                className="w-full md:w-1/3 px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="None">None</option>
                <option value="1800 (2x900)">1800 (2x900)</option>
                <option value="1800 (3x600)">1800 (3x600)</option>
                <option value="2700 (3x900)">2700 (3x900)</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Match Types
              </label>
              
              <div className="flex flex-wrap gap-2 mb-4">
                {matchTypes && Object.keys(matchTypes).map((type) => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => addMatchType(type)}
                    className="px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                  >
                    + {type}
                  </button>
                ))}
              </div>
              
              {newMatch.match_types.length > 0 ? (
                <div className="space-y-4">
                  {newMatch.match_types.map((matchType, index) => (
                    <div key={index} className="border p-4 rounded">
                      <div className="flex justify-between items-center mb-3">
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
                        <button
                          type="button"
                          onClick={() => removeMatchType(index)}
                          className="text-red-600 hover:text-red-800"
                        >
                          Remove
                        </button>
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Calibers
                        </label>
                        <div className="flex flex-wrap gap-2">
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
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-gray-500 mb-4">No match types added yet. Click the buttons above to add match types.</div>
              )}
            </div>
            
            <div className="flex justify-end">
              <button 
                type="submit" 
                className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
              >
                Create Match
              </button>
            </div>
          </form>
        </div>
      )}
      
      {/* Matches List */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Match Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Date
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Location
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredMatches.length === 0 ? (
              <tr>
                <td colSpan="4" className="px-6 py-4 text-center text-gray-500">
                  {selectedYear === "all" 
                    ? "No matches found" 
                    : `No matches found for ${selectedYear}`}
                </td>
              </tr>
            ) : (
              filteredMatches.map((match) => (
                <tr key={match.id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{match.name}</div>
                    {match.aggregate_type !== "None" && (
                      <div className="text-xs text-blue-600">{match.aggregate_type}</div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-500">
                      {new Date(match.date).toLocaleDateString()}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-500">{match.location}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <Link 
                      to={`/matches/${match.id}`} 
                      className="text-blue-600 hover:text-blue-900 mr-4"
                    >
                      View Details
                    </Link>
                    {isAdmin() && (
                      <Link 
                        to={`/scores/add/${match.id}`} 
                        className="text-green-600 hover:text-green-900"
                      >
                        Add Scores
                      </Link>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// App Component
function App() {
  return (
    <div className="App min-h-screen bg-gray-100">
      <AuthProvider>
        <BrowserRouter>
          <Navbar />
          <main className="pt-4 pb-8">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/unauthorized" element={<Unauthorized />} />
              
              {/* Protected Routes */}
              <Route 
                path="/shooters" 
                element={<ProtectedRoute><ShootersList /></ProtectedRoute>} 
              />
              <Route 
                path="/shooters/:shooterId" 
                element={<ProtectedRoute><ShooterDetail /></ProtectedRoute>} 
              />
              <Route 
                path="/matches" 
                element={<ProtectedRoute><MatchesList /></ProtectedRoute>} 
              />
              <Route 
                path="/matches/:matchId" 
                element={<ProtectedRoute><MatchReport /></ProtectedRoute>} 
              />
              <Route 
                path="/scores/add/:matchId" 
                element={<ProtectedRoute adminOnly={true}><ScoreEntry /></ProtectedRoute>} 
              />
              <Route 
                path="/scores/edit/:scoreId" 
                element={<ProtectedRoute adminOnly={true}><EditScore /></ProtectedRoute>} 
              />
              <Route 
                path="/admin/users" 
                element={<ProtectedRoute adminOnly={true}><UserManagement /></ProtectedRoute>} 
              />
              <Route 
                path="/change-password" 
                element={<ProtectedRoute><ChangePassword /></ProtectedRoute>} 
              />
            </Routes>
          </main>
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}

export default App;