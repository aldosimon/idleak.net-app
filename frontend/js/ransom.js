// Replace with your actual Supabase URL and key
const SUPABASE_URL = 'https://egodqvysjgmboyrnopkj.supabase.co/';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVnb2RxdnlzamdtYm95cm5vcGtqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTg1NTMxNTEsImV4cCI6MjA3NDEyOTE1MX0.SFCN1S_YLjlpLWX7WsrM087AAWKRMY59PF2tCIMCAyg';
const RANSOMWARE_TABLE = 'idransom'; // <-- Table name stored in a variable

const { createClient } = supabase
const _supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

// Get HTML element
const container = document.getElementById('ransomware-table-container');

// Fetch data from Supabase and render with Grid.js
async function fetchDataAndRender() {
// Fetch all data from the Supabase table, omitting 'id' and 'country'
const { data, error } = await _supabase
    .from(RANSOMWARE_TABLE)
    .select('title, description, discovered_date, published_date, website, industry, source, url_source');

    if (error) {
        console.error('Error fetching data:', error);
        container.innerHTML = '<p>Error loading data. Please try again later.</p>';
        return;
    }

    if (!data || data.length === 0) {
        container.innerHTML = '<p>No incidents found.</p>';
        return;
    }
    
    // Get the column headers from the first row of data
    const columns = Object.keys(data[0]);

    // Create a new Grid instance
    new gridjs.Grid({
        columns: columns,
        data: data,
        search: true, // Enable search functionality
        sort: true,   // Enable sorting
        pagination: { // Configure pagination
            enabled: true,
            limit: 10, // Items per page
            summary: true // Show pagination summary
        }
    }).render(container);
}

// Initial data fetch on page load
document.addEventListener('DOMContentLoaded', () => {
    fetchDataAndRender();
});