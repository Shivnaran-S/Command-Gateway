const API_URL = "http://localhost:8000";
let currentUser = null;
let apiKey = "";

// --- GLOBAL STATE ---
let userSortOrder = 'desc';
let adminSortOrder = 'desc';

async function login() {
    apiKey = document.getElementById('api-key-input').value;
    const res = await fetch(`${API_URL}/me`, { headers: { 'x-api-key': apiKey } });

    if (res.ok) {
        currentUser = await res.json();
        document.getElementById('login-section').style.display = 'none';
        document.getElementById('dashboard-section').style.display = 'block';
        document.getElementById('user-info').innerText = `Logged in as: ${currentUser.username}`;
        document.getElementById('credit-display').innerText = currentUser.credits;

        // NEW: Fetch Rules for everyone
        fetchRules();

        if (currentUser.role === 'admin') {
            document.getElementById('admin-panel').style.display = 'block';
            
            // REQUIREMENT 1: Hide "My Command History" for admins
            document.getElementById('user-history-card').style.display = 'none';
            
            fetchAdminLogs();
        } else {
            // Ensure Admin panel is hidden
            document.getElementById('admin-panel').style.display = 'none';
            
            // Show "My Command History" for members
            document.getElementById('user-history-card').style.display = 'block';
            
            fetchUserLogs();
        }
    } else {
        alert("Invalid API Key");
    }
}

// UPDATED COMMAND SUBMISSION UI
async function submitCommand() {
    const cmdText = document.getElementById('cmd-input').value;
    const res = await fetch(`${API_URL}/commands`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-api-key': apiKey },
        body: JSON.stringify({ command_text: cmdText })
    });
    
    const data = await res.json();
    
    // UI Update
    const container = document.getElementById('cmd-result-container');
    const statusSpan = document.getElementById('res-status');
    const reasonSpan = document.getElementById('res-reason');
    
    container.style.display = 'block';
    statusSpan.innerText = data.status;
    reasonSpan.innerText = data.message;
    
    if(data.status === 'EXECUTED') statusSpan.style.color = 'lime';
    else statusSpan.style.color = 'red';

    if (res.ok) {
        document.getElementById('credit-display').innerText = data.new_balance;
        // Refresh logs immediately
        fetchUserLogs(); 
        if(currentUser.role === 'admin') fetchAdminLogs();
    }
}

// USER LOGS (Bottom of page)
async function fetchUserLogs() {
    const status = document.getElementById('user-status-filter').value;
    const url = `${API_URL}/logs?status_filter=${status}&sort_order=${userSortOrder}`;
    
    const res = await fetch(url, { headers: { 'x-api-key': apiKey } });
    const logs = await res.json();
    
    const tbody = document.querySelector('#user-logs-table tbody');
    tbody.innerHTML = logs.map(l => `
        <tr>
            <td>${new Date(l.timestamp).toLocaleTimeString()}</td>
            <td>${l.command_text}</td>
            <td style="color:${l.status==='EXECUTED'?'lime':'red'}">${l.status}</td>
            <td>${l.reason}</td>
        </tr>
    `).join('');
}

function toggleUserSort() {
    userSortOrder = userSortOrder === 'desc' ? 'asc' : 'desc';
    document.getElementById('user-sort-btn').innerText = userSortOrder === 'desc' ? 'Time ↓' : 'Time ↑';
    fetchUserLogs();
}

// ADMIN LOGS (Complex filters)
async function fetchAdminLogs() {
    const role = document.getElementById('admin-role-filter').value;
    const status = document.getElementById('admin-status-filter').value;
    const targetKey = document.getElementById('admin-key-filter').value;
    
    let url = `${API_URL}/logs?role_filter=${role}&status_filter=${status}&sort_order=${adminSortOrder}`;
    if(targetKey) url += `&target_api_key=${targetKey}`;

    const res = await fetch(url, { headers: { 'x-api-key': apiKey } });
    const logs = await res.json();
    
    const tbody = document.querySelector('#admin-logs-table tbody');
    tbody.innerHTML = logs.map(l => `
        <tr>
            <td>${new Date(l.timestamp).toLocaleTimeString()}</td>
            
            <td>${l.username} ${l.username === currentUser.username ? '(Me)' : ''}</td>
            
            <td>${l.command_text}</td>
            <td style="color:${l.status==='EXECUTED'?'lime':'red'}">${l.status}</td>
            <td>${l.reason}</td>
        </tr>
    `).join('');
}

function toggleAdminSort() {
    adminSortOrder = adminSortOrder === 'desc' ? 'asc' : 'desc';
    document.getElementById('admin-sort-btn').innerText = adminSortOrder === 'desc' ? 'Time ↓' : 'Time ↑';
    fetchAdminLogs();
}

// USER MANAGEMENT (Search, Update, Delete)
async function createUser() {
    const username = document.getElementById('new-username').value;
    const role = document.getElementById('new-role').value;
    const credits = document.getElementById('new-credits').value; // Added credits
    
    const res = await fetch(`${API_URL}/users/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-api-key': apiKey },
        body: JSON.stringify({ username, role, credits: parseInt(credits) })
    });
    
    if(res.ok) {
        const data = await res.json();
        document.getElementById('new-user-key').innerText = `Success! Key: ${data.api_key}`;
    } else {
        alert("Error creating user (Username exists?)");
    }
}

async function searchUser() {
    const targetKey = document.getElementById('manage-api-key').value;
    const res = await fetch(`${API_URL}/users/search?target_key=${targetKey}`, {
        headers: { 'x-api-key': apiKey }
    });
    
    if(res.ok) {
        const user = await res.json();
        document.getElementById('edit-user-form').style.display = 'block';
        document.getElementById('edit-username').value = user.username;
        document.getElementById('edit-credits').value = user.credits;
    } else {
        alert("User not found or invalid key");
        document.getElementById('edit-user-form').style.display = 'none';
    }
}

async function saveUserChanges() {
    const targetKey = document.getElementById('manage-api-key').value;
    const username = document.getElementById('edit-username').value;
    const credits = document.getElementById('edit-credits').value;
    
    const res = await fetch(`${API_URL}/users/update?target_key=${targetKey}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'x-api-key': apiKey },
        body: JSON.stringify({ username, credits: parseInt(credits) })
    });
    
    if(res.ok) alert("User Updated!");
}

async function deleteUser() {
    if(!confirm("Are you sure? This cannot be undone.")) return;
    
    const targetKey = document.getElementById('manage-api-key').value;
    const res = await fetch(`${API_URL}/users/delete?target_key=${targetKey}`, {
        method: 'DELETE',
        headers: { 'x-api-key': apiKey }
    });
    
    if(res.ok) {
        alert("User Deleted");
        document.getElementById('edit-user-form').style.display = 'none';
        document.getElementById('manage-api-key').value = '';
    }
}

// Function to fetch and display rules
async function fetchRules() {
    const res = await fetch(`${API_URL}/rules`, {
        headers: { 'x-api-key': apiKey }
    });
    
    if (res.ok) {
        const rules = await res.json();
        const tbody = document.querySelector('#rules-list-table tbody');
        
        tbody.innerHTML = rules.map(r => `
            <tr>
                <td style="font-family: monospace; color: #ffeb3b;">${r.pattern}</td>
                <td style="font-weight: bold; color: ${r.action === 'AUTO_ACCEPT' ? 'lime' : '#f44336'}">
                    ${r.action}
                </td>
            </tr>
        `).join('');
    }
}

async function addRule() {
    const pattern = document.getElementById('rule-pattern').value;
    const action = document.getElementById('rule-action').value;
    
    const res = await fetch(`${API_URL}/rules`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-api-key': apiKey },
        body: JSON.stringify({ pattern, action })
    });
    
    if(res.ok) {
        alert("Rule added!");
        fetchRules(); 
    } else {
        alert("Failed to add rule (Invalid Regex?)");
    }
}

async function fetchLogs() {
    const res = await fetch(`${API_URL}/logs`, { headers: { 'x-api-key': apiKey } });
    const logs = await res.json();
    const tbody = document.querySelector('#logs-table tbody');
    
    tbody.innerHTML = logs.map(l => {
        // Simple logic: Green if executed, Red if rejected
        const color = l.status === 'EXECUTED' ? '#4caf50' : '#f44336';
        
        return `
        <tr>
            <td>${new Date(l.timestamp).toLocaleTimeString()}</td>
            <td>${l.user_id}</td>
            <td>${l.command_text}</td>
            
            <td style="color: ${color}; font-weight:bold;">
                ${l.status}
            </td>
            
            <td>${l.reason}</td>
        </tr>
    `}).join('');
}

function logout() {
    location.reload();
}