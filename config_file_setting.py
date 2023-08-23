"""config_file_setting.py
    初期設定ファイルのデータエンティティクラス
    初期設定ファイルの読み込みを行う
"""
import configparser
import dataclasses
import decimal
import os
from typing import List


@dataclasses.dataclass
class ConfigFileEntity:
    """データエンティティ
        configファイルの内容保持用エンティティクラス
    """
    file_nm_base: str
    file_save_dir: str
    dbname :str
    user : str
    password : str
    sql_file_dir : str
    account_id: str
    client_id: str
    client_secret: str
    access_token: str
    api_base_url: str
    visibility_public: str
    visibility_unlisted: str
    visibility_private: str
    visibility_direct: str
    receive_interval : int
    timeout_interval : int
    cost_limit : decimal
    permission_server : List[str]
    api_key: str
    chatgpt_model: str
    temperature: float
    role_system_content: str

class SetConfigFileData:
    """外部設定ファイル設定
        外部設定ファイルを読み込み、設定する。
    """
    def __init__(self):
        """コンストラクタ
        """
        self.config = None
        # 外部設定ファイル読み込み
        self.__read_config_file()
    
    def set_config_datas(self):
        """外部設定ファイル設定
            外部設定ファイルを読み込み、設定する。
        """
        try:
            # 内容設定
            return ConfigFileEntity(
                                    file_nm_base = str(self.config['LogSetting']['file_nm_base']),
                                    file_save_dir = str(self.config['LogSetting']['file_save_dir']),
                                    dbname = str(self.config['DBSetting']['dbname']),
                                    user = str(self.config['DBSetting']['user']),
                                    password = str(self.config['DBSetting']['password']),
                                    sql_file_dir = str(self.config['DBSetting']['sql_file_dir']),
                                    account_id = str(self.config['BotSetting']['account_id']),
                                    client_id = str(self.config['BotSetting']['client_id']),
                                    client_secret = str(self.config['BotSetting']['client_secret']),
                                    access_token = str(self.config['BotSetting']['access_token']),
                                    api_base_url = str(self.config['BotSetting']['api_base_url']),
                                    visibility_public = str(self.config['BotSetting']['visibility_public']),
                                    visibility_unlisted = str(self.config['BotSetting']['visibility_unlisted']),
                                    visibility_private = str(self.config['BotSetting']['visibility_private']),
                                    visibility_direct = str(self.config['BotSetting']['visibility_direct']),
                                    receive_interval = str(self.config['BotSetting']['receive_interval']),
                                    timeout_interval = str(self.config['BotSetting']['timeout_interval']),
                                    cost_limit = str(self.config['BotSetting']['cost_limit']),
                                    permission_server = str(self.config['BotSetting']['permission_server']).split(","),
                                    api_key = str(self.config['chatGPTSetting']['api_key']),
                                    chatgpt_model = str(self.config['chatGPTSetting']['chatgpt_model']),
                                    temperature = str(self.config['chatGPTSetting']['temperature']),
                                    role_system_content = str(self.config['chatGPTSetting']['role_system_content']),
                                    )

        except Exception as e:
            print("Configファイル設定エラー" + str(e))
            exit()
    
    def __read_config_file(self):
        """外部設定ファイル読み込み
        """
        try:
            # 外部設定ファイル読み込み
            self.config = configparser.ConfigParser()
            self.config.read(os.path.dirname(os.path.abspath(__file__)) + r'/Config.ini', 'UTF-8')
        except Exception as e:
            print("外部設定ファイル読み込みエラー。" + str(e))
            exit()