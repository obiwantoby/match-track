import { useState, useEffect } from "react";
import axios from "axios";
import { useParams, Link } from "react-router-dom";
import { useAuth } from "../App";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const MatchReport = () => {
  const { matchId } = useParams();
  const [match, setMatch] = useState(null);
  const [report, setReport] = useState(null);
  const [selectedView, setSelectedView] = useState("summary"); // summary, details, aggregates
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { isAdmin } = useAuth();

  useEffect(() => {
    const fetchMatchData = async () => {
      try {
        // Fetch match details
        const matchResponse = await axios.get(`${API}/matches/${matchId}`);
        setMatch(matchResponse.data);
        
        // Fetch match report
        const reportResponse = await axios.get(`${API}/match-report/${matchId}`);
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

  // Helper to get readable caliber name
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

  return (
    <div className="container mx-auto p-4">
      <div className="mb-6 flex flex-col md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2">{match.name}</h1>
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
        
        <div className="mt-4 md:mt-0 flex flex-col md:flex-row gap-3">
          {isAdmin() && (
            <Link to={`/scores/add/${matchId}`} className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-center">
              Add Scores
            </Link>
          )}
          <Link to="/matches" className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600 text-center">
            Back to Matches
          </Link>
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
      
      {/* Match Configuration */}
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
          
          {/* Winners Section */}
          {Object.keys(winners).length > 0 && (
            <div className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">Category Winners</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                {Object.entries(winners).map(([category, winner]) => {
                  const [matchType, caliber] = category.split('_');
                  return (
                    <div key={category} className="bg-white p-6 rounded-lg shadow hover:shadow-md transition-shadow">
                      <div className="flex justify-between items-start mb-3">
                        <div>
                          <h3 className="text-lg font-semibold">{matchType}</h3>
                          <p className="text-sm text-gray-600">{formatCaliber(caliber)}</p>
                        </div>
                        <div className="bg-yellow-100 text-yellow-800 text-xs font-medium px-2.5 py-0.5 rounded">
                          Winner
                        </div>
                      </div>
                      <div className="mt-3">
                        <Link to={`/shooters/${winner.shooterId}`} className="text-lg font-bold text-blue-600 hover:underline">
                          {winner.shooterName}
                        </Link>
                        <div className="flex justify-between mt-2">
                          <div>
                            <span className="text-gray-600 text-sm">Score:</span>
                            <span className="ml-1 font-semibold">{winner.score}</span>
                          </div>
                          <div>
                            <span className="text-gray-600 text-sm">X Count:</span>
                            <span className="ml-1 font-semibold">{winner.xCount}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
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
                                  {matchTypeInstance ? matchTypeInstance.type : instance}
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
                                    {isAdmin() && (
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
                                      <td className="px-4 py-2 text-center">{stage.score}</td>
                                      <td className="px-4 py-2 text-center">{stage.x_count}</td>
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
              {isAdmin() && (
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
