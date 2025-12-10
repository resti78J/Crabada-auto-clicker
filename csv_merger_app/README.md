# 📊 CSV/Excel Merger App

Applicazione web locale per unire file CSV ed Excel scaricati da LinkedIn, con **deduplicazione automatica** per evitare dati duplicati.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 🎯 Funzionalità Principali

- ✅ **Upload multiplo** - Carica più file CSV/Excel contemporaneamente
- ✅ **Deduplicazione intelligente** - Riconosce automaticamente i dati LinkedIn
- ✅ **Anteprima dati** - Visualizza i dati prima e dopo il merge
- ✅ **Statistiche** - Report dettagliato sui duplicati rimossi
- ✅ **Cronologia** - Accedi ai file mergati precedenti
- ✅ **Drag & Drop** - Interfaccia intuitiva
- ✅ **Esportazione flessibile** - CSV o Excel (XLSX)

---

## 🚀 Installazione Rapida

### Prerequisiti

- Python 3.8 o superiore
- pip (gestore pacchetti Python)

### Passaggi

1. **Entra nella cartella del progetto:**
   ```bash
   cd csv_merger_app
   ```

2. **Crea un ambiente virtuale (opzionale ma consigliato):**
   ```bash
   python -m venv venv
   
   # Su Windows:
   venv\Scripts\activate
   
   # Su macOS/Linux:
   source venv/bin/activate
   ```

3. **Installa le dipendenze:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Avvia l'applicazione:**
   
   **Metodo semplice (consigliato):**
   - Su **Windows**: Doppio click su `start.bat`
   - Su **macOS/Linux**: Esegui `./start.sh`
   
   **Metodo manuale:**
   ```bash
   python3 app.py
   ```

5. **Apri il browser:**
   Vai su **http://localhost:5000**

---

## 📖 Come Usare l'App

### Passo 1: Carica i File

- **Drag & Drop**: Trascina i tuoi file CSV/Excel direttamente sulla zona di upload
- **Sfoglia**: Clicca su "Sfoglia" per selezionare i file dal tuo computer
- Puoi caricare più file contemporaneamente

### Passo 2: Configura il Merge

#### Opzioni di Deduplicazione

- **Rimuovi duplicati** (default: ON)
  - Attivato: elimina le righe duplicate basandosi sulle colonne chiave
  - Disattivato: unisce tutti i file senza controllo duplicati

- **Auto-rileva colonne chiave LinkedIn** (default: ON)
  - L'app cerca automaticamente queste colonne (in ordine di priorità):
    1. `Profile URL` / `LinkedIn URL` (più affidabile)
    2. `Email`
    3. `Full Name` / `Name`
    4. `First Name` + `Last Name`

#### Selezione Manuale Colonne Chiave

Se disattivi l'auto-rilevamento, puoi selezionare manualmente le colonne da usare come chiave per identificare i duplicati.

#### Formato Output

- **CSV**: Compatibile con tutti i software
- **Excel (XLSX)**: Ideale per ulteriori elaborazioni

### Passo 3: Esegui il Merge

Clicca su **"Esegui Merge"** e attendi il completamento.

### Passo 4: Visualizza i Risultati

L'app mostra:
- **File processati**: numero di file uniti
- **Righe totali**: somma delle righe di tutti i file
- **Duplicati rimossi**: quante righe duplicate sono state eliminate
- **Righe finali**: numero di righe nel file finale
- **Anteprima**: prime 10 righe del risultato

### Passo 5: Scarica il File

Clicca su **"Scarica File Mergato"** per ottenere il file finale.

---

## 💡 Casi d'Uso Tipici

### Scenario 1: Merge Settimanale LinkedIn

1. Scarichi export settimanali da LinkedIn Sales Navigator
2. Carichi tutti i file nell'app
3. L'app usa `Profile URL` per identificare contatti unici
4. Ottieni un file pulito senza duplicati

### Scenario 2: Unione Liste Marketing

1. Hai più liste CSV da campagne diverse
2. Attivi la deduplicazione basata su `Email`
3. Ottieni una lista unificata con contatti unici

### Scenario 3: Merge Semplice (senza deduplicazione)

1. Disattiva "Rimuovi duplicati"
2. I file vengono semplicemente concatenati
3. Utile quando vuoi mantenere tutti i record

---

## 🛠 Struttura del Progetto

```
csv_merger_app/
├── app.py              # Backend Flask
├── requirements.txt    # Dipendenze Python
├── README.md           # Documentazione
├── start.sh            # Script avvio Linux/macOS
├── start.bat           # Script avvio Windows
├── templates/
│   └── index.html      # Interfaccia HTML
├── static/
│   ├── style.css       # Stili CSS
│   └── script.js       # Logica JavaScript
├── uploads/            # File caricati (temporanei)
└── merged/             # File mergati (output)
```

---

## ⚙️ Configurazione Avanzata

### Modifica Porta

Nel file `app.py`, modifica la linea finale:
```python
app.run(debug=True, host='0.0.0.0', port=5000)  # Cambia 5000 con la porta desiderata
```

### Dimensione Massima File

Nel file `app.py`, modifica:
```python
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB default
```

### Aggiungere Colonne Chiave LinkedIn

Nel file `app.py`, modifica la funzione `detect_linkedin_columns()` per aggiungere nuove colonne da riconoscere.

---

## 🔒 Privacy e Sicurezza

- **Dati locali**: Tutti i file rimangono sul tuo computer
- **Nessun upload esterno**: L'app funziona completamente offline
- **File temporanei**: I file caricati possono essere eliminati con "Rimuovi tutti"

---

## ❓ Risoluzione Problemi

### L'app non si avvia

```bash
# Verifica che Python sia installato
python3 --version

# Reinstalla le dipendenze
pip3 install -r requirements.txt --force-reinstall
```

### Errore di encoding CSV

L'app gestisce automaticamente diversi encoding (UTF-8, Latin-1, etc.). Se hai ancora problemi, prova ad aprire il CSV in Excel e salvarlo come "CSV UTF-8".

### File Excel non riconosciuto

Assicurati che il file abbia estensione `.xlsx` o `.xls` e che non sia corrotto.

### Duplicati non rimossi

Verifica che:
1. L'opzione "Rimuovi duplicati" sia attivata
2. Le colonne chiave siano corrette
3. I valori non abbiano spazi extra o differenze di maiuscole/minuscole

---

## 📝 Note Tecniche

- **Framework**: Flask (Python)
- **Elaborazione dati**: Pandas
- **Supporto Excel**: openpyxl, xlrd
- **Frontend**: HTML5, CSS3, JavaScript vanilla
- **Nessuna dipendenza da database**: tutto su file system

---

## 🆘 Supporto

Per problemi o suggerimenti, controlla il codice sorgente o modifica secondo le tue esigenze. L'app è progettata per essere semplice da personalizzare.

---

**Buon lavoro con i tuoi dati! 🚀**
