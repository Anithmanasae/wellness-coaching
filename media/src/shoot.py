import asyncio, os
from playwright.async_api import async_playwright

OUT = "media/screens"
NAMES = {"s1":"01-home","s2":"02-food","s3":"03-grocery","s4":"04-pharmacy","s5":"05-cart"}

async def main():
    os.makedirs(OUT, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        pg = await b.new_page(viewport={"width":390,"height":900}, device_scale_factor=3)
        await pg.goto("file://" + os.path.abspath("media/src/screens.html"))
        await pg.wait_for_timeout(600)
        for sid, name in NAMES.items():
            el = await pg.query_selector("#" + sid)
            path = f"{OUT}/{name}.png"
            await el.screenshot(path=path)
            box = await el.bounding_box()
            print(f"{name}.png  {int(box['width'])}x{int(box['height'])} css px")
        await b.close()

asyncio.run(main())
