import logging as log
import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from sys import argv

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

ITEMS_DIR = 'items'
CURRENT_ITEMS_DIR = 'current'
CURRENT_PRICE_FILE = 'current_price.txt'
LOG_FILE = 'log.log'


def main():
    try:
        if len(argv) < 4 or len(argv) > 5:
            usage()
        item_id = argv[2]
        config(item_id)
        url = argv[1]
        price = get_price(url)
        compare_to_previous_price(url, item_id, price)
        persist_price(item_id, price)
    except Exception as e:
        log.error(e)


def config(item_id):
    """ Configures directories and files """

    load_dotenv()
    item_dir = os.path.join(ITEMS_DIR, CURRENT_ITEMS_DIR, item_id)
    if not os.path.exists(item_dir):
        os.mkdir(item_dir)
    Path(os.path.join(item_dir, CURRENT_PRICE_FILE)).touch(exist_ok=True)
    log.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', filename=os.path.join(item_dir, LOG_FILE),
                    level=log.INFO)


def get_price(url):
    """ Invokes the appropriate get_price_from_* function based on the url """

    try:
        page = requests.get(url)
    except requests.exceptions.SSLError:
        # try once more
        page = requests.get(url)
    soup = BeautifulSoup(page.text, 'html.parser')
    if 'emag.bg' in url:
        return get_price_from_emag(soup)
    elif 'ozone.bg' in url:
        return get_price_from_ozone(soup)
    elif 'ardes.bg' in url:
        return get_price_from_ardes(soup)
    else:
        usage()


def get_price_from_emag(soup):
    """ Returns the current price for the tracked item as a float """

    price_with_currency = soup.find('p', {'class': 'product-new-price'}).text
    price_str = price_with_currency.split()[0]
    formatted_price_str = price_str.replace('.', '').replace(',', '.')
    return float(formatted_price_str)


def get_price_from_ozone(soup):
    """ Returns the current price for the tracked item as a float """

    special_price = soup.find('p', {'class': 'special-price'})
    price_str = None
    if special_price is not None:
        # There is a discount
        price_str = special_price.find('span', {'class': 'price'}).text
    else:
        # No discount
        regular_price = soup.find('span', {'class': 'regular-price'})
        price_str = regular_price.find('span', {'class': 'price'}).text
    price_str_no_currency = price_str[:-4]
    formatted_price_str = price_str_no_currency.strip().replace(',', '.')
    formatted_price_str = re.sub(r'\s+', '', formatted_price_str)
    return float(formatted_price_str)


def get_price_from_ardes(soup):
    """ Returns the current price for the tracked item as a float """

    price_str = soup.find('span', {'class': 'full-price'}).text
    formatted_price_str = price_str.strip().split()[0]
    return float(formatted_price_str)


def compare_to_previous_price(url, item_id, current_price):
    """ Compares current price to previous one and send a notification if needed """

    with open(os.path.join(ITEMS_DIR, CURRENT_ITEMS_DIR, item_id, CURRENT_PRICE_FILE), 'r') as file:
        previous_price_str = file.read()
        if previous_price_str == '':
            log.info(f'First run, price {current_price}')
            return
        previous_price = float(previous_price_str)
        if current_price == previous_price:
            log.info(f'Price {current_price}')
            return
        log.info(f'Price change: {previous_price} -> {current_price}')
        if len(argv) != 5:
            notify(item_id, url, previous_price, current_price)
        else:
            boundary_price_str = argv[3]
            try:
                boundary_price = float(boundary_price_str)
            except ValueError:
                usage()
            if current_price < boundary_price:
                notify(item_id, url, previous_price, current_price)


def notify(item_id, url, previous_price, current_price):
    """ Sends an email about a price change """

    sender_email = os.environ.get('SENDER_EMAIL')
    receiver_email = argv[3]
    email_password = os.environ.get('EMAIL_PASSWORD')
    text = f'The price of item "{item_id}" went from {previous_price} to {current_price}!\n\n{url}'
    message = EmailMessage()
    message.set_content(text)
    message['Subject'] = 'Price Change Alert'
    message['From'] = sender_email
    message['To'] = receiver_email
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as server:
        server.login(sender_email, email_password)
        server.send_message(message)
        log.info('Sending email notification')


def persist_price(item_id, price):
    """ Writes the current price to a file to compare later """

    with open(os.path.join(ITEMS_DIR, CURRENT_ITEMS_DIR, item_id, CURRENT_PRICE_FILE), 'w') as file:
        file.write(str(price))


def usage():
    """ Shows program usage """

    message = f'''Usage: {argv[0]} url id [boundary_price]
    
Price tracker

Arguments:    
  url            URL of item to track. Currently supported websites:
                    - www.emag.bg
                    - www.ozone.bg
                    - www.ardes.bg
  id             A string uniquely identifying the tracked item, in case there are multiple
  email          To which email address to send notifications
  boundary_price (Optional) If set, will notify only if current price is below it. Else, will notify on every price drop.'''

    raise SystemExit(message)


if __name__ == '__main__':
    main()
