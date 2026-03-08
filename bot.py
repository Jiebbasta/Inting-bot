import os
import discord
from discord.ext import commands
from discord import app_commands

intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Comandi sincronizzati: {len(synced)}")
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


token = os.getenv("DISCORD_TOKEN")
if not token:
    raise RuntimeError("Variabile DISCORD_TOKEN non trovata.")

bot.run(token)