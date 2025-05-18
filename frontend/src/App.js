import { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Link, useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import "./App.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Navbar Component
const Navbar = () => {
  return (
    <nav className="bg-gray-800 text-white p-4">
      <div className="container mx-auto flex justify-between items-center">
        <Link to="/" className="text-xl font-bold">Shooting Match Scorer</Link>
        <div className="space-x-4">
          <Link to="/shooters" className="hover:text-gray-300">Shooters</Link>
          <Link to="/matches" className="hover:text-gray-300">Matches</Link>
        </div>
      </div>
    </nav>
  );
};

// Home Page
const Home = () => {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-6">Welcome to Shooting Match Scorer</h1>
        <p className="text-xl mb-8">Manage your shooting matches, track scores, and view performance reports</p>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
          <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
            <h2 className="text-2xl font-bold mb-4 text-gray-800">Shooter Management</h2>
            <p className="mb-4 text-gray-600">Add and manage shooters for your matches</p>
            <Link to="/shooters" className="inline-block bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
              Manage Shooters
            </Link>
          </div>
          
          <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
            <h2 className="text-2xl font-bold mb-4 text-gray-800">Match Management</h2>
            <p className="mb-4 text-gray-600">Create matches and record scores</p>
            <Link to="/matches" className="inline-block bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
              Manage Matches
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

// Shooters List
const ShootersList = () => {
  const [shooters, setShooters] = useState([]);
  const [newShooterName, setNewShooterName] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
        name: newShooterName
      });
      
      setShooters([...shooters, response.data]);
      setNewShooterName("");
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
      
      {/* Add Shooter Form */}
      <div className="mb-8 bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4">Add New Shooter</h2>
        <form onSubmit={handleAddShooter} className="flex flex-col sm:flex-row gap-2">
          <input
            type="text"
            value={newShooterName}
            onChange={(e) => setNewShooterName(e.target.value)}
            placeholder="Enter shooter name"
            className="flex-grow px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
          <button 
            type="submit" 
            className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
          >
            Add Shooter
          </button>
        </form>
      </div>
      
      {/* Shooters List */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {shooters.length === 0 ? (
              <tr>
                <td colSpan="2" className="px-6 py-4 text-center text-gray-500">
                  No shooters found. Add a shooter above.
                </td>
              </tr>
            ) : (
              shooters.map((shooter) => (
                <tr key={shooter.id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{shooter.name}</div>
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

// Shooter Detail Page
const ShooterDetail = () => {
  const { shooterId } = useParams();
  const [shooter, setShooter] = useState(null);
  const [scores, setScores] = useState([]);
  const [averages, setAverages] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchShooterData = async () => {
      try {
        // Fetch shooter details
        const shooterResponse = await axios.get(`${API}/shooters/${shooterId}`);
        setShooter(shooterResponse.data);
        
        // Fetch shooter's scores
        const scoresResponse = await axios.get(`${API}/shooter-report/${shooterId}`);
        setScores(scoresResponse.data);
        
        // Fetch shooter's averages
        const averagesResponse = await axios.get(`${API}/shooter-averages/${shooterId}`);
        setAverages(averagesResponse.data);
        
        setLoading(false);
      } catch (err) {
        console.error("Error fetching shooter details:", err);
        setError("Failed to load shooter details. Please try again.");
        setLoading(false);
      }
    };

    fetchShooterData();
  }, [shooterId]);

  if (loading) return <div className="container mx-auto p-4 text-center">Loading shooter details...</div>;
  if (error) return <div className="container mx-auto p-4 text-center text-red-500">{error}</div>;
  if (!shooter) return <div className="container mx-auto p-4 text-center">Shooter not found</div>;

  return (
    <div className="container mx-auto p-4">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-3xl font-bold">{shooter.name}'s Profile</h1>
        <Link to="/shooters" className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600">
          Back to Shooters
        </Link>
      </div>
      
      {/* Shooter's Average Performance */}
      {averages && Object.keys(averages.caliber_averages).length > 0 ? (
        <div className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">Average Performance by Caliber</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {Object.entries(averages.caliber_averages).map(([caliber, data]) => (
              <div key={caliber} className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-xl font-semibold mb-3">{caliber}</h3>
                <p className="text-sm text-gray-500 mb-3">Based on {data.matches_count} matches</p>
                
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead>
                      <tr>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                        <th className="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">Avg Score</th>
                        <th className="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">Avg X Count</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      <tr>
                        <td className="px-3 py-2 text-sm font-medium">Slow Fire (SF)</td>
                        <td className="px-3 py-2 text-center">{data.sf_score_avg}</td>
                        <td className="px-3 py-2 text-center">{data.sf_x_count_avg}</td>
                      </tr>
                      <tr>
                        <td className="px-3 py-2 text-sm font-medium">Timed Fire (TF)</td>
                        <td className="px-3 py-2 text-center">{data.tf_score_avg}</td>
                        <td className="px-3 py-2 text-center">{data.tf_x_count_avg}</td>
                      </tr>
                      <tr>
                        <td className="px-3 py-2 text-sm font-medium">Rapid Fire (RF)</td>
                        <td className="px-3 py-2 text-center">{data.rf_score_avg}</td>
                        <td className="px-3 py-2 text-center">{data.rf_x_count_avg}</td>
                      </tr>
                      <tr>
                        <td className="px-3 py-2 text-sm font-medium">National Match Course (NMC)</td>
                        <td className="px-3 py-2 text-center">{data.nmc_score_avg}</td>
                        <td className="px-3 py-2 text-center">{data.nmc_x_count_avg}</td>
                      </tr>
                      <tr className="bg-gray-50">
                        <td className="px-3 py-2 text-sm font-bold">Total</td>
                        <td className="px-3 py-2 text-center font-bold">{data.total_score_avg}</td>
                        <td className="px-3 py-2 text-center font-bold">{data.total_x_count_avg}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="mb-8 bg-white p-6 rounded-lg shadow">
          <p className="text-gray-500">No performance data available yet. Shooter needs to participate in matches.</p>
        </div>
      )}
      
      {/* Shooter's Match History */}
      <div>
        <h2 className="text-2xl font-semibold mb-4">Match History</h2>
        {scores.length === 0 ? (
          <div className="bg-white p-6 rounded-lg shadow">
            <p className="text-gray-500">No match history found for this shooter.</p>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Match</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Caliber</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">SF</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">TF</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">RF</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">NMC</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {scores.map((score) => (
                  <tr key={score.id}>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <Link to={`/matches/${score.match_id}`} className="text-blue-600 hover:text-blue-900">
                        {score.match_name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {new Date(score.match_date).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">{score.caliber}</td>
                    <td className="px-4 py-3 text-center">
                      {score.sf_score} ({score.sf_x_count}X)
                    </td>
                    <td className="px-4 py-3 text-center">
                      {score.tf_score} ({score.tf_x_count}X)
                    </td>
                    <td className="px-4 py-3 text-center">
                      {score.rf_score} ({score.rf_x_count}X)
                    </td>
                    <td className="px-4 py-3 text-center">
                      {score.nmc_score} ({score.nmc_x_count}X)
                    </td>
                    <td className="px-4 py-3 font-semibold text-center">
                      {score.total_score} ({score.total_x_count}X)
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

// Matches List
const MatchesList = () => {
  const [matches, setMatches] = useState([]);
  const [newMatch, setNewMatch] = useState({ name: "", date: new Date().toISOString().split('T')[0] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchMatches = async () => {
      try {
        const response = await axios.get(`${API}/matches`);
        setMatches(response.data);
        setLoading(false);
      } catch (err) {
        console.error("Error fetching matches:", err);
        setError("Failed to load matches. Please try again.");
        setLoading(false);
      }
    };

    fetchMatches();
  }, []);

  const handleAddMatch = async (e) => {
    e.preventDefault();
    if (!newMatch.name.trim()) return;

    try {
      const response = await axios.post(`${API}/matches`, {
        name: newMatch.name,
        date: new Date(newMatch.date).toISOString()
      });
      
      setMatches([response.data, ...matches]);
      setNewMatch({ name: "", date: new Date().toISOString().split('T')[0] });
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
      
      {/* Add Match Form */}
      <div className="mb-8 bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4">Add New Match</h2>
        <form onSubmit={handleAddMatch} className="flex flex-col gap-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="matchName" className="block text-sm font-medium text-gray-700 mb-1">
                Match Name
              </label>
              <input
                id="matchName"
                type="text"
                value={newMatch.name}
                onChange={(e) => setNewMatch({...newMatch, name: e.target.value})}
                placeholder="Enter match name"
                className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label htmlFor="matchDate" className="block text-sm font-medium text-gray-700 mb-1">
                Match Date
              </label>
              <input
                id="matchDate"
                type="date"
                value={newMatch.date}
                onChange={(e) => setNewMatch({...newMatch, date: e.target.value})}
                className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
          </div>
          <div>
            <button 
              type="submit" 
              className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
            >
              Add Match
            </button>
          </div>
        </form>
      </div>
      
      {/* Matches List */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Match Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {matches.length === 0 ? (
              <tr>
                <td colSpan="3" className="px-6 py-4 text-center text-gray-500">
                  No matches found. Add a match above.
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
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <Link 
                      to={`/matches/${match.id}`} 
                      className="text-blue-600 hover:text-blue-900 mr-4"
                    >
                      View Details
                    </Link>
                    <Link 
                      to={`/scores/add/${match.id}`} 
                      className="text-green-600 hover:text-green-900"
                    >
                      Add Scores
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

// Match Detail
const MatchDetail = () => {
  const { matchId } = useParams();
  const [match, setMatch] = useState(null);
  const [scores, setScores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchMatchData = async () => {
      try {
        // Fetch match details
        const matchResponse = await axios.get(`${API}/matches/${matchId}`);
        setMatch(matchResponse.data);
        
        // Fetch match scores
        const scoresResponse = await axios.get(`${API}/match-report/${matchId}`);
        setScores(scoresResponse.data);
        
        setLoading(false);
      } catch (err) {
        console.error("Error fetching match details:", err);
        setError("Failed to load match details. Please try again.");
        setLoading(false);
      }
    };

    fetchMatchData();
  }, [matchId]);

  if (loading) return <div className="container mx-auto p-4 text-center">Loading match details...</div>;
  if (error) return <div className="container mx-auto p-4 text-center text-red-500">{error}</div>;
  if (!match) return <div className="container mx-auto p-4 text-center">Match not found</div>;

  // Group scores by shooter
  const scoresByShooter = {};
  scores.forEach(score => {
    if (!scoresByShooter[score.shooter_id]) {
      scoresByShooter[score.shooter_id] = {
        shooter_id: score.shooter_id,
        shooter_name: score.shooter_name,
        scores: []
      };
    }
    scoresByShooter[score.shooter_id].scores.push(score);
  });

  return (
    <div className="container mx-auto p-4">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{match.name}</h1>
          <p className="text-gray-600">
            {new Date(match.date).toLocaleDateString()}
          </p>
        </div>
        <div className="flex gap-3">
          <Link to="/matches" className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600">
            Back to Matches
          </Link>
          <Link to={`/scores/add/${matchId}`} className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
            Add Scores
          </Link>
        </div>
      </div>
      
      {/* Match Scores */}
      {Object.values(scoresByShooter).length === 0 ? (
        <div className="bg-white p-6 rounded-lg shadow text-center">
          <p className="text-gray-500 mb-4">No scores have been recorded for this match.</p>
          <Link to={`/scores/add/${matchId}`} className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700">
            Add First Score
          </Link>
        </div>
      ) : (
        Object.values(scoresByShooter).map(shooter => (
          <div key={shooter.shooter_id} className="mb-8">
            <h2 className="text-2xl font-semibold mb-3">
              <Link to={`/shooters/${shooter.shooter_id}`} className="text-blue-600 hover:underline">
                {shooter.shooter_name}
              </Link>
            </h2>
            
            <div className="bg-white rounded-lg shadow overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Caliber</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">SF</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">TF</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">RF</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">NMC</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {shooter.scores.map(score => (
                    <tr key={score.id}>
                      <td className="px-4 py-3">{score.caliber}</td>
                      <td className="px-4 py-3 text-center">
                        {score.sf_score} ({score.sf_x_count}X)
                      </td>
                      <td className="px-4 py-3 text-center">
                        {score.tf_score} ({score.tf_x_count}X)
                      </td>
                      <td className="px-4 py-3 text-center">
                        {score.rf_score} ({score.rf_x_count}X)
                      </td>
                      <td className="px-4 py-3 text-center">
                        {score.nmc_score} ({score.nmc_x_count}X)
                      </td>
                      <td className="px-4 py-3 font-semibold text-center">
                        {score.total_score} ({score.total_x_count}X)
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))
      )}
    </div>
  );
};

// Add Score Form
const AddScoreForm = () => {
  const { matchId } = useParams();
  const navigate = useNavigate();
  const [match, setMatch] = useState(null);
  const [shooters, setShooters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const [scoreData, setScoreData] = useState({
    shooter_id: "",
    caliber: "",
    sf_score: 0,
    sf_x_count: 0,
    tf_score: 0,
    tf_x_count: 0,
    rf_score: 0,
    rf_x_count: 0
  });
  
  // Caliber options from the requirements
  const calibers = [".22", ".45", "9mm Service", "45 Service", "CF"];

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch match details
        const matchResponse = await axios.get(`${API}/matches/${matchId}`);
        setMatch(matchResponse.data);
        
        // Fetch all shooters
        const shootersResponse = await axios.get(`${API}/shooters`);
        setShooters(shootersResponse.data);
        
        setLoading(false);
      } catch (err) {
        console.error("Error fetching data:", err);
        setError("Failed to load required data. Please try again.");
        setLoading(false);
      }
    };

    fetchData();
  }, [matchId]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    
    // Convert numerical inputs to numbers
    const numericFields = ['sf_score', 'sf_x_count', 'tf_score', 'tf_x_count', 'rf_score', 'rf_x_count'];
    const newValue = numericFields.includes(name) ? parseInt(value, 10) || 0 : value;
    
    setScoreData({
      ...scoreData,
      [name]: newValue
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!scoreData.shooter_id || !scoreData.caliber) {
      setError("Please select a shooter and caliber.");
      return;
    }
    
    try {
      const submitData = {
        ...scoreData,
        match_id: matchId
      };
      
      await axios.post(`${API}/scores`, submitData);
      navigate(`/matches/${matchId}`);
    } catch (err) {
      console.error("Error submitting score:", err);
      setError("Failed to save score. Please try again.");
    }
  };

  if (loading) return <div className="container mx-auto p-4 text-center">Loading form data...</div>;
  if (error) return <div className="container mx-auto p-4 text-center text-red-500">{error}</div>;
  if (!match) return <div className="container mx-auto p-4 text-center">Match not found</div>;

  // Calculate NMC scores (SF + TF + RF)
  const nmcScore = scoreData.sf_score + scoreData.tf_score + scoreData.rf_score;
  const nmcXCount = scoreData.sf_x_count + scoreData.tf_x_count + scoreData.rf_x_count;

  return (
    <div className="container mx-auto p-4">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Add Score</h1>
          <p className="text-gray-600">
            Match: {match.name} ({new Date(match.date).toLocaleDateString()})
          </p>
        </div>
        <Link to={`/matches/${matchId}`} className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600">
          Back to Match
        </Link>
      </div>
      
      <div className="bg-white p-6 rounded-lg shadow">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Shooter Selection */}
            <div>
              <label htmlFor="shooter_id" className="block text-sm font-medium text-gray-700 mb-1">
                Shooter
              </label>
              <select
                id="shooter_id"
                name="shooter_id"
                value={scoreData.shooter_id}
                onChange={handleInputChange}
                className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              >
                <option value="">-- Select Shooter --</option>
                {shooters.map(shooter => (
                  <option key={shooter.id} value={shooter.id}>
                    {shooter.name}
                  </option>
                ))}
              </select>
            </div>
            
            {/* Caliber Selection */}
            <div>
              <label htmlFor="caliber" className="block text-sm font-medium text-gray-700 mb-1">
                Caliber
              </label>
              <select
                id="caliber"
                name="caliber"
                value={scoreData.caliber}
                onChange={handleInputChange}
                className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              >
                <option value="">-- Select Caliber --</option>
                {calibers.map(cal => (
                  <option key={cal} value={cal}>
                    {cal}
                  </option>
                ))}
              </select>
            </div>
          </div>
          
          {/* Score Entries */}
          <div className="border rounded-lg overflow-hidden">
            <div className="bg-gray-100 p-4 border-b">
              <h3 className="text-lg font-semibold">Score Details</h3>
            </div>
            
            <div className="p-4 space-y-6">
              {/* SF Scores */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label htmlFor="sf_score" className="block text-sm font-medium text-gray-700 mb-1">
                    Slow Fire (SF) Score
                  </label>
                  <input
                    type="number"
                    id="sf_score"
                    name="sf_score"
                    min="0"
                    max="300"
                    value={scoreData.sf_score}
                    onChange={handleInputChange}
                    className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                <div>
                  <label htmlFor="sf_x_count" className="block text-sm font-medium text-gray-700 mb-1">
                    SF X Count
                  </label>
                  <input
                    type="number"
                    id="sf_x_count"
                    name="sf_x_count"
                    min="0"
                    max="30"
                    value={scoreData.sf_x_count}
                    onChange={handleInputChange}
                    className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
              </div>
              
              {/* TF Scores */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label htmlFor="tf_score" className="block text-sm font-medium text-gray-700 mb-1">
                    Timed Fire (TF) Score
                  </label>
                  <input
                    type="number"
                    id="tf_score"
                    name="tf_score"
                    min="0"
                    max="300"
                    value={scoreData.tf_score}
                    onChange={handleInputChange}
                    className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                <div>
                  <label htmlFor="tf_x_count" className="block text-sm font-medium text-gray-700 mb-1">
                    TF X Count
                  </label>
                  <input
                    type="number"
                    id="tf_x_count"
                    name="tf_x_count"
                    min="0"
                    max="30"
                    value={scoreData.tf_x_count}
                    onChange={handleInputChange}
                    className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
              </div>
              
              {/* RF Scores */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label htmlFor="rf_score" className="block text-sm font-medium text-gray-700 mb-1">
                    Rapid Fire (RF) Score
                  </label>
                  <input
                    type="number"
                    id="rf_score"
                    name="rf_score"
                    min="0"
                    max="300"
                    value={scoreData.rf_score}
                    onChange={handleInputChange}
                    className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                <div>
                  <label htmlFor="rf_x_count" className="block text-sm font-medium text-gray-700 mb-1">
                    RF X Count
                  </label>
                  <input
                    type="number"
                    id="rf_x_count"
                    name="rf_x_count"
                    min="0"
                    max="30"
                    value={scoreData.rf_x_count}
                    onChange={handleInputChange}
                    className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
              </div>
              
              {/* NMC Totals (calculated) */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-gray-50 p-4 rounded-lg">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    National Match Course (NMC) Total Score
                  </label>
                  <div className="px-4 py-2 border rounded bg-gray-100 font-semibold">
                    {nmcScore}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    NMC Total X Count
                  </label>
                  <div className="px-4 py-2 border rounded bg-gray-100 font-semibold">
                    {nmcXCount}
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div className="flex justify-end">
            <button 
              type="submit" 
              className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
            >
              Save Score
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

function App() {
  return (
    <div className="App min-h-screen bg-gray-100">
      <BrowserRouter>
        <Navbar />
        <main className="pt-4 pb-8">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/shooters" element={<ShootersList />} />
            <Route path="/shooters/:shooterId" element={<ShooterDetail />} />
            <Route path="/matches" element={<MatchesList />} />
            <Route path="/matches/:matchId" element={<MatchDetail />} />
            <Route path="/scores/add/:matchId" element={<AddScoreForm />} />
          </Routes>
        </main>
      </BrowserRouter>
    </div>
  );
}

export default App;
