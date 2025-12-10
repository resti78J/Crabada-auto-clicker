# LinkedIn CSV/Excel Merge Utility

Script locale per unire rapidamente gli export CSV/XLSX di LinkedIn mantenendo ogni ondata di download separata dalle precedenti. Ogni esecuzione genera un file con timestamp e un file di metadati, così puoi archiviare e ritrovare i merge effettuati senza sovrascrivere quelli vecchi.

## Requisiti
- Python 3.10 o superiore
- `pip` per installare le dipendenze elencate in `requirements.txt`

Installa le dipendenze una sola volta:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso rapido
1. Scarica manualmente i CSV (o XLSX) da LinkedIn e mettili in una cartella, ad esempio `imports/2025-12-10/`.
2. Avvia il merge assegnando un tag univoco alla “tranche” di download:

```bash
python merge_linkedin_exports.py imports/2025-12-10 --tag prima_tranche
```

3. Troverai l’output in `merged_runs/20251210-153045_prima_tranche.xlsx` (più un JSON con i metadati). I file precedenti restano intatti perché ogni run ha un nome diverso grazie al timestamp + tag.

## Opzioni principali
- `inputs`: uno o più file/cartelle. Con `--recursive` la cartella viene esplorata in profondità.
- `--tag`: etichetta per ricordare la provenienza (es. `settimana42`, `lead-milano`).
- `--output-dir`: dove salvare i merge (default: `merged_runs`).
- `--output-format`: `xlsx` (default) o `csv`.
- `--sheet-name`: nome del foglio se esporti in XLSX.
- `--encoding` e `--delimiter`: utili se i CSV usano separatori/charset diversi.
- `--dedupe-on col1 col2`: elimina i duplicati considerando solo certe colonne.

Esempio completo:

```bash
python merge_linkedin_exports.py \\
  inputs/settimana-50 \\
  --recursive \\
  --tag settimana_50 \\
  --output-format xlsx \\
  --dedupe-on \"Email Address\" \"First Name\"
```

## Cosa produce
- File dati (`.xlsx` o `.csv`) con tutte le righe normalizzate (colonne mancanti riempite con celle vuote) e colonna `_source_file` per sapere da quale export proviene ogni riga.
- File JSON di metadati con conteggio righe, elenco file usati e dedupe applicato. Puoi archiviarlo o caricarlo in strumenti di tracking.

## Flusso di lavoro consigliato
1. Scarica i nuovi export LinkedIn in una cartella nominata per data o campagna.
2. Lancia il merge indicando un nuovo `--tag`. Il timestamp automatico ti evita collisioni.
3. Subito dopo il merge, carica il file risultante dove ti serve (CRM, Google Sheets, ecc.).
4. Mantieni le cartelle originali: così puoi rilanciare il merge se LinkedIn cambia struttura colonne.

In questo modo i download successivi non vanno a contaminare quelli precedenti: restano separati sia negli input (cartelle diverse) sia negli output (file timestampati). *** End Patch