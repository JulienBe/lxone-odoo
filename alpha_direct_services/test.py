import sys
from ads_conn import ads_conn
from ads_order import ads_order

# test
c = ads_conn(host="ftp.alpha-d-s.com", user=sys.argv[1], password=sys.argv[2])
c.connect()
d = ads_order()
d.set_shipping(civility='civ', firstname='firstname', name='name', corp_name='test', adr1='test', \
		adr2='test', adr3='test', adr4='test', country='test', zip='test', city='test', phone='test', email='test')
c.upload_data(d)
