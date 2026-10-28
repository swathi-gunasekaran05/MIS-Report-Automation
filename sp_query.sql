-- FIRST SP
CREATE OR REPLACE PROCEDURE public.sp_get_all_students()
LANGUAGE plpgsql
AS $$
BEGIN
    TRUNCATE TABLE public.stg_student_data;

    INSERT INTO public.stg_student_data
    SELECT *
    FROM public.student_data;
END;
$$;

CALL public.sp_get_all_students();




-- SECOND SP
CREATE TABLE IF NOT EXISTS public.student_count_summary (
    total_students BIGINT,
    refreshed_at TIMESTAMP
);

CREATE OR REPLACE PROCEDURE public.sp_get_student_count()
LANGUAGE plpgsql
AS $$
BEGIN
    TRUNCATE TABLE public.student_count_summary;

    INSERT INTO public.student_count_summary
    SELECT COUNT(*), CURRENT_TIMESTAMP
    FROM public.stg_student_data;
END;
$$;

CALL public.sp_get_student_count();





-- THIRD SP
CREATE TABLE IF NOT EXISTS public.age_analysis_summary (
    age INTEGER,
    student_count BIGINT
);

CREATE OR REPLACE PROCEDURE public.sp_get_age_analysis()
LANGUAGE plpgsql
AS $$
BEGIN
    TRUNCATE TABLE public.age_analysis_summary;

    INSERT INTO public.age_analysis_summary
    SELECT age, COUNT(*)
    FROM public.stg_student_data
    WHERE age IS NOT NULL
    GROUP BY age
    ORDER BY age;
END;
$$;

CALL public.sp_get_age_analysis();





-- FOURTH SP
CREATE TABLE IF NOT EXISTS public.health_summary (
    avg_mental_health NUMERIC,
    avg_physical_health NUMERIC
);

CREATE OR REPLACE PROCEDURE public.sp_get_health_summary()
LANGUAGE plpgsql
AS $$
BEGIN
    TRUNCATE TABLE public.health_summary;

    INSERT INTO public.health_summary
    SELECT
        AVG(mental_health_score),
        AVG(physical_health_score)
    FROM public.stg_student_data;
	
END;
$$;

CALL public.sp_get_health_summary();





-- FIFTH SP
CREATE TABLE IF NOT EXISTS public.social_media_summary (
    gender VARCHAR(50),
    avg_social_media_hours NUMERIC
);

CREATE OR REPLACE PROCEDURE public.sp_get_social_media()
LANGUAGE plpgsql
AS $$
BEGIN
    TRUNCATE TABLE public.social_media_summary;

    INSERT INTO public.social_media_summary
    SELECT
        gender,
        AVG(daily_social_media_hours)
    FROM public.stg_student_data
    GROUP BY gender;
END;
$$;

CALL public.sp_get_social_media();


SELECT
    routine_name
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_type = 'PROCEDURE'
ORDER BY routine_name;


SELECT * FROM public.student_count_summary;