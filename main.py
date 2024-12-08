import datetime as dt
import time
import random
import logging

from optibook.synchronous_client import Exchange

exchange = Exchange()
exchange.connect()

logging.getLogger('client').setLevel('ERROR')


def trade_would_breach_position_limit(instrument_id, volume, side, position_limit=250):
    positions = exchange.get_positions()
    position_instrument = positions[instrument_id]

    if side == 'bid':
        return position_instrument + volume > position_limit
    elif side == 'ask':
        return position_instrument - volume < -position_limit
    else:
        raise Exception(f'''Invalid side provided: {side}, expecting 'bid' or 'ask'.''')


def print_positions_and_pnl():
    positions = exchange.get_positions()
    pnl = exchange.get_pnl()

    print('Positions:')
    for instrument_id in positions:
        print(f'  {instrument_id:10s}: {positions[instrument_id]:4.0f}')

    print(f'\nPnL: {pnl:.2f}')


STOCK_A_ID = 'PHILIPS_A'
STOCK_B_ID = 'PHILIPS_B'


def get_buy_sell_book():
    oba = exchange.get_last_price_book(STOCK_A_ID)
    obb = exchange.get_last_price_book(STOCK_B_ID)

    oba_best_ask_price = oba.asks[0].price
    oba_best_bid_price = oba.bids[0].price

    obb_best_ask_price = obb.asks[0].price
    obb_best_bid_price = obb.bids[0].price

    if oba_best_ask_price <= obb_best_bid_price:
        return obb, oba

    if obb_best_ask_price <= oba_best_bid_price:
        return oba, obb

    return None, None


def best_offer(sb, bb):
    buy_book = None
    sell_book = None
    if sb.asks[0].price <= bb.bids[0].price:
        sell_book, buy_book = bb, sb
    return valid_buy_sell_book(buy_book, sell_book), sell_book, buy_book


def can_buy(buy_book, volume):
    if exchange.get_positions()[buy_book.instrument_id] + volume > 200:
        return False
    return True


def can_sell(sell_book, volume):
    if exchange.get_positions()[sell_book.instrument_id] - volume < -200:
        return False
    return True


tolerancy = 0.5
DELTA = 40


def valid_buy_sell_book(buy_book, sell_book):
    return buy_book and sell_book


def sell(sell_book, volume):
    exchange.insert_order(instrument_id=sell_book.instrument_id, price=sell_book.bids[0].price, volume=volume,
                          side='ask', order_type='ioc')


def buy(buy_book, volume):
    exchange.insert_order(instrument_id=buy_book.instrument_id, price=buy_book.asks[0].price, volume=volume, side='bid',
                          order_type='ioc')


while True:

    sell_book, buy_book = get_buy_sell_book()
    if not (valid_buy_sell_book(buy_book, sell_book)):
        continue

    sell_positions = exchange.get_positions()[sell_book.instrument_id]
    buy_positions = exchange.get_positions()[buy_book.instrument_id]

    print(f'')
    print(f'-----------------------------------------------------------------')
    print(f'TRADE LOOP ITERATION ENTERED AT {str(dt.datetime.now()):18s} UTC.')
    print(f'-----------------------------------------------------------------')

    print_positions_and_pnl()
    print(f'')

    delta = abs(buy_positions + sell_positions)
    print(f'delta: {delta}')
    volume = min(min(sell_book.bids[0].volume, buy_book.asks[0].volume), 200)

    print(f'BUY_BOOK: {buy_book.instrument_id}, SELL_BOOK: {sell_book.instrument_id}')
    if can_buy(buy_book, volume) and can_sell(sell_book, volume):

        print(f'in IF BUY_BOOK: {buy_book.instrument_id}, SELL_BOOK: {sell_book.instrument_id}, volume: {volume}')
        buy(buy_book, volume)
        sell(sell_book, volume)
    else:
        if (delta >= DELTA * tolerancy):
            volume = min(delta, 10)
            if can_buy(buy_book, volume):
                buy(buy_book, volume)
            if can_sell(sell_book, volume):
                sell(sell_book, volume)
    time.sleep(1)

