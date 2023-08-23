CREATE TABLE systemdb.AIB_T_REPLY_SENTENSE(
    id_user VARCHAR(500) NOT NULL,
    ts_question DATETIME NOT NULL,
    cm_question VARCHAR(500) NOT NULL,
    ts_answer DATETIME,
    cm_answer VARCHAR(1500),
    su_cost DOUBLE(9, 8),
    flg_delete char(1) NOT NULL,
    ts_update DATETIME NOT NULL,
    nm_update VARCHAR(20) NOT NULL,
    ts_regist DATETIME NOT NULL,
    nm_regist VARCHAR(20) NOT NULL,
    PRIMARY KEY(id_user, ts_question)
);

CREATE TABLE systemdb.AIB_M_TOKEN_COEF(
    nm_ai_model VARCHAR(50) NOT NULL,
    su_input_cost DOUBLE(6,4) NOT NULL,
    su_output_cost DOUBLE(6, 4) NOT NULL,
    flg_delete CHAR(1) NOT NULL,
    ts_update DATETIME NOT NULL,
    nm_update VARCHAR(20) NOT NULL,
    ts_regist DATETIME NOT NULL,
    nm_regist VARCHAR(20) NOT NULL,
    PRIMARY KEY(nm_ai_model)
);
