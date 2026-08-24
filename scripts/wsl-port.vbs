' Lanzador oculto de wsl-port: pythonw + run.py, SIN terminal.
' Funciona en cualquier PC que clone el repositorio.
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)

' Buscar pythonw.exe en PATH o en ubicaciones comunes
pythonw = ""

' 1. Intentar con el pythonw del sistema (PATH)
pythonw = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python311\pythonw.exe"
If fso.FileExists(pythonw) Then
    ' Found it
Else
    ' 2. Intentar con el venv del proyecto
    pythonw = dir & "\.venv\Scripts\pythonw.exe"
    If Not fso.FileExists(pythonw) Then
        ' 3. Intentar con pythonw del PATH
        pythonw = "pythonw.exe"
    End If
End If

' Ejecutar run.py sin ventana
sh.Run """" & pythonw & """ """ & dir & "\run.py""", 0, False
