from dydx3 import Client
import os


class DydxExchange:

    def __init__(self):
        self.public_client = Client(host='https://api.dydx.exchange')

    def get_current_price(self, asset: str, save_path: str = './'):
        markets = self.public_client.public.get_markets()
        data = markets.data['markets'][f'{asset}-USD']['indexPrice']
        with open(f'{os.path.join(save_path, asset)}.csv', 'w') as f:
            f.write('price\n')
            f.write(data)

    # def dydx2space(self, asset: str, save_path: str = './'):
    #     self.get_current_price(asset=asset, save_path=save_path)

