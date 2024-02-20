"""mastodon_service.py
    Mastodonに関連する処理
"""
import asyncio
import dataclasses
from datetime import datetime, timedelta
import random
import re

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
    noti: dict
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
                if self.__check_validation(notifi_entity, visibility_status):
                    # 正常処理
                    now = datetime.now()

                    # 質問文登録
                    self.__regist_question(notifi_entity.id, now, notifi_entity.content)

                    self.logger.info('@' + str(notifi_entity.id) + "さんへ返信処理開始")
                    content = "こんにちは。" + notifi_entity.content
                    self.logger.info("質問文:" + str(content))

                    # 回答文生成
                    generateToots = GenerateToots()
                    loop = asyncio.get_event_loop()
                    res = loop.run_until_complete((generateToots.process_wait(content, notifi_entity.id)))

                    self.__do_toot(res, notifi_entity, visibility_status)

        except Exception as e:
            self.logger.critical("通知の受信に関して、エラーが発生しました。" + str(e))
        
    def __set_notification(self, notif):
        """通知内容のうち処理に必要な項目をデータクラスに設定する
            Args:
                notif:通知
            Returns:
                NotifiEntity
        """
        try:
            return NotifiEntity(
                                noti = notif['status'], # status
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

            # リプライ本文を抜き出す
            content = ""
            if not html_data.find("span", class_='h-card'):
                # Misskeyからのリプライ
                if html_data.find("a").next_sibling != None:
                    content = html_data.find("a").next_sibling
            else:
                # Mastodonからのリプライ
                if html_data.find("span").next_sibling != None:
                    content = html_data.find("span").next_sibling

            # リプライ本文返却
            return content
        
        except Exception as e:
            self.logger.critical("質問文編集処理で、エラーが発生しました。" + str(e))
            raise e
                
    def __check_validation(self, notifi_entity, visibility_status):
        '''バリデーションチェック
            受信した通知が返信要件をみたいしているかを確認
            Args:
                notifi_entity:受信した通知内容
                visibility_status:botの返信時visibility
            Returns:
                True:チェックOK
                False:チェックNG
        '''
        try:
            self.logger.info("バリデーションチェック")

            # 質問者にエラー内容を返答しない種類のバリデーションチェック。
            regex_pattern = "|".join(self.config.permission_server)
            if re.match(regex_pattern, notifi_entity.uri) is None:
                # インスタンスチェック 他インスタンスへは返信を行わない。
                self.logger.warning("許可外サーバーからのリプライです。")
                return False

            elif notifi_entity.cn_mention > 1:
                # 質問者以外のアカウントへのリプライ防止
                self.logger.warning("複数アカウントの検知。")
                return False
            
            elif not self.__check_receive_interval(notifi_entity.id):
                # 投稿間隔チェック
                self.logger.warning("投稿間隔が短いです。")
                return False


            # 質問者にエラー内容を返答する種類のバリデーションチェック。
            # コスト取得
            self.api_cost = self.__get_api_cost()

            if len(str(notifi_entity.content).replace(' ', '')) == 0: 
                # 未入力チェック
                self.logger.warning("質問未入力")
                self.mastodon.status_reply(notifi_entity.noti, '質問内容を入力してください。', notifi_entity.id, visibility = visibility_status)

            elif(self.api_cost > float(self.config.cost_limit)):
                # コストチェック
                self.logger.warning("コスト超過")
                if 'おみくじ' in notifi_entity.content:
                    self.mastodon.status_reply(notifi_entity.noti, self.__lottery(), notifi_entity.id, visibility = visibility_status)

                else:
                    # コスト超過時告知文
                    self.mastodon.status_reply(notifi_entity.noti, '今日はもうちょっと疲れたから、質問に答えるのはしんどいわ。でもおみくじやったらできるで。「おみくじ」って話しかけてや。',\
                                            notifi_entity.id, visibility = visibility_status)

            elif self.__check_include_url(notifi_entity.content_raw):
                # URLチェック
                self.logger.warning("URLを含む投稿")
                self.mastodon.status_reply(notifi_entity.noti, '質問文にURLが含まれています。URLを削除して再度投稿してくだいさい。', notifi_entity.id, visibility = visibility_status)

            else:
                return True

        except Exception as e:
            self.logger.critical("バリデーションチェックで、エラーが発生しました。" + str(e))
            raise e        

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

    def __check_include_url(self, content_raw):
        '''URLチェック
            URLリンクが質問文に含まれる場合は返信を行わない。
            Args:
                content_raw:HTML情報を含んだ通知情報
            Returns:
                True:チェックOK
                False:チェックNG
        '''
        try:
            content_raw = str(content_raw).replace("<br>", " ")
            content_raw = str(content_raw).replace("</br>", " ")
            content_raw = str(content_raw).replace("<br />", " ")

            html_data = BeautifulSoup(content_raw, "html.parser")

            # リンクを抽出
            links = html_data.find_all("a")

            # URL検知
            if len(links) > 1:
                return True
            else:
                return False

        except Exception as e:
            self.logger.critical("リンクチェックで、エラーが発生しました。" + str(e))
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

    def __do_toot(self, response, notifi_entity, visibility_param):
        """トゥート処理
            生成文書を編集し、トゥートする。
            Args:
                response:生成文
                notifi_entity:通知情報保持データエンティティ
                visibility_param:返信時のvisibility
        """
        try:
            if response == 'None':
                self.logger.critical("予期せぬエラーの発生。")
                self.mastodon.status_post('予期せぬエラーの発生。強制終了します。', visibility = 'unlisted')
                exit()

            # 予期せぬリプライの防止
            response = str(response).replace('@', '＠')

            self.logger.info("トゥート")
            if len('@' + notifi_entity.id + ' ' + response) > 500:  # トゥート上限エラー回避。
                length = len('@' + notifi_entity.id + ' ' + response)
                splitLine =  [response[i:i+450] for i in range(0, length, 450)]

                for num in range(len(splitLine)):
                    # 返信
                    self.mastodon.status_reply(notifi_entity.noti,
                                str(splitLine[num]),
                                notifi_entity.id,
                                visibility = visibility_param)
            else:
                # 返信
                self.mastodon.status_reply(notifi_entity.noti,
                        str(response),
                        notifi_entity.id,
                        visibility = visibility_param)
                
        except Exception as e:
            self.logger.critical("トゥート処理にて、エラーが発生しました。" + str(e))
            raise e
        
    def __lottery(self):
        '''おみくじ
            Returns:
                result:結果
        '''
        result = ''
        lines = ''

        lineCnt = len(open(self.config.lottery_path).readlines())

        linePos = random.randint(1, lineCnt);

        with open(self.config.lottery_path, "r") as f:
            lines = f.read().splitlines()
        
        result = lines[linePos]
        return result