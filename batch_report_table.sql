CREATE TABLE public.mis_batch_report (
    batchreportid BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    batchid BIGINT NOT NULL,
    masterid BIGINT NOT NULL,
    reportname VARCHAR(200) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Started',
    attemptcount INT NOT NULL DEFAULT 0,

    CONSTRAINT fk_mis_batch_report_batch
        FOREIGN KEY (batchid)
        REFERENCES public.mis_batch_log(batchid),

    CONSTRAINT fk_mis_batch_report_master
        FOREIGN KEY (masterid)
        REFERENCES public.mis_control_master(masterid),

    CONSTRAINT uq_mis_batch_report
        UNIQUE (batchid, reportname),

    CONSTRAINT chk_mis_batch_report_status
        CHECK (status IN (
            'Started', 'In Progress', 'Success', 'Failed'
        ))
);


select * from mis_batch_report

truncate table mis_batch_report;


SELECT
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN (
      'mis_control_master',
      'mis_batch_log',
      'mis_batch_report',
      'mis_execution_log',
      'mis_batch_run'
  )
ORDER BY table_name, ordinal_position;
