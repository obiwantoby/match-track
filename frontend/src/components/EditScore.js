import { useState, useEffect } from "react";
import axios from "axios";
import { useParams, useNavigate, Link } from "react-router-dom";
import getAPIUrl from "./API_FIX";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = getAPIUrl(BACKEND_URL);

const EditScore = () => {
  const { scoreId } = useParams();
  const navigate = useNavigate();
  const [score, setScore] = useState(null);
  const [match, setMatch] = useState(null);
  const [matchConfig, setMatchConfig] = useState(null);
  const [shooter, setShooter] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  
  // Form state for the score being edited
  const [formData, setFormData] = useState({
    stages: []
  });
  
  useEffect(() => {
    fetchData();
  }, [scoreId]);
  
  // Function to match stage names between score and match config
  const findMatchingMatchType = (score, matchConfig) => {
    if (!score || !matchConfig || !matchConfig.match_types) return null;
    
    // First try to find the match type by instance name
    const matchType = matchConfig.match_types.find(mt => 
      mt.instance_name === score.match_type_instance
    );
    
    if (matchType) return matchType;
    
    // If not found, try to find by comparing stages
    const scoreStageNames = score.stages.map(s => s.name);
    
    // Check if the score stages are a subset of any match type's entry stages
    // or if the entry stages are similar enough (e.g., "SF" vs "SF1")
    return matchConfig.match_types.find(mt => {
      // Check if all score stages are contained in this match type's entry stages
      // or if they follow a similar pattern (e.g., score has "SF", match has "SF1")
      return scoreStageNames.every(stageName => 
        mt.entry_stages.includes(stageName) || 
        mt.entry_stages.some(entryStage => entryStage.startsWith(stageName) || 
                            stageName.startsWith(entryStage.replace(/\d+$/, "")))
      );
    });
  };

  const handleStageChange = (stageIdx, field, value) => {
    const updatedStages = [...formData.stages];
    
    // If value is empty string, set it to null to represent a skipped match
    if (value === "") {
      updatedStages[stageIdx][field] = null;
    } else {
      // Otherwise parse it as an integer
      updatedStages[stageIdx][field] = parseInt(value, 10);
    }
    
    setFormData({
      ...formData,
      stages: updatedStages
    });
  };
  
  const fetchData = async () => {
    try {
      if (!scoreId) {
        setError("Score ID is missing. Cannot edit this score.");
        setLoading(false);
        return;
      }
      
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
      // Fetch score data
      const scoreResponse = await axios.get(`${API}/scores/${scoreId}`, config);
      setScore(scoreResponse.data);
      
      // Fetch match details
      const matchResponse = await axios.get(`${API}/matches/${scoreResponse.data.match_id}`, config);
      setMatch(matchResponse.data);
      
      // Fetch match configuration
      const configResponse = await axios.get(`${API}/match-config/${scoreResponse.data.match_id}`, config);
      setMatchConfig(configResponse.data);
      
      // Fetch shooter details
      const shooterResponse = await axios.get(`${API}/shooters/${scoreResponse.data.shooter_id}`, config);
      setShooter(shooterResponse.data);
      
      // Initialize form data with the score
      setFormData({
        shooter_id: scoreResponse.data.shooter_id,
        match_id: scoreResponse.data.match_id,
        match_type_instance: scoreResponse.data.match_type_instance,
        caliber: scoreResponse.data.caliber,
        stages: scoreResponse.data.stages
      });
      
      setLoading(false);
    } catch (err) {
      console.error("Error fetching data:", err);
      let errorMessage = "Failed to load required data. Please try again.";
      if (err.response) {
        console.error("Error response:", err.response.data);
        if (err.response.data && err.response.data.detail) {
          errorMessage = `Error: ${err.response.data.detail}`;
        }
      }
      setError(errorMessage);
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      // Get the token from localStorage
      const token = localStorage.getItem('token');
      if (!token) {
        setError("Authentication required. Please log in again.");
        return;
      }

      // Set authorization header
      const config = {
        headers: { Authorization: `Bearer ${token}` }
      };
      
      const response = await axios.put(`${API}/scores/${scoreId}`, formData, config);
      setSuccess(true);
      setTimeout(() => {
        navigate(`/matches/${formData.match_id}`);
      }, 2000);
    } catch (err) {
      let errorMessage = "Failed to update score. Please try again.";
      if (err.response) {
        if (err.response.data && err.response.data.detail) {
          errorMessage = `Error: ${err.response.data.detail}`;
        }
      }
      setError(errorMessage);
      setLoading(false);
    }
  };

  // Helper to get the matching match type from config
  
  if (!score || !match || !matchConfig || !shooter) {
    return <div className="container mx-auto p-4 text-center">Score data not found</div>;
  }
  
  // Get the matching match type
  const matchingMatchType = findMatchingMatchType(score, matchConfig);
  if (!matchingMatchType) {
    return (
      <div className="container mx-auto p-4 text-center">
        <div className="text-red-500 mb-4">
          Could not find a matching match type for this score. The stage names may not match the current match configuration.
        </div>
        <pre className="text-left bg-gray-100 p-4 rounded overflow-auto">
          {JSON.stringify({ 
            scoreStages: score.stages.map(s => s.name),
            matchTypes: matchConfig.match_types.map(mt => ({
              name: mt.instance_name,
              stages: mt.entry_stages
            }))
          }, null, 2)}
        </pre>
      </div>
    );
  }

  if (success) {
    return (
      <div className="container mx-auto p-4">
        <div className="bg-green-100 text-green-700 p-6 rounded-lg shadow-md text-center">
          <h2 className="text-xl font-bold mb-2">Score Updated Successfully!</h2>
          <p>Redirecting to match details...</p>
        </div>
      </div>
    );
  }

  // Find the match type configuration
  const matchTypeObj = matchingMatchType || matchConfig.match_types.find(mt => mt.instance_name === formData.match_type_instance);
  const maxScore = matchTypeObj ? matchTypeObj.max_score : 0;

  // Calculate subtotals based on stage values
  const calculateSubtotals = () => {
    const subtotals = {};
    
    if (matchTypeObj && matchTypeObj.subtotal_mappings && Object.keys(matchTypeObj.subtotal_mappings).length > 0) {
      for (const [subtotalName, sourceStages] of Object.entries(matchTypeObj.subtotal_mappings)) {
        let subtotalScore = 0;
        let subtotalXCount = 0;
        
        formData.stages.forEach(stage => {
          if (sourceStages.includes(stage.name)) {
            if (stage.score !== null) {
              subtotalScore += stage.score;
            }
            if (stage.x_count !== null) {
              subtotalXCount += stage.x_count;
            }
          }
        });
        
        subtotals[subtotalName] = {
          score: subtotalScore,
          x_count: subtotalXCount
        };
      }
    }
    
    return subtotals;
  };

  // Calculate total score and X count
  const calculateTotals = () => {
    return {
      totalScore: formData.stages.reduce((sum, stage) => 
        stage.score !== null ? sum + stage.score : sum, 0),
      totalXCount: formData.stages.reduce((sum, stage) => 
        stage.x_count !== null ? sum + stage.x_count : sum, 0)
    };
  };

  const subtotals = calculateSubtotals();
  const { totalScore, totalXCount } = calculateTotals();

  return (
    <div className="container mx-auto p-4">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Edit Score</h1>
          <p className="text-gray-600">
            Match: {match.name} ({new Date(match.date).toLocaleDateString()})
          </p>
          <p className="text-gray-600">
            Shooter: {shooter.name}
          </p>
          <p className="text-gray-600">
            Match Type: {matchTypeObj ? matchTypeObj.type : "Unknown"} - {formData.caliber}
          </p>
        </div>
        <Link to={`/matches/${match.id}`} className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600">
          Back to Match
        </Link>
      </div>
      
      <div className="bg-white p-6 rounded-lg shadow">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Entry Stages */}
          <div className="mb-6">
            <h5 className="font-medium mb-3 text-gray-700">Entry Stages</h5>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {formData.stages.map((stage, stageIdx) => (
                <div key={stageIdx} className="border p-3 rounded hover:shadow-md transition-shadow">
                  <h5 className="font-medium mb-2">{stage.name}</h5>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Score
                      </label>
                      <input
                        type="number"
                        min="0"
                        max="100"
                        value={stage.score === null ? "" : stage.score}
                        onChange={(e) => handleStageChange(stageIdx, 'score', e.target.value)}
                        className="w-full px-3 py-1 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                        value={stage.x_count === null ? "" : stage.x_count}
                        onChange={(e) => handleStageChange(stageIdx, 'x_count', e.target.value)}
                        className="w-full px-3 py-1 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          {/* Subtotals Section - Only shown for match types with subtotals */}
          {Object.keys(subtotals).length > 0 && (
            <div className="mb-6">
              <h5 className="font-medium mb-3 text-gray-700">Subtotals (Automatically Calculated)</h5>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(subtotals).map(([subtotalName, values]) => (
                  <div key={subtotalName} className="border p-3 rounded bg-gray-50">
                    <h5 className="font-medium mb-2">{subtotalName}</h5>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Score
                        </label>
                        <div className="w-full px-3 py-1 border rounded bg-gray-100 font-medium">
                          {values.score}
                        </div>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          X Count
                        </label>
                        <div className="w-full px-3 py-1 border rounded bg-gray-100 font-medium">
                          {values.x_count}
                        </div>
                      </div>
                    </div>
                    {matchTypeObj.subtotal_mappings[subtotalName] && (
                      <div className="mt-2 text-xs text-gray-500">
                        Sum of: {matchTypeObj.subtotal_mappings[subtotalName].join(', ')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Grand Total */}
          <div className="mt-4 bg-gray-50 p-3 rounded">
            <h5 className="font-medium mb-2">Total</h5>
            <div className="flex justify-between items-center">
              <div>
                <span className="text-lg font-semibold">{totalScore}</span>
                <span className="text-gray-600"> / {maxScore}</span>
                <span className="ml-4 text-gray-600">X Count: {totalXCount}</span>
              </div>
              <div className="text-sm text-gray-500">
                {Math.round((totalScore / maxScore) * 100)}%
              </div>
            </div>
          </div>
          
          {/* Submit Button */}
          <div className="flex justify-end mt-8">
            <button 
              type="submit" 
              className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
            >
              Update Score
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default EditScore;
