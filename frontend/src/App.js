import { useState, useEffect, createContext, useContext } from "react";
import { BrowserRouter, Routes, Route, Link, useNavigate, useParams, Navigate } from "react-router-dom";
import axios from "axios";
import "./App.css";
import UserManagement from "./components/UserManagement";
import ShooterDetail from "./components/ShooterDetail";
import MatchReport from "./components/MatchReport";
import ScoreEntry from "./components/ScoreEntry";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
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
      // Convert to form data format required by OAuth2 password flow
      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);
      
      const response = await axios.post(`${AUTH_API}/token`, formData);
      const { access_token, user_id, role } = response.data;
      
      // Store token in localStorage
      localStorage.setItem('token', access_token);
      
      // Set default auth header
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      // Update user state
      setUser({
        id: user_id,
        role,
        token: access_token
      });
      
      return true;
    } catch (error) {
      console.error("Login error:", error);
      return false;
    }
  };

  const register = async (username, email, password) => {
    try {
      await axios.post(`${AUTH_API}/register`, {
        username,
        email,
        password,
        role: "reporter" // Default role for new users
      });
      return true;
    } catch (error) {
      console.error("Registration error:", error);
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    setUser(null);
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
  
  if (loading) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>;
  }
  
  if (!user) {
    return <Navigate to="/login" />;
  }
  
  if (adminOnly && !isAdmin()) {
    return <Navigate to="/unauthorized" />;
  }
  
  return children;
};

// Home Page
const Home = () => {
  const { user, isAdmin } = useAuth();
  
  return (
    <div className="container mx-auto p-4">
      <div className="bg-white p-8 rounded-lg shadow-md">
        <h1 className="text-3xl font-bold mb-6 text-center">Shooting Match Score Management</h1>
        
        <div className="text-center mb-8">
          <p className="text-lg mb-4">
            Welcome to the Shooting Match Score Management System
          </p>
          <p className="text-gray-600 mb-4">
            Track shooters, matches, and scores with comprehensive reporting
          </p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
            <h2 className="text-xl font-semibold mb-3">Shooter Management</h2>
            <p className="text-gray-600 mb-4">
              Track shooters with their NRA and CMP numbers
            </p>
            <Link 
              to="/shooters" 
              className="block w-full bg-blue-600 text-white py-2 text-center rounded hover:bg-blue-700"
            >
              Manage Shooters
            </Link>
          </div>
          
          <div className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
            <h2 className="text-xl font-semibold mb-3">Match Management</h2>
            <p className="text-gray-600 mb-4">
              Set up matches with various configurations and aggregate types
            </p>
            <Link 
              to="/matches" 
              className="block w-full bg-blue-600 text-white py-2 text-center rounded hover:bg-blue-700"
            >
              Manage Matches
            </Link>
          </div>
        </div>
        
        {isAdmin() && (
          <div className="mt-8 border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
            <h2 className="text-xl font-semibold mb-3">Admin Controls</h2>
            <p className="text-gray-600 mb-4">
              Manage user accounts and permissions
            </p>
            <Link 
              to="/admin/users" 
              className="block w-full bg-purple-600 text-white py-2 text-center rounded hover:bg-purple-700"
            >
              User Management
            </Link>
          </div>
        )}
      </div>
    </div>
  );
};

// Navbar Component
const Navbar = () => {
  const { user, logout, isAdmin } = useAuth();
  
  return (
    <nav className="bg-gray-800 text-white p-4">
      <div className="container mx-auto flex justify-between items-center">
        <Link to="/" className="text-xl font-bold">Shooting Match Scorer</Link>
        
        {user ? (
          <div className="flex items-center">
            <div className="space-x-4 mr-6">
              <Link to="/shooters" className="hover:text-gray-300">Shooters</Link>
              <Link to="/matches" className="hover:text-gray-300">Matches</Link>
              {isAdmin() && (
                <Link to="/admin/users" className="hover:text-gray-300">Users</Link>
              )}
            </div>
            
            <div className="flex items-center">
              <span className="mr-2 text-sm">
                {isAdmin() ? 'Admin' : 'Reporter'}
              </span>
              <button 
                onClick={logout}
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
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    
    const success = await login(email, password);
    if (success) {
      navigate('/');
    } else {
      setError("Invalid email or password. Please try again.");
    }
  };

  return (
    <div className="container mx-auto max-w-md p-4">
      <div className="bg-white p-8 rounded-lg shadow-md">
        <h1 className="text-2xl font-bold mb-6 text-center">Login</h1>
        
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
          
          <div>
            <button 
              type="submit" 
              className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
            >
              Login
            </button>
          </div>
        </form>
        
        <div className="mt-4 text-center">
          <p className="text-sm text-gray-600">
            Don't have an account? 
            <Link to="/register" className="ml-1 text-blue-600 hover:underline">
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
  const [success, setSuccess] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    
    const success = await register(username, email, password);
    if (success) {
      setSuccess(true);
      setTimeout(() => {
        navigate('/login');
      }, 2000);
    } else {
      setError("Registration failed. Email may already be registered.");
    }
  };

  if (success) {
    return (
      <div className="container mx-auto max-w-md p-4">
        <div className="bg-green-100 text-green-700 p-6 rounded-lg shadow-md text-center">
          <h2 className="text-xl font-bold mb-2">Registration Successful!</h2>
          <p>Redirecting to login page...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto max-w-md p-4">
      <div className="bg-white p-8 rounded-lg shadow-md">
        <h1 className="text-2xl font-bold mb-6 text-center">Register</h1>
        
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
          
          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-1">
              Confirm Password
            </label>
            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          
          <div>
            <button 
              type="submit" 
              className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
            >
              Register
            </button>
          </div>
        </form>
        
        <div className="mt-4 text-center">
          <p className="text-sm text-gray-600">
            Already have an account? 
            <Link to="/login" className="ml-1 text-blue-600 hover:underline">
              Login here
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

// Unauthorized Page
const Unauthorized = () => {
  return (
    <div className="container mx-auto max-w-md p-4">
      <div className="bg-yellow-100 text-yellow-800 p-6 rounded-lg shadow-md text-center">
        <h2 className="text-2xl font-bold mb-2">Access Denied</h2>
        <p className="mb-4">You don't have permission to access this page.</p>
        <Link to="/" className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
          Return to Home
        </Link>
      </div>
    </div>
  );
};

// Shooters List
const ShootersList = () => {
  const [shooters, setShooters] = useState([]);
  const [newShooterName, setNewShooterName] = useState("");
  const [nraNumber, setNraNumber] = useState("");
  const [cmpNumber, setCmpNumber] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
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

  const handleAddShooter = async (e) => {
    e.preventDefault();
    if (!newShooterName.trim()) return;

    try {
      const response = await axios.post(`${API}/shooters`, {
        name: newShooterName,
        nra_number: nraNumber || null,
        cmp_number: cmpNumber || null
      });
      
      setShooters([...shooters, response.data]);
      setNewShooterName("");
      setNraNumber("");
      setCmpNumber("");
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
                <label htmlFor="shooterName" className="block text-sm font-medium text-gray-700 mb-1">
                  Shooter Name
                </label>
                <input
                  id="shooterName"
                  type="text"
                  value={newShooterName}
                  onChange={(e) => setNewShooterName(e.target.value)}
                  placeholder="Enter shooter name"
                  className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label htmlFor="nraNumber" className="block text-sm font-medium text-gray-700 mb-1">
                  NRA Number (Optional)
                </label>
                <input
                  id="nraNumber"
                  type="text"
                  value={nraNumber}
                  onChange={(e) => setNraNumber(e.target.value)}
                  placeholder="Enter NRA number"
                  className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label htmlFor="cmpNumber" className="block text-sm font-medium text-gray-700 mb-1">
                  CMP Number (Optional)
                </label>
                <input
                  id="cmpNumber"
                  type="text"
                  value={cmpNumber}
                  onChange={(e) => setCmpNumber(e.target.value)}
                  placeholder="Enter CMP number"
                  className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div>
              <button 
                type="submit" 
                className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
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
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">NRA Number</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">CMP Number</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {shooters.length === 0 ? (
              <tr>
                <td colSpan="4" className="px-6 py-4 text-center text-gray-500">
                  No shooters found. {isAdmin() ? "Add a shooter above." : ""}
                </td>
              </tr>
            ) : (
              shooters.map((shooter) => (
                <tr key={shooter.id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{shooter.name}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{shooter.nra_number || "-"}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{shooter.cmp_number || "-"}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <Link 
                      to={`/shooters/${shooter.id}`} 
                      className="text-blue-600 hover:text-blue-900 mr-4"
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

// Note: ShooterDetail component has been moved to its own file: /components/ShooterDetail.js

// Matches List
const MatchesList = () => {
  const [matches, setMatches] = useState([]);
  const [newMatch, setNewMatch] = useState({ 
    name: "", 
    date: new Date().toISOString().split('T')[0],
    location: "",
    match_types: [],
    aggregate_type: "None"
  });
  const [matchType, setMatchType] = useState({
    type: "NMC",
    instance_name: "",
    calibers: []
  });
  const [availableTypes, setAvailableTypes] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { isAdmin } = useAuth();

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch matches
        const matchesResponse = await axios.get(`${API}/matches`);
        setMatches(matchesResponse.data);
        
        // Fetch available match types
        const typesResponse = await axios.get(`${API}/match-types`);
        setAvailableTypes(typesResponse.data);
        
        setLoading(false);
      } catch (err) {
        console.error("Error fetching matches:", err);
        setError("Failed to load matches. Please try again.");
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setNewMatch({
      ...newMatch,
      [name]: value
    });
  };

  const handleMatchTypeChange = (e) => {
    const { name, value } = e.target;
    setMatchType({
      ...matchType,
      [name]: value
    });
  };

  const handleCaliberChange = (e) => {
    const caliber = e.target.value;
    const isChecked = e.target.checked;
    
    if (isChecked) {
      setMatchType({
        ...matchType,
        calibers: [...matchType.calibers, caliber]
      });
    } else {
      setMatchType({
        ...matchType,
        calibers: matchType.calibers.filter(c => c !== caliber)
      });
    }
  };

  const addMatchType = () => {
    if (!matchType.instance_name || matchType.calibers.length === 0) {
      setError("Please provide an instance name and select at least one caliber");
      return;
    }
    
    setNewMatch({
      ...newMatch,
      match_types: [...newMatch.match_types, { ...matchType }]
    });
    
    // Reset match type form
    setMatchType({
      type: "NMC",
      instance_name: "",
      calibers: []
    });
  };

  const removeMatchType = (index) => {
    const updatedMatchTypes = [...newMatch.match_types];
    updatedMatchTypes.splice(index, 1);
    setNewMatch({
      ...newMatch,
      match_types: updatedMatchTypes
    });
  };

  const handleAddMatch = async (e) => {
    e.preventDefault();
    if (!newMatch.name.trim() || !newMatch.location.trim() || newMatch.match_types.length === 0) {
      setError("Please fill in all required fields and add at least one match type");
      return;
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

  if (loading) return <div className="container mx-auto p-4 text-center">Loading matches...</div>;
  if (error) return <div className="container mx-auto p-4 text-center text-red-500">{error}</div>;

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6">Matches</h1>
      
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
                className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="None">None</option>
                <option value="1800 (2x900)">1800 (2x900)</option>
                <option value="1800 (3x600)">1800 (3x600)</option>
                <option value="2700 (3x900)">2700 (3x900)</option>
              </select>
            </div>
            
            {/* Match Types Section */}
            <div className="border rounded-lg overflow-hidden">
              <div className="bg-gray-100 p-4 border-b">
                <h3 className="text-lg font-semibold">Match Types</h3>
              </div>
              
              <div className="p-4">
                {/* Added Match Types */}
                {newMatch.match_types.length > 0 ? (
                  <div className="mb-4">
                    <h4 className="text-md font-medium mb-2">Added Match Types:</h4>
                    <div className="space-y-2">
                      {newMatch.match_types.map((mt, index) => (
                        <div key={index} className="flex justify-between items-center bg-gray-50 p-3 rounded">
                          <div>
                            <span className="font-medium">{mt.instance_name}</span>
                            <span className="text-gray-600 ml-2">({mt.type})</span>
                            <div className="text-sm text-gray-500 mt-1">
                              Calibers: {mt.calibers.join(', ')}
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
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="mb-4 text-gray-500 text-center py-2">
                    No match types added yet. Add at least one match type below.
                  </div>
                )}
                
                {/* Add New Match Type */}
                <div className="border-t pt-4">
                  <h4 className="text-md font-medium mb-3">Add Match Type:</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <div>
                      <label htmlFor="type" className="block text-sm font-medium text-gray-700 mb-1">
                        Type
                      </label>
                      <select
                        id="type"
                        name="type"
                        value={matchType.type}
                        onChange={handleMatchTypeChange}
                        className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="NMC">National Match Course (NMC)</option>
                        <option value="600">600 Point Aggregate</option>
                        <option value="900">900 Point Aggregate</option>
                        <option value="Presidents">Presidents Course</option>
                      </select>
                    </div>
                    <div>
                      <label htmlFor="instance_name" className="block text-sm font-medium text-gray-700 mb-1">
                        Instance Name
                      </label>
                      <input
                        id="instance_name"
                        name="instance_name"
                        type="text"
                        value={matchType.instance_name}
                        onChange={handleMatchTypeChange}
                        placeholder="e.g., NMC1, 600_1"
                        className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                  
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Calibers
                    </label>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      <div className="flex items-center">
                        <input
                          id="caliber_22"
                          type="checkbox"
                          value=".22"
                          checked={matchType.calibers.includes(".22")}
                          onChange={handleCaliberChange}
                          className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                        />
                        <label htmlFor="caliber_22" className="ml-2 text-sm text-gray-700">
                          .22
                        </label>
                      </div>
                      <div className="flex items-center">
                        <input
                          id="caliber_cf"
                          type="checkbox"
                          value="CF"
                          checked={matchType.calibers.includes("CF")}
                          onChange={handleCaliberChange}
                          className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                        />
                        <label htmlFor="caliber_cf" className="ml-2 text-sm text-gray-700">
                          Center Fire (CF)
                        </label>
                      </div>
                      <div className="flex items-center">
                        <input
                          id="caliber_45"
                          type="checkbox"
                          value=".45"
                          checked={matchType.calibers.includes(".45")}
                          onChange={handleCaliberChange}
                          className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                        />
                        <label htmlFor="caliber_45" className="ml-2 text-sm text-gray-700">
                          .45
                        </label>
                      </div>
                      <div className="flex items-center">
                        <input
                          id="caliber_9mm"
                          type="checkbox"
                          value="9mm Service"
                          checked={matchType.calibers.includes("9mm Service")}
                          onChange={handleCaliberChange}
                          className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                        />
                        <label htmlFor="caliber_9mm" className="ml-2 text-sm text-gray-700">
                          9mm Service
                        </label>
                      </div>
                      <div className="flex items-center">
                        <input
                          id="caliber_45s"
                          type="checkbox"
                          value="45 Service"
                          checked={matchType.calibers.includes("45 Service")}
                          onChange={handleCaliberChange}
                          className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                        />
                        <label htmlFor="caliber_45s" className="ml-2 text-sm text-gray-700">
                          45 Service
                        </label>
                      </div>
                    </div>
                  </div>
                  
                  <button
                    type="button"
                    onClick={addMatchType}
                    className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                  >
                    Add Match Type
                  </button>
                </div>
              </div>
            </div>
            
            <div>
              <button 
                type="submit" 
                className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
                disabled={newMatch.match_types.length === 0}
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
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Match Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Location</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {matches.length === 0 ? (
              <tr>
                <td colSpan="4" className="px-6 py-4 text-center text-gray-500">
                  No matches found. {isAdmin() ? "Add a match above." : ""}
                </td>
              </tr>
            ) : (
              matches.map((match) => (
                <tr key={match.id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{match.name}</div>
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

// Note: MatchDetail component has been moved to its own file: /components/MatchReport.js

// Note: AddScoreForm component has been moved to its own file: /components/ScoreEntry.js

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
                element={<ProtectedRoute><MatchDetail /></ProtectedRoute>} 
              />
              <Route 
                path="/scores/add/:matchId" 
                element={<ProtectedRoute adminOnly={true}><AddScoreForm /></ProtectedRoute>} 
              />
              <Route 
                path="/admin/users" 
                element={<ProtectedRoute adminOnly={true}><UserManagement /></ProtectedRoute>} 
              />
            </Routes>
          </main>
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}

export default App;
