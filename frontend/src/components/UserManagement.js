<file>
      <absolute_file_name>/app/frontend/src/components/UserManagement.js</absolute_file_name>
      <content_update>
        <find>  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6">User Management</h1></find>
        <replace>  // Function to reset the database
  const handleDatabaseReset = async () => {
    if (window.confirm("Are you sure you want to reset the database? This will delete all matches, scores, and shooters.")) {
      try {
        await axios.post(`${API}/reset-database`);
        setSuccess("Database reset successfully!");
        setTimeout(() => {
          setSuccess("");
          // Refresh the page
          window.location.reload();
        }, 3000);
      } catch (err) {
        console.error("Error resetting database:", err);
        setError("Failed to reset database. Please try again.");
      }
    }
  };

  return (
    <div className="container mx-auto p-4">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">User Management</h1>
        <button 
          onClick={handleDatabaseReset}
          className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
        >
          Reset Database
        </button>
      </div></replace>
      </content_update>
    </file>