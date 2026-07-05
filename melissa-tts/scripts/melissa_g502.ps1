<# 
 melissa_g502.ps1 — Puente MELISSA-TTS para Logitech G502
 Metodo A: Activa MELISSA-TTS, pega portapapeles, y habla con Ctrl+Enter
 
 Asignar en G Hub:
   1. G Hub > G502 X > Asignaciones > Boton lateral superior
   2. Tipo: Ejecutar programa -> melissa_g502.ps1
   3. O crear macro LEER_MELISSA que lance este script
 
 Requisitos:
   - edge-tts (pip install edge-tts)
   - Opcional: azure-cognitiveservices-speech (para voces Neural)
 
 Autor: MELI (PUENTE_OPERADORA) / MELISSA (PUENTE_BILINGUE_TRADUCTORA)
 Sistema: COLMENA / IArtLabs
 Version: 1.0.0
#>

param(
    [string]$Action = "speak"
)

$ErrorActionPreference = "SilentlyContinue"

$melissaScript = Join-Path $PSScriptRoot "melissa_tts_gui.py"
$melissaWindowTitle = "MELISSA-TTS"

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count);
}
"@

function Find-MelissaWindow {
    $procs = Get-Process | Where-Object { $_.MainWindowTitle -like "*$melissaWindowTitle*" -and $_.MainWindowHandle -ne [IntPtr]::Zero }
    if ($procs) {
        return $procs[0]
    }
    return $null
}

function Start-MelissaIfNotRunning {
    $proc = Find-MelissaWindow
    if ($null -eq $proc) {
        Start-Process -FilePath "python" -ArgumentList $melissaScript -WindowStyle Normal
        Start-Sleep -Milliseconds 2000
        $proc = Find-MelissaWindow
    }
    return $proc
}

function Activate-MelissaWindow {
    param([IntPtr]$Handle)
    [Win32]::ShowWindow($Handle, 9) | Out-Null
    [Win32]::SetForegroundWindow($Handle) | Out-Null
    Start-Sleep -Milliseconds 200
    $fg = [Win32]::GetForegroundWindow()
    $sb = New-Object System.Text.StringBuilder 256
    [Win32]::GetWindowText($fg, $sb, 256) | Out-Null
    return ($sb.ToString() -like "*$melissaWindowTitle*")
}

switch ($Action) {
    "speak" {
        $proc = Start-MelissaIfNotRunning
        if ($null -ne $proc) {
            $activated = Activate-MelissaWindow -Handle $proc.MainWindowHandle
            if ($activated) {
                Add-Type -AssemblyName System.Windows.Forms
                [System.Windows.Forms.SendKeys]::SendWait("^v")
                Start-Sleep -Milliseconds 300
                [System.Windows.Forms.SendKeys]::SendWait("^{ENTER}")
                Write-Output "MELISSA-TTS: Texto pegado y hablado"
            } else {
                Write-Output "HOLD: No se pudo activar ventana MELISSA-TTS"
            }
        } else {
            Write-Output "HOLD: MELISSA-TTS no se pudo iniciar"
        }
    }
    "speak-conclude" {
        $proc = Start-MelissaIfNotRunning
        if ($null -ne $proc) {
            $activated = Activate-MelissaWindow -Handle $proc.MainWindowHandle
            if ($activated) {
                Add-Type -AssemblyName System.Windows.Forms
                [System.Windows.Forms.SendKeys]::SendWait("^v")
                Start-Sleep -Milliseconds 300
                [System.Windows.Forms.SendKeys]::SendWait("^+{ENTER}")
                Write-Output "MELISSA-TTS: Texto pegado y concluido"
            } else {
                Write-Output "HOLD: No se pudo activar ventana MELISSA-TTS"
            }
        } else {
            Write-Output "HOLD: MELISSA-TTS no se pudo iniciar"
        }
    }
    "open" {
        $proc = Start-MelissaIfNotRunning
        if ($null -ne $proc) {
            Activate-MelissaWindow -Handle $proc.MainWindowHandle | Out-Null
            Write-Output "MELISSA-TTS: Ventana activada"
        } else {
            Write-Output "HOLD: MELISSA-TTS no se pudo iniciar"
        }
    }
    default {
        Write-Output "Uso: .\melissa_g502.ps1 -Action speak|speak-conclude|open"
    }
}