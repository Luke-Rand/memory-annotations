// Global Application State
let appConfig = {
    target_directory: '',
    mode: 'scan',
    has_rawpy: false
};
let imagesList = [];
let activeImageIndex = -1;
let currentTags = [];
let isFormDirty = false;
let hotFolderLastId = 0;
let pollingActive = false;

// DOM Elements
const dirInput = document.getElementById('dir-input');
const btnSaveConfig = document.getElementById('btn-save-config');
const modeScanBtn = document.getElementById('mode-scan');
const modeHotBtn = document.getElementById('mode-hotfolder');
const imageCountBadge = document.getElementById('image-count');
const searchInput = document.getElementById('search-input');
const imageListContainer = document.getElementById('image-list');

const viewerPlaceholder = document.getElementById('viewer-placeholder');
const imageLoader = document.getElementById('image-loader');
const activeImage = document.getElementById('active-image');
const overlayInfo = document.getElementById('image-overlay-info');
const overlayFilename = document.getElementById('overlay-filename');
const overlayResolution = document.getElementById('overlay-resolution');

const statusIndicator = document.getElementById('status-indicator');
const annotationForm = document.getElementById('annotation-form');
const inputSubject = document.getElementById('input-subject');
const inputDate = document.getElementById('input-date');
const inputLocation = document.getElementById('input-location');
const inputDescription = document.getElementById('input-description');
const tagInputField = document.getElementById('tag-input-field');
const tagsContainer = document.getElementById('tags-container');
const customFieldsContainer = document.getElementById('custom-fields-container');
const btnAddCustomField = document.getElementById('btn-add-custom-field');
const btnReset = document.getElementById('btn-reset');
const btnSave = document.getElementById('btn-save');
const toastContainer = document.getElementById('toast-container');

// Startup Initialization
document.addEventListener('DOMContentLoaded', () => {
    loadConfig();
    setupEventListeners();
});

// Toast system
function showToast(title, message, type = 'info', actionCallback = null, actionText = '') {
    const toast = document.createElement('div');
    toast.className = 'toast';
    
    let icon = 'fa-info-circle';
    if (type === 'success') icon = 'fa-circle-check';
    if (type === 'warning') icon = 'fa-triangle-exclamation';
    if (type === 'error') icon = 'fa-circle-xmark';
    
    toast.innerHTML = `
        <div class="toast-header">
            <span class="toast-title ${type}">
                <i class="fa-solid ${icon}"></i> ${title}
            </span>
            <button class="toast-close"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div class="toast-body">${message}</div>
    `;
    
    if (actionCallback && actionText) {
        const actionBtn = document.createElement('button');
        actionBtn.className = 'toast-action';
        actionBtn.innerText = actionText;
        actionBtn.addEventListener('click', () => {
            actionCallback();
            toast.classList.add('removing');
            setTimeout(() => toast.remove(), 300);
        });
        toast.appendChild(actionBtn);
    }
    
    toast.querySelector('.toast-close').addEventListener('click', () => {
        toast.classList.add('removing');
        setTimeout(() => toast.remove(), 300);
    });
    
    toastContainer.appendChild(toast);
    
    // Auto-remove after 6 seconds if no interactive action is required
    if (!actionCallback) {
        setTimeout(() => {
            if (toast.parentNode) {
                toast.classList.add('removing');
                setTimeout(() => toast.remove(), 300);
            }
        }, 6000);
    }
}

// Fetch Configurations
async function loadConfig() {
    try {
        const res = await fetch('/api/config');
        const data = await res.json();
        appConfig = data;
        
        dirInput.value = appConfig.target_directory;
        updateModeUI(appConfig.mode);
        
        if (!appConfig.has_rawpy) {
            showToast('RAW Support Muted', 'rawpy is not installed on this system. Canon CR3 images cannot be loaded or processed.', 'warning');
        }
        
        if (appConfig.target_directory) {
            loadImages();
            if (appConfig.mode === 'hotfolder') {
                startHotFolderPolling();
            }
        }
    } catch (err) {
        showToast('Connection Error', 'Failed to communicate with local server.', 'error');
    }
}

// Save configuration updates
async function saveConfig(directory, mode) {
    try {
        const res = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target_directory: directory, mode })
        });
        const data = await res.json();
        
        if (res.ok) {
            appConfig = data.config;
            showToast('Config Saved', 'Directory and mode settings updated.', 'success');
            loadImages();
            
            if (appConfig.mode === 'hotfolder') {
                startHotFolderPolling();
            } else {
                stopHotFolderPolling();
            }
        } else {
            showToast('Config Error', data.error || 'Failed to save configuration.', 'error');
        }
    } catch (err) {
        showToast('Connection Error', 'Failed to communicate with local server.', 'error');
    }
}

function updateModeUI(activeMode) {
    if (activeMode === 'hotfolder') {
        modeHotBtn.classList.add('active');
        modeScanBtn.classList.remove('active');
    } else {
        modeScanBtn.classList.add('active');
        modeHotBtn.classList.remove('active');
    }
}

// Fetch file listing from backend
async function loadImages(autoSelectFile = null) {
    try {
        const res = await fetch('/api/images');
        if (!res.ok) throw new Error('Failed to load images');
        
        imagesList = await res.json();
        renderImageList(autoSelectFile);
    } catch (err) {
        showToast('Scanner Error', 'Failed to read files in target directory.', 'error');
    }
}

// Render image items in the sidebar browser
function renderImageList(autoSelectFile = null) {
    imageCountBadge.innerText = `${imagesList.length} files`;
    
    if (imagesList.length === 0) {
        imageListContainer.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-folder-closed"></i>
                <p>No valid images found (.jpg, .jpeg, .cr3)</p>
            </div>
        `;
        closeActiveImage();
        return;
    }
    
    const query = searchInput.value.toLowerCase().trim();
    const filtered = imagesList.map((img, idx) => ({ ...img, originalIndex: idx }))
                               .filter(img => img.name.toLowerCase().includes(query));
                               
    if (filtered.length === 0) {
        imageListContainer.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-magnifying-glass"></i>
                <p>No matching images</p>
            </div>
        `;
        return;
    }
    
    imageListContainer.innerHTML = '';
    filtered.forEach(img => {
        const div = document.createElement('div');
        div.className = `image-item ${img.originalIndex === activeImageIndex ? 'active' : ''}`;
        div.dataset.index = img.originalIndex;
        
        const badgeClass = `badge-${img.type}`;
        const statusBadge = img.annotated 
            ? '<span class="status-badge annotated"><i class="fa-solid fa-circle-check"></i></span>'
            : '<span class="status-badge pending"><i class="fa-regular fa-circle"></i></span>';
            
        div.innerHTML = `
            <div class="image-item-info">
                <span class="image-item-name" title="${img.name}">${img.name}</span>
                <div class="image-item-meta">
                    <span class="file-badge ${badgeClass}">${img.type}</span>
                </div>
            </div>
            ${statusBadge}
        `;
        
        div.addEventListener('click', () => {
            selectImage(img.originalIndex);
        });
        
        imageListContainer.appendChild(div);
    });
    
    // Auto-select flow
    if (autoSelectFile) {
        const selectIdx = imagesList.findIndex(img => img.name === autoSelectFile);
        if (selectIdx !== -1) {
            selectImage(selectIdx);
            scrollToActiveItem();
        }
    } else if (activeImageIndex >= imagesList.length) {
        selectImage(imagesList.length - 1);
    } else if (activeImageIndex === -1 && imagesList.length > 0) {
        // Don't auto-load first image immediately on start, let the user select it, or auto-load if desired
        // Select first item
        selectImage(0);
    } else if (activeImageIndex !== -1) {
        // Sync visual active state
        const items = imageListContainer.querySelectorAll('.image-item');
        items.forEach(item => {
            if (parseInt(item.dataset.index) === activeImageIndex) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    }
}

function scrollToActiveItem() {
    const activeItem = imageListContainer.querySelector('.image-item.active');
    if (activeItem) {
        activeItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function closeActiveImage() {
    activeImageIndex = -1;
    activeImage.classList.add('hidden');
    overlayInfo.classList.add('hidden');
    viewerPlaceholder.classList.remove('hidden');
    imageLoader.classList.add('hidden');
    disableForm();
}

// Select and load an image
async function selectImage(index) {
    if (index < 0 || index >= imagesList.length) return;
    
    // Check for unsaved changes before navigating
    if (isFormDirty) {
        const confirmLeave = confirm('You have unsaved changes. Discard changes and navigate?');
        if (!confirmLeave) return;
    }
    
    activeImageIndex = index;
    isFormDirty = false;
    
    // Highlight item in sidebar
    const items = imageListContainer.querySelectorAll('.image-item');
    items.forEach(item => {
        if (parseInt(item.dataset.index) === index) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
    
    const image = imagesList[index];
    
    // Show loading state
    viewerPlaceholder.classList.add('hidden');
    activeImage.classList.add('hidden');
    overlayInfo.classList.add('hidden');
    imageLoader.classList.remove('hidden');
    
    // Load metadata and image source in parallel
    const metadataPromise = fetch(`/api/annotation?path=${encodeURIComponent(image.path)}`).then(r => r.json());
    
    // Set image source
    activeImage.src = `/api/image?path=${encodeURIComponent(image.path)}`;
    
    // When image finishes loading
    activeImage.onload = () => {
        imageLoader.classList.add('hidden');
        activeImage.classList.remove('hidden');
        overlayFilename.innerText = image.name;
        overlayResolution.innerText = image.type.toUpperCase();
        overlayResolution.className = `badge file-badge badge-${image.type}`;
        overlayInfo.classList.remove('hidden');
    };
    
    activeImage.onerror = () => {
        imageLoader.classList.add('hidden');
        viewerPlaceholder.classList.remove('hidden');
        showToast('Image Load Error', `Failed to load image preview for ${image.name}`, 'error');
    };
    
    try {
        const meta = await metadataPromise;
        populateForm(meta, image.annotated);
    } catch (err) {
        showToast('Metadata Error', 'Failed to retrieve image sidecar annotations.', 'error');
    }
}

// Fill out the metadata panel fields
function populateForm(meta, isAnnotated) {
    enableForm();
    
    inputSubject.value = meta.subject || '';
    inputDate.value = meta.date || '';
    inputLocation.value = meta.location || '';
    inputDescription.value = meta.description || '';
    
    // Set Tags
    currentTags = meta.tags || [];
    renderTags();
    
    // Set Custom Fields
    customFieldsContainer.innerHTML = '';
    const custom = meta.custom || {};
    Object.entries(custom).forEach(([key, value]) => {
        addCustomFieldRow(key, value);
    });
    
    setFormDirtyState(false);
    updateStatusIndicator(isAnnotated);
}

function enableForm() {
    annotationForm.removeAttribute('disabled');
    inputSubject.disabled = false;
    inputDate.disabled = false;
    inputLocation.disabled = false;
    inputDescription.disabled = false;
    tagInputField.disabled = false;
    btnAddCustomField.disabled = false;
    btnReset.disabled = false;
    btnSave.disabled = false;
}

function disableForm() {
    annotationForm.setAttribute('disabled', 'true');
    inputSubject.disabled = true;
    inputDate.disabled = true;
    inputLocation.disabled = true;
    inputDescription.disabled = true;
    tagInputField.disabled = true;
    btnAddCustomField.disabled = true;
    btnReset.disabled = true;
    btnSave.disabled = true;
    
    inputSubject.value = '';
    inputDate.value = '';
    inputLocation.value = '';
    inputDescription.value = '';
    tagsContainer.innerHTML = '';
    customFieldsContainer.innerHTML = '';
    
    statusIndicator.className = 'status-indicator pending';
    statusIndicator.innerHTML = '<i class="fa-solid fa-circle-dot"></i> Unsaved';
}

function setFormDirtyState(dirty) {
    isFormDirty = dirty;
    if (dirty) {
        statusIndicator.className = 'status-indicator pending';
        statusIndicator.innerHTML = '<i class="fa-solid fa-circle-dot"></i> Unsaved changes';
    }
}

function updateStatusIndicator(isSaved) {
    if (isSaved) {
        statusIndicator.className = 'status-indicator saved';
        statusIndicator.innerHTML = '<i class="fa-solid fa-circle-check"></i> Annotated';
    } else {
        statusIndicator.className = 'status-indicator pending';
        statusIndicator.innerHTML = '<i class="fa-solid fa-circle-dot"></i> Unsaved';
    }
}

// Tag chips rendering
function renderTags() {
    tagsContainer.innerHTML = '';
    currentTags.forEach((tag, idx) => {
        const chip = document.createElement('span');
        chip.className = 'tag-chip';
        chip.innerHTML = `${tag} <i class="fa-solid fa-xmark" data-index="${idx}"></i>`;
        
        chip.querySelector('i').addEventListener('click', (e) => {
            const removeIdx = parseInt(e.target.dataset.index);
            currentTags.splice(removeIdx, 1);
            renderTags();
            setFormDirtyState(true);
        });
        
        tagsContainer.appendChild(chip);
    });
}

// Custom Key-Value attributes
function addCustomFieldRow(key = '', value = '') {
    const row = document.createElement('div');
    row.className = 'custom-field-row';
    
    row.innerHTML = `
        <input type="text" class="custom-key-input" placeholder="Field name" value="${key}" autocomplete="off">
        <input type="text" class="custom-value-input" placeholder="Value" value="${value}" autocomplete="off">
        <button type="button" class="btn-remove-custom" title="Remove field"><i class="fa-solid fa-trash"></i></button>
    `;
    
    row.querySelector('.btn-remove-custom').addEventListener('click', () => {
        row.remove();
        setFormDirtyState(true);
    });
    
    row.querySelectorAll('input').forEach(input => {
        input.addEventListener('input', () => setFormDirtyState(true));
    });
    
    customFieldsContainer.appendChild(row);
}

// Save action
async function saveAnnotations() {
    if (activeImageIndex === -1) return;
    
    const image = imagesList[activeImageIndex];
    
    // Collect Custom Fields
    const custom = {};
    const rows = customFieldsContainer.querySelectorAll('.custom-field-row');
    rows.forEach(row => {
        const key = row.querySelector('.custom-key-input').value.trim();
        const val = row.querySelector('.custom-value-input').value.trim();
        if (key) {
            custom[key] = val;
        }
    });
    
    const payload = {
        subject: inputSubject.value,
        date: inputDate.value,
        location: inputLocation.value,
        description: inputDescription.value,
        tags: currentTags,
        custom: custom
    };
    
    try {
        const res = await fetch(`/api/annotation?path=${encodeURIComponent(image.path)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (res.ok) {
            setFormDirtyState(false);
            updateStatusIndicator(true);
            showToast('Saved', `Metadata sidecar saved for ${image.name}`, 'success');
            
            // Mark as annotated in local list and trigger list refresh
            imagesList[activeImageIndex].annotated = true;
            renderImageList();
        } else {
            const data = await res.json();
            showToast('Save Error', data.error || 'Failed to save metadata.', 'error');
        }
    } catch (err) {
        showToast('Connection Error', 'Failed to save annotations to server.', 'error');
    }
}

// Reset form
function resetForm() {
    if (activeImageIndex === -1) return;
    selectImage(activeImageIndex);
}

// Setup Event Listeners
function setupEventListeners() {
    // Config Save
    btnSaveConfig.addEventListener('click', () => {
        saveConfig(dirInput.value.trim(), appConfig.mode);
    });
    
    // Mode switches
    modeScanBtn.addEventListener('click', () => {
        if (appConfig.mode !== 'scan') {
            saveConfig(dirInput.value.trim(), 'scan');
        }
    });
    
    modeHotBtn.addEventListener('click', () => {
        if (appConfig.mode !== 'hotfolder') {
            saveConfig(dirInput.value.trim(), 'hotfolder');
        }
    });
    
    // Search filter
    searchInput.addEventListener('input', () => {
        renderImageList();
    });
    
    // Form Inputs Dirty State tracking
    [inputSubject, inputDate, inputLocation, inputDescription].forEach(input => {
        input.addEventListener('input', () => setFormDirtyState(true));
    });
    
    // Tags Manager Input
    tagInputField.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ',') {
            e.preventDefault();
            const val = tagInputField.value.replace(/,/g, '').trim();
            if (val && !currentTags.includes(val)) {
                currentTags.push(val);
                renderTags();
                setFormDirtyState(true);
            }
            tagInputField.value = '';
        }
    });
    
    // Custom Fields
    btnAddCustomField.addEventListener('click', () => {
        addCustomFieldRow();
        setFormDirtyState(true);
    });
    
    // Form Actions
    annotationForm.addEventListener('submit', (e) => {
        e.preventDefault();
        saveAnnotations();
    });
    
    btnReset.addEventListener('click', () => {
        resetForm();
    });
    
    // Keybinds (arrows / shortcuts)
    document.addEventListener('keydown', (e) => {
        // Prevent action when user is typing in forms or text fields
        const isTyping = ['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName);
        
        // Save shortcut Ctrl+S
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
            e.preventDefault();
            saveAnnotations();
            return;
        }
        
        if (isTyping) {
            // Let Esc key blur form fields to return focus to general layout
            if (e.key === 'Escape') {
                document.activeElement.blur();
            }
            return;
        }
        
        if (e.key === 'ArrowRight') {
            e.preventDefault();
            navigateIndex(1);
        } else if (e.key === 'ArrowLeft') {
            e.preventDefault();
            navigateIndex(-1);
        }
    });
}

function navigateIndex(direction) {
    if (imagesList.length === 0) return;
    let nextIdx = activeImageIndex + direction;
    if (nextIdx >= imagesList.length) nextIdx = 0;
    if (nextIdx < 0) nextIdx = imagesList.length - 1;
    selectImage(nextIdx);
    
    // Scroll active item into view
    setTimeout(scrollToActiveItem, 50);
}

// Hot folder long-polling loop
async function startHotFolderPolling() {
    if (pollingActive) return;
    pollingActive = true;
    console.log('Started Hot Folder long-polling loop');
    
    // Initialize hot folder ID to ignore pre-existing files on first switch,
    // or set to 0 to catch everything from this session.
    // Let's set it to retrieve currently tracked session items, or start fresh.
    try {
        const res = await fetch(`/api/hotfolder/events?since=0`);
        if (res.ok) {
            const events = await res.json();
            hotFolderLastId = events.length > 0 ? Math.max(...events.map(e => e.id)) : 0;
        }
    } catch (err) {
        console.error('Failed to initialize hotfolder pointer:', err);
    }
    
    while (pollingActive && appConfig.mode === 'hotfolder') {
        try {
            const res = await fetch(`/api/hotfolder/events?since=${hotFolderLastId}`);
            if (!res.ok) {
                // Wait a bit before retrying on server errors to avoid infinite spam
                await new Promise(r => setTimeout(r, 2000));
                continue;
            }
            
            const newEvents = await res.json();
            if (newEvents && newEvents.length > 0) {
                // Update tracker
                hotFolderLastId = Math.max(hotFolderLastId, ...newEvents.map(e => e.id));
                
                // Show notification for each file
                newEvents.forEach(evt => {
                    showToast(
                        'New Image Detected',
                        `File <strong>${evt.name}</strong> landed in the hot folder.`,
                        'info',
                        () => {
                            // On toast action click: reload images list and select this file!
                            loadImages(evt.name);
                        },
                        'Annotate Slide'
                    );
                });
                
                // Reload image list in sidebar to reflect new arrivals
                loadImages();
            }
        } catch (err) {
            console.error('Polling error:', err);
            await new Promise(r => setTimeout(r, 3000)); // Delay retry
        }
    }
    
    pollingActive = false;
}

function stopHotFolderPolling() {
    pollingActive = false;
    console.log('Stopped Hot Folder polling loop');
}
