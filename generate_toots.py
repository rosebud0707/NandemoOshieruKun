"""generate_toots.py
    OpenAI APIを用いて、質問に対する返答を生成する。
"""
import asyncio

import openai
import tiktoken

from logger_utils import Logger
from config_file_setting import SetConfigFileData
from database_manager import DatabaseManager


class GenerateToots:
    """GenerateToots
        APIに質問文を投げかけて、トゥートの生成を行う。
    """
    def __init__(self):
        # 各インスタンス化
        self.config_instance = SetConfigFileData()
        self.config = self.config_instance.set_config_datas()
        self.logger_instance = Logger(self.config)
        openai.api_key = str(self.config.api_key)

    async def process_wait(self, content, id):
        """タイムアウトエラー処理
            規定時間以内に応答しない場合、タイムアウトエラーとする。
            Args:
                content:リプライ
                id:アカウントID
        """        
        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(loop.run_in_executor(None, self.__gen_msg, content, id), timeout=int(self.config.timeout_interval))
            return result

        except asyncio.TimeoutError:
            # Timeoutが発生したとき
            self.logger_instance.critical("タイムアウトエラー")
            return "タイムアウトエラー。しばらく経ってから再度投稿してください。"
        
    def __gen_msg(self, content, id):
        """レスポンス生成
            OpenAI APIを用いて、返答生成
            Args:
                content:リプライ
                id:アカウントID
            Returns:
                response:返答
        """
        try:
            # OpenAIインスタンス化
            self.logger_instance.info("OpenAIインスタンス化")
            openAiInstance = openai.ChatCompletion.create(
                model=self.config.chatgpt_model,
                temperature=float(self.config.temperature),
                messages=[{"role": "system", "content": self.config.role_system_content},
                          {"role": "user","content": content}]
            )

            # 質問文のトークン数を取得
            enc = tiktoken.get_encoding('cl100k_base')
            input_tokens = len(enc.encode(content))

            # レスポンス受取、トークン数取得
            response = openAiInstance.choices[0].message.content
            output_tokens = len(enc.encode(response))
            self.logger_instance.info("生成文：" + response)

            # 回答文、コスト更新
            self.__update_answer(id, response, float(input_tokens), float(output_tokens))

            return str(response)

        except Exception as e:
            self.logger_instance.critical("文書生成に関してエラーが発生しました。" + str(e))
            return "chatGPTでエラーが発生しました。"
    
    def __update_answer(self, id, content, input_tokens, output_tokens):
        """回答内容更登録
            Args:
                id:アカウントID
                content:リプライ
                input_tokens:入力トークン
                output_tokens:出力トークン
        """
        try:
            self.logger_instance.info("回答文登録")
            # DatabaseManagerインスタンス化
            dbmanager_instance = DatabaseManager(self.config, "SQL_005.sql")
            # SQL実行
            cnt = dbmanager_instance.exec_query(content, self.__get_cost(input_tokens, output_tokens), id, id)
            self.logger_instance.info("{cn}件更新".format(cn=str(cnt)))
        except Exception as e:
            self.logger_instance.critical("DB更新に関してエラーが発生しました。" + str(e))
            raise e
        
    def __get_cost(self, input_tokens, output_tokens):
        """コスト算出
            質問・回答のトークン数よりコストを算出する。
            Args:
                input_tokens:入力トークン
                output_tokens:出力トークン
            Return:
                コスト
        """
        try:
            self.logger_instance.info("token算出")
            # DatabaseManagerインスタンス化
            dbmanager_instance = DatabaseManager(self.config, "SQL_004.sql")
            # SQL実行
            dr = dbmanager_instance.exec_select(self.config.chatgpt_model)

            return input_tokens * (float(dr['INPUT_COST']) / 1000) + output_tokens * (float(dr['OUTPUT_COST']) / 1000)
        except Exception as e:
            self.logger_instance.critical("コスト計算に関してエラーが発生しました。" + str(e))
            raise e
