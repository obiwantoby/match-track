<file>
      <absolute_file_name>/app/frontend/src/components/MatchReport.js</absolute_file_name>
      <content_update>
        <find>                                <td className="px-4 py-2 text-center">
                                  <button 
                                    onClick={() => {
                                      const detailElement = document.getElementById(`scorecard-${shooterId}-${key}`);
                                      if (detailElement) {
                                        detailElement.open = !detailElement.open;
                                      }
                                    }} 
                                    className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                                  >
                                    View Scorecard
                                  </button>
                                </td></find>
        <replace>                                <td className="px-4 py-2 text-center">
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
                                </td></replace>
      </content_update>
    </file>