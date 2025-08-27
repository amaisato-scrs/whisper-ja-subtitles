-- /Users/sato/Scripts/Whisper/shortcuts/WhisperInbox.applescript
use AppleScript version "2.4"
use scripting additions

on run
	set mePath to POSIX path of (path to me)
	set homeDir to do shell script "cd " & quoted form of mePath & " && cd .. && pwd"
	-- 非管理者で実行する場合は「with administrator privileges」は付けない
	do shell script "/bin/bash -lc " & quoted form of ("cd " & homeDir & " && source ./env.sh && bash bin/inbox_run_once.sh")
end run
