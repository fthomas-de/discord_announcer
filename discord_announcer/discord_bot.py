from aadiscordbot.utils.auth import is_user_bot_admin, is_user_authenticated, get_discord_user_id, get_auth_user
from django.contrib.auth.models import User
from django.apps import apps

## Use a small helper to check if AA-Discordbot is installs
def discord_bot_active():
        return apps.is_installed('aadiscordbot')

def send_message_to_discord():
    print("1")
    
    ## Only import it, if it is installed
    if discord_bot_active():
        print("2")
        from aadiscordbot.tasks import send_message
        # if you want to send discord embed import them too.
        from discord import Embed, Color

        # Discord ID of channel
        msg = "User ID Tests"
        e = Embed(title="User ID Tests!",
                description="This is a Test Embed.\n\n```Discord User ID```",
                color=Color.nitro_pink())
        e.add_field(name="Test Field 1", value="Value of some kind goes here")

        channel_id = 1413885436366950582

        send_message(channel_id=channel_id, embed=e) # Embed
        #send_message(channel_id=channel_id, message=msg) # Message
        #send_message(channel_id=channel_id, message=msg, embed=e) # Both
        print("3")