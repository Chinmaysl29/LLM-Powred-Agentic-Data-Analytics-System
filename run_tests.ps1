# =============================================================================
# AI Data Analyst OS — Full Backend Test Suite Runner
# Run from the project root: .\run_tests.ps1
# =============================================================================

param(
    [string]$Suite = "all",        # all | unit | integration | api | services | agents | e2e
    [string]$Module = "",          # Run a specific test file, e.g. "test_core"
    [switch]$Verbose,
    [switch]$Coverage,
    [switch]$FailFast,
    [switch]$NoCaptue
)

$ROOT = $PSScriptRoot
$TESTS = Join-Path $ROOT "tests"
$PYTEST = "pytest"

# -------------------------------------------------------------------------
# Build pytest arguments
# -------------------------------------------------------------------------
$args = @()

# Test path
if ($Module -ne "") {
    $args += Join-Path $TESTS "$Module.py"
} else {
    switch ($Suite) {
        "unit" {
            $args += "$TESTS/test_core.py"
            $args += "$TESTS/test_database.py"
            $args += "$TESTS/test_middleware.py"
            $args += "$TESTS/test_models.py"
            $args += "$TESTS/test_repositories.py"
        }
        "services" {
            $args += "$TESTS/test_services_core.py"
            $args += "$TESTS/test_services_analytics.py"
            $args += "$TESTS/test_services_forecast.py"
            $args += "$TESTS/test_services_rag.py"
            $args += "$TESTS/test_services_auth.py"
        }
        "agents" {
            $args += "$TESTS/test_agents.py"
        }
        "api" {
            $args += "$TESTS/test_api_health.py"
            $args += "$TESTS/test_api_auth.py"
            $args += "$TESTS/test_api_datasets.py"
            $args += "$TESTS/test_api_analytics.py"
            $args += "$TESTS/test_api_forecasting.py"
            $args += "$TESTS/test_api_rag.py"
            $args += "$TESTS/test_api_workspaces.py"
        }
        "e2e" {
            $args += "$TESTS/test_integration_e2e.py"
        }
        default {
            # Run ALL tests
            $args += $TESTS
        }
    }
}

# Options
$args += "-v"
if ($Verbose) { $args += "--tb=long" } else { $args += "--tb=short" }
if ($FailFast) { $args += "-x" }
if ($NoCaptue) { $args += "-s" }

# Coverage
if ($Coverage) {
    $args += "--cov=backend"
    $args += "--cov-report=term-missing"
    $args += "--cov-report=html:htmlcov"
    $args += "--cov-fail-under=60"
}

# Always use asyncio mode
$args += "--asyncio-mode=auto"

# -------------------------------------------------------------------------
# Run
# -------------------------------------------------------------------------
Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  AI Data Analyst OS — Backend Test Suite" -ForegroundColor Cyan
Write-Host "  Suite: $Suite" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $ROOT
& $PYTEST @args

$exitCode = $LASTEXITCODE
Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "ALL TESTS PASSED" -ForegroundColor Green
} else {
    Write-Host "TESTS FAILED (exit code: $exitCode)" -ForegroundColor Red
}
exit $exitCode
