import json, requests, pprint

url = 'https://raw.githubusercontent.com/dugurs/kwh_to_won/main/test/test.json'

# params = dict(
#     origin='Chicago,IL',
#     destination='Los+Angeles,CA',
#     waypoints='Joplin,MO|Oklahoma+City,OK',
#     sensor='false'
# )
# data = requests.get(url=url, params=params)


data = requests.get(url=url)
binary = data.content
output = json.loads(binary)

# test to see if the request was valid
# print output['status']

# output all of the results
pprint.pprint(output)