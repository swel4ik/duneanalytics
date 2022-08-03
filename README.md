# Dune Analytics

[![Python 3.9](https://img.shields.io/badge/python-3.9-blue.svg)](https://www.python.org/downloads/release/python-390/)

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

[![Build](https://github.com/itzmestar/duneanalytics/actions/workflows/python-package.yml/badge.svg)](https://github.com/itzmestar/duneanalytics/actions/workflows/python-package.yml)
<hr style="border:0.5px solid gray"> </hr>

### Unofficial Python Library for [Dune Analytics](https://duneanalytics.com/)

The library can be used to fetch the table data from `python` backend.

#### Disclaimer: Use at your own risk! 
It may not work for some/all urls.

This library doesn't run the query, rather it fetches the query result from the backend.

<hr style="border:0.5px solid gray"> </hr>

### Charts Plotted:
Here are some examples of charts plotted in Googlesheet after fetching the data.

-----

[**@balancerlabs / Balancer New/Old Traders**](https://duneanalytics.com/queries/31203/62900)

![Balancer](sample/balancer.svg)

-----

[**@k06a / 1inch New/Old Users Per Day**](https://duneanalytics.com/queries/1193/2032)

![1inch](sample/1inch.svg)

-----

[**@Bancor / Bancor Unique Protected Wallets Over Time**](https://duneanalytics.com/queries/12948/25894)

![Bancor](sample/bancor.svg)

<hr style="border:0.5px solid gray"> </hr>

### Installation:

use pip to install:

``` 
pip install duneanalytics
```

<hr style="border:0.5px solid gray"> </hr>

### Authentication:

You need to have `username` & `password` for [Dune Analytics](https://duneanalytics.com/)

<hr style="border:0.5px solid gray"> </hr>

### Example usage:

```
from duneanalytics import DuneAnalytics
```
#### Initialize client and login
```
dune = DuneAnalytics('username', 'password', 'ACCESS_ID', 'SECRET_KEY')
# try to login
dune.login()
# fetch token
dune.fetch_auth_token()

# fetch query result id using query id
# query id for any query can be found from the url of the query:
# for example: 
# https://dune.com/queries/4494/8769 => 4494
# https://dune.com/queries/3705/7192 => 3705
# https://dune.com/queries/3751/7276 => 3751

result_id = dune.query_result_id(query_id=5508)

# fetch query result
data = dune.query_result(result_id)
```
#### Download and save csv from Dune
```
# save csv
save_path = './'

# convert json data to csv
dune.query2csv(data, save_path)

# alternative end-to-end csv download with dune pro
dune.download_csv(result_id, save_path)
```
#### End-to-end Dune to S3 uploading
```
result_id = dune.query_result_id(query_id=935947)
dune.dune2space(result_id)
```
#### Update permission for all files in s3 space
`dune.update_permissions()`
### Interaction with dydx exchange API
`pip install dydx-v3-python`
#### Get asset current price and upload to the s3 space
```
from duneanalytics import DuneAnalytics

client = DuneAnalytics('username', 'password', 'ACCESS_ID', 'SECRET_KEY')
client.dydx2space('ICP')
# Output: ICP.csv file on s3 with current ICP price
```
