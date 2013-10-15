import sys
from ads_conn import ads_conn
from ads_order import ads_order

# test
c = ads_conn(host="ftp.alpha-d-s.com", user=sys.argv[1], password=sys.argv[2])
c.connect()
c.poll(None, None, None)
