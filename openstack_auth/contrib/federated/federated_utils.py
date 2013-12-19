import json
import urllib
import urllib2

#############
# The following functions are not part of the API
# They are tools to avoid code redundancy
#############

## Send a request that will be process by the Federation Middleware
# It add the X-Auth-Type: federated header in the HTTP request
def middlewareRequest(keystoneEndpoint, data = {}, method = "GET"):
    headers = {'X-Authentication-Type': 'federated'}
    if method == "GET":
        data = urllib.urlencode(data)
        req = urllib2.Request(keystoneEndpoint + '?' + data, headers = headers)
        response = urllib2.urlopen(req)
    elif method == "POST":
        data = json.dumps(data)
        headers['Content-Type'] = 'application/json'
        req = urllib2.Request(keystoneEndpoint, data, headers)
        response = urllib2.urlopen(req)
    return response

## Displays the list of tenants to the user so he can choose one
def selectTenant(tenantsList):
    print "You have access to the following tenant(s):"
    for idx, tenant in enumerate(tenantsList):
        print "\t{", idx, "} ", tenant["friendlyName"]
    chosen = False
    choice = None
    while not chosen:
        try:
            choice = int(raw_input("Enter the number corresponding to the tenant you want to use: "))
        except:
            print "An error occurred with your selection"
        if not choice is None:
	    if choice < 0 or choice >= len(tenantsList):
                chosen = False
	        print "The selection made was not a valid choice of tenant"
	    else:
	        chosen = True
    return tenantsList[choice]

## Displays the list of realm to the user
def selectRealm(realmList):
    print "You have access to the following realm(s):"
    for idx, realm in enumerate(realmList):
        print "\t{", idx, "} ", realm["name"]
    choice = None
    while choice is None:
    	try:
            choice = int(raw_input("Enter the number corresponding to the realm you want to use: "))
    	except:
            print "An error occurred with your selection"
    	if choice < 0 or choice >= len(realmList):
            print "The selection made was not a valid choice of realm"
	    choice = None
    return realmList[choice]

## Given a tenants list and a friendly name, returns the corresponding tenantId
def getTenantId(tenantsList, friendlyname):
    for idx, tenant in enumerate(tenantsList):
        if tenant["friendlyName"] == friendlyname:
            return tenant["id"]
