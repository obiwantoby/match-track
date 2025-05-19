<file>
      <absolute_file_name>/app/frontend/src/components/ShooterDetail.js</absolute_file_name>
      <content_update>
        <find>    // Get caliber averages data
    const caliberAverages = averages && averages.caliber_averages ? averages.caliber_averages : {};
    const calibers = Object.keys(caliberAverages);</find>
        <replace>    // Get caliber averages data based on selected year filter
    const statsToDisplay = selectedYear !== "all" 
      ? calculateYearlyStatistics() 
      : averages;
    
    const caliberAverages = statsToDisplay && statsToDisplay.caliber_averages ? statsToDisplay.caliber_averages : {};
    const calibers = Object.keys(caliberAverages);
    
    // Reset selected caliber tab if it's no longer available
    if (selectedCaliberTab && !calibers.includes(selectedCaliberTab) && calibers.length > 0) {
      setSelectedCaliberTab(calibers[0]);
    }</replace>
      </content_update>
    </file>