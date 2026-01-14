@echo off

rem RunMe_$app_name $username $password $site $inputFile $mode $filename $jobid $project

TITLE UserManagement
setlocal enableDelayedExpansion

pushd "..\scripts\"
call envTC14.bat
pushd "..\RoboTc\"

echo procedure launched on %date% %time% CET > ../log/RoboTC/semaphore_UserManager.out
echo procedure launched on %date% %time% CET > ../log/RoboTC/semaphore_%6.out

set ArrOfSites[0]=ITCEPE1P
set ArrOfSites[1]=ITCEIT1P
set ArrOfSites[2]=ITCESTLP
set ArrOfSites[3]=NEW_DELHI
set ArrOfSites[4]=HAZELWOOD
set ArrOfSites[5]=CURITIBA

set ArrOfSitesCV[0]=ITCEIT1P
set ArrOfSitesCV[1]=TORC14

set ArrOfSitesAGCE[0]=NEW_DELHI
set ArrOfSitesAGCE[1]=HAZELWOOD
set ArrOfSitesAGCE[2]=CURITIBA
set ArrOfSitesAGCE[3]=ITCEPE1P

set FILE=%4
set SITE=%3
set SCOPE=%5
set "x=0"

mkdir \\ivittrn53fsie27\\scambio$\\robotc

if "%SITE%" == "ALL_CNHi" GOTO Loop
if "%SITE%" == "ALL_CV" GOTO LoopCV
if "%SITE%" == "ALL_AGCE" GOTO LoopAGCE



GOTO :SSSSS

:Loop
if defined ArrOfSites[%x%] (
	%JAVA_PATH_BIN%java.exe it.maneat.soa.UserManagement.MakeUser -classpath %CLASSPATH% -prop_file=%config% -u="%1" -p="%2" -input_file=../log/RoboTC/uploads/%FILE% -site=!ArrOfSites[%x%]! -scope=%SCOPE% -output=../log/RoboTC/output/%6 -taskid=%8>> ../log/RoboTC/output/%6_out.log
    set /a "x+=1"
		
    GOTO Loop
) else GOTO END

:LoopCV
if defined ArrOfSitesCV[%x%] (
	%JAVA_PATH_BIN%java.exe it.maneat.soa.UserManagement.MakeUser -classpath %CLASSPATH% -prop_file=%config% -u="%1" -p="%2" -input_file=../log/RoboTC/uploads/%FILE% -site=!ArrOfSitesCV[%x%]! -scope=%SCOPE% -output=../log/RoboTC/output/%6 -taskid=%8 >> ../log/RoboTC/output/%6_out.log
    set /a "x+=1"
	    
	GOTO LoopCV
) else GOTO END

:LoopAGCE
if defined ArrOfSitesAGCE[%x%] (
	%JAVA_PATH_BIN%java.exe it.maneat.soa.UserManagement.MakeUser -classpath %CLASSPATH% -prop_file=%config% -u="%1" -p="%2" -input_file=../log/RoboTC/uploads/%FILE% -site=!ArrOfSitesAGCE[%x%]! -scope=%SCOPE% -output=../log/RoboTC/output/%6 -taskid=%8 >> ../log/RoboTC/output/%6_out.log
    set /a "x+=1"
	
    GOTO LoopAGCE
) else GOTO END

:SSSSS
%JAVA_PATH_BIN%java.exe it.maneat.soa.UserManagement.MakeUser -classpath %CLASSPATH% -prop_file=%config% -u="%1" -p="%2" -input_file=../log/RoboTC/uploads/%FILE% -site=%SITE% -scope=%SCOPE% -output=../log/RoboTC/output/%6 -taskid=%8 >> ../log/RoboTC/output/%6_out.log


:END
pushd "mail"
%XAMPP%\php -f _index.php taskID="%7" > ../log/RoboTC/message_taskID_%7.out
pushd "..\"
del ..\log\RoboTC\semaphore_UserManager.out
del ..\log\RoboTC\semaphore_%6.out
exit
