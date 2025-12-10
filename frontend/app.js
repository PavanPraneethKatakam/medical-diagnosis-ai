// API Configuration
const API_BASE = 'http://localhost:8001';

// Authentication credentials (Basic Auth)
const AUTH_USERNAME = 'admin';
const AUTH_PASSWORD = 'changeme123';
const AUTH_HEADER = 'Basic ' + btoa(AUTH_USERNAME + ':' + AUTH_PASSWORD);

// Helper function to create authenticated fetch options
function getAuthHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': AUTH_HEADER
    };
}

// Global state
let currentPatientId = null;
let currentDAG = null;

// Initialize Mermaid
mermaid.initialize({ startOnLoad: false, theme: 'dark' });

// Load patients on page load
window.addEventListener('DOMContentLoaded', () => {
    loadPatients();
    updateSystemStatus();
});

// Theme Toggle
function toggleTheme() {
    document.body.classList.toggle('light-mode');
    const btn = document.querySelector('.theme-toggle');
    btn.textContent = document.body.classList.contains('light-mode') ? '☀️' : '🌙';
}

// Load all patients
async function loadPatients() {
    try {
        const response = await fetch(`${API_BASE}/patients`);
        const patients = await response.json();

        const select = document.getElementById('patientSelect');
        patients.forEach(patient => {
            const option = document.createElement('option');
            option.value = patient.patient_id;
            option.textContent = `${patient.name} (ID: ${patient.patient_id})`;
            option.dataset.dob = patient.dob;
            option.dataset.gender = patient.gender;
            option.dataset.name = patient.name;
            select.appendChild(option);
        });
    } catch (error) {
        showError('Failed to load patients: ' + error.message);
    }
}

// Load patient history
async function loadPatientHistory() {
    const select = document.getElementById('patientSelect');
    const selectedOption = select.options[select.selectedIndex];

    if (!selectedOption.value) {
        document.getElementById('patientInfo').style.display = 'none';
        document.getElementById('historyCard').style.display = 'none';
        document.getElementById('controlsCard').style.display = 'none';
        return;
    }

    currentPatientId = parseInt(selectedOption.value);

    // Show patient info
    document.getElementById('patientName').textContent = selectedOption.dataset.name;
    document.getElementById('patientDOB').textContent = selectedOption.dataset.dob;
    document.getElementById('patientGender').textContent = selectedOption.dataset.gender;
    document.getElementById('patientInfo').style.display = 'block';

    // Load history
    try {
        const response = await fetch(`${API_BASE}/patients/${currentPatientId}/history`);
        const history = await response.json();

        displayHistory(history);

        document.getElementById('historyCard').style.display = 'block';
        document.getElementById('controlsCard').style.display = 'block';
    } catch (error) {
        showError('Failed to load patient history: ' + error.message);
    }
}

// Display patient history
function displayHistory(history) {
    const timeline = document.getElementById('historyTimeline');

    if (!history || history.length === 0) {
        timeline.innerHTML = '<p style="color: var(--text-secondary);">No medical history available</p>';
        return;
    }

    timeline.innerHTML = history.map((visit, index) => `
        <div class="timeline-item">
            <div class="timeline-marker">${index + 1}</div>
            <div class="timeline-content">
                <div class="timeline-date">${visit.visit_date}</div>
                <div class="timeline-disease">
                    <strong>${visit.diagnosis_code || 'N/A'}</strong>
                    <p>${visit.diagnosis_name || 'No diagnosis name'}</p>
                </div>
            </div>
        </div>
    `).join('');
}

// Generate prediction
async function generatePrediction() {
    if (!currentPatientId) return;

    const btn = document.querySelector('#controlsCard button');
    const btnText = document.getElementById('predictBtnText');
    const loader = document.getElementById('predictLoader');

    btnText.style.display = 'none';
    loader.style.display = 'inline-block';
    btn.disabled = true;

    updateSystemStatus('🔄 Running agent workflow...');

    try {
        const clinicianComment = document.getElementById('clinicianComment').value;

        const response = await fetch(`${API_BASE}/agents/predict`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                patient_id: currentPatientId,
                clinician_comment: clinicianComment || undefined
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        // Display predictions
        displayPredictions(data);

        // Display DAG
        displayDAG(data.dag);

        updateSystemStatus('✅ Prediction complete');
    } catch (error) {
        showError('Prediction failed: ' + error.message);
        updateSystemStatus('❌ Prediction failed');
    } finally {
        btnText.style.display = 'inline';
        loader.style.display = 'none';
        btn.disabled = false;
    }
}

// Display predictions with collapsible cards and score bars
function displayPredictions(data) {
    const predictionsDiv = document.getElementById('predictionsList');
    const explanationDiv = document.getElementById('explanation');
    const evidenceDiv = document.getElementById('evidence');

    // Check if data has predictions
    if (!data || !data.predictions || data.predictions.length === 0) {
        predictionsDiv.innerHTML = '<p style="color: var(--text-secondary);">No predictions available</p>';
        explanationDiv.innerHTML = '<p style="color: var(--text-secondary);">No explanation available</p>';
        evidenceDiv.innerHTML = '<p style="color: var(--text-secondary);">No evidence available</p>';
        return;
    }

    // Predictions with collapsible details
    predictionsDiv.innerHTML = data.predictions.map((pred, index) => `
        <div class="prediction-item rank-${pred.rank}" onclick="togglePredictionDetails(this)">
            <div class="prediction-header">
                <span class="rank-badge">#${pred.rank}</span>
                <span class="disease-code">${pred.code}</span>
                <span class="score-badge">${(pred.score * 100).toFixed(1)}%</span>
                <span class="expand-icon">▼</span>
            </div>
            <div class="prediction-details">
                <div class="score-breakdown">
                    <div class="score-bar">
                        <label>Transition Probability</label>
                        <div class="bar">
                            <div class="fill" style="width: 0%" data-width="${((pred.transition_score || pred.transition_prob || 0) * 100).toFixed(0)}%"></div>
                        </div>
                        <span style="font-size: 0.8rem; color: var(--text-secondary);">${((pred.transition_score || pred.transition_prob || 0) * 100).toFixed(1)}%</span>
                    </div>
                    <div class="score-bar">
                        <label>Knowledge Match</label>
                        <div class="bar">
                            <div class="fill" style="width: 0%" data-width="${((pred.doc_similarity || pred.knowledge_score || 0) * 100).toFixed(0)}%"></div>
                        </div>
                        <span style="font-size: 0.8rem; color: var(--text-secondary);">${((pred.doc_similarity || pred.knowledge_score || 0) * 100).toFixed(1)}%</span>
                    </div>
                    <div class="score-bar">
                        <label>DAG Support</label>
                        <div class="bar">
                            <div class="fill" style="width: 0%" data-width="${((pred.dag_score || 0) * 100).toFixed(0)}%"></div>
                        </div>
                        <span style="font-size: 0.8rem; color: var(--text-secondary);">${((pred.dag_score || 0) * 100).toFixed(1)}%</span>
                    </div>
                </div>
                <div class="explanation">
                    <strong>Reasoning:</strong> ${pred.reasoning || 'Based on patient history and medical knowledge.'}
                </div>
            </div>
        </div>
    `).join('');

    // Animate score bars after a short delay
    setTimeout(() => {
        document.querySelectorAll('.score-bar .fill').forEach(fill => {
            fill.style.width = fill.getAttribute('data-width');
        });
    }, 100);

    // Explanation
    explanationDiv.innerHTML = `
        <div class="explanation">
            ${data.explanation || 'Predictions generated using multi-agent workflow.'}
            ${data.fallback ? '<div class="fallback-note">⚠️ Note: Using fallback prediction strategy</div>' : ''}
        </div>
    `;

    // Evidence
    if (data.evidence && data.evidence.length > 0) {
        evidenceDiv.innerHTML = data.evidence.map(ev => `
            <div class="evidence-item">
                <div class="evidence-header">
                    <strong>${ev.disease_code || 'Medical Knowledge'}</strong>
                    <span class="similarity-badge">${(ev.similarity * 100).toFixed(0)}% match</span>
                </div>
                <div class="evidence-snippet">${ev.summary || ev.snippet || ev.content?.substring(0, 200) + '...'}</div>
            </div>
        `).join('');
    } else {
        evidenceDiv.innerHTML = '<p style="color: var(--text-secondary);">No evidence available</p>';
    }

    // Show the predictions card
    document.getElementById('predictionsCard').style.display = 'block';
}

// Toggle prediction details
function togglePredictionDetails(element) {
    const details = element.querySelector('.prediction-details');
    const isExpanded = element.classList.contains('expanded');

    // Close all other predictions
    document.querySelectorAll('.prediction-item').forEach(item => {
        if (item !== element) {
            item.classList.remove('expanded');
            item.querySelector('.prediction-details').classList.remove('expanded');
        }
    });

    // Toggle this prediction
    if (isExpanded) {
        element.classList.remove('expanded');
        details.classList.remove('expanded');
    } else {
        element.classList.add('expanded');
        details.classList.add('expanded');
    }
}

// Display DAG
function displayDAG(dag) {
    currentDAG = dag;

    if (!dag || !dag.nodes || dag.nodes.length === 0) {
        document.getElementById('dagCard').style.display = 'none';
        return;
    }

    // Generate Mermaid diagram
    let mermaidCode = 'graph LR\n';

    // Add nodes
    dag.nodes.forEach(node => {
        mermaidCode += `    ${node.id}["${node.id}"]\n`;
    });

    // Add edges
    dag.edges.forEach(edge => {
        const weight = (edge.weight * 100).toFixed(0);
        mermaidCode += `    ${edge.from} -->|${weight}%| ${edge.to}\n`;
    });

    // Style nodes
    mermaidCode += '    classDef default fill:#667eea,stroke:#764ba2,stroke-width:2px,color:#fff\n';

    const container = document.getElementById('mermaidDiagram');
    container.innerHTML = `<pre class="mermaid">${mermaidCode}</pre>`;

    mermaid.run({ nodes: container.querySelectorAll('.mermaid') });

    document.getElementById('dagCard').style.display = 'block';
}

// Refine DAG
async function refineDAG() {
    if (!currentPatientId) return;

    const action = document.getElementById('refineAction').value;
    const fromDisease = document.getElementById('fromDisease').value;
    const toDisease = document.getElementById('toDisease').value;
    const reason = document.getElementById('refineReason').value;

    if (!fromDisease || !toDisease || !reason) {
        alert('Please fill in all fields');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/agents/refine`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                patient_id: currentPatientId,
                feedback: { action, from: fromDisease, to: toDisease, reason }
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Check if data has the expected structure
        if (data.dag) {
            displayDAG(data.dag);
        }

        if (data.predictions) {
            displayPredictions(data);
        }

        // Clear form
        document.getElementById('fromDisease').value = '';
        document.getElementById('toDisease').value = '';
        document.getElementById('refineReason').value = '';

        showSuccess('DAG updated successfully!');
    } catch (error) {
        console.error('Refine error:', error);
        showError('Failed to refine DAG: ' + error.message);
    }
}

// Chat functionality
async function sendChatMessage() {
    if (!currentPatientId) {
        alert('Please select a patient first');
        return;
    }

    const input = document.getElementById('chatInput');
    const message = input.value.trim();

    if (!message) return;

    // Add user message to chat
    addChatMessage('user', message);
    input.value = '';

    try {
        const response = await fetch(`${API_BASE}/agents/chat`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                patient_id: currentPatientId,
                message: message
            })
        });

        const data = await response.json();
        addChatMessage('assistant', data.reply);
    } catch (error) {
        addChatMessage('assistant', 'Sorry, I encountered an error: ' + error.message);
    }
}

function handleChatKeypress(event) {
    if (event.key === 'Enter') {
        sendChatMessage();
    }
}

function addChatMessage(role, message) {
    const messagesDiv = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}`;
    messageDiv.innerHTML = `
        <div class="message-avatar">${role === 'user' ? '👤' : '🤖'}</div>
        <div class="message-content">${message}</div>
    `;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Upload document
async function uploadDocument() {
    const fileInput = document.getElementById('fileInput');
    const diseaseCode = document.getElementById('diseaseCodeInput').value;
    const statusDiv = document.getElementById('uploadStatus');

    if (!fileInput.files[0]) {
        alert('Please select a file');
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    if (diseaseCode) {
        formData.append('disease_code', diseaseCode);
    }

    statusDiv.innerHTML = '<p class="loading">⏳ Uploading...</p>';

    try {
        const response = await fetch(`${API_BASE}/agents/upload_doc`, {
            method: 'POST',
            headers: {
                'Authorization': AUTH_HEADER
            },
            body: formData
        });

        const data = await response.json();
        statusDiv.innerHTML = `<p class="success">✅ ${data.message}</p>`;

        // Clear inputs
        fileInput.value = '';
        document.getElementById('diseaseCodeInput').value = '';
    } catch (error) {
        statusDiv.innerHTML = `<p class="error">❌ Upload failed: ${error.message}</p>`;
    }
}

// System status
async function updateSystemStatus(message) {
    const statusEl = document.getElementById('systemStatus');
    if (message) {
        statusEl.textContent = message;
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();
        statusEl.textContent = `🟢 ${data.status} - ${data.patient_count} patients`;
    } catch (error) {
        statusEl.textContent = '🔴 API Offline';
    }
}

// Utility functions
function showError(message) {
    alert('Error: ' + message);
}

function showSuccess(message) {
    alert('Success: ' + message);
}
