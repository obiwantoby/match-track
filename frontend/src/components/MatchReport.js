<file>
      <absolute_file_name>/app/frontend/src/components/MatchReport.js</absolute_file_name>
      <content_update>
        <find>  useEffect(() => {
    const fetchMatchData = async () => {
      try {
        // Fetch match details
        const matchResponse = await axios.get(`${API}/matches/${matchId}`);
        setMatch(matchResponse.data);
        
        // Fetch match report
        const reportResponse = await axios.get(`${API}/match-report/${matchId}`);
        setReport(reportResponse.data);
        
        setLoading(false);
      } catch (err) {
        console.error("Error fetching match details:", err);
        setError("Failed to load match details. Please try again.");
        setLoading(false);
      }
    };

    fetchMatchData();
  }, [matchId]);</find>
        <replace>  useEffect(() => {
    const fetchMatchData = async () => {
      try {
        // Fetch match details
        const matchResponse = await axios.get(`${API}/matches/${matchId}`);
        setMatch(matchResponse.data);
        
        // Set match year
        const matchDate = new Date(matchResponse.data.date);
        setMatchYear(matchDate.getFullYear());
        
        // Fetch match report
        const reportResponse = await axios.get(`${API}/match-report/${matchId}`);
        setReport(reportResponse.data);
        
        setLoading(false);
      } catch (err) {
        console.error("Error fetching match details:", err);
        setError("Failed to load match details. Please try again.");
        setLoading(false);
      }
    };

    fetchMatchData();
  }, [matchId]);</replace>
      </content_update>
    </file>