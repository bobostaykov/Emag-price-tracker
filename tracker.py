import logging as log
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from sys import argv

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

CURRENT_PRICE_FILE = 'current_price.txt'


def main():
    try:
        config()
        if len(argv) < 2 or len(argv) > 3:
            usage()
        url = argv[1]
        item_name, price = get_name_and_price(url)
        compare_to_previous_price(url, item_name, price)
        persist_price(price)
    except Exception as e:
        log.error(e)


def config():
    load_dotenv()
    Path(CURRENT_PRICE_FILE).touch(exist_ok=True)
    log.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', filename='log.log', level=log.INFO)


def get_name_and_price(url):
    """ Finds the current price as a float for the tracked item and its name """

    try:
        page = requests.get(url)
    except requests.exceptions.SSLError:
        # try once more
        page = requests.get(url)
    soup = BeautifulSoup(page.text, 'html.parser')
    item_name = soup.find('h1', 'page-title').text
    price_with_currency = soup.find('p', {'class': 'product-new-price'}).text
    price_str = price_with_currency.split()[0]
    formatted_price_str = price_str.replace('.', '').replace(',', '.')
    return item_name, float(formatted_price_str)


def compare_to_previous_price(url, item_name, current_price):
    """ Compares current price to previous one and send a notification if needed """

    with open(CURRENT_PRICE_FILE, 'r') as file:
        previous_price_str = file.read()
        if previous_price_str == '':
            log.info(f'First run, price {current_price}')
            return
        previous_price = float(previous_price_str)
        if current_price == previous_price:
            log.info(f'Price {current_price}')
            return
        log.info(f'Price change: {previous_price} -> {current_price}')
        if len(argv) != 3:
            notify(item_name, url, previous_price, current_price)
        else:
            boundary_price_str = argv[2]
            try:
                boundary_price = float(boundary_price_str)
            except ValueError:
                usage()
            if current_price < boundary_price:
                notify(item_name, url, previous_price, current_price)


def notify(item_name, url, previous_price, current_price):
    """ Sends an email about a price drop """

    sender_email = os.environ.get('SENDER_EMAIL')
    receiver_email = os.environ.get('RECEIVER_EMAIL')
    email_password = os.environ.get('EMAIL_PASSWORD')
    text = f'''The price of item
{item_name}
went from {previous_price} to {current_price}!

{url}'''
    message = EmailMessage()
    message.set_content(text)
    message['Subject'] = 'Price Drop Alert'
    message['From'] = sender_email
    message['To'] = receiver_email
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as server:
        server.login(sender_email, email_password)
        server.send_message(message)
        log.info('Sending email notification')


def persist_price(price):
    """ Writes the current price to a file to compare later """

    with open(CURRENT_PRICE_FILE, 'w') as file:
        file.write(str(price))


def usage():
    """ Shows program usage """

    message = f'''Usage: {argv[0]} url [-p boundary_price]
    
Emag price tracker

Arguments:    
  url               URL of item to track
  -p boundary_price If set, will notify only if current price is below it. Else, will notify on every price drop.'''

    log.error(message)
    raise SystemExit(message)


if __name__ == '__main__':
    main()
