<file>
      <absolute_file_name>/app/frontend/src/components/ShooterDetail.js</absolute_file_name>
      <content_update>
        <find>  // Match History section
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

    return (
      <div className="space-y-6">
        {Object.entries(report.matches).map(([matchId, matchData]) => {</find>
        <replace>  // Match History section
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
        {Object.entries(filteredMatches).map(([matchId, matchData]) => {</replace>
      </content_update>
    </file>