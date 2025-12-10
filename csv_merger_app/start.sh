#!/bin/bash
# Script di avvio per CSV/Excel Merger App (Linux/macOS)

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                   CSV/Excel Merger App                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Vai nella directory dello script
cd "$(dirname "$0")"

# Controlla se le dipendenze sono installate
if ! python3 -c "import flask" 2>/dev/null; then
    echo "📦 Installazione dipendenze..."
    pip3 install -r requirements.txt
fi

echo "🚀 Avvio server..."
echo "📍 Apri il browser su: http://localhost:5000"
echo "⏹  Premi CTRL+C per terminare"
echo ""

python3 app.py
