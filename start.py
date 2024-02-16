import json
import time
import schedule
import logging
import requests

from search import search_mercari

def notify_discord(hook_url, item, old_item=None, proxies=None):
    embed = {
        'title': f'{item.productName}',
        'url': f'{item.productURL}',
        'fields': [
            {
                'name': '価格:',
                'value': f" {item.price} 円" if old_item is None else f"~~{old_item.price}~~ {item.price} 円",
                'inline': False
            },
        ],
        'image': {
            'url': item.imageURL,
        },
    }

    payload_json = json.dumps({'embeds': [embed], 'username': 'Mercari'})
    while(True):
        try:
            response = requests.post(hook_url,
                                     payload_json,
                                     headers={'Content-Type': 'application/json'},
                                     proxies=proxies)
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
        keywords_of[id].append(keyword)

    def update_items_via_keywords(keywords_of, some_items, info):
        unique_values = [list(x) for x in set(tuple(x) for x in keywords_of.values())]
        for keyword_combination in unique_values:
            ids = list(filter(lambda x: keywords_of[x] == keyword_combination, keywords_of))
            if len(ids) > 0:
                logging.info(f"{info} {len(ids)} {'item' if len(ids) == 1 else 'items'} about [{', '.join(keyword_combination)}].")
                for id in ids:
                    if args['hook_url'] is not None:
                        notify_discord(args['hook_url'], some_items[id], None if info == 'Found' else items[id], proxies=args['proxies'])
                    else:
                        logging.info(some_items[id].productURL)
                    items[id] = some_items[id]

    new_items = {}
    reduced_items = {}

    for keyword in keywords:
        for item in search_mercari(keyword, proxies=args['proxies']):
            if item.id not in items:
                new_items[item.id] = item
                update_keywords(new_items_keywords_of, item.id, keyword)
            elif int(item.price) < int(items[item.id].price):
                reduced_items[item.id] = item
                update_keywords(reduced_items_keywords_of, item.id, keyword)

    update_items_via_keywords(new_items_keywords_of, new_items, "Found")
    update_items_via_keywords(reduced_items_keywords_of, reduced_items, "Price reduction on")

    if len(new_items) == 0 and len(reduced_items) == 0:
        logging.info(f"No new items found.")


def load_json():
    args = {}
    with open('settings.json', 'r', encoding='UTF-8') as data_file:
        data = json.load(data_file)
        args['keywords'] = data['keywords']
        args['hook_url'] = data['hook_url'] if data['hook_url'] else None
        args['proxies'] = data['proxies'] if data['proxies'] else None
    return args


def init():

    global items
    global keywords
    global args

    for keyword in args['keywords']:
        if keyword not in keywords:
            logging.info(f"Preprocessing items via keyword [{keyword}]...")
            for item in search_mercari(keyword, proxies=args['proxies']):
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
