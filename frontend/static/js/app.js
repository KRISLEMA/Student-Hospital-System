// Configuration
const API_URL = '';
axios.defaults.withCredentials = true;

// Current state
let currentUser = null;
let doctorsList = [];
let dashboardChart = null;

// DOM Elements
const views = ['home', 'login', 'register', 'student-dashboard', 'doctor-dashboard', 'admin-dashboard'];
const navAuthButtons = document.getElementById('nav-auth-buttons');
const navUserInfo = document.getElementById('nav-user-info');
const userDisplay = document.getElementById('user-display');
const userRole = document.getElementById('user-role');
const mainNav = document.getElementById('main-nav');

// Theme Management
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.body.setAttribute('data-bs-theme', savedTheme);
    updateThemeIcon(savedTheme);
}

function toggleTheme() {
    const currentTheme = document.body.getAttribute('data-bs-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    document.body.setAttribute('data-bs-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
    const icon = document.getElementById('theme-icon');
    if (theme === 'dark') {
        icon.classList.replace('bi-sun-fill', 'bi-moon-stars-fill');
        icon.classList.replace('text-warning', 'text-info');
    } else {
        icon.classList.replace('bi-moon-stars-fill', 'bi-sun-fill');
        icon.classList.replace('text-info', 'text-warning');
    }
}

function showView(id) {
    views.forEach(v => {
        const el = document.getElementById(`view-${v}`);
        if (el) el.classList.toggle('d-none', v !== id);
    });
}

// Initialize the application
async function init() {
    initTheme();
    try {
        const response = await axios.get(`${API_URL}/me`);
        currentUser = response.data;
        updateUIForLoggedInUser();
        showDashboard();
    } catch (error) {
        currentUser = null;
        updateUIForLoggedOutUser();
        showView('home');
    }
}

function updateUIForLoggedInUser() {
    navAuthButtons.classList.add('d-none');
    navUserInfo.classList.remove('d-none');
    userDisplay.textContent = currentUser.full_name;
    userRole.textContent = currentUser.role.toUpperCase();
    
    // Update main nav items based on role
    updateMainNav();
}

function updateUIForLoggedOutUser() {
    navAuthButtons.classList.remove('d-none');
    navUserInfo.classList.add('d-none');
    mainNav.innerHTML = '';
}

function updateMainNav() {
    let items = '';
    if (currentUser.role === 'student') {
        items = `
            <li class="nav-item"><a class="nav-link" href="#" onclick="showDashboard()">Dashboard</a></li>
            <li class="nav-item"><a class="nav-link" href="#" onclick="showModal('book-modal')">Book Appointment</a></li>
        `;
    } else if (currentUser.role === 'doctor') {
        items = `<li class="nav-item"><a class="nav-link" href="#" onclick="showDashboard()">My Appointments</a></li>`;
    } else if (currentUser.role === 'admin') {
        items = `
            <li class="nav-item"><a class="nav-link" href="#" onclick="showDashboard()">Analytics</a></li>
            <li class="nav-item"><a class="nav-link" href="#" onclick="showView('admin-dashboard')">Management</a></li>
        `;
    }
    mainNav.innerHTML = items;
}

document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    try {
        const r = await axios.post(`${API_URL}/login`, { username, password });
        currentUser = r.data.user;
        updateUIForLoggedInUser();
        showDashboard();
    } catch (e2) {
        alert(e2.response?.data?.message || 'Login failed');
    }
});

document.getElementById('register-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const full_name = document.getElementById('register-fullname').value;
    const username = document.getElementById('register-username').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    try {
        await axios.post(`${API_URL}/register`, { full_name, username, email, password });
        alert('Registration successful! Please login.');
        showView('login');
    } catch (e2) {
        alert(e2.response?.data?.message || 'Registration failed');
    }
});

document.getElementById('transfer-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('transfer-appointment-id').value;
    const doctor_id = document.getElementById('transfer-doctor-id').value;
    const reason = document.getElementById('transfer-reason').value;
    try {
        await axios.post(`${API_URL}/appointments/${id}/transfer`, { doctor_id, reason });
        bootstrap.Modal.getInstance(document.getElementById('modalTransfer')).hide();
        alert('Patient transferred successfully!');
        refreshDoctor();
    } catch (error) {
        alert(error.response?.data?.message || 'Transfer failed');
    }
});

async function logout() {
    try {
        await axios.post(`${API_URL}/logout`);
        currentUser = null;
        updateUIForLoggedOutUser();
        showView('home');
    } catch (error) {
        console.error('Logout failed', error);
    }
}

function showDashboard() {
    if (currentUser.role === 'student') {
        showView('student-dashboard');
        refreshStudent();
    } else if (currentUser.role === 'doctor') {
        showView('doctor-dashboard');
        refreshDoctor();
    } else {
        showView('admin-dashboard');
        refreshAdmin();
    }
}

async function refreshStudent() {
    try {
        const noti = await axios.get(`${API_URL}/notifications`);
        document.getElementById('student-notifications').innerHTML = noti.data.length ? noti.data.slice(0, 5).map(n => `
            <li class="list-group-item border-0 border-bottom py-3 px-4">
                <div class="d-flex justify-content-between align-items-start mb-1">
                    <span class="badge rounded-pill bg-primary-subtle text-primary small">${n.type}</span>
                    <small class="text-muted" style="font-size: 0.7rem;">${new Date(n.created_at).toLocaleDateString()}</small>
                </div>
                <div class="small text-dark fw-medium">${n.content}</div>
            </li>
        `).join('') : '<li class="list-group-item border-0 py-4 text-center text-muted small">No new notifications</li>';

        const a = await axios.get(`${API_URL}/appointments`);
        document.getElementById('student-appointments').innerHTML = a.data.length ? a.data.map(x => {
            const badge = statusBadge(x.status);
            const urgentTag = x.urgent ? '<span class="badge bg-danger urgent-badge ms-1" style="font-size: 0.6rem;">URGENT</span>' : '';
            const act = x.status === 'Pending' ? `
                <div class="btn-group">
                    <button class="btn btn-sm btn-outline-danger rounded-pill px-3 me-2" onclick="cancelAppointment(${x.id})">Cancel</button>
                    <button class="btn btn-sm btn-outline-secondary rounded-pill px-3" onclick="openReschedule(${x.id})">Reschedule</button>
                </div>
            ` : '-';
            return `
                <tr>
                    <td class="ps-4 fw-bold">${x.doctor_name || 'TBD'}</td>
                    <td><span class="badge bg-secondary-subtle text-secondary rounded-pill">${x.specialization}</span></td>
                    <td>
                        <div class="small fw-bold text-dark">${x.date}</div>
                        <div class="small text-muted">${x.time} ${urgentTag}</div>
                    </td>
                    <td>${badge}</td>
                    <td class="text-end pe-4">${act}</td>
                </tr>
            `;
        }).join('') : '<tr><td colspan="5" class="text-center py-5 text-muted">You have no appointments yet</td></tr>';

        const r = await axios.get(`${API_URL}/medical_records`);
        document.getElementById('student-records').innerHTML = r.data.length ? r.data.map(m => `
            <li class="list-group-item border-0 border-bottom py-3 px-4">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <span class="fw-bold text-dark small">Record #${m.id}</span>
                    <small class="text-muted" style="font-size: 0.7rem;">${new Date(m.created_at).toLocaleDateString()}</small>
                </div>
                <div class="small text-secondary mb-1">Diagnosis: <span class="text-dark fw-medium">${m.diagnosis}</span></div>
                <div class="text-muted" style="font-size: 0.75rem;">${m.notes || ''}</div>
            </li>
        `).join('') : '<li class="list-group-item border-0 py-4 text-center text-muted small">No medical records found</li>';

        const p = await axios.get(`${API_URL}/prescriptions`);
        document.getElementById('student-prescriptions').innerHTML = p.data.length ? p.data.map(m => `
            <li class="list-group-item border-0 border-bottom py-3 px-4">
                <div class="fw-bold text-dark small mb-1">${m.medication}</div>
                <div class="d-flex justify-content-between align-items-center">
                    <span class="badge bg-info-subtle text-info rounded-pill" style="font-size: 0.7rem;">${m.dosage}</span>
                    <small class="text-muted italic" style="font-size: 0.7rem;">${m.instructions || 'As directed'}</small>
                </div>
            </li>
        `).join('') : '<li class="list-group-item border-0 py-4 text-center text-muted small">No active prescriptions</li>';
    } catch (error) {
        console.error('Failed to refresh student dashboard', error);
    }
}

async function refreshDoctor() {
    try {
        const a = await axios.get(`${API_URL}/appointments`);
        document.getElementById('doctor-appointments').innerHTML = a.data.length ? a.data.map(x => {
            const urgentTag = x.urgent ? '<span class="badge bg-danger urgent-badge ms-1" style="font-size: 0.6rem;">URGENT</span>' : '';
            
            let actions = '';
            if (x.status === 'Pending') {
                actions = `
                    <div class="btn-group">
                        <button class="btn btn-sm btn-success rounded-pill px-3 me-2" onclick="updateStatus(${x.id}, 'Confirmed')">Confirm</button>
                        <button class="btn btn-sm btn-outline-danger rounded-pill px-3" onclick="updateStatus(${x.id}, 'Cancelled')">Cancel</button>
                    </div>
                `;
            } else if (x.status === 'Confirmed') {
                actions = `
                    <div class="btn-group">
                        <button class="btn btn-sm btn-primary rounded-pill px-3 me-2" onclick="updateStatus(${x.id}, 'Completed')">Mark Completed</button>
                        <button class="btn btn-sm btn-outline-info rounded-pill px-3 me-2" onclick="openTransferModal(${x.id}, '${x.specialization}')">Transfer</button>
                        <button class="btn btn-sm btn-success rounded-pill px-3" onclick="prefillRecordForm(${x.id})">Add Record</button>
                    </div>
                `;
            } else if (x.status === 'Completed') {
                actions = `<button class="btn btn-sm btn-outline-success rounded-pill px-3" onclick="prefillRecordForm(${x.id})">Add Record</button>`;
            } else {
                actions = '-';
            }

            return `
                <tr>
                    <td class="ps-4 fw-bold text-dark">${x.student_name} ${urgentTag}</td>
                    <td>
                        <div class="small fw-bold">${x.date}</div>
                        <div class="small text-muted">${x.time}</div>
                    </td>
                    <td>${statusBadge(x.status)}</td>
                    <td class="text-end pe-4">${actions}</td>
                </tr>
            `;
        }).join('') : '<tr><td colspan="4" class="text-center py-5 text-muted">No appointments assigned to you</td></tr>';

        // Fetch recent records for doctor
        const r = await axios.get(`${API_URL}/medical_records`);
        document.getElementById('doctor-recent-records').innerHTML = r.data.length ? r.data.reverse().slice(0, 10).map(m => `
            <li class="list-group-item border-0 border-bottom py-3 px-4">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <span class="fw-bold text-dark small">Record #${m.id} (Appt #${m.appointment_id})</span>
                    <button class="btn btn-sm btn-outline-info rounded-pill px-2 py-0" style="font-size: 0.7rem;" onclick="prefillPrescriptionForm(${m.id})">Prescribe</button>
                </div>
                <div class="small text-secondary mb-1">Diagnosis: <span class="text-dark fw-medium">${m.diagnosis}</span></div>
                <div class="text-muted" style="font-size: 0.7rem;">${new Date(m.created_at).toLocaleString()}</div>
            </li>
        `).join('') : '<li class="list-group-item border-0 py-4 text-center text-muted small">No recent records</li>';
    } catch (error) {
        console.error('Failed to refresh doctor dashboard', error);
    }
}

async function openTransferModal(appointmentId, specialization) {
    document.getElementById('transfer-appointment-id').value = appointmentId;
    const select = document.getElementById('transfer-doctor-id');
    select.innerHTML = '<option value="" disabled selected>Loading doctors...</option>';
    
    try {
        const response = await axios.get(`${API_URL}/admin/doctors`);
        // Filter by specialization and exclude self if possible (though we don't have current doctor ID easily here)
        const doctors = response.data.filter(d => d.specialization === specialization);
        
        if (doctors.length <= 1) {
            select.innerHTML = '<option value="" disabled selected>No other doctors available for this specialization</option>';
        } else {
            select.innerHTML = '<option value="" disabled selected>Select a doctor</option>' + 
                doctors.map(d => `<option value="${d.id}">Dr. ${d.name}</option>`).join('');
        }
        
        new bootstrap.Modal(document.getElementById('modalTransfer')).show();
    } catch (error) {
        alert('Failed to fetch doctors list');
    }
}

function prefillRecordForm(appointmentId) {
    document.getElementById('record-appointment-id').value = appointmentId;
    document.getElementById('record-diagnosis').focus();
    window.scrollTo({ top: document.getElementById('form-record').offsetTop - 120, behavior: 'smooth' });
}

function prefillPrescriptionForm(recordId) {
    document.getElementById('presc-record-id').value = recordId;
    document.getElementById('presc-medication').focus();
    window.scrollTo({ top: document.getElementById('form-prescription').offsetTop - 120, behavior: 'smooth' });
}

let adminDoctorsList = [];

async function refreshAdmin() {
    try {
        const a = await axios.get(`${API_URL}/analytics/summary`);
        document.getElementById('admin-stats').innerHTML = [
            statCard('Total Visits', a.data.total, 'bi-people', 'primary'),
            statCard('Approved', a.data.status_counts.Confirmed || 0, 'bi-check2-circle', 'success'),
            statCard('Cancelled', a.data.status_counts.Cancelled || 0, 'bi-x-circle', 'danger'),
            statCard('Completed', a.data.status_counts.Completed || 0, 'bi-award', 'info')
        ].join('');

        const ctx = document.getElementById('chart-appointments').getContext('2d');
        const labels = a.data.by_day.map(d => d.date);
        const counts = a.data.by_day.map(d => d.count);
        
        if (window._chart) window._chart.destroy();
        window._chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: 'Appointments',
                    data: counts,
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13, 110, 253, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { display: false } },
                    x: { grid: { display: false } }
                }
            }
        });

        const d = await axios.get(`${API_URL}/admin/doctors`);
        adminDoctorsList = d.data;
        document.getElementById('admin-doctors').innerHTML = adminDoctorsList.length ? adminDoctorsList.map(x => `
            <li class="list-group-item border-0 border-bottom py-3 d-flex justify-content-between align-items-center">
                <div class="flex-grow-1">
                    <div class="fw-bold text-dark small">${x.name}</div>
                    <div class="text-muted" style="font-size: 0.7rem;">${x.availability || 'Schedule not set'}</div>
                    <span class="badge bg-primary-subtle text-primary rounded-pill mt-1" style="font-size: 0.65rem;">${x.specialization}</span>
                </div>
                <div class="btn-group">
                    <button class="btn btn-sm btn-outline-primary border-0" onclick="openEditDoctor(${x.id})">
                        <i class="bi bi-pencil-square"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger border-0" onclick="deleteDoctor(${x.id})">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </li>
        `).join('') : '<li class="list-group-item border-0 py-4 text-center text-muted small">No doctors registered</li>';

    } catch (error) {
        console.error('Failed to refresh admin dashboard', error);
    }
}

function statCard(title, value, icon, color) {
    return `
        <div class="col-md-3">
            <div class="card border-0 shadow-sm dashboard-stat-card h-100" style="border-left-color: var(--${color}-color) !important;">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <div class="text-muted small fw-bold text-uppercase">${title}</div>
                        <i class="bi ${icon} text-${color} fs-4"></i>
                    </div>
                    <div class="h3 fw-bold mb-0">${value}</div>
                </div>
            </div>
        </div>
    `;
}

function statusBadge(s) {
    const map = {
        Pending: { bg: 'warning-subtle', text: 'warning' },
        Confirmed: { bg: 'success-subtle', text: 'success' },
        Cancelled: { bg: 'danger-subtle', text: 'danger' },
        Completed: { bg: 'primary-subtle', text: 'primary' }
    };
    const style = map[s] || { bg: 'secondary-subtle', text: 'secondary' };
    return `<span class="badge bg-${style.bg} text-${style.text} rounded-pill px-3">${s}</span>`;
}

document.getElementById('book-date').addEventListener('change', updateTimeSlots);
document.getElementById('book-specialization').addEventListener('change', updateTimeSlots);

async function updateTimeSlots() {
    const date = document.getElementById('book-date').value;
    const specialization = document.getElementById('book-specialization').value;
    if (!date || !specialization) return;
    try {
        const r = await axios.get(`${API_URL}/timeslots`, { params: { date, specialization } });
        if (r.data.available.length === 0) {
            document.getElementById('book-time').innerHTML = '<option disabled>No doctors available for this specialization/date</option>';
        } else {
            document.getElementById('book-time').innerHTML = r.data.available.map(t => `<option value="${t}">${t}</option>`).join('');
        }
    } catch (error) {
        document.getElementById('book-time').innerHTML = '<option disabled>Error loading slots</option>';
    }
}

document.getElementById('book-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const specialization = document.getElementById('book-specialization').value;
    const date = document.getElementById('book-date').value;
    const time = document.getElementById('book-time').value;
    const urgent = document.getElementById('book-urgent').checked;
    const reason = document.getElementById('book-reason').value;
    try {
        await axios.post(`${API_URL}/appointments`, { specialization, date, time, urgent, reason });
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalBook'));
        modal.hide();
        refreshStudent();
    } catch (e2) {
        alert(e2.response?.data?.message || 'Booking failed');
    }
});

async function cancelAppointment(id) {
    if (!confirm('Cancel this appointment?')) return;
    await axios.patch(`${API_URL}/appointments/${id}/status`, { status: 'Cancelled' });
    refreshStudent();
}

function openReschedule(id) {
    const date = prompt('New date (YYYY-MM-DD)');
    const time = prompt('New time (HH:MM)');
    if (!date || !time) return;
    axios.post(`${API_URL}/appointments/${id}/reschedule`, { date, time }).then(refreshStudent).catch(e => alert(e.response?.data?.message || 'Reschedule failed'));
}

async function updateStatus(id, status) {
    await axios.patch(`${API_URL}/appointments/${id}/status`, { status });
    if (currentUser.role === 'doctor') refreshDoctor(); else refreshAdmin();
}

document.getElementById('form-record').addEventListener('submit', async (e) => {
    e.preventDefault();
    const appointment_id = document.getElementById('record-appointment-id').value;
    const diagnosis = document.getElementById('record-diagnosis').value;
    const notes = document.getElementById('record-notes').value;
    try {
        await axios.post(`${API_URL}/medical_records`, { appointment_id, diagnosis, notes });
        alert('Medical record saved successfully!');
        document.getElementById('form-record').reset();
        refreshDoctor();
    } catch (e2) {
        alert(e2.response?.data?.message || 'Failed to save record. Ensure the appointment ID is correct and assigned to you.');
    }
});

document.getElementById('form-prescription').addEventListener('submit', async (e) => {
    e.preventDefault();
    const record_id = document.getElementById('presc-record-id').value;
    const medication = document.getElementById('presc-medication').value;
    const dosage = document.getElementById('presc-dosage').value;
    const instructions = document.getElementById('presc-instructions').value;
    try {
        await axios.post(`${API_URL}/prescriptions`, { record_id, medication, dosage, instructions });
        alert('Prescription issued successfully!');
        document.getElementById('form-prescription').reset();
        refreshDoctor();
    } catch (e2) {
        alert(e2.response?.data?.message || 'Failed to issue prescription. Ensure the record ID is correct.');
    }
});

async function deleteDoctor(id) {
    if (confirm('Are you sure you want to delete this doctor and their associated account?')) {
        try {
            await axios.delete(`${API_URL}/admin/doctors/${id}`);
            refreshAdmin();
        } catch (error) {
            alert('Failed to delete doctor');
        }
    }
}

function openEditDoctor(id) {
    const doctor = adminDoctorsList.find(d => d.id === id);
    if (!doctor) return;
    document.getElementById('edit-doc-id').value = doctor.id;
    document.getElementById('edit-doc-name').value = doctor.name;
    document.getElementById('edit-doc-spec').value = doctor.specialization;
    document.getElementById('edit-doc-availability').value = doctor.availability || '';
    document.getElementById('edit-doc-username').value = doctor.username || '';
    document.getElementById('edit-doc-password').value = '';
    
    const modal = new bootstrap.Modal(document.getElementById('modalEditDoctor'));
    modal.show();
}

document.getElementById('form-edit-doctor').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('edit-doc-id').value;
    const data = {
        name: document.getElementById('edit-doc-name').value,
        specialization: document.getElementById('edit-doc-spec').value,
        availability: document.getElementById('edit-doc-availability').value,
        username: document.getElementById('edit-doc-username').value,
        password: document.getElementById('edit-doc-password').value
    };
    
    try {
        await axios.patch(`${API_URL}/admin/doctors/${id}`, data);
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalEditDoctor'));
        modal.hide();
        refreshAdmin();
    } catch (e) {
        alert(e.response?.data?.message || 'Update failed');
    }
});

document.getElementById('form-create-doctor').addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('doc-name').value;
    const email = document.getElementById('doc-email').value;
    const specialization = document.getElementById('doc-spec').value;
    const availability = document.getElementById('doc-availability').value;
    const username = document.getElementById('doc-username').value;
    const password = document.getElementById('doc-password').value;

    try {
        await axios.post(`${API_URL}/admin/doctors`, { name, email, specialization, availability, username, password });
        alert('Doctor created successfully');
        e.target.reset();
        refreshAdmin();
    } catch (error) {
        alert(error.response?.data?.message || 'Failed to create doctor');
    }
});

window.addEventListener('load', init);
