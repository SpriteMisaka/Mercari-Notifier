import json
import time
import logging
import requests

from xml.dom.minidom import parseString

class Item:
    def __init__(self):
        self.id = None
        self.site = None
        self.productID = None
        self.productName = None
        self.productURL = None
        self.imageURL = None
        self.price = None

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36 Edge/16.16299"}

def search(keyword, sites=['mercari', 'yahoo', 'paypay'], maximum_page=3, proxies=None):

    results = []

    for site in sites:

        page = 1
        while True:

            while True:
                try:
                    if site in ['mercari', 'yahoo']:
                        res = requests.post(f"https://zenmarket.jp/ja/{site}.aspx/getProducts?q={keyword}&sort=new&order=desc",
                                            json={"page": page},
                                            headers=headers,
                                            proxies=proxies)
                    elif site in ['paypay']:
                        res = requests.post(f"http://paypayfleamarket.yahoo.co.jp/api/v1/search/?results=100&imageShape=square&sort=ranking&order=ASC&webp=false&offset=0&query={keyword}&module=catalog:hit:21",
                                            headers=headers,
                                            proxies=proxies)
                except Exception as e:
                    logging.warning(e)
                    time.sleep(10)
                    continue
                if res.status_code == 200:
                    time.sleep(1)
                    break
                else:
                    time.sleep(10)

            if site in ['mercari', 'yahoo']:
                content = json.loads(res.json()["d"])
                items = content['Items']
            elif site in ['paypay']:
                content = res.json()
                items = content['items']

            if len(items) == 0:
                break

            for i in items:
                item = Item()
                item.site = site

                if site in ['mercari', 'yahoo']:

                    item.price = parseString(i["PriceTextControl"]).getElementsByTagName("span")[0].getAttribute("data-jpy").strip('¥').replace(",", "")

                    if site == 'mercari':
                        item.productID = i['ItemCode']
                        item.productName = i['ClearTitle']
                        item.productURL = f"{'https://jp.mercari.com/item/' if i['IsSellerTypePerson'] else 'https://jp.mercari.com/shops/product/'}{i['ItemCode']}"
                        item.imageURL = i["PreviewImageUrl"]

                    if site == 'yahoo':
                        item.productID = i['AuctionID']
                        item.productName = i['Title']
                        item.productURL = f"https://page.auctions.yahoo.co.jp/jp/auction/{i['AuctionID']}"
                        item.imageURL = i['Thumbnail']

                elif site in ['paypay']:
                    item.price = i['price']
                    item.productID = i['id']
                    item.productName = i['title']
                    item.productURL = f"https://paypayfleamarket.yahoo.co.jp/item/{i['id']}"
                    item.imageURL = i['thumbnailImageUrl']

                item.id = f"[{item.site}]{item.productID}"
                results.append(item)

            if page == maximum_page and site in ['paypay']:
                break
            page += 1

    return results
