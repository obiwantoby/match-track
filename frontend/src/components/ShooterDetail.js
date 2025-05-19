<file>
      <absolute_file_name>/app/frontend/src/components/ShooterDetail.js</absolute_file_name>
      <content_update>
        <find>  useEffect(() => {
    const fetchShooterData = async () => {
      try {
        // Fetch shooter details
        const shooterResponse = await axios.get(`${API}/shooters/${shooterId}`);
        setShooter(shooterResponse.data);
        
        // Fetch shooter report
        const reportResponse = await axios.get(`${API}/shooter-report/${shooterId}`);
        setReport(reportResponse.data);
        
        // Fetch shooter averages for the caliber tabs
        const averagesResponse = await axios.get(`${API}/shooter-averages/${shooterId}`);
        setAverages(averagesResponse.data);
        
        // Set default caliber tab if available
        if (averagesResponse.data && averagesResponse.data.caliber_averages) {
          const calibers = Object.keys(averagesResponse.data.caliber_averages);
          if (calibers.length > 0) {
            setSelectedCaliberTab(calibers[0]);
          }
        }
        
        setLoading(false);
      } catch (err) {
        console.error("Error fetching shooter details:", err);
        setError("Failed to load shooter details. Please try again.");
        setLoading(false);
      }
    };

    fetchShooterData();
  }, [shooterId]);</find>
        <replace>  useEffect(() => {
    const fetchShooterData = async () => {
      try {
        // Fetch shooter details
        const shooterResponse = await axios.get(`${API}/shooters/${shooterId}`);
        setShooter(shooterResponse.data);
        
        // Fetch shooter report
        const reportResponse = await axios.get(`${API}/shooter-report/${shooterId}`);
        setReport(reportResponse.data);
        
        // Extract unique years from match dates
        if (reportResponse.data && reportResponse.data.matches) {
          const years = [...new Set(Object.values(reportResponse.data.matches).map(match => 
            new Date(match.match.date).getFullYear()
          ))].sort((a, b) => b - a); // Sort years in descending order
          
          setAvailableYears(years);
          
          // Set selected year to the most recent year if available
          if (years.length > 0) {
            setSelectedYear(years[0].toString());
          }
        }
        
        // Fetch shooter averages for the caliber tabs
        const averagesResponse = await axios.get(`${API}/shooter-averages/${shooterId}`);
        setAverages(averagesResponse.data);
        
        // Set default caliber tab if available
        if (averagesResponse.data && averagesResponse.data.caliber_averages) {
          const calibers = Object.keys(averagesResponse.data.caliber_averages);
          if (calibers.length > 0) {
            setSelectedCaliberTab(calibers[0]);
          }
        }
        
        setLoading(false);
      } catch (err) {
        console.error("Error fetching shooter details:", err);
        setError("Failed to load shooter details. Please try again.");
        setLoading(false);
      }
    };

    fetchShooterData();
  }, [shooterId]);</replace>
      </content_update>
    </file>