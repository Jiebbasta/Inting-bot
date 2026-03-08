import os
import discord
from discord.ext import commands
from discord import app_commands

GUILD_ID = 1479164434197778442

intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

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

token = os.getenv("DISCORD_TOKEN")
if not token:
    raise RuntimeError("Variabile DISCORD_TOKEN non trovata.")

bot.run(token)

