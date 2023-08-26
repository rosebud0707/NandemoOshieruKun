"""mastodon_service.py
    Mastodonに関連する処理
"""
import asyncio
import dataclasses
from datetime import datetime, timedelta

from bs4 import BeautifulSoup 
from mastodon import Mastodon, StreamListener

from config_file_setting import SetConfigFileData
from database_manager import DatabaseManager
from generate_toots import GenerateToots
from logger_utils import Logger


@dataclasses.dataclass
class NotifiEntity:
    """データエンティティ
        notificationの内容保持用エンティティクラス
    """
    visibility: str
    cn_mention: int
    id : str
    uri : str
    content_raw : str
    content : str

class MastodonService:
    """MastodonService
        Mastodonの初期設定を行い、StreamListerを起動する。
    """
    def __init__(self):
        """コンストラクタ
            Args:
                config:初期設定ファイル
                logger:ログクラス
        """
        # 各インスタンス化
        self.config_instance = SetConfigFileData()
        self.config = self.config_instance.set_config_datas()
        self.logger_instance = Logger(self.config)
        self.mastodon = Mastodon(client_id = self.config.client_id,
                                 client_secret = self.config.client_secret,
                                 access_token = self.config.access_token,
                                 api_base_url = self.config.api_base_url )
        
    def start_stream(self):
        """Stream開始
            Streamを開始する。
        """
        self.logger_instance.info("StreamListnerの起動")    
        self.mastodon.stream_user(Stream(self.config, self.logger_instance, self.mastodon))

class Stream(StreamListener):
    """StreamListenerを継承
       各種StreamListenerの処理を行う
    """
    def __init__(self, config, logger, mastodon):
        """コンストラクタ
            Args:
                config:外部設定ファイル保持データクラス
                logger:ロガーインスタンス
                mastodon:Mastodonインスタンス
        """
        self.logger = logger
        self.mastodon = mastodon
        self.config = config

    def on_notification(self, notif):
        """通知受信処理
            通知を受信した場合の処理
            Args:
                notif:通知
        """
        try:
            if notif['type'] == 'mention':
                self.logger.info("mentionの検知")

                # 受け取った通知内容のセット
                notifi_entity = self.__set_notification(notif)
                
                # 公開範囲設定。directでリプライされた際はdirectで、それ以外はunlistedで返答を行う。
                if notifi_entity.visibility == 'direct':
                    visibility_status = self.config.visibility_direct
                else:
                    visibility_status = self.config.visibility_unlisted

                # 返信要件チェック
                if self.__check_validation(notifi_entity) == True:
                    # コスト取得
                    self.api_cost = self.__get_api_cost()

                    if len(str(notifi_entity.content)) == 0: 
                        # 未入力チェック
                        self.logger.warning("質問未入力")
                        self.mastodon.status_reply(notif['status'] , '質問内容を入力してください。', notifi_entity.id, visibility = visibility_status)
                    elif(self.api_cost > float(self.config.cost_limit)):
                        # コストチェック
                        self.logger.warning("コスト超過")
                        self.mastodon.status_reply(notif['status'] , '本日の営業は終了しました。明日の利用をお願いいたします。', notifi_entity.id, visibility = visibility_status)
                    else:
                        # 正常処理
                        now = datetime.now()
                        # 質問文登録
                        self.__regist_question(notifi_entity.id, now, notifi_entity.content)

                        self.logger.info('@' + str(notifi_entity.id) + "さんへ返信処理開始")
                        content = "こんにちは。" + notifi_entity.content
                        self.logger.info("質問文:" + str(content))

                        generateToots = GenerateToots()
                        loop = asyncio.get_event_loop()
                        res = loop.run_until_complete((generateToots.process_wait(content, notifi_entity.id))) # 回答文生成

                        self.__do_toot(res, notifi_entity.id, notif['status'], visibility_status) # トゥート

        except Exception as e:
            self.logger.critical("通知の受信に関して、エラーが発生しました。" + str(e))
    
    def __get_api_cost(self):
        """APIコスト取得
            実行日のAPIコストを取得する。
            Return:
                APIコスト数
        """
        try:
            # DatabaseManagerインスタンス化
            dbmanager_instance = DatabaseManager(self.config, "SQL_001.sql")
            # SQL実行
            dr = dbmanager_instance.exec_select()

            if dr['API_COST'] is None or len(dr['API_COST']) == 0:
                api_cost = 0
            else:
                api_cost = float(dr['API_COST'])
        
            return api_cost
        except Exception as e:
            self.logger.critical("APIコスト取得処理で、エラーが発生しました。" + str(e))
            raise e
    
    def __set_notification(self, notif):
        """通知内容のうち処理に必要な項目をデータクラスに設定する
            Args:
                notif:通知
            Returns:
                NotifiEntity
        """
        try:
            return NotifiEntity(
                                visibility = str(notif['status']['visibility']), # visivility
                                cn_mention = len(notif['status']['mentions']), # mentionに含まれるアカウント数
                                id = str(notif['status']['account']['username']), # id
                                uri = str(notif['status']['uri']), # ユーザのインスタンスURI
                                content_raw = str(notif['status']['content']), # リプライ内容
                                content = str(self.__edit_content(str(notif['status']['content']))) # 質問文の編集                         
            )
        except Exception as e:
            self.logger.critical("NotifiEntity設定時にエラーが発生しました。" + str(e))
            raise e
        
    def __edit_content(self, content_raw):
        '''質問内容編集
            取り出したリプライの情報より、質問文を編集する。
            Args:
                content_raw:タグを含んだリプライ文
            Returns:
                編集済質問文
        '''
        try:
            self.logger.info("質問文の編集処理開始")

            # 改行の削除
            content_raw = str(content_raw).replace("<br>", " ")
            content_raw = str(content_raw).replace("</br>", " ")
            content_raw = str(content_raw).replace("<br />", " ")

            html_data = BeautifulSoup(content_raw, "html.parser")

            links = html_data.find_all("a") # リンクを抽出

            # URLを連結する
            content_links = ""
            if len(links) > 1:
                for i in range(1, len(links)):
                    content_links += links[i].get("href") + ' '

            # リプライ本文を抜き出す
            if html_data.find("span").text == None:
                content = ""
            else:
                content = html_data.find("span").text
            
            # リプライ本文とURLを結合する
            return content + content_links
        
        except Exception as e:
            self.logger.critical("質問文編集処理で、エラーが発生しました。" + str(e))
            raise e
                
    def __check_validation(self, notifi_entity):
        '''バリデーションチェック
            受信した通知が返信要件をみたいしているかを確認
            Args:
                notifi_entity:受信した通知内容
            Returns:
                True:チェックOK
                False:チェックNG
        '''
        try:
            self.logger.info("バリデーションチェック")

            # インスタンスチェック 他インスタンスへは返信を行わない。
            if notifi_entity.uri in self.config.permission_server:
                self.logger.warning("許可外サーバーからのリプライです。")
                return False
                # 質問者以外のアカウントへのリプライ防止
            elif notifi_entity.cn_mention > 1:
                self.logger.warning("複数アカウントの検知。")
                return False
            # 投稿間隔チェック
            elif self.__check_receive_interval(notifi_entity.id) == False:
                self.logger.warning("投稿間隔が短いです。")
                return False
            else:
                return True

        except Exception as e:
            self.logger.critical("バリデーションチェックで、エラーが発生しました。" + str(e))
            raise e        

    def __check_receive_interval(self, id):
        '''投稿間隔チェック
            同一IDより規定時間以内に再度投稿されたかを確認する。規定時間以内の場合は処理を行わない。
            Args:
                id:アカウントID
            Returns:
                True:チェックOK
                False:チェックNG
        '''
        try:
            self.logger.info("投稿間隔チェック")
            # DatabaseManagerインスタンス化
            dbmanager_instance = DatabaseManager(self.config, "SQL_002.sql")
            # SQL実行
            dr = dbmanager_instance.exec_select((id))

            # 前回の投稿時刻の取得
            dt_recent = dr['RECENT_POST_TIME'][0]
            
            if dt_recent is None:
                return True
            else:
                if datetime.now() > dt_recent + timedelta(seconds = int(self.config.receive_interval)):
                    # 規定間隔を超過していた場合
                    return True
                else:
                    # 規定間隔内の場合
                    return False

        except Exception as e:
            self.logger.critical("投稿間隔チェックで、エラーが発生しました。" + str(e))
            raise e

    def __regist_question(self, id, ts, content):
        '''質問登録
            質問をDB上に登録する。
            Args:
                id:アカウントID
                ts:現在日時
                content:本文
        '''
        try:
            # DatabaseManagerインスタンス化
            dbmanager_instance = DatabaseManager(self.config, "SQL_003.sql")
            # SQL実行
            dbmanager_instance.exec_query(id, ts, content)
        
        except Exception as e:
            self.logger.critical("DB登録に関して、エラーが発生しました。" + str(e))
            raise e

    def __do_toot(self, response, id, st, visibility_param):
        """トゥート処理
            生成文書を編集し、トゥートする。
            Args:
                response:生成文
                id:Mastodon User ID
                st:status
                visibility_param:visibility
        """
        try:
            if response == 'None':
                self.logger.critical("予期せぬエラーの発生。")
                self.mastodon.status_post('予期せぬエラーの発生。強制終了します。', visibility = 'unlisted')
                exit()

            # 予期せぬリプライの防止
            response = str(response).replace('@', '＠')

            self.logger.info("トゥート")
            if len('@' + id + ' ' + response) > 500:  # トゥート上限エラー回避。
                length = len('@' + id + ' ' + response)
                splitLine =  [response[i:i+450] for i in range(0, length, 450)]

                for num in range(len(splitLine)):
                    # 返信
                    self.mastodon.status_reply(st,
                                str(splitLine[num]),
                                id,
                                visibility = visibility_param)
            else:
                # 返信
                self.mastodon.status_reply(st,
                        str(response),
                        id,
                        visibility = visibility_param)
                
        except Exception as e:
            self.logger.critical("トゥート処理にて、エラーが発生しました。" + str(e))
            raise e