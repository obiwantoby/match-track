<file>
      <absolute_file_name>/app/frontend/src/components/MatchReport.js</absolute_file_name>
      <content_update>
        <find>  const [selectedView, setSelectedView] = useState("summary"); // summary, details, aggregates
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { isAdmin } = useAuth();</find>
        <replace>  const [selectedView, setSelectedView] = useState("summary"); // summary, details, aggregates
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { isAdmin } = useAuth();
  const [matchYear, setMatchYear] = useState(null);</replace>
      </content_update>
    </file>