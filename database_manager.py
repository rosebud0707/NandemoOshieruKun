"""database_manager.py
    DB接続
    クエリ実行処理を記載
"""
import os

import MySQLdb
import pandas as pd


class DatabaseManager:
    """データベースマネージャ
        DB接続、クエリ実行を行うクラス
    """
    def __init__(self, conf, sqlfile):
        """コンストラクタ
            Args:
                conf:外部設定ファイル
                sqlfile:実行SQLクエリファイル
        """
        self.connection = MySQLdb.connect(host="localhost",port=3306,
                                          user=conf.user,
                                          passwd=conf.password,
                                          db=conf.dbname,
                                          charset="utf8"
                                          )
        self.cursor = self.connection.cursor()
        with open(os.path.dirname(os.path.abspath(__file__)) + conf.sql_file_dir + '/' +  sqlfile, "r") as file:
            self.sql_query = file.read()

    def exec_select(self, *args):
        """SELECT実行メソッド
            Args:
                args:SQLパラメータ
            Return:
                実行結果
        """
        try:
            df = pd.read_sql_query(self.sql_query, self.connection, params=(args))
            return df
        finally:
            self.cursor.close()
            self.connection.close()

    def exec_query(self, *args):
        """INSERT/UPDATE/DELETE実行メソッド
            Args:
                args:SQLパラメータ
            Return:
                処理件数
        """
        try:
            affected_rows = self.cursor.execute(self.sql_query, args)
            self.connection.commit()
            return affected_rows
        finally:
            self.cursor.close()
            self.connection.close()