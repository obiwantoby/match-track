import { useState, useEffect } from "react";
import axios from "axios";
import { useParams, useNavigate, Link } from "react-router-dom";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

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
    const fetchData = async () => {
      try {
        // Fetch score details
        const scoreResponse = await axios.get(`${API}/scores/${scoreId}`);
        setScore(scoreResponse.data);
        
        // Fetch match details
        const matchResponse = await axios.get(`${API}/matches/${scoreResponse.data.match_id}`);
        setMatch(matchResponse.data);
        
        // Fetch match configuration
        const configResponse = await axios.get(`${API}/match-config/${scoreResponse.data.match_id}`);
        setMatchConfig(configResponse.data);
        
        // Fetch shooter details
        const shooterResponse = await axios.get(`${API}/shooters/${scoreResponse.data.shooter_id}`);
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
        setError("Failed to load required data. Please try again.");
        setLoading(false);
      }
    };

    fetchData();
  }, [scoreId]);

  const handleStageChange = (stageIndex, field, value) => {
    const updatedStages = [...formData.stages];
    // Convert value to integer, default to 0 if NaN
    updatedStages[stageIndex][field] = parseInt(value, 10) || 0;
    
    setFormData({
      ...formData,
      stages: updatedStages
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      // Update the score
      await axios.put(`${API}/scores/${scoreId}`, formData);
      setSuccess(true);
      setTimeout(() => {
        navigate(`/matches/${formData.match_id}`);
      }, 2000);
    } catch (err) {
      console.error("Error updating score:", err);
      setError("Failed to update score. Please try again.");
    }
  };

  if (loading) return <div className="container mx-auto p-4 text-center">Loading score data...</div>;
  if (error) return <div className="container mx-auto p-4 text-center text-red-500">{error}</div>;
  if (!score || !match || !matchConfig || !shooter) return <div className="container mx-auto p-4 text-center">Score data not found</div>;

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
  const matchTypeObj = matchConfig.match_types.find(mt => mt.instance_name === formData.match_type_instance);
  const maxScore = matchTypeObj ? matchTypeObj.max_score : 0;
  const is900 = matchTypeObj && matchTypeObj.type === "900";

  // Calculate subtotals based on stage values
  const calculateSubtotals = () => {
    const subtotals = {};
    
    if (matchTypeObj && matchTypeObj.subtotal_mappings && Object.keys(matchTypeObj.subtotal_mappings).length > 0) {
      for (const [subtotalName, sourceStages] of Object.entries(matchTypeObj.subtotal_mappings)) {
        let subtotalScore = 0;
        let subtotalXCount = 0;
        
        formData.stages.forEach(stage => {
          if (sourceStages.includes(stage.name)) {
            subtotalScore += stage.score;
            subtotalXCount += stage.x_count;
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
      totalScore: formData.stages.reduce((sum, stage) => sum + stage.score, 0),
      totalXCount: formData.stages.reduce((sum, stage) => sum + stage.x_count, 0)
    };
  };

  // Calculate the special 900 total (based on NMC subtotals)
  const calculate900Total = () => {
    if (is900) {
      const subtotals = calculateSubtotals();
      
      if (subtotals.SFNMC && subtotals.TFNMC && subtotals.RFNMC) {
        return {
          totalScore: subtotals.SFNMC.score + subtotals.TFNMC.score + subtotals.RFNMC.score,
          totalXCount: subtotals.SFNMC.x_count + subtotals.TFNMC.x_count + subtotals.RFNMC.x_count
        };
      }
    }
    
    return calculateTotals();
  };

  const subtotals = calculateSubtotals();
  const { totalScore, totalXCount } = is900 ? calculate900Total() : calculateTotals();

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
                        value={stage.score}
                        onChange={(e) => handleStageChange(stageIdx, 'score', e.target.value)}
                        className="w-full px-3 py-1 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                        onChange={(e) => handleStageChange(stageIdx, 'x_count', e.target.value)}
                        className="w-full px-3 py-1 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
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
            {is900 && (
              <div className="mt-2 text-xs text-gray-500">
                For 900 Match Type: Total is the sum of SFNMC, TFNMC, and RFNMC subtotals.
              </div>
            )}
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
