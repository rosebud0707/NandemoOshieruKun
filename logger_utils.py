"""logger_utils.py
    ログファイルの命名、出力
    各種ログレベル別出力メソッドの定義
"""
import datetime
import logging
import os


class Logger:
    """ログ出力
        ログファイルの生成を行う
    """
    def __init__(self, config):
        """コンストラクタ
        """
        self.save_dir = config.file_save_dir
        self.log_file_nm_base = config.file_nm_base
        self.current_date = self.__set_current_date()
        self.file_path = os.path.dirname(os.path.abspath(__file__)) + self.save_dir + '/' +  self.log_file_nm_base + '_{p}' + '.log'
        self.__set_log_config()

    def debug(self, err_msg):
        """debugログ
            Args:
                err_msg:任意の表示メッセージ
        """
        self.__write_log('debug', err_msg)

    def info(self, err_msg):
        """infoログ
            Args:
                err_msg:任意の表示メッセージ
        """
        self.__write_log('info', err_msg)

    def warning(self, err_msg):
        """warningログ
            Args:
                err_msg:任意の表示メッセージ
        """
        self.__write_log('warning', err_msg)

    def error(self, err_msg):
        """errorログ
            Args:
                err_msg:任意の表示メッセージ
        """
        self.__write_log('error', err_msg)

    def critical(self, err_msg):
        """criticalログ
            Args:
                err_msg:任意の表示メッセージ
        """
        self.__write_log('critical', err_msg)
    
    def __set_log_config(self):
        """ログファイル設定
            ログファイルの設定を行う
        """
        logging.basicConfig(filename = self.file_path.format(p=self.current_date),       # ログファイル名 
                            filemode = 'a',                                              # ファイル書込モード
                            level    = logging.DEBUG,                                    # ログレベル
                            format   = " %(asctime)s - %(levelname)s - %(message)s "     # ログ出力フォーマット
                            )

    def __set_current_date(self):
        """日付設定
            現在日付を返す
        """
        # 日付設定
        t_delta = datetime.timedelta(hours=9)
        JST = datetime.timezone(t_delta, 'JST')
        now = datetime.datetime.now(JST)
        return now.strftime('%Y%m%d')

    def __write_log(self, log_level, err_msg):
        """ログ出力
            ログファイルの出力を行う
            Args:
                log_level:ログレベル
                err_msg:エラーメッセージ
        """
        try:
            if(os.path.isfile(self.file_path.format(p=self.__set_current_date())) == False):
                # 日付が異なる場合、新規にログファイルを出力する
                # fileモードと現在日付を再設定
                self.current_date = self.__set_current_date()
                self.__set_log_config()

            if log_level == "debug":
                logging.debug(err_msg)

            elif log_level == "info":
                logging.info(err_msg)

            elif log_level == "warning":
                logging.warning(err_msg)

            elif log_level == "error":
                logging.error(err_msg)

            elif log_level == "critical":
                logging.critical(err_msg)
        
        except Exception as e:
            print("ログファイル設定エラー" + str(e))
            exit()