"""
refresh_model_dropdown.py — 更新 Excel 中 MODEL_AUDITOR_1 / MODEL_AUDITOR_2 的下拉选项
"""
import openpyxl
from openpyxl.worksheet.datavalidation import DataValidation

wb = openpyxl.load_workbook("tao_config.xlsx")
ws = wb["系统配置"]

target_keys = {"MODEL_AUDITOR_1", "MODEL_AUDITOR_2"}
target_cells = []
for row in ws.iter_rows(min_row=1):
    key_cell = row[0]
    if key_cell.value and str(key_cell.value).strip() in target_keys:
        val_cell = row[1]
        target_cells.append(val_cell.coordinate)

dropdown_str = "qwen3.6-plus,gpt-5.4"

from openpyxl.worksheet.datavalidation import DataValidationList

kept = []
for dv in ws.data_validations.dataValidation:
    sqref_str = str(dv.sqref)
    if not any(c in sqref_str for c in target_cells):
        kept.append(dv)

ws.data_validations = DataValidationList()
for dv in kept:
    ws.data_validations.append(dv)

for coord in target_cells:
    dv = DataValidation(
        type="list",
        formula1=f'"{dropdown_str}"',
        allow_blank=True,
        showDropDown=False,
    )
    dv.sqref = coord
    ws.data_validations.append(dv)
    print(f"  updated dropdown: {coord}")

wb.save("tao_config.xlsx")
print("Done. tao_config.xlsx saved.")