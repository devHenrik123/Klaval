from crawler import Shop
from dscrd_bot.persistent_data import Persistence
from dscrd_bot.util import get_crawler


async def task_persist_shop_state() -> None:
    shop: Shop = get_crawler().get_shop()
    Persistence.get().shop_offers = [offer.name for offer in shop.seasonal_offers + shop.alices_deals]
    Persistence.write()
