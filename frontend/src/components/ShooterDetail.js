import { useState, useEffect } from "react";
import axios from "axios";
import { useParams, Link } from "react-router-dom";
import { useAuth } from "../App";
import getAPIUrl from "./API_FIX";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
// Check if BACKEND_URL already contains /api to avoid duplication
const API = getAPIUrl(BACKEND_URL);

const ShooterDetail = () => {
  const { shooterId } = useParams();
  const { isAdmin } = useAuth();
  const [shooter, setShooter] = useState(null);
  const [report, setReport] = useState(null);
  const [averages, setAverages] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedCaliberTab, setSelectedCaliberTab] = useState(null);
  const [selectedYear, setSelectedYear] = useState("all");
  const [availableYears, setAvailableYears] = useState([]);
  
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
        
        // Fetch shooter report
        const reportResponse = await axios.get(`${API}/shooter-report/${shooterId}`);
        setReport(reportResponse.data);
        
        // Extract unique years from match dates
        if (reportResponse.data && reportResponse.data.matches) {
          const years = [...new Set(Object.values(reportResponse.data.matches).map(match => 
            new Date(match.match.date).getFullYear()
          ))].sort((a, b) => b - a); // Sort years in descending order
          
          setAvailableYears(years);
          
          // Set selected year to the most recent year if available
          if (years.length > 0) {
            setSelectedYear(years[0].toString());
          }
        }
        
        // Fetch shooter averages for the caliber tabs
        const averagesResponse = await axios.get(`${API}/shooter-averages/${shooterId}`);
        setAverages(averagesResponse.data);
        
        // Set default caliber tab if available
        if (averagesResponse.data && averagesResponse.data.caliber_averages) {
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

  // Handle editing shooter info
  const handleEditClick = () => {
    if (shooter) {
      setEditData({
        name: shooter.name,
        nra_number: shooter.nra_number || "",
        cmp_number: shooter.cmp_number || ""
      });
      setIsEditing(true);
    }
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setEditData({
      ...editData,
      [name]: value
    });
  };

  const handleSaveEdit = async () => {
    try {
      // This would normally be a PUT request to update the shooter
      // but for this example, we'll just update the local state
      setShooter({
        ...shooter,
        ...editData
      });
      
      setIsEditing(false);
    } catch (err) {
      console.error("Error updating shooter:", err);
      setError("Failed to update shooter details. Please try again.");
    }
  };

  // Tab navigation
  const [activeTab, setActiveTab] = useState("overview");

  if (loading) return <div className="container mx-auto p-4 text-center">Loading shooter details...</div>;
  if (error) return <div className="container mx-auto p-4 text-center text-red-500">{error}</div>;
  if (!shooter) return <div className="container mx-auto p-4 text-center">Shooter not found</div>;

  // Helper formatting functions
  const formatCaliber = (caliber) => {
    switch(caliber) {
      case "TWENTYTWO": return ".22";
      case "CENTERFIRE": return "CF";
      case "FORTYFIVE": return ".45";
      case "NINESERVICE": return "9mm Service";
      case "FORTYFIVESERVICE": return "45 Service";
      default: return caliber;
    }
  };

  // Overview section
  const renderOverview = () => {
    return (
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4">Shooter Information</h2>
        
        {!isEditing ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <div className="mb-4">
                <p className="text-sm text-gray-500">Name</p>
                <p className="font-medium">{shooter.name}</p>
              </div>
              <div className="mb-4">
                <p className="text-sm text-gray-500">NRA Number</p>
                <p className="font-medium">{shooter.nra_number || "Not provided"}</p>
              </div>
              <div className="mb-4">
                <p className="text-sm text-gray-500">CMP Number</p>
                <p className="font-medium">{shooter.cmp_number || "Not provided"}</p>
              </div>
            </div>
            
            <div>
              {averages && averages.caliber_averages && Object.keys(averages.caliber_averages).length > 0 && (
                <div>
                  <p className="text-sm text-gray-500 mb-2">Average Scores by Caliber</p>
                  <div className="grid grid-cols-1 gap-3">
                    {Object.entries(averages.caliber_averages).map(([caliber, data]) => (
                      <div key={caliber} className="flex items-center justify-between p-2 border rounded">
                        <div className="font-medium">{formatCaliber(caliber)}</div>
                        <div className="text-right">
                          <div className="font-semibold">{data.total_score_avg} / {data.matches_count > 0 ? (data.total_score_avg / data.matches_count).toFixed(2) : 0}</div>
                          <div className="text-xs text-gray-500">{data.matches_count} matches</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {isAdmin() && (
                <div className="mt-6 flex justify-end">
                  <button 
                    onClick={handleEditClick}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    Edit Shooter
                  </button>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                  Name
                </label>
                <input
                  id="name"
                  name="name"
                  type="text"
                  value={editData.name}
                  onChange={handleInputChange}
                  className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label htmlFor="nra_number" className="block text-sm font-medium text-gray-700 mb-1">
                  NRA Number
                </label>
                <input
                  id="nra_number"
                  name="nra_number"
                  type="text"
                  value={editData.nra_number}
                  onChange={handleInputChange}
                  className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            
            <div className="mb-4">
              <label htmlFor="cmp_number" className="block text-sm font-medium text-gray-700 mb-1">
                CMP Number
              </label>
              <input
                id="cmp_number"
                name="cmp_number"
                type="text"
                value={editData.cmp_number}
                onChange={handleInputChange}
                className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            <div className="flex justify-end space-x-3">
              <button 
                onClick={handleCancelEdit}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
              >
                Cancel
              </button>
              <button 
                onClick={handleSaveEdit}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Save
              </button>
            </div>
          </div>
        )}
      </div>
    );
  };

  // Match History section
  const renderMatchHistory = () => {
    if (!report || !report.matches || Object.keys(report.matches).length === 0) {
      return (
        <div className="bg-white p-6 rounded-lg shadow text-center">
          <p className="text-gray-500 mb-4">This shooter has not participated in any matches.</p>
          {isAdmin() && (
            <Link to="/matches" className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
              Add Scores
            </Link>
          )}
        </div>
      );
    }

    // Filter matches by selected year if not "all"
    const filteredMatches = selectedYear === "all"
      ? report.matches
      : Object.fromEntries(
          Object.entries(report.matches).filter(([_, matchData]) => {
            const matchYear = new Date(matchData.match.date).getFullYear().toString();
            return matchYear === selectedYear;
          })
        );

    // Handle case when no matches exist for the selected year
    if (Object.keys(filteredMatches).length === 0) {
      return (
        <div className="bg-white p-6 rounded-lg shadow text-center">
          <p className="text-gray-500 mb-4">No matches found for the selected year ({selectedYear}).</p>
          <button 
            onClick={() => setSelectedYear("all")}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            View All Years
          </button>
        </div>
      );
    }

    return (
      <div className="space-y-6">
        {Object.entries(filteredMatches).map(([matchId, matchData]) => {
          const match = matchData.match;
          const scores = matchData.scores;
          
          return (
            <div key={matchId} className="bg-white p-6 rounded-lg shadow">
              <div className="mb-4 flex justify-between items-start">
                <div>
                  <h3 className="text-lg font-semibold mb-1">
                    <Link to={`/matches/${matchId}`} className="text-blue-600 hover:underline">
                      {match.name}
                    </Link>
                  </h3>
                  <div className="text-sm text-gray-600 mb-1">
                    {new Date(match.date).toLocaleDateString()} at {match.location}
                  </div>
                  {match.aggregate_type !== "None" && (
                    <div className="text-sm">
                      <span className="font-medium text-gray-700">Aggregate: </span>
                      <span className="text-blue-600">{match.aggregate_type}</span>
                    </div>
                  )}
                </div>
                
                <Link 
                  to={`/matches/${matchId}`} 
                  className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                >
                  View Full Match
                </Link>
              </div>
              
              <div className="mt-4">
                <h4 className="font-medium text-gray-700 mb-3">Scores:</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {scores.map((scoreData, index) => {
                    const { score, match_type } = scoreData;
                    if (!match_type) return null;
                    
                    return (
                      <div key={index} className="border rounded p-3 bg-gray-50">
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <div className="font-medium">{match_type.type}</div>
                            <div className="text-sm text-gray-600">{formatCaliber(score.caliber)}</div>
                          </div>
                          {isAdmin() && (
                            <Link 
                              to={`/scores/edit/${score.id}`}
                              className="text-green-600 hover:text-green-800 text-xs font-medium"
                            >
                              Edit
                            </Link>
                          )}
                        </div>
                        <div className="mt-2 flex justify-between">
                          <div>
                            <span className="text-gray-600 text-sm">Score:</span>
                            <span className="ml-1 font-semibold">{score.total_score === null ? "-" : score.total_score}</span>
                          </div>
                          <div>
                            <span className="text-gray-600 text-sm">X Count:</span>
                            <span className="ml-1 font-semibold">{score.total_x_count === null ? "-" : score.total_x_count}</span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  // Statistics section
  const renderStatistics = () => {
    // Check for report and averages
    if (!report || !report.averages || 
        (!report.averages.by_match_type || Object.keys(report.averages.by_match_type).length === 0) && 
        (!report.averages.by_caliber || Object.keys(report.averages.by_caliber).length === 0)) {
      return (
        <div className="bg-white p-6 rounded-lg shadow text-center">
          <p className="text-gray-500">Not enough match data to generate statistics.</p>
        </div>
      );
    }
    
    // Filter and calculate statistics based on the selected year
    const calculateYearlyStatistics = () => {
      if (!report || !report.matches) return null;
      
      // Get all matches for the selected year
      const yearMatches = selectedYear === "all" 
        ? report.matches 
        : Object.fromEntries(
            Object.entries(report.matches).filter(([_, matchData]) => {
              const matchYear = new Date(matchData.match.date).getFullYear().toString();
              return matchYear === selectedYear;
            })
          );
      
      if (Object.keys(yearMatches).length === 0) {
        return null; // No matches for the selected year
      }
      
      // Group scores by caliber and calculate statistics
      const caliberStats = {};
      
      Object.values(yearMatches).forEach(matchData => {
        matchData.scores.forEach(scoreData => {
          const { score, match_type } = scoreData;
          if (!score || !match_type) return;
          
          const caliber = score.caliber;
          
          // Initialize caliber stats if not exists
          if (!caliberStats[caliber]) {
            caliberStats[caliber] = {
              matches_count: 0,
              sf_score_sum: 0,
              sf_x_count_sum: 0,
              tf_score_sum: 0,
              tf_x_count_sum: 0,
              rf_score_sum: 0,
              rf_x_count_sum: 0,
              nmc_score_sum: 0,
              nmc_x_count_sum: 0,
              total_score_sum: 0,
              total_x_count_sum: 0,
              scores: []
            };
          }
          
          // Add to statistics
          caliberStats[caliber].matches_count++;
          
          // Only add to totals if the score is not null
          if (score.total_score !== null) {
            caliberStats[caliber].total_score_sum += score.total_score;
            caliberStats[caliber].total_x_count_sum += (score.total_x_count !== null ? score.total_x_count : 0);
            caliberStats[caliber].valid_matches_count = (caliberStats[caliber].valid_matches_count || 0) + 1;
          }
          
          caliberStats[caliber].scores.push(score);
          
          // Process stages
          score.stages.forEach(stage => {
            if (stage.score === null) return; // Skip null scores
            
            if (stage.name.includes("SF")) {
              caliberStats[caliber].sf_score_sum += stage.score;
              caliberStats[caliber].sf_x_count_sum += stage.x_count;
              caliberStats[caliber].sf_valid_count = (caliberStats[caliber].sf_valid_count || 0) + 1;
            } else if (stage.name.includes("TF")) {
              caliberStats[caliber].tf_score_sum += stage.score;
              caliberStats[caliber].tf_x_count_sum += stage.x_count;
              caliberStats[caliber].tf_valid_count = (caliberStats[caliber].tf_valid_count || 0) + 1;
            } else if (stage.name.includes("RF")) {
              caliberStats[caliber].rf_score_sum += stage.score;
              caliberStats[caliber].rf_x_count_sum += stage.x_count;
              caliberStats[caliber].rf_valid_count = (caliberStats[caliber].rf_valid_count || 0) + 1;
            }
          });
          
          // Add to NMC stats if it's an NMC match
          if ((match_type.type === "NMC" || score.match_type_instance.includes("NMC")) && score.total_score !== null) {
            caliberStats[caliber].nmc_score_sum += score.total_score;
            caliberStats[caliber].nmc_x_count_sum += score.total_x_count;
            caliberStats[caliber].nmc_valid_count = (caliberStats[caliber].nmc_valid_count || 0) + 1;
          }
        });
      });
      
      // Calculate averages
      Object.keys(caliberStats).forEach(caliber => {
        const stats = caliberStats[caliber];
        const total_valid_count = stats.valid_matches_count || 0;
        const sf_valid_count = stats.sf_valid_count || 0;
        const tf_valid_count = stats.tf_valid_count || 0;
        const rf_valid_count = stats.rf_valid_count || 0;
        const nmc_valid_count = stats.nmc_valid_count || 0;
        
        if (total_valid_count > 0) {
          caliberStats[caliber] = {
            ...stats,
            matches_count: stats.matches_count,
            valid_matches_count: total_valid_count,
            sf_score_avg: sf_valid_count > 0 ? Math.round((stats.sf_score_sum / sf_valid_count) * 100) / 100 : 0,
            sf_x_count_avg: sf_valid_count > 0 ? Math.round((stats.sf_x_count_sum / sf_valid_count) * 100) / 100 : 0,
            tf_score_avg: tf_valid_count > 0 ? Math.round((stats.tf_score_sum / tf_valid_count) * 100) / 100 : 0,
            tf_x_count_avg: tf_valid_count > 0 ? Math.round((stats.tf_x_count_sum / tf_valid_count) * 100) / 100 : 0,
            rf_score_avg: rf_valid_count > 0 ? Math.round((stats.rf_score_sum / rf_valid_count) * 100) / 100 : 0,
            rf_x_count_avg: rf_valid_count > 0 ? Math.round((stats.rf_x_count_sum / rf_valid_count) * 100) / 100 : 0,
            nmc_score_avg: nmc_valid_count > 0 ? Math.round((stats.nmc_score_sum / nmc_valid_count) * 100) / 100 : 0,
            nmc_x_count_avg: nmc_valid_count > 0 ? Math.round((stats.nmc_x_count_sum / nmc_valid_count) * 100) / 100 : 0,
            total_score_avg: Math.round((stats.total_score_sum / total_valid_count) * 100) / 100,
            total_x_count_avg: Math.round((stats.total_x_count_sum / total_valid_count) * 100) / 100
          };
        }
      });
      
      return { caliber_averages: caliberStats };
    };
    
    // Use filtered stats if a specific year is selected
    const statsToUse = selectedYear !== "all" 
      ? calculateYearlyStatistics() 
      : averages;
    
    // If no stats available for the selected year
    if (selectedYear !== "all" && (!statsToUse || !statsToUse.caliber_averages || Object.keys(statsToUse.caliber_averages).length === 0)) {
      return (
        <div className="bg-white p-6 rounded-lg shadow text-center">
          <p className="text-gray-500 mb-4">No statistics available for {selectedYear}.</p>
          <button 
            onClick={() => setSelectedYear("all")}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            View All Years
          </button>
        </div>
      );
    }

    // Get caliber averages data based on selected year filter
    const statsToDisplay = selectedYear !== "all" 
      ? calculateYearlyStatistics() 
      : averages;
    
    const caliberAverages = statsToDisplay && statsToDisplay.caliber_averages ? statsToDisplay.caliber_averages : {};
    const calibers = Object.keys(caliberAverages);
    
    // Reset selected caliber tab if it's no longer available
    if (selectedCaliberTab && !calibers.includes(selectedCaliberTab) && calibers.length > 0) {
      setSelectedCaliberTab(calibers[0]);
    }

    return (
      <div className="bg-white p-6 rounded-lg shadow">
        {/* Caliber tabs */}
        {calibers.length > 0 && (
          <>
            <div className="mb-4">
              <h3 className="text-lg font-semibold mb-3">
                Performance by Caliber
                {selectedYear !== "all" && (
                  <span className="ml-2 text-sm font-normal text-gray-600">
                    ({selectedYear} only)
                  </span>
                )}
              </h3>
              <div className="flex flex-wrap border-b">
                {calibers.map((caliber) => (
                  <button
                    key={caliber}
                    onClick={() => setSelectedCaliberTab(caliber)}
                    className={`px-4 py-2 font-medium ${
                      selectedCaliberTab === caliber
                        ? "border-b-2 border-blue-600 text-blue-600"
                        : "text-gray-500 hover:text-gray-700"
                    }`}
                  >
                    {formatCaliber(caliber)}
                  </button>
                ))}
              </div>
            </div>

            {/* Selected caliber stats */}
            {selectedCaliberTab && caliberAverages[selectedCaliberTab] && (
              <div className="mt-6">
                <h4 className="font-medium text-gray-700 mb-3">
                  {formatCaliber(selectedCaliberTab)} Performance ({caliberAverages[selectedCaliberTab].matches_count} matches, {caliberAverages[selectedCaliberTab].valid_matches_count} valid)
                </h4>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                  <div className="border p-4 rounded">
                    <div className="mb-2 font-medium">Overall Averages</div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <div className="text-sm text-gray-600">Avg. Score</div>
                        <div className="font-semibold">{caliberAverages[selectedCaliberTab].total_score_avg}</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-600">Avg. X Count</div>
                        <div className="font-semibold">{caliberAverages[selectedCaliberTab].total_x_count_avg}</div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="border p-4 rounded">
                    <div className="mb-2 font-medium">National Match Course (NMC)</div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <div className="text-sm text-gray-600">Avg. Score</div>
                        <div className="font-semibold">{caliberAverages[selectedCaliberTab].nmc_score_avg}</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-600">Avg. X Count</div>
                        <div className="font-semibold">{caliberAverages[selectedCaliberTab].nmc_x_count_avg}</div>
                      </div>
                    </div>
                  </div>
                </div>
                
                <h4 className="font-medium text-gray-700 mb-3">Stage Averages</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="border p-4 rounded">
                    <div className="mb-2 font-medium">Slow Fire (SF)</div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <div className="text-sm text-gray-600">Avg. Score</div>
                        <div className="font-semibold">{caliberAverages[selectedCaliberTab].sf_score_avg}</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-600">Avg. X Count</div>
                        <div className="font-semibold">{caliberAverages[selectedCaliberTab].sf_x_count_avg}</div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="border p-4 rounded">
                    <div className="mb-2 font-medium">Timed Fire (TF)</div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <div className="text-sm text-gray-600">Avg. Score</div>
                        <div className="font-semibold">{caliberAverages[selectedCaliberTab].tf_score_avg}</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-600">Avg. X Count</div>
                        <div className="font-semibold">{caliberAverages[selectedCaliberTab].tf_x_count_avg}</div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="border p-4 rounded">
                    <div className="mb-2 font-medium">Rapid Fire (RF)</div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <div className="text-sm text-gray-600">Avg. Score</div>
                        <div className="font-semibold">{caliberAverages[selectedCaliberTab].rf_score_avg}</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-600">Avg. X Count</div>
                        <div className="font-semibold">{caliberAverages[selectedCaliberTab].rf_x_count_avg}</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        
        {calibers.length === 0 && (
          <p className="text-gray-500 text-center">Not enough match data to generate statistics.</p>
        )}
      </div>
    );
  };

  return (
    <div className="container mx-auto p-4">
      <div className="mb-6 flex flex-col md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2">{shooter.name}</h1>
          <div className="text-gray-600">
            {shooter.nra_number && (
              <p><span className="font-medium">NRA Number:</span> {shooter.nra_number}</p>
            )}
            {shooter.cmp_number && (
              <p><span className="font-medium">CMP Number:</span> {shooter.cmp_number}</p>
            )}
          </div>
        </div>
        
        <div className="mt-4 md:mt-0">
          <Link to="/shooters" className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600">
            Back to Shooters
          </Link>
        </div>
      </div>
      
      <div className="mb-8">
        {/* Tabs */}
        <div className="mb-6 border-b">
          <div className="flex flex-wrap justify-between items-center">
            <div className="flex">
              <button 
                onClick={() => setActiveTab("overview")}
                className={`px-4 py-2 font-medium text-sm ${
                  activeTab === "overview" 
                    ? "border-b-2 border-blue-600 text-blue-600" 
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                Overview
              </button>
              <button 
                onClick={() => setActiveTab("match-history")}
                className={`px-4 py-2 font-medium text-sm ${
                  activeTab === "match-history" 
                    ? "border-b-2 border-blue-600 text-blue-600" 
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                Match History
              </button>
              <button 
                onClick={() => setActiveTab("statistics")}
                className={`px-4 py-2 font-medium text-sm ${
                  activeTab === "statistics" 
                    ? "border-b-2 border-blue-600 text-blue-600" 
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                Statistics
              </button>
            </div>
            
            {/* Year Filter - Show only for Match History and Statistics tabs */}
            {(activeTab === "match-history" || activeTab === "statistics") && availableYears.length > 0 && (
              <div className="flex items-center mt-2 sm:mt-0">
                <label htmlFor="year-filter" className="mr-2 text-sm text-gray-700">
                  Year:
                </label>
                <select
                  id="year-filter"
                  value={selectedYear}
                  onChange={(e) => setSelectedYear(e.target.value)}
                  className="px-3 py-1 border rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">All Years</option>
                  {availableYears.map(year => (
                    <option key={year} value={year.toString()}>
                      {year}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </div>
        
        {/* Tab Content */}
        {activeTab === "overview" && renderOverview()}
        {activeTab === "match-history" && renderMatchHistory()}
        {activeTab === "statistics" && renderStatistics()}
      </div>
    </div>
  );
};

export default ShooterDetail;