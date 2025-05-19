<file>
      <absolute_file_name>/app/frontend/src/components/ShooterDetail.js</absolute_file_name>
      <content_update>
        <find>  // Statistics section
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
    
    // If year filter is applied, we need to recalculate averages based on matches from selected year only
    if (selectedYear !== "all" && report.matches) {
      // This would ideally be handled by the backend with a query parameter
      // For now, we'll show a message about viewing statistics for all years
      if (selectedYear !== "all") {
        return (
          <div className="bg-white p-6 rounded-lg shadow">
            <p className="text-gray-700 mb-4">
              Statistics are currently available for all years combined. Year-specific statistics filtering 
              will be available in a future update.
            </p>
            <p className="text-gray-500 text-sm">
              Currently showing data from all {availableYears.length} year{availableYears.length !== 1 ? 's' : ''}.
            </p>
          </div>
        );
      }
    }</find>
        <replace>  // Statistics section
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
          caliberStats[caliber].total_score_sum += score.total_score;
          caliberStats[caliber].total_x_count_sum += score.total_x_count;
          caliberStats[caliber].scores.push(score);
          
          // Process stages
          score.stages.forEach(stage => {
            if (stage.name.includes("SF")) {
              caliberStats[caliber].sf_score_sum += stage.score;
              caliberStats[caliber].sf_x_count_sum += stage.x_count;
            } else if (stage.name.includes("TF")) {
              caliberStats[caliber].tf_score_sum += stage.score;
              caliberStats[caliber].tf_x_count_sum += stage.x_count;
            } else if (stage.name.includes("RF")) {
              caliberStats[caliber].rf_score_sum += stage.score;
              caliberStats[caliber].rf_x_count_sum += stage.x_count;
            }
          });
          
          // Add to NMC stats if it's an NMC match
          if (match_type.type === "NMC" || score.match_type_instance.includes("NMC")) {
            caliberStats[caliber].nmc_score_sum += score.total_score;
            caliberStats[caliber].nmc_x_count_sum += score.total_x_count;
          }
        });
      });
      
      // Calculate averages
      Object.keys(caliberStats).forEach(caliber => {
        const stats = caliberStats[caliber];
        const count = stats.matches_count;
        
        if (count > 0) {
          caliberStats[caliber] = {
            ...stats,
            sf_score_avg: Math.round((stats.sf_score_sum / count) * 100) / 100,
            sf_x_count_avg: Math.round((stats.sf_x_count_sum / count) * 100) / 100,
            tf_score_avg: Math.round((stats.tf_score_sum / count) * 100) / 100,
            tf_x_count_avg: Math.round((stats.tf_x_count_sum / count) * 100) / 100,
            rf_score_avg: Math.round((stats.rf_score_sum / count) * 100) / 100,
            rf_x_count_avg: Math.round((stats.rf_x_count_sum / count) * 100) / 100,
            nmc_score_avg: Math.round((stats.nmc_score_sum / count) * 100) / 100,
            nmc_x_count_avg: Math.round((stats.nmc_x_count_sum / count) * 100) / 100,
            total_score_avg: Math.round((stats.total_score_sum / count) * 100) / 100,
            total_x_count_avg: Math.round((stats.total_x_count_sum / count) * 100) / 100
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
    }</replace>
      </content_update>
    </file>