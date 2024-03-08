import os
from typing import Union
from pydantic import BaseModel

import requests

HUBBLE_URL = os.environ.get("HUBBLE_URL")

class CastId(BaseModel):
    fid: int
    hash: str

class UntrustedData(BaseModel):
    fid: int
    url: str
    messageHash: str
    timestamp: int
    network: int
    buttonIndex: int
    inputText: Union[str, None] = None
    castId: CastId

class TrustedData(BaseModel):
    messageBytes: str

class FCPostData(BaseModel):
    untrustedData: UntrustedData
    trustedData: TrustedData
    
class FrameActionBody(BaseModel):
    url: str
    buttonIndex: int
    inputText: str
    castId: CastId
    state: str

class ValidMessageData(BaseModel):
    type: str
    fid: int
    timestamp: int
    network: str
    frameActionBody: FrameActionBody

class ValidMessage(BaseModel):
    data: ValidMessageData
    hash: str
    hashScheme: str
    signature: str
    signatureScheme: str
    signer: str

class ValidateMessageResponse(BaseModel):
    valid: bool
    message: Union[ValidMessage, None] = None

class User(BaseModel):
    fid: int
    name: str
    display_name: str
    pfp: str
    primary_address: str


def validate(messageHash: str) -> ValidateMessageResponse:
    url = f"{HUBBLE_URL}/validateMessage"
    headers = { "Content-Type": "application/octet-stream" }
    data = bytes.fromhex(messageHash)
    response = requests.post(url, headers=headers, data=data).json()
    return ValidateMessageResponse(**response)

def user_info(fid: int) -> User:
    # get linked addresses
    res = requests.get(f"{HUBBLE_URL}/verificationsByFid?fid={fid}")
    messages = res.json().get('messages', [])
    addresses = [m['data']['verificationAddEthAddressBody']['address'] for m in messages]

    # get user data
    res = requests.get(f"{HUBBLE_URL}/userDataByFid?fid={fid}")
    messages = res.json().get('messages', [])
    pfp = ""
    name = ""
    display_name = ""
    for message in messages:
        data = message['data']
        type = data['userDataBody']['type']
        value = data['userDataBody']['value']
        if type == "USER_DATA_TYPE_PFP":
            pfp = value
        elif type == "USER_DATA_TYPE_USERNAME":
            name = value
        elif type == "USER_DATA_TYPE_DISPLAY":
            display_name = value

    primary_address = str(addresses[0]) if len(addresses) > 0 else ""
    return User(fid=fid, name=name, display_name=display_name, pfp=pfp, primary_address=primary_address)