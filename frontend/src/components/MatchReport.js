<file>
      <absolute_file_name>/app/frontend/src/components/MatchReport.js</absolute_file_name>
      <content_update>
        <find>      <div className="mb-6 flex flex-col md:flex-row md:items-center md:justify-between">
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
        </div></find>
        <replace>      <div className="mb-6 flex flex-col md:flex-row md:items-center md:justify-between">
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
        </div></replace>
      </content_update>
    </file>