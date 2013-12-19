class UnknownRealm(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

class UnableToConnect(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

class InvalidTenantID(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

class CommunicationsError(Exception):
    pass

class SyntaxError(Exception):
    pass

class InvalidIdpMessage(Exception):
    pass
