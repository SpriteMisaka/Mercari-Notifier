import re
import time
import logging
import requests

from bs4 import BeautifulSoup


class Item:
    def __init__(self, site: str, productID: str):
        self.site = site
        self.productID = productID
        self.id = f"[{self.site}]{self.productID}"

        self.productName = None
        self.productURL = None
        self.imageURL = None
        self.price = None


headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36 Edge/16.16299"}


def parse_item(site, element):

    item = None

    if site == 'yahoo':
        auction_url = element.find('a', class_='auction-url')

        item = Item(site, productID=re.search(r'itemCode=(\w+)', auction_url['href']).group(1))
        item.productName = auction_url.text.strip()
        item.productURL = f"https://page.auctions.yahoo.co.jp/jp/auction/{item.productID}"
        item.imageURL = element.find('img')['src']
        item.price = re.sub(r'[^\d]', '', element.find('span', class_='amount')['data-jpy'].strip())

    elif site == 'mercari':
        product_link = element.find('a', class_='product-link')
        notranslate_divs = element.find_all('div', class_='notranslate')
        shop = False
        for div in notranslate_divs:
            style = div.get('style', '')
            if 'display: block' in style and 'ショップ' in div.get_text():
                shop = True
                break

        item = Item(site, productID=re.search(r'itemCode=(\w+)', product_link['href']).group(1))
        item.productName = element.find('h3', class_='item-title').text.strip()
        item.productURL = f'https://jp.mercari.com/shops/product/{item.productID}' if shop else f"https://jp.mercari.com/item/{item.productID}"
        item.imageURL = element.find('img')['src']
        item.price = re.sub(r'[^\d]', '', element.find('span', class_='amount')['data-jpy'].strip())

    elif site == 'paypay':
        href = element['href']
        if href.startswith('/item/'):

            item = Item(site, productID=href.split('/')[-1])
            item.productName = element.find('img')['alt'].strip()
            item.productURL = f"https://paypayfleamarket.yahoo.co.jp/item/{item.productID}"
            item.imageURL = element.find('img')['src']
            item.price = re.search(r'price:(\d+)', element['data-cl-params']).group(1)

    return item


def search(keyword, sites=['mercari', 'yahoo', 'paypay'], maximum_page=3, proxies=None):

    results = []

    for site in sites:

        page = 1
        while True:

            while True:
                try:
                    if site in ['mercari', 'yahoo']:
                        res = requests.post(f"https://zenmarket.jp/ja/{site}.aspx?q={keyword}&sort=new&order=desc&p={page}",
                                            headers=headers, proxies=proxies)
                    elif site in ['paypay']:
                        res = requests.post(f"https://paypayfleamarket.yahoo.co.jp/search/{keyword}?page={page}",
                                            headers=headers, proxies=proxies)
                except Exception as e:
                    logging.warning(e)
                    time.sleep(1)
                    continue
                if res.status_code == 200 or res.status_code == 404:
                    break
                else:
                    time.sleep(1)

            soup = BeautifulSoup(res.content, 'html.parser')
            if site == 'yahoo':
                items = soup.find_all('div', class_='yahoo-search-result')
            elif site == 'mercari':
                items = soup.find_all('div', class_='product')
            elif site == 'paypay':
                items = soup.find_all('a', href=True)
            else:
                items = []
            
            for i in items:
                item = parse_item(site, i)
                if item:
                    results.append(item)

            if page == maximum_page:
                break
            page += 1

            # DEPRECATED!

            # if site in ['mercari', 'yahoo']:
            #     content = json.loads(res.json()["d"])
            #     items = content['Items']
            # elif site in ['paypay']:
            #     content = res.json()
            #     items = content['items']

            # if len(items) == 0:
            #     break

            # for i in items:
            #     item = Item()
            #     item.site = site

            #     if site in ['mercari', 'yahoo']:

            #         item.price = parseString(i["PriceTextControl"]).getElementsByTagName("span")[0].getAttribute("data-jpy").strip('¥').replace(",", "")

            #         if site == 'mercari':
            #             item.productID = i['ItemCode']
            #             item.productName = i['ClearTitle']
            #             item.productURL = f"{'https://jp.mercari.com/item/' if i['IsSellerTypePerson'] else 'https://jp.mercari.com/shops/product/'}{i['ItemCode']}"
            #             item.imageURL = i["PreviewImageUrl"]

            #         if site == 'yahoo':
            #             item.productID = i['AuctionID']
            #             item.productName = i['Title']
            #             item.productURL = f"https://page.auctions.yahoo.co.jp/jp/auction/{i['AuctionID']}"
            #             item.imageURL = i['Thumbnail']

            #     elif site in ['paypay']:
            #         item.price = str(i['price'])
            #         item.productID = i['id']
            #         item.productName = i['title']
            #         item.productURL = f"https://paypayfleamarket.yahoo.co.jp/item/{i['id']}"
            #         item.imageURL = i['thumbnailImageUrl']

            #     item.id = f"[{item.site}]{item.productID}"
            #     results.append(item)

    return results
