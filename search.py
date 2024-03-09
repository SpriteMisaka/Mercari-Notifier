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

def search_zenmarket(keyword, sites=['mercari', 'yahoo'], maximum_page=3, proxies=None):

    results = []

    for site in sites:

        page = 1
        while True:

            while True:
                try:
                    res = requests.post(f"https://zenmarket.jp/ja/{site}.aspx/getProducts?q={keyword}&sort=new&order=desc",
                                        json={"page": page},
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

            content = json.loads(res.json()["d"])
            if len(content['Items']) == 0:
                break

            for i in content['Items']:
                item = Item()
                item.site = site
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

                item.id = f"[{item.site}]{item.productID}"
                results.append(item)

            if page == maximum_page:
                break
            page += 1

    return results
