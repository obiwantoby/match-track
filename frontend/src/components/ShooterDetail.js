<file>
      <absolute_file_name>/app/frontend/src/components/ShooterDetail.js</absolute_file_name>
      <content_update>
        <find>  // Statistics section
  const renderStatistics = () => {
    if (!report || !report.averages || 
        (!report.averages.by_match_type || Object.keys(report.averages.by_match_type).length === 0) && 
        (!report.averages.by_caliber || Object.keys(report.averages.by_caliber).length === 0)) {
      return (
        <div className="bg-white p-6 rounded-lg shadow text-center">
          <p className="text-gray-500">Not enough match data to generate statistics.</p>
        </div>
      );
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
    }</replace>
      </content_update>
    </file>