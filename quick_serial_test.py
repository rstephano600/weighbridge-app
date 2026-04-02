# PowerShell Serial Port Test for Weighbridge
# Run this in PowerShell to test COM4 directly

$portName = "COM4"
$baudRate = 9600

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "PowerShell Serial Port Test" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

Write-Host "Attempting to open $portName at $baudRate baud..." -ForegroundColor Yellow

try {
    # Create serial port object
    $port = New-Object System.IO.Ports.SerialPort $portName, $baudRate, None, 8, One
    
    # Set timeouts
    $port.ReadTimeout = 1000
    $port.WriteTimeout = 1000
    
    # Open port
    $port.Open()
    
    Write-Host "✓ Port opened successfully!" -ForegroundColor Green
    Write-Host "`nListening for data (Press Ctrl+C to stop)..." -ForegroundColor Yellow
    Write-Host "Put weight on scale now!`n" -ForegroundColor Yellow
    Write-Host "------------------------------------------------------------" -ForegroundColor Gray
    
    $startTime = Get-Date
    $dataReceived = $false
    
    # Listen for 30 seconds
    while (((Get-Date) - $startTime).TotalSeconds -lt 30) {
        try {
            if ($port.BytesToRead -gt 0) {
                $data = $port.ReadLine()
                $timestamp = Get-Date -Format "HH:mm:ss"
                
                Write-Host "[$timestamp] DATA: $data" -ForegroundColor Green
                $dataReceived = $true
            }
            Start-Sleep -Milliseconds 100
        }
        catch {
            # Timeout is OK, just continue
        }
    }
    
    if (-not $dataReceived) {
        Write-Host "`n⚠ No data received in 30 seconds" -ForegroundColor Yellow
        Write-Host "`nPossible reasons:" -ForegroundColor Yellow
        Write-Host "  1. Weighbridge not sending data automatically" -ForegroundColor White
        Write-Host "  2. Wrong baud rate (try 19200, 4800)" -ForegroundColor White
        Write-Host "  3. Cable not connected properly" -ForegroundColor White
        Write-Host "  4. Need to enable 'Auto Print' on weighbridge" -ForegroundColor White
    }
    
    $port.Close()
    Write-Host "`n✓ Port closed" -ForegroundColor Green
    
} catch {
    Write-Host "`n✗ Error: $_" -ForegroundColor Red
    Write-Host "`nTroubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Close any program using COM4" -ForegroundColor White
    Write-Host "  2. Install/update CH340 drivers" -ForegroundColor White
    Write-Host "  3. Try unplugging and replugging USB adapter" -ForegroundColor White
    Write-Host "  4. Check Device Manager for errors" -ForegroundColor White
    Write-Host "  5. Restart computer" -ForegroundColor White
}

Write-Host "`n============================================================" -ForegroundColor Cyan