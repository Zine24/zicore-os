$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:PATH = "C:\Program Files\nodejs;$env:PATH"
$env:NODE_OPTIONS = "--no-experimental-strip-types"
Set-Location "C:\Users\zinem\Documents\zicore-system\mobile\android"

$logFile = "C:\Users\zinem\Documents\zicore-system\mobile\build_log6.txt"
"Build started at $(Get-Date)" | Out-File $logFile
& cmd /c "gradlew.bat assembleRelease 2>&1" | Out-File $logFile -Append
"Build finished at $(Get-Date)" | Out-File $logFile -Append
