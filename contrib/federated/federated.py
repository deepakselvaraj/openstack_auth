import os
import json
import BaseHTTPServer
import ssl
import urlparse
import urllib2
import webbrowser
import federated_exceptions as fe
import federated_utils as futils

## The super-function calls different API methods to obtain the scoped token
# @param keystoneEndpoint The keystone url
# @param realm The IdP the user will be using
# @param tenantFn The tenant friendly name the user wants to use
def federatedAuthentication(keystoneEndpoint, realm = None, tenantFn = None):
    realms = getRealmList(keystoneEndpoint)
    if realm is None or {'name': realm} not in realms['realms']:
        realm = futils.selectRealm(realms['realms'])
    request = getIdPRequest(keystoneEndpoint, realm)
    response = getIdPResponse(request['idpEndpoint'], request['idpRequest'])
    tenantData = getUnscopedToken(keystoneEndpoint, response, realm)
    tenant = futils.getTenantId(tenantData['tenants'], tenantFn)
    if tenant is None:
        tenant = futils.selectTenant(tenantData['tenants'])['id']
    scopedToken = swapTokens(keystoneEndpoint, tenantData['unscopedToken'], tenant)
    return scopedToken

## Get the list of all the IdP available
# @param keystoneEndpoint The keystone url
def getRealmList(keystoneEndpoint):
    data = {}
    resp = futils.middlewareRequest(keystoneEndpoint, data, 'POST')
    info = json.loads(resp.read())
    return info

## Get the authentication request to send to the IdP
# @param keystoneEndpoint The keystone url
# @param realm The name of the IdP
def getIdPRequest(keystoneEndpoint, realm):
    data = {'realm': realm}
    resp = futils.middlewareRequest(keystoneEndpoint, data, 'POST')
    info = json.loads(resp.read())
    return info

# This variable is necessary to get the IdP response
response = None

## Sends the authentication request to the IdP along 
# @param idpEndpoint The IdP address
# @param idpRequest The authentication request returned by Keystone
def getIdPResponse(idpEndpoint, idpRequest):
    global response
    response = None
    config = open(os.path.join(os.path.dirname(__file__),"config/federated.cfg"), "Ur")
    line = config.readline().rstrip()
    key = ""
    cert = ""
    timeout = 300
    while line:
        if line.split('=')[0] == "KEY":
            key = line.split("=")[1].rstrip()

        if line.split("=")[0] == "CERT":
            cert = line.split("=")[1].rstrip()
	if line.split('=')[0] == "TIMEOUT":
	    timeout = int(line.split("=")[1])
        line = config.readline().rstrip()
    config.close()
    if key == "default":
	key = os.path.join(os.path.dirname(__file__),"certs/server.key")
    if cert == "default":
        cert = os.path.join(os.path.dirname(__file__),"certs/server.crt")
    webbrowser.open(idpEndpoint + idpRequest)
    class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
        
        def log_request(code=0, size=0):
            return
        def log_error(format="", msg=""):
            return
        def log_request(format="", msg=""):
            return

        def do_POST(self):
            global response
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            varLen = int(self.headers["Content-Length"])
            #response = urlparse.parse_qs(self.rfile.read(varLen))
            response = self.rfile.read(varLen)
            if response is None:
                self.wfile.write("An error occured.")
                raise federated_exceptions.CommunicationsError()
            self.wfile.write("You have successfully logged in. "
                             "You can close this window now.")
    httpd = BaseHTTPServer.HTTPServer(('localhost', 8080), RequestHandler)
    try:
    	httpd.socket = ssl.wrap_socket(httpd.socket, keyfile=key, certfile=cert, server_side=True)
	httpd.socket.settimeout(1)
    except BaseException as e:
	print e.value
    count = 0
    while response is None and count < timeout:
    	try:
            httpd.handle_request()
	    count = count + 1
        except Exception as e:
	    print e.value
    if response is None:
	print ("There was no response from the Identity Provider or the request timed out")
        exit("An error occurred, please try again")
    return response

## Get an unscoped token for the user along with the tenants list
# @param keystoneEndpoint The keystone url
# @param idpResponse The assertion retreived from the IdP
def getUnscopedToken(keystoneEndpoint, idpResponse, realm = None):
    if realm is None:
	data = {'idpResponse' : idpResponse}
    else:
    	data = {'idpResponse' : idpResponse, 'realm' : realm}
    resp = futils.middlewareRequest(keystoneEndpoint, data, 'POST')
    info = json.loads(resp.read())
    return info

## Get a tenant-scoped token for the user
# @param keystoneEndpoint The keystone url
# @param idpResponse The assertion retreived from the IdP
# @param tenantFn The tenant friendly name
def getScopedToken(keystoneEndpoint, idpResponse, tenantFn):
    response = getUnscopedToken(keystoneEndpoint, idpResponse)
    tenantId = futils.getTenantId(response["tenants"])
    if tenantId is None:
        print "Error the tenant could not be found, should raise InvalidTenant"
    scoped = swapTokens(keystoneEndpoint, response["unscopedToken"], tenantId)
    return scoped

## Get a scoped token from an unscoped one
# @param keystoneEndpoint The keystone url
# @param unscopedToken The unscoped authentication token obtained from getUnscopedToken()
# @param tenanId The tenant Id the user wants to use
def swapTokens(keystoneEndpoint, unscopedToken, tenantId):
    data = {'auth' : {'token' : {'id' : unscopedToken}, 'tenantId' : tenantId}}
    data = json.dumps(data)
    req = urllib2.Request(keystoneEndpoint + "tokens", data, {'Content-Type' : 'application/json'})
    resp = urllib2.urlopen(req)
    return json.loads(resp.read())
