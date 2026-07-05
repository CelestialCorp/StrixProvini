# 🦉 StrixProvini: Ecosistema Integrato per la Gestione dei Provini Community 🚀

StrixProvini è una soluzione completa che integra un'applicazione web Flask e un Bot Discord avanzato, pensata per semplificare e automatizzare la gestione dei provini e delle audizioni all'interno di community online, in particolare server Discord. Offre un'interfaccia sicura per lo staff e un'esperienza utente fluida per i partecipanti, garantendo trasparenza e reattività.

## ✨ Funzionalità Principali

- 🌐 **Dashboard Web Protetta**: Un'interfaccia Flask intuitiva e sicura per lo staff, accessibile tramite credenziali protette, per gestire tutti gli aspetti dei provini.
- 📊 **Grafico Statistiche in Tempo Reale**: Visualizzazione dinamica delle performance dei provini e delle tendenze, per analisi immediate.
- 🗄️ **Database SQLite Sicuro**: Tutti i dati dei provini, votazioni e feedback sono archiviati in un database SQLite locale, garantendo persistenza e sicurezza tramite Flask-SQLAlchemy.
- 🔔 **Notifiche Embed Automatiche su Discord**: Il Bot Discord invia notifiche eleganti e informative direttamente in un canale staff dedicato, con tutti i dettagli del provino.
-  кнопки **Pulsanti Interattivi Accetta/Rifiuta**: Lo staff può interagire direttamente con le notifiche Discord tramite pulsanti, per accettare o rifiutare un provino con un solo click, senza lasciare Discord.
- 📥 **Esportazione Dati**: Possibilità di esportare i dati del database per analisi esterne o backup.

## 📁 Struttura del Progetto

```
StrixProvini/
│
├── .env                 # Variabili d'ambiente sensibili (TOKEN Discord, chiavi segrete, credenziali)
├── main.py              # Script principale: avvia l'app Flask e il Bot Discord
├── requirements.txt     # Tutte le librerie Python necessarie
├── instance/            # Cartella per il database SQLite (ad esempio, instance/site.db)
│   └── site.db          # Database SQLite del progetto
│
├── templates/           # File HTML per l'interfaccia Flask
│   ├── base.html
│   ├── classifica.html
│   ├── dashboard.html
│   ├── export.html
│   ├── feedback.html
│   ├── login.html
│   └── votazione.html
│
└── static/              # File statici (CSS, JavaScript, immagini)
    └── style.css
```

## ⚙️ Installazione e Configurazione Locale

Segui questi passaggi per configurare e avviare il progetto in locale.

### 1. Clonazione del Repository

Apri il terminale e clona il repository:

```bash
git clone https://github.com/CelestialCorp/StrixProvini.git
cd StrixProvini
```

### 2. Installazione dei Requisiti

Installa tutte le dipendenze Python necessarie utilizzando `pip`:

```bash
pip install -r requirements.txt
```

### 3. Configurazione del File `.env`

Crea un file `.env` nella directory principale del progetto (la stessa di `main.py`) e configuralo con le seguenti variabili. Assicurati di non condividere questo file pubblicamente.

```ini
FLASK_SECRET_KEY='la_tua_chiave_segreta_flask_qui' # Genera una chiave complessa per la sicurezza di Flask
ADMIN_USERNAME='admin'                             # Username per l'accesso alla dashboard web
ADMIN_PASSWORD='password_sicura'                   # Password per l'accesso alla dashboard web
TOKEN='IL_TUO_TOKEN_BOT_DISCORD'                   # Token del tuo Bot Discord (ottienilo dal Discord Developer Portal)
GUILD_ID=123456789012345678                        # ID del tuo server Discord (Guild ID)
STAFF_CHANNEL_ID=987654321098765432                # ID del canale Discord dove verranno inviate le notifiche per lo staff
ROLE_MEMBRI_ID=112233445566778899                  # ID del ruolo che gli utenti devono avere per poter interagire col bot/sistema
```

**Come ottenere gli ID di Discord (Guild, Channel, Role):**
1. Abilita la Modalità Sviluppatore nelle impostazioni di Discord (Utente -> Impostazioni App -> Avanzate).
2. Clicca con il tasto destro sul server, canale o ruolo e seleziona "Copia ID".

### 4. Inizializzazione del Database

Prima del primo avvio, è necessario inizializzare il database SQLite. Apri la shell di Python nella directory principale del progetto:

```bash
python
```

All'interno della shell di Python, esegui i seguenti comandi:

```python
from main import app, db
with app.app_context():
    db.create_all()
    print("Database inizializzato!")
exit()
```

Questo creerà il file `site.db` all'interno della cartella `instance/`.

### 5. Avvio dell'Applicazione

Dopo aver configurato il file `.env` e inizializzato il database, puoi avviare l'applicazione. Esegui questo comando nella directory principale del progetto:

```bash
python main.py
```

L'applicazione Flask sarà disponibile su `http://127.0.0.1:5000` (o altra porta se configurata), e il Bot Discord si connetterà automaticamente.

## 📄 Licenza

Questo progetto è distribuito sotto licenza MIT. Vedi il file `LICENSE` per maggiori dettagli.

## 👥 Autori

- ([Gatto] (https://github.com/CelestialCorp)) – Sviluppatore principale.
