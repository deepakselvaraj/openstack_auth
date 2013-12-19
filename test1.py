URL = "http://192.168.56.101:35357/v3"
import contrib as s
f = s.federated.federated
fd = f.federated
fx = f.federated_exceptions
fu = f.federated_utils
realms = fd.getRealmList(URL)
print "===realms===", realms
endpoint = fd.getIdPRequest(URL, realms["realms"][0])
print "=====endpoint=====", endpoint
