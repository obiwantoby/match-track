import { useState, useEffect } from "react";
import axios from "axios";
import { useParams, Link } from "react-router-dom";
import { useAuth } from "../App";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ShooterDetail = () => {
  const { shooterId } = useParams();
  const { isAdmin } = useAuth();
  const [shooter, setShooter] = useState(null);
  const [report, setReport] = useState(null);
  const [averages, setAverages] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedCaliberTab, setSelectedCaliberTab] = useState(null);
  
  // Edit mode states
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState({
    name: "",
    nra_number: "",
    cmp_number: ""
  });

  useEffect(() => {
    const fetchShooterData = async () => {
      try {
        // Fetch shooter details
        const shooterResponse = await axios.get(`${API}/shooters/${shooterId}`);
        setShooter(shooterResponse.data);
        setEditData({
          name: shooterResponse.data.name,
          nra_number: shooterResponse.data.nra_number || "",
          cmp_number: shooterResponse.data.cmp_number || ""
        });
        
        // Fetch shooter's report
        const reportResponse = await axios.get(`${API}/shooter-report/${shooterId}`);
        setReport(reportResponse.data);
        
        // Fetch shooter's averages
        const averagesResponse = await axios.get(`${API}/shooter-averages/${shooterId}`);
        setAverages(averagesResponse.data);
        
        if (averagesResponse.data.caliber_averages) {
          // Set the first caliber as the selected tab
          const calibers = Object.keys(averagesResponse.data.caliber_averages);
          if (calibers.length > 0) {
            setSelectedCaliberTab(calibers[0]);
          }
        }
        
        setLoading(false);
      } catch (err) {
        console.error("Error fetching shooter details:", err);
        setError("Failed to load shooter details. Please try again.");
        setLoading(false);
      }
    };

    fetchShooterData();
  }, [shooterId]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setEditData({
      ...editData,
      [name]: value
    });
  };

  const handleSave = async () => {
    try {
      const response = await axios.put(`${API}/shooters/${shooterId}`, editData);
      setShooter(response.data);
      setIsEditing(false);
    } catch (err) {
      console.error("Error updating shooter:", err);
      setError("Failed to update shooter details. Please try again.");
    }
  };

  if (loading) return <div className="container mx-auto p-4 text-center">Loading shooter details...</div>;
  if (error) return <div className="container mx-auto p-4 text-center text-red-500">{error}</div>;
  if (!shooter) return <div className="container mx-auto p-4 text-center">Shooter not found</div>;

  const renderPerformanceChart = (caliber) => {
    if (!averages || !averages.caliber_averages || !averages.caliber_averages[caliber]) {
      return (
        <div className="p-6 text-center text-gray-500">
          No performance data available for this caliber.
        </div>
      );
    }

    const data = averages.caliber_averages[caliber];
    const matchCount = data.matches_count;
    
    // Calculate percentage of max possible score for each category
    const sfPercent = (data.sf_score_avg / 100) * 100; // Assuming max SF score is 100
    const tfPercent = (data.tf_score_avg / 100) * 100; // Assuming max TF score is 100
    const rfPercent = (data.rf_score_avg / 100) * 100; // Assuming max RF score is 100
    const nmcPercent = (data.nmc_score_avg / 300) * 100; // Assuming max NMC score is 300
    const totalPercent = (data.total_score_avg / 900) * 100; // Assuming max total score is 900

    return (
      <div className="p-6">
        <div className="mb-4 text-sm text-gray-600">
          Based on {matchCount} matches using {caliber}
        </div>
        
        <div className="space-y-6">
          {/* Slow Fire */}
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-sm font-medium text-gray-700">Slow Fire</span>
              <span className="text-sm font-medium text-gray-700">{data.sf_score_avg}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div className="bg-blue-600 h-2.5 rounded-full" style={{ width: `${sfPercent}%` }}></div>
            </div>
            <div className="mt-1 text-xs text-gray-500">
              X Count: {data.sf_x_count_avg}
            </div>
          </div>
          
          {/* Timed Fire */}
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-sm font-medium text-gray-700">Timed Fire</span>
              <span className="text-sm font-medium text-gray-700">{data.tf_score_avg}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div className="bg-green-500 h-2.5 rounded-full" style={{ width: `${tfPercent}%` }}></div>
            </div>
            <div className="mt-1 text-xs text-gray-500">
              X Count: {data.tf_x_count_avg}
            </div>
          </div>
          
          {/* Rapid Fire */}
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-sm font-medium text-gray-700">Rapid Fire</span>
              <span className="text-sm font-medium text-gray-700">{data.rf_score_avg}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div className="bg-purple-500 h-2.5 rounded-full" style={{ width: `${rfPercent}%` }}></div>
            </div>
            <div className="mt-1 text-xs text-gray-500">
              X Count: {data.rf_x_count_avg}
            </div>
          </div>
          
          {/* NMC */}
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-sm font-medium text-gray-700">National Match Course</span>
              <span className="text-sm font-medium text-gray-700">{data.nmc_score_avg}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div className="bg-yellow-500 h-2.5 rounded-full" style={{ width: `${nmcPercent}%` }}></div>
            </div>
            <div className="mt-1 text-xs text-gray-500">
              X Count: {data.nmc_x_count_avg}
            </div>
          </div>
          
          {/* Total Score */}
          <div className="pt-4 border-t">
            <div className="flex justify-between mb-1">
              <span className="text-sm font-medium text-gray-700">Overall Performance</span>
              <span className="text-sm font-medium text-gray-700">{data.total_score_avg}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div className="bg-red-500 h-2.5 rounded-full" style={{ width: `${totalPercent}%` }}></div>
            </div>
            <div className="mt-1 text-xs text-gray-500">
              X Count: {data.total_x_count_avg}
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="container mx-auto p-4">
      {/* Shooter Info Card */}
      <div className="bg-white rounded-lg shadow-md mb-8">
        <div className="p-6">
          <div className="flex justify-between items-start">
            <div>
              {isEditing ? (
                <input
                  type="text"
                  name="name"
                  value={editData.name}
                  onChange={handleInputChange}
                  className="text-3xl font-bold bg-gray-100 border rounded px-2 py-1 mb-2 w-full"
                />
              ) : (
                <h1 className="text-3xl font-bold mb-2">{shooter.name}</h1>
              )}
              
              <div className="mt-4 space-y-2">
                <div className="flex items-center">
                  <span className="text-gray-600 w-24">NRA Number:</span>
                  {isEditing ? (
                    <input
                      type="text"
                      name="nra_number"
                      value={editData.nra_number}
                      onChange={handleInputChange}
                      className="bg-gray-100 border rounded px-2 py-1 w-full"
                      placeholder="Enter NRA Number"
                    />
                  ) : (
                    <span className="font-medium">{shooter.nra_number || "Not provided"}</span>
                  )}
                </div>
                
                <div className="flex items-center">
                  <span className="text-gray-600 w-24">CMP Number:</span>
                  {isEditing ? (
                    <input
                      type="text"
                      name="cmp_number"
                      value={editData.cmp_number}
                      onChange={handleInputChange}
                      className="bg-gray-100 border rounded px-2 py-1 w-full"
                      placeholder="Enter CMP Number"
                    />
                  ) : (
                    <span className="font-medium">{shooter.cmp_number || "Not provided"}</span>
                  )}
                </div>
              </div>
            </div>
            
            <div className="flex space-x-3">
              {isAdmin() && !isEditing && (
                <button
                  onClick={() => setIsEditing(true)}
                  className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                >
                  Edit Shooter
                </button>
              )}
              
              {isEditing && (
                <>
                  <button
                    onClick={handleSave}
                    className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                  >
                    Save
                  </button>
                  <button
                    onClick={() => setIsEditing(false)}
                    className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700"
                  >
                    Cancel
                  </button>
                </>
              )}
              
              <Link to="/shooters" className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600">
                Back to Shooters
              </Link>
            </div>
          </div>
        </div>
      </div>
      
      {/* Performance Tabs */}
      {averages && averages.caliber_averages && Object.keys(averages.caliber_averages).length > 0 ? (
        <div className="bg-white rounded-lg shadow-md mb-8">
          <div className="px-6 py-4 border-b">
            <h2 className="text-2xl font-semibold">Performance Analysis</h2>
          </div>
          
          {/* Caliber Tabs */}
          <div className="border-b">
            <div className="flex overflow-x-auto">
              {Object.keys(averages.caliber_averages).map(caliber => (
                <button
                  key={caliber}
                  onClick={() => setSelectedCaliberTab(caliber)}
                  className={`px-6 py-3 font-medium text-sm whitespace-nowrap ${
                    selectedCaliberTab === caliber
                      ? "border-b-2 border-blue-600 text-blue-600"
                      : "text-gray-500 hover:text-gray-700"
                  }`}
                >
                  {caliber}
                </button>
              ))}
            </div>
          </div>
          
          {/* Selected Caliber Performance */}
          {selectedCaliberTab && renderPerformanceChart(selectedCaliberTab)}
        </div>
      ) : (
        <div className="bg-white p-6 rounded-lg shadow-md mb-8">
          <p className="text-gray-500">No performance data available yet. Shooter needs to participate in matches.</p>
        </div>
      )}
      
      {/* Match History */}
      <div className="bg-white rounded-lg shadow-md">
        <div className="px-6 py-4 border-b">
          <h2 className="text-2xl font-semibold">Match History</h2>
        </div>
        
        {report && report.matches && Object.keys(report.matches).length > 0 ? (
          <div className="p-6 space-y-6">
            {Object.entries(report.matches).map(([matchId, matchData]) => (
              <div key={matchId} className="border rounded-lg overflow-hidden">
                <div className="px-5 py-3 bg-gray-50 border-b">
                  <h3 className="text-lg font-semibold">
                    <Link to={`/matches/${matchId}`} className="text-blue-600 hover:underline">
                      {matchData.match.name}
                    </Link>
                  </h3>
                  <p className="text-sm text-gray-600">
                    {new Date(matchData.match.date).toLocaleDateString()} • {matchData.match.location}
                  </p>
                </div>
                
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Match Type</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Caliber</th>
                        <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase">Score</th>
                        <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase">X Count</th>
                        <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Details</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {matchData.scores.map((scoreEntry, idx) => (
                        <tr key={idx}>
                          <td className="px-4 py-2 whitespace-nowrap">
                            {scoreEntry.match_type ? scoreEntry.match_type.instance_name : scoreEntry.score.match_type_instance}
                          </td>
                          <td className="px-4 py-2 whitespace-nowrap">
                            {scoreEntry.score.caliber}
                          </td>
                          <td className="px-4 py-2 text-center font-medium">
                            {scoreEntry.score.total_score}
                          </td>
                          <td className="px-4 py-2 text-center">
                            {scoreEntry.score.total_x_count}
                          </td>
                          <td className="px-4 py-2 text-right">
                            <button 
                              onClick={() => {
                                // This would open a modal with details, but for now just use an alert
                                const stages = scoreEntry.score.stages
                                  .map(s => `${s.name}: ${s.score} (${s.x_count}X)`)
                                  .join(', ');
                                alert(`Score Breakdown: ${stages}`);
                              }}
                              className="text-blue-600 hover:text-blue-800 text-sm"
                            >
                              View Stages
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-6 text-center">
            <p className="text-gray-500">No match history found for this shooter.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ShooterDetail;
