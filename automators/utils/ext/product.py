import re
from typing import List

# Tools
PriceRE = re.compile(r"([Rp.]{2,3} |Rp)(?P<price>[0-9.]*)")
PriceNoCurrencyRE = re.compile(r"(?P<price>[0-9.]*)")
getPriceStr = lambda s: PriceRE.search(s).groupdict().get('price') if s.startswith('Rp') else PriceNoCurrencyRE.search(s).groupdict().get('price')
getPrice = lambda s: float(getPriceStr(s).replace('.', '').replace(',','.')) # ',' for decimal points. '.' for thousands seperator.
getPrice.__name__='getPrice'

# Tools specifically for values
# TODO: REMAKE ALL THE TOOLS TO BE PASSABLE TO EACH OTHER.
# InBetween by default will use getPrice as its valueGetter
CaseInsensitive = lambda matcherString: lambda targetString:targetString.lower()==matcherString.lower()


class Macros:
    getPrice=getPrice
    # Contains = lambda matcherString: lambda targetString: targetString.__contains__(matcherString)
    
    class Contains:
        __slots__=['matcherString']
        def __init__(self, matcherString: str):
            self.matcherString=matcherString
        def __repr__(self):
            return "Contains({!r})".format(self.matcherString)
        def __call__(self, targetString: str):
            return targetString.__contains__(self.matcherString)
    
    # ContainsAny = lambda listOfMatcherString: lambda targetString: any([targetString.__contains__(matcherString) for matcherString in listOfMatcherString])
    class ContainsAny:
        __slots__=['listOfMatcherSubstrings']
        def __init__(self, listOfMatcherSubstrings: List[str]):
            self.listOfMatcherSubstrings=listOfMatcherSubstrings
        def __repr__(self):
            return "ContainsAny({!r})".format(self.listOfMatcherSubstrings)
        def __call__(self, targetString: str):
            return any([targetString.__contains__(s) for s in self.listOfMatcherSubstrings])
    
    # PriceInBetween = lambda start, end, valueGetter=getPrice: (lambda start, end: lambda x: min([start, end]) <= valueGetter(x) <= max([start, end]))(valueGetter(start), valueGetter(end))
    class PriceInBetween:
        __slots__=['start','end','valueGetter','repr_args']
        def __init__(self, start, end, valueGetter=getPrice):
            self.repr_args='{!r}, {!r}, {}'.format(start, end, valueGetter.__name__)
            start, end=valueGetter(start), valueGetter(end)
            self.start=min(start,end)
            self.end=max(start,end)
            self.valueGetter=valueGetter
        def __repr__(self):
            return "PriceInBetween({})".format(self.repr_args)
        def __call__(self, x):
            return self.start<=self.valueGetter(x)<=self.end


Contains=Macros.Contains
ContainsAny=Macros.ContainsAny
PriceInBetween=Macros.PriceInBetween


# Tool for multi statements
# make the function with def to not waste processing power with all(list comp)
def Multi(*statement_list):
    if isinstance(statement_list[0], list) and len(statement_list):
        statement_list=statement_list[0]
    def _all(x):
        for statement in statement_list:
            if not statement(x):
                return False
    return _all

class ProductSpec:
    # Parsed at: 2022-03-15
    products = [{'name': '1 GB semua jaringan + bebas zona', 'description': '1 GB semua jaringan bebas zona, masa aktif 30 hari', 'price': 'Rp 23.500'},
                {'name': 'Gigamax Basic', 'description': 'Kuota MaxStream 12GB + Kuota All Net 3 GB , Masa Berlaku 30 Hari', 'price': 'Rp 51.000'},
                {'name': '[BEST SELLER] 1GB - 3 Hari', 'description': 'Paket Data Up to 1GB sesuai zona (berlaku 3 hari), besaran kuota mengikuti zona, cek zona di *363*46#', 'price': 'Rp 12.500'},
                {'name': 'ZOOM 7 hari 4GB', 'description': '4 GB Kuota Zoom. Masa Berlaku 7 Hari.', 'price': 'Rp 50.300'},
                {'name': 'Disney + Hotstar 12 Bulan - Kuota 3GB MaxStream', 'description': 'Disney + Hotstar 12 Bulan - Kuota 3GB MaxStream. Masa aktif 360 Hari', 'price': 'Rp 145.000'},
                {'name': 'Disney + Hotstar 6 Bulan - Kuota 3GB MaxStream', 'description': 'Disney + Hotstar 6 Bulan - Kuota 3GB MaxStream. Masa aktif 180 Hari', 'price': 'Rp 85.000'},
                {'name': 'ZOOM 1 hari 500MB', 'description': '500 MB Kuota Zoom. Masa Berlaku 1 Hari.', 'price': 'Rp 15.500'},
                {'name': 'Nelpon COMBO 10GB', 'description': '10GB + 2GB VideoMax + 100 mnt + 100 sms (on net) berlaku 30 Hari', 'price': 'Rp 100.400'},
                {'name': '50 MB', 'description': 'DATA FLASH 50MB Semua jaringan bebas zona', 'price': 'Rp 4.900'},
                {'name': 'Up to 50GB + 2GB MAXStream', 'description': 'Paket Data Up to 50GB + 2GB MAXStream sesuai zona (berlaku 30hari), besaran kuota mengikuti zona, cek zona di *363*46#', 'price': 'Rp 200.500'},
                {'name': 'ZOOM 7 hari 4GB', 'description': '4 GB Kuota Zoom. Masa Berlaku 7 Hari.', 'price': 'Rp 50.300'},
                {'name': 'MAXStream Gala 40GB', 'description': 'Kuota MaxStream 30 GB + Kuota All Net 10 GB, Masa Berlaku 30 Hari.', 'price': 'Rp 150.000'},
                {'name': 'Gigamax Fit', 'description': 'Kuota MaxStream 5 GB + Kuota All Net 1 GB, Masa Berlaku 30 Hari', 'price': 'Rp 26.000'},
                {'name': 'OMG! Nonton 34GB kuota* + 51GB aplikasi local', 'description': 'Kuota berdasarkan Length of Stay pelanggan, untuk Length of Stay', 'price': 'Rp 250.500'},
                {'name': 'ZOOM 3 hari 1.5GB', 'description': '1.5 GB Kuota Zoom. Masa Berlaku 3 Hari.', 'price': 'Rp 25.300'},
                {'name': 'Paket OMG 75K 30 Hari', 'description': 'Kuota berdasarkan zona, mohon cek link berikut: http://tsel.me/omgmodern', 'price': 'Rp 75.900'},
                {'name': 'Broadband Zone up to 8GB + 2GB Video 30 Hari', 'description': 'Zoning Quota 4GB - 8GB + 2GB Video, Masa aktif 30 hari sesuai zona', 'price': 'Rp 86.000'},
                {'name': 'Paket Nelpon Telkomsel 25000', 'description': 'Paket Nelpon 550 menit ke sesama Tsel + 50 menit ke semua operator, masa aktif 7 hari. Kuota sesuai zona user, cek di *363*46#', 'price': 'Rp 27.000'},
                {'name': 'GamesMax 3GB', 'description': 'GamesMax 2GB + Internet 1GB + 1 Games Voucher berlaku 30 hari', 'price': 'Rp 25.500'},
                {'name': 'MusicMAX', 'description': 'Data Package 1.25GB, kuota nasional, 0.25GB kuota YouTube, 5 GB Music Apps DPI (Spotify, JOOX, Langit Music, Resso, Deezer, Smule, WeSing, and Starmaker). Masa aktif 30 Hari', 'price': 'Rp 25.700'},
                {'name': 'Gigamax Basic', 'description': 'Kuota MaxStream 12GB + Kuota All Net 3 GB , Masa Berlaku 30 Hari', 'price': 'Rp 51.000'},
                {'name': 'Up to 50GB + 2GB MAXStream', 'description': 'Paket Data Up to 50GB + 2GB MAXStream sesuai zona (berlaku 30hari), besaran kuota mengikuti zona, cek zona di *363*46#', 'price': 'Rp 200.500'},
                {'name': 'ZOOM 30 hari 15GB', 'description': '15 GB Kuota Zoom. Masa Berlaku 30 Hari.', 'price': 'Rp 130.500'},
                {'name': 'Paket Bicara Semua Operator 30 Hari - 85K', 'description': 'Hingga 3900 menit ke Sesama Telkomsel + 100 menit ke Semua Operator. Untuk Regional Papua dan Maluku berlaku masa aktif 14 Hari. Untuk regional lain berlaku masa aktif 30 hari ( tergantung zona), cek kuota di *363*46#', 'price': 'Rp 84.950'},
                {'name': 'Paket OMG 100K 30 Hari', 'description': 'Kuota berdasarkan zona, mohon cek link berikut: http://tsel.me/omgmodern', 'price': 'Rp 100.500'},
                {'name': 'OMG! Nonton 18.5GB kuota* + 30GB aplikasi local', 'description': 'Kuota berdasarkan Length of Stay pelanggan, untuk Length of Stay', 'price': 'Rp 200.000'},
                {'name': '[BEST SELLER] Data 10GB', 'description': 'Up to 8 GB + 2 GB Video sesuai zona (berlaku 30hari), besaran kuota mengikuti zona, cek zona di *363*46#', 'price': 'Rp 85.500'},
                {'name': 'Paket Bicara sesama Telkomsel 30 hari', 'description': 'Paket Bicara sesama Telkomsel 30 hari sesuai zona, cek zona di *363*46#', 'price': 'Rp 105.500'},
                {'name': 'ZOOM 1 hari 500MB', 'description': '500 MB Kuota Zoom. Masa Berlaku 1 Hari.', 'price': 'Rp 15.500'},
                {'name': 'MAXStream Gala 40GB', 'description': 'Kuota MaxStream 30 GB + Kuota All Net 10 GB, Masa Berlaku 30 Hari.', 'price': 'Rp 150.000'},
                {'name': 'Paket Bicara semua operator 1 hari', 'description': 'Paket Bicara semua operator 1 hari sesuai zona, cek zona di *363*46#', 'price': 'Rp 10.500'},
                {'name': 'Disney + Hotstar 12 Bulan - Kuota 3GB MaxStream', 'description': 'Disney + Hotstar 12 Bulan - Kuota 3GB MaxStream. Masa aktif 360 Hari', 'price': 'Rp 145.000'},
                {'name': '[BEST SELLER] Data 1GB - 7 Hari', 'description': 'Paket Data Up to 1GB sesuai zona (berlaku 7 hari), besaran kuota mengikuti zona, cek zona di *363*46#', 'price': 'Rp 20.300'},
                {'name': '[BEST SELLER] Paket Bicara semua operator 3 hari', 'description': 'Paket Bicara semua operator 3 hari sesuai zona, cek zona di *363*46#', 'price': 'Rp 20.400'},
                {'name': '[BEST SELLER] Data 10GB', 'description': 'Up to 8 GB + 2 GB Video sesuai zona (berlaku 30hari), besaran kuota mengikuti zona, cek zona di *363*46#', 'price': 'Rp 85.500'},
                {'name': 'ZOOM 7 hari 4GB', 'description': '4 GB Kuota Zoom. Masa Berlaku 7 Hari.', 'price': 'Rp 50.300'},
                {'name': 'OMG! Nonton 34GB kuota* + 51GB aplikasi local', 'description': 'Kuota berdasarkan Length of Stay pelanggan, untuk Length of Stay', 'price': 'Rp 250.500'},
                {'name': 'OMG! Ketengan 0.7 GB sampai 2 GB', 'description': 'Kuota berdasarkan Zona, mohon cek link berikut\xa0http://tsel.me/omgmodern\xa0atau melalui umb *363*46# . Masa aktif 7 hari', 'price': 'Rp 30.500'},
                {'name': '1 GB semua jaringan + bebas zona', 'description': '1 GB semua jaringan bebas zona, masa aktif 30 hari', 'price': 'Rp 23.500'},
                {'name': 'Paket OMG 50K 30 Hari', 'description': 'Kuota berdasarkan zona, mohon cek link berikut: http://tsel.me/omgmodern', 'price': 'Rp 51.000'},
                {'name': 'OMG! Ketengan 1.3 GB sampai 2.3 GB', 'description': 'Kuota berdasarkan Zona, mohon cek link berikut\xa0http://tsel.me/omgmodern\xa0atau melalui umb *363*46# . Masa aktif 3 hari', 'price': 'Rp 21.700'},
                {'name': 'MAXStream Gala 24GB', 'description': 'Kuota MaxStream 20 GB + Kuota All Net 4 GB, Masa Berlaku 30 Hari.', 'price': 'Rp 100.000'},
                {'name': 'Gigamax Fit', 'description': 'Kuota MaxStream 5 GB + Kuota All Net 1 GB, Masa Berlaku 30 Hari', 'price': 'Rp 26.000'},
                {'name': 'Paket OMG 30K 7 Hari', 'description': 'Kuota berdasarkan zona, mohon cek link berikut: http://tsel.me/omgmodern', 'price': 'Rp 31.000'},
                {'name': 'Disney + Hotstar 3 Bulan - Kuota 3GB MaxStream', 'description': 'Disney + Hotstar 3 Bulan - Kuota 3GB MaxStream. Masa aktif 90 Hari', 'price': 'Rp 55.000'},
                {'name': 'Paket Nelpon Telkomsel 100000', 'description': 'Paket Nelpon 2000 menit ke sesama Tsel + 100 menit ke semua operator, masa aktif 30 hari. Kuota sesuai zona user, cek di *363*46#', 'price': 'Rp 101.000'},
                {'name': 'Data Zone up tp 12GB', 'description': 'Zoning Quota 8GB - 12GB + 2GB OMG, Masa aktif 30 Hari', 'price': 'Rp 105.000'},
                {'name': '[BEST SELLER] Data 1GB - 7 Hari', 'description': 'Paket Data Up to 1GB sesuai zona (berlaku 7 hari), besaran kuota mengikuti zona, cek zona di *363*46#', 'price': 'Rp 20.300'},
                {'name': '500 MB semua jaringan + bebas zona', 'description': '500 MB semua jaringan + bebas zona, masa aktif 30 hari', 'price': 'Rp 14.900'},
                {'name': 'GamesMax 3GB', 'description': 'GamesMax 2GB + Internet 1GB + 1 Games Voucher berlaku 30 hari', 'price': 'Rp 25.500'},
                {'name': 'OMG! Ketengan 1.3 GB sampai 2.3 GB', 'description': 'Kuota berdasarkan Zona, mohon cek link berikut\xa0http://tsel.me/omgmodern\xa0atau melalui umb *363*46# . Masa aktif 3 hari', 'price': 'Rp 21.700'},
                {'name': 'Broadband Zone up to 4,5GB + 2GB OMG', 'description': 'Zoning Quota 2GB - 4,5GB + 2GB OMG, Masa aktif 30 Hari', 'price': 'Rp 69.000'},
                {'name': 'OMG! Nonton 12GB kuota* + 18GB aplikasi local', 'description': 'Kuota berdasarkan Length of Stay pelanggan, untuk Length of Stay', 'price': 'Rp 125.000'},
                {'name': 'Paket Nelpon Telkomsel 20000', 'description': 'Paket Nelpon 370 menit ke sesama Tsel + 30 menit ke semua operator, masa aktif 3 hari. Kuota sesuai zona user, cek di *363*46#', 'price': 'Rp 21.000'},
                {'name': 'OMG! Nonton 12GB kuota* + 18GB aplikasi local', 'description': 'Kuota berdasarkan Length of Stay pelanggan, untuk Length of Stay', 'price': 'Rp 125.000'},
                {'name': 'Paket Bicara Semua Operator 30 Hari - 135K', 'description': 'Hingga 10,200 menit ke Sesama Telkomsel + 200 menit ke Semua Operator. Masa Aktif 30 hari ( tergantung zona). Cek kuota di *363*46#', 'price': 'Rp 135.000'},
                {'name': 'ZOOM 3 hari 1.5GB', 'description': '1.5 GB Kuota Zoom. Masa Berlaku 3 Hari.', 'price': 'Rp 25.300'},
                {'name': 'OMG! Ketengan 2.5 GB sampai 3.7 GB', 'description': 'OMG! Ketengan 2.5 GB sampai 3.7 GB, 1 hari', 'price': 'Rp 15.500'},
                {'name': 'Broadband Zone up to 8GB + 2GB Video 30 Hari', 'description': 'Zoning Quota 4GB - 8GB + 2GB Video, Masa aktif 30 hari sesuai zona', 'price': 'Rp 86.000'},
                {'name': '50 MB', 'description': 'DATA FLASH 50MB Semua jaringan bebas zona', 'price': 'Rp 4.900'},
                {'name': 'Data Zone up tp 12GB', 'description': 'Zoning Quota 8GB - 12GB + 2GB OMG, Masa aktif 30 Hari', 'price': 'Rp 105.000'},
                {'name': 'OMG! Nonton 18.5GB kuota* + 30GB aplikasi local', 'description': 'Kuota berdasarkan Length of Stay pelanggan, untuk Length of Stay', 'price': 'Rp 200.000'},
                {'name': '[BEST SELLER] Paket Bicara semua operator 7 hari', 'description': 'Paket Bicara semua operator 7 hari sesuai zona, cek zona di *363*46#', 'price': 'Rp 25.400'},
                {'name': 'Paket OMG 200K 30 Hari', 'description': 'Kuota berdasarkan zona, mohon cek link berikut: http://tsel.me/omgmodern', 'price': 'Rp 201.000'},
                {'name': 'MAXStream Gala 24GB', 'description': 'Kuota MaxStream 20 GB + Kuota All Net 4 GB, Masa Berlaku 30 Hari.', 'price': 'Rp 100.000'},
                {'name': 'Broadband Zone up to 4,5GB + 2GB OMG', 'description': 'Zoning Quota 2GB - 4,5GB + 2GB OMG, Masa aktif 30 Hari', 'price': 'Rp 69.000'},
                {'name': '3 GB semua jaringan + bebas zona', 'description': '3 GB semua jaringan + bebas zona, masa aktif 30 hari', 'price': 'Rp 72.500'},
                {'name': 'OMG! Ketengan 2.5 GB sampai 3.7 GB', 'description': 'OMG! Ketengan 2.5 GB sampai 3.7 GB, 1 hari', 'price': 'Rp 15.500'},
                {'name': 'Paket OMG 30K 7 Hari', 'description': 'Kuota berdasarkan zona, mohon cek link berikut: http://tsel.me/omgmodern', 'price': 'Rp 31.000'},
                {'name': 'Paket OMG 75K 30 Hari', 'description': 'Kuota berdasarkan zona, mohon cek link berikut: http://tsel.me/omgmodern', 'price': 'Rp 75.900'},
                {'name': 'Paket Bicara sesama Telkomsel 7 hari', 'description': 'Paket Bicara sesama Telkomsel 7 hari sesuai zona, cek zona di *363*46#', 'price': 'Rp 40.500'},
                {'name': 'Disney + Hotstar 1 Bulan - Kuota 3GB MaxStream', 'description': 'Disney + Hotstar 1 Bulan - Kuota 3GB MaxStream. Masa aktif 30 Hari', 'price': 'Rp 25.500'},
                {'name': 'Paket OMG 150K 30 Hari', 'description': 'Kuota berdasarkan zona, mohon cek link berikut: http://tsel.me/omgmodern', 'price': 'Rp 150.750'},
                {'name': 'Paket Nelpon Telkomsel 25000', 'description': 'Paket Nelpon 550 menit ke sesama Tsel + 50 menit ke semua operator, masa aktif 7 hari. Kuota sesuai zona user, cek di *363*46#', 'price': 'Rp 27.000'},
                {'name': '[BEST SELLER] Paket Bicara semua operator 3 hari', 'description': 'Paket Bicara semua operator 3 hari sesuai zona, cek zona di *363*46#', 'price': 'Rp 20.400'},
                {'name': 'Paket Bicara sesama Telkomsel 30 hari', 'description': 'Paket Bicara sesama Telkomsel 30 hari sesuai zona, cek zona di *363*46#', 'price': 'Rp 105.500'},
                {'name': 'Paket Bicara sesama Telkomsel 7 hari', 'description': 'Paket Bicara sesama Telkomsel 7 hari sesuai zona, cek zona di *363*46#', 'price': 'Rp 40.500'},
                {'name': 'Disney + Hotstar 3 Bulan - Kuota 3GB MaxStream', 'description': 'Disney + Hotstar 3 Bulan - Kuota 3GB MaxStream. Masa aktif 90 Hari', 'price': 'Rp 55.000'},
                {'name': 'Paket Nelpon Telkomsel 100000', 'description': 'Paket Nelpon 2000 menit ke sesama Tsel + 100 menit ke semua operator, masa aktif 30 hari. Kuota sesuai zona user, cek di *363*46#', 'price': 'Rp 101.000'},
                {'name': 'ZOOM 30 hari 15GB', 'description': '15 GB Kuota Zoom. Masa Berlaku 30 Hari.', 'price': 'Rp 130.500'}]
    Product_TK = {'TK8': [{'name': 'Data 10GB',
                          'description': 'Paket Data 8 GB + 2 GB Video, berlaku 30 Hari',
                          'price': 'Rp 85.000'}],
                  'TK12': [{'name': 'Data 14GB',
                           'description': 'Paket Data 12 GB + 2 GB Video, berlaku 30 Hari',
                           'price': 'Rp 100.000'}]}
    Product_TN = {'TN1': [{'name': 'Paket Bicara semua operator 1 hari', 
                          'description': 'Paket Bicara semua operator 1 hari sesuai zona, cek zona di *363*46#', 
                          'price': 'Rp 10.500'}],
                  'TN3': [{'name': '[BEST SELLER] Paket Bicara semua operator 3 hari', 
                          'description': 'Paket Bicara semua operator 3 hari sesuai zona, cek zona di *363*46#', 
                          'price': 'Rp 20.400'}],
                  'TN7': [{'name': '[BEST SELLER] Paket Bicara semua operator 7 hari', 
                          'description': 'Paket Bicara semua operator 7 hari sesuai zona, cek zona di *363*46#', 
                          'price': 'Rp 25.400'}],
                  'TN30': [{'name': 'Paket Nelpon Telkomsel 100000', 
                           'description': 'Paket Nelpon 2000 menit ke sesama Tsel + 100 menit ke semua operator, masa aktif 30 hari. Kuota sesuai zona user, cek di *363*46#', 
                           'price': 'Rp 101.000'}],
                  'TN30_': [{'name': 'Paket Bicara Sesama Telkomsel 30 Hari', 
                           'description': 'Nelpon ke sesama Telkomsel hingga 10100 menit. Masa aktif 30 hari. ( tergantung zona). Cek kuota di *363*46#',
                           'price': 'Rp 107.000'}]}
    Product_TI = {'TI20': [{'name': '500 MB semua jaringan + bebas zona', 
                           'description': '500 MB semua jaringan + bebas zona, masa aktif 30 hari', 
                           'price': 'Rp 14.900'}]}
    Products = {}
    Products.update(Product_TK)
    Products.update(Product_TN)
    Products.update(Product_TI)
    PRODUCTS = Products

    ProductCodeCloserToBottom = ['TN30']


class DigiposProductSpec:
    parsed = [{'name': 'Paket Nelpon Sakti/7 hr 7 Hari', 'description': '240 minute Voice All Operator + Sepuasnya Voice TSEL ', 'price': 'Rp 29.200'},
              {'name': 'Paket Nelpon 15 hari 15 Hari', 'description': '100 minute Voice All Operator + 1100 minute Voice TSEL ', 'price': 'Rp 53.000'},
              {'name': 'Nelpon Pas - Pulsa nelpon semua operator 30 hari / 100k 30 Hari', 'description': '100 minute Voice All Operator + 500 SMS SMS All Operator ', 'price': 'Rp 101.000'},
              {'name': 'Nelpon Pas - Pulsa nelpon semua operator 30 hari / 50K 30 Hari', 'description': '50 minute Voice All Operator ', 'price': 'Rp 54.000'},
              {'name': '5Ribu/1Hari 1 Hari', 'description': '50 SMS SMS All Operator ', 'price': 'Rp 6.500'},
              {'name': '2,100mnt/30 hari 30 Hari', 'description': '100 minute Voice All Operator + 2000 minute Voice TSEL ', 'price': 'Rp 117.000'},
              {'name': 'Nelpon Pas - Pulsa nelpon semua operator 7 hari / 25k 7 Hari', 'description': '20 minute Voice All Operator ', 'price': 'Rp 26.200'},
              {'name': '200mnt/1 hari 1 Hari', 'description': '15 minute Voice All Operator + Unlimited Voice TSEL ', 'price': 'Rp 18.700'},
              {'name': 'Paket Nelpon Sakti/30 hr 30 Hari', 'description': 'Sepuasnya Voice TSEL + 1000 minute Voice All Operator ', 'price': 'Rp 101.000'},
              {'name': '6,500mnt/30 hari 30 Hari', 'description': '250 minute Voice All Operator + 6250 minute Voice TSEL ', 'price': 'Rp 160.000'},
              {'name': 'Paket Nelpon Sakti/1 hr 1 Hari', 'description': '40 minute Voice All Operator + Sepuasnya Voice TSEL ', 'price': 'Rp 7.000'},
              {'name': 'Nelpon Pas - Pulsa nelpon semua operator 1 hari / 5K 1 Hari', 'description': '5 minute Voice All Operator ', 'price': 'Rp 6.500'},
              {'name': '400mnt/3 hari 3 Hari', 'description': '30 minute Voice All Operator + 370 minute Voice TSEL ', 'price': 'Rp 23.200'},
              {'name': 'Nelpon Fix - Pulsa nelpon semua operator 3 hari 3 Hari', 'description': '10 minute Voice All Operator ', 'price': 'Rp 10.000'},
              {'name': '600mnt/7 hari 7 Hari', 'description': 'Unlimited Voice TSEL + 50 minute Voice All Operator ', 'price': 'Rp 33.200'},
              {'name': 'Nelpon Pas - Pulsa nelpon semua operator 3 hari / 10K 3 Hari', 'description': '10 minute Voice All Operator ', 'price': 'Rp 11.700'},
              {'name': 'SMS All Opt Bulanan mulai 10 SMS/hari  30 Hari', 'description': '300 SMS SMS All Operator ', 'price': 'Rp 21.200'},
              {'name': '5Ribu/1Hari 1 Hari', 'description': '50 SMS SMS All Operator ', 'price': 'Rp 6.500'},
              {'name': '200mnt/1 hari 1 Hari', 'description': '15 minute Voice All Operator + Unlimited Voice TSEL ', 'price': 'Rp 18.700'},
              {'name': 'Paket Nelpon Sakti/7 hr 7 Hari', 'description': '240 minute Voice All Operator + Sepuasnya Voice TSEL ', 'price': 'Rp 29.200'},
              {'name': 'Nelpon Fix - Pulsa nelpon semua operator 1 hari 1 Hari', 'description': '5 minute Voice All Operator ', 'price': 'Rp 5.000'},
              {'name': 'Nelpon Pas - Pulsa nelpon semua operator 7 hari / 25k 7 Hari', 'description': '20 minute Voice All Operator ', 'price': 'Rp 26.200'},
              {'name': 'Talkmania Murah Sepuasnya Seharian 1 Hari', 'description': '333333.33 minute Voice TSEL ', 'price': 'Rp 9.000'},
              {'name': '400mnt/3 hari 3 Hari', 'description': '30 minute Voice All Operator + 370 minute Voice TSEL ', 'price': 'Rp 23.200'},
              {'name': 'Nelpon Fix - Pulsa nelpon semua operator 3 hari 3 Hari', 'description': '10 minute Voice All Operator ', 'price': 'Rp 10.000'},
              {'name': 'Nelpon Pas - Pulsa nelpon semua operator 30 hari / 100k 30 Hari', 'description': '100 minute Voice All Operator + 500 SMS SMS All Operator ', 'price': 'Rp 101.000'},
              {'name': 'Paket Nelpon 15 hari 15 Hari', 'description': '100 minute Voice All Operator + 1100 minute Voice TSEL ', 'price': 'Rp 53.000'},
              {'name': 'Nelpon Pas - Pulsa nelpon semua operator 30 hari / 50K 30 Hari', 'description': '50 minute Voice All Operator ', 'price': 'Rp 54.000'},
              {'name': 'Nelpon Pas - Pulsa nelpon semua operator 7 hari / 20k 7 Hari', 'description': '20 minute Voice All Operator ', 'price': 'Rp 21.200'},
              {'name': 'Nelpon Pas - Pulsa nelpon semua operator 3 hari / 10K 3 Hari', 'description': '10 minute Voice All Operator ', 'price': 'Rp 11.700'},
              {'name': 'Nelpon Fix - Pulsa nelpon semua operator 1 hari 1 Hari', 'description': '5 minute Voice All Operator ', 'price': 'Rp 5.000'}]
    Products = {'TN3':  [{'name': '400mnt/3 hari 3 Hari', 
                          'description': Contains('30 minute Voice All Operator + 370 minute Voice TSEL'), 
                          'price': 'Rp 23.200'}],
                'TN7':  [{'name': 'Paket Nelpon Sakti/7 hr 7 Hari',
                          'description': ContainsAny(['240 minute Voice All Operator + Sepuasnya Voice TSEL', '30 minute Voice All Operator + Sepuasnya Voice TSEL']),
                          'price':PriceInBetween('Rp 4.000', 'Rp 38.800')},
                         {'name': '600mnt/7 hari 7 Hari',
                          'description': Contains('Unlimited Voice TSEL + 50 minute Voice All Operator'),
                          'price':PriceInBetween('Rp 4.000', 'Rp 33.700')}],
                'TN30': [{'name': 'Paket Nelpon Sakti/30 hr 30 Hari', 
                          'description': Contains('Sepuasnya Voice TSEL + 1000 minute Voice All Operator'), 
                          'price': PriceInBetween('Rp 15.000', 'Rp 110.000')},
                         {'name': '2,100mnt/30 hari 30 Hari',
                          'description': Contains('100 minute Voice All Operator + 2000 minute Voice TSEL'),
                          'price': PriceInBetween('Rp 15.000', 'Rp 117.500')}]}
    
    # Confirmation product name are different, pay close attention. DO NOT CHANGE TO THE SAME NAME.
    ProductsConfirmation = {'TN3':  [{'name': Contains('400mnt/3 hari'),
                                     'price': 'Rp 23.200'}],
                            'TN7':  [{'name': ContainsAny(['Paket Nelpon Sakti/7 hr', '600mnt/7 hari']),
                                     'price': PriceInBetween('Rp 4.000', 'Rp 38.800')}],
                            'TN30': [{'name': ContainsAny(['Paket Nelpon Sakti/30 hr', '2,100mnt/30 hari']),
                                     'price': PriceInBetween('Rp 15.000', 'Rp 118.000')}]}


class MitraTokopediaProductSpec:
    parsed=[{}]
    Products = {}
    
    Products_TN = {'TN3': [{'name': Contains('Paket Bicara Semua Operator 3 Hari'),
                            'description': ContainsAny(['', 
                                                        #'Hingga 700 menit ke Sesama Telkomsel + 25 menit ke Semua Operator. Masa Aktif 3 hari. KUOTA SESUAI ZONA USER, SILAHKAN CEK di *363*46#']
                                                        ]),
                            'price': PriceInBetween('Rp19.975', 'Rp20.000')}],
                   'TN7':  [{'name': Contains('Paket Bicara Semua Operator 7 Hari'), # 'Bicara 375mnt-950mnt(Zona)'
                            'description': ContainsAny(['', 
                                                        # 'Hingga 950 menit Nelpon ke sesama Telkomsel + 50 menit Nelpon ke semua operator. Masa aktif 7 hari. KUOTA SESUAI ZONA USER, SILAHKAN CEK di *363*46#'
                                                        ]),
                            'price': 'Rp24.850'}],
                   '1TN7':  [{'name': Contains('Bicara 375mnt-950mnt(Zona)'),
                            'description': ContainsAny(['', 
                                                        # 'Hingga 950 menit Nelpon ke sesama Telkomsel + 50 menit Nelpon ke semua operator. Masa aktif 7 hari. KUOTA SESUAI ZONA USER, SILAHKAN CEK di *363*46#'
                                                        ]),
                            'price': 'Rp24.950'}]
                   }
    
    Products_TI = {'TI10': [{'name': Contains('Flash 100MB'),
                             'description': Contains('100MB All network, bebas zona'),
                             'price': 'Rp5.000'}],
                   'TI20': [{'name': Contains('Flash 500MB'),
                             'description': Contains('500MB All network, bebas zona'),
                             'price': 'Rp9.500'}],
                   'TI25': [{'name': Contains('Flash 1GB'),
                             'description': Contains('1GB All network, bebas zona'),
                             'price': 'Rp19.800'}]
                   }
    
    ProductCodeCloserToBottom = [] #'TN3','TN7'
    
    Products.update(Products_TN)
    Products.update(Products_TI)
