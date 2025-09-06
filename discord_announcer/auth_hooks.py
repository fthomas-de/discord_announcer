"""Hook into Alliance Auth"""

# Django
from django.utils.translation import gettext_lazy as _

# Alliance Auth
from allianceauth import hooks
from allianceauth.services.hooks import MenuItemHook, UrlHook

# AA DA App
from discord_announcer import urls


class DAMenuItem(MenuItemHook):
    """This class ensures only authorized users will see the menu entry"""

    def __init__(self):
        # setup menu entry for sidebar
        MenuItemHook.__init__(
            self,
            _("discord_announcer"),
            "fas fa-cube fa-fw",
            "discord_announcer:index",
            navactive=["discord_announcer:"],
        )

    def render(self, request):
        """Render the menu item"""

        if request.user.has_perm("discord_announcer.basic_access"):
            return MenuItemHook.render(self, request)

        return ""


@hooks.register("menu_item_hook")
def register_menu():
    """Register the menu item"""

    return DAMenuItem()


@hooks.register("url_hook")
def register_urls():
    """Register app urls"""

    return UrlHook(urls, "discord_announcer", r"^discord_announcer/")

@hooks.register('discord_cogs_hook')
def register_cogs():
    return ["discord_announcer.cogs.cog_a", "discord_announcer.cogs.cog_b"]
