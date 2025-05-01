# 🎤 StrixProvini

**StrixProvini** è un'applicazione web sviluppata in Python con Flask, progettata per gestire le audizioni (provini) all'interno di una community, come un server Discord. Il sistema consente di raccogliere candidature, assegnare feedback e visualizzare una classifica aggiornata dei partecipanti.

## 📁 Struttura del Progetto

```
StrixProvini/
│
├── main.py              # Script principale per l'esecuzione dell'app
├── requirements.txt     # Librerie Python richieste
├── classifica.json      # Dati della classifica
├── provini.json         # Dati dei provini inviati
├── feedback.txt         # Feedback salvati
│
├── templates/           # Template HTML (renderizzati da Flask)
└── static/              # File statici (CSS, immagini, JS)
```

## ⚙️ Requisiti

- Python 3.8+
- Flask

Installa i requisiti con:
```bash
pip install -r requirements.txt
```

## 🚀 Avvio dell'Applicazione

Clona il repository:
```bash
git clone https://github.com/CelestialCorp/StrixProvini.git
cd StrixProvini
```

Installa le dipendenze:
```bash
pip install -r requirements.txt
```

Avvia il server Flask:
```bash
python main.py
```

Accedi all'interfaccia web all'indirizzo:
```
http://localhost:5000
```

## ✅ Funzionalità Principali

- Invio candidature per i provini
- Visualizzazione della classifica aggiornata
- Gestione e salvataggio dei feedback
- Interfaccia utente semplice e immediata

## 📄 Licenza

Questo progetto è distribuito sotto licenza MIT.

## 👥 Autori

Sviluppato da CelestialCorp – GitHub
