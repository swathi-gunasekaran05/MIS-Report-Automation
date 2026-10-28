CREATE TABLE public.mis_control_master (
    masterid BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    domainname VARCHAR(100) NOT NULL,
    reportname VARCHAR(200) NOT NULL,
    worksheetname VARCHAR(100) NOT NULL,
    SPName VARCHAR(200),
    querytoexecute TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Active',
    frequency VARCHAR(20) NOT NULL
);

INSERT INTO public.mis_control_master
    (domainname, reportname, worksheetname,
     SPName, querytoexecute, status, frequency)
VALUES
    ('Student', 'All Students Report', 'AllStudents',
     'sp_get_all_students',
     'SELECT * FROM public.stg_student_data',
     'Active', 'Daily'),

    ('Student', 'Student Count Report', 'StudentCount',
     'sp_get_student_count',
     'SELECT * FROM public.student_count_summary',
     'Active', 'Daily'),

    ('Student', 'Age Analysis Report', 'AgeAnalysis',
     'sp_get_age_analysis',
     'SELECT * FROM public.age_analysis_summary',
     'Active', 'Daily'),

    ('Student', 'Health Summary Report', 'HealthSummary',
     'sp_get_health_summary',
     'SELECT * FROM public.health_summary',
     'Active', 'Daily'),

    ('Student', 'Social Media Summary Report', 'SocialMedia',
     'sp_get_social_media',
     'SELECT * FROM public.social_media_summary',
     'Active', 'Weekly');



SELECT *
FROM public.mis_control_master
ORDER BY masterid;

TRUNCATE TABLE public.mis_control_master
RESTART IDENTITY;



SELECT
    masterid,
    domainname,
    reportname,
    worksheetname,
    spname,
    querytoexecute,
    status,
    frequency
FROM public.mis_control_master
ORDER BY masterid;

