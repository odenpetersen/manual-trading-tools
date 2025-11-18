#!/usr/bin/env python3
import os
import dotenv; dotenv.load_dotenv()
import server
import requests
import asyncio
import sys
import heapq
import py_clob_client
import py_clob_client.client

class PolymarketServer(server.Server):
	def __init__(self, refresh_interval = 10):
		self.refresh_interval = refresh_interval
		super().__init__("PolymarketServer")
		self.client = py_clob_client.client.ClobClient(os.environ['CLOB_ADDRESS'], key=os.environ['POLYMARKET_PRIVATE_KEY'], chain_id=int(os.environ['POLYMARKET_CHAIN_ID']), signature_type = 1, funder=os.environ['POLYMARKET_PUBLIC_KEY'])

		self.client.set_api_creds(self.client.create_or_derive_api_creds())

		self.ongoing_tasks.append(self.maintain_assets_list())

	async def maintain_assets_list(self):
		next_cursor = "MjIwMDA="#None

		async def get_next():
			while True:
				loop = asyncio.get_event_loop()
				return (await loop.run_in_executor(None, requests.get, f"{os.environ['MARKETS_API_ENDPOINT']}?next_cursor={'' if next_cursor is None else next_cursor}")).json()

		while True:
			resp = await get_next()

			for q in resp["data"]:
				if q["enable_order_book"] is True:
					for token in q["tokens"]:
						if token["token_id"] != '':
							self.add_asset(token["token_id"], f"{q['market_slug']}/{token['outcome']}", ' '.join([*([] if q['tags'] is None else q['tags']),q['description'],q['question']]))

			if resp["next_cursor"] != "LTE=":
				next_cursor = resp["next_cursor"]
				print(f"{next_cursor=}, {len(self.asset_names)=}", file = sys.stderr)
			else:
				await asyncio.sleep(self.refresh_interval)

	async def get_books(self, asset_ids, depth=0):
		asset_ids = asset_ids.split(',')
		depth = int(depth)

		async def get_book(asset_id, depth=depth):
			result = (await loop.run_in_executor(None, requests.get, f"{os.environ['BOOK_API_ENDPOINT']}?token_id={asset_id}")).json()
			if 'bids' not in result:
				print(f"get_book has {result=}", sys.stderr)
			bids, asks = [[(float(level['price']),float(level['size'])) for level in side] for side in (result['bids'],result['asks'])]
			if depth==0:
				depth = max(map(len,(bids,asks)))
			bids, asks = heapq.nlargest(depth, bids), heapq.nsmallest(depth, asks)

			return {p : s*q for s,side in ((1,bids),(-1,asks)) for p,q in side}

		return list(await asyncio.gather(*map(get_book,asset_ids)))

	async def place_order(self, asset_id : str, size : float, price : float):
		
		BUY, SELL = py_clob_client.order_builder.constants.BUY, py_clob_client.order_builder.constants.SELL
		order_args = py_clob_client.clob_types.OrderArgs(price=price, size=abs(size), side=BUY if size>0 else SELL, token_id = asset_id)

		def post_monkeypatch(endpoint, headers=None, data=None):
			method = 'POST'
			headers = py_clob_client.http_helpers.helpers.overloadHeaders(method,headers)
			resp = requests.request(method=method, url=endpoint, headers=headers, json=data if data else None, proxies = dict(http='socks5h://127.0.0.1:9050',https='socks5h://127.0.0.1:9050'))
			try:
				return resp.json()
			except requests.JSONDecodeError:
				return resp.text

		tmp = py_clob_client.client.post 
		py_clob_client.client.post = post_monkeypatch
		result = self.client.create_and_post_order(order_args)
		py_clob_client.client.post = tmp
		return result

	async def get_orders(self):
		return self.client.get_orders()
		

if __name__ == "__main__":
	server = PolymarketServer()
	loop = asyncio.get_event_loop()
	loop.run_until_complete(server.run())
