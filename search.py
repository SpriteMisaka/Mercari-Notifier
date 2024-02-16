import json
import time
import logging
import requests

from xml.dom.minidom import parseString

class Item:
    def __init__(self):
        self.id = None
        self.productName = None
        self.productURL = None
        self.imageURL = None
        self.price = None

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36 Edge/16.16299"}

def search_mercari(keyword, maximum_page=3, proxies=None):

    results = []

    page = 1
    while True:

        while True:
            try:
                res = requests.post(f"https://zenmarket.jp/ja/mercari.aspx/getProducts?q={keyword}&sort=new&order=desc",
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
            item.id = i['ItemCode']
            item.productName = i['ClearTitle']
            item.productURL = f"{'https://jp.mercari.com/item/' if i['IsSellerTypePerson'] else 'https://jp.mercari.com/shops/product/'}{i['ItemCode']}"
            item.imageURL = i["PreviewImageUrl"]
            item.price = parseString(i["PriceTextControl"]).getElementsByTagName("span")[0].getAttribute("data-jpy").strip('¥').replace(",", "")

            results.append(item)

        if page == maximum_page:
            break
        page += 1

    return results
