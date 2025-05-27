import { useState, useEffect } from "react";
import axios from "axios";
import { useParams, useNavigate, Link } from "react-router-dom";
import getAPIUrl from "./API_FIX";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = getAPIUrl(BACKEND_URL);

const ScoreEntry = () => {
  const { matchId } = useParams();
  const navigate = useNavigate();
  const [match, setMatch] = useState(null);
  const [matchConfig, setMatchConfig] = useState(null);
  const [shooters, setShooters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  
  // Updated formData to handle multiple match types and calibers in one submission
  const [formData, setFormData] = useState({
    shooter_id: "",
    match_id: matchId,
    scores: []
  });
  
  useEffect(() => {
    const fetchData = async () => {
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

        // Fetch match details
        const matchResponse = await axios.get(`${API}/matches/${matchId}`, config);
        setMatch(matchResponse.data);
        
        // Fetch match configuration
        const configResponse = await axios.get(`${API}/match-config/${matchId}`, config);
        setMatchConfig(configResponse.data);
        
        // Fetch all shooters
        const shootersResponse = await axios.get(`${API}/shooters`, config);
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

  // Initialize score forms when shooter is selected and match config is loaded
  useEffect(() => {
    if (matchConfig && formData.shooter_id && matchConfig.match_types.length > 0) {
      const fetchExistingScores = async () => {
        try {
          // Get the token from localStorage
          const token = localStorage.getItem('token');
          if (!token) {
            return;
          }

          // Set authorization header
          const config = {
            headers: { Authorization: `Bearer ${token}` }
          };

          // Fetch existing scores for this shooter and match
          const scoreResponse = await axios.get(`${API}/scores?shooter_id=${formData.shooter_id}&match_id=${matchId}`, config);
          const existingScores = scoreResponse.data;

          // Map of existing scores by match type and caliber
          const existingScoreMap = {};
          existingScores.forEach(score => {
            const key = `${score.match_type_instance}-${score.caliber}`;
            existingScoreMap[key] = score;
          });

          const initialScores = [];
          
          // Create a score entry form for each match type and caliber combination
          matchConfig.match_types.forEach(matchType => {
            matchType.calibers.forEach(caliber => {
              const key = `${matchType.instance_name}-${caliber}`;
              
              // Check if we have existing scores for this match type and caliber
              if (existingScoreMap[key]) {
                // Use existing scores to prefill the form
                initialScores.push({
                  match_type_instance: matchType.instance_name,
                  caliber: caliber,
                  stages: existingScoreMap[key].stages
                });
              } else {
                // Only create entries for the actual entry stages (not subtotals)
                const stages = matchType.entry_stages.map(stageName => ({
                  name: stageName,
                  score: null,
                  x_count: null
                }));
                
                initialScores.push({
                  match_type_instance: matchType.instance_name,
                  caliber: caliber,
                  stages: stages
                });
              }
            });
          });
          
          setFormData({
            ...formData,
            scores: initialScores
          });
        } catch (err) {
          console.error("Error fetching existing scores:", err);
          
          // Fallback to empty scores if we can't fetch existing ones
          const initialScores = [];
          
          // Create a score entry form for each match type and caliber combination
          matchConfig.match_types.forEach(matchType => {
            matchType.calibers.forEach(caliber => {
              // Only create entries for the actual entry stages (not subtotals)
              const stages = matchType.entry_stages.map(stageName => ({
                name: stageName,
                score: null,
                x_count: null
              }));
              
              initialScores.push({
                match_type_instance: matchType.instance_name,
                caliber: caliber,
                stages: stages
              });
            });
          });
          
          setFormData({
            ...formData,
            scores: initialScores
          });
        }
      };

      fetchExistingScores();
    }
  }, [formData.shooter_id, matchConfig, matchId]);

  const handleShooterChange = (e) => {
    setFormData({
      ...formData,
      shooter_id: e.target.value,
      scores: [] // Reset scores when shooter changes
    });
  };

  const handleStageChange = (scoreIndex, stageIndex, field, value) => {
    const updatedScores = [...formData.scores];
    
    // If value is empty string, set it to null to represent a skipped match
    if (value === "") {
      updatedScores[scoreIndex].stages[stageIndex][field] = null;
    } else {
      // Otherwise parse it as an integer
      updatedScores[scoreIndex].stages[stageIndex][field] = parseInt(value, 10);
    }
    
    setFormData({
      ...formData,
      scores: updatedScores
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.shooter_id || formData.scores.length === 0) {
      setError("Please select a shooter and enter scores");
      return;
    }
    
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
      
      // Submit each score entry
      const submissionPromises = formData.scores.map(scoreEntry => {
        return axios.post(`${API}/scores`, {
          shooter_id: formData.shooter_id,
          match_id: matchId,
          match_type_instance: scoreEntry.match_type_instance,
          caliber: scoreEntry.caliber,
          stages: scoreEntry.stages
        }, config);
      });
      
      await Promise.all(submissionPromises);
      setSuccess(true);
      setTimeout(() => {
        navigate(`/matches/${matchId}`);
      }, 2000);
    } catch (err) {
      console.error("Error submitting scores:", err);
      setError("Failed to save scores. Please try again.");
    }
  };

  if (loading) return <div className="container mx-auto p-4 text-center">Loading form data...</div>;
  if (error) return <div className="container mx-auto p-4 text-center text-red-500">{error}</div>;
  if (!match || !matchConfig) return <div className="container mx-auto p-4 text-center">Match data not found</div>;

  if (success) {
    return (
      <div className="container mx-auto p-4">
        <div className="bg-green-100 text-green-700 p-6 rounded-lg shadow-md text-center">
          <h2 className="text-xl font-bold mb-2">Scores Saved Successfully!</h2>
          <p>Redirecting to match details...</p>
        </div>
      </div>
    );
  }

  // Group scores by match type
  const scoresByType = {};
  if (formData.scores.length > 0) {
    formData.scores.forEach(score => {
      const matchTypeObj = matchConfig.match_types.find(mt => mt.instance_name === score.match_type_instance);
      if (!matchTypeObj) return;
      
      const key = matchTypeObj.type;
      if (!scoresByType[key]) {
        scoresByType[key] = [];
      }
      scoresByType[key].push({
        ...score,
        matchTypeObj // Add the match type configuration to the score object
      });
    });
  }

  // Helper function to calculate subtotals based on stage values
  const calculateSubtotals = (score, matchTypeObj) => {
    const subtotals = {};
    
    if (matchTypeObj.subtotal_mappings && Object.keys(matchTypeObj.subtotal_mappings).length > 0) {
      for (const [subtotalName, sourceStages] of Object.entries(matchTypeObj.subtotal_mappings)) {
        let subtotalScore = 0;
        let subtotalXCount = 0;
        
        score.stages.forEach(stage => {
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

  // Helper function to calculate total score and X count for a score
  const calculateTotals = (score) => {
    // Check if all stages have null scores (not shot match)
    const allNull = score.stages.every(stage => stage.score === null);
    
    if (allNull) {
      return {
        totalScore: null,
        totalXCount: null,
        allStagesTotalNull: true
      };
    }
    
    return {
      totalScore: score.stages.reduce((sum, stage) => 
        stage.score !== null ? sum + stage.score : sum, 0),
      totalXCount: score.stages.reduce((sum, stage) => 
        stage.x_count !== null ? sum + stage.x_count : sum, 0),
      allStagesTotalNull: false
    };
  };

  return (
    <div className="container mx-auto p-4">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Add Scores</h1>
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
          {/* Shooter Selection */}
          <div className="mb-6">
            <label htmlFor="shooter_id" className="block text-lg font-medium text-gray-700 mb-2">
              Shooter
            </label>
            <select
              id="shooter_id"
              value={formData.shooter_id}
              onChange={handleShooterChange}
              className="w-full md:w-1/2 px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
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
          
          {formData.shooter_id && Object.keys(scoresByType).length > 0 && (
            <div className="space-y-8">
              {/* Score Forms Grouped by Match Type */}
              {Object.entries(scoresByType).map(([matchType, scores]) => (
                <div key={matchType} className="border rounded-lg overflow-hidden">
                  <div className="bg-gray-100 p-4 border-b">
                    <h3 className="text-lg font-semibold">{matchType} Scores</h3>
                    <p className="text-sm text-gray-600 mt-1">
                      Enter scores for all calibers in this match type
                    </p>
                  </div>
                  
                  <div className="p-4">
                    {/* Caliber Tabs */}
                    <div className="border-b mb-4">
                      <div className="flex overflow-x-auto">
                        {scores.map((score, idx) => (
                          <button
                            key={idx}
                            type="button"
                            onClick={() => {
                              // Scroll to the caliber's section
                              document.getElementById(`score-${matchType}-${score.caliber}`).scrollIntoView({
                                behavior: 'smooth',
                                block: 'start'
                              });
                            }}
                            className="px-4 py-2 font-medium text-sm whitespace-nowrap text-gray-600 hover:text-gray-900"
                          >
                            {score.caliber}
                          </button>
                        ))}
                      </div>
                    </div>
                    
                    {/* Score Forms for Each Caliber */}
                    <div className="space-y-8">
                      {scores.map((score, scoreIdx) => {
                        const scoreIndex = formData.scores.findIndex(
                          s => s.match_type_instance === score.match_type_instance && s.caliber === score.caliber
                        );
                        
                        if (scoreIndex === -1) return null;
                        
                        const matchTypeObj = score.matchTypeObj;
                        const maxScore = matchTypeObj ? matchTypeObj.max_score : 0;
                        
                        // Calculate stage totals
                        const { totalScore, totalXCount, allStagesTotalNull } = calculateTotals(formData.scores[scoreIndex]);
                        
                        // Calculate subtotals if any
                        const subtotals = calculateSubtotals(formData.scores[scoreIndex], matchTypeObj);
                        
                        return (
                          <div 
                            key={`${score.match_type_instance}-${score.caliber}`}
                            id={`score-${matchType}-${score.caliber}`}
                            className="border rounded-lg p-4"
                          >
                            <h4 className="text-lg font-medium mb-3">
                              {score.match_type_instance} - {score.caliber}
                            </h4>
                            
                            {/* Entry Stages */}
                            <div className="mb-6">
                              <h5 className="font-medium mb-3 text-gray-700">Entry Stages</h5>
                              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {formData.scores[scoreIndex].stages.map((stage, stageIdx) => (
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
                                          onChange={(e) => handleStageChange(scoreIndex, stageIdx, 'score', e.target.value)}
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
                                          onChange={(e) => handleStageChange(scoreIndex, stageIdx, 'x_count', e.target.value)}
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
                            
                            {/* Grand Total for this caliber */}
                            <div className="mt-4 bg-gray-50 p-3 rounded">
                              <h5 className="font-medium mb-2">Total</h5>
                              <div className="flex justify-between items-center">
                                {totalScore === null || allStagesTotalNull ? (
                                  <div>
                                    <span className="text-lg font-semibold">-</span>
                                    <span className="ml-4 text-gray-600">X Count: -</span>
                                  </div>
                                ) : (
                                  <>
                                    <div>
                                      <span className="text-lg font-semibold">{totalScore}</span>
                                      <span className="text-gray-600"> / {maxScore}</span>
                                      <span className="ml-4 text-gray-600">X Count: {totalXCount}</span>
                                    </div>
                                    <div className="text-sm text-gray-500">
                                      {maxScore > 0 ? Math.round((totalScore / maxScore) * 100) : 0}%
                                    </div>
                                  </>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              ))}
              
              {/* Submit Button */}
              <div className="flex justify-end mt-8">
                <button 
                  type="submit" 
                  className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
                >
                  Save All Scores
                </button>
              </div>
            </div>
          )}
          
          {formData.shooter_id && Object.keys(scoresByType).length === 0 && (
            <div className="text-center p-8 bg-gray-50 rounded-lg">
              <p className="text-gray-500">
                No match types configured for this match. Please update the match configuration.
              </p>
            </div>
          )}
          
          {!formData.shooter_id && (
            <div className="text-center p-8 bg-gray-50 rounded-lg">
              <p className="text-gray-500">
                Please select a shooter to enter scores.
              </p>
            </div>
          )}
        </form>
      </div>
    </div>
  );
};

export default ScoreEntry;