param(
    [Parameter(Mandatory = $true)][string]$WorkbookPath,
    [Parameter(Mandatory = $true)][string]$ReceiptPath
)

$ErrorActionPreference = 'Stop'
$resolvedWorkbook = (Resolve-Path -LiteralPath $WorkbookPath).Path
$receiptParent = Split-Path -Parent $ReceiptPath
if (-not (Test-Path -LiteralPath $receiptParent)) {
    throw "Receipt parent does not exist: $receiptParent"
}
$beforeHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $resolvedWorkbook).Hash.ToLowerInvariant()
$excel = $null
$workbook = $null
try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $workbook = $excel.Workbooks.Open($resolvedWorkbook, 0, $false)
    $excel.CalculateFullRebuild()
    $workbook.Save()
    $workbook.Close($false)
    $workbook = $null
    $afterHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $resolvedWorkbook).Hash.ToLowerInvariant()
    $receipt = [ordered]@{
        status = 'PASS'
        workbook = $resolvedWorkbook
        excel_version = $excel.Version
        calculation = 'CalculateFullRebuild'
        before_sha256 = $beforeHash
        after_sha256 = $afterHash
        validated_at = (Get-Date).ToString('o')
    }
    $receipt | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $ReceiptPath -Encoding UTF8
}
finally {
    if ($workbook) { $workbook.Close($false) }
    if ($excel) {
        $excel.Quit()
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($excel)
    }
}
