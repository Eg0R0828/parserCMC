# -*- coding: utf-8 -*-


from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityTextUrl
import urllib.request
from selenium import webdriver
from bs4 import BeautifulSoup


class TradePairInfo:
    def __init__(self, url_, price_, volume_percent_, volume_usd_):
        self.url = url_
        self.price = price_
        self.volume_percent = volume_percent_
        self.volume_usd = volume_usd_

    def get_price(self):
        return self.price

    def get_url(self):
        return self.url

    def get_volume_percent(self):
        return self.volume_percent

    def get_volume_usd(self):
        return self.volume_usd


def get_cmc_link(url_from_message):
    # Making a request and getting an exchange html-page from TG-message text
    req = urllib.request.Request(url_from_message, data=None,
    headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
    with urllib.request.urlopen(req, timeout=10) as exchange_page:
        # HTML-page parsing for CMC-link searching
        soup = BeautifulSoup(exchange_page.read(), 'lxml')
        links = soup.find('section', {'id': 'ContentPlaceHolder1_divSummary'}).\
            find_all('div', {'id': 'ContentPlaceHolder1_divLinks'})[0].find_all('a', {'class': 'dropdown-item'})
        cmc_link = ''
        for link in links:
            if str(link.get('href')).find('coinmarketcap.com') != -1:
                cmc_link = str(link.get('href'))
                break
        return cmc_link


def alert_message_parse(event):
    text = str(event.raw_text)
    coin_name = str(event.message.get_entities_text(MessageEntityTextUrl)[0][1])
    coin_price = float(text.split('$')[1].split(' ')[0])
    coin_dynamic = float(text.split('%')[0].split(' ')[-1].replace('+', ''))
    coin_url = get_cmc_link(str(event.message.get_entities_text(MessageEntityTextUrl)[0][0].url))
    return coin_name, coin_price, coin_dynamic, coin_url


def create_trade_pairs_list(coin_url):
    trade_pairs = []
    # Exchange page parsing
    driver = webdriver.Chrome(options=webdriver.ChromeOptions().add_argument('headless'))
    driver.get(coin_url)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    driver.close()
    for table_row in soup.find('table', {'class': 'sc-f7a61dda-3 iPOptk cmc-table '}).find_all('tr'):
        url, price, volume_percent, volume_usd = '', 0.0, 0.0, 0.0
        try:
            url = str(table_row.find('div', {'class': 'sc-8bac979a-1 liaGEs'}).find('a').get('href'))
            price = float(str(table_row.find('p', {'class': 'sc-e225a64a-0 eXVyON'}).text).replace('$', ''))
            volume_percent = float(str(table_row.find_all('p', {'class': 'sc-e225a64a-0 dFVWVA'})[1].text).replace(',', '.').replace('%', ''))
            volume_usd = float(str(table_row.find_all('p', {'class': 'sc-e225a64a-0 dFVWVA'})[0].text).replace(',', '').replace('$', ''))
        except BaseException:
            continue
        finally:
            if url != '':
                trade_pairs.append(TradePairInfo(url_=url, price_=price, volume_percent_=volume_percent, volume_usd_=volume_usd))
    return trade_pairs


if __name__ == '__main__':
    # TG App config
    username = '@Your_Telegram_NickName'
    api_id = 00000000
    api_hash = '********************************'
    # TG chat name
    chat_name = '@EtherDROPS2_bot'
    # Top trade pairs positions (count)
    top_positions = 3

    # Creating client
    client = TelegramClient(username, api_id, api_hash)

    # New message listening
    @client.on(events.NewMessage(chats=[chat_name]))
    async def message_event_handler(event):
        # Getting all interested data from the message text
        coin_name, coin_url, coin_price, coin_dynamic = '', '', 0.0, 0.0
        try:
            if str(event.raw_text).find('price changed') > -1:
                (coin_name, coin_price, coin_dynamic, coin_url) = alert_message_parse(event)
                print('Message text:\n' + str(event.raw_text))
        except BaseException:
            pass
        finally:
            if coin_name != '' and coin_url != '' and coin_price != 0.0 and coin_dynamic != 0.0:
                # Switching to the "Markets" tab in the target website (coinmarketcap.com)
                if coin_url.find('markets/') == -1: coin_url += 'markets/'
                # Printing all input data
                print('\nInterested data from message:\n' + coin_name, coin_price, coin_dynamic, coin_url)
                # Data collecting from the cmc-table with trade pairs
                trade_pairs = create_trade_pairs_list(coin_url)
                # Conditions checking and printing the best trade pair data
                print('\nTop-' + str(top_positions), 'best trade pairs:')
                for j in range(top_positions):
                    index, curr_vol = 0, -1
                    for i in range(len(trade_pairs)):
                        if coin_dynamic > 0.0 and trade_pairs[i].get_price() < coin_price and trade_pairs[i].get_volume_percent() > curr_vol:
                            curr_vol = trade_pairs[i].get_volume_percent()
                            index = i
                        elif coin_dynamic < 0.0 and trade_pairs[i].get_price() > coin_price and trade_pairs[i].get_volume_percent() > curr_vol:
                            curr_vol = trade_pairs[i].get_volume_percent()
                            index = i
                    print(str(j + 1) + ')', trade_pairs[index].get_url() + ';',
                          str(trade_pairs[index].get_price()) + '$;', str(trade_pairs[index].get_volume_percent()) +
                          '% (' + str(trade_pairs[index].get_volume_usd()) + '$)')
                    trade_pairs.pop(index)

    # Program loop starting
    client.start()
    client.run_until_disconnected()
