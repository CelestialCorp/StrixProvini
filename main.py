import os
import json
from datetime import datetime
from dotenv import load_dotenv
from keep_alive import keep_alive
import discord
from discord.ext import commands
from discord import app_commands

# Costanti
PROVINI_FILE = "provini.json"
ROLE_MEMBRI_ID = 1213221604436217887
ROLE_PROVINI_ID = 1276989508679634954

# Caricamento e salvataggio JSON
def carica_provini():
    if not os.path.exists(PROVINI_FILE):
        return {"in_attesa": []}
    with open(PROVINI_FILE, "r") as f:
        return json.load(f)

def salva_provini(data):
    with open(PROVINI_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Setup ambiente e server
load_dotenv()
keep_alive()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Variabile globale per i provini
provini_in_attesa = carica_provini()["in_attesa"]

@bot.event
async def on_ready():
    print(f"{bot.user} è online!")
    activity = discord.Activity(type=discord.ActivityType.watching, name="Provini su STRIX!")
    await bot.change_presence(activity=activity)
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizzati {len(synced)} comandi slash.")
    except Exception as e:
        print(f"Errore durante la sincronizzazione: {e}")

# ---------------- COMANDI ---------------- #

@bot.tree.command(name="membri", description="Mostra tutti i membri del team STRIX!")
async def membri(interaction: discord.Interaction):
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
    voti = [voto_mira, voto_edit, voto_freebuild, voto_partita]
    if voto_facoltativo > 0:
        voti.append(voto_facoltativo)

    if not all(1 <= voto <= 10 for voto in voti):
        await interaction.response.send_message("⚠️ I voti devono essere tra 1 e 10.", ephemeral=True)
        return

    media = round(sum(voti) / len(voti))
    if media >= 5:
        msg = f"✅ {nome_utente}, benvenuto ufficialmente nel team con voto: **{media}**!"
    else:
        msg = f"❌ {nome_utente}, non hai superato il provino (voto: **{media}**), ma fai comunque parte del team!"
    await interaction.response.send_message(msg)

@bot.tree.command(name="data", description="Programma un provino per un utente.")
async def data(interaction: discord.Interaction, nome_utente: str, orario: str, data: str):
    try:
        datetime.strptime(data, "%d/%m/%Y")
        datetime.strptime(orario, "%H:%M")
    except ValueError:
        await interaction.response.send_message("📅 Formato errato. Usa DD/MM/YYYY e HH:MM.", ephemeral=True)
        return

    msg = (
        f"📆 **Ciao {nome_utente}!**\n"
        f"Il tuo provino è programmato per il **{data}** alle **{orario}**.\n\n"
        "**Dettagli:**\n- Modalità: Creativa & Battaglia Reale\n- Durata: ~40 min\n\n"
        "✨ Potresti essere il prossimo player STRIX!"
    )
    await interaction.response.send_message(msg)

    if nome_utente not in provini_in_attesa:
        provini_in_attesa.append(nome_utente)
        salva_provini({"in_attesa": provini_in_attesa})
        await interaction.channel.send(f"✅ {nome_utente} aggiunto alla lista dei provini.")
    else:
        await interaction.channel.send(f"⚠️ {nome_utente} è già in lista.")

@bot.tree.command(name="provini", description="Mostra lo stato dei provini.")
async def provini(interaction: discord.Interaction):
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
@app_commands.describe(aggiungi="Nome da aggiungere", rimuovi="Nome da rimuovere")
async def appuntamenti(interaction: discord.Interaction, aggiungi: str = None, rimuovi: str = None):
    data = carica_provini()

    if aggiungi:
        if aggiungi in data["in_attesa"]:
            await interaction.response.send_message(f"⚠️ `{aggiungi}` è già in lista.", ephemeral=True)
        else:
            data["in_attesa"].append(aggiungi)
            salva_provini(data)
            await interaction.response.send_message(f"✅ `{aggiungi}` aggiunto alla lista.")
        return

    if rimuovi:
        if rimuovi in data["in_attesa"]:
            data["in_attesa"].remove(rimuovi)
            salva_provini(data)
            await interaction.response.send_message(f"✅ `{rimuovi}` rimosso dalla lista.")
        else:
            await interaction.response.send_message(f"⚠️ `{rimuovi}` non trovato nella lista.", ephemeral=True)
        return

    lista = data["in_attesa"]
    if not lista:
        await interaction.response.send_message("🎉 Nessun membro in attesa!", ephemeral=True)
    else:
        embed = discord.Embed(
            title="📅 Membri in attesa di provino",
            description="\n".join(f"- {nome}" for nome in lista),
            color=discord.Color.orange()
        )
        embed.set_footer(text="Usa /appuntamenti per gestire la lista.")
        await interaction.response.send_message(embed=embed)

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
        "/data": "Programma un provino",
        "/provini": "Mostra lo stato dei provini",
        "/appuntamenti": "Gestisci la lista dei provini",
    }
    for nome, desc in comandi.items():
        embed.add_field(name=nome, value=desc, inline=False)
    embed.set_footer(text="Contattaci per supporto!")
    await interaction.response.send_message(embed=embed)

# ---------------- EVENTO MESSAGGI ---------------- #

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.lower() == 'p':
        risposta = (
            f"Ciao {message.author.mention}!\n"
            "Ecco come verrai valutato:\n"
            "- **MIRA** 🔫\n"
            "- **EDIT** ✏️\n"
            "- **FREE BUILD** 🧱\n"
            "Successivamente, 1v1 contro i giudici!\n\n"
            "**Punteggio tra 7-8:** Partita BR con **10 eliminazioni**\n"
            "**Punteggio tra 9-10:** Partita Ranked con **6 eliminazioni**\n\n"
            "**Scrivi il tuo ID di Fortnite per iniziare!**"
        )
        await message.channel.send(risposta)

    await bot.process_commands(message)

# Avvio del bot
bot.run(os.getenv("TOKEN"))
