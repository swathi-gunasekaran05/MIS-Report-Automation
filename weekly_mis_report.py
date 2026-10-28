import os
import psycopg
import pandas as pd
from dotenv import load_dotenv

from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.worksheet.table import Table, TableStyleInfo

# Load environment variables
load_dotenv()

# Database connection
conn = psycopg.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)

print("PostgreSQL connection successful!")

# Fetch active Weekly report configurations
query = """
    SELECT *
    FROM public.MIScontrolmaster
    WHERE status = 'Active'
      AND frequency = 'Weekly';
"""

df_reports = pd.read_sql_query(query, conn)

print("Active Weekly Reports:")
print(df_reports)
print("Total reports:", len(df_reports))

# Loop through each Weekly report
for index, proc in df_reports.iterrows():

    # Get report details
    reportname = proc["reportname"]
    worksheetname = proc["worksheetname"]
    storedprocedurename = proc["spname"]
    querytoexecute = proc["querytoexecute"]

    print("\nProcessing Report:", reportname)
    print("Stored Procedure:", storedprocedurename)
    print("Worksheet:", worksheetname)

    # Execute the stored procedure
    with conn.cursor() as cur:
        cur.execute(
            f"CALL public.{storedprocedurename}()"
        )

    conn.commit()

    print("Stored procedure executed successfully!")

    # Execute the report query
    dfname = pd.read_sql_query(querytoexecute, conn)

    print("Report data fetched successfully!")
    print(dfname.head())


    # Create and format Excel report
    with pd.ExcelWriter(reportname, engine="openpyxl") as writer:

        dfname.to_excel(
            writer,
            sheet_name=worksheetname,
            index=False
        )

        workbook = writer.book
        worksheet = workbook[worksheetname]

        # Header formatting
        header_fill = PatternFill(
            fill_type="solid",
            fgColor="1F497D"
        )

        header_font = Font(
            color="FFFFFF",
            bold=True
        )

        header_alignment = Alignment(
            horizontal="center",
            vertical="center"
        )

        data_alignment = Alignment(
            vertical="center"
        )

        # Format header
        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment

        # Format data
        for row in worksheet.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = data_alignment

        # Adjust column width
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter

            for cell in column:
                if cell.value is not None:
                    max_length = max(
                        max_length,
                        len(str(cell.value))
                    )

            worksheet.column_dimensions[
                column_letter
            ].width = min(max_length + 3, 50)

        # Freeze header
        worksheet.freeze_panes = "A2"

        # Header height
        worksheet.row_dimensions[1].height = 25

        # Create Excel table
        if worksheet.max_row > 1 and worksheet.max_column > 0:

            table_range = (
                f"A1:{worksheet.cell(worksheet.max_row, worksheet.max_column).coordinate}"
            )

            table_name = f"Table_{worksheetname}"

            table = Table(
                displayName=table_name,
                ref=table_range
            )

            table_style = TableStyleInfo(
                name="TableStyleMedium2",
                showFirstColumn=False,
                showLastColumn=False,
                showRowStripes=True,
                showColumnStripes=False
            )

            table.tableStyleInfo = table_style
            worksheet.add_table(table)

    print("Excel report created:", reportname)

# Close connection AFTER all reports are processed
conn.close()

print("Daily MIS Report Automation completed!")
