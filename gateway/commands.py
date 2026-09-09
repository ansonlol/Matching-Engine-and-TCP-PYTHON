from dataclasses import dataclass
from typing import Any 

@dataclass(slots=True)
class Command:
    """One inbound message from a client, for the matching thread."""
    client_id : int # where the connections is from whom
    message_type : int # the add cancel modify thing
    payload : bytes  # the raw bytes message

@dataclass(slots=True)
class Reply:
    # one outbound message from server frammed back to client
    client_id : int
    message_type : int # order accept reject trades
    proto_msg : Any 


