const API_URL = "http://localhost:8000";
let currentUser = null;
let apiKey = "";

async function login() {
    apiKey = document.getElementById('api-key-input').value;
    const res = await fetch(`${API_URL}/me`, {
        headers: { 'x-api-key': apiKey }
    });

    if (res.ok) {
        currentUser = await res.json();
        document.getElementById('login-section').style.display = 'none';
        document.getElementById('dashboard-section').style.display = 'block';
        document.getElementById('user-info').innerText = `Logged in as: ${currentUser.username} (${currentUser.role})`;
        document.getElementById('credit-display').innerText = currentUser.credits;

        if (currentUser.role === 'admin') {
            document.getElementById('admin-panel').style.display = 'block';
            fetchLogs();
        }
    } else {
        alert("Invalid API Key");
    }
}

async function submitCommand() {
    const cmdText = document.getElementById('cmd-input').value;
    const res = await fetch(`${API_URL}/commands`, {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'x-api-key': apiKey 
        },
        body: JSON.stringify({ command_text: cmdText })
    });
    
    const data = await res.json();
    const resultBox = document.getElementById('cmd-result');
    
    if (res.ok) {
        resultBox.innerText = `> ${data.message}`;
        resultBox.style.color = data.status === 'executed' ? '#4caf50' : '#f44336';
        document.getElementById('credit-display').innerText = data.new_balance;
    } else {
        resultBox.innerText = `Error: ${data.detail}`;
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
    
    if(res.ok) alert("Rule added!");
    else alert("Failed to add rule (Invalid Regex?)");
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

async function createUser() {
    const username = document.getElementById('new-username').value;
    const role = document.getElementById('new-role').value;
    const res = await fetch(`${API_URL}/users/generate?username=${username}&role=${role}`, {
        method: 'POST',
        headers: { 'x-api-key': apiKey }
    });
    const data = await res.json();
    document.getElementById('new-user-key').innerText = `Key: ${data.api_key}`;
}

function logout() {
    location.reload();
}