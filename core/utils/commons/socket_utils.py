#/usr/bin/env python3

# -*- encoding: utf-8 -*-
from email import header
import os
import json
import time
import socket
import base64
from typing import AnyStr

from core.utils.commons.networking import pack_msg
from core.utils.commons.networking import unpack_msg

from core.utils.commons.networking import MARSHALPacker
from core.utils.commons.networking import MARSHALUnpacker

from core.utils.commons.exceptions import ReadError
from core.utils.commons.exceptions import WriteError
from core.utils.commons.exceptions import ClientRecvError
from core.utils.commons.exceptions import ClientSendError

from core.utils.commons.io_utils import Modes
from core.utils.commons.io_utils import IOUtils

from core.utils.commons.crypto import AESCipher

from core.utils.commons.commands import Commands
from core.utils.commons.commands import ErrorMessages

from core.utils.printing import *
from core.utils.socket_server import DataBase
key = "30e79f45d426cabf4aeaebb7192c77b5742abf2a1a993bc0a26ebb272bf9809e"
class SockUtils:
    def __init__(self,socket_descriptor = None,aes_key = key,aes_iv = key,auto_exit = True,max_timeout = 60*10) -> None:
        self.socket_descriptor = socket_descriptor
        self.aes_credentials = {
            "key":aes_key,
            "iv":aes_iv
        }
        self.auto_exit = auto_exit
        self.__max_timeout_sec = max_timeout
    def settimeout(self,timeout: int):
        self.__max_timeout_sec = timeout
    def send(self,header: str,**kwargs) -> int:
        raw_data = MARSHALPacker(header,**kwargs)
        encrypted_data = AESCipher(key=self.aes_credentials["key"],iv=self.aes_credentials["iv"]).encrypt(raw_data)
        packed_msg = pack_msg(encrypted_data)
        try:
            self.socket_descriptor.send(packed_msg)
            return len(raw_data)
        except ClientSendError as send_err:
            if self.auto_exit:
                return True # exit the client cmd 
            raise ClientSendError("Hata veri gönderilirken bir hata oluştu ") from send_err

    def recv(self,to_encode = None) -> dict:
        def _recv(socket_descriptor: socket,max_timeout=None) -> bytes:
            if max_timeout:
                socket_descriptor.settimeout(max_timeout)
            try:
                raw_msglen = unpack_msg(socket_descriptor.recv(4))
                raw_data = socket_descriptor.recv(raw_msglen)
                while len(raw_data) < raw_msglen:
                    raw_data+=socket_descriptor.recv(raw_msglen-len(raw_data))
                return raw_data
            except socket.timeout:
                if max_timeout:
                    return b""
                    print_failure("Hata %s saniye boyunca hiç bir veri alınamadı !! " % (self.max_timeout_sec))
                    self.socket_descriptor.settimeout(None) # default
        received_data = _recv(self.socket_descriptor,max_timeout=self.__max_timeout_sec)
        if not received_data == b"" and received_data is not None:
            decrypted_data = AESCipher(key=self.aes_credentials["key"],iv=self.aes_credentials["iv"]).decrypt(received_data)
            unpacked_marshalled_data = MARSHALUnpacker(decrypted_data)
            return unpacked_marshalled_data

    def send_and_recv(self,header = None,**parameters) -> dict:
        self.send(header,parameters)
        return self.recv()
    def recv_until(self,header = None,**kwargs) -> dict:
        self.send(header=header,**kwargs)
        _progress = True
        while _progress:
            data = self.recv()
            if data.header == Commands.COMMAND_EOP:
                _progress = False
            yield data
        yield MARSHALUnpacker(MARSHALPacker(header="NULL"))
    def client_is_online(self):
        try:
            self.send(Commands.COMMAND_DO_GET_CLIENT_IS_ONLINE)
            return Commands.COMMAND_CLIENT_ONLINE
        except:
            return ErrorMessages.ERR_MSG_CLIENT_NOT_ONLINE
    @classmethod
    def get_sock(cls):
        return DataBase.all_client_socks["127.0.0.1"]

    def __repr__(self) -> str:
        return "< %s aes_key=%s aes_iv=%s status=%s >" % (
            self.__class__.__name__,
            self.aes_credentials["key"],
            self.aes_credentials["iv"],
            self.client_is_online()
            )
        