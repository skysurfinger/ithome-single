# 每小时更新 IT之家单列版快照并推送到 GitHub（供 Pages 公网自动更新）
$ErrorActionPreference = 'Stop'
$dir = 'C:\Users\Administrator\.local\share\TeleAgent\TeleAgent的工作空间\IT之家单列版'
$tokenFile = 'C:\Users\Administrator\.local\share\TeleAgent\TeleAgent的工作空间\.temp\github_iptv_token.txt'
$log = Join-Path $dir 'sync.log'

function Log($msg) {
  $line = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' ' + $msg
  Add-Content -Path $log -Value $line -Encoding UTF8
}

try {
  if (-not (Test-Path $tokenFile)) { Log 'ERROR: token file missing'; exit 1 }
  $token = (Get-Content $tokenFile -Raw).Trim()
  Set-Location $dir

  git fetch origin 2>$null
  git reset --hard origin/main 2>$null

  python build_snapshot.py
  if ($LASTEXITCODE -ne 0) { Log 'ERROR: build_snapshot failed'; exit 1 }

  git add index.html
  $dirty = git diff --cached --quiet; $code = $LASTEXITCODE
  if ($code -eq 0) {
    Log 'no change'
    exit 0
  }

  $msg = 'snapshot ' + (Get-Date -Format 'yyyy-MM-dd HH:mm')
  git -c user.name='ithome-snapshot-bot' -c user.email='ithome-snapshot-bot@users.noreply.github.com' commit -m $msg 2>$null
  git push "https://x-access-token:$token@github.com/skysurfinger/ithome-single.git" HEAD:main 2>$null
  if ($LASTEXITCODE -eq 0) { Log 'pushed OK' } else { Log 'ERROR: push failed'; exit 1 }
} catch {
  Log ('ERROR: ' + $_.Exception.Message)
  exit 1
}