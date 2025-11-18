import fastapi
import uvicorn
import asyncio
import dotenv; dotenv.load_dotenv()
import os
import string
import collections
import functools
import frozendict
import heapq

def get_keywords(s):
	freq = collections.Counter(s.translate(str.maketrans(string.punctuation, ' '*len(string.punctuation))).lower().split(' '))
	del freq[""]
	return frozendict.deepfreeze(freq)

@functools.lru_cache
def norm(d):
	if not isinstance(d,frozendict.frozendict):
		raise TypeError(f"Cached function norm expected frozendict, but {type(d)=}")
	return sum([d[k]**2 for k in d])**0.5

def cosine_similarity(dict_a, dict_b):
	(_,dict_a), (_,dict_b) = sorted([(len(d)+0.5*(d==dict_a),d) for d in (dict_a,dict_b)])
	norm_product = norm(dict_a)*norm(dict_b)
	total = sum([dict_a[word]*dict_b.get(word,0) for word in dict_a])

	return total/norm_product if norm_product!=0 else np.nan

class Server:
	def __init__(self, name = "Server"):
		self.app = fastapi.FastAPI(title = name)

		self.groups = dict()
		self.group_selection = dict()

		self.groups_counter = 0

		self.ongoing_tasks = []

		self.asset_names = dict()

		self.asset_keywords = dict()

		self.app.post("/set_group")(self.set_group)
		self.app.patch("/rename_group")(self.rename_group)
		self.app.get("/get_group")(self.get_group)
		self.app.get("/get_groups")(self.get_groups)
		self.app.delete("/remove_group")(self.remove_group)

		self.app.get("/search")(self.search)
		self.app.get("/get_names")(self.get_names)
		self.app.get("/get_id")(self.get_id)

		self.app.get("/get_books")(self.get_books)

		self.app.post("/place_order")(self.place_order)
		self.app.get("/get_orders")(self.get_orders)

	async def run(self, **uvi_kwargs):
		await asyncio.gather(self.run_server(**uvi_kwargs), *self.ongoing_tasks)
	async def run_server(self, **uvi_kwargs):
		await uvicorn.Server(uvicorn.Config(self.app, host=os.environ['SERVER_ADDRESS'], port=os.environ['SERVER_PORT'], **uvi_kwargs)).serve()

	def add_asset(self, asset_id, asset_name, description):
		self.asset_names[asset_id] = asset_name
		self.asset_keywords[asset_id] = get_keywords(description)

	def set_group(self, name, assets):
		if name=='':
			name = str(self.groups_counter)
			self.groups_counter += 1
		self.group[name] = set(assets)
		self.group_selection[name] = None if len(assets)==0 else next(iter(assets))
		
	def extend_group(name,assets):
		self.group[name].update(assets)
		if self.group_selection[name] not in self.group:
			self.group_selection[name] = None if len(self.group[name])==0 else next(iter(assets))
	def reduce_group(name,assets):
		self.group[name].difference_update(assets)
		if self.group_selection[name] not in self.group:
			self.group_selection[name] = None if len(self.group[name])==0 else next(iter(self.group[name]))
	def rename_group(self, old, new):
		self.group[new] = self.group[old]
		del self.group[old]
	def get_group(self, name):
		return self.group[name]
	def get_groups(self):
		return list(self.groups)
	def remove_group(self, name):
		del self.groups[name]

	def search(self, query="", max_num_results=0):
		max_num_results = int(max_num_results)
		if max_num_results == 0:
			max_num_results = len(self.asset_keywords)
		if query == "":
			return list(self.asset_keywords)[:max_num_results]
		keywords = get_keywords(query)
		scores = [(cosine_similarity(self.asset_keywords[asset_id], keywords),asset_id) for asset_id in self.asset_keywords]
		return [asset_id for score,asset_id in heapq.nlargest(max_num_results, scores) if score>0]
	def get_names(self, asset_ids):
		asset_ids = asset_ids.split(',')
		return list(map(self.asset_names.get, asset_ids))
	def get_id(self, name):
		asset_id, = [asset_id for asset_id in self.asset_names if self.asset_names[asset_id]==name]
		return asset_id

	def get_books(self, asset_ids, depth=1):
		raise Exception("Abstract method")
	def place_order(self, asset_ids, size, price):
		raise Exception("Abstract method")
	def get_orders(self, assets):
		raise Exception("Abstract method")
	def get_theo(self, assets):
		raise Exception("Abstract method")
	def get_toplevels(self, assets):
		raise Exception("Abstract method")
	def get_price_history(self, assets):
		raise Exception("Abstract method")
	def get_trade_history(self, assets):
		raise Exception("Abstract method")
	def get_positions(self, assets):
		raise Exception("Abstract method")
	def get_covariance(self, assets):
		raise Exception("Abstract method")
	def get_news(self, assets):
		raise Exception("Abstract method")
