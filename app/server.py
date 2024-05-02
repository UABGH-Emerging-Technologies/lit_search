import os
import tempfile

import pandas as pd
import pypandoc
import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

# proof of concept for reading uploaded word docs and excel files just like in scoping review
# on server side, word docs is made a tempfile which is then converted to md by pypandoc
# on server side, excel is made a pandas dataframe.

app = FastAPI()


@app.post("/upload/")
async def create_upload_file(file: UploadFile = File(...)):
    """
    Upload a file and process it based on its MIME type. This endpoint supports both Word documents
    and Excel files. See below for how to send files via HTTP request:

    curl -X POST -F "file=@path_to_your_file.docx;type=application/vnd.openxmlformats-officedocument.wordprocessingml.document" http://localhost:8000/upload/

    The parts of the file tuple in requests are:
    - file name: Indicates the name of the file being uploaded.
    - file content: The binary content of the file.
    - MIME type: Specifies the type of file, which helps the server in processing it correctly.
    """

    try:
        # Process Word document
        if (
            file.content_type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ):
            return await process_word_document(file)

        # Process Excel file
        elif (
            file.content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ):
            return process_excel_file(file)

        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")

    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


async def process_word_document(file: UploadFile):
    """
    The function `process_word_document` reads a Word document file, converts it to markdown format
    using pypandoc, and returns the markdown content.

    Args:
      file (UploadFile): The `file` parameter in the `process_word_document` function is of type
    `UploadFile`. This parameter represents the uploaded Word document file that needs to be processed.

    Returns:
      A JSON response containing the converted markdown text from the Word document.
    """
    with tempfile.NamedTemporaryFile(delete=True, suffix=".docx") as tmpfile:
        content = await file.read()  # Read file content as bytes
        tmpfile.write(content)
        tmpfile.flush()  # Ensure all data is written to disk
        tmpfile_path = tmpfile.name  # Save the path where the file is stored

        # Convert the document to markdown using pypandoc
        markdown_text = pypandoc.convert_file(
            tmpfile_path, "markdown", extra_args=["--extract-media=.", "--wrap=none"]
        )

    return JSONResponse(content={"markdown": markdown_text})


def process_excel_file(file: UploadFile):
    """
    The function `process_excel_file` reads an uploaded Excel file, extracts the first row as a JSON
    object, and returns it as a JSON response.

    Args:
      file (UploadFile): The `file` parameter in the `process_excel_file` function is of type
    `UploadFile`. This type represents a file uploaded through a form in a web application. The function
    reads the content of this uploaded file, saves it temporarily on disk, processes it as an Excel file
    using Pandas,

    Returns:
      The function `process_excel_file` reads an Excel file uploaded as `file`, extracts the first row
    of the file as a JSON object, and returns it as a JSON response.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        # Save file to disk temporarily
        content = file.file.read()  # Read file content as bytes
        tmp.write(content)
        tmp.seek(0)

        # Load the Excel file using Pandas
        df = pd.read_excel(tmp.name)

        # Assuming we return the first row as a JSON object
        first_row = df.iloc[0].to_json()

        # Clean up the temporary file
        os.unlink(tmp.name)

        return JSONResponse(content={"first_row": first_row})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
