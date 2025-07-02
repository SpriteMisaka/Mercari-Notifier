import re
import time
import logging
import requests

from bs4 import BeautifulSoup


MERCARI_CONDITIONS = {
    "新品、未使用": "0",
    "未使用に近い": "1",
    "目立った傷や汚れなし": "2",
    "やや傷や汚れあり": "3",
    "傷や汚れあり": "4",
    "中古": "5"
}


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


def parse_zenmarket_item(site, element):
    if site == 'yahoo':
        url = element.find('a', class_='auction-url')
        name = url.text.strip()
    else:
        url = element.find('a', class_='product-link')
        name = element.find('h3', class_='item-title').text.strip()
    item = Item(site, productID=re.search(r'itemCode=(\w+)', url['href'])[1])
    item.productName = name
    if site == 'mercari':
        notranslate_divs = element.find_all('div', class_='notranslate')
        shop = False
        for div in notranslate_divs:
            style = div.get('style', '')
            if 'display: block' in style and 'ショップ' in div.get_text():
                shop = True
                break
        item.productURL = f'https://jp.mercari.com/shops/product/{item.productID}' if shop else f"https://jp.mercari.com/item/{item.productID}"
    elif site == 'yahoo':
        item.productURL = f"https://page.auctions.yahoo.co.jp/jp/auction/{item.productID}"
    elif site == 'rakuma':
        item.productURL = f'https://item.fril.jp/{item.productID}'
    item.imageURL = element.find('img')['src']
    item.price = re.sub(r'[^\d]', '', element.find('span', class_='amount')['data-jpy'].strip())
    return item


def parse_paypay_item(element):
    href = element['href']
    if href.startswith('/item/'):
        item = Item('paypay', productID=href.split('/')[-1])
        item.productName = element.find('img')['alt'].strip()
        item.productURL = f"https://paypayfleamarket.yahoo.co.jp/item/{item.productID}"
        item.imageURL = element.find('img')['src']
        item.price = re.search(r'price:(\d+)', element['data-cl-params'])[1]
        return item
    return None


def parse_item(site, element):
    if site == 'paypay':
        return parse_paypay_item(element)
    elif site in ['mercari', 'yahoo', 'rakuma']:
        return parse_zenmarket_item(site, element)
    return None


def search(keyword, args, sites=None, maximum_page=3) -> list[Item]:
    proxies = args['proxies']

    if sites is None:
        sites = ['mercari', 'yahoo', 'paypay', 'rakuma']
    results = []

    for site in sites:

        page = 1
        while True:

            while True:
                res = []
                try:
                    if site == 'mercari':
                        condition_filters = args['mercari_settings']['condition_filters']
                        conditions = [MERCARI_CONDITIONS[k] for k, v in condition_filters.items() if v]
                        res.append(
                            requests.post(
                                f"https://zenmarket.jp/ja/{site}.aspx?q={keyword}&sort=new&order=desc&p={page}&condition={','.join(conditions)}",
                                headers=headers,
                                proxies=proxies
                            )
                        )
                    elif site == 'yahoo':
                        res.append(
                            requests.post(f"https://zenmarket.jp/ja/{site}.aspx?q={keyword}&sort=new&order=desc&p={page}",
                                          headers=headers, proxies=proxies)
                        )
                    elif site in ['paypay']:
                        res.append(
                            requests.post(f"https://paypayfleamarket.yahoo.co.jp/search/{keyword}?page={page}",
                                          headers=headers, proxies=proxies)
                        )
                    elif site in ['rakuma']:
                        res.extend([
                            requests.post(f"https://zenmarket.jp/ja/rakuma.aspx?sellerType={t}&q={keyword}&sort=new&order=desc&p={page}",
                                            headers=headers, proxies=proxies) for t in [1, 2]
                        ])
                except Exception as e:
                    logging.warning(e)
                    time.sleep(1)
                    continue
                if all(r.status_code in [200, 404] for r in res):
                    break
                else:
                    time.sleep(1)

            for r in res:
                soup = BeautifulSoup(r.content, 'html.parser')

                if site == 'yahoo':
                    items = soup.find_all('div', class_='yahoo-search-result')
                elif site in ['mercari', 'rakuma']:
                    items = soup.find_all('div', class_='product')
                elif site == 'paypay':
                    items = soup.find_all('a', href=True)

                for i in items:
                    if item := parse_item(site, i):
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


def mercari_details(url, args):
    proxies = args['proxies']

    while True:
        try:
            response = requests.get(url, headers=headers, proxies=proxies)
        except Exception as e:
            logging.warning(e)
            time.sleep(10)
            continue

        if response.ok:
            time.sleep(1)
            break
        else:
            time.sleep(10)

    soup = BeautifulSoup(response.content, 'html.parser')
    condition_span = soup.find('span', {'id': 'lblConditionName'})
    condition = condition_span.text if condition_span else "不明"
    seller_span = soup.find('span', {'id': 'seller'})
    seller_id = seller_span['sellerid'] if seller_span else "不明"
    seller_name = seller_span.text if seller_span else "不明"
    rate_span = soup.find('span', {'id': 'sellerRate_ratingValue'})
    seller_rate = round(float(rate_span.text), 2) if rate_span else "不明"
    return condition, seller_id, seller_name, seller_rate
