import os
import uuid
import logging
from datetime import datetime, date
from pathlib import Path

import psycopg
import pandas as pd
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment
from dotenv import load_dotenv


# ============================================================
# 1. CONFIGURATION
# ============================================================

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

REPORT_FOLDER = Path("MIS_Reports")
REPORT_FOLDER.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. DATABASE CONNECTION
# ============================================================

def get_connection():
    """Connect to PostgreSQL using values from the .env file."""
    connection = psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    logging.info("PostgreSQL connection established.")
    return connection


# ============================================================
# 3. FETCH ACTIVE DAILY REPORTS
# ============================================================

def get_daily_reports(connection):
    """Return only Active reports whose frequency is Daily."""
    query = """
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
        WHERE status = 'Active'
          AND frequency = 'Daily'
        ORDER BY masterid;
    """

    df = pd.read_sql_query(query, connection)
    logging.info("Daily reports found: %s", len(df))
    return df


# ============================================================
# 4. CREATE OR REUSE THE DAILY BATCH
# ============================================================

def create_batch_log(connection, df):
    """
    The current database constraint allows one batch per
    domain + frequency + batchdate. Reuse that batch on a
    same-day rerun; do not reset its report results.
    """
    domainname = str(df.iloc[0]["domainname"])
    today = date.today()

    insert_query = """
        INSERT INTO public.mis_batch_log
        (
            domainname,
            frequency,
            batchdate,
            startdate,
            enddate,
            totalreports,
            completedreports,
            failedreports,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (domainname, frequency, batchdate)
        DO NOTHING
        RETURNING batchid;
    """

    with connection.cursor() as cursor:
        cursor.execute(
            insert_query,
            (
                domainname,
                "Daily",
                today,
                today,
                None,
                len(df),
                0,
                0,
                "In Progress"
            )
        )
        row = cursor.fetchone()

        if row is not None:
            batchid = row[0]
            logging.info("New batch created: %s", batchid)
        else:
            cursor.execute(
                """
                SELECT batchid
                FROM public.mis_batch_log
                WHERE domainname = %s
                  AND frequency = %s
                  AND batchdate = %s
                FOR UPDATE;
                """,
                (domainname, "Daily", today)
            )
            existing = cursor.fetchone()
            if existing is None:
                raise RuntimeError("Could not find or create the daily batch.")

            batchid = existing[0]
            cursor.execute(
                """
                UPDATE public.mis_batch_log
                SET totalreports = %s,
                    enddate = NULL,
                    status = 'In Progress'
                WHERE batchid = %s;
                """,
                (len(df), batchid)
            )
            logging.info("Reusing today's batch: %s", batchid)

    connection.commit()
    return batchid


# ============================================================
# 5. CREATE / FIND A REPORT RECORD
# ============================================================

def create_batch_report(connection, batchid, report):
    """
    New report -> create In Progress row with attempt 1.
    Existing Success report -> return should_run=False.
    Existing non-Success report -> retry and increment attempts.
    """
    reportname = str(report["reportname"])
    masterid = int(report["masterid"])

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO public.mis_batch_report
            (
                batchid,
                masterid,
                reportname,
                status,
                attemptcount
            )
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (batchid, reportname)
            DO NOTHING
            RETURNING batchreportid, status;
            """,
            (batchid, masterid, reportname, "In Progress", 1)
        )

        row = cursor.fetchone()

        if row is not None:
            batchreportid, status = row
            should_run = True
        else:
            cursor.execute(
                """
                SELECT batchreportid, status
                FROM public.mis_batch_report
                WHERE batchid = %s
                  AND reportname = %s
                FOR UPDATE;
                """,
                (batchid, reportname)
            )
            existing = cursor.fetchone()
            if existing is None:
                raise RuntimeError(
                    f"Could not find report log for {reportname}."
                )

            batchreportid, existing_status = existing

            if existing_status == "Success":
                status = existing_status
                should_run = False
            else:
                cursor.execute(
                    """
                    UPDATE public.mis_batch_report
                    SET masterid = %s,
                        status = 'In Progress',
                        attemptcount = attemptcount + 1
                    WHERE batchreportid = %s;
                    """,
                    (masterid, batchreportid)
                )
                status = "In Progress"
                should_run = True

    connection.commit()
    return batchreportid, should_run


# ============================================================
# 6. UPDATE REPORT STATUS
# ============================================================

def update_report_status(connection, batchreportid, status):
    """Update one report's status."""
    query = """
        UPDATE public.mis_batch_report
        SET status = %s
        WHERE batchreportid = %s;
    """

    with connection.cursor() as cursor:
        cursor.execute(query, (status, batchreportid))

    connection.commit()


# ============================================================
# 7. SAVE EXECUTION LOG
# ============================================================

def save_execution_log(
    connection,
    batchid,
    batchreportid,
    report,
    status,
    starttime,
    endtime,
    rowsprocessed,
    errormessage
):
    """Save one row for this report execution attempt."""
    durationseconds = (endtime - starttime).total_seconds()

    query = """
        INSERT INTO public.mis_execution_log
        (
            batchid,
            runid,
            batchreportid,
            executionid,
            masterid,
            reportname,
            status,
            starttime,
            endtime,
            durationseconds,
            rowsprocessed,
            errormessage,
            createdtimestamp
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s);
    """

    # IMPORTANT: This assumes runid is intended to equal batchid.
    # If runid has a foreign key to a separate run table, use the
    # actual run ID from that table instead.
    with connection.cursor() as cursor:
        cursor.execute(
            query,
            (
                batchid,
                batchid,
                batchreportid,
                uuid.uuid4(),
                int(report["masterid"]),
                str(report["reportname"]),
                status,
                starttime,
                endtime,
                durationseconds,
                rowsprocessed,
                errormessage,
                datetime.now().astimezone()
            )
        )

    connection.commit()


# ============================================================
# 8. SAVE AND FORMAT EXCEL WORKSHEET
# ============================================================

def save_excel_report(result_df, domainname, worksheetname):
    """Replace only the current worksheet and preserve other sheets."""
    file_path = REPORT_FOLDER / f"{domainname}.xlsx"

    if file_path.exists():
        with pd.ExcelWriter(
            file_path,
            engine="openpyxl",
            mode="a",
            if_sheet_exists="replace"
        ) as writer:
            result_df.to_excel(
                writer,
                sheet_name=worksheetname,
                index=False
            )
    else:
        with pd.ExcelWriter(
            file_path,
            engine="openpyxl",
            mode="w"
        ) as writer:
            result_df.to_excel(
                writer,
                sheet_name=worksheetname,
                index=False
            )

    workbook = openpyxl.load_workbook(file_path)
    try:
        worksheet = workbook[worksheetname]

        header_fill = PatternFill(
            fill_type="solid",
            fgColor="1F497D"
        )
        header_font = Font(bold=True, color="FFFFFF")
        header_alignment = Alignment(
            horizontal="center",
            vertical="center"
        )

        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment

        worksheet.freeze_panes = "A2"
        worksheet.row_dimensions[1].height = 25

        if worksheet.max_row >= 1 and worksheet.max_column >= 1:
            worksheet.auto_filter.ref = worksheet.dimensions

        for column_cells in worksheet.columns:
            max_length = 0
            column_letter = column_cells[0].column_letter

            for cell in column_cells:
                if cell.value is not None:
                    max_length = max(max_length, len(str(cell.value)))

            worksheet.column_dimensions[column_letter].width = min(
                max_length + 2, 40
            )

        workbook.save(file_path)
    finally:
        workbook.close()

    logging.info(
        "Excel saved: %s | Sheet: %s",
        file_path,
        worksheetname
    )


# ============================================================
# 9. PROCESS REPORTS WITH EXCEPTION HANDLING
# ============================================================

def process_daily_reports(df, connection, batchid):
    """
    Skip reports already marked Success.
    Retry reports that are Failed or unfinished.
    A failed report does not stop the remaining reports.
    """
    for _, report in df.iterrows():
        reportname = str(report["reportname"])
        starttime = datetime.now().astimezone()
        endtime = starttime
        rowsprocessed = 0
        errormessage = None
        status = "Failed"
        batchreportid = None
        should_run = True

        logging.info("Checking report: %s", reportname)

        # Create/find tracking row. If this fails, record the error
        # in terminal and continue to the next configured report.
        try:
            batchreportid, should_run = create_batch_report(
                connection,
                batchid,
                report
            )
        except Exception as error:
            connection.rollback()
            logging.exception(
                "Could not prepare report log for %s",
                reportname
            )
            continue

        if not should_run:
            logging.info(
                "Skipping already successful report: %s",
                reportname
            )
            continue

        try:
            spname = report["spname"]

            # Stored procedure errors are caught here so the report
            # can be marked Failed and the loop can continue.
            if pd.notna(spname) and str(spname).strip():
                # Procedure names come from trusted control-table config.
                # Keep them as schema-qualified identifiers in that table.
                procedure_name = str(spname).strip()
                if not procedure_name.replace("_", "").isalnum():
                    raise ValueError(
                        f"Invalid stored procedure name: {procedure_name}"
                    )

                with connection.cursor() as cursor:
                    cursor.execute(
                        f"CALL public.{procedure_name}()"
                    )
                connection.commit()

            querytoexecute = report["querytoexecute"]
            if pd.isna(querytoexecute) or not str(querytoexecute).strip():
                raise ValueError(
                    f"No query configured for report {reportname}"
                )

            result_df = pd.read_sql_query(
                str(querytoexecute),
                connection
            )
            rowsprocessed = len(result_df)

            save_excel_report(
                result_df,
                str(report["domainname"]),
                str(report["worksheetname"])
            )

            status = "Success"

        except Exception as error:
            try:
                connection.rollback()
            except Exception:
                logging.exception("Rollback failed for %s", reportname)

            status = "Failed"
            errormessage = str(error)

            logging.exception("Report failed: %s", reportname)

        finally:
            endtime = datetime.now().astimezone()

            # Save final report status and execution history.
            # If log persistence fails, report it clearly in terminal.
            try:
                update_report_status(
                    connection,
                    batchreportid,
                    status
                )

                save_execution_log(
                    connection,
                    batchid,
                    batchreportid,
                    report,
                    status,
                    starttime,
                    endtime,
                    rowsprocessed,
                    errormessage
                )
            except Exception:
                connection.rollback()
                logging.exception(
                    "Could not persist final status/log for %s",
                    reportname
                )

        logging.info(
            "Report: %s | Status: %s | Rows: %s",
            reportname,
            status,
            rowsprocessed
        )


# ============================================================
# 10. CALCULATE BATCH STATUS FROM DATABASE REPORT STATUSES
# ============================================================

def update_batch_log(connection, batchid):
    """
    Batch is Success only if every expected report has a Success
    status. Failed, In Progress, or missing report rows prevent Success.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT totalreports
            FROM public.mis_batch_log
            WHERE batchid = %s;
            """,
            (batchid,)
        )
        batch_row = cursor.fetchone()

        if batch_row is None:
            raise ValueError(f"Batch {batchid} was not found.")

        totalreports = batch_row[0]

        cursor.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE status = 'Success'),
                COUNT(*) FILTER (WHERE status = 'Failed'),
                COUNT(*) FILTER (WHERE status = 'In Progress'),
                COUNT(*)
            FROM public.mis_batch_report
            WHERE batchid = %s;
            """,
            (batchid,)
        )

        completedreports, failed_count, in_progress_count, logged_count = (
            cursor.fetchone()
        )

    # Treat reports not yet logged as incomplete/failing for this run.
    missing_count = max(totalreports - logged_count, 0)
    failedreports = failed_count + in_progress_count + missing_count

    if totalreports > 0 and completedreports == totalreports:
        batch_status = "Success"
        failedreports = 0
    elif failedreports > 0 or completedreports < totalreports:
        batch_status = "Failed"
    else:
        batch_status = "Failed"

    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE public.mis_batch_log
            SET completedreports = %s,
                failedreports = %s,
                enddate = %s,
                status = %s
            WHERE batchid = %s;
            """,
            (
                completedreports,
                failedreports,
                date.today(),
                batch_status,
                batchid
            )
        )

    connection.commit()

    logging.info(
        "Batch %s | Total: %s | Success: %s | Failed/incomplete: %s | Status: %s",
        batchid,
        totalreports,
        completedreports,
        failedreports,
        batch_status
    )


# ============================================================
# 11. MAIN FUNCTION
# ============================================================

def main():
    connection = None
    batchid = None

    try:
        connection = get_connection()

        df = get_daily_reports(connection)

        if df.empty:
            logging.info("No active Daily reports found.")
            return

        # This design reuses the same day's batch because the current
        # uq_mis_batch constraint is domainname + frequency + batchdate.
        batchid = create_batch_log(connection, df)

        process_daily_reports(
            df,
            connection,
            batchid
        )

        # Always derive final batch status from database report statuses,
        # not from in-memory counters.
        update_batch_log(connection, batchid)

    except Exception:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                logging.exception("Final rollback failed.")

        logging.exception("Daily MIS automation failed.")

        # If a batch exists, attempt to mark it Failed rather than
        # leaving a false Success status after an unexpected error.
        if connection is not None and batchid is not None:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE public.mis_batch_log
                        SET status = 'Failed',
                            enddate = %s
                        WHERE batchid = %s;
                        """,
                        (date.today(), batchid)
                    )
                connection.commit()
            except Exception:
                connection.rollback()
                logging.exception(
                    "Could not mark batch %s as Failed.",
                    batchid
                )

    finally:
        if connection is not None:
            connection.close()
            logging.info("PostgreSQL connection closed.")


# ============================================================
# 12. ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
