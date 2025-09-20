from django.apps import apps
from allianceauth.services.hooks import get_extension_logger

logger = get_extension_logger(__name__)

## Use a small helper to check if AA-Discordbot is installs
def discord_bot_active():
        return apps.is_installed('aadiscordbot')

def send_message_to_discord(messages: list, channel_id: int, hours: int):   
    
    if channel_id is None:
        print("No channel ID provided")
        return

    ## Only import it, if it is installed
    if discord_bot_active():
        from aadiscordbot.tasks import send_message

        # if you want to send discord embed import them too.
        from discord import Embed, Color

        for (header, message) in messages:
                # Discord ID of channel
                e = Embed(title="Sales (last " + str(hours) + " hours): " + header,
                        #description="This is a Test Embed.\n\n```Discord User ID```",
                        #description="```Item XYZ 1x\nItem XYZ 1x```",
                        description=message,
                        color=Color.nitro_pink())
                #e.add_field(name="Test Field 1", value="Value of some kind goes here")

                send_message(channel_id=channel_id, embed=e) # Embed
                #send_message(channel_id=channel_id, message=message) # Message
                #send_message(channel_id=channel_id, message=message, embed=e) # Both