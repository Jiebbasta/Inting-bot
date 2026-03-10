import os
import discord
import json
import calendar
from datetime import datetime
from discord.ext import tasks
from discord.ext import commands
from discord import app_commands

GUILD_ID = 1479164434197778442

intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

BIRTHDAYS_FILE = "birthdays.json"
BIRTHDAY_SETTINGS_FILE = "birthday_settings.json"
BIRTHDAY_SENT_FILE = "birthday_sent.json"


def load_json(filename, default):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


birthdays = load_json(BIRTHDAYS_FILE, {})
birthday_settings = load_json(BIRTHDAY_SETTINGS_FILE, {})
birthday_sent = load_json(BIRTHDAY_SENT_FILE, {})


MONTHS = [
    ("Gennaio", 1),
    ("Febbraio", 2),
    ("Marzo", 3),
    ("Aprile", 4),
    ("Maggio", 5),
    ("Giugno", 6),
    ("Luglio", 7),
    ("Agosto", 8),
    ("Settembre", 9),
    ("Ottobre", 10),
    ("Novembre", 11),
    ("Dicembre", 12),
]

@bot.event
async def on_ready():
    try:
        guild = discord.Object(id=GUILD_ID)

        # pulisce eventuali comandi guild vecchi
        bot.tree.clear_commands(guild=guild)

        # ricopia i comandi globali nella tua guild
        bot.tree.copy_global_to(guild=guild)

        # sincronizza nella tua guild
        synced = await bot.tree.sync(guild=guild)

        print(f"Comandi sincronizzati nella guild: {len(synced)}")
        print("Comandi registrati:", [cmd.name for cmd in synced])

    except Exception as e:
        print(f"Errore sync comandi: {e}")

    print(f"Bot online come {bot.user}")

    if not birthday_checker.is_running():
        birthday_checker.start()

class MonthSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=month_name, value=str(month_number))
            for month_name, month_number in MONTHS
        ]
        super().__init__(placeholder="Seleziona il mese", options=options)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        view.selected_month = int(self.values[0])
        await interaction.response.edit_message(view=view)

class DaySelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=str(day), value=str(day)) for day in range(1, 32)]
        super().__init__(placeholder="Seleziona il giorno", options=options)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        view.selected_day = int(self.values[0])
        await interaction.response.edit_message(view=view)

class SaveBirthdayButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Salva compleanno", style=discord.ButtonStyle.green)

    async def callback(self, interaction: discord.Interaction):
        view = self.view

        if view.selected_month is None or view.selected_day is None:
            await interaction.response.send_message(
                "Devi selezionare sia il mese sia il giorno.",
                ephemeral=True
            )
            return

        user_id = str(interaction.user.id)

        birthdays[user_id] = {
            "month": view.selected_month,
            "day": view.selected_day
        }

        save_json(BIRTHDAYS_FILE, birthdays)

        await interaction.response.send_message(
            f"Compleanno salvato: **{view.selected_day:02d}/{view.selected_month:02d}**",
            ephemeral=True
        )

class BirthdayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

        self.selected_month = None
        self.selected_day = None

        self.add_item(MonthSelect())
        self.add_item(DaySelect())
        self.add_item(SaveBirthdayButton())

@bot.tree.command(
    name="sposta_tutti",
    description="Sposta tutti gli utenti da una voice channel a un'altra"
)
@app_commands.describe(
    sorgente="Canale vocale da cui spostare gli utenti",
    destinazione="Canale vocale in cui spostarli"
)
@app_commands.default_permissions(administrator=True)
async def sposta_tutti(
    interaction: discord.Interaction,
    sorgente: discord.VoiceChannel,
    destinazione: discord.VoiceChannel
):
    # controllo lato Discord + controllo lato codice
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "Non hai i permessi per usare questo comando.",
            ephemeral=True
        )
        return

    if sorgente.id == destinazione.id:
        await interaction.response.send_message(
            "Sorgente e destinazione non possono essere uguali.",
            ephemeral=True
        )
        return

    membri = list(sorgente.members)

    if not membri:
        await interaction.response.send_message(
            f"Non c'è nessuno in {sorgente.mention}.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    spostati = 0
    errori = []

    for membro in membri:
        try:
            await membro.move_to(
                destinazione,
                reason=f"Spostamento richiesto da {interaction.user}"
            )
            spostati += 1
        except discord.Forbidden:
            errori.append(membro.display_name)
        except discord.HTTPException:
            errori.append(membro.display_name)

    msg = (
        f"Ho spostato **{spostati}** utenti "
        f"da {sorgente.mention} a {destinazione.mention}."
    )

    if errori:
        msg += "\n\nNon sono riuscito a spostare:\n- " + "\n- ".join(errori[:10])
        if len(errori) > 10:
            msg += f"\n...e altri {len(errori) - 10}"

    await interaction.followup.send(msg, ephemeral=True)
    
@bot.tree.command(
    name="crea_torneo",
    description="Crea la struttura dei canali per un torneo"
)
@app_commands.describe(
    squadre="Numero di squadre del torneo"
)
@app_commands.default_permissions(administrator=True)
async def crea_torneo(interaction: discord.Interaction, squadre: int):

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "Non hai i permessi per usare questo comando.",
            ephemeral=True
        )
        return

    guild = interaction.guild

    await interaction.response.defer()

    # crea categoria
    categoria = await guild.create_category("🏆 TORNEO")

    # lobby principale
    await guild.create_voice_channel(
        name="🟢 Lobby",
        category=categoria
    )

    # crea team
    for i in range(1, squadre + 1):
        await guild.create_voice_channel(
            name=f"🔊 Team {i}",
            category=categoria
        )

    # canali extra
    await guild.create_voice_channel(
        name="🎙️ Casting",
        category=categoria
    )

    await guild.create_voice_channel(
        name="⏳ Attesa",
        category=categoria
    )

    await interaction.followup.send(
        f"Struttura torneo creata con **{squadre} squadre**."
    )

@bot.tree.command(
    name="chiudi_torneo",
    description="Elimina tutti i canali del torneo"
)
@app_commands.default_permissions(administrator=True)
async def chiudi_torneo(interaction: discord.Interaction):

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "Non hai i permessi per usare questo comando.",
            ephemeral=True
        )
        return

    guild = interaction.guild

    await interaction.response.defer()

    categoria = discord.utils.get(guild.categories, name="🏆 TORNEO")

    if not categoria:
        await interaction.followup.send(
            "Non ho trovato la categoria del torneo.",
            ephemeral=True
        )
        return

    # elimina tutti i canali nella categoria
    for canale in categoria.channels:
        await canale.delete()

    # elimina la categoria
    await categoria.delete()

    await interaction.followup.send(
        "Torneo chiuso e tutti i canali eliminati."
    )

@bot.tree.command(
    name="sposta_qui",
    description="Sposta tutti gli utenti di un canale nella tua voice"
)
@app_commands.describe(
    sorgente="Canale vocale da cui spostare gli utenti"
)
@app_commands.default_permissions(administrator=True)
async def sposta_qui(
    interaction: discord.Interaction,
    sorgente: discord.VoiceChannel
):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "Non hai i permessi per usare questo comando.",
            ephemeral=True
        )
        return

    if not isinstance(interaction.user, discord.Member) or not interaction.user.voice:
        await interaction.response.send_message(
            "Devi essere in un canale vocale per usare questo comando.",
            ephemeral=True
        )
        return

    destinazione = interaction.user.voice.channel

    if sorgente.id == destinazione.id:
        await interaction.response.send_message(
            "Sei già in quel canale.",
            ephemeral=True
        )
        return

    membri = list(sorgente.members)

    if not membri:
        await interaction.response.send_message(
            f"Non c'è nessuno in {sorgente.mention}.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    spostati = 0
    errori = []

    for membro in membri:
        try:
            await membro.move_to(
                destinazione,
                reason=f"Spostamento richiesto da {interaction.user}"
            )
            spostati += 1
        except discord.Forbidden:
            errori.append(membro.display_name)
        except discord.HTTPException:
            errori.append(membro.display_name)

    msg = (
        f"Ho spostato **{spostati}** utenti "
        f"da {sorgente.mention} a {destinazione.mention}."
    )

    if errori:
        msg += "\n\nNon sono riuscito a spostare:\n- " + "\n- ".join(errori[:10])
        if len(errori) > 10:
            msg += f"\n...e altri {len(errori) - 10}"

    await interaction.followup.send(msg, ephemeral=True)

@bot.tree.command(
    name="compleanno",
    description="Imposta il tuo compleanno"
)
async def compleanno(interaction: discord.Interaction):

    await interaction.response.send_message(
        "Seleziona mese e giorno del tuo compleanno:",
        view=BirthdayView(),
        ephemeral=True
    )

@bot.tree.command(
    name="set_birthday_chat",
    description="Imposta il canale degli auguri"
)
@app_commands.default_permissions(administrator=True)
async def set_birthday_chat(interaction: discord.Interaction, canale: discord.TextChannel):

    guild_id = str(interaction.guild.id)

    if guild_id not in birthday_settings:
        birthday_settings[guild_id] = {}

    birthday_settings[guild_id]["channel_id"] = canale.id

    save_json(BIRTHDAY_SETTINGS_FILE, birthday_settings)

    await interaction.response.send_message(
        f"Canale compleanni impostato su {canale.mention}",
        ephemeral=True
    )

@bot.tree.command(
    name="set_birthday_message",
    description="Imposta il messaggio di compleanno"
)
@app_commands.default_permissions(administrator=True)
async def set_birthday_message(interaction: discord.Interaction, messaggio: str):

    guild_id = str(interaction.guild.id)

    if guild_id not in birthday_settings:
        birthday_settings[guild_id] = {}

    birthday_settings[guild_id]["message"] = messaggio

    save_json(BIRTHDAY_SETTINGS_FILE, birthday_settings)

    await interaction.response.send_message(
        "Messaggio compleanno salvato.",
        ephemeral=True
    )

@tasks.loop(hours=24)
async def birthday_checker():
    today = datetime.utcnow()
    today_key = today.strftime("%m-%d")

    if today_key not in birthday_sent:
        birthday_sent[today_key] = []

    for guild in bot.guilds:
        guild_id = str(guild.id)
        settings = birthday_settings.get(guild_id)

        if not settings:
            continue

        channel = guild.get_channel(settings.get("channel_id"))

        if not channel:
            continue

        message_template = settings.get(
            "message",
            "🎉 Auguri di buon compleanno {user}! 🎂"
        )

        for user_id, data in birthdays.items():
            if data["month"] == today.month and data["day"] == today.day:
                member = guild.get_member(int(user_id))

                if member is None:
                    continue

                unique_key = f"{guild.id}-{member.id}"

                if unique_key in birthday_sent[today_key]:
                    continue

                message = message_template.replace("{user}", member.mention)

                await channel.send(message)

                birthday_sent[today_key].append(unique_key)
                save_json(BIRTHDAY_SENT_FILE, birthday_sent)

token = os.getenv("DISCORD_TOKEN")
if not token:
    raise RuntimeError("Variabile DISCORD_TOKEN non trovata.")

bot.run(token)
