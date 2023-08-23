UPDATE AIB_T_REPLY_SENTENSE
SET
ts_answer = NOW()
, cm_answer = %s
, su_cost = %s
, ts_update = NOW()
WHERE
    id_user = %s
    AND ts_question = (SELECT ts_q FROM (SELECT MAX(ts_question) AS ts_q FROM AIB_T_REPLY_SENTENSE WHERE id_user = %s) AS tmp_table)