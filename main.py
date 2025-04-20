import os
from dotenv import load_dotenv
from keep_alive import keep_alive
import discord
from discord.ext import commands
from discord import app_commands
import json

PROVINI_FILE = "provini.json"

def carica_provini():
    if not os.path.exists(PROVINI_FILE):
        return {"in_attesa": []}
    with open(PROVINI_FILE, "r") as f:
        return json.load(f)

def salva_provini(data):
    with open(PROVINI_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Carica le variabili d'ambiente dal file .env
load_dotenv()

# Avvia il server Flask per mantenere vivo il bot
keep_alive()

# Configurazione del bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Necessario per ottenere tutti i membri del server

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} è online e pronto!")
    activity = discord.Activity(type=discord.ActivityType.watching, name="Provini su STRIX!")
    await bot.change_presence(activity=activity)
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizzati {len(synced)} comandi slash.")
    except Exception as e:
        print(f"Errore durante la sincronizzazione dei comandi: {e}")

# Comando /membri
@bot.tree.command(name="membri", description="Mostra tutti i membri del team STRIX!")
async def membri(interaction: discord.Interaction):
    role_id = 1213221604436217887  # ID del ruolo
    guild = interaction.guild

    # Trova il ruolo tramite il suo ID
    role = discord.utils.get(guild.roles, id=role_id)

    if not role:
        await interaction.response.send_message(f"Il ruolo con ID `{role_id}` non è stato trovato nel server.", ephemeral=True)
        return

    members_with_role = [member for member in guild.members if role in member.roles]

    if not members_with_role:
        await interaction.response.send_message("Nessun membro ha questo ruolo al momento.", ephemeral=True)
        return

    membri_elenco = [member.mention for member in members_with_role]
    response = f"Membri del team STRIX `{role.name}`:\n\n" + "\n".join(membri_elenco)
    await interaction.response.send_message(response)

# Comando /voto_media
@bot.tree.command(name="voto_media", description="Valuta un utente per il provino (1-10 per ogni abilità).")
async def voto_media(interaction: discord.Interaction, nome_utente: str, voto_mira: int, voto_edit: int, voto_freebuild: int, voto_partita: int, voto_facoltativo: int = 0):
    voti = [voto_mira, voto_edit, voto_freebuild, voto_partita]
    if voto_facoltativo > 0:
        voti.append(voto_facoltativo)

    if not all(1 <= voto <= 10 for voto in voti):
        await interaction.response.send_message("I voti devono essere tra 1 e 10. Inserisci valori validi.", ephemeral=True)
        return

    media_voti = round(sum(voti) / len(voti))
    if media_voti >= 5:
        messaggio = f"{nome_utente}, benvenuto ufficialmente nel team con voto: {media_voti}!"
    else:
        messaggio = f"{nome_utente}, non hai superato il provino con voto: {media_voti}, ma fai comunque parte del team!"
    await interaction.response.send_message(messaggio)

# Comando /data
@bot.tree.command(name="data", description="Programma un provino per un utente.")
async def data(interaction: discord.Interaction, nome_utente: str, orario: str, data: str):
    messaggio_finale = (
        f"Ciao {nome_utente}!\n"
        f"Il tuo provino è programmato per il **{data}** alle **{orario}**.\n\n"
        "⚡ Dettagli:\n"
        "- Modalità: Creativa e Battaglia Reale/Ranked\n"
        "- Durata: Circa 40 minuti\n\n"
        "Non perdere l’occasione, potresti essere il prossimo player del nostro team!"
    )
    await interaction.response.send_message(messaggio_finale)

# Comando /provini
@bot.tree.command(name="provini", description="Mostra lo stato dei provini per i membri con un ruolo specifico.")
async def provini(interaction: discord.Interaction):
    role_id = 1276989508679634954  # ID del ruolo
    guild = interaction.guild
    role = discord.utils.get(guild.roles, id=role_id)

    if not role:
        await interaction.response.send_message(f"Il ruolo con ID `{role_id}` non è stato trovato nel server.", ephemeral=True)
        return

    members_with_role = [member for member in guild.members if role in member.roles]

    if not members_with_role:
        await interaction.response.send_message("Nessun membro ha questo ruolo al momento.", ephemeral=True)
        return

    verified = [f"{member.mention} = ✔" for member in members_with_role if "completato" in member.display_name.lower()]
    not_verified = [f"{member.mention} = X" for member in members_with_role if "completato" not in member.display_name.lower()]

    response = (
        "Membri che devono fare provino e non:\n"
        "✔ = Membri verificati\n"
        "X = Membri ancora non verificati\n\n"
        + "\n".join(verified + not_verified) +
        "\n\nPer i membri con (X), fissare un provino al più presto!"
    )
    await interaction.response.send_message(response)

# Comando /appuntamenti
@bot.tree.command(name="appuntamenti", description="Gestisci la lista dei provini (aggiungi, rimuovi, visualizza).")
@app_commands.describe(aggiungi="(Opzionale) Nome da aggiungere", rimuovi="(Opzionale) Nome da rimuovere")
async def appuntamenti(interaction: discord.Interaction, aggiungi: str = None, rimuovi: str = None):
    data = carica_provini()

    if aggiungi:
        if aggiungi in data["in_attesa"]:
            await interaction.response.send_message(f"⚠️ `{aggiungi}` è già nella lista.", ephemeral=True)
        else:
            data["in_attesa"].append(aggiungi)
            salva_provini(data)
            await interaction.response.send_message(f"✅ `{aggiungi}` è stato aggiunto alla lista dei provini.")
        return

    if rimuovi:
        if rimuovi in data["in_attesa"]:
            data["in_attesa"].remove(rimuovi)
            salva_provini(data)
            await interaction.response.send_message(f"✅ `{rimuovi}` rimosso dalla lista dei provini.")
        else:
            await interaction.response.send_message(f"⚠️ `{rimuovi}` non è nella lista.", ephemeral=True)
        return

    # Se non viene fornito né aggiungi né rimuovi, mostra la lista
    in_attesa = data["in_attesa"]
    if not in_attesa:
        await interaction.response.send_message("🎉 Nessun membro in attesa di provino!", ephemeral=True)
        return

    lista = "\n".join(f"- {nome}" for nome in in_attesa)
    embed = discord.Embed(
        title="📅 Membri in attesa di provino",
        description=f"**Lista:**\n{lista}",
        color=discord.Color.orange()
    )
    embed.set_footer(text="Usa /appuntamenti aggiungi:<nome> o rimuovi:<nome>")
    await interaction.response.send_message(embed=embed)

# Evento per messaggi
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

# Avvia il bot
bot.run(os.getenv('DISCORD_TOKEN'))
