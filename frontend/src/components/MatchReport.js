import { useState, useEffect } from "react";
import axios from "axios";
import { useParams, Link } from "react-router-dom";
import { useAuth } from "../App";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
// Check if BACKEND_URL already contains /api to avoid duplication
const API = BACKEND_URL.endsWith('/api') ? BACKEND_URL : `${BACKEND_URL}/api`;

const MatchReport = () => {
  const { matchId } = useParams();
  const [match, setMatch] = useState(null);
  const [report, setReport] = useState(null);
  const [selectedView, setSelectedView] = useState("summary"); // summary, details, aggregates
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { isAdmin } = useAuth();
  const [matchYear, setMatchYear] = useState(null);

  useEffect(() => {
    const fetchMatchData = async () => {
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
        
        // Set match year
        const matchDate = new Date(matchResponse.data.date);
        setMatchYear(matchDate.getFullYear());
        
        // Fetch match report
        const reportResponse = await axios.get(`${API}/match-report/${matchId}`, config);
        setReport(reportResponse.data);
        
        // Calculate aggregates if they're missing
        if (reportResponse.data && reportResponse.data.shooters) {
          Object.entries(reportResponse.data.shooters).forEach(([shooterId, shooterData]) => {
            // Check if this shooter has aggregates
            if (!shooterData.aggregates || Object.keys(shooterData.aggregates).length === 0) {
              // For 1800 (3x600) aggregate
              if (matchResponse.data.aggregate_type === "1800 (3x600)") {
                // Group scores by caliber
                const scoresByCaliberType = {};
                
                Object.entries(shooterData.scores).forEach(([key, scoreData]) => {
                  const caliber = scoreData.score.caliber;
                  if (!scoresByCaliberType[caliber]) {
                    scoresByCaliberType[caliber] = [];
                  }
                  scoresByCaliberType[caliber].push(scoreData.score);
                });
                
                // Calculate aggregate for each caliber with at least 3 scores
                const aggregates = {};
                Object.entries(scoresByCaliberType).forEach(([caliber, scores]) => {
                  if (scores.length >= 3) {
                    // Only include non-null scores in the totals
                    const totalScore = scores.reduce((sum, score) => 
                      score.total_score !== null ? sum + score.total_score : sum, 0);
                    const totalXCount = scores.reduce((sum, score) => 
                      score.total_x_count !== null ? sum + score.total_x_count : sum, 0);
                    
                    const caliberId = caliber === ".22" ? "TWENTYTWO" : 
                                     caliber === "CF" ? "CENTERFIRE" : 
                                     caliber === ".45" ? "FORTYFIVE" : caliber;
                    
                    aggregates[`1800_${caliberId}`] = {
                      score: totalScore,
                      x_count: totalXCount,
                      components: scores.map(s => s.match_type_instance)
                    };
                  }
                });
                
                if (Object.keys(aggregates).length > 0) {
                  shooterData.aggregates = aggregates;
                }
              }
            }
          });
        }
        
        setReport(reportResponse.data);
        
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

  const shooterCount = report && report.shooters ? Object.keys(report.shooters).length : 0;
  const scoreCount = report && report.shooters ? 
    Object.values(report.shooters).reduce((total, shooter) => 
      total + Object.keys(shooter.scores).length, 0) : 0;
  
  // Get unique calibers used in this match
  const calibers = new Set();
  if (report && report.shooters) {
    Object.values(report.shooters).forEach(shooter => {
      Object.values(shooter.scores).forEach(score => {
        calibers.add(score.score.caliber);
      });
    });
  }

  // Helper to determine the winner for each match type and caliber
  const getWinners = () => {
    if (!report || !report.shooters) return {};
    
    const winners = {};
    
    // Group scores by match type and caliber
    const matchTypeCaliberScores = {};
    
    Object.entries(report.shooters).forEach(([shooterId, shooterData]) => {
      Object.entries(shooterData.scores).forEach(([key, scoreData]) => {
        const [instance, caliber] = key.split('_');
        
        if (!matchTypeCaliberScores[instance]) {
          matchTypeCaliberScores[instance] = {};
        }
        
        if (!matchTypeCaliberScores[instance][caliber]) {
          matchTypeCaliberScores[instance][caliber] = [];
        }
        
        matchTypeCaliberScores[instance][caliber].push({
          shooterId,
          shooterName: shooterData.shooter.name,
          score: scoreData.score.total_score,
          xCount: scoreData.score.total_x_count
        });
      });
    });
    
    // Find winner for each category
    Object.entries(matchTypeCaliberScores).forEach(([instance, caliberData]) => {
      Object.entries(caliberData).forEach(([caliber, scores]) => {
        // Sort by score (highest first), then by X count (highest first)
        scores.sort((a, b) => {
          if (b.score !== a.score) return b.score - a.score;
          return b.xCount - a.xCount;
        });
        
        if (scores.length > 0) {
          const key = `${instance}_${caliber}`;
          winners[key] = scores[0];
        }
      });
    });
    
    return winners;
  };

  const winners = getWinners();

  // Helper function to format caliber for display
  const formatCaliber = (caliber) => {
    if (caliber === "TWENTYTWO" || caliber === "TWENTYTWO") return ".22";
    if (caliber === "CENTERFIRE" || caliber === "CF") return "CF";
    if (caliber === "FORTYFIVE" || caliber === ".45") return ".45";
    return caliber;
  };

  return (
    <div className="container mx-auto p-4">
      <div className="mb-6 flex flex-col md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center mb-2">
            <h1 className="text-3xl font-bold">{match.name}</h1>
            {matchYear && (
              <span className="ml-3 text-sm bg-gray-200 text-gray-800 px-2 py-1 rounded">
                {matchYear}
              </span>
            )}
          </div>
          <div className="text-gray-600 space-y-1">
            <p><span className="font-medium">Date:</span> {new Date(match.date).toLocaleDateString()}</p>
            <p><span className="font-medium">Location:</span> {match.location}</p>
            {match.aggregate_type !== "None" && (
              <p>
                <span className="font-medium">Aggregate Type:</span>
                <span className="ml-2 inline-block bg-blue-100 text-blue-800 text-xs font-semibold px-2.5 py-0.5 rounded">
                  {match.aggregate_type}
                </span>
              </p>
            )}
          </div>
        </div>
        
        <div className="mt-4 md:mt-0 flex flex-col space-y-2">
          <Link to={`/matches`} className="bg-gray-200 hover:bg-gray-300 text-gray-800 py-2 px-4 rounded flex items-center justify-center">
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path>
            </svg>
            Back to Matches
          </Link>
          
          {/* Excel Download Button */}
          <button 
            onClick={async () => {
              try {
                const token = localStorage.getItem('token');
                if (!token) {
                  alert("Authentication required. Please log in again.");
                  return;
                }
                
                // Create headers with authentication
                const headers = {
                  Authorization: `Bearer ${token}`
                };
                
                // Perform authenticated request with proper response handling
                const response = await axios.get(`${API}/match-report/${matchId}/excel`, {
                  headers,
                  responseType: 'blob' // Important for binary data like Excel files
                });
                
                // Create a download link
                const url = window.URL.createObjectURL(new Blob([response.data]));
                const link = document.createElement('a');
                link.href = url;
                link.setAttribute('download', `match_report_${match.name.replace(/\s+/g, '_')}_${new Date(match.date).toISOString().split('T')[0]}.xlsx`);
                document.body.appendChild(link);
                link.click();
                
                // Clean up
                window.URL.revokeObjectURL(url);
                document.body.removeChild(link);
              } catch (err) {
                console.error("Error downloading Excel report:", err);
                alert("Failed to download Excel report. Please try again.");
              }
            }}
            className="bg-green-600 hover:bg-green-700 text-white py-2 px-4 rounded flex items-center justify-center"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
            </svg>
            Download Excel Report
          </button>
          
          {/* Edit Match Button for Admins */}
          {isAdmin && (
            <Link 
              to={`/matches/${matchId}/edit`} 
              className="bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded flex items-center justify-center"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
              </svg>
              Edit Match
            </Link>
          )}
        </div>
      </div>
      
      {/* Match Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-2">Participants</h3>
          <p className="text-3xl font-bold">{shooterCount}</p>
          <p className="text-gray-500 text-sm mt-1">shooters participated</p>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-2">Scores</h3>
          <p className="text-3xl font-bold">{scoreCount}</p>
          <p className="text-gray-500 text-sm mt-1">total scores recorded</p>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-2">Calibers</h3>
          <div className="flex flex-wrap gap-2 mt-2">
            {Array.from(calibers).map((caliber, idx) => (
              <span key={idx} className="inline-block bg-gray-100 text-gray-800 text-xs px-2 py-1 rounded">
                {formatCaliber(caliber)}
              </span>
            ))}
            {calibers.size === 0 && <p className="text-gray-500">No calibers recorded</p>}
          </div>
        </div>
      </div>
      
      {/* View Selector */}
      <div className="mb-6 border-b">
        <div className="flex flex-wrap">
          <button 
            onClick={() => setSelectedView("summary")}
            className={`px-4 py-2 font-medium text-sm ${
              selectedView === "summary" 
                ? "border-b-2 border-blue-600 text-blue-600" 
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            Summary
          </button>
          <button 
            onClick={() => setSelectedView("details")}
            className={`px-4 py-2 font-medium text-sm ${
              selectedView === "details" 
                ? "border-b-2 border-blue-600 text-blue-600" 
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            Detailed Scores
          </button>
          {match.aggregate_type !== "None" && (
            <button 
              onClick={() => setSelectedView("aggregates")}
              className={`px-4 py-2 font-medium text-sm ${
                selectedView === "aggregates" 
                  ? "border-b-2 border-blue-600 text-blue-600" 
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              Aggregates
            </button>
          )}
        </div>
      </div>
      
      {selectedView === "summary" && (
        <>
          <div className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Match Configuration</h2>
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Instance</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Calibers</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Max Score</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {match.match_types.map((mt, index) => (
                    <tr key={index}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{mt.instance_name}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">{mt.type}</div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex flex-wrap gap-1">
                          {mt.calibers.map((caliber, idx) => (
                            <span key={idx} className="inline-block bg-gray-100 text-gray-800 text-xs px-2 py-0.5 rounded">
                              {formatCaliber(caliber)}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        {mt.type === "NMC" ? "300" : 
                        mt.type === "600" ? "600" : 
                        mt.type === "900" ? "900" : 
                        mt.type === "Presidents" ? "400" : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          
          {/* Match Summary Table */}
          {report && report.shooters && Object.keys(report.shooters).length > 0 && (
            <div className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">Match Summary</h2>
              <div className="bg-white rounded-lg shadow overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Shooter Name</th>
                      {match.match_types.map((mt) => (
                        mt.calibers.map((caliber) => (
                          <th key={`${mt.instance_name}_${caliber}`} className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                            {mt.instance_name} ({formatCaliber(caliber)})
                          </th>
                        ))
                      ))}
                      {match.aggregate_type !== "None" && (
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                          {match.aggregate_type}
                        </th>
                      )}
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {Object.entries(report.shooters).map(([shooterId, shooterData]) => {
                      // For aggregates
                      const aggregates = shooterData.aggregates || {};
                      
                      return (
                        <tr key={shooterId}>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <Link to={`/shooters/${shooterId}`} className="text-sm font-medium text-blue-600 hover:underline">
                              {shooterData.shooter.name}
                            </Link>
                          </td>
                          
                          {/* Generate cells for each match type and caliber */}
                          {match.match_types.map((mt) => (
                            mt.calibers.map((caliber) => {
                              // We need to try multiple key formats because the data structure varies
                              const possibleKeys = [
                                // Simple format: instance_caliber
                                `${mt.instance_name}_${caliber}`,
                                
                                // Enum format: instance_CaliberType.ENUM
                                `${mt.instance_name}_CaliberType.${caliber.replace(/[.]/g, '').toUpperCase()}`,
                                
                                // Special cases for specific calibers
                                caliber === '.22' && `${mt.instance_name}_CaliberType.TWENTYTWO`,
                                caliber === 'CF' && `${mt.instance_name}_CaliberType.CENTERFIRE`,
                                caliber === '.45' && `${mt.instance_name}_CaliberType.FORTYFIVE`,
                                caliber === 'Service Pistol' && `${mt.instance_name}_CaliberType.SERVICEPISTOL`,
                                caliber === 'Service Revolver' && `${mt.instance_name}_CaliberType.SERVICEREVOLVER`,
                                caliber === 'DR' && `${mt.instance_name}_CaliberType.DR`,
                                
                                // Legacy formats
                                caliber === 'Service Pistol' && `${mt.instance_name}_9mm Service`,
                                caliber === 'Service Pistol' && `${mt.instance_name}_45 Service`,
                                caliber === 'Service Pistol' && `${mt.instance_name}_CaliberType.NINESERVICE`,
                                caliber === 'Service Pistol' && `${mt.instance_name}_CaliberType.FORTYFIVESERVICE`
                              ].filter(Boolean); // Remove falsy values
                              
                              // Try all possible keys
                              let scoreData = null;
                              for (const key of possibleKeys) {
                                if (shooterData.scores[key]) {
                                  scoreData = shooterData.scores[key];
                                  break;
                                }
                              }
                              
                              // Try one more option: see if any key contains both the instance name and caliber
                              if (!scoreData) {
                                const relevantKeys = Object.keys(shooterData.scores).filter(key => 
                                  key.includes(mt.instance_name) && (
                                    // Direct caliber match
                                    key.includes(caliber) || 
                                    
                                    // Special caliber matches
                                    (caliber === '.22' && (
                                      key.includes('TWENTYTWO') || 
                                      key.includes('.22')
                                    )) ||
                                    (caliber === 'CF' && (
                                      key.includes('CENTERFIRE') || 
                                      key.includes('CF')
                                    )) ||
                                    (caliber === '.45' && (
                                      key.includes('FORTYFIVE') || 
                                      key.includes('.45')
                                    )) ||
                                    (caliber === 'Service Pistol' && (
                                      key.includes('SERVICEPISTOL') || 
                                      key.includes('Service Pistol') || 
                                      key.includes('9mm Service') || 
                                      key.includes('45 Service') ||
                                      key.includes('NINESERVICE') ||
                                      key.includes('FORTYFIVESERVICE')
                                    )) ||
                                    (caliber === 'Service Revolver' && (
                                      key.includes('SERVICEREVOLVER') || 
                                      key.includes('Service Revolver')
                                    )) ||
                                    (caliber === 'DR' && (
                                      key.includes('DR')
                                    ))
                                  )
                                );
                                
                                if (relevantKeys.length > 0) {
                                  scoreData = shooterData.scores[relevantKeys[0]];
                                }
                              }
                              
                              // Generate a unique key for React
                              const cellKey = `${mt.instance_name}_${caliber}`;
                              
                              return (
                                <td key={cellKey} className="px-4 py-3 text-center">
                                  {scoreData ? (
                                    <div>
                                      <span className="font-medium">{scoreData.score.total_score}</span>
                                      <span className="text-gray-500 text-xs ml-1">({scoreData.score.total_x_count}X)</span>
                                    </div>
                                  ) : (
                                    <span className="text-gray-400">-</span>
                                  )}
                                </td>
                              );
                            })
                          ))}
                          
                          {/* Aggregate Score */}
                          {match.aggregate_type !== "None" && (
                            <td className="px-4 py-3 text-center">
                              {(() => {
                                // For 1800 (3x600) or 1800 (2x900) match, we want to show the sum of all calibers
                                if (match.aggregate_type === "1800 (3x600)" || match.aggregate_type === "1800 (2x900)") {
                                  // Calculate grand total across all calibers
                                  let totalScore = 0;
                                  let totalXCount = 0;
                                  let hasScores = false;
                                  
                                  // Go through all scores and sum them up
                                  Object.entries(shooterData.scores).forEach(([key, scoreData]) => {
                                    // Only include non-null scores
                                    if (scoreData.score.total_score !== null) {
                                      totalScore += scoreData.score.total_score;
                                      totalXCount += scoreData.score.total_x_count;
                                      hasScores = true;
                                    }
                                  });
                                  
                                  if (hasScores) {
                                    return (
                                      <div className="font-medium">
                                        {totalScore}<span className="text-gray-500 text-xs ml-1">({totalXCount}X)</span>
                                      </div>
                                    );
                                  }
                                }
                                
                                // For other aggregate types, show individual aggregates
                                let aggregateScores = [];
                                
                                // If server-provided aggregates exist, use them
                                if (shooterData.aggregates && Object.keys(shooterData.aggregates).length > 0) {
                                  Object.entries(shooterData.aggregates).forEach(([aggKey, aggData]) => {
                                    aggregateScores.push(
                                      <div key={aggKey} className="font-medium">
                                        {aggData.score}<span className="text-gray-500 text-xs ml-1">({aggData.x_count}X)</span>
                                        <div className="text-gray-400 text-xs">{formatCaliber(aggKey.split('_')[1])}</div>
                                      </div>
                                    );
                                  });
                                }
                                
                                return aggregateScores.length > 0 ? 
                                  aggregateScores : 
                                  <span className="text-gray-400">-</span>;
                              })()}
                            </td>
                          )}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          
          {/* Winners Section */}
          {Object.keys(winners).length > 0 && (
            <div className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">Category Winners</h2>
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Shooter</th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Score</th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">X Count</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {Object.entries(winners).map(([category, winner]) => {
                      const [matchType, caliber] = category.split('_');
                      return (
                        <tr key={category}>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm font-medium text-gray-900">{matchType}</div>
                            <div className="text-xs text-gray-500">{formatCaliber(caliber)}</div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <Link to={`/shooters/${winner.shooterId}`} className="text-sm font-medium text-blue-600 hover:underline">
                              {winner.shooterName}
                            </Link>
                          </td>
                          <td className="px-6 py-4 text-center font-medium">
                            {winner.score}
                          </td>
                          <td className="px-6 py-4 text-center">
                            {winner.xCount}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
      
      {/* Detailed Scores */}
      {selectedView === "details" && (
        <div>
          <h2 className="text-2xl font-semibold mb-4">Match Results</h2>
          {report && report.shooters && Object.keys(report.shooters).length > 0 ? (
            <div className="space-y-8">
              {Object.entries(report.shooters).map(([shooterId, shooterData]) => (
                <div key={shooterId} className="bg-white rounded-lg shadow overflow-hidden">
                  <div className="px-6 py-4 bg-gray-50 border-b">
                    <h3 className="text-lg font-semibold">
                      <Link to={`/shooters/${shooterId}`} className="text-blue-600 hover:underline">
                        {shooterData.shooter.name}
                      </Link>
                      {shooterData.shooter.nra_number && (
                        <span className="ml-2 text-sm text-gray-500">
                          NRA: {shooterData.shooter.nra_number}
                        </span>
                      )}
                    </h3>
                  </div>
                  
                  <div className="px-6 py-4">
                    {/* Scorecard Table View */}
                    <div className="overflow-x-auto mb-4">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Instance Name</th>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Match Type</th>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Caliber</th>
                            <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase">Total Score</th>
                            <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase">X Count</th>
                            <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase">Actions</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                          {Object.entries(shooterData.scores).map(([key, scoreData]) => {
                            const [instance, caliber] = key.split('_');
                            const isWinner = winners[key] && winners[key].shooterId === shooterId;
                            
                            // Get match type to check if it's a 900 aggregate
                            const matchTypeInstance = match.match_types.find(mt => mt.instance_name === instance);
                            const is900 = matchTypeInstance && matchTypeInstance.type === "900";
                            
                            return (
                              <tr key={key} className={isWinner ? "bg-yellow-50" : ""}>
                                <td className="px-4 py-2 whitespace-nowrap">
                                  {instance}
                                </td>
                                <td className="px-4 py-2 whitespace-nowrap">
                                  {matchTypeInstance ? matchTypeInstance.type : "-"}
                                  {isWinner && (
                                    <span className="ml-2 inline-block bg-yellow-100 text-yellow-800 text-xs font-medium px-2 py-0.5 rounded">
                                      Winner
                                    </span>
                                  )}
                                </td>
                                <td className="px-4 py-2 whitespace-nowrap">
                                  {formatCaliber(caliber)}
                                </td>
                                <td className="px-4 py-2 text-center font-medium">
                                  {scoreData.score.total_score}
                                </td>
                                <td className="px-4 py-2 text-center">
                                  {scoreData.score.total_x_count}
                                </td>
                                <td className="px-4 py-2 text-center">
                                  <div className="flex justify-center space-x-3">
                                    <button 
                                      onClick={() => {
                                        const detailElement = document.getElementById(`scorecard-${shooterId}-${key}`);
                                        if (detailElement) {
                                          detailElement.open = !detailElement.open;
                                        }
                                      }} 
                                      className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                                    >
                                      View
                                    </button>
                                    {isAdmin && isAdmin() && (
                                      <Link 
                                        to={`/scores/edit/${scoreData.score.id}`}
                                        className="text-green-600 hover:text-green-800 text-sm font-medium"
                                      >
                                        Edit
                                      </Link>
                                    )}
                                  </div>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                    
                    {/* Expandable Scorecards */}
                    <div className="mt-4 space-y-6">
                      {Object.entries(shooterData.scores).map(([key, scoreData]) => {
                        const [instance, caliber] = key.split('_');
                        const matchTypeInstance = match.match_types.find(mt => mt.instance_name === instance);
                        const matchType = matchTypeInstance ? matchTypeInstance.type : "Unknown";
                        const is900 = matchType === "900";
                        
                        return (
                          <details key={`scorecard-${key}`} id={`scorecard-${shooterId}-${key}`} className="bg-gray-50 rounded-lg p-4">
                            <summary className="font-medium cursor-pointer mb-3">
                              {matchType} - {formatCaliber(caliber)} Scorecard
                            </summary>
                            
                            <div className="mt-3 overflow-x-auto">
                              <table className="min-w-full divide-y divide-gray-200 text-sm">
                                <thead className="bg-gray-100">
                                  <tr>
                                    <th className="px-4 py-2 text-left font-medium text-gray-700">Stage</th>
                                    <th className="px-4 py-2 text-center font-medium text-gray-700">Score</th>
                                    <th className="px-4 py-2 text-center font-medium text-gray-700">X Count</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-200">
                                  {/* Stage Scores */}
                                  {scoreData.score.stages.map((stage, idx) => (
                                    <tr key={`stage-${idx}`}>
                                      <td className="px-4 py-2 font-medium">{stage.name}</td>
                                      <td className="px-4 py-2 text-center">{stage.score === null ? "-" : stage.score}</td>
                                      <td className="px-4 py-2 text-center">{stage.x_count === null ? "-" : stage.x_count}</td>
                                    </tr>
                                  ))}
                                  
                                  {/* Subtotals for 900 match type */}
                                  {is900 && (
                                    <>
                                      <tr className="bg-gray-100">
                                        <td colSpan="3" className="px-4 py-2 font-medium text-gray-700">Subtotals</td>
                                      </tr>
                                      {Object.entries(scoreData.subtotals).map(([name, values], idx) => (
                                        <tr key={`subtotal-${idx}`} className="bg-blue-50">
                                          <td className="px-4 py-2 font-medium">{name}</td>
                                          <td className="px-4 py-2 text-center font-medium">{values.score}</td>
                                          <td className="px-4 py-2 text-center">{values.x_count}</td>
                                        </tr>
                                      ))}
                                    </>
                                  )}
                                  
                                  {/* Total Score */}
                                  <tr className="bg-gray-100 font-medium">
                                    <td className="px-4 py-2">Total</td>
                                    <td className="px-4 py-2 text-center">{scoreData.score.total_score}</td>
                                    <td className="px-4 py-2 text-center">{scoreData.score.total_x_count}</td>
                                  </tr>
                                </tbody>
                              </table>
                            </div>
                          </details>
                        );
                      })}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-white p-6 rounded-lg shadow text-center">
              <p className="text-gray-500 mb-4">No scores have been recorded for this match.</p>
              {isAdmin && isAdmin() && (
                <Link to={`/scores/add/${matchId}`} className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700">
                  Add First Score
                </Link>
              )}
            </div>
          )}
        </div>
      )}
      
      {/* Aggregates View */}
      {selectedView === "aggregates" && match.aggregate_type !== "None" && (
        <div>
          <h2 className="text-2xl font-semibold mb-4">Aggregate Results</h2>
          <p className="mb-4 text-gray-600">
            Aggregate Type: {match.aggregate_type}
          </p>
          
          {report && report.shooters && Object.keys(report.shooters).length > 0 ? (
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Shooter</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Aggregate</th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Score</th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">X Count</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Components</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {Object.entries(report.shooters)
                    // Calculate aggregates if not provided by the server
                    .map(([shooterId, shooterData]) => {
                      const processedShooterData = { ...shooterData };
                      
                      // If no aggregates, calculate them
                      if (!processedShooterData.aggregates || Object.keys(processedShooterData.aggregates).length === 0) {
                        if (match.aggregate_type === "1800 (3x600)" || match.aggregate_type === "1800 (2x900)") {
                          const scoresByCaliberType = {};
                          
                          // Collect scores by caliber
                          Object.entries(processedShooterData.scores).forEach(([key, scoreData]) => {
                            const caliber = scoreData.score.caliber;
                            
                            if (!scoresByCaliberType[caliber]) {
                              scoresByCaliberType[caliber] = {
                                scores: [],
                                components: []
                              };
                            }
                            
                            scoresByCaliberType[caliber].scores.push(scoreData.score);
                            scoresByCaliberType[caliber].components.push(scoreData.score.match_type_instance);
                          });
                          
                          // Calculate aggregate for each caliber
                          const calculatedAggregates = {};
                          
                          Object.entries(scoresByCaliberType).forEach(([caliber, { scores, components }]) => {
                            if (scores.length > 0) {
                              const totalScore = scores.reduce((sum, score) => sum + score.total_score, 0);
                              const totalXCount = scores.reduce((sum, score) => sum + score.total_x_count, 0);
                              
                              const caliberId = caliber.replace(/[.]/g, '').toUpperCase();
                              
                              calculatedAggregates[`1800_${caliberId}`] = {
                                score: totalScore,
                                x_count: totalXCount,
                                components: components
                              };
                            }
                          });
                          
                          processedShooterData.aggregates = calculatedAggregates;
                        }
                      }
                      
                      return [shooterId, processedShooterData];
                    })
                    .filter(([_, shooterData]) => shooterData.aggregates && Object.keys(shooterData.aggregates).length > 0)
                    .flatMap(([shooterId, shooterData]) => 
                      Object.entries(shooterData.aggregates).map(([aggKey, aggData]) => ({
                        shooterId,
                        shooterName: shooterData.shooter.name,
                        aggregateType: aggKey.split('_')[0],
                        caliber: aggKey.split('_')[1],
                        score: aggData.score,
                        xCount: aggData.x_count,
                        components: aggData.components
                      }))
                    )
                    .sort((a, b) => {
                      // Sort by aggregate type first, then by caliber, then by score (highest first)
                      if (a.aggregateType !== b.aggregateType) return a.aggregateType.localeCompare(b.aggregateType);
                      if (a.caliber !== b.caliber) return a.caliber.localeCompare(b.caliber);
                      return b.score - a.score;
                    })
                    .map((item, idx) => (
                      <tr key={idx}>
                        <td className="px-6 py-4">
                          <Link to={`/shooters/${item.shooterId}`} className="text-blue-600 hover:underline font-medium">
                            {item.shooterName}
                          </Link>
                        </td>
                        <td className="px-6 py-4">
                          <div className="font-medium">{item.aggregateType}</div>
                          <div className="text-sm text-gray-500">{formatCaliber(item.caliber)}</div>
                        </td>
                        <td className="px-6 py-4 text-center font-medium">
                          {item.score}
                        </td>
                        <td className="px-6 py-4 text-center">
                          {item.xCount}
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex flex-wrap gap-1">
                            {item.components.map((comp, cidx) => (
                              <span key={cidx} className="inline-block bg-gray-100 text-gray-800 text-xs px-2 py-0.5 rounded">
                                {comp}
                              </span>
                            ))}
                          </div>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="bg-white p-6 rounded-lg shadow text-center">
              <p className="text-gray-500">No aggregate scores available for this match.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default MatchReport;