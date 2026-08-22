@echo off
set JAVA_HOME=C:\Program Files\Android\Android Studio\jbr
set PATH=C:\Program Files\nodejs;%PATH%
set NODE_OPTIONS=--no-experimental-strip-types
cd /d C:\Users\zinem\Documents\zicore-system\mobile\android
call gradlew.bat assembleRelease
echo BUILD_RESULT=%ERRORLEVEL%
