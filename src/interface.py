#!/usr/bin/env python3
import argparse
import requests
import dotenv; dotenv.load_dotenv()
import os
import sys
import json
import datetime
import traceback
import itertools

methods = dict()

main_parser = argparse.ArgumentParser(description="Interact with server", add_help = False)
subparsers = main_parser.add_subparsers(dest="method", required=True)

def request(suffix, method):
	response = method(f"http://{os.environ['SERVER_ADDRESS']}:{os.environ['SERVER_PORT']}/{suffix}")
	try:
		return response.json()
	except Exception as e:
		print(e)
		print(traceback.format_exc())
		print(response.text)

def command(f):
	methods[f.__name__] = f
	f.parser = subparsers.add_parser(f.__name__, help=f.__doc__)
	return f

@command
def search(args):
	for x in request(f"search?query={args.query}&max_num_results={args.max_num_results}", requests.get):
		print(x)
search.parser.add_argument("query", nargs = '?', default="", type=str, help="Search query string")
search.parser.add_argument("-n", "--max_num_results", nargs = '?', default=0, type=int, help="Maximum number of results")

@command
def get_names(args):
	asset_ids = sys.stdin.read().splitlines()
	for x in request(f"get_names?asset_ids={','.join(asset_ids)}", requests.get):
		print(x)

@command
def get_id(args):
	result = request(f"get_id?name={args.name}", requests.get)
	print(result)
get_id.parser.add_argument("name", nargs = '?', default="", type=str, help="Search query string")

@command
def get_books(args):
	asset_ids = sys.stdin.read().rstrip().replace('\n',' ').split(' ')
	names = request(f"get_names?asset_ids={','.join(asset_ids)}", requests.get) if args.name is True else itertools.repeat(None)
	for name, x in zip(names, request(f"get_books?asset_ids={','.join(asset_ids)}&depth={args.depth}", requests.get)):
		if name is not None:
			print(name)
		if args.pretty_print is None:
			print({float(p):x[p] for p in x})
		else:
			pairs = sorted({float(p):x[p] for p in x}.items(), reverse=True)
			pre_point_len = max([len(str(p).split('.')[0]) for p,q in pairs]+[0])
			post_point_len = max([len(str(p).split('.')[1]) for p,q in pairs]+[0])
			qty_len = max([len(str(q)) for p,q in pairs]+[0])
			if args.pretty_print == 0:
				width = os.get_terminal_size().columns - pre_point_len - post_point_len - qty_len - 5
				units = max([abs(q) for p,q in pairs]) / width
			else:
				units = args.pretty_print
			block_char = '\u2588'
			for p,q in pairs:
				pre_point, post_point = str(p).split('.')
				color = '\033[32m' if q>0 else '\033[31m' if q<0 else ''
				reset = '\033[39m'
				print(f"{color}{pre_point.rjust(pre_point_len)}.{post_point.ljust(post_point_len)} | {block_char*int(abs(q)/units)} {q}{reset}")
get_books.parser.add_argument("-d", "--depth", nargs = '?', default=0, type=int, help="Maximum number of book levels either side")
get_books.parser.add_argument("-p", "--pretty_print", nargs = '?', const = 0, default = None, type=int, help="Pretty print with optionally specified units")
get_books.parser.add_argument("-n", "--name", nargs = '?', default=False, const=True, type=int, help="Maximum number of book levels either side")

@command
def place_order(args):
	response = request(f"place_order?asset_id={args.asset_id}&size={args.size}&price={args.price}", requests.post)
	print(response)
place_order.parser.add_argument("asset_id", help="ID of asset to trade")
place_order.parser.add_argument("size", help="Number of units to trade")
place_order.parser.add_argument("price", help="Limit price")

@command
def get_orders(args):
	response = request(f"get_orders", requests.get)
	for order in response:
		if args.field is None:
			print(order)
		else:
			print(order[args.field])
get_orders.parser.add_argument("-f", "--field", nargs = '?', default=None, const="id", type=str, help="Field to return. Defaults to id.")

@command
def display_books(args):
	asset_ids = sys.stdin.read().rstrip().replace('\n',' ').split(' ')
	names = request(f"get_names?asset_ids={','.join(asset_ids)}", requests.get)
	books = [{float(p):x[p] for p in x} for x in request(f"get_books?asset_ids={','.join(asset_ids)}&depth={args.depth}", requests.get)]

	bids,asks = zip(*[[sorted([(p,book[p]) for p in book if side*book[p]>0], reverse=side==1) for side in (1,-1)] for book in books])
	
	width,height = (lambda x : (x.columns, x.lines))(os.get_terminal_size())
	name_len = max(max(map(len,names)),2)

	line_counter = 0
	for name,bid_pairs,ask_pairs in zip(names,bids,asks):

		if line_counter + 3 > height-1:
			break

		side_len = (width - name_len) // 2

		bid_prices, bid_sizes = zip(*bid_pairs)
		ask_prices, ask_sizes = zip(*ask_pairs)
		ask_sizes = [-x for x in ask_sizes]

		price_width = max(map(len,map(str,bid_prices+ask_prices)))
		size_width = max(map(len,map(str,ask_sizes+ask_sizes)))
		cell_width = max(price_width, size_width) + 3

		bid_prices_string = []
		for i,price in enumerate(bid_prices):
			if side_len-(i+1)*cell_width<0:
				break
			bid_prices_string.append(f"{str(price).center(cell_width-3)} | ")
		bid_prices_string = ''.join(reversed(bid_prices_string))

		bid_sizes_string = []
		for i,size in enumerate(bid_sizes):
			if side_len-(i+1)*cell_width<0:
				break
			bid_sizes_string.append(f"{str(size).center(cell_width-3)} | ")
		bid_sizes_string = ''.join(reversed(bid_sizes_string))

		ask_prices_string = []
		for i,price in enumerate(ask_prices):
			if side_len+name_len+(i+1)*cell_width>=width:
				break
			ask_prices_string.append(f" | {str(price).center(cell_width-3)}")
		ask_prices_string = ''.join(ask_prices_string)

		ask_sizes_string = []
		for i,size in enumerate(ask_sizes):
			if side_len+name_len+(i+1)*cell_width>=width:
				break
			ask_sizes_string.append(f" | {str(size).center(cell_width-3)}")
		ask_sizes_string = ''.join(ask_sizes_string)

		print(bid_prices_string.rjust(side_len) + ' '*name_len + ask_prices_string)
		print(bid_sizes_string.rjust(side_len) + name.center(name_len) + ask_sizes_string)
		print('-'*width)
		line_counter += 3
	print(datetime.datetime.now())
	line_counter += 1
	for _ in range(height-line_counter):
		print()

display_books.parser.add_argument("-d", "--depth", nargs = '?', default=0, type=int, help="Maximum number of book levels either side")
	

def main():
	args = main_parser.parse_args()
	methods[args.method](args)

if __name__ == "__main__":
	main()
