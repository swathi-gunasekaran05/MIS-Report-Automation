CREATE TABLE public.mis_batch_log (
    batchid BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    domainname VARCHAR(100) NOT NULL,
    frequency VARCHAR(20) NOT NULL,
    batchdate DATE NOT NULL,
    startdate DATE NOT NULL DEFAULT CURRENT_DATE,
    enddate DATE,
    totalreports INT NOT NULL DEFAULT 0,
    completedreports INT NOT NULL DEFAULT 0,
    failedreports INT NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'Started',

    CONSTRAINT uq_mis_batch
        UNIQUE (domainname, frequency, batchdate),

    CONSTRAINT chk_mis_batch_status
        CHECK (status IN (
            'Started', 'In Progress', 'Success', 'Failed'
        ))
);

select * from mis_batch_log;

truncate table mis_batch_log