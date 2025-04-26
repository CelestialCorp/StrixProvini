# Importazioni necessarie
import os
import json
from datetime import datetime
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask, render_template, request, redirect, url_for, session
import threading

# Configurazione Flask e variabili globali
# Setup Flask
app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Cambia questa chiave con una più sicura!

DATA_FILE = 'provini.json'
USERNAME = 'admin'
PASSWORD = 'password'

# Rotte principali
@app.route('/')
def home():
    # Reindirizza alla dashboard o al login
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Gestisce il login dell'utente
    if request.method == 'POST':
        if request.form['username'] == USERNAME and request.form['password'] == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return 'Credenziali non valide!'
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    # Mostra la dashboard privata (richiede login)
    if not 'logged_in' in session:
        return redirect(url_for('login'))
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
    else:
        data = {"in_attesa": []}

    # Ensure each member is a dictionary with 'name', 'date', and 'time' keys
    for i, member in enumerate(data.get("in_attesa", [])):
        if isinstance(member, str):
            data["in_attesa"][i] = {"name": member, "date": "", "time": ""}

    return render_template('dashboard.html', in_attesa=data.get("in_attesa", []))

@app.route('/public_dashboard')
def public_dashboard():
    # Mostra la dashboard pubblica (senza login)
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
    else:
        data = {"in_attesa": []}

    return render_template('dashboard.html', in_attesa=data.get("in_attesa", []), public=True)

@app.route('/logout')
def logout():
    # Effettua il logout dell'utente
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# Rotte per la gestione dei membri
@app.route('/add_member', methods=['POST'])
def add_member():
    # Aggiunge un membro alla lista dei provini
    if not 'logged_in' in session:
        return redirect(url_for('login'))
    member_id = request.form['member_id']
    member_date = request.form['member_date']
    member_time = request.form['member_time']
    data = carica_provini()
    if not any(member['name'] == member_id for member in data['in_attesa']):
        data['in_attesa'].append({"name": member_id, "date": member_date, "time": member_time})
        salva_provini(data)
    return redirect(url_for('dashboard'))

@app.route('/remove_member', methods=['POST'])
def remove_member():
    # Rimuove un membro dalla lista dei provini
    if not 'logged_in' in session:
        return redirect(url_for('login'))
    member_id = request.form['member_id']
    data = carica_provini()
    data = ensure_provini_structure(data)

    # Rimuovi il membro dalla lista
    data['in_attesa'] = [member for member in data['in_attesa'] if member['name'] != member_id]

    # Salva i dati aggiornati
    salva_provini(data)

    return redirect(url_for('dashboard'))

# Rotte per la gestione dei nickname
@app.route('/update_nicknames', methods=['POST'])
def update_nicknames():
    # Aggiorna i nickname dei membri (disabilitato)
    if not 'logged_in' in session:
        return redirect(url_for('login'))

    # Rimuoviamo la logica di conversione ID a nome
    return redirect(url_for('dashboard'))

@app.route('/resolve_nicknames', methods=['POST'])
def resolve_nicknames():
    # Risolve i nickname basati su ID Discord
    if not 'logged_in' in session:
        return redirect(url_for('login'))

    guild_id = os.getenv("GUILD_ID")
    if not guild_id:
        return "GUILD_ID non configurato.", 500

    guild = discord.utils.get(bot.guilds, id=int(guild_id))
    if not guild:
        return "Server Discord non trovato.", 404

    data = carica_provini()
    for member in data['in_attesa']:
        if member['name'].startswith("<@") and member['name'].endswith(">"):
            user_id = int(member['name'][2:-1])
            discord_member = guild.get_member(user_id)
            if discord_member:
                member['name'] = discord_member.display_name

    salva_provini(data)
    return redirect(url_for('dashboard'))

# Rotte per esportazione e feedback
@app.route('/export_data')
def export_data():
    # Esporta i dati dei provini in formato CSV
    if not 'logged_in' in session:
        return redirect(url_for('login'))

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
    else:
        data = {"in_attesa": []}

    # Creazione del file CSV
    csv_content = "Nome,Data,Orario\n"
    for member in data.get("in_attesa", []):
        csv_content += f"{member['name']},{member.get('date', '')},{member.get('time', '')}\n"

    # Restituzione del file CSV come risposta
    return (csv_content, 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename="provini.csv"'
    })

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    # Salva il feedback inviato dagli utenti
    if not 'logged_in' in session:
        return redirect(url_for('login'))

    feedback = request.form.get('feedback', '').strip()
    if feedback:
        # Salva il feedback in un file o database
        with open('feedback.txt', 'a') as f:
            f.write(f"{datetime.now().isoformat()} - {feedback}\n")

    return redirect(url_for('dashboard'))

@app.route('/feedback')
def feedback():
    # Mostra i feedback inviati
    if not 'logged_in' in session:
        return redirect(url_for('login'))

    # Leggi i feedback dal file
    if os.path.exists('feedback.txt'):
        with open('feedback.txt', 'r') as f:
            feedback_lines = f.readlines()
        # Modifica il formato del feedback per mostrare solo la data e il messaggio
        feedback_lines = [f"{line.split('T')[0]} - {line.split(' - ', 1)[1]}" for line in feedback_lines]
    else:
        feedback_lines = []

    return render_template('feedback.html', feedback_lines=feedback_lines)

@app.route('/export')
def export_page():
    # Mostra la pagina per esportare i dati
    if not 'logged_in' in session:
        return redirect(url_for('login'))

    return render_template('export.html')

@app.route('/classifica')
def classifica():
    # Mostra la classifica dei voti
    if not 'logged_in' in session:
        return redirect(url_for('login'))

    # Carica i dati della classifica
    if os.path.exists('classifica.json'):
        with open('classifica.json', 'r') as f:
            classifica_data = json.load(f)
    else:
        classifica_data = []

    return render_template('classifica.html', classifica=classifica_data)

# Funzioni di utilità
@app.context_processor
def inject_nicknames():
    # Funzione per risolvere i nickname
    def resolve_nickname(name):
        if name.startswith("<@") and name.endswith(">"):
            guild_id = os.getenv("GUILD_ID")
            if not guild_id:
                return name

            guild = discord.utils.get(bot.guilds, id=int(guild_id))
            if not guild:
                return name

            user_id = int(name[2:-1])
            member = guild.get_member(user_id)
            if member:
                return member.display_name
        return name

    return dict(resolve_nickname=resolve_nickname)

# Funzioni per la gestione dei file
PROVINI_FILE = "provini.json"
ROLE_MEMBRI_ID = 1213221604436217887
ROLE_PROVINI_ID = 1276989508679634954

def carica_provini():
    # Carica i dati dei provini dal file JSON
    if not os.path.exists(PROVINI_FILE):
        return {"in_attesa": []}
    with open(PROVINI_FILE, "r") as f:
        return json.load(f)

def salva_provini(data):
    # Salva i dati dei provini nel file JSON
    with open(PROVINI_FILE, "w") as f:
        json.dump(data, f, indent=4)

def ensure_provini_structure(data):
    # Garantisce la struttura corretta dei dati dei provini
    """Garantisce che ogni elemento in 'in_attesa' sia un dizionario con le chiavi 'name', 'date', e 'time'."""
    for i, member in enumerate(data.get("in_attesa", [])):
        if isinstance(member, str):
            data["in_attesa"][i] = {"name": member, "date": "", "time": ""}
    return data

# Configurazione del bot Discord
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
provini_in_attesa = carica_provini()["in_attesa"]

# Eventi e comandi del bot Discord
@bot.event
async def on_ready():
    # Evento eseguito quando il bot è pronto
    print(f"{bot.user} è online!")
    activity = discord.Activity(type=discord.ActivityType.watching, name="Provini su STRIX!")
    await bot.change_presence(activity=activity)
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizzati {len(synced)} comandi slash.")
    except Exception as e:
        print(f"Errore durante la sincronizzazione: {e}")

@bot.tree.command(name="ping", description="Controlla se il bot è online.")
async def ping(interaction: discord.Interaction):
    # Comando per verificare lo stato del bot
    await interaction.response.send_message("🏓 Pong! Il bot è attivo!")

@bot.tree.command(name="membri", description="Mostra tutti i membri del team STRIX!")
async def membri(interaction: discord.Interaction):
    # Mostra i membri del team con un ruolo specifico
    role = discord.utils.get(interaction.guild.roles, id=ROLE_MEMBRI_ID)
    if not role:
        await interaction.response.send_message(f"Ruolo con ID `{ROLE_MEMBRI_ID}` non trovato.", ephemeral=True)
        return
    membri = [member.mention for member in interaction.guild.members if role in member.roles]
    if not membri:
        await interaction.response.send_message("Nessun membro con questo ruolo al momento.", ephemeral=True)
    else:
        await interaction.response.send_message(
            f"👥 Membri del team STRIX `{role.name}`:\n" + "\n".join(membri)
        )

@bot.tree.command(name="voto_media", description="Valuta un utente per il provino (1-10 per abilità).")
async def voto_media(interaction: discord.Interaction, nome_utente: str, voto_mira: int, voto_edit: int, voto_freebuild: int, voto_partita: int, voto_facoltativo: int = 0):
    # Calcola e salva il voto medio di un utente
    voti = [voto_mira, voto_edit, voto_freebuild, voto_partita]
    if voto_facoltativo > 0:
        voti.append(voto_facoltativo)

    # Se uno dei voti non è valido (1-10), rispondi SUBITO ed esci
    if not all(1 <= voto <= 10 for voto in voti):
        await interaction.response.send_message("⚠️ I voti devono essere tra 1 e 10.", ephemeral=True)
        return

    # Se tutti i voti sono corretti, calcola media e rispondi
    media = round(sum(voti) / len(voti))
    if media >= 5:
        msg = f"✅ {nome_utente}, benvenuto ufficialmente nel team con voto: **{media}**!"
    else:
        msg = f"❌ {nome_utente}, non hai superato il provino (voto: **{media}**), ma fai comunque parte del team!"

    # Salva i dati nella classifica
    if os.path.exists('classifica.json'):
        with open('classifica.json', 'r') as f:
            classifica_data = json.load(f)
    else:
        classifica_data = []

    classifica_data.append({"name": nome_utente, "media": media})

    with open('classifica.json', 'w') as f:
        json.dump(classifica_data, f, indent=4)

    await interaction.response.send_message(msg)

@bot.tree.command(name="provini", description="Mostra lo stato dei provini.")
async def provini(interaction: discord.Interaction):
    # Mostra lo stato dei provini
    role = discord.utils.get(interaction.guild.roles, id=ROLE_PROVINI_ID)
    if not role:
        await interaction.response.send_message(f"Ruolo con ID `{ROLE_PROVINI_ID}` non trovato.", ephemeral=True)
        return
    members = [member for member in interaction.guild.members if role in member.roles]
    verified = [f"{m.mention} = ✔" for m in members if "completato" in m.display_name.lower()]
    not_verified = [f"{m.mention} = X" for m in members if "completato" not in m.display_name.lower()]
    risposta = (
        "**📋 Stato Provini:**\n"
        "✔ = Completato\n"
        "X = Da fare\n\n"
        + "\n".join(verified + not_verified)
    )
    await interaction.response.send_message(risposta)

@bot.tree.command(name="appuntamenti", description="Gestisci la lista dei provini.")
@app_commands.describe(aggiungi="ID da aggiungere", orario="Orario del provino (HH:MM)", data="Data del provino (DD/MM/YYYY)", rimuovi="ID da rimuovere")
async def appuntamenti(interaction: discord.Interaction, aggiungi: str = None, orario: str = None, data: str = None, rimuovi: str = None):
    # Gestisce l'aggiunta e la rimozione di appuntamenti
    data_provini = carica_provini()
    data_provini = ensure_provini_structure(data_provini)

    if aggiungi and rimuovi:
        await interaction.response.send_message("❌ Non puoi aggiungere e rimuovere contemporaneamente.", ephemeral=True)
        return

    if aggiungi:
        if not data or not orario:
            await interaction.response.send_message("📅 Devi fornire sia la data che l'orario.", ephemeral=True)
            return
        try:
            datetime.strptime(data, "%d/%m/%Y")
            datetime.strptime(orario, "%H:%M")
        except ValueError:
            await interaction.response.send_message("📅 Formato errato. Usa DD/MM/YYYY per la data e HH:MM per l'orario.", ephemeral=True)
            return

        if any(member['name'] == aggiungi for member in data_provini["in_attesa"]):
            await interaction.response.send_message(f"⚠️ `{aggiungi}` è già in lista.", ephemeral=True)
        else:
            data_provini["in_attesa"].append({"name": aggiungi, "date": data, "time": orario})
            salva_provini(data_provini)
            await interaction.response.send_message(f"✅ `{aggiungi}` aggiunto alla lista con data {data} e orario {orario}.", ephemeral=True)

            # Messaggio di conferma dettagliato
            await interaction.followup.send(
                f"📆 **Ciao {aggiungi}!**\n"
                f"Il tuo provino è programmato per il **{data}** alle **{orario}**.\n\n"
                "**Dettagli:**\n"
                "- Modalità: Creativa & Battaglia Reale\n"
                "- Durata: ~40 min\n\n"
                "✨ Potresti essere il prossimo player STRIX!"
            )
        return

    if rimuovi:
        if any(member['name'] == rimuovi for member in data_provini["in_attesa"]):
            data_provini["in_attesa"] = [member for member in data_provini["in_attesa"] if member['name'] != rimuovi]
            salva_provini(data_provini)
            await interaction.response.send_message(f"✅ `{rimuovi}` rimosso dalla lista.", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ `{rimuovi}` non trovato nella lista.", ephemeral=True)
        return

    # Mostra la lista se non ci sono parametri
    lista = data_provini["in_attesa"]
    if not lista:
        await interaction.response.send_message("🎉 Nessun membro in attesa!", ephemeral=True)
    else:
        embed = discord.Embed(
            title="📅 Membri in attesa di provino",
            description="\n".join(f"- {member['name']} (Data: {member['date']}, Orario: {member['time']})" for member in lista),
            color=discord.Color.orange()
        )
        embed.set_footer(text="Usa /appuntamenti per gestire la lista.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="aiuto", description="Mostra tutti i comandi disponibili.")
async def aiuto(interaction: discord.Interaction):
    # Mostra una lista di comandi disponibili
    embed = discord.Embed(
        title="🤖 Comandi disponibili",
        description="Ecco i comandi che puoi usare con il bot STRIX:",
        color=discord.Color.blue()
    )
    comandi = {
        "/membri": "Mostra i membri del team STRIX",
        "/voto_media": "Valuta un utente per il provino",
        "/provini": "Mostra lo stato dei provini",
        "/appuntamenti": "Gestisci la lista dei provini",
    }
    for nome, desc in comandi.items():
        embed.add_field(name=nome, value=desc, inline=False)
    embed.set_footer(text="Contattaci per supporto!   |   Creato da @gatto_six")
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_message(message):
    # Evento eseguito per ogni messaggio ricevuto
    await bot.process_commands(message)
    if message.author == bot.user:
        return
    if message.content.lower() == 'p':
        risposta = (
            f"Ciao {message.author.mention}!\n"
            "Ecco come verrai valutato:\n"
            "- **MIRA** 🔫\n"
            "- **EDIT** ✏️\n"
            "- **FREE BUILD** 🧱\n"
            "- **PARTITA** 🔥\n\n"
            "**Punteggio alto?** Potresti entrare in STRIX!"
        )
        await message.channel.send(risposta)

# Avvio del bot e del server Flask
def run_flask():
    # Avvia il server Flask
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    # Avvia il bot Discord e il server Flask
    threading.Thread(target=run_flask).start()
    bot.run(os.getenv("TOKEN"))