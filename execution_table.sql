CREATE TABLE public.mis_execution_log (
    logid BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    batchid BIGINT NOT NULL,
    runid BIGINT NOT NULL,
    batchreportid BIGINT NOT NULL,
    executionid UUID NOT NULL,
    masterid BIGINT NOT NULL,
    reportname VARCHAR(200) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Started',
    starttime TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    endtime TIMESTAMPTZ,
    durationseconds NUMERIC(12,2),
    rowsprocessed BIGINT,
    errormessage TEXT,
    createdtimestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_mis_execution_batch
        FOREIGN KEY (batchid)
        REFERENCES public.mis_batch_log(batchid),

    CONSTRAINT fk_mis_execution_batchreport
        FOREIGN KEY (batchreportid)
        REFERENCES public.mis_batch_report(batchreportid),

    CONSTRAINT fk_mis_execution_master
        FOREIGN KEY (masterid)
        REFERENCES public.mis_control_master(masterid),

    CONSTRAINT chk_mis_execution_status
        CHECK (status IN (
            'Started', 'In Progress', 'Success', 'Failed'
        ))
);

select * from mis_execution_log;

truncate table mis_execution_log