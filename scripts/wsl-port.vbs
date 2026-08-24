' Lanzador oculto de wsl-port: exe compilado, SIN terminal.
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
sh.Run """" & dir & "\dist\wsl-port\wsl-port.exe""", 0, False