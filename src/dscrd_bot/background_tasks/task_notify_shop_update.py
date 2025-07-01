from asyncio import sleep

from discord import Bot
from discord.abc import GuildChannel

from crawler import Shop, ShopOffer
from dscrd_bot.embeds import DefaultEmbed
from dscrd_bot.persistent_data import Persistence, Server
from dscrd_bot.util import get_crawler


async def notify_new_offer(offer: ShopOffer, shop_section: str, channel: GuildChannel, server: Server) -> None:
    await channel.send(
        embed=DefaultEmbed(
            title=f"{shop_section} Update",
            description=(
                f"**{offer.name}** (*{offer.price} Cinders*) has been added to the shop."
            ),
            custom_title=server.embed_author,
            author_icon_url=server.embed_icon_url,
            image=offer.image_url
        )
    )


async def task_notify_shop_update(bot: Bot) -> None:
    shop: Shop = get_crawler().get_shop()
    shop_changed = not all(o.name in Persistence.get().shop_offers for o in shop.alices_deals + shop.seasonal_offers)
    if not shop_changed:
        return

    for server in Persistence.get().servers:
        try:
            if server.linked_team:
                channel: GuildChannel | None = bot.get_channel(int(server.linked_team.events_channel))
                if not channel:
                    continue  # No channel -> No notification -> can continue to next server

                for offer in shop.seasonal_offers:
                    if offer.name not in Persistence.get().shop_offers:
                        await notify_new_offer(offer, "Season Shop", channel, server)

                for offer in shop.alices_deals:
                    if offer.name not in Persistence.get().shop_offers:
                        await notify_new_offer(offer, "Alices Deals", channel, server)

            await sleep(.5)  # Give bot some time to handle more important stuff.
        except Exception as ex:
            # Must catch everything to avoid crash!
            print(f"Cannot notify server ({server.id}) for shop updates: {ex}")
