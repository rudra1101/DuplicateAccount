class ConnectorError(Exception):
    pass


class ConnectorNotFoundError(ConnectorError):
    pass


class ConnectorConfigurationError(ConnectorError):
    pass


class ConnectorConnectionError(ConnectorError):
    pass


class ConnectorFileNotFoundError(ConnectorError):
    pass