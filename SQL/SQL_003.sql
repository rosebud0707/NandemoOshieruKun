INSERT INTO
AIB_T_REPLY_SENTENSE
(
id_user
,ts_question
,cm_question
,flg_delete
,ts_update
,nm_update
,ts_regist
,nm_regist
)
values
(
%s
,%s
,%s
,'0'
,CURRENT_TIMESTAMP()
,'system'
,CURRENT_TIMESTAMP()
,'system'
);