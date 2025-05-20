// Helper function to fix API URL construction
const getAPIUrl = (baseUrl) => {
  // Check if BACKEND_URL already contains /api to avoid duplication
  return baseUrl.endsWith('/api') ? baseUrl : `${baseUrl}/api`;
};

export default getAPIUrl;
