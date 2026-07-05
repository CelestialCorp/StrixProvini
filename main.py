"""
Application principale STRIX Provini - Flask + Discord Bot Unificato.
Integrato: SQLite, pulsanti di approvazione/rifiuto su Discord, rimozione legacy JSON.
"""

import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord import app_commands, ui
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import threading

# Caricamento configurazioni
load_dotenv()

# Setup Flask
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'strix-secret-key-12345')

# Configurazione database SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///strixprovini.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modelli Database SQLite
class Provino(db.Model):
    __tablename__ = 'provini'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    date = db.Column(db.String(50), nullable=True)
    time = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(50), default="In attesa")  # "In attesa", "Approvato", "Rifiutato"

class Classifica(db.Model):
    __tablename__ = 'classifica'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    media = db.Column(db.Integer, nullable=False)

class FeedbackEntry(db.Model):
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

# Inizializza Database
with app.app_context():
    db.create_all()

# Credenziali amministratore da variabili d'ambiente
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')

# Ruoli e canali Discord
ROLE_MEMBRI_ID = int(os.getenv('ROLE_MEMBRI_ID', 1213221604436217887))
ROLE_PROVINI_ID = int(os.getenv('ROLE_PROVINI_ID', 1276989508679634954))
STAFF_CHANNEL_ID = int(os.getenv('STAFF_CHANNEL_ID', 1264161415166427187))

# Configurazione del bot Discord unificato
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Componente UI per l'approvazione e il rifiuto rapido
class ProvinoActionView(ui.View):
    def __init__(self, provino_name: str, provino_id: int):
        super().__init__(timeout=None)
        self.provino_name = provino_name
        self.provino_id = provino_id

    @ui.button(label="Accetta ✅", style=discord.ButtonStyle.green, custom_id="accept_provino")
    async def accept(self, interaction: discord.Interaction, button: ui.Button):
        # Disabilita l'interazione per evitare clic multipli
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)

        # Esegui aggiornamento DB nel contesto thread-safe
        with app.app_context():
            provino = Provino.query.get(self.provino_id)
            if provino:
                provino.status = "Approvato"
                db.session.commit()

        # Assegna il ruolo e manda DM
        guild = interaction.guild
        member = None
        
        # Cerca il membro per nome/ID se è un tag o id numerico
        try:
            if self.provino_name.startswith("<@") and self.provino_name.endswith(">"):
                user_id = int(self.provino_name[2:-1].replace("!", ""))
                member = await guild.fetch_member(user_id)
            elif self.provino_name.isdigit():
                member = await guild.fetch_member(int(self.provino_name))
            else:
                # Cerca per nome utente testuale
                member = discord.utils.get(guild.members, name=self.provino_name)
        except Exception:
            pass

        role = guild.get_role(ROLE_MEMBRI_ID)
        role_assigned = False
        if member and role:
            try:
                await member.add_roles(role)
                role_assigned = True
            except Exception as e:
                print(f"Errore nell'assegnare il ruolo: {e}")

        # Invia messaggio privato
        dm_sent = False
        if member:
            try:
                await member.send(f"🎉 **Congratulazioni {member.display_name}!** Il tuo provino per il team STRIX è stato **Approvato**! Benvenuto tra noi!")
                dm_sent = True
            except Exception as e:
                print(f"Errore nell'inviare il DM: {e}")

        status_msg = f"✅ Provino per **{self.provino_name}** approvato da {interaction.user.mention}."
        if role_assigned:
            status_msg += f"\nRuolo {role.name} assegnato con successo."
        if dm_sent:
            status_msg += "\nMessaggio privato inviato con successo."
        else:
            status_msg += "\nNon è stato possibile inviare il DM privato."

        await interaction.response.send_message(status_msg)

    @ui.button(label="Rifiuta ❌", style=discord.ButtonStyle.red, custom_id="reject_provino")
    async def reject(self, interaction: discord.Interaction, button: ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)

        # Esegui aggiornamento DB
        with app.app_context():
            provino = Provino.query.get(self.provino_id)
            if provino:
                provino.status = "Rifiutato"
                db.session.commit()

        # Cerca membro per invio DM
        guild = interaction.guild
        member = None
        try:
            if self.provino_name.startswith("<@") and self.provino_name.endswith(">"):
                user_id = int(self.provino_name[2:-1].replace("!", ""))
                member = await guild.fetch_member(user_id)
            elif self.provino_name.isdigit():
                member = await guild.fetch_member(int(self.provino_name))
            else:
                member = discord.utils.get(guild.members, name=self.provino_name)
        except Exception:
            pass

        dm_sent = False
        if member:
            try:
                await member.send(f"❌ Ciao {member.display_name}, ci dispiace informarti che il tuo provino per il team STRIX è stato **Rifiutato**. Non mollare, potrai riprovare in futuro!")
                dm_sent = True
            except Exception as e:
                print(f"Errore nell'inviare il DM: {e}")

        status_msg = f"❌ Provino per **{self.provino_name}** rifiutato da {interaction.user.mention}."
        if dm_sent:
            status_msg += "\nMessaggio privato inviato."
        
        await interaction.response.send_message(status_msg)


# Funzione ausiliaria per inviare notifiche su Discord in modo asincrono e thread-safe
def notify_discord_new_provino(provino_name, provino_id, date, time):
    if not bot.is_ready():
        return

    async def send_embed():
        channel = bot.get_channel(STAFF_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="📋 Nuovo Provino Registrato!",
                description=f"Un nuovo provino è stato inserito sul sito web.",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Candidato", value=provino_name, inline=False)
            embed.add_field(name="Data provino", value=date or "Non specificata", inline=True)
            embed.add_field(name="Orario", value=time or "Non specificato", inline=True)
            embed.set_footer(text="Usa i pulsanti sottostanti per gestire il candidato")

            view = ProvinoActionView(provino_name, provino_id)
            await channel.send(embed=embed, view=view)

    # Invia la coroutine al loop di eventi in cui gira il bot Discord
    asyncio.run_coroutine_threadsafe(send_embed(), bot.loop)


# Rotte principali Flask
@app.route('/')
def home():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            flash('Login effettuato con successo.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Credenziali non valide!', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    try:
        provini = Provino.query.all()
        in_attesa = [p for p in provini if p.status == "In attesa"]
        completati_count = sum(1 for p in provini if p.status == "Approvato")
        in_attesa_count = len(in_attesa)
        rifiutati_count = sum(1 for p in provini if p.status == "Rifiutato")
    except Exception as e:
        flash(f'Errore nel recuperare i provini: {e}', 'danger')
        in_attesa = []
        completati_count, in_attesa_count, rifiutati_count = 0, 0, 0
    return render_template('dashboard.html', 
                           in_attesa=in_attesa, 
                           completati_count=completati_count, 
                           in_attesa_count=in_attesa_count, 
                           rifiutati_count=rifiutati_count)

@app.route('/public_dashboard')
def public_dashboard():
    try:
        provini = Provino.query.all()
        in_attesa = [p for p in provini if p.status == "In attesa"]
        completati_count = sum(1 for p in provini if p.status == "Approvato")
        in_attesa_count = len(in_attesa)
        rifiutati_count = sum(1 for p in provini if p.status == "Rifiutato")
    except Exception as e:
        flash(f'Errore nel recuperare i provini: {e}', 'danger')
        in_attesa = []
        completati_count, in_attesa_count, rifiutati_count = 0, 0, 0
    return render_template('dashboard.html', 
                           in_attesa=in_attesa, 
                           completati_count=completati_count, 
                           in_attesa_count=in_attesa_count, 
                           rifiutati_count=rifiutati_count,
                           public=True)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/add_member', methods=['POST'])
def add_member():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    member_id = request.form.get('member_id', '').strip()
    member_date = request.form.get('member_date', '').strip()
    member_time = request.form.get('member_time', '').strip()
    if not member_id:
        flash('ID membro obbligatorio.', 'warning')
        return redirect(url_for('dashboard'))
    try:
        exists = Provino.query.filter_by(name=member_id).first()
        if not exists:
            new_provino = Provino(name=member_id, date=member_date, time=member_time)
            db.session.add(new_provino)
            db.session.commit()
            flash('Membro aggiunto con successo.', 'success')

            # Notifica automatica asincrona al bot Discord con i pulsanti interattivi
            notify_discord_new_provino(new_provino.name, new_provino.id, new_provino.date, new_provino.time)
        else:
            flash('Membro già presente.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante l\'aggiunta: {e}', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/remove_member', methods=['POST'])
def remove_member():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    member_id = request.form.get('member_id', '').strip()
    try:
        # Trova il provino
        provino = Provino.query.filter_by(name=member_id).first()
        
        # Elimina il provino se esiste
        if provino:
            db.session.delete(provino)
            
        # Hard Delete: cancella anche tutti i record con lo stesso nome dalla Classifica
        classifica_items = Classifica.query.filter_by(name=member_id).all()
        for item in classifica_items:
            db.session.delete(item)
            
        db.session.commit()
        if provino or classifica_items:
            flash('Membro eliminato completamente dal sistema (provini e classifiche).', 'success')
        else:
            flash('Membro non trovato nel sistema.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante la rimozione totale del membro: {e}', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/admin/elimina-membro-totalmente/<int:provino_id>', methods=['POST'])
def elimina_membro_totalmente(provino_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    try:
        provino = Provino.query.get(provino_id)
        if provino:
            nome_membro = provino.name

            # ---------- DATABASE ----------
            # 1. Rimuovi il provino
            db.session.delete(provino)

            # 2. Rimuovi dalla Classifica (voti e statistiche)
            classifica_items = Classifica.query.filter_by(name=nome_membro).all()
            for item in classifica_items:
                db.session.delete(item)

            # 3. Rimuovi eventuali feedback associati (se il contenuto contiene il nome)
            feedback_items = FeedbackEntry.query.filter(FeedbackEntry.content.contains(nome_membro)).all()
            for fb in feedback_items:
                db.session.delete(fb)

            db.session.commit()

            # ---------- DISCORD ----------
            async def remove_roles():
                # Debug: stampa l'ID/username che stiamo per processare
                print(f"[DEBUG] Inizio rimozione ruoli per provino nome: {nome_membro}")
                try:
                    # Recupera il guild dal bot usando l'ID del server (GUILD_ID)
                    guild_id = os.getenv('GUILD_ID')
                    if not guild_id:
                        print("[DEBUG] GUILD_ID non impostato nella .env")
                        return
                    guild = bot.get_guild(int(guild_id))
                    if not guild:
                        print(f"[DEBUG] Guild con ID {guild_id} non trovato")
                        return

                    # --- Ricerca membro tramite ID numerico univoco ---
                    user_id = None
                    if nome_membro.startswith('<@') and nome_membro.endswith('>'):
                        # estrai ID da mention
                        user_id = int(nome_membro[2:-1].replace('!', ''))
                    elif nome_membro.isdigit():
                        user_id = int(nome_membro)
                    else:
                        # Se il nome non è un ID, non possiamo garantire la ricerca; loggiamo e abortiamo
                        print(f"[DEBUG] Nome provino '{nome_membro}' non è un ID Discord, salto rimozione ruolo")
                        return

                    print(f"[DEBUG] Tentativo di rimozione ruoli per utente ID: {user_id}")
                    # fetch_member garantisce una ricerca sul server anche se non in cache
                    try:
                        member = guild.get_member(user_id) or await guild.fetch_member(user_id)
                    except Exception as e:
                        print(f"[DEBUG] Errore fetch_member per ID {user_id}: {e}")
                        return

                    if not member:
                        print(f"[DEBUG] Membro con ID {user_id} non trovato nel guild")
                        return

                    # Rimuovi i ruoli "Membri" e "Provini" se presenti
                    role_membri = guild.get_role(int(ROLE_MEMBRI_ID))
                    role_provini = guild.get_role(int(ROLE_PROVINI_ID))
                    try:
                        if role_membri and role_membri in member.roles:
                            await member.remove_roles(role_membri)
                            print(f"[DEBUG] Ruolo Membri rimosso da {member.display_name}")
                        if role_provini and role_provini in member.roles:
                            await member.remove_roles(role_provini)
                            print(f"[DEBUG] Ruolo Provini rimosso da {member.display_name}")
                    except Exception as e:
                        # Log ma non interrompere la procedura
                        print(f"[DEBUG] Errore nella rimozione dei ruoli Discord: {e}")
                except Exception as e:
                    # Gestione generica di errori (es. membro non più nel server)
                    print(f"[DEBUG] Errore nella sincronizzazione Discord per {nome_membro}: {e}")

            # Esegui la coroutine in modo thread‑safe
            asyncio.run_coroutine_threadsafe(remove_roles(), bot.loop)

            flash(f'Membro "{nome_membro}" cancellato DEFINITIVAMENTE da ogni tabella del database e privato dei ruoli su Discord.', 'success')
        else:
            flash('Provino non trovato.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante l\'eliminazione radicale del membro: {e}', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/export_data')
def export_data():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    try:
        provini = Provino.query.all()
    except Exception as e:
        flash(f'Errore nell\'esportare i dati: {e}', 'danger')
        provini = []
    csv_content = "Nome,Data,Orario,Stato\n"
    for p in provini:
        csv_content += f"{p.name},{p.date or ''},{p.time or ''},{p.status}\n"
    return (csv_content, 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename="provini.csv"'
    })

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    feedback_text = request.form.get('feedback', '').strip()
    if feedback_text:
        try:
            entry = FeedbackEntry(content=feedback_text)
            db.session.add(entry)
            db.session.commit()
            flash('Feedback inviato con successo!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Errore nel salvare il feedback: {e}', 'danger')
    return redirect(url_for('feedback'))

@app.route('/feedback')
def feedback():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    try:
        feedback_entries = FeedbackEntry.query.order_by(FeedbackEntry.date.desc()).all()
    except Exception as e:
        flash(f'Errore nel caricare i feedback: {e}', 'danger')
        feedback_entries = []
    return render_template('feedback.html', feedback_entries=feedback_entries)

@app.route('/export')
def export_page():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('export.html')

@app.route('/classifica')
def classifica():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    try:
        classifica_data = Classifica.query.all()
    except Exception as e:
        flash(f'Errore nel caricare la classifica: {e}', 'danger')
        classifica_data = []
    return render_template('classifica.html', classifica=classifica_data)

@app.route('/admin/elimina-voto/<int:voto_id>', methods=['POST'])
def elimina_voto(voto_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    try:
        voto = Classifica.query.get(voto_id)
        if voto:
            db.session.delete(voto)
            db.session.commit()
            flash('Voto/classificazione eliminato con successo!', 'success')
        else:
            flash('Voto non trovato.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante l\'eliminazione del voto: {e}', 'danger')
    return redirect(url_for('classifica'))

@app.route('/admin/elimina-feedback/<int:feedback_id>', methods=['POST'])
def elimina_feedback(feedback_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    try:
        feedback_entry = FeedbackEntry.query.get(feedback_id)
        if feedback_entry:
            db.session.delete(feedback_entry)
            db.session.commit()
            flash('Feedback eliminato con successo!', 'success')
        else:
            flash('Feedback non trovato.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante l\'eliminazione del feedback: {e}', 'danger')
    return redirect(url_for('feedback'))


# Bottone per invio votazione da pannello web
@app.route('/votazione', methods=['GET', 'POST'])
def votazione():
    if request.method == 'POST':
        nome_utente = request.form['nome_utente']
        voto_mira = int(request.form['voto_mira'])
        voto_edit = int(request.form['voto_edit'])
        voto_freebuild = int(request.form['voto_freebuild'])
        voto_partita = int(request.form['voto_partita'])
        voto_facoltativo = request.form.get('voto_facoltativo')

        voti = [voto_mira, voto_edit, voto_freebuild, voto_partita]
        if voto_facoltativo:
            voti.append(int(voto_facoltativo))
        media = round(sum(voti) / len(voti))

        if media >= 5:
            msg = f"{nome_utente}, benvenuto ufficialmente nel team con voto: **{media}**!"
        else:
            msg = f"{nome_utente}, non hai superato il provino ma sei ufficialmente nel team con voto: **{media}**!"

        # Inserisci nella classifica del DB
        try:
            nuovo_voto = Classifica(name=nome_utente, media=media)
            db.session.add(nuovo_voto)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Errore nel salvare in classifica: {e}")

        # Invio asincrono del messaggio sul canale Discord utilizzando il bot principale già avviato
        async def send_voto_msg():
            channel = bot.get_channel(STAFF_CHANNEL_ID)
            if channel:
                await channel.send(msg)

        asyncio.run_coroutine_threadsafe(send_voto_msg(), bot.loop)

        return f"Messaggio inviato e salvato a DB: {msg}"

    return render_template('votazione.html')


# Context processor per la risoluzione dei nickname Discord sui template HTML
@app.context_processor
def inject_nicknames():
    def resolve_nickname(name):
        if name.startswith("<@") and name.endswith(">"):
            guild_id = os.getenv("GUILD_ID")
            if not guild_id:
                return name
            guild = discord.utils.get(bot.guilds, id=int(guild_id))
            if not guild:
                return name
            try:
                user_id = int(name[2:-1].replace("!", ""))
                member = guild.get_member(user_id)
                if member:
                    return member.display_name
            except Exception:
                pass
        return name
    return dict(resolve_nickname=resolve_nickname)


# Eventi e comandi del bot Discord
@bot.event
async def on_ready():
    print(f"{bot.user} è online e pronto!")
    activity = discord.Activity(type=discord.ActivityType.watching, name="Provini su STRIX!")
    await bot.change_presence(activity=activity)
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizzati {len(synced)} comandi slash.")
    except Exception as e:
        print(f"Errore durante la sincronizzazione dei comandi slash: {e}")

@bot.tree.command(name="ping", description="Controlla se il bot è online.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong! Il bot è attivo!")

@bot.tree.command(name="membri", description="Mostra tutti i membri del team STRIX!")
async def membri(interaction: discord.Interaction):
    role = discord.utils.get(interaction.guild.roles, id=ROLE_MEMBRI_ID)
    if not role:
        await interaction.response.send_message(f"Ruolo con ID `{ROLE_MEMBRI_ID}` non trovato.", ephemeral=True)
        return
    membri_list = [member.mention for member in interaction.guild.members if role in member.roles]
    if not membri_list:
        await interaction.response.send_message("Nessun membro con questo ruolo al momento.", ephemeral=True)
    else:
        await interaction.response.send_message(
            f"👥 Membri del team STRIX `{role.name}`:\n" + "\n".join(membri_list)
        )

@bot.tree.command(name="voto_media", description="Valuta un utente per il provino (1-10 per abilità).")
async def voto_media(interaction: discord.Interaction, nome_utente: str, voto_mira: int, voto_edit: int, voto_freebuild: int, voto_partita: int, voto_facoltativo: int = 0):
    voti = [voto_mira, voto_edit, voto_freebuild, voto_partita]
    if voto_facoltativo > 0:
        voti.append(voto_facoltativo)

    if not all(1 <= voto <= 10 for voto in voti):
        await interaction.response.send_message("⚠️ I voti devono essere tra 1 e 10.", ephemeral=True)
        return

    media = round(sum(voti) / len(voti))
    if media >= 5:
        msg = f"{nome_utente}, benvenuto ufficialmente nel team con voto: **{media}**!"
    else:
        msg = f"{nome_utente}, non hai superato il provino ma sei ufficialmente nel team con voto: **{media}**!"

    # Salva nel DB SQLite classifica
    with app.app_context():
        nuova_classifica = Classifica(name=nome_utente, media=media)
        db.session.add(nuova_classifica)
        db.session.commit()

    await interaction.response.send_message(msg)

@bot.tree.command(name="provini", description="Mostra lo stato dei provini.")
async def provini_command(interaction: discord.Interaction):
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

@bot.tree.command(name="appuntamenti", description="Gestisci la lista dei provini nel DB.")
@app_commands.describe(aggiungi="ID da aggiungere", orario="Orario del provino (HH:MM)", data="Data del provino (DD/MM/YYYY)", rimuovi="ID da rimuovere")
async def appuntamenti(interaction: discord.Interaction, aggiungi: str = None, orario: str = None, data: str = None, rimuovi: str = None):
    if aggiungi and rimuovi:
        await interaction.response.send_message("❌ Non puoi aggiungere e rimuovere contemporaneamente.", ephemeral=True)
        return

    if aggiungi:
        if not data or not orario:
            await interaction.response.send_message("📅 Devi fornire sia la data che l'orario.", ephemeral=True)
            return
        
        # Inserimento nel database SQLite
        with app.app_context():
            exists = Provino.query.filter_by(name=aggiungi).first()
            if exists:
                await interaction.response.send_message(f"⚠️ `{aggiungi}` è già in lista.", ephemeral=True)
                return
            
            nuovo = Provino(name=aggiungi, date=data, time=orario)
            db.session.add(nuovo)
            db.session.commit()
            prov_id = nuovo.id

        await interaction.response.send_message(f"✅ `{aggiungi}` aggiunto alla lista con data {data} e orario {orario}.", ephemeral=True)

        # Messaggio di conferma dettagliato in chat e notifica automatica con bottoni
        await interaction.followup.send(
            f"   **Ciao {aggiungi}!**\n"
            f"Il tuo provino è programmato per il **{data}** alle **{orario}**.\n\n"
            "**Dettagli:**\n"
            "- Modalità: Creativa & Battaglia Reale\n"
            "- Durata: ~40 min\n\n"
            "✨ Potresti essere il prossimo player STRIX!"
        )
        # Notifica staff asincrona con bottoni
        notify_discord_new_provino(aggiungi, prov_id, data, orario)
        return

    if rimuovi:
        with app.app_context():
            provino = Provino.query.filter_by(name=rimuovi).first()
            if provino:
                db.session.delete(provino)
                db.session.commit()
                await interaction.response.send_message(f"✅ `{rimuovi}` rimosso dalla lista dei provini.", ephemeral=True)
            else:
                await interaction.response.send_message(f"⚠️ `{rimuovi}` non trovato.", ephemeral=True)
        return

    # Mostra la lista dal Database SQLite
    with app.app_context():
        lista = Provino.query.all()

    if not lista:
        await interaction.response.send_message("🎉 Nessun membro in attesa!", ephemeral=True)
    else:
        embed = discord.Embed(
            title="📅 Membri in attesa di provino",
            description="\n".join(f"- {p.name} (Data: {p.date or 'TBD'}, Orario: {p.time or 'TBD'}, Stato: {p.status})" for p in lista),
            color=discord.Color.orange()
        )
        embed.set_footer(text="Usa /appuntamenti per gestire la lista.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="aiuto", description="Mostra tutti i comandi disponibili.")
async def aiuto(interaction: discord.Interaction):
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
    await bot.process_commands(message)
    if message.author == bot.user:
        return
    if message.content.lower() == 'p':
        embed = discord.Embed(
            title="🎯Ecco come funzionano i Provini!",
            description=(
                f"Ciao {message.author.mention}!\n\n"
                "**I provini per entrare nel team STRIX si svolgeranno in due fasi:**\n\n"
                "**⋆༺𓆩PROVE INIZIALI𓆪༻⋆**\n\n"
                "Verranno valutate le seguenti abilità, ciascuna con un punteggio da 1 a 10:\n\n"
                "- **🔫 MIRA**\n"
                "- **✏️ EDIT**\n"
                "- **🧱 FREE BUILD**\n\n"
                "**Successivamente, affronterete un 1v1 in due round contro ogni giudice presente, che valuterà le vostre capacità di combattimento.**\n\n"
                "**⫘⫘⫘⫘⫘⫘⫘⫘⫘⫘⫘⫘**\n\n"
                "**⋆༺𓆩PROVE FINALI𓆪༻⋆**\n\n"
                "- **Punteggio tra 7 e 8:** Gioca una partita in Battaglia Reale con obiettivo 10 eliminazioni.\n"
                "- **Punteggio tra 9 e 10:** Gioca una partita classificata (RANKED) con obiettivo 6 eliminazioni.\n\n"
                "**⫘⫘⫘⫘⫘⫘⫘⫘⫘⫘⫘⫘**\n\n"
                "**⋆༺𓆩VALUTAZIONE𓆪༻⋆**\n\n"
                "- Se superi la prova, la media verrà aumentata; altrimenti sarà ridotta.\n"
                "- Anche chi ottiene un punteggio inferiore a 5 farà parte del team!\n\n"
                "**⫘⫘⫘⫘⫘⫘⫘⫘⫘⫘⫘⫘**\n\n"
                "Al più presto riceverai orario e data!\n"
                "**Scrivi il tuo ID di Fortnite!**"
            ),
            color=discord.Color.blue()
        )
        embed.set_image(url="https://tenor.com/view/red-banner-gif-26193040")
        await message.channel.send(embed=embed)


# Funzione di avvio di Flask in thread separato
def run_flask():
    app.run(host="0.0.0.0", port=8080, use_reloader=False)


if __name__ == "__main__":
    # Avvia Flask in un thread dedicato
    threading.Thread(target=run_flask, daemon=True).start()
    # Avvia il Bot Discord principale
    token = os.getenv("TOKEN") or os.getenv("DISCORD_BOT_TOKEN")
    if token:
        bot.run(token)
    else:
        print("Errore: Nessun Token Discord trovato in .env!")
