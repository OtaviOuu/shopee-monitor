import zendriver as uc
from zendriver import *
import json
import base64
from rich.console import Console
import aiofiles
import os
import aiohttp
import dotenv
import asyncio
import time
from typing import TypedDict, List


dotenv.load_dotenv(override=True)


class Book(TypedDict):
    name: str
    price: float
    link: str
    image: str
    images: List[str]



class ShopeeScraper:
    def __init__(self, browser):
        self.browser: Browser = browser
        self.latest_request_id = None
        self.page = None
        self.console = Console()

    async def _response_handler(self, event) -> None:
        if "api/v4/search/search_items" in event.response.url:
            self.console.print(
                f"[bold green]Capturado:[/bold green] {event.response.url}"
            )
            self.latest_request_id = event.request_id

    async def _get_response_body(self) -> None:
        if not self.latest_request_id:
            return

        cmd = uc.cdp.network.get_response_body(self.latest_request_id)
        response = await self.page.send(cmd)

        if response:
            body, is_base64 = response
            if is_base64:
                body = base64.b64decode(body)
            try:
                data = json.loads(body)
                return data
            except json.JSONDecodeError:
                self.console.print_exception()
                return

    async def in_db(self, book_name: str) -> bool:
        async with aiofiles.open("shopee.json", "r") as f:
            data = await f.read()
            data = json.loads(data)
            if book_name in data["items"]:
                return True
            return False
        
    async def send_notification(self, book: Book) -> None: 


        
        bot_token = os.getenv("BOT_TOKEN")
        chat_id = os.getenv("CHAT_ID")
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"

        image_url = book["image"]

        caption = (
            f"📚 *Lirvo Encontrado!*\n\n"
            f"🎓 *Título:* {book['name']}\n\n"
            f"💰 *Preço:* R${book['price']}\n\n"
            f"🔗 *Link:* [Clique aqui]({book['link']})\n\n"
        )

        data = {
            "chat_id": chat_id,
            "caption": caption,
            "parse_mode": "Markdown",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, data=data, params={"photo": image_url}
            ) as response:
                if response.status == 200:
                    print(f"Mensagem enviada com sucesso: {book['name']}")
                else:
                    print(f"Erro ao enviar mensagem: {response.status}")

    async def scrape(self, url: str) -> None:
        self.console.print(f"[bold green]Iniciando Scraper[/bold green]")
        self.page = await self.browser.get(url)
        self.page.add_handler(
            cdp.network.ResponseReceived, self._response_handler
        )
        await self.page.wait_for(
            selector=".row.shopee-search-item-result__items li"
        )
        await self.page.wait(t=4)
        items = await self._get_response_body()
            
        for item in items["items"]:
            item_data = item["item_basic"]

            item_name = item_data["name"]
            in_db = await self.in_db(item_name)
            if in_db:
                continue
            
            
            item_price = item_data["price"]
            item_image = item_data.get("image")
            item_images = item_data.get("images")
            item_id = item_data.get("itemid")
            item_shop_id = item_data.get("shopid")
            item_url = f"https://shopee.com.br/{item_name}-i.{item_shop_id}.{item_id}"

            book = {
                "name": item_name,
                "price": item_price / 100000,
                "link": item_url,
                "image": f"https://down-br.img.susercontent.com/file/{item_image}_tn.webp",
                "images": item_images
            }
            self.console.print(book)
            async with aiofiles.open("shopee.json", "r") as f:
                data = await f.read()
                data = json.loads(data)
            
                data["items"].append(item_name)
            
                async with aiofiles.open("shopee.json", "w") as f:
                    await f.write(json.dumps(data, indent=4, ensure_ascii=False))

            await self.send_notification(book)



async def main():
    target_store = "https://shopee.com.br/search?facet=11060478&page=0&sortBy=ctime"
    

    browser = await uc.start(
        headless=True,
        browser_executable_path="/snap/bin/chromium",
        user_data_dir="./uc-user-data",
    )

    shopee = ShopeeScraper(browser)
    await shopee.scrape(target_store)
    await browser.stop()


if __name__ == "__main__":
    while True:
        asyncio.run(main())
        time.sleep(100)
        