import { useState, useEffect } from "react";
import axios from "axios";
import { useParams, useNavigate, Link } from "react-router-dom";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ScoreEntry = () => {
  const { matchId } = useParams();
  const navigate = useNavigate();
  const [match, setMatch] = useState(null);
  const [matchConfig, setMatchConfig] = useState(null);
  const [shooters, setShooters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  
  const [formData, setFormData] = useState({
    shooter_id: "",
    match_id: matchId,
    caliber: "",
    match_type_instance: "",
    stages: []
  });
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch match details
        const matchResponse = await axios.get(`${API}/matches/${matchId}`);
        setMatch(matchResponse.data);
        
        // Fetch match configuration
        const configResponse = await axios.get(`${API}/match-config/${matchId}`);
        setMatchConfig(configResponse.data);
        
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

  // Effect to reset stages when match type changes
  useEffect(() => {
    if (matchConfig && formData.match_type_instance) {
      const selectedType = matchConfig.match_types.find(
        mt => mt.instance_name === formData.match_type_instance
      );
      
      if (selectedType) {
        // Reset stages for the new match type
        const newStages = selectedType.stages.map(stageName => ({
          name: stageName,
          score: 0,
          x_count: 0
        }));
        
        setFormData({
          ...formData,
          stages: newStages
        });
      }
    }
  }, [formData.match_type_instance, matchConfig]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value
    });
  };

  const handleStageChange = (index, field, value) => {
    const updatedStages = [...formData.stages];
    updatedStages[index][field] = parseInt(value, 10) || 0;
    
    setFormData({
      ...formData,
      stages: updatedStages
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.shooter_id || !formData.caliber || !formData.match_type_instance) {
      setError("Please select a shooter, caliber, and match type");
      return;
    }
    
    try {
      await axios.post(`${API}/scores`, formData);
      setSuccess(true);
      setTimeout(() => {
        navigate(`/matches/${matchId}`);
      }, 2000);
    } catch (err) {
      console.error("Error submitting score:", err);
      setError("Failed to save score. Please try again.");
    }
  };

  if (loading) return <div className="container mx-auto p-4 text-center">Loading form data...</div>;
  if (error) return <div className="container mx-auto p-4 text-center text-red-500">{error}</div>;
  if (!match || !matchConfig) return <div className="container mx-auto p-4 text-center">Match data not found</div>;

  // Calculate total score and X count
  const totalScore = formData.stages.reduce((sum, stage) => sum + stage.score, 0);
  const totalXCount = formData.stages.reduce((sum, stage) => sum + stage.x_count, 0);

  // Get available calibers for the selected match type
  const availableCalibers = formData.match_type_instance 
    ? matchConfig.match_types.find(mt => mt.instance_name === formData.match_type_instance)?.calibers || []
    : [];

  if (success) {
    return (
      <div className="container mx-auto p-4">
        <div className="bg-green-100 text-green-700 p-6 rounded-lg shadow-md text-center">
          <h2 className="text-xl font-bold mb-2">Score Saved Successfully!</h2>
          <p>Redirecting to match details...</p>
        </div>
      </div>
    );
  }

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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Shooter Selection */}
            <div>
              <label htmlFor="shooter_id" className="block text-sm font-medium text-gray-700 mb-1">
                Shooter
              </label>
              <select
                id="shooter_id"
                name="shooter_id"
                value={formData.shooter_id}
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
            
            {/* Match Type Selection */}
            <div>
              <label htmlFor="match_type_instance" className="block text-sm font-medium text-gray-700 mb-1">
                Match Type
              </label>
              <select
                id="match_type_instance"
                name="match_type_instance"
                value={formData.match_type_instance}
                onChange={handleInputChange}
                className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              >
                <option value="">-- Select Match Type --</option>
                {matchConfig.match_types.map((mt, idx) => (
                  <option key={idx} value={mt.instance_name}>
                    {mt.instance_name} ({mt.type})
                  </option>
                ))}
              </select>
            </div>
            
            {/* Caliber Selection - Only show calibers available for the selected match type */}
            <div>
              <label htmlFor="caliber" className="block text-sm font-medium text-gray-700 mb-1">
                Caliber
              </label>
              <select
                id="caliber"
                name="caliber"
                value={formData.caliber}
                onChange={handleInputChange}
                className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
                disabled={!formData.match_type_instance}
              >
                <option value="">-- Select Caliber --</option>
                {availableCalibers.map((cal, idx) => (
                  <option key={idx} value={cal}>
                    {cal}
                  </option>
                ))}
              </select>
            </div>
          </div>
          
          {/* Score Entries - Only show if match type is selected */}
          {formData.match_type_instance && (
            <div className="border rounded-lg overflow-hidden">
              <div className="bg-gray-100 p-4 border-b">
                <h3 className="text-lg font-semibold">Score Details</h3>
                <p className="text-sm text-gray-600 mt-1">
                  Enter scores for {formData.stages.length} stages
                </p>
              </div>
              
              <div className="p-4 space-y-6">
                {formData.stages.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {formData.stages.map((stage, idx) => (
                      <div key={idx} className="border p-4 rounded-lg hover:shadow-md transition-shadow">
                        <h4 className="font-medium mb-3">{stage.name}</h4>
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Score
                            </label>
                            <input
                              type="number"
                              min="0"
                              max="100"
                              value={stage.score}
                              onChange={(e) => handleStageChange(idx, 'score', e.target.value)}
                              className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                              required
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              X Count
                            </label>
                            <input
                              type="number"
                              min="0"
                              max="10"
                              value={stage.x_count}
                              onChange={(e) => handleStageChange(idx, 'x_count', e.target.value)}
                              className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                              required
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-gray-500 text-center py-4">
                    Select a match type to enter scores
                  </div>
                )}
                
                {/* Totals */}
                {formData.stages.length > 0 && (
                  <div className="bg-gray-50 p-4 rounded-lg mt-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Total Score
                        </label>
                        <div className="px-4 py-2 border rounded bg-gray-100 font-semibold">
                          {totalScore}
                        </div>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Total X Count
                        </label>
                        <div className="px-4 py-2 border rounded bg-gray-100 font-semibold">
                          {totalXCount}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
          
          <div className="flex justify-end">
            <button 
              type="submit" 
              className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
              disabled={!formData.shooter_id || !formData.caliber || !formData.match_type_instance}
            >
              Save Score
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ScoreEntry;
