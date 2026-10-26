param(
    [string]$MySqlBin = 'D:\MySQL\mysql-5.7.37-winx64\bin',
    [string]$RedisBin = 'D:\Redis'
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskRuntime = Join-Path $taskRoot '.runtime'
$taskData = Join-Path $taskRuntime 'mysql'
New-Item -ItemType Directory -Force -Path $taskRuntime | Out-Null
function Test-TaskPort([int]$Port) {
    $taskClient = [Net.Sockets.TcpClient]::new()
    try { $taskClient.Connect('127.0.0.1', $Port); return $true } catch { return $false } finally { $taskClient.Dispose() }
}
if (!(Test-TaskPort 3306)) {
    $taskServer = Join-Path $MySqlBin 'mysqld.exe'
    if (!(Test-Path -LiteralPath $taskServer)) { throw 'MySQL binary missing: pass -MySqlBin with the bin directory.' }
    $taskFresh = !(Test-Path -LiteralPath (Join-Path $taskData 'mysql'))
    if ($taskFresh) {
        New-Item -ItemType Directory -Force -Path $taskData | Out-Null
        $taskInit = Start-Process -FilePath $taskServer -ArgumentList @('--no-defaults', '--initialize-insecure', "--basedir=$((Split-Path $MySqlBin -Parent))", "--datadir=$taskData") -WindowStyle Hidden -Wait -PassThru -RedirectStandardError (Join-Path $taskRuntime 'mysql-init.log')
        if ($taskInit.ExitCode -ne 0) { throw 'MySQL initialization failed; see .runtime/mysql-init.log' }
    }
    Start-Process -FilePath $taskServer -ArgumentList @('--no-defaults', "--basedir=$((Split-Path $MySqlBin -Parent))", "--datadir=$taskData", '--port=3306', '--bind-address=127.0.0.1', '--character-set-server=utf8mb4', '--collation-server=utf8mb4_unicode_ci', "--log-error=$taskRuntime/mysql.log") -WindowStyle Hidden
    for ($taskAttempt=0; $taskAttempt -lt 30; $taskAttempt++) { if (Test-TaskPort 3306) { break }; Start-Sleep -Seconds 1 }
    if (!(Test-TaskPort 3306)) { throw 'MySQL did not start; see .runtime/mysql.log' }
    if ($taskFresh) { & python (Join-Path $PSScriptRoot 'configure-local-db.py'); if ($LASTEXITCODE -ne 0) { throw 'Local DB credentials setup failed' } }
}
if (!(Test-TaskPort 6379)) {
    $taskRedis = Join-Path $RedisBin 'redis-server.exe'
    if (!(Test-Path -LiteralPath $taskRedis)) { throw 'Redis binary missing: pass -RedisBin with its directory.' }
    Start-Process -FilePath $taskRedis -ArgumentList @('--port', '6379', '--bind', '127.0.0.1', '--dir', $taskRuntime, '--dbfilename', 'redis.rdb', '--logfile', (Join-Path $taskRuntime 'redis.log')) -WindowStyle Hidden
}
Write-Output 'Project-local MySQL and Redis are available on 127.0.0.1:3306 / 6379.'
