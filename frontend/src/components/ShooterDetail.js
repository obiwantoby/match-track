<file>
      <absolute_file_name>/app/frontend/src/components/ShooterDetail.js</absolute_file_name>
      <content_update>
        <find>  const [selectedCaliberTab, setSelectedCaliberTab] = useState(null);
  
  // Edit mode states
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState({
    name: "",
    nra_number: "",
    cmp_number: ""
  });</find>
        <replace>  const [selectedCaliberTab, setSelectedCaliberTab] = useState(null);
  const [selectedYear, setSelectedYear] = useState("all");
  const [availableYears, setAvailableYears] = useState([]);
  
  // Edit mode states
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState({
    name: "",
    nra_number: "",
    cmp_number: ""
  });</replace>
      </content_update>
    </file>