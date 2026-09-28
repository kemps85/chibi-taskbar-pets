[CmdletBinding()]
param(
    # Paths are relative to the repository root unless they are absolute.
    [string]$ProjectRoot = 'src/taskbar-pet',
    [string]$OutputDirectory = 'dist/win-unpacked',
    [string[]]$ExpectedResource = @(
        # M0 is still required because the Firefly module_sword stable pack
        # intentionally resolves its authored reference frames from here.
        'resources/pet-assets/firefly/m0-human-right',
        'resources/pet-assets/config/taskbar_pet_behavior_v1.json',
        'resources/pet-assets/clip-packs/miyabi/v1',
        'resources/pet-assets/clip-packs/firefly/v1'
    )
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Resolve-RepositoryPath {
    param([Parameter(Mandatory = $true)][string]$Path)

    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }

    return [System.IO.Path]::GetFullPath((Join-Path $script:RepositoryRoot $Path))
}

function Resolve-ProjectChildPath {
    param([Parameter(Mandatory = $true)][string]$Path)

    if ([System.IO.Path]::IsPathRooted($Path)) {
        $candidate = [System.IO.Path]::GetFullPath($Path)
    }
    else {
        $candidate = [System.IO.Path]::GetFullPath((Join-Path $script:ProjectPath $Path))
    }

    $projectPrefix = $script:ProjectPath.TrimEnd('\') + '\'
    if (-not $candidate.StartsWith($projectPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Path '$Path' must remain inside the taskbar-pet project."
    }

    return $candidate
}

function Get-OptionalProperty {
    param(
        [AllowNull()][object]$Object,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if ($null -eq $Object) {
        return $null
    }

    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) {
        return $null
    }

    return $property.Value
}

function Convert-ToExecutableName {
    param([AllowNull()][object]$Value)

    if ($null -eq $Value) {
        return $null
    }

    $name = ([string]$Value).Trim()
    if ([string]::IsNullOrWhiteSpace($name)) {
        return $null
    }

    if ($name.EndsWith('.exe', [System.StringComparison]::OrdinalIgnoreCase)) {
        $name = $name.Substring(0, $name.Length - 4)
    }

    $name = $name -replace '[<>:"/\\|?*]', ''
    if ([string]::IsNullOrWhiteSpace($name)) {
        return $null
    }

    return "$name.exe"
}

function Add-ValidationError {
    param([Parameter(Mandatory = $true)][string]$Message)

    $script:ValidationErrors.Add($Message)
}

function Test-ContainedPath {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$Path
    )

    $prefix = $Root.TrimEnd('\') + '\'
    return $Path.Equals($Root, [System.StringComparison]::OrdinalIgnoreCase) -or
        $Path.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)
}

function Test-DeclaredResourceEntries {
    param(
        [AllowNull()][object]$Entries,
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$Label
    )

    if ($null -eq $Entries) {
        return
    }

    foreach ($entry in @($Entries)) {
        $source = $null
        $destination = $null
        if ($entry -is [string]) {
            $source = [string]$entry
        }
        else {
            $source = [string](Get-OptionalProperty -Object $entry -Name 'from')
            $destination = [string](Get-OptionalProperty -Object $entry -Name 'to')
        }

        if ([string]::IsNullOrWhiteSpace($source)) {
            Add-ValidationError -Message "$Label contains an entry without a source path."
            continue
        }

        if ([string]::IsNullOrWhiteSpace($destination)) {
            $sourceWithoutTrailingSlash = $source.TrimEnd('/', '\')
            $destination = Split-Path -Leaf $sourceWithoutTrailingSlash
        }
        if ([string]::IsNullOrWhiteSpace($destination) -or $destination.Contains('*')) {
            # A wildcard destination cannot be checked reliably. The source
            # itself is still represented by the normal app/resource checks.
            continue
        }

        $target = [System.IO.Path]::GetFullPath((Join-Path $Root $destination))
        if (-not (Test-ContainedPath -Root $Root -Path $target)) {
            Add-ValidationError -Message "$Label destination escapes the packaged root: $destination"
            continue
        }
        if (-not (Test-Path -LiteralPath $target)) {
            Add-ValidationError -Message "$Label destination is missing from the package: $target"
        }
    }
}

function Read-PackagedJson {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Label
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        Add-ValidationError -Message "$Label is missing: $Path"
        return $null
    }

    try {
        return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    }
    catch {
        Add-ValidationError -Message "$Label is not valid JSON: $Path ($($_.Exception.Message))"
        return $null
    }
}

function Test-RightAnchorContract {
    param([AllowNull()][object]$Anchor)

    if ($null -eq $Anchor) {
        return $false
    }

    if ($Anchor -is [System.Array]) {
        $values = @($Anchor)
        return $values.Count -eq 2 -and [string]$values[0] -eq '64' -and [string]$values[1] -eq '120'
    }

    $x = Get-OptionalProperty -Object $Anchor -Name 'x'
    $y = Get-OptionalProperty -Object $Anchor -Name 'y'
    return [string]$x -eq '64' -and [string]$y -eq '120'
}

function Test-ContiguousClipFrames {
    param(
        [Parameter(Mandatory = $true)][string]$FramesPath,
        [Parameter(Mandatory = $true)][int]$DeclaredFrameCount,
        [Parameter(Mandatory = $true)][string]$Label
    )

    if (-not (Test-Path -LiteralPath $FramesPath -PathType Container)) {
        Add-ValidationError -Message "$Label frame directory is missing: $FramesPath"
        return
    }

    $actualFiles = @(Get-ChildItem -LiteralPath $FramesPath -File)
    $actualNames = @($actualFiles | ForEach-Object { $_.Name })
    $expectedNames = @(for ($index = 0; $index -lt $DeclaredFrameCount; $index++) {
        'frame-{0:D3}.png' -f $index
    })

    if ($actualNames.Count -ne $DeclaredFrameCount) {
        Add-ValidationError -Message "$Label frame count mismatch: manifest=$DeclaredFrameCount, packaged=$($actualNames.Count)"
    }

    $missing = @($expectedNames | Where-Object { $actualNames -notcontains $_ })
    $unexpected = @($actualNames | Where-Object { $expectedNames -notcontains $_ })
    if ($missing.Count -gt 0) {
        Add-ValidationError -Message "$Label has non-contiguous/missing frames: $($missing | Select-Object -First 8 -Join ', ')"
    }
    if ($unexpected.Count -gt 0) {
        Add-ValidationError -Message "$Label has unexpected frame names: $($unexpected | Select-Object -First 8 -Join ', ')"
    }
}

function Test-StableClipPack {
    param(
        [Parameter(Mandatory = $true)][string]$ResourcesRoot,
        [Parameter(Mandatory = $true)][string]$Character,
        [Parameter(Mandatory = $true)][string]$SignatureClip
    )

    $packRoot = Join-Path $ResourcesRoot ("pet-assets/clip-packs/{0}/v1" -f $Character)
    $manifestPath = Join-Path $packRoot 'manifest.json'
    $qaPath = Join-Path $packRoot 'qa.json'
    $label = "M1 $Character stable pack"
    $manifest = Read-PackagedJson -Path $manifestPath -Label "$label manifest"
    $qa = Read-PackagedJson -Path $qaPath -Label "$label QA report"

    if ($null -ne $qa -and (Get-OptionalProperty -Object $qa -Name 'status') -ne 'PASS') {
        Add-ValidationError -Message "$label QA report status must be PASS."
    }
    if ($null -eq $manifest) {
        return
    }

    if ((Get-OptionalProperty -Object $manifest -Name 'status') -ne 'PASS') {
        Add-ValidationError -Message "$label manifest status must be PASS."
    }
    if ((Get-OptionalProperty -Object $manifest -Name 'schema_version') -ne 1) {
        Add-ValidationError -Message "$label manifest schema_version must be 1."
    }
    if ((Get-OptionalProperty -Object $manifest -Name 'character_id') -ne $Character) {
        Add-ValidationError -Message "$label manifest character_id must be $Character."
    }
    $canvas = Get-OptionalProperty -Object $manifest -Name 'canvas'
    if ((Get-OptionalProperty -Object $canvas -Name 'width') -ne 160 -or
        (Get-OptionalProperty -Object $canvas -Name 'height') -ne 144) {
        Add-ValidationError -Message "$label canvas must be 160x144."
    }
    if ((Get-OptionalProperty -Object $manifest -Name 'master_direction') -ne 'right') {
        Add-ValidationError -Message "$label master_direction must be right."
    }

    $signature = Get-OptionalProperty -Object (Get-OptionalProperty -Object $manifest -Name 'signature') -Name 'clip'
    if ($signature -ne $SignatureClip) {
        Add-ValidationError -Message "$label signature.clip must be $SignatureClip."
    }
    $requiredClips = @((Get-OptionalProperty -Object $manifest -Name 'required_clips'))
    $expectedClips = @('idle', 'walk', 'hunger_cue', 'sleep_cue', 'sleep_enter', 'sleep_loop', 'wake', $SignatureClip)
    foreach ($clipId in $expectedClips) {
        if ($requiredClips -notcontains $clipId) {
            Add-ValidationError -Message "$label required_clips is missing $clipId."
        }
    }

    $clips = Get-OptionalProperty -Object $manifest -Name 'clips'
    if ($null -eq $clips) {
        Add-ValidationError -Message "$label manifest clips table is missing."
        return
    }

    foreach ($clipId in $expectedClips) {
        $clip = Get-OptionalProperty -Object $clips -Name $clipId
        if ($null -eq $clip) {
            Add-ValidationError -Message "$label clip $clipId is missing."
            continue
        }

        $framePattern = Get-OptionalProperty -Object $clip -Name 'frame_name_pattern'
        if ($framePattern -ne 'frame-{index:000}.png') {
            Add-ValidationError -Message "$label clip $clipId frame_name_pattern is not frame-{index:000}.png."
        }
        $frameCountText = [string](Get-OptionalProperty -Object $clip -Name 'frame_count')
        $frameCount = 0
        if ($frameCountText -notmatch '^\d+$' -or -not [int]::TryParse($frameCountText, [ref]$frameCount) -or $frameCount -le 0) {
            Add-ValidationError -Message "$label clip $clipId frame_count must be a positive integer."
            continue
        }

        if (-not (Test-RightAnchorContract -Anchor (Get-OptionalProperty -Object $clip -Name 'right_anchor'))) {
            Add-ValidationError -Message "$label clip $clipId right_anchor must be [64, 120]."
        }
        $durations = @((Get-OptionalProperty -Object $clip -Name 'frame_durations_ms'))
        if ($durations.Count -ne $frameCount) {
            Add-ValidationError -Message "$label clip $clipId frame_durations_ms must contain $frameCount entries."
        }
        else {
            foreach ($duration in $durations) {
                $durationText = [string]$duration
                $durationValue = 0
                if ($durationText -notmatch '^\d+$' -or -not [int]::TryParse($durationText, [ref]$durationValue) -or $durationValue -le 0) {
                    Add-ValidationError -Message "$label clip $clipId has a non-positive frame duration."
                    break
                }
            }
        }

        $framesRelative = [string](Get-OptionalProperty -Object $clip -Name 'frames')
        if ([string]::IsNullOrWhiteSpace($framesRelative)) {
            Add-ValidationError -Message "$label clip $clipId frames path is missing."
            continue
        }
        $framesPath = [System.IO.Path]::GetFullPath((Join-Path $packRoot $framesRelative))
        if (-not (Test-ContainedPath -Root $packRoot -Path $framesPath)) {
            Add-ValidationError -Message "$label clip $clipId frames path escapes its pack root: $framesRelative"
            continue
        }
        Test-ContiguousClipFrames -FramesPath $framesPath -DeclaredFrameCount $frameCount -Label "$label clip $clipId"
    }
}

function Test-M1PackagedContract {
    param([Parameter(Mandatory = $true)][string]$ResourcesRoot)

    $behaviorPath = Join-Path $ResourcesRoot 'pet-assets/config/taskbar_pet_behavior_v1.json'
    $behavior = Read-PackagedJson -Path $behaviorPath -Label 'M1 behavior configuration'
    if ($null -eq $behavior) {
        return
    }

    if ((Get-OptionalProperty -Object $behavior -Name 'milestone') -ne 'M1') {
        Add-ValidationError -Message 'Packaged behavior configuration milestone must be M1.'
    }
    if ((Get-OptionalProperty -Object $behavior -Name 'schemaVersion') -ne 1) {
        Add-ValidationError -Message 'Packaged behavior configuration schemaVersion must be 1.'
    }
    $scopeCharacters = @((Get-OptionalProperty -Object (Get-OptionalProperty -Object $behavior -Name 'scope') -Name 'characters'))
    if ($scopeCharacters.Count -ne 2) {
        Add-ValidationError -Message 'Packaged M1 scope.characters must contain exactly Miyabi and Firefly.'
    }
    foreach ($character in @('miyabi', 'firefly')) {
        if ($scopeCharacters -notcontains $character) {
            Add-ValidationError -Message "Packaged M1 scope.characters is missing $character."
        }
    }

    $characters = Get-OptionalProperty -Object $behavior -Name 'characters'
    $miyabiConfig = Get-OptionalProperty -Object $characters -Name 'miyabi'
    $fireflyConfig = Get-OptionalProperty -Object $characters -Name 'firefly'
    foreach ($contract in @(
        [pscustomobject]@{ Character = 'miyabi'; Config = $miyabiConfig; SignatureClip = 'spirit_tail' },
        [pscustomobject]@{ Character = 'firefly'; Config = $fireflyConfig; SignatureClip = 'module_sword' }
    )) {
        if ($null -eq $contract.Config) {
            Add-ValidationError -Message "Packaged M1 character configuration is missing $($contract.Character)."
            continue
        }
        $required = @((Get-OptionalProperty -Object $contract.Config -Name 'requiredClips'))
        if ($required -notcontains $contract.SignatureClip) {
            Add-ValidationError -Message "Packaged M1 $($contract.Character) requiredClips is missing $($contract.SignatureClip)."
        }
        $manifestRef = [string](Get-OptionalProperty -Object $contract.Config -Name 'clipPackManifest')
        $expectedRef = "assets/runtime/taskbar-pet/clip-packs/$($contract.Character)/v1/manifest.json"
        if ($manifestRef -ne $expectedRef) {
            Add-ValidationError -Message "Packaged M1 $($contract.Character) clipPackManifest must be $expectedRef."
        }
        Test-StableClipPack -ResourcesRoot $ResourcesRoot -Character $contract.Character -SignatureClip $contract.SignatureClip
    }
}

$script:RepositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$script:ProjectPath = Resolve-RepositoryPath -Path $ProjectRoot
$script:ValidationErrors = New-Object System.Collections.Generic.List[string]

if (-not (Test-Path -LiteralPath $script:ProjectPath -PathType Container)) {
    throw "Taskbar-pet project directory was not found: $script:ProjectPath"
}

$packagePath = Join-Path $script:ProjectPath 'package.json'
if (-not (Test-Path -LiteralPath $packagePath -PathType Leaf)) {
    throw "Taskbar-pet package.json was not found: $packagePath"
}

$package = Get-Content -LiteralPath $packagePath -Raw | ConvertFrom-Json
$buildConfiguration = Get-OptionalProperty -Object $package -Name 'build'
$windowsConfiguration = Get-OptionalProperty -Object $buildConfiguration -Name 'win'
$resourcesPath = $null
$foundExecutable = $null
$outputPath = Resolve-ProjectChildPath -Path $OutputDirectory

if (-not (Test-Path -LiteralPath $outputPath -PathType Container)) {
    Add-ValidationError -Message "win-unpacked output directory is missing: $outputPath"
}
else {
    $resourcesPath = Join-Path $outputPath 'resources'
    if (-not (Test-Path -LiteralPath $resourcesPath -PathType Container)) {
        Add-ValidationError -Message "Packaged resources directory is missing: $resourcesPath"
    }
    else {
        $asarPath = Join-Path $resourcesPath 'app.asar'
        $appDirectory = Join-Path $resourcesPath 'app'
        if (-not (Test-Path -LiteralPath $asarPath -PathType Leaf) -and
            -not (Test-Path -LiteralPath $appDirectory -PathType Container)) {
            Add-ValidationError -Message "Expected resources/app.asar or resources/app was not found."
        }

        Test-DeclaredResourceEntries -Entries (Get-OptionalProperty -Object $buildConfiguration -Name 'extraResources') -Root $resourcesPath -Label 'build.extraResources'
    }

    Test-DeclaredResourceEntries -Entries (Get-OptionalProperty -Object $buildConfiguration -Name 'extraFiles') -Root $outputPath -Label 'build.extraFiles'

    # M1 is the current release contract. Validate the packaged behavior
    # config and both stable character packs before the optional M0 smoke
    # launch; this prevents a Firefly-only package from passing accidentally.
    Test-M1PackagedContract -ResourcesRoot $resourcesPath

    foreach ($resource in @($ExpectedResource)) {
        if ([string]::IsNullOrWhiteSpace($resource)) {
            continue
        }

        $resourcePath = [System.IO.Path]::GetFullPath((Join-Path $outputPath $resource))
        if (-not (Test-ContainedPath -Root $outputPath -Path $resourcePath)) {
            Add-ValidationError -Message "Expected resource escapes win-unpacked: $resource"
        }
        elseif (-not (Test-Path -LiteralPath $resourcePath)) {
            Add-ValidationError -Message "Expected resource is missing: $resourcePath"
        }
    }

    $executableNames = New-Object System.Collections.Generic.List[string]
    foreach ($value in @(
        (Get-OptionalProperty -Object $buildConfiguration -Name 'executableName'),
        (Get-OptionalProperty -Object $windowsConfiguration -Name 'executableName'),
        (Get-OptionalProperty -Object $buildConfiguration -Name 'productName'),
        (Get-OptionalProperty -Object $package -Name 'productName'),
        (Get-OptionalProperty -Object $package -Name 'name')
    )) {
        $executableName = Convert-ToExecutableName -Value $value
        if ($null -ne $executableName -and -not $executableNames.Contains($executableName)) {
            $executableNames.Add($executableName)
        }
    }

    foreach ($executableName in $executableNames) {
        $candidate = Join-Path $outputPath $executableName
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            $foundExecutable = $candidate
            break
        }
    }

    if ($null -eq $foundExecutable) {
        $fallbackExecutables = @(Get-ChildItem -LiteralPath $outputPath -Filter '*.exe' -File | Where-Object {
            $_.Name -notmatch '(?i)uninstall'
        })
        if ($fallbackExecutables.Count -eq 1) {
            $foundExecutable = $fallbackExecutables[0].FullName
        }
        elseif ($fallbackExecutables.Count -eq 0) {
            Add-ValidationError -Message 'No application executable was found in win-unpacked.'
        }
        else {
            Add-ValidationError -Message ('Could not determine the application executable; candidates: ' + (($fallbackExecutables | ForEach-Object Name) -join ', '))
        }
    }

    if ($null -ne $foundExecutable -and (Get-Item -LiteralPath $foundExecutable).Length -le 0) {
        Add-ValidationError -Message "Application executable is empty: $foundExecutable"
    }
}

if ($script:ValidationErrors.Count -eq 0 -and $null -ne $foundExecutable) {
    $existingPackagedProcesses = @(Get-Process | Where-Object {
        $_.Path -and $_.Path.Equals($foundExecutable, [System.StringComparison]::OrdinalIgnoreCase)
    })
    if ($existingPackagedProcesses.Count -gt 0) {
        Add-ValidationError -Message "Packaged smoke cannot start while the same executable is already running: $foundExecutable"
    }
    else {
        Write-Host "> smoke testing $foundExecutable --smoke"
        $smokeProcess = Start-Process -FilePath $foundExecutable -ArgumentList '--smoke' -PassThru -WindowStyle Hidden
        try {
            if (-not $smokeProcess.WaitForExit(15000)) {
                Add-ValidationError -Message 'Packaged smoke timed out before rendering the first authored frame.'
            }
            elseif ($smokeProcess.ExitCode -ne 0) {
                Add-ValidationError -Message "Packaged smoke exited with code $($smokeProcess.ExitCode)."
            }
        }
        finally {
            if (-not $smokeProcess.HasExited) {
                try {
                    $smokeProcess.Kill($true)
                    $smokeProcess.WaitForExit()
                }
                catch {
                    Write-Verbose "Unable to stop timed-out smoke process: $_"
                }
            }
        }
    }
}

if ($script:ValidationErrors.Count -gt 0) {
    Write-Host 'Taskbar-pet package validation FAILED:' -ForegroundColor Red
    foreach ($errorMessage in $script:ValidationErrors) {
        Write-Host "  - $errorMessage" -ForegroundColor Red
    }
    throw "Package validation failed with $($script:ValidationErrors.Count) error(s)."
}

Write-Host "Taskbar-pet package validation PASSED: $outputPath" -ForegroundColor Green
