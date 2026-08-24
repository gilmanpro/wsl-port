' Lanzador oculto de wsl-port: pythonw + run.py, SIN terminal.
' Funciona en cualquier PC que clone el repositorio.
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)

' Buscar pythonw.exe
pythonw = ""

' 1. venv del proyecto
pythonw = dir & "\.venv\Scripts\pythonw.exe"
If fso.FileExists(pythonw) Then
    ' Found
Else
    ' 2. Python del sistema (PATH)
    pythonw = "pythonw.exe"
End If

' Ejecutar run.py sin ventana
sh.Run """" & pythonw & """ """ & dir & "\run.py""", 0, False
