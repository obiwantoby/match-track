import { useState, useEffect } from "react";
import axios from "axios";
import { useParams, useNavigate, Link } from "react-router-dom";
import getAPIUrl from "./API_FIX";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = getAPIUrl(BACKEND_URL);

const EditMatch = () => {
  const { matchId } = useParams();
  const navigate = useNavigate();
  const [match, setMatch] = useState(null);
  const [matchTypes, setMatchTypes] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [instanceCounter, setInstanceCounter] = useState(1);
  
  // Form state for the match being edited
  const [formData, setFormData] = useState({
    name: "",
    date: "",
    location: "",
    match_types: [],
    aggregate_type: "None"
  });
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch match details
        const matchResponse = await axios.get(`${API}/matches/${matchId}`);
        setMatch(matchResponse.data);
        
        // Find highest instance number to set counter
        let highestCounter = 0;
        matchResponse.data.match_types.forEach(mt => {
          const instanceNum = parseInt(mt.instance_name.replace(/^\D+/g, '') || '0');
          if (instanceNum > highestCounter) {
            highestCounter = instanceNum;
          }
        });
        setInstanceCounter(highestCounter + 1);
        
        // Fetch match types
        const typesResponse = await axios.get(`${API}/match-types`);
        setMatchTypes(typesResponse.data);
        
        // Initialize form data with the match
        setFormData({
          name: matchResponse.data.name,
          date: new Date(matchResponse.data.date).toISOString().split('T')[0],
          location: matchResponse.data.location,
          match_types: matchResponse.data.match_types,
          aggregate_type: matchResponse.data.aggregate_type
        });
        
        setLoading(false);
      } catch (err) {
        console.error("Error fetching data:", err);
        setError("Failed to load required data. Please try again.");
        setLoading(false);
      }
    };

    fetchData();
  }, [matchId]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value
    });
  };

  const addMatchType = (type) => {
    const instanceName = `${type}${instanceCounter}`;
    setInstanceCounter(instanceCounter + 1);
    
    setFormData({
      ...formData,
      match_types: [
        ...formData.match_types,
        {
          type,
          instance_name: instanceName,
          calibers: []
        }
      ]
    });
  };

  const removeMatchType = (index) => {
    const updatedTypes = [...formData.match_types];
    updatedTypes.splice(index, 1);
    
    setFormData({
      ...formData,
      match_types: updatedTypes
    });
  };

  const toggleCaliber = (matchTypeIndex, caliber) => {
    const updatedTypes = [...formData.match_types];
    const currentCaliberIndex = updatedTypes[matchTypeIndex].calibers.indexOf(caliber);
    
    if (currentCaliberIndex === -1) {
      // Add caliber
      updatedTypes[matchTypeIndex].calibers.push(caliber);
    } else {
      // Remove caliber
      updatedTypes[matchTypeIndex].calibers.splice(currentCaliberIndex, 1);
    }
    
    setFormData({
      ...formData,
      match_types: updatedTypes
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.name || !formData.date || !formData.location || formData.match_types.length === 0) {
      setError("Please fill out all required fields and add at least one match type");
      return;
    }
    
    // Check that each match type has at least one caliber
    for (const matchType of formData.match_types) {
      if (matchType.calibers.length === 0) {
        setError(`Please select at least one caliber for ${matchType.instance_name}`);
        return;
      }
    }
    
    try {
      // Update the match
      await axios.put(`${API}/matches/${matchId}`, {
        name: formData.name,
        date: new Date(formData.date).toISOString(),
        location: formData.location,
        match_types: formData.match_types,
        aggregate_type: formData.aggregate_type
      });
      
      setSuccess(true);
      setTimeout(() => {
        navigate(`/matches/${matchId}`);
      }, 2000);
    } catch (err) {
      console.error("Error updating match:", err);
      setError("Failed to update match. Please try again.");
    }
  };

  if (loading) return <div className="container mx-auto p-4 text-center">Loading match data...</div>;
  if (error) return <div className="container mx-auto p-4 text-center text-red-500">{error}</div>;
  if (!match || !matchTypes) return <div className="container mx-auto p-4 text-center">Match data not found</div>;

  if (success) {
    return (
      <div className="container mx-auto p-4">
        <div className="bg-green-100 text-green-700 p-6 rounded-lg shadow-md text-center">
          <h2 className="text-xl font-bold mb-2">Match Updated Successfully!</h2>
          <p>Redirecting to match details...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Edit Match</h1>
          <p className="text-gray-600">
            Update match details or add new match types
          </p>
        </div>
        <Link to={`/matches/${matchId}`} className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600">
          Back to Match
        </Link>
      </div>
      
      <div className="bg-white p-6 rounded-lg shadow">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                Match Name
              </label>
              <input
                id="name"
                name="name"
                type="text"
                value={formData.name}
                onChange={handleInputChange}
                placeholder="Enter match name"
                className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label htmlFor="date" className="block text-sm font-medium text-gray-700 mb-1">
                Match Date
              </label>
              <input
                id="date"
                name="date"
                type="date"
                value={formData.date}
                onChange={handleInputChange}
                className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label htmlFor="location" className="block text-sm font-medium text-gray-700 mb-1">
                Location
              </label>
              <input
                id="location"
                name="location"
                type="text"
                value={formData.location}
                onChange={handleInputChange}
                placeholder="Enter match location"
                className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
          </div>
          
          <div>
            <label htmlFor="aggregate_type" className="block text-sm font-medium text-gray-700 mb-1">
              Aggregate Type
            </label>
            <select
              id="aggregate_type"
              name="aggregate_type"
              value={formData.aggregate_type}
              onChange={handleInputChange}
              className="w-full md:w-1/3 px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="None">None</option>
              <option value="1800 (2x900)">1800 (2x900)</option>
              <option value="1800 (3x600)">1800 (3x600)</option>
              <option value="2700 (3x900)">2700 (3x900)</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Add New Match Types
            </label>
            
            <div className="flex flex-wrap gap-2 mb-4">
              {matchTypes && Object.keys(matchTypes).map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => addMatchType(type)}
                  className="px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                >
                  + {type}
                </button>
              ))}
            </div>
            
            {formData.match_types.length > 0 ? (
              <div className="space-y-4">
                {formData.match_types.map((matchType, index) => (
                  <div key={index} className="border p-4 rounded">
                    <div className="flex justify-between items-center mb-3">
                      <div className="flex flex-col md:flex-row md:items-center gap-2">
                        <div className="font-medium">{matchType.type}</div>
                        <div className="flex items-center">
                          <span className="text-gray-500 mr-2">Name:</span>
                          <input
                            type="text"
                            value={matchType.instance_name}
                            onChange={(e) => {
                              const updatedTypes = [...formData.match_types];
                              updatedTypes[index].instance_name = e.target.value;
                              setFormData({
                                ...formData,
                                match_types: updatedTypes
                              });
                            }}
                            className="border px-2 py-1 rounded text-sm"
                            placeholder={`${matchType.type}${instanceCounter}`}
                          />
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => removeMatchType(index)}
                        className="text-red-600 hover:text-red-800"
                      >
                        Remove
                      </button>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Calibers
                      </label>
                      <div className="flex flex-wrap gap-2">
                        {[".22", "CF", ".45", "Service Pistol", "Service Revolver", "DR"].map((caliber) => (
                          <button
                            key={caliber}
                            type="button"
                            onClick={() => toggleCaliber(index, caliber)}
                            className={`px-2 py-1 rounded text-sm ${
                              matchType.calibers.includes(caliber)
                                ? "bg-blue-600 text-white"
                                : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                            }`}
                          >
                            {caliber}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-gray-500 mb-4">No match types added yet. Click the buttons above to add match types.</div>
            )}
          </div>
          
          <div className="flex justify-end">
            <button 
              type="submit" 
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            >
              Update Match
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default EditMatch;