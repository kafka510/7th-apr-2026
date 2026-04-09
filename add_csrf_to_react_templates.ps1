# ========================================
# Add CSRF Meta Tag to All React Templates
# ========================================
# This script adds <meta name="csrf-token" content="{{ csrf_token }}">
# to all React templates that don't already have it

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Add CSRF Token to React Templates" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$BASE_PATH = "D:\django_web_app\templates"

# Get all React templates
$reactTemplates = Get-ChildItem -Path $BASE_PATH -Recurse -Filter "*_react.html"

Write-Host "[1/3] Found $($reactTemplates.Count) React templates" -ForegroundColor Yellow
Write-Host ""

# Check which templates already have the CSRF meta tag
$withCSRF = @()
$withoutCSRF = @()

foreach ($template in $reactTemplates) {
    $content = Get-Content $template.FullName -Raw
    if ($content -match 'name="csrf-token"') {
        $withCSRF += $template
    } else {
        $withoutCSRF += $template
    }
}

Write-Host "[2/3] CSRF Token Status:" -ForegroundColor Yellow
Write-Host "   ✅ Already have CSRF meta tag: $($withCSRF.Count)" -ForegroundColor Green
Write-Host "   ❌ Missing CSRF meta tag: $($withoutCSRF.Count)" -ForegroundColor Red
Write-Host ""

if ($withoutCSRF.Count -eq 0) {
    Write-Host "✅ All React templates already have CSRF meta tag!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Templates with CSRF:" -ForegroundColor Cyan
    foreach ($template in $withCSRF) {
        Write-Host "   ✅ $($template.Name)" -ForegroundColor Green
    }
    exit 0
}

Write-Host "Templates missing CSRF:" -ForegroundColor Yellow
foreach ($template in $withoutCSRF) {
    Write-Host "   ❌ $($template.Name)" -ForegroundColor Red
}
Write-Host ""

# Ask for confirmation
$confirm = Read-Host "Add CSRF meta tag to these $($withoutCSRF.Count) templates? (y/n)"
if ($confirm -ne 'y' -and $confirm -ne 'Y') {
    Write-Host "Aborted by user" -ForegroundColor Yellow
    exit 0
}
Write-Host ""

Write-Host "[3/3] Adding CSRF meta tag..." -ForegroundColor Yellow

$updated = 0
$failed = 0

foreach ($template in $withoutCSRF) {
    try {
        Write-Host "   Processing: $($template.Name)" -ForegroundColor Cyan
        
        $content = Get-Content $template.FullName -Raw
        
        # Find the {% block extra_head %} or {% block head %} section
        # Pattern 1: Look for {% block extra_head %}
        if ($content -match '{% block extra_head %}') {
            $pattern = '({% block extra_head %})'
            $replacement = '$1`n  <meta name="csrf-token" content="{{ csrf_token }}">'
            $content = $content -replace $pattern, $replacement
            $updated++
            Write-Host "      ✅ Added to extra_head block" -ForegroundColor Green
        }
        # Pattern 2: Look for {% block head %}
        elseif ($content -match '{% block head %}') {
            $pattern = '({% block head %})'
            $replacement = '$1`n  <meta name="csrf-token" content="{{ csrf_token }}">'
            $content = $content -replace $pattern, $replacement
            $updated++
            Write-Host "      ✅ Added to head block" -ForegroundColor Green
        }
        # Pattern 3: Create extra_head block after title block
        elseif ($content -match '{% block title %}.*?{% endblock %}') {
            $pattern = '({% block title %}.*?{% endblock %})'
            $replacement = '$1`n`n{% block extra_head %}`n  <meta name="csrf-token" content="{{ csrf_token }}">`n{% endblock %}'
            $content = $content -replace $pattern, $replacement
            $updated++
            Write-Host "      ✅ Created extra_head block" -ForegroundColor Green
        }
        # Pattern 4: Add at the beginning of file (fallback)
        else {
            $lines = $content -split "`n"
            # Find the first {% extends %} or {% load %} line
            $insertIndex = 0
            for ($i = 0; $i -lt $lines.Count; $i++) {
                if ($lines[$i] -match '{% extends|{% load') {
                    $insertIndex = $i + 1
                    break
                }
            }
            
            # Insert after extends/load
            $newLines = @()
            $newLines += $lines[0..$insertIndex]
            $newLines += ""
            $newLines += "{% block extra_head %}"
            $newLines += '  <meta name="csrf-token" content="{{ csrf_token }}">'
            $newLines += "{% endblock %}"
            $newLines += ""
            if ($insertIndex + 1 -lt $lines.Count) {
                $newLines += $lines[($insertIndex + 1)..($lines.Count - 1)]
            }
            
            $content = $newLines -join "`n"
            $updated++
            Write-Host "      ✅ Added at top of file" -ForegroundColor Green
        }
        
        # Write back to file
        $content | Set-Content $template.FullName -NoNewline
        
    } catch {
        Write-Host "      ❌ Failed: $_" -ForegroundColor Red
        $failed++
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Update Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "   ✅ Updated: $updated templates" -ForegroundColor Green
Write-Host "   ❌ Failed: $failed templates" -ForegroundColor Red
Write-Host "   ✅ Already had CSRF: $($withCSRF.Count) templates" -ForegroundColor Green
Write-Host ""

if ($failed -gt 0) {
    Write-Host "⚠️ Some templates failed to update. Please check them manually." -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "1. Review the changes in each template" -ForegroundColor White
Write-Host "2. Ensure views have @ensure_csrf_cookie decorator" -ForegroundColor White
Write-Host "3. Update React components to use import { getCSRFToken } from '@/utils/csrf'" -ForegroundColor White
Write-Host "4. Rebuild React frontend: cd frontend && npm run build" -ForegroundColor White
Write-Host "5. Deploy to production" -ForegroundColor White
Write-Host ""

# Show list of updated files
if ($updated -gt 0) {
    Write-Host "Updated files:" -ForegroundColor Cyan
    foreach ($template in $withoutCSRF) {
        if (Test-Path $template.FullName) {
            Write-Host "   - $($template.Name)" -ForegroundColor White
        }
    }
    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Script completed!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

