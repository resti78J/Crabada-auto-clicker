/**
 * CSV/Excel Merger App - JavaScript Frontend
 * Gestisce l'interattività dell'applicazione
 */

// Stato dell'applicazione
const appState = {
    uploadedFiles: [],
    selectedColumns: [],
    mergedFilePath: null,
    mergedFileName: null
};

// Elementi DOM
const elements = {
    uploadZone: document.getElementById('uploadZone'),
    fileInput: document.getElementById('fileInput'),
    fileList: document.getElementById('fileList'),
    fileItems: document.getElementById('fileItems'),
    clearFilesBtn: document.getElementById('clearFilesBtn'),
    configSection: document.getElementById('configSection'),
    removeDuplicates: document.getElementById('removeDuplicates'),
    autoDetect: document.getElementById('autoDetect'),
    keyColumnsGroup: document.getElementById('keyColumnsGroup'),
    columnsSelect: document.getElementById('columnsSelect'),
    mergeBtn: document.getElementById('mergeBtn'),
    resultsSection: document.getElementById('resultsSection'),
    loadingOverlay: document.getElementById('loadingOverlay'),
    toastContainer: document.getElementById('toastContainer'),
    downloadBtn: document.getElementById('downloadBtn'),
    newMergeBtn: document.getElementById('newMergeBtn'),
    historyHeader: document.getElementById('historyHeader'),
    historyBody: document.getElementById('historyBody'),
    historyList: document.getElementById('historyList')
};

// ============================================
// Funzioni Utility
// ============================================

/**
 * Mostra una notifica toast
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        info: 'fa-info-circle'
    };
    
    toast.innerHTML = `
        <i class="fas ${icons[type]}"></i>
        <span>${message}</span>
    `;
    
    elements.toastContainer.appendChild(toast);
    
    // Rimuovi dopo 4 secondi
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

/**
 * Mostra/nasconde il loading overlay
 */
function setLoading(show) {
    elements.loadingOverlay.classList.toggle('active', show);
}

/**
 * Formatta la dimensione del file
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// ============================================
// Gestione Upload File
// ============================================

/**
 * Inizializza drag & drop
 */
function initDragDrop() {
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        elements.uploadZone.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        elements.uploadZone.addEventListener(eventName, () => {
            elements.uploadZone.classList.add('dragover');
        });
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        elements.uploadZone.addEventListener(eventName, () => {
            elements.uploadZone.classList.remove('dragover');
        });
    });
    
    elements.uploadZone.addEventListener('drop', handleDrop);
}

/**
 * Gestisce il drop dei file
 */
function handleDrop(e) {
    const files = e.dataTransfer.files;
    handleFiles(files);
}

/**
 * Gestisce l'upload dei file
 */
async function handleFiles(files) {
    if (files.length === 0) return;
    
    const formData = new FormData();
    for (const file of files) {
        formData.append('files[]', file);
    }
    
    setLoading(true);
    
    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.error) {
            showToast(data.error, 'error');
            return;
        }
        
        // Aggiungi file allo stato
        appState.uploadedFiles.push(...data.files);
        
        // Mostra errori se presenti
        if (data.errors && data.errors.length > 0) {
            data.errors.forEach(err => showToast(err, 'error'));
        }
        
        showToast(data.message, 'success');
        updateFileList();
        
    } catch (error) {
        showToast('Errore durante l\'upload: ' + error.message, 'error');
    } finally {
        setLoading(false);
    }
}

/**
 * Aggiorna la lista dei file caricati
 */
function updateFileList() {
    if (appState.uploadedFiles.length === 0) {
        elements.fileList.style.display = 'none';
        elements.configSection.style.display = 'none';
        return;
    }
    
    elements.fileList.style.display = 'block';
    elements.configSection.style.display = 'block';
    
    elements.fileItems.innerHTML = appState.uploadedFiles.map((file, index) => `
        <div class="file-item" data-index="${index}">
            <div class="file-item-icon">
                <i class="fas ${file.original_name.endsWith('.csv') ? 'fa-file-csv' : 'fa-file-excel'}"></i>
            </div>
            <div class="file-item-info">
                <div class="file-item-name">${file.original_name}</div>
                <div class="file-item-meta">
                    <span>${file.rows} righe</span> · 
                    <span>${file.columns.length} colonne</span>
                </div>
            </div>
            <button class="file-item-remove" onclick="removeFile(${index})" title="Rimuovi file">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `).join('');
    
    // Aggiorna le colonne disponibili per la deduplicazione
    loadCommonColumns();
}

/**
 * Rimuove un file dalla lista
 */
function removeFile(index) {
    appState.uploadedFiles.splice(index, 1);
    updateFileList();
    showToast('File rimosso', 'info');
}

/**
 * Pulisce tutti i file
 */
async function clearAllFiles() {
    if (appState.uploadedFiles.length === 0) return;
    
    try {
        await fetch('/clear', { method: 'POST' });
        appState.uploadedFiles = [];
        updateFileList();
        elements.resultsSection.style.display = 'none';
        showToast('Tutti i file sono stati rimossi', 'info');
    } catch (error) {
        showToast('Errore durante la pulizia', 'error');
    }
}

// ============================================
// Gestione Configurazione
// ============================================

/**
 * Carica le colonne comuni tra tutti i file
 */
async function loadCommonColumns() {
    if (appState.uploadedFiles.length === 0) return;
    
    try {
        const response = await fetch('/columns', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                files: appState.uploadedFiles.map(f => f.filepath)
            })
        });
        
        const data = await response.json();
        
        if (data.columns && data.columns.length > 0) {
            renderColumnChips(data.columns, data.suggested);
        }
        
    } catch (error) {
        console.error('Errore caricamento colonne:', error);
    }
}

/**
 * Renderizza i chip delle colonne selezionabili
 */
function renderColumnChips(columns, suggested) {
    elements.columnsSelect.innerHTML = columns.map(col => {
        const isSuggested = suggested && suggested.includes(col);
        return `
            <div class="column-chip ${isSuggested ? 'selected' : ''}" 
                 data-column="${col}" 
                 onclick="toggleColumn(this)">
                <i class="fas ${isSuggested ? 'fa-check' : 'fa-plus'}"></i>
                ${col}
            </div>
        `;
    }).join('');
    
    // Aggiorna stato selezione
    appState.selectedColumns = suggested || [];
}

/**
 * Toggle selezione colonna
 */
function toggleColumn(element) {
    const column = element.dataset.column;
    element.classList.toggle('selected');
    
    const icon = element.querySelector('i');
    
    if (element.classList.contains('selected')) {
        icon.className = 'fas fa-check';
        if (!appState.selectedColumns.includes(column)) {
            appState.selectedColumns.push(column);
        }
    } else {
        icon.className = 'fas fa-plus';
        appState.selectedColumns = appState.selectedColumns.filter(c => c !== column);
    }
}

/**
 * Gestisce il toggle auto-detect
 */
function handleAutoDetectToggle() {
    const isEnabled = elements.autoDetect.checked;
    elements.keyColumnsGroup.style.display = isEnabled ? 'none' : 'block';
}

// ============================================
// Gestione Merge
// ============================================

/**
 * Esegue il merge dei file
 */
async function executeMerge() {
    if (appState.uploadedFiles.length === 0) {
        showToast('Carica almeno un file', 'error');
        return;
    }
    
    const autoDetect = elements.autoDetect.checked;
    const removeDuplicates = elements.removeDuplicates.checked;
    const outputFormat = document.querySelector('input[name="outputFormat"]:checked').value;
    
    const mergeConfig = {
        files: appState.uploadedFiles.map(f => f.filepath),
        auto_detect: autoDetect,
        remove_duplicates: removeDuplicates,
        output_format: outputFormat,
        key_columns: autoDetect ? null : appState.selectedColumns
    };
    
    setLoading(true);
    
    try {
        const response = await fetch('/merge', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(mergeConfig)
        });
        
        const data = await response.json();
        
        if (data.error) {
            showToast(data.error, 'error');
            return;
        }
        
        // Salva riferimento al file mergato
        appState.mergedFilePath = data.output_path;
        appState.mergedFileName = data.output_file;
        
        // Mostra risultati
        displayResults(data);
        
        showToast('Merge completato con successo!', 'success');
        
        // Aggiorna cronologia
        loadHistory();
        
    } catch (error) {
        showToast('Errore durante il merge: ' + error.message, 'error');
    } finally {
        setLoading(false);
    }
}

/**
 * Mostra i risultati del merge
 */
function displayResults(data) {
    elements.resultsSection.style.display = 'block';
    
    // Aggiorna statistiche
    document.getElementById('statFilesProcessed').textContent = data.stats.files_processed;
    document.getElementById('statRowsBefore').textContent = data.stats.total_rows_before;
    document.getElementById('statDuplicates').textContent = data.stats.duplicates_removed;
    document.getElementById('statFinalRows').textContent = data.stats.final_rows;
    
    // Info colonne chiave
    const keyColumnsInfo = document.getElementById('keyColumnsInfo');
    if (data.key_columns_used && data.key_columns_used.length > 0) {
        keyColumnsInfo.innerHTML = `
            <i class="fas fa-key"></i>
            <span>Deduplicazione basata su: <strong>${data.key_columns_used.join(', ')}</strong></span>
        `;
        keyColumnsInfo.style.display = 'flex';
    } else {
        keyColumnsInfo.innerHTML = `
            <i class="fas fa-info-circle"></i>
            <span>Deduplicazione basata su tutte le colonne</span>
        `;
        keyColumnsInfo.style.display = 'flex';
    }
    
    // Popola tabella preview
    const previewHead = document.getElementById('previewHead');
    const previewBody = document.getElementById('previewBody');
    
    if (data.columns && data.preview) {
        previewHead.innerHTML = `
            <tr>
                ${data.columns.map(col => `<th>${col}</th>`).join('')}
            </tr>
        `;
        
        previewBody.innerHTML = data.preview.map(row => `
            <tr>
                ${data.columns.map(col => `<td title="${row[col] || ''}">${row[col] || ''}</td>`).join('')}
            </tr>
        `).join('');
    }
    
    // Scroll ai risultati
    elements.resultsSection.scrollIntoView({ behavior: 'smooth' });
}

/**
 * Download del file mergato
 */
function downloadMergedFile() {
    if (!appState.mergedFileName) {
        showToast('Nessun file da scaricare', 'error');
        return;
    }
    
    window.location.href = `/download/${appState.mergedFileName}`;
    showToast('Download avviato', 'success');
}

/**
 * Reset per nuovo merge
 */
function resetForNewMerge() {
    appState.uploadedFiles = [];
    appState.selectedColumns = [];
    appState.mergedFilePath = null;
    appState.mergedFileName = null;
    
    elements.fileList.style.display = 'none';
    elements.configSection.style.display = 'none';
    elements.resultsSection.style.display = 'none';
    elements.fileInput.value = '';
    
    // Pulisci file temporanei
    fetch('/clear', { method: 'POST' });
    
    showToast('Pronto per un nuovo merge', 'info');
    
    // Scroll in alto
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ============================================
// Gestione Cronologia
// ============================================

/**
 * Toggle sezione cronologia
 */
function toggleHistory() {
    const isOpen = elements.historyBody.style.display !== 'none';
    elements.historyBody.style.display = isOpen ? 'none' : 'block';
    document.querySelector('.collapse-icon').classList.toggle('rotated', !isOpen);
    
    if (!isOpen) {
        loadHistory();
    }
}

/**
 * Carica la cronologia dei file mergati
 */
async function loadHistory() {
    try {
        const response = await fetch('/history');
        const data = await response.json();
        
        if (data.files && data.files.length > 0) {
            elements.historyList.innerHTML = data.files.map(file => `
                <div class="history-item">
                    <div class="history-item-info">
                        <div class="history-item-icon">
                            <i class="fas ${file.filename.endsWith('.csv') ? 'fa-file-csv' : 'fa-file-excel'}"></i>
                        </div>
                        <div>
                            <div class="history-item-name">${file.filename}</div>
                            <div class="history-item-meta">
                                ${formatFileSize(file.size)} · ${file.created}
                            </div>
                        </div>
                    </div>
                    <a href="/download/${file.filename}" class="btn btn-sm btn-primary">
                        <i class="fas fa-download"></i> Scarica
                    </a>
                </div>
            `).join('');
        } else {
            elements.historyList.innerHTML = '<p class="empty-history">Nessun file mergato ancora.</p>';
        }
        
    } catch (error) {
        console.error('Errore caricamento cronologia:', error);
    }
}

// ============================================
// Inizializzazione
// ============================================

function init() {
    // Drag & Drop
    initDragDrop();
    
    // Event Listeners
    elements.fileInput.addEventListener('change', (e) => handleFiles(e.target.files));
    elements.uploadZone.addEventListener('click', () => elements.fileInput.click());
    elements.clearFilesBtn.addEventListener('click', clearAllFiles);
    elements.autoDetect.addEventListener('change', handleAutoDetectToggle);
    elements.mergeBtn.addEventListener('click', executeMerge);
    elements.downloadBtn.addEventListener('click', downloadMergedFile);
    elements.newMergeBtn.addEventListener('click', resetForNewMerge);
    elements.historyHeader.addEventListener('click', toggleHistory);
    
    // Previeni click sul file input dal bubbling verso l'upload zone
    elements.fileInput.addEventListener('click', (e) => e.stopPropagation());
    
    // Carica cronologia iniziale
    loadHistory();
    
    console.log('CSV/Excel Merger App inizializzata');
}

// Avvia l'app quando il DOM è pronto
document.addEventListener('DOMContentLoaded', init);
