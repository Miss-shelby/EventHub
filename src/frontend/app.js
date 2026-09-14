// EventHub Frontend Testing Dashboard Application Logic
const API_BASE = '/api/v1/events';

// Global state
let allEvents = [];
let createFiles = [];
let editFiles = [];
let uploadModalFiles = [];

// DOM Elements
const eventsContainer = document.getElementById('events-container');
const searchInput = document.getElementById('search-input');
const categoryFilter = document.getElementById('category-filter');
const statusFilter = document.getElementById('status-filter');
const toastContainer = document.getElementById('toast-container');

// Stats Elements
const statTotal = document.getElementById('stat-total-events');
const statUpcoming = document.getElementById('stat-upcoming-events');
const statCapacity = document.getElementById('stat-total-capacity');
const statRegistered = document.getElementById('stat-total-registered');

// Modals
const createModal = document.getElementById('create-modal');
const editModal = document.getElementById('edit-modal');
const uploadModal = document.getElementById('upload-modal');
const deleteModal = document.getElementById('delete-modal');

// ---------------------------------------------------------------------------------
// INITIALIZATION
// ---------------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  setupEventListeners();
  setupAllDropzones();
  loadEvents();
});

function setupEventListeners() {
  // Filters & Search (triggers live backend query filtering)
  let debounceTimeout;
  searchInput.addEventListener('input', () => {
    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(loadEvents, 300);
  });
  categoryFilter.addEventListener('change', loadEvents);
  statusFilter.addEventListener('change', loadEvents);

  // Modal Triggers & Closers
  document.getElementById('btn-open-create-modal').addEventListener('click', () => {
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('create-date').value = today;
    createFiles = [];
    document.getElementById('create-upload-previews').innerHTML = '';
    document.getElementById('create-image-file-input').value = '';
    openModal(createModal);
  });

  document.querySelectorAll('[data-close-modal]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const modalId = e.currentTarget.getAttribute('data-close-modal');
      closeModal(document.getElementById(modalId));
    });
  });

  // Close modals when clicking backdrop
  document.querySelectorAll('.modal-overlay').forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal(modal);
    });
  });

  // Form Submissions
  document.getElementById('create-event-form').addEventListener('submit', handleCreateEvent);
  document.getElementById('edit-event-form').addEventListener('submit', handleUpdateEvent);
  document.getElementById('upload-image-form').addEventListener('submit', handleStandaloneUploadImages);
  document.getElementById('btn-confirm-delete').addEventListener('click', handleConfirmDelete);
}

// ---------------------------------------------------------------------------------
// DROPZONE SETUP HELPERS
// ---------------------------------------------------------------------------------
function setupAllDropzones() {
  // 1. Create Modal Dropzone
  attachDropzoneEvents('create-dropzone', 'create-image-file-input', (files) => {
    createFiles = Array.from(files);
    renderPreviews(createFiles, 'create-upload-previews');
  });

  // 2. Edit Modal Dropzone
  attachDropzoneEvents('edit-dropzone', 'edit-image-file-input', (files) => {
    editFiles = Array.from(files);
    renderPreviews(editFiles, 'edit-upload-previews');
  });

  // 3. Standalone Upload Modal Dropzone
  attachDropzoneEvents('image-dropzone', 'image-file-input', (files) => {
    uploadModalFiles = Array.from(files);
    renderPreviews(uploadModalFiles, 'upload-previews');
  });
}

function attachDropzoneEvents(dropzoneId, inputId, onFilesSelected) {
  const dropzone = document.getElementById(dropzoneId);
  const fileInput = document.getElementById(inputId);
  if (!dropzone || !fileInput) return;

  dropzone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (e) => onFilesSelected(e.target.files));

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });

  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    onFilesSelected(e.dataTransfer.files);
  });
}

function renderPreviews(files, containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = '';

  files.forEach(file => {
    if (!file.type.startsWith('image/')) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = document.createElement('img');
      img.src = e.target.result;
      img.className = 'preview-thumb';
      img.title = file.name;
      container.appendChild(img);
    };
    reader.readAsDataURL(file);
  });
}

// ---------------------------------------------------------------------------------
// MODAL HELPERS
// ---------------------------------------------------------------------------------
function openModal(modal) {
  modal.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeModal(modal) {
  modal.classList.remove('active');
  document.body.style.overflow = '';
}

// ---------------------------------------------------------------------------------
// TOAST NOTIFICATIONS
// ---------------------------------------------------------------------------------
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️';
  toast.innerHTML = `<span>${icon}</span><div>${message}</div>`;
  
  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// ---------------------------------------------------------------------------------
// API CALLS & CRUD
// ---------------------------------------------------------------------------------

// 1. GET ALL EVENTS (LIVE FROM NEON POSTGRESQL WITH BACKEND FILTERING)
async function loadEvents() {
  const dbStatusText = document.getElementById('db-status-text');
  try {
    const params = new URLSearchParams();
    const query = searchInput.value.trim();
    const category = categoryFilter.value;
    const status = statusFilter.value;

    if (query) params.append('name', query);
    if (category && category !== 'ALL') params.append('category', category);
    if (status && status !== 'ALL') params.append('status', status);

    const queryString = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${API_BASE}/${queryString}`);
    if (!res.ok) throw new Error(`HTTP Error: ${res.status}`);
    
    allEvents = await res.json();
    if (dbStatusText) {
      dbStatusText.textContent = `Connected: ${allEvents.length} Live Events Loaded`;
    }
    
    updateStats(allEvents);
    renderFilteredEvents();
  } catch (err) {
    console.error('Error fetching events:', err);
    if (dbStatusText) dbStatusText.textContent = 'Database Connection Error';
    showToast(`Failed to load events: ${err.message}`, 'error');
    eventsContainer.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">⚠️</div>
        <h3 class="empty-title">Error Connecting to Neon PostgreSQL</h3>
        <p class="empty-text">${err.message}</p>
        <button class="btn btn-primary" onclick="loadEvents()">Retry Connection</button>
      </div>
    `;
  }
}

// 2. CREATE EVENT (POST JSON + Optional Immediate Image Upload)
async function handleCreateEvent(e) {
  e.preventDefault();
  const btn = document.getElementById('btn-submit-create');
  btn.disabled = true;
  btn.textContent = 'Creating in Neon DB...';

  const payload = {
    name: document.getElementById('create-name').value.trim(),
    description: document.getElementById('create-description').value.trim(),
    category: document.getElementById('create-category').value,
    status: document.getElementById('create-status').value,
    date: document.getElementById('create-date').value,
    event_time: document.getElementById('create-time').value,
    location: document.getElementById('create-location').value.trim(),
    organizer: document.getElementById('create-organizer').value.trim(),
    price: parseInt(document.getElementById('create-price').value, 10) || 0,
    capacity: parseInt(document.getElementById('create-capacity').value, 10) || 1,
    registered: parseInt(document.getElementById('create-registered').value, 10) || 0,
    images: []
  };

  try {
    const res = await fetch(`${API_BASE}/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const errorData = await res.json();
      throw new Error(errorData.detail ? JSON.stringify(errorData.detail) : 'Failed to create event');
    }

    const createdEvent = await res.json();

    // If images were selected in dropzone, upload them immediately to this event
    if (createFiles.length > 0) {
      btn.textContent = 'Uploading images...';
      const formData = new FormData();
      createFiles.forEach(file => formData.append('files', file));

      const uploadRes = await fetch(`${API_BASE}/${createdEvent.uid}/images`, {
        method: 'POST',
        body: formData
      });

      if (!uploadRes.ok) {
        showToast('Event created, but some image uploads failed.', 'error');
      }
    }

    showToast(`Event "${createdEvent.name}" created live in Neon DB!`, 'success');
    closeModal(createModal);
    document.getElementById('create-event-form').reset();
    createFiles = [];
    document.getElementById('create-upload-previews').innerHTML = '';
    await loadEvents();
  } catch (err) {
    showToast(`Create Error: ${err.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Create Event';
  }
}

// 3. EDIT EVENT (PATCH + Optional Image Upload)
function openEditModal(eventUid) {
  const event = allEvents.find(e => e.uid === eventUid);
  if (!event) return;

  document.getElementById('edit-uid').value = event.uid;
  document.getElementById('edit-name').value = event.name || '';
  document.getElementById('edit-description').value = event.description || '';
  document.getElementById('edit-category').value = event.category || 'Technology';
  document.getElementById('edit-status').value = event.status || 'upcoming';
  
  if (event.date) {
    const rawDate = event.date.split('T')[0];
    document.getElementById('edit-date').value = rawDate;
  } else {
    document.getElementById('edit-date').value = '';
  }

  document.getElementById('edit-time').value = event.event_time || '09:00:00';
  document.getElementById('edit-location').value = event.location || '';
  document.getElementById('edit-organizer').value = event.organizer || '';
  document.getElementById('edit-price').value = event.price || 0;
  document.getElementById('edit-capacity').value = event.capacity || 100;
  document.getElementById('edit-registered').value = event.registered || 0;

  // Render current images
  const currentImagesContainer = document.getElementById('edit-current-images');
  currentImagesContainer.innerHTML = '';
  const images = Array.isArray(event.images) ? event.images : [];
  if (images.length === 0) {
    currentImagesContainer.innerHTML = '<span style="color: var(--text-muted); font-size: 0.8125rem;">No images currently attached.</span>';
  } else {
    images.forEach(imgUrl => {
      const img = document.createElement('img');
      img.src = imgUrl;
      img.className = 'preview-thumb';
      currentImagesContainer.appendChild(img);
    });
  }

  // Reset new edit file upload previews
  editFiles = [];
  document.getElementById('edit-upload-previews').innerHTML = '';
  document.getElementById('edit-image-file-input').value = '';

  openModal(editModal);
}

async function handleUpdateEvent(e) {
  e.preventDefault();
  const btn = document.getElementById('btn-submit-edit');
  btn.disabled = true;
  btn.textContent = 'Saving to Neon DB...';

  const uid = document.getElementById('edit-uid').value;
  const payload = {
    name: document.getElementById('edit-name').value.trim(),
    description: document.getElementById('edit-description').value.trim(),
    category: document.getElementById('edit-category').value,
    status: document.getElementById('edit-status').value,
    location: document.getElementById('edit-location').value.trim(),
    organizer: document.getElementById('edit-organizer').value.trim(),
    price: parseInt(document.getElementById('edit-price').value, 10),
    capacity: parseInt(document.getElementById('edit-capacity').value, 10),
    registered: parseInt(document.getElementById('edit-registered').value, 10)
  };

  const editDate = document.getElementById('edit-date').value;
  if (editDate) payload.date = editDate;

  const editTime = document.getElementById('edit-time').value;
  if (editTime) payload.event_time = editTime;

  try {
    const res = await fetch(`${API_BASE}/${uid}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const errorData = await res.json();
      throw new Error(errorData.detail ? JSON.stringify(errorData.detail) : 'Update failed');
    }

    // If new image files were added during edit, upload them
    if (editFiles.length > 0) {
      btn.textContent = 'Uploading new images...';
      const formData = new FormData();
      editFiles.forEach(file => formData.append('files', file));

      const uploadRes = await fetch(`${API_BASE}/${uid}/images`, {
        method: 'POST',
        body: formData
      });

      if (!uploadRes.ok) {
        showToast('Event updated, but image upload failed.', 'error');
      }
    }

    showToast('Event updated live in Neon DB!', 'success');
    closeModal(editModal);
    await loadEvents();
  } catch (err) {
    showToast(`Update Error: ${err.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Save Changes';
  }
}

// 4. DELETE EVENT (DELETE)
function openDeleteModal(eventUid, eventName) {
  document.getElementById('delete-event-uid').value = eventUid;
  document.getElementById('delete-event-name').textContent = eventName;
  openModal(deleteModal);
}

async function handleConfirmDelete() {
  const uid = document.getElementById('delete-event-uid').value;
  const btn = document.getElementById('btn-confirm-delete');
  btn.disabled = true;
  btn.textContent = 'Deleting from Neon DB...';

  try {
    const res = await fetch(`${API_BASE}/${uid}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete event');

    showToast('Event permanently deleted from Neon PostgreSQL!', 'success');
    closeModal(deleteModal);
    await loadEvents();
  } catch (err) {
    showToast(`Delete Error: ${err.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Delete Permanently';
  }
}

// 5. STANDALONE UPLOAD IMAGES MODAL (POST Multipart)
function openUploadModal(eventUid, eventName) {
  document.getElementById('upload-event-uid').value = eventUid;
  document.getElementById('upload-event-title').textContent = eventName;
  uploadModalFiles = [];
  document.getElementById('upload-previews').innerHTML = '';
  document.getElementById('image-file-input').value = '';
  openModal(uploadModal);
}

async function handleStandaloneUploadImages(e) {
  e.preventDefault();
  const uid = document.getElementById('upload-event-uid').value;
  if (!uploadModalFiles.length) {
    showToast('Please select at least one image file to upload.', 'error');
    return;
  }

  const btn = document.getElementById('btn-submit-upload');
  btn.disabled = true;
  btn.textContent = 'Uploading & Saving...';

  const formData = new FormData();
  uploadModalFiles.forEach(file => {
    formData.append('files', file);
  });

  try {
    const res = await fetch(`${API_BASE}/${uid}/images`, {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      const errorData = await res.json();
      throw new Error(errorData.detail ? JSON.stringify(errorData.detail) : 'Upload failed');
    }

    showToast('Images uploaded & saved to Neon PostgreSQL!', 'success');
    closeModal(uploadModal);
    await loadEvents();
  } catch (err) {
    showToast(`Upload Error: ${err.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Upload Images';
  }
}

// ---------------------------------------------------------------------------------
// RENDERING & STATS
// ---------------------------------------------------------------------------------
function updateStats(events) {
  statTotal.textContent = events.length;
  
  const upcomingCount = events.filter(e => e.status && e.status.toLowerCase() === 'upcoming').length;
  statUpcoming.textContent = upcomingCount;

  const totalCap = events.reduce((acc, curr) => acc + (curr.capacity || 0), 0);
  statCapacity.textContent = totalCap.toLocaleString();

  const totalReg = events.reduce((acc, curr) => acc + (curr.registered || 0), 0);
  statRegistered.textContent = totalReg.toLocaleString();
}

function toggleJsonView(uid) {
  const block = document.getElementById(`json-block-${uid}`);
  if (block) {
    block.classList.toggle('open');
  }
}

function renderFilteredEvents() {
  if (allEvents.length === 0) {
    eventsContainer.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📂</div>
        <h3 class="empty-title">No events in database match criteria</h3>
        <p class="empty-text">Click "+ Create New Event" to insert a record into your Neon PostgreSQL database.</p>
      </div>
    `;
    return;
  }

  eventsContainer.innerHTML = allEvents.map(event => createEventCardHTML(event)).join('');
}

function createEventCardHTML(event) {
  const images = Array.isArray(event.images) ? event.images : [];
  const primaryImage = images.length > 0 ? images[0] : null;

  // Format Date & Time
  let formattedDate = event.date || 'TBD';
  if (event.date) {
    try {
      const d = new Date(event.date);
      formattedDate = d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
      formattedDate = event.date;
    }
  }

  const statusClass = `status-${(event.status || 'upcoming').toLowerCase()}`;
  const priceDisplay = event.price > 0 ? `₦${event.price.toLocaleString()}` : '<span class="free-tag">Free</span>';
  
  const capacity = event.capacity || 100;
  const registered = event.registered || 0;
  const percent = Math.min(100, Math.round((registered / capacity) * 100));

  const jsonString = escapeHtml(JSON.stringify(event, null, 2));

  return `
    <article class="event-card" id="event-card-${event.uid}">
      <div class="card-media">
        ${primaryImage ? `
          <img src="${primaryImage}" alt="${escapeHtml(event.name)}" class="card-image" onerror="this.onerror=null; this.parentElement.innerHTML='<div class=\\'image-fallback\\'>🖼️ Image Load Failed</div>'">
        ` : `
          <div class="image-fallback">
            <span style="font-size: 2rem;">🎟️</span>
            <span>No Image Uploaded</span>
          </div>
        `}
        ${images.length > 1 ? `<span class="image-count-badge">📷 +${images.length - 1} more</span>` : ''}
        <span class="status-tag ${statusClass}">${escapeHtml(event.status || 'upcoming')}</span>
      </div>

      <div class="card-body">
        <span class="uuid-badge" title="Neon PostgreSQL Primary Key">UID: ${event.uid}</span>
        <div class="card-category">${escapeHtml(event.category || 'General')}</div>
        <h3 class="card-title">${escapeHtml(event.name || 'Untitled Event')}</h3>
        <p class="card-description">${escapeHtml(event.description || 'No description provided.')}</p>

        <div class="card-meta-list">
          <div class="meta-item">
            <span class="meta-icon">📅</span>
            <span>${formattedDate} at ${event.event_time || '00:00'}</span>
          </div>
          <div class="meta-item">
            <span class="meta-icon">📍</span>
            <span>${escapeHtml(event.location || 'Location TBA')}</span>
          </div>
          <div class="meta-item">
            <span class="meta-icon">👤</span>
            <span>By ${escapeHtml(event.organizer || 'Organizer')}</span>
          </div>
        </div>

        <div class="capacity-box">
          <div class="capacity-labels">
            <span>Attendance (${percent}%)</span>
            <span><strong>${registered}</strong> / ${capacity}</span>
          </div>
          <div class="progress-bar-bg">
            <div class="progress-bar-fill" style="width: ${percent}%;"></div>
          </div>
        </div>

        <div style="margin-bottom: 0.75rem;">
          <button type="button" class="json-viewer-toggle" onclick="toggleJsonView('${event.uid}')">
            { } View Raw Neon JSON
          </button>
          <pre class="raw-json-block" id="json-block-${event.uid}">${jsonString}</pre>
        </div>

        <div class="card-footer">
          <div class="price-tag">${priceDisplay}</div>
          <div class="card-actions">
            <button class="btn btn-secondary btn-icon" title="Upload Images" onclick="openUploadModal('${event.uid}', '${escapeJs(event.name)}')">
              📷
            </button>
            <button class="btn btn-secondary btn-icon" title="Edit Event" onclick="openEditModal('${event.uid}')">
              ✏️
            </button>
            <button class="btn btn-danger btn-icon" title="Delete Event" onclick="openDeleteModal('${event.uid}', '${escapeJs(event.name)}')">
              🗑️
            </button>
          </div>
        </div>
      </div>
    </article>
  `;
}

// Utility to escape HTML to prevent XSS
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function escapeJs(str) {
  if (!str) return '';
  return String(str).replace(/'/g, "\\'").replace(/"/g, '\\"');
}
