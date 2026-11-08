# Opens HCC_CCP_Report.docx in Microsoft Word, updates the Table of Contents, List of Figures and
# List of Tables (page numbers), saves the .docx and exports a PDF next to it.
# Usage (PowerShell):  powershell -ExecutionPolicy Bypass -File report\finalize_word.ps1
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$docx = Join-Path $here "HCC_CCP_Report.docx"
$pdf = Join-Path $here "HCC_CCP_Report.pdf"
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($docx)
    for ($pass = 0; $pass -lt 2; $pass++) {
        $doc.Repaginate()
        [void]$doc.Fields.Update()
        foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
        foreach ($tof in $doc.TablesOfFigures) { $tof.Update() }
    }
    $doc.Save()
    $doc.ExportAsFixedFormat($pdf, 17)   # 17 = wdExportFormatPDF
    $doc.Close(0)
    Write-Output "Updated and exported: $pdf"
}
finally {
    $word.Quit()
}
