#!/usr/bin/env python3
"""
SETUP CSV/EXCEL MERGER APP
==========================
Esegui questo file per creare automaticamente l'intera applicazione.

ISTRUZIONI:
1. Salva questo file sul tuo Desktop come "setup_merger.py"
2. Doppio click per eseguirlo
3. Verrà creata la cartella "csv_merger_app" con tutto il necessario
"""

import os
import subprocess
import sys

# Cartella base
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "csv_merger_app")

def create_directories():
    """Crea le cartelle necessarie"""
    dirs = [
        BASE_DIR,
        os.path.join(BASE_DIR, "templates"),
        os.path.join(BASE_DIR, "static"),
        os.path.join(BASE_DIR, "uploads"),
        os.path.join(BASE_DIR, "merged")
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    print("✓ Cartelle create")

def create_requirements():
    """Crea requirements.txt"""
    content = """flask>=2.3.0
pandas>=2.0.0
openpyxl>=3.1.0
xlrd>=2.0.0
werkzeug>=2.3.0
"""
    with open(os.path.join(BASE_DIR, "requirements.txt"), "w") as f:
        f.write(content)
    print("✓ requirements.txt creato")

def create_app_py():
    """Crea il file principale app.py"""
    content = '''"""
CSV/Excel Merger App - Applicazione per merge di file CSV/Excel con deduplicazione
"""

import os
import uuid
import hashlib
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MERGED_FOLDER'] = 'merged'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['MERGED_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def read_file(filepath):
    ext = filepath.rsplit('.', 1)[1].lower()
    if ext == 'csv':
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        for encoding in encodings:
            try:
                return pd.read_csv(filepath, encoding=encoding)
            except UnicodeDecodeError:
                continue
        return pd.read_csv(filepath, encoding='latin-1', errors='replace')
    else:
        return pd.read_excel(filepath)

def merge_dataframes(dataframes, key_columns=None, remove_duplicates=True):
    if not dataframes:
        return None, {}
    
    stats = {
        'files_processed': len(dataframes),
        'total_rows_before': sum(len(df) for df in dataframes),
        'duplicates_removed': 0,
        'final_rows': 0
    }
    
    merged_df = pd.concat(dataframes, ignore_index=True)
    
    if remove_duplicates and len(merged_df) > 0:
        if key_columns and all(col in merged_df.columns for col in key_columns):
            before_count = len(merged_df)
            merged_df = merged_df.drop_duplicates(subset=key_columns, keep='first')
            stats['duplicates_removed'] = before_count - len(merged_df)
        else:
            before_count = len(merged_df)
            merged_df = merged_df.drop_duplicates(keep='first')
            stats['duplicates_removed'] = before_count - len(merged_df)
    
    stats['final_rows'] = len(merged_df)
    return merged_df, stats

def detect_linkedin_columns(df):
    linkedin_key_columns = [
        'Profile URL', 'LinkedIn URL', 'profile_url', 'linkedin_url',
        'Email', 'email', 'Email Address',
        'Full Name', 'full_name', 'Name', 'name',
        'First Name', 'first_name', 'Last Name', 'last_name'
    ]
    
    found_columns = [col for col in linkedin_key_columns if col in df.columns]
    
    if any(col in found_columns for col in ['Profile URL', 'LinkedIn URL', 'profile_url', 'linkedin_url']):
        return [col for col in ['Profile URL', 'LinkedIn URL', 'profile_url', 'linkedin_url'] if col in found_columns][:1]
    
    if any(col in found_columns for col in ['Email', 'email', 'Email Address']):
        return [col for col in ['Email', 'email', 'Email Address'] if col in found_columns][:1]
    
    if any(col in found_columns for col in ['Full Name', 'full_name', 'Name', 'name']):
        return [col for col in ['Full Name', 'full_name', 'Name', 'name'] if col in found_columns][:1]
    
    first_name_cols = [col for col in ['First Name', 'first_name'] if col in found_columns]
    last_name_cols = [col for col in ['Last Name', 'last_name'] if col in found_columns]
    if first_name_cols and last_name_cols:
        return [first_name_cols[0], last_name_cols[0]]
    
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files[]' not in request.files:
        return jsonify({'error': 'Nessun file caricato'}), 400
    
    files = request.files.getlist('files[]')
    
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'Nessun file selezionato'}), 400
    
    uploaded_files = []
    errors = []
    
    for file in files:
        if file and file.filename:
            if allowed_file(file.filename):
                original_name = secure_filename(file.filename)
                unique_id = str(uuid.uuid4())[:8]
                filename = f"{unique_id}_{original_name}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                file.save(filepath)
                
                try:
                    df = read_file(filepath)
                    uploaded_files.append({
                        'filename': filename,
                        'original_name': original_name,
                        'rows': len(df),
                        'columns': list(df.columns),
                        'filepath': filepath
                    })
                except Exception as e:
                    errors.append(f"Errore lettura {original_name}: {str(e)}")
                    os.remove(filepath)
            else:
                errors.append(f"Formato non supportato: {file.filename}")
    
    return jsonify({
        'files': uploaded_files,
        'errors': errors,
        'message': f'{len(uploaded_files)} file caricati con successo'
    })

@app.route('/merge', methods=['POST'])
def merge_files():
    data = request.get_json()
    
    filepaths = data.get('files', [])
    key_columns = data.get('key_columns', None)
    auto_detect = data.get('auto_detect', True)
    remove_duplicates = data.get('remove_duplicates', True)
    output_format = data.get('output_format', 'csv')
    
    if not filepaths:
        return jsonify({'error': 'Nessun file selezionato per il merge'}), 400
    
    dataframes = []
    
    for filepath in filepaths:
        if os.path.exists(filepath):
            try:
                df = read_file(filepath)
                dataframes.append(df)
            except Exception as e:
                return jsonify({'error': f'Errore lettura file: {str(e)}'}), 500
    
    if not dataframes:
        return jsonify({'error': 'Nessun file valido trovato'}), 400
    
    if auto_detect and not key_columns:
        key_columns = detect_linkedin_columns(dataframes[0])
    
    merged_df, stats = merge_dataframes(dataframes, key_columns=key_columns, remove_duplicates=remove_duplicates)
    
    if merged_df is None:
        return jsonify({'error': 'Errore durante il merge'}), 500
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_filename = f"merged_{timestamp}.{output_format}"
    output_path = os.path.join(app.config['MERGED_FOLDER'], output_filename)
    
    try:
        if output_format == 'xlsx':
            merged_df.to_excel(output_path, index=False)
        else:
            merged_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    except Exception as e:
        return jsonify({'error': f'Errore salvataggio: {str(e)}'}), 500
    
    preview_data = merged_df.head(10).to_dict('records')
    
    return jsonify({
        'success': True,
        'output_file': output_filename,
        'output_path': output_path,
        'stats': stats,
        'key_columns_used': key_columns,
        'columns': list(merged_df.columns),
        'preview': preview_data
    })

@app.route('/download/<filename>')
def download_file(filename):
    filepath = os.path.join(app.config['MERGED_FOLDER'], secure_filename(filename))
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=filename)
    return jsonify({'error': 'File non trovato'}), 404

@app.route('/columns', methods=['POST'])
def get_columns():
    data = request.get_json()
    filepaths = data.get('files', [])
    
    if not filepaths:
        return jsonify({'columns': []})
    
    all_columns = []
    
    for filepath in filepaths:
        if os.path.exists(filepath):
            try:
                df = read_file(filepath)
                all_columns.append(set(df.columns))
            except:
                pass
    
    if not all_columns:
        return jsonify({'columns': []})
    
    common_columns = list(set.intersection(*all_columns))
    
    linkedin_priority = ['Profile URL', 'LinkedIn URL', 'Email', 'email', 
                         'Full Name', 'Name', 'First Name', 'Last Name']
    
    def column_priority(col):
        try:
            return linkedin_priority.index(col)
        except ValueError:
            return len(linkedin_priority) + 1
    
    common_columns.sort(key=column_priority)
    
    return jsonify({
        'columns': common_columns,
        'suggested': detect_linkedin_columns(pd.DataFrame(columns=common_columns))
    })

@app.route('/clear', methods=['POST'])
def clear_files():
    for f in os.listdir(app.config['UPLOAD_FOLDER']):
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f))
        except:
            pass
    return jsonify({'message': 'File temporanei eliminati'})

@app.route('/history')
def get_history():
    merged_files = []
    for f in os.listdir(app.config['MERGED_FOLDER']):
        filepath = os.path.join(app.config['MERGED_FOLDER'], f)
        stat = os.stat(filepath)
        merged_files.append({
            'filename': f,
            'size': stat.st_size,
            'created': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        })
    merged_files.sort(key=lambda x: x['created'], reverse=True)
    return jsonify({'files': merged_files})

if __name__ == '__main__':
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║                   CSV/Excel Merger App                      ║
    ║                                                              ║
    ║  Apri il browser e vai su: http://localhost:5000            ║
    ║                                                              ║
    ║  Premi CTRL+C per terminare il server                       ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    app.run(debug=True, host='0.0.0.0', port=5000)
'''
    with open(os.path.join(BASE_DIR, "app.py"), "w", encoding="utf-8") as f:
        f.write(content)
    print("✓ app.py creato")

def create_index_html():
    """Crea il template HTML"""
    content = '''<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CSV/Excel Merger</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="logo">
                <i class="fas fa-layer-group"></i>
                <h1>CSV/Excel Merger</h1>
            </div>
            <p class="subtitle">Unisci i tuoi file CSV/Excel senza duplicati</p>
        </header>

        <main class="main-content">
            <section class="card">
                <div class="card-header">
                    <span class="step-number">1</span>
                    <h2>Carica i File</h2>
                </div>
                <div class="card-body">
                    <div class="upload-zone" id="uploadZone">
                        <i class="fas fa-cloud-upload-alt upload-icon"></i>
                        <p>Trascina qui i file CSV/Excel</p>
                        <span class="upload-hint">oppure</span>
                        <label class="btn btn-primary">
                            <i class="fas fa-folder-open"></i> Sfoglia
                            <input type="file" id="fileInput" multiple accept=".csv,.xlsx,.xls" hidden>
                        </label>
                    </div>
                    
                    <div class="file-list" id="fileList" style="display: none;">
                        <div class="file-list-header">
                            <h3>File Caricati</h3>
                            <button class="btn btn-sm btn-danger" id="clearFilesBtn">
                                <i class="fas fa-trash"></i> Rimuovi tutti
                            </button>
                        </div>
                        <div id="fileItems"></div>
                    </div>
                </div>
            </section>

            <section class="card" id="configSection" style="display: none;">
                <div class="card-header">
                    <span class="step-number">2</span>
                    <h2>Configura</h2>
                </div>
                <div class="card-body">
                    <div class="config-group">
                        <label class="toggle-option">
                            <input type="checkbox" id="removeDuplicates" checked>
                            <span>Rimuovi duplicati</span>
                        </label>
                        <label class="toggle-option">
                            <input type="checkbox" id="autoDetect" checked>
                            <span>Auto-rileva colonne LinkedIn</span>
                        </label>
                    </div>
                    <div class="config-group">
                        <label><input type="radio" name="outputFormat" value="csv" checked> CSV</label>
                        <label><input type="radio" name="outputFormat" value="xlsx"> Excel</label>
                    </div>
                    <button class="btn btn-primary btn-lg" id="mergeBtn">
                        <i class="fas fa-magic"></i> Esegui Merge
                    </button>
                </div>
            </section>

            <section class="card" id="resultsSection" style="display: none;">
                <div class="card-header">
                    <span class="step-number">3</span>
                    <h2>Risultato</h2>
                </div>
                <div class="card-body">
                    <div class="stats-grid">
                        <div class="stat-card">
                            <span class="stat-value" id="statFilesProcessed">0</span>
                            <span class="stat-label">File</span>
                        </div>
                        <div class="stat-card">
                            <span class="stat-value" id="statRowsBefore">0</span>
                            <span class="stat-label">Righe totali</span>
                        </div>
                        <div class="stat-card warning">
                            <span class="stat-value" id="statDuplicates">0</span>
                            <span class="stat-label">Duplicati rimossi</span>
                        </div>
                        <div class="stat-card success">
                            <span class="stat-value" id="statFinalRows">0</span>
                            <span class="stat-label">Righe finali</span>
                        </div>
                    </div>
                    <div id="keyColumnsInfo" class="info-box"></div>
                    <div class="table-container">
                        <table class="preview-table">
                            <thead id="previewHead"></thead>
                            <tbody id="previewBody"></tbody>
                        </table>
                    </div>
                    <div class="actions">
                        <button class="btn btn-success btn-lg" id="downloadBtn">
                            <i class="fas fa-download"></i> Scarica
                        </button>
                        <button class="btn btn-secondary" id="newMergeBtn">
                            <i class="fas fa-redo"></i> Nuovo
                        </button>
                    </div>
                </div>
            </section>

            <section class="card">
                <div class="card-header" id="historyHeader" style="cursor:pointer;">
                    <h2><i class="fas fa-history"></i> Cronologia</h2>
                </div>
                <div class="card-body" id="historyBody" style="display: none;">
                    <div id="historyList"></div>
                </div>
            </section>
        </main>
    </div>

    <div class="loading-overlay" id="loadingOverlay">
        <div class="loading-spinner">
            <i class="fas fa-spinner fa-spin"></i>
            <p>Elaborazione...</p>
        </div>
    </div>

    <div class="toast-container" id="toastContainer"></div>

    <script src="{{ url_for('static', filename='script.js') }}"></script>
</body>
</html>
'''
    with open(os.path.join(BASE_DIR, "templates", "index.html"), "w", encoding="utf-8") as f:
        f.write(content)
    print("✓ index.html creato")

def create_style_css():
    """Crea il file CSS"""
    content = '''* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Inter', sans-serif; background: #f5f7fa; color: #333; line-height: 1.6; }
.container { max-width: 900px; margin: 0 auto; padding: 20px; }
.header { text-align: center; padding: 40px 20px; }
.logo { display: flex; align-items: center; justify-content: center; gap: 15px; margin-bottom: 10px; }
.logo i { font-size: 2.5rem; color: #0077b5; }
.logo h1 { font-size: 2rem; font-weight: 700; }
.subtitle { color: #6c757d; }
.card { background: #fff; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 20px; overflow: hidden; }
.card-header { display: flex; align-items: center; gap: 15px; padding: 20px; border-bottom: 1px solid #e0e0e0; background: #fafbfc; }
.card-header h2 { font-size: 1.2rem; }
.step-number { display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; background: #0077b5; color: white; border-radius: 50%; font-weight: 600; }
.card-body { padding: 20px; }
.upload-zone { border: 2px dashed #ccc; border-radius: 10px; padding: 40px; text-align: center; cursor: pointer; background: #fafbfc; transition: all 0.3s; }
.upload-zone:hover, .upload-zone.dragover { border-color: #0077b5; background: rgba(0,119,181,0.05); }
.upload-icon { font-size: 3rem; color: #0077b5; margin-bottom: 15px; }
.upload-hint { display: block; color: #999; margin: 10px 0; }
.btn { display: inline-flex; align-items: center; gap: 8px; padding: 12px 24px; border: none; border-radius: 6px; font-size: 1rem; font-weight: 500; cursor: pointer; transition: all 0.3s; }
.btn-sm { padding: 8px 16px; font-size: 0.875rem; }
.btn-lg { padding: 16px 32px; font-size: 1.1rem; }
.btn-primary { background: #0077b5; color: white; }
.btn-primary:hover { background: #005885; }
.btn-secondary { background: #6c757d; color: white; }
.btn-success { background: #28a745; color: white; }
.btn-success:hover { background: #218838; }
.btn-danger { background: #dc3545; color: white; }
.file-list { margin-top: 20px; }
.file-list-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
.file-item { display: flex; align-items: center; gap: 15px; padding: 12px; background: #f8f9fa; border-radius: 6px; margin-bottom: 8px; border: 1px solid #e0e0e0; }
.file-item-icon { font-size: 1.5rem; color: #28a745; }
.file-item-info { flex: 1; }
.file-item-name { font-weight: 500; }
.file-item-meta { font-size: 0.85rem; color: #6c757d; }
.file-item-remove { background: none; border: none; color: #dc3545; font-size: 1.2rem; cursor: pointer; }
.config-group { margin-bottom: 20px; }
.toggle-option { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; cursor: pointer; }
.toggle-option input { width: 18px; height: 18px; }
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }
.stat-card { padding: 15px; background: #f8f9fa; border-radius: 8px; text-align: center; border-left: 4px solid #0077b5; }
.stat-card.warning { border-left-color: #ffc107; }
.stat-card.success { border-left-color: #28a745; }
.stat-value { font-size: 1.5rem; font-weight: 700; display: block; }
.stat-label { font-size: 0.8rem; color: #6c757d; }
.info-box { padding: 12px; background: rgba(0,119,181,0.1); border-radius: 6px; margin-bottom: 15px; }
.table-container { overflow-x: auto; border: 1px solid #e0e0e0; border-radius: 6px; margin-bottom: 20px; max-height: 300px; }
.preview-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.preview-table th, .preview-table td { padding: 10px; text-align: left; border-bottom: 1px solid #e0e0e0; white-space: nowrap; }
.preview-table th { background: #f8f9fa; font-weight: 600; position: sticky; top: 0; }
.actions { display: flex; gap: 15px; justify-content: center; }
.loading-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(255,255,255,0.9); display: none; align-items: center; justify-content: center; z-index: 1000; }
.loading-overlay.active { display: flex; }
.loading-spinner { text-align: center; }
.loading-spinner i { font-size: 3rem; color: #0077b5; }
.toast-container { position: fixed; top: 20px; right: 20px; z-index: 1001; }
.toast { padding: 15px 20px; background: white; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); margin-bottom: 10px; display: flex; align-items: center; gap: 10px; animation: slideIn 0.3s; }
.toast.success { border-left: 4px solid #28a745; }
.toast.error { border-left: 4px solid #dc3545; }
.toast.info { border-left: 4px solid #17a2b8; }
@keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
.history-item { display: flex; justify-content: space-between; align-items: center; padding: 12px; background: #f8f9fa; border-radius: 6px; margin-bottom: 8px; }
@media (max-width: 600px) { .stats-grid { grid-template-columns: repeat(2, 1fr); } .actions { flex-direction: column; } }
'''
    with open(os.path.join(BASE_DIR, "static", "style.css"), "w", encoding="utf-8") as f:
        f.write(content)
    print("✓ style.css creato")

def create_script_js():
    """Crea il file JavaScript"""
    content = '''const appState = { uploadedFiles: [], selectedColumns: [], mergedFileName: null };

const $ = id => document.getElementById(id);

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = 'toast ' + type;
    const icons = { success: 'fa-check-circle', error: 'fa-exclamation-circle', info: 'fa-info-circle' };
    toast.innerHTML = '<i class="fas ' + icons[type] + '"></i><span>' + message + '</span>';
    $('toastContainer').appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

function setLoading(show) {
    $('loadingOverlay').classList.toggle('active', show);
}

// Upload
$('uploadZone').addEventListener('click', () => $('fileInput').click());
$('fileInput').addEventListener('change', e => handleFiles(e.target.files));

['dragenter', 'dragover', 'dragleave', 'drop'].forEach(evt => {
    $('uploadZone').addEventListener(evt, e => { e.preventDefault(); e.stopPropagation(); });
});
['dragenter', 'dragover'].forEach(evt => {
    $('uploadZone').addEventListener(evt, () => $('uploadZone').classList.add('dragover'));
});
['dragleave', 'drop'].forEach(evt => {
    $('uploadZone').addEventListener(evt, () => $('uploadZone').classList.remove('dragover'));
});
$('uploadZone').addEventListener('drop', e => handleFiles(e.dataTransfer.files));

async function handleFiles(files) {
    if (!files.length) return;
    const formData = new FormData();
    for (const file of files) formData.append('files[]', file);
    
    setLoading(true);
    try {
        const res = await fetch('/upload', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.error) { showToast(data.error, 'error'); return; }
        appState.uploadedFiles.push(...data.files);
        if (data.errors) data.errors.forEach(e => showToast(e, 'error'));
        showToast(data.message, 'success');
        updateFileList();
    } catch (e) { showToast('Errore upload', 'error'); }
    finally { setLoading(false); }
}

function updateFileList() {
    if (!appState.uploadedFiles.length) {
        $('fileList').style.display = 'none';
        $('configSection').style.display = 'none';
        return;
    }
    $('fileList').style.display = 'block';
    $('configSection').style.display = 'block';
    $('fileItems').innerHTML = appState.uploadedFiles.map((f, i) => 
        '<div class="file-item"><div class="file-item-icon"><i class="fas fa-file-csv"></i></div>' +
        '<div class="file-item-info"><div class="file-item-name">' + f.original_name + '</div>' +
        '<div class="file-item-meta">' + f.rows + ' righe</div></div>' +
        '<button class="file-item-remove" onclick="removeFile(' + i + ')"><i class="fas fa-times"></i></button></div>'
    ).join('');
}

function removeFile(i) {
    appState.uploadedFiles.splice(i, 1);
    updateFileList();
}

$('clearFilesBtn').addEventListener('click', async () => {
    await fetch('/clear', { method: 'POST' });
    appState.uploadedFiles = [];
    updateFileList();
    $('resultsSection').style.display = 'none';
});

// Merge
$('mergeBtn').addEventListener('click', async () => {
    if (!appState.uploadedFiles.length) { showToast('Carica almeno un file', 'error'); return; }
    
    const config = {
        files: appState.uploadedFiles.map(f => f.filepath),
        auto_detect: $('autoDetect').checked,
        remove_duplicates: $('removeDuplicates').checked,
        output_format: document.querySelector('input[name="outputFormat"]:checked').value
    };
    
    setLoading(true);
    try {
        const res = await fetch('/merge', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        const data = await res.json();
        if (data.error) { showToast(data.error, 'error'); return; }
        
        appState.mergedFileName = data.output_file;
        
        $('statFilesProcessed').textContent = data.stats.files_processed;
        $('statRowsBefore').textContent = data.stats.total_rows_before;
        $('statDuplicates').textContent = data.stats.duplicates_removed;
        $('statFinalRows').textContent = data.stats.final_rows;
        
        $('keyColumnsInfo').innerHTML = data.key_columns_used ? 
            '<i class="fas fa-key"></i> Deduplicazione su: <strong>' + data.key_columns_used.join(', ') + '</strong>' :
            '<i class="fas fa-info-circle"></i> Deduplicazione su tutte le colonne';
        
        if (data.columns && data.preview) {
            $('previewHead').innerHTML = '<tr>' + data.columns.map(c => '<th>' + c + '</th>').join('') + '</tr>';
            $('previewBody').innerHTML = data.preview.map(row => 
                '<tr>' + data.columns.map(c => '<td>' + (row[c] || '') + '</td>').join('') + '</tr>'
            ).join('');
        }
        
        $('resultsSection').style.display = 'block';
        $('resultsSection').scrollIntoView({ behavior: 'smooth' });
        showToast('Merge completato!', 'success');
        loadHistory();
    } catch (e) { showToast('Errore merge', 'error'); }
    finally { setLoading(false); }
});

$('downloadBtn').addEventListener('click', () => {
    if (appState.mergedFileName) {
        window.location.href = '/download/' + appState.mergedFileName;
        showToast('Download avviato', 'success');
    }
});

$('newMergeBtn').addEventListener('click', () => {
    appState.uploadedFiles = [];
    appState.mergedFileName = null;
    $('fileList').style.display = 'none';
    $('configSection').style.display = 'none';
    $('resultsSection').style.display = 'none';
    fetch('/clear', { method: 'POST' });
    window.scrollTo({ top: 0, behavior: 'smooth' });
});

// History
$('historyHeader').addEventListener('click', () => {
    const body = $('historyBody');
    body.style.display = body.style.display === 'none' ? 'block' : 'none';
    if (body.style.display === 'block') loadHistory();
});

async function loadHistory() {
    try {
        const res = await fetch('/history');
        const data = await res.json();
        $('historyList').innerHTML = data.files.length ? 
            data.files.map(f => 
                '<div class="history-item"><span>' + f.filename + ' - ' + f.created + '</span>' +
                '<a href="/download/' + f.filename + '" class="btn btn-sm btn-primary"><i class="fas fa-download"></i></a></div>'
            ).join('') : '<p>Nessun file mergato.</p>';
    } catch (e) {}
}

loadHistory();
'''
    with open(os.path.join(BASE_DIR, "static", "script.js"), "w", encoding="utf-8") as f:
        f.write(content)
    print("✓ script.js creato")

def install_dependencies():
    """Installa le dipendenze Python"""
    print("\n📦 Installazione dipendenze...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "flask", "pandas", "openpyxl", "xlrd"])
        print("✓ Dipendenze installate")
        return True
    except Exception as e:
        print(f"⚠ Errore installazione: {e}")
        print("  Esegui manualmente: pip install flask pandas openpyxl xlrd")
        return False

def create_start_script():
    """Crea script di avvio"""
    # Windows
    bat_content = '''@echo off
cd /d "%~dp0"
echo Avvio CSV/Excel Merger...
echo Apri il browser su: http://localhost:5000
python app.py
pause
'''
    with open(os.path.join(BASE_DIR, "AVVIA.bat"), "w") as f:
        f.write(bat_content)
    
    # Mac/Linux
    sh_content = '''#!/bin/bash
cd "$(dirname "$0")"
echo "Avvio CSV/Excel Merger..."
echo "Apri il browser su: http://localhost:5000"
python3 app.py
'''
    with open(os.path.join(BASE_DIR, "avvia.sh"), "w") as f:
        f.write(sh_content)
    
    print("✓ Script di avvio creati")

def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║           SETUP CSV/EXCEL MERGER APP                        ║
╚════════════════════════════════════════════════════════════╝
""")
    
    print("📁 Creazione progetto in:", BASE_DIR)
    print()
    
    create_directories()
    create_requirements()
    create_app_py()
    create_index_html()
    create_style_css()
    create_script_js()
    create_start_script()
    
    install_dependencies()
    
    print("""
╔════════════════════════════════════════════════════════════╗
║                    ✅ INSTALLAZIONE COMPLETATA              ║
╠════════════════════════════════════════════════════════════╣
║                                                              ║
║  Per avviare l'app:                                         ║
║                                                              ║
║  WINDOWS: Doppio click su "AVVIA.bat" nella cartella        ║
║           csv_merger_app                                    ║
║                                                              ║
║  MAC/LINUX: Esegui ./avvia.sh nella cartella                ║
║             csv_merger_app                                  ║
║                                                              ║
║  Poi apri il browser su: http://localhost:5000              ║
║                                                              ║
╚════════════════════════════════════════════════════════════╝
""")
    
    # Chiedi se avviare subito
    try:
        risposta = input("\nVuoi avviare l'app adesso? (s/n): ").strip().lower()
        if risposta in ['s', 'si', 'y', 'yes']:
            os.chdir(BASE_DIR)
            print("\n🚀 Avvio server... Apri http://localhost:5000 nel browser")
            subprocess.call([sys.executable, "app.py"])
    except:
        pass

if __name__ == "__main__":
    main()
