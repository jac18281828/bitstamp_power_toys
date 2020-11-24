import asyncio
import aiohttp
import websockets
import json
import sys
import time
import traceback
import certifi
import ssl
import math
import collections
from pricelistener import PriceListener
from buytheo import BuyTheo

class BitstampWss:

    WSS_URL = 'wss://ws.bitstamp.net'
    ORDER_BOOK_URL = 'https://www.bitstamp.net/api/v2/order_book/btcusd?group=1'

    HEARTBEAT_TIMEOUT = 5

    def __init__(self):
        
        self.is_running = True
        self.update_time = 0
        self.timestamp = 0
        self.microtimestamp = 0
        self.bids = {}
        self.asks = {}
        self.data_buffer = []
        self.is_fetched = False

        self.pricelistener = PriceListener()
        self.buytheo = BuyTheo()

    async def send_json(self, websocket, event):
        event_payload = json.dumps(event)
        print(event_payload)
        await websocket.send(event_payload)        

    async def ping(self, websocket):
        self.update_time = time.time()
        await websocket.ping()

    async def on_subscription(self, websocket, message):
        print('subscribed: %s' % message)

    async def update_order_book(self, book):
        update_time = int(book['microtimestamp'])
        if update_time > self.microtimestamp:
            self.timestamp = int(book['timestamp'])
            self.microtimestamp = update_time
            for bid in book['bids']:
                price = float(bid[0])
                qty   = float(bid[1])

                priceLevel = str(bid[0])

                if math.isclose(qty, 0.0):
                    if priceLevel in self.bids:
                        del self.bids[priceLevel]
                else:
                    self.bids[priceLevel] = qty

            for ask in book['asks']:
                price = float(ask[0])
                qty   = float(ask[1])

                priceLevel = str(ask[0])

                if math.isclose(qty, 0.0):
                    if priceLevel in self.asks:
                        del self.asks[priceLevel]
                else:
                    self.asks[priceLevel] = qty
                        

    async def on_data(self, websocket, event):
        if self.data_buffer is not None:
            self.data_buffer.append(event)
        else:
            await self.update_order_book(event)

    async def on_message(self, websocket, message):
        self.update_time = time.time()

        event_message = json.loads(message)

        if event_message['event'] == 'data':
            update = event_message['data']
            if event_message['channel'] == 'diff_order_book_btcusd':
                await self.on_data(websocket, update)            
        else:
            if event_message['event'] == 'bts:subscription_succeeded':
                await self.on_subscription(websocket, event_message)
            else:
                if event_message['event'] == 'bts:request_reconnect':
                    print('Going down on request from server')
                    self.is_running = False
                else:
                    print('Unknown event: %s' % event_message['event'])
        

    async def send_subscription(self, websocket):
        event = {'event': 'bts:subscribe',
                 'data': {
                     'channel': 'diff_order_book_btcusd'
                 }
        }

        await self.send_json(websocket, event)


    async def fetch(self, session, url):
        async with session.get(url, ssl=ssl.create_default_context(cafile=certifi.where())) as response:
            return await response.text()

    async def fetch_order_book(self):
        async with aiohttp.ClientSession() as session:
            await self.fetch_order_book_rest(session)
        
    async def fetch_order_book_rest(self, session):
        url = self.ORDER_BOOK_URL
        
        result = await self.fetch(session, url)

        json_book = json.loads(result)

        booktimestamp = int(json_book['microtimestamp'])

        await self.update_order_book(json_book)

        while len(self.data_buffer) < 5:
            await asyncio.sleep(.1)

        data_queue = self.data_buffer
        
        self.data_buffer = None

        if len(data_queue) > 0:

            any_prior = False
            any_equal = False

            print("%d queued changes." % len(data_queue))
            
            for update in data_queue:
                update_time = int(update['microtimestamp'])
                if booktimestamp > update_time:
                    any_prior = True
                else:
                    if booktimestamp == update_time:
                        any_equal = True
                    else:
                        await self.update_order_book(update)

            if not any_prior:
                print('No prior update.')

            print('')
            print('')
            print('')                

            if any_equal:
                print('SNAPSHOT matching change window')
            else:
                print('Initial update missing: data lost')
                print('Expect to fail')
                #self.is_running = False

            print('')
            print('')
            print('')                
                
        else:
            print('No updates to apply.  Not yet subscribed?')
            self.is_running = False

    async def on_open(self, websocket):
        await self.send_subscription(websocket)
        
    async def on_idle(self, websocket):
        if self.is_fetched == False and len(self.data_buffer) > 1:
            self.is_fetched = True
            await self.fetch_order_book()

        await self.heartbeat(websocket)
        

    async def heartbeat(self, websocket):
        now = time.time()
        timedelta = now - self.update_time
        if timedelta > self.HEARTBEAT_TIMEOUT:
            print('Idle: sending ping')
            await self.ping(websocket)
        else:
            await asyncio.sleep(self.HEARTBEAT_TIMEOUT - timedelta)
            
    async def receive_message(self, websocket):
        async for message in websocket:
            await self.on_message(websocket, message)
            
    def on_error(self, err):
        print('Error in websocket connection: {}'.format(err))
        print(traceback.format_exc(err))
        self.is_running = False

    async def print_best(self):
        if self.data_buffer is None:

            best_bid = None
            best_offer = None
            
            print('\t\tbest asks')
            best_offers = reversed(sorted(self.asks.items(), key=lambda level: float(level[0]))[0:4])
            for level in best_offers:
                print ('\t\t%s' % str(level))                                
                best_offer = level
                    
            best_bids = sorted(self.bids.items(), reverse=True, key=lambda level: float(level[0]))[0:4]
            for level in best_bids:
                print (level)
                if best_bid is None:
                    best_bid = level
                    
            print('best bids')

            self.pricelistener.on_price_update(best_bids, best_offers)
            self.buytheo.on_price_update(best_bids, best_offers)

            if float(best_bid[0]) >= float(best_offer[0]):
                print('CROSSING!  This can not be correct!')
                self.is_running = False

            print('')
            print('')
            print('')
                
    async def run_event_loop(self):
        try:
            async with websockets.connect(self.WSS_URL, ssl=ssl.create_default_context(cafile=certifi.where())) as websocket:

                await self.on_open(websocket)

                while self.is_running:

                    tasks = [
                        asyncio.ensure_future(self.on_idle(websocket)),
                        asyncio.ensure_future(self.receive_message(websocket))
                    ]

                    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

                    for task in pending:
                        task.cancel()

                    await self.print_best()
                    
        except Exception as e:
            self.on_error(e)


if __name__ == '__main__':

    try:

        bss = BitstampWss()

        asioloop = asyncio.get_event_loop()
        asioloop.run_until_complete(bss.run_event_loop())

    finally:
        asioloop.close()
