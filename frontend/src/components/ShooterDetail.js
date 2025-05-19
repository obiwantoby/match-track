<file>
      <absolute_file_name>/app/frontend/src/components/ShooterDetail.js</absolute_file_name>
      <content_update>
        <find>        {/* Tabs */}
        <div className="mb-6 border-b">
          <div className="flex flex-wrap">
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
        </div></find>
        <replace>        {/* Tabs */}
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
        </div></replace>
      </content_update>
    </file>