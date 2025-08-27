-- /Users/sato/Scripts/Whisper/shortcuts/WhisperHUD.applescript
use AppleScript version "2.7"
use framework "Foundation"
use framework "AppKit"
use scripting additions

property theWindow : missing value
property theBar : missing value
property theDesc : missing value
property thePctLabel : missing value
property statusPath : ""

on run
	try
		set mePath to POSIX path of (path to me)
		set homeDir to do shell script "cd " & quoted form of mePath & " && cd .. && pwd"
		set statusPath to homeDir & "/_status.txt"

		set rect to current application's NSMakeRect(200, 200, 360, 72)

		-- スタイルマスクは確実性のため数値合成（titled=1, closable=2）
		set styleMask to 3
		set backing to current application's NSBackingStoreBuffered

		set theWindow to current application's NSWindow's alloc()'s ¬
			initWithContentRect_styleMask_backing_defer_(rect, styleMask, backing, false)
		theWindow's setTitle:"Whisper HUD"
		-- setLevel は環境により失敗することがあるため変数化して渡す
		set statusLevel to current application's NSStatusWindowLevel
		theWindow's setLevel:statusLevel
		theWindow's setReleasedWhenClosed:false
		theWindow's setOpaque:false

		set cv to theWindow's contentView()
		set theBar to current application's NSProgressIndicator's alloc()'s ¬
			initWithFrame:(current application's NSMakeRect(20, 20, 320, 16))
		theBar's setIndeterminate:false
		theBar's setMinValue:0
		theBar's setMaxValue:100
		cv's addSubview:theBar

		set theDesc to current application's NSTextField's labelWithString:"準備中…"
		theDesc's setFrame:(current application's NSMakeRect(20, 44, 280, 16))
		cv's addSubview:theDesc

		set thePctLabel to current application's NSTextField's labelWithString:"0%"
		thePctLabel's setFrame:(current application's NSMakeRect(300, 44, 40, 16))
		thePctLabel's setAlignment:(current application's NSTextAlignmentRight)
		cv's addSubview:thePctLabel

		theWindow's center()
		theWindow's orderFrontRegardless()
	end try
end run

on idle
	try
		set defTxt to "PERCENT=0" & linefeed & "DESC=待機中"
		set cmd to "test -f " & quoted form of statusPath & " && cat " & quoted form of statusPath & " || printf %s " & quoted form of defTxt
		set txt to do shell script cmd
		set ls to paragraphs of txt
		set pct to 0
		set desc to "待機中"
		repeat with L in ls
			if L begins with "PERCENT=" then set pct to (text 9 thru -1 of L) as number
			if L begins with "DESC=" then set desc to text 6 thru -1 of L
		end repeat

		(theBar's setDoubleValue:pct)
		(thePctLabel's setStringValue:((pct as integer) as string) & "%")
		(theDesc's setStringValue:desc)

		if pct = 100 then
			theWindow's performSelector:"orderOut:" withObject:(missing value) afterDelay:5
		end if
	end try
	return 1
end idle
