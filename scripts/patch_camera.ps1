param(
    [string]$DllPath,
    [string]$CecilPath = ""
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $DllPath)) {
    Write-Error "Assembly not found: $DllPath"
    exit 1
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$wsDir = Split-Path -Parent $scriptDir

if ([string]::IsNullOrEmpty($CecilPath)) {
    $possiblePaths = @(
        (Join-Path $wsDir "tools\ilspycmd\Mono.Cecil.dll"),
        "tools\ilspycmd\Mono.Cecil.dll",
        (Join-Path $scriptDir "..\tools\ilspycmd\Mono.Cecil.dll")
    )
    foreach ($p in $possiblePaths) {
        if (Test-Path $p) {
            $CecilPath = (Resolve-Path $p).Path
            break
        }
    }
}

if (-not (Test-Path $CecilPath)) {
    Write-Error "Mono.Cecil.dll not found: $CecilPath"
    exit 1
}

Add-Type -Path (Resolve-Path $CecilPath).Path

# Read bytes into memory first so the file is not locked
$resolvedDll = (Resolve-Path $DllPath).Path
$bytes = [System.IO.File]::ReadAllBytes($resolvedDll)
$mem = New-Object System.IO.MemoryStream(,$bytes)
$asm = [Mono.Cecil.AssemblyDefinition]::ReadAssembly($mem)
$mainMod = $asm.MainModule

$type = $mainMod.Types | Where-Object { $_.Name -eq 'EnvironmentCameraController' }
if ($null -eq $type) {
    Write-Error "EnvironmentCameraController type not found"
    exit 1
}

$getFloatRef = $mainMod.GetMemberReferences() | Where-Object { 
    $_.Name -eq 'GetFloat' -and $_.DeclaringType.FullName -eq 'UnityEngine.PlayerPrefs' 
} | Select-Object -First 1

$opMulRef = $mainMod.GetMemberReferences() | Where-Object { 
    $_.Name -eq 'op_Multiply' -and $_.FullName -like '*UnityEngine.Vector3,System.Single*' 
} | Select-Object -First 1

# 1. Patch getGyro()
$mGetGyro = $type.Methods | Where-Object { $_.Name -eq 'getGyro' }
$ilGyro = $mGetGyro.Body.GetILProcessor()

# Check if already patched
$alreadyPatched = $false
foreach ($instr in $mGetGyro.Body.Instructions) {
    if ($instr.OpCode.Name -eq 'ldstr' -and [string]$instr.Operand -eq 'gyro_sensitivity') {
        $alreadyPatched = $true
        break
    }
}

if (-not $alreadyPatched) {
    $found = $null
    foreach ($instr in $mGetGyro.Body.Instructions) {
        if ($instr.OpCode.Name -eq 'ldc.r4' -and [Math]::Abs([float]$instr.Operand - 57.29578) -lt 0.001) {
            $found = $instr.Next # this is the call op_Multiply
            break
        }
    }

    if ($found -ne $null) {
        $i1 = $ilGyro.Create([Mono.Cecil.Cil.OpCodes]::Ldstr, "gyro_sensitivity")
        $i2 = $ilGyro.Create([Mono.Cecil.Cil.OpCodes]::Ldc_R4, [float]1.2)
        $i3 = $ilGyro.Create([Mono.Cecil.Cil.OpCodes]::Call, $getFloatRef)
        $i4 = $ilGyro.Create([Mono.Cecil.Cil.OpCodes]::Call, $opMulRef)
        
        $ilGyro.InsertAfter($found, $i1)
        $ilGyro.InsertAfter($i1, $i2)
        $ilGyro.InsertAfter($i2, $i3)
        $ilGyro.InsertAfter($i3, $i4)
        Write-Host "[+] Patched getGyro() with live gyro_sensitivity multiplier."
    }
}

# 2. Patch FixedUpdate()
$mFixed = $type.Methods | Where-Object { $_.Name -eq 'FixedUpdate' }
$ilFixed = $mFixed.Body.GetILProcessor()

$fixedAlreadyPatched = $false
foreach ($instr in $mFixed.Body.Instructions) {
    if ($instr.OpCode.Name -eq 'ldstr' -and [string]$instr.Operand -eq 'gyro_sensitivity') {
        $fixedAlreadyPatched = $true
        break
    }
}

if (-not $fixedAlreadyPatched) {
    $fScaleX = $type.Fields | Where-Object { $_.Name -eq 'accInputScaleX' }
    $fScaleY = $type.Fields | Where-Object { $_.Name -eq 'accInputScaleY' }
    $fSpeed = $type.Fields | Where-Object { $_.Name -eq 'cameraSpeedLimit' }
    $fSpeedTilt = $type.Fields | Where-Object { $_.Name -eq 'cameraSpeedLimitTilt' }

    $first = $mFixed.Body.Instructions[0]

    $fixInstrs = @(
        # accInputScaleX = PlayerPrefs.GetFloat("gyro_sensitivity", 1.2f)
        $ilFixed.Create([Mono.Cecil.Cil.OpCodes]::Ldarg_0),
        $ilFixed.Create([Mono.Cecil.Cil.OpCodes]::Ldstr, "gyro_sensitivity"),
        $ilFixed.Create([Mono.Cecil.Cil.OpCodes]::Ldc_R4, [float]1.2),
        $ilFixed.Create([Mono.Cecil.Cil.OpCodes]::Call, $getFloatRef),
        $ilFixed.Create([Mono.Cecil.Cil.OpCodes]::Stfld, $fScaleX),

        # accInputScaleY = PlayerPrefs.GetFloat("gyro_sensitivity", 1.2f)
        $ilFixed.Create([Mono.Cecil.Cil.OpCodes]::Ldarg_0),
        $ilFixed.Create([Mono.Cecil.Cil.OpCodes]::Ldstr, "gyro_sensitivity"),
        $ilFixed.Create([Mono.Cecil.Cil.OpCodes]::Ldc_R4, [float]1.2),
        $ilFixed.Create([Mono.Cecil.Cil.OpCodes]::Call, $getFloatRef),
        $ilFixed.Create([Mono.Cecil.Cil.OpCodes]::Stfld, $fScaleY),

        # cameraSpeedLimit = 180f - (PlayerPrefs.GetFloat("gyro_damping", 35f) * 1.5f)
        $ilFixed.Create([Mono.Cecil.Cil.OpCodes]::Ldarg_0),
        $ilFixed.Create([Mono.Cecil.Cil.OpCodes]::Ldc_R4, [float]180.0),
        $ilFixed.Create([Mono.Cecil.Cil.OpCodes]::Ldstr, "gyro_damping"),
        $ilFixed.Create([Mono.Cecil.Cil.OpCodes]::Ldc_R4, [float]35.0),
        $ilFixed.Create([Mono.Cecil.Cil.OpCodes]::Call, $getFloatRef),
        $ilFixed.Create([Mono.Cecil.Cil.OpCodes]::Ldc_R4, [float]1.5),
        $ilFixed.Create([Mono.Cecil.Cil.OpCodes]::Mul),
        $ilFixed.Create([Mono.Cecil.Cil.OpCodes]::Sub),
        $ilFixed.Create([Mono.Cecil.Cil.OpCodes]::Stfld, $fSpeed),

        # cameraSpeedLimitTilt = cameraSpeedLimit
        $ilFixed.Create([Mono.Cecil.Cil.OpCodes]::Ldarg_0),
        $ilFixed.Create([Mono.Cecil.Cil.OpCodes]::Ldarg_0),
        $ilFixed.Create([Mono.Cecil.Cil.OpCodes]::Ldfld, $fSpeed),
        $ilFixed.Create([Mono.Cecil.Cil.OpCodes]::Stfld, $fSpeedTilt)
    )

    foreach ($inst in $fixInstrs) {
        $ilFixed.InsertBefore($first, $inst)
    }
    Write-Host "[+] Patched FixedUpdate() with sensitivity & damping scaling."
}

# 3. Save modified assembly
$asm.Write($resolvedDll)
$asm.Dispose()
$mem.Dispose()
Write-Host "[+] Successfully saved modified Assembly-CSharp.dll to $resolvedDll"
