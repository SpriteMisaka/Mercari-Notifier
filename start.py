import json
import time
import schedule
import logging
import requests

from io import BytesIO

from search import Item, search, mercari_details


SITE_NAME = {
    'mercari': 'メルカリ',
    'yahoo': 'Yahoo!オークション',
    'paypay': 'Yahoo!フリマ',
    'rakuma': '楽天ラクマ'
}


def notify(style: str, item: Item, args, old_item=None,
           discord_hook_url=None, telegram_token=None, telegram_chat_id=None):
    proxies = args['proxies']
    mercari_extra = {}
    if item.site == 'mercari':
        ext = args["mercari_settings"]["extra_display"]
        if any(ext.values()):
            mercari_url = f"https://zenmarket.jp/ja/mercariproduct.aspx?itemCode={item.productID}"
            condition, seller_id, seller_name, seller_rate = mercari_details(mercari_url, args)
            if ext['seller']:
                mercari_extra['セラー'] = f"{seller_name} (ID: {seller_id}; 評価: ★{seller_rate})"
            if ext['condition']:
                mercari_extra['商品の状態'] = f"#{condition}"
    while True:
        try:
            if style == 'discord':
                url = discord_hook_url
                embed = {
                    'title': f'[{SITE_NAME[item.site]}] {item.productName}',
                    'url': f'{item.productURL}',
                    'fields': (
                        [
                            {
                                'name': '価格:',
                                'value': (
                                    f"{item.price} 円"
                                    if old_item is None
                                    else f"~~{old_item.price}~~ {item.price} 円"
                                ),
                                'inline': False,
                            },
                        ]
                        + [
                            {'name': f'{k}:', 'value': v, 'inline': False}
                            for k, v in mercari_extra.items()
                        ]
                    )
                }
                if args['image_display']:
                    embed['image'] = {}
                    embed['image']['url'] = item.imageURL
                payload_json = json.dumps({'embeds': [embed], 'username': 'Mercari'})
                response = requests.post(url, payload_json,
                                         headers={'Content-Type': 'application/json'},
                                         proxies=proxies)
            elif style == 'telegram':
                message =  f'<a href="{item.productURL}"><b>[{SITE_NAME[item.site]}] {item.productName}</b></a>\n' + '<b>価格:</b>\n' + \
                    (f"{item.price} 円" if old_item is None else f"<del>{old_item.price}</del> {item.price} 円") +\
                    (('\n' + '\n'.join([f'<b>{k}:</b>\n{v}' for k, v in mercari_extra.items()])) if mercari_extra else '')

                files = None
                if args['image_display']:
                    res = requests.get(item.imageURL, proxies=proxies)
                    image_bytes = res.content
                    image_stream = BytesIO(image_bytes)
                    files = {"photo": image_stream}

                params = {
                    'chat_id': telegram_chat_id,
                    'caption': message,
                    'parse_mode': 'HTML'
                }

                response = requests.post(f'https://api.telegram.org/bot{telegram_token}/sendPhoto',
                                         data=params, files=files, proxies=proxies)

        except Exception as e:
            logging.warning(e)
            time.sleep(10)
            continue

        if response.ok:
            time.sleep(1)
            break
        else:
            time.sleep(10)


def job():

    global items
    global keywords
    global args

    args = load_json()
    init()

    new_items_keywords_of = {}
    reduced_items_keywords_of = {}

    def update_keywords(keywords_of, id, keyword):
        if id not in keywords_of:
            keywords_of[id] = []
        if keyword not in keywords_of[id]:
            keywords_of[id].append(keyword)

    def update_items_via_keywords(keywords_of, some_items, info):
        unique_values = [list(x) for x in {tuple(x) for x in keywords_of.values()}]
        for keyword_combination in unique_values:
            ids = list(filter(lambda x: keywords_of[x] == keyword_combination, keywords_of))
            if ids:
                logging.info(f"{info} {len(ids)} {'item' if len(ids) == 1 else 'items'} about [{', '.join(keyword_combination)}].")
                for id in ids:
                    item = some_items[id]
                    old_item = None if info == 'Found' else items[id]
                    if args['discord_hook_url']:
                        notify("discord", item, args, old_item,
                               discord_hook_url=args['discord_hook_url'])
                    if args['telegram_token'] and args['telegram_chat_id']:
                        notify("telegram", item, args, old_item,
                               telegram_token=args['telegram_token'], telegram_chat_id=args['telegram_chat_id'])
                    logging.info(some_items[id].productURL)
                    items[id] = some_items[id]

    new_items = {}
    reduced_items = {}

    for keyword in keywords:
        for item in search(keyword, args):
            if any(e in item.productName for e in args['exclude']):
                continue
            if 'price_min' in args and keyword in args['price_min'] and int(item.price) < args['price_min'][keyword]:
                continue
            if 'price_max' in args and keyword in args['price_max'] and int(item.price) > args['price_max'][keyword]:
                continue
            if item.id not in items:
                new_items[item.id] = item
                update_keywords(new_items_keywords_of, item.id, keyword)
            elif int(item.price) < int(items[item.id].price):
                reduced_items[item.id] = item
                update_keywords(reduced_items_keywords_of, item.id, keyword)

    update_items_via_keywords(new_items_keywords_of, new_items, "Found")
    update_items_via_keywords(reduced_items_keywords_of, reduced_items, "Price reduction on")

    if not new_items and not reduced_items:
        logging.info("No new items found.")


def load_json():
    args = {}
    with open('settings.json', 'r', encoding='UTF-8') as data_file:
        data = json.load(data_file)
        args['keywords'] = data['keywords']
        args['price_min'] = data.get('price_min', {})
        args['price_max'] = data.get('price_max', {})
        args['discord_hook_url'] = data['discord_hook_url'] or None
        args['telegram_token'] = data['telegram_token'] or None
        args['telegram_chat_id'] = data['telegram_chat_id'] or None
        args['proxies'] = data['proxies'] or None
        args['exclude'] = data['exclude'] or None
        args['image_display'] = data.get('image_display', True)
        args['mercari_settings'] = data['mercari_settings']
    return args


def init():

    global items
    global keywords
    global args

    for keyword in args['keywords']:
        if keyword not in keywords:
            logging.info(f"Preprocessing items via keyword [{keyword}]...")
            for item in search(keyword, args):
                items[item.id] = item
    keywords = args['keywords']

if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO,
                        datefmt="%Y-%m-%d %H:%M:%S",
                        format="%(asctime)s [%(levelname)s] %(message)s")

    items = {}
    keywords = []
    args = load_json()
    init()

    logging.info("Done.")

    for i in [str(j).zfill(2) for j in range(8, 24)] + ["00"]:
        schedule.every().day.at(f"{i}:00").do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)
