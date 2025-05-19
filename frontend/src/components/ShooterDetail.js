<file>
      <absolute_file_name>/app/frontend/src/components/ShooterDetail.js</absolute_file_name>
      <content_update>
        <find>            {/* Caliber tabs */}
            {calibers.length > 0 && (
              <>
                <div className="mb-4">
                  <h3 className="text-lg font-semibold mb-3">Performance by Caliber</h3></find>
        <replace>            {/* Caliber tabs */}
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
                  </h3></replace>
      </content_update>
    </file>