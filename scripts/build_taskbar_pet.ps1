[CmdletBinding()]
param(
    # Paths are relative to the repository root unless they are absolute.
    [string]$ProjectRoot = 'src/taskbar-pet',
    [string]$OutputDirectory = 'dist/win-unpacked',
    [string]$TestScript,
    [string]$AssetValidationScript,
    [string]$BuildScript,
    [string[]]$ExpectedResource = @()
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

function Get-NpmScriptText {
    param([Parameter(Mandatory = $true)][string]$Name)

    if ($null -eq $script:NpmScripts) {
        return $null
    }

    $property = $script:NpmScripts.PSObject.Properties[$Name]
    if ($null -eq $property) {
        return $null
    }

    return [string]$property.Value
}

function Select-NpmScript {
    param(
        [string]$Override,
        [Parameter(Mandatory = $true)][string[]]$Candidates,
        [Parameter(Mandatory = $true)][string]$Purpose
    )

    if (-not [string]::IsNullOrWhiteSpace($Override)) {
        if ($null -eq (Get-NpmScriptText -Name $Override)) {
            throw "The requested $Purpose npm script '$Override' is not present in package.json."
        }

        return $Override
    }

    foreach ($candidate in $Candidates) {
        if ($null -ne (Get-NpmScriptText -Name $candidate)) {
            return $candidate
        }
    }

    throw "No $Purpose npm script was found. Add one to src/taskbar-pet/package.json or pass -$Purpose`Script explicitly."
}

function Invoke-Npm {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    Write-Host ("`n> npm " + ($Arguments -join ' '))
    & $script:NpmPath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "npm command failed with exit code ${LASTEXITCODE}: npm $($Arguments -join ' ')"
    }
}

$script:RepositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$script:ProjectPath = Resolve-RepositoryPath -Path $ProjectRoot

if (-not (Test-Path -LiteralPath $script:ProjectPath -PathType Container)) {
    throw "Taskbar-pet project directory was not found: $script:ProjectPath"
}

$packagePath = Join-Path $script:ProjectPath 'package.json'
$lockPath = Join-Path $script:ProjectPath 'package-lock.json'
if (-not (Test-Path -LiteralPath $packagePath -PathType Leaf)) {
    throw "Taskbar-pet package.json was not found: $packagePath"
}
if (-not (Test-Path -LiteralPath $lockPath -PathType Leaf)) {
    throw "Deterministic installation requires package-lock.json: $lockPath"
}

$package = Get-Content -LiteralPath $packagePath -Raw | ConvertFrom-Json
$script:NpmScripts = $package.scripts
$npmCommand = Get-Command npm -ErrorAction SilentlyContinue
if ($null -eq $npmCommand) {
    throw 'npm was not found on PATH. Install the project-approved Node.js runtime before building.'
}
$script:NpmPath = $npmCommand.Source

$testScriptName = Select-NpmScript -Override $TestScript -Candidates @(
    'test',
    'test:ci',
    'test:unit',
    'test:all'
) -Purpose 'test'
$assetScriptName = Select-NpmScript -Override $AssetValidationScript -Candidates @(
    'validate:assets',
    'validate-assets',
    'assets:validate',
    'verify:assets',
    'test:assets',
    # The package also exposes `smoke`, which executes the packaged renderer
    # asset contract when a dedicated validate:assets alias is unavailable.
    'smoke'
) -Purpose 'asset validation'

Push-Location $script:ProjectPath
try {
    Write-Host "Building taskbar-pet from $script:ProjectPath"

    # npm ci is intentionally required: it removes drift from a stale
    # node_modules tree and installs exactly the package-lock dependency graph.
    Invoke-Npm -Arguments @('ci')
    Invoke-Npm -Arguments @('run', $testScriptName)
    Invoke-Npm -Arguments @('run', $assetScriptName)

    $outputPath = Resolve-ProjectChildPath -Path $OutputDirectory
    if (Test-Path -LiteralPath $outputPath) {
        # A previous packaged smoke can keep app.asar open. Only stop
        # executables located in this exact app-owned output directory; never
        # broad-match a similarly named desktop process.
        $runningPackagedProcesses = @()
        foreach ($packagedExecutable in @(Get-ChildItem -LiteralPath $outputPath -Filter '*.exe' -File | Where-Object {
            $_.Name -notmatch '(?i)uninstall'
        })) {
            $runningPackagedProcesses += @(Get-Process | Where-Object {
                $_.Path -and $_.Path.Equals($packagedExecutable.FullName, [System.StringComparison]::OrdinalIgnoreCase)
            })
        }
        if ($runningPackagedProcesses.Count -gt 0) {
            Write-Host "Stopping $($runningPackagedProcesses.Count) stale packaged smoke process(es)."
            $runningPackagedProcesses | Stop-Process -Force
            Start-Sleep -Milliseconds 500
        }
        Write-Host "Removing previous unpacked output: $outputPath"
        $removedOutput = $false
        $lastRemoveError = $null
        for ($attempt = 1; $attempt -le 8; $attempt++) {
            try {
                Remove-Item -LiteralPath $outputPath -Recurse -Force
                $removedOutput = $true
                break
            }
            catch {
                $lastRemoveError = $_
                Start-Sleep -Seconds 1
            }
        }
        if (-not $removedOutput) {
            throw "Unable to remove the previous unpacked output after 8 attempts. Close any running packaged pet and retry. Last error: $lastRemoveError"
        }
    }

    $buildScriptName = $null
    if (-not [string]::IsNullOrWhiteSpace($BuildScript)) {
        $buildScriptName = Select-NpmScript -Override $BuildScript -Candidates @('build:win', 'build') -Purpose 'build'
    }
    else {
        foreach ($candidate in @('build:win:dir', 'build:win', 'package:win', 'build')) {
            if ($null -ne (Get-NpmScriptText -Name $candidate)) {
                $buildScriptName = $candidate
                break
            }
        }
    }

    $usedPackagingScript = $false
    if ($null -ne $buildScriptName) {
        $buildText = Get-NpmScriptText -Name $buildScriptName
        $buildArguments = @('run', $buildScriptName)
        if ($buildText -match '(?i)electron-builder') {
            # A directory build is the first artifact on purpose. The --dir
            # flag prevents this helper from publishing an installer.
            $buildArguments += @('--', '--win', '--dir')
            $usedPackagingScript = $true
        }

        Invoke-Npm -Arguments $buildArguments
    }

    # A compile-only npm build or a package script with a different name still
    # gets a deterministic local electron-builder directory build. --no keeps
    # npm from downloading an undeclared global/transient package.
    if (-not (Test-Path -LiteralPath $outputPath -PathType Container)) {
        Write-Host 'No win-unpacked directory was produced; invoking the local electron-builder binary.'
        Invoke-Npm -Arguments @('exec', '--no', '--', 'electron-builder', '--win', '--dir')
    }

    if (-not (Test-Path -LiteralPath $outputPath -PathType Container)) {
        throw "The Windows directory build did not produce $outputPath"
    }

    $validatorPath = Join-Path $PSScriptRoot 'validate_taskbar_pet_package.ps1'
    if (-not (Test-Path -LiteralPath $validatorPath -PathType Leaf)) {
        throw "Package validator was not found: $validatorPath"
    }

    $validatorArguments = @{
        ProjectRoot = $script:ProjectPath
        OutputDirectory = $outputPath
    }
    if ($ExpectedResource.Count -gt 0) {
        $validatorArguments.ExpectedResource = $ExpectedResource
    }

    Write-Host "`n> validating $outputPath"
    & $validatorPath @validatorArguments
    if (-not $?) {
        throw 'Taskbar-pet package validation failed.'
    }

    Write-Host "`nTaskbar-pet win-unpacked build completed: $outputPath"
}
finally {
    Pop-Location
}
