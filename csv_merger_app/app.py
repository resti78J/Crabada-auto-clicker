"""
CSV/Excel Merger App - Applicazione per merge di file CSV/Excel con deduplicazione
Autore: AI Assistant
Descrizione: Applicazione web locale per unire file CSV/Excel evitando duplicati
"""

import os
import uuid
import hashlib
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
from werkzeug.utils import secure_filename

# Configurazione Flask
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MERGED_FOLDER'] = 'merged'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # Max 50MB per file

# Estensioni permesse
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

# Assicura che le cartelle esistano
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['MERGED_FOLDER'], exist_ok=True)


def allowed_file(filename):
    """Verifica se l'estensione del file è permessa"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def read_file(filepath):
    """
    Legge un file CSV o Excel e restituisce un DataFrame pandas
    Gestisce automaticamente l'encoding e il formato
    """
    ext = filepath.rsplit('.', 1)[1].lower()
    
    if ext == 'csv':
        # Prova diversi encoding comuni
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        for encoding in encodings:
            try:
                df = pd.read_csv(filepath, encoding=encoding)
                return df
            except UnicodeDecodeError:
                continue
        # Se nessun encoding funziona, usa latin-1 come fallback
        return pd.read_csv(filepath, encoding='latin-1', errors='replace')
    else:
        # Excel file
        return pd.read_excel(filepath)


def generate_row_hash(row, key_columns=None):
    """
    Genera un hash univoco per una riga basandosi su colonne chiave
    Se key_columns è None, usa tutte le colonne
    """
    if key_columns:
        values = [str(row[col]) for col in key_columns if col in row.index]
    else:
        values = [str(v) for v in row.values]
    
    row_string = '|'.join(values).lower().strip()
    return hashlib.md5(row_string.encode()).hexdigest()


def merge_dataframes(dataframes, key_columns=None, remove_duplicates=True):
    """
    Unisce più DataFrame rimuovendo i duplicati
    
    Args:
        dataframes: Lista di DataFrame pandas
        key_columns: Lista di colonne da usare come chiave per identificare duplicati
                    Se None, usa tutte le colonne
        remove_duplicates: Se True, rimuove i duplicati
    
    Returns:
        DataFrame unificato con statistiche
    """
    if not dataframes:
        return None, {}
    
    # Statistiche
    stats = {
        'files_processed': len(dataframes),
        'total_rows_before': sum(len(df) for df in dataframes),
        'duplicates_removed': 0,
        'final_rows': 0
    }
    
    # Concatena tutti i DataFrame
    merged_df = pd.concat(dataframes, ignore_index=True)
    
    if remove_duplicates and len(merged_df) > 0:
        # Se sono specificate colonne chiave, usa quelle per la deduplicazione
        if key_columns and all(col in merged_df.columns for col in key_columns):
            # Rimuovi duplicati basandosi sulle colonne chiave
            before_count = len(merged_df)
            merged_df = merged_df.drop_duplicates(subset=key_columns, keep='first')
            stats['duplicates_removed'] = before_count - len(merged_df)
        else:
            # Rimuovi duplicati basandosi su tutte le colonne
            before_count = len(merged_df)
            merged_df = merged_df.drop_duplicates(keep='first')
            stats['duplicates_removed'] = before_count - len(merged_df)
    
    stats['final_rows'] = len(merged_df)
    
    return merged_df, stats


def detect_linkedin_columns(df):
    """
    Rileva automaticamente le colonne chiave tipiche dei CSV di LinkedIn
    per una migliore deduplicazione
    """
    linkedin_key_columns = [
        'Profile URL', 'LinkedIn URL', 'profile_url', 'linkedin_url',
        'Email', 'email', 'Email Address',
        'Full Name', 'full_name', 'Name', 'name',
        'First Name', 'first_name', 'Last Name', 'last_name'
    ]
    
    # Trova le colonne presenti nel DataFrame
    found_columns = [col for col in linkedin_key_columns if col in df.columns]
    
    # Priorità: URL LinkedIn > Email > Nome completo > Nome + Cognome
    if any(col in found_columns for col in ['Profile URL', 'LinkedIn URL', 'profile_url', 'linkedin_url']):
        return [col for col in ['Profile URL', 'LinkedIn URL', 'profile_url', 'linkedin_url'] if col in found_columns][:1]
    
    if any(col in found_columns for col in ['Email', 'email', 'Email Address']):
        return [col for col in ['Email', 'email', 'Email Address'] if col in found_columns][:1]
    
    if any(col in found_columns for col in ['Full Name', 'full_name', 'Name', 'name']):
        return [col for col in ['Full Name', 'full_name', 'Name', 'name'] if col in found_columns][:1]
    
    # Nome + Cognome come fallback
    first_name_cols = [col for col in ['First Name', 'first_name'] if col in found_columns]
    last_name_cols = [col for col in ['Last Name', 'last_name'] if col in found_columns]
    if first_name_cols and last_name_cols:
        return [first_name_cols[0], last_name_cols[0]]
    
    return None  # Usa tutte le colonne


@app.route('/')
def index():
    """Pagina principale"""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_files():
    """
    Endpoint per caricare i file
    Accetta multiple file CSV/Excel
    """
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
                # Genera un nome univoco per il file
                original_name = secure_filename(file.filename)
                unique_id = str(uuid.uuid4())[:8]
                filename = f"{unique_id}_{original_name}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                file.save(filepath)
                
                # Leggi il file per ottenere info
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


@app.route('/preview', methods=['POST'])
def preview_file():
    """
    Anteprima di un file caricato
    Mostra le prime righe del file
    """
    data = request.get_json()
    filepath = data.get('filepath')
    
    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'File non trovato'}), 404
    
    try:
        df = read_file(filepath)
        preview_data = df.head(10).to_dict('records')
        columns = list(df.columns)
        
        return jsonify({
            'preview': preview_data,
            'columns': columns,
            'total_rows': len(df)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/merge', methods=['POST'])
def merge_files():
    """
    Endpoint principale per il merge dei file
    
    Parametri JSON:
        - files: Lista di filepath da unire
        - key_columns: Lista di colonne chiave per deduplicazione (opzionale)
        - auto_detect: Se True, rileva automaticamente le colonne chiave LinkedIn
        - remove_duplicates: Se True, rimuove i duplicati
        - output_format: 'csv' o 'xlsx'
    """
    data = request.get_json()
    
    filepaths = data.get('files', [])
    key_columns = data.get('key_columns', None)
    auto_detect = data.get('auto_detect', True)
    remove_duplicates = data.get('remove_duplicates', True)
    output_format = data.get('output_format', 'csv')
    
    if not filepaths:
        return jsonify({'error': 'Nessun file selezionato per il merge'}), 400
    
    dataframes = []
    columns_info = {}
    
    # Leggi tutti i file
    for filepath in filepaths:
        if os.path.exists(filepath):
            try:
                df = read_file(filepath)
                dataframes.append(df)
                columns_info[filepath] = list(df.columns)
            except Exception as e:
                return jsonify({'error': f'Errore lettura file: {str(e)}'}), 500
    
    if not dataframes:
        return jsonify({'error': 'Nessun file valido trovato'}), 400
    
    # Auto-detect colonne chiave se richiesto
    if auto_detect and not key_columns:
        # Usa il primo DataFrame per rilevare le colonne
        key_columns = detect_linkedin_columns(dataframes[0])
    
    # Esegui il merge
    merged_df, stats = merge_dataframes(
        dataframes,
        key_columns=key_columns,
        remove_duplicates=remove_duplicates
    )
    
    if merged_df is None:
        return jsonify({'error': 'Errore durante il merge'}), 500
    
    # Genera nome file output
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_filename = f"merged_{timestamp}.{output_format}"
    output_path = os.path.join(app.config['MERGED_FOLDER'], output_filename)
    
    # Salva il file
    try:
        if output_format == 'xlsx':
            merged_df.to_excel(output_path, index=False)
        else:
            merged_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    except Exception as e:
        return jsonify({'error': f'Errore salvataggio: {str(e)}'}), 500
    
    # Prepara preview dei dati
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
    """
    Download del file mergato
    """
    filepath = os.path.join(app.config['MERGED_FOLDER'], secure_filename(filename))
    
    if os.path.exists(filepath):
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename
        )
    
    return jsonify({'error': 'File non trovato'}), 404


@app.route('/columns', methods=['POST'])
def get_columns():
    """
    Restituisce le colonne comuni tra i file selezionati
    Utile per scegliere le colonne chiave per la deduplicazione
    """
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
    
    # Trova colonne comuni a tutti i file
    common_columns = list(set.intersection(*all_columns))
    
    # Ordina per rilevanza (colonne LinkedIn-like prima)
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
    """
    Pulisce i file temporanei
    """
    # Pulisci uploads
    for f in os.listdir(app.config['UPLOAD_FOLDER']):
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f))
        except:
            pass
    
    return jsonify({'message': 'File temporanei eliminati'})


@app.route('/history')
def get_history():
    """
    Restituisce la lista dei file già mergati
    """
    merged_files = []
    
    for f in os.listdir(app.config['MERGED_FOLDER']):
        filepath = os.path.join(app.config['MERGED_FOLDER'], f)
        stat = os.stat(filepath)
        merged_files.append({
            'filename': f,
            'size': stat.st_size,
            'created': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        })
    
    # Ordina per data creazione (più recente prima)
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
