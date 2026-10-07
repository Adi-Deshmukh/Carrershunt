from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.company_import import import_companies

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("/import")
async def import_company_excel(
    file: UploadFile = File(...),
) -> dict:
    filename = file.filename or ""
    if not filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Upload an Excel file (.xlsx or .xls).",
        )

    content = await file.read()

    try:
        result = import_companies(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Could not read the Excel file.",
        ) from exc

    return {
        "imported": len(result.imported),
        "duplicates": len(result.duplicates),
        "invalid": len(result.invalid),
        "companies": [company.model_dump(mode="json") for company in result.imported],
        "duplicate_names": result.duplicates,
        "invalid_rows": result.invalid,
    }
