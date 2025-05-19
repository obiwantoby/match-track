<file>
      <absolute_file_name>/app/frontend/src/components/MatchReport.js</absolute_file_name>
      <content_update>
        <find>      {selectedView === "summary" && (
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
      )}</find>
        <replace>      {selectedView === "summary" && (
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
                              const key = `${mt.instance_name}_${caliber}`;
                              const scoreData = shooterData.scores[key];
                              
                              return (
                                <td key={key} className="px-4 py-3 text-center">
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
                              {Object.entries(aggregates).map(([aggKey, aggData], idx) => (
                                <div key={idx} className="font-medium">
                                  {aggData.score}<span className="text-gray-500 text-xs ml-1">({aggData.x_count}X)</span>
                                  <div className="text-gray-400 text-xs">{formatCaliber(aggKey.split('_')[1])}</div>
                                </div>
                              ))}
                              {Object.keys(aggregates).length === 0 && <span className="text-gray-400">-</span>}
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
      )}</replace>
      </content_update>
    </file>