# Request a Document Export

Use this page to request PDF or Word exports of UIAO documents.

## Self-Service Export (GitHub Actions)

If you have permission to run GitHub Actions workflows:

1. Go to the [Document Export workflow](https://github.com/WhalerMike/uiao-docs/actions/workflows/document-export.yml)
2. Click **Run workflow**
3. Enter the document path relative to `docs/` (e.g., `documents/uiao-042.md`)
4. Select the output format: `docx`, `pdf`, or `both`
5. Click **Run workflow**
6. Download the result from the **Artifacts** section after the workflow completes

## Request via Issue

If you do not have Actions permissions, submit a request:

1. Open a [new export request issue](https://github.com/WhalerMike/uiao-docs/issues/new?template=export-request.yml)
2. Fill in the document path and desired format
3. A team member will fulfil the request and attach the exported file

!!! tip
    The **Download as PDF** button on each page uses your browser's print dialog. Select **Save as PDF** as the destination for an instant export.
