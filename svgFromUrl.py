import os
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urljoin


async def fetch(session, url):
    async with session.get(url) as response:
        if response.status == 200:
            return await response.text()
        print(f"Failed to retrieve {url}. Status code: {response.status}")
        return None


async def download_image(session, img_url, download_dir):
    async with session.get(img_url) as response:
        if response.status == 200:
            path = os.path.join(download_dir, os.path.basename(img_url))
            with open(path, "wb") as file:
                file.write(await response.read())
            print(f"Downloaded {os.path.basename(img_url)}")
        else:
            print(f"Failed to download {img_url}. Status code: {response.status}")


async def download_embedded_svg(svg_code, index, download_dir):
    path = os.path.join(download_dir, f"embedded_svg_{index + 1}.svg")
    try:
        with open(path, "w", encoding="utf-8") as file:
            file.write(svg_code)
        #print(f"Saved embedded SVG as {path}")
    except Exception as e:
        print(f"Could not save embedded SVG: {e}")


async def download_all_svgs(url, download_dir="downloaded_svgs"):
    os.makedirs(download_dir, exist_ok=True)

    async with aiohttp.ClientSession() as session:
        html_content = await fetch(session, url)
        if not html_content:
            return

        soup = BeautifulSoup(html_content, "html.parser")

        tasks = []
        img_tags = soup.find_all("img", src=lambda x: x.endswith(".svg"))
        for img in img_tags:
            img_url = urljoin(url, img["src"])
            tasks.append(download_image(session, img_url, download_dir))

        svg_tags = soup.find_all("svg")
        for i, svg in enumerate(svg_tags):
            svg_code = str(svg)
            tasks.append(download_embedded_svg(svg_code, i, download_dir))

        await asyncio.gather(*tasks)


# Example usage:
#asyncio.run(download_all_svgs('https://osu-sig.vercel.app/card?user=Ghost-Tales&mode=std&lang=en&blur=100&round_avatar=true&animation=true&hue=218&w=1100&h=640'))
